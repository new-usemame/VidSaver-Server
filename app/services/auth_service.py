"""Authentication Service

Handles password hashing, verification, and session management
for universal password authentication.
"""

import logging
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Tuple

from passlib.context import CryptContext

logger = logging.getLogger(__name__)

# Password hashing context using bcrypt
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthService:
    """Authentication service for universal password protection
    
    Provides:
    - Password hashing and verification
    - Session token generation and validation
    - In-memory session storage (sessions don't persist across restarts)
    """
    
    def __init__(self, session_timeout_hours: int = 24):
        """Initialize auth service
        
        Args:
            session_timeout_hours: How long sessions remain valid (default: 24 hours)
        """
        self.session_timeout_hours = session_timeout_hours
        # In-memory session store: {token: expiry_datetime}
        self._sessions: Dict[str, datetime] = {}
    
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
    
    def create_session(self) -> Tuple[str, datetime]:
        """Create a new session token
        
        Returns:
            Tuple of (session_token, expiry_datetime)
        """
        # Generate cryptographically secure token
        token = secrets.token_urlsafe(32)
        expiry = datetime.now() + timedelta(hours=self.session_timeout_hours)
        
        # Store session
        self._sessions[token] = expiry
        
        # Clean up expired sessions periodically
        self._cleanup_expired_sessions()
        
        logger.info(f"Created new session, expires at {expiry}")
        return token, expiry
    
    def validate_session(self, token: str) -> bool:
        """Validate a session token
        
        Args:
            token: Session token to validate
            
        Returns:
            True if session is valid and not expired, False otherwise
        """
        if not token or token not in self._sessions:
            return False
        
        expiry = self._sessions[token]
        if datetime.now() > expiry:
            # Session expired, remove it
            del self._sessions[token]
            logger.info("Session expired")
            return False
        
        return True
    
    def invalidate_session(self, token: str) -> bool:
        """Invalidate (logout) a session
        
        Args:
            token: Session token to invalidate
            
        Returns:
            True if session was found and removed, False otherwise
        """
        if token in self._sessions:
            del self._sessions[token]
            logger.info("Session invalidated")
            return True
        return False
    
    def _cleanup_expired_sessions(self):
        """Remove expired sessions from memory"""
        now = datetime.now()
        expired = [token for token, expiry in self._sessions.items() if now > expiry]
        for token in expired:
            del self._sessions[token]
        if expired:
            logger.debug(f"Cleaned up {len(expired)} expired sessions")
    
    def get_active_session_count(self) -> int:
        """Get count of active (non-expired) sessions
        
        Returns:
            Number of active sessions
        """
        self._cleanup_expired_sessions()
        return len(self._sessions)


# Global auth service instance
_auth_service: Optional[AuthService] = None


def get_auth_service(session_timeout_hours: int = 24) -> AuthService:
    """Get global auth service instance
    
    Args:
        session_timeout_hours: Session timeout (only used on first call)
        
    Returns:
        AuthService instance
    """
    global _auth_service
    
    if _auth_service is None:
        _auth_service = AuthService(session_timeout_hours)
    
    return _auth_service


def reset_auth_service():
    """Reset auth service (mainly for testing)"""
    global _auth_service
    _auth_service = None
