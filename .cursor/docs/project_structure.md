# Project Structure: Video Download Server

## Overview

This document defines the complete file and folder structure for the Video Download Server project. The structure is designed to support a lightweight, maintainable Python server with clear separation of concerns.

## Root Directory Structure

```
video-download-server/
├── app/                          # Main application code
│   ├── __init__.py
│   ├── main.py                   # FastAPI application entry point
│   ├── api/                      # API endpoints and routes
│   │   ├── __init__.py
│   │   ├── v1/                   # API version 1
│   │   │   ├── __init__.py
│   │   │   ├── download.py       # POST /api/v1/download
│   │   │   ├── status.py         # GET /api/v1/status/{download_id}
│   │   │   ├── history.py        # GET /api/v1/history
│   │   │   └── health.py         # GET /api/v1/health
│   │   └── dependencies.py       # Shared dependencies (auth, rate limiting)
│   ├── models/                   # Data models and schemas
│   │   ├── __init__.py
│   │   ├── database.py           # Database models and schema
│   │   ├── requests.py           # Pydantic request models
│   │   └── responses.py          # Pydantic response models
│   ├── services/                 # Business logic services
│   │   ├── __init__.py
│   │   ├── database_service.py   # Database operations (CRUD)
│   │   ├── download_service.py   # yt-dlp wrapper and download logic
│   │   ├── queue_service.py      # Queue worker and processing
│   │   └── retry_service.py      # Retry logic with exponential backoff
│   ├── core/                     # Core functionality
│   │   ├── __init__.py
│   │   ├── config.py             # Configuration loader and validator
│   │   ├── logging.py            # Logging setup and helpers
│   │   ├── security.py           # Authentication and rate limiting
│   │   └── exceptions.py         # Custom exceptions
│   └── utils/                    # Utility functions
│       ├── __init__.py
│       ├── validators.py         # URL and input validation
│       ├── disk_utils.py         # Disk space checking
│       └── helpers.py            # General helper functions
├── certs/                        # SSL/TLS certificates
│   ├── server.crt                # Self-signed certificate (generated)
│   ├── server.key                # Private key (generated)
│   └── openssl.cnf               # OpenSSL configuration for certificate generation
├── config/                       # Configuration files
│   ├── config.yaml               # Main configuration file
│   └── config.yaml.example       # Example configuration (template)
├── data/                         # Data storage
│   └── downloads.db              # SQLite database (created at runtime)
├── logs/                         # Log files
│   ├── server.log                # Main server log (rotated)
│   ├── server.log.1              # Rotated log files
│   └── ...
├── scripts/                      # Deployment and utility scripts
│   ├── install.sh                # Installation script (Linux/macOS)
│   ├── generate_cert.sh          # Certificate generation script
│   ├── init_database.py          # Database initialization script
│   └── service/                  # Service configuration files
│       ├── video-server.service  # systemd service file (Linux/Pi)
│       └── com.videoserver.download.plist  # launchd plist (macOS)
├── tests/                        # Test files
│   ├── __init__.py
│   ├── conftest.py               # pytest configuration and fixtures
│   ├── test_api/                 # API endpoint tests
│   │   ├── __init__.py
│   │   ├── test_download.py
│   │   ├── test_status.py
│   │   ├── test_history.py
│   │   └── test_health.py
│   ├── test_services/            # Service layer tests
│   │   ├── __init__.py
│   │   ├── test_database_service.py
│   │   ├── test_download_service.py
│   │   └── test_queue_service.py
│   └── test_utils/               # Utility tests
│       ├── __init__.py
│       └── test_validators.py
├── .cursor/                      # Cursor IDE configuration
│   ├── docs/                     # Project documentation
│   │   ├── Implementation.md     # Implementation plan (this was generated)
│   │   ├── project_structure.md  # This file
│   │   └── Bug_tracking.md       # Bug tracking and resolution log
│   └── rules/                    # Cursor rules
│       ├── PRD.md                # Product Requirements Document
│       ├── Workflow.mdc          # Development workflow rules
│       └── Generate.mdc          # Implementation plan generator rules
├── .env.example                  # Example environment variables
├── .gitignore                    # Git ignore file
├── requirements.txt              # Python dependencies
├── README.md                     # Project README with setup instructions
└── server.py                     # Main entry point (simple wrapper for app/main.py)
```

## Detailed Structure Explanation

### `/app` - Main Application Code

The core application logic, organized into clear modules:

- **`main.py`**: FastAPI application initialization, middleware setup, HTTPS configuration, startup/shutdown handlers
- **`api/`**: All API endpoints organized by version and resource
  - **`v1/`**: Version 1 endpoints, each endpoint in its own file for maintainability
  - **`dependencies.py`**: Shared dependencies like authentication, rate limiting, database connections
