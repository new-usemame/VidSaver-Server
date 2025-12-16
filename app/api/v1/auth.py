"""Authentication Endpoints

POST /api/v1/auth/login - Login with universal password
POST /api/v1/auth/logout - Logout and invalidate session
GET /api/v1/auth/verify - Verify session validity
GET /api/v1/auth/status - Check if auth is enabled
GET /api/v1/auth/sessions - Session management page
"""

import logging
from datetime import datetime
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Request, HTTPException, status, Header, Cookie, Response
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from app.core.config import get_config
from app.services.auth_service import get_auth_service

logger = logging.getLogger(__name__)
router = APIRouter()


def get_client_ip(request: Request) -> str:
    """Extract client IP from request, handling proxies"""
    # Check for forwarded headers (when behind proxy)
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip
    
    # Fall back to direct connection
    if request.client:
        return request.client.host
    
    return "unknown"


# Request/Response models
class LoginRequest(BaseModel):
    """Login request with password"""
    password: str = Field(..., min_length=1, description="The universal access password")


class LoginResponse(BaseModel):
    """Login response with session token"""
    success: bool
    message: str
    session_token: Optional[str] = None
    expires_at: Optional[datetime] = None


class LogoutResponse(BaseModel):
    """Logout response"""
    success: bool
    message: str


class VerifyResponse(BaseModel):
    """Session verification response"""
    authenticated: bool
    message: str


class AuthStatusResponse(BaseModel):
    """Auth status response"""
    auth_enabled: bool
    message: str


class SessionInfo(BaseModel):
    """Session information"""
    id: int
    ip_address: Optional[str]
    device_info: Optional[str]
    created_at: int
    last_used_at: Optional[int]
    expires_at: Optional[int]


class SessionsListResponse(BaseModel):
    """Response for listing sessions"""
    sessions: List[Dict[str, Any]]
    total: int


class ActivityLogResponse(BaseModel):
    """Response for activity log"""
    entries: List[Dict[str, Any]]
    total: int


@router.get(
    "/status",
    response_model=AuthStatusResponse,
    summary="Check Auth Status",
    description="Check if authentication is enabled on this server",
    tags=["Authentication"]
)
async def auth_status() -> AuthStatusResponse:
    """Check if authentication is enabled
    
    Returns:
        AuthStatusResponse indicating if auth is required
    """
    config = get_config()
    auth_enabled = config.auth.enabled and config.auth.password_hash is not None
    
    if auth_enabled:
        return AuthStatusResponse(
            auth_enabled=True,
            message="Authentication is required. Please login with the universal password."
        )
    else:
        return AuthStatusResponse(
            auth_enabled=False,
            message="Authentication is disabled. All endpoints are accessible."
        )


@router.get(
    "/login",
    response_class=HTMLResponse,
    summary="Login Page",
    description="Display the login page",
    tags=["Authentication"]
)
async def login_page(redirect: str = "/"):
    """Display the login page
    
    Args:
        redirect: URL to redirect to after successful login
    """
    html_content = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Login - Video Server</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }}
        
        .login-container {{
            background: white;
            border-radius: 16px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            padding: 40px;
            width: 100%;
            max-width: 400px;
        }}
        
        .header {{
            text-align: center;
            margin-bottom: 30px;
        }}
        
        .header h1 {{
            font-size: 28px;
            color: #2c3e50;
            margin-bottom: 8px;
        }}
        
        .header p {{
            color: #6c757d;
            font-size: 14px;
        }}
        
        .form-group {{
            margin-bottom: 20px;
        }}
        
        .form-group label {{
            display: block;
            font-weight: 600;
            color: #495057;
            margin-bottom: 8px;
            font-size: 14px;
        }}
        
        .form-control {{
            width: 100%;
            padding: 12px 15px;
            border: 2px solid #e9ecef;
            border-radius: 8px;
            font-size: 16px;
            transition: border-color 0.2s;
        }}
        
        .form-control:focus {{
            outline: none;
            border-color: #667eea;
        }}
        
        .btn {{
            width: 100%;
            padding: 14px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 8px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: transform 0.2s, box-shadow 0.2s;
        }}
        
        .btn:hover {{
            transform: translateY(-2px);
            box-shadow: 0 5px 20px rgba(102, 126, 234, 0.4);
        }}
        
        .btn:disabled {{
            opacity: 0.7;
            cursor: not-allowed;
            transform: none;
        }}
        
        .alert {{
            padding: 12px 15px;
            border-radius: 8px;
            margin-bottom: 20px;
            font-size: 14px;
        }}
        
        .alert-error {{
            background: #f8d7da;
            color: #721c24;
            border: 1px solid #f5c6cb;
        }}
        
        .alert-success {{
            background: #d4edda;
            color: #155724;
            border: 1px solid #c3e6cb;
        }}
        
        #error-message {{
            display: none;
        }}
        
        .logo {{
            font-size: 48px;
            margin-bottom: 10px;
        }}
    </style>
