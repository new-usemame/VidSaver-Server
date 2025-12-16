# 🚀 Quick Deployment to Production Mac

**5-Minute Setup Guide**

## Step 1: Copy Project
```bash
# Option A: Using Git
git clone <repo-url> "TikTok Downloader Server"

# Option B: Using rsync from dev Mac
rsync -avz --exclude 'venv' "/path/to/project/" user@prod-mac:"~/TikTok Downloader Server/"
```

## Step 2: Setup Environment
```bash
cd "~/TikTok Downloader Server"
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Step 3: Configure
```bash
cp config/config.yaml.example config/config.yaml
nano config/config.yaml
# Edit: output_directory, domain (if needed)
```

## Step 4: Run
```bash
# Start server
python manage.py start

# Or run in background without dashboard
python server.py &
```

> **Note:** Database initializes automatically. SSL certificates are optional for local network.

## Step 5: Test
```bash
# Get your Mac's IP
ifconfig | grep "inet " | grep -v 127.0.0.1

# Test from iOS Safari:
# https://YOUR_IP:58443/docs
```

## Auto-Start on Boot (Optional)
```bash
# Create launch agent (edit YOUR_USERNAME):
cp scripts/com.videoserver.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.videoserver.plist
```

✅ **Done! Server is running on port 58443**

Full guide: `.cursor/docs/PRODUCTION_DEPLOYMENT.md`
