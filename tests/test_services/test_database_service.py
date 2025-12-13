"""Unit Tests for Database Service

Comprehensive tests for database operations, connection pooling,
transactions, and CRUD operations.
"""

import pytest
import sqlite3
import time
import uuid
from pathlib import Path

from app.services.database_service import DatabaseService
from app.models.database import (
    Download, 
    DownloadStatus, 
    initialize_database,
    get_schema_version,
)


class TestDatabaseInitialization:
    """Test database initialization and schema creation"""
    
    def test_database_auto_initialization(self, temp_db_path):
        """Test that database is auto-initialized with schema"""
        service = DatabaseService(temp_db_path, auto_init=True)
        
        # Check database file exists
        assert Path(temp_db_path).exists()
        
        # Check schema version
        version = get_schema_version(temp_db_path)
        assert version == 1
        
        service.close_connection()
    
    def test_database_schema_structure(self, temp_db_path):
        """Test that all required tables and indexes are created"""
        initialize_database(temp_db_path)
        
        conn = sqlite3.connect(temp_db_path)
        cursor = conn.cursor()
        
        # Check downloads table exists
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='downloads'"
        )
        assert cursor.fetchone() is not None
        
        # Check all indexes exist
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name='idx_status'"
        )
        assert cursor.fetchone() is not None
        
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name='idx_created_at'"
        )
        assert cursor.fetchone() is not None
        
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name='idx_client_id'"
        )
        assert cursor.fetchone() is not None
        
        # Check schema_migrations table
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='schema_migrations'"
        )
        assert cursor.fetchone() is not None
        
        conn.close()
    
    def test_schema_version_tracking(self, temp_db_path):
        """Test that schema version is tracked correctly"""
        initialize_database(temp_db_path)
        
        version = get_schema_version(temp_db_path)
        assert version == 1
        
        # Test uninitialized database
        temp_db_path2 = str(Path(temp_db_path).parent / "uninitialized.db")
        version = get_schema_version(temp_db_path2)
        assert version == 0


class TestConnectionManagement:
    """Test database connection management and pooling"""
    
    def test_connection_creation(self, db_service):
        """Test that connection is created on first access"""
        conn = db_service._get_connection()
        assert conn is not None
        assert isinstance(conn, sqlite3.Connection)
    
    def test_connection_reuse(self, db_service):
        """Test that same connection is reused within thread"""
        conn1 = db_service._get_connection()
        conn2 = db_service._get_connection()
        assert conn1 is conn2
    
    def test_connection_close(self, db_service):
        """Test that connection can be closed"""
        conn = db_service._get_connection()
        assert conn is not None
        
        db_service.close_connection()
        
        # Getting connection again should create new one
        conn2 = db_service._get_connection()
        assert conn2 is not conn


class TestTransactions:
    """Test transaction management for data integrity"""
    
    def test_transaction_commit(self, db_service, sample_download):
        """Test that transaction commits successfully"""
        with db_service.transaction():
            db_service.create_download(sample_download)
        
        # Verify data was committed
        retrieved = db_service.get_download(sample_download.id)
        assert retrieved is not None
        assert retrieved.id == sample_download.id
    
    def test_transaction_rollback(self, db_service, sample_download):
        """Test that transaction rolls back on error"""
        try:
            with db_service.transaction():
                db_service.create_download(sample_download, auto_commit=False)
                # Force an error
                raise Exception("Test error")
        except Exception:
            pass
        
        # Verify data was not committed
        retrieved = db_service.get_download(sample_download.id)
        assert retrieved is None
    
    def test_transaction_isolation(self, db_service, sample_download):
        """Test that transactions are isolated"""
        # Create download
        db_service.create_download(sample_download)
        
        # Update in transaction
        with db_service.transaction():
            download = db_service.get_download(sample_download.id)
            download.status = DownloadStatus.DOWNLOADING
            db_service.update_download(download)
        
        # Verify update was committed
        retrieved = db_service.get_download(sample_download.id)
        assert retrieved.status == DownloadStatus.DOWNLOADING


