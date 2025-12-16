"""Main FastAPI Application

This is the entry point for the Video Download Server.
Initializes FastAPI, configures middleware, and sets up routes.
"""

import logging
import time
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse, HTMLResponse
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
    logger.info(f"Downloads folder: {config.downloads.root_directory}")
    logger.info(f"Max concurrent downloads: {config.downloads.max_concurrent}")
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


@app.middleware("http")
async def authentication_middleware(request: Request, call_next):
    """Enforce authentication on protected endpoints
    
    - Checks if auth is enabled in config
    - Allows unauthenticated access to public paths
    - Requires valid session token for all other endpoints
    """
    config = get_config()
    
    # Skip if auth is disabled or no password is set
    if not config.auth.enabled or not config.auth.password_hash:
        return await call_next(request)
    
    # Define public paths that don't require authentication
    public_paths = [
        "/",
        "/docs",
        "/redoc",
        "/openapi.json",
        "/api/v1/health",
    ]
    
    # Check if path is public or under /api/v1/auth/
    path = request.url.path
    is_public = (
        path in public_paths or
        path.startswith("/api/v1/auth/") or
        path.startswith("/api/v1/auth")  # Handle /api/v1/auth without trailing slash
    )
    
    if is_public:
        return await call_next(request)
    
    # Extract token from Authorization header or cookie
    token = None
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header[7:]
    else:
        # Try to get from cookie
        token = request.cookies.get("session_token")
    
    # Validate token
    if not token:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={
                "error": "authentication_required",
                "message": "Authentication required. Please login at /api/v1/auth/login"
            },
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    # Import auth service and validate session
    from app.services.auth_service import get_auth_service
    auth_service = get_auth_service(config.auth.session_timeout_hours)
    
    if not auth_service.validate_session(token):
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={
                "error": "invalid_session",
                "message": "Session expired or invalid. Please login again at /api/v1/auth/login"
            },
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    # Token is valid, proceed with request
    return await call_next(request)


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


