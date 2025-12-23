"""File Storage Service

Provides file-based storage for downloads queue using JSON files.
Replaces DatabaseService with a simpler, DB-free approach.

Folder structure:
    /downloads/
      {username}/
        _queue/
          {download_id}.json    # Pending/downloading items
        _failed/
          {download_id}.json    # Failed downloads
        tiktok/
          video.mp4
          video.json            # Metadata sidecar
        instagram/
          ...
"""

import json
import logging
import os
import threading
import time
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field, asdict

from app.models.database import DownloadStatus

logger = logging.getLogger(__name__)


@dataclass
class QueueItem:
    """Queue item model for JSON storage
    
    Represents a download request in the queue.
    Uses username instead of user_id for file-based storage.
    """
    id: str                              # UUID v4
    url: str                             # Original video URL
    client_id: str                       # Client device identifier
    status: str                          # pending, downloading, failed
    username: str                        # Username (folder name)
    genre: str                           # Detected genre
    created_at: int                      # Unix timestamp of creation
    last_updated: int                    # Unix timestamp of last update
    genre_detection_error: Optional[str] = None
    filename: Optional[str] = None       # Downloaded filename
    file_path: Optional[str] = None      # Full path to downloaded file
    file_size: Optional[int] = None      # File size in bytes
    error_message: Optional[str] = None  # Error details if failed
    retry_count: int = 0                 # Number of retry attempts
    started_at: Optional[int] = None     # When download started
    completed_at: Optional[int] = None   # When download completed
    failed_at: Optional[int] = None      # When download failed
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization"""
        return {
            "id": self.id,
            "url": self.url,
            "client_id": self.client_id,
            "status": self.status,
            "username": self.username,
            "genre": self.genre,
            "genre_detection_error": self.genre_detection_error,
            "filename": self.filename,
            "file_path": self.file_path,
            "file_size": self.file_size,
            "error_message": self.error_message,
            "retry_count": self.retry_count,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "failed_at": self.failed_at,
            "last_updated": self.last_updated,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "QueueItem":
        """Create QueueItem from dictionary"""
        return cls(
            id=data["id"],
            url=data["url"],
            client_id=data["client_id"],
            status=data["status"],
            username=data["username"],
            genre=data["genre"],
            genre_detection_error=data.get("genre_detection_error"),
            filename=data.get("filename"),
            file_path=data.get("file_path"),
            file_size=data.get("file_size"),
            error_message=data.get("error_message"),
            retry_count=data.get("retry_count", 0),
            created_at=data["created_at"],
            started_at=data.get("started_at"),
            completed_at=data.get("completed_at"),
            failed_at=data.get("failed_at"),
            last_updated=data["last_updated"],
        )


class FileStorageService:
    """File-based storage service for download queue management
    
    Uses JSON files in per-user _queue/ and _failed/ folders.
    Thread-safe with file locking.
    """
    
    # Special folder names (prefixed with _ to distinguish from genres)
    QUEUE_FOLDER = "_queue"
    FAILED_FOLDER = "_failed"
    AUTH_FOLDER = "_auth"
    
    # Standard genre folders
    GENRES = ['tiktok', 'instagram', 'youtube', 'pdf', 'ebook', 'unknown']
    
    def __init__(self, root_directory: str):
        """Initialize file storage service
        
        Args:
            root_directory: Root directory for all downloads
        """
        self.root_directory = Path(root_directory)
        self._lock = threading.Lock()
        
        # Ensure root directory exists
        self.root_directory.mkdir(parents=True, exist_ok=True)
        logger.info(f"FileStorageService initialized with root: {self.root_directory}")
    
    # ========================================================================
    # User/Folder Management
    # ========================================================================
    
    def get_user_directory(self, username: str) -> Path:
        """Get user's root directory path"""
        return self.root_directory / username.lower()
    
    def get_queue_directory(self, username: str) -> Path:
        """Get user's queue directory path"""
        return self.get_user_directory(username) / self.QUEUE_FOLDER
    
    def get_failed_directory(self, username: str) -> Path:
        """Get user's failed directory path"""
        return self.get_user_directory(username) / self.FAILED_FOLDER
    
    def get_genre_directory(self, username: str, genre: str) -> Path:
        """Get user's genre directory path"""
        return self.get_user_directory(username) / genre.lower()
    
    def ensure_user_directories(self, username: str) -> bool:
        """Ensure all user directories exist
        
        Creates:
        - {root}/{username}/
        - {root}/{username}/_queue/
        - {root}/{username}/_failed/
        - {root}/{username}/{genre}/ for each genre
        
        Args:
            username: Username (will be lowercased)
            
        Returns:
            True if successful
        """
        username = username.lower()
        
        try:
            # Create user root
            user_dir = self.get_user_directory(username)
            user_dir.mkdir(parents=True, exist_ok=True)
            
            # Create queue and failed folders
            self.get_queue_directory(username).mkdir(parents=True, exist_ok=True)
            self.get_failed_directory(username).mkdir(parents=True, exist_ok=True)
            
            # Create genre folders
            for genre in self.GENRES:
                self.get_genre_directory(username, genre).mkdir(parents=True, exist_ok=True)
            
            logger.debug(f"Ensured directories for user: {username}")
            return True
            
        except Exception as e:
            logger.error(f"Error creating directories for {username}: {e}", exc_info=True)
            return False
    
    def user_exists(self, username: str) -> bool:
        """Check if user folder exists"""
        return self.get_user_directory(username).exists()
    
    def get_or_create_user(self, username: str) -> str:
        """Get existing user or create folder structure
        
        Args:
            username: Username
            
        Returns:
            Normalized username (lowercase)
        """
        username = username.lower()
        self.ensure_user_directories(username)
        return username
    
    def list_users(self) -> List[str]:
        """List all users (folders in root directory)
        
        Returns:
            List of usernames
        """
        users = []
        try:
            for item in self.root_directory.iterdir():
                if item.is_dir() and not item.name.startswith('_'):
                    users.append(item.name)
        except Exception as e:
            logger.error(f"Error listing users: {e}", exc_info=True)
        return sorted(users)
    
    # ========================================================================
    # Queue JSON Operations
    # ========================================================================
    
    def _get_queue_path(self, username: str, download_id: str) -> Path:
        """Get path to queue JSON file"""
        return self.get_queue_directory(username) / f"{download_id}.json"
    
    def _get_failed_path(self, username: str, download_id: str) -> Path:
        """Get path to failed JSON file"""
        return self.get_failed_directory(username) / f"{download_id}.json"
    
    def _write_json(self, path: Path, data: dict) -> bool:
        """Write JSON file atomically
        
        Uses write-to-temp-then-rename for atomic updates.
        """
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
    # Download CRUD Operations
    # ========================================================================
    
    def create_download(self, item: QueueItem) -> QueueItem:
        """Create new download in queue
        
        Args:
            item: QueueItem to save
            
        Returns:
            Saved QueueItem
        """
        with self._lock:
            # Ensure user directories exist
            self.ensure_user_directories(item.username)
            
            # Write to queue folder
            path = self._get_queue_path(item.username, item.id)
            self._write_json(path, item.to_dict())
            
            logger.info(f"Created download {item.id} in queue for user {item.username}")
            return item
    
    def get_download(self, download_id: str, username: Optional[str] = None) -> Optional[QueueItem]:
        """Get download by ID
        
        Args:
            download_id: Download UUID
            username: Optional username to narrow search
            
        Returns:
            QueueItem if found, None otherwise
        """
        # If username provided, search only that user's folders
        if username:
            return self._search_user_download(username, download_id)
        
        # Otherwise search all users
        for user in self.list_users():
            item = self._search_user_download(user, download_id)
            if item:
                return item
        
        return None
    
    def _search_user_download(self, username: str, download_id: str) -> Optional[QueueItem]:
        """Search for download in user's queue and failed folders"""
        # Check queue folder
        queue_path = self._get_queue_path(username, download_id)
        if queue_path.exists():
            data = self._read_json(queue_path)
            if data:
                return QueueItem.from_dict(data)
        
        # Check failed folder
        failed_path = self._get_failed_path(username, download_id)
        if failed_path.exists():
            data = self._read_json(failed_path)
            if data:
                return QueueItem.from_dict(data)
        
        return None
    
    def update_download(self, item: QueueItem) -> QueueItem:
        """Update existing download
        
        Args:
            item: QueueItem with updated values
            
        Returns:
            Updated QueueItem
        """
        with self._lock:
            item.last_updated = int(time.time())
            
            # Determine which folder it's in
            queue_path = self._get_queue_path(item.username, item.id)
            failed_path = self._get_failed_path(item.username, item.id)
            
            if queue_path.exists():
                self._write_json(queue_path, item.to_dict())
            elif failed_path.exists():
                self._write_json(failed_path, item.to_dict())
            else:
                # Item doesn't exist, create in queue
                self._write_json(queue_path, item.to_dict())
            
            return item
    
    def update_download_status(
        self,
        download_id: str,
        username: str,
        status: str,
        started_at: Optional[int] = None,
        completed_at: Optional[int] = None,
        filename: Optional[str] = None,
        file_path: Optional[str] = None,
        file_size: Optional[int] = None,
        error_message: Optional[str] = None,
        genre: Optional[str] = None,
        genre_detection_error: Optional[str] = None
    ) -> Optional[QueueItem]:
        """Update download status and related fields
        
        Args:
            download_id: Download ID
            username: Username
            status: New status
            Other args: Optional field updates
            
        Returns:
            Updated QueueItem or None if not found
        """
        item = self.get_download(download_id, username)
        if not item:
            return None
        
        with self._lock:
            # Update fields
            item.status = status
            item.last_updated = int(time.time())
            
            if started_at is not None:
                item.started_at = started_at
            if completed_at is not None:
                item.completed_at = completed_at
            if filename is not None:
                item.filename = filename
            if file_path is not None:
                item.file_path = file_path
            if file_size is not None:
                item.file_size = file_size
            if error_message is not None:
                item.error_message = error_message
            if genre is not None:
                item.genre = genre
            if genre_detection_error is not None:
                item.genre_detection_error = genre_detection_error
            
            # Write back to file
            queue_path = self._get_queue_path(item.username, item.id)
            failed_path = self._get_failed_path(item.username, item.id)
            
            if queue_path.exists():
                self._write_json(queue_path, item.to_dict())
            elif failed_path.exists():
                self._write_json(failed_path, item.to_dict())
            
            return item
    
    def delete_download(self, download_id: str, username: str) -> bool:
        """Delete download from queue or failed folder
        
        Args:
            download_id: Download ID
            username: Username
            
        Returns:
            True if deleted
        """
        with self._lock:
            queue_path = self._get_queue_path(username, download_id)
            failed_path = self._get_failed_path(username, download_id)
            
            deleted = False
            if queue_path.exists():
                deleted = self._delete_json(queue_path)
            if failed_path.exists():
                deleted = self._delete_json(failed_path) or deleted
            
            return deleted
    
    def move_to_failed(self, download_id: str, username: str, error_message: str) -> Optional[QueueItem]:
        """Move download from queue to failed folder
        
        Args:
            download_id: Download ID
            username: Username
            error_message: Error message to record
            
        Returns:
            Updated QueueItem or None
        """
        with self._lock:
            queue_path = self._get_queue_path(username, download_id)
            
            if not queue_path.exists():
                logger.warning(f"Download {download_id} not found in queue for {username}")
                return None
            
            # Read current data
            data = self._read_json(queue_path)
            if not data:
                return None
            
            item = QueueItem.from_dict(data)
            
            # Update status
            item.status = DownloadStatus.FAILED.value
            item.error_message = error_message
            item.failed_at = int(time.time())
            item.last_updated = int(time.time())
            
            # Ensure failed directory exists
            self.get_failed_directory(username).mkdir(parents=True, exist_ok=True)
            
            # Write to failed folder
            failed_path = self._get_failed_path(username, download_id)
            self._write_json(failed_path, item.to_dict())
            
            # Delete from queue
            self._delete_json(queue_path)
            
            logger.info(f"Moved download {download_id} to failed folder for {username}")
            return item
    
    def complete_download(self, download_id: str, username: str) -> bool:
        """Remove download from queue after completion
        
        Note: Metadata should be saved separately via metadata_service
        
        Args:
            download_id: Download ID
            username: Username
            
        Returns:
            True if removed
        """
        with self._lock:
            queue_path = self._get_queue_path(username, download_id)
            return self._delete_json(queue_path)
    
    # ========================================================================
    # Queue Queries
    # ========================================================================
    
    def get_pending_downloads(self, limit: Optional[int] = None) -> List[QueueItem]:
        """Get all pending downloads across all users
        
        Scans all user _queue/ folders for pending items.
        
        Args:
            limit: Maximum number of results
            
        Returns:
            List of pending QueueItems, sorted by created_at
        """
        items = []
        
        for username in self.list_users():
            queue_dir = self.get_queue_directory(username)
            if not queue_dir.exists():
                continue
            
            for json_file in queue_dir.glob("*.json"):
                data = self._read_json(json_file)
                if data and data.get("status") in [
                    DownloadStatus.PENDING.value,
                    DownloadStatus.QUEUED.value
                ]:
                    items.append(QueueItem.from_dict(data))
        
        # Sort by created_at (oldest first)
        items.sort(key=lambda x: x.created_at)
        
        if limit:
            items = items[:limit]
        
        return items
    
    def get_downloading(self, limit: Optional[int] = None) -> List[QueueItem]:
        """Get all currently downloading items
        
        Args:
            limit: Maximum number of results
            
        Returns:
            List of downloading QueueItems
        """
        items = []
        
        for username in self.list_users():
            queue_dir = self.get_queue_directory(username)
            if not queue_dir.exists():
                continue
            
            for json_file in queue_dir.glob("*.json"):
                data = self._read_json(json_file)
                if data and data.get("status") == DownloadStatus.DOWNLOADING.value:
                    items.append(QueueItem.from_dict(data))
        
        items.sort(key=lambda x: x.started_at or x.created_at)
        
        if limit:
            items = items[:limit]
        
        return items
    
    def get_failed_downloads(self, username: Optional[str] = None, limit: Optional[int] = None) -> List[QueueItem]:
        """Get failed downloads
        
        Args:
            username: Optional username to filter by
            limit: Maximum number of results
            
        Returns:
            List of failed QueueItems
        """
        items = []
        
        users = [username] if username else self.list_users()
        
        for user in users:
            failed_dir = self.get_failed_directory(user)
            if not failed_dir.exists():
                continue
            
            for json_file in failed_dir.glob("*.json"):
                data = self._read_json(json_file)
                if data:
                    items.append(QueueItem.from_dict(data))
        
        # Sort by failed_at or last_updated (newest first)
        items.sort(key=lambda x: x.failed_at or x.last_updated, reverse=True)
        
        if limit:
            items = items[:limit]
        
        return items
    
    def get_downloads_by_status(self, status: str, limit: Optional[int] = None) -> List[QueueItem]:
        """Get downloads by status
        
        Args:
            status: Status to filter by
            limit: Maximum number of results
            
        Returns:
            List of QueueItems
        """
        if status == DownloadStatus.FAILED.value:
            return self.get_failed_downloads(limit=limit)
        elif status == DownloadStatus.DOWNLOADING.value:
            return self.get_downloading(limit=limit)
        elif status in [DownloadStatus.PENDING.value, DownloadStatus.QUEUED.value]:
            return self.get_pending_downloads(limit=limit)
        
        # For other statuses, scan all queue files
        items = []
        for username in self.list_users():
            queue_dir = self.get_queue_directory(username)
            if not queue_dir.exists():
                continue
            
            for json_file in queue_dir.glob("*.json"):
                data = self._read_json(json_file)
                if data and data.get("status") == status:
                    items.append(QueueItem.from_dict(data))
        
        items.sort(key=lambda x: x.created_at)
        
        if limit:
            items = items[:limit]
        
        return items
    
    def get_queue_counts(self) -> Dict[str, int]:
        """Get counts of items by status
        
        Returns:
            Dictionary with status counts
        """
        pending = len(self.get_pending_downloads())
        downloading = len(self.get_downloading())
        failed = len(self.get_failed_downloads())
        
        return {
            "pending": pending,
            "downloading": downloading,
            "failed": failed,
            "total": pending + downloading + failed
        }
    
    def reset_stale_downloads(self, max_age_seconds: int = 3600) -> int:
        """Reset stale 'downloading' status to 'pending'
        
        Called on server startup to handle downloads interrupted by crashes.
        
        Args:
            max_age_seconds: Maximum age for downloading status
            
        Returns:
            Number of downloads reset
        """
        count = 0
        cutoff_time = int(time.time()) - max_age_seconds
        
        with self._lock:
            for username in self.list_users():
                queue_dir = self.get_queue_directory(username)
                if not queue_dir.exists():
                    continue
                
                for json_file in queue_dir.glob("*.json"):
                    data = self._read_json(json_file)
                    if not data:
                        continue
                    
                    if (data.get("status") == DownloadStatus.DOWNLOADING.value and 
                        data.get("last_updated", 0) < cutoff_time):
                        data["status"] = DownloadStatus.PENDING.value
                        data["last_updated"] = int(time.time())
                        self._write_json(json_file, data)
                        count += 1
                        logger.info(f"Reset stale download: {data.get('id')}")
        
        return count
    
    def increment_retry_count(self, download_id: str, username: str) -> Optional[QueueItem]:
        """Increment retry count for a download
        
        Args:
            download_id: Download ID
            username: Username
            
        Returns:
            Updated QueueItem or None
        """
        item = self.get_download(download_id, username)
        if not item:
            return None
        
        item.retry_count += 1
        item.last_updated = int(time.time())
        
        return self.update_download(item)


# Global instance (lazy initialization)
_file_storage_service: Optional[FileStorageService] = None
_service_lock = threading.Lock()


def get_file_storage_service(root_directory: Optional[str] = None) -> FileStorageService:
    """Get or create global FileStorageService instance
    
    Args:
        root_directory: Root directory (required on first call)
        
    Returns:
        FileStorageService instance
    """
    global _file_storage_service
    
    with _service_lock:
        if _file_storage_service is None:
            if root_directory is None:
                raise ValueError("root_directory required for first initialization")
            _file_storage_service = FileStorageService(root_directory)
        
        return _file_storage_service
