import sqlite3
from uuid import uuid4

conn = sqlite3.connect('/Users/akshitagrawal/Knowledge-graph-RAG/mock_insurance.db')
cursor = conn.cursor()

# Users table (insurance provider users only)
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

class InsuranceCredentialsDB:
    """Database class for managing insurance credentials using the existing users table"""
    
    def __init__(self):
        self.conn = sqlite3.connect('/Users/akshitagrawal/Knowledge-graph-RAG/mock_insurance.db', check_same_thread=False)
        self.cursor = self.conn.cursor()
        self._initialize_database()
    
    def _initialize_database(self):
        """Initialize the insurance credentials database with proper table structure"""
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS insurance_credentials (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chatbot_user_id TEXT NOT NULL,
            insurance_username TEXT NOT NULL,
            insurance_password TEXT NOT NULL,
            insurance_user_id TEXT,
            is_valid BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(chatbot_user_id, insurance_username)
        )
        ''')
        self.conn.commit()
    
    def store_insurance_credentials(self, chatbot_user_id, insurance_username, insurance_password, insurance_user_id=None):
        """Store insurance credentials for a chatbot user"""
        self.cursor.execute('''
            INSERT OR REPLACE INTO insurance_credentials 
            (chatbot_user_id, insurance_username, insurance_password, insurance_user_id, updated_at)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
        ''', (chatbot_user_id, insurance_username, insurance_password, insurance_user_id))
        self.conn.commit()

    def get_insurance_credentials(self, chatbot_user_id):
        """Get insurance credentials for a chatbot user"""
        self.cursor.execute('''
            SELECT insurance_username, insurance_password, insurance_user_id, is_valid
            FROM insurance_credentials 
            WHERE chatbot_user_id = ? AND is_valid = 1
            ORDER BY updated_at DESC
            LIMIT 1
        ''', (chatbot_user_id,))
        result = self.cursor.fetchone()
        if result:
            return {
                'insurance_username': result[0],
                'insurance_password': result[1],
                'insurance_user_id': result[2],
                'is_valid': result[3]
            }
        return None

    def invalidate_insurance_credentials(self, chatbot_user_id, insurance_username):
        """Mark insurance credentials as invalid"""
        self.cursor.execute('''
            UPDATE insurance_credentials 
            SET is_valid = 0, updated_at = CURRENT_TIMESTAMP
            WHERE chatbot_user_id = ? AND insurance_username = ?
        ''', (chatbot_user_id, insurance_username))
        self.conn.commit()

    def update_insurance_user_id(self, chatbot_user_id, insurance_username, insurance_user_id):
        """Update the insurance_user_id after successful login"""
        self.cursor.execute('''
            UPDATE insurance_credentials 
            SET insurance_user_id = ?, updated_at = CURRENT_TIMESTAMP
            WHERE chatbot_user_id = ? AND insurance_username = ? AND is_valid = 1
        ''', (insurance_user_id, chatbot_user_id, insurance_username))
        self.conn.commit()

    def delete_insurance_credentials(self, chatbot_user_id):
        """Delete all insurance credentials for a chatbot user"""
        self.cursor.execute('DELETE FROM insurance_credentials WHERE chatbot_user_id = ?', (chatbot_user_id,))
        self.conn.commit()

# Create global instance
insurance_credentials_db = InsuranceCredentialsDB()
