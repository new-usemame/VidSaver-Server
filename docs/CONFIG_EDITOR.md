# Configuration Editor

## Overview

The Video Server includes a modern, web-based configuration editor that allows you to manage all server settings through an intuitive user interface instead of manually editing YAML files.

**✨ The config editor is integrated into the main server** - access it through the menu bar app or directly via browser when the server is running.

## Accessing the Config Editor

### Method 1: Menu Bar App (Recommended)
1. Double-click **"Start Video Server.command"**
2. Click the menu bar icon (📹)
3. Click **"▶️ Start Server"** (if not already running)
4. Select **"🎛️ Config Editor"**
5. The editor opens automatically in your browser

### Method 2: Direct Browser Access
Navigate to: `http://localhost:58443/api/v1/config/editor`

**Note:** The server must be running to access the config editor.

## Features

### 📋 Organized Tabs
Settings are organized into logical sections:
- **🖥️ Server** - Basic server settings, SSL/TLS, database configuration
- **📥 Downloads** - Download directory, concurrency, retry settings
- **⬇️ Downloader** - yt-dlp configuration, rate limiting, timeouts
- **🔒 Security** - API keys, rate limiting, whitelisted domains
- **📝 Logging** - Log level, file location, rotation settings

### 🎯 Key Features
- **Real-time Validation** - Settings are validated before saving
- **Help Tooltips** - Hover over field labels for guidance
- **API Key Generator** - Generate secure API keys with one click
- **Reset to Defaults** - Restore default configuration if needed
- **Auto-save** - Changes are saved immediately to `config/config.yaml`
- **Responsive Design** - Works on desktop, tablet, and mobile devices

### 🔐 Security Settings

#### API Keys
1. Navigate to the **Security** tab
2. Click **"🔑 Generate New API Key"**
3. The key is automatically copied to your clipboard
4. It's also added to the API Keys text area
5. Click **"💾 Save Configuration"** to persist the changes

#### Rate Limiting
Set the maximum number of requests per hour per client:
- Default: 100 requests/hour
- Range: 1-10,000

#### Allowed Domains
Whitelist domains for video downloads:
- Default: `tiktok.com`, `instagram.com`
- Add one domain per line
- Only URLs from these domains will be accepted

### 🌐 SSL/TLS Configuration

#### Option 1: Let's Encrypt (Recommended for Production)
1. Check **"Enable SSL/HTTPS"**
2. Enter your domain name (e.g., `video.yourdomain.com`)
3. Check **"Use Let's Encrypt"**
4. Enter your email address for renewal notifications
5. Save and restart the server

#### Option 2: Manual Certificates
1. Check **"Enable SSL/HTTPS"**
2. Uncheck **"Use Let's Encrypt"**
3. Enter paths to your certificate and key files
4. Save and restart the server

#### Option 3: HTTP Only (Local Network)
1. Uncheck **"Enable SSL/HTTPS"**
2. Save and restart the server
3. For iOS apps, add `NSAllowsLocalNetworking=true` to Info.plist

## Usage Tips

### ⚡ Quick Actions
- **Reload** - Discard changes and reload from file
- **Reset to Defaults** - Restore factory settings

### 🔄 After Making Changes
1. Click **"💾 Save Configuration"**
2. Wait for success confirmation
3. **Restart the server** for changes to take effect:
   - Tray App: Click **"🔄 Restart Server"**
   - Command Line: `python manage.py restart`

### 🎯 Common Tasks

#### Change Server Port
1. Go to **Server** tab
2. Update the **Port** field
3. Save and restart

#### Configure Download Location
1. Go to **Downloads** tab
2. Update **Root Directory**
3. Save (no restart needed for this change)

#### Add API Authentication
1. Go to **Security** tab
2. Generate new API keys
3. Save configuration
4. Restart server
5. Share keys with authorized clients

#### Adjust Log Level
1. Go to **Logging** tab
2. Select log level:
   - **DEBUG** - Development/troubleshooting
   - **INFO** - Normal production operation
   - **WARNING** - Only warnings and errors
   - **ERROR** - Only errors
3. Save and restart

## API Endpoints

The config editor also exposes API endpoints:

### Get Configuration
```bash
GET /api/v1/config
```

### Update Configuration
```bash
PUT /api/v1/config
Content-Type: application/json

{
  "server": {...},
  "downloads": {...},
  ...
}
```

### Reset to Defaults
```bash
POST /api/v1/config/reset
```

### Generate API Key
```bash
POST /api/v1/config/generate-key
```

## Troubleshooting

### Config Editor Won't Load
1. Ensure the server is running (check menu bar icon)
2. Try restarting the server from the menu bar app
3. Check if port 58443 is accessible: `curl http://localhost:58443/health`
4. Check server logs: View Logs from menu bar app

### Changes Not Taking Effect
1. Verify you clicked **"💾 Save Configuration"**
2. Check for error messages in the UI
3. **Restart the server** - most changes require a restart
4. Check logs for configuration errors

### Cannot Save Configuration
1. Check file permissions on `config/config.yaml`
2. Ensure the config directory exists
3. Check server logs for detailed error messages

### Reset to Defaults Not Working
1. Verify `config/config.yaml.example` exists
2. Check file permissions
3. Manually copy: `cp config/config.yaml.example config/config.yaml`

## Advanced: Manual Editing

If you prefer to edit the YAML file directly:
1. Stop the server
2. Edit `config/config.yaml` in your favorite text editor
3. Validate YAML syntax
4. Start the server

The menu bar app also provides a **"📝 Edit Config File"** option that opens the file in your default text editor.

## Security Notes

- The config editor is accessible to anyone who can reach your server
- If running on a public network, ensure SSL is enabled and use API key authentication
- Never share your API keys publicly
- Regularly rotate API keys for production deployments
- Use Let's Encrypt for automatic certificate management

## Need Help?

- Check the [README.md](../README.md) for general information
- See [SSL_SETUP.md](SSL_SETUP.md) for SSL/TLS configuration help
- Review server logs in `logs/server.log`
- API documentation: `http://localhost:58443/docs`
