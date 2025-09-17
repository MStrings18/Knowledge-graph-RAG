from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import requests
import sqlite3
from database import db_session
from graph_pipeline import run_graph_message
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from uuid import uuid4
from fastapi import UploadFile, File

app = FastAPI()

# Enable CORS for local development and simple static hosting
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_PATH = "/Users/akshitagrawal/Knowledge-graph-RAG/threads.db"


class ChatRequest(BaseModel):
    user_message: str
    user_id: str 
    thread_id: str        

class LoginRequest(BaseModel):
    username: str
    password: str

class SignupRequest(BaseModel):
    username: str
    password: str
    email: str
    name: str

@app.post("/login")
def login(req: LoginRequest):
    # In your schema users table has email, not username. We'll treat provided username as email.
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT user_id FROM users WHERE username = ? AND password = ?",
        (req.username, req.password),
    )
    row = cursor.fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Invalid credentials")
    user_id = row[0]
    return {"status":"success", "user_id": user_id}

@app.get("/history/{thread_id}")
def get_history(thread_id: str):
    messages = db_session.get_messages(thread_id)
    # Normalize rows to dicts
    history = [
        {"sender": sender, "message": message, "timestamp": timestamp}
        for sender, message, timestamp in messages
    ]
    return {"history": history}


@app.post("/chat")
def chat(req: ChatRequest):
    # Persist the user's message to the thread
    db_session.add_message(req.thread_id, "user", req.user_message)
    # Run the message through the graph
    response = run_graph_message(req.user_message, req.user_id, req.thread_id)
    print(response)
    # Persist the assistant response
    db_session.add_message(req.thread_id, "bot", response['response'])
    return {"response" : response}


class CreateThreadRequest(BaseModel):
    user_id: str
    document_path: str | None = None


@app.post("/threads")
def create_thread(req: CreateThreadRequest):
    thread_id = str(uuid4())
    db_session.add_thread(thread_id, req.user_id, req.document_path or "", "started")
    return {"thread_id": thread_id}


@app.get("/threads/{user_id}")
def list_threads(user_id: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT t.thread_id, t.user_id, t.document_path, t.status, t.created_at, t.updated_at,
               m.message AS first_message
        FROM threads t
        LEFT JOIN (
            SELECT thread_id, message
            FROM messages
            WHERE (thread_id, timestamp) IN (
                SELECT thread_id, MIN(timestamp)
                FROM messages
                GROUP BY thread_id
            )
        ) m ON t.thread_id = m.thread_id
        WHERE t.user_id = ?
        ORDER BY t.updated_at DESC
        """,
        (user_id,),
    )

    rows = cursor.fetchall()
    conn.close()

    threads = [
        {
            "thread_id": r[0],
            "user_id": r[1],
            "document_path": r[2],
            "status": r[3],
            "created_at": r[4],
            "updated_at": r[5],
            "first_message": r[6],
        }
        for r in rows
    ]

    return {"threads": threads}






@app.get("/")
def root():
    return RedirectResponse(url="/app/")

@app.post("/append_message")
def append_message(thread_id: str, role: str, message: str):
    db_session.add_message(thread_id, role, message)
    return {"success": True}


@app.post("/threads/upload")
def upload_pdf(user_id: str, file: UploadFile = File(...)):
    file_location = f"uploads/{uuid4()}_{file.filename}"
    with open(file_location, "wb") as f:
        f.write(file.file.read())
    thread_id = str(uuid4())
    db_session.add_thread(thread_id, user_id, file_location, "started")
    return {"thread_id": thread_id, "file_path": file_location}


@app.post("/signup")
def sign_up(req: SignupRequest):
    user_id = str(uuid4()) 
    conn = sqlite3.connect(DB_PATH)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('SELECT username, email FROM users WHERE username = ? OR email = ?', (req.username, req.email))
    existing = cursor.fetchone()

    if existing:
        if existing[0] == req.username:
            raise HTTPException(status_code=400, detail="Username already registered")
        else:
            raise HTTPException(status_code=400, detail="Email already registered")

    cursor.execute(
        "INSERT INTO users (user_id, username, password, name, email) VALUES (?, ?, ?, ?, ?)",
        (user_id, req.username, req.password, req.name, req.email),
    )
    conn.commit()
    conn.close()

    return {
        "user_id": user_id,
        "message": "User registered successfully, log in from the portal to continue",
        "status" : "success"
    }


if __name__ == "__main__":
    # Run with: uvicorn API:app --reload --port 8000
    import uvicorn
    uvicorn.run("API:app", host="0.0.0.0", port=8000, reload=True)

