"""File-based Authentication Service

Handles password hashing, verification, and session management
using JSON files instead of a database.

Folder structure:
    /downloads/
      _auth/
        sessions/
          {token_hash}.json     # One file per session
        log/
          2024-12-22.json       # Daily auth logs (append-style)
"""

import hashlib
import json
import logging
import os
import secrets
import threading
from datetime import datetime, date
from pathlib import Path
from typing import Optional, Tuple, List, Dict, Any

from passlib.context import CryptContext

logger = logging.getLogger(__name__)

# Password hashing context using bcrypt
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def parse_user_agent(user_agent: Optional[str]) -> str:
    """Parse user agent string to extract browser and OS info
    
    Args:
        user_agent: Raw user agent string
        
    Returns:
        Human-readable device info string
    """
    if not user_agent:
        return "Unknown Device"
    
    ua = user_agent.lower()
    
    # Detect browser
    browser = "Unknown Browser"
    if "chrome" in ua and "edg" not in ua and "opr" not in ua:
        browser = "Chrome"
    elif "firefox" in ua:
        browser = "Firefox"
    elif "safari" in ua and "chrome" not in ua:
        browser = "Safari"
    elif "edg" in ua:
        browser = "Edge"
    elif "opr" in ua or "opera" in ua:
        browser = "Opera"
    elif "msie" in ua or "trident" in ua:
        browser = "Internet Explorer"
    
    # Detect OS
    os_name = "Unknown OS"
    if "iphone" in ua:
        os_name = "iOS"
    elif "ipad" in ua:
        os_name = "iPadOS"
    elif "android" in ua:
        os_name = "Android"
    elif "mac os" in ua or "macintosh" in ua:
        os_name = "macOS"
    elif "windows" in ua:
        os_name = "Windows"
    elif "linux" in ua:
        os_name = "Linux"
    
    return f"{browser}/{os_name}"


def hash_token(token: str) -> str:
    """Hash a session token using SHA256
    
    Args:
        token: Plain session token
        
    Returns:
        SHA256 hash of the token
    """
    return hashlib.sha256(token.encode()).hexdigest()


