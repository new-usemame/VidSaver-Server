"""Database Service Layer

Provides database connection management, connection pooling, and CRUD operations
for the downloads table. Implements transaction wrappers for data integrity.

Based on PRD Section 4.2 and Implementation Plan Stage 1.
"""

import sqlite3
import threading
from contextlib import contextmanager
from typing import Optional, List, Tuple
from pathlib import Path
import time

from app.models.database import Download, DownloadStatus, User, initialize_database


class DatabaseService:
    """Database service with connection pooling and CRUD operations
    
    Implements thread-safe database operations with connection pooling.
    Each thread gets its own connection to avoid SQLite threading issues.
    """
    
    def __init__(self, db_path: str, auto_init: bool = True):
        """Initialize database service
        
        Args:
            db_path: Path to SQLite database file
            auto_init: If True, initialize database schema if not exists
        """
        self.db_path = db_path
        self._local = threading.local()
        self._lock = threading.Lock()
        
        # Ensure database directory exists
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize database if needed
        if auto_init:
            initialize_database(db_path)
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get thread-local database connection
        
        Returns:
            SQLite connection for current thread
        """
        if not hasattr(self._local, 'connection') or self._local.connection is None:
            self._local.connection = sqlite3.connect(
                self.db_path,
                check_same_thread=False,
                timeout=30.0,  # 30 second timeout for locks
            )
            # Enable foreign keys and WAL mode for better concurrency
            self._local.connection.execute("PRAGMA foreign_keys = ON")
            self._local.connection.execute("PRAGMA journal_mode = WAL")
            # Use Row factory for dict-like access
            self._local.connection.row_factory = sqlite3.Row
        
        return self._local.connection
    
    def close_connection(self):
        """Close thread-local connection"""
        if hasattr(self._local, 'connection') and self._local.connection:
            self._local.connection.close()
            self._local.connection = None
    
    @contextmanager
    def connection_scope(self):
        """Context manager for automatic connection cleanup
        
        Usage:
            with db_service.connection_scope():
                download = db_service.get_download(download_id)
                # ... use download ...
            # Connection automatically closed
        
        Yields:
            Self (DatabaseService instance)
        """
        try:
            yield self
        finally:
            self.close_connection()
    
    @contextmanager
    def transaction(self):
        """Transaction context manager for data integrity
        
        Usage:
            with db_service.transaction():
                db_service.create_download(...)
        
        Yields:
            Database connection
            
        Raises:
            sqlite3.Error: On database errors (transaction will rollback)
        """
        conn = self._get_connection()
        try:
            # Start transaction (explicit BEGIN)
            conn.execute("BEGIN IMMEDIATE")
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            # Ensure connection is in good state after transaction
            try:
                # Rollback any uncommitted changes
                if conn.in_transaction:
                    conn.rollback()
            except Exception as e:
                # Log but don't raise - we're in cleanup
                import logging
                logging.getLogger(__name__).warning(f"Error during transaction cleanup: {e}")
    
    def _row_to_download(self, row: sqlite3.Row) -> Download:
        """Convert database row to Download object
        
        Args:
            row: SQLite Row object
            
        Returns:
            Download object
        """
        # Handle genre_detection_error which might be None in older records
        try:
            genre_detection_error = row["genre_detection_error"]
        except (KeyError, IndexError):
            genre_detection_error = None
        
        return Download(
            id=row["id"],
            url=row["url"],
            client_id=row["client_id"],
            status=DownloadStatus(row["status"]),
            created_at=row["created_at"],
            last_updated=row["last_updated"],
            user_id=row["user_id"],
            genre=row["genre"],
            filename=row["filename"],
            file_path=row["file_path"],
            file_size=row["file_size"],
            error_message=row["error_message"],
            genre_detection_error=genre_detection_error,
            retry_count=row["retry_count"],
            started_at=row["started_at"],
            completed_at=row["completed_at"],
        )
    
    def _row_to_user(self, row: sqlite3.Row) -> User:
        """Convert database row to User object
        
        Args:
            row: SQLite Row object
            
        Returns:
            User object
        """
        return User(
            id=row["id"],
            username=row["username"],
            created_at=row["created_at"],
        )
    
    # ========================================================================
    # USER CRUD Operations
    # ========================================================================
    
    def create_user(self, username: str, auto_commit: bool = True) -> User:
        """Create new user record
        
        Args:
            username: Username (should be lowercase, alphanumeric)
            auto_commit: If True, commit immediately (default). Set False when in transaction.
            
        Returns:
            Created User object
            
        Raises:
            sqlite3.IntegrityError: If username already exists
            sqlite3.Error: On other database errors
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        created_at = int(time.time())
        
        cursor.execute("""
            INSERT INTO users (username, created_at)
            VALUES (?, ?)
        """, (username, created_at))
        
        if auto_commit:
            conn.commit()
        
        # Get the created user
        user_id = cursor.lastrowid
        return User(id=user_id, username=username, created_at=created_at)
    
    def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Get user by ID
        
        Args:
            user_id: User ID
            
        Returns:
            User object if found, None otherwise
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        
        return self._row_to_user(row) if row else None
    
    def get_user_by_username(self, username: str) -> Optional[User]:
        """Get user by username (case-insensitive)
        
        Args:
            username: Username to lookup
            
        Returns:
            User object if found, None otherwise
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Case-insensitive lookup using COLLATE NOCASE
        cursor.execute(
            "SELECT * FROM users WHERE username = ? COLLATE NOCASE",
            (username,)
        )
        row = cursor.fetchone()
        
        return self._row_to_user(row) if row else None
    
    def get_or_create_user(self, username: str) -> User:
        """Get existing user or create new one
        
        Args:
            username: Username (should be lowercase, alphanumeric)
            
        Returns:
            User object (existing or newly created)
            
        Raises:
            sqlite3.Error: On database errors
        """
        # Try to get existing user
        user = self.get_user_by_username(username)
        if user:
            return user
        
        # Create new user
        try:
            return self.create_user(username)
        except sqlite3.IntegrityError:
            # Race condition: another thread created the user
            # Try to get it again
            user = self.get_user_by_username(username)
            if user:
                return user
            raise
    
    def list_users(self, limit: int = 100, offset: int = 0) -> Tuple[List[User], int]:
        """List all users with pagination
        
        Args:
            limit: Maximum number of results
            offset: Pagination offset
            
        Returns:
            Tuple of (list of users, total count)
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Get total count
        cursor.execute("SELECT COUNT(*) FROM users")
        total = cursor.fetchone()[0]
        
        # Get paginated results
        cursor.execute("""
            SELECT * FROM users
            ORDER BY username ASC
            LIMIT ? OFFSET ?
        """, (limit, offset))
        
        rows = cursor.fetchall()
        users = [self._row_to_user(row) for row in rows]
        
        return users, total
    
    def delete_user(self, user_id: int) -> bool:
        """Delete user by ID
        
        Note: This will fail if user has downloads (foreign key constraint)
        
        Args:
            user_id: User ID
            
        Returns:
            True if deleted, False if not found
            
        Raises:
            sqlite3.IntegrityError: If user has downloads
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
        conn.commit()
        
        return cursor.rowcount > 0
    
    # ========================================================================
    # DOWNLOAD CRUD Operations
    # ========================================================================
    
    def create_download(self, download: Download, auto_commit: bool = True) -> Download:
        """Create new download record
        
        Args:
            download: Download object to insert
            auto_commit: If True, commit immediately (default). Set False when in transaction.
            
        Returns:
            Created Download object
            
        Raises:
            sqlite3.IntegrityError: If download with same ID already exists
            sqlite3.Error: On other database errors
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO downloads (
                id, url, client_id, status, user_id, genre,
                filename, file_path, file_size,
                error_message, genre_detection_error, retry_count,
                created_at, started_at, completed_at, last_updated
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            download.id,
            download.url,
            download.client_id,
            download.status.value,
            download.user_id,
            download.genre,
            download.filename,
            download.file_path,
            download.file_size,
            download.error_message,
            download.genre_detection_error,
            download.retry_count,
            download.created_at,
            download.started_at,
            download.completed_at,
            download.last_updated,
        ))
        
        if auto_commit:
            conn.commit()
        return download
    
    def get_download(self, download_id: str) -> Optional[Download]:
        """Get download by ID
        
        Args:
            download_id: UUID of download
            
        Returns:
            Download object if found, None otherwise
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM downloads WHERE id = ?", (download_id,))
        row = cursor.fetchone()
        
        return self._row_to_download(row) if row else None
    
    def update_download(self, download: Download) -> Download:
        """Update existing download record
        
        Args:
            download: Download object with updated values
            
        Returns:
            Updated Download object
            
        Raises:
            sqlite3.Error: On database errors
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Update last_updated timestamp
        download.last_updated = int(time.time())
        
        cursor.execute("""
            UPDATE downloads SET
                url = ?,
                client_id = ?,
                status = ?,
                user_id = ?,
                genre = ?,
                filename = ?,
                file_path = ?,
                file_size = ?,
                error_message = ?,
                genre_detection_error = ?,
                retry_count = ?,
                started_at = ?,
                completed_at = ?,
                last_updated = ?
            WHERE id = ?
        """, (
            download.url,
            download.client_id,
            download.status.value,
            download.user_id,
            download.genre,
            download.filename,
            download.file_path,
            download.file_size,
            download.error_message,
            download.genre_detection_error,
            download.retry_count,
            download.started_at,
            download.completed_at,
            download.last_updated,
            download.id,
        ))
        
        conn.commit()
        return download
    
    def delete_download(self, download_id: str) -> bool:
        """Delete download by ID
        
        Args:
            download_id: UUID of download
            
        Returns:
            True if deleted, False if not found
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM downloads WHERE id = ?", (download_id,))
        conn.commit()
        
        return cursor.rowcount > 0
    
    def update_download_status(
        self,
        download_id: str,
        status: DownloadStatus,
        started_at: Optional[int] = None,
        completed_at: Optional[int] = None,
        filename: Optional[str] = None,
        file_size: Optional[int] = None,
        error_message: Optional[str] = None,
        genre: Optional[str] = None,
        genre_detection_error: Optional[str] = None
    ) -> Optional[Download]:
        """Update download status and related fields
        
        Args:
            download_id: Download ID to update
            status: New status
            started_at: Optional started timestamp
            completed_at: Optional completed timestamp
            filename: Optional filename
            file_size: Optional file size
            error_message: Optional error message
            genre: Optional genre (if detected during download)
            genre_detection_error: Optional genre detection error
            
        Returns:
            Updated Download object or None if not found
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Build update query dynamically based on provided fields
        updates = ["status = ?", "last_updated = ?"]
        params = [status.value, int(time.time())]
        
        if started_at is not None:
            updates.append("started_at = ?")
            params.append(started_at)
        
        if completed_at is not None:
            updates.append("completed_at = ?")
            params.append(completed_at)
        
        if filename is not None:
            updates.append("filename = ?")
            params.append(filename)
        
        if file_size is not None:
            updates.append("file_size = ?")
            params.append(file_size)
        
        if error_message is not None:
            updates.append("error_message = ?")
            params.append(error_message)
        
        if genre is not None:
            updates.append("genre = ?")
            params.append(genre)
        
        if genre_detection_error is not None:
            updates.append("genre_detection_error = ?")
            params.append(genre_detection_error)
        
        params.append(download_id)
        
        query = f"UPDATE downloads SET {', '.join(updates)} WHERE id = ?"
        cursor.execute(query, params)
        conn.commit()
        
        # Return updated download
        return self.get_download(download_id)
    
    def get_downloads_by_status(
        self, 
        status: DownloadStatus,
        limit: Optional[int] = None
    ) -> List[Download]:
        """Get all downloads with specific status
        
        Args:
            status: Status to filter by
            limit: Maximum number of results (optional)
            
        Returns:
            List of Download objects
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        query = "SELECT * FROM downloads WHERE status = ? ORDER BY created_at ASC"
        params = [status.value]
        
        if limit is not None:
            query += " LIMIT ?"
            params.append(limit)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        return [self._row_to_download(row) for row in rows]
    
    def get_downloads_by_client(
        self,
        client_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> Tuple[List[Download], int]:
        """Get downloads for specific client with pagination
        
        Args:
            client_id: Client device identifier
            limit: Maximum number of results
            offset: Pagination offset
            
        Returns:
            Tuple of (list of downloads, total count)
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Get total count
        cursor.execute(
            "SELECT COUNT(*) FROM downloads WHERE client_id = ?",
            (client_id,)
        )
        total = cursor.fetchone()[0]
        
        # Get paginated results
        cursor.execute("""
            SELECT * FROM downloads 
            WHERE client_id = ?
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
        """, (client_id, limit, offset))
        
        rows = cursor.fetchall()
        downloads = [self._row_to_download(row) for row in rows]
        
        return downloads, total
    
    def get_downloads_by_user_id(
        self,
        user_id: int,
        limit: int = 50,
        offset: int = 0
    ) -> Tuple[List[Download], int]:
        """Get downloads for specific user with pagination
        
        Args:
            user_id: User ID
            limit: Maximum number of results
            offset: Pagination offset
            
        Returns:
            Tuple of (list of downloads, total count)
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Get total count
        cursor.execute(
            "SELECT COUNT(*) FROM downloads WHERE user_id = ?",
            (user_id,)
        )
        total = cursor.fetchone()[0]
        
        # Get paginated results
        cursor.execute("""
            SELECT * FROM downloads 
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
        """, (user_id, limit, offset))
        
        rows = cursor.fetchall()
        downloads = [self._row_to_download(row) for row in rows]
        
        return downloads, total
    
    def get_downloads_by_username(
        self,
        username: str,
        limit: int = 50,
        offset: int = 0
    ) -> Tuple[List[Download], int]:
        """Get downloads for specific username with pagination
        
        Args:
            username: Username (case-insensitive)
            limit: Maximum number of results
            offset: Pagination offset
            
        Returns:
            Tuple of (list of downloads, total count)
        """
        # Get user first
        user = self.get_user_by_username(username)
        if not user:
            return [], 0
        
        return self.get_downloads_by_user_id(user.id, limit, offset)
    
    def get_downloads_by_genre(
        self,
        genre: str,
        limit: int = 50,
        offset: int = 0
    ) -> Tuple[List[Download], int]:
        """Get downloads for specific genre with pagination
        
        Args:
            genre: Genre to filter by
            limit: Maximum number of results
            offset: Pagination offset
            
        Returns:
            Tuple of (list of downloads, total count)
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Get total count
        cursor.execute(
            "SELECT COUNT(*) FROM downloads WHERE genre = ?",
            (genre,)
        )
        total = cursor.fetchone()[0]
        
        # Get paginated results
        cursor.execute("""
            SELECT * FROM downloads 
            WHERE genre = ?
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
        """, (genre, limit, offset))
        
        rows = cursor.fetchall()
        downloads = [self._row_to_download(row) for row in rows]
        
        return downloads, total
    
    def get_all_downloads(
        self,
        limit: int = 50,
        offset: int = 0
    ) -> Tuple[List[Download], int]:
        """Get all downloads with pagination
        
        Args:
            limit: Maximum number of results (max 200)
            offset: Pagination offset
            
        Returns:
            Tuple of (list of downloads, total count)
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Get total count
        cursor.execute("SELECT COUNT(*) FROM downloads")
        total = cursor.fetchone()[0]
        
        # Get paginated results
        cursor.execute("""
            SELECT * FROM downloads 
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
        """, (min(limit, 200), offset))
        
        rows = cursor.fetchall()
        downloads = [self._row_to_download(row) for row in rows]
        
        return downloads, total
    
    def increment_retry_count(self, download_id: str) -> Optional[Download]:
        """Increment retry count for a download
        
        Args:
            download_id: UUID of download
            
        Returns:
            Updated Download object, or None if not found
        """
        download = self.get_download(download_id)
        if not download:
            return None
        
        download.retry_count += 1
        download.last_updated = int(time.time())
        
        return self.update_download(download)
    
    def get_queue_size(self) -> int:
        """Get number of downloads in queue (queued status)
        
        Returns:
            Count of queued downloads
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT COUNT(*) FROM downloads WHERE status = ?",
            (DownloadStatus.QUEUED.value,)
        )
        
        return cursor.fetchone()[0]
    
    def reset_stale_downloads(self, max_age_seconds: int = 3600) -> int:
        """Reset stale 'downloading' status to 'queued'
        
        Called on server startup to handle downloads interrupted by crashes.
        
        Args:
            max_age_seconds: Maximum age for downloading status (default 1 hour)
            
        Returns:
            Number of downloads reset
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cutoff_time = int(time.time()) - max_age_seconds
        
        cursor.execute("""
            UPDATE downloads 
            SET status = ?, last_updated = ?
            WHERE status = ? AND last_updated < ?
        """, (
            DownloadStatus.QUEUED.value,
            int(time.time()),
            DownloadStatus.DOWNLOADING.value,
            cutoff_time
        ))
        
        conn.commit()
        return cursor.rowcount

