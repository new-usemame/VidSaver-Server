"""Metadata Service

Extracts rich metadata from yt-dlp info dictionaries and manages JSON sidecar files
alongside downloaded videos. This allows storing detailed video information without
using the database for file organization.
"""

import json
import logging
import os
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)

# Common metadata fields extracted for all platforms
COMMON_FIELDS = [
    'id',
    'title',
    'description',
    'uploader',
    'uploader_id',
    'uploader_url',
    'channel',
    'channel_id',
    'channel_url',
    'upload_date',
    'timestamp',
    'duration',
    'view_count',
    'like_count',
    'comment_count',
    'repost_count',
    'tags',
    'categories',
    'thumbnail',
    'webpage_url',
    'extractor',
    'extractor_key',
]

# Platform-specific fields
TIKTOK_FIELDS = [
    'track',
    'artist',
    'creator',
    'creator_url',
]

YOUTUBE_FIELDS = [
    'chapters',
    'age_limit',
    'is_live',
    'was_live',
    'live_status',
    'release_timestamp',
    'availability',
]

INSTAGRAM_FIELDS = [
    'is_video',
    'location',
]


def extract_metadata(info: Dict[str, Any]) -> Dict[str, Any]:
    """Extract relevant metadata from yt-dlp info dictionary.
    
    Args:
        info: Raw info dictionary from yt-dlp extract_info()
        
    Returns:
        Cleaned metadata dictionary with relevant fields
    """
    if not info:
        return {}
    
    metadata = {}
    
    # Extract common fields
    for field in COMMON_FIELDS:
        if field in info and info[field] is not None:
            metadata[field] = info[field]
    
    # Detect platform and extract platform-specific fields
    extractor = info.get('extractor_key') or info.get('extractor') or ''
    extractor_lower = extractor.lower()
    
    platform_fields = []
    if 'tiktok' in extractor_lower:
        platform_fields = TIKTOK_FIELDS
        metadata['platform'] = 'tiktok'
    elif 'youtube' in extractor_lower:
        platform_fields = YOUTUBE_FIELDS
        metadata['platform'] = 'youtube'
    elif 'instagram' in extractor_lower:
        platform_fields = INSTAGRAM_FIELDS
        metadata['platform'] = 'instagram'
    else:
        metadata['platform'] = extractor_lower or 'unknown'
    
    # Extract platform-specific fields
    for field in platform_fields:
        if field in info and info[field] is not None:
            metadata[field] = info[field]
    
    # Add download timestamp
    metadata['downloaded_at'] = datetime.now().isoformat()
    
    # Clean up tags - ensure it's a list of strings
    if 'tags' in metadata and metadata['tags']:
        if isinstance(metadata['tags'], list):
            metadata['tags'] = [str(tag) for tag in metadata['tags'] if tag]
        else:
            metadata['tags'] = [str(metadata['tags'])]
    
    # Format duration as human-readable if available
    if 'duration' in metadata and metadata['duration']:
        try:
            duration_secs = int(metadata['duration'])
            mins, secs = divmod(duration_secs, 60)
            hours, mins = divmod(mins, 60)
            if hours > 0:
                metadata['duration_formatted'] = f"{hours}:{mins:02d}:{secs:02d}"
            else:
                metadata['duration_formatted'] = f"{mins}:{secs:02d}"
        except (ValueError, TypeError):
            pass
    
    # Format upload date if available
    if 'upload_date' in metadata and metadata['upload_date']:
        try:
            date_str = str(metadata['upload_date'])
            if len(date_str) == 8:  # YYYYMMDD format
                formatted = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
                metadata['upload_date_formatted'] = formatted
        except (ValueError, TypeError):
            pass
    
    # Format view/like/comment counts with commas
    for count_field in ['view_count', 'like_count', 'comment_count', 'repost_count']:
        if count_field in metadata and metadata[count_field] is not None:
            try:
                count = int(metadata[count_field])
                metadata[f'{count_field}_formatted'] = f"{count:,}"
            except (ValueError, TypeError):
                pass
    
    logger.debug(f"Extracted metadata for {metadata.get('platform', 'unknown')}: {metadata.get('title', 'Unknown')[:50]}")
    
    return metadata


def get_metadata_path(video_path: str) -> Path:
    """Get the JSON metadata file path for a video file.
    
    Args:
        video_path: Path to the video file
        
    Returns:
        Path to the companion JSON metadata file
    """
    video_path = Path(video_path)
    # Replace video extension with .json
    return video_path.with_suffix('.json')


def save_metadata(video_path: str, metadata: Dict[str, Any]) -> bool:
    """Save metadata to a JSON sidecar file alongside the video.
    
    Args:
        video_path: Path to the video file
        metadata: Metadata dictionary to save
        
    Returns:
        True if saved successfully, False otherwise
    """
    if not metadata:
        logger.warning("No metadata to save")
        return False
    
    try:
        json_path = get_metadata_path(video_path)
        
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False, default=str)
        
        logger.info(f"Saved metadata to: {json_path}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to save metadata for {video_path}: {e}", exc_info=True)
        return False


def load_metadata(video_path: str) -> Optional[Dict[str, Any]]:
    """Load metadata from the JSON sidecar file for a video.
    
    Args:
        video_path: Path to the video file
        
    Returns:
        Metadata dictionary if found, None otherwise
    """
    try:
        json_path = get_metadata_path(video_path)
        
        if not json_path.exists():
            return None
        
        with open(json_path, 'r', encoding='utf-8') as f:
            metadata = json.load(f)
        
        return metadata
        
    except json.JSONDecodeError as e:
        logger.warning(f"Invalid JSON in metadata file {video_path}: {e}")
        return None
    except Exception as e:
        logger.error(f"Failed to load metadata for {video_path}: {e}", exc_info=True)
        return None


def metadata_exists(video_path: str) -> bool:
    """Check if a metadata JSON file exists for a video.
    
    Args:
        video_path: Path to the video file
        
    Returns:
        True if metadata file exists, False otherwise
    """
    return get_metadata_path(video_path).exists()


def delete_metadata(video_path: str) -> bool:
    """Delete the metadata JSON file for a video.
    
    Args:
        video_path: Path to the video file
        
    Returns:
        True if deleted or didn't exist, False on error
    """
    try:
        json_path = get_metadata_path(video_path)
        
        if json_path.exists():
            json_path.unlink()
            logger.info(f"Deleted metadata file: {json_path}")
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to delete metadata for {video_path}: {e}", exc_info=True)
        return False


def get_metadata_summary(metadata: Dict[str, Any]) -> Dict[str, Any]:
    """Get a summary of metadata suitable for API responses.
    
    This returns a subset of fields for display in listings,
    not the full metadata.
    
    Args:
        metadata: Full metadata dictionary
        
    Returns:
        Summary dictionary with display-friendly fields
    """
    if not metadata:
        return {}
    
    summary = {}
    
    # Basic info
    summary_fields = [
        'title',
        'description',
        'uploader',
        'platform',
        'duration_formatted',
        'upload_date_formatted',
        'view_count_formatted',
        'like_count_formatted',
        'comment_count_formatted',
        'tags',
        'webpage_url',
        'thumbnail',
    ]
    
    for field in summary_fields:
        if field in metadata and metadata[field] is not None:
            summary[field] = metadata[field]
    
    # Truncate description for summary
    if 'description' in summary and summary['description']:
        desc = summary['description']
        if len(desc) > 200:
            summary['description_short'] = desc[:197] + '...'
        else:
            summary['description_short'] = desc
    
    return summary
