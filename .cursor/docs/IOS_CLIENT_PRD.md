# Product Requirements Document: iOS Video Downloader Client

## 1. Overview

A lightweight iOS app with share sheet extension that captures video URLs from TikTok and Instagram, sending them to a private HTTPS server for download. The app serves as a reliable conduit with offline caching and history tracking.

## 2. Goals

- **Zero Data Loss**: Cache URLs locally if server unreachable, send when connection restored
- **Instant Sharing**: Share sheet extension captures URLs seamlessly from any app
- **Server Confirmation**: Verify every URL is persisted on server before clearing cache
- **History Tracking**: Independent client-side history of all shared videos
- **Simplicity**: Minimal UI, focus on reliability over features
- **Privacy**: Direct connection to private server, no third-party services

## 3. Technical Stack

- **Platform**: iOS 15.0+ (SwiftUI + UIKit for Share Extension)
- **Language**: Swift 5.7+
- **Storage**: UserDefaults or SwiftData for cache and history
- **Networking**: URLSession with self-signed certificate handling
- **App Architecture**: 
  - Main App: SwiftUI with basic configuration and history view
  - Share Extension: UIKit-based extension for URL capture

## 4. Core Features

### 4.1 Share Sheet Extension

The primary interface for capturing video URLs from other apps.

**Activation Flow:**
1. User browses TikTok/Instagram and finds video to save
2. User taps native "Share" button
3. User selects app icon from share sheet
4. Extension captures URL and sends to server
5. User receives instant feedback (success/queued/error)

**Technical Requirements:**
- Action Extension that accepts public.url types
- Validate URL is from supported domains (tiktok.com, instagram.com)
- Extract clean URL from shared content
- Add to local cache with pending status
- Attempt immediate server upload
- Update cache based on server response
- Show compact UI with status message

### 4.2 Offline Caching System

Ensures no video URLs are lost due to network issues.

**Cache Structure:**
```swift
struct CachedURL: Codable, Identifiable {
    let id: UUID
    let url: String
    let sourceApp: String
    let cachedAt: Date
    var status: CacheStatus // pending, uploading, confirmed, failed
    var serverDownloadId: String?
    var lastAttempt: Date?
    var attemptCount: Int
}

enum CacheStatus: String, Codable {
    case pending      // Not yet sent to server
    case uploading    // Currently sending
    case confirmed    // Server confirmed receipt
    case failed       // Max retries exceeded
}
```

**Cache Behavior:**
- URLs added immediately upon share
- Automatic retry when app opens
- Retry on share extension activation
- Background retry (if possible)
- Exponential backoff (immediate, 30s, 2min, 5min)
- Max 10 retry attempts before marking as failed
- User can manually retry failed URLs
- Clear confirmed URLs after 24 hours

### 4.3 Server Communication

Direct HTTPS communication with private server.

**API Integration:**

#### POST /api/v1/download
```swift
// Request
struct DownloadRequest: Codable {
    let url: String
    let client_id: String  // Device UUID
    let timestamp: Int
}

// Response
struct DownloadResponse: Codable {
    let status: String     // "queued" or "error"
    let download_id: String?
    let message: String
    let timestamp: Int
    let error: String?
}
```

**Network Manager Requirements:**
- Handle self-signed HTTPS certificates
- 10-second timeout for requests
- Retry logic for network errors
- Background URLSession for reliability
- Certificate pinning for security

**Self-Signed Certificate Handling:**
```swift
// URLSessionDelegate implementation
func urlSession(_ session: URLSession,
                didReceive challenge: URLAuthenticationChallenge,
                completionHandler: @escaping (URLSession.AuthChallengeDisposition, URLCredential?) -> Void) {
    // Trust self-signed certificate
    // Validate server certificate matches stored cert
}
```

### 4.4 History Tracking

Client-side record of all shared videos, independent of cache.

**History Structure:**
```swift
struct HistoryEntry: Codable, Identifiable {
    let id: UUID
    let url: String
    let sharedAt: Date
    let serverDownloadId: String?
    let status: String // queued, confirmed, failed
    let sourceApp: String
}
```

**History Features:**
- Permanent record (not deleted after confirmation)
- Sorted by date (newest first)
- Show status for each entry
- Copy URL to clipboard
- Re-share failed URLs
- Search/filter by domain
- Optional: Delete individual entries
- Optional: Export history

### 4.5 Main App Interface

Simple SwiftUI app for configuration and history viewing.

**Screens:**

#### 1. Settings/Configuration Screen
```
┌─────────────────────────────┐
│  Video Downloader           │
├─────────────────────────────┤
│                             │
│  Server Configuration       │
│  ┌─────────────────────────┐│
│  │ https://192.168.1.100:  ││
│  │ 8443                    ││
│  └─────────────────────────┘│
│                             │
│  ● Connected                │
│  Last sync: 2 mins ago      │
│                             │
│  [Test Connection]          │
│                             │
│  Pending Uploads: 3         │
│  [Retry All]                │
│                             │
│  Certificate Status         │
│  ✓ Trusted                  │
│  [View Instructions]        │
│                             │
└─────────────────────────────┘
```

