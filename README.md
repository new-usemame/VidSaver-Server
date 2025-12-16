# Video Download Server

A lightweight, production-ready Python HTTPS server for downloading videos from TikTok, Instagram, YouTube, and more. Designed for seamless integration with iOS share extensions, featuring multi-user support, automatic genre detection, queue-based downloads, and zero data loss guarantees.

## 🎯 Features

- **Multi-User Support**: Organize downloads by user with automatic folder structure
- **Genre Detection**: Automatically categorizes content (TikTok, Instagram, YouTube, PDF, eBook, etc.)
- **Instant Response**: Accepts download requests and returns confirmation in < 500ms
- **Zero Data Loss**: All URLs persisted to database before client confirmation
- **Background Processing**: Queue-based downloads with configurable concurrency
- **Smart Retry Logic**: Automatic retries with exponential backoff (1min → 5min → 15min)
- **HTTPS Support**: Self-signed certificate generation with iOS compatibility
- **Multiple Platforms**: TikTok, Instagram, YouTube, PDFs, eBooks, and 1000+ sites via yt-dlp
- **REST API**: Clean, documented API endpoints with status tracking
- **Production Ready**: Designed to run as background service on Mac/Raspberry Pi
- **Low Resource Usage**: < 100MB RAM idle, < 500MB during downloads

## 📋 Requirements

- **Python**: 3.9 - 3.14 (recommended: 3.12 or 3.13)
- **Operating System**: Windows, macOS, Linux, or Raspberry Pi OS
- **Disk Space**: Variable (depends on downloaded videos)
- **Network**: Internet connection for downloads

## 🚀 Quick Start

### 1. Clone and Setup

```bash
# Clone the repository
git clone <repository-url>
cd "TikTok Downloader Server"

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Generate SSL Certificate

```bash
# RECOMMENDED: Use Let's Encrypt (requires a domain name pointing to your server)
# iOS recognizes Let's Encrypt certificates as legitimate - no manual trust steps needed!
sudo ./scripts/setup_letsencrypt.sh <your-domain> <your-email>
# Example: sudo ./scripts/setup_letsencrypt.sh video.example.com admin@example.com

# After Let's Encrypt setup, verify config.yaml has:
#   domain: "your-domain.com"
#   use_letsencrypt: true
#   letsencrypt_email: "your-email@example.com"

# ALTERNATIVE: Self-signed certificate (requires manual iOS trust setup)
./scripts/generate_selfsigned.sh
```

### 3. Configure Server

```bash
# Copy example configuration
cp config/config.yaml.example config/config.yaml

# Edit configuration
nano config/config.yaml
```

> **Tip:** You can edit the configuration later using the Config Editor (via web interface or tray app).

### 4. Initialize Database

```bash
# Run database initialization script (to be created in Stage 1)
python scripts/init_database.py
```

### 5. Run Server

```bash
# Using cross-platform CLI (recommended)
python manage.py start

# Or direct mode
python server.py

# Or with uvicorn directly
uvicorn app.main:app --host 0.0.0.0 --port 8443 --ssl-keyfile certs/server.key --ssl-certfile certs/server.crt
```

## 🖥️ Cross-Platform Management

The server includes cross-platform tools for management that work on **Windows, Linux, and macOS**:

### CLI Commands (`manage.py`)

```bash
# Server Control
python manage.py start          # Start server
python manage.py stop           # Stop server
python manage.py restart        # Restart server
python manage.py status         # Show detailed status with health check

# Monitoring
python manage.py logs           # View last 50 log lines
python manage.py logs -f        # Follow logs in real-time (tail -f)
python manage.py info           # Headless-friendly status output
python manage.py info --json    # JSON output for scripting
python manage.py console        # Interactive console with live updates

# Utilities
python manage.py tray           # Start system tray app separately
python manage.py docs           # Open API docs in browser
python manage.py config         # Show current configuration
```

### System Tray App (`tray_app.py`)

A cross-platform system tray application with:
- Server status indicator (green = running, gray = stopped)
- Start/Stop/Restart controls
- Quick access to API docs, Config Editor, QR Setup
- Log viewer access
- Works on Windows, Linux, and macOS

```bash
# Start tray app separately (after starting server)
python manage.py tray

