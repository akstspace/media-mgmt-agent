"""
Database Manager for Media Agent

Handles secure storage of credentials using SQLite with encryption.
Uses Fernet encryption for API keys and passwords.
"""

import os
import sqlite3
from pathlib import Path
from typing import Optional, Dict
from cryptography.fernet import Fernet
import hashlib


class DatabaseManager:
    """Manages encrypted credential storage in SQLite database."""
    
    def __init__(self, db_path: str = "media_agent.db", encryption_key: Optional[str] = None, data_dir: Optional[str] = None):
        """
        Initialize the database manager.
        
        Args:
            db_path: Path to SQLite database file (relative to data_dir if data_dir is provided)
            encryption_key: Encryption key for credentials (auto-generated if not provided)
            data_dir: Directory for persistent data storage (default: current directory)
        """
        # Set up data directory
        self.data_dir = Path(data_dir) if data_dir else Path(".")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Database path relative to data directory
        self.db_path = str(self.data_dir / db_path)
        
        # Generate or load encryption key
        key_file = self.data_dir / ".encryption_key"
        if encryption_key:
            self.fernet_key = encryption_key.encode()
        elif key_file.exists():
            with open(key_file, 'rb') as f:
                self.fernet_key = f.read()
        else:
            # Generate new key
            self.fernet_key = Fernet.generate_key()
            # Save key to file (should be added to .gitignore)
            with open(key_file, 'wb') as f:
                f.write(self.fernet_key)
            print(f"🔐 Generated new encryption key: {key_file}")
        
        self.cipher = Fernet(self.fernet_key)
        self._init_database()
    
    def _init_database(self):
        """Initialize database tables."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Users table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Credentials table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS credentials (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    service_name TEXT NOT NULL,
                    encrypted_url TEXT,
                    encrypted_api_key TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                    UNIQUE(user_id, service_name)
                )
            """)
            
            # Settings table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS settings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    setting_key TEXT NOT NULL,
                    setting_value TEXT,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                    UNIQUE(user_id, setting_key)
                )
            """)
            
            conn.commit()
    
    def _hash_password(self, password: str) -> str:
        """Hash a password using SHA-256."""
        return hashlib.sha256(password.encode()).hexdigest()
    
    def _encrypt(self, data: str) -> str:
        """Encrypt data."""
        if not data:
            return ""
        return self.cipher.encrypt(data.encode()).decode()
    
    def _decrypt(self, encrypted_data: str) -> str:
        """Decrypt data."""
        if not encrypted_data:
            return ""
        return self.cipher.decrypt(encrypted_data.encode()).decode()
    
    # User management
    def create_user(self, username: str, password: str) -> bool:
        """
        Create a new user.
        
        Args:
            username: Username
            password: Password (will be hashed)
            
        Returns:
            True if successful, False if user exists
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                password_hash = self._hash_password(password)
                cursor.execute(
                    "INSERT INTO users (username, password_hash) VALUES (?, ?)",
                    (username, password_hash)
                )
                conn.commit()
                return True
        except sqlite3.IntegrityError:
            return False
    
    def verify_user(self, username: str, password: str) -> Optional[int]:
        """
        Verify user credentials.
        
        Args:
            username: Username
            password: Password
            
        Returns:
            User ID if credentials are valid, None otherwise
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            password_hash = self._hash_password(password)
            cursor.execute(
                "SELECT id FROM users WHERE username = ? AND password_hash = ?",
                (username, password_hash)
            )
            result = cursor.fetchone()
            return result[0] if result else None
    
    def user_exists(self, username: str) -> bool:
        """Check if a user exists."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
            return cursor.fetchone() is not None
    
    def has_any_users(self) -> bool:
        """Check if any users exist in the database."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM users")
            count = cursor.fetchone()[0]
            return count > 0
    
    def change_password(self, username: str, old_password: str, new_password: str) -> bool:
        """
        Change user password.
        
        Args:
            username: Username
            old_password: Current password
            new_password: New password
            
        Returns:
            True if successful, False otherwise
        """
        user_id = self.verify_user(username, old_password)
        if not user_id:
            return False
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            new_hash = self._hash_password(new_password)
            cursor.execute(
                "UPDATE users SET password_hash = ? WHERE id = ?",
                (new_hash, user_id)
            )
            conn.commit()
            return True
    
    # Credentials management
    def save_credentials(
        self,
        user_id: int,
        service_name: str,
        url: Optional[str] = None,
        api_key: Optional[str] = None
    ):
        """
        Save or update service credentials for a user.
        
        Args:
            user_id: User ID
            service_name: Service name (e.g., 'radarr', 'sonarr', 'openrouter')
            url: Service URL (encrypted)
            api_key: API key (encrypted)
        """
        encrypted_url = self._encrypt(url) if url else None
        encrypted_key = self._encrypt(api_key) if api_key else None
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO credentials (user_id, service_name, encrypted_url, encrypted_api_key)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(user_id, service_name) 
                DO UPDATE SET 
                    encrypted_url = excluded.encrypted_url,
                    encrypted_api_key = excluded.encrypted_api_key,
                    updated_at = CURRENT_TIMESTAMP
            """, (user_id, service_name, encrypted_url, encrypted_key))
            conn.commit()
    
    def get_credentials(self, user_id: int, service_name: str) -> Optional[Dict[str, str]]:
        """
        Get decrypted credentials for a service.
        
        Args:
            user_id: User ID
            service_name: Service name
            
        Returns:
            Dictionary with 'url' and 'api_key', or None if not found
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT encrypted_url, encrypted_api_key 
                FROM credentials 
                WHERE user_id = ? AND service_name = ?
            """, (user_id, service_name))
            result = cursor.fetchone()
            
            if not result:
                return None
            
            return {
                'url': self._decrypt(result[0]) if result[0] else None,
                'api_key': self._decrypt(result[1]) if result[1] else None
            }
    
    def get_all_credentials(self, user_id: int) -> Dict[str, Dict[str, str]]:
        """
        Get all credentials for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            Dictionary mapping service names to credential dictionaries
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT service_name, encrypted_url, encrypted_api_key 
                FROM credentials 
                WHERE user_id = ?
            """, (user_id,))
            results = cursor.fetchall()
            
            credentials = {}
            for service_name, enc_url, enc_key in results:
                credentials[service_name] = {
                    'url': self._decrypt(enc_url) if enc_url else None,
                    'api_key': self._decrypt(enc_key) if enc_key else None
                }
            
            return credentials
    
    def delete_credentials(self, user_id: int, service_name: str):
        """Delete credentials for a service."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM credentials WHERE user_id = ? AND service_name = ?",
                (user_id, service_name)
            )
            conn.commit()
    
    # Settings management
    def save_setting(self, user_id: int, key: str, value: str):
        """Save or update a user setting."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO settings (user_id, setting_key, setting_value)
                VALUES (?, ?, ?)
                ON CONFLICT(user_id, setting_key) 
                DO UPDATE SET setting_value = excluded.setting_value
            """, (user_id, key, value))
            conn.commit()
    
    def get_setting(self, user_id: int, key: str) -> Optional[str]:
        """Get a user setting."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT setting_value FROM settings WHERE user_id = ? AND setting_key = ?",
                (user_id, key)
            )
            result = cursor.fetchone()
            return result[0] if result else None
    
    def get_all_settings(self, user_id: int) -> Dict[str, str]:
        """Get all settings for a user."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT setting_key, setting_value FROM settings WHERE user_id = ?",
                (user_id,)
            )
            return dict(cursor.fetchall())
