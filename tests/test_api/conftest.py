"""Pytest configuration for API tests"""

import pytest
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.services.database_service import DatabaseService
from app.core.config import get_config


@pytest.fixture
def in_memory_db():
    """Create an in-memory database for testing
    
    This fixture provides a fresh database for each test.
    The database is automatically cleaned up after the test.
    """
    # Create database service with in-memory database and auto-init
    db = DatabaseService(db_path=":memory:", auto_init=True)
    
    yield db
    
    # Cleanup
    db.close_connection()

