"""API Request/Response Models

Pydantic models for API endpoints.
"""

from typing import Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, field_validator, ConfigDict
import re

from app.models.database import DownloadStatus


class DownloadRequest(BaseModel):
    """Request model for POST /api/v1/download
    
    Receives a video URL from the client for download.
    """
    url: str = Field(
        ...,
        description="URL to download (TikTok, Instagram, YouTube, PDF, etc.)",
        min_length=10,
        max_length=2048,
        examples=[
            "https://www.tiktok.com/@user/video/1234567890",
            "https://www.instagram.com/reel/ABC123xyz/",
            "https://www.youtube.com/watch?v=abc123",
        ]
    )
    username: str = Field(
        ...,
        description="Username for organizing downloads (alphanumeric only)",
        min_length=1,
        max_length=100,
        examples=["john", "user123"]
    )
    client_id: Optional[str] = Field(
        None,
        description="Optional client identifier for tracking",
        max_length=255,
        examples=["ios-app-v1.0", "web-client"]
    )
    
    @field_validator('url')
    @classmethod
    def validate_url(cls, v: str) -> str:
        """Validate URL format"""
        # Basic URL format check
        url_pattern = re.compile(
            r'^https?://'  # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain
            r'localhost|'  # localhost
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
            r'(?::\d+)?'  # optional port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)
        
        if not url_pattern.match(v):
            raise ValueError('Invalid URL format')
        
        return v
    
    @field_validator('username')
    @classmethod
    def validate_username(cls, v: str) -> str:
        """Validate username format (alphanumeric only)"""
        if not v:
            raise ValueError('Username cannot be empty')
        
        if not re.match(r'^[a-zA-Z0-9]+$', v):
            raise ValueError('Username must be alphanumeric (letters and numbers only)')
        
        return v.lower()  # Normalize to lowercase
    
    @field_validator('client_id')
    @classmethod
    def validate_client_id(cls, v: Optional[str]) -> Optional[str]:
        """Validate client_id format"""
        if v is not None and v.strip() == '':
            return None
        return v


class DownloadResponse(BaseModel):
    """Response model for POST /api/v1/download
    
    Returns confirmation that the download was queued.
    """
    success: bool = Field(
        ...,
        description="Whether the request was successful"
    )
    download_id: str = Field(
        ...,
        description="Unique identifier for tracking this download",
        examples=["550e8400-e29b-41d4-a716-446655440000"]
    )
    message: str = Field(
        ...,
        description="Human-readable message",
        examples=["Download queued successfully"]
    )
    status: DownloadStatus = Field(
        ...,
        description="Current download status"
    )
    username: str = Field(
        ...,
        description="Username for this download"
    )
    genre: str = Field(
        ...,
        description="Detected content genre (tiktok, instagram, youtube, pdf, ebook, unknown)"
    )
    submitted_at: datetime = Field(
        ...,
        description="Timestamp when the download was submitted"
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "download_id": "550e8400-e29b-41d4-a716-446655440000",
                "message": "Download queued successfully",
                "status": "pending",
                "username": "john",
                "genre": "tiktok",
                "submitted_at": "2025-11-07T18:30:00Z"
            }
        }
    )


class StatusResponse(BaseModel):
    """Response model for GET /api/v1/status/{download_id}
    
    Returns the current status of a download.
    """
    download_id: str = Field(
        ...,
        description="Unique identifier for this download"
    )
    url: str = Field(
        ...,
        description="Original video URL"
    )
    status: DownloadStatus = Field(
        ...,
        description="Current download status"
    )
    username: str = Field(
        ...,
        description="Username for this download"
    )
    genre: str = Field(
        ...,
        description="Detected content genre"
    )
    submitted_at: datetime = Field(
        ...,
        description="When the download was submitted"
    )
    started_at: Optional[datetime] = Field(
        None,
        description="When download processing started"
    )
    completed_at: Optional[datetime] = Field(
        None,
        description="When download completed"
    )
    file_path: Optional[str] = Field(
        None,
        description="Path to downloaded file (if completed)"
    )
    file_size: Optional[int] = Field(
        None,
        description="Size of downloaded file in bytes (if completed)"
    )
    error_message: Optional[str] = Field(
        None,
        description="Error message (if failed)"
    )
    genre_detection_error: Optional[str] = Field(
        None,
        description="Error during genre detection (if any)"
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "download_id": "550e8400-e29b-41d4-a716-446655440000",
                "url": "https://www.tiktok.com/@user/video/1234567890",
                "status": "completed",
                "username": "john",
                "genre": "tiktok",
                "submitted_at": "2025-11-07T18:30:00Z",
                "started_at": "2025-11-07T18:30:01Z",
                "completed_at": "2025-11-07T18:30:15Z",
                "file_path": "/path/to/video.mp4",
                "file_size": 5242880,
                "error_message": None,
                "genre_detection_error": None
            }
        }
    )


class HealthResponse(BaseModel):
    """Response model for GET /api/v1/health
    
    Returns server health status.
    """
    status: str = Field(
        ...,
        description="Health status",
        examples=["healthy"]
    )
    timestamp: datetime = Field(
        ...,
        description="Current server timestamp"
    )
    version: str = Field(
        ...,
        description="Server version",
        examples=["1.0.0"]
    )
    database: Dict[str, Any] = Field(
        ...,
        description="Database health information"
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "healthy",
                "timestamp": "2025-11-07T18:30:00Z",
                "version": "1.0.0",
                "database": {
                    "connected": True,
                    "total_downloads": 42
                }
            }
        }
    )


class ErrorResponse(BaseModel):
    """Generic error response model"""
    error: str = Field(
        ...,
        description="Error type",
        examples=["validation_error", "not_found", "internal_error"]
    )
    message: str = Field(
        ...,
        description="Human-readable error message"
    )
    request_id: Optional[str] = Field(
        None,
        description="Request ID for tracking"
    )
    details: Optional[Dict[str, Any]] = Field(
        None,
        description="Additional error details"
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "error": "validation_error",
                "message": "Invalid URL format",
                "request_id": "550e8400-e29b-41d4-a716-446655440000",
                "details": {
                    "field": "url",
                    "reason": "Domain not supported"
                }
            }
        }
    )

