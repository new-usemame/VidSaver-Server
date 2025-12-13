"""PyTest Configuration and Fixtures

Provides shared fixtures for all tests including database setup/teardown.
"""

import pytest
import tempfile
import os
from pathlib import Path
import time
import uuid

from app.services.database_service import DatabaseService
from app.models.database import Download, DownloadStatus


@pytest.fixture
def temp_db_path():
    """Provide temporary database path for testing
    
    Creates a temporary database file that is automatically cleaned up
    after the test completes.
    """
    # Create temp file
    fd, path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    
    yield path
    
    # Cleanup
    try:
        os.unlink(path)
    except OSError:
        pass


@pytest.fixture
def db_service(temp_db_path):
    """Provide DatabaseService instance with temporary database
    
    Automatically initializes database schema and cleans up after test.
    """
    service = DatabaseService(temp_db_path, auto_init=True)
    
    yield service
    
    # Cleanup connection
    service.close_connection()


@pytest.fixture
def sample_download():
    """Provide sample Download object for testing"""
    now = int(time.time())
    return Download(
        id=str(uuid.uuid4()),
        url="https://www.tiktok.com/@user/video/1234567890",
        client_id="test-client-123",
        status=DownloadStatus.QUEUED,
        created_at=now,
        last_updated=now,
    )


@pytest.fixture
def sample_downloads():
    """Provide list of sample Download objects for testing"""
    now = int(time.time())
    downloads = []
    
    for i in range(5):
        downloads.append(Download(
            id=str(uuid.uuid4()),
            url=f"https://www.tiktok.com/@user/video/{1234567890 + i}",
            client_id="test-client-123",
            status=DownloadStatus.QUEUED if i < 3 else DownloadStatus.COMPLETED,
            created_at=now - (i * 100),  # Stagger creation times
            last_updated=now - (i * 100),
            filename=f"video_{i}.mp4" if i >= 3 else None,
            file_size=1024000 + (i * 1000) if i >= 3 else None,
        ))
    
    return downloads

