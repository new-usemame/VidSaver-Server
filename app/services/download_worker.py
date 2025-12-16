"""Download Worker Service

Background worker that processes video download queue using yt-dlp.
Monitors database for pending downloads and processes them asynchronously.
"""

import logging
import time
import threading
import os
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

import yt_dlp

from app.services.database_service import DatabaseService
from app.services.genre_detector import GenreDetector
from app.services.user_service import UserService
from app.models.database import Download, DownloadStatus, User
from app.core.config import get_config

logger = logging.getLogger(__name__)


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
            ydl_opts = {
                'outtmpl': os.path.join(
                    str(genre_dir),
                    f'{safe_id}_%(title).80s.%(ext)s'
                ),
                'format': 'best',
                'quiet': True,
                'no_warnings': True,
                'extract_flat': False,
                'ignoreerrors': False,
                'restrictfilenames': True,  # Convert special chars to ASCII-safe equivalents
            }
            
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
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                
                if info is None:
                    return {
                        'success': False,
                        'error': 'Failed to extract video information'
                    }
                
                # Try to detect genre from extractor info (fallback/verification)
                extractor_name = info.get('extractor_key') or info.get('extractor')
                detected_genre = GenreDetector.detect_from_extractor(extractor_name)
                
                # If we got a better genre detection, move the file
                final_genre = genre
                if detected_genre and detected_genre != genre:
                    logger.info(f"yt-dlp detected better genre: {detected_genre} (was: {genre})")
                    final_genre = detected_genre
                    
                    # Get filename first
                    old_filename = ydl.prepare_filename(info)
                    
                    # Move file to correct genre folder if it exists
                    if os.path.exists(old_filename):
                        new_genre_dir = self.user_service.get_genre_directory(user.username, final_genre)
                        new_genre_dir.mkdir(parents=True, exist_ok=True)
                        new_filename = os.path.join(str(new_genre_dir), os.path.basename(old_filename))
                        
                        try:
                            os.rename(old_filename, new_filename)
                            filename = new_filename
                            logger.info(f"Moved file to correct genre folder: {final_genre}")
                        except Exception as move_error:
                            logger.warning(f"Failed to move file to correct genre: {move_error}")
                            filename = old_filename
                    else:
                        filename = ydl.prepare_filename(info)
                else:
                    filename = ydl.prepare_filename(info)
                
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
        
        except yt_dlp.utils.DownloadError as e:
            logger.error(f"yt-dlp download error: {e}")
            return {
                'success': False,
                'error': f'Download error: {str(e)}'
            }
        
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

