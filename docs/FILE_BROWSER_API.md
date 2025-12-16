# File Browser API - Client Integration Guide

Server documentation for iOS/client integration with the Downloads & Queue API.

## Overview

The File Browser API provides two main capabilities:

1. **Download Queue** - Track pending, in-progress, and failed downloads (database-backed)
2. **File Browser** - Browse and stream completed downloads (file system-backed)

**Base URL:** `/api/v1/downloads`

---

## Authentication

**All endpoints require authentication**, even if global auth is disabled.

### Headers
```
Authorization: Bearer <session_token>
```

### Getting a Token
```http
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

## Download Queue Endpoints

These endpoints read from the database to show download status.

### GET /queue - Get Download Queue

Returns all non-completed downloads organized by status.

```http
GET /api/v1/downloads/queue
```

**Response:**
```json
{
  "downloading": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "url": "https://tiktok.com/@user/video/123",
      "status": "downloading",
      "username": "defaultuser",
      "genre": "tiktok",
      "error_message": null,
      "retry_count": 0,
      "created_at": 1702742400,
      "created_formatted": "2 min ago",
      "started_at": 1702742410,
      "started_formatted": "1 min ago"
    }
  ],
  "pending": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440001",
      "url": "https://instagram.com/p/ABC123",
      "status": "pending",
      "username": "defaultuser",
      "genre": "instagram",
      "error_message": null,
      "retry_count": 0,
      "created_at": 1702742500,
      "created_formatted": "Just now",
      "started_at": null,
      "started_formatted": null
    }
  ],
  "failed": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440002",
      "url": "https://tiktok.com/@user/video/456",
      "status": "failed",
      "username": "defaultuser",
      "genre": "tiktok",
      "error_message": "HTTP Error 404: Video not found",
      "retry_count": 3,
      "created_at": 1702740000,
      "created_formatted": "1 hour ago",
      "started_at": 1702740010,
      "started_formatted": "1 hour ago"
    }
  ],
  "counts": {
    "downloading": 1,
    "pending": 1,
    "failed": 1,
    "total": 3
  }
}
```

**Use Cases:**
- Show active download progress with spinner/animation
- Display pending queue with position
- Show failed downloads with error messages and retry option
- Badge counter for total queue items

---

### POST /retry/{download_id} - Retry Failed Download

Reset a failed download back to pending so it will be retried by the worker.

```http
POST /api/v1/downloads/retry/550e8400-e29b-41d4-a716-446655440002
```

**Response (200):**
```json
{
  "success": true,
  "message": "Download queued for retry",
  "download_id": "550e8400-e29b-41d4-a716-446655440002"
}
```

**Error Responses:**
- `404` - Download not found
- `400` - Download is not in failed status

```json
{
  "error": "invalid_status",
  "message": "Cannot retry download with status 'completed'. Only failed downloads can be retried."
}
```

**Use Case:** Retry button on failed downloads.

---

## File Browser Endpoints

These endpoints read from the file system to show completed downloads.

### GET /structure - Get Folder Structure

Returns folder hierarchy with file counts and storage usage.

```http
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

**Use Cases:**
- Folder tree navigation UI
- Storage usage per user/genre
- Quick stats display

---

### GET /videos - Get Videos List

Returns a flat list of videos with filtering, sorting, and pagination.

```http
GET /api/v1/downloads/videos?username=defaultuser&genre=tiktok&sort=newest&limit=20
```

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `username` | string | null | Filter by username |
| `genre` | string | null | Filter by genre |
| `search` | string | null | Search in filename |
| `sort` | string | "newest" | `newest`, `oldest`, `largest`, `smallest`, `name` |
| `limit` | int | 50 | Results per page (1-200) |
| `offset` | int | 0 | Pagination offset |

**Response:**
```json
{
  "videos": [
    {
      "filename": "video_7301234567890.mp4",
      "username": "defaultuser",
      "genre": "tiktok",
      "path": "defaultuser/tiktok/video_7301234567890.mp4",
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

**Use Cases:**
- Video grid/list view
- Search functionality
- Paginated browsing

---

### GET /stream/{path} - Stream/Download File

Stream or download a video file directly.

```http
GET /api/v1/downloads/stream/defaultuser%2Ftiktok%2Fvideo_123.mp4
```

**Path Parameter:** URL-encoded relative path from the `path` field in videos list.

**Response:** File stream with appropriate `Content-Type` header.

**Supported Types:**
- Video: `.mp4`, `.webm`, `.mov`, `.avi`, `.mkv`, `.m4v`
- Audio: `.mp3`, `.wav`, `.ogg`, `.flac`, `.m4a`
- Documents: `.pdf`, `.epub`, `.mobi`

---

## iOS Integration Examples

### Swift Models

```swift
// Queue Response
struct QueueResponse: Codable {
    let downloading: [QueueItem]
    let pending: [QueueItem]
    let failed: [QueueItem]
    let counts: QueueCounts
}

