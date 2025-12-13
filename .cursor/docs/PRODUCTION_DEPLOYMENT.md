# 🚀 Production Mac Deployment Guide

**Complete step-by-step guide to deploy the Video Download Server on your production Mac.**

---

## 📋 Prerequisites

- ✅ macOS 10.15+ (Catalina or newer)
- ✅ Python 3.11+ installed (`python3 --version`)
- ✅ Network access on port 58443
- ✅ (Optional) Domain name if using Let's Encrypt

---

## 🎯 Deployment Options

Choose the option that best fits your needs:

| Option | Use Case | Setup Time |
|--------|----------|------------|
| **Option 1: Quick Setup** | Testing, personal use | 10 minutes |
| **Option 2: Production with Domain** | Public access with SSL | 30 minutes |
| **Option 3: Auto-Start Service** | Always-on background service | 45 minutes |

---

## 🚀 Option 1: Quick Setup (Recommended to Start)

### Step 1: Copy Files to Production Mac

**Method A: Using Git (Recommended)**
```bash
# On production Mac
cd ~
git clone <your-repo-url> "TikTok Downloader Server"
cd "TikTok Downloader Server"
```

**Method B: Using rsync (if no Git)**
```bash
# From development Mac
rsync -avz --exclude 'venv' --exclude '__pycache__' \
  ~/path/to/TikTok-Downloader-Server/ \
  user@production-mac:"~/TikTok Downloader Server/"

# Then SSH into production Mac
ssh user@production-mac
cd "~/TikTok Downloader Server"
```

**Method C: Using AirDrop/Manual Copy**
```bash
# 1. Compress project folder (excluding venv)
# 2. Copy to production Mac via AirDrop
# 3. Extract to home directory
cd "~/TikTok Downloader Server"
```

---

### Step 2: Install Python and Dependencies

```bash
# Check Python version (need 3.11+)
python3 --version

# If Python not installed, install via Homebrew:
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
brew install python@3.13

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

**Expected output:**
```
Successfully installed:
  - fastapi
  - uvicorn
  - pydantic
  - pyyaml
  - yt-dlp
  - ... (and dependencies)
```

---

### Step 3: Configure for Production

**Copy example config:**
```bash
cp config/config.yaml.example config/config.yaml
```

**Edit configuration:**
```bash
nano config/config.yaml
# or
open -a TextEdit config/config.yaml
```

**Key settings to change:**
```yaml
server:
  host: "0.0.0.0"              # Listen on all interfaces
  port: 58443                   # Already set!
  domain: null                  # Set later if using Let's Encrypt
  use_letsencrypt: false        # Set to true if you have a domain

database:
  path: "data/downloads.db"     # Local SQLite database

downloads:
  output_directory: "~/Videos/TikTokDownloads"  # ← Change to your preference
  max_concurrent: 1             # Keep at 1 for stability

logging:
  level: "INFO"                 # Keep INFO for production
  file: "logs/server.log"       # Logs location
```

---

### Step 4: Initialize Database

```bash
# Create database
python scripts/init_database.py
```

**Expected output:**
```
Initializing database at: /Users/[user]/TikTok Downloader Server/data/downloads.db
Creating new database...
✅ Database initialized successfully (schema version: 1)
```

---

### Step 5: Generate SSL Certificates

**For testing (self-signed):**
```bash
bash scripts/generate_selfsigned.sh
```

This creates:
- `certs/server.crt` - SSL certificate
- `certs/server.key` - Private key

**Note:** Self-signed certificates require manual iOS trust setup. For production with no iOS setup, use Let's Encrypt (see Option 2).

---

### Step 6: Test the Server

```bash
# Start server
python server.py
```

**Expected output:**
```
2025-11-07 21:07:40 | INFO | Video Download Server starting up...
2025-11-07 21:07:40 | INFO | Server: 0.0.0.0:58443
2025-11-07 21:07:40 | INFO | Download worker started
INFO: Uvicorn running on https://0.0.0.0:58443
```

**Test from same Mac:**
```bash
# Open new terminal
curl -k https://localhost:58443/api/v1/health | jq
```

**Expected response:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "database": {
    "connected": true,
    "total_downloads": 0
  }
}
```

---

### Step 7: Test from iOS Device

**Get your Mac's IP address:**
```bash
ifconfig | grep "inet " | grep -v 127.0.0.1
```

