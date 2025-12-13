"""History Endpoint

GET /api/v1/history - Get download history with pagination and filtering
"""

import logging
from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, Request, Query, HTTPException, status

from app.api.v1.models import StatusResponse
from app.services.database_service import DatabaseService
from app.models.database import Download, DownloadStatus
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
    "/history",
    response_model=List[StatusResponse],
    summary="Get Download History",
    description="Retrieve download history with optional filtering and pagination. "
                "Returns downloads sorted by submission date (newest first).",
    responses={
        200: {
            "description": "Download history retrieved successfully",
            "model": List[StatusResponse]
        },
        500: {
            "description": "Internal server error"
        }
    },
    tags=["History"]
)
async def get_download_history(
    request: Request,
    limit: int = Query(
        50,
        ge=1,
        le=100,
        description="Maximum number of downloads to return (1-100)",
        examples=[50]
    ),
    offset: int = Query(
        0,
        ge=0,
        description="Number of downloads to skip (for pagination)",
        examples=[0]
    ),
    status_filter: Optional[str] = Query(
        None,
        alias="status",
        description="Filter by download status (pending, downloading, completed, failed)",
        examples=["completed"]
    ),
    client_id: Optional[str] = Query(
        None,
        description="Filter by client ID",
        examples=["ios-app-v1.0"]
    ),
    username: Optional[str] = Query(
        None,
        description="Filter by username",
        examples=["john"]
    )
) -> List[StatusResponse]:
    """Get download history with pagination and filtering
    
    This endpoint returns a list of downloads with optional filtering by:
    - Status (pending, downloading, completed, failed)
    - Client ID
    - Username
    
    Results are paginated and sorted by submission date (newest first).
    
    Args:
        request: FastAPI request object
        limit: Maximum number of results to return (1-100)
        offset: Number of results to skip (for pagination)
        status_filter: Optional status filter
        client_id: Optional client ID filter
        username: Optional username filter
        
    Returns:
        List of StatusResponse objects
        
    Raises:
        HTTPException 400: Invalid parameters
        HTTPException 500: Database error
    """
    request_id = getattr(request.state, "request_id", "unknown")
    
    logger.info(
        f"History request {request_id}: "
        f"limit={limit} offset={offset} status={status_filter} client_id={client_id} username={username}"
    )
    
    # Validate status filter if provided
    if status_filter:
        valid_statuses = [s.value for s in DownloadStatus]
        if status_filter not in valid_statuses:
            logger.warning(
                f"Invalid status filter {request_id}: {status_filter}"
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "invalid_parameter",
                    "message": f"Invalid status filter. Must be one of: {', '.join(valid_statuses)}",
                    "request_id": request_id
                }
            )
    
    # Query database
    try:
        config = get_config()
        db = DatabaseService(db_path=config.database.path)
        
        # Get downloads based on username filter
        if username:
            # Filter by username
            all_downloads, total_count = db.get_downloads_by_username(username, limit=1000, offset=0)
        else:
            # Get all downloads
            all_downloads, total_count = db.get_all_downloads(limit=1000, offset=0)
        
        # Apply additional filters
        filtered_downloads = list(all_downloads)  # Make a copy
        
        if status_filter:
            filtered_downloads = [
                d for d in filtered_downloads 
                if d.status.value == status_filter
            ]
        
        if client_id:
            filtered_downloads = [
                d for d in filtered_downloads 
                if d.client_id == client_id
            ]
        
        # Sort by creation date (newest first)
        filtered_downloads.sort(key=lambda d: d.created_at, reverse=True)
        
        # Apply pagination
        paginated_downloads = filtered_downloads[offset:offset + limit]
        
        # Get usernames for all downloads
        user_map = {}  # Cache user lookups
        for download in paginated_downloads:
            if download.user_id not in user_map:
                user = db.get_user_by_id(download.user_id)
                if user:
                    user_map[download.user_id] = user.username
                else:
                    user_map[download.user_id] = "unknown"
        
        db.close_connection()
        
        logger.info(
            f"History retrieved {request_id}: "
            f"total={len(filtered_downloads)} returned={len(paginated_downloads)}"
        )
        
        # Convert to response models
        return [
            _download_to_status_response(d, user_map[d.user_id])
            for d in paginated_downloads
        ]
    
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    
    except Exception as e:
        logger.error(
            f"Failed to retrieve history {request_id}: {e}",
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "database_error",
                "message": "Failed to retrieve download history. Please try again.",
                "request_id": request_id
            }
        )

