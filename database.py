import sqlite3
import json
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self, db_name='vbspu_bot.db'):
        self.db_name = db_name
        self.init_database()
    
    def init_database(self):
        """Initialize database with required tables"""
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            
            # Users table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    email TEXT,
                    password_hash TEXT,
                    role TEXT DEFAULT 'user',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_login TIMESTAMP
                )
            ''')
            
            # Chat history table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS chat_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    session_id TEXT,
                    user_message TEXT,
                    bot_response TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            ''')
            
            # Scraped data table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS scraped_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    category TEXT NOT NULL,
                    data TEXT NOT NULL,
                    source_url TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Bot settings table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS bot_settings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    setting_key TEXT UNIQUE NOT NULL,
                    setting_value TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Admin logs table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS admin_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    admin_id INTEGER,
                    action TEXT NOT NULL,
                    details TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (admin_id) REFERENCES users (id)
                )
            ''')
            
            # PDF uploads table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS pdf_uploads (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    filename TEXT NOT NULL,
                    original_filename TEXT NOT NULL,
                    category TEXT,
                    tags TEXT,
                    description TEXT,
                    file_size INTEGER,
                    upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    uploaded_by INTEGER,
                    status TEXT DEFAULT 'active',
                    FOREIGN KEY (uploaded_by) REFERENCES users (id)
                )
            ''')
            
            # PDF content table for search
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS pdf_content (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    pdf_id INTEGER NOT NULL,
                    page_number INTEGER,
                    content TEXT,
                    keywords TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (pdf_id) REFERENCES pdf_uploads (id)
                )
            ''')
            
            # Query-PDF mapping table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS query_pdf_mapping (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    query_text TEXT NOT NULL,
                    pdf_id INTEGER,
                    relevance_score REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (pdf_id) REFERENCES pdf_uploads (id)
                )
            ''')
            
            # Insert default admin user if not exists
            cursor.execute('''
                INSERT OR IGNORE INTO users (username, email, password_hash, role)
                VALUES ('admin', 'admin@vbspu.ac.in', 'admin123', 'admin')
            ''')
            
            # Insert default bot settings
            default_settings = [
                ('bot_name', 'VBSPU AI Assistant', 'Name of the bot'),
                ('max_response_length', '500', 'Maximum character limit for responses'),
                ('auto_scrape_interval', '3600', 'Auto scrape interval in seconds'),
                ('welcome_message', 'नमस्ते! मैं VBSPU AI Assistant हूं। क्या जानना चाहते हैं आप?', 'Welcome message for users'),
                ('off_topic_response', 'Main sirf VBSPU se related queries me hi madad kar sakta hoon.', 'Response for off-topic queries')
            ]
            
            for key, value, desc in default_settings:
                cursor.execute('''
                    INSERT OR IGNORE INTO bot_settings (setting_key, setting_value, description)
                    VALUES (?, ?, ?)
                ''', (key, value, desc))
            
            conn.commit()
            conn.close()
            logger.info("Database initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing database: {e}")
    
    def get_connection(self):
        """Get database connection"""
        return sqlite3.connect(self.db_name)
    
    # User management
    def create_user(self, username, email, password_hash, role='user'):
        """Create a new user"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO users (username, email, password_hash, role)
                VALUES (?, ?, ?, ?)
            ''', (username, email, password_hash, role))
            conn.commit()
            user_id = cursor.lastrowid
            conn.close()
            return user_id
        except Exception as e:
            logger.error(f"Error creating user: {e}")
            return None
    
    def authenticate_user(self, username, password):
        """Authenticate user"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, username, email, role FROM users
                WHERE username = ? AND password_hash = ?
            ''', (username, password))
            user = cursor.fetchone()
            conn.close()
            return user
        except Exception as e:
            logger.error(f"Error authenticating user: {e}")
            return None
    
    def get_user_by_id(self, user_id):
        """Get user by ID"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, username, email, password_hash, role, created_at, last_login
                FROM users WHERE id = ?
            ''', (user_id,))
            user = cursor.fetchone()
            conn.close()
            return user
        except Exception as e:
            logger.error(f"Error getting user by ID: {e}")
            return None
    
    def update_user(self, user_id, username, email=None, password=None, role='user'):
        """Update user"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            if password:
                cursor.execute('''
                    UPDATE users 
                    SET username = ?, email = ?, password_hash = ?, role = ?
                    WHERE id = ?
                ''', (username, email, password, role, user_id))
            else:
                cursor.execute('''
                    UPDATE users 
                    SET username = ?, email = ?, role = ?
                    WHERE id = ?
                ''', (username, email, role, user_id))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Error updating user: {e}")
            return False
    
    def delete_user(self, user_id):
        """Delete user"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('DELETE FROM users WHERE id = ?', (user_id,))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Error deleting user: {e}")
            return False
    
    def create_user(self, username, email, password, role='user'):
        """Create new user"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO users (username, email, password_hash, role, created_at)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            ''', (username, email, password, role))
            user_id = cursor.lastrowid
            conn.commit()
            conn.close()
            return user_id
        except Exception as e:
            logger.error(f"Error creating user: {e}")
            return None
    
    def update_last_login(self, user_id):
        """Update user's last login timestamp"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE users 
                SET last_login = CURRENT_TIMESTAMP 
                WHERE id = ?
            ''', (user_id,))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Error updating last login: {e}")
            return False
    
    def get_user_by_username(self, username):
        """Get user by username"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, username, email, password_hash, role, created_at, last_login
                FROM users WHERE username = ?
            ''', (username,))
            user = cursor.fetchone()
            conn.close()
            return user
        except Exception as e:
            logger.error(f"Error getting user by username: {e}")
            return None
    
    def get_all_users(self):
        """Get all users"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT id, username, email, role, created_at, last_login FROM users ORDER BY created_at DESC')
            users = cursor.fetchall()
            conn.close()
            
            # Convert to list of dictionaries for better JSON handling
            user_list = []
            for user in users:
                user_list.append({
                    'id': user[0],
                    'username': user[1],
                    'email': user[2],
                    'role': user[3],
                    'created_at': user[4],
                    'last_login': user[5]
                })
            
            return user_list
        except Exception as e:
            logger.error(f"Error getting all users: {e}")
            return []
    
    def get_user_by_id(self, user_id):
        """Get user by ID"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, username, email, role, created_at, last_login
                FROM users WHERE id = ?
            ''', (user_id,))
            user = cursor.fetchone()
            conn.close()
            return user
        except Exception as e:
            logger.error(f"Error getting user: {e}")
            return None
    
    # Chat history
    def save_chat_message(self, user_id, session_id, user_message, bot_response):
        """Save chat message to database"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO chat_history (user_id, session_id, user_message, bot_response)
                VALUES (?, ?, ?, ?)
            ''', (user_id, session_id, user_message, bot_response))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Error saving chat message: {e}")
    
    def get_chat_history(self, user_id=None, session_id=None, limit=50):
        """Get chat history"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            if user_id:
                cursor.execute('''
                    SELECT id, user_message, bot_response, timestamp, session_id
                    FROM chat_history WHERE user_id = ?
                    ORDER BY timestamp DESC LIMIT ?
                ''', (user_id, limit))
            elif session_id:
                cursor.execute('''
                    SELECT id, user_message, bot_response, timestamp, session_id
                    FROM chat_history WHERE session_id = ?
                    ORDER BY timestamp DESC LIMIT ?
                ''', (session_id, limit))
            else:
                cursor.execute('''
                    SELECT id, user_message, bot_response, timestamp, session_id
                    FROM chat_history ORDER BY timestamp DESC LIMIT ?
                ''', (limit,))
            
            history = cursor.fetchall()
            conn.close()
            
            # Convert to list of dictionaries for better JSON handling
            chat_list = []
            for chat in history:
                chat_list.append({
                    'id': chat[0],
                    'user_message': chat[1],
                    'bot_response': chat[2],
                    'timestamp': chat[3],
                    'session_id': chat[4]
                })
            
            return chat_list
        except Exception as e:
            logger.error(f"Error getting chat history: {e}")
            return []
    
    # Scraped data management
    def save_scraped_data(self, category, data, source_url=None):
        """Save scraped data"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Check if data exists for this category
            cursor.execute('SELECT id FROM scraped_data WHERE category = ?', (category,))
            existing = cursor.fetchone()
            
            data_json = json.dumps(data)
            
            if existing:
                # Update existing data
                cursor.execute('''
                    UPDATE scraped_data 
                    SET data = ?, source_url = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE category = ?
                ''', (data_json, source_url, category))
            else:
                # Insert new data
                cursor.execute('''
                    INSERT INTO scraped_data (category, data, source_url)
                    VALUES (?, ?, ?)
                ''', (category, data_json, source_url))
            
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Error saving scraped data: {e}")
    
    def get_scraped_data(self, category=None):
        """Get scraped data"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            if category:
                cursor.execute('''
                    SELECT data, updated_at FROM scraped_data WHERE category = ?
                ''', (category,))
                result = cursor.fetchone()
                conn.close()
                if result:
                    return json.loads(result[0])
                else:
                    return None
            else:
                cursor.execute('SELECT category, data, updated_at FROM scraped_data')
                results = cursor.fetchall()
                conn.close()
                data = {}
                for category, data_json, updated_at in results:
                    data[category] = json.loads(data_json)
                return data
        except Exception as e:
            logger.error(f"Error loading from database: {e}")
            return None if category else {}
    
    # Bot settings
    def get_setting(self, key):
        """Get bot setting"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                SELECT setting_value FROM bot_settings WHERE setting_key = ?
            ''', (key,))
            result = cursor.fetchone()
            conn.close()
            return result[0] if result else None
        except Exception as e:
            logger.error(f"Error getting setting: {e}")
            return None
    
    # PDF Management Functions
    def save_pdf_upload(self, filename, original_filename, category, tags, description, file_size, uploaded_by):
        """Save PDF upload information"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO pdf_uploads (filename, original_filename, category, tags, description, file_size, uploaded_by)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (filename, original_filename, category, tags, description, file_size, uploaded_by))
            pdf_id = cursor.lastrowid
            conn.commit()
            conn.close()
            return pdf_id
        except Exception as e:
            logger.error(f"Error saving PDF upload: {e}")
            return None
    
    def get_pdf_uploads(self, category=None, status='active'):
        """Get PDF uploads"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            if category:
                cursor.execute('''
                    SELECT * FROM pdf_uploads WHERE category = ? AND status = ? ORDER BY upload_date DESC
                ''', (category, status))
            else:
                cursor.execute('''
                    SELECT * FROM pdf_uploads WHERE status = ? ORDER BY upload_date DESC
                ''', (status,))
            
            uploads = cursor.fetchall()
            conn.close()
            return uploads
        except Exception as e:
            logger.error(f"Error getting PDF uploads: {e}")
            return []
    
    def save_pdf_content(self, pdf_id, page_number, content, keywords):
        """Save PDF content for search"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO pdf_content (pdf_id, page_number, content, keywords)
                VALUES (?, ?, ?, ?)
            ''', (pdf_id, page_number, content, keywords))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Error saving PDF content: {e}")
    
    def search_pdf_content(self, query):
        """Search PDF content based on query"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Search in content and keywords
            cursor.execute('''
                SELECT DISTINCT pdf_id, content, page_number, keywords
                FROM pdf_content 
                WHERE content LIKE ? OR keywords LIKE ?
                ORDER BY page_number
            ''', (f'%{query}%', f'%{query}%'))
            
            results = cursor.fetchall()
            conn.close()
            return results
        except Exception as e:
            logger.error(f"Error searching PDF content: {e}")
            return []
    
    def save_query_pdf_mapping(self, query_text, pdf_id, relevance_score):
        """Save query-PDF mapping"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO query_pdf_mapping (query_text, pdf_id, relevance_score)
                VALUES (?, ?, ?)
            ''', (query_text, pdf_id, relevance_score))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Error saving query-PDF mapping: {e}")
    
    def get_relevant_pdfs(self, query, limit=5):
        """Get relevant PDFs for a query"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # First check exact query matches
            cursor.execute('''
                SELECT DISTINCT p.*, q.relevance_score
                FROM pdf_uploads p
                JOIN query_pdf_mapping q ON p.id = q.pdf_id
                WHERE q.query_text LIKE ? AND p.status = 'active'
                ORDER BY q.relevance_score DESC, q.created_at DESC
                LIMIT ?
            ''', (f'%{query}%', limit))
            
            exact_matches = cursor.fetchall()
            
            # If no exact matches, search in content
            if not exact_matches:
                cursor.execute('''
                    SELECT DISTINCT p.*, 0.5 as relevance_score
                    FROM pdf_uploads p
                    JOIN pdf_content c ON p.id = c.pdf_id
                    WHERE (c.content LIKE ? OR c.keywords LIKE ? OR p.tags LIKE ? OR p.description LIKE ?)
                    AND p.status = 'active'
                    ORDER BY relevance_score DESC, p.upload_date DESC
                    LIMIT ?
                ''', (f'%{query}%', f'%{query}%', f'%{query}%', f'%{query}%', limit))
                
                exact_matches = cursor.fetchall()
            
            conn.close()
            return exact_matches
        except Exception as e:
            logger.error(f"Error getting relevant PDFs: {e}")
            return []
    
    def delete_pdf(self, pdf_id):
        """Delete PDF and its content"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Delete PDF content
            cursor.execute('DELETE FROM pdf_content WHERE pdf_id = ?', (pdf_id,))
            
            # Delete query mappings
            cursor.execute('DELETE FROM query_pdf_mapping WHERE pdf_id = ?', (pdf_id,))
            
            # Delete PDF upload record
            cursor.execute('DELETE FROM pdf_uploads WHERE id = ?', (pdf_id,))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Error deleting PDF: {e}")
            return False
    
    def get_all_settings(self):
        """Get all bot settings"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT setting_key, setting_value FROM bot_settings')
            settings = cursor.fetchall()
            conn.close()
            return {key: value for key, value in settings}
        except Exception as e:
            logger.error(f"Error getting all settings: {e}")
            return {}
    
    def update_setting(self, key, value):
        """Update bot setting"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE bot_settings 
                SET setting_value = ?, updated_at = CURRENT_TIMESTAMP
                WHERE setting_key = ?
            ''', (value, key))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Error updating setting: {e}")
            return False
    
    def get_all_settings(self):
        """Get all bot settings"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT setting_key, setting_value, description FROM bot_settings')
            results = cursor.fetchall()
            conn.close()
            return {key: {'value': value, 'description': desc} for key, value, desc in results}
        except Exception as e:
            logger.error(f"Error getting all settings: {e}")
            return {}
    
    # Admin logs
    def log_admin_action(self, admin_id, action, details=None):
        """Log admin action"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO admin_logs (admin_id, action, details)
                VALUES (?, ?, ?)
            ''', (admin_id, action, details))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Error logging admin action: {e}")
    
    def get_admin_logs(self, limit=100):
        """Get admin logs"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                SELECT al.action, al.details, al.timestamp, u.username
                FROM admin_logs al
                JOIN users u ON al.admin_id = u.id
                ORDER BY al.timestamp DESC LIMIT ?
            ''', (limit,))
            logs = cursor.fetchall()
            conn.close()
            
            # Convert to list of dictionaries for better JSON handling
            log_list = []
            for log in logs:
                log_list.append({
                    'action': log[0],
                    'details': log[1],
                    'timestamp': log[2],
                    'admin_username': log[3]
                })
            
            return log_list
        except Exception as e:
            logger.error(f"Error getting admin logs: {e}")
            return []

# Initialize database
db = DatabaseManager()
