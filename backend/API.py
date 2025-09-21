from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
import requests
import sqlite3
from database import db_session
from graph_pipeline import run_graph_message
from mock_insurance_db import insurance_credentials_db
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from uuid import uuid4
from fastapi import FastAPI, UploadFile, File, Form
from fastapi import FastAPI, UploadFile, File, Form
import os

from chunker2 import chunk_pdf
from ner_extractor import map_keywords_to_chunks
from keyword_filter import filter_keys
from graph_builder2 import KnowledgeGraphBuilder
import io
from config import DOCUMENTS_DIR, NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD, NEO4J_DATABASE
from graph_retriever2 import GraphRetriever



app = FastAPI()

# Add middleware to log request data for debugging
@app.middleware("http")
async def log_requests(request: Request, call_next):
    if request.url.path == "/chat":
        body = await request.body()
        print(f"[DEBUG] Raw request body: {body.decode()}")
    response = await call_next(request)
    return response

# Enable CORS for local development and simple static hosting
origins = [
    "http://localhost:3000",  # For local testing
    "https://knowledge-graph-rag-kpzl.onrender.com/" # Replace with your actual domain
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Get database path from environment or use default
import config
DB_PATH = os.getenv("THREADS_DB_PATH") or os.path.join(config.BASE_DIR, "threads.db")


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

class InsuranceCredentialsRequest(BaseModel):
    user_id: str
    thread_id: str
    insurance_username: str
    insurance_password: str

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
    try:
        print(f"[DEBUG] ChatRequest received: user_message='{req.user_message}', user_id='{req.user_id}', thread_id='{req.thread_id}'")
        # Persist the user's message to the thread
        db_session.add_message(req.thread_id, "user", req.user_message)
        # Run the message through the graph
        response = run_graph_message(req.user_message, req.user_id, req.thread_id)
        print(response)
        # Persist the assistant response
        db_session.add_message(req.thread_id, "bot", response['response'])
        return {"response" : response}
    except Exception as e:
        print(f"[ERROR] Chat endpoint failed: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Chat processing failed: {str(e)}")

@app.post("/insurance-login")
def insurance_login(req: InsuranceCredentialsRequest):
    """
    Login to insurance provider and return insurance user ID.
    This endpoint validates insurance credentials with the mock insurance API and stores them.
    """
    try:
        # Call the mock insurance API directly
        response = requests.post(
            "http://localhost:5000/login",
            json={
                "username": req.insurance_username,
                "password": req.insurance_password
            }
        )
        response.raise_for_status()
        data = response.json()
        
        if not data.get("success"):
            raise HTTPException(
                status_code=401,
                detail="Invalid insurance credentials"
            )
        
        insurance_user_id = data.get("user_id")
        if not insurance_user_id:
            raise HTTPException(
                status_code=500,
                detail="Insurance login failed: user_id missing"
            )
        
        # Store the credentials in the database for future use
        insurance_credentials_db.store_insurance_credentials(
            chatbot_user_id=req.user_id,
            thread_id=req.thread_id,
            insurance_username=req.insurance_username,
            insurance_password=req.insurance_password,
            insurance_user_id=insurance_user_id
        )
        
        print(f"[DEBUG] Stored insurance credentials for user {req.user_id}")
        
        return {
            "status": "success",
            "message": "Insurance login successful",
            "insurance_user_id": insurance_user_id,
            "insurance_username": req.insurance_username
        }
        
    except requests.exceptions.HTTPError as e:
        print(f"[ERROR] Insurance API returned HTTP error: {e}")
        if e.response.status_code == 401:
            raise HTTPException(
                status_code=401,
                detail="Invalid insurance credentials"
            )
        else:
            raise HTTPException(
                status_code=500,
                detail="Insurance provider error"
            )
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Insurance API request failed: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to connect to insurance provider"
        )
    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] Insurance login failed: {e}")
        raise HTTPException(
            status_code=400,
            detail="Invalid insurance credentials. Please check your username and password."
        )

@app.delete("/users/{user_id}")
def delete_user_account(user_id: str):
    """Delete user account and all associated data from chatbot database"""
    # Check if user exists
    user = db_session.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Delete user account and all associated data from chatbot database
    success = db_session.delete_user_account(user_id)
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete user account")
    
    # Also delete insurance credentials from insurance database
    try:
        insurance_credentials_db.delete_insurance_credentials(user_id)
    except Exception as e:
        print(f"Warning: Failed to delete insurance credentials: {e}")
        # Don't fail the whole operation if insurance credentials deletion fails
    
    return {
        "status": "success", 
        "message": "User account and all associated data deleted successfully"
    }




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
def upload_pdf(thread_id: str = Form(...), file: UploadFile = File(...)):
    """
    Upload a PDF for an existing thread, directly chunk and build KG in memory.
    """
    # Read file content from memory
    file_content = file.file.read()
    file_stream = io.BytesIO(file_content)

    # --- 1. Chunk PDF ---
    chunks = chunk_pdf(file_stream)   # make sure chunk_pdf accepts file-like object
    print(f"Loaded {len(chunks)} chunks for thread {thread_id}.")

    # --- 2. Extract keywords ---
    key_chunk_map = map_keywords_to_chunks(chunks)
    print(f"NER keywords {len(key_chunk_map.keys())} unique keywords/entities")
    filtered_map = filter_keys(key_chunk_map, len(chunks))
    print(f"Filtered {len(filtered_map.keys())} unique keywords/entities")
    keywords = sorted(filtered_map.keys())

    # --- 3. Build Knowledge Graph ---
    kg = KnowledgeGraphBuilder()
    kg.clear_graph(thread_id)   # only clear graph for this thread
    print(f"Cleared existing graph for thread {thread_id}.")
    kg.build_graph_from_map(filtered_map, thread_id)   # pass thread_id to tag all nodes/edges
    kg.close()
    print("Knowledge graph built successfully.")

    return {
        "thread_id": thread_id,
        "chunks": len(chunks),
        "keywords": len(filtered_map.keys()),
        "status": "graph built from in-memory PDF"
    }


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