# Or run directly
python tray_app.py
```

### Console Mode (Headless)

For servers without a display (headless mode), use the console command:

```bash
python manage.py console
```

This displays a live-updating dashboard with:
- Server status and uptime
- Access URLs (local and LAN)
- Download queue statistics
- Recent downloads
- Resource usage (memory, CPU)

Press `Ctrl+C` to exit console mode.

### Platform-Specific Notes

**Windows:**
- Use `python` instead of `python3`
- Virtual environment: `venv\Scripts\activate`
- System tray appears in notification area

**Linux:**
- Requires `libappindicator` for system tray (most distros include this)
- Install with: `sudo apt install libayatana-appindicator3-1` (Ubuntu/Debian)

**macOS:**
- Full support out of the box
- System tray appears in menu bar area

## 📁 Project Structure

```
video-download-server/
├── app/                    # Main application code
│   ├── api/               # API endpoints (v1)
│   ├── models/            # Data models (database, requests, responses)
│   ├── services/          # Business logic (database, downloads, queue)
│   ├── core/              # Core functionality (config, logging, security)
│   └── utils/             # Utility functions (validators, helpers)
├── certs/                 # SSL certificates
├── config/                # Configuration files
├── data/                  # SQLite database
├── logs/                  # Application logs (auto-rotated)
├── scripts/               # Installation and utility scripts
├── tests/                 # Test suite
├── requirements.txt       # Python dependencies
└── README.md             # This file
```

## 🔌 API Endpoints

### POST /api/v1/download
Submit a video URL for download.

**Request:**
```json
{
  "url": "https://www.tiktok.com/@user/video/1234567890",
  "client_id": "ios-device-uuid"
}
```

**Response (< 500ms):**
```json
{
  "download_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "queued",
  "message": "Download request accepted",
  "timestamp": "2025-11-07T10:30:00Z"
}
```

### GET /api/v1/status/{download_id}
Check download status.

**Response:**
```json
{
  "download_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "url": "https://www.tiktok.com/@user/video/1234567890",
  "filename": "tiktok_video_1234567890.mp4",
  "file_size": 15728640,
  "progress": 100,
  "created_at": "2025-11-07T10:30:00Z",
  "completed_at": "2025-11-07T10:31:23Z"
}
```

**Status Values:** `queued`, `downloading`, `completed`, `failed`

### GET /api/v1/history
Retrieve download history with pagination.

**Query Parameters:**
- `limit`: Number of results (default: 50, max: 200)
- `offset`: Pagination offset (default: 0)
- `client_id`: Filter by client (optional)

**Response:**
```json
{
  "downloads": [...],
  "total": 150,
  "limit": 50,
  "offset": 0
}
```

### GET /api/v1/health
Server health check.

**Response:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "uptime": 86400,
  "queue_size": 3
}
```

## ⚙️ Configuration

Configuration is managed via `config/config.yaml`:

```yaml
server:
  host: "0.0.0.0"
  port: 8443
  cert_file: "certs/server.crt"
  key_file: "certs/server.key"

database:
  path: "data/downloads.db"

downloads:
  output_directory: "~/Downloads/VideoServer"
  max_concurrent: 1
  max_retries: 3
  retry_delays: [60, 300, 900]  # seconds

downloader:
  rate_limit: null
  user_agent_rotation: true
  timeout: 300

security:
  api_keys: []
  rate_limit_per_client: 100  # requests per hour

logging:
  level: "INFO"
  file: "logs/server.log"
  max_size: "10MB"
  backup_count: 5
```

Environment variables override configuration file values (see `.env.example`).

## 🔒 Security

### API Authentication
Protect endpoints with API keys via `X-API-Key` header:

```bash
curl -H "X-API-Key: your-secret-key" https://localhost:8443/api/v1/download
```

Configure keys in `config.yaml` or via `VIDEO_SERVER_API_KEYS` environment variable.

### Rate Limiting
- Default: 100 requests per hour per `client_id`
- Configurable in `config.yaml`
- Returns HTTP 429 when limit exceeded

### HTTPS Certificate
Self-signed certificates work for local/private networks. For iOS:

1. Install certificate on device (Settings → General → VPN & Device Management)
2. Trust certificate (Settings → General → About → Certificate Trust Settings)

## 🧪 Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test suite
pytest tests/test_api/
pytest tests/test_services/
```

## 🚢 Deployment

### Run as Service (macOS)

```bash
# Install service
sudo cp scripts/service/com.videoserver.download.plist /Library/LaunchDaemons/
sudo launchctl load /Library/LaunchDaemons/com.videoserver.download.plist

# Start service
sudo launchctl start com.videoserver.download

# Check status
sudo launchctl list | grep videoserver
```

### Run as Service (Linux/Raspberry Pi)

```bash
# Install service
sudo cp scripts/service/video-server.service /etc/systemd/system/
sudo systemctl daemon-reload

