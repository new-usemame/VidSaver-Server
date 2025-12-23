"""Tests for Health Check Endpoint"""

import pytest
import tempfile
import shutil
from fastapi.testclient import TestClient

from app.main import app
from app.core.config import get_config


class TestHealthEndpoint:
    """Test GET /api/v1/health endpoint"""
    
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
    def client(self, temp_storage_dir):
        """Create test client with temp storage"""
        config = get_config()
        original_root = config.downloads.root_directory
        config.downloads.root_directory = temp_storage_dir
        
        client = TestClient(app)
        yield client
        
        config.downloads.root_directory = original_root
    
    def test_health_check_success(self, client):
        """Test successful health check"""
        response = client.get("/api/v1/health")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert data["version"] == "1.0.0"
        assert "database" in data  # Field kept for API compatibility
        assert data["database"]["connected"] is True
    
    def test_health_check_response_headers(self, client):
        """Test health check includes request ID header"""
        response = client.get("/api/v1/health")
        
        assert response.status_code == 200
        assert "X-Request-ID" in response.headers
        
        # Request ID should be a valid UUID format
        request_id = response.headers["X-Request-ID"]
        assert len(request_id) == 36  # UUID format
        assert request_id.count("-") == 4