**From iOS Safari:**
```
https://192.168.1.100:58443/docs
```

**If using self-signed certificate:**
1. Safari will show "This connection is not private"
2. Tap "Show Details"
3. Tap "Visit this website"
4. Tap "Visit Website" again

---

### Step 8: Keep Server Running

**Option A: Run in Background (Simple)**
```bash
# Start in background
nohup python server.py > logs/nohup.log 2>&1 &

# Save process ID
echo $! > server.pid

# Check if running
ps aux | grep "python server.py"
```

**Stop server:**
```bash
kill $(cat server.pid)
rm server.pid
```

**Option B: Use screen (Better)**
```bash
# Install screen if needed
brew install screen

# Start in screen session
screen -S videoserver
python server.py

# Detach: Press Ctrl+A then D

# Re-attach later:
screen -r videoserver

# Kill session:
screen -X -S videoserver quit
```

---

## 🌐 Option 2: Production with Domain (Let's Encrypt)

### Prerequisites
- ✅ Domain name (e.g., `videos.yourdomain.com`)
- ✅ DNS A record pointing to your Mac's public IP
- ✅ Port 58443 forwarded in router (if behind firewall)

### Step 1: Configure Domain

**Edit config.yaml:**
```yaml
server:
  host: "0.0.0.0"
  port: 58443
  domain: "videos.yourdomain.com"     # ← Your domain
  use_letsencrypt: true               # ← Enable Let's Encrypt
  letsencrypt_email: "you@email.com"  # ← Your email
```

### Step 2: Set Up Let's Encrypt

```bash
# Install certbot
brew install certbot

# Run setup script (this will prompt for domain confirmation)
bash scripts/setup_letsencrypt.sh videos.yourdomain.com

# Follow prompts - it will:
# 1. Verify domain ownership
# 2. Generate certificates
# 3. Set up auto-renewal
```

### Step 3: Verify Certificates

```bash
# Check certificate
openssl x509 -in certs/letsencrypt/fullchain.pem -text -noout | grep "Subject:"

# Test server
python server.py
```

### Step 4: Test from iOS (No Setup Required!)

```
https://videos.yourdomain.com:58443/docs
```

✅ **Should work immediately - no certificate installation needed!**

---

## 🔄 Option 3: Auto-Start Service (Always On)

### Step 1: Create Launch Agent

```bash
# Create plist file
nano ~/Library/LaunchAgents/com.videoserver.plist
```

**Paste this (update paths):**
```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.videoserver</string>
    
    <key>ProgramArguments</key>
    <array>
        <string>/Users/YOUR_USERNAME/TikTok Downloader Server/venv/bin/python</string>
        <string>/Users/YOUR_USERNAME/TikTok Downloader Server/server.py</string>
    </array>
    
    <key>WorkingDirectory</key>
    <string>/Users/YOUR_USERNAME/TikTok Downloader Server</string>
    
    <key>RunAtLoad</key>
    <true/>
    
    <key>KeepAlive</key>
    <true/>
    
    <key>StandardOutPath</key>
    <string>/Users/YOUR_USERNAME/TikTok Downloader Server/logs/service.log</string>
    
    <key>StandardErrorPath</key>
    <string>/Users/YOUR_USERNAME/TikTok Downloader Server/logs/service-error.log</string>
    
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
    </dict>
</dict>
</plist>
```

**Important:** Replace `YOUR_USERNAME` with your actual macOS username!

### Step 2: Load and Start Service

```bash
# Load the service
launchctl load ~/Library/LaunchAgents/com.videoserver.plist

# Start the service
launchctl start com.videoserver

# Check if running
launchctl list | grep videoserver
ps aux | grep "python server.py"
```

### Step 3: Manage Service

```bash
# Stop service
launchctl stop com.videoserver

# Restart service
launchctl stop com.videoserver && launchctl start com.videoserver

# Unload service (disable auto-start)
launchctl unload ~/Library/LaunchAgents/com.videoserver.plist

# View logs
tail -f logs/service.log
tail -f logs/service-error.log
```

### Step 4: Verify Auto-Start

```bash
# Reboot your Mac
sudo shutdown -r now

# After reboot, check if server started automatically
launchctl list | grep videoserver
curl -k https://localhost:58443/api/v1/health
```

---

## 🔍 Troubleshooting

### Issue: Port Already in Use

```bash
# Find what's using port 58443
sudo lsof -i :58443

# Kill the process
kill -9 <PID>
```

