"""Downloads Browser Endpoints

GET /api/v1/downloads/browse - HTML page for browsing downloads
GET /api/v1/downloads/structure - Returns folder tree JSON
GET /api/v1/downloads/videos - Returns videos list with filters and metadata paths
GET /api/v1/downloads/stream/{path} - Stream/download a file (video, thumbnail, etc.)
GET /api/v1/downloads/metadata/{path} - Get parsed metadata JSON for a video
GET /api/v1/downloads/queue - Get download queue status

SECURITY: This module ALWAYS requires authentication, even if global auth is disabled.
"""

import logging
import os
import json
import mimetypes
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime
from urllib.parse import quote, unquote

from fastapi import APIRouter, Request, HTTPException, status, Query
from fastapi.responses import HTMLResponse, FileResponse, StreamingResponse, RedirectResponse

from app.core.config import get_config
from app.services.auth_service import get_auth_service
from app.services.user_service import UserService
from app.services.database_service import DatabaseService
from app.models.database import DownloadStatus

logger = logging.getLogger(__name__)
router = APIRouter()


# =============================================================================
# Security Functions
# =============================================================================

# Allowed file extensions for streaming/download
ALLOWED_EXTENSIONS = {
    '.mp4', '.webm', '.mov', '.avi', '.mkv', '.m4v', '.m4a',  # Video
    '.mp3', '.wav', '.ogg', '.flac',  # Audio
    '.pdf', '.epub', '.mobi',  # Documents
    '.json',  # Metadata sidecar files
    '.webp', '.jpg', '.jpeg', '.png',  # Thumbnails
}


def extract_bearer_token(request: Request) -> Optional[str]:
    """Extract Bearer token from Authorization header"""
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        return auth_header[7:]
    return None


async def require_auth(request: Request) -> bool:
    """Always require auth for downloads browser, regardless of global setting.
    
    Returns True if authenticated, raises HTTPException otherwise.
    """
    config = get_config()
    
    # Check if password is configured
    if not config.auth.password_hash:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": "auth_not_configured",
                "message": "Authentication not configured. Set a password first using: python manage.py auth set-password"
            }
        )
    
    # Get token from cookie or header
    token = request.cookies.get("session_token") or extract_bearer_token(request)
    
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": "authentication_required",
                "message": "This page requires authentication. Please login first.",
                "login_url": "/api/v1/auth/login"
            }
        )
    
    # Validate session
    auth_service = get_auth_service(config.auth.session_timeout_hours)
    is_valid, session_id = auth_service.validate_session(token)
    
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": "session_expired",
                "message": "Session expired or invalid. Please login again.",
                "login_url": "/api/v1/auth/login"
            }
        )
    
    return True


def is_safe_path(requested_path: str, allowed_root: Path) -> bool:
    """Validate path is within allowed directory (prevent path traversal attacks).
    
    Args:
        requested_path: The path requested by the user
        allowed_root: The root directory that paths must be within
        
    Returns:
        True if path is safe, False otherwise
    """
    try:
        # Build full path
        full_path = allowed_root / requested_path
        
        # Resolve to absolute path (follows symlinks, normalizes ..)
        resolved = full_path.resolve()
        allowed_resolved = allowed_root.resolve()
        
        # Check if resolved path is under allowed root
        return resolved.is_relative_to(allowed_resolved)
    except (ValueError, RuntimeError, OSError):
        return False


def is_allowed_extension(filename: str) -> bool:
    """Check if file extension is allowed for streaming"""
    ext = Path(filename).suffix.lower()
    return ext in ALLOWED_EXTENSIONS


def format_file_size(size_bytes: int) -> str:
    """Format file size in human-readable format"""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"


def format_timestamp(timestamp: int) -> str:
    """Format Unix timestamp as relative time"""
    if not timestamp:
        return "Unknown"
    
    now = datetime.now().timestamp()
    diff = now - timestamp
    
    if diff < 60:
        return "Just now"
    elif diff < 3600:
        mins = int(diff / 60)
        return f"{mins} min{'s' if mins != 1 else ''} ago"
    elif diff < 86400:
        hours = int(diff / 3600)
        return f"{hours} hour{'s' if hours != 1 else ''} ago"
    elif diff < 604800:
        days = int(diff / 86400)
        return f"{days} day{'s' if days != 1 else ''} ago"
    else:
        return datetime.fromtimestamp(timestamp).strftime("%b %d, %Y")


