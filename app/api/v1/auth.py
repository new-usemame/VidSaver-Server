"""Authentication Endpoints

POST /api/v1/auth/login - Login with universal password
POST /api/v1/auth/logout - Logout and invalidate session
GET /api/v1/auth/verify - Verify session validity
GET /api/v1/auth/status - Check if auth is enabled
"""

import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Request, HTTPException, status, Header, Cookie, Response
from pydantic import BaseModel, Field

from app.core.config import get_config
from app.services.auth_service import get_auth_service

logger = logging.getLogger(__name__)
router = APIRouter()


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


@router.post(
    "/login",
    response_model=LoginResponse,
    summary="Login",
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
        logger.warning(f"Login attempt {request_id}: Invalid password")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": "invalid_password",
                "message": "Invalid password"
            }
        )
    
    # Create session
    token, expires_at = auth_service.create_session()
    
    # Set session cookie (httponly for security)
    response.set_cookie(
        key="session_token",
        value=token,
        httponly=True,
        secure=config.server.ssl.enabled,  # Only secure if HTTPS
        samesite="lax",
        max_age=config.auth.session_timeout_hours * 3600
    )
    
    logger.info(f"Login successful {request_id}: Session created")
    
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
    
    # Extract token from header or cookie
    token = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:]
    elif session_token:
        token = session_token
    
    if token:
        auth_service = get_auth_service(config.auth.session_timeout_hours)
        auth_service.invalidate_session(token)
    
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
    
    if auth_service.validate_session(token):
        return VerifyResponse(
            authenticated=True,
            message="Session is valid"
        )
    else:
        return VerifyResponse(
            authenticated=False,
            message="Session is invalid or expired"
        )
