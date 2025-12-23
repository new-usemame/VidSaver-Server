# Simple Setup Guide - HTTP Mode (Recommended)

**⚡ Quick, Easy, No Certificates Needed!**

This guide shows you how to run the server in **HTTP mode** for simple local network usage. No SSL certificates, no domain names, no complex setup!

---

## 🎯 Perfect For

- ✅ Personal use on home/office network
- ✅ iOS app development
- ✅ Open source projects needing "just works" setup
- ✅ No sensitive data transmission
- ✅ Local network only (no internet exposure)

---

## 🚀 Quick Start (5 Minutes)

### 1. Clone & Install

```bash
# Clone repository
git clone <your-repo-url> VideoDownloadServer
cd VideoDownloadServer

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Copy Config

```bash
cp config/config.yaml.example config/config.yaml
```

### 3. Start Server

```bash
python manage.py start
```

**That's it!** The server is now running at `http://0.0.0.0:58443`

---

## 📱 iOS App Configuration

### Step 1: Add App Transport Security Exception

Add this to your iOS app's `Info.plist`:

```xml
<key>NSAppTransportSecurity</key>
<dict>
    <key>NSAllowsLocalNetworking</key>
    <true/>
</dict>
```

**What this does:** Allows your iOS app to connect to HTTP servers on the local network. This is a standard iOS feature for home automation apps, development servers, etc.

**Is it safe?** Yes! `NSAllowsLocalNetworking` only allows HTTP to local network IPs (192.168.x.x, 10.x.x.x, 172.16.x.x). It does NOT allow HTTP to internet addresses.

### Step 2: Find Your Server's IP Address

On your Mac running the server:

```bash
ifconfig | grep "inet " | grep -v 127.0.0.1 | awk '{print $2}' | head -1
```

Example output: `192.168.1.100`

### Step 3: Configure iOS App

In your iOS app code:

```swift
let apiClient = VideoDownloadAPIClient(
    baseURL: "http://192.168.1.100:58443/api/v1"
)
```

**Change `192.168.1.100` to your server's actual IP!**

### Step 4: Test

On your iOS device (connected to same WiFi):

1. Open Safari
2. Go to: `http://192.168.1.100:58443/api/v1/health`
3. You should see JSON response

---

## ⚙️ Configuration

The default configuration is already set for HTTP mode in `config/config.yaml`:

```yaml
server:
  host: "0.0.0.0"  # Listen on all interfaces
  port: 58443      # Server port
  
  ssl:
    enabled: false  # HTTP mode (default)
```

**No changes needed!** Just run and go.

---

## 🔧 Management Commands

### Start Server

```bash
source venv/bin/activate
python manage.py start
```

### Check Server is Running

```bash
curl http://localhost:58443/api/v1/health
```

### Get Server IP

```bash
ifconfig | grep "inet " | grep -v 127.0.0.1 | awk '{print $2}' | head -1
```

### View Logs

```bash
tail -f logs/server.log
```

### Stop Server

```bash
python manage.py stop
```

---

## 🌐 Access URLs

| From | URL |
|------|-----|
| Same Mac | `http://localhost:58443/api/v1/health` |
| Other devices on same network | `http://192.168.1.100:58443/api/v1/health` |
| API Documentation | `http://192.168.1.100:58443/docs` |

*(Replace `192.168.1.100` with your server's actual IP)*

---

## 🔒 Security Notes

### Is HTTP Safe for This?

**Yes**, for local network use:

- ✅ Your WiFi password is the security layer
- ✅ Traffic never leaves your local network
- ✅ Not exposed to internet (no port forwarding needed)
- ✅ No sensitive data is stored (just video URLs and metadata)
- ✅ Standard practice for home servers, dev servers, IoT devices

### Do I Need HTTPS?

**Only if:**
- ❌ You need internet-facing access (not recommended for personal use)
- ❌ Your company/organization requires encryption
- ❌ You're transmitting sensitive data (you're not)

