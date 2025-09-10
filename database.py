import sqlite3
conn = sqlite3.connect('threads.db')
cursor = conn.cursor()

#Users table
cursor.execute('''
CREATE TABLE IF NOT EXISTS users (
    user_id TEXT PRIMARY KEY,
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

conn.commit()

class DB:
    def add_user(self, user_id, name, email):
        cursor.execute('''
        INSERT INTO users (user_id, name, email) VALUES (?, ?, ?)
        ''', (user_id, name, email))
        conn.commit()

    def get_user(self, user_id):
        cursor.execute('''
        SELECT * FROM users WHERE user_id = ?
        ''', (user_id,))
        return cursor.fetchone()
    
    def add_thread(self, thread_id, user_id, document_path, status):
        cursor.execute('''
        INSERT INTO threads (thread_id, user_id, document_path, status) VALUES (?, ?, ?, ?)
        ''', (thread_id, user_id, document_path, "started"))
        conn.commit()

    def get_document_path(self, thread_id):
        cursor.execute('''
        SELECT document_path FROM threads WHERE thread_id = ?
        ''', (thread_id,))
        result = cursor.fetchone()
        return result[0] if result else None
    
    def update_status(self, thread_id, status):
        cursor.execute('''
        UPDATE threads SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE thread_id = ?
        ''', (status, thread_id))
        conn.commit()

    def get_status(self, thread_id):
        cursor.execute('SELECT status FROM threads WHERE thread_id = ?', (thread_id,))
        result = cursor.fetchone()
        return result[0] if result else None
    

db_session = DB()

