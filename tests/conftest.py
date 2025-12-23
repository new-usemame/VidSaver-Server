"""PyTest Configuration and Fixtures

Provides shared fixtures for all tests including file storage setup/teardown.
"""

import pytest
import tempfile
import os
import shutil
from pathlib import Path
import time
import uuid

from app.services.file_storage_service import FileStorageService, QueueItem
from app.models.database import DownloadStatus


@pytest.fixture
def temp_dir():
    """Provide temporary directory for testing
    
    Creates a temporary directory that is automatically cleaned up
    after the test completes.
    """
    # Create temp directory
    path = tempfile.mkdtemp()
    
    yield path
    
    # Cleanup
    try:
        shutil.rmtree(path)
    except OSError:
        pass


@pytest.fixture
def storage_service(temp_dir):
    """Provide FileStorageService instance with temporary directory
    
    Automatically cleans up after test.
    """
    service = FileStorageService(temp_dir)
    
    yield service


@pytest.fixture
def sample_queue_item():
    """Provide sample QueueItem for testing"""
    now = int(time.time())
    return QueueItem(
        id=str(uuid.uuid4()),
        url="https://www.tiktok.com/@user/video/1234567890",
        client_id="test-client-123",
        status=DownloadStatus.PENDING.value,
        username="testuser",
        genre="tiktok",
        created_at=now,
        last_updated=now,
    )


@pytest.fixture
def sample_queue_items():
    """Provide list of sample QueueItem objects for testing"""
    now = int(time.time())
    items = []
    
    for i in range(5):
        status = DownloadStatus.PENDING.value if i < 3 else DownloadStatus.COMPLETED.value
        items.append(QueueItem(
            id=str(uuid.uuid4()),
            url=f"https://www.tiktok.com/@user/video/{1234567890 + i}",
            client_id="test-client-123",
            status=status,
            username="testuser",
            genre="tiktok",
            created_at=now - (i * 100),  # Stagger creation times
            last_updated=now - (i * 100),
            filename=f"video_{i}.mp4" if i >= 3 else None,
            file_size=1024000 + (i * 1000) if i >= 3 else None,
        ))
    
    return items
