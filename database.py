"""
Database Manager - Complete fixed version with all required methods
"""
import sqlite3
import json
import time
from datetime import datetime
from pathlib import Path

class DatabaseManager:
    def __init__(self, db_path):
        self.db_path = db_path
        self.conn = None
        self.cursor = None
        self.connect()
        self.initialize_database()
        
        print(f"[DATABASE] Initialized: {db_path}")
    
    def connect(self):
        """Connect to SQLite database"""
        try:
            self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self.conn.row_factory = sqlite3.Row
            self.cursor = self.conn.cursor()
            return True
        except Exception as e:
            print(f"[DATABASE] Connection error: {e}")
            return False
    
    def initialize_database(self):
        """Create tables if they don't exist - ENHANCED VERSION"""
        try:
            print("[DATABASE] Initializing database tables...")
            
            # Users table
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    status INTEGER DEFAULT 2,
                    avatar TEXT,
                    bio TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_seen TIMESTAMP
                )
            ''')
            
            # Messages table - CHANGED BOOLEAN to INTEGER for SQLite
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sender TEXT NOT NULL,
                    recipient TEXT NOT NULL,
                    message TEXT NOT NULL,
                    is_encrypted INTEGER DEFAULT 0,
                    message_type TEXT DEFAULT 'text',
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # === MESH/TOWER EXTENSION (NON-INVASIVE) ===
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS mesh_towers (
                    tower_id TEXT PRIMARY KEY,
                    name TEXT,
                    owner TEXT,
                    ip TEXT,
                    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS mesh_links (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    link_key TEXT UNIQUE,
                    type TEXT,
                    a TEXT,
                    b TEXT,
                    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS freq_channels (
                    id TEXT PRIMARY KEY,
                    name TEXT,
                    owner TEXT,
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS freq_members (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    freq_id TEXT,
                    username TEXT,
                    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(freq_id, username)
                )
            ''')
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS mesh_emergency (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sender TEXT,
                    message TEXT,
                    tower_id TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Peer keys table
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS peer_keys (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user TEXT NOT NULL,
                    peer TEXT NOT NULL,
                    key_data TEXT NOT NULL,
                    key_id TEXT,
                    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user, peer)
                )
            ''')
            
            # Groups table
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS groups (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    group_id TEXT UNIQUE NOT NULL,
                    name TEXT NOT NULL,
                    description TEXT,
                    creator TEXT NOT NULL,
                    avatar TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Group members table
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS group_members (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    group_id TEXT NOT NULL,
                    username TEXT NOT NULL,
                    role TEXT DEFAULT 'member',
                    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(group_id, username)
                )
            ''')
            
            # Group messages table
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS group_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    group_id TEXT NOT NULL,
                    sender TEXT NOT NULL,
                    message TEXT NOT NULL,
                    is_encrypted INTEGER DEFAULT 0,
                    message_type TEXT DEFAULT 'text',
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Status/Stories table
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS statuses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL,
                    content TEXT NOT NULL,
                    media_type TEXT DEFAULT 'text',
                    media_data TEXT,
                    background_color TEXT DEFAULT '#4CAF50',
                    views TEXT,
                    expires_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Calls history table
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS calls (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    caller TEXT NOT NULL,
                    receiver TEXT NOT NULL,
                    call_type TEXT NOT NULL,
                    call_mode TEXT NOT NULL,
                    status TEXT DEFAULT 'missed',
                    duration INTEGER DEFAULT 0,
                    started_at TIMESTAMP,
                    ended_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            self.conn.commit()
            print("[DATABASE] All tables created")
            
            # Check and fix schema issues
            self.fix_schema()
            
            return True
            
        except Exception as e:
            print(f"[DATABASE] Initialization error: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def fix_schema(self):
        """Fix database schema issues"""
        try:
            print("[DATABASE] Checking schema...")
            
            # Check messages table structure
            self.cursor.execute("PRAGMA table_info(messages)")
            columns = self.cursor.fetchall()
            column_names = [col[1] for col in columns]
            
            print(f"[DATABASE] Current columns in messages: {column_names}")
            
            # If is_encrypted column is missing, add it
            if 'is_encrypted' not in column_names:
                print("[DATABASE] Adding missing is_encrypted column...")
                try:
                    self.cursor.execute('''
                        ALTER TABLE messages 
                        ADD COLUMN is_encrypted INTEGER DEFAULT 0
                    ''')
                    self.conn.commit()
                    print("[DATABASE] Added is_encrypted column")
                except Exception as e:
                    print(f"[DATABASE] Could not add column, will recreate table: {e}")
                    self.recreate_messages_table()

            # client_msg_id: shared delivery id so a message saved by the sender's
            # app and by the receiver's app never ends up stored twice
            if 'client_msg_id' not in column_names:
                print("[DATABASE] Adding client_msg_id column (duplicate protection)...")
                try:
                    self.cursor.execute('''
                        ALTER TABLE messages 
                        ADD COLUMN client_msg_id TEXT
                    ''')
                    self.conn.commit()
                    print("[DATABASE] Added client_msg_id column")
                except Exception as e:
                    print(f"[DATABASE] Could not add client_msg_id column: {e}")
            
            # Check if 'read' column exists (old schema) and remove it
            if 'read' in column_names:
                print("[DATABASE] Removing old 'read' column...")
                self.recreate_messages_table()
            
            # Clean up duplicate rows stored before dedupe existed:
            # keep the earliest copy of each identical message
            try:
                self.cursor.execute('''
                    DELETE FROM messages
                    WHERE id NOT IN (
                        SELECT MIN(id) FROM messages
                        GROUP BY sender, recipient, message, timestamp
                    )
                ''')
                removed = self.cursor.rowcount
                if removed > 0:
                    print(f"[DATABASE] Removed {removed} duplicate message rows")
                self.conn.commit()
            except Exception as e:
                print(f"[DATABASE] Duplicate cleanup skipped: {e}")

            # Create indexes after fixing schema
            # Users table may predate the avatar/bio columns -> add them
            self.cursor.execute("PRAGMA table_info(users)")
            user_cols = [col[1] for col in self.cursor.fetchall()]
            if 'avatar' not in user_cols:
                print("[DATABASE] Adding missing users.avatar column...")
                try:
                    self.cursor.execute("ALTER TABLE users ADD COLUMN avatar TEXT")
                    self.conn.commit()
                    print("[DATABASE] Added users.avatar column")
                except Exception as e:
                    print(f"[DATABASE] Could not add avatar column: {e}")
            if 'bio' not in user_cols:
                print("[DATABASE] Adding missing users.bio column...")
                try:
                    self.cursor.execute("ALTER TABLE users ADD COLUMN bio TEXT")
                    self.conn.commit()
                    print("[DATABASE] Added users.bio column")
                except Exception as e:
                    print(f"[DATABASE] Could not add bio column: {e}")

            self.cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_messages_conversation 
                ON messages(sender, recipient, timestamp)
            ''')
            
            self.cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_users_username 
                ON users(username)
            ''')
            
            self.conn.commit()
            print("[DATABASE] Schema verified and fixed")
            
        except Exception as e:
            print(f"[DATABASE] Error fixing schema: {e}")
            import traceback
            traceback.print_exc()
    
    def recreate_messages_table(self):
        """Completely recreate the messages table with correct schema"""
        try:
            print("[DATABASE] Recreating messages table...")
            
            # Create backup of existing data
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS messages_backup AS 
                SELECT * FROM messages
            ''')
            
            # Drop the old table
            self.cursor.execute("DROP TABLE IF EXISTS messages")
            
            # Create new table with correct schema
            self.cursor.execute('''
                CREATE TABLE messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sender TEXT NOT NULL,
                    recipient TEXT NOT NULL,
                    message TEXT NOT NULL,
                    is_encrypted INTEGER DEFAULT 0,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Try to restore data if backup exists
            try:
                self.cursor.execute("SELECT COUNT(*) FROM messages_backup")
                count = self.cursor.fetchone()[0]
                if count > 0:
                    # Check backup table structure
                    self.cursor.execute("PRAGMA table_info(messages_backup)")
                    backup_cols = [col[1] for col in self.cursor.fetchall()]
                    
                    if 'is_encrypted' in backup_cols:
                        self.cursor.execute('''
                            INSERT INTO messages (id, sender, recipient, message, is_encrypted, timestamp)
                            SELECT id, sender, recipient, message, is_encrypted, timestamp 
                            FROM messages_backup
                        ''')
                    else:
                        self.cursor.execute('''
                            INSERT INTO messages (id, sender, recipient, message, timestamp)
                            SELECT id, sender, recipient, message, timestamp 
                            FROM messages_backup
                        ''')
                    
                    print(f"[DATABASE] Restored {count} messages")
            except Exception as e:
                print(f"[DATABASE] Could not restore messages: {e}")
            
            # Clean up backup
            self.cursor.execute("DROP TABLE IF EXISTS messages_backup")
            
            self.conn.commit()
            print("[DATABASE] Messages table recreated successfully")
            
        except Exception as e:
            print(f"[DATABASE] Error recreating table: {e}")
            self.conn.rollback()
    
    # ========== USER METHODS ==========
    
    def user_exists(self, username):
        """Check if user exists in database"""
        try:
            self.cursor.execute(
                "SELECT 1 FROM users WHERE username = ?", 
                (username,)
            )
            return self.cursor.fetchone() is not None
        except Exception as e:
            print(f"[DATABASE] Error checking user: {e}")
            return False
    
    def add_user(self, username, status=2):
        """Add or update user"""
        try:
            # Check if user exists
            if self.user_exists(username):
                # Update last seen
                self.cursor.execute(
                    "UPDATE users SET last_seen = ?, status = ? WHERE username = ?",
                    (datetime.now(), status, username)
                )
                print(f"[DATABASE] Updated user {username}")
            else:
                # Insert new user
                self.cursor.execute(
                    "INSERT INTO users (username, status, last_seen) VALUES (?, ?, ?)",
                    (username, status, datetime.now())
                )
                print(f"[DATABASE] Added new user {username}")
            
            self.conn.commit()
            return True
        except Exception as e:
            print(f"[DATABASE] Error adding user: {e}")
            return False
    
    # ========== MESSAGE METHODS ==========
    
    def save_message(self, sender, recipient, message, is_encrypted=False, client_msg_id=None):
        """Save message to database. If client_msg_id was already stored, return its existing id."""
        try:
            print(f"[DATABASE] Saving message: {sender} -> {recipient}, encrypted: {is_encrypted}")
            
            # Convert boolean to integer for SQLite
            is_encrypted_int = 1 if is_encrypted else 0

            # Dedupe: the delivery id is saved once, no matter which
            # machine's copy of the packet triggered the save
            if client_msg_id:
                self.cursor.execute(
                    "SELECT id FROM messages WHERE client_msg_id = ?",
                    (client_msg_id,)
                )
                existing = self.cursor.fetchone()
                if existing:
                    print(f"[DATABASE] Duplicate delivery {client_msg_id} skipped (already id {existing['id']})")
                    return existing['id']
            
            self.cursor.execute('''
                INSERT INTO messages (sender, recipient, message, is_encrypted, client_msg_id)
                VALUES (?, ?, ?, ?, ?)
            ''', (sender, recipient, message, is_encrypted_int, client_msg_id))
            
            self.conn.commit()
            message_id = self.cursor.lastrowid
            print(f"[DATABASE] Message saved with ID: {message_id}")
            return message_id
            
        except Exception as e:
            print(f"[DATABASE] Error saving message: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def get_messages(self, user1, user2, limit=100):
        """Get conversation between two users - FIXED VERSION"""
        try:
            print(f"[DATABASE] Getting messages between {user1} and {user2}")
            
            # First verify the table has correct columns
            self.cursor.execute("PRAGMA table_info(messages)")
            columns = self.cursor.fetchall()
            column_names = [col[1] for col in columns]
            
            if 'is_encrypted' not in column_names:
                print("[DATABASE] WARNING: is_encrypted column missing in messages table")
                # Use fallback query without is_encrypted
                self.cursor.execute('''
                    SELECT 
                        id,
                        sender,
                        recipient,
                        message,
                        datetime(timestamp, 'localtime') as timestamp
                    FROM messages 
                    WHERE (sender = ? AND recipient = ?) 
                       OR (sender = ? AND recipient = ?)
                    ORDER BY timestamp ASC
                    LIMIT ?
                ''', (user1, user2, user2, user1, limit))
            else:
                # Normal query with is_encrypted
                self.cursor.execute('''
                    SELECT 
                        id,
                        sender,
                        recipient,
                        message,
                        is_encrypted,
                        datetime(timestamp, 'localtime') as timestamp
                    FROM messages 
                    WHERE (sender = ? AND recipient = ?) 
                       OR (sender = ? AND recipient = ?)
                    ORDER BY timestamp ASC
                    LIMIT ?
                ''', (user1, user2, user2, user1, limit))
            
            rows = self.cursor.fetchall()
            
            # Convert to list of dictionaries
            messages = []
            for row in rows:
                msg_dict = {
                    'id': row['id'],
                    'sender': row['sender'],
                    'recipient': row['recipient'],
                    'message': row['message'],
                    'timestamp': row['timestamp']
                }
                
                # Add is_encrypted if column exists
                if 'is_encrypted' in dict(row).keys():
                    msg_dict['is_encrypted'] = bool(row['is_encrypted'])
                else:
                    msg_dict['is_encrypted'] = False
                
                messages.append(msg_dict)
            
            print(f"[DATABASE] Found {len(messages)} messages")
            return messages
            
        except Exception as e:
            print(f"[DATABASE] Error getting messages: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def get_conversation_previews(self, username):
        """Latest message per conversation partner, for the sidebar list."""
        try:
            self.cursor.execute('''
                SELECT m.sender, m.recipient, m.message,
                       COALESCE(m.is_encrypted, 0) AS is_encrypted,
                       datetime(m.timestamp, 'localtime') AS timestamp
                FROM messages m
                JOIN (
                    SELECT MAX(id) AS last_id,
                           CASE WHEN sender = ? THEN recipient ELSE sender END AS peer
                    FROM messages
                    WHERE sender = ? OR recipient = ?
                    GROUP BY peer
                ) latest ON latest.last_id = m.id
            ''', (username, username, username))

            previews = {}
            for row in self.cursor.fetchall():
                sender = row['sender']
                peer = row['recipient'] if sender == username else sender
                previews[peer] = {
                    'message': row['message'],
                    'sender': sender,
                    'timestamp': row['timestamp'],
                    'is_encrypted': bool(row['is_encrypted'])
                }
            return previews
        except Exception as e:
            print(f"[DATABASE] Error getting conversation previews: {e}")
            return {}

    # ========== KEY MANAGEMENT METHODS ==========
    
    def save_peer_key(self, user, peer, key_data, key_id):
        """Save peer's encryption key"""
        try:
            print(f"[DATABASE] Saving peer key for {user} -> {peer}")
            
            self.cursor.execute('''
                INSERT OR REPLACE INTO peer_keys (user, peer, key_data, key_id)
                VALUES (?, ?, ?, ?)
            ''', (user, peer, key_data, key_id))
            
            self.conn.commit()
            print(f"[DATABASE] Peer key saved for {peer}")
            return True
        except Exception as e:
            print(f"[DATABASE] Error saving peer key: {e}")
            return False
    
    def get_peer_keys(self, user):
        """Get all peer keys for a user"""
        try:
            print(f"[DATABASE] Getting peer keys for {user}")
            
            self.cursor.execute(
                "SELECT peer, key_data, key_id FROM peer_keys WHERE user = ?",
                (user,)
            )
            
            rows = self.cursor.fetchall()
            keys = {}
            for row in rows:
                keys[row['peer']] = {
                    'key': row['key_data'],
                    'key_id': row['key_id']
                }
            
            print(f"[DATABASE] Found {len(keys)} peer keys")
            return keys
        except Exception as e:
            print(f"[DATABASE] Error getting peer keys: {e}")
            return {}
    
    # ========== STATISTICS METHODS ==========
    
    def get_statistics(self, username):
        """Get user statistics"""
        try:
            stats = {}
            
            # Total messages sent
            self.cursor.execute(
                "SELECT COUNT(*) as count FROM messages WHERE sender = ?",
                (username,)
            )
            stats['messages_sent'] = self.cursor.fetchone()['count']
            
            # Total messages received
            self.cursor.execute(
                "SELECT COUNT(*) as count FROM messages WHERE recipient = ?",
                (username,)
            )
            stats['messages_received'] = self.cursor.fetchone()['count']
            
            # Encrypted messages
            self.cursor.execute('''
                SELECT COUNT(*) as count FROM messages 
                WHERE (sender = ? OR recipient = ?) AND is_encrypted = 1
            ''', (username, username))
            stats['encrypted_messages'] = self.cursor.fetchone()['count']
            
            # Peers with keys
            self.cursor.execute(
                "SELECT COUNT(DISTINCT peer) as count FROM peer_keys WHERE user = ?",
                (username,)
            )
            stats['peers_with_keys'] = self.cursor.fetchone()['count']
            
            print(f"[DATABASE] Statistics for {username}: {stats}")
            return stats
            
        except Exception as e:
            print(f"[DATABASE] Error getting statistics: {e}")
            return {}
    
    # ========== GROUP METHODS ==========
    
    def create_group(self, group_id, name, creator, description=""):
        """Create a new group"""
        try:
            self.cursor.execute('''
                INSERT INTO groups (group_id, name, description, creator)
                VALUES (?, ?, ?, ?)
            ''', (group_id, name, description, creator))
            
            # Add creator as admin
            self.cursor.execute('''
                INSERT INTO group_members (group_id, username, role)
                VALUES (?, ?, 'admin')
            ''', (group_id, creator))
            
            self.conn.commit()
            print(f"[DATABASE] Group {name} created by {creator}")
            return True
        except Exception as e:
            print(f"[DATABASE] Error creating group: {e}")
            return False
    
    def add_group_member(self, group_id, username, role='member'):
        """Add member to group"""
        try:
            self.cursor.execute('''
                INSERT OR IGNORE INTO group_members (group_id, username, role)
                VALUES (?, ?, ?)
            ''', (group_id, username, role))
            self.conn.commit()
            return True
        except Exception as e:
            print(f"[DATABASE] Error adding group member: {e}")
            return False
    
    def get_user_groups(self, username):
        """Get all groups for a user"""
        try:
            self.cursor.execute('''
                SELECT g.group_id, g.name, g.description, g.creator, g.created_at
                FROM groups g
                JOIN group_members gm ON g.group_id = gm.group_id
                WHERE gm.username = ?
                ORDER BY g.created_at DESC
            ''', (username,))
            
            rows = self.cursor.fetchall()
            groups = []
            for row in rows:
                # Get member count
                self.cursor.execute(
                    "SELECT COUNT(*) as count FROM group_members WHERE group_id = ?",
                    (row['group_id'],)
                )
                member_count = self.cursor.fetchone()['count']
                
                groups.append({
                    'group_id': row['group_id'],
                    'name': row['name'],
                    'description': row['description'],
                    'creator': row['creator'],
                    'member_count': member_count,
                    'created_at': row['created_at']
                })
            return groups
        except Exception as e:
            print(f"[DATABASE] Error getting user groups: {e}")
            return []
    
    def get_group_members(self, group_id):
        """Get all members of a group"""
        try:
            self.cursor.execute('''
                SELECT username, role, joined_at
                FROM group_members
                WHERE group_id = ?
                ORDER BY role DESC, joined_at ASC
            ''', (group_id,))
            
            rows = self.cursor.fetchall()
            members = []
            for row in rows:
                members.append({
                    'username': row['username'],
                    'role': row['role'],
                    'joined_at': row['joined_at']
                })
            return members
        except Exception as e:
            print(f"[DATABASE] Error getting group members: {e}")
            return []
    
    def save_group_message(self, group_id, sender, message, is_encrypted=False):
        """Save group message"""
        try:
            is_encrypted_int = 1 if is_encrypted else 0
            self.cursor.execute('''
                INSERT INTO group_messages (group_id, sender, message, is_encrypted)
                VALUES (?, ?, ?, ?)
            ''', (group_id, sender, message, is_encrypted_int))
            self.conn.commit()
            return self.cursor.lastrowid
        except Exception as e:
            print(f"[DATABASE] Error saving group message: {e}")
            return None
    
    def get_group_messages(self, group_id, limit=100):
        """Get group messages"""
        try:
            self.cursor.execute('''
                SELECT id, group_id, sender, message, is_encrypted, 
                       datetime(timestamp, 'localtime') as timestamp
                FROM group_messages
                WHERE group_id = ?
                ORDER BY timestamp ASC
                LIMIT ?
            ''', (group_id, limit))
            
            rows = self.cursor.fetchall()
            messages = []
            for row in rows:
                messages.append({
                    'id': row['id'],
                    'group_id': row['group_id'],
                    'sender': row['sender'],
                    'message': row['message'],
                    'is_encrypted': bool(row['is_encrypted']),
                    'timestamp': row['timestamp']
                })
            return messages
        except Exception as e:
            print(f"[DATABASE] Error getting group messages: {e}")
            return []
    
    # ========== STATUS METHODS ==========
    
    def create_status(self, username, content, media_type='text', media_data=None, background_color='#4CAF50'):
        """Create a status post"""
        try:
            from datetime import timedelta
            expires_at = datetime.now() + timedelta(hours=24)
            self.cursor.execute('''
                INSERT INTO statuses (username, content, media_type, media_data, background_color, expires_at)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (username, content, media_type, media_data, background_color, expires_at))
            self.conn.commit()
            return self.cursor.lastrowid
        except Exception as e:
            print(f"[DATABASE] Error creating status: {e}")
            return None
    
    def get_statuses(self):
        """Get all active statuses (not expired)"""
        try:
            from datetime import datetime
            now = datetime.now()
            self.cursor.execute('''
                SELECT id, username, content, media_type, media_data, background_color, 
                       views, datetime(created_at, 'localtime') as created_at
                FROM statuses
                WHERE expires_at > ?
                ORDER BY created_at DESC
            ''', (now,))
            
            rows = self.cursor.fetchall()
            statuses = []
            for row in rows:
                views = json.loads(row['views']) if row['views'] else []
                statuses.append({
                    'id': row['id'],
                    'username': row['username'],
                    'content': row['content'],
                    'media_type': row['media_type'],
                    'media_data': row['media_data'],
                    'background_color': row['background_color'],
                    'views': views,
                    'created_at': row['created_at']
                })
            return statuses
        except Exception as e:
            print(f"[DATABASE] Error getting statuses: {e}")
            return []
    
    def view_status(self, status_id, viewer):
        """Mark status as viewed"""
        try:
            self.cursor.execute("SELECT views FROM statuses WHERE id = ?", (status_id,))
            row = self.cursor.fetchone()
            if not row:
                return False
            views = json.loads(row['views']) if row['views'] else []
            if viewer not in views:
                views.append(viewer)
                self.cursor.execute(
                    "UPDATE statuses SET views = ? WHERE id = ?",
                    (json.dumps(views), status_id)
                )
                self.conn.commit()
            return True
        except Exception as e:
            print(f"[DATABASE] Error viewing status: {e}")
            return False
    
    # ========== USER PROFILE METHODS ==========

    def update_user_avatar(self, username, avatar_path):
        """Update user's avatar image path"""
        try:
            self.cursor.execute(
                "UPDATE users SET avatar = ? WHERE username = ?",
                (avatar_path, username)
            )
            self.conn.commit()
            print(f"[DATABASE] Updated avatar for {username}: {avatar_path}")
            return True
        except Exception as e:
            print(f"[DATABASE] Error updating avatar: {e}")
            return False

    def update_user_profile(self, username, bio=None, status=None):
        """Update user's bio and/or status"""
        try:
            updates = []
            params = []
            if bio is not None:
                updates.append("bio = ?")
                params.append(bio)
            if status is not None:
                updates.append("status = ?")
                params.append(status)
            if not updates:
                return False
            params.append(username)
            query = f"UPDATE users SET {', '.join(updates)} WHERE username = ?"
            self.cursor.execute(query, tuple(params))
            self.conn.commit()
            print(f"[DATABASE] Updated profile for {username}")
            return True
        except Exception as e:
            print(f"[DATABASE] Error updating profile: {e}")
            return False

    def get_user_profile(self, username):
        """Get user profile details"""
        try:
            self.cursor.execute(
                "SELECT username, avatar, bio, status, last_seen, created_at FROM users WHERE username = ?",
                (username,)
            )
            row = self.cursor.fetchone()
            if not row:
                return None
            return {
                'username': row['username'],
                'avatar': row['avatar'],
                'bio': row['bio'],
                'status': row['status'],
                'last_seen': row['last_seen'],
                'created_at': row['created_at']
            }
        except Exception as e:
            print(f"[DATABASE] Error getting user profile: {e}")
            return None

    # ========== CALL METHODS ==========
    
    def save_call(self, caller, receiver, call_type, call_mode, status='missed', duration=0):
        """Save call history"""
        try:
            self.cursor.execute('''
                INSERT INTO calls (caller, receiver, call_type, call_mode, status, duration, started_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (caller, receiver, call_type, call_mode, status, duration, datetime.now()))
            self.conn.commit()
            return self.cursor.lastrowid
        except Exception as e:
            print(f"[DATABASE] Error saving call: {e}")
            return None
    
    def update_call(self, call_id, status, duration=0):
        """Update call status and duration"""
        try:
            self.cursor.execute('''
                UPDATE calls SET status = ?, duration = ?, ended_at = ? WHERE id = ?
            ''', (status, duration, datetime.now(), call_id))
            self.conn.commit()
            return True
        except Exception as e:
            print(f"[DATABASE] Error updating call: {e}")
            return False
    
    def get_call_history(self, username, limit=50):
        """Get call history for user"""
        try:
            self.cursor.execute('''
                SELECT id, caller, receiver, call_type, call_mode, status, duration,
                       datetime(started_at, 'localtime') as started_at,
                       datetime(ended_at, 'localtime') as ended_at
                FROM calls
                WHERE caller = ? OR receiver = ?
                ORDER BY created_at DESC
                LIMIT ?
            ''', (username, username, limit))
            
            rows = self.cursor.fetchall()
            calls = []
            for row in rows:
                calls.append({
                    'id': row['id'],
                    'caller': row['caller'],
                    'receiver': row['receiver'],
                    'call_type': row['call_type'],
                    'call_mode': row['call_mode'],
                    'status': row['status'],
                    'duration': row['duration'],
                    'started_at': row['started_at'],
                    'ended_at': row['ended_at']
                })
            return calls
        except Exception as e:
            print(f"[DATABASE] Error getting call history: {e}")
            return []
    
    # ========== CLEANUP METHOD ==========
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            print("[DATABASE] Connection closed")