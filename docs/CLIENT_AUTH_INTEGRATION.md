# Client Authentication Integration Guide

## Overview

The server now supports **optional universal password authentication**. When enabled, all API endpoints (except health/auth) require a valid session token.

## Quick Reference

| Endpoint | Method | Auth Required | Purpose |
|----------|--------|---------------|---------|
| `/api/v1/auth/status` | GET | No | Check if auth is enabled |
| `/api/v1/auth/login` | POST | No | Login, get session token |
| `/api/v1/auth/logout` | POST | Yes | Invalidate session |
| `/api/v1/auth/verify` | GET | Yes | Verify token is valid |
| `/api/v1/download` | POST | **When enabled** | Submit download |
| `/api/v1/status/*` | GET | **When enabled** | Check status |
| `/api/v1/history` | GET | **When enabled** | Get history |

## Client Flow

```
1. GET /api/v1/auth/status
   └─> { "auth_enabled": true/false, ... }

2. If auth_enabled == true AND no stored token:
   └─> Show login UI, collect password

3. POST /api/v1/auth/login
   Body: { "password": "user_password" }
   └─> Success: { "success": true, "session_token": "abc123...", "expires_at": "..." }
   └─> Failure: 401 { "detail": { "error": "invalid_password" } }

4. Store session_token securely (Keychain on iOS)

5. All subsequent requests include header:
   Authorization: Bearer <session_token>
```

## API Details

### Check Auth Status
```
GET /api/v1/auth/status

Response:
{
  "auth_enabled": true,
  "has_password": true,
  "message": "Authentication is enabled..."
}
```

### Login
```
POST /api/v1/auth/login
Content-Type: application/json

{ "password": "the_password" }

Success (200):
{
  "success": true,
  "message": "Login successful",
  "session_token": "abc123...",
  "expires_at": "2025-01-15T10:30:00Z"  // null if never expires
}

Failure (401):
{
  "detail": {
    "error": "invalid_password",
    "message": "Invalid password"
  }
}
```

### Using the Token
```
GET /api/v1/history
Authorization: Bearer abc123...
```

### Handling 401 Responses
When auth is enabled and token is missing/invalid:
```json
{
  "error": "authentication_required",
  "message": "Authentication required. Please login at /api/v1/auth/login"
}
```
**Client action:** Clear stored token, prompt for login.

## Implementation Checklist

- [ ] On app launch, call `GET /api/v1/auth/status`
- [ ] If `auth_enabled` is true and no valid token, show login screen
- [ ] Store `session_token` securely after successful login
- [ ] Add `Authorization: Bearer <token>` header to all API requests
- [ ] Handle 401 responses by prompting re-login
- [ ] Optionally show "Logout" option that calls `POST /api/v1/auth/logout`

## Notes

- Session tokens persist across app restarts (stored server-side)
- `expires_at` can be null (never expires) or a future datetime
- The password is universal (same for all users)
- Auth is **optional** - server works without it when disabled
