# Security Features Tracker

A concise log of security features implemented in the Video Download Server.

---

## Authentication & Sessions
- **Universal password auth** - Single password protects all API endpoints (`app/services/auth_service.py`)
- **Session tokens** - bcrypt-hashed passwords, SHA256-hashed session tokens with configurable expiry
- **Session management** - View/revoke active sessions, activity logging

## Downloads Browser Security
- **Mandatory auth** - `/api/v1/downloads/*` always requires login, even if global auth is disabled
- **Path traversal protection** - `is_safe_path()` validates all file paths stay within downloads directory
- **File type restrictions** - Only serves allowed extensions (`.mp4`, `.webm`, `.pdf`, etc.)
- **No directory listing outside root** - Cannot browse system files, only configured downloads folder

## API Security
- **Rate limiting** - Configurable per-client request limits
- **API key support** - Optional API keys for programmatic access
- **Input validation** - Pydantic models validate all request data

---

*Last updated: Dec 2024*
