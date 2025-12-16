"""Database Models and Schema Definition

This module defines the database schema for the Video Download Server.
Based on PRD Section 4.2 Database Schema.
"""

import sqlite3
from enum import Enum
from typing import Optional
from dataclasses import dataclass
from datetime import datetime


class DownloadStatus(str, Enum):
    """Download status enumeration"""
    PENDING = "pending"  # Initially queued, waiting to be processed
    QUEUED = "queued"  # Same as pending (alias for compatibility)
    DOWNLOADING = "downloading"  # Currently being downloaded
    COMPLETED = "completed"  # Successfully completed
    FAILED = "failed"  # Failed with error


@dataclass
class User:
    """User record model
    
    Represents a user account for organizing downloads.
    Username is stored in lowercase for case-insensitive lookups.
    """
    id: int                              # Auto-increment PRIMARY KEY
    username: str                        # Lowercase alphanumeric username (UNIQUE)
    created_at: int                      # Unix timestamp of creation
    
    def to_dict(self) -> dict:
        """Convert User to dictionary for JSON serialization"""
        return {
            "id": self.id,
            "username": self.username,
            "created_at": self.created_at,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "User":
        """Create User from dictionary"""
        return cls(
            id=data["id"],
            username=data["username"],
            created_at=data["created_at"],
        )


@dataclass
class Download:
    """Download record model
    
    Represents a single video download request and its current state.
    All timestamps are Unix timestamps (seconds since epoch).
    """
    id: str                              # UUID v4
    url: str                             # Original video URL
    client_id: str                       # Client device identifier
    status: DownloadStatus               # Current download status
    created_at: int                      # Unix timestamp of creation
    last_updated: int                    # Unix timestamp of last update
    user_id: int                         # Foreign key to users.id
    genre: str                           # Detected genre (tiktok, instagram, youtube, pdf, ebook, unknown)
    filename: Optional[str] = None       # Downloaded filename (null until completed)
    file_path: Optional[str] = None      # Full path to downloaded file
    file_size: Optional[int] = None      # File size in bytes
    error_message: Optional[str] = None  # Error details if failed
    genre_detection_error: Optional[str] = None  # Error if genre detection fails (preserves data)
    retry_count: int = 0                 # Number of retry attempts
    started_at: Optional[int] = None     # When download started (Unix timestamp)
    completed_at: Optional[int] = None   # When download completed (Unix timestamp)

    def to_dict(self) -> dict:
        """Convert Download to dictionary for JSON serialization"""
        return {
            "id": self.id,
            "url": self.url,
            "client_id": self.client_id,
            "status": self.status.value if isinstance(self.status, DownloadStatus) else self.status,
            "user_id": self.user_id,
            "genre": self.genre,
            "filename": self.filename,
            "file_path": self.file_path,
            "file_size": self.file_size,
            "error_message": self.error_message,
            "genre_detection_error": self.genre_detection_error,
            "retry_count": self.retry_count,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "last_updated": self.last_updated,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Download":
        """Create Download from dictionary"""
        # Convert status string to enum if needed
        status = data["status"]
        if isinstance(status, str):
            status = DownloadStatus(status)
        
        return cls(
            id=data["id"],
            url=data["url"],
            client_id=data["client_id"],
            status=status,
            created_at=data["created_at"],
            last_updated=data["last_updated"],
            user_id=data["user_id"],
            genre=data["genre"],
            filename=data.get("filename"),
            file_path=data.get("file_path"),
            file_size=data.get("file_size"),
            error_message=data.get("error_message"),
            genre_detection_error=data.get("genre_detection_error"),
            retry_count=data.get("retry_count", 0),
            started_at=data.get("started_at"),
            completed_at=data.get("completed_at"),
        )


@dataclass
class Session:
    """Session record model for persistent auth sessions"""
    id: int                              # Auto-increment PRIMARY KEY
    token_hash: str                      # SHA256 hash of the session token
    ip_address: Optional[str]            # Client IP address
    user_agent: Optional[str]            # Browser user agent string
    device_info: Optional[str]           # Parsed device info (browser/OS)
    created_at: int                      # Unix timestamp of creation
    last_used_at: Optional[int]          # Unix timestamp of last activity
    expires_at: Optional[int]            # Unix timestamp of expiry (null = never)
    is_active: bool = True               # Whether session is active
    
    def to_dict(self) -> dict:
        """Convert Session to dictionary for JSON serialization"""
        return {
            "id": self.id,
            "token_hash": self.token_hash,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "device_info": self.device_info,
            "created_at": self.created_at,
            "last_used_at": self.last_used_at,
            "expires_at": self.expires_at,
            "is_active": self.is_active,
        }
    
    @classmethod
    def from_row(cls, row: tuple) -> "Session":
        """Create Session from database row"""
        return cls(
            id=row[0],
            token_hash=row[1],
            ip_address=row[2],
            user_agent=row[3],
            device_info=row[4],
            created_at=row[5],
            last_used_at=row[6],
            expires_at=row[7],
            is_active=bool(row[8]) if row[8] is not None else True,
        )


@dataclass
class AuthLogEntry:
    """Auth activity log entry"""
    id: int                              # Auto-increment PRIMARY KEY
    timestamp: int                       # Unix timestamp
    event_type: str                      # login, logout, login_failed, api_request
    ip_address: Optional[str]            # Client IP address
    user_agent: Optional[str]            # Browser user agent
    endpoint: Optional[str]              # API endpoint (for api_request events)
    details: Optional[str]               # JSON string with extra details
    session_id: Optional[int]            # Reference to session (if applicable)
    
    def to_dict(self) -> dict:
        """Convert AuthLogEntry to dictionary for JSON serialization"""
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "event_type": self.event_type,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "endpoint": self.endpoint,
            "details": self.details,
            "session_id": self.session_id,
        }
    
    @classmethod
    def from_row(cls, row: tuple) -> "AuthLogEntry":
        """Create AuthLogEntry from database row"""
        return cls(
            id=row[0],
            timestamp=row[1],
            event_type=row[2],
            ip_address=row[3],
            user_agent=row[4],
            endpoint=row[5],
            details=row[6],
            session_id=row[7],
        )


# Database Schema SQL
SCHEMA_VERSION = 3

# Users table
CREATE_USERS_TABLE = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE COLLATE NOCASE,
    created_at INTEGER NOT NULL
);
"""

CREATE_USERS_USERNAME_INDEX = """
CREATE INDEX IF NOT EXISTS idx_username ON users(username COLLATE NOCASE);
"""

# Downloads table (v2 with user_id and genre)
CREATE_DOWNLOADS_TABLE = """
CREATE TABLE IF NOT EXISTS downloads (
    id TEXT PRIMARY KEY,
    url TEXT NOT NULL,
    client_id TEXT NOT NULL,
    status TEXT NOT NULL,
    user_id INTEGER NOT NULL,
    genre TEXT NOT NULL,
    filename TEXT,
    file_path TEXT,
    file_size INTEGER,
    error_message TEXT,
    genre_detection_error TEXT,
    retry_count INTEGER DEFAULT 0,
    created_at INTEGER NOT NULL,
    started_at INTEGER,
    completed_at INTEGER,
    last_updated INTEGER NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
"""

CREATE_STATUS_INDEX = """
CREATE INDEX IF NOT EXISTS idx_status ON downloads(status);
"""

CREATE_CREATED_AT_INDEX = """
CREATE INDEX IF NOT EXISTS idx_created_at ON downloads(created_at DESC);
"""

CREATE_CLIENT_ID_INDEX = """
CREATE INDEX IF NOT EXISTS idx_client_id ON downloads(client_id);
"""

CREATE_USER_ID_INDEX = """
CREATE INDEX IF NOT EXISTS idx_user_id ON downloads(user_id);
"""

CREATE_GENRE_INDEX = """
CREATE INDEX IF NOT EXISTS idx_genre ON downloads(genre);
"""

# Schema migrations table for version tracking
CREATE_MIGRATIONS_TABLE = """
CREATE TABLE IF NOT EXISTS schema_migrations (
    version INTEGER PRIMARY KEY,
    applied_at INTEGER NOT NULL,
    description TEXT
);
"""

# Sessions table for persistent auth sessions
CREATE_SESSIONS_TABLE = """
CREATE TABLE IF NOT EXISTS sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    token_hash TEXT UNIQUE NOT NULL,
    ip_address TEXT,
    user_agent TEXT,
    device_info TEXT,
    created_at INTEGER NOT NULL,
    last_used_at INTEGER,
    expires_at INTEGER,
    is_active INTEGER DEFAULT 1
);
"""

CREATE_SESSIONS_TOKEN_INDEX = """
CREATE INDEX IF NOT EXISTS idx_sessions_token ON sessions(token_hash);
"""

CREATE_SESSIONS_ACTIVE_INDEX = """
CREATE INDEX IF NOT EXISTS idx_sessions_active ON sessions(is_active);
"""

# Auth activity log table
CREATE_AUTH_LOG_TABLE = """
CREATE TABLE IF NOT EXISTS auth_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp INTEGER NOT NULL,
    event_type TEXT NOT NULL,
    ip_address TEXT,
    user_agent TEXT,
    endpoint TEXT,
    details TEXT,
    session_id INTEGER,
    FOREIGN KEY (session_id) REFERENCES sessions(id)
);
"""

CREATE_AUTH_LOG_TIMESTAMP_INDEX = """
CREATE INDEX IF NOT EXISTS idx_auth_log_timestamp ON auth_log(timestamp DESC);
"""

CREATE_AUTH_LOG_EVENT_TYPE_INDEX = """
CREATE INDEX IF NOT EXISTS idx_auth_log_event_type ON auth_log(event_type);
"""

# All initialization statements in order (for new databases)
INIT_STATEMENTS = [
    CREATE_USERS_TABLE,
    CREATE_USERS_USERNAME_INDEX,
    CREATE_DOWNLOADS_TABLE,
    CREATE_STATUS_INDEX,
    CREATE_CREATED_AT_INDEX,
    CREATE_CLIENT_ID_INDEX,
    CREATE_USER_ID_INDEX,
    CREATE_GENRE_INDEX,
    CREATE_MIGRATIONS_TABLE,
    CREATE_SESSIONS_TABLE,
    CREATE_SESSIONS_TOKEN_INDEX,
    CREATE_SESSIONS_ACTIVE_INDEX,
    CREATE_AUTH_LOG_TABLE,
    CREATE_AUTH_LOG_TIMESTAMP_INDEX,
    CREATE_AUTH_LOG_EVENT_TYPE_INDEX,
]


def initialize_database(db_path: str) -> None:
    """Initialize database with schema and indexes
    
    Args:
        db_path: Path to SQLite database file
        
    Raises:
        sqlite3.Error: If database initialization fails
    """
    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.cursor()
        
        # Execute all initialization statements
        for statement in INIT_STATEMENTS:
            cursor.execute(statement)
        
        # Record schema version
        cursor.execute(
            "INSERT OR IGNORE INTO schema_migrations (version, applied_at, description) VALUES (?, ?, ?)",
            (SCHEMA_VERSION, int(datetime.now().timestamp()), "Initial schema")
        )
        
        conn.commit()
    finally:
        conn.close()


def get_schema_version(db_path: str) -> int:
    """Get current database schema version
    
    Args:
        db_path: Path to SQLite database file
        
    Returns:
        Current schema version, or 0 if not initialized
    """
    try:
        conn = sqlite3.connect(db_path)
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT MAX(version) FROM schema_migrations")
            result = cursor.fetchone()
            return result[0] if result and result[0] is not None else 0
        finally:
            conn.close()
    except sqlite3.OperationalError:
        # Table doesn't exist yet
        return 0