struct QueueItem: Codable, Identifiable {
    let id: String
    let url: String
    let status: String
    let username: String
    let genre: String
    let errorMessage: String?
    let retryCount: Int
    let createdAt: Int
    let createdFormatted: String
    let startedAt: Int?
    let startedFormatted: String?
    
    enum CodingKeys: String, CodingKey {
        case id, url, status, username, genre
        case errorMessage = "error_message"
        case retryCount = "retry_count"
        case createdAt = "created_at"
        case createdFormatted = "created_formatted"
        case startedAt = "started_at"
        case startedFormatted = "started_formatted"
    }
}

struct QueueCounts: Codable {
    let downloading: Int
    let pending: Int
    let failed: Int
    let total: Int
}

// Video/File Response
struct VideosResponse: Codable {
    let videos: [Video]
    let total: Int
    let limit: Int
    let offset: Int
    let hasMore: Bool
    
    enum CodingKeys: String, CodingKey {
        case videos, total, limit, offset
        case hasMore = "has_more"
    }
}

struct Video: Codable, Identifiable {
    var id: String { path }
    let filename: String
    let username: String
    let genre: String
    let path: String
    let sizeBytes: Int
    let sizeFormatted: String
    let modifiedAt: Int
    let modifiedFormatted: String
    let `extension`: String
    
    enum CodingKeys: String, CodingKey {
        case filename, username, genre, path
        case sizeBytes = "size_bytes"
        case sizeFormatted = "size_formatted"
        case modifiedAt = "modified_at"
        case modifiedFormatted = "modified_formatted"
        case `extension`
    }
}
```

### Swift - Fetch Queue

```swift
func fetchQueue() async throws -> QueueResponse {
    var request = URLRequest(url: URL(string: "\(baseURL)/api/v1/downloads/queue")!)
    request.setValue("Bearer \(sessionToken)", forHTTPHeaderField: "Authorization")
    
    let (data, _) = try await URLSession.shared.data(for: request)
    return try JSONDecoder().decode(QueueResponse.self, from: data)
}
```

### Swift - Retry Failed Download

```swift
func retryDownload(id: String) async throws {
    var request = URLRequest(url: URL(string: "\(baseURL)/api/v1/downloads/retry/\(id)")!)
    request.httpMethod = "POST"
    request.setValue("Bearer \(sessionToken)", forHTTPHeaderField: "Authorization")
    
    let (_, response) = try await URLSession.shared.data(for: request)
    
    guard let httpResponse = response as? HTTPURLResponse,
          httpResponse.statusCode == 200 else {
        throw APIError.retryFailed
    }
}
```

### Swift - Fetch Videos

```swift
func fetchVideos(username: String? = nil, genre: String? = nil) async throws -> VideosResponse {
    var components = URLComponents(string: "\(baseURL)/api/v1/downloads/videos")!
    var queryItems: [URLQueryItem] = [
        URLQueryItem(name: "sort", value: "newest"),
        URLQueryItem(name: "limit", value: "50")
    ]
    
    if let username = username {
        queryItems.append(URLQueryItem(name: "username", value: username))
    }
    if let genre = genre {
        queryItems.append(URLQueryItem(name: "genre", value: genre))
    }
    
    components.queryItems = queryItems
    
    var request = URLRequest(url: components.url!)
    request.setValue("Bearer \(sessionToken)", forHTTPHeaderField: "Authorization")
    
    let (data, _) = try await URLSession.shared.data(for: request)
    return try JSONDecoder().decode(VideosResponse.self, from: data)
}
```

### Swift - Video Playback

```swift
import AVKit

func playVideo(_ video: Video) {
    let encodedPath = video.path.addingPercentEncoding(withAllowedCharacters: .urlPathAllowed) ?? video.path
    let url = URL(string: "\(baseURL)/api/v1/downloads/stream/\(encodedPath)")!
    
    // AVURLAsset with auth header
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

## Recommended Polling Strategy

For the Queue tab, implement smart polling:

```swift
class QueueManager: ObservableObject {
    @Published var queue: QueueResponse?
    private var timer: Timer?
    
    func startPolling() {
        // Initial fetch
        Task { await refresh() }
        
        // Poll every 5 seconds when queue has items
        timer = Timer.scheduledTimer(withTimeInterval: 5.0, repeats: true) { _ in
            Task { await self.refresh() }
        }
    }
    
    func stopPolling() {
        timer?.invalidate()
        timer = nil
    }
    
    func refresh() async {
        do {
            let newQueue = try await fetchQueue()
            await MainActor.run {
                self.queue = newQueue
                
                // Stop polling if queue is empty
                if newQueue.counts.total == 0 {
                    self.stopPolling()
                }
            }
        } catch {
            print("Queue fetch error: \(error)")
        }
    }
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

## Quick Reference

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/queue` | GET | Get downloading, pending, failed items |
| `/retry/{id}` | POST | Retry a failed download |
| `/structure` | GET | Get folder tree with counts |
| `/videos` | GET | List videos with filters |
| `/stream/{path}` | GET | Stream/download a file |

**Genres:** `tiktok`, `instagram`, `youtube`, `pdf`, `ebook`, `unknown`