class TestCRUDOperations:
    """Test Create, Read, Update, Delete operations"""
    
    def test_create_download(self, db_service, sample_download):
        """Test creating a new download record"""
        created = db_service.create_download(sample_download)
        
        assert created.id == sample_download.id
        assert created.url == sample_download.url
        assert created.status == DownloadStatus.QUEUED
    
    def test_create_duplicate_download(self, db_service, sample_download):
        """Test that creating duplicate ID raises error"""
        db_service.create_download(sample_download)
        
        with pytest.raises(sqlite3.IntegrityError):
            db_service.create_download(sample_download)
    
    def test_get_download(self, db_service, sample_download):
        """Test retrieving a download by ID"""
        db_service.create_download(sample_download)
        
        retrieved = db_service.get_download(sample_download.id)
        
        assert retrieved is not None
        assert retrieved.id == sample_download.id
        assert retrieved.url == sample_download.url
        assert retrieved.client_id == sample_download.client_id
    
    def test_get_nonexistent_download(self, db_service):
        """Test retrieving non-existent download returns None"""
        retrieved = db_service.get_download("nonexistent-id")
        assert retrieved is None
    
    def test_update_download(self, db_service, sample_download):
        """Test updating an existing download"""
        db_service.create_download(sample_download)
        
        # Update status
        sample_download.status = DownloadStatus.COMPLETED
        sample_download.filename = "downloaded_video.mp4"
        sample_download.file_size = 1024000
        
        updated = db_service.update_download(sample_download)
        
        assert updated.status == DownloadStatus.COMPLETED
        assert updated.filename == "downloaded_video.mp4"
        assert updated.file_size == 1024000
        
        # Verify update persisted
        retrieved = db_service.get_download(sample_download.id)
        assert retrieved.status == DownloadStatus.COMPLETED
        assert retrieved.filename == "downloaded_video.mp4"
    
    def test_update_updates_timestamp(self, db_service, sample_download):
        """Test that update automatically updates last_updated timestamp"""
        db_service.create_download(sample_download)
        
        original_timestamp = sample_download.last_updated
        time.sleep(1.1)  # Wait for timestamp to change (1 second resolution)
        
        sample_download.status = DownloadStatus.DOWNLOADING
        updated = db_service.update_download(sample_download)
        
        assert updated.last_updated > original_timestamp
    
    def test_delete_download(self, db_service, sample_download):
        """Test deleting a download"""
        db_service.create_download(sample_download)
        
        deleted = db_service.delete_download(sample_download.id)
        assert deleted is True
        
        # Verify deletion
        retrieved = db_service.get_download(sample_download.id)
        assert retrieved is None
    
    def test_delete_nonexistent_download(self, db_service):
        """Test deleting non-existent download returns False"""
        deleted = db_service.delete_download("nonexistent-id")
        assert deleted is False


class TestQueryOperations:
    """Test query and filter operations"""
    
    def test_get_downloads_by_status(self, db_service, sample_downloads):
        """Test filtering downloads by status"""
        # Create test downloads
        for download in sample_downloads:
            db_service.create_download(download)
        
        # Query queued downloads
        queued = db_service.get_downloads_by_status(DownloadStatus.QUEUED)
        assert len(queued) == 3
        assert all(d.status == DownloadStatus.QUEUED for d in queued)
        
        # Query completed downloads
        completed = db_service.get_downloads_by_status(DownloadStatus.COMPLETED)
        assert len(completed) == 2
        assert all(d.status == DownloadStatus.COMPLETED for d in completed)
    
    def test_get_downloads_by_status_with_limit(self, db_service, sample_downloads):
        """Test limiting results in status query"""
        for download in sample_downloads:
            db_service.create_download(download)
        
        queued = db_service.get_downloads_by_status(DownloadStatus.QUEUED, limit=2)
        assert len(queued) == 2
    
    def test_get_downloads_by_client(self, db_service, sample_downloads):
        """Test filtering downloads by client ID"""
        # Create test downloads
        for download in sample_downloads:
            db_service.create_download(download)
        
        # Add download from different client
        other_download = Download(
            id=str(uuid.uuid4()),
            url="https://www.tiktok.com/@other/video/999",
            client_id="other-client-456",
            status=DownloadStatus.QUEUED,
            created_at=int(time.time()),
            last_updated=int(time.time()),
        )
        db_service.create_download(other_download)
        
        # Query by client
        downloads, total = db_service.get_downloads_by_client("test-client-123")
        
        assert len(downloads) == 5
        assert total == 5
        assert all(d.client_id == "test-client-123" for d in downloads)
    
    def test_get_downloads_by_client_pagination(self, db_service, sample_downloads):
        """Test pagination in client query"""
        for download in sample_downloads:
            db_service.create_download(download)
        
        # First page
        page1, total = db_service.get_downloads_by_client(
            "test-client-123", limit=2, offset=0
        )
        assert len(page1) == 2
        assert total == 5
        
        # Second page
        page2, total = db_service.get_downloads_by_client(
            "test-client-123", limit=2, offset=2
        )
        assert len(page2) == 2
        assert total == 5
        
        # Verify no overlap
        page1_ids = {d.id for d in page1}
        page2_ids = {d.id for d in page2}
        assert page1_ids.isdisjoint(page2_ids)
    
    def test_get_all_downloads(self, db_service, sample_downloads):
        """Test getting all downloads with pagination"""
        for download in sample_downloads:
            db_service.create_download(download)
        
        downloads, total = db_service.get_all_downloads(limit=50, offset=0)
        
        assert len(downloads) == 5
        assert total == 5
    
    def test_get_all_downloads_respects_max_limit(self, db_service):
        """Test that limit is capped at 200"""
        # Create 250 test downloads
        for i in range(250):
            download = Download(
                id=str(uuid.uuid4()),
                url=f"https://test.com/video/{i}",
                client_id="test-client",
                status=DownloadStatus.QUEUED,
                created_at=int(time.time()),
                last_updated=int(time.time()),
            )
            db_service.create_download(download)
        
        # Request 300 but should only get 200
        downloads, total = db_service.get_all_downloads(limit=300, offset=0)
        
        assert len(downloads) == 200
        assert total == 250


