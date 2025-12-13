# SSL & QR Code Connection Guide

## 🔒 Critical SSL Concept

**Let's Encrypt certificates are issued to DOMAIN NAMES, not IP addresses.**

### The Problem
When using Let's Encrypt SSL/HTTPS:
- ✅ `https://video.example.com:8443` → **Works!** (certificate matches domain)
- ❌ `https://68.186.221.57:8443` → **Fails!** (certificate mismatch error)

iOS will reject the connection if the hostname doesn't match the certificate.

---

## 📱 QR Code Format

The server now includes the domain name in the QR code when Let's Encrypt is enabled.

### QR Code Data Structure

```json
{
  "domain": "video.example.com",  // NEW: Domain for Let's Encrypt
  "lan": "192.168.1.119:8443",       // Local network IP
  "wan": "68.186.221.57:8443",        // Public/internet IP
  "protocol": "https",                 // http or https
  "key": "your-api-key",              // API key (if configured)
  "v": "2.0"                          // Version
}
```

### When Each Field is Present

| Field | Present When | Value |
|-------|--------------|-------|
| `domain` | SSL enabled AND Let's Encrypt configured | e.g., `video.example.com` |
| `lan` | Always | e.g., `192.168.1.119:8443` |
| `wan` | If public IP detected | e.g., `68.186.221.57:8443` or `null` |
| `protocol` | Always | `https` or `http` |
| `key` | If API keys configured | API key string or `null` |

---

## 🎯 iOS Client Connection Priority

Your iOS client should connect in this order:

### When SSL is Enabled (protocol = "https")

**Priority 1: Domain (Required for SSL)**
```
https://video.example.com:8443
```
- **Use if:** `domain` field exists and `protocol` is `https`
- **Why:** Let's Encrypt certificate only works with the domain name
- **Fallback:** If domain connection fails, SSL won't work with IPs

### When SSL is Disabled (protocol = "http")

**Priority 1: LAN (Same network)**
```
http://192.168.1.119:8443
```
- **Use if:** Device is on same local network
- **Why:** Faster, no internet required
- **How to detect:** Try connecting first, or check if device IP is in same subnet

**Priority 2: WAN (Internet)**
```
http://68.186.221.57:8443
```
- **Use if:** LAN fails or device is remote
- **Why:** Works from anywhere
- **Requirement:** Port forwarding must be configured on router

---

## 📋 Connection Logic Flowchart

```
Scan QR Code
    ↓
Parse JSON
    ↓
Is protocol "https"?
    ├─ YES → Is domain present?
    │        ├─ YES → Try: https://domain:port ✓
    │        └─ NO  → Show error: "SSL requires domain"
    │
    └─ NO (http) → Try in order:
                   1. http://lan:port (if same network)
                   2. http://wan:port (if available)
                   3. Show error: "Cannot connect"
```

---

## 🔧 Implementation Recommendations

### Swift Example (iOS)

```swift
struct ServerConfig: Codable {
    let domain: String?
    let lan: String
    let wan: String?
    let `protocol`: String
    let key: String?
    let v: String
}

func getConnectionURL(from config: ServerConfig) -> URL? {
    // SSL requires domain
    if config.protocol == "https" {
        guard let domain = config.domain else {
            print("ERROR: SSL requires domain name")
            return nil
        }
        return URL(string: "\(config.protocol)://\(domain)")
    }
    
    // Non-SSL: try LAN first, then WAN
    // Try LAN (check if we're on same network)
    if isOnSameNetwork(lanIP: config.lan) {
        return URL(string: "\(config.protocol)://\(config.lan)")
    }
    
    // Try WAN if available
    if let wan = config.wan {
        return URL(string: "\(config.protocol)://\(wan)")
    }
    
    return nil
}

func isOnSameNetwork(lanIP: String) -> Bool {
    // Extract IP from "192.168.1.119:8443" format
    let components = lanIP.components(separatedBy: ":")
    guard let serverIP = components.first else { return false }
    
    // Get device's current IP
    guard let deviceIP = getDeviceIP() else { return false }
    
    // Compare subnets (first 3 octets for common home networks)
    let serverSubnet = serverIP.components(separatedBy: ".").prefix(3).joined(separator: ".")
    let deviceSubnet = deviceIP.components(separatedBy: ".").prefix(3).joined(separator: ".")
    
    return serverSubnet == deviceSubnet
}
```

---

## 🔍 Self-Signed vs Let's Encrypt

