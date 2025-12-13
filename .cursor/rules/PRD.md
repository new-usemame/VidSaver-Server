# Product Requirements Document: Video Download Server

## 1. Overview

A lightweight Python-based HTTPS server that receives video URLs (TikTok, Instagram) from iOS clients via share sheet and downloads them to local storage. The server runs as a background process on Mac or Raspberry Pi with minimal resource usage.

## 2. Goals

- **Zero Data Loss**: All video URLs must be persisted immediately upon receipt with confirmation sent to client
- **Reliability**: Queue-based download system with retry logic
- **Simplicity**: Single production deployment, no dev/prod split
- **Low Resource Usage**: Designed to run continuously as a background process
- **iOS Compatible**: Self-signed HTTPS certificates that work with iOS clients

## 3. Technical Stack

- **Language**: Python 3.9+
- **Web Framework**: Flask or FastAPI (lightweight HTTPS server)
- **Database**: SQLite (simple, file-based, no external dependencies)
- **Video Downloader**: yt-dlp (supports TikTok, Instagram, and many other platforms)
- **HTTPS**: Self-signed certificate with proper iOS compatibility

## 4. Core Features

### 4.1 API Endpoints

#### POST /api/v1/download
Receives video URL from client for download.

**Request Body:**
```json
{
  "url": "https://tiktok.com/@user/video/123456789",
  "client_id": "unique-device-identifier",
  "timestamp": 1234567890
}
```

**Response (Success):**
```json
{
  "status": "queued",
  "download_id": "uuid-v4",
  "message": "Video queued for download",
  "timestamp": 1234567890
}
```

**Response (Error):**
```json
{
  "status": "error",
  "error": "Invalid URL format",
  "timestamp": 1234567890
}
```

#### GET /api/v1/status/{download_id}
Check status of a download.

**Response:**
```json
{
  "download_id": "uuid-v4",
  "status": "completed|downloading|queued|failed",
  "url": "original-url",
  "progress": 85,
  "error_message": null,
  "completed_at": 1234567890
}
```

#### GET /api/v1/history
Retrieve download history (paginated).

**Query Parameters:**
- `limit`: Number of records (default: 50, max: 200)
- `offset`: Pagination offset (default: 0)

**Response:**
```json
{
  "total": 150,
  "downloads": [
    {
      "download_id": "uuid",
      "url": "original-url",
      "status": "completed",
      "filename": "video.mp4",
      "created_at": 1234567890,
      "completed_at": 1234567891
    }
  ]
}
```

#### GET /api/v1/health
Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "uptime": 86400,
  "queue_size": 3
}
```

### 4.2 Database Schema

#### downloads table
```sql
CREATE TABLE downloads (
    id TEXT PRIMARY KEY,              -- UUID v4
    url TEXT NOT NULL,                -- Original video URL
    client_id TEXT NOT NULL,          -- Client device identifier
    status TEXT NOT NULL,             -- queued|downloading|completed|failed
    filename TEXT,                    -- Downloaded filename (null until completed)
    file_path TEXT,                   -- Full path to downloaded file
    file_size INTEGER,                -- File size in bytes
    error_message TEXT,               -- Error details if failed
    retry_count INTEGER DEFAULT 0,    -- Number of retry attempts
    created_at INTEGER NOT NULL,      -- Unix timestamp
    started_at INTEGER,               -- When download started
    completed_at INTEGER,             -- When download completed
    last_updated INTEGER NOT NULL     -- Last status update
);

CREATE INDEX idx_status ON downloads(status);
CREATE INDEX idx_created_at ON downloads(created_at DESC);
CREATE INDEX idx_client_id ON downloads(client_id);
```

### 4.3 Download Queue System

- **Queue Processing**: Background worker thread that processes downloads one at a time (or configurable concurrency)
- **Retry Logic**: Failed downloads retry up to 3 times with exponential backoff (1min, 5min, 15min)
- **Status Updates**: Database updated at each stage (queued → downloading → completed/failed)
- **Disk Space Check**: Verify sufficient disk space before starting download

### 4.4 Video Downloader Configuration

Using `yt-dlp` with the following configuration:
- **Format**: Best available quality (prefer mp4)
- **Output Directory**: Configurable (default: `~/Downloads/VideoServer`)
- **Filename Pattern**: `%(title)s_%(id)s.%(ext)s`
- **Rate Limiting**: Optional rate limiting to avoid IP bans
- **User Agent Rotation**: Use random user agents
- **Cookies**: Optional cookie file support for authenticated downloads

### 4.5 Configuration

Environment variables or config file (`config.yaml`):

```yaml
server:
  host: "0.0.0.0"
  port: 8443
  cert_file: "certs/server.crt"
  key_file: "certs/server.key"

