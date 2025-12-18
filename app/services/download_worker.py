"""Download Worker Service

Background worker that processes video download queue using yt-dlp.
Monitors database for pending downloads and processes them asynchronously.
"""

import logging
import time
import threading
import os
import shutil
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
from datetime import datetime

import yt_dlp

from app.services.database_service import DatabaseService
from app.services.genre_detector import GenreDetector
from app.services.user_service import UserService
from app.models.database import Download, DownloadStatus, User
from app.core.config import get_config

logger = logging.getLogger(__name__)


def _get_ffmpeg_path() -> Tuple[bool, Optional[str]]:
    """Get ffmpeg path, checking system PATH first, then imageio-ffmpeg bundle.
    
    Returns:
        Tuple of (is_available, path_or_none)
        - If system ffmpeg found: (True, None) - yt-dlp will find it automatically
        - If imageio-ffmpeg found: (True, "/path/to/ffmpeg") - need to tell yt-dlp
        - If neither found: (False, None)
    """
    # First check system PATH
    if shutil.which('ffmpeg') is not None:
        return True, None
    
    # Try imageio-ffmpeg bundled binary
    try:
        import imageio_ffmpeg
        ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()
        if ffmpeg_path and os.path.exists(ffmpeg_path):
            logger.info(f"Using bundled ffmpeg from imageio-ffmpeg: {ffmpeg_path}")
            return True, ffmpeg_path
    except ImportError:
        pass
    except Exception as e:
        logger.debug(f"imageio-ffmpeg check failed: {e}")
    
    return False, None


