"""Authentication Service

Handles password hashing, verification, and session management
for universal password authentication with database persistence.
"""

import hashlib
import json
import logging
import secrets
import sqlite3
from datetime import datetime
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


class AuthService:
    """Authentication service for universal password protection
    
    Provides:
    - Password hashing and verification
    - Session token generation and validation with database persistence
    - IP and device tracking
    - Activity logging
    """
    
    def __init__(self, db_path: str, session_timeout_hours: Optional[int] = 24):
        """Initialize auth service
        
        Args:
            db_path: Path to SQLite database file
            session_timeout_hours: How long sessions remain valid (0 or None = never expires)
        """
        self.db_path = db_path
        self.session_timeout_hours = session_timeout_hours
        self._ensure_tables()
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection"""
        return sqlite3.connect(self.db_path)
    
    def _ensure_tables(self):
        """Ensure auth tables exist in database"""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            
            # Create sessions table
            cursor.execute("""
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
                )
            """)
            
            # Create auth_log table
            cursor.execute("""
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
                )
            """)
            
            # Create indexes
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_sessions_token ON sessions(token_hash)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_sessions_active ON sessions(is_active)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_auth_log_timestamp ON auth_log(timestamp DESC)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_auth_log_event_type ON auth_log(event_type)")
            
            conn.commit()
        finally:
            conn.close()
    
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
        
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO sessions (token_hash, ip_address, user_agent, device_info, created_at, last_used_at, expires_at, is_active)
                VALUES (?, ?, ?, ?, ?, ?, ?, 1)
            """, (token_hash, ip_address, user_agent, device_info, now, now, expires_at))
            
            session_id = cursor.lastrowid
            conn.commit()
            
            logger.info(f"Created new session {session_id} for {device_info} from {ip_address}")
            return token, expiry_datetime, session_id
        finally:
            conn.close()
    
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
        
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            
            # Find session
            cursor.execute("""
                SELECT id, expires_at, is_active FROM sessions WHERE token_hash = ?
            """, (token_hash,))
            
            row = cursor.fetchone()
            if not row:
                return False, None
            
            session_id, expires_at, is_active = row
            
            # Check if active
            if not is_active:
                return False, None
            
            # Check expiry (if set)
            if expires_at is not None and now > expires_at:
                # Session expired, mark as inactive
                cursor.execute("UPDATE sessions SET is_active = 0 WHERE id = ?", (session_id,))
                conn.commit()
                logger.info(f"Session {session_id} expired")
                return False, None
            
            # Update last_used_at
            if update_last_used:
                cursor.execute("UPDATE sessions SET last_used_at = ? WHERE id = ?", (now, session_id))
                conn.commit()
            
            return True, session_id
        finally:
            conn.close()
    
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
        
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("UPDATE sessions SET is_active = 0 WHERE token_hash = ?", (token_hash,))
            conn.commit()
            
            if cursor.rowcount > 0:
                logger.info("Session invalidated")
                return True
            return False
        finally:
            conn.close()
    
    def revoke_session_by_id(self, session_id: int) -> bool:
        """Revoke a session by its ID
        
        Args:
            session_id: Session ID to revoke
            
        Returns:
            True if session was found and deactivated
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("UPDATE sessions SET is_active = 0 WHERE id = ?", (session_id,))
            conn.commit()
            
            if cursor.rowcount > 0:
                logger.info(f"Session {session_id} revoked")
                return True
            return False
        finally:
            conn.close()
    
    def revoke_all_sessions(self) -> int:
        """Revoke all active sessions
        
        Returns:
            Number of sessions revoked
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("UPDATE sessions SET is_active = 0 WHERE is_active = 1")
            conn.commit()
            
            count = cursor.rowcount
            logger.info(f"Revoked {count} sessions")
            return count
        finally:
            conn.close()
    
    def get_all_sessions(self) -> List[Dict[str, Any]]:
        """Get all active sessions
        
        Returns:
            List of session dictionaries
        """
        now = int(datetime.now().timestamp())
        
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, token_hash, ip_address, user_agent, device_info, 
                       created_at, last_used_at, expires_at, is_active
                FROM sessions 
                WHERE is_active = 1 AND (expires_at IS NULL OR expires_at > ?)
                ORDER BY last_used_at DESC
            """, (now,))
            
            sessions = []
            for row in cursor.fetchall():
                sessions.append({
                    "id": row[0],
                    "token_hash": row[1][:16] + "...",  # Truncate for display
                    "ip_address": row[2],
                    "user_agent": row[3],
                    "device_info": row[4],
                    "created_at": row[5],
                    "last_used_at": row[6],
                    "expires_at": row[7],
                    "is_active": bool(row[8]),
                })
            
            return sessions
        finally:
            conn.close()
    
    def get_active_session_count(self) -> int:
        """Get count of active (non-expired) sessions
        
        Returns:
            Number of active sessions
        """
        now = int(datetime.now().timestamp())
        
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COUNT(*) FROM sessions 
                WHERE is_active = 1 AND (expires_at IS NULL OR expires_at > ?)
            """, (now,))
            
            return cursor.fetchone()[0]
        finally:
            conn.close()
    
    # Activity logging methods
    
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
        details_json = json.dumps(details) if details else None
        
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO auth_log (timestamp, event_type, ip_address, user_agent, endpoint, details, session_id)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (now, event_type, ip_address, user_agent, endpoint, details_json, session_id))
            conn.commit()
        except Exception as e:
            logger.error(f"Failed to log auth event: {e}")
        finally:
            conn.close()
    
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
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            
            # Build query
            where_clause = ""
            params = []
            if event_type:
                where_clause = "WHERE event_type = ?"
                params.append(event_type)
            
            # Get total count
            cursor.execute(f"SELECT COUNT(*) FROM auth_log {where_clause}", params)
            total = cursor.fetchone()[0]
            
            # Get entries
            cursor.execute(f"""
                SELECT id, timestamp, event_type, ip_address, user_agent, endpoint, details, session_id
                FROM auth_log 
                {where_clause}
                ORDER BY timestamp DESC
                LIMIT ? OFFSET ?
            """, params + [limit, offset])
            
            entries = []
            for row in cursor.fetchall():
                details = None
                if row[6]:
                    try:
                        details = json.loads(row[6])
                    except:
                        details = row[6]
                
                entries.append({
                    "id": row[0],
                    "timestamp": row[1],
                    "event_type": row[2],
                    "ip_address": row[3],
                    "user_agent": row[4],
                    "endpoint": row[5],
                    "details": details,
                    "session_id": row[7],
                })
            
            return entries, total
        finally:
            conn.close()
    
    def clear_activity_log(self) -> int:
        """Clear all activity log entries
        
        Returns:
            Number of entries cleared
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM auth_log")
            count = cursor.fetchone()[0]
            
            cursor.execute("DELETE FROM auth_log")
            conn.commit()
            
            logger.info(f"Cleared {count} activity log entries")
            return count
        finally:
            conn.close()


# Global auth service instance
_auth_service: Optional[AuthService] = None


def get_auth_service(session_timeout_hours: Optional[int] = 24, db_path: Optional[str] = None) -> AuthService:
    """Get global auth service instance
    
    Args:
        session_timeout_hours: Session timeout (only used on first call)
        db_path: Database path (only used on first call)
        
    Returns:
        AuthService instance
    """
    global _auth_service
    
    if _auth_service is None:
        # Get database path from config if not provided
        if db_path is None:
            from app.core.config import get_config
            config = get_config()
            db_path = config.database.path
        
        _auth_service = AuthService(db_path, session_timeout_hours)
    
    return _auth_service


def reset_auth_service():
    """Reset auth service (mainly for testing)"""
    global _auth_service
    _auth_service = None
