"""Logging Configuration

Sets up structured logging with rotation for the application.
"""

import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler

from app.core.config import get_config


def setup_logging():
    """Setup application logging with rotation
    
    Configures:
    - Console output (INFO and above)
    - File output with rotation (configurable level)
    - Structured format with timestamps
    """
    config = get_config()
    
    # Create logs directory
    log_file = Path(config.logging.file)
    log_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Get log level
    log_level = getattr(logging, config.logging.level.upper(), logging.INFO)
    
    # Create formatter
    formatter = logging.Formatter(
        fmt='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Remove existing handlers
    root_logger.handlers = []
    
    # Console handler (always INFO or above)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # File handler with rotation
    max_bytes = config.logging.get_max_bytes()
    file_handler = RotatingFileHandler(
        filename=str(log_file),
        maxBytes=max_bytes,
        backupCount=config.logging.backup_count,
        encoding='utf-8'
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)
    
    # Log initial message
    logger = logging.getLogger(__name__)
    logger.info("Logging system initialized")
    logger.info(f"Log file: {log_file}")
    logger.info(f"Log level: {config.logging.level}")
    logger.info(f"Max file size: {config.logging.max_size}")
    logger.info(f"Backup count: {config.logging.backup_count}")


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance for a module
    
    Args:
        name: Module name (typically __name__)
        
    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)