### Let's Encrypt (Recommended)
- **Certificate issued to:** Domain name
- **Connection:** MUST use domain name
- **iOS Trust:** Automatic (globally trusted CA)
- **Example:** `https://video.example.com:8443` ✓

### Self-Signed
- **Certificate issued to:** Can be domain or IP
- **Connection:** Use whatever cert was issued to
- **iOS Trust:** Manual (install certificate on device)
- **Examples:** 
  - If cert issued to domain: `https://server.local:8443`
  - If cert issued to IP: `https://192.168.1.119:8443`

**Key Difference:** Let's Encrypt ALWAYS requires domain. Self-signed can work with IPs if configured that way.

---

## ⚠️ Common Issues & Solutions

### Issue: "Certificate mismatch" on iOS

**Cause:** Connecting to IP when cert is for domain

**Solution:** Ensure iOS client uses domain when `protocol` is `https`

```swift
// ❌ WRONG - using IP with SSL
https://68.186.221.57:8443

// ✅ CORRECT - using domain with SSL  
https://video.example.com:8443
```

### Issue: "Cannot connect" when using domain

**Possible causes:**
1. DNS not resolving → Check A/AAAA records
2. Port not forwarded → Check router port 8443 forwarding
3. Firewall blocking → Check macOS firewall settings
4. Wrong port → Verify server is running on correct port

**Debug steps:**
```bash
# 1. Check DNS resolution
dig video.example.com

# 2. Check if server is listening
lsof -i :8443

# 3. Test from terminal
curl https://video.example.com:8443/api/v1/health
```

### Issue: Works on LAN but not remotely

**Cause:** Port forwarding not configured

**Solution:** 
1. Forward port 8443 (for app) AND port 80 (for Let's Encrypt) in router
2. Verify public IP matches DNS
3. Test from outside network (mobile data)

---

## 📊 Connection Scenarios

### Scenario 1: Home Network with Let's Encrypt

**Setup:**
- SSL: Enabled
- Domain: video.example.com
- LAN IP: 192.168.1.119
- WAN IP: 68.186.221.57

**iOS App Behavior:**
- **At home (same WiFi):** Uses `https://video.example.com:8443` (resolves to LAN IP via DNS)
- **Remote (cellular):** Uses `https://video.example.com:8443` (resolves to WAN IP via DNS)
- **Result:** Seamless! Same domain works everywhere

### Scenario 2: Home Network without SSL

**Setup:**
- SSL: Disabled
- No domain
- LAN IP: 192.168.1.119
- WAN IP: 68.186.221.57

**iOS App Behavior:**
- **At home:** Uses `http://192.168.1.119:8443` (faster, direct)
- **Remote:** Uses `http://68.186.221.57:8443` (works if port forwarded)

### Scenario 3: Development with Self-Signed

**Setup:**
- SSL: Enabled (self-signed)
- Domain: localhost.local
- LAN IP: 192.168.1.119

**iOS App Behavior:**
- **Must use:** `https://localhost.local:8443` or `https://192.168.1.119:8443` (depending on how cert was generated)
- **Requires:** Manual certificate installation on iOS device

---

## 🎯 Summary for iOS Developer

### What to Do

1. **Parse QR code** to get domain, lan, wan, protocol
2. **Check protocol:**
   - If `https` → Use domain (required!)
   - If `http` → Try LAN first, then WAN
3. **Handle SSL properly:**
   - Let's Encrypt → Just works with domain
   - Self-signed → Warn user to install certificate
4. **Test both scenarios:**
   - Home network (LAN)
   - Remote/cellular (WAN)
5. **Provide good error messages:**
   - "SSL requires domain configuration"
   - "Cannot reach server - check network"
   - "Certificate trust error - install certificate"

### What NOT to Do

- ❌ Don't use IP addresses with Let's Encrypt SSL
- ❌ Don't assume WAN IP is always available
- ❌ Don't ignore certificate validation errors
- ❌ Don't hardcode connection priority without checking SSL

---

## 📞 Testing Checklist

- [ ] QR code includes domain when SSL enabled
- [ ] iOS connects to domain (not IP) when protocol is https
- [ ] iOS tries LAN first when protocol is http
- [ ] iOS falls back to WAN when LAN unavailable
- [ ] Certificate validation works on iOS
- [ ] Connection works from home network
- [ ] Connection works from cellular/remote
- [ ] Error messages are helpful

---

**Last Updated:** November 26, 2025  
**Version:** 2.0.0

