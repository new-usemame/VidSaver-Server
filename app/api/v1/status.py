"""Status Endpoint

GET /api/v1/status/{download_id} - Check the status of a download
"""

import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Request, HTTPException, status, Path

from app.api.v1.models import StatusResponse, ErrorResponse
from app.services.database_service import DatabaseService
from app.models.database import Download
from app.core.config import get_config

logger = logging.getLogger(__name__)
router = APIRouter()


def _download_to_status_response(download: Download, username: str) -> StatusResponse:
    """Convert Download database model to StatusResponse API model
    
    Args:
        download: Download database object
        username: Username for this download
        
    Returns:
        StatusResponse with all relevant fields
    """
    # Convert timestamps from Unix epoch to datetime
    submitted_at = datetime.fromtimestamp(download.created_at)
    started_at = datetime.fromtimestamp(download.started_at) if download.started_at else None
    completed_at = datetime.fromtimestamp(download.completed_at) if download.completed_at else None
    
    return StatusResponse(
        download_id=download.id,
        url=download.url,
        status=download.status,
        username=username,
        genre=download.genre,
        submitted_at=submitted_at,
        started_at=started_at,
        completed_at=completed_at,
        file_path=download.filename,
        file_size=download.file_size,
        error_message=download.error_message,
        genre_detection_error=download.genre_detection_error
    )


@router.get(
    "/status/{download_id}",
    response_model=StatusResponse,
    summary="Check Download Status",
    description="Check the current status of a video download by its ID. "
                "Returns detailed information including progress and file location if completed.",
    responses={
        200: {
            "description": "Download status retrieved successfully",
            "model": StatusResponse
        },
        404: {
            "description": "Download ID not found",
            "model": ErrorResponse
        },
        500: {
            "description": "Internal server error",
            "model": ErrorResponse
        }
    },
    tags=["Status"]
)
async def get_download_status(
    request: Request,
    download_id: str = Path(
        ...,
        description="Unique download identifier (UUID)",
        examples=["550e8400-e29b-41d4-a716-446655440000"]
    )
) -> StatusResponse:
    """Get the status of a specific download
    
    This endpoint queries the database for the download record and returns
    its current status, including:
    - Current status (pending, downloading, completed, failed)
    - Submission and completion timestamps
    - File location (if completed)
    - Error message (if failed)
    
    Args:
        request: FastAPI request object
        download_id: UUID of the download to check
        
    Returns:
        StatusResponse with current download information
        
    Raises:
        HTTPException 404: Download ID not found
        HTTPException 500: Database error
    """
    request_id = getattr(request.state, "request_id", "unknown")
    
    logger.info(
        f"Status check request {request_id}: download_id={download_id}"
    )
    
    # Validate UUID format
    try:
        import uuid
        uuid.UUID(download_id)
    except ValueError:
        logger.warning(
            f"Invalid download_id format {request_id}: {download_id}"
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "invalid_id",
                "message": "Invalid download ID format. Must be a valid UUID.",
                "request_id": request_id
            }
        )
    
    # Query database
    try:
        config = get_config()
        db = DatabaseService(db_path=config.database.path)
        
        download = db.get_download(download_id)
        
        if download is None:
            db.close_connection()
            logger.warning(
                f"Download not found {request_id}: {download_id}"
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error": "not_found",
                    "message": f"Download with ID '{download_id}' not found.",
                    "request_id": request_id
                }
            )
        
        # Get user info for response
        user = db.get_user_by_id(download.user_id)
        db.close_connection()
        
        if not user:
            logger.error(f"User ID {download.user_id} not found for download {download_id}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "error": "data_integrity_error",
                    "message": "Download user information is missing.",
                    "request_id": request_id
                }
            )
        
        logger.info(
            f"Status retrieved {request_id}: "
            f"download_id={download_id} status={download.status} user={user.username}"
        )
        
        return _download_to_status_response(download, user.username)
    
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    
    except Exception as e:
        logger.error(
            f"Failed to retrieve status {request_id}: {e}",
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "database_error",
                "message": "Failed to retrieve download status. Please try again.",
                "request_id": request_id
            }
        )

