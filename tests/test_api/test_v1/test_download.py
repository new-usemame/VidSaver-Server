"""Tests for Download Endpoint"""

import pytest
from fastapi.testclient import TestClient
import uuid

from app.main import app
from app.models.database import DownloadStatus


class TestDownloadEndpoint:
    """Test POST /api/v1/download endpoint"""
    
    @pytest.fixture
    def client(self):
        """Create test client"""
        return TestClient(app)
    
    def test_submit_tiktok_download(self, client, in_memory_db):
        """Test submitting a TikTok download"""
        response = client.post(
            "/api/v1/download",
            json={
                "url": "https://www.tiktok.com/@user/video/1234567890",
                "client_id": "test-client"
            }
        )
        
        assert response.status_code == 201
        data = response.json()
        
        assert data["success"] is True
        assert "download_id" in data
        assert data["message"] == "Download queued successfully"
        assert data["status"] == "pending"
        assert "submitted_at" in data
        
        # Verify UUID format
        download_id = data["download_id"]
        assert uuid.UUID(download_id)  # Should not raise
    
    def test_submit_instagram_download(self, client, in_memory_db):
        """Test submitting an Instagram download"""
        response = client.post(
            "/api/v1/download",
            json={
                "url": "https://www.instagram.com/reel/ABC123xyz/"
            }
        )
        
        assert response.status_code == 201
        data = response.json()
        
        assert data["success"] is True
        assert "download_id" in data
    
    def test_submit_tiktok_short_url(self, client, in_memory_db):
        """Test submitting a TikTok short URL"""
        response = client.post(
            "/api/v1/download",
            json={
                "url": "https://vm.tiktok.com/ZMhxyz123/"
            }
        )
        
        assert response.status_code == 201
        data = response.json()
        
        assert data["success"] is True
    
    def test_download_persisted_to_database(self, client, in_memory_db):
        """Test download is persisted to database before response"""
        response = client.post(
            "/api/v1/download",
            json={
                "url": "https://www.tiktok.com/@user/video/1234567890",
                "client_id": "test-client"
            }
        )
        
        assert response.status_code == 201
        data = response.json()
        download_id = data["download_id"]
        
        # Verify in database
        download = in_memory_db.get_download(download_id)
        assert download is not None
        assert download.download_id == download_id
        assert download.url == "https://www.tiktok.com/@user/video/1234567890"
        assert download.status == DownloadStatus.PENDING
        assert download.client_id == "test-client"
    
    def test_download_without_client_id(self, client, in_memory_db):
        """Test download without client_id"""
        response = client.post(
            "/api/v1/download",
            json={
                "url": "https://www.tiktok.com/@user/video/1234567890"
            }
        )
        
        assert response.status_code == 201
        data = response.json()
        
        # Verify in database
        download = in_memory_db.get_download(data["download_id"])
        assert download.client_id is None
    
    def test_invalid_url_format(self, client, in_memory_db):
        """Test invalid URL format"""
        response = client.post(
            "/api/v1/download",
            json={
                "url": "not-a-valid-url"
            }
        )
        
        assert response.status_code == 422  # Validation error
        data = response.json()
        assert "detail" in data
    
    def test_unsupported_domain(self, client, in_memory_db):
        """Test unsupported domain"""
        response = client.post(
            "/api/v1/download",
            json={
                "url": "https://www.youtube.com/watch?v=123"
            }
        )
        
        assert response.status_code == 422  # Validation error
        data = response.json()
        assert "detail" in data
        # Check that error mentions domain not supported
        detail_str = str(data["detail"])
        assert "not supported" in detail_str.lower()
    
    def test_url_too_short(self, client, in_memory_db):
        """Test URL too short"""
        response = client.post(
            "/api/v1/download",
            json={
                "url": "http://a"
            }
        )
        
        assert response.status_code == 422
    
    def test_url_too_long(self, client, in_memory_db):
        """Test URL too long"""
        long_url = "https://www.tiktok.com/" + "x" * 3000
        response = client.post(
            "/api/v1/download",
            json={
                "url": long_url
            }
        )
        
        assert response.status_code == 422
    
    def test_missing_url(self, client, in_memory_db):
        """Test missing URL field"""
        response = client.post(
            "/api/v1/download",
            json={
                "client_id": "test"
            }
        )
        
        assert response.status_code == 422
    
    def test_multiple_downloads(self, client, in_memory_db):
        """Test multiple downloads get unique IDs"""
        response1 = client.post(
            "/api/v1/download",
            json={
                "url": "https://www.tiktok.com/@user/video/111"
            }
        )
        response2 = client.post(
            "/api/v1/download",
            json={
                "url": "https://www.tiktok.com/@user/video/222"
            }
        )
        
        assert response1.status_code == 201
        assert response2.status_code == 201
        
        id1 = response1.json()["download_id"]
        id2 = response2.json()["download_id"]
        
        assert id1 != id2
        
        # Both should be in database
        assert in_memory_db.get_download(id1) is not None
        assert in_memory_db.get_download(id2) is not None
    
    def test_response_includes_request_id(self, client, in_memory_db):
        """Test response includes request ID header"""
        response = client.post(
            "/api/v1/download",
            json={
                "url": "https://www.tiktok.com/@user/video/123"
            }
        )
        
        assert response.status_code == 201
        assert "X-Request-ID" in response.headers
    
    def test_http_protocol_allowed(self, client, in_memory_db):
        """Test HTTP (non-secure) URLs are allowed"""
        response = client.post(
            "/api/v1/download",
            json={
                "url": "http://www.tiktok.com/@user/video/123"
            }
        )
        
        assert response.status_code == 201
    
    def test_mobile_tiktok_url(self, client, in_memory_db):
        """Test mobile TikTok URL"""
        response = client.post(
            "/api/v1/download",
            json={
                "url": "https://m.tiktok.com/v/123456.html"
            }
        )
        
        assert response.status_code == 201
    
    def test_response_time_fast(self, client, in_memory_db):
        """Test response time is fast (< 500ms requirement)"""
        import time
        
        start_time = time.time()
        response = client.post(
            "/api/v1/download",
            json={
                "url": "https://www.tiktok.com/@user/video/123"
            }
        )
        duration = time.time() - start_time
        
        assert response.status_code == 201
        assert duration < 0.5  # Must be < 500ms
    
    def test_idempotent_download_ids(self, client, in_memory_db):
        """Test each request gets unique download_id even for same URL"""
        url = "https://www.tiktok.com/@user/video/123"
        
        response1 = client.post("/api/v1/download", json={"url": url})
        response2 = client.post("/api/v1/download", json={"url": url})
        
        id1 = response1.json()["download_id"]
        id2 = response2.json()["download_id"]
        
        # Should get different IDs for same URL
        assert id1 != id2


class TestDownloadEndpointDocumentation:
    """Test API documentation for download endpoint"""
    
    @pytest.fixture
    def client(self):
        """Create test client"""
        return TestClient(app)
    
    def test_openapi_schema_includes_download(self, client):
        """Test OpenAPI schema includes download endpoint"""
        response = client.get("/openapi.json")
        
        assert response.status_code == 200
        schema = response.json()
        
        assert "/api/v1/download" in schema["paths"]
        assert "post" in schema["paths"]["/api/v1/download"]
    
    def test_docs_page_accessible(self, client):
        """Test /docs page is accessible"""
        response = client.get("/docs")
        
        assert response.status_code == 200
        assert b"Video Download Server" in response.content

