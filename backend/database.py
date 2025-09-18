import sqlite3
conn = sqlite3.connect('/Users/akshitagrawal/Knowledge-graph-RAG/backend/threads.db', check_same_thread=False)
cursor = conn.cursor()

#Users table
cursor.execute('''
CREATE TABLE IF NOT EXISTS users (
    user_id TEXT PRIMARY KEY,
    username TEXT NOT NULL,
    password TEXT NOT NULL,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
               
)
''')


#Threads table
cursor.execute('''
CREATE TABLE IF NOT EXISTS threads (
    thread_id TEXT PRIMARY KEY,
    user_id TEXT,
    document_path TEXT NOT NULL, 
    status TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
''')

cursor.execute('''
               
    CREATE TABLE IF NOT EXISTS messages (
        message_id INTEGER PRIMARY KEY AUTOINCREMENT,
        thread_id TEXT,
        sender TEXT,  -- "user" or "bot"
        message TEXT,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
''')

# Insurance credentials are stored in mock_insurance.db, not here

conn.commit()

class DB:
    def __init__(self):
        self.conn = sqlite3.connect('/Users/akshitagrawal/Knowledge-graph-RAG/backend/threads.db', check_same_thread=False)
        self.cursor = self.conn.cursor()
    
    # --- existing methods ---
    def add_user(self, user_id, name, email):
        self.cursor.execute('''
        INSERT INTO users (user_id, name, email) VALUES (?, ?, ?)
        ''', (user_id, name, email))
        self.conn.commit()

    def authenticate(self, username: str, password: str):
        self.cursor.execute("SELECT user_id FROM users WHERE username = ? AND password = ?",
                            (username, password))
        result = self.cursor.fetchone()
        return result[0] if result else None

    def get_user(self, user_id):
        self.cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        return self.cursor.fetchone()

    def add_thread(self, thread_id, user_id, document_path, status):
        self.cursor.execute('''
        INSERT INTO threads (thread_id, user_id, document_path, status) VALUES (?, ?, ?, ?)
        ''', (thread_id, user_id, document_path, status))
        self.conn.commit()

    def get_document_path(self, thread_id):
        self.cursor.execute('SELECT document_path FROM threads WHERE thread_id = ?', (thread_id,))
        result = self.cursor.fetchone()
        return result[0] if result else None

    def update_status(self, thread_id, status):
        self.cursor.execute('''
        UPDATE threads SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE thread_id = ?
        ''', (status, thread_id))
        self.conn.commit()

    def get_status(self, thread_id):
        self.cursor.execute('SELECT status FROM threads WHERE thread_id = ?', (thread_id,))
        result = self.cursor.fetchone()
        return result[0] if result else None

    # --- NEW: Message methods ---
    def add_message(self, thread_id, sender, message):
        self.cursor.execute('''
        INSERT INTO messages (thread_id, sender, message) VALUES (?, ?, ?)
        ''', (thread_id, sender, message))
        self.conn.commit()

    def get_messages(self, thread_id):
        self.cursor.execute('SELECT sender, message, timestamp FROM messages WHERE thread_id = ? ORDER BY timestamp ASC', (thread_id,))
        return self.cursor.fetchall()


    def update_thread_file(self, thread_id, document_path):
        self.cursor.execute('''
            UPDATE threads
            SET document_path = ?
            WHERE thread_id = ?
        ''', (document_path, thread_id))
        self.conn.commit()

    # Insurance credentials methods are in mock_insurance_db.py

    # --- Account deletion methods ---
    def delete_user_account(self, user_id):
        """Delete user account and all associated data from chatbot database"""
        try:
            # Delete all user's messages
            self.cursor.execute('''
                DELETE FROM messages 
                WHERE thread_id IN (SELECT thread_id FROM threads WHERE user_id = ?)
            ''', (user_id,))
            
            # Delete all user's threads
            self.cursor.execute('DELETE FROM threads WHERE user_id = ?', (user_id,))
            
            # Delete the user
            self.cursor.execute('DELETE FROM users WHERE user_id = ?', (user_id,))
            
            self.conn.commit()
            return True
        except Exception as e:
            self.conn.rollback()
            print(f"Error deleting user account: {e}")
            return False

    
db_session = DB()