#### 2. History Screen
```
┌─────────────────────────────┐
│  ← Settings    History      │
├─────────────────────────────┤
│  [Search...]                │
│                             │
│  Today                      │
│  ● tiktok.com/@user/...     │
│    Confirmed · 2:30 PM      │
│                             │
│  ● instagram.com/reel/...   │
│    Confirmed · 1:15 PM      │
│                             │
│  Yesterday                  │
│  ⚠ tiktok.com/@user/...     │
│    Failed · 3:45 PM         │
│    [Retry]                  │
│                             │
│  ⏳ instagram.com/p/...     │
│    Pending · 11:30 AM       │
│                             │
└─────────────────────────────┘
```

**UI Requirements:**
- Single tab interface or navigation stack
- Settings/config as primary screen
- History as secondary screen
- Connection status indicator
- Pending upload counter with badge
- Pull-to-refresh in history
- Swipe actions (delete, retry, copy)

### 4.6 Background Sync

Attempt to sync pending URLs when possible.

**Strategies:**
1. **App Launch**: Check for pending URLs, attempt sync
2. **Share Extension Activation**: Sync all pending before adding new
3. **Background App Refresh**: Periodic sync (if enabled)
4. **Network Change Notification**: Sync when WiFi/cellular connects

**Implementation:**
```swift
// Background task registration
func application(_ application: UIApplication,
                 didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]?) -> Bool {
    BGTaskScheduler.shared.register(
        forTaskWithIdentifier: "com.videodownloader.sync",
        using: nil
    ) { task in
        self.handleBackgroundSync(task: task as! BGProcessingTask)
    }
    return true
}
```

## 5. Data Flow

### Successful Share Flow
```
1. User shares video in TikTok
2. Share extension captures URL
3. URL added to cache (status: pending)
4. URL added to history (status: queued)
5. Immediate server upload attempt
6. Server responds with download_id
7. Cache updated (status: confirmed, download_id)
8. History updated (status: confirmed, download_id)
9. User sees success message
10. Extension dismisses
```

### Offline Share Flow
```
1. User shares video (no connection)
2. Share extension captures URL
3. URL added to cache (status: pending)
4. URL added to history (status: pending)
5. Server upload fails (network error)
6. User sees "Queued - will retry" message
7. Extension dismisses
---
8. User opens app later (connection restored)
9. App checks cache for pending URLs
10. Attempts upload for each pending URL
11. Server confirms receipt
12. Cache and history updated
```

## 6. Security & Privacy

### 6.1 HTTPS Certificate Trust
- User must install and trust server's self-signed certificate
- App validates certificate matches expected cert
- Reject connections if certificate changes (security measure)
- Provide clear instructions for iOS certificate installation

**Certificate Installation Steps for User:**
1. Download certificate file from server (server.crt)
2. Settings → General → VPN & Device Management → Install Profile
3. Enter passcode
4. Settings → General → About → Certificate Trust Settings
5. Enable "Full Trust" for server certificate

### 6.2 Data Security
- Server URL stored in UserDefaults (not sensitive)
- Optional: API key stored in Keychain (if authentication enabled)
- No video content stored on device
- Only URLs cached locally
- Clear sensitive data on app deletion

### 6.3 Privacy
- No analytics or tracking
- No third-party services
- Direct server communication only
- Device UUID used as client_id (standard iOS identifier)

## 7. Configuration

### 7.1 User Settings
```swift
struct AppSettings {
    var serverURL: String = "https://192.168.1.100:8443"
    var apiKey: String? = nil // Optional authentication
    var autoRetry: Bool = true
    var maxRetries: Int = 10
    var clearConfirmedAfter: TimeInterval = 86400 // 24 hours
    var enableBackgroundSync: Bool = true
}
```

### 7.2 App Group
Share extension and main app must share data via App Group.

```swift
// Both targets use shared container
let sharedDefaults = UserDefaults(suiteName: "group.com.yourname.videodownloader")
```

**Shared Data:**
- Cache of pending URLs
- History entries
- Server configuration
- Last sync timestamp

## 8. Error Handling

### 8.1 Common Errors

| Error | User Message | Action |
|-------|-------------|---------|
| Network timeout | "Queued - will retry when connected" | Add to cache, retry later |
| Invalid URL | "Unable to share this content" | Show error, don't cache |
| Server error | "Server unavailable - queued for retry" | Add to cache, retry later |
| Certificate invalid | "Server certificate not trusted" | Show setup instructions |
| Disk full | "Unable to cache - storage full" | Show error, skip cache |

### 8.2 User Feedback
- Toast/alert in share extension (brief, clear)
- Status indicators in main app
- Detailed error messages in history
- Retry buttons for failed items

## 9. Testing Requirements

### 9.1 Manual Testing
- [ ] Share from TikTok (various URLs)
- [ ] Share from Instagram (posts, reels, stories)
- [ ] Share with server offline (verify caching)
- [ ] Open app with cached URLs (verify sync)
- [ ] Kill app during upload (verify resilience)
- [ ] Airplane mode → share → enable network → verify sync
- [ ] Invalid URL handling
- [ ] Server error handling
- [ ] Certificate trust flow
- [ ] History display and actions
- [ ] Settings persistence

