"""Tests for History Endpoint"""

import pytest
from fastapi.testclient import TestClient
import time

from app.main import app
from app.models.database import Download, DownloadStatus


class TestHistoryEndpoint:
    """Test GET /api/v1/history endpoint"""
    
    @pytest.fixture
    def client(self):
        """Create test client"""
        return TestClient(app)
    
    def test_get_empty_history(self, client, in_memory_db):
        """Test getting history when no downloads exist"""
        response = client.get("/api/v1/history")
        
        assert response.status_code == 200
        data = response.json()
        
        assert isinstance(data, list)
        assert len(data) == 0
    
    def test_get_history_with_downloads(self, client, in_memory_db):
        """Test getting history with multiple downloads"""
        now = int(time.time())
        
        # Create downloads
        for i in range(5):
            download = Download(
                id=f"test-download-{i}",
                url=f"https://www.tiktok.com/@user/video/{i}",
                status=DownloadStatus.PENDING,
                client_id="test-client",
                created_at=now - (i * 10),
                last_updated=now - (i * 10)
            )
            in_memory_db.create_download(download)
        
        response = client.get("/api/v1/history")
        
        assert response.status_code == 200
        data = response.json()
        
        assert len(data) == 5
        # Should be sorted by creation date (newest first)
        assert data[0]["download_id"] == "test-download-0"
        assert data[4]["download_id"] == "test-download-4"
    
    def test_history_pagination_limit(self, client, in_memory_db):
        """Test history pagination with limit parameter"""
        now = int(time.time())
        
        # Create 10 downloads
        for i in range(10):
            download = Download(
                id=f"test-download-{i}",
                url=f"https://www.tiktok.com/@user/video/{i}",
                status=DownloadStatus.PENDING,
                client_id="test-client",
                created_at=now - i,
                last_updated=now - i
            )
            in_memory_db.create_download(download)
        
        # Request only 3
        response = client.get("/api/v1/history?limit=3")
        
        assert response.status_code == 200
        data = response.json()
        
        assert len(data) == 3
    
    def test_history_pagination_offset(self, client, in_memory_db):
        """Test history pagination with offset parameter"""
        now = int(time.time())
        
        # Create 10 downloads
        for i in range(10):
            download = Download(
                id=f"test-download-{i}",
                url=f"https://www.tiktok.com/@user/video/{i}",
                status=DownloadStatus.PENDING,
                client_id="test-client",
                created_at=now - i,
                last_updated=now - i
            )
            in_memory_db.create_download(download)
        
        # Skip first 5, get next 3
        response = client.get("/api/v1/history?limit=3&offset=5")
        
        assert response.status_code == 200
        data = response.json()
        
        assert len(data) == 3
        assert data[0]["download_id"] == "test-download-5"
    
    def test_history_filter_by_status(self, client, in_memory_db):
        """Test filtering history by status"""
        now = int(time.time())
        
        # Create downloads with different statuses
        statuses = [
            DownloadStatus.PENDING,
            DownloadStatus.COMPLETED,
            DownloadStatus.FAILED,
            DownloadStatus.PENDING,
            DownloadStatus.COMPLETED
        ]
        
        for i, status in enumerate(statuses):
            download = Download(
                id=f"test-download-{i}",
                url=f"https://www.tiktok.com/@user/video/{i}",
                status=status,
                client_id="test-client",
                created_at=now - i,
                last_updated=now - i
            )
            in_memory_db.create_download(download)
        
        # Filter by completed
        response = client.get("/api/v1/history?status=completed")
        
        assert response.status_code == 200
        data = response.json()
        
        assert len(data) == 2
        assert all(d["status"] == "completed" for d in data)
    
    def test_history_filter_by_client_id(self, client, in_memory_db):
        """Test filtering history by client_id"""
        now = int(time.time())
        
        # Create downloads with different client_ids
        client_ids = ["client-a", "client-b", "client-a", "client-c", "client-a"]
        
        for i, cid in enumerate(client_ids):
            download = Download(
                id=f"test-download-{i}",
                url=f"https://www.tiktok.com/@user/video/{i}",
                status=DownloadStatus.PENDING,
                client_id=cid,
                created_at=now - i,
                last_updated=now - i
            )
            in_memory_db.create_download(download)
        
        # Filter by client-a
        response = client.get("/api/v1/history?client_id=client-a")
        
        assert response.status_code == 200
        data = response.json()
        
        assert len(data) == 3
    
    def test_history_combined_filters(self, client, in_memory_db):
        """Test combining status and client_id filters"""
        now = int(time.time())
        
        # Create diverse downloads
        downloads = [
            ("0", DownloadStatus.PENDING, "client-a"),
            ("1", DownloadStatus.COMPLETED, "client-a"),
            ("2", DownloadStatus.COMPLETED, "client-b"),
            ("3", DownloadStatus.PENDING, "client-a"),
            ("4", DownloadStatus.COMPLETED, "client-a"),
        ]
        
        for i, (id_suffix, status, cid) in enumerate(downloads):
            download = Download(
                id=f"test-download-{id_suffix}",
                url=f"https://www.tiktok.com/@user/video/{i}",
                status=status,
                client_id=cid,
                created_at=now - i,
                last_updated=now - i
            )
            in_memory_db.create_download(download)
        
        # Filter by completed AND client-a
        response = client.get("/api/v1/history?status=completed&client_id=client-a")
        
        assert response.status_code == 200
        data = response.json()
        
        assert len(data) == 2
        assert all(d["status"] == "completed" for d in data)
    
    def test_history_sorting_newest_first(self, client, in_memory_db):
        """Test downloads are sorted by creation date (newest first)"""
        now = int(time.time())
        
        # Create downloads with different creation times
        for i in range(5):
            download = Download(
                id=f"test-download-{i}",
                url=f"https://www.tiktok.com/@user/video/{i}",
                status=DownloadStatus.PENDING,
                client_id="test-client",
                created_at=now - (100 * i),  # Larger gaps
                last_updated=now - (100 * i)
            )
            in_memory_db.create_download(download)
        
        response = client.get("/api/v1/history")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify sorting (newest first)
        for i in range(len(data) - 1):
            current_time = data[i]["submitted_at"]
            next_time = data[i + 1]["submitted_at"]
            assert current_time >= next_time
    
    def test_history_invalid_status_filter(self, client, in_memory_db):
        """Test invalid status filter returns 400"""
        response = client.get("/api/v1/history?status=invalid_status")
        
        assert response.status_code == 400
        data = response.json()
        
        assert "error" in data["detail"]
        assert data["detail"]["error"] == "invalid_parameter"
    
    def test_history_limit_bounds(self, client, in_memory_db):
        """Test limit parameter bounds"""
        # Limit below minimum (should use 1)
        response = client.get("/api/v1/history?limit=0")
        assert response.status_code == 422  # Validation error
        
        # Limit above maximum (should use 100)
        response = client.get("/api/v1/history?limit=200")
        assert response.status_code == 422  # Validation error
    
    def test_history_negative_offset(self, client, in_memory_db):
        """Test negative offset is rejected"""
        response = client.get("/api/v1/history?offset=-1")
        
        assert response.status_code == 422  # Validation error
    
    def test_history_includes_request_id(self, client, in_memory_db):
        """Test response includes request ID header"""
        response = client.get("/api/v1/history")
        
        assert response.status_code == 200
        assert "X-Request-ID" in response.headers
    
    def test_history_with_completed_downloads(self, client, in_memory_db):
        """Test history includes file information for completed downloads"""
        now = int(time.time())
        
        download = Download(
            id="test-completed",
            url="https://www.tiktok.com/@user/video/123",
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
        
        response = client.get("/api/v1/history")
        
        assert response.status_code == 200
        data = response.json()
        
        assert len(data) == 1
        assert data[0]["status"] == "completed"
        assert data[0]["file_path"] == "/path/to/video.mp4"
        assert data[0]["file_size"] == 5242880


class TestHistoryEndpointDocumentation:
    """Test API documentation for history endpoint"""
    
    @pytest.fixture
    def client(self):
        """Create test client"""
        return TestClient(app)
    
    def test_openapi_schema_includes_history(self, client):
        """Test OpenAPI schema includes history endpoint"""
        response = client.get("/openapi.json")
        
        assert response.status_code == 200
        schema = response.json()
        
        assert "/api/v1/history" in schema["paths"]
        assert "get" in schema["paths"]["/api/v1/history"]
    
    def test_history_parameters_documented(self, client):
        """Test history endpoint parameters are documented"""
        response = client.get("/openapi.json")
        
        assert response.status_code == 200
        schema = response.json()
        
        parameters = schema["paths"]["/api/v1/history"]["get"]["parameters"]
        param_names = [p["name"] for p in parameters]
        
        assert "limit" in param_names
        assert "offset" in param_names
        assert "status" in param_names
        assert "client_id" in param_names

