"""Main FastAPI Application

This is the entry point for the Video Download Server.
Initializes FastAPI, configures middleware, and sets up routes.
"""

import logging
import time
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from app.core.config import get_config
from app.core.logging import setup_logging
from app.utils.cert_utils import get_certificate_info, check_certificate_expiry
from app.services.download_worker import start_worker, stop_worker

# Setup logging
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events (startup and shutdown)"""
    # Startup
    config = get_config()
    logger.info("=" * 60)
    logger.info("Video Download Server starting up...")
    logger.info(f"Version: {app.version}")
    logger.info(f"Environment: Production")
    logger.info("=" * 60)
    
    # Log configuration
    logger.info(f"Server: {config.server.host}:{config.server.port}")
    logger.info(f"Database: {config.database.path}")
    logger.info(f"Downloads: {config.downloads.root_directory}")
    logger.info(f"Max concurrent: {config.downloads.max_concurrent}")
    logger.info(f"Log level: {config.logging.level}")
    
    # Check SSL certificate
    if config.server.ssl.enabled:
        if config.server.ssl.use_letsencrypt and config.server.ssl.domain:
            from app.utils.cert_utils import get_letsencrypt_paths
            cert_path, _ = get_letsencrypt_paths(config.server.ssl.domain)
            logger.info(f"SSL: Enabled (Let's Encrypt, domain: {config.server.ssl.domain})")
            
            # Check certificate expiry
            needs_renewal, days, message = check_certificate_expiry(cert_path)
            if days is not None:
                logger.info(f"Certificate: {message}")
                if needs_renewal:
                    logger.warning("Certificate needs renewal soon!")
        else:
            logger.info(f"SSL: Enabled (Manual certificates)")
            logger.info(f"Certificate: {config.server.ssl.cert_file}")
            logger.info(f"Key: {config.server.ssl.key_file}")
    else:
        logger.info(f"SSL: Disabled (HTTP mode)")
    
    # Validate paths
    errors = config.validate_paths()
    if errors:
        logger.warning("Configuration validation warnings:")
        for error in errors:
            logger.warning(f"  - {error}")
    
    logger.info("Server startup complete")
    logger.info("=" * 60)
    
    # Start download worker
    logger.info("Starting download worker...")
    start_worker()
    logger.info("Download worker started")
    
    yield
    
    # Shutdown
    logger.info("Stopping download worker...")
    stop_worker()
    logger.info("=" * 60)
    logger.info("Video Download Server shutting down...")
    logger.info("Cleanup complete")
    logger.info("=" * 60)


# Create FastAPI application
app = FastAPI(
    title="Video Download Server",
    description="HTTPS server for downloading videos from TikTok and Instagram",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)


# Add CORS middleware (optional, for web interfaces)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this based on your needs
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_request_id_middleware(request: Request, call_next):
    """Add unique request ID to each request for tracing"""
    import uuid
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    
    # Add to response headers
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    
    return response


@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    """Log all incoming requests and responses"""
    start_time = time.time()
    request_id = getattr(request.state, "request_id", "unknown")
    
    # Log request
    logger.info(
        f"Request {request_id}: {request.method} {request.url.path} "
        f"from {request.client.host if request.client else 'unknown'}"
    )
    
    # Process request
    try:
        response = await call_next(request)
        
        # Calculate duration
        duration = time.time() - start_time
        
        # Log response
        logger.info(
            f"Response {request_id}: {response.status_code} "
            f"in {duration:.3f}s"
        )
        
        return response
        
    except Exception as e:
        duration = time.time() - start_time
        logger.error(
            f"Error {request_id}: {str(e)} after {duration:.3f}s",
            exc_info=True
        )
        raise


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for unhandled errors"""
    request_id = getattr(request.state, "request_id", "unknown")
    
    logger.error(
        f"Unhandled exception {request_id}: {str(exc)}",
        exc_info=True
    )
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal server error",
            "message": "An unexpected error occurred",
            "request_id": request_id,
        }
    )


# Root endpoint
@app.get("/", tags=["Root"])
async def root() -> Dict[str, str]:
    """Root endpoint - welcome message"""
    return {
        "message": "Video Download Server",
        "version": app.version,
        "docs": "/docs",
        "health": "/api/v1/health",
        "config_editor": "/api/v1/config/editor",
    }


# Include API routers
from app.api.v1 import download, health, status, history, config
app.include_router(health.router, prefix="/api/v1", tags=["Health"])
app.include_router(download.router, prefix="/api/v1", tags=["Download"])
app.include_router(status.router, prefix="/api/v1", tags=["Status"])
app.include_router(history.router, prefix="/api/v1", tags=["History"])
app.include_router(config.router, prefix="/api/v1/config", tags=["Configuration"])


def run_server():
    """Run the server with uvicorn
    
    This function is called from server.py
    
    When SSL is enabled, runs dual servers:
    - HTTPS on configured port (for domain/WAN access)
    - HTTP on configured port + 1 (for LAN access via IP)
    """
    import threading
    
    # Setup logging first
    setup_logging()
    
    # Get configuration
    config = get_config()
    
    # Prepare base uvicorn configuration
    base_config = {
        "app": "app.main:app",
        "host": config.server.host,
        "log_level": config.logging.level.lower(),
        "reload": False,
        "access_log": True,
    }
    
    if config.server.ssl.enabled:
        # DUAL SERVER MODE: Run both HTTPS and HTTP
        # - HTTPS on main port (for domain access)
        # - HTTP on main port - 1 (for LAN IP access)
        
        # Determine SSL certificate paths
        if config.server.ssl.use_letsencrypt and config.server.ssl.domain:
            from app.utils.cert_utils import get_letsencrypt_paths
            cert_path, key_path = get_letsencrypt_paths(config.server.ssl.domain)
        else:
            cert_path = config.server.ssl.cert_file
            key_path = config.server.ssl.key_file
        
        https_port = config.server.port
        http_port = config.server.port - 1  # e.g., 58443 -> 58442
        
        # HTTPS server config
        https_config = {
            **base_config,
            "port": https_port,
            "ssl_keyfile": key_path,
            "ssl_certfile": cert_path,
        }
        
        # HTTP server config (for LAN access)
        http_config = {
            **base_config,
            "port": http_port,
        }
        
        logger.info(f"Starting dual-server mode:")
        logger.info(f"  HTTPS: port {https_port} (for domain: {config.server.ssl.domain})")
        logger.info(f"  HTTP:  port {http_port} (for LAN IP access)")
        
        # Run HTTP server in a background thread
        def run_http_server():
            uvicorn.run(**http_config)
        
        http_thread = threading.Thread(target=run_http_server, daemon=True)
        http_thread.start()
        
        # Run HTTPS server in main thread
        uvicorn.run(**https_config)
    else:
        # Single HTTP server
        uvicorn_config = {
            **base_config,
            "port": config.server.port,
        }
        uvicorn.run(**uvicorn_config)


if __name__ == "__main__":
    run_server()

