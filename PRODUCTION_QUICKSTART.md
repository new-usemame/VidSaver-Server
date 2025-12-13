# Production Mac Setup - Quick Start Card

**🎯 Goal:** Deploy server on production Mac with HTTPS in ~20 minutes using automated Cursor AI workflow

---

## 📦 What You'll Need

- ✅ Production Mac with Python 3.11+
- ✅ Your domain name (e.g., `videos.example.com`)
- ✅ Your email address (for Let's Encrypt)
- ✅ Access to your domain's DNS settings
- ✅ This Git repository URL

---

## 🚀 Setup Steps

### Step 1: Prepare DNS (5 minutes)
**Before cloning the repository:**

1. Get your production Mac's public IP:
   ```bash
   curl ifconfig.me
   ```

2. Go to your domain registrar's DNS settings

3. Add an A record:
   - **Type:** A
   - **Name:** `videos` (or subdomain of choice)
   - **Value:** [Your Mac's public IP from step 1]
   - **TTL:** 300

4. Wait 5-10 minutes for DNS propagation

5. Verify:
   ```bash
   dig +short videos.yourdomain.com
   # Should show your public IP
   ```

---

### Step 2: Clone Repository (1 minute)

```bash
cd ~
git clone <your-git-repo-url> VideoDownloadServer
cd VideoDownloadServer
```

**Note:** Git will automatically exclude:
- `venv/` (will create fresh)
- `config/config.yaml` (will create from template)
- `data/*.db` (will initialize)
- `certs/*.pem` (will obtain from Let's Encrypt)
- Log files, cache files, etc.

---

### Step 3: Open in Cursor (1 minute)

```bash
# Open project in Cursor IDE
cursor .
```

Or manually open Cursor and open the `VideoDownloadServer` directory.

---

### Step 4: Run Automated Setup (15-30 minutes)

**In Cursor AI chat, type:**

```
Perform @ProductionSetup.mdc
```

**The AI will ask you for:**
1. **Domain name:** `videos.yourdomain.com`
2. **Email address:** `your-email@example.com`
3. **Downloads directory:** [Press Enter for default: `~/Downloads/VideoServer`]

**The AI will automatically:**
- ✅ Create virtual environment
- ✅ Install all dependencies
- ✅ Create `config/config.yaml` with your settings
- ✅ Initialize database (`data/downloads.db`)
- ✅ Obtain Let's Encrypt SSL certificates
- ✅ Configure macOS firewall
- ✅ Test server startup
- ✅ Configure auto-start (launchd)
- ✅ Run verification tests

**Just sit back and let it work!**

---

### Step 5: Verify (2 minutes)

**Check server is running:**
```bash
curl https://localhost:8443/api/v1/health
```

**Expected response:**
```json
{
    "status": "healthy",
    "timestamp": "2025-11-08T21:00:00",
    "version": "1.0.0",
    "database": {
        "connected": true,
        "total_downloads": 0
    }
}
```

**Test external access (from iOS device or another computer):**
```
https://videos.yourdomain.com:8443/api/v1/health
```

**Check auto-start:**
```bash
launchctl list | grep videodownload
# Should show: com.videodownload.server
```

---

## ✅ Success Indicators

You're done when:
- ✅ Health endpoint responds with 200 OK
- ✅ No SSL certificate errors in browser/iOS
- ✅ Server accessible from external network
- ✅ Auto-start configured (survives reboot)
- ✅ Logs show healthy operation

---

## 🎮 Server Management Commands

### Control Server
```bash
# Start
launchctl start com.videodownload.server

# Stop
launchctl stop com.videodownload.server

# Restart
launchctl stop com.videodownload.server
launchctl start com.videodownload.server

# Check status
launchctl list | grep videodownload
ps aux | grep server.py
```

### Monitor
```bash
# View live logs
tail -f logs/server.log

# View recent errors
grep ERROR logs/server.log | tail -20

# Check downloads
ls -lh ~/Downloads/VideoServer/
```

### Test Endpoints
```bash
# Health check
curl https://videos.yourdomain.com:8443/api/v1/health

# Submit test download
curl -X POST https://videos.yourdomain.com:8443/api/v1/download \
  -H "Content-Type: application/json" \
  -d '{"url":"https://www.tiktok.com/@test/video/123","client_id":"test"}'

# View history
curl https://videos.yourdomain.com:8443/api/v1/history?limit=5
```

---

## 🔧 Troubleshooting

### Issue: Can't access from external network
```bash
# 1. Verify DNS
dig +short videos.yourdomain.com
# Should show your public IP

# 2. Test locally first
curl https://localhost:8443/api/v1/health

# 3. Check firewall
sudo /usr/libexec/ApplicationFirewall/socketfilterfw --getglobalstate

# 4. Check router port forwarding
# Port 8443 must forward to Mac's local IP
ifconfig | grep "inet " | grep -v 127.0.0.1
# Use this IP in router's port forwarding config
```

### Issue: SSL certificate error
```bash
# 1. Check certificates exist
ls -la certs/fullchain.pem certs/privkey.pem

# 2. Check certificate validity
openssl x509 -in certs/fullchain.pem -text -noout | grep "Not After"

# 3. Re-run Let's Encrypt setup
sudo bash scripts/setup_letsencrypt.sh videos.yourdomain.com your-email@example.com
launchctl restart com.videodownload.server
```

### Issue: Server won't start
```bash
# 1. Check logs
tail -f logs/server.log
tail -f logs/launchd.err.log

# 2. Check port availability
lsof -i :8443
# If something is using port 8443, kill it or change port

# 3. Test manual start
source venv/bin/activate
python server.py
# Look for error messages
```

### Issue: Database not found
```bash
# Re-initialize database
source venv/bin/activate
python scripts/init_database.py
```

---

## 📱 Connect iOS App

**Update your iOS app's API client:**

```swift
// In your iOS app
let apiClient = VideoDownloadAPIClient(
    baseURL: "https://videos.yourdomain.com:8443/api/v1"
)
```

**That's it!** No certificate installation, no special trust settings needed on iOS. Let's Encrypt certificates are automatically trusted.

**See full iOS integration guide:** `.cursor/docs/IOS_INTEGRATION_GUIDE.md`

---

## 🔒 Security Checklist

- ✅ Using Let's Encrypt SSL (not self-signed)
- ✅ Certificates auto-renew every 90 days
- ✅ Private keys never committed to Git
- ✅ Configuration file excluded from Git
- ✅ Firewall configured
- ✅ Server runs as regular user (not root)
- ✅ Log rotation enabled

---

## 📚 Detailed Documentation

| Document | Purpose |
|----------|---------|
| `.cursor/rules/ProductionSetup.mdc` | Automated workflow (what Cursor AI executes) |
| `.cursor/docs/PRODUCTION_SETUP_MAC.md` | Detailed manual setup guide |
| `.cursor/docs/GIT_MIGRATION_CHECKLIST.md` | What's excluded by Git, what to create |
| `.cursor/docs/IOS_INTEGRATION_GUIDE.md` | iOS client integration guide |
| `docs/SSL_SETUP.md` | SSL/TLS certificate setup guide |

---

## 🎉 Summary

**Total Time:** ~20-30 minutes

**What happens:**
1. DNS setup: 5 min
2. Git clone: 1 min
3. Automated Cursor setup: 15-20 min
4. Verification: 2 min

**Result:**
- ✅ Production server running 24/7
- ✅ Valid SSL certificates (iOS-compatible)
- ✅ Auto-starts on boot
- ✅ Auto-renewing certificates
- ✅ Ready for iOS app integration

---

## 🆘 Need Help?

1. Check logs: `tail -f logs/server.log`
2. Review troubleshooting section above
3. Check `.cursor/docs/Bug_tracking.md` for known issues
4. Re-run setup: `Perform @ProductionSetup.mdc` (safe to run multiple times)

---

**Last Updated:** November 8, 2025

**Version:** 1.0.0

