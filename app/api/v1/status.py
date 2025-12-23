"""Status Endpoint

GET /api/v1/status/{download_id} - Check the status of a download
"""

import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Request, HTTPException, status, Path

from app.api.v1.models import StatusResponse, ErrorResponse
from app.services.file_storage_service import FileStorageService, QueueItem
from app.core.config import get_config

logger = logging.getLogger(__name__)
router = APIRouter()


def _queue_item_to_status_response(item: QueueItem) -> StatusResponse:
    """Convert QueueItem to StatusResponse API model
    
    Args:
        item: QueueItem from file storage
        
    Returns:
        StatusResponse with all relevant fields
    """
    # Convert timestamps from Unix epoch to datetime
    submitted_at = datetime.fromtimestamp(item.created_at)
    started_at = datetime.fromtimestamp(item.started_at) if item.started_at else None
    completed_at = datetime.fromtimestamp(item.completed_at) if item.completed_at else None
    
    return StatusResponse(
        download_id=item.id,
        url=item.url,
        status=item.status,
        username=item.username,
        genre=item.genre,
        submitted_at=submitted_at,
        started_at=started_at,
        completed_at=completed_at,
        file_path=item.filename,
        file_size=item.file_size,
        error_message=item.error_message,
        genre_detection_error=item.genre_detection_error
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
    
    This endpoint searches the queue and failed folders for the download record
    and returns its current status, including:
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
        HTTPException 500: Storage error
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
    
    # Search queue and failed folders
    try:
        config = get_config()
        storage = FileStorageService(root_directory=config.downloads.root_directory)
        
        # Search all users for this download
        item = storage.get_download(download_id)
        
        if item is None:
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
        
        logger.info(
            f"Status retrieved {request_id}: "
            f"download_id={download_id} status={item.status} user={item.username}"
        )
        
        return _queue_item_to_status_response(item)
    
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
                "error": "storage_error",
                "message": "Failed to retrieve download status. Please try again.",
                "request_id": request_id
            }
        )
