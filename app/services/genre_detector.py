"""Genre Detection Service

Detects content genre from URLs for proper folder organization.
Uses URL pattern matching first, then falls back to yt-dlp extraction.
"""

import logging
import re
from typing import Optional, Tuple
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class GenreDetector:
    """Service for detecting content genre from URLs
    
    Supported genres:
    - tiktok: TikTok videos
    - instagram: Instagram posts/reels/stories
    - youtube: YouTube videos
    - pdf: PDF files
    - ebook: eBook formats
    - unknown: Anything else (fallback)
    """
    
    # URL pattern to genre mapping
    URL_PATTERNS = {
        'tiktok': [
            r'tiktok\.com',
            r'vm\.tiktok\.com',
            r'm\.tiktok\.com',
        ],
        'instagram': [
            r'instagram\.com',
            r'instagr\.am',
        ],
        'youtube': [
            r'youtube\.com',
            r'youtu\.be',
            r'm\.youtube\.com',
        ],
        'pdf': [
            r'\.pdf($|\?)',  # .pdf extension at end or before query params
        ],
        'ebook': [
            r'\.epub($|\?)',
            r'\.mobi($|\?)',
            r'\.azw($|\?)',
            r'\.azw3($|\?)',
        ],
    }
    
    # yt-dlp extractor names to genre mapping
    EXTRACTOR_PATTERNS = {
        'tiktok': ['TikTok', 'TikTokUser', 'TikTokSound', 'TikTokEffect'],
        'instagram': ['Instagram', 'InstagramIOS', 'InstagramUser'],
        'youtube': ['Youtube', 'YoutubeTab', 'YoutubePlaylist', 'YoutubeLive'],
    }
    
    @classmethod
    def detect_from_url(cls, url: str) -> Optional[str]:
        """Detect genre from URL pattern matching
        
        Args:
            url: URL to analyze
            
        Returns:
            Genre string or None if not detected
        """
        try:
            url_lower = url.lower()
            
            # Check each genre's patterns
            for genre, patterns in cls.URL_PATTERNS.items():
                for pattern in patterns:
                    if re.search(pattern, url_lower, re.IGNORECASE):
                        logger.debug(f"Detected genre '{genre}' from URL pattern: {pattern}")
                        return genre
            
            return None
            
        except Exception as e:
            logger.error(f"Error detecting genre from URL: {e}", exc_info=True)
            return None
    
    @classmethod
    def detect_from_extractor(cls, extractor_name: Optional[str]) -> Optional[str]:
        """Detect genre from yt-dlp extractor name
        
        Args:
            extractor_name: yt-dlp extractor name (e.g., 'TikTok', 'Youtube')
            
        Returns:
            Genre string or None if not detected
        """
        if not extractor_name:
            return None
        
        try:
            # Check each genre's extractor patterns
            for genre, extractors in cls.EXTRACTOR_PATTERNS.items():
                for extractor in extractors:
                    if extractor.lower() in extractor_name.lower():
                        logger.debug(f"Detected genre '{genre}' from extractor: {extractor_name}")
                        return genre
            
            return None
            
        except Exception as e:
            logger.error(f"Error detecting genre from extractor: {e}", exc_info=True)
            return None
    
    @classmethod
    def detect(cls, url: str, extractor_name: Optional[str] = None) -> Tuple[str, Optional[str]]:
        """Detect genre using all available methods
        
        Detection order:
        1. URL pattern matching
        2. yt-dlp extractor name
        3. Fallback to 'unknown'
        
        Args:
            url: URL to analyze
            extractor_name: Optional yt-dlp extractor name
            
        Returns:
            Tuple of (genre, detection_error)
            - genre: Always returns a valid genre string (never None)
            - detection_error: Error message if detection had issues, None otherwise
        """
        detection_error = None
        
        try:
            # Try URL pattern matching first
            genre = cls.detect_from_url(url)
            if genre:
                logger.info(f"Genre detected from URL: {genre}")
                return genre, None
            
            # Try yt-dlp extractor as fallback
            if extractor_name:
                genre = cls.detect_from_extractor(extractor_name)
                if genre:
                    logger.info(f"Genre detected from extractor: {genre}")
                    return genre, None
            
            # Fallback to unknown
            logger.warning(f"Could not detect genre for URL: {url}, using 'unknown'")
            detection_error = f"Could not detect genre from URL or extractor"
            return 'unknown', detection_error
            
        except Exception as e:
            logger.error(f"Error during genre detection: {e}", exc_info=True)
            detection_error = f"Genre detection error: {str(e)}"
            return 'unknown', detection_error
    
    @classmethod
    def is_valid_genre(cls, genre: str) -> bool:
        """Check if a genre string is valid
        
        Args:
            genre: Genre string to validate
            
        Returns:
            True if valid genre, False otherwise
        """
        valid_genres = {'tiktok', 'instagram', 'youtube', 'pdf', 'ebook', 'unknown'}
        return genre.lower() in valid_genres
    
    @classmethod
    def normalize_genre(cls, genre: str) -> str:
        """Normalize genre string to lowercase
        
        Args:
            genre: Genre string
            
        Returns:
            Normalized genre string
        """
        return genre.lower().strip()
    
    @classmethod
    def get_supported_genres(cls) -> list:
        """Get list of all supported genres
        
        Returns:
            List of supported genre strings
        """
        return ['tiktok', 'instagram', 'youtube', 'pdf', 'ebook', 'unknown']


# Convenience function for quick detection
def detect_genre(url: str, extractor_name: Optional[str] = None) -> Tuple[str, Optional[str]]:
    """Convenience function to detect genre
    
    Args:
        url: URL to analyze
        extractor_name: Optional yt-dlp extractor name
        
    Returns:
        Tuple of (genre, detection_error)
    """
    return GenreDetector.detect(url, extractor_name)

