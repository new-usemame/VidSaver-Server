"""Tests for Status Endpoint"""

import pytest
from fastapi.testclient import TestClient
import time
import tempfile
import shutil
import uuid

from app.main import app
from app.models.database import DownloadStatus
from app.services.file_storage_service import FileStorageService, QueueItem
from app.core.config import get_config


class TestStatusEndpoint:
    """Test GET /api/v1/status/{download_id} endpoint"""
    
    @pytest.fixture
    def temp_storage_dir(self):
        """Create temporary storage directory"""
        path = tempfile.mkdtemp()
        yield path
        try:
            shutil.rmtree(path)
        except OSError:
            pass
    
    @pytest.fixture
    def storage(self, temp_storage_dir):
        """Create file storage service"""
        return FileStorageService(temp_storage_dir)
    
    @pytest.fixture
    def client(self, temp_storage_dir):
        """Create test client with temp storage"""
        config = get_config()
        original_root = config.downloads.root_directory
        config.downloads.root_directory = temp_storage_dir
        
        client = TestClient(app)
        yield client
        
        config.downloads.root_directory = original_root
    
    def test_get_pending_download_status(self, client, storage):
        """Test getting status of a pending download"""
        now = int(time.time())
        download_id = str(uuid.uuid4())
        
        # Create a queue item
        item = QueueItem(
            id=download_id,
            url="https://www.tiktok.com/@user/video/123",
            status=DownloadStatus.PENDING.value,
            client_id="test-client",
            username="testuser",
            genre="tiktok",
            created_at=now,
            last_updated=now
        )
        storage.create_download(item)
        
        # Get status
        response = client.get(f"/api/v1/status/{download_id}")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["download_id"] == download_id
        assert data["url"] == "https://www.tiktok.com/@user/video/123"
        assert data["status"] == "pending"
        assert "submitted_at" in data
        assert data["started_at"] is None
        assert data["completed_at"] is None
        assert data["file_path"] is None
        assert data["file_size"] is None
        assert data["error_message"] is None
    
    def test_get_downloading_status(self, client, storage):
        """Test getting status of an in-progress download"""
        now = int(time.time())
        download_id = str(uuid.uuid4())
        
        item = QueueItem(
            id=download_id,
            url="https://www.tiktok.com/@user/video/555",
            status=DownloadStatus.DOWNLOADING.value,
            client_id="test-client",
            username="testuser",
            genre="tiktok",
            created_at=now - 20,
            last_updated=now,
            started_at=now - 15
        )
        storage.create_download(item)
        
        response = client.get(f"/api/v1/status/{download_id}")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "downloading"
        assert data["started_at"] is not None
        assert data["completed_at"] is None
    
    def test_get_failed_download_status(self, client, storage):
        """Test getting status of a failed download"""
        now = int(time.time())
        download_id = str(uuid.uuid4())
        
        item = QueueItem(
            id=download_id,
            url="https://www.tiktok.com/@user/video/999",
            status=DownloadStatus.PENDING.value,
            client_id="test-client",
            username="testuser",
            genre="tiktok",
            created_at=now - 50,
            last_updated=now
        )
        storage.create_download(item)
        
        # Move to failed
        storage.move_to_failed(download_id, "testuser", "Network timeout")
        
        response = client.get(f"/api/v1/status/{download_id}")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["download_id"] == download_id
        assert data["status"] == "failed"
        assert data["error_message"] == "Network timeout"
        assert data["file_path"] is None
    
    def test_download_not_found(self, client):
        """Test 404 response for non-existent download"""
        response = client.get("/api/v1/status/550e8400-e29b-41d4-a716-446655440000")
        
        assert response.status_code == 404
        data = response.json()
        
        assert "error" in data["detail"]
        assert data["detail"]["error"] == "not_found"
        assert "request_id" in data["detail"]
    
    def test_invalid_uuid_format(self, client):
        """Test 400 response for invalid UUID format"""
        response = client.get("/api/v1/status/invalid-uuid")
        
        assert response.status_code == 400
        data = response.json()
        
        assert "error" in data["detail"]
        assert data["detail"]["error"] == "invalid_id"
    
    def test_response_includes_request_id(self, client, storage):
        """Test response includes request ID header"""
        now = int(time.time())
        download_id = str(uuid.uuid4())
        
        item = QueueItem(
            id=download_id,
            url="https://www.tiktok.com/@user/video/123",
            status=DownloadStatus.PENDING.value,
            client_id="test-client",
            username="testuser",
            genre="tiktok",
            created_at=now,
            last_updated=now
        )
        storage.create_download(item)
        
        response = client.get(f"/api/v1/status/{download_id}")
        
        assert response.status_code == 200
        assert "X-Request-ID" in response.headers
    
    def test_timestamps_are_iso_format(self, client, storage):
        """Test timestamps are in ISO 8601 format"""
        now = int(time.time())
        download_id = str(uuid.uuid4())
        
        item = QueueItem(
            id=download_id,
            url="https://www.tiktok.com/@user/video/123",
            status=DownloadStatus.PENDING.value,
            client_id="test-client",
            username="testuser",
            genre="tiktok",
            created_at=now,
            last_updated=now,
            started_at=now + 1
        )
        storage.create_download(item)
        
        response = client.get(f"/api/v1/status/{download_id}")
        
        assert response.status_code == 200
        data = response.json()
        
        # Check ISO 8601 format (should contain 'T')
        assert "T" in data["submitted_at"]


class TestStatusEndpointDocumentation:
    """Test API documentation for status endpoint"""
    
    @pytest.fixture
    def client(self):
        """Create test client"""
        return TestClient(app)
    
    def test_openapi_schema_includes_status(self, client):
        """Test OpenAPI schema includes status endpoint"""
        response = client.get("/openapi.json")
        
        assert response.status_code == 200
        schema = response.json()
        
        assert "/api/v1/status/{download_id}" in schema["paths"]
        assert "get" in schema["paths"]["/api/v1/status/{download_id}"]
    
    def test_status_endpoint_in_docs(self, client):
        """Test status endpoint appears in documentation"""
        response = client.get("/docs")
        
        assert response.status_code == 200
        # Docs page should be accessible
        assert b"openapi" in response.content.lower()