database:
  path: "data/downloads.db"

downloads:
  output_directory: "~/Downloads/VideoServer"
  max_concurrent: 1
  max_retries: 3
  retry_delays: [60, 300, 900]  # seconds

downloader:
  rate_limit: null  # or "1M" for 1MB/s
  user_agent_rotation: true
  timeout: 300  # seconds
  
logging:
  level: "INFO"
  file: "logs/server.log"
  max_size: "10MB"
  backup_count: 5
```

## 5. Security Considerations

### 5.1 HTTPS Certificate
- Generate self-signed certificate with proper iOS compatibility
- Certificate valid for internal IP and DNS name
- Include Subject Alternative Names (SAN) for iOS trust
- Client must install and trust the certificate

### 5.2 Authentication
- Optional API key authentication via header: `X-API-Key: secret-key`
- Keys stored in environment variables
- Rate limiting per client_id (e.g., 100 requests per hour)

### 5.3 Input Validation
- URL validation (whitelist domains: tiktok.com, instagram.com, etc.)
- Sanitize all inputs to prevent injection attacks
- Maximum URL length check

### 5.4 Network Security
- Firewall rules to restrict access to known client IPs (optional)
- HTTPS only, no HTTP fallback
- Request size limits

## 6. Client Integration Guide

### 6.1 Certificate Installation
Provide instructions for iOS to trust self-signed certificate:
1. Download certificate to device
2. Settings → General → VPN & Device Management
3. Install profile
4. Settings → General → About → Certificate Trust Settings
5. Enable full trust

### 6.2 API Integration
```swift
// Example Swift code for share extension
struct DownloadRequest: Codable {
    let url: String
    let client_id: String
    let timestamp: Int
}

func sendToServer(url: String) async throws {
    let request = DownloadRequest(
        url: url,
        client_id: UIDevice.current.identifierForVendor?.uuidString ?? "unknown",
        timestamp: Int(Date().timeIntervalSince1970)
    )
    
    var urlRequest = URLRequest(url: URL(string: "https://your-server.local:8443/api/v1/download")!)
    urlRequest.httpMethod = "POST"
    urlRequest.setValue("application/json", forHTTPHeaderField: "Content-Type")
    urlRequest.httpBody = try JSONEncoder().encode(request)
    
    let (data, response) = try await URLSession.shared.data(for: urlRequest)
    // Handle response and cache if failed
}
```

### 6.3 Offline Caching
Client should implement:
- Local cache for failed requests
- Retry logic when app reopens or network restored
- Clear cache after successful server confirmation

### 6.4 Response Handling
- Wait for server confirmation (download_id)
- Store download_id locally for status tracking
- Display error messages to user if immediate failure

## 7. Deployment

### 7.1 Installation Script
Provide setup script that:
1. Installs Python dependencies
2. Generates HTTPS certificate
3. Creates necessary directories
4. Initializes database
5. Creates systemd/launchd service (based on OS)

### 7.2 Running as Service

**macOS (launchd):**
```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.videoserver.download</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/local/bin/python3</string>
        <string>/path/to/server.py</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
</dict>
</plist>
```

**Linux/Raspberry Pi (systemd):**
```ini
[Unit]
Description=Video Download Server
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/video-server
ExecStart=/usr/bin/python3 /home/pi/video-server/server.py
Restart=always

[Install]
WantedBy=multi-user.target
```

### 7.3 Monitoring
- Log rotation configured
- Health endpoint for monitoring
- Disk space alerts (optional)

## 8. Error Handling

### 8.1 Common Errors
- **Network errors**: Retry with backoff
- **Invalid URL**: Return error to client immediately
- **Download failure**: Retry up to max_retries
- **Disk full**: Log error, notify client, pause queue
- **yt-dlp errors**: Log details, mark as failed

### 8.2 Logging
- All requests logged with timestamp, client_id, URL
- Download start/complete/failure logged
- Error stack traces captured
- Rotation to prevent disk fill

## 9. Success Criteria

- ✅ Server accepts URLs from iOS client
- ✅ Immediate confirmation sent to client (< 500ms)
- ✅ All URLs persisted to database before confirmation
- ✅ Videos downloaded successfully from TikTok and Instagram
- ✅ Failed downloads retry automatically
- ✅ HTTPS works with self-signed cert on iOS
- ✅ Server runs continuously as background process
- ✅ Resource usage < 100MB RAM idle, < 500MB during download
- ✅ No data loss even on server crash/restart

## 10. Future Enhancements (Out of Scope v1)

- Web UI for browsing downloads
- Multiple download locations
- Automatic duplicate detection
- Download scheduling
- Video transcoding
- Cloud backup integration
- Multi-user support