### 9.2 Edge Cases
- Multiple rapid shares (queue handling)
- App termination during sync
- Network change during upload
- Server returns error after accepting URL
- Duplicate URL sharing
- Extremely long URLs
- Malformed share data

## 10. Success Criteria

- ✅ Share extension captures URLs from TikTok and Instagram
- ✅ URLs successfully sent to server with confirmation
- ✅ Offline caching prevents data loss
- ✅ Automatic retry when connection restored
- ✅ History tracks all shared videos
- ✅ Self-signed HTTPS works after certificate installation
- ✅ Share extension response time < 2 seconds (when online)
- ✅ Clean, minimal UI focused on reliability
- ✅ No crashes during 100 consecutive shares
- ✅ Memory usage < 50MB

## 11. Future Enhancements (Out of Scope v1)

- Download status sync from server
- Push notifications when downloads complete
- In-app video player/preview
- Multiple server profiles
- Automatic certificate download/trust
- Widget showing recent shares
- Siri shortcuts integration
- Share analytics (success rate, timing)
- Custom URL schemes for deep linking
- iCloud sync of history across devices

## 12. Technical Specifications

### 12.1 Project Structure
```
VideoDownloader/
├── VideoDownloader/           # Main app target
│   ├── App.swift
│   ├── Views/
│   │   ├── SettingsView.swift
│   │   └── HistoryView.swift
│   ├── Models/
│   │   ├── CachedURL.swift
│   │   ├── HistoryEntry.swift
│   │   └── AppSettings.swift
│   ├── Services/
│   │   ├── NetworkManager.swift
│   │   ├── CacheManager.swift
│   │   └── HistoryManager.swift
│   └── Utils/
│       └── URLValidator.swift
├── ShareExtension/            # Share extension target
│   ├── ShareViewController.swift
│   └── Info.plist
└── Shared/                    # Shared between targets
    └── Constants.swift
```

### 12.2 Dependencies
- No external dependencies required (all native iOS)
- Optional: SwiftData for more robust storage (iOS 17+)

### 12.3 Minimum Requirements
- iOS 15.0+
- Swift 5.7+
- Xcode 14.0+

### 12.4 Permissions Required
- None (share extension has default permissions)
- Optional: Background App Refresh for better sync

### 12.5 App Store Requirements
- Privacy Policy (data handling disclosure)
- Clear description of private server requirement
- Screenshots showing setup and usage
- Support URL with certificate installation guide

## 13. Developer Notes

### 13.1 Share Extension Gotchas
- Memory limit: ~30MB for extensions
- Background time: ~30 seconds max
- Keep processing minimal
- Use URLSession with .background configuration
- Shared container for data persistence

### 13.2 Self-Signed Certificate
```swift
// Example: Store certificate locally for validation
class CertificateManager {
    static let serverCertData = Data(base64Encoded: "...")
    
    func validateCertificate(_ serverTrust: SecTrust) -> Bool {
        // Compare server cert with stored cert
        // Return true only if exact match
    }
}
```

### 13.3 URL Validation
```swift
func isValidVideoURL(_ urlString: String) -> Bool {
    guard let url = URL(string: urlString) else { return false }
    
    let validDomains = [
        "tiktok.com",
        "www.tiktok.com",
        "vm.tiktok.com",
        "instagram.com",
        "www.instagram.com"
    ]
    
    return validDomains.contains { domain in
        url.host?.hasSuffix(domain) ?? false
    }
}
```

### 13.4 Background Sync
```swift
func scheduleBackgroundSync() {
    let request = BGProcessingTaskRequest(identifier: "com.videodownloader.sync")
    request.requiresNetworkConnectivity = true
    request.earliestBeginDate = Date(timeIntervalSinceNow: 15 * 60) // 15 min
    
    try? BGTaskScheduler.shared.submit(request)
}
```

## 14. Collaboration with Server

### 14.1 Server Expectations
The iOS client expects the server to:
- Accept POST /api/v1/download with JSON payload
- Respond within 10 seconds
- Return download_id on success
- Use self-signed HTTPS certificate
- Be accessible via local network or WAN

### 14.2 Client Responsibilities
The iOS client must:
- Send properly formatted JSON requests
- Include client_id (device UUID) in all requests
- Handle server errors gracefully
- Cache requests when server unavailable
- Validate SSL certificate matches expected cert

### 14.3 Shared Contract
```json
// Request format (from iOS)
{
  "url": "https://tiktok.com/@user/video/123",
  "client_id": "A1B2C3D4-E5F6-G7H8-I9J0-K1L2M3N4O5P6",
  "timestamp": 1234567890
}

// Success response (from server)
{
  "status": "queued",
  "download_id": "550e8400-e29b-41d4-a716-446655440000",
  "message": "Video queued for download",
  "timestamp": 1234567890
}

// Error response (from server)
{
  "status": "error",
  "error": "Invalid URL format",
  "timestamp": 1234567890
}
```

---

**Document Version**: 1.0  
**Last Updated**: November 7, 2025  
**Status**: Ready for Implementation