def read_video_metadata(video_path: Path) -> Optional[Dict[str, Any]]:
    """Read metadata from sidecar JSON file.
    
    Args:
        video_path: Path to the video file
        
    Returns:
        Parsed metadata dict, or None if not found/invalid
    """
    info_path = video_path.parent / (video_path.name + '.info.json')
    if not info_path.exists():
        return None
    try:
        with open(info_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.warning(f"Error reading metadata for {video_path}: {e}")
        return None


def get_thumbnail_path(video_path: Path) -> Optional[Path]:
    """Find thumbnail file for a video.
    
    Checks for common thumbnail extensions in order of preference.
    
    Args:
        video_path: Path to the video file
        
    Returns:
        Path to thumbnail if found, None otherwise
    """
    # yt-dlp saves thumbnails with same base name but different extension
    base = video_path.stem
    parent = video_path.parent
    
    # Check common thumbnail extensions
    for ext in ['.webp', '.jpg', '.jpeg', '.png']:
        thumb_path = parent / f"{base}{ext}"
        if thumb_path.exists():
            return thumb_path
    return None


# =============================================================================
# API Endpoints
# =============================================================================

@router.get(
    "/structure",
    summary="Get Folder Structure",
    description="Returns the downloads folder structure with user directories, genres, and file counts.",
    responses={
        200: {"description": "Folder structure retrieved successfully"},
        401: {"description": "Authentication required"},
        500: {"description": "Internal server error"}
    }
)
async def get_folder_structure(request: Request):
    """Get the downloads folder structure as JSON"""
    await require_auth(request)
    
    config = get_config()
    root_dir = Path(config.downloads.root_directory)
    
    if not root_dir.exists():
        return {
            "root_directory": str(root_dir),
            "users": [],
            "total_videos": 0,
            "total_size": 0,
            "error": "Downloads directory does not exist"
        }
    
    users = []
    total_videos = 0
    total_size = 0
    
    # Scan user directories
    try:
        for user_dir in sorted(root_dir.iterdir()):
            if not user_dir.is_dir():
                continue
            
            username = user_dir.name
            genres = {}
            user_total_videos = 0
            user_total_size = 0
            
            # Scan genre directories
            for genre_dir in user_dir.iterdir():
                if not genre_dir.is_dir():
                    continue
                
                genre_name = genre_dir.name
                genre_count = 0
                genre_size = 0
                
                # Count files in genre directory
                for file_path in genre_dir.iterdir():
                    if file_path.is_file() and is_allowed_extension(file_path.name):
                        genre_count += 1
                        try:
                            genre_size += file_path.stat().st_size
                        except OSError:
                            pass
                
                if genre_count > 0:
                    genres[genre_name] = {
                        "count": genre_count,
                        "size_bytes": genre_size,
                        "size_formatted": format_file_size(genre_size)
                    }
                    user_total_videos += genre_count
                    user_total_size += genre_size
            
            if user_total_videos > 0 or genres:
                users.append({
                    "username": username,
                    "genres": genres,
                    "total_videos": user_total_videos,
                    "total_size": user_total_size,
                    "total_size_formatted": format_file_size(user_total_size)
                })
                total_videos += user_total_videos
                total_size += user_total_size
    
    except Exception as e:
        logger.error(f"Error scanning folder structure: {e}", exc_info=True)
        return {
            "root_directory": str(root_dir),
            "users": [],
            "total_videos": 0,
            "total_size": 0,
            "error": f"Error scanning directory: {str(e)}"
        }
    
    return {
        "root_directory": str(root_dir),
        "users": users,
        "total_videos": total_videos,
        "total_size": total_size,
        "total_size_formatted": format_file_size(total_size)
    }


@router.get(
    "/videos",
    summary="Get Videos List",
    description="Returns a list of videos with optional filtering by user, genre, and search.",
    responses={
        200: {"description": "Videos list retrieved successfully"},
        401: {"description": "Authentication required"},
        500: {"description": "Internal server error"}
    }
)
async def get_videos_list(
    request: Request,
    username: Optional[str] = Query(None, description="Filter by username"),
    genre: Optional[str] = Query(None, description="Filter by genre (tiktok, instagram, etc.)"),
    search: Optional[str] = Query(None, description="Search in filename"),
    sort: str = Query("newest", description="Sort order: newest, oldest, largest, smallest, name"),
    limit: int = Query(50, ge=1, le=200, description="Maximum results"),
    offset: int = Query(0, ge=0, description="Pagination offset")
):
    """Get list of videos with filtering and pagination"""
    await require_auth(request)
    
    config = get_config()
    root_dir = Path(config.downloads.root_directory)
    
    if not root_dir.exists():
        return {
            "videos": [],
            "total": 0,
            "limit": limit,
            "offset": offset
        }
    
    videos = []
    
    # Determine which user directories to scan
    if username:
        user_dirs = [root_dir / username] if (root_dir / username).exists() else []
    else:
        user_dirs = [d for d in root_dir.iterdir() if d.is_dir()]
    
    # Scan directories
    for user_dir in user_dirs:
        user_name = user_dir.name
        
        # Determine which genre directories to scan
        if genre:
            genre_dirs = [user_dir / genre] if (user_dir / genre).exists() else []
        else:
            genre_dirs = [d for d in user_dir.iterdir() if d.is_dir()]
        
        for genre_dir in genre_dirs:
            genre_name = genre_dir.name
            
            # Extensions that are primary content (not metadata/thumbnails)
            primary_extensions = {
                '.mp4', '.webm', '.mov', '.avi', '.mkv', '.m4v', '.m4a',  # Video
                '.mp3', '.wav', '.ogg', '.flac',  # Audio
                '.pdf', '.epub', '.mobi',  # Documents
            }
            
            for file_path in genre_dir.iterdir():
                if not file_path.is_file():
                    continue
                
                # Only include primary content files (skip .info.json and thumbnails)
                ext = file_path.suffix.lower()
                if ext not in primary_extensions:
                    continue
                
                # Apply search filter
                if search and search.lower() not in file_path.name.lower():
                    continue
                
                try:
                    stat = file_path.stat()
                    
                    # Build relative path for streaming
                    rel_path = f"{user_name}/{genre_name}/{file_path.name}"
                    
                    # Check for metadata sidecar file
                    info_json_path = file_path.parent / (file_path.name + '.info.json')
                    has_metadata = info_json_path.exists()
                    
                    # Check for thumbnail
                    thumb = get_thumbnail_path(file_path)
                    thumbnail_path = f"{user_name}/{genre_name}/{thumb.name}" if thumb else None
                    
                    videos.append({
                        "filename": file_path.name,
                        "username": user_name,
                        "genre": genre_name,
                        "path": rel_path,
                        "size_bytes": stat.st_size,
                        "size_formatted": format_file_size(stat.st_size),
                        "modified_at": int(stat.st_mtime),
                        "modified_formatted": format_timestamp(int(stat.st_mtime)),
                        "extension": ext,
                        "has_metadata": has_metadata,
                        "metadata_path": f"{rel_path}.info.json" if has_metadata else None,
                        "thumbnail_path": thumbnail_path,
                    })
                except OSError as e:
                    logger.warning(f"Error reading file {file_path}: {e}")
    
    # Sort videos
    if sort == "newest":
        videos.sort(key=lambda v: v["modified_at"], reverse=True)
    elif sort == "oldest":
        videos.sort(key=lambda v: v["modified_at"])
    elif sort == "largest":
        videos.sort(key=lambda v: v["size_bytes"], reverse=True)
    elif sort == "smallest":
        videos.sort(key=lambda v: v["size_bytes"])
    elif sort == "name":
        videos.sort(key=lambda v: v["filename"].lower())
    
    # Get total before pagination
    total = len(videos)
    
    # Apply pagination
    videos = videos[offset:offset + limit]
    
    return {
        "videos": videos,
        "total": total,
        "limit": limit,
        "offset": offset,
        "has_more": offset + len(videos) < total
    }


@router.get(
    "/stream/{file_path:path}",
    summary="Stream Video File",
    description="Stream or download a video file from the downloads directory.",
    responses={
        200: {"description": "File streamed successfully"},
        401: {"description": "Authentication required"},
        403: {"description": "Access forbidden"},
        404: {"description": "File not found"}
    }
)
async def stream_file(request: Request, file_path: str):
    """Stream a video file from the downloads directory.
    
    Security:
    - Always requires authentication
    - Validates path is within downloads directory
    - Only serves allowed file types
    """
    await require_auth(request)
    
    config = get_config()
    root_dir = Path(config.downloads.root_directory)
    
    # Decode URL-encoded path
    file_path = unquote(file_path)
    
    # Security: Validate path is within allowed directory
    if not is_safe_path(file_path, root_dir):
        logger.warning(f"Path traversal attempt blocked: {file_path}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Invalid path"
        )
    
    # Build full path
    full_path = (root_dir / file_path).resolve()
    
    # Check file exists
    if not full_path.exists() or not full_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )
    
    # Security: Check file extension
    if not is_allowed_extension(full_path.name):
        logger.warning(f"Blocked attempt to serve disallowed file type: {full_path.name}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="File type not allowed"
        )
    
    # Determine content type
    content_type, _ = mimetypes.guess_type(str(full_path))
    if not content_type:
        content_type = "application/octet-stream"
    
    # Return file response with streaming
    return FileResponse(
        path=str(full_path),
        media_type=content_type,
        filename=full_path.name
    )


@router.get(
    "/metadata/{file_path:path}",
    summary="Get Video Metadata",
    description="Returns parsed metadata JSON for a video file from its sidecar .info.json file.",
    responses={
        200: {"description": "Metadata retrieved successfully"},
        401: {"description": "Authentication required"},
        404: {"description": "Video or metadata not found"}
    }
)
async def get_video_metadata(request: Request, file_path: str):
    """Get metadata for a video file.
    
    Reads the .info.json sidecar file and returns parsed metadata.
    Returns curated fields useful for display, not the raw yt-dlp dump.
    """
    await require_auth(request)
    
    config = get_config()
    root_dir = Path(config.downloads.root_directory)
    
    # Decode URL-encoded path
    file_path = unquote(file_path)
    
    # Security: Validate path is within allowed directory
    if not is_safe_path(file_path, root_dir):
        logger.warning(f"Path traversal attempt blocked: {file_path}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Invalid path"
        )
    
    # Build full path to video file
    video_path = (root_dir / file_path).resolve()
    
    # Check video file exists
    if not video_path.exists() or not video_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video file not found"
        )
    
    # Read metadata from sidecar file
    metadata = read_video_metadata(video_path)
    
    if metadata is None:
        # Return minimal metadata from file info
        try:
            stat = video_path.stat()
            return {
                "has_full_metadata": False,
                "filename": video_path.name,
                "file_size": stat.st_size,
                "modified_at": int(stat.st_mtime),
            }
        except OSError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Could not read file information"
            )
    
    # Build comprehensive metadata response organized by categories
    # This structure is designed to be extensible for new platforms
    # The UI will iterate through categories and display available fields
    
    def get_first(*keys):
        """Get first non-None value from multiple possible keys"""
        for key in keys:
            val = metadata.get(key)
            if val is not None:
                return val
        return None
    
    return {
        "has_full_metadata": True,
        
        # Basic content information
        "basic": {
            "id": metadata.get("id"),
            "title": get_first("title", "fulltitle", "alt_title"),
            "description": metadata.get("description"),
            "webpage_url": get_first("webpage_url", "original_url", "url"),
            "duration": metadata.get("duration"),
            "duration_string": metadata.get("duration_string"),
            "upload_date": metadata.get("upload_date"),
            "timestamp": metadata.get("timestamp"),
            "release_date": metadata.get("release_date"),
            "release_year": metadata.get("release_year"),
        },
        
        # Creator/channel information
        "creator": {
            "uploader": get_first("uploader", "creator", "channel", "artist"),
            "uploader_id": get_first("uploader_id", "channel_id", "creator_id"),
            "uploader_url": get_first("uploader_url", "channel_url"),
            "channel": metadata.get("channel"),
            "channel_id": metadata.get("channel_id"),
            "channel_url": metadata.get("channel_url"),
            "channel_follower_count": metadata.get("channel_follower_count"),
        },
        
        # Engagement metrics
        "engagement": {
            "view_count": metadata.get("view_count"),
            "like_count": metadata.get("like_count"),
            "dislike_count": metadata.get("dislike_count"),
            "comment_count": metadata.get("comment_count"),
            "repost_count": metadata.get("repost_count"),
            "average_rating": metadata.get("average_rating"),
            "age_limit": metadata.get("age_limit"),
        },
        
        # Categorization and tags
        "categorization": {
            "categories": metadata.get("categories"),
            "tags": metadata.get("tags"),
            "genres": metadata.get("genres"),
            "playlist": metadata.get("playlist"),
            "playlist_index": metadata.get("playlist_index"),
            "chapter": metadata.get("chapter"),
            "chapter_number": metadata.get("chapter_number"),
        },
        
        # Audio/music specific (TikTok sounds, music videos, etc.)
        "audio": {
            "track": metadata.get("track"),
            "artist": metadata.get("artist"),
            "album": metadata.get("album"),
            "album_artist": metadata.get("album_artist"),
            "disc_number": metadata.get("disc_number"),
            "track_number": metadata.get("track_number"),
            "composer": metadata.get("composer"),
            "genre": metadata.get("genre"),
        },
        
        # Technical/platform info
        "technical": {
            "extractor": metadata.get("extractor"),
            "extractor_key": metadata.get("extractor_key"),
            "format": metadata.get("format"),
            "format_id": metadata.get("format_id"),
            "resolution": metadata.get("resolution"),
            "width": metadata.get("width"),
            "height": metadata.get("height"),
            "fps": metadata.get("fps"),
            "vcodec": metadata.get("vcodec"),
            "acodec": metadata.get("acodec"),
            "filesize": metadata.get("filesize"),
            "filesize_approx": metadata.get("filesize_approx"),
            "tbr": metadata.get("tbr"),
            "abr": metadata.get("abr"),
            "vbr": metadata.get("vbr"),
            "aspect_ratio": metadata.get("aspect_ratio"),
            "stretched_ratio": metadata.get("stretched_ratio"),
        },
        
        # Location data (if available)
        "location": {
            "location": metadata.get("location"),
            "latitude": metadata.get("latitude") if metadata.get("latitude") else None,
            "longitude": metadata.get("longitude") if metadata.get("longitude") else None,
        },
        
        # Live stream info
        "live": {
            "is_live": metadata.get("is_live"),
            "was_live": metadata.get("was_live"),
            "live_status": metadata.get("live_status"),
            "release_timestamp": metadata.get("release_timestamp"),
            "availability": metadata.get("availability"),
        },
        
        # Thumbnail
        "thumbnail": metadata.get("thumbnail"),
        
        # Subtitles info (just availability, not content)
        "has_subtitles": bool(metadata.get("subtitles") or metadata.get("automatic_captions")),
        "subtitle_languages": list(metadata.get("subtitles", {}).keys()) if metadata.get("subtitles") else [],
    }


