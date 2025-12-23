"""Authentication Service

This module provides authentication services using file-based JSON storage.
It re-exports the FileAuthService for backward compatibility with existing imports.
"""

# Re-export everything from file_auth_service for backward compatibility
from app.services.file_auth_service import (
    FileAuthService as AuthService,
    get_file_auth_service as get_auth_service,
    reset_file_auth_service as reset_auth_service,
    hash_token,
    parse_user_agent,
)

# For backward compatibility, also export the hash/verify functions at module level
from app.services.file_auth_service import FileAuthService

# Expose static methods at module level for convenience
hash_password = FileAuthService.hash_password
verify_password = FileAuthService.verify_password

__all__ = [
    'AuthService',
    'get_auth_service',
    'reset_auth_service',
    'hash_token',
    'parse_user_agent',
    'hash_password',
    'verify_password',
]
