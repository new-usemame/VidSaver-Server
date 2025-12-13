"""Tests for Status Endpoint"""

import pytest
from fastapi.testclient import TestClient
import time

from app.main import app
from app.models.database import Download, DownloadStatus


class TestStatusEndpoint:
    """Test GET /api/v1/status/{download_id} endpoint"""
    
    @pytest.fixture
    def client(self):
        """Create test client"""
        return TestClient(app)
    
    def test_get_pending_download_status(self, client, in_memory_db):
        """Test getting status of a pending download"""
        # Create a download
        now = int(time.time())
        download = Download(
            id="test-download-123",
            url="https://www.tiktok.com/@user/video/123",
            status=DownloadStatus.PENDING,
            client_id="test-client",
            created_at=now,
            last_updated=now
        )
        in_memory_db.create_download(download)
        
        # Get status
        response = client.get("/api/v1/status/test-download-123")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["download_id"] == "test-download-123"
        assert data["url"] == "https://www.tiktok.com/@user/video/123"
        assert data["status"] == "pending"
        assert "submitted_at" in data
        assert data["started_at"] is None
        assert data["completed_at"] is None
        assert data["file_path"] is None
        assert data["file_size"] is None
        assert data["error_message"] is None
    
    def test_get_completed_download_status(self, client, in_memory_db):
        """Test getting status of a completed download"""
        now = int(time.time())
        download = Download(
            id="test-download-456",
            url="https://www.instagram.com/reel/abc/",
            status=DownloadStatus.COMPLETED,
            client_id="test-client",
            created_at=now - 100,
            last_updated=now,
            started_at=now - 90,
            completed_at=now - 10,
            filename="/path/to/video.mp4",
            file_size=5242880
        )
        in_memory_db.create_download(download)
        
        response = client.get("/api/v1/status/test-download-456")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["download_id"] == "test-download-456"
        assert data["status"] == "completed"
        assert data["file_path"] == "/path/to/video.mp4"
        assert data["file_size"] == 5242880
        assert data["started_at"] is not None
        assert data["completed_at"] is not None
    
    def test_get_failed_download_status(self, client, in_memory_db):
        """Test getting status of a failed download"""
        now = int(time.time())
        download = Download(
            id="test-download-789",
            url="https://www.tiktok.com/@user/video/999",
            status=DownloadStatus.FAILED,
            client_id="test-client",
            created_at=now - 50,
            last_updated=now,
            started_at=now - 40,
            error_message="Network timeout"
        )
        in_memory_db.create_download(download)
        
        response = client.get("/api/v1/status/test-download-789")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["download_id"] == "test-download-789"
        assert data["status"] == "failed"
        assert data["error_message"] == "Network timeout"
        assert data["file_path"] is None
    
    def test_get_downloading_status(self, client, in_memory_db):
        """Test getting status of an in-progress download"""
        now = int(time.time())
        download = Download(
            id="test-download-999",
            url="https://www.tiktok.com/@user/video/555",
            status=DownloadStatus.DOWNLOADING,
            client_id="test-client",
            created_at=now - 20,
            last_updated=now,
            started_at=now - 15
        )
        in_memory_db.create_download(download)
        
        response = client.get("/api/v1/status/test-download-999")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "downloading"
        assert data["started_at"] is not None
        assert data["completed_at"] is None
    
    def test_download_not_found(self, client, in_memory_db):
        """Test 404 response for non-existent download"""
        response = client.get("/api/v1/status/550e8400-e29b-41d4-a716-446655440000")
        
        assert response.status_code == 404
        data = response.json()
        
        assert "error" in data["detail"]
        assert data["detail"]["error"] == "not_found"
        assert "request_id" in data["detail"]
    
    def test_invalid_uuid_format(self, client, in_memory_db):
        """Test 400 response for invalid UUID format"""
        response = client.get("/api/v1/status/invalid-uuid")
        
        assert response.status_code == 400
        data = response.json()
        
        assert "error" in data["detail"]
        assert data["detail"]["error"] == "invalid_id"
    
    def test_response_includes_request_id(self, client, in_memory_db):
        """Test response includes request ID header"""
        now = int(time.time())
        download = Download(
            id="test-download-reqid",
            url="https://www.tiktok.com/@user/video/123",
            status=DownloadStatus.PENDING,
            client_id=None,
            created_at=now,
            last_updated=now
        )
        in_memory_db.create_download(download)
        
        response = client.get("/api/v1/status/test-download-reqid")
        
        assert response.status_code == 200
        assert "X-Request-ID" in response.headers
    
    def test_status_endpoint_performance(self, client, in_memory_db):
        """Test status endpoint responds quickly"""
        now = int(time.time())
        download = Download(
            id="test-download-perf",
            url="https://www.tiktok.com/@user/video/123",
            status=DownloadStatus.PENDING,
            client_id=None,
            created_at=now,
            last_updated=now
        )
        in_memory_db.create_download(download)
        
        start_time = time.time()
        response = client.get("/api/v1/status/test-download-perf")
        duration = time.time() - start_time
        
        assert response.status_code == 200
        assert duration < 0.1  # Should respond in < 100ms
    
    def test_timestamps_are_iso_format(self, client, in_memory_db):
        """Test timestamps are in ISO 8601 format"""
        now = int(time.time())
        download = Download(
            id="test-download-timestamps",
            url="https://www.tiktok.com/@user/video/123",
            status=DownloadStatus.COMPLETED,
            client_id=None,
            created_at=now,
            last_updated=now,
            started_at=now + 1,
            completed_at=now + 10
        )
        in_memory_db.create_download(download)
        
        response = client.get("/api/v1/status/test-download-timestamps")
        
        assert response.status_code == 200
        data = response.json()
        
        # Check ISO 8601 format (should contain 'T' and end with timezone or 'Z')
        assert "T" in data["submitted_at"]
        assert "T" in data["started_at"]
        assert "T" in data["completed_at"]


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

