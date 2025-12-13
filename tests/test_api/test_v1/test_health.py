"""Tests for Health Check Endpoint"""

import pytest
from fastapi.testclient import TestClient

from app.main import app


class TestHealthEndpoint:
    """Test GET /api/v1/health endpoint"""
    
    @pytest.fixture
    def client(self):
        """Create test client"""
        return TestClient(app)
    
    def test_health_check_success(self, client, in_memory_db):
        """Test successful health check"""
        response = client.get("/api/v1/health")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert data["version"] == "1.0.0"
        assert "database" in data
        assert data["database"]["connected"] is True
        assert "total_downloads" in data["database"]
    
    def test_health_check_with_downloads(self, client, in_memory_db):
        """Test health check with existing downloads"""
        # Add some downloads
        in_memory_db.create_download(
            download_id="test-1",
            url="https://www.tiktok.com/@user/video/123",
            status="pending"
        )
        in_memory_db.create_download(
            download_id="test-2",
            url="https://www.instagram.com/reel/abc/",
            status="completed"
        )
        
        response = client.get("/api/v1/health")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "healthy"
        assert data["database"]["total_downloads"] == 2
    
    def test_health_check_response_headers(self, client, in_memory_db):
        """Test health check includes request ID header"""
        response = client.get("/api/v1/health")
        
        assert response.status_code == 200
        assert "X-Request-ID" in response.headers
        
        # Request ID should be a valid UUID format
        request_id = response.headers["X-Request-ID"]
        assert len(request_id) == 36  # UUID format
        assert request_id.count("-") == 4