# Root endpoint - Landing page
@app.get("/", tags=["Root"], response_class=HTMLResponse)
async def root(request: Request):
    """Root endpoint - landing page with quick links"""
    from app.services.network_service import get_network_service
    
    config = get_config()
    port = config.server.port
    ssl_enabled = config.server.ssl.enabled
    
    # Get network info
    network = get_network_service()
    lan_ip = await network.get_lan_ip()
    
    # Dual-port logic
    if ssl_enabled:
        local_protocol = 'https'
        local_port = port
        lan_protocol = 'http'
        lan_port = port - 1
    else:
        local_protocol = 'http'
        local_port = port
        lan_protocol = 'http'
        lan_port = port
    
    html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Video Download Server</title>
        <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
                background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
                min-height: 100vh;
                color: #e0e0e0;
                padding: 40px 20px;
            }}
            .container {{
                max-width: 600px;
                margin: 0 auto;
            }}
            h1 {{
                font-size: 2rem;
                margin-bottom: 8px;
                color: #fff;
            }}
            .version {{
                color: #888;
                font-size: 0.9rem;
                margin-bottom: 30px;
            }}
            .status {{
                display: inline-flex;
                align-items: center;
                gap: 8px;
                background: rgba(76, 175, 80, 0.2);
                border: 1px solid rgba(76, 175, 80, 0.4);
                padding: 8px 16px;
                border-radius: 20px;
                margin-bottom: 30px;
                font-size: 0.9rem;
            }}
            .status-dot {{
                width: 10px;
                height: 10px;
                background: #4caf50;
                border-radius: 50%;
                animation: pulse 2s infinite;
            }}
            @keyframes pulse {{
                0%, 100% {{ opacity: 1; }}
                50% {{ opacity: 0.5; }}
            }}
            .section {{
                background: rgba(255, 255, 255, 0.05);
                border-radius: 12px;
                padding: 20px;
                margin-bottom: 20px;
            }}
            .section-title {{
                font-size: 0.85rem;
                text-transform: uppercase;
                letter-spacing: 1px;
                color: #888;
                margin-bottom: 15px;
            }}
            .menu {{
                display: flex;
                flex-direction: column;
                gap: 10px;
            }}
            .menu a {{
                display: flex;
                align-items: center;
                gap: 12px;
                padding: 14px 16px;
                background: rgba(255, 255, 255, 0.08);
                border-radius: 8px;
                text-decoration: none;
                color: #fff;
                transition: all 0.2s;
            }}
            .menu a:hover {{
                background: rgba(255, 255, 255, 0.15);
                transform: translateX(4px);
            }}
            .menu .icon {{
                font-size: 1.3rem;
            }}
            .menu .label {{
                flex: 1;
            }}
            .menu .arrow {{
                color: #666;
            }}
            .urls {{
                display: flex;
                flex-direction: column;
                gap: 12px;
            }}
            .url-group {{
                margin-bottom: 8px;
            }}
            .url-group-title {{
                font-size: 0.8rem;
                color: #888;
                margin-bottom: 6px;
            }}
            .url {{
                font-family: 'SF Mono', Monaco, 'Courier New', monospace;
                font-size: 0.85rem;
                background: rgba(0, 0, 0, 0.3);
                padding: 8px 12px;
                border-radius: 6px;
                word-break: break-all;
            }}
            .url a {{
                color: #64b5f6;
                text-decoration: none;
            }}
            .url a:hover {{
                text-decoration: underline;
            }}
            .url.lan a {{
                color: #ffb74d;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>📹 Video Download Server</h1>
            <p class="version">v{app.version}</p>
            
            <div class="status">
                <span class="status-dot"></span>
                Server Running
            </div>
            
            <div class="section">
                <div class="section-title">Quick Access</div>
                <div class="menu">
                    <a href="/docs">
                        <span class="icon">📖</span>
                        <span class="label">API Documentation</span>
                        <span class="arrow">→</span>
                    </a>
                    <a href="/api/v1/config/editor">
                        <span class="icon">🎛️</span>
                        <span class="label">Config Editor</span>
                        <span class="arrow">→</span>
                    </a>
                    <a href="/api/v1/config/setup">
                        <span class="icon">📱</span>
                        <span class="label">QR Code Setup</span>
                        <span class="arrow">→</span>
                    </a>
                    <a href="/api/v1/health">
                        <span class="icon">💚</span>
                        <span class="label">Health Check</span>
                        <span class="arrow">→</span>
                    </a>
                </div>
            </div>
            
            <div class="section">
                <div class="section-title">Access URLs</div>
                <div class="urls">
                    <div class="url-group">
                        <div class="url-group-title">This Machine (localhost)</div>
                        <div class="url"><a href="{local_protocol}://localhost:{local_port}/docs">{local_protocol}://localhost:{local_port}</a></div>
                    </div>
                    <div class="url-group">
                        <div class="url-group-title">LAN (other devices)</div>
                        <div class="url lan"><a href="{lan_protocol}://{lan_ip}:{lan_port}">{lan_protocol}://{lan_ip}:{lan_port}</a></div>
                    </div>
                </div>
            </div>
            
            <div class="section">
                <div class="section-title">📁 Downloads Folder</div>
                <div class="url" style="color: #81c784;">{config.downloads.root_directory}</div>
            </div>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html)


# Include API routers
from app.api.v1 import download, health, status, history, config, auth
app.include_router(health.router, prefix="/api/v1", tags=["Health"])
app.include_router(download.router, prefix="/api/v1", tags=["Download"])
app.include_router(status.router, prefix="/api/v1", tags=["Status"])
app.include_router(history.router, prefix="/api/v1", tags=["History"])
app.include_router(config.router, prefix="/api/v1/config", tags=["Configuration"])
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])


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