### Issue: Permission Denied

```bash
# Fix permissions
chmod +x scripts/*.sh
chmod 755 venv/bin/python
```

### Issue: Can't Connect from iOS

```bash
# Check firewall
sudo /usr/libexec/ApplicationFirewall/socketfilterfw --getglobalstate

# Allow Python through firewall
sudo /usr/libexec/ApplicationFirewall/socketfilterfw --add $(which python3)
sudo /usr/libexec/ApplicationFirewall/socketfilterfw --unblock $(which python3)
```

### Issue: Database Locked

```bash
# Stop all instances
pkill -f "python server.py"

# Restart
python server.py
```

### Issue: SSL Certificate Errors

```bash
# Regenerate self-signed certificate
rm -rf certs/server.*
bash scripts/generate_selfsigned.sh

# Or check Let's Encrypt certificate
sudo certbot certificates
```

---

## 📊 Monitoring

### View Logs

```bash
# Real-time logs
tail -f logs/server.log

# Search for errors
grep ERROR logs/server.log

# View last 100 lines
tail -n 100 logs/server.log
```

### Check Server Status

```bash
# Health check
curl -k https://localhost:58443/api/v1/health | jq

# View downloads
curl -k https://localhost:58443/api/v1/history | jq

# Check database
sqlite3 data/downloads.db "SELECT COUNT(*) FROM downloads;"
```

### Monitor Resources

```bash
# CPU and memory usage
ps aux | grep python

# Disk space
df -h ~/Videos/TikTokDownloads

# Database size
du -h data/downloads.db
```

---

## 🔒 Security Checklist

- [ ] Changed default port from 8443 to 58443
- [ ] Using Let's Encrypt SSL (or self-signed for testing)
- [ ] Configured firewall to allow port 58443
- [ ] Set up log rotation (logs don't grow forever)
- [ ] Regular backups of database and videos
- [ ] Strong password on Mac user account
- [ ] Mac set to lock when idle

---

## 🔄 Updating the Server

```bash
# Stop server
launchctl stop com.videoserver  # If using service
# or kill the process

# Pull updates
cd "~/TikTok Downloader Server"
git pull  # If using Git

# Update dependencies
source venv/bin/activate
pip install --upgrade -r requirements.txt

# Restart server
launchctl start com.videoserver  # If using service
# or python server.py &
```

---

## 📱 iOS App Integration

Once deployed, your iOS app should connect to:

```
Production Mac (Local Network):
https://192.168.1.100:58443

Production Mac (with Domain):
https://videos.yourdomain.com:58443
```

**API Endpoints:**
- POST `/api/v1/download` - Submit video URL
- GET `/api/v1/status/{id}` - Check download status
- GET `/api/v1/history` - View download history
- GET `/api/v1/health` - Health check

---

## ✅ Deployment Checklist

### Basic Setup
- [ ] Python 3.11+ installed
- [ ] Virtual environment created
- [ ] Dependencies installed
- [ ] Config file created and customized
- [ ] Database initialized
- [ ] SSL certificates generated
- [ ] Server starts successfully
- [ ] Health check works

### Network Setup
- [ ] Port 58443 accessible
- [ ] Firewall configured
- [ ] Can access from same network
- [ ] (Optional) Port forwarding configured
- [ ] (Optional) Domain DNS configured

### Production Ready
- [ ] Auto-start service configured
- [ ] Logs are being written
- [ ] Monitoring in place
- [ ] Backup strategy planned
- [ ] Documentation read

### iOS Testing
- [ ] Can connect from iOS Safari
- [ ] API endpoints work
- [ ] Downloads complete successfully
- [ ] Status updates work

---

## 🎯 Quick Start Commands Summary

```bash
# 1. Setup
cd "~/TikTok Downloader Server"
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 2. Configure
cp config/config.yaml.example config/config.yaml
nano config/config.yaml  # Edit settings

# 3. Initialize
python scripts/init_database.py
bash scripts/generate_selfsigned.sh

# 4. Run
python server.py

# 5. Test
curl -k https://localhost:58443/api/v1/health
```

---

## 📞 Need Help?

Check logs first:
```bash
tail -f logs/server.log
```

Common issues documented in `Bug_tracking.md`

---

**🎉 You're Ready for Production!**

Your Video Download Server is now deployed and ready to handle downloads from your iOS app!