class DownloadWorker:
    """Background worker for processing video downloads
    
    This worker:
    1. Polls database for pending downloads
    2. Downloads videos using yt-dlp
    3. Organizes files by username and genre
    4. Updates database with status and progress
    5. Handles errors and retries
    """
    
    def __init__(self, db_path: str, root_dir: str):
        """Initialize download worker
        
        Args:
            db_path: Path to SQLite database
            root_dir: Root directory for all user folders
        """
        self.db_path = db_path
        self.root_dir = root_dir
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.poll_interval = 5  # seconds between queue checks
        
        # Create root directory if it doesn't exist
        Path(root_dir).mkdir(parents=True, exist_ok=True)
        
        # Initialize user service
        self.user_service = UserService(root_dir)
        
        logger.info(f"DownloadWorker initialized: root_dir={root_dir}")
    
    def start(self):
        """Start the worker thread"""
        if self.running:
            logger.warning("Worker already running")
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._worker_loop, daemon=True)
        self.thread.start()
        logger.info("Download worker started")
    
    def stop(self):
        """Stop the worker thread"""
        if not self.running:
            return
        
        logger.info("Stopping download worker...")
        self.running = False
        
        if self.thread:
            self.thread.join(timeout=10)
        
        logger.info("Download worker stopped")
    
    def _worker_loop(self):
        """Main worker loop - polls for pending downloads"""
        logger.info("Worker loop started")
        
        while self.running:
            try:
                # Get next pending download
                db = DatabaseService(db_path=self.db_path)
                pending_downloads = db.get_downloads_by_status(DownloadStatus.PENDING)
                db.close_connection()
                
                if pending_downloads:
                    # Process first pending download
                    download = pending_downloads[0]
                    logger.info(f"Processing download: {download.id}")
                    self._process_download(download)
                else:
                    # No pending downloads, sleep
                    time.sleep(self.poll_interval)
            
            except Exception as e:
                logger.error(f"Error in worker loop: {e}", exc_info=True)
                time.sleep(self.poll_interval)
    
    def _process_download(self, download: Download):
        """Process a single download
        
        Args:
            download: Download object to process
        """
        download_id = download.id
        
        try:
            # Get user info for folder structure
            db = DatabaseService(db_path=self.db_path)
            user = db.get_user_by_id(download.user_id)
            
            if not user:
                logger.error(f"User ID {download.user_id} not found for download {download_id}")
                db.update_download_status(
                    download_id=download_id,
                    status=DownloadStatus.FAILED,
                    error_message="User not found"
                )
                db.close_connection()
                return
            
            # Update status to downloading
            db.update_download_status(
                download_id=download_id,
                status=DownloadStatus.DOWNLOADING,
                started_at=int(time.time())
            )
            db.close_connection()
            
            logger.info(f"Starting download {download_id}: {download.url} (user: {user.username}, genre: {download.genre})")
            
            # Download video using yt-dlp
            result = self._download_video(download.url, download_id, user, download.genre)
            
            if result['success']:
                # Update genre if yt-dlp provided better detection
                final_genre = result.get('detected_genre', download.genre)
                
                # Update status to completed
                db = DatabaseService(db_path=self.db_path)
                db.update_download_status(
                    download_id=download_id,
                    status=DownloadStatus.COMPLETED,
                    completed_at=int(time.time()),
                    filename=result['filename'],
                    file_size=result['file_size'],
                    genre=final_genre if final_genre != download.genre else None,
                    genre_detection_error=result.get('genre_detection_error')
                )
                db.close_connection()
                
                logger.info(
                    f"Download completed {download_id}: "
                    f"{result['filename']} ({result['file_size']} bytes)"
                )
            else:
                # Update status to failed
                db = DatabaseService(db_path=self.db_path)
                db.update_download_status(
                    download_id=download_id,
                    status=DownloadStatus.FAILED,
                    error_message=result['error']
                )
                db.close_connection()
                
                logger.error(f"Download failed {download_id}: {result['error']}")
        
        except Exception as e:
            logger.error(f"Error processing download {download_id}: {e}", exc_info=True)
            
            # Update status to failed
            try:
                db = DatabaseService(db_path=self.db_path)
                db.update_download_status(
                    download_id=download_id,
                    status=DownloadStatus.FAILED,
                    error_message=str(e)
                )
                db.close_connection()
            except Exception as db_error:
                logger.error(f"Failed to update error status: {db_error}")
    
    def _download_video(self, url: str, download_id: str, user: User, genre: str) -> Dict[str, Any]:
        """Download video using yt-dlp with user/genre folder structure
        
        Args:
            url: Video URL to download
            download_id: Unique download identifier
            user: User object
            genre: Current genre (may be updated based on yt-dlp info)
            
        Returns:
            Dict with success status, filename, file_size, detected_genre, or error
        """
        try:
            # Ensure user directories exist
            self.user_service.ensure_user_directories(user.username)
            
            # Sanitize download_id for filename
            safe_id = download_id.replace('-', '_')[:8]
            
            # Get genre-specific directory
            genre_dir = self.user_service.get_genre_directory(user.username, genre)
            
            # yt-dlp options
            # Note: Title is truncated to 80 chars to avoid macOS 255-byte filename limit
            # (TikTok descriptions can be 500+ chars with recipes, hashtags, etc.)
            
            # Check ffmpeg availability (system PATH or imageio-ffmpeg bundle)
            ffmpeg_available, ffmpeg_path = _get_ffmpeg_path()
            
            # Choose format based on ffmpeg availability
            # - With ffmpeg: can merge separate video+audio streams (better quality for YouTube)
            # - Without ffmpeg: must use pre-merged streams only
            # Codec preference: H.264 (avc1) > H.265 (hvc1) > any (including AV1)
            # H.264/H.265 are universally playable; AV1 requires special players like VLC
            if ffmpeg_available:
                format_selector = (
                    'bestvideo[vcodec^=avc1]+bestaudio/'  # Prefer H.264
                    'bestvideo[vcodec^=hvc1]+bestaudio/'  # Then H.265
                    'bestvideo+bestaudio/'                 # Then any codec (AV1, VP9, etc.)
                    'best'                                 # Finally single stream
                )
                logger.debug("ffmpeg available - using merge format selector with H.264/H.265 preference")
            else:
                format_selector = (
                    'best[vcodec^=avc1]/'  # Prefer H.264
                    'best[vcodec^=hvc1]/'  # Then H.265  
                    'best'                  # Then any
                )
                logger.info("ffmpeg not available - using single-stream format")
            
            ydl_opts = {
                'outtmpl': os.path.join(
                    str(genre_dir),
                    f'{safe_id}_%(title).80s.%(ext)s'
                ),
                'format': format_selector,
                'merge_output_format': 'mp4',  # Ensure merged output is MP4 (when ffmpeg available)
                'quiet': True,
                'no_warnings': True,
                'extract_flat': False,
                'ignoreerrors': False,
                'restrictfilenames': True,  # Convert special chars to ASCII-safe equivalents
                # Metadata: Save JSON sidecar file with all video metadata
                # Creates video.mp4.info.json alongside video.mp4
                # Contains: title, description, uploader, views, likes, comments, tags, etc.
                'writeinfojson': True,
                # Thumbnail: Save video thumbnail image
                'writethumbnail': True,
            }
            
            # Tell yt-dlp where ffmpeg is if using bundled version
            if ffmpeg_path:
                ydl_opts['ffmpeg_location'] = ffmpeg_path
            
            # Add cookie file if configured
            config = get_config()
            if config.downloader.cookie_file:
                cookie_path = Path(config.downloader.cookie_file)
                if cookie_path.exists():
                    ydl_opts['cookiefile'] = str(cookie_path)
                    logger.info(f"Using cookie file for authentication: {cookie_path}")
                else:
                    logger.warning(f"Cookie file specified but not found: {cookie_path}")
            
            # Download video
            info = None
            download_error = None
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                try:
                    info = ydl.extract_info(url, download=True)
                except yt_dlp.utils.DownloadError as e:
                    # yt-dlp may throw errors about intermediate files during merge
                    # but the final output might still be created successfully
                    download_error = e
                    logger.warning(f"yt-dlp reported error (checking if output exists): {e}")
                    
                    # Try to extract info without downloading to get expected filename
                    try:
                        info = ydl.extract_info(url, download=False)
                    except Exception:
                        pass
            
            if info is None:
                if download_error:
                    return {
                        'success': False,
                        'error': f'Download error: {str(download_error)}'
                    }
                return {
                    'success': False,
                    'error': 'Failed to extract video information'
                }
            
            # Try to detect genre from extractor info (fallback/verification)
            extractor_name = info.get('extractor_key') or info.get('extractor')
            detected_genre = GenreDetector.detect_from_extractor(extractor_name)
            
            # Calculate expected filename
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                expected_filename = ydl.prepare_filename(info)
            
            # Check if file exists (might exist even if yt-dlp reported an error)
            # Also check for merged output format (.mp4) if expected file doesn't exist
            filename = expected_filename
            if not os.path.exists(filename):
                # Try .mp4 extension (merge_output_format)
                base_without_ext = os.path.splitext(expected_filename)[0]
                mp4_filename = base_without_ext + '.mp4'
                if os.path.exists(mp4_filename):
                    filename = mp4_filename
                else:
                    # Search for any file with our safe_id prefix in the genre directory
                    for f in genre_dir.iterdir():
                        if f.name.startswith(safe_id) and f.suffix.lower() in {'.mp4', '.webm', '.mkv', '.mov'}:
                            filename = str(f)
                            logger.info(f"Found output file by prefix: {filename}")
                            break
            
            # If file still doesn't exist after error, it's a real failure
            if not os.path.exists(filename):
                if download_error:
                    return {
                        'success': False,
                        'error': f'Download error: {str(download_error)}'
                    }
                return {
                    'success': False,
                    'error': 'Download completed but output file not found'
                }
            
            # File exists - download succeeded (even if yt-dlp reported intermediate errors)
            if download_error:
                logger.info(f"Download succeeded despite yt-dlp error - output file exists: {filename}")
            
            # If we got a better genre detection, move the file
            final_genre = genre
            if detected_genre and detected_genre != genre:
                logger.info(f"yt-dlp detected better genre: {detected_genre} (was: {genre})")
                final_genre = detected_genre
                
                # Move file to correct genre folder if it exists
                if os.path.exists(filename):
                    new_genre_dir = self.user_service.get_genre_directory(user.username, final_genre)
                    new_genre_dir.mkdir(parents=True, exist_ok=True)
                    new_filename = os.path.join(str(new_genre_dir), os.path.basename(filename))
                    
                    try:
                        os.rename(filename, new_filename)
                        filename = new_filename
                        logger.info(f"Moved file to correct genre folder: {final_genre}")
                    except Exception as move_error:
                        logger.warning(f"Failed to move file to correct genre: {move_error}")
            
            # Get file size
            file_size = 0
            if os.path.exists(filename):
                file_size = os.path.getsize(filename)
            
            result = {
                'success': True,
                'filename': os.path.basename(filename),
                'file_size': file_size,
                'title': info.get('title', 'Unknown'),
                'duration': info.get('duration', 0),
            }
            
            # Include detected genre if different
            if final_genre != genre:
                result['detected_genre'] = final_genre
            
            return result
        
        except Exception as e:
            logger.error(f"Unexpected error during download: {e}", exc_info=True)
            return {
                'success': False,
                'error': f'Unexpected error: {str(e)}'
            }


# Global worker instance
_worker_instance: Optional[DownloadWorker] = None


def start_worker():
    """Start the global download worker"""
    global _worker_instance
    
    if _worker_instance is not None:
        logger.warning("Worker already started")
        return
    
    config = get_config()
    _worker_instance = DownloadWorker(
        db_path=config.database.path,
        root_dir=config.downloads.root_directory
    )
    _worker_instance.start()
    logger.info("Global download worker started")


def stop_worker():
    """Stop the global download worker"""
    global _worker_instance
    
    if _worker_instance is None:
        return
    
    _worker_instance.stop()
    _worker_instance = None
    logger.info("Global download worker stopped")


def get_worker() -> Optional[DownloadWorker]:
    """Get the global worker instance
    
    Returns:
        DownloadWorker instance or None
    """
    return _worker_instance

