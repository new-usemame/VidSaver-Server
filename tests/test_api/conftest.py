"""Pytest configuration for API tests"""

import pytest
import sys
import tempfile
import shutil
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.services.file_storage_service import FileStorageService
from app.core.config import get_config, set_config, Config


@pytest.fixture
def temp_storage_dir():
    """Create a temporary storage directory for testing
    
    This fixture provides a fresh storage directory for each test.
    The directory is automatically cleaned up after the test.
    """
    # Create temporary directory
    path = tempfile.mkdtemp()
    
    yield path
    
    # Cleanup
    try:
        shutil.rmtree(path)
    except OSError:
        pass


@pytest.fixture
def file_storage(temp_storage_dir):
    """Create file storage service with temporary directory
    
    This fixture provides a fresh file storage for each test.
    """
    storage = FileStorageService(root_directory=temp_storage_dir)
    
    yield storage