- **`models/`**: Data models and schemas
  - **`database.py`**: Database schema definition, table creation, SQLite connection management
  - **`requests.py`**: Pydantic models for API request validation
  - **`responses.py`**: Pydantic models for API response serialization
- **`services/`**: Business logic layer, separated from API routes
  - **`database_service.py`**: CRUD operations, transaction management, query builders
  - **`download_service.py`**: yt-dlp wrapper, download execution, progress tracking
  - **`queue_service.py`**: Background worker, queue polling, concurrent download management
  - **`retry_service.py`**: Retry scheduling, exponential backoff, failure handling
- **`core/`**: Core system functionality
  - **`config.py`**: YAML config loading, Pydantic validation, environment variable overrides
  - **`logging.py`**: Logging configuration, structured logging helpers, rotation setup
  - **`security.py`**: API key validation, rate limiting implementation, input sanitization
  - **`exceptions.py`**: Custom exception classes for different error scenarios
- **`utils/`**: Utility functions
  - **`validators.py`**: URL validation, domain whitelisting, input validation regex
  - **`disk_utils.py`**: Disk space checking, path validation
  - **`helpers.py`**: General utility functions (UUID generation, timestamp handling, etc.)

### `/certs` - SSL/TLS Certificates

Contains HTTPS certificates for secure communication with iOS clients:

- **`server.crt`**: Self-signed SSL certificate (generated during installation)
- **`server.key`**: Private key for the certificate (keep secure, never commit to git)
- **`openssl.cnf`**: OpenSSL configuration file with SAN (Subject Alternative Names) for iOS compatibility

**Security Note:** The `server.key` file must be protected (chmod 600) and excluded from version control.

### `/config` - Configuration Files

Configuration management:

- **`config.yaml`**: Main configuration file (user-editable, not committed to git if contains secrets)
- **`config.yaml.example`**: Template configuration with default values and documentation

**Configuration Structure:**
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
  retry_delays: [60, 300, 900]

downloader:
  rate_limit: null
  user_agent_rotation: true
  timeout: 300

security:
  api_keys: []  # List of valid API keys
  rate_limit_per_client: 100  # requests per hour

logging:
  level: "INFO"
  file: "logs/server.log"
  max_size: "10MB"
  backup_count: 5
```

### `/data` - Data Storage

Runtime data storage:

- **`downloads.db`**: SQLite database file (created automatically on first run)
- Database backups can be stored here as well

**Note:** This directory should be backed up regularly. The `.gitignore` should exclude `*.db` files.

### `/logs` - Log Files

Application logs with rotation:

- **`server.log`**: Current log file
- **`server.log.1`, `server.log.2`, etc.**: Rotated log files (max 5 backups)

**Log Rotation:** Configured to rotate when file reaches 10MB, keeping 5 backup files.

### `/scripts` - Deployment and Utility Scripts

Scripts for installation, deployment, and maintenance:

- **`install.sh`**: Main installation script (detects OS, installs dependencies, generates certs, sets up service)
- **`generate_cert.sh`**: Certificate generation script (can be run independently)
- **`init_database.py`**: Database initialization (creates schema, indexes)
- **`service/`**: Service configuration templates
  - **`video-server.service`**: systemd service file for Linux/Raspberry Pi
  - **`com.videoserver.download.plist`**: launchd plist for macOS

### `/tests` - Test Suite

Comprehensive test coverage:

- **`conftest.py`**: pytest fixtures and configuration
- **`test_api/`**: Integration tests for API endpoints
- **`test_services/`**: Unit tests for service layer
- **`test_utils/`**: Unit tests for utility functions

**Testing Approach:**
- Unit tests for isolated components
- Integration tests for API endpoints
- Database tests use in-memory SQLite
- Mock external dependencies (yt-dlp, network calls)

### `/.cursor` - Cursor IDE Configuration

Project-specific Cursor IDE settings:

- **`docs/`**: Project documentation
  - **`Implementation.md`**: Generated implementation plan
  - **`project_structure.md`**: This file
  - **`Bug_tracking.md`**: Bug log and resolution tracking
- **`rules/`**: Cursor AI rules
  - **`PRD.md`**: Product Requirements Document
  - **`Workflow.mdc`**: Development workflow rules
  - **`Generate.mdc`**: Implementation plan generator rules

## File Naming Conventions

### Python Files:
- **Modules**: `lowercase_with_underscores.py` (snake_case)
- **Classes**: `CapitalizedWords` (PascalCase)
- **Functions/Variables**: `lowercase_with_underscores` (snake_case)
- **Constants**: `UPPERCASE_WITH_UNDERSCORES`

### Configuration Files:
- **YAML**: `config.yaml`, `openssl.cnf`
- **Examples**: `*.example` suffix (e.g., `config.yaml.example`)

### Scripts:
- **Shell scripts**: `lowercase_with_underscores.sh`
- **Python scripts**: `lowercase_with_underscores.py`

### Service Files:
- **systemd**: `kebab-case.service`
- **launchd**: `reverse-domain.plist` (e.g., `com.videoserver.download.plist`)

## Environment Variables

Optional environment variable overrides (defined in `.env` or system environment):

```bash
# Server Configuration
VIDEO_SERVER_HOST=0.0.0.0
VIDEO_SERVER_PORT=8443

