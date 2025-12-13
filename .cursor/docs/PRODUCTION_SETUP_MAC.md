# Production Setup Guide - macOS

**Target:** Production Mac  
**Goal:** Deploy Video Download Server with Let's Encrypt HTTPS  
**Time Required:** 30-45 minutes

---

## 🎯 Overview

This guide will walk you through deploying the Video Download Server on your production Mac with proper HTTPS using Let's Encrypt.

### What We'll Do

1. ✅ Verify prerequisites
2. ✅ Transfer server files to production Mac
3. ✅ Configure your domain
4. ✅ Set up Let's Encrypt SSL certificates
5. ✅ Start the server
6. ✅ Test from iOS device
7. ✅ Configure auto-start on boot

---

## Step 1: Prerequisites Check

### On Your Production Mac

Open Terminal and verify these requirements:

```bash
# 1. Check Python version (need 3.11+)
python3 --version
# Should show: Python 3.11.x or 3.12.x or 3.13.x

# 2. Check if Python 3 is installed
which python3
# Should show: /usr/bin/python3 or /usr/local/bin/python3

# 3. Check if pip is available
python3 -m pip --version
# Should show: pip version

# 4. Check available disk space (need at least 2GB)
df -h
```

### If Python 3.11+ is Not Installed

```bash
# Install Homebrew if not already installed
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install Python 3.13
brew install python@3.13

# Verify installation
python3 --version
```

### Domain Requirements

You mentioned you own a domain. You'll need:
- ✅ Your domain name (e.g., `myserver.example.com`)
- ✅ Access to your domain's DNS settings
- ✅ Your production Mac's public IP address

**Find Your Public IP:**
```bash
curl ifconfig.me
# Example output: 203.0.113.45
```

**Save this IP - you'll need it for DNS!**

---

## Step 2: Transfer Server Files

### Option A: Using Git (Recommended)

If your project is in a Git repository:

```bash
# On production Mac
cd ~
git clone <your-repo-url> "TikTok Downloader Server"
cd "TikTok Downloader Server"
```

### Option B: Direct Transfer (AirDrop/USB/Network)

**On Development Mac:**
```bash
# Navigate to project directory
cd ~/path/to/TikTok-Downloader-Server

# Create archive excluding unnecessary files
tar -czf server-deployment.tar.gz \
  --exclude='venv' \
  --exclude='data/downloads.db' \
  --exclude='logs' \
  --exclude='.git' \
  --exclude='__pycache__' \
  --exclude='*.pyc' \
  .

# Transfer server-deployment.tar.gz to production Mac
# (via AirDrop, USB drive, or scp)
```

**On Production Mac:**
```bash
# Create project directory
mkdir -p ~/VideoDownloadServer
cd ~/VideoDownloadServer

# Extract archive
tar -xzf ~/Downloads/server-deployment.tar.gz

# Verify files
ls -la
```

### Option C: Manual Network Transfer

**On Development Mac:**
```bash
# From project root
rsync -avz --exclude 'venv' --exclude 'data' --exclude 'logs' \
  . username@production-mac-ip:~/VideoDownloadServer/
```

---

## Step 3: Initial Server Setup

### On Production Mac:

```bash
# Navigate to project directory
cd ~/VideoDownloadServer

# Create Python virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install dependencies
pip install -r requirements.txt

# Verify installation
pip list
```

**Expected output should include:**
- fastapi
- uvicorn
- pydantic
- pyyaml
- yt-dlp

### Initialize Database

```bash
# Still in project directory with venv activated
python scripts/init_database.py
```

**Expected output:**
```
✅ Database initialized successfully (schema version: 1)
Database location: /Users/username/VideoDownloadServer/data/downloads.db
```

---

## Step 4: Configure Your Domain

### A. Update DNS Settings

**Go to your domain registrar's DNS management panel and add an A record:**

| Type | Name | Value | TTL |
|------|------|-------|-----|
| A | @ (or subdomain) | [Your Public IP] | 300 |

