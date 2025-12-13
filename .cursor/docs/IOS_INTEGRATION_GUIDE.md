# iOS Integration Guide

**Version:** 1.0.0  
**Last Updated:** November 8, 2025  
**Server Compatibility:** Video Download Server v1.0.0

This guide provides everything you need to integrate your iOS application with the Video Download Server.

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Server Configuration](#server-configuration)
3. [iOS App Transport Security Setup](#ios-app-transport-security-setup)
4. [API Overview](#api-overview)
5. [Swift Integration](#swift-integration)
6. [Code Examples](#code-examples)
7. [Error Handling](#error-handling)
8. [Best Practices](#best-practices)
9. [Testing](#testing)
10. [Advanced: HTTPS Mode](#advanced-https-mode)

---

## Quick Start

### Prerequisites

- iOS 15.0+ (for async/await support)
- Xcode 13.0+
- Swift 5.5+
- Server running on local network (HTTP mode - default)

### Installation

No external dependencies required! All code uses native iOS frameworks:
- `Foundation` for networking
- `Combine` for reactive programming (optional)

---

## Server Configuration

### Default Setup (HTTP Mode - Recommended)

By default, the server runs in **HTTP mode** for simple local network usage:

```
http://[YOUR_MAC_IP]:58443
```

**Why HTTP is Perfect for This:**
- ✅ No certificate setup needed
- ✅ No domain name required
- ✅ Works with IP addresses
- ✅ Secure on local network (WiFi protected)
- ✅ Zero configuration on iOS (just add Info.plist key)
- ✅ Fast setup - clone and run!

**Finding Your Server IP:**

On your Mac running the server:
```bash
ifconfig | grep "inet " | grep -v 127.0.0.1 | awk '{print $2}' | head -1
```

Example output: `192.168.1.100`

Your server URL will be:
```
http://192.168.1.100:58443
```

### iOS App Configuration

Update your iOS app configuration:
```swift
struct APIConfig {
    // Replace with your Mac's IP address
    static let baseURL = "http://192.168.1.100:58443"
}
```

---

## iOS App Transport Security Setup

iOS blocks HTTP connections by default. To allow HTTP on local network:

### 1. Open Your iOS Project's `Info.plist`

### 2. Add App Transport Security Exception

Add this configuration to allow HTTP on local network IPs:

```xml
<key>NSAppTransportSecurity</key>
<dict>
    <key>NSAllowsLocalNetworking</key>
    <true/>
</dict>
```

**What This Does:**
- Allows HTTP connections to local network IPs (192.168.x.x, 10.x.x.x, 172.16.x.x)
- Does NOT allow HTTP to internet addresses (still secure!)
- Standard iOS feature used by home automation apps, development servers, etc.

**Is This Safe?**
- ✅ **YES!** This only allows HTTP to local network IPs
- ✅ Your WiFi password is the security layer
- ✅ Traffic never leaves your local network
- ✅ Internet connections still require HTTPS

### Alternative: Allow Specific IP (More Restrictive)

If you want to only allow your specific server IP:

```xml
<key>NSAppTransportSecurity</key>
<dict>
    <key>NSExceptionDomains</key>
    <dict>
        <key>192.168.1.100</key>
        <dict>
            <key>NSExceptionAllowsInsecureHTTPLoads</key>
            <true/>
        </dict>
    </dict>
</dict>
```

**Note:** You'll need to update this if your server's IP changes. `NSAllowsLocalNetworking` is more flexible.

---

## API Overview

### Base URL
```
http://[YOUR_MAC_IP]:58443/api/v1
```

Example:
```
http://192.168.1.100:58443/api/v1
```

### Available Endpoints

| Endpoint | Method | Purpose | Response Time |
|----------|--------|---------|---------------|
| `/download` | POST | Submit video for download | < 100ms |
| `/status/{id}` | GET | Check download status | < 50ms |
| `/history` | GET | Get download history | < 100ms |
| `/health` | GET | Check server health | < 50ms |

### Quick Test

Test your connection from iOS Safari:
```
http://192.168.1.100:58443/api/v1/health
```

You should see a JSON response with `"status": "healthy"`.

### Authentication

**Currently:** No authentication required (trusted local network)  
**Future:** Add API key in `X-API-Key` header if implementing authentication

---

## Swift Integration

### 1. API Client Structure

Create a dedicated API client for all server communication:

```swift
import Foundation

class VideoDownloadAPI {
    // MARK: - Configuration
    
    private let baseURL: String
    private let session: URLSession
    private let deviceID: String
    
    init(baseURL: String = "http://192.168.1.100:58443/api/v1") {
        self.baseURL = baseURL
        
        // Configure URLSession
        let configuration = URLSessionConfiguration.default
        configuration.timeoutIntervalForRequest = 30
        configuration.timeoutIntervalForResource = 300
        self.session = URLSession(configuration: configuration)
        
        // Generate or retrieve device ID
        self.deviceID = UIDevice.current.identifierForVendor?.uuidString ?? UUID().uuidString
    }
    
    // MARK: - API Methods (see below)
}
```

**Important:** Replace `192.168.1.100` with your Mac's actual IP address!

### 2. Data Models

Define models matching server responses:

```swift
import Foundation

// MARK: - Download Request

struct DownloadRequest: Codable {
    let url: String
    let clientId: String
    
    enum CodingKeys: String, CodingKey {
        case url
        case clientId = "client_id"
    }
}

// MARK: - Download Response

struct DownloadResponse: Codable {
    let success: Bool
    let downloadId: String
    let message: String
    let status: DownloadStatus
    let submittedAt: String
    
    enum CodingKeys: String, CodingKey {
        case success
        case downloadId = "download_id"
        case message
        case status
        case submittedAt = "submitted_at"
    }
}

// MARK: - Download Status

enum DownloadStatus: String, Codable {
    case pending = "pending"
    case downloading = "downloading"
    case completed = "completed"
    case failed = "failed"
    
    var displayName: String {
        switch self {
        case .pending: return "Queued"
        case .downloading: return "Downloading"
        case .completed: return "Completed"
        case .failed: return "Failed"
        }
    }
    
    var icon: String {
        switch self {
        case .pending: return "clock"
        case .downloading: return "arrow.down.circle.fill"
        case .completed: return "checkmark.circle.fill"
        case .failed: return "xmark.circle.fill"
        }
    }
}

// MARK: - Status Response

struct StatusResponse: Codable {
    let downloadId: String
    let url: String
    let status: DownloadStatus
    let submittedAt: String
    let startedAt: String?
    let completedAt: String?
    let filePath: String?
    let fileSize: Int?
    let errorMessage: String?
    
    enum CodingKeys: String, CodingKey {
        case downloadId = "download_id"
        case url
        case status
        case submittedAt = "submitted_at"
        case startedAt = "started_at"
        case completedAt = "completed_at"
        case filePath = "file_path"
        case fileSize = "file_size"
        case errorMessage = "error_message"
    }
    
    // Computed properties for display
    var fileSizeFormatted: String? {
        guard let size = fileSize else { return nil }
        return ByteCountFormatter.string(fromByteCount: Int64(size), countStyle: .file)
    }
    
    var submittedDate: Date? {
        ISO8601DateFormatter().date(from: submittedAt)
    }
}

// MARK: - Health Response

struct HealthResponse: Codable {
    let status: String
    let timestamp: String
    let version: String
    let database: DatabaseHealth
}

struct DatabaseHealth: Codable {
    let connected: Bool
    let totalDownloads: Int
    
    enum CodingKeys: String, CodingKey {
        case connected
        case totalDownloads = "total_downloads"
    }
}

// MARK: - Error Response

struct APIError: Codable, LocalizedError {
    let error: String
    let message: String
    let requestId: String?
    
    enum CodingKeys: String, CodingKey {
        case error
        case message
        case requestId = "request_id"
    }
    
    var errorDescription: String? {
        return message
    }
}
```

### 3. API Methods

#### Submit Download

```swift
extension VideoDownloadAPI {
    func submitDownload(url: String) async throws -> DownloadResponse {
        let endpoint = "\(baseURL)/download"
        guard let requestURL = URL(string: endpoint) else {
            throw URLError(.badURL)
        }
        
        var request = URLRequest(url: requestURL)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        
        // Create request body
        let body = DownloadRequest(url: url, clientId: deviceID)
        request.httpBody = try JSONEncoder().encode(body)
        
        // Make request
        let (data, response) = try await session.data(for: request)
        
        // Check response
        guard let httpResponse = response as? HTTPURLResponse else {
            throw URLError(.badServerResponse)
        }
        
        guard (200...299).contains(httpResponse.statusCode) else {
            // Try to decode error
            if let apiError = try? JSONDecoder().decode(APIError.self, from: data) {
                throw apiError
            }
            throw URLError(.badServerResponse)
        }
        
        // Decode success response
        let downloadResponse = try JSONDecoder().decode(DownloadResponse.self, from: data)
        return downloadResponse
    }
}
```

#### Check Download Status

```swift
extension VideoDownloadAPI {
    func checkStatus(downloadId: String) async throws -> StatusResponse {
        let endpoint = "\(baseURL)/status/\(downloadId)"
        guard let requestURL = URL(string: endpoint) else {
            throw URLError(.badURL)
        }
        
        var request = URLRequest(url: requestURL)
        request.httpMethod = "GET"
        
        let (data, response) = try await session.data(for: request)
        
        guard let httpResponse = response as? HTTPURLResponse else {
            throw URLError(.badServerResponse)
        }
        
        guard (200...299).contains(httpResponse.statusCode) else {
            if let apiError = try? JSONDecoder().decode(APIError.self, from: data) {
                throw apiError
            }
            throw URLError(.badServerResponse)
        }
        
        let statusResponse = try JSONDecoder().decode(StatusResponse.self, from: data)
        return statusResponse
    }
}
```

#### Get Download History

```swift
extension VideoDownloadAPI {
    func getHistory(
        limit: Int = 50,
        offset: Int = 0,
        status: DownloadStatus? = nil,
        clientId: String? = nil
    ) async throws -> [StatusResponse] {
        var components = URLComponents(string: "\(baseURL)/history")!
        var queryItems: [URLQueryItem] = [
            URLQueryItem(name: "limit", value: "\(limit)"),
            URLQueryItem(name: "offset", value: "\(offset)")
        ]
        
        if let status = status {
            queryItems.append(URLQueryItem(name: "status", value: status.rawValue))
        }
        
        if let clientId = clientId {
            queryItems.append(URLQueryItem(name: "client_id", value: clientId))
        }
        
        components.queryItems = queryItems
        
        guard let requestURL = components.url else {
            throw URLError(.badURL)
        }
        
        var request = URLRequest(url: requestURL)
        request.httpMethod = "GET"
        
        let (data, response) = try await session.data(for: request)
        
        guard let httpResponse = response as? HTTPURLResponse else {
            throw URLError(.badServerResponse)
        }
        
        guard (200...299).contains(httpResponse.statusCode) else {
            if let apiError = try? JSONDecoder().decode(APIError.self, from: data) {
                throw apiError
            }
            throw URLError(.badServerResponse)
        }
        
        let history = try JSONDecoder().decode([StatusResponse].self, from: data)
        return history
    }
}
```

#### Check Server Health

```swift
extension VideoDownloadAPI {
    func checkHealth() async throws -> HealthResponse {
        let endpoint = "\(baseURL)/health"
        guard let requestURL = URL(string: endpoint) else {
            throw URLError(.badURL)
        }
        
        var request = URLRequest(url: requestURL)
        request.httpMethod = "GET"
        
        let (data, response) = try await session.data(for: request)
        
        guard let httpResponse = response as? HTTPURLResponse else {
            throw URLError(.badServerResponse)
        }
        
        guard (200...299).contains(httpResponse.statusCode) else {
            throw URLError(.badServerResponse)
        }
        
        let healthResponse = try JSONDecoder().decode(HealthResponse.self, from: data)
        return healthResponse
    }
}
```

---

## Code Examples

### Example 1: Submit Download from Share Extension

```swift
import UIKit

class ShareViewController: UIViewController {
    let api = VideoDownloadAPI()
    
    override func viewDidLoad() {
        super.viewDidLoad()
        handleSharedURL()
    }
    
    func handleSharedURL() {
        guard let extensionItem = extensionContext?.inputItems.first as? NSExtensionItem,
              let itemProvider = extensionItem.attachments?.first else {
            return
        }
        
        if itemProvider.hasItemConformingToTypeIdentifier("public.url") {
            itemProvider.loadItem(forTypeIdentifier: "public.url", options: nil) { [weak self] (url, error) in
                guard let self = self,
                      let url = url as? URL else {
                    return
                }
                
                Task {
                    await self.submitDownload(url: url.absoluteString)
                }
            }
        }
    }
    
    func submitDownload(url: String) async {
        do {
            let response = try await api.submitDownload(url: url)
            
            await MainActor.run {
                showSuccess(message: "Download queued! ID: \(response.downloadId)")
            }
            
            // Start polling for status
            await pollDownloadStatus(downloadId: response.downloadId)
            
        } catch let error as APIError {
            await MainActor.run {
                showError(message: error.message)
            }
        } catch {
            await MainActor.run {
                showError(message: "Failed to submit download: \(error.localizedDescription)")
            }
        }
    }
    
    func pollDownloadStatus(downloadId: String) async {
        var isComplete = false
        
        while !isComplete {
            do {
                try await Task.sleep(nanoseconds: 2_000_000_000) // 2 seconds
                
                let status = try await api.checkStatus(downloadId: downloadId)
                
                await MainActor.run {
                    updateStatus(status)
                }
                
                // Check if download is complete
                if status.status == .completed || status.status == .failed {
                    isComplete = true
                }
                
            } catch {
                print("Error polling status: \(error)")
                break
            }
        }
    }
    
    func showSuccess(message: String) {
        // Show success UI
        let alert = UIAlertController(title: "Success", message: message, preferredStyle: .alert)
        alert.addAction(UIAlertAction(title: "OK", style: .default) { [weak self] _ in
            self?.extensionContext?.completeRequest(returningItems: nil, completionHandler: nil)
        })
        present(alert, animated: true)
    }
    
    func showError(message: String) {
        // Show error UI
        let alert = UIAlertController(title: "Error", message: message, preferredStyle: .alert)
        alert.addAction(UIAlertAction(title: "OK", style: .default) { [weak self] _ in
            self?.extensionContext?.cancelRequest(withError: NSError(domain: "VideoDownload", code: -1))
        })
        present(alert, animated: true)
    }
    
    func updateStatus(_ status: StatusResponse) {
        // Update UI with current status
        print("Status: \(status.status.displayName)")
    }
}
```

### Example 2: Download History View

```swift
import SwiftUI

struct DownloadHistoryView: View {
    @StateObject private var viewModel = DownloadHistoryViewModel()
    
    var body: some View {
        NavigationView {
            List {
                ForEach(viewModel.downloads, id: \.downloadId) { download in
                    DownloadRow(download: download)
                }
                
                if viewModel.hasMore {
                    ProgressView()
                        .onAppear {
                            Task {
                                await viewModel.loadMore()
                            }
                        }
                }
            }
            .navigationTitle("Downloads")
            .refreshable {
                await viewModel.refresh()
            }
            .task {
                await viewModel.loadInitial()
            }
        }
    }
}

struct DownloadRow: View {
    let download: StatusResponse
    
    var body: some View {
        HStack {
            Image(systemName: download.status.icon)
                .foregroundColor(statusColor)
            
            VStack(alignment: .leading, spacing: 4) {
                Text(download.url)
                    .font(.body)
                    .lineLimit(1)
                
                HStack {
                    Text(download.status.displayName)
                        .font(.caption)
                        .foregroundColor(.secondary)
                    
                    if let size = download.fileSizeFormatted {
                        Text("• \(size)")
                            .font(.caption)
                            .foregroundColor(.secondary)
                    }
                }
            }
            
            Spacer()
            
            if download.status == .downloading {
                ProgressView()
            }
        }
        .padding(.vertical, 4)
    }
    
    var statusColor: Color {
        switch download.status {
        case .pending: return .orange
        case .downloading: return .blue
        case .completed: return .green
        case .failed: return .red
        }
    }
}

@MainActor
class DownloadHistoryViewModel: ObservableObject {
    @Published var downloads: [StatusResponse] = []
    @Published var isLoading = false
    @Published var hasMore = true
    
    private let api = VideoDownloadAPI()
    private let limit = 20
    private var offset = 0
    
    func loadInitial() async {
        guard !isLoading else { return }
        isLoading = true
        offset = 0
        
        do {
            let history = try await api.getHistory(limit: limit, offset: offset)
            downloads = history
            hasMore = history.count == limit
            offset += limit
        } catch {
            print("Error loading history: \(error)")
        }
        
        isLoading = false
    }
    
    func loadMore() async {
        guard !isLoading, hasMore else { return }
        isLoading = true
        
        do {
            let history = try await api.getHistory(limit: limit, offset: offset)
            downloads.append(contentsOf: history)
            hasMore = history.count == limit
            offset += limit
        } catch {
            print("Error loading more: \(error)")
        }
        
        isLoading = false
    }
    
    func refresh() async {
        await loadInitial()
    }
}
```

### Example 3: Real-Time Status Monitoring

```swift
import Combine

class DownloadMonitor: ObservableObject {
    @Published var currentStatus: StatusResponse?
    @Published var isMonitoring = false
    
    private let api = VideoDownloadAPI()
    private var monitoringTask: Task<Void, Never>?
    private let pollInterval: TimeInterval = 2.0
    
    func startMonitoring(downloadId: String) {
        guard !isMonitoring else { return }
        isMonitoring = true
        
        monitoringTask = Task { [weak self] in
            guard let self = self else { return }
            
            while !Task.isCancelled {
                do {
                    let status = try await self.api.checkStatus(downloadId: downloadId)
                    
                    await MainActor.run {
                        self.currentStatus = status
                    }
                    
                    // Stop monitoring if complete or failed
                    if status.status == .completed || status.status == .failed {
                        await MainActor.run {
                            self.stopMonitoring()
                        }
                        break
                    }
                    
                    // Wait before next poll
                    try await Task.sleep(nanoseconds: UInt64(self.pollInterval * 1_000_000_000))
                    
                } catch {
                    print("Error monitoring status: \(error)")
                    await MainActor.run {
                        self.stopMonitoring()
                    }
                    break
                }
            }
        }
    }
    
    func stopMonitoring() {
        monitoringTask?.cancel()
        monitoringTask = nil
        isMonitoring = false
    }
    
    deinit {
        stopMonitoring()
    }
}
```

---

## Error Handling

### Common Error Scenarios

```swift
enum DownloadError: LocalizedError {
    case invalidURL
    case serverUnavailable
    case invalidResponse
    case downloadNotFound
    case unsupportedPlatform
    
    var errorDescription: String? {
        switch self {
        case .invalidURL:
            return "The URL is not valid or not supported. Please check the URL and try again."
        case .serverUnavailable:
            return "Unable to connect to the download server. Please check your internet connection."
        case .invalidResponse:
            return "Received an invalid response from the server."
        case .downloadNotFound:
            return "The download was not found. It may have been deleted."
        case .unsupportedPlatform:
            return "This video platform is not currently supported. Only TikTok and Instagram are supported."
        }
    }
}

// Error handling wrapper
extension VideoDownloadAPI {
    func submitDownloadSafe(url: String) async -> Result<DownloadResponse, Error> {
        do {
            let response = try await submitDownload(url: url)
            return .success(response)
        } catch let error as APIError {
            // Handle API-specific errors
            if error.error == "invalid_parameter" {
                return .failure(DownloadError.unsupportedPlatform)
            }
            return .failure(error)
        } catch let error as URLError {
            // Handle network errors
            if error.code == .notConnectedToInternet || error.code == .cannotConnectToHost {
                return .failure(DownloadError.serverUnavailable)
            }
            return .failure(error)
        } catch {
            return .failure(error)
        }
    }
}
```

### User-Friendly Error Messages

```swift
extension Error {
    var userFriendlyMessage: String {
        if let apiError = self as? APIError {
            return apiError.message
        } else if let downloadError = self as? DownloadError {
            return downloadError.errorDescription ?? "An error occurred"
        } else if let urlError = self as? URLError {
            switch urlError.code {
            case .notConnectedToInternet:
                return "No internet connection. Please check your network settings."
            case .cannotConnectToHost:
                return "Cannot connect to server. Please try again later."
            case .timedOut:
                return "Request timed out. Please check your connection and try again."
            default:
                return "Network error: \(urlError.localizedDescription)"
            }
        } else {
            return "An unexpected error occurred: \(self.localizedDescription)"
        }
    }
}
```

---

## Best Practices

### 1. SSL Certificate Pinning (Production)

For enhanced security, implement certificate pinning:

```swift
class PinnedSessionDelegate: NSObject, URLSessionDelegate {
    func urlSession(
        _ session: URLSession,
        didReceive challenge: URLAuthenticationChallenge,
        completionHandler: @escaping (URLSession.AuthChallengeDisposition, URLCredential?) -> Void
    ) {
        guard challenge.protectionSpace.authenticationMethod == NSURLAuthenticationMethodServerTrust,
              let serverTrust = challenge.protectionSpace.serverTrust else {
            completionHandler(.cancelAuthenticationChallenge, nil)
            return
        }
        
        // Validate certificate
        let credential = URLCredential(trust: serverTrust)
        completionHandler(.useCredential, credential)
    }
}
```

### 2. Persistent Device ID

Store device ID persistently:

```swift
extension VideoDownloadAPI {
    private func getDeviceID() -> String {
        let key = "com.yourapp.deviceID"
        
        if let existingID = UserDefaults.standard.string(forKey: key) {
            return existingID
        }
        
        let newID = UUID().uuidString
        UserDefaults.standard.set(newID, forKey: key)
        return newID
    }
}
```

### 3. Background Downloads

For long-running downloads, use background sessions:

```swift
class BackgroundDownloadManager {
    static let shared = BackgroundDownloadManager()
    
    private lazy var backgroundSession: URLSession = {
        let config = URLSessionConfiguration.background(withIdentifier: "com.yourapp.background")
        config.isDiscretionary = false
        config.sessionSendsLaunchEvents = true
        return URLSession(configuration: config, delegate: self, delegateQueue: nil)
    }()
    
    // Use this session for long-running operations
}
```

### 4. Caching

Implement caching for history:

```swift
actor DownloadCache {
    private var cache: [String: StatusResponse] = [:]
    private let maxAge: TimeInterval = 300 // 5 minutes
    private var timestamps: [String: Date] = [:]
    
    func get(_ id: String) -> StatusResponse? {
        guard let timestamp = timestamps[id],
              Date().timeIntervalSince(timestamp) < maxAge else {
            return nil
        }
        return cache[id]
    }
    
    func set(_ id: String, response: StatusResponse) {
        cache[id] = response
        timestamps[id] = Date()
    }
    
    func invalidate(_ id: String) {
        cache.removeValue(forKey: id)
        timestamps.removeValue(forKey: id)
    }
}
```

### 5. Rate Limiting

Implement client-side rate limiting:

```swift
actor RateLimiter {
    private var lastRequestTime: Date?
    private let minimumInterval: TimeInterval = 1.0
    
    func waitIfNeeded() async {
        if let lastTime = lastRequestTime {
            let elapsed = Date().timeIntervalSince(lastTime)
            if elapsed < minimumInterval {
                let waitTime = minimumInterval - elapsed
                try? await Task.sleep(nanoseconds: UInt64(waitTime * 1_000_000_000))
            }
        }
        lastRequestTime = Date()
    }
}
```

---

## Testing

### Unit Tests

```swift
import XCTest
@testable import YourApp

class VideoDownloadAPITests: XCTestCase {
    var api: VideoDownloadAPI!
    
    override func setUp() {
        super.setUp()
        api = VideoDownloadAPI(baseURL: "https://test-server.com:8443/api/v1")
    }
    
    func testSubmitDownload() async throws {
        let url = "https://www.tiktok.com/@user/video/123"
        
        do {
            let response = try await api.submitDownload(url: url)
            XCTAssertTrue(response.success)
            XCTAssertFalse(response.downloadId.isEmpty)
            XCTAssertEqual(response.status, .pending)
        } catch {
            XCTFail("Download submission failed: \(error)")
        }
    }
    
    func testInvalidURL() async {
        let url = "https://youtube.com/watch?v=123"
        
        do {
            _ = try await api.submitDownload(url: url)
            XCTFail("Should have thrown error for unsupported platform")
        } catch let error as APIError {
            XCTAssertEqual(error.error, "invalid_parameter")
        } catch {
            XCTFail("Wrong error type: \(error)")
        }
    }
    
    func testCheckStatus() async throws {
        // First submit a download
        let url = "https://www.tiktok.com/@user/video/123"
        let submitResponse = try await api.submitDownload(url: url)
        
        // Then check its status
        let statusResponse = try await api.checkStatus(downloadId: submitResponse.downloadId)
        XCTAssertEqual(statusResponse.downloadId, submitResponse.downloadId)
        XCTAssertNotNil(statusResponse.status)
    }
}
```

### Integration Tests

```swift
class IntegrationTests: XCTestCase {
    func testFullDownloadFlow() async throws {
        let api = VideoDownloadAPI()
        
        // 1. Submit download
        let submitResponse = try await api.submitDownload(
            url: "https://www.tiktok.com/@test/video/123"
        )
        XCTAssertTrue(submitResponse.success)
        let downloadId = submitResponse.downloadId
        
        // 2. Poll for completion
        var attempts = 0
        var finalStatus: StatusResponse?
        
        while attempts < 30 { // Max 1 minute
            try await Task.sleep(nanoseconds: 2_000_000_000)
            
            let status = try await api.checkStatus(downloadId: downloadId)
            
            if status.status == .completed || status.status == .failed {
                finalStatus = status
                break
            }
            
            attempts += 1
        }
        
        // 3. Verify completion
        XCTAssertNotNil(finalStatus)
        XCTAssertTrue(finalStatus?.status == .completed || finalStatus?.status == .failed)
        
        // 4. Check history
        let history = try await api.getHistory(limit: 10)
        XCTAssertTrue(history.contains { $0.downloadId == downloadId })
    }
}
```

---

## Troubleshooting

### Common Issues

#### 1. Can't Connect to Server

**Problem:** "The network connection was lost" or "Could not connect to the server"

**Solutions:**
1. **Verify both devices are on same WiFi network**
   ```bash
   # On Mac, check IP
   ifconfig | grep "inet " | grep -v 127.0.0.1
   
   # On iOS, Settings → WiFi → Info icon
   # Both should be on same subnet (e.g., 192.168.1.x)
   ```

2. **Verify server is running**
   ```bash
   python server.py
   ```

3. **Test from Mac first**
   ```bash
   curl http://localhost:58443/api/v1/health
   ```

4. **Check Info.plist has ATS exception**
   - Look for `NSAllowsLocalNetworking` = `true`

5. **Verify Mac firewall allows Python**
   - System Preferences → Security & Privacy → Firewall → Firewall Options
   - Ensure Python is allowed

#### 2. App Transport Security Error

**Problem:** "App Transport Security has blocked a cleartext HTTP resource load"

**Solution:** Add `NSAllowsLocalNetworking` to Info.plist:

```xml
<key>NSAppTransportSecurity</key>
<dict>
    <key>NSAllowsLocalNetworking</key>
    <true/>
</dict>
```

#### 3. Wrong Server IP

**Problem:** Connection works sometimes but not always

**Solution:**
- Your Mac's IP may have changed (DHCP)
- Get current IP: `ifconfig | grep "inet " | grep -v 127.0.0.1`
- Update iOS app's baseURL
- Consider setting static IP on your Mac

#### 4. Connection Timeout

**Problem:** Requests timeout

**Solutions:**
- Increase timeout in URLSessionConfiguration
- Check server is running and accessible
- Verify firewall settings allow port 58443
- Test from Safari first: `http://[MAC_IP]:58443/api/v1/health`

#### 5. Invalid JSON Response

**Problem:** "Failed to decode response"

**Solutions:**
- Check server is returning correct Content-Type header
- Verify API models match server response structure
- Add logging to see raw response

```swift
// Debug helper
func printRawResponse(_ data: Data) {
    if let json = try? JSONSerialization.jsonObject(with: data),
       let prettyData = try? JSONSerialization.data(withJSONObject: json, options: .prettyPrinted),
       let prettyString = String(data: prettyData, encoding: .utf8) {
        print("Response:\n\(prettyString)")
    }
}
```

---

## Quick Reference

### Supported URL Patterns

| Platform | Pattern | Example |
|----------|---------|---------|
| TikTok | `tiktok.com/@user/video/*` | `https://www.tiktok.com/@user/video/123` |
| TikTok (short) | `vm.tiktok.com/*` | `https://vm.tiktok.com/abc123` |
| Instagram | `instagram.com/p/*` | `https://www.instagram.com/p/abc123` |
| Instagram | `instagram.com/reel/*` | `https://www.instagram.com/reel/abc123` |

### HTTP Status Codes

| Code | Meaning | Action |
|------|---------|--------|
| 200 | Success | Process response |
| 201 | Created | Download queued |
| 400 | Bad Request | Check request parameters |
| 404 | Not Found | Download ID doesn't exist |
| 422 | Validation Error | URL not supported |
| 500 | Server Error | Retry or report issue |

### Response Times

| Endpoint | Expected | Maximum |
|----------|----------|---------|
| /download | < 100ms | 500ms |
| /status/{id} | < 50ms | 200ms |
| /history | < 100ms | 500ms |
| /health | < 50ms | 200ms |

---

## Support

### Server Logs

Check server logs for debugging:
```bash
tail -f logs/server.log
```

### Health Check

Verify server is running:
```bash
# From Mac
curl http://localhost:58443/api/v1/health

# From another device
curl http://192.168.1.100:58443/api/v1/health
```

### API Documentation

Browse interactive API docs:
```
http://192.168.1.100:58443/docs
```

(Replace `192.168.1.100` with your Mac's IP)

---

## Advanced: HTTPS Mode

The server runs in HTTP mode by default for simplicity. If you need HTTPS:

### When You Need HTTPS

- ✅ Internet-facing deployment (not local network only)
- ✅ Company/organization security requirements
- ✅ Transmitting sensitive data (beyond video URLs)

**For personal, local network use: HTTP is recommended and safe!**

### Enabling HTTPS

#### 1. Configure Server

Edit `config/config.yaml`:

```yaml
server:
  port: 58443
  ssl:
    enabled: true                      # Enable SSL
    use_letsencrypt: true              # Use Let's Encrypt
    domain: "videos.yourdomain.com"    # Your domain
    letsencrypt_email: "you@email.com" # Your email
```

#### 2. Set Up Let's Encrypt

```bash
sudo bash scripts/setup_letsencrypt.sh videos.yourdomain.com you@email.com
```

Requirements:
- Domain name
- DNS A record pointing to server IP
- Port 80 accessible (for Let's Encrypt validation)

#### 3. Update iOS App

Change baseURL to HTTPS with domain:

```swift
struct APIConfig {
    static let baseURL = "https://videos.yourdomain.com:58443"
}
```

#### 4. Remove ATS Exception

Remove `NSAllowsLocalNetworking` from Info.plist since you're now using HTTPS with a valid certificate.

### HTTPS vs HTTP Comparison

| Feature | HTTP (Default) | HTTPS (Advanced) |
|---------|---------------|------------------|
| **Setup Time** | 5 minutes | 30-45 minutes |
| **Domain Required** | ❌ No | ✅ Yes |
| **DNS Setup** | ❌ No | ✅ Yes |
| **Certificates** | ❌ No | ✅ Yes |
| **Port 80/443** | ❌ No | ✅ Yes (for Let's Encrypt) |
| **Works with IP** | ✅ Yes | ❌ No |
| **Local Network** | ✅ Perfect | ✅ Yes |
| **Internet Access** | ⚠️ Possible but not recommended | ✅ Yes |
| **iOS Trust** | ✅ Automatic (ATS exception) | ✅ Automatic (Let's Encrypt) |

### Testing HTTPS

```bash
# Test from Mac
curl https://videos.yourdomain.com:58443/api/v1/health

# Test from iOS Safari
# Open: https://videos.yourdomain.com:58443/api/v1/health
```

For detailed HTTPS setup, see `PRODUCTION_SETUP_MAC.md`.

---

## Next Steps

1. ✅ Copy API client code to your iOS project
2. ✅ Update `baseURL` with your server IP
3. ✅ Add `NSAllowsLocalNetworking` to Info.plist
4. ✅ Implement Share Extension for TikTok/Instagram
5. ✅ Add history view to display downloads
6. ✅ Test with real TikTok/Instagram URLs
7. ✅ (Optional) Enable HTTPS if needed

---

**Happy Coding! 🚀**

For issues or questions, check the server logs or API documentation at `/docs`.

**Default Setup:** HTTP on local network - simple, secure, and works great!