class TestHelperMethods:
    """Test helper methods for common operations"""
    
    def test_update_download_status(self, db_service, sample_download):
        """Test convenience method for status updates"""
        db_service.create_download(sample_download)
        
        updated = db_service.update_download_status(
            sample_download.id,
            DownloadStatus.DOWNLOADING
        )
        
        assert updated is not None
        assert updated.status == DownloadStatus.DOWNLOADING
        assert updated.started_at is not None  # Should set started_at
    
    def test_update_download_status_with_error(self, db_service, sample_download):
        """Test status update with error message"""
        db_service.create_download(sample_download)
        
        error_msg = "Download failed: network error"
        updated = db_service.update_download_status(
            sample_download.id,
            DownloadStatus.FAILED,
            error_message=error_msg
        )
        
        assert updated.status == DownloadStatus.FAILED
        assert updated.error_message == error_msg
        assert updated.completed_at is not None
    
    def test_update_download_status_nonexistent(self, db_service):
        """Test updating status of non-existent download"""
        updated = db_service.update_download_status(
            "nonexistent-id",
            DownloadStatus.COMPLETED
        )
        assert updated is None
    
    def test_increment_retry_count(self, db_service, sample_download):
        """Test incrementing retry counter"""
        db_service.create_download(sample_download)
        
        assert sample_download.retry_count == 0
        
        # Increment once
        updated = db_service.increment_retry_count(sample_download.id)
        assert updated.retry_count == 1
        
        # Increment again
        updated = db_service.increment_retry_count(sample_download.id)
        assert updated.retry_count == 2
    
    def test_get_queue_size(self, db_service, sample_downloads):
        """Test getting queue size"""
        for download in sample_downloads:
            db_service.create_download(download)
        
        queue_size = db_service.get_queue_size()
        assert queue_size == 3  # 3 QUEUED downloads in sample_downloads
    
    def test_reset_stale_downloads(self, db_service):
        """Test resetting stale downloading status"""
        now = int(time.time())
        
        # Create old stale download
        stale_download = Download(
            id=str(uuid.uuid4()),
            url="https://test.com/stale",
            client_id="test-client",
            status=DownloadStatus.DOWNLOADING,
            created_at=now - 7200,  # 2 hours ago
            last_updated=now - 7200,
        )
        db_service.create_download(stale_download)
        
        # Create recent downloading (not stale)
        recent_download = Download(
            id=str(uuid.uuid4()),
            url="https://test.com/recent",
            client_id="test-client",
            status=DownloadStatus.DOWNLOADING,
            created_at=now - 60,  # 1 minute ago
            last_updated=now - 60,
        )
        db_service.create_download(recent_download)
        
        # Reset stale downloads (max age 1 hour)
        reset_count = db_service.reset_stale_downloads(max_age_seconds=3600)
        
        assert reset_count == 1
        
        # Verify stale was reset
        stale = db_service.get_download(stale_download.id)
        assert stale.status == DownloadStatus.QUEUED
        
        # Verify recent was not reset
        recent = db_service.get_download(recent_download.id)
        assert recent.status == DownloadStatus.DOWNLOADING


class TestDataIntegrity:
    """Test data integrity and edge cases"""
    
    def test_concurrent_updates(self, db_service, sample_download):
        """Test that updates don't lose data"""
        db_service.create_download(sample_download)
        
        # Simulate concurrent update scenario
        download1 = db_service.get_download(sample_download.id)
        download2 = db_service.get_download(sample_download.id)
        
        # Update both
        download1.retry_count = 1
        download2.error_message = "Test error"
        
        db_service.update_download(download1)
        db_service.update_download(download2)
        
        # Last write wins - verify final state
        final = db_service.get_download(sample_download.id)
        assert final.error_message == "Test error"
        # retry_count will be lost (last write wins)
    
    def test_null_values(self, db_service):
        """Test that null values are handled correctly"""
        download = Download(
            id=str(uuid.uuid4()),
            url="https://test.com/video",
            client_id="test-client",
            status=DownloadStatus.QUEUED,
            created_at=int(time.time()),
            last_updated=int(time.time()),
            filename=None,  # Explicitly null
            file_path=None,
            file_size=None,
            error_message=None,
            started_at=None,
            completed_at=None,
        )
        
        db_service.create_download(download)
        retrieved = db_service.get_download(download.id)
        
        assert retrieved.filename is None
        assert retrieved.file_path is None
        assert retrieved.file_size is None
        assert retrieved.started_at is None
    
    def test_long_strings(self, db_service):
        """Test handling of long strings"""
        long_url = "https://test.com/" + ("x" * 2000)
        long_error = "Error: " + ("x" * 5000)
        
        download = Download(
            id=str(uuid.uuid4()),
            url=long_url,
            client_id="test-client",
            status=DownloadStatus.FAILED,
            created_at=int(time.time()),
            last_updated=int(time.time()),
            error_message=long_error,
        )
        
        db_service.create_download(download)
        retrieved = db_service.get_download(download.id)
        
        assert retrieved.url == long_url
        assert retrieved.error_message == long_error

