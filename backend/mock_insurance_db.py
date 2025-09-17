import sqlite3
from uuid import uuid4

conn = sqlite3.connect('/Users/akshitagrawal/Knowledge-graph-RAG/mock_insurance.db')
cursor = conn.cursor()

# Users table
cursor.execute('''
CREATE TABLE IF NOT EXISTS users (
    insurance_user_id TEXT PRIMARY KEY,
    username TEXT UNIQUE,
    password TEXT,
    policy_number TEXT,
    email TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
''')

# Seed with one mock user
cursor.execute('''
INSERT OR IGNORE INTO users (insurance_user_id, username, password, policy_number, email)
VALUES (?, ?, ?, ?, ?)
''', (str(uuid4()), "test_user", "test_pass", "MOCK_POLICY_001", "test_user@example.com"))

conn.commit()
