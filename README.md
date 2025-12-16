# Video Download Server

A lightweight Python server for downloading videos from TikTok, Instagram, YouTube, and 1000+ sites. Perfect for iOS Shortcuts integration with QR code setup, queue-based downloads, and zero data loss.

## ✨ Features

| Feature | Description |
|---------|-------------|
| **1000+ Sites** | TikTok, Instagram, YouTube, PDFs, and more via yt-dlp |
| **iOS Ready** | QR code setup for easy iOS Shortcut configuration |
| **Web Interface** | Config editor, API docs, and status dashboard at root URL |
| **Queue System** | Background downloads with retry logic (1min → 5min → 15min) |
| **Cross-Platform** | CLI + system tray app for Windows, macOS, and Linux |
| **Multi-User** | Organize downloads by user with auto folder structure |
| **Zero Data Loss** | URLs persisted to database before confirmation |

## 🚀 Quick Start (3 Steps)

```bash
# 1. Clone and install
git clone <repository-url>
cd TikTok-Downloader-Server
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 2. Copy config (uses sensible defaults)
cp config/config.yaml.example config/config.yaml

# 3. Start server
python manage.py start
```

That's it! The database initializes automatically. Open the URL shown to access the web interface.

## 📱 iOS Setup

1. Start the server: `python manage.py start`
2. On your iOS device, visit the **QR Setup URL** shown in the terminal
3. Scan the QR code to auto-configure your iOS Shortcut

> **Note:** For local network (LAN), the server uses HTTP which works with iOS when you add `NSAllowsLocalNetworking=true` to your app's Info.plist. No SSL certificate needed!

## 🖥️ Management

### Dashboard (Default)

Run `python manage.py` with no arguments to see:
- Server status (🟢 running / 🔴 stopped)
- Access URLs for localhost and LAN
- Quick command reference

### Commands

```bash
python manage.py              # Show dashboard
python manage.py start        # Start server
python manage.py stop         # Stop server
python manage.py restart      # Restart server
python manage.py status       # Detailed status + health check

python manage.py tray         # Start system tray app
python manage.py logs -f      # Follow logs (tail -f)
python manage.py console      # Live dashboard (headless mode)

python manage.py docs         # Open API docs in browser
python manage.py editor       # Open config editor in browser
python manage.py qr           # Open QR setup page in browser
```

### System Tray App

Start with `python manage.py tray` for a desktop icon with:
- Status indicator (green/gray)
- Start/Stop/Restart controls
- Quick access to docs, config, QR setup

## 🌐 Web Interface

When the server is running, visit the root URL to access:

| Page | URL | Description |
|------|-----|-------------|
| **Hub** | `/` | Quick links and server status |
| **API Docs** | `/docs` | Interactive API documentation |
| **Config Editor** | `/api/v1/config/editor` | Edit settings in browser |
| **QR Setup** | `/api/v1/config/setup` | iOS Shortcut configuration |
| **Health** | `/api/v1/health` | Server health check |

## 🔌 API Reference

### POST /api/v1/download
Submit a URL for download.

```bash
curl -X POST http://localhost:58443/api/v1/download \
  -H "Content-Type: application/json" \
  -d '{"url": "https://tiktok.com/@user/video/123", "client_id": "my-device"}'
```

**Response:**
```json
{
  "download_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "queued",
  "message": "Download request accepted"
}
```

### GET /api/v1/status/{download_id}
Check download progress. Status: `queued` → `downloading` → `completed` or `failed`

### GET /api/v1/history
List downloads with pagination (`?limit=50&offset=0`)

### GET /api/v1/health
Server health and queue statistics

## ⚙️ Configuration

Edit `config/config.yaml` or use the web-based Config Editor.

### Key Settings

```yaml
server:
  access_level: "local"     # "localhost", "local" (LAN), or "public"
  port: 58443
  ssl:
    enabled: false          # HTTP works fine for local network

downloads:
  root_directory: "~/Downloads/VidSaver"
  max_concurrent: 1
  max_retries: 3

security:
  api_keys: []              # Add keys for authentication
  rate_limit_per_client: 100
```

### SSL (Optional)

SSL is **not required** for local network use. Enable only if you need HTTPS:

```yaml
server:
  ssl:
    enabled: true
    domain: "video.yourdomain.com"  # Required for Let's Encrypt
    use_letsencrypt: true
    letsencrypt_email: "you@example.com"
```

When SSL is enabled, the server runs in **dual-port mode**:
- HTTPS on main port (58443) for localhost
- HTTP on port-1 (58442) for LAN devices (SSL certs don't work with IP addresses)

## 📁 Project Structure

```
TikTok-Downloader-Server/
├── manage.py          # CLI management tool
├── tray_app.py        # System tray application
├── server.py          # Server entry point
├── app/               # Main application
│   ├── api/v1/        # API endpoints
│   ├── services/      # Business logic
│   └── core/          # Config, logging
├── config/            # Configuration files
├── data/              # SQLite database (auto-created)
└── logs/              # Server logs (auto-rotated)
```

## 🐛 Troubleshooting

| Issue | Solution |
|-------|----------|
| Port in use | `python manage.py status` shows what's using it |
| Server won't start | Check logs: `python manage.py logs` |
| Downloads failing | Test URL: `yt-dlp --simulate <url>` |
| iOS can't connect | Ensure device is on same network, check firewall |

### Python Version

Requires Python 3.9-3.13. If you get PyO3 errors:

```bash
# macOS
brew install python@3.12
python3.12 -m venv venv

# Then reinstall
source venv/bin/activate
pip install -r requirements.txt
```

## 🧪 Testing

```bash
pytest                      # Run all tests
pytest --cov=app           # With coverage
```

## 📖 More Documentation

- [iOS Integration Guide](docs/iOS_INTEGRATION.md) - Swift examples and Shortcuts setup
- [SSL Setup Guide](docs/SSL_SETUP.md) - Certificate configuration
- [Config Editor Guide](docs/CONFIG_EDITOR.md) - Web-based configuration

---

**Platforms:** Windows, macOS, Linux  
**Python:** 3.9 - 3.13  
**License:** [Your license]