**For most users:** HTTP on local network is perfect! 🎉

---

## 🚫 What You DON'T Need

With HTTP mode, you avoid:
- ❌ No domain name required
- ❌ No DNS configuration
- ❌ No SSL certificate generation
- ❌ No Let's Encrypt setup
- ❌ No port 80/443 opening
- ❌ No certificate trust on iOS
- ❌ No router port forwarding (unless you want internet access)

---

## 🆚 HTTP vs HTTPS Comparison

| Feature | HTTP Mode (Simple) | HTTPS Mode (Advanced) |
|---------|-------------------|----------------------|
| **Setup Time** | 5 minutes | 30-45 minutes |
| **Domain Required** | ❌ No | ✅ Yes |
| **DNS Configuration** | ❌ No | ✅ Yes |
| **SSL Certificates** | ❌ No | ✅ Yes |
| **Port 80/443 Open** | ❌ No | ✅ Yes |
| **iOS Trust Setup** | ❌ No | ❌ No (with Let's Encrypt) |
| **Local Network** | ✅ Yes | ✅ Yes |
| **Internet Access** | ❌ No* | ✅ Yes |
| **Encrypted Traffic** | ❌ No | ✅ Yes |

*You can enable internet access with HTTP via port forwarding, but it's not recommended for security.

---

## 🔧 Advanced: Enable HTTPS Later

If you decide you want HTTPS later, it's easy!

### Edit `config/config.yaml`:

```yaml
server:
  ssl:
    enabled: true              # Enable SSL
    use_letsencrypt: true      # Use Let's Encrypt
    domain: "videos.yourdomain.com"
    letsencrypt_email: "your-email@example.com"
```

### Run Let's Encrypt Setup:

```bash
sudo bash scripts/setup_letsencrypt.sh videos.yourdomain.com your-email@example.com
```

### Restart Server:

```bash
python server.py
```

See `PRODUCTION_SETUP_MAC.md` for detailed HTTPS setup instructions.

---

## 📋 Troubleshooting

### Can't Connect from iOS Device

1. **Check both devices are on same WiFi**
   ```bash
   # On Mac
   ifconfig | grep "inet " | grep -v 127.0.0.1
   
   # On iOS, go to Settings → WiFi → Info icon → check IP
   # Should be on same subnet (e.g., both 192.168.1.x)
   ```

2. **Check Mac firewall allows Python**
   - System Preferences → Security & Privacy → Firewall
   - Click "Firewall Options"
   - Ensure Python is allowed

3. **Verify server is running**
   ```bash
   curl http://localhost:58443/api/v1/health
   ```

4. **Check Info.plist has ATS exception**
   - Look for `NSAllowsLocalNetworking` = `true`

### "Connection Refused" Error

- Server may not be running: `python server.py`
- Wrong port: Check config.yaml for correct port
- Wrong IP: Run `ifconfig` to get current IP

### iOS App Shows HTTPS Error

- You're using `https://` instead of `http://`
- Change URL to `http://` (not `https://`)

---

## 🎉 Success!

If you can:
1. ✅ Start server: `python server.py`
2. ✅ Test locally: `curl http://localhost:58443/api/v1/health`
3. ✅ Connect from iOS: Safari shows JSON response

**You're done!** Your server is ready for use! 🚀

---

## 📚 Next Steps

- Read `.cursor/docs/IOS_INTEGRATION_GUIDE.md` for full iOS client implementation
- Check `PRODUCTION_QUICKSTART.md` if you want HTTPS later
- Run tests: `pytest`
- View API docs: `http://[your-server-ip]:58443/docs`

---

## 🆘 Need Help?

- Check logs: `tail -f logs/server.log`
- Test health endpoint: `curl http://localhost:58443/api/v1/health`
- Check port: `lsof -i :58443`
- Verify IP: `ifconfig | grep "inet "`

---

**Last Updated:** December 16, 2025  
**Version:** 1.0.0 (HTTP Mode)

