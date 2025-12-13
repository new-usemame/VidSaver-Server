# iOS Integration Guide v2.0

Complete guide for integrating the Video Download Server with iOS apps. This guide covers the new QR code setup flow, multi-user support, genre-based organization, and best practices.

## Table of Contents

- [Overview](#overview)
- [What's New in v2.0](#whats-new-in-v20)
- [Quick Setup with QR Code](#quick-setup-with-qr-code)
- [Server Setup](#server-setup)
- [API Reference](#api-reference)
- [iOS Share Extension Integration](#ios-share-extension-integration)
- [Swift Code Examples](#swift-code-examples)
- [Testing & Debugging](#testing--debugging)
- [Best Practices](#best-practices)

---

## Overview

The Video Download Server provides a REST API for downloading videos from multiple platforms (TikTok, Instagram, YouTube, PDFs, eBooks, etc.) with multi-user support and automatic genre-based organization.

### Key Features for iOS

- **🎯 QR Code Setup**: Scan a QR code to instantly configure your app - no manual IP entry!
- **👥 Multi-User Support**: Each user has their own organized folder structure
- **🎨 Genre-Based Organization**: Content automatically categorized by type
- **⚡ Fast Response**: < 500ms response time for immediate user feedback
- **🔄 Background Processing**: Downloads happen asynchronously on the server
- **📊 Status Tracking**: Query download status anytime with detailed progress
- **💾 Zero Data Loss**: All requests persisted before confirmation
- **🔐 Optional API Key Authentication**: Secure your server with API keys
- **🌐 LAN & WAN Support**: Works on local network and over internet

### Folder Structure

Downloads are automatically organized as:
```
~/Downloads/VidSaver/
├── {username}/           # Each user gets their own folder
│   ├── tiktok/          # TikTok videos
│   ├── instagram/       # Instagram posts/reels/stories
│   ├── youtube/         # YouTube videos
│   ├── pdf/             # PDF documents
│   ├── ebook/           # eBooks (epub, mobi, azw)
│   └── unknown/         # Content with undetected genre
```

**Note**: Usernames and folders are always lowercase for consistency.

---

## What's New in v2.0

### 🎯 1. QR Code Setup (NEW!)

The easiest way to connect! Your server generates a QR code containing:
- **LAN IP**: For use on the same WiFi network
- **WAN IP**: For remote access (requires port forwarding)
- **Port & Protocol**: HTTP or HTTPS with SSL
- **API Key**: If authentication is configured
- **Version**: Server version for compatibility checking

**How it works:**
1. Server admin opens: `http://SERVER_IP:58443/api/v1/config/setup`
2. QR code displays with connection info
3. User scans QR code in iOS app
4. App automatically configures itself
5. Ready to download!

**QR Code Data Format (JSON):**
```json
{
  "lan": "192.168.1.119:58443",
  "wan": "68.186.221.57:58443",
  "protocol": "http",
  "key": "your-api-key-if-configured",
  "v": "2.0"
}
```

### 👥 2. Multi-User Support (NEW!)

- Each download request includes a `username` field
- Users are automatically created on first request
- All downloads organized per user
- Username validation: alphanumeric only (letters and numbers)
- Case-insensitive: "John" and "john" are the same user

### 🎨 3. Genre Detection (NEW!)

- Automatic content categorization
- Detection methods:
  1. **URL Pattern Matching** (fast, primary method)
  2. **yt-dlp Extractor** (fallback during download)
- Supported genres:
  - `tiktok` - TikTok videos
  - `instagram` - Instagram posts/reels/stories
  - `youtube` - YouTube videos/shorts
  - `pdf` - PDF documents
  - `ebook` - eBooks (epub, mobi, azw3)
  - `unknown` - Other content
- Genre detection errors are tracked but don't prevent downloads

### 🛡️ 4. Reliability Improvements (NEW!)

- **Auto-Restart**: Server restarts automatically after config changes
- **Database Backups**: Automatic backups before schema migrations
- **Improved Logging**: Better error tracking and debugging
- **Connection Management**: Better database connection handling
- **Config Validation**: YAML validation prevents invalid configurations

---

## Quick Setup with QR Code

### Step 1: Server Admin Opens Setup Page

On the server (Mac/Raspberry Pi):
1. Open menu bar app (📱 Video Server)
2. Click **"📱 QR Code Setup"**
3. Or browse to: `http://localhost:58443/api/v1/config/setup`

### Step 2: iOS User Scans QR Code

In your iOS app:

```swift
import AVFoundation
import SwiftUI

struct QRScannerView: UIViewControllerRepresentable {
    @Binding var scannedData: String?
    
    func makeUIViewController(context: Context) -> QRScanViewController {
        return QRScanViewController(delegate: context.coordinator)
    }
    
    func updateUIViewController(_ uiViewController: QRScanViewController, context: Context) {}
    
    func makeCoordinator() -> Coordinator {
        Coordinator(self)
    }
    
    class Coordinator: NSObject, AVCaptureMetadataOutputObjectsDelegate {
        let parent: QRScannerView
        
        init(_ parent: QRScannerView) {
            self.parent = parent
        }
        
        func metadataOutput(_ output: AVCaptureMetadataOutput, 
                           didOutput metadataObjects: [AVMetadataObject], 
                           from connection: AVCaptureConnection) {
            if let metadataObject = metadataObjects.first {
                guard let readableObject = metadataObject as? AVMetadataMachineReadableCodeObject else { return }
                guard let stringValue = readableObject.stringValue else { return }
                
                AudioServicesPlaySystemSound(SystemSoundID(kSystemSoundID_Vibrate))
                parent.scannedData = stringValue
            }
        }
    }
}

// Parse QR code data
struct ServerConfig: Codable {
    let lan: String
    let wan: String?
    let protocol: String
    let key: String?
    let v: String
}

func parseQRCode(_ data: String) -> ServerConfig? {
    guard let jsonData = data.data(using: .utf8) else { return nil }
    return try? JSONDecoder().decode(ServerConfig.self, from: jsonData)
}

// Save configuration
func saveServerConfig(_ config: ServerConfig, useWAN: Bool = false) {
    let host = useWAN ? (config.wan ?? config.lan) : config.lan
    UserDefaults.standard.set("\(config.protocol)://\(host)", forKey: "serverURL")
    UserDefaults.standard.set(config.key, forKey: "apiKey")
    UserDefaults.standard.set(config.v, forKey: "serverVersion")
}
```

### Step 3: Choose Connection Type

Present user with choice:

```swift
struct ConnectionChoiceView: View {
    let config: ServerConfig
    @Environment(\.dismiss) var dismiss
    
    var body: some View {
        VStack(spacing: 20) {
            Text("Choose Connection Type")
                .font(.title)
            
            // LAN Option
            VStack(alignment: .leading) {
                Text("📱 Local Network")
                    .font(.headline)
                Text("Use when on the same WiFi")
                    .font(.caption)
                    .foregroundColor(.secondary)
                Text("http://\(config.lan)")
                    .font(.system(.body, design: .monospaced))
                    .foregroundColor(.blue)
            }
            .padding()
            .background(Color.blue.opacity(0.1))
            .cornerRadius(10)
            .onTapGesture {
                saveServerConfig(config, useWAN: false)
                dismiss()
            }
            
            // WAN Option (if available)
            if let wan = config.wan {
                VStack(alignment: .leading) {
                    Text("🌐 Internet Access")
                        .font(.headline)
                    Text("Access from anywhere (requires port forwarding)")
                        .font(.caption)
                        .foregroundColor(.secondary)
                    Text("http://\(wan)")
                        .font(.system(.body, design: .monospaced))
                        .foregroundColor(.green)
                }
                .padding()
                .background(Color.green.opacity(0.1))
                .cornerRadius(10)
                .onTapGesture {
                    saveServerConfig(config, useWAN: true)
                    dismiss()
                }
            }
        }
        .padding()
    }
}
```

---

## Server Setup

### 1. Start the Server

Double-click **"Start Video Server.command"** to launch the menu bar app, or:

```bash
cd "/path/to/TikTok-Downloader-Server"
./manage.sh start
```

The server will be accessible at:
- **LAN**: `http://YOUR_LOCAL_IP:58443`
- **WAN**: `http://YOUR_PUBLIC_IP:58443` (requires port forwarding)

### 2. Configuration

The server uses `config/config.yaml`. You can edit it via:
- **Web Interface**: Click "🎛️ Config Editor" in menu bar app
- **Manual Edit**: `nano config/config.yaml`

**Key Settings for iOS:**

```yaml
server:
  host: "0.0.0.0"        # Listen on all interfaces
  port: 58443            # Server port
  ssl:
    enabled: false       # Set true for HTTPS
    cert_file: "certs/server.crt"
    key_file: "certs/server.key"

downloads:
  root_directory: "~/Downloads/VidSaver"  # Base folder for all users
  max_concurrent: 1     # Downloads at once
  max_retries: 3        # Retry failed downloads

security:
  api_keys: []          # Optional: ["your-secret-key"]
  rate_limit_per_client: 100  # Per hour

logging:
  level: "INFO"         # DEBUG for troubleshooting
```

### 3. Port Forwarding (for Internet Access)

To access your server from anywhere:

1. Log in to your router (usually `192.168.1.1`)
2. Find "Port Forwarding" or "Virtual Server"
3. Forward port **58443** to your server's LAN IP
4. Save and restart router
5. Test with: `http://YOUR_PUBLIC_IP:58443/api/v1/health`

### 4. iOS App Transport Security

**For HTTP (Development):**

Add to your iOS app's `Info.plist`:

```xml
<key>NSAppTransportSecurity</key>
<dict>
    <key>NSAllowsLocalNetworking</key>
    <true/>
</dict>
```

**For HTTPS (Production):**

1. Server generates self-signed certificate
2. Install certificate on iOS device
3. Trust certificate in Settings
4. See [SSL_SETUP.md](./SSL_SETUP.md) for details

---

## API Reference

### Base URL

```
http://YOUR_SERVER_IP:58443/api/v1
```

All timestamps are in ISO 8601 format (UTC).

### Authentication (Optional)

If API keys are configured, include in headers:

```swift
request.setValue("Bearer YOUR_API_KEY", forHTTPHeaderField: "Authorization")
```

---

### 1. Submit Download

**POST** `/download`

Submit a URL for download. Server responds immediately (< 500ms), download happens in background.

**Request Body:**
```json
{
  "url": "https://www.tiktok.com/@user/video/123456",
  "username": "john",
  "client_id": "ios-app-v1.0"
}
```

**Fields:**
- `url` (required): Any valid URL (TikTok, Instagram, YouTube, PDF, etc.)
- `username` (required): Alphanumeric only, case-insensitive, 1-100 chars
- `client_id` (optional): Your app identifier for tracking

**Response (201 Created):**
```json
{
  "success": true,
  "download_id": "550e8400-e29b-41d4-a716-446655440000",
  "message": "Download queued successfully",
  "status": "pending",
  "username": "john",
  "genre": "tiktok",
  "submitted_at": "2025-11-18T02:30:00Z"
}
```

**Error Responses:**

*400 Bad Request - Invalid Username:*
```json
{
  "detail": [
    {
      "type": "value_error",
      "loc": ["body", "username"],
      "msg": "Username must be alphanumeric (letters and numbers only)"
    }
  ]
}
```

*400 Bad Request - Invalid URL:*
```json
{
  "detail": [
    {
      "type": "value_error",
      "loc": ["body", "url"],
      "msg": "Invalid URL format"
    }
  ]
}
```

---

### 2. Check Download Status

**GET** `/status/{download_id}`

Get the current status and details of a download.

**Response (200 OK):**
```json
{
  "download_id": "550e8400-e29b-41d4-a716-446655440000",
  "url": "https://www.tiktok.com/@user/video/123456",
  "status": "completed",
  "username": "john",
  "genre": "tiktok",
  "submitted_at": "2025-11-18T02:30:00Z",
  "started_at": "2025-11-18T02:30:02Z",
  "completed_at": "2025-11-18T02:30:15Z",
  "file_path": "abc123_My_Video.mp4",
  "file_size": 5242880,
  "error_message": null,
  "genre_detection_error": null
}
```

**Status Values:**
- `pending` - Queued, waiting to start
- `downloading` - Currently downloading from source
- `completed` - Successfully downloaded to server
- `failed` - Download failed (check `error_message`)

**Fields:**
- `file_path`: Filename only (not full path) when completed
- `file_size`: Bytes, when completed
- `error_message`: Error details if status is `failed`
- `genre_detection_error`: Genre detection error (download may still succeed)

**Error Responses:**

*404 Not Found:*
```json
{
  "detail": "Download not found"
}
```

---

### 3. Get Download History

**GET** `/history?limit=50&offset=0&username=john&status=completed`

Retrieve download history with filtering and pagination.

**Query Parameters:**
- `limit` (optional): Results per page (1-100, default: 50)
- `offset` (optional): Pagination offset (default: 0)
- `username` (optional): Filter by username
- `status` (optional): Filter by status (pending/downloading/completed/failed)
- `client_id` (optional): Filter by client identifier

**Response (200 OK):**
```json
[
  {
    "download_id": "550e8400-e29b-41d4-a716-446655440000",
    "url": "https://www.tiktok.com/@user/video/123456",
    "status": "completed",
    "username": "john",
    "genre": "tiktok",
    "submitted_at": "2025-11-18T02:30:00Z",
    "started_at": "2025-11-18T02:30:02Z",
    "completed_at": "2025-11-18T02:30:15Z",
    "file_path": "abc123_My_Video.mp4",
    "file_size": 5242880,
    "error_message": null,
    "genre_detection_error": null
  },
  ...
]
```

**Use Cases:**
- Show user their download history: `?username=john&limit=20`
- Monitor pending downloads: `?status=pending`
- App-specific downloads: `?client_id=ios-app-v1.0`

---

### 4. Server Health

**GET** `/health`

Check if server is running and healthy.

**Response (200 OK):**
```json
{
  "status": "healthy",
  "timestamp": "2025-11-18T02:30:00Z",
  "version": "2.0.0",
  "database": {
    "connected": true,
    "total_downloads": 150
  }
}
```

---

### 5. Connection Info (for QR Setup)

**GET** `/config/connection`

Get server connection information. Used internally by setup page.

**Response (200 OK):**
```json
{
  "server_name": "Video Download Server",
  "version": "2.0.0",
  "lan": {
    "ip": "192.168.1.119",
    "url": "http://192.168.1.119:58443",
    "available": true
  },
  "wan": {
    "ip": "68.186.221.57",
    "url": "http://68.186.221.57:58443",
    "available": true
  },
  "port": 58443,
  "protocol": "http",
  "ssl_enabled": false,
  "api_key": "your-key-if-configured",
  "supported_genres": ["tiktok", "instagram", "youtube", "pdf", "ebook"],
  "setup_timestamp": "2025-11-18T02:30:00Z"
}
```

---

## iOS Share Extension Integration

### 1. Create Share Extension

1. In Xcode: **File → New → Target → Share Extension**
2. Name it "Save to VidSaver" or similar
3. Add to your app target

### 2. Configure Info.plist

Add supported content types:

```xml
<key>NSExtension</key>
<dict>
    <key>NSExtensionAttributes</key>
    <dict>
        <key>NSExtensionActivationRule</key>
        <dict>
            <key>NSExtensionActivationSupportsWebURLWithMaxCount</key>
            <integer>1</integer>
        </dict>
    </dict>
    <key>NSExtensionMainStoryboard</key>
    <string>MainInterface</string>
    <key>NSExtensionPointIdentifier</key>
    <string>com.apple.share-services</string>
</dict>
```

### 3. Setup App Group

Share data between app and extension:

1. In Xcode target capabilities, enable **App Groups**
2. Create group: `group.com.yourcompany.vidsaver`
3. Enable for both main app and share extension

### 4. Configure App Transport Security

Add to main app's `Info.plist`:

```xml
<key>NSAppTransportSecurity</key>
<dict>
    <key>NSAllowsLocalNetworking</key>
    <true/>
</dict>
```

---

## Swift Code Examples

### Complete API Client

```swift
import Foundation

class VideoDownloadAPI {
    static let shared = VideoDownloadAPI()
    
    // Configuration stored in UserDefaults
    private var baseURL: String {
        UserDefaults(suiteName: "group.com.yourcompany.vidsaver")?
            .string(forKey: "serverURL") ?? "http://192.168.1.100:58443/api/v1"
    }
    
    private var apiKey: String? {
        UserDefaults(suiteName: "group.com.yourcompany.vidsaver")?
            .string(forKey: "apiKey")
    }
    
    private var username: String {
        UserDefaults(suiteName: "group.com.yourcompany.vidsaver")?
            .string(forKey: "username") ?? "defaultuser"
    }
    
    // MARK: - Models
    
    struct DownloadRequest: Codable {
        let url: String
        let username: String
        let clientId: String?
        
        enum CodingKeys: String, CodingKey {
            case url, username
            case clientId = "client_id"
        }
    }
    
    struct DownloadResponse: Codable {
        let success: Bool
        let downloadId: String
        let message: String
        let status: String
        let username: String
        let genre: String
        let submittedAt: Date
        
        enum CodingKeys: String, CodingKey {
            case success, message, status, username, genre
            case downloadId = "download_id"
            case submittedAt = "submitted_at"
        }
    }
    
    struct StatusResponse: Codable {
        let downloadId: String
        let url: String
        let status: String
        let username: String
        let genre: String
        let submittedAt: Date
        let startedAt: Date?
        let completedAt: Date?
        let filePath: String?
        let fileSize: Int?
        let errorMessage: String?
        let genreDetectionError: String?
        
        enum CodingKeys: String, CodingKey {
            case url, status, username, genre
            case downloadId = "download_id"
            case submittedAt = "submitted_at"
            case startedAt = "started_at"
            case completedAt = "completed_at"
            case filePath = "file_path"
            case fileSize = "file_size"
            case errorMessage = "error_message"
            case genreDetectionError = "genre_detection_error"
        }
    }
    
    struct HealthResponse: Codable {
        let status: String
        let timestamp: Date
        let version: String
        let database: DatabaseInfo
        
        struct DatabaseInfo: Codable {
            let connected: Bool
            let totalDownloads: Int
            
            enum CodingKeys: String, CodingKey {
                case connected
                case totalDownloads = "total_downloads"
            }
        }
    }
    
    // MARK: - API Methods
    
    /// Submit a download request
    func submitDownload(
        url: String,
        username: String? = nil,
        completion: @escaping (Result<DownloadResponse, Error>) -> Void
    ) {
        let endpoint = "\(baseURL)/download"
        
        guard let requestURL = URL(string: endpoint) else {
            completion(.failure(APIError.invalidURL))
            return
        }
        
        var request = URLRequest(url: requestURL)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        
        // Add API key if configured
        if let apiKey = apiKey {
            request.setValue("Bearer \(apiKey)", forHTTPHeaderField: "Authorization")
        }
        
        let downloadRequest = DownloadRequest(
            url: url,
            username: username ?? self.username,
            clientId: "ios-app-v2.0"
        )
        
        do {
            let encoder = JSONEncoder()
            encoder.keyEncodingStrategy = .convertToSnakeCase
            request.httpBody = try encoder.encode(downloadRequest)
        } catch {
            completion(.failure(error))
            return
        }
        
        let task = URLSession.shared.dataTask(with: request) { data, response, error in
            if let error = error {
                completion(.failure(error))
                return
            }
            
            guard let data = data else {
                completion(.failure(APIError.noData))
                return
            }
            
            // Check for HTTP errors
            if let httpResponse = response as? HTTPURLResponse,
               httpResponse.statusCode != 201 {
                if let errorMessage = try? JSONDecoder().decode(ErrorResponse.self, from: data) {
                    completion(.failure(APIError.serverError(errorMessage.detail)))
                    return
                }
                completion(.failure(APIError.httpError(httpResponse.statusCode)))
                return
            }
            
            do {
                let decoder = JSONDecoder()
                decoder.keyDecodingStrategy = .convertFromSnakeCase
                decoder.dateDecodingStrategy = .iso8601
                let response = try decoder.decode(DownloadResponse.self, from: data)
                completion(.success(response))
            } catch {
                completion(.failure(error))
            }
        }
        
        task.resume()
    }
    
    /// Check download status
    func checkStatus(
        downloadId: String,
        completion: @escaping (Result<StatusResponse, Error>) -> Void
    ) {
        let endpoint = "\(baseURL)/status/\(downloadId)"
        
        guard let requestURL = URL(string: endpoint) else {
            completion(.failure(APIError.invalidURL))
            return
        }
        
        var request = URLRequest(url: requestURL)
        
        // Add API key if configured
        if let apiKey = apiKey {
            request.setValue("Bearer \(apiKey)", forHTTPHeaderField: "Authorization")
        }
        
        let task = URLSession.shared.dataTask(with: request) { data, response, error in
            if let error = error {
                completion(.failure(error))
                return
            }
            
            guard let data = data else {
                completion(.failure(APIError.noData))
                return
            }
            
            do {
                let decoder = JSONDecoder()
                decoder.keyDecodingStrategy = .convertFromSnakeCase
                decoder.dateDecodingStrategy = .iso8601
                let response = try decoder.decode(StatusResponse.self, from: data)
                completion(.success(response))
            } catch {
                completion(.failure(error))
            }
        }
        
        task.resume()
    }
    
    /// Get download history
    func getHistory(
        username: String? = nil,
        status: String? = nil,
        limit: Int = 50,
        offset: Int = 0,
        completion: @escaping (Result<[StatusResponse], Error>) -> Void
    ) {
        var components = URLComponents(string: "\(baseURL)/history")!
        var queryItems: [URLQueryItem] = []
        
        queryItems.append(URLQueryItem(name: "limit", value: String(limit)))
        queryItems.append(URLQueryItem(name: "offset", value: String(offset)))
        
        if let username = username {
            queryItems.append(URLQueryItem(name: "username", value: username))
        }
        
        if let status = status {
            queryItems.append(URLQueryItem(name: "status", value: status))
        }
        
        components.queryItems = queryItems
        
        guard let requestURL = components.url else {
            completion(.failure(APIError.invalidURL))
            return
        }
        
        var request = URLRequest(url: requestURL)
        
        // Add API key if configured
        if let apiKey = apiKey {
            request.setValue("Bearer \(apiKey)", forHTTPHeaderField: "Authorization")
        }
        
        let task = URLSession.shared.dataTask(with: request) { data, response, error in
            if let error = error {
                completion(.failure(error))
                return
            }
            
            guard let data = data else {
                completion(.failure(APIError.noData))
                return
            }
            
            do {
                let decoder = JSONDecoder()
                decoder.keyDecodingStrategy = .convertFromSnakeCase
                decoder.dateDecodingStrategy = .iso8601
                let response = try decoder.decode([StatusResponse].self, from: data)
                completion(.success(response))
            } catch {
                completion(.failure(error))
            }
        }
        
        task.resume()
    }
    
    /// Check server health
    func checkHealth(completion: @escaping (Result<HealthResponse, Error>) -> Void) {
        let endpoint = "\(baseURL)/health"
        
        guard let requestURL = URL(string: endpoint) else {
            completion(.failure(APIError.invalidURL))
            return
        }
        
        let task = URLSession.shared.dataTask(with: requestURL) { data, response, error in
            if let error = error {
                completion(.failure(error))
                return
            }
            
            guard let data = data else {
                completion(.failure(APIError.noData))
                return
            }
            
            do {
                let decoder = JSONDecoder()
                decoder.keyDecodingStrategy = .convertFromSnakeCase
                decoder.dateDecodingStrategy = .iso8601
                let response = try decoder.decode(HealthResponse.self, from: data)
                completion(.success(response))
            } catch {
                completion(.failure(error))
            }
        }
        
        task.resume()
    }
    
    // MARK: - Error Types
    
    struct ErrorResponse: Codable {
        let detail: String
    }
    
    enum APIError: LocalizedError {
        case invalidURL
        case noData
        case serverError(String)
        case httpError(Int)
        
        var errorDescription: String? {
            switch self {
            case .invalidURL:
                return "Invalid server URL"
            case .noData:
                return "No data received from server"
            case .serverError(let message):
                return message
            case .httpError(let code):
                return "HTTP error: \(code)"
            }
        }
    }
}
```

### Share Extension Implementation

```swift
import UIKit
import Social

class ShareViewController: UIViewController {
    
    private let api = VideoDownloadAPI.shared
    
    private var activityIndicator: UIActivityIndicatorView!
    private var statusLabel: UILabel!
    
    override func viewDidLoad() {
        super.viewDidLoad()
        
        setupUI()
        extractAndSubmitURL()
    }
    
    private func setupUI() {
        view.backgroundColor = .systemBackground
        
        // Activity indicator
        activityIndicator = UIActivityIndicatorView(style: .large)
        activityIndicator.center = view.center
        activityIndicator.startAnimating()
        view.addSubview(activityIndicator)
        
        // Status label
        statusLabel = UILabel()
        statusLabel.text = "Sending to server..."
        statusLabel.textAlignment = .center
        statusLabel.frame = CGRect(
            x: 20,
            y: view.center.y + 50,
            width: view.bounds.width - 40,
            height: 30
        )
        view.addSubview(statusLabel)
    }
    
    private func extractAndSubmitURL() {
        guard let item = extensionContext?.inputItems.first as? NSExtensionItem,
              let attachments = item.attachments else {
            showError("No URL found")
            return
        }
        
        for attachment in attachments {
            if attachment.hasItemConformingToTypeIdentifier("public.url") {
                attachment.loadItem(forTypeIdentifier: "public.url", options: nil) { [weak self] item, error in
                    guard let self = self else { return }
                    
                    if let error = error {
                        DispatchQueue.main.async {
                            self.showError(error.localizedDescription)
                        }
                        return
                    }
                    
                    if let url = item as? URL {
                        self.submitURL(url)
                    } else {
                        DispatchQueue.main.async {
                            self.showError("Invalid URL")
                        }
                    }
                }
                return
            }
        }
        
        showError("No URL found in shared content")
    }
    
    private func submitURL(_ url: URL) {
        api.submitDownload(url: url.absoluteString) { [weak self] result in
            DispatchQueue.main.async {
                guard let self = self else { return }
                
                self.activityIndicator.stopAnimating()
                
                switch result {
                case .success(let response):
                    self.showSuccess(response: response)
                    
                case .failure(let error):
                    self.showError(error.localizedDescription)
                }
            }
        }
    }
    
    private func showSuccess(response: VideoDownloadAPI.DownloadResponse) {
        statusLabel.text = "✓ Saved!"
        
        // Show genre-specific message
        let genreEmoji: String
        switch response.genre {
        case "tiktok": genreEmoji = "🎵"
        case "instagram": genreEmoji = "📸"
        case "youtube": genreEmoji = "🎥"
        case "pdf": genreEmoji = "📄"
        case "ebook": genreEmoji = "📚"
        default: genreEmoji = "💾"
        }
        
        let alert = UIAlertController(
            title: "\(genreEmoji) Downloading",
            message: "Your \(response.genre) content is being downloaded to the server.",
            preferredStyle: .alert
        )
        
        alert.addAction(UIAlertAction(title: "Done", style: .default) { [weak self] _ in
            self?.extensionContext?.completeRequest(returningItems: nil)
        })
        
        present(alert, animated: true)
    }
    
    private func showError(_ message: String) {
        statusLabel.text = "✗ Error"
        
        let alert = UIAlertController(
            title: "Error",
            message: message,
            preferredStyle: .alert
        )
        
        alert.addAction(UIAlertAction(title: "Cancel", style: .cancel) { [weak self] _ in
            self?.extensionContext?.cancelRequest(withError: NSError(domain: "ShareExtension", code: -1))
        })
        
        alert.addAction(UIAlertAction(title: "Retry", style: .default) { [weak self] _ in
            self?.extractAndSubmitURL()
        })
        
        present(alert, animated: true)
    }
}
```

### SwiftUI Main App Example

```swift
import SwiftUI

struct ContentView: View {
    @StateObject private var viewModel = DownloadViewModel()
    @State private var showingQRScanner = false
    @State private var showingSettings = false
    
    var body: some View {
        NavigationView {
            VStack {
                if viewModel.isConfigured {
                    // Configured - show downloads
                    downloadsList
                } else {
                    // Not configured - show setup
                    setupView
                }
            }
            .navigationTitle("VidSaver")
            .toolbar {
                ToolbarItem(placement: .navigationBarTrailing) {
                    Button {
                        showingSettings = true
                    } label: {
                        Image(systemName: "gear")
                    }
                }
            }
            .sheet(isPresented: $showingQRScanner) {
                QRScannerSheet { config in
                    viewModel.configureFromQR(config)
                }
            }
            .sheet(isPresented: $showingSettings) {
                SettingsView(viewModel: viewModel)
            }
        }
    }
    
    private var setupView: some View {
        VStack(spacing: 30) {
            Image(systemName: "qrcode.viewfinder")
                .font(.system(size: 80))
                .foregroundColor(.blue)
            
            Text("Connect to Server")
                .font(.title)
            
            Text("Scan the QR code from your Video Download Server to get started.")
                .multilineTextAlignment(.center)
                .foregroundColor(.secondary)
                .padding(.horizontal)
            
            Button {
                showingQRScanner = true
            } label: {
                Label("Scan QR Code", systemImage: "qrcode.viewfinder")
                    .frame(maxWidth: .infinity)
                    .padding()
                    .background(Color.blue)
                    .foregroundColor(.white)
                    .cornerRadius(10)
            }
            .padding(.horizontal)
            
            Button("Enter Manually") {
                showingSettings = true
            }
            .foregroundColor(.blue)
        }
        .padding()
    }
    
    private var downloadsList: some View {
        VStack {
            // Server status
            HStack {
                Circle()
                    .fill(viewModel.serverHealthy ? Color.green : Color.red)
                    .frame(width: 8, height: 8)
                
                Text(viewModel.serverHealthy ? "Connected" : "Disconnected")
                    .font(.caption)
                    .foregroundColor(.secondary)
                
                Spacer()
                
                Text(viewModel.username)
                    .font(.caption)
                    .foregroundColor(.secondary)
            }
            .padding(.horizontal)
            .padding(.vertical, 8)
            
            // Downloads list
            List {
                ForEach(viewModel.downloads) { download in
                    DownloadRow(download: download)
                }
            }
            .refreshable {
                await viewModel.refresh()
            }
        }
        .onAppear {
            Task {
                await viewModel.loadDownloads()
                await viewModel.checkHealth()
            }
        }
    }
}

struct DownloadRow: View {
    let download: VideoDownloadAPI.StatusResponse
    
    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                genreIcon
                
                VStack(alignment: .leading, spacing: 4) {
                    if let filename = download.filePath {
                        Text(filename)
                            .font(.headline)
                            .lineLimit(1)
                    } else {
                        Text(download.url)
                            .font(.headline)
                            .lineLimit(1)
                    }
                    
                    HStack {
                        statusBadge
                        
                        if let fileSize = download.fileSize {
                            Text(ByteCountFormatter.string(fromByteCount: Int64(fileSize), countStyle: .file))
                                .font(.caption)
                                .foregroundColor(.secondary)
                        }
                    }
                }
                
                Spacer()
            }
            
            if let error = download.errorMessage {
                Text(error)
                    .font(.caption)
                    .foregroundColor(.red)
                    .lineLimit(2)
            }
        }
        .padding(.vertical, 4)
    }
    
    private var genreIcon: some View {
        let (icon, color): (String, Color) = {
            switch download.genre {
            case "tiktok": return ("music.note", .pink)
            case "instagram": return ("camera", .purple)
            case "youtube": return ("play.rectangle", .red)
            case "pdf": return ("doc", .orange)
            case "ebook": return ("book", .blue)
            default: return ("questionmark.circle", .gray)
            }
        }()
        
        return Image(systemName: icon)
            .foregroundColor(color)
            .frame(width: 30)
    }
    
    private var statusBadge: some View {
        let (text, color): (String, Color) = {
            switch download.status {
            case "pending": return ("⏳ Queued", .orange)
            case "downloading": return ("⬇️ Downloading", .blue)
            case "completed": return ("✓ Done", .green)
            case "failed": return ("✗ Failed", .red)
            default: return (download.status, .gray)
            }
        }()
        
        return Text(text)
            .font(.caption)
            .foregroundColor(color)
    }
}

@MainActor
class DownloadViewModel: ObservableObject {
    @Published var downloads: [VideoDownloadAPI.StatusResponse] = []
    @Published var isConfigured = false
    @Published var serverHealthy = false
    @Published var username = "defaultuser"
    
    private let api = VideoDownloadAPI.shared
    private let defaults = UserDefaults(suiteName: "group.com.yourcompany.vidsaver")!
    
    init() {
        isConfigured = defaults.string(forKey: "serverURL") != nil
        username = defaults.string(forKey: "username") ?? "defaultuser"
    }
    
    func configureFromQR(_ config: ServerConfig) {
        // User chooses LAN or WAN
        // For simplicity, using LAN here
        defaults.set("http://\(config.lan)", forKey: "serverURL")
        defaults.set(config.key, forKey: "apiKey")
        defaults.set("2.0", forKey: "serverVersion")
        
        isConfigured = true
        
        Task {
            await checkHealth()
            await loadDownloads()
        }
    }
    
    func loadDownloads() async {
        api.getHistory(username: username, limit: 50, offset: 0) { [weak self] result in
            if case .success(let downloads) = result {
                DispatchQueue.main.async {
                    self?.downloads = downloads.map { DownloadRowModel(status: $0) }
                }
            }
        }
    }
    
    func checkHealth() async {
        api.checkHealth { [weak self] result in
            DispatchQueue.main.async {
                self?.serverHealthy = (try? result.get()) != nil
            }
        }
    }
    
    func refresh() async {
        await checkHealth()
        await loadDownloads()
    }
}

// Make StatusResponse Identifiable for List
extension VideoDownloadAPI.StatusResponse: Identifiable {
    var id: String { downloadId }
}

struct ServerConfig: Codable {
    let lan: String
    let wan: String?
    let protocol: String
    let key: String?
    let v: String
}
```

---

## Testing & Debugging

### 1. Test Server Connection

```swift
func testServerConnection() {
    VideoDownloadAPI.shared.checkHealth { result in
        switch result {
        case .success(let health):
            print("✓ Server is healthy")
            print("  Version: \(health.version)")
            print("  Database: \(health.database.connected ? "connected" : "disconnected")")
            print("  Total downloads: \(health.database.totalDownloads)")
            
        case .failure(let error):
            print("✗ Connection failed: \(error.localizedDescription)")
        }
    }
}
```

### 2. Test Download Submission

```swift
func testDownload() {
    let testURL = "https://www.tiktok.com/@test/video/123"
    
    VideoDownloadAPI.shared.submitDownload(url: testURL, username: "testuser") { result in
        switch result {
        case .success(let response):
            print("✓ Download queued")
            print("  ID: \(response.downloadId)")
            print("  Genre: \(response.genre)")
            print("  Status: \(response.status)")
            
        case .failure(let error):
            print("✗ Failed: \(error.localizedDescription)")
        }
    }
}
```

### 3. cURL Commands for Testing

Test the API from Terminal (replace IP address):

```bash
# Check health
curl http://192.168.1.119:58443/api/v1/health

# Submit download
curl -X POST http://192.168.1.119:58443/api/v1/download \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://www.tiktok.com/@user/video/123",
    "username": "testuser",
    "client_id": "curl-test"
  }'

# Check status (replace with actual download_id)
curl http://192.168.1.119:58443/api/v1/status/550e8400-e29b-41d4-a716-446655440000

# Get history
curl "http://192.168.1.119:58443/api/v1/history?username=testuser&limit=10"

# With API key
curl -H "Authorization: Bearer your-api-key" \
  http://192.168.1.119:58443/api/v1/health
```

### 4. Common Issues

**❌ "Connection refused"**
- ✓ Verify server is running: Menu bar icon should be visible
- ✓ Check IP address is correct
- ✓ Ensure you're on the same network (for LAN)
- ✓ Test with browser: `http://IP:58443/docs`

**❌ "Username validation failed"**
- ✓ Use only letters and numbers (no spaces or special characters)
- ✓ Examples: `john`, `user123`, `JohnDoe` (becomes `johndoe`)
- ✗ Bad: `john-doe`, `john.doe`, `john doe`

**❌ "Invalid URL format"**
- ✓ URL must start with `http://` or `https://`
- ✓ URL must be properly formatted
- ✓ URL length: 10-2048 characters

**❌ "SSL certificate error" (HTTPS)**
- ✓ Install server certificate on iOS device
- ✓ Trust certificate in Settings
- ✓ Or use HTTP with `NSAllowsLocalNetworking=true`
- ✓ See [SSL_SETUP.md](./SSL_SETUP.md)

**❌ Genre detection failed**
- ✓ File still downloads to `unknown` folder
- ✓ Check `genre_detection_error` field for details
- ✓ URL and data are preserved in database
- ✓ Not a critical error - download continues

**❌ Server responds slowly**
- ✓ Check server logs: Click "📊 View Logs" in menu bar
- ✓ Verify only 1 concurrent download is configured
- ✓ Check disk space on server
- ✓ Consider upgrading server hardware

---

## Best Practices

### 1. Username Management

Store username in shared UserDefaults:

```swift
extension UserDefaults {
    static let shared = UserDefaults(suiteName: "group.com.yourcompany.vidsaver")!
    
    var username: String {
        get { string(forKey: "username") ?? "defaultuser" }
        set { 
            // Validate and normalize
            let normalized = newValue.lowercased()
            if isValidUsername(normalized) {
                set(normalized, forKey: "username")
            }
        }
    }
    
    var serverURL: String? {
        get { string(forKey: "serverURL") }
        set { set(newValue, forKey: "serverURL") }
    }
    
    var apiKey: String? {
        get { string(forKey: "apiKey") }
        set { set(newValue, forKey: "apiKey") }
    }
}

func isValidUsername(_ username: String) -> Bool {
    let pattern = "^[a-z0-9]+$"  // Lowercase alphanumeric
    return username.range(of: pattern, options: .regularExpression) != nil
}
```

### 2. Error Handling

Implement comprehensive error handling:

```swift
enum DownloadError: Error, LocalizedError {
    case notConfigured
    case invalidUsername
    case invalidURL
    case networkError(Error)
    case serverError(String)
    case authenticationRequired
    
    var errorDescription: String? {
        switch self {
        case .notConfigured:
            return "Server not configured. Please scan QR code to connect."
        case .invalidUsername:
            return "Username must contain only letters and numbers."
        case .invalidURL:
            return "Invalid URL format. Please try again."
        case .networkError(let error):
            return "Network error: \(error.localizedDescription)"
        case .serverError(let message):
            return "Server error: \(message)"
        case .authenticationRequired:
            return "API key required. Please check your settings."
        }
    }
    
    var recoverySuggestion: String? {
        switch self {
        case .notConfigured:
            return "Tap 'Connect to Server' and scan the QR code from your server."
        case .invalidUsername:
            return "Use only letters (a-z) and numbers (0-9) in your username."
        case .invalidURL:
            return "Make sure the URL is complete and properly formatted."
        case .networkError:
            return "Check your internet connection and try again."
        case .serverError:
            return "Try again later or contact your server administrator."
        case .authenticationRequired:
            return "Ask your server administrator for an API key."
        }
    }
}
```

### 3. Background Monitoring

Monitor downloads in your main app:

```swift
class DownloadMonitor: ObservableObject {
    @Published var activeDownloads: [VideoDownloadAPI.StatusResponse] = []
    private var timer: Timer?
    
    func startMonitoring() {
        // Poll every 5 seconds for active downloads
        timer = Timer.scheduledTimer(withTimeInterval: 5.0, repeats: true) { [weak self] _ in
            self?.checkActiveDownloads()
        }
    }
    
    func stopMonitoring() {
        timer?.invalidate()
        timer = nil
    }
    
    private func checkActiveDownloads() {
        // Get pending and downloading items
        VideoDownloadAPI.shared.getHistory(status: "pending", limit: 100, offset: 0) { [weak self] result in
            guard case .success(let pending) = result else { return }
            
            VideoDownloadAPI.shared.getHistory(status: "downloading", limit: 100, offset: 0) { [weak self] result in
                guard case .success(let downloading) = result else { return }
                
                DispatchQueue.main.async {
                    self?.activeDownloads = pending + downloading
                }
            }
        }
    }
}
```

### 4. User Feedback

Provide clear, genre-aware feedback:

```swift
func statusMessage(for download: VideoDownloadAPI.StatusResponse) -> String {
    let genreEmoji: String = {
        switch download.genre {
        case "tiktok": return "🎵"
        case "instagram": return "📸"
        case "youtube": return "🎥"
        case "pdf": return "📄"
        case "ebook": return "📚"
        default: return "💾"
        }
    }()
    
    switch download.status {
    case "pending":
        return "\(genreEmoji) Waiting in queue..."
    case "downloading":
        return "\(genreEmoji) Downloading \(download.genre)..."
    case "completed":
        let size = ByteCountFormatter.string(
            fromByteCount: Int64(download.fileSize ?? 0),
            countStyle: .file
        )
        return "✓ \(genreEmoji) Downloaded \(size)"
    case "failed":
        return "✗ Failed: \(download.errorMessage ?? "Unknown error")"
    default:
        return download.status
    }
}

func genreDisplayName(_ genre: String) -> String {
    switch genre {
    case "tiktok": return "TikTok"
    case "instagram": return "Instagram"
    case "youtube": return "YouTube"
    case "pdf": return "PDF"
    case "ebook": return "eBook"
    case "unknown": return "Other"
    default: return genre.capitalized
    }
}
```

### 5. Offline Handling

Handle offline scenarios gracefully:

```swift
class NetworkMonitor: ObservableObject {
    @Published var isOnline = true
    
    private let monitor = NWPathMonitor()
    private let queue = DispatchQueue(label: "NetworkMonitor")
    
    init() {
        monitor.pathUpdateHandler = { [weak self] path in
            DispatchQueue.main.async {
                self?.isOnline = path.status == .satisfied
            }
        }
        monitor.start(queue: queue)
    }
    
    deinit {
        monitor.cancel()
    }
}

// Use in your view
struct ContentView: View {
    @StateObject private var networkMonitor = NetworkMonitor()
    
    var body: some View {
        VStack {
            if !networkMonitor.isOnline {
                HStack {
                    Image(systemName: "wifi.slash")
                    Text("Offline - some features unavailable")
                }
                .padding()
                .background(Color.orange.opacity(0.2))
                .cornerRadius(8)
            }
            
            // Rest of your UI
        }
    }
}
```

### 6. Keychain for API Keys

Store API keys securely:

```swift
import Security

class KeychainHelper {
    static func save(key: String, value: String) {
        let data = value.data(using: .utf8)!
        
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrAccount as String: key,
            kSecValueData as String: data
        ]
        
        SecItemDelete(query as CFDictionary)
        SecItemAdd(query as CFDictionary, nil)
    }
    
    static func load(key: String) -> String? {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrAccount as String: key,
            kSecReturnData as String: true
        ]
        
        var result: AnyObject?
        SecItemCopyMatching(query as CFDictionary, &result)
        
        guard let data = result as? Data else { return nil }
        return String(data: data, encoding: .utf8)
    }
}

// Usage
KeychainHelper.save(key: "apiKey", value: "your-secret-key")
let apiKey = KeychainHelper.load(key: "apiKey")
```

---

## Additional Resources

### Documentation
- **[Server Setup Guide](../README.md)** - Complete server setup and configuration
- **[SSL Setup Guide](./SSL_SETUP.md)** - Certificate generation and iOS installation
- **[Config Editor Guide](./CONFIG_EDITOR.md)** - Interactive configuration management

### API Documentation
- **FastAPI Docs**: `http://YOUR_SERVER:58443/docs` - Interactive API documentation
- **ReDoc**: `http://YOUR_SERVER:58443/redoc` - Alternative API documentation

### Supported Platforms
- **yt-dlp supported sites**: [1000+ supported sites](https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md)
- **Popular platforms**: TikTok, Instagram, YouTube, Twitter/X, Facebook, and many more

---

## Support & Troubleshooting

### Server Logs

View server logs from menu bar app or terminal:

```bash
# View recent logs
tail -50 ~/TikTok-Downloader-Server/logs/server.log

# Follow logs in real-time
tail -f ~/TikTok-Downloader-Server/logs/server.log

# Search for errors
grep "ERROR" ~/TikTok-Downloader-Server/logs/server.log
```

### Database Inspection

Check database directly (for debugging):

```bash
cd ~/TikTok-Downloader-Server
sqlite3 data/downloads.db

# SQLite commands:
.tables                              # List tables
SELECT * FROM users;                 # View all users
SELECT * FROM downloads LIMIT 10;    # View recent downloads
SELECT * FROM downloads WHERE username='john';  # User's downloads
.quit                                # Exit
```

### Common Log Messages

- `Download queued successfully` - Download accepted
- `Processing download` - Download started
- `Download completed` - Download finished
- `Download failed` - Download error (check error_message)
- `Genre detection failed` - Genre unknown (not critical)
- `User created` - New user automatically created

### Getting Help

1. **Check Server Status**: Menu bar app should show green checkmark
2. **Test API**: Browse to `http://SERVER_IP:58443/docs`
3. **View Logs**: Click "📊 View Logs" in menu bar app
4. **Test URL**: Try downloading manually with yt-dlp
5. **Check Database**: Verify downloads are being saved

---

## Version History

### v2.0.0 (November 2025)
- ✨ Added QR code setup for easy iOS configuration
- ✨ Added multi-user support with per-user folders
- ✨ Added automatic genre detection and organization
- ✨ Added auto-restart after config changes
- ✨ Added automatic database backups before migrations
- ✨ Improved error handling and logging
- ✨ Added menu bar app for Mac
- 🐛 Fixed database connection management
- 🐛 Fixed config validation issues

### v1.0.0 (November 2025)
- 🎉 Initial release
- ✅ Basic download functionality
- ✅ Status tracking
- ✅ History endpoint
- ✅ HTTPS support

---

## License

See main repository for license information.

## Acknowledgments

- **FastAPI** - Modern Python web framework
- **yt-dlp** - Powerful video downloader supporting 1000+ sites
- **Swift & SwiftUI** - iOS development frameworks

---

**Happy Downloading! 🎉**

For more information, visit the [main README](../README.md) or check the [server logs](../logs/server.log).