# Enable and start
sudo systemctl enable video-server
sudo systemctl start video-server

# Check status
sudo systemctl status video-server
```

## 📊 Monitoring

### View Logs

```bash
# Using manage.py (cross-platform)
python manage.py logs           # Last 50 lines
python manage.py logs -n 100    # Last 100 lines
python manage.py logs -f        # Follow in real-time

# Traditional (Unix)
tail -f logs/server.log

# View specific log level
grep "ERROR" logs/server.log
```

### Health Check

```bash
# Using manage.py (recommended)
python manage.py status

# Using curl
curl https://localhost:8443/api/v1/health

# Monitor queue
watch -n 5 'curl -s https://localhost:8443/api/v1/health | jq .queue_size'

# Interactive console (cross-platform)
python manage.py console
```

### Database Backup

```bash
# Backup database
cp data/downloads.db data/backups/downloads_$(date +%Y%m%d).db

# Automated backup (add to crontab)
0 2 * * * cp /path/to/data/downloads.db /path/to/backups/downloads_$(date +\%Y\%m\%d).db
```

## 🐛 Troubleshooting

### Issue: PyO3 version error during pip install
**Error:** `the configured Python interpreter version (3.14) is newer than PyO3's maximum supported version (3.13)`

**Solution:** Use Python 3.12 or 3.13 instead of 3.14:
```bash
# macOS with Homebrew
brew install python@3.12
python3.12 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Issue: Server won't start
- Check Python version: `python --version` (requires 3.9-3.13)
- Verify port 8443 is available: `lsof -i :8443`
- Check certificate files exist: `ls -la certs/`

### Issue: Downloads failing
- Check yt-dlp version: `yt-dlp --version`
- Test URL manually: `yt-dlp --simulate <url>`
- Check disk space: `df -h`
- Review logs: `grep "ERROR" logs/server.log`

### Issue: iOS device can't connect
- Verify certificate is installed and trusted on device
- Check server is accessible: `ping <server-ip>`
- Verify firewall allows port 8443
- Test with curl from another device

## 🔄 Update & Maintenance

### Update Dependencies

```bash
# Activate virtual environment
source venv/bin/activate

# Update packages
pip install --upgrade -r requirements.txt

# Test after update
pytest
```

### Renew Certificate

```bash
# Generate new certificate
./scripts/generate_selfsigned.sh

# Restart server
sudo systemctl restart video-server  # Linux
# or
sudo launchctl stop com.videoserver.download && sudo launchctl start com.videoserver.download  # macOS
```

## 📖 Documentation

### User Guides
- **[iOS Integration Guide](docs/iOS_INTEGRATION.md)** - Complete guide for iOS app integration with Swift examples
- **[SSL Setup Guide](docs/SSL_SETUP.md)** - Certificate generation and iOS installation
- **[Config Editor Guide](docs/CONFIG_EDITOR.md)** - Interactive configuration management

### Development
- **Implementation Plan**: `.cursor/docs/Implementation.md`
- **Project Structure**: `.cursor/docs/project_structure.md`
- **Bug Tracking**: `.cursor/docs/Bug_tracking.md`
- **API Documentation**: Auto-generated at `https://localhost:8443/docs` (FastAPI)

## 🤝 Development

### Development Setup

1. Follow Quick Start instructions
2. Install development dependencies: `pip install -r requirements.txt`
3. Set up pre-commit hooks (optional): `pre-commit install`
4. Run tests before committing: `pytest`

### Code Style

- **Formatter**: Black (`black .`)
- **Linter**: Flake8 (`flake8 app/`)
- **Type Checker**: MyPy (`mypy app/`)

### Contributing

1. Check `.cursor/docs/Implementation.md` for current stage and tasks
2. Review `.cursor/docs/Bug_tracking.md` before fixing issues
3. Follow project structure defined in `.cursor/docs/project_structure.md`
4. Write tests for new features
5. Update documentation

## 📝 License

[Add your license here]

## 🙏 Acknowledgments

- **FastAPI**: Modern Python web framework
- **yt-dlp**: Powerful video downloader
- **uvicorn**: Lightning-fast ASGI server

## 📞 Support

For issues and questions:
1. Check troubleshooting section above
2. Review logs in `logs/server.log`
3. Check `.cursor/docs/Bug_tracking.md` for known issues
4. [Add your support contact/links]

---

**Version**: 1.0.0  
**Last Updated**: December 16, 2025  
**Platforms**: Windows, macOS, Linux  
**Status**: Production Ready with Cross-Platform Support

