"""Download Endpoint

POST /api/v1/download - Submit a video URL for download
"""

import logging
import uuid
from datetime import datetime

from fastapi import APIRouter, Request, HTTPException, status
from pydantic import ValidationError

from app.api.v1.models import DownloadRequest, DownloadResponse, ErrorResponse
from app.services.database_service import DatabaseService
from app.services.genre_detector import detect_genre
from app.services.user_service import UserService
from app.models.database import DownloadStatus, Download
from app.core.config import get_config
import time

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post(
    "/download",
    response_model=DownloadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit Video Download",
    description="Submit a URL for download (TikTok, Instagram, YouTube, PDF, etc.). "
                "Returns immediately with a download_id for tracking.",
    responses={
        201: {
            "description": "Download queued successfully",
            "model": DownloadResponse
        },
        400: {
            "description": "Invalid request (bad URL, unsupported domain, etc.)",
            "model": ErrorResponse
        },
        500: {
            "description": "Internal server error",
            "model": ErrorResponse
        }
    },
    tags=["Download"]
)
async def submit_download(
    request: Request,
    download_request: DownloadRequest
) -> DownloadResponse:
    """Submit a URL for download
    
    This endpoint:
    1. Validates the URL and username
    2. Detects content genre from URL
    3. Gets or creates user account
    4. Generates a unique download_id
    5. Persists to database (BEFORE responding)
    6. Returns confirmation in < 500ms
    
    The actual download happens asynchronously in the background queue.
    
    Args:
        request: FastAPI request object
        download_request: Download request with URL, username, and optional client_id
        
    Returns:
        DownloadResponse with download_id, status, genre
        
    Raises:
        HTTPException 400: Invalid URL, username, or validation error
        HTTPException 500: Database error
    """
    request_id = getattr(request.state, "request_id", "unknown")
    
    # Generate unique download_id
    download_id = str(uuid.uuid4())
    submitted_at = datetime.now()
    
    logger.info(
        f"Download request {request_id}: "
        f"URL={download_request.url} "
        f"username={download_request.username} "
        f"client_id={download_request.client_id} "
        f"download_id={download_id}"
    )
    
    # Detect genre from URL (no data loss - always returns a genre)
    genre, genre_detection_error = detect_genre(download_request.url)
    logger.info(f"Genre detected: {genre}" + (f" (error: {genre_detection_error})" if genre_detection_error else ""))
    
    # Persist to database BEFORE responding (zero data loss requirement)
    try:
        config = get_config()
        db = DatabaseService(db_path=config.database.path)
        
        # Get or create user (auto-creation)
        user = db.get_or_create_user(download_request.username)
        logger.info(f"User: {user.username} (ID: {user.id})")
        
        # Ensure user directories exist
        user_service = UserService(config.downloads.root_directory)
        user_service.ensure_user_directories(user.username)
        
        # Create Download object
        download = Download(
            id=download_id,
            url=download_request.url,
            status=DownloadStatus.PENDING,
            client_id=download_request.client_id or "unknown",  # Default if not provided
            user_id=user.id,
            genre=genre,
            genre_detection_error=genre_detection_error,
            created_at=int(submitted_at.timestamp()),
            last_updated=int(submitted_at.timestamp())
        )
        
        # Create download record in database
        db.create_download(download=download, auto_commit=True)
        
        db.close_connection()
        
        logger.info(
            f"Download {download_id} persisted to database: "
            f"status=pending, user_id={user.id}, genre={genre}"
        )
    
    except Exception as e:
        logger.error(
            f"Failed to persist download {download_id}: {e}",
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "database_error",
                "message": "Failed to save download request. Please try again.",
                "request_id": request_id
            }
        )
    
    # Return success response
    logger.info(
        f"Download {download_id} queued successfully "
        f"(request {request_id})"
    )
    
    return DownloadResponse(
        success=True,
        download_id=download_id,
        message="Download queued successfully",
        status=DownloadStatus.PENDING,
        username=download_request.username,
        genre=genre,
        submitted_at=submitted_at
    )