**Example:**
- **Type:** A
- **Name:** `videos` (creates `videos.yourdomain.com`)
- **Value:** `203.0.113.45` (your production Mac's public IP)
- **TTL:** 300 (5 minutes)

**Alternative:** Use root domain:
- **Name:** `@` (creates `yourdomain.com`)

💡 **Tip:** Use a subdomain like `videos.yourdomain.com` or `dl.yourdomain.com` for cleaner organization.

### B. Verify DNS Propagation

Wait 5-10 minutes, then test:

```bash
# Replace with your domain
dig videos.yourdomain.com

# Or use nslookup
nslookup videos.yourdomain.com
```

**Expected output should show your public IP address.**

### C. Update Server Configuration

Edit the server configuration:

```bash
# Open configuration file
nano config/config.yaml
```

**Update these settings:**

```yaml
app:
  name: "Video Download Server"
  version: "1.0.0"
  environment: "Production"

server:
  host: "0.0.0.0"
  port: 8443
  reload: false  # Important: Set to false in production

ssl:
  use_letsencrypt: true  # Enable Let's Encrypt
  domain: "videos.yourdomain.com"  # YOUR DOMAIN HERE
  email: "your-email@example.com"  # YOUR EMAIL HERE
  cert_file: "certs/fullchain.pem"
  key_file: "certs/privkey.pem"

downloads:
  output_directory: "/Users/YOUR-USERNAME/Downloads/VideoServer"  # Update path
  max_concurrent: 1

database:
  path: "data/downloads.db"
  max_connections: 5

logging:
  level: "INFO"
  file_path: "logs/server.log"
  max_bytes: 10485760
  backup_count: 5
```

**Save and exit:** Press `Ctrl+O`, `Enter`, then `Ctrl+X`

---

## Step 5: Configure Firewall

### Open Port 8443

macOS uses `pf` (packet filter) firewall. You need to allow incoming connections on port 8443.

**Option A: Using macOS System Preferences (Easiest)**

1. Go to **System Preferences** → **Security & Privacy** → **Firewall**
2. Click **Firewall Options**
3. Click **+** to add an application
4. Navigate to and select `Python` or your app
5. Set to **Allow incoming connections**

**Option B: Using Terminal**

```bash
# Check if firewall is enabled
sudo /usr/libexec/ApplicationFirewall/socketfilterfw --getglobalstate

# If enabled, allow Python
sudo /usr/libexec/ApplicationFirewall/socketfilterfw --add /usr/bin/python3
sudo /usr/libexec/ApplicationFirewall/socketfilterfw --unblockapp /usr/bin/python3
```

### Open Port on Router (Important!)

**If your Mac is behind a router, you need port forwarding:**

1. Log into your router's admin panel (usually http://192.168.1.1)
2. Find **Port Forwarding** section
3. Add rule:
   - **External Port:** 8443
   - **Internal Port:** 8443
   - **Internal IP:** Your Mac's local IP (find with `ifconfig | grep "inet "`)
   - **Protocol:** TCP

---

## Step 6: Set Up Let's Encrypt SSL

### A. Run Setup Script

```bash
# Make script executable
chmod +x scripts/setup_letsencrypt.sh

# Run Let's Encrypt setup
sudo bash scripts/setup_letsencrypt.sh videos.yourdomain.com your-email@example.com
```

**The script will:**
1. ✅ Install Certbot (if needed)
2. ✅ Request SSL certificate from Let's Encrypt
3. ✅ Verify domain ownership (HTTP challenge)
4. ✅ Download certificates
5. ✅ Copy certificates to `certs/` directory
6. ✅ Set up auto-renewal

**Expected output:**
```
✅ Certificates obtained successfully!
Certificate: /etc/letsencrypt/live/videos.yourdomain.com/fullchain.pem
Private Key: /etc/letsencrypt/live/videos.yourdomain.com/privkey.pem
Certificates copied to: /Users/username/VideoDownloadServer/certs/
✅ Let's Encrypt setup complete!
```

### B. Verify Certificates

```bash
# Check certificates exist
ls -lh certs/
```

**You should see:**
- `fullchain.pem`
- `privkey.pem`

### C. Test Certificate

```bash
# Verify certificate is valid
openssl x509 -in certs/fullchain.pem -text -noout | grep "Issuer\|Subject\|Not After"
```

**Expected output:**
```
Issuer: C = US, O = Let's Encrypt, CN = R3
Subject: CN = videos.yourdomain.com
Not After : Feb  5 12:34:56 2026 GMT
```

---

## Step 7: Start the Server

### First Test Run

```bash
# Navigate to project directory
cd ~/VideoDownloadServer

# Activate virtual environment
source venv/bin/activate

# Start server
python server.py
```

**Expected output:**
```
2025-11-07 21:00:00 | INFO | Logging system initialized
2025-11-07 21:00:00 | INFO | Video Download Server starting up...
2025-11-07 21:00:00 | INFO | Version: 1.0.0
2025-11-07 21:00:00 | INFO | Environment: Production
2025-11-07 21:00:00 | INFO | Server: 0.0.0.0:8443
2025-11-07 21:00:00 | INFO | SSL: Let's Encrypt
2025-11-07 21:00:00 | INFO | Certificate: certs/fullchain.pem
2025-11-07 21:00:00 | INFO | Download worker started
INFO: Uvicorn running on https://0.0.0.0:8443 (Press CTRL+C to quit)
```

**🎉 If you see this, your server is running!**

### Test Locally

**In a new terminal window on the same Mac:**

```bash
# Test health endpoint
curl -k https://localhost:8443/api/v1/health | python3 -m json.tool
```

**Expected response:**
```json
{
    "status": "healthy",
    "timestamp": "2025-11-07T21:00:05",
    "version": "1.0.0",
    "database": {
        "connected": true,
        "total_downloads": 0
    }
}
```

### Test from Another Device on Same Network

**On another computer/phone connected to same WiFi:**

```bash
# Use your Mac's local IP
curl https://192.168.1.XXX:8443/api/v1/health
```

---

## Step 8: Test from iOS Device

### A. Test from Safari

**On your iOS device:**

1. Open Safari
2. Go to: `https://videos.yourdomain.com:8443/api/v1/health`
3. You should see JSON response

**If you get a certificate error:**
- This shouldn't happen with Let's Encrypt
- Verify DNS is pointing to correct IP
- Wait a few more minutes for DNS propagation

### B. Test with iOS App

**Once your iOS app is ready:**

1. Update `baseURL` in your iOS app:
   ```swift
   let baseURL = "https://videos.yourdomain.com:8443/api/v1"
   ```

2. Build and run app on device (not simulator)

3. Try sharing a TikTok/Instagram video

4. Check server logs:
   ```bash
   tail -f logs/server.log
   ```

### C. Submit Test Download

**From iOS Safari or your app:**

```javascript
// You can test in Safari console
fetch('https://videos.yourdomain.com:8443/api/v1/download', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({
    url: 'https://www.tiktok.com/@user/video/123',
    client_id: 'test-ios'
  })
})
.then(r => r.json())
.then(d => console.log(d))
```

---

## Step 9: Configure Auto-Start on Boot

### Create Launch Agent

**This ensures the server starts automatically when your Mac boots.**

```bash
# Create launch agent directory if it doesn't exist
mkdir -p ~/Library/LaunchAgents

# Create launch agent plist
nano ~/Library/LaunchAgents/com.videodownload.server.plist
```

**Paste this content (update paths):**

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.videodownload.server</string>
    
    <key>ProgramArguments</key>
    <array>
        <string>/Users/YOUR-USERNAME/VideoDownloadServer/venv/bin/python</string>
        <string>/Users/YOUR-USERNAME/VideoDownloadServer/server.py</string>
    </array>
    
    <key>WorkingDirectory</key>
    <string>/Users/YOUR-USERNAME/VideoDownloadServer</string>
    
    <key>RunAtLoad</key>
    <true/>
    
    <key>KeepAlive</key>
    <true/>
    
    <key>StandardOutPath</key>
    <string>/Users/YOUR-USERNAME/VideoDownloadServer/logs/launchd.out.log</string>
    
    <key>StandardErrorPath</key>
    <string>/Users/YOUR-USERNAME/VideoDownloadServer/logs/launchd.err.log</string>
    
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
    </dict>
</dict>
</plist>
```

**Important:** Replace `YOUR-USERNAME` with your actual macOS username!

**Save and exit:** `Ctrl+O`, `Enter`, `Ctrl+X`

### Load Launch Agent

```bash
# Load the launch agent
launchctl load ~/Library/LaunchAgents/com.videodownload.server.plist

# Verify it's running
launchctl list | grep videodownload
```

### Test Auto-Start

```bash
# Stop current server (Ctrl+C in terminal where it's running)

# Start via launch agent
launchctl start com.videodownload.server

# Check if it's running
curl https://localhost:8443/api/v1/health

# Check logs
tail -f logs/launchd.out.log
```

### Useful Commands

```bash
# Stop server
launchctl stop com.videodownload.server

# Restart server
launchctl stop com.videodownload.server
launchctl start com.videodownload.server

# Unload (disable auto-start)
launchctl unload ~/Library/LaunchAgents/com.videodownload.server.plist

# Reload after editing plist
launchctl unload ~/Library/LaunchAgents/com.videodownload.server.plist
launchctl load ~/Library/LaunchAgents/com.videodownload.server.plist
```

---

## Step 10: Monitoring & Maintenance

### Check Server Status

```bash
# View real-time logs
tail -f logs/server.log

# Check if server is responding
curl https://videos.yourdomain.com:8443/api/v1/health

# Check download history
curl https://videos.yourdomain.com:8443/api/v1/history?limit=10
```

### View Downloaded Videos

```bash
# List downloaded videos
ls -lh ~/Downloads/VideoServer/

# Check disk usage
du -sh ~/Downloads/VideoServer/
```

### Certificate Renewal

**Let's Encrypt certificates auto-renew!** Certbot sets up a cron job automatically.

**To manually renew:**

```bash
sudo certbot renew

# Copy renewed certs
sudo cp /etc/letsencrypt/live/videos.yourdomain.com/fullchain.pem ~/VideoDownloadServer/certs/
sudo cp /etc/letsencrypt/live/videos.yourdomain.com/privkey.pem ~/VideoDownloadServer/certs/
sudo chown $(whoami) ~/VideoDownloadServer/certs/*.pem

# Restart server
launchctl stop com.videodownload.server
launchctl start com.videodownload.server
```

### Database Maintenance

```bash
# Backup database
cp data/downloads.db data/downloads.db.backup

# Check database size
du -h data/downloads.db

# View download statistics
sqlite3 data/downloads.db "SELECT status, COUNT(*) FROM downloads GROUP BY status;"
```

### Cleanup Old Downloads (Optional)

```bash
# Delete downloads older than 30 days
find ~/Downloads/VideoServer/ -type f -mtime +30 -delete

# Or manually review and delete
ls -lt ~/Downloads/VideoServer/
```

---

## Troubleshooting

### Issue: Can't Access from Internet

**Symptoms:** Works on local network but not from internet

**Solutions:**
1. Verify DNS is pointing to correct public IP:
   ```bash
   dig videos.yourdomain.com
   ```

2. Check port forwarding on router (port 8443)

3. Verify firewall allows incoming connections

4. Test with online tools: https://www.yougetsignal.com/tools/open-ports/

### Issue: SSL Certificate Error

**Symptoms:** "Certificate is not trusted" on iOS

**Solutions:**
1. Verify Let's Encrypt certificate is installed:
   ```bash
   openssl s_client -connect videos.yourdomain.com:8443 -servername videos.yourdomain.com
   ```

2. Check certificate expiration:
   ```bash
   openssl x509 -in certs/fullchain.pem -noout -dates
   ```

3. Ensure fullchain.pem (not cert.pem) is being used

### Issue: Server Not Starting

**Symptoms:** Server crashes on start

**Solutions:**
1. Check logs:
   ```bash
   tail -f logs/server.log
   tail -f logs/launchd.err.log
   ```

2. Verify port 8443 is not in use:
   ```bash
   lsof -i :8443
   ```

3. Test manually:
   ```bash
   source venv/bin/activate
   python server.py
   ```

4. Check Python version:
   ```bash
   python3 --version
   # Must be 3.11+
   ```

### Issue: Downloads Failing

**Symptoms:** Videos submitted but fail to download

**Solutions:**
1. Check yt-dlp is installed:
   ```bash
   source venv/bin/activate
   pip show yt-dlp
   ```

2. Test yt-dlp directly:
   ```bash
   source venv/bin/activate
   yt-dlp --version
   yt-dlp "https://www.tiktok.com/@user/video/123"
   ```

3. Check output directory permissions:
   ```bash
   ls -ld ~/Downloads/VideoServer/
   ```

4. Check server logs for specific errors:
   ```bash
   grep "ERROR" logs/server.log | tail -20
   ```

---

## Quick Reference

### Important Files

| File | Location | Purpose |
|------|----------|---------|
| Server | `~/VideoDownloadServer/server.py` | Main entry point |
| Config | `~/VideoDownloadServer/config/config.yaml` | Configuration |
| Database | `~/VideoDownloadServer/data/downloads.db` | Download records |
| Logs | `~/VideoDownloadServer/logs/server.log` | Server logs |
| SSL Certs | `~/VideoDownloadServer/certs/` | SSL certificates |
| Launch Agent | `~/Library/LaunchAgents/com.videodownload.server.plist` | Auto-start config |

### Important Commands

```bash
# Start server manually
cd ~/VideoDownloadServer && source venv/bin/activate && python server.py

# Start via launch agent
launchctl start com.videodownload.server

# Stop server
launchctl stop com.videodownload.server

# View logs
tail -f ~/VideoDownloadServer/logs/server.log

# Test health
curl https://videos.yourdomain.com:8443/api/v1/health

# Update code (if using git)
cd ~/VideoDownloadServer && git pull

# Restart after update
launchctl stop com.videodownload.server
launchctl start com.videodownload.server
```

### URLs to Bookmark

- **API Docs:** `https://videos.yourdomain.com:8443/docs`
- **Health Check:** `https://videos.yourdomain.com:8443/api/v1/health`
- **History:** `https://videos.yourdomain.com:8443/api/v1/history`

---

## Security Checklist

- ✅ Using Let's Encrypt SSL (not self-signed)
- ✅ Firewall configured to allow only port 8443
- ✅ Server running as regular user (not root)
- ✅ Log rotation enabled
- ✅ Database not publicly accessible
- ✅ Domain DNS secured
- ⚠️ Consider adding API authentication for public deployment

---

## Next Steps

1. ✅ Complete all steps above
2. ✅ Test thoroughly from iOS device
3. ✅ Verify auto-start works (restart Mac)
4. ✅ Connect iOS app
5. ✅ Monitor for a few days
6. ✅ Set up backup strategy (optional)

---

## Support

### View API Documentation

Visit: `https://videos.yourdomain.com:8443/docs`

### Check Logs

```bash
# Server logs
tail -f ~/VideoDownloadServer/logs/server.log

# Launch agent logs
tail -f ~/VideoDownloadServer/logs/launchd.out.log
tail -f ~/VideoDownloadServer/logs/launchd.err.log
```

### Test Endpoints

```bash
# Health check
curl https://videos.yourdomain.com:8443/api/v1/health

# Submit download
curl -X POST https://videos.yourdomain.com:8443/api/v1/download \
  -H "Content-Type: application/json" \
  -d '{"url":"https://www.tiktok.com/@user/video/123","client_id":"test"}'

# Check history
curl https://videos.yourdomain.com:8443/api/v1/history?limit=5
```

---

**🎉 Congratulations! Your production server is now running with HTTPS! 🎉**

Your iOS device can now securely connect and download videos! 🚀

