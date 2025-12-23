"""Database Models (Dataclasses)

This module defines the data models used throughout the application.
These are simple dataclasses that can be serialized to/from JSON.

Note: The application no longer uses SQLite. These models are kept for
backward compatibility with the API responses.
"""

from enum import Enum
from typing import Optional
from dataclasses import dataclass


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
    
    Note: In file-based storage, a user is simply a folder.
    This class is kept for API compatibility.
    """
    id: int                              # Legacy field (not used in file storage)
    username: str                        # Lowercase alphanumeric username
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
            id=data.get("id", 0),
            username=data["username"],
            created_at=data.get("created_at", 0),
        )


@dataclass
class Download:
    """Download record model
    
    Represents a single video download request and its current state.
    All timestamps are Unix timestamps (seconds since epoch).
    
    Note: This class is kept for backward compatibility.
    The file storage system uses QueueItem instead.
    """
    id: str                              # UUID v4
    url: str                             # Original video URL
    client_id: str                       # Client device identifier
    status: DownloadStatus               # Current download status
    created_at: int                      # Unix timestamp of creation
    last_updated: int                    # Unix timestamp of last update
    user_id: int                         # Legacy field (replaced by username)
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
            user_id=data.get("user_id", 0),
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
    """Session record model for persistent auth sessions
    
    Note: In file-based storage, sessions are stored as individual JSON files.
    """
    id: int                              # Session ID
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
    def from_dict(cls, data: dict) -> "Session":
        """Create Session from dictionary"""
        return cls(
            id=data.get("id", 0),
            token_hash=data["token_hash"],
            ip_address=data.get("ip_address"),
            user_agent=data.get("user_agent"),
            device_info=data.get("device_info"),
            created_at=data["created_at"],
            last_used_at=data.get("last_used_at"),
            expires_at=data.get("expires_at"),
            is_active=data.get("is_active", True),
        )


@dataclass
class AuthLogEntry:
    """Auth activity log entry
    
    Note: In file-based storage, log entries are stored in daily JSON files.
    """
    id: int                              # Entry ID
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
    def from_dict(cls, data: dict) -> "AuthLogEntry":
        """Create AuthLogEntry from dictionary"""
        return cls(
            id=data.get("id", 0),
            timestamp=data["timestamp"],
            event_type=data["event_type"],
            ip_address=data.get("ip_address"),
            user_agent=data.get("user_agent"),
            endpoint=data.get("endpoint"),
            details=data.get("details"),
            session_id=data.get("session_id"),
        )