@router.get(
    "/queue",
    summary="Get Download Queue",
    description="Returns pending, in-progress, and failed downloads from the database.",
    responses={
        200: {"description": "Queue retrieved successfully"},
        401: {"description": "Authentication required"},
        500: {"description": "Internal server error"}
    }
)
async def get_download_queue(request: Request):
    """Get download queue status from database
    
    Returns downloads that are:
    - pending: Waiting to be processed
    - downloading: Currently being downloaded
    - failed: Failed with an error
    """
    await require_auth(request)
    
    config = get_config()
    
    try:
        db = DatabaseService(db_path=config.database.path)
        
        # Get downloads by status
        pending = db.get_downloads_by_status(DownloadStatus.PENDING, limit=50)
        queued = db.get_downloads_by_status(DownloadStatus.QUEUED, limit=50)
        downloading = db.get_downloads_by_status(DownloadStatus.DOWNLOADING, limit=10)
        failed = db.get_downloads_by_status(DownloadStatus.FAILED, limit=50)
        
        # Combine pending and queued (they're essentially the same)
        all_pending = pending + queued
        
        # Get usernames for all downloads
        def get_username(user_id: int) -> str:
            user = db.get_user_by_id(user_id)
            return user.username if user else "unknown"
        
        # Format download for response
        def format_download(d):
            return {
                "id": d.id,
                "url": d.url,
                "status": d.status.value,
                "username": get_username(d.user_id),
                "genre": d.genre,
                "error_message": d.error_message,
                "retry_count": d.retry_count,
                "created_at": d.created_at,
                "created_formatted": format_timestamp(d.created_at),
                "started_at": d.started_at,
                "started_formatted": format_timestamp(d.started_at) if d.started_at else None,
            }
        
        db.close_connection()
        
        return {
            "downloading": [format_download(d) for d in downloading],
            "pending": [format_download(d) for d in all_pending],
            "failed": [format_download(d) for d in failed],
            "counts": {
                "downloading": len(downloading),
                "pending": len(all_pending),
                "failed": len(failed),
                "total": len(downloading) + len(all_pending) + len(failed)
            }
        }
    
    except Exception as e:
        logger.error(f"Error getting download queue: {e}", exc_info=True)
        return {
            "downloading": [],
            "pending": [],
            "failed": [],
            "counts": {"downloading": 0, "pending": 0, "failed": 0, "total": 0},
            "error": str(e)
        }


@router.post(
    "/retry/{download_id}",
    summary="Retry Failed Download",
    description="Reset a failed download back to pending status so it will be retried.",
    responses={
        200: {"description": "Download queued for retry"},
        401: {"description": "Authentication required"},
        404: {"description": "Download not found"},
        400: {"description": "Download is not in failed status"}
    }
)
async def retry_download(request: Request, download_id: str):
    """Retry a failed download
    
    Resets the download status from 'failed' back to 'pending' so the
    download worker will pick it up and try again.
    """
    await require_auth(request)
    
    config = get_config()
    
    try:
        db = DatabaseService(db_path=config.database.path)
        
        # Get the download
        download = db.get_download(download_id)
        
        if not download:
            db.close_connection()
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": "not_found", "message": "Download not found"}
            )
        
        # Check if it's actually failed
        if download.status != DownloadStatus.FAILED:
            db.close_connection()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "invalid_status",
                    "message": f"Cannot retry download with status '{download.status.value}'. Only failed downloads can be retried."
                }
            )
        
        # Reset to pending status
        db.update_download_status(
            download_id=download_id,
            status=DownloadStatus.PENDING,
            error_message=None  # Clear the error message
        )
        
        db.close_connection()
        
        logger.info(f"Download {download_id} queued for retry")
        
        return {
            "success": True,
            "message": "Download queued for retry",
            "download_id": download_id
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrying download {download_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "server_error", "message": str(e)}
        )


@router.get(
    "/browse",
    response_class=HTMLResponse,
    summary="Downloads Browser Page",
    description="HTML page for browsing downloaded videos.",
    responses={
        200: {"description": "HTML page"},
        302: {"description": "Redirect to login"},
        401: {"description": "Authentication required"}
    }
)
async def browse_downloads_page(request: Request):
    """Serve the downloads browser HTML page.
    
    Always requires authentication - redirects to login if not authenticated.
    """
    config = get_config()
    
    # Check if password is configured
    if not config.auth.password_hash:
        return HTMLResponse(content=_get_auth_required_html("no_password"))
    
    # Get token from cookie or header
    token = request.cookies.get("session_token") or extract_bearer_token(request)
    
    if not token:
        # Redirect to login with return URL
        from urllib.parse import urlencode
        login_url = "/api/v1/auth/login?" + urlencode({"redirect": str(request.url)})
        return RedirectResponse(url=login_url, status_code=status.HTTP_302_FOUND)
    
    # Validate session
    auth_service = get_auth_service(config.auth.session_timeout_hours)
    is_valid, session_id = auth_service.validate_session(token)
    
    if not is_valid:
        from urllib.parse import urlencode
        login_url = "/api/v1/auth/login?" + urlencode({"redirect": str(request.url)})
        return RedirectResponse(url=login_url, status_code=status.HTTP_302_FOUND)
    
    # User is authenticated, serve the page
    return HTMLResponse(content=_get_browse_html())


