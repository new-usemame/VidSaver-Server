"""Health Check Endpoint

GET /api/v1/health - Returns server health status
"""

import logging
from datetime import datetime
from typing import Dict, Any

from fastapi import APIRouter, Request

from app.api.v1.models import HealthResponse
from app.services.database_service import DatabaseService
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
    
    # Check database connectivity
    db_status: Dict[str, Any] = {
        "connected": False,
        "total_downloads": 0
    }
    
    try:
        db = DatabaseService(db_path=config.database.path)
        
        # Test database connection by querying all downloads
        downloads = db.get_all_downloads()
        count = len(downloads)
        db_status["connected"] = True
        db_status["total_downloads"] = count
        logger.debug(f"Database healthy: {count} downloads")
        
        db.close_connection()
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        db_status["connected"] = False
        db_status["error"] = str(e)
    
    return HealthResponse(
        status="healthy" if db_status["connected"] else "unhealthy",
        timestamp=datetime.now(),
        version="1.0.0",
        database=db_status
    )

