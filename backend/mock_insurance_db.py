

import sqlite3
from uuid import uuid4

# Insurance users table (insurance provider users only)
# This table stores the mapping between chatbot users and their insurance credentials
conn = sqlite3.connect(r'C:\Users\Manan Verma\Coding\Projects\kg-rag\backend\mock_insurance.db')
cursor = conn.cursor()

# Check if the table exists and what columns it has
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='insurance_users'")
table_exists = cursor.fetchone() is not None

if table_exists:
    # Check existing columns
    cursor.execute("PRAGMA table_info(insurance_users)")
    columns = [column[1] for column in cursor.fetchall()]
    
    if 'chatbot_user_id' not in columns:
        print("[DEBUG] Migrating insurance_users table to new schema")
        # Drop the old table and recreate with new schema
        cursor.execute('DROP TABLE IF EXISTS insurance_users')
        table_exists = False

if not table_exists:
    cursor.execute('''
    CREATE TABLE insurance_users (
        insurance_user_id TEXT PRIMARY KEY,
        chatbot_user_id TEXT NOT NULL,
        thread_id TEXT NOT NULL,
        username TEXT NOT NULL,
        password TEXT NOT NULL,
        policy_number TEXT,
        email TEXT,
        is_valid BOOLEAN DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(chatbot_user_id, thread_id, username)
    )
    ''')
    
    # Seed with one mock user for testing
    cursor.execute('''
    INSERT OR IGNORE INTO insurance_users (insurance_user_id, chatbot_user_id, thread_id, username, password, policy_number, email)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (str(uuid4()), "test_chatbot_user", "default", "test_user", "test_pass", "MOCK_POLICY_001", "test_user@example.com"))

conn.commit()

class InsuranceCredentialsDB:
    """Database class for managing insurance credentials using the insurance_users table"""
    
    def __init__(self):
        self.conn = sqlite3.connect(r'C:\Users\Manan Verma\Coding\Projects\kg-rag\backend\mock_insurance.db', check_same_thread=False)
        self.cursor = self.conn.cursor()
    
    def store_insurance_credentials(self, chatbot_user_id, thread_id, insurance_username, insurance_password, insurance_user_id=None):
        """Store insurance credentials for a chatbot user in a specific thread"""
        if insurance_user_id is None:
            insurance_user_id = str(uuid4())
        
        self.cursor.execute('''
            INSERT OR REPLACE INTO insurance_users 
            (insurance_user_id, chatbot_user_id, thread_id, username, password, updated_at)
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ''', (insurance_user_id, chatbot_user_id, thread_id, insurance_username, insurance_password))
        self.conn.commit()

    def get_insurance_credentials(self, chatbot_user_id, thread_id):
        """Get insurance credentials for a chatbot user in a specific thread"""
        self.cursor.execute('''
            SELECT username, password, insurance_user_id, is_valid
            FROM insurance_users 
            WHERE chatbot_user_id = ? AND thread_id = ? AND is_valid = 1
            ORDER BY updated_at DESC
            LIMIT 1
        ''', (chatbot_user_id, thread_id))
        result = self.cursor.fetchone()
        if result:
            return {
                'insurance_username': result[0],
                'insurance_password': result[1],
                'insurance_user_id': result[2],
                'is_valid': result[3]
            }
        return None

    def invalidate_insurance_credentials(self, chatbot_user_id, thread_id, insurance_username):
        """Mark insurance credentials as invalid for a specific thread"""
        self.cursor.execute('''
            UPDATE insurance_users 
            SET is_valid = 0, updated_at = CURRENT_TIMESTAMP
            WHERE chatbot_user_id = ? AND thread_id = ? AND username = ?
        ''', (chatbot_user_id, thread_id, insurance_username))
        self.conn.commit()

    def update_insurance_user_id(self, chatbot_user_id, thread_id, insurance_username, insurance_user_id):
        """Update the insurance_user_id after successful login for a specific thread"""
        self.cursor.execute('''
            UPDATE insurance_users 
            SET insurance_user_id = ?, updated_at = CURRENT_TIMESTAMP
            WHERE chatbot_user_id = ? AND thread_id = ? AND username = ? AND is_valid = 1
        ''', (insurance_user_id, chatbot_user_id, thread_id, insurance_username))
        self.conn.commit()

    def delete_insurance_credentials(self, chatbot_user_id):
        """Delete all insurance credentials for a chatbot user"""
        self.cursor.execute('DELETE FROM insurance_users WHERE chatbot_user_id = ?', (chatbot_user_id,))
        self.conn.commit()

# Create global instance
insurance_credentials_db = InsuranceCredentialsDB()
