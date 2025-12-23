"""Tests for API Request/Response Models"""

import pytest
from datetime import datetime
from pydantic import ValidationError

from app.api.v1.models import (
    DownloadRequest,
    DownloadResponse,
    StatusResponse,
    HealthResponse,
    ErrorResponse
)
from app.models.database import DownloadStatus


class TestDownloadRequest:
    """Test DownloadRequest model"""
    
    def test_valid_tiktok_url(self):
        """Test valid TikTok URL"""
        request = DownloadRequest(
            url="https://www.tiktok.com/@user/video/1234567890",
            username="testuser",
            client_id="test-client"
        )
        assert request.url == "https://www.tiktok.com/@user/video/1234567890"
        assert request.username == "testuser"
        assert request.client_id == "test-client"
    
    def test_valid_instagram_url(self):
        """Test valid Instagram URL"""
        request = DownloadRequest(
            url="https://www.instagram.com/reel/ABC123xyz/",
            username="testuser"
        )
        assert "instagram.com" in request.url
    
    def test_valid_tiktok_short_url(self):
        """Test valid TikTok short URL"""
        request = DownloadRequest(
            url="https://vm.tiktok.com/ZMhxyz123/",
            username="testuser"
        )
        assert "vm.tiktok.com" in request.url
    
    def test_invalid_url_format(self):
        """Test invalid URL format"""
        with pytest.raises(ValidationError) as exc_info:
            DownloadRequest(url="not-a-valid-url", username="testuser")
        assert "Invalid URL format" in str(exc_info.value)
    
    def test_url_too_short(self):
        """Test URL too short"""
        with pytest.raises(ValidationError) as exc_info:
            DownloadRequest(url="http://a", username="testuser")
        errors = exc_info.value.errors()
        assert any("at least 10 characters" in str(e) for e in errors)
    
    def test_url_too_long(self):
        """Test URL too long"""
        long_url = "https://www.tiktok.com/" + "x" * 3000
        with pytest.raises(ValidationError) as exc_info:
            DownloadRequest(url=long_url, username="testuser")
        errors = exc_info.value.errors()
        assert any("at most 2048 characters" in str(e) for e in errors)
    
    def test_optional_client_id(self):
        """Test client_id is optional"""
        request = DownloadRequest(url="https://www.tiktok.com/@user/video/1234567890", username="testuser")
        assert request.client_id is None
    
    def test_empty_client_id_becomes_none(self):
        """Test empty client_id becomes None"""
        request = DownloadRequest(
            url="https://www.tiktok.com/@user/video/1234567890",
            username="testuser",
            client_id="   "
        )
        assert request.client_id is None
    
    def test_http_protocol_allowed(self):
        """Test HTTP (non-secure) protocol is allowed"""
        request = DownloadRequest(url="http://www.tiktok.com/@user/video/1234567890", username="testuser")
        assert request.url.startswith("http://")


class TestDownloadResponse:
    """Test DownloadResponse model"""
    
    def test_valid_response(self):
        """Test valid download response"""
        now = datetime.now()
        response = DownloadResponse(
            success=True,
            download_id="550e8400-e29b-41d4-a716-446655440000",
            message="Download queued successfully",
            status="pending",
            username="testuser",
            genre="tiktok",
            submitted_at=now
        )
        assert response.success is True
        assert response.download_id == "550e8400-e29b-41d4-a716-446655440000"
        assert response.status == "pending"
        assert response.username == "testuser"
        assert response.genre == "tiktok"
        assert response.submitted_at == now
    
    def test_response_serialization(self):
        """Test response can be serialized to JSON"""
        now = datetime.now()
        response = DownloadResponse(
            success=True,
            download_id="test-id",
            message="Test message",
            status="pending",
            username="testuser",
            genre="tiktok",
            submitted_at=now
        )
        json_data = response.model_dump()
        assert json_data["success"] is True
        assert json_data["download_id"] == "test-id"


class TestStatusResponse:
    """Test StatusResponse model"""
    
    def test_pending_status(self):
        """Test status response for pending download"""
        now = datetime.now()
        response = StatusResponse(
            download_id="test-id",
            url="https://www.tiktok.com/@user/video/123",
            status="pending",
            username="testuser",
            genre="tiktok",
            submitted_at=now
        )
        assert response.status == "pending"
        assert response.started_at is None
        assert response.completed_at is None
        assert response.file_path is None
    
    def test_completed_status(self):
        """Test status response for completed download"""
        now = datetime.now()
        response = StatusResponse(
            download_id="test-id",
            url="https://www.tiktok.com/@user/video/123",
            status="completed",
            username="testuser",
            genre="tiktok",
            submitted_at=now,
            started_at=now,
            completed_at=now,
            file_path="/path/to/video.mp4",
            file_size=1024000
        )
        assert response.status == "completed"
        assert response.file_path == "/path/to/video.mp4"
        assert response.file_size == 1024000
    
    def test_failed_status(self):
        """Test status response for failed download"""
        now = datetime.now()
        response = StatusResponse(
            download_id="test-id",
            url="https://www.tiktok.com/@user/video/123",
            status="failed",
            username="testuser",
            genre="tiktok",
            submitted_at=now,
            started_at=now,
            error_message="Network error"
        )
        assert response.status == "failed"
        assert response.error_message == "Network error"


class TestHealthResponse:
    """Test HealthResponse model"""
    
    def test_healthy_status(self):
        """Test healthy status response"""
        now = datetime.now()
        response = HealthResponse(
            status="healthy",
            timestamp=now,
            version="1.0.0",
            database={"connected": True, "total_downloads": 42}
        )
        assert response.status == "healthy"
        assert response.version == "1.0.0"
        assert response.database["connected"] is True
        assert response.database["total_downloads"] == 42
    
    def test_unhealthy_status(self):
        """Test unhealthy status response"""
        now = datetime.now()
        response = HealthResponse(
            status="unhealthy",
            timestamp=now,
            version="1.0.0",
            database={"connected": False, "error": "Connection failed"}
        )
        assert response.status == "unhealthy"
        assert response.database["connected"] is False


class TestErrorResponse:
    """Test ErrorResponse model"""
    
    def test_basic_error(self):
        """Test basic error response"""
        response = ErrorResponse(
            error="validation_error",
            message="Invalid input"
        )
        assert response.error == "validation_error"
        assert response.message == "Invalid input"
        assert response.request_id is None
        assert response.details is None
    
    def test_error_with_details(self):
        """Test error response with details"""
        response = ErrorResponse(
            error="validation_error",
            message="Invalid URL",
            request_id="test-request-id",
            details={"field": "url", "reason": "Domain not supported"}
        )
        assert response.error == "validation_error"
        assert response.request_id == "test-request-id"
        assert response.details["field"] == "url"
