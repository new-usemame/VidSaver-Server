"""Health Check Endpoint

GET /api/v1/health - Returns server health status
"""

import logging
from datetime import datetime
from typing import Dict, Any

from fastapi import APIRouter, Request

from app.api.v1.models import HealthResponse
from app.services.file_storage_service import FileStorageService
from app.core.config import get_config

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health Check",
    description="Returns the health status of the server and its dependencies",
    tags=["Health"]
)
async def health_check(request: Request) -> HealthResponse:
    """Health check endpoint
    
    Returns:
        HealthResponse with current server status
    """
    request_id = getattr(request.state, "request_id", "unknown")
    config = get_config()
    
    logger.info(f"Health check request {request_id}")
    
    # Check storage status
    storage_status: Dict[str, Any] = {
        "connected": False,
        "queue_items": 0
    }
    
    try:
        storage = FileStorageService(root_directory=config.downloads.root_directory)
        
        # Get queue counts
        counts = storage.get_queue_counts()
        storage_status["connected"] = True
        storage_status["queue_items"] = counts["total"]
        storage_status["pending"] = counts["pending"]
        storage_status["downloading"] = counts["downloading"]
        storage_status["failed"] = counts["failed"]
        logger.debug(f"Storage healthy: {counts['total']} queue items")
        
    except Exception as e:
        logger.error(f"Storage health check failed: {e}")
        storage_status["connected"] = False
        storage_status["error"] = str(e)
    
    return HealthResponse(
        status="healthy" if storage_status["connected"] else "unhealthy",
        timestamp=datetime.now(),
        version="1.0.0",
        database=storage_status  # Keep field name for API compatibility
    )