</head>
<body>
    <div class="login-container">
        <div class="header">
            <div class="logo">🔐</div>
            <h1>Video Server</h1>
            <p>Enter your password to continue</p>
        </div>
        
        <div id="error-message" class="alert alert-error"></div>
        
        <form id="login-form" onsubmit="handleLogin(event)">
            <div class="form-group">
                <label for="password">Password</label>
                <input type="password" class="form-control" id="password" placeholder="Enter password" required autofocus>
            </div>
            
            <button type="submit" class="btn" id="submit-btn">
                Login
            </button>
        </form>
    </div>
    
    <script>
        const redirectUrl = {repr(redirect)};
        
        async function handleLogin(event) {{
            event.preventDefault();
            
            const password = document.getElementById('password').value;
            const submitBtn = document.getElementById('submit-btn');
            const errorDiv = document.getElementById('error-message');
            
            // Disable button
            submitBtn.disabled = true;
            submitBtn.textContent = 'Logging in...';
            errorDiv.style.display = 'none';
            
            try {{
                const response = await fetch('/api/v1/auth/login', {{
                    method: 'POST',
                    headers: {{
                        'Content-Type': 'application/json'
                    }},
                    body: JSON.stringify({{ password: password }})
                }});
                
                const data = await response.json();
                
                if (response.ok && data.success) {{
                    // Login successful - redirect
                    window.location.href = redirectUrl;
                }} else {{
                    // Show error
                    errorDiv.textContent = data.detail?.message || data.message || 'Invalid password';
                    errorDiv.style.display = 'block';
                    submitBtn.disabled = false;
                    submitBtn.textContent = 'Login';
                }}
            }} catch (error) {{
                errorDiv.textContent = 'Connection error. Please try again.';
                errorDiv.style.display = 'block';
                submitBtn.disabled = false;
                submitBtn.textContent = 'Login';
            }}
        }}
    </script>
