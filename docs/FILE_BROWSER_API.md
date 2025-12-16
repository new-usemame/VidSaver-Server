# File Browser API - Client Integration Guide

Server-side documentation for iOS/client integration with the Downloads File Browser API.

## Overview

The File Browser API provides access to downloaded files organized by `username/genre/` structure. Unlike the deprecated history endpoint, this reads directly from the file system—if a file exists on disk, it appears here.

**Base URL:** `/api/v1/downloads`

## Authentication

**All File Browser endpoints require authentication**, even if global auth is disabled.

### Headers
```
Authorization: Bearer <session_token>
```

Or use cookie-based auth (for web browsers):
```
Cookie: session_token=<token>
```

### Getting a Token
```
POST /api/v1/auth/login
Content-Type: application/json

{"password": "your-password"}
```

Response:
```json
{
  "success": true,
  "session_token": "abc123...",
  "expires_at": "2024-12-17T12:00:00Z"
}
```

---

## Endpoints

### 1. Get Folder Structure

Returns the complete folder hierarchy with file counts and sizes.

```
GET /api/v1/downloads/structure
```

**Response:**
```json
{
  "root_directory": "/Users/name/Downloads/VidSaver",
  "users": [
    {
      "username": "defaultuser",
      "genres": {
        "tiktok": {
          "count": 5,
          "size_bytes": 52428800,
          "size_formatted": "50.0 MB"
        },
        "instagram": {
          "count": 2,
          "size_bytes": 20971520,
          "size_formatted": "20.0 MB"
        }
      },
      "total_videos": 7,
      "total_size": 73400320,
      "total_size_formatted": "70.0 MB"
    }
  ],
  "total_videos": 7,
  "total_size": 73400320,
  "total_size_formatted": "70.0 MB"
}
```

**Use Case:** Build a folder tree UI, show storage usage per user/genre.

---

### 2. Get Videos List

Returns a flat list of videos with filtering, sorting, and pagination.

```
GET /api/v1/downloads/videos
```

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `username` | string | null | Filter by username |
| `genre` | string | null | Filter by genre (tiktok, instagram, youtube, etc.) |
| `search` | string | null | Search in filename |
| `sort` | string | "newest" | Sort order: `newest`, `oldest`, `largest`, `smallest`, `name` |
| `limit` | int | 50 | Results per page (1-200) |
| `offset` | int | 0 | Pagination offset |

**Example Request:**
```
GET /api/v1/downloads/videos?username=defaultuser&genre=tiktok&sort=newest&limit=20
```

**Response:**
```json
{
  "videos": [
    {
      "filename": "video_123456.mp4",
      "username": "defaultuser",
      "genre": "tiktok",
      "path": "defaultuser/tiktok/video_123456.mp4",
      "size_bytes": 10485760,
      "size_formatted": "10.0 MB",
      "modified_at": 1702742400,
      "modified_formatted": "2 hours ago",
      "extension": ".mp4"
    }
  ],
  "total": 45,
  "limit": 20,
  "offset": 0,
  "has_more": true
}
```

**Use Case:** Display video grid/list, implement search, paginated browsing.

---

### 3. Stream/Download File

Stream or download a video file directly.

```
GET /api/v1/downloads/stream/{path}
```

**Path Parameter:** The `path` field from the videos list response (URL-encoded).

**Example:**
```
GET /api/v1/downloads/stream/defaultuser%2Ftiktok%2Fvideo_123456.mp4
```

**Response:** File stream with appropriate `Content-Type` header.

**Supported File Types:**
- Video: `.mp4`, `.webm`, `.mov`, `.avi`, `.mkv`, `.m4v`
- Audio: `.mp3`, `.wav`, `.ogg`, `.flac`, `.m4a`
- Documents: `.pdf`, `.epub`, `.mobi`

**Use Case:** Video playback, file download button.

---

## iOS Integration Example

### Swift - Fetch Videos

```swift
func fetchVideos(username: String? = nil, genre: String? = nil) async throws -> VideosResponse {
    var components = URLComponents(string: "\(baseURL)/api/v1/downloads/videos")!
    var queryItems: [URLQueryItem] = []
    
    if let username = username {
        queryItems.append(URLQueryItem(name: "username", value: username))
    }
    if let genre = genre {
        queryItems.append(URLQueryItem(name: "genre", value: genre))
    }
    queryItems.append(URLQueryItem(name: "sort", value: "newest"))
    queryItems.append(URLQueryItem(name: "limit", value: "50"))
    
    components.queryItems = queryItems
    
    var request = URLRequest(url: components.url!)
    request.setValue("Bearer \(sessionToken)", forHTTPHeaderField: "Authorization")
    
    let (data, _) = try await URLSession.shared.data(for: request)
    return try JSONDecoder().decode(VideosResponse.self, from: data)
}
```

### Swift - Build Stream URL

```swift
func streamURL(for video: Video) -> URL {
    let encodedPath = video.path.addingPercentEncoding(withAllowedCharacters: .urlPathAllowed) ?? video.path
    return URL(string: "\(baseURL)/api/v1/downloads/stream/\(encodedPath)")!
}
```

### Swift - Video Playback with AVPlayer

```swift
import AVKit

func playVideo(_ video: Video) {
    let url = streamURL(for: video)
    
    // Add auth header for streaming
    let asset = AVURLAsset(url: url, options: [
        "AVURLAssetHTTPHeaderFieldsKey": ["Authorization": "Bearer \(sessionToken)"]
    ])
    
    let playerItem = AVPlayerItem(asset: asset)
    let player = AVPlayer(playerItem: playerItem)
    
    let playerVC = AVPlayerViewController()
    playerVC.player = player
    present(playerVC, animated: true) {
        player.play()
    }
}
```

---

## Response Models

### Video Object
```json
{
  "filename": "string",      // File name only
  "username": "string",      // Owner username
  "genre": "string",         // tiktok, instagram, youtube, pdf, ebook, unknown
  "path": "string",          // Relative path for streaming (username/genre/filename)
  "size_bytes": 0,           // File size in bytes
  "size_formatted": "string", // Human readable size
  "modified_at": 0,          // Unix timestamp
  "modified_formatted": "string", // Human readable time
  "extension": "string"      // File extension (.mp4, .pdf, etc.)
}
```

### Folder Structure User Object
```json
{
  "username": "string",
  "genres": {
    "genre_name": {
      "count": 0,
      "size_bytes": 0,
      "size_formatted": "string"
    }
  },
  "total_videos": 0,
  "total_size": 0,
  "total_size_formatted": "string"
}
```

---

## Error Responses

### 401 Unauthorized
```json
{
  "error": "authentication_required",
  "message": "This page requires authentication. Please login first.",
  "login_url": "/api/v1/auth/login"
}
```

### 403 Forbidden
```json
{
  "detail": "Access denied: Invalid path"
}
```

### 404 Not Found
```json
{
  "detail": "File not found"
}
```

---

## Notes

1. **File system based** - Shows files that actually exist on disk. No database sync issues.
2. **Always authenticated** - Even if global auth is off, these endpoints require login.
3. **Path encoding** - Always URL-encode the `path` parameter when streaming.
4. **Genres** - Common values: `tiktok`, `instagram`, `youtube`, `pdf`, `ebook`, `unknown`
