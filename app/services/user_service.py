"""User Service

Manages user accounts and folder structure for multi-user support.
Handles user validation, auto-creation, and directory management.
"""

import logging
import re
from pathlib import Path
from typing import Optional
from datetime import datetime

from app.models.database import User

logger = logging.getLogger(__name__)


class UserService:
    """Service for managing users and their folder structure
    
    Features:
    - Username validation (alphanumeric only)
    - Case-insensitive username lookups
    - Auto-creation of users on first use
    - Folder structure management
    """
    
    # Username validation pattern: alphanumeric only (letters and numbers)
    USERNAME_PATTERN = re.compile(r'^[a-zA-Z0-9]+$')
    
    def __init__(self, root_directory: str):
        """Initialize user service
        
        Args:
            root_directory: Root directory for all user folders
        """
        self.root_directory = Path(root_directory)
        
        # Ensure root directory exists
        self.root_directory.mkdir(parents=True, exist_ok=True)
        logger.info(f"UserService initialized with root: {self.root_directory}")
    
    @classmethod
    def validate_username(cls, username: str) -> tuple[bool, Optional[str]]:
        """Validate username format
        
        Rules:
        - Must be alphanumeric only (letters and numbers)
        - No special characters, spaces, or punctuation
        - Cannot be empty
        
        Args:
            username: Username to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not username:
            return False, "Username cannot be empty"
        
        if not cls.USERNAME_PATTERN.match(username):
            return False, "Username must be alphanumeric (letters and numbers only)"
        
        return True, None
    
    @classmethod
    def normalize_username(cls, username: str) -> str:
        """Normalize username to lowercase for consistency
        
        Args:
            username: Username to normalize
            
        Returns:
            Normalized username (lowercase)
        """
        return username.lower().strip()
    
    def create_user_directories(self, username: str) -> bool:
        """Create directory structure for a user
        
        Creates:
        - {root}/{username}/
        - {root}/{username}/tiktok/
        - {root}/{username}/instagram/
        - {root}/{username}/youtube/
        - {root}/{username}/pdf/
        - {root}/{username}/ebook/
        - {root}/{username}/unknown/
        
        Args:
            username: Normalized username (lowercase)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Normalize username
            username = self.normalize_username(username)
            
            # Create user root directory
            user_dir = self.root_directory / username
            user_dir.mkdir(parents=True, exist_ok=True)
            
            # Create genre subdirectories
            genres = ['tiktok', 'instagram', 'youtube', 'pdf', 'ebook', 'unknown']
            for genre in genres:
                genre_dir = user_dir / genre
                genre_dir.mkdir(parents=True, exist_ok=True)
            
            logger.info(f"Created directory structure for user: {username}")
            return True
            
        except Exception as e:
            logger.error(f"Error creating directories for user {username}: {e}", exc_info=True)
            return False
    
    def get_user_directory(self, username: str) -> Path:
        """Get root directory path for a user
        
        Args:
            username: Username (will be normalized)
            
        Returns:
            Path to user's root directory
        """
        username = self.normalize_username(username)
        return self.root_directory / username
    
    def get_genre_directory(self, username: str, genre: str) -> Path:
        """Get genre-specific directory path for a user
        
        Args:
            username: Username (will be normalized)
            genre: Genre name (e.g., 'tiktok', 'instagram')
            
        Returns:
            Path to user's genre directory
        """
        username = self.normalize_username(username)
        genre = genre.lower().strip()
        return self.root_directory / username / genre
    
    def ensure_user_directories(self, username: str) -> bool:
        """Ensure user directories exist (create if needed)
        
        Args:
            username: Username (will be normalized)
            
        Returns:
            True if directories exist or were created successfully
        """
        username = self.normalize_username(username)
        user_dir = self.get_user_directory(username)
        
        # If user directory doesn't exist, create full structure
        if not user_dir.exists():
            return self.create_user_directories(username)
        
        # User dir exists, ensure all genre subdirectories exist
        genres = ['tiktok', 'instagram', 'youtube', 'pdf', 'ebook', 'unknown']
        try:
            for genre in genres:
                genre_dir = self.get_genre_directory(username, genre)
                genre_dir.mkdir(parents=True, exist_ok=True)
            return True
        except Exception as e:
            logger.error(f"Error ensuring directories for user {username}: {e}", exc_info=True)
            return False
    
    def user_directory_exists(self, username: str) -> bool:
        """Check if user directory exists
        
        Args:
            username: Username (will be normalized)
            
        Returns:
            True if directory exists, False otherwise
        """
        username = self.normalize_username(username)
        user_dir = self.get_user_directory(username)
        return user_dir.exists()
    
    def list_user_directories(self) -> list[str]:
        """List all user directories in root
        
        Returns:
            List of usernames that have directories
        """
        try:
            if not self.root_directory.exists():
                return []
            
            usernames = []
            for item in self.root_directory.iterdir():
                if item.is_dir():
                    usernames.append(item.name)
            
            return sorted(usernames)
            
        except Exception as e:
            logger.error(f"Error listing user directories: {e}", exc_info=True)
            return []
    
    def get_directory_info(self, username: str) -> dict:
        """Get information about a user's directory structure
        
        Args:
            username: Username (will be normalized)
            
        Returns:
            Dictionary with directory information
        """
        username = self.normalize_username(username)
        user_dir = self.get_user_directory(username)
        
        info = {
            'username': username,
            'user_directory': str(user_dir),
            'exists': user_dir.exists(),
            'genres': {}
        }
        
        if user_dir.exists():
            genres = ['tiktok', 'instagram', 'youtube', 'pdf', 'ebook', 'unknown']
            for genre in genres:
                genre_dir = self.get_genre_directory(username, genre)
                info['genres'][genre] = {
                    'path': str(genre_dir),
                    'exists': genre_dir.exists(),
                }
        
        return info


def create_user_service(root_directory: str) -> UserService:
    """Factory function to create UserService instance
    
    Args:
        root_directory: Root directory for all user folders
        
    Returns:
        UserService instance
    """
    return UserService(root_directory)