class FileAuthService:
    """File-based authentication service
    
    Provides:
    - Password hashing and verification
    - Session token generation and validation with JSON persistence
    - IP and device tracking
    - Activity logging to daily JSON files
    - In-memory session cache for fast validation
    """
    
    AUTH_FOLDER = "_auth"
    SESSIONS_FOLDER = "sessions"
    LOG_FOLDER = "log"
    
    def __init__(self, root_directory: str, session_timeout_hours: Optional[int] = 24):
        """Initialize auth service
        
        Args:
            root_directory: Root directory for downloads (auth folder created here)
            session_timeout_hours: How long sessions remain valid (0 or None = never expires)
        """
        self.root_directory = Path(root_directory)
        self.session_timeout_hours = session_timeout_hours
        self._lock = threading.Lock()
        
        # In-memory cache for validated sessions: token_hash -> (session_data, expiry)
        self._session_cache: Dict[str, Tuple[dict, Optional[int]]] = {}
        self._cache_lock = threading.Lock()
        
        # Auto-incrementing session ID counter
        self._session_id_counter = self._get_next_session_id()
        
        # Ensure directories exist
        self._ensure_directories()
    
    def _ensure_directories(self):
        """Ensure auth directories exist"""
        self.get_sessions_directory().mkdir(parents=True, exist_ok=True)
        self.get_log_directory().mkdir(parents=True, exist_ok=True)
    
    def get_auth_directory(self) -> Path:
        """Get _auth directory path"""
        return self.root_directory / self.AUTH_FOLDER
    
    def get_sessions_directory(self) -> Path:
        """Get sessions directory path"""
        return self.get_auth_directory() / self.SESSIONS_FOLDER
    
    def get_log_directory(self) -> Path:
        """Get log directory path"""
        return self.get_auth_directory() / self.LOG_FOLDER
    
    def _get_session_path(self, token_hash: str) -> Path:
        """Get path to session JSON file"""
        return self.get_sessions_directory() / f"{token_hash}.json"
    
    def _get_log_path(self, log_date: date) -> Path:
        """Get path to daily log JSON file"""
        return self.get_log_directory() / f"{log_date.isoformat()}.json"
    
    def _get_next_session_id(self) -> int:
        """Get next session ID by scanning existing sessions"""
        max_id = 0
        sessions_dir = self.get_sessions_directory()
        
        if sessions_dir.exists():
            for json_file in sessions_dir.glob("*.json"):
                try:
                    with open(json_file, 'r') as f:
                        data = json.load(f)
                        if data.get("id", 0) > max_id:
                            max_id = data["id"]
                except:
                    pass
        
        return max_id + 1
    
    def _write_json(self, path: Path, data: dict) -> bool:
        """Write JSON file atomically"""
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write to temp file first
            temp_path = path.with_suffix('.tmp')
            with open(temp_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            # Atomic rename
            temp_path.replace(path)
            return True
            
        except Exception as e:
            logger.error(f"Error writing JSON to {path}: {e}", exc_info=True)
            return False
    
    def _read_json(self, path: Path) -> Optional[dict]:
        """Read JSON file"""
        try:
            if not path.exists():
                return None
            
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
                
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in {path}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error reading JSON from {path}: {e}", exc_info=True)
            return None
    
    def _delete_json(self, path: Path) -> bool:
        """Delete JSON file"""
        try:
            if path.exists():
                path.unlink()
            return True
        except Exception as e:
            logger.error(f"Error deleting {path}: {e}", exc_info=True)
            return False
    
    # ========================================================================
    # Password Hashing (static methods, same as before)
    # ========================================================================
    
    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password using bcrypt
        
        Args:
            password: Plain text password
            
        Returns:
            Bcrypt hash of the password
        """
        return pwd_context.hash(password)
    
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash
        
        Args:
            plain_password: Plain text password to verify
            hashed_password: Bcrypt hash to verify against
            
        Returns:
            True if password matches, False otherwise
        """
        try:
            return pwd_context.verify(plain_password, hashed_password)
        except Exception as e:
            logger.error(f"Password verification error: {e}")
            return False
    
    # ========================================================================
    # Session Management
    # ========================================================================
    
    def create_session(
        self, 
        ip_address: Optional[str] = None, 
        user_agent: Optional[str] = None
    ) -> Tuple[str, Optional[datetime], int]:
        """Create a new session token
        
        Args:
            ip_address: Client IP address
            user_agent: Client user agent string
            
        Returns:
            Tuple of (session_token, expiry_datetime or None if never expires, session_id)
        """
        # Generate cryptographically secure token
        token = secrets.token_urlsafe(32)
        token_hash = hash_token(token)
        
        now = int(datetime.now().timestamp())
        
        # Calculate expiry (None if timeout is 0 or None)
        expires_at = None
        expiry_datetime = None
        if self.session_timeout_hours and self.session_timeout_hours > 0:
            expires_at = now + (self.session_timeout_hours * 3600)
            expiry_datetime = datetime.fromtimestamp(expires_at)
        
        device_info = parse_user_agent(user_agent)
        
        with self._lock:
            session_id = self._session_id_counter
            self._session_id_counter += 1
            
            session_data = {
                "id": session_id,
                "token_hash": token_hash,
                "ip_address": ip_address,
                "user_agent": user_agent,
                "device_info": device_info,
                "created_at": now,
                "last_used_at": now,
                "expires_at": expires_at,
                "is_active": True,
            }
            
            # Save to file
            session_path = self._get_session_path(token_hash)
            self._write_json(session_path, session_data)
            
            # Add to cache
            with self._cache_lock:
                self._session_cache[token_hash] = (session_data, expires_at)
        
        logger.info(f"Created new session {session_id} for {device_info} from {ip_address}")
        return token, expiry_datetime, session_id
    
    def validate_session(self, token: str, update_last_used: bool = True) -> Tuple[bool, Optional[int]]:
        """Validate a session token
        
        Args:
            token: Session token to validate
            update_last_used: Whether to update last_used_at timestamp
            
        Returns:
            Tuple of (is_valid, session_id or None)
        """
        if not token:
            return False, None
        
        token_hash = hash_token(token)
        now = int(datetime.now().timestamp())
        
        # Check cache first
        with self._cache_lock:
            if token_hash in self._session_cache:
                session_data, expires_at = self._session_cache[token_hash]
                
                # Check if still active
                if not session_data.get("is_active", False):
                    del self._session_cache[token_hash]
                    return False, None
                
                # Check expiry
                if expires_at is not None and now > expires_at:
                    # Mark as inactive
                    session_data["is_active"] = False
                    self._update_session_file(token_hash, session_data)
                    del self._session_cache[token_hash]
                    logger.info(f"Session {session_data.get('id')} expired")
                    return False, None
                
                # Update last_used if requested
                if update_last_used:
                    session_data["last_used_at"] = now
                    # Update file periodically (every 5 minutes) to avoid excessive writes
                    if now - session_data.get("_last_file_update", 0) > 300:
                        session_data["_last_file_update"] = now
                        self._update_session_file(token_hash, session_data)
                
                return True, session_data.get("id")
        
        # Not in cache, check file
        session_path = self._get_session_path(token_hash)
        session_data = self._read_json(session_path)
        
        if not session_data:
            return False, None
        
        # Check if active
        if not session_data.get("is_active", False):
            return False, None
        
        # Check expiry
        expires_at = session_data.get("expires_at")
        if expires_at is not None and now > expires_at:
            # Mark as inactive
            session_data["is_active"] = False
            self._write_json(session_path, session_data)
            logger.info(f"Session {session_data.get('id')} expired")
            return False, None
        
        # Update last_used
        if update_last_used:
            session_data["last_used_at"] = now
            self._write_json(session_path, session_data)
        
        # Add to cache
        with self._cache_lock:
            self._session_cache[token_hash] = (session_data, expires_at)
        
        return True, session_data.get("id")
    
    def _update_session_file(self, token_hash: str, session_data: dict):
        """Update session file (removes internal cache fields)"""
        # Remove internal fields before saving
        data_to_save = {k: v for k, v in session_data.items() if not k.startswith('_')}
        session_path = self._get_session_path(token_hash)
        self._write_json(session_path, data_to_save)
    
    def invalidate_session(self, token: str) -> bool:
        """Invalidate (logout) a session
        
        Args:
            token: Session token to invalidate
            
        Returns:
            True if session was found and deactivated, False otherwise
        """
        if not token:
            return False
        
        token_hash = hash_token(token)
        
        with self._lock:
            # Remove from cache
            with self._cache_lock:
                if token_hash in self._session_cache:
                    del self._session_cache[token_hash]
            
            # Update file
            session_path = self._get_session_path(token_hash)
            session_data = self._read_json(session_path)
            
            if session_data:
                session_data["is_active"] = False
                self._write_json(session_path, session_data)
                logger.info(f"Session {session_data.get('id')} invalidated")
                return True
        
        return False
    
    def revoke_session_by_id(self, session_id: int) -> bool:
        """Revoke a session by its ID
        
        Args:
            session_id: Session ID to revoke
            
        Returns:
            True if session was found and deactivated
        """
        with self._lock:
            sessions_dir = self.get_sessions_directory()
            
            for json_file in sessions_dir.glob("*.json"):
                session_data = self._read_json(json_file)
                if session_data and session_data.get("id") == session_id:
                    session_data["is_active"] = False
                    self._write_json(json_file, session_data)
                    
                    # Remove from cache
                    token_hash = json_file.stem
                    with self._cache_lock:
                        if token_hash in self._session_cache:
                            del self._session_cache[token_hash]
                    
                    logger.info(f"Session {session_id} revoked")
                    return True
        
        return False
    
    def revoke_all_sessions(self) -> int:
        """Revoke all active sessions
        
        Returns:
            Number of sessions revoked
        """
        count = 0
        
        with self._lock:
            # Clear cache
            with self._cache_lock:
                self._session_cache.clear()
            
            sessions_dir = self.get_sessions_directory()
            
            for json_file in sessions_dir.glob("*.json"):
                session_data = self._read_json(json_file)
                if session_data and session_data.get("is_active"):
                    session_data["is_active"] = False
                    self._write_json(json_file, session_data)
                    count += 1
        
        logger.info(f"Revoked {count} sessions")
        return count
    
    def get_all_sessions(self) -> List[Dict[str, Any]]:
        """Get all active sessions
        
        Returns:
            List of session dictionaries
        """
        now = int(datetime.now().timestamp())
        sessions = []
        
        sessions_dir = self.get_sessions_directory()
        if not sessions_dir.exists():
            return sessions
        
        for json_file in sessions_dir.glob("*.json"):
            session_data = self._read_json(json_file)
            if not session_data:
                continue
            
            # Check if active and not expired
            if not session_data.get("is_active"):
                continue
            
            expires_at = session_data.get("expires_at")
            if expires_at is not None and now > expires_at:
                continue
            
            sessions.append({
                "id": session_data.get("id"),
                "token_hash": session_data.get("token_hash", "")[:16] + "...",
                "ip_address": session_data.get("ip_address"),
                "user_agent": session_data.get("user_agent"),
                "device_info": session_data.get("device_info"),
                "created_at": session_data.get("created_at"),
                "last_used_at": session_data.get("last_used_at"),
                "expires_at": session_data.get("expires_at"),
                "is_active": session_data.get("is_active", True),
            })
        
        # Sort by last_used_at descending
        sessions.sort(key=lambda x: x.get("last_used_at", 0), reverse=True)
        
        return sessions
    
    def get_active_session_count(self) -> int:
        """Get count of active (non-expired) sessions
        
        Returns:
            Number of active sessions
        """
        return len(self.get_all_sessions())
    
    # ========================================================================
    # Activity Logging
    # ========================================================================
    
    def log_event(
        self,
        event_type: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        endpoint: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        session_id: Optional[int] = None
    ):
        """Log an authentication event
        
        Args:
            event_type: Type of event (login, logout, login_failed, api_request)
            ip_address: Client IP address
            user_agent: Client user agent
            endpoint: API endpoint (for api_request events)
            details: Additional details as dictionary
            session_id: Associated session ID
        """
        now = int(datetime.now().timestamp())
        today = date.today()
        
        entry = {
            "timestamp": now,
            "event_type": event_type,
            "ip_address": ip_address,
            "user_agent": user_agent,
            "endpoint": endpoint,
            "details": details,
            "session_id": session_id,
        }
        
        with self._lock:
            try:
                log_path = self._get_log_path(today)
                
                # Read existing log or create new
                if log_path.exists():
                    log_data = self._read_json(log_path)
                    if not log_data:
                        log_data = {"date": today.isoformat(), "entries": []}
                else:
                    log_data = {"date": today.isoformat(), "entries": []}
                
                # Add entry with auto-incrementing ID
                entry["id"] = len(log_data["entries"]) + 1
                log_data["entries"].append(entry)
                
                # Write back
                self._write_json(log_path, log_data)
                
            except Exception as e:
                logger.error(f"Failed to log auth event: {e}")
    
    def get_activity_log(
        self, 
        limit: int = 100, 
        offset: int = 0,
        event_type: Optional[str] = None
    ) -> Tuple[List[Dict[str, Any]], int]:
        """Get activity log entries
        
        Args:
            limit: Maximum entries to return
            offset: Pagination offset
            event_type: Filter by event type (optional)
            
        Returns:
            Tuple of (list of log entries, total count)
        """
        all_entries = []
        
        log_dir = self.get_log_directory()
        if not log_dir.exists():
            return [], 0
        
        # Read all log files (sorted by date descending)
        log_files = sorted(log_dir.glob("*.json"), reverse=True)
        
        for log_file in log_files:
            log_data = self._read_json(log_file)
            if not log_data:
                continue
            
            entries = log_data.get("entries", [])
            
            # Filter by event type if specified
            if event_type:
                entries = [e for e in entries if e.get("event_type") == event_type]
            
            all_entries.extend(entries)
        
        # Sort by timestamp descending
        all_entries.sort(key=lambda x: x.get("timestamp", 0), reverse=True)
        
        total = len(all_entries)
        
        # Apply pagination
        paginated = all_entries[offset:offset + limit]
        
        return paginated, total
    
    def clear_activity_log(self) -> int:
        """Clear all activity log entries
        
        Returns:
            Number of entries cleared
        """
        count = 0
        
        with self._lock:
            log_dir = self.get_log_directory()
            if not log_dir.exists():
                return 0
            
            for log_file in log_dir.glob("*.json"):
                log_data = self._read_json(log_file)
                if log_data:
                    count += len(log_data.get("entries", []))
                self._delete_json(log_file)
        
        logger.info(f"Cleared {count} activity log entries")
        return count


# Global auth service instance
_file_auth_service: Optional[FileAuthService] = None
_service_lock = threading.Lock()


def get_file_auth_service(
    root_directory: Optional[str] = None,
    session_timeout_hours: Optional[int] = 24
) -> FileAuthService:
    """Get global file auth service instance
    
    Args:
        root_directory: Root directory (required on first call)
        session_timeout_hours: Session timeout (only used on first call)
        
    Returns:
        FileAuthService instance
    """
    global _file_auth_service
    
    with _service_lock:
        if _file_auth_service is None:
            if root_directory is None:
                # Try to get from config
                from app.core.config import get_config
                config = get_config()
                root_directory = config.downloads.root_directory
            
            _file_auth_service = FileAuthService(root_directory, session_timeout_hours)
        
        return _file_auth_service


def reset_file_auth_service():
    """Reset auth service (mainly for testing)"""
    global _file_auth_service
    _file_auth_service = None