def _get_auth_required_html(reason: str) -> str:
    """Return HTML for authentication required page"""
    if reason == "no_password":
        message = "Authentication is not configured. Please set a password first."
        instruction = "Run: <code>python manage.py auth set-password</code>"
    else:
        message = "You must be logged in to access the Downloads Browser."
        instruction = '<a href="/api/v1/auth/login">Click here to login</a>'
    
    return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Authentication Required - Downloads Browser</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            color: #e0e0e0;
            padding: 20px;
        }}
        .container {{
            background: rgba(255, 255, 255, 0.05);
            border-radius: 16px;
            padding: 40px;
            max-width: 500px;
            text-align: center;
        }}
        h1 {{ font-size: 2rem; margin-bottom: 20px; color: #ff6b6b; }}
        p {{ margin-bottom: 20px; line-height: 1.6; }}
        code {{
            background: rgba(0, 0, 0, 0.3);
            padding: 4px 8px;
            border-radius: 4px;
            font-family: monospace;
        }}
        a {{
            color: #64b5f6;
            text-decoration: none;
        }}
        a:hover {{ text-decoration: underline; }}
        .back-link {{
            margin-top: 30px;
            display: block;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🔒 Authentication Required</h1>
        <p>{message}</p>
        <p>{instruction}</p>
        <a href="/" class="back-link">← Back to Home</a>
    </div>
</body>
</html>
"""


def _get_browse_html() -> str:
    """Return the main downloads browser HTML page"""
    return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Downloads Browser - Video Server</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            min-height: 100vh;
            color: #e0e0e0;
        }
        
        /* Header */
        .header {
            background: rgba(0, 0, 0, 0.3);
            padding: 20px;
            display: flex;
            align-items: center;
            gap: 20px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        }
        
        .back-btn {
            display: flex;
            align-items: center;
            gap: 6px;
            color: #e0e0e0;
            text-decoration: none;
            font-size: 14px;
            padding: 8px 16px;
            background: rgba(255, 255, 255, 0.1);
            border-radius: 8px;
            transition: all 0.2s;
        }
        
        .back-btn:hover {
            background: rgba(255, 255, 255, 0.2);
        }
        
        .header h1 {
            font-size: 1.5rem;
            flex: 1;
        }
        
        .stats {
            font-size: 0.9rem;
            color: #888;
        }
        
        /* Tabs */
        .tabs {
            display: flex;
            background: rgba(0, 0, 0, 0.2);
            padding: 0 20px;
        }
        
        .tab {
            padding: 15px 25px;
            background: none;
            border: none;
            color: #888;
            font-size: 15px;
            cursor: pointer;
            border-bottom: 3px solid transparent;
            transition: all 0.2s;
        }
        
        .tab:hover {
            color: #e0e0e0;
        }
        
        .tab.active {
            color: #64b5f6;
            border-bottom-color: #64b5f6;
        }
        
        /* Main Content */
        .content {
            padding: 20px;
            max-width: 1400px;
            margin: 0 auto;
        }
        
        .tab-content {
            display: none;
        }
        
        .tab-content.active {
            display: block;
        }
        
        /* Filters */
        .filters {
            display: flex;
            flex-wrap: wrap;
            gap: 15px;
            margin-bottom: 20px;
            padding: 15px;
            background: rgba(255, 255, 255, 0.05);
            border-radius: 12px;
        }
        
        .filter-group {
            display: flex;
            flex-direction: column;
            gap: 5px;
        }
        
        .filter-group label {
            font-size: 12px;
            color: #888;
            text-transform: uppercase;
        }
        
        .filter-group select,
        .filter-group input {
            padding: 8px 12px;
            background: rgba(0, 0, 0, 0.3);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 6px;
            color: #e0e0e0;
            font-size: 14px;
            min-width: 150px;
        }
        
        .filter-group select:focus,
        .filter-group input:focus {
            outline: none;
            border-color: #64b5f6;
        }
        
        .search-input {
            flex: 1;
            min-width: 200px;
        }
        
        /* Folder Tree */
        .folder-tree {
            background: rgba(255, 255, 255, 0.05);
            border-radius: 12px;
            padding: 20px;
        }
        
        .tree-item {
            margin-bottom: 5px;
        }
        
        .tree-header {
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 10px;
            background: rgba(255, 255, 255, 0.05);
            border-radius: 8px;
            cursor: pointer;
            transition: background 0.2s;
        }
        
        .tree-header:hover {
            background: rgba(255, 255, 255, 0.1);
        }
        
        .tree-icon {
            font-size: 1.2rem;
        }
        
        .tree-name {
            flex: 1;
            font-weight: 500;
        }
        
        .tree-count {
            font-size: 0.85rem;
            color: #888;
            background: rgba(0, 0, 0, 0.3);
            padding: 2px 8px;
            border-radius: 10px;
        }
        
        .tree-size {
            font-size: 0.85rem;
            color: #64b5f6;
        }
        
        .tree-children {
            display: none;
            margin-left: 30px;
            margin-top: 5px;
        }
        
        .tree-children.expanded {
            display: block;
        }
        
        .tree-file {
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 8px 10px;
            border-radius: 6px;
            cursor: pointer;
            transition: background 0.2s;
        }
        
        .tree-file:hover {
            background: rgba(255, 255, 255, 0.1);
        }
        
        .file-icon {
            font-size: 1.1rem;
        }
        
        .file-name {
            flex: 1;
            font-size: 0.9rem;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }
        
        .file-size {
            font-size: 0.8rem;
            color: #888;
        }
        
        /* Video Grid */
        .video-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
            gap: 20px;
        }
        
        .video-card {
            background: rgba(255, 255, 255, 0.05);
            border-radius: 12px;
            overflow: hidden;
            cursor: pointer;
            transition: transform 0.2s, box-shadow 0.2s;
        }
        
        .video-card:hover {
            transform: translateY(-4px);
            box-shadow: 0 8px 25px rgba(0, 0, 0, 0.3);
        }
        
        .video-thumb {
            height: 160px;
            background: linear-gradient(135deg, #2a2a4a 0%, #1a1a3a 100%);
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 3rem;
            overflow: hidden;
            position: relative;
        }
        
        .video-thumb-img {
            width: 100%;
            height: 100%;
            object-fit: cover;
        }
        
        .video-thumb-icon {
            font-size: 3rem;
        }
        
        .video-info {
            padding: 15px;
        }
        
        .video-title {
            font-size: 0.95rem;
            font-weight: 500;
            margin-bottom: 8px;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }
        
        .video-meta {
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
            font-size: 0.8rem;
            color: #888;
        }
        
        .video-badge {
            padding: 2px 8px;
            background: rgba(100, 181, 246, 0.2);
            color: #64b5f6;
            border-radius: 4px;
            font-size: 0.75rem;
        }
        
        /* Modal */
        .modal-overlay {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0, 0, 0, 0.85);
            z-index: 1000;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }
        
        .modal-overlay.active {
            display: flex;
        }
        
        .modal {
            background: #1a1a2e;
            border-radius: 16px;
            max-width: 900px;
            width: 100%;
            max-height: 90vh;
            overflow: hidden;
            display: flex;
            flex-direction: column;
        }
        
        .modal-header {
            display: flex;
            align-items: center;
            padding: 15px 20px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        }
        
        .modal-title {
            flex: 1;
            font-size: 1.1rem;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }
        
        .modal-close {
            background: none;
            border: none;
            color: #e0e0e0;
            font-size: 1.5rem;
            cursor: pointer;
            padding: 5px;
        }
        
        .modal-body {
            padding: 20px;
            overflow-y: auto;
        }
        
        .video-player-container {
            background: #000;
            border-radius: 8px;
            overflow: hidden;
            margin-bottom: 20px;
        }
        
        .video-player {
            width: 100%;
            max-height: 400px;
        }
        
        .video-details {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            max-height: 60vh;
            overflow-y: auto;
            padding-right: 10px;
        }
        
        .video-details::-webkit-scrollbar {
            width: 6px;
        }
        
        .video-details::-webkit-scrollbar-track {
            background: rgba(255, 255, 255, 0.05);
            border-radius: 3px;
        }
        
        .video-details::-webkit-scrollbar-thumb {
            background: rgba(255, 255, 255, 0.2);
            border-radius: 3px;
        }
        
        .detail-item {
            background: rgba(255, 255, 255, 0.05);
            padding: 12px;
            border-radius: 8px;
        }
        
        .detail-label {
            font-size: 0.75rem;
            color: #888;
            text-transform: uppercase;
            margin-bottom: 5px;
        }
        
        .detail-value {
            font-size: 0.95rem;
            word-break: break-word;
        }
        
        /* Metadata category styles */
        .meta-category {
            background: rgba(255, 255, 255, 0.02);
            border-radius: 8px;
            padding: 15px;
            margin-top: 10px;
        }
        
        .meta-category-header {
            font-size: 0.85rem;
            font-weight: 600;
            color: #888;
            margin-bottom: 12px;
            padding-bottom: 8px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        }
        
        .meta-category-content {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 12px;
        }
        
        .meta-category-content .detail-item {
            background: transparent;
            padding: 0;
        }
        
        .meta-tag {
            background: rgba(100, 181, 246, 0.15);
            color: #64b5f6;
            padding: 3px 10px;
            border-radius: 12px;
            margin: 2px;
            display: inline-block;
            font-size: 0.8rem;
        }
        
        .meta-description {
            white-space: pre-wrap;
            max-height: 200px;
            overflow-y: auto;
            line-height: 1.5;
            padding: 10px;
            background: rgba(0, 0, 0, 0.2);
            border-radius: 6px;
            font-size: 0.9rem;
        }
        
        .modal-actions {
            display: flex;
            gap: 10px;
            margin-top: 20px;
        }
        
        .btn {
            padding: 10px 20px;
            border: none;
            border-radius: 8px;
            font-size: 14px;
            cursor: pointer;
            transition: all 0.2s;
            text-decoration: none;
            display: inline-flex;
            align-items: center;
            gap: 8px;
        }
        
        .btn-primary {
            background: #64b5f6;
            color: #000;
        }
        
        .btn-primary:hover {
            background: #42a5f5;
        }
        
        .btn-secondary {
            background: rgba(255, 255, 255, 0.1);
            color: #e0e0e0;
        }
        
        .btn-secondary:hover {
            background: rgba(255, 255, 255, 0.2);
        }
        
        /* Loading */
        .loading {
            text-align: center;
            padding: 40px;
            color: #888;
        }
        
        .spinner {
            border: 3px solid rgba(255, 255, 255, 0.1);
            border-top: 3px solid #64b5f6;
            border-radius: 50%;
            width: 40px;
            height: 40px;
            animation: spin 1s linear infinite;
            margin: 0 auto 20px;
        }
        
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        
        /* Empty State */
        .empty-state {
            text-align: center;
            padding: 60px 20px;
            color: #888;
        }
        
        .empty-state .icon {
            font-size: 4rem;
            margin-bottom: 20px;
        }
        
        /* Pagination */
        .pagination {
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 10px;
            margin-top: 30px;
            padding: 20px;
        }
        
        .pagination button {
            padding: 8px 16px;
            background: rgba(255, 255, 255, 0.1);
            border: none;
            border-radius: 6px;
            color: #e0e0e0;
            cursor: pointer;
            transition: background 0.2s;
        }
        
        .pagination button:hover:not(:disabled) {
            background: rgba(255, 255, 255, 0.2);
        }
        
        .pagination button:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }
        
        .pagination .page-info {
            color: #888;
            font-size: 0.9rem;
        }
        
        /* Queue Badge */
        .queue-badge {
            background: #ff6b6b;
            color: white;
            font-size: 11px;
            padding: 2px 6px;
            border-radius: 10px;
            margin-left: 6px;
            font-weight: bold;
        }
        
        /* Queue Container */
        .queue-container {
            display: flex;
            flex-direction: column;
            gap: 20px;
        }
        
        .queue-section {
            background: rgba(255, 255, 255, 0.05);
            border-radius: 12px;
            overflow: hidden;
        }
        
        .queue-section-header {
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 15px 20px;
            background: rgba(0, 0, 0, 0.2);
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        }
        
        .queue-section-icon {
            font-size: 1.2rem;
        }
        
        .queue-section-title {
            flex: 1;
            font-weight: 600;
            font-size: 1rem;
        }
        
        .queue-section-count {
            background: rgba(255, 255, 255, 0.15);
            padding: 4px 10px;
            border-radius: 12px;
            font-size: 0.85rem;
        }
        
        .queue-list {
            padding: 10px;
        }
        
        .queue-empty {
            text-align: center;
            padding: 20px;
            color: #666;
            font-style: italic;
        }
        
        .queue-item {
            display: flex;
            align-items: flex-start;
            gap: 15px;
            padding: 15px;
            background: rgba(255, 255, 255, 0.03);
            border-radius: 8px;
            margin-bottom: 8px;
            transition: background 0.2s;
        }
        
        .queue-item:hover {
            background: rgba(255, 255, 255, 0.08);
        }
        
        .queue-item:last-child {
            margin-bottom: 0;
        }
        
        .queue-item-icon {
            font-size: 1.5rem;
            flex-shrink: 0;
        }
        
        .queue-item-icon.downloading {
            animation: pulse-download 1.5s ease-in-out infinite;
        }
        
        @keyframes pulse-download {
            0%, 100% { opacity: 1; transform: scale(1); }
            50% { opacity: 0.6; transform: scale(0.95); }
        }
        
        .queue-item-content {
            flex: 1;
            min-width: 0;
        }
        
        .queue-item-url {
            font-size: 0.9rem;
            color: #e0e0e0;
            word-break: break-all;
            margin-bottom: 6px;
        }
        
        .queue-item-meta {
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
            font-size: 0.8rem;
            color: #888;
        }
        
        .queue-item-badge {
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 0.75rem;
        }
        
        .queue-item-badge.genre {
            background: rgba(100, 181, 246, 0.2);
            color: #64b5f6;
        }
        
        .queue-item-badge.status-downloading {
            background: rgba(76, 175, 80, 0.2);
            color: #4caf50;
        }
        
        .queue-item-badge.status-pending {
            background: rgba(255, 193, 7, 0.2);
            color: #ffc107;
        }
        
        .queue-item-badge.status-failed {
            background: rgba(244, 67, 54, 0.2);
            color: #f44336;
        }
        
        .queue-item-error {
            margin-top: 8px;
            padding: 10px;
            background: rgba(244, 67, 54, 0.1);
            border: 1px solid rgba(244, 67, 54, 0.3);
            border-radius: 6px;
            font-size: 0.85rem;
            color: #ff8a80;
        }
        
        .queue-item-error-label {
            font-weight: 600;
            margin-bottom: 4px;
        }
        
        .queue-actions {
            margin-top: 20px;
            display: flex;
            justify-content: center;
        }
        
        .queue-item-actions {
            display: flex;
            gap: 8px;
            margin-top: 10px;
        }
        
        .btn-retry {
            padding: 6px 12px;
            background: rgba(76, 175, 80, 0.2);
            border: 1px solid rgba(76, 175, 80, 0.4);
            border-radius: 6px;
            color: #4caf50;
            font-size: 0.8rem;
            cursor: pointer;
            transition: all 0.2s;
            display: inline-flex;
            align-items: center;
            gap: 4px;
        }
        
        .btn-retry:hover {
            background: rgba(76, 175, 80, 0.3);
            border-color: rgba(76, 175, 80, 0.6);
        }
        
        .btn-retry:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }
    </style>
</head>
<body>
    <div class="header">
        <a href="/" class="back-btn">← Home</a>
        <h1>📁 Downloads Browser</h1>
        <div class="stats" id="total-stats">Loading...</div>
    </div>
    
    <div class="tabs">
        <button class="tab active" onclick="showTab('folders')">📂 Folder View</button>
        <button class="tab" onclick="showTab('videos')">🎬 All Videos</button>
        <button class="tab" onclick="showTab('queue')">⏳ Queue <span id="queue-badge" class="queue-badge" style="display: none;">0</span></button>
    </div>
    
    <div class="content">
        <!-- Folder Tab -->
        <div id="tab-folders" class="tab-content active">
            <div class="folder-tree" id="folder-tree">
                <div class="loading">
                    <div class="spinner"></div>
                    <p>Loading folder structure...</p>
                </div>
            </div>
        </div>
        
        <!-- Videos Tab -->
        <div id="tab-videos" class="tab-content">
            <div class="filters">
                <div class="filter-group">
                    <label>User</label>
                    <select id="filter-user" onchange="applyFilters()">
                        <option value="">All Users</option>
                    </select>
                </div>
                <div class="filter-group">
                    <label>Genre</label>
                    <select id="filter-genre" onchange="applyFilters()">
                        <option value="">All Genres</option>
                        <option value="tiktok">TikTok</option>
                        <option value="instagram">Instagram</option>
                        <option value="youtube">YouTube</option>
                        <option value="unknown">Unknown</option>
                    </select>
                </div>
                <div class="filter-group">
                    <label>Sort By</label>
                    <select id="filter-sort" onchange="applyFilters()">
                        <option value="newest">Newest First</option>
                        <option value="oldest">Oldest First</option>
                        <option value="largest">Largest First</option>
                        <option value="smallest">Smallest First</option>
                        <option value="name">Name (A-Z)</option>
                    </select>
                </div>
                <div class="filter-group search-input">
                    <label>Search</label>
                    <input type="text" id="filter-search" placeholder="Search filename..." oninput="debounceSearch()">
                </div>
            </div>
            
            <div class="video-grid" id="video-grid">
                <div class="loading">
                    <div class="spinner"></div>
                    <p>Loading videos...</p>
                </div>
            </div>
            
            <div class="pagination" id="pagination" style="display: none;">
                <button onclick="prevPage()" id="btn-prev">← Previous</button>
                <span class="page-info" id="page-info">Page 1</span>
                <button onclick="nextPage()" id="btn-next">Next →</button>
            </div>
        </div>
        
        <!-- Queue Tab -->
        <div id="tab-queue" class="tab-content">
            <div class="queue-container">
                <!-- Downloading Section -->
                <div class="queue-section" id="section-downloading">
                    <div class="queue-section-header">
                        <span class="queue-section-icon">⬇️</span>
                        <span class="queue-section-title">Downloading</span>
                        <span class="queue-section-count" id="count-downloading">0</span>
                    </div>
                    <div class="queue-list" id="list-downloading">
                        <div class="queue-empty">No active downloads</div>
                    </div>
                </div>
                
                <!-- Pending Section -->
                <div class="queue-section" id="section-pending">
                    <div class="queue-section-header">
                        <span class="queue-section-icon">⏳</span>
                        <span class="queue-section-title">Pending</span>
                        <span class="queue-section-count" id="count-pending">0</span>
                    </div>
                    <div class="queue-list" id="list-pending">
                        <div class="queue-empty">No pending downloads</div>
                    </div>
                </div>
                
                <!-- Failed Section -->
                <div class="queue-section" id="section-failed">
                    <div class="queue-section-header">
                        <span class="queue-section-icon">❌</span>
                        <span class="queue-section-title">Failed</span>
                        <span class="queue-section-count" id="count-failed">0</span>
                    </div>
                    <div class="queue-list" id="list-failed">
                        <div class="queue-empty">No failed downloads</div>
                    </div>
                </div>
            </div>
            
            <div class="queue-actions">
                <button class="btn btn-secondary" onclick="loadQueue()">🔄 Refresh</button>
            </div>
        </div>
    </div>
    
    <!-- Video Modal -->
    <div class="modal-overlay" id="modal-overlay" onclick="closeModalOnOverlay(event)">
        <div class="modal">
            <div class="modal-header">
                <span class="modal-title" id="modal-title">Video</span>
                <button class="modal-close" onclick="closeModal()">×</button>
            </div>
            <div class="modal-body">
                <div class="video-player-container">
                    <video class="video-player" id="video-player" controls>
                        Your browser does not support video playback.
                    </video>
                </div>
                <div class="video-details" id="video-details"></div>
                <div class="modal-actions">
                    <a id="download-btn" class="btn btn-primary" download>
                        ⬇️ Download
                    </a>
                    <button class="btn btn-secondary" onclick="closeModal()">Close</button>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        // State
        let folderData = null;
        let videosData = [];
        let currentPage = 0;
        const pageSize = 30;
        let searchTimeout = null;
        
        // Initialize
        document.addEventListener('DOMContentLoaded', () => {
            loadFolderStructure();
            loadVideos();
            loadQueue();
            // Auto-refresh queue every 5 seconds
            setInterval(loadQueue, 5000);
        });
        
        // Tab switching
        function showTab(tabName) {
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
            
            document.querySelector(`[onclick="showTab('${tabName}')"]`).classList.add('active');
            document.getElementById(`tab-${tabName}`).classList.add('active');
        }
        
        // Load folder structure
        async function loadFolderStructure() {
            try {
                const response = await fetch('/api/v1/downloads/structure');
                if (!response.ok) throw new Error('Failed to load');
                
                folderData = await response.json();
                renderFolderTree();
                updateStats();
                populateUserFilter();
            } catch (error) {
                document.getElementById('folder-tree').innerHTML = `
                    <div class="empty-state">
                        <div class="icon">⚠️</div>
                        <p>Error loading folder structure: ${error.message}</p>
                    </div>
                `;
            }
        }
        
        // Render folder tree
        function renderFolderTree() {
            const container = document.getElementById('folder-tree');
            
            if (!folderData.users || folderData.users.length === 0) {
                container.innerHTML = `
                    <div class="empty-state">
                        <div class="icon">📭</div>
                        <p>No downloads yet</p>
                        <p style="font-size: 0.9rem; margin-top: 10px;">Downloaded videos will appear here</p>
                    </div>
                `;
                return;
            }
            
            let html = '';
            for (const user of folderData.users) {
                html += `
                    <div class="tree-item">
                        <div class="tree-header" onclick="toggleTree(this)">
                            <span class="tree-icon">👤</span>
                            <span class="tree-name">${escapeHtml(user.username)}</span>
                            <span class="tree-count">${user.total_videos} files</span>
                            <span class="tree-size">${user.total_size_formatted}</span>
                        </div>
                        <div class="tree-children">
                            ${renderGenres(user)}
                        </div>
                    </div>
                `;
            }
            
            container.innerHTML = html;
        }
        
        function renderGenres(user) {
            let html = '';
            const genreIcons = {
                'tiktok': '🎵',
                'instagram': '📷',
                'youtube': '▶️',
                'pdf': '📄',
                'ebook': '📚',
                'unknown': '❓'
            };
            
            for (const [genre, data] of Object.entries(user.genres)) {
                const icon = genreIcons[genre] || '📁';
                html += `
                    <div class="tree-item">
                        <div class="tree-header" onclick="toggleTree(this); loadGenreFiles('${user.username}', '${genre}', this)">
                            <span class="tree-icon">${icon}</span>
                            <span class="tree-name">${genre}</span>
                            <span class="tree-count">${data.count} files</span>
                            <span class="tree-size">${data.size_formatted}</span>
                        </div>
                        <div class="tree-children" data-loaded="false"></div>
                    </div>
                `;
            }
            return html;
        }
        
        function toggleTree(header) {
            const children = header.nextElementSibling;
            children.classList.toggle('expanded');
        }
        
        async function loadGenreFiles(username, genre, header) {
            const children = header.nextElementSibling;
            
            // Only load once
            if (children.dataset.loaded === 'true') return;
            children.dataset.loaded = 'true';
            
            children.innerHTML = '<div class="loading" style="padding: 10px;"><p>Loading...</p></div>';
            
            try {
                const response = await fetch(`/api/v1/downloads/videos?username=${username}&genre=${genre}&limit=100`);
                const data = await response.json();
                
                if (data.videos.length === 0) {
                    children.innerHTML = '<p style="padding: 10px; color: #888;">No files</p>';
                    return;
                }
                
                const extIcons = {
                    '.mp4': '🎬', '.webm': '🎬', '.mov': '🎬', '.avi': '🎬', '.mkv': '🎬',
                    '.mp3': '🎵', '.wav': '🎵',
                    '.pdf': '📄', '.epub': '📚'
                };
                
                let html = '';
                for (const video of data.videos) {
                    const icon = extIcons[video.extension] || '📄';
                    html += `
                        <div class="tree-file" onclick="openVideo(${JSON.stringify(video).replace(/"/g, '&quot;')})">
                            <span class="file-icon">${icon}</span>
                            <span class="file-name">${escapeHtml(video.filename)}</span>
                            <span class="file-size">${video.size_formatted}</span>
                        </div>
                    `;
                }
                children.innerHTML = html;
            } catch (error) {
                children.innerHTML = `<p style="padding: 10px; color: #ff6b6b;">Error: ${error.message}</p>`;
            }
        }
        
        // Load videos list
        async function loadVideos() {
            const grid = document.getElementById('video-grid');
            grid.innerHTML = '<div class="loading"><div class="spinner"></div><p>Loading videos...</p></div>';
            
            const params = new URLSearchParams({
                limit: pageSize,
                offset: currentPage * pageSize,
                sort: document.getElementById('filter-sort').value
            });
            
            const user = document.getElementById('filter-user').value;
            const genre = document.getElementById('filter-genre').value;
            const search = document.getElementById('filter-search').value;
            
            if (user) params.append('username', user);
            if (genre) params.append('genre', genre);
            if (search) params.append('search', search);
            
            try {
                const response = await fetch(`/api/v1/downloads/videos?${params}`);
                const data = await response.json();
                
                videosData = data.videos;
                renderVideoGrid(data);
                updatePagination(data);
            } catch (error) {
                grid.innerHTML = `
                    <div class="empty-state">
                        <div class="icon">⚠️</div>
                        <p>Error loading videos: ${error.message}</p>
                    </div>
                `;
            }
        }
        
        function renderVideoGrid(data) {
            const grid = document.getElementById('video-grid');
            
            if (data.videos.length === 0) {
                grid.innerHTML = `
                    <div class="empty-state" style="grid-column: 1 / -1;">
                        <div class="icon">📭</div>
                        <p>No videos found</p>
                        <p style="font-size: 0.9rem; margin-top: 10px;">Try adjusting your filters</p>
                    </div>
                `;
                return;
            }
            
            const thumbIcons = {
                '.mp4': '🎬', '.webm': '🎬', '.mov': '🎬', '.avi': '🎬', '.mkv': '🎬', '.m4v': '🎬',
                '.mp3': '🎵', '.wav': '🎵', '.m4a': '🎵',
                '.pdf': '📄', '.epub': '📚'
            };
            
            let html = '';
            for (const video of data.videos) {
                const icon = thumbIcons[video.extension] || '📄';
                
                // Use actual thumbnail if available, otherwise fall back to emoji icon
                const thumbHtml = video.thumbnail_path
                    ? `<img src="/api/v1/downloads/stream/${encodeURIComponent(video.thumbnail_path)}" 
                           alt="" class="video-thumb-img" loading="lazy" 
                           onerror="this.parentElement.innerHTML='<div class=\\'video-thumb-icon\\'>${icon}</div>'">`
                    : `<div class="video-thumb-icon">${icon}</div>`;
                
                html += `
                    <div class="video-card" onclick="openVideo(${JSON.stringify(video).replace(/"/g, '&quot;')})">
                        <div class="video-thumb">${thumbHtml}</div>
                        <div class="video-info">
                            <div class="video-title" title="${escapeHtml(video.filename)}">${escapeHtml(video.filename)}</div>
                            <div class="video-meta">
                                <span class="video-badge">${video.genre}</span>
                                <span>${video.size_formatted}</span>
                                <span>${video.modified_formatted}</span>
                            </div>
                        </div>
                    </div>
                `;
            }
            
            grid.innerHTML = html;
        }
        
        function updatePagination(data) {
            const pagination = document.getElementById('pagination');
            const pageInfo = document.getElementById('page-info');
            const prevBtn = document.getElementById('btn-prev');
            const nextBtn = document.getElementById('btn-next');
            
            if (data.total <= pageSize) {
                pagination.style.display = 'none';
                return;
            }
            
            pagination.style.display = 'flex';
            
            const totalPages = Math.ceil(data.total / pageSize);
            pageInfo.textContent = `Page ${currentPage + 1} of ${totalPages} (${data.total} videos)`;
            
            prevBtn.disabled = currentPage === 0;
            nextBtn.disabled = !data.has_more;
        }
        
        function prevPage() {
            if (currentPage > 0) {
                currentPage--;
                loadVideos();
            }
        }
        
        function nextPage() {
            currentPage++;
            loadVideos();
        }
        
        // Filters
        function applyFilters() {
            currentPage = 0;
            loadVideos();
        }
        
        function debounceSearch() {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(() => {
                currentPage = 0;
                loadVideos();
            }, 300);
        }
        
        function populateUserFilter() {
            const select = document.getElementById('filter-user');
            if (folderData && folderData.users) {
                for (const user of folderData.users) {
                    const option = document.createElement('option');
                    option.value = user.username;
                    option.textContent = user.username;
                    select.appendChild(option);
                }
            }
        }
        
        function updateStats() {
            if (folderData) {
                document.getElementById('total-stats').textContent = 
                    `${folderData.total_videos} videos • ${folderData.total_size_formatted}`;
            }
        }
        
        // Modal
        async function openVideo(video) {
            const modal = document.getElementById('modal-overlay');
            const player = document.getElementById('video-player');
            const title = document.getElementById('modal-title');
            const details = document.getElementById('video-details');
            const downloadBtn = document.getElementById('download-btn');
            
            const streamUrl = `/api/v1/downloads/stream/${encodeURIComponent(video.path)}`;
            
            title.textContent = video.filename;
            
            // Check if it's a video file
            const videoExts = ['.mp4', '.webm', '.mov', '.m4v'];
            if (videoExts.includes(video.extension)) {
                player.style.display = 'block';
                player.src = streamUrl;
            } else {
                player.style.display = 'none';
                player.src = '';
            }
            
            downloadBtn.href = streamUrl;
            downloadBtn.download = video.filename;
            
            // Show basic info first, then load rich metadata
            renderBasicDetails(video, details);
            modal.classList.add('active');
            
            // Fetch rich metadata if available
            if (video.has_metadata) {
                try {
                    const response = await fetch(`/api/v1/downloads/metadata/${encodeURIComponent(video.path)}`);
                    if (response.ok) {
                        const metadata = await response.json();
                        if (metadata.has_full_metadata) {
                            renderRichDetails(video, metadata, details);
                        }
                    }
                } catch (e) {
                    console.log('Could not load metadata:', e);
                    // Keep basic details
                }
            }
        }
        
        function renderBasicDetails(video, container) {
            container.innerHTML = `
                <div class="detail-item">
                    <div class="detail-label">Filename</div>
                    <div class="detail-value">${escapeHtml(video.filename)}</div>
                </div>
                <div class="detail-item">
                    <div class="detail-label">User</div>
                    <div class="detail-value">${escapeHtml(video.username)}</div>
                </div>
                <div class="detail-item">
                    <div class="detail-label">Genre</div>
                    <div class="detail-value">${escapeHtml(video.genre)}</div>
                </div>
                <div class="detail-item">
                    <div class="detail-label">Size</div>
                    <div class="detail-value">${video.size_formatted}</div>
                </div>
                <div class="detail-item">
                    <div class="detail-label">Modified</div>
                    <div class="detail-value">${video.modified_formatted}</div>
                </div>
            `;
        }
        
        function renderRichDetails(video, meta, container) {
            // Metadata field configuration - easily extensible for new platforms
            // Format: { key: { label, format, wide } }
            // format: 'text', 'number', 'date', 'duration', 'url', 'tags', 'resolution'
            const fieldConfig = {
                // Basic fields
                title: { label: 'Title', format: 'text', wide: true },
                description: { label: 'Description', format: 'description', wide: true },
                webpage_url: { label: 'Original URL', format: 'url', wide: true },
                duration: { label: 'Duration', format: 'duration' },
                upload_date: { label: 'Upload Date', format: 'date' },
                release_date: { label: 'Release Date', format: 'date' },
                release_year: { label: 'Release Year', format: 'text' },
                
                // Creator fields
                uploader: { label: 'Creator', format: 'text' },
                uploader_url: { label: 'Creator URL', format: 'url' },
                channel: { label: 'Channel', format: 'text' },
                channel_url: { label: 'Channel URL', format: 'url' },
                channel_follower_count: { label: 'Followers', format: 'number' },
                
                // Engagement fields
                view_count: { label: 'Views', format: 'number' },
                like_count: { label: 'Likes', format: 'number' },
                dislike_count: { label: 'Dislikes', format: 'number' },
                comment_count: { label: 'Comments', format: 'number' },
                repost_count: { label: 'Reposts', format: 'number' },
                average_rating: { label: 'Rating', format: 'text' },
                age_limit: { label: 'Age Limit', format: 'text' },
                
                // Categorization fields
                categories: { label: 'Categories', format: 'tags' },
                tags: { label: 'Tags', format: 'tags', wide: true },
                genres: { label: 'Genres', format: 'tags' },
                playlist: { label: 'Playlist', format: 'text' },
                
                // Audio fields
                track: { label: 'Track', format: 'text' },
                artist: { label: 'Artist', format: 'text' },
                album: { label: 'Album', format: 'text' },
                composer: { label: 'Composer', format: 'text' },
                genre: { label: 'Genre', format: 'text' },
                
                // Technical fields
                extractor: { label: 'Platform', format: 'text' },
                format: { label: 'Format', format: 'text' },
                resolution: { label: 'Resolution', format: 'resolution' },
                fps: { label: 'FPS', format: 'text' },
                vcodec: { label: 'Video Codec', format: 'text' },
                acodec: { label: 'Audio Codec', format: 'text' },
                
                // Location
                location: { label: 'Location', format: 'text' },
                
                // Live
                live_status: { label: 'Live Status', format: 'text' },
                availability: { label: 'Availability', format: 'text' },
            };
            
            // Formatters for different data types
            const formatters = {
                text: (v) => escapeHtml(String(v)),
                number: (v) => Number(v).toLocaleString(),
                date: (v) => {
                    if (!v) return null;
                    if (typeof v === 'string' && v.length === 8) {
                        return `${v.slice(0,4)}-${v.slice(4,6)}-${v.slice(6,8)}`;
                    }
                    return v;
                },
                duration: (v) => {
                    if (!v) return null;
                    const hrs = Math.floor(v / 3600);
                    const mins = Math.floor((v % 3600) / 60);
                    const secs = Math.floor(v % 60);
                    if (hrs > 0) return `${hrs}h ${mins}m ${secs}s`;
                    if (mins > 0) return `${mins}m ${secs}s`;
                    return `${secs}s`;
                },
                url: (v) => `<a href="${escapeHtml(v)}" target="_blank" rel="noopener" style="color: #64b5f6; word-break: break-all;">${escapeHtml(v)}</a>`,
                tags: (v) => {
                    if (!Array.isArray(v) || v.length === 0) return null;
                    return v.slice(0, 15).map(t => 
                        `<span class="meta-tag">${escapeHtml(t)}</span>`
                    ).join('') + (v.length > 15 ? `<span class="meta-tag">+${v.length - 15} more</span>` : '');
                },
                description: (v) => {
                    if (!v) return null;
                    const escaped = escapeHtml(v);
                    return `<div class="meta-description">${escaped}</div>`;
                },
                resolution: (v, data) => {
                    if (data.width && data.height) {
                        return `${data.width}x${data.height}`;
                    }
                    return v || null;
                }
            };
            
            // Category display configuration
            const categories = [
                { key: 'basic', title: 'Content Info', icon: '📄', fields: ['title', 'description', 'duration', 'upload_date', 'release_date', 'webpage_url'] },
                { key: 'creator', title: 'Creator', icon: '👤', fields: ['uploader', 'channel', 'uploader_url', 'channel_url', 'channel_follower_count'] },
                { key: 'engagement', title: 'Engagement', icon: '📊', fields: ['view_count', 'like_count', 'dislike_count', 'comment_count', 'repost_count', 'average_rating'] },
                { key: 'categorization', title: 'Categories', icon: '🏷️', fields: ['categories', 'tags', 'genres', 'playlist'] },
                { key: 'audio', title: 'Audio/Music', icon: '🎵', fields: ['track', 'artist', 'album', 'composer', 'genre'] },
                { key: 'technical', title: 'Technical', icon: '⚙️', fields: ['extractor', 'format', 'resolution', 'fps', 'vcodec', 'acodec'] },
                { key: 'location', title: 'Location', icon: '📍', fields: ['location'] },
                { key: 'live', title: 'Live Info', icon: '🔴', fields: ['live_status', 'availability'] },
            ];
            
            // Helper to get value from nested category data
            function getValue(categoryKey, fieldKey) {
                const category = meta[categoryKey];
                if (!category || typeof category !== 'object') return null;
                return category[fieldKey];
            }
            
            // Render field item
            function renderField(fieldKey, value, categoryData) {
                if (value === null || value === undefined || value === '' || 
                    (Array.isArray(value) && value.length === 0)) {
                    return '';
                }
                
                const config = fieldConfig[fieldKey] || { label: fieldKey, format: 'text' };
                const formatter = formatters[config.format] || formatters.text;
                const formatted = formatter(value, categoryData || {});
                
                if (!formatted) return '';
                
                const wideClass = config.wide ? ' style="grid-column: 1 / -1;"' : '';
                return `<div class="detail-item"${wideClass}>
                    <div class="detail-label">${config.label}</div>
                    <div class="detail-value">${formatted}</div>
                </div>`;
            }
            
            let html = '';
            
            // Add file info at the top
            html += `<div class="detail-item">
                <div class="detail-label">File Size</div>
                <div class="detail-value">${video.size_formatted}</div>
            </div>`;
            html += `<div class="detail-item">
                <div class="detail-label">Downloaded</div>
                <div class="detail-value">${video.modified_formatted}</div>
            </div>`;
            
            // Render each category with content
            for (const cat of categories) {
                const categoryData = meta[cat.key];
                if (!categoryData || typeof categoryData !== 'object') continue;
                
                // Check if category has any non-empty values
                let categoryHtml = '';
                for (const fieldKey of cat.fields) {
                    const value = categoryData[fieldKey];
                    categoryHtml += renderField(fieldKey, value, categoryData);
                }
                
                if (categoryHtml) {
                    html += `<div class="meta-category" style="grid-column: 1 / -1;">
                        <div class="meta-category-header">${cat.icon} ${cat.title}</div>
                        <div class="meta-category-content">${categoryHtml}</div>
                    </div>`;
                }
            }
            
            // Subtitle info
            if (meta.has_subtitles && meta.subtitle_languages && meta.subtitle_languages.length > 0) {
                html += `<div class="detail-item" style="grid-column: 1 / -1;">
                    <div class="detail-label">Subtitles Available</div>
                    <div class="detail-value">${meta.subtitle_languages.map(l => `<span class="meta-tag">${escapeHtml(l)}</span>`).join('')}</div>
                </div>`;
            }
            
            container.innerHTML = html;
        }
        
        function closeModal() {
            const modal = document.getElementById('modal-overlay');
            const player = document.getElementById('video-player');
            
            player.pause();
            player.src = '';
            modal.classList.remove('active');
        }
        
        function closeModalOnOverlay(event) {
            if (event.target.id === 'modal-overlay') {
                closeModal();
            }
        }
        
        // Queue functions
        let queueData = null;
        
        async function loadQueue() {
            try {
                const response = await fetch('/api/v1/downloads/queue');
                if (!response.ok) throw new Error('Failed to load queue');
                
                queueData = await response.json();
                renderQueue();
                updateQueueBadge();
            } catch (error) {
                console.error('Error loading queue:', error);
            }
        }
        
        function renderQueue() {
            if (!queueData) return;
            
            // Render downloading
            renderQueueSection('downloading', queueData.downloading, '⬇️');
            
            // Render pending
            renderQueueSection('pending', queueData.pending, '⏳');
            
            // Render failed
            renderQueueSection('failed', queueData.failed, '❌');
            
            // Update counts
            document.getElementById('count-downloading').textContent = queueData.counts.downloading;
            document.getElementById('count-pending').textContent = queueData.counts.pending;
            document.getElementById('count-failed').textContent = queueData.counts.failed;
        }
        
        function renderQueueSection(section, items, defaultIcon) {
            const container = document.getElementById(`list-${section}`);
            
            if (!items || items.length === 0) {
                const emptyMessages = {
                    'downloading': 'No active downloads',
                    'pending': 'No pending downloads',
                    'failed': 'No failed downloads'
                };
                container.innerHTML = `<div class="queue-empty">${emptyMessages[section]}</div>`;
                return;
            }
            
            const genreIcons = {
                'tiktok': '🎵',
                'instagram': '📷',
                'youtube': '▶️',
                'pdf': '📄',
                'ebook': '📚',
                'unknown': '❓'
            };
            
            let html = '';
            for (const item of items) {
                const icon = genreIcons[item.genre] || defaultIcon;
                const iconClass = section === 'downloading' ? 'downloading' : '';
                
                // Truncate URL for display
                let displayUrl = item.url;
                if (displayUrl.length > 80) {
                    displayUrl = displayUrl.substring(0, 77) + '...';
                }
                
                html += `
                    <div class="queue-item">
                        <div class="queue-item-icon ${iconClass}">${icon}</div>
                        <div class="queue-item-content">
                            <div class="queue-item-url" title="${escapeHtml(item.url)}">${escapeHtml(displayUrl)}</div>
                            <div class="queue-item-meta">
                                <span class="queue-item-badge genre">${item.genre}</span>
                                <span class="queue-item-badge status-${section}">${item.status}</span>
                                <span>👤 ${escapeHtml(item.username)}</span>
                                <span>📅 ${item.created_formatted}</span>
                                ${item.retry_count > 0 ? `<span>🔄 ${item.retry_count} retries</span>` : ''}
                            </div>
                            ${item.error_message ? `
                                <div class="queue-item-error">
                                    <div class="queue-item-error-label">Error:</div>
                                    ${escapeHtml(item.error_message)}
                                </div>
                            ` : ''}
                            ${section === 'failed' ? `
                                <div class="queue-item-actions">
                                    <button class="btn-retry" onclick="retryDownload('${item.id}')" id="retry-${item.id}">
                                        🔄 Retry
                                    </button>
                                </div>
                            ` : ''}
                        </div>
                    </div>
                `;
            }
            
            container.innerHTML = html;
        }
        
        async function retryDownload(downloadId) {
            const btn = document.getElementById(`retry-${downloadId}`);
            if (btn) {
                btn.disabled = true;
                btn.innerHTML = '⏳ Retrying...';
            }
            
            try {
                const response = await fetch(`/api/v1/downloads/retry/${downloadId}`, {
                    method: 'POST'
                });
                
                if (!response.ok) {
                    const data = await response.json();
                    throw new Error(data.detail?.message || 'Failed to retry');
                }
                
                // Reload queue to show updated status
                await loadQueue();
                
            } catch (error) {
                console.error('Error retrying download:', error);
                if (btn) {
                    btn.disabled = false;
                    btn.innerHTML = '❌ Failed - Click to retry';
                }
                alert('Failed to retry download: ' + error.message);
            }
        }
        
        function updateQueueBadge() {
            const badge = document.getElementById('queue-badge');
            if (queueData && queueData.counts.total > 0) {
                badge.textContent = queueData.counts.total;
                badge.style.display = 'inline';
            } else {
                badge.style.display = 'none';
            }
        }
        
        // Utility
        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }
        
        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                closeModal();
            }
        });
    </script>
</body>
</html>
"""