# Security
VIDEO_SERVER_API_KEYS=key1,key2,key3

# Database
VIDEO_SERVER_DB_PATH=data/downloads.db

# Logging
VIDEO_SERVER_LOG_LEVEL=INFO

# Downloads
VIDEO_SERVER_OUTPUT_DIR=~/Downloads/VideoServer
VIDEO_SERVER_MAX_CONCURRENT=1
```

**Priority:** Environment variables > config.yaml > defaults

## Dependencies Management

### `requirements.txt` Structure:

```
# Web Framework
fastapi==0.104.1
uvicorn[standard]==0.24.0
pydantic==2.5.0
pydantic-settings==2.1.0

# Video Downloader
yt-dlp==2023.11.16

# Configuration
PyYAML==6.0.1

# HTTP Client (for any external API calls)
httpx==0.25.1

# Testing
pytest==7.4.3
pytest-asyncio==0.21.1
pytest-cov==4.1.0

# Code Quality (optional)
black==23.11.0
flake8==6.1.0
mypy==1.7.1
```

## .gitignore Recommended Entries

```
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
ENV/
*.egg-info/

# Data
data/*.db
data/*.db-journal
data/backups/

# Logs
logs/*.log
logs/*.log.*

# Certificates (never commit private keys)
certs/*.key
certs/*.crt

# Configuration (if contains secrets)
config/config.yaml
.env

# Downloads
Downloads/

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Testing
.pytest_cache/
.coverage
htmlcov/
```

## Deployment Structure

### Development Environment:
```
/Users/developer/Projects/video-download-server/
├── app/
├── config/config.yaml  (development settings)
├── certs/  (self-signed cert)
└── logs/
```

### Production Environment (macOS):
```
/usr/local/video-download-server/
├── app/
├── config/config.yaml  (production settings)
├── certs/  (production cert)
├── logs/  (with log rotation)
├── data/downloads.db
└── server.py
```

### Production Environment (Raspberry Pi):
```
/home/pi/video-download-server/
├── app/
├── config/config.yaml
├── certs/
├── logs/
├── data/downloads.db
└── server.py
```

## Running the Server

### Development Mode:
```bash
cd /path/to/video-download-server
source venv/bin/activate
python server.py
# or
uvicorn app.main:app --reload --host 0.0.0.0 --port 8443 --ssl-keyfile certs/server.key --ssl-certfile certs/server.crt
```

### Production Mode (as Service):
```bash
# macOS
sudo launchctl load /Library/LaunchDaemons/com.videoserver.download.plist
sudo launchctl start com.videoserver.download

# Linux/Raspberry Pi
sudo systemctl enable video-server
sudo systemctl start video-server
sudo systemctl status video-server
```

## Configuration Best Practices

1. **Separation of Concerns**: Each module has a single, well-defined responsibility
2. **Dependency Direction**: Dependencies flow inward (API → Services → Database)
3. **Configuration Externalization**: All environment-specific settings in config.yaml
4. **Logging**: Centralized logging configuration in `core/logging.py`
5. **Testing**: Tests mirror the structure of `app/` directory
6. **Documentation**: Keep documentation in `.cursor/docs/` for easy reference
7. **Security**: Never commit secrets, certificates, or database files

## Module Import Patterns

```python
# API endpoint imports
from app.services.database_service import DatabaseService
from app.models.requests import DownloadRequest
from app.models.responses import DownloadResponse
from app.core.config import get_config
from app.core.logging import get_logger

# Service imports
from app.core.config import Config
from app.models.database import Download
from app.utils.validators import validate_url

# Utilities imports
from app.core.exceptions import ValidationError
```

## Data Flow

```
Client (iOS) → API Endpoint → Service Layer → Database
                ↓
              Logging
                ↓
              Queue Worker → yt-dlp → Local Storage
```

## Notes

- This structure supports **single deployment** with no dev/prod split
- All paths are **relative to project root** for portability
- **Database and logs** are in separate directories for easy backup
- **Configuration** is externalized for different environments
- **Scripts** folder contains all deployment automation
- **Tests** mirror the application structure for easy navigation

## Maintenance

- **Logs**: Rotate automatically (10MB, 5 backups)
- **Database**: Backup `data/downloads.db` regularly
- **Certificates**: Renew self-signed certificates annually
- **Dependencies**: Update `requirements.txt` and test before deploying

---

**Last Updated:** November 7, 2025  
**Project Version:** 1.0.0 (Initial Structure)