</body>
</html>'''
    
    return HTMLResponse(content=html_content)


@router.post(
    "/login",
    response_model=LoginResponse,
    summary="Login API",
    description="Login with the universal access password to get a session token",
    tags=["Authentication"]
)
async def login(
    request: Request,
    response: Response,
    login_request: LoginRequest
) -> LoginResponse:
    """Login with universal password
    
    Args:
        login_request: LoginRequest with password
        response: FastAPI response for setting cookies
        
    Returns:
        LoginResponse with session token if successful
        
    Raises:
        HTTPException 401: Invalid password
        HTTPException 400: Auth not configured
    """
    request_id = getattr(request.state, "request_id", "unknown")
    config = get_config()
    ip_address = get_client_ip(request)
    user_agent = request.headers.get("User-Agent")
    
    # Check if auth is enabled
    if not config.auth.enabled:
        logger.info(f"Login attempt {request_id}: Auth is disabled")
        return LoginResponse(
            success=True,
            message="Authentication is disabled. No login required."
        )
    
    # Check if password is configured
    if not config.auth.password_hash:
        logger.warning(f"Login attempt {request_id}: No password configured")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "auth_not_configured",
                "message": "Authentication is enabled but no password is set. Run: python manage.py auth set-password"
            }
        )
    
    # Get auth service
    auth_service = get_auth_service(config.auth.session_timeout_hours)
    
    # Verify password
    if not auth_service.verify_password(login_request.password, config.auth.password_hash):
        # Log failed attempt
        auth_service.log_event(
            event_type="login_failed",
            ip_address=ip_address,
            user_agent=user_agent,
            details={"reason": "invalid_password"}
        )
        logger.warning(f"Login attempt {request_id}: Invalid password from {ip_address}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": "invalid_password",
                "message": "Invalid password"
            }
        )
    
    # Create session with IP and user agent tracking
    token, expires_at, session_id = auth_service.create_session(
        ip_address=ip_address,
        user_agent=user_agent
    )
    
    # Log successful login
    auth_service.log_event(
        event_type="login",
        ip_address=ip_address,
        user_agent=user_agent,
        session_id=session_id
    )
    
    # Set session cookie (httponly for security)
    # Handle unlimited timeout (0 or None)
    timeout_hours = config.auth.session_timeout_hours
    if timeout_hours and timeout_hours > 0:
        max_age = timeout_hours * 3600
    else:
        # Very long expiry for "never expires" (10 years)
        max_age = 10 * 365 * 24 * 3600
    
    response.set_cookie(
        key="session_token",
        value=token,
        httponly=True,
        secure=config.server.ssl.enabled,  # Only secure if HTTPS
        samesite="lax",
        max_age=max_age
    )
    
    logger.info(f"Login successful {request_id}: Session {session_id} created for {ip_address}")
    
    return LoginResponse(
        success=True,
        message="Login successful",
        session_token=token,
        expires_at=expires_at
    )


@router.post(
    "/logout",
    response_model=LogoutResponse,
    summary="Logout",
    description="Logout and invalidate the current session",
    tags=["Authentication"]
)
async def logout(
    request: Request,
    response: Response,
    authorization: Optional[str] = Header(None, alias="Authorization"),
    session_token: Optional[str] = Cookie(None)
) -> LogoutResponse:
    """Logout and invalidate session
    
    Args:
        authorization: Bearer token in header
        session_token: Session token from cookie
        response: FastAPI response for clearing cookies
        
    Returns:
        LogoutResponse
    """
    request_id = getattr(request.state, "request_id", "unknown")
    config = get_config()
    ip_address = get_client_ip(request)
    user_agent = request.headers.get("User-Agent")
    
    # Extract token from header or cookie
    token = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:]
    elif session_token:
        token = session_token
    
    if token:
        auth_service = get_auth_service(config.auth.session_timeout_hours)
        
        # Get session ID before invalidating
        is_valid, session_id = auth_service.validate_session(token, update_last_used=False)
        
        auth_service.invalidate_session(token)
        
        # Log logout
        auth_service.log_event(
            event_type="logout",
            ip_address=ip_address,
            user_agent=user_agent,
            session_id=session_id
        )
    
    # Clear cookie
    response.delete_cookie("session_token")
    
    logger.info(f"Logout {request_id}: Session invalidated")
    
    return LogoutResponse(
        success=True,
        message="Logged out successfully"
    )


@router.get(
    "/verify",
    response_model=VerifyResponse,
    summary="Verify Session",
    description="Check if the current session is valid",
    tags=["Authentication"]
)
async def verify_session(
    request: Request,
    authorization: Optional[str] = Header(None, alias="Authorization"),
    session_token: Optional[str] = Cookie(None)
) -> VerifyResponse:
    """Verify current session
    
    Args:
        authorization: Bearer token in header
        session_token: Session token from cookie
        
    Returns:
        VerifyResponse indicating if session is valid
    """
    config = get_config()
    
    # If auth is disabled, always authenticated
    if not config.auth.enabled or not config.auth.password_hash:
        return VerifyResponse(
            authenticated=True,
            message="Authentication is disabled"
        )
    
    # Extract token from header or cookie
    token = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:]
    elif session_token:
        token = session_token
    
    if not token:
        return VerifyResponse(
            authenticated=False,
            message="No session token provided"
        )
    
    auth_service = get_auth_service(config.auth.session_timeout_hours)
    
    is_valid, session_id = auth_service.validate_session(token)
    if is_valid:
        return VerifyResponse(
            authenticated=True,
            message="Session is valid"
        )
    else:
        return VerifyResponse(
            authenticated=False,
            message="Session is invalid or expired"
        )


# Session management endpoints

@router.get(
    "/sessions/list",
    response_model=SessionsListResponse,
    summary="List Active Sessions",
    description="Get list of all active sessions",
    tags=["Authentication"]
)
async def list_sessions() -> SessionsListResponse:
    """Get all active sessions"""
    config = get_config()
    auth_service = get_auth_service(config.auth.session_timeout_hours)
    
    sessions = auth_service.get_all_sessions()
    
    return SessionsListResponse(
        sessions=sessions,
        total=len(sessions)
    )


@router.delete(
    "/sessions/{session_id}",
    summary="Revoke Session",
    description="Revoke a specific session by ID",
    tags=["Authentication"]
)
async def revoke_session(session_id: int, request: Request):
    """Revoke a specific session"""
    config = get_config()
    auth_service = get_auth_service(config.auth.session_timeout_hours)
    ip_address = get_client_ip(request)
    user_agent = request.headers.get("User-Agent")
    
    success = auth_service.revoke_session_by_id(session_id)
    
    if success:
        auth_service.log_event(
            event_type="session_revoked",
            ip_address=ip_address,
            user_agent=user_agent,
            details={"revoked_session_id": session_id}
        )
        return {"success": True, "message": f"Session {session_id} revoked"}
    else:
        raise HTTPException(status_code=404, detail="Session not found")


@router.delete(
    "/sessions",
    summary="Revoke All Sessions",
    description="Revoke all active sessions",
    tags=["Authentication"]
)
async def revoke_all_sessions(request: Request):
    """Revoke all active sessions"""
    config = get_config()
    auth_service = get_auth_service(config.auth.session_timeout_hours)
    ip_address = get_client_ip(request)
    user_agent = request.headers.get("User-Agent")
    
    count = auth_service.revoke_all_sessions()
    
    auth_service.log_event(
        event_type="all_sessions_revoked",
        ip_address=ip_address,
        user_agent=user_agent,
        details={"sessions_revoked": count}
    )
    
    return {"success": True, "message": f"Revoked {count} sessions"}


@router.get(
    "/log",
    response_model=ActivityLogResponse,
    summary="Get Activity Log",
    description="Get authentication activity log",
    tags=["Authentication"]
)
async def get_activity_log(
    limit: int = 100,
    offset: int = 0,
    event_type: Optional[str] = None
) -> ActivityLogResponse:
    """Get activity log entries"""
    config = get_config()
    auth_service = get_auth_service(config.auth.session_timeout_hours)
    
    entries, total = auth_service.get_activity_log(
        limit=limit,
        offset=offset,
        event_type=event_type
    )
    
    return ActivityLogResponse(
        entries=entries,
        total=total
    )


@router.delete(
    "/log",
    summary="Clear Activity Log",
    description="Clear all activity log entries",
    tags=["Authentication"]
)
async def clear_activity_log(request: Request):
    """Clear all activity log entries"""
    config = get_config()
    auth_service = get_auth_service(config.auth.session_timeout_hours)
    ip_address = get_client_ip(request)
    
    count = auth_service.clear_activity_log()
    
    return {"success": True, "message": f"Cleared {count} log entries"}


# Session management HTML page
@router.get(
    "/sessions",
    response_class=HTMLResponse,
    summary="Session Management Page",
    description="Web interface for managing sessions and viewing activity log",
    tags=["Authentication"]
)
async def sessions_page():
    """Serve the session management HTML page"""
    html_content = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Sessions & Activity Log</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 16px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
        }
        
        .header {
            background: linear-gradient(135deg, #2c3e50 0%, #34495e 100%);
            color: white;
            padding: 25px 30px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .header h1 { font-size: 24px; }
        
        .back-btn {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            color: white;
            text-decoration: none;
            padding: 10px 20px;
            background: rgba(255,255,255,0.15);
            border-radius: 8px;
            transition: all 0.2s;
        }
        
        .back-btn:hover { background: rgba(255,255,255,0.25); }
        
        .content { padding: 30px; }
        
        .section {
            background: #f8f9fa;
            border-radius: 12px;
            padding: 25px;
            margin-bottom: 25px;
        }
        
        .section-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
        }
        
        .section-title {
            font-size: 18px;
            font-weight: 600;
            color: #2c3e50;
        }
        
        .badge {
            background: #667eea;
            color: white;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 14px;
        }
        
        .btn {
            padding: 10px 20px;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-size: 14px;
            font-weight: 500;
            transition: all 0.2s;
        }
        
        .btn-danger { background: #e74c3c; color: white; }
        .btn-danger:hover { background: #c0392b; }
        .btn-secondary { background: #95a5a6; color: white; }
        .btn-secondary:hover { background: #7f8c8d; }
        .btn-primary { background: #667eea; color: white; }
        .btn-primary:hover { background: #5a6fd6; }
        
        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 15px;
        }
        
        th, td {
            padding: 12px 15px;
            text-align: left;
            border-bottom: 1px solid #dee2e6;
        }
        
        th {
            background: #e9ecef;
            font-weight: 600;
            color: #495057;
            font-size: 13px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        
        tr:hover { background: #f1f3f5; }
        
        .device-info {
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        .device-icon {
            width: 32px;
            height: 32px;
            background: #e9ecef;
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 16px;
        }
        
        .time-ago {
            color: #6c757d;
            font-size: 13px;
        }
        
        .event-badge {
            display: inline-block;
            padding: 4px 10px;
            border-radius: 4px;
            font-size: 12px;
            font-weight: 500;
        }
        
        .event-login { background: #d4edda; color: #155724; }
        .event-logout { background: #fff3cd; color: #856404; }
        .event-login_failed { background: #f8d7da; color: #721c24; }
        .event-api_request { background: #cce5ff; color: #004085; }
        .event-session_revoked { background: #e2e3e5; color: #383d41; }
        .event-all_sessions_revoked { background: #e2e3e5; color: #383d41; }
        
        .filter-bar {
            display: flex;
            gap: 15px;
            align-items: center;
            margin-bottom: 15px;
        }
        
        .filter-bar select {
            padding: 8px 15px;
            border: 1px solid #dee2e6;
            border-radius: 6px;
            font-size: 14px;
        }
        
        .empty-state {
            text-align: center;
            padding: 40px;
            color: #6c757d;
        }
        
        .empty-state-icon {
            font-size: 48px;
            margin-bottom: 15px;
        }
        
        .load-more {
            text-align: center;
            padding: 15px;
        }
        
        .alert {
            padding: 15px 20px;
            border-radius: 8px;
            margin-bottom: 20px;
        }
        
        .alert-success { background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
        .alert-error { background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
        
        #alert-container {
            position: fixed;
            top: 20px;
            right: 20px;
            z-index: 1000;
            max-width: 400px;
        }
        
        @media (max-width: 768px) {
            .header { flex-direction: column; gap: 15px; text-align: center; }
            .section-header { flex-direction: column; gap: 15px; align-items: flex-start; }
            .filter-bar { flex-direction: column; align-items: stretch; }
            table { font-size: 13px; }
            th, td { padding: 8px 10px; }
        }
    </style>
</head>
<body>
    <div id="alert-container"></div>
    
    <div class="container">
        <div class="header">
            <h1>Sessions & Activity Log</h1>
            <a href="/api/v1/config/editor" class="back-btn">← Back to Config</a>
        </div>
        
        <div class="content">
            <!-- Active Sessions -->
            <div class="section">
                <div class="section-header">
                    <div style="display: flex; align-items: center; gap: 15px;">
                        <span class="section-title">Active Sessions</span>
                        <span class="badge" id="session-count">0</span>
                    </div>
                    <button class="btn btn-danger" onclick="revokeAllSessions()">Revoke All</button>
                </div>
                
                <div id="sessions-container">
                    <div class="empty-state">
                        <div class="empty-state-icon">🔄</div>
                        <div>Loading sessions...</div>
                    </div>
                </div>
            </div>
            
            <!-- Activity Log -->
            <div class="section">
                <div class="section-header">
                    <div style="display: flex; align-items: center; gap: 15px;">
                        <span class="section-title">Activity Log</span>
                        <span class="badge" id="log-count">0</span>
                    </div>
                    <button class="btn btn-secondary" onclick="clearLog()">Clear Log</button>
                </div>
                
                <div class="filter-bar">
                    <select id="event-filter" onchange="loadLog()">
                        <option value="">All Events</option>
                        <option value="login">Logins</option>
                        <option value="logout">Logouts</option>
                        <option value="login_failed">Failed Logins</option>
                        <option value="api_request">API Requests</option>
                    </select>
                    <button class="btn btn-primary" onclick="loadLog()">Refresh</button>
                </div>
                
                <div id="log-container">
                    <div class="empty-state">
                        <div class="empty-state-icon">🔄</div>
                        <div>Loading activity log...</div>
                    </div>
                </div>
                
                <div class="load-more" id="load-more" style="display: none;">
                    <button class="btn btn-secondary" onclick="loadMoreLog()">Load More</button>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        let logOffset = 0;
        const logLimit = 50;
        
        function showAlert(message, type) {
            const container = document.getElementById('alert-container');
            const alert = document.createElement('div');
            alert.className = `alert alert-${type}`;
            alert.textContent = message;
            container.appendChild(alert);
            setTimeout(() => alert.remove(), 5000);
        }
        
        function formatTimeAgo(timestamp) {
            const now = Math.floor(Date.now() / 1000);
            const diff = now - timestamp;
            
            if (diff < 60) return 'Just now';
            if (diff < 3600) return `${Math.floor(diff / 60)} min ago`;
            if (diff < 86400) return `${Math.floor(diff / 3600)} hours ago`;
            if (diff < 604800) return `${Math.floor(diff / 86400)} days ago`;
            
            return new Date(timestamp * 1000).toLocaleDateString();
        }
        
        function getDeviceIcon(deviceInfo) {
            if (!deviceInfo) return '💻';
            const d = deviceInfo.toLowerCase();
            if (d.includes('ios') || d.includes('iphone')) return '📱';
            if (d.includes('ipad')) return '📱';
            if (d.includes('android')) return '📱';
            if (d.includes('mac')) return '💻';
            if (d.includes('windows')) return '🖥️';
            if (d.includes('linux')) return '🐧';
            return '💻';
        }
        
        async function loadSessions() {
            try {
                const response = await fetch('/api/v1/auth/sessions/list');
                const data = await response.json();
                
                document.getElementById('session-count').textContent = data.total;
                
                if (data.sessions.length === 0) {
                    document.getElementById('sessions-container').innerHTML = `
                        <div class="empty-state">
                            <div class="empty-state-icon">🔐</div>
                            <div>No active sessions</div>
                        </div>
                    `;
                    return;
                }
                
                let html = `
                    <table>
                        <thead>
                            <tr>
                                <th>Device</th>
                                <th>IP Address</th>
                                <th>Last Active</th>
                                <th>Created</th>
                                <th>Action</th>
                            </tr>
                        </thead>
                        <tbody>
                `;
                
                for (const session of data.sessions) {
                    html += `
                        <tr>
                            <td>
                                <div class="device-info">
                                    <div class="device-icon">${getDeviceIcon(session.device_info)}</div>
                                    <div>${session.device_info || 'Unknown'}</div>
                                </div>
                            </td>
                            <td>${session.ip_address || 'Unknown'}</td>
                            <td class="time-ago">${formatTimeAgo(session.last_used_at)}</td>
                            <td class="time-ago">${formatTimeAgo(session.created_at)}</td>
                            <td>
                                <button class="btn btn-danger" onclick="revokeSession(${session.id})" style="padding: 6px 12px; font-size: 12px;">
                                    Revoke
                                </button>
                            </td>
                        </tr>
                    `;
                }
                
                html += '</tbody></table>';
                document.getElementById('sessions-container').innerHTML = html;
                
            } catch (error) {
                showAlert('Failed to load sessions: ' + error.message, 'error');
            }
        }
        
        async function revokeSession(sessionId) {
            if (!confirm('Are you sure you want to revoke this session?')) return;
            
            try {
                const response = await fetch(`/api/v1/auth/sessions/${sessionId}`, { method: 'DELETE' });
                if (response.ok) {
                    showAlert('Session revoked', 'success');
                    loadSessions();
                    loadLog();
                } else {
                    throw new Error('Failed to revoke session');
                }
            } catch (error) {
                showAlert('Error: ' + error.message, 'error');
            }
        }
        
        async function revokeAllSessions() {
            if (!confirm('Are you sure you want to revoke ALL sessions? Everyone will need to login again.')) return;
            
            try {
                const response = await fetch('/api/v1/auth/sessions', { method: 'DELETE' });
                if (response.ok) {
                    const data = await response.json();
                    showAlert(data.message, 'success');
                    loadSessions();
                    loadLog();
                } else {
                    throw new Error('Failed to revoke sessions');
                }
            } catch (error) {
                showAlert('Error: ' + error.message, 'error');
            }
        }
        
        async function loadLog(append = false) {
            if (!append) logOffset = 0;
            
            const eventFilter = document.getElementById('event-filter').value;
            const url = `/api/v1/auth/log?limit=${logLimit}&offset=${logOffset}` + 
                        (eventFilter ? `&event_type=${eventFilter}` : '');
            
            try {
                const response = await fetch(url);
                const data = await response.json();
                
                document.getElementById('log-count').textContent = data.total;
                
                if (data.entries.length === 0 && !append) {
                    document.getElementById('log-container').innerHTML = `
                        <div class="empty-state">
                            <div class="empty-state-icon">📋</div>
                            <div>No activity logged yet</div>
                        </div>
                    `;
                    document.getElementById('load-more').style.display = 'none';
                    return;
                }
                
                let html = '';
                if (!append) {
                    html = `
                        <table>
                            <thead>
                                <tr>
                                    <th>Time</th>
                                    <th>Event</th>
                                    <th>IP Address</th>
                                    <th>Details</th>
                                </tr>
                            </thead>
                            <tbody id="log-tbody">
                    `;
                }
                
                for (const entry of data.entries) {
                    const eventClass = 'event-' + entry.event_type;
                    const eventLabel = entry.event_type.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase());
                    
                    let details = '';
                    if (entry.endpoint) details = entry.endpoint;
                    else if (entry.details) {
                        if (typeof entry.details === 'object') {
                            details = JSON.stringify(entry.details);
                        } else {
                            details = entry.details;
                        }
                    }
                    if (details.length > 50) details = details.substring(0, 47) + '...';
                    
                    html += `
                        <tr>
                            <td class="time-ago">${formatTimeAgo(entry.timestamp)}</td>
                            <td><span class="event-badge ${eventClass}">${eventLabel}</span></td>
                            <td>${entry.ip_address || '-'}</td>
                            <td>${details || '-'}</td>
                        </tr>
                    `;
                }
                
                if (!append) {
                    html += '</tbody></table>';
                    document.getElementById('log-container').innerHTML = html;
                } else {
                    document.getElementById('log-tbody').insertAdjacentHTML('beforeend', html);
                }
                
                // Show/hide load more button
                const loadMore = document.getElementById('load-more');
                if (logOffset + data.entries.length < data.total) {
                    loadMore.style.display = 'block';
                } else {
                    loadMore.style.display = 'none';
                }
                
            } catch (error) {
                showAlert('Failed to load activity log: ' + error.message, 'error');
            }
        }
        
        function loadMoreLog() {
            logOffset += logLimit;
            loadLog(true);
        }
        
        async function clearLog() {
            if (!confirm('Are you sure you want to clear all activity logs?')) return;
            
            try {
                const response = await fetch('/api/v1/auth/log', { method: 'DELETE' });
                if (response.ok) {
                    const data = await response.json();
                    showAlert(data.message, 'success');
                    loadLog();
                } else {
                    throw new Error('Failed to clear log');
                }
            } catch (error) {
                showAlert('Error: ' + error.message, 'error');
            }
        }
        
        // Initial load
        loadSessions();
        loadLog();
        
        // Auto-refresh every 30 seconds
        setInterval(() => {
            loadSessions();
        }, 30000);
    </script>
</body>
</html>'''
    
    return HTMLResponse(content=html_content)
