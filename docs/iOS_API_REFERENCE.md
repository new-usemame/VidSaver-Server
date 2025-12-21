# iOS API Quick Reference

Quick reference for iOS clients to access video metadata, thumbnails, and streaming.

## Authentication

All `/api/v1/downloads/*` endpoints require authentication.

```swift
// Add to all requests
request.setValue("Bearer \(sessionToken)", forHTTPHeaderField: "Authorization")

// For video streaming (where headers can't be set), use query param:
let url = "\(baseURL)/api/v1/downloads/stream/\(path)?token=\(sessionToken)"
```

---

## Video Listing

**GET** `/api/v1/downloads/videos`

```swift
// Query params: username, genre, search, sort, limit, offset
let url = "\(baseURL)/api/v1/downloads/videos?sort=newest&limit=50"
```

**Response:**
```json
{
  "videos": [
    {
      "filename": "video_123.mp4",
      "username": "john",
      "genre": "tiktok",
      "path": "john/tiktok/video_123.mp4",
      "size_bytes": 10485760,
      "size_formatted": "10.0 MB",
      "modified_at": 1702742400,
      "modified_formatted": "2 hours ago",
      "extension": ".mp4"
    }
  ],
  "total": 45,
  "has_more": true
}
```

---

## Video Streaming

**GET** `/api/v1/downloads/stream/{path}`

Supports HTTP **Range requests** (required for iOS AVPlayer).

```swift
// Path must be URL-encoded
let encodedPath = video.path.addingPercentEncoding(withAllowedCharacters: .urlPathAllowed)!
let streamURL = URL(string: "\(baseURL)/api/v1/downloads/stream/\(encodedPath)?token=\(token)")!

// AVPlayer with auth
let asset = AVURLAsset(url: streamURL)
let player = AVPlayer(playerItem: AVPlayerItem(asset: asset))
```

**Headers returned:**
- `Accept-Ranges: bytes` (enables seeking)
- `Content-Range: bytes 0-999/5000` (for 206 responses)

---

## Video Metadata (Info JSON)

Each video has a companion `.json` file with rich metadata. **Stream it like a video:**

```swift
// For video: john/tiktok/video_123.mp4
// Metadata: john/tiktok/video_123.json

func fetchMetadata(for video: Video) async throws -> VideoMetadata? {
    let jsonPath = video.path.replacingOccurrences(of: video.extension, with: ".json")
    let encodedPath = jsonPath.addingPercentEncoding(withAllowedCharacters: .urlPathAllowed)!
    
    var request = URLRequest(url: URL(string: "\(baseURL)/api/v1/downloads/stream/\(encodedPath)")!)
    request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
    
    let (data, response) = try await URLSession.shared.data(for: request)
    
    guard (response as? HTTPURLResponse)?.statusCode == 200 else {
        return nil  // Metadata file doesn't exist
    }
    
    return try JSONDecoder().decode(VideoMetadata.self, from: data)
}
```

**Metadata JSON fields:**
```json
{
  "id": "7301234567890",
  "title": "Video Title",
  "description": "...",
  "uploader": "@username",
  "platform": "tiktok",
  "duration": 30,
  "duration_formatted": "0:30",
  "thumbnail": "https://...",      // External URL from source
  "webpage_url": "https://...",
  "view_count": 12345,
  "like_count": 500,
  "upload_date": "20241215",
  "upload_date_formatted": "2024-12-15",
  "downloaded_at": "2024-12-15T10:30:00"
}
```

---

## Thumbnails

Thumbnails are **external URLs** from the source platform (stored in metadata JSON).

```swift
// Option 1: Use external thumbnail URL from metadata
if let thumbnailURL = metadata.thumbnail {
    // Load from TikTok/Instagram/YouTube CDN
    imageView.load(from: URL(string: thumbnailURL)!)
}

// Option 2: Generate local thumbnail from video
import AVFoundation

func generateThumbnail(from videoURL: URL) -> UIImage? {
    let asset = AVAsset(url: videoURL)
    let generator = AVAssetImageGenerator(asset: asset)
    generator.appliesPreferredTrackTransform = true
    
    let time = CMTime(seconds: 1, preferredTimescale: 60)
    if let cgImage = try? generator.copyCGImage(at: time, actualTime: nil) {
        return UIImage(cgImage: cgImage)
    }
    return nil
}
```

---

## Download Queue

**GET** `/api/v1/downloads/queue`

```json
{
  "downloading": [...],
  "pending": [...],
  "failed": [...],
  "counts": { "downloading": 1, "pending": 5, "failed": 0, "total": 6 }
}
```

**POST** `/api/v1/downloads/retry/{download_id}` - Retry failed download

---

## Folder Structure

**GET** `/api/v1/downloads/structure`

```json
{
  "users": [
    {
      "username": "john",
      "genres": {
        "tiktok": { "count": 25, "size_formatted": "150 MB" },
        "instagram": { "count": 10, "size_formatted": "80 MB" }
      },
      "total_videos": 35,
      "total_size_formatted": "230 MB"
    }
  ],
  "total_videos": 35,
  "total_size_formatted": "230 MB"
}
```

---

## Swift Models

```swift
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

struct VideoMetadata: Codable {
    let id: String?
    let title: String?
    let description: String?
    let uploader: String?
    let platform: String?
    let duration: Int?
    let durationFormatted: String?
    let thumbnail: String?
    let webpageUrl: String?
    let viewCount: Int?
    let likeCount: Int?
    let uploadDate: String?
    let uploadDateFormatted: String?
    let downloadedAt: String?
    
    enum CodingKeys: String, CodingKey {
        case id, title, description, uploader, platform, duration, thumbnail
        case durationFormatted = "duration_formatted"
        case webpageUrl = "webpage_url"
        case viewCount = "view_count"
        case likeCount = "like_count"
        case uploadDate = "upload_date"
        case uploadDateFormatted = "upload_date_formatted"
        case downloadedAt = "downloaded_at"
    }
}
```

---

## Endpoint Summary

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/downloads/videos` | GET | List videos (filterable) |
| `/api/v1/downloads/stream/{path}` | GET | Stream video/audio/json |
| `/api/v1/downloads/structure` | GET | Folder tree with counts |
| `/api/v1/downloads/queue` | GET | Download queue status |
| `/api/v1/downloads/retry/{id}` | POST | Retry failed download |
| `/api/v1/download` | POST | Submit new download |
| `/api/v1/status/{id}` | GET | Check download status |
| `/api/v1/health` | GET | Server health (no auth) |

**Note:** The `/stream/{path}` endpoint can serve `.json` metadata files - just replace the video extension with `.json` in the path.
