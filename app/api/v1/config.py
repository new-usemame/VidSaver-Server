"""
Configuration management API endpoints
"""

import logging
import io
import json
import base64
from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse, Response, StreamingResponse
from pathlib import Path
from typing import Any, Dict
import yaml
import secrets
import qrcode
import qrcode.image.svg

from app.services.network_service import get_network_service
from app.core.config import get_config

logger = logging.getLogger(__name__)

router = APIRouter()

# Path to config file
PROJECT_DIR = Path(__file__).parent.parent.parent.parent
CONFIG_PATH = PROJECT_DIR / "config" / "config.yaml"
CONFIG_EXAMPLE_PATH = PROJECT_DIR / "config" / "config.yaml.example"


@router.get("/setup", response_class=HTMLResponse)
async def get_setup_page():
    """Serve the server setup page with QR code"""
    html_content = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Video Server - Setup</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        
        .container {
            max-width: 800px;
            width: 100%;
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
        }
        
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px;
            text-align: center;
        }
        
        .header h1 {
            font-size: 36px;
            margin-bottom: 10px;
        }
        
        .header p {
            opacity: 0.9;
            font-size: 18px;
        }
        
        .content {
            padding: 40px;
        }
        
        .qr-section {
            text-align: center;
            margin-bottom: 40px;
        }
        
        .qr-code {
            background: white;
            padding: 20px;
            border-radius: 16px;
            display: inline-block;
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
            margin: 20px 0;
        }
        
        .qr-code img {
            display: block;
            max-width: 100%;
            height: auto;
        }
        
        .instruction {
            font-size: 18px;
            color: #2c3e50;
            margin-bottom: 30px;
            line-height: 1.6;
        }
        
        .connection-info {
            background: #f8f9fa;
            border-radius: 12px;
            padding: 25px;
            margin-bottom: 30px;
        }
        
        .connection-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 15px 0;
            border-bottom: 1px solid #dee2e6;
        }
        
        .connection-item:last-child {
            border-bottom: none;
        }
        
        .connection-label {
            font-weight: 600;
            color: #495057;
            font-size: 14px;
        }
        
        .connection-value {
            font-family: 'Courier New', monospace;
            color: #667eea;
            font-weight: 500;
            font-size: 14px;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        .copy-btn {
            background: #667eea;
            color: white;
            border: none;
            padding: 6px 12px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 12px;
            transition: all 0.3s;
        }
        
        .copy-btn:hover {
            background: #5568d3;
            transform: translateY(-1px);
        }
        
        .status-badge {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: 600;
        }
        
        .status-online {
            background: #d4edda;
            color: #155724;
        }
        
        .status-offline {
            background: #f8d7da;
            color: #721c24;
        }
        
        .instructions-section {
            background: #fff3cd;
            border-left: 4px solid #ffc107;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 30px;
        }
        
        .instructions-section h3 {
            color: #856404;
            margin-bottom: 15px;
            font-size: 18px;
        }
        
        .instructions-section ol {
            margin-left: 20px;
            color: #856404;
        }
        
        .instructions-section li {
            margin-bottom: 10px;
            line-height: 1.6;
        }
        
        .footer {
            text-align: center;
            padding: 20px;
            background: #f8f9fa;
            color: #6c757d;
            font-size: 14px;
        }
        
        .loading {
            text-align: center;
            padding: 40px;
            color: #6c757d;
        }
        
        .spinner {
            border: 4px solid #f3f3f3;
            border-top: 4px solid #667eea;
            border-radius: 50%;
            width: 40px;
            height: 40px;
            animation: spin 1s linear infinite;
            margin: 0 auto;
        }
        
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        
        .btn-group {
            display: flex;
            gap: 10px;
            justify-content: center;
            margin-top: 30px;
        }
        
        .btn {
            padding: 12px 30px;
            border: none;
            border-radius: 8px;
            font-size: 15px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s;
        }
        
        .btn-primary {
            background: #667eea;
            color: white;
        }
        
        .btn-primary:hover {
            background: #5568d3;
            transform: translateY(-2px);
        }
        
        .btn-secondary {
            background: #6c757d;
            color: white;
        }
        
        .btn-secondary:hover {
            background: #5a6268;
            transform: translateY(-2px);
        }
        
        @media (max-width: 768px) {
            .header h1 {
                font-size: 28px;
            }
            
            .content {
                padding: 20px;
            }
            
            .connection-item {
                flex-direction: column;
                align-items: flex-start;
                gap: 10px;
            }
            
            .btn-group {
                flex-direction: column;
            }
            
            .btn {
                width: 100%;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📱 Video Server Setup</h1>
            <p>Scan the QR code with your iOS app</p>
        </div>
        
        <div class="content">
            <div id="loading" class="loading">
                <div class="spinner"></div>
                <p style="margin-top: 15px;">Loading server information...</p>
            </div>
            
            <div id="main-content" style="display: none;">
                <div class="qr-section">
                    <h2 style="color: #2c3e50; margin-bottom: 15px;">Setup QR Code</h2>
                    <p class="instruction">
                        Open your iOS app and tap "Scan Server" to automatically configure the connection
                    </p>
                    <p class="instruction" id="ssl-connection-note" style="display: none; font-size: 13px; color: #667eea; margin-top: 8px;">
                        🔒 <strong>SSL Enabled:</strong> Your iOS app will connect via the domain name for secure HTTPS
                    </p>
                    <div class="qr-code">
                        <img id="qr-image" src="/api/v1/config/qr.png" alt="Setup QR Code" style="width: 300px; height: 300px; image-rendering: crisp-edges;">
                    </div>
                </div>
                
                <div class="connection-info">
                    <h3 style="color: #2c3e50; margin-bottom: 20px;">Connection Details</h3>
                    
                    <div class="connection-item" id="domain-item" style="display: none;">
                        <span class="connection-label">🌐 Domain (SSL)</span>
                        <div class="connection-value">
                            <span id="domain-url" style="font-weight: bold; color: #27ae60;">-</span>
                            <button class="copy-btn" onclick="copy('domain-url')">Copy</button>
                        </div>
                    </div>
                    
                    <div class="connection-item">
                        <span class="connection-label">Local Network (LAN)</span>
                        <div class="connection-value">
                            <span id="lan-url">-</span>
                            <button class="copy-btn" onclick="copy('lan-url')">Copy</button>
                        </div>
                    </div>
                    
                    <div class="connection-item">
                        <span class="connection-label">Internet Access (WAN)</span>
                        <div class="connection-value">
                            <span id="wan-url">-</span>
                            <span id="wan-status" class="status-badge">-</span>
                            <button class="copy-btn" onclick="copy('wan-url')">Copy</button>
                        </div>
                    </div>
                    
                    <div class="connection-item">
                        <span class="connection-label">Port</span>
                        <div class="connection-value">
                            <span id="port">-</span>
                        </div>
                    </div>
                    
                    <div class="connection-item">
                        <span class="connection-label">Protocol</span>
                        <div class="connection-value">
                            <span id="protocol">-</span>
                        </div>
                    </div>
                    
                    <div class="connection-item" id="api-key-item" style="display: none;">
                        <span class="connection-label">API Key</span>
                        <div class="connection-value">
                            <span id="api-key" style="font-size: 12px;">-</span>
                            <button class="copy-btn" onclick="copy('api-key')">Copy</button>
                        </div>
                    </div>
                </div>
                
                <div class="instructions-section">
                    <h3>📋 Port Forwarding Instructions</h3>
                    <ol>
                        <li>Log in to your router's admin panel (usually 192.168.1.1)</li>
                        <li>Find "Port Forwarding" or "Virtual Server" settings</li>
                        <li>Forward port <strong id="port-forward">58443</strong> to <strong id="lan-ip">192.168.1.X</strong></li>
                        <li>Save settings and restart your router if needed</li>
                        <li>Your server will then be accessible from anywhere via the WAN URL</li>
                    </ol>
                </div>
                
                <div class="btn-group">
                    <button class="btn btn-primary" onclick="downloadQR()">💾 Download QR Code</button>
                    <button class="btn btn-secondary" onclick="refresh()">🔄 Refresh</button>
                </div>
            </div>
        </div>
        
        <div class="footer">
            <p>Video Download Server v2.0 • Multi-user support with genre organization</p>
        </div>
    </div>
    
    <script>
        let connectionData = {};
        
        async function loadConnectionInfo() {
            try {
                const response = await fetch('/api/v1/config/connection');
                if (!response.ok) throw new Error('Failed to load connection info');
                
                connectionData = await response.json();
                populateConnectionInfo(connectionData);
                
                document.getElementById('loading').style.display = 'none';
                document.getElementById('main-content').style.display = 'block';
            } catch (error) {
                document.getElementById('loading').innerHTML = `
                    <p style="color: #e74c3c;">❌ Error: ${error.message}</p>
                    <button class="btn btn-primary" onclick="loadConnectionInfo()" style="margin-top: 20px;">Try Again</button>
                `;
            }
        }
        
        function populateConnectionInfo(data) {
            // Domain (for Let's Encrypt SSL)
            if (data.domain && data.ssl_enabled) {
                const domainUrl = `${data.protocol}://${data.domain}:${data.port}`;
                document.getElementById('domain-item').style.display = 'flex';
                document.getElementById('domain-url').textContent = domainUrl;
                // Show SSL connection note
                const sslNote = document.getElementById('ssl-connection-note');
                if (sslNote) sslNote.style.display = 'block';
            } else {
                document.getElementById('domain-item').style.display = 'none';
                const sslNote = document.getElementById('ssl-connection-note');
                if (sslNote) sslNote.style.display = 'none';
            }
            
            // LAN
            document.getElementById('lan-url').textContent = data.lan.url;
            document.getElementById('lan-ip').textContent = data.lan.ip;
            
            // WAN
            if (data.wan.url) {
                document.getElementById('wan-url').textContent = data.wan.url;
                document.getElementById('wan-status').textContent = '✓ Available';
                document.getElementById('wan-status').className = 'status-badge status-online';
            } else {
                document.getElementById('wan-url').textContent = 'Not available';
                document.getElementById('wan-status').textContent = '✗ Unavailable';
                document.getElementById('wan-status').className = 'status-badge status-offline';
            }
            
            // Port
            document.getElementById('port').textContent = data.port;
            document.getElementById('port-forward').textContent = data.port;
            
            // Protocol
            const protocol = data.protocol.toUpperCase();
            document.getElementById('protocol').textContent = protocol + (data.ssl_enabled ? ' (SSL)' : '');
            
            // API Key
            if (data.api_key) {
                document.getElementById('api-key-item').style.display = 'flex';
                document.getElementById('api-key').textContent = data.api_key;
            }
            
            // Refresh QR code image to ensure it's current (cache bust)
            const qrImage = document.getElementById('qr-image');
            const timestamp = new Date().getTime();
            qrImage.src = `/api/v1/config/qr.png?t=${timestamp}`;
        }
        
        function copy(elementId) {
            const element = document.getElementById(elementId);
            const text = element.textContent;
            
            navigator.clipboard.writeText(text).then(() => {
                // Show feedback
                const btn = event.target;
                const originalText = btn.textContent;
                btn.textContent = '✓ Copied!';
                setTimeout(() => {
                    btn.textContent = originalText;
                }, 2000);
            }).catch(err => {
                alert('Failed to copy: ' + err);
            });
        }
        
        function downloadQR() {
            const link = document.createElement('a');
            link.href = '/api/v1/config/qr.png?size=10';
            link.download = 'video-server-setup.png';
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
        }
        
        function refresh() {
            document.getElementById('loading').style.display = 'block';
            document.getElementById('main-content').style.display = 'none';
            
            // Refresh QR code with cache buster
            const qrImage = document.getElementById('qr-image');
            qrImage.src = '/api/v1/config/qr.png?t=' + new Date().getTime();
            
            loadConnectionInfo();
        }
        
        // Load on page load
        window.addEventListener('DOMContentLoaded', loadConnectionInfo);
    </script>
</body>
</html>
    """
    return HTMLResponse(content=html_content)


@router.get("/editor", response_class=HTMLResponse)
async def get_config_editor():
    """Serve the config editor HTML page"""
    html_content = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Video Server - Configuration Editor</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 16px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
        }
        
        .header {
            background: linear-gradient(135deg, #2c3e50 0%, #34495e 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }
        
        .header h1 {
            font-size: 32px;
            margin-bottom: 10px;
        }
        
        .header p {
            opacity: 0.9;
            font-size: 16px;
        }
        
        .tabs {
            display: flex;
            background: #f8f9fa;
            border-bottom: 2px solid #dee2e6;
            overflow-x: auto;
        }
        
        .tab {
            padding: 15px 25px;
            background: transparent;
            border: none;
            cursor: pointer;
            font-size: 15px;
            font-weight: 500;
            color: #6c757d;
            transition: all 0.3s;
            white-space: nowrap;
        }
        
        .tab:hover {
            background: rgba(0,0,0,0.05);
        }
        
        .tab.active {
            color: #667eea;
            border-bottom: 3px solid #667eea;
        }
        
        .content {
            padding: 30px;
            max-height: 600px;
            overflow-y: auto;
        }
        
        .tab-content {
            display: none;
        }
        
        .tab-content.active {
            display: block;
        }
        
        .section {
            margin-bottom: 30px;
        }
        
        .section-header {
            font-size: 20px;
            font-weight: 600;
            color: #2c3e50;
            margin-bottom: 15px;
            padding-bottom: 10px;
            border-bottom: 2px solid #e9ecef;
        }
        
        .form-group {
            margin-bottom: 20px;
        }
        
        .form-group label {
            display: block;
            font-weight: 600;
            color: #495057;
            margin-bottom: 8px;
            font-size: 14px;
        }
        
        .form-group .help-text {
            display: block;
            font-size: 12px;
            color: #6c757d;
            margin-top: 4px;
        }
        
        .form-control {
            width: 100%;
            padding: 12px;
            border: 2px solid #dee2e6;
            border-radius: 8px;
            font-size: 14px;
            transition: border-color 0.3s;
        }
        
        .form-control:focus {
            outline: none;
            border-color: #667eea;
        }
        
        .form-control:disabled {
            background-color: #f8f9fa;
            color: #adb5bd;
            cursor: not-allowed;
            opacity: 0.6;
        }
        
        .label-with-info {
            display: flex;
            align-items: center;
            gap: 8px;
        }
        
        .info-icon {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 18px;
            height: 18px;
            background: #667eea;
            color: white;
            border-radius: 50%;
            font-size: 12px;
            font-weight: bold;
            cursor: help;
            position: relative;
        }
        
        .info-icon:hover .tooltip {
            display: block;
        }
        
        .tooltip {
            display: none;
            position: absolute;
            left: 25px;
            top: 50%;
            transform: translateY(-50%);
            background: #2c3e50;
            color: white;
            padding: 12px 15px;
            border-radius: 8px;
            font-size: 13px;
            line-height: 1.5;
            width: 300px;
            z-index: 1000;
            box-shadow: 0 4px 12px rgba(0,0,0,0.3);
            font-weight: normal;
        }
        
        .tooltip::before {
            content: '';
            position: absolute;
            left: -8px;
            top: 50%;
            transform: translateY(-50%);
            border-right: 8px solid #2c3e50;
            border-top: 8px solid transparent;
            border-bottom: 8px solid transparent;
        }
        
        textarea.form-control {
            resize: vertical;
            min-height: 100px;
            font-family: 'Courier New', monospace;
        }
        
        .checkbox-wrapper {
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        .checkbox-wrapper input[type="checkbox"] {
            width: 20px;
            height: 20px;
            cursor: pointer;
        }
        
        .footer {
            padding: 20px 30px;
            background: #f8f9fa;
            border-top: 2px solid #dee2e6;
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 10px;
            flex-wrap: wrap;
        }
        
        .btn {
            padding: 12px 30px;
            border: none;
            border-radius: 8px;
            font-size: 15px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s;
            display: inline-flex;
            align-items: center;
            gap: 8px;
        }
        
        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        }
        
        .btn-primary {
            background: #27ae60;
            color: white;
        }
        
        .btn-secondary {
            background: #3498db;
            color: white;
        }
        
        .btn-danger {
            background: #e74c3c;
            color: white;
        }
        
        .btn-info {
            background: #9b59b6;
            color: white;
        }
        
        .alert {
            padding: 15px 20px;
            border-radius: 8px;
            margin-bottom: 20px;
            font-size: 14px;
        }
        
        .alert-success {
            background: #d4edda;
            color: #155724;
            border: 1px solid #c3e6cb;
        }
        
        .alert-error {
            background: #f8d7da;
            color: #721c24;
            border: 1px solid #f5c6cb;
        }
        
        .alert-info {
            background: #d1ecf1;
            color: #0c5460;
            border: 1px solid #bee5eb;
        }
        
        .loading {
            text-align: center;
            padding: 40px;
            color: #6c757d;
        }
        
        .spinner {
            border: 4px solid #f3f3f3;
            border-top: 4px solid #667eea;
            border-radius: 50%;
            width: 40px;
            height: 40px;
            animation: spin 1s linear infinite;
            margin: 0 auto;
        }
        
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        
        .two-columns {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
        }
        
        @media (max-width: 768px) {
            .two-columns {
                grid-template-columns: 1fr;
            }
            
            .footer {
                flex-direction: column;
            }
            
            .btn {
                width: 100%;
                justify-content: center;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📹 Video Server Configuration</h1>
            <p>Edit your server configuration with ease</p>
        </div>
        
        <div class="tabs">
            <button class="tab active" onclick="showTab('server', event)">🖥️ Server</button>
            <button class="tab" onclick="showTab('downloads', event)">📥 Downloads</button>
            <button class="tab" onclick="showTab('downloader', event)">⬇️ Downloader</button>
            <button class="tab" onclick="showTab('security', event)">🔒 Security</button>
            <button class="tab" onclick="showTab('logging', event)">📝 Logging</button>
        </div>
        
        <div class="content">
            <div id="alert-container"></div>
            <div id="loading" class="loading">
                <div class="spinner"></div>
                <p style="margin-top: 15px;">Loading configuration...</p>
            </div>
            
            <!-- Server Tab -->
            <div id="tab-server" class="tab-content active">
                <div class="section">
                    <div class="section-header">Basic Server Settings</div>
                    <div class="two-columns">
                        <div class="form-group">
                            <div class="label-with-info">
                                <label>Network Access</label>
                                <span class="info-icon">i
                                    <span class="tooltip"><strong>Localhost:</strong> Only accessible from this computer. Use for testing.<br><br><strong>Local Network:</strong> Accessible from devices on your WiFi/LAN. Best for home/office use.<br><br><strong>Public:</strong> Accessible from anywhere via internet. Requires router port forwarding and SSL strongly recommended.</span>
                                </span>
                            </div>
                            <select class="form-control" id="server-access-level">
                                <option value="localhost">Localhost - This device only</option>
                                <option value="local">Local Network - LAN access (recommended)</option>
                                <option value="public">Public - LAN + Internet (requires port forwarding)</option>
                            </select>
                            <span class="help-text">Control who can connect to your server</span>
                        </div>
                        <div class="form-group">
                            <div class="label-with-info">
                                <label>Port</label>
                                <span class="info-icon">i
                                    <span class="tooltip">The port number where the server listens for connections. Default is 58443. Use ports 1024-65535 (ports below 1024 require root/admin). If changing, update port forwarding in your router and iOS app configuration.</span>
                                </span>
                            </div>
                            <input type="number" class="form-control" id="server-port" placeholder="58443">
                            <span class="help-text">Port number (1024-65535)</span>
                        </div>
                    </div>
                </div>
                
                <div class="section">
                    <div class="section-header">SSL/TLS Configuration</div>
                    
                    <div class="alert alert-info" style="margin-bottom: 20px;">
                        <strong>📱 iOS Compatibility:</strong> Let's Encrypt certificates are trusted automatically on iOS—no manual setup required. Self-signed certificates require manual installation on each device.
                    </div>
                    
                    <div class="form-group">
                        <div class="checkbox-wrapper">
                            <input type="checkbox" id="ssl-enabled" onchange="updateSSLFieldStates()">
                            <div class="label-with-info">
                                <label>Enable SSL/HTTPS</label>
                                <span class="info-icon">i
                                    <span class="tooltip">SSL/HTTPS encrypts all communication between your iOS app and the server. Required for production use and strongly recommended for security. Once enabled, you must configure either Let's Encrypt (recommended) or provide your own certificate files.</span>
                                </span>
                            </div>
                        </div>
                        <span class="help-text">Secure communication with encryption</span>
                    </div>
                    
                    <div id="ssl-config-section" style="opacity: 0.5; pointer-events: none; transition: opacity 0.3s;">
                        <!-- Let's Encrypt Section (Recommended) -->
                        <div class="form-group" style="background: #e8f5e9; padding: 20px; border-radius: 8px; border-left: 4px solid #4caf50; margin-bottom: 20px;">
                            <div class="checkbox-wrapper" style="margin-bottom: 15px;">
                                <input type="checkbox" id="ssl-letsencrypt" onchange="updateSSLFieldStates()">
                                <div class="label-with-info">
                                    <label style="font-size: 16px; color: #2e7d32;">✅ Use Let's Encrypt (Recommended)</label>
                                    <span class="info-icon" style="background: #4caf50;">i
                                        <span class="tooltip">Let's Encrypt provides free, auto-renewing SSL certificates that work instantly on all devices. Certificates renew automatically before expiry. This is the easiest and most reliable option. Requires: a domain name (e.g., video.yourdomain.com) and port 80 accessible for initial validation.</span>
                                    </span>
                                </div>
                            </div>
                            
                            <div class="two-columns">
                                    <div class="form-group">
                                        <div class="label-with-info">
                                            <label>Domain Name</label>
                                            <span class="info-icon">i
                                                <span class="tooltip">Your fully qualified domain name (e.g., video.yourdomain.com). Must point to this server's IP address via DNS A record. Let's Encrypt will validate ownership by connecting to this domain on port 80.</span>
                                            </span>
                                        </div>
                                        <input type="text" class="form-control" id="ssl-domain" placeholder="video.yourdomain.com" oninput="updateLetsEncryptCommand()">
                                        <span class="help-text">e.g., video.yourdomain.com</span>
                                    </div>
                                    <div class="form-group">
                                        <div class="label-with-info">
                                            <label>Email Address</label>
                                            <span class="info-icon">i
                                                <span class="tooltip">Your email address for Let's Encrypt notifications. You'll receive alerts about certificate expiry (as a backup to automatic renewal) and important updates. Never used for spam.</span>
                                            </span>
                                        </div>
                                        <input type="email" class="form-control" id="ssl-email" placeholder="admin@yourdomain.com" oninput="updateLetsEncryptCommand()">
                                        <span class="help-text">For renewal notifications</span>
                                    </div>
                            </div>
                            
                            <div class="alert alert-info" style="margin-top: 10px; margin-bottom: 0;">
                                <strong>Setup Steps:</strong>
                                <ol style="margin: 10px 0 0 20px; padding: 0; line-height: 1.8;">
                                    <li>Point your domain's DNS to this server's IP</li>
                                    <li><strong>Open port 80</strong> in your router (forward to this server)</li>
                                    <li>Run setup: <code id="letsencrypt-command">sudo ./scripts/setup_letsencrypt.sh your-domain.com your@email.com</code></li>
                                    <li><strong>Fix certificate permissions</strong> (copy/paste entire block):
                                        <pre id="permission-commands" style="background: #2c3e50; color: #ecf0f1; padding: 10px; border-radius: 4px; margin-top: 5px; font-size: 11px; overflow-x: auto;">sudo chmod 755 /etc/letsencrypt/live
sudo chmod 755 /etc/letsencrypt/archive
sudo chmod 755 /etc/letsencrypt/live/your-domain.com
sudo chmod 644 /etc/letsencrypt/live/your-domain.com/fullchain.pem
sudo chmod 644 /etc/letsencrypt/live/your-domain.com/privkey.pem</pre>
                                    </li>
                                    <li>Enable SSL in this config editor and save</li>
                                    <li><strong>Access via HTTPS:</strong> <code>https://localhost:58443</code> (note the <strong>https://</strong>)</li>
                                </ol>
                                
                                <div id="after-setup-note" style="margin-top: 15px; padding: 10px; background: #e8f5e9; border-left: 3px solid #4caf50; border-radius: 4px;">
                                    <strong>✅ After Setup:</strong> Server will be accessible at <code id="https-domain-url">https://your-domain.com:8443</code> from anywhere, and <code>https://localhost:58443</code> locally. The menu bar app links will automatically update to use HTTPS.
                                </div>
                                
                                <div style="margin-top: 10px; padding: 10px; background: #fff3cd; border-left: 3px solid #ffc107; border-radius: 4px;">
                                    <strong>⚠️ Port 80 Required:</strong> Let's Encrypt needs port 80 open to verify domain ownership. You can close it after setup, but <strong>must reopen it every 60 days for automatic certificate renewal</strong>. If your certificates expire and iOS shows "not secure", check that port 80 is forwarded in your router.
                                </div>
                                
                                <div style="margin-top: 10px; padding: 10px; background: #ffebee; border-left: 3px solid #f44336; border-radius: 4px; font-size: 12px;">
                                    <strong>🔒 Important:</strong> Certificates auto-renew every 60 days. Without proper permissions, the server won't start with SSL enabled. If you get "Permission denied" errors, re-run the permission commands above.
                                </div>
                            </div>
                        </div>
                        
                        <!-- Manual Certificate Section -->
                        <div class="form-group" style="background: #fff3cd; padding: 20px; border-radius: 8px; border-left: 4px solid #ffc107;">
                            <div style="margin-bottom: 15px;">
                                <div class="label-with-info">
                                    <label style="font-size: 16px; color: #856404;">📝 Manual Certificate (Self-Signed or Custom)</label>
                                    <span class="info-icon" style="background: #ffc107;">i
                                        <span class="tooltip">Use this for development/testing with self-signed certificates, or if you have your own SSL certificate from another provider. Self-signed certificates require manual installation on each iOS device. Not recommended for production.</span>
                                    </span>
                                </div>
                                <span class="help-text" style="color: #856404;">Only if NOT using Let's Encrypt</span>
                            </div>
                            
                            <div class="two-columns">
                                <div class="form-group">
                                    <div class="label-with-info">
                                        <label>Certificate File Path</label>
                                        <span class="info-icon" style="background: #ffc107;">i
                                            <span class="tooltip">Path to your SSL certificate file (.crt or .pem). For self-signed: generate with './scripts/generate_selfsigned.sh'. The certificate must match the private key below.</span>
                                        </span>
                                    </div>
                                    <input type="text" class="form-control" id="ssl-cert" placeholder="certs/server.crt">
                                    <span class="help-text">e.g., certs/server.crt</span>
                                </div>
                                <div class="form-group">
                                    <div class="label-with-info">
                                        <label>Private Key File Path</label>
                                        <span class="info-icon" style="background: #ffc107;">i
                                            <span class="tooltip">Path to your SSL private key file (.key or .pem). Keep this file secure—never share it. Must correspond to the certificate file above.</span>
                                        </span>
                                    </div>
                                    <input type="text" class="form-control" id="ssl-key" placeholder="certs/server.key">
                                    <span class="help-text">e.g., certs/server.key</span>
                                </div>
                            </div>
                            
                            <div class="alert alert-info" style="margin-top: 10px; margin-bottom: 0;">
                                <strong>Generate Self-Signed:</strong> <code>./scripts/generate_selfsigned.sh your-hostname</code><br>
                                <strong>⚠️ iOS Setup Required:</strong> You must install the certificate on each iOS device (Settings → Profile → Certificate Trust)
                            </div>
                        </div>
                    </div>
                </div>
                
                <div class="section">
                    <div class="section-header">Database</div>
                    <div class="form-group">
                        <div class="label-with-info">
                            <label>Database Path</label>
                            <span class="info-icon">i
                                <span class="tooltip">Path to the SQLite database file that stores download history, user data, and video metadata. The server creates this file automatically if it doesn't exist. Backups are recommended for production use.</span>
                            </span>
                        </div>
                        <input type="text" class="form-control" id="database-path" placeholder="data/downloads.db">
                        <span class="help-text">Path to SQLite database file</span>
                    </div>
                </div>
            </div>
            
            <!-- Downloads Tab -->
            <div id="tab-downloads" class="tab-content">
                <div class="section">
                    <div class="section-header">Download Settings</div>
                    <div class="form-group">
                        <div class="label-with-info">
                            <label>Output Directory</label>
                            <span class="info-icon">i
                                <span class="tooltip">Where downloaded videos are saved on your computer. Supports ~ for home directory (e.g., ~/Downloads/VideoServer). Videos are organized into subdirectories by genre (TikTok, Instagram, etc.) and user. Create the directory manually or the server will create it automatically.</span>
                            </span>
                        </div>
                        <div style="display: flex; gap: 10px;">
                            <input type="text" class="form-control" id="downloads-output" placeholder="~/Downloads/VideoServer" style="flex: 1;">
                            <input type="file" id="directory-input" webkitdirectory directory multiple style="display: none;">
                            <button type="button" class="btn btn-info" onclick="document.getElementById('directory-input').click()" style="padding: 12px 20px; white-space: nowrap;">
                                📁 Browse
                            </button>
                        </div>
                        <span class="help-text">Where downloaded videos are saved</span>
                    </div>
                    <div class="two-columns">
                        <div class="form-group">
                            <div class="label-with-info">
                                <label>Max Concurrent Downloads</label>
                                <span class="info-icon">i
                                    <span class="tooltip">How many videos can download simultaneously. 1 is recommended to avoid rate limiting and connection issues from platforms. Higher values (2-3) may speed up bulk downloads but can trigger platform anti-bot protections.</span>
                                </span>
                            </div>
                            <input type="number" class="form-control" id="downloads-concurrent" min="1" max="10" placeholder="1">
                            <span class="help-text">Number of simultaneous downloads (1 recommended)</span>
                        </div>
                        <div class="form-group">
                            <div class="label-with-info">
                                <label>Max Retry Attempts</label>
                                <span class="info-icon">i
                                    <span class="tooltip">How many times to retry a failed download before giving up. 3 is a good balance. Set to 0 to disable retries entirely. Failed downloads wait progressively longer between each attempt (see Retry Schedule below).</span>
                                </span>
                            </div>
                            <input type="number" class="form-control" id="downloads-retries" min="0" max="10" placeholder="3" onchange="updateRetryDelayFields()">
                            <span class="help-text">Number of retry attempts for failed downloads</span>
                        </div>
                    </div>
                </div>
                
                <div class="section">
                    <div class="section-header">Retry Schedule</div>
                    <div class="alert alert-info" style="margin-bottom: 20px;">
                        <strong>⏱️ Configure Retry Timing:</strong> How long to wait before each retry attempt. Exponential backoff helps with temporary failures. Times are in seconds.
                    </div>
                    <div id="retry-delays-container" style="display: grid; gap: 15px;">
                        <!-- Dynamic retry delay fields will be inserted here -->
                    </div>
                </div>
            </div>
            
            <!-- Downloader Tab -->
            <div id="tab-downloader" class="tab-content">
                <div class="section">
                    <div class="section-header">yt-dlp Settings</div>
                    <div class="two-columns">
                        <div class="form-group">
                            <label>Rate Limit</label>
                            <input type="text" class="form-control" id="downloader-rate" placeholder="Leave empty for unlimited">
                            <span class="help-text">e.g., '1M' for 1MB/s, '500K' for 500KB/s</span>
                        </div>
                        <div class="form-group">
                            <label>Download Timeout (seconds)</label>
                            <input type="number" class="form-control" id="downloader-timeout" min="10" max="3600" placeholder="300">
                            <span class="help-text">Maximum time for a download</span>
                        </div>
                    </div>
                    <div class="form-group">
                        <div class="checkbox-wrapper">
                            <input type="checkbox" id="downloader-ua-rotation">
                            <label>Enable User Agent Rotation</label>
                        </div>
                        <span class="help-text">Randomize user agent to avoid detection</span>
                    </div>
                </div>
                
                <div class="section">
                    <div class="section-header">Cookie File (Optional)</div>
                    <div class="alert alert-info" style="margin-bottom: 15px;">
                        <strong>🔒 Authentication for Private Content</strong><br><br>
                        Cookie files allow downloading private, age-restricted, or members-only content by authenticating as a logged-in user.<br><br>
                        <strong>How to use:</strong><br>
                        1. Install a browser extension like <strong>"Get cookies.txt LOCALLY"</strong> (Chrome/Firefox)<br>
                        2. Log in to the platform (TikTok, Instagram, etc.) in your browser<br>
                        3. Use the extension to export cookies to a file (e.g., <code>cookies.txt</code>)<br>
                        4. Specify the file path below (supports ~ for home directory)<br>
                        5. Restart the server for changes to take effect<br><br>
                        <strong>⚠️ Security Note:</strong> Cookie files contain your login session. Keep them secure and never share them.
                    </div>
                    <div class="form-group">
                        <label>Cookie File Path</label>
                        <input type="text" class="form-control" id="downloader-cookies" placeholder="e.g., ~/Downloads/cookies.txt (optional)">
                        <span class="help-text">Leave empty if not needed. File must exist at the specified path.</span>
                    </div>
                </div>
            </div>
            
            <!-- Security Tab -->
            <div id="tab-security" class="tab-content">
                <div class="section">
                    <div class="section-header">API Keys</div>
                    <div class="alert alert-info">
                        <strong>⚠️ Security Notice:</strong> Leave empty to disable authentication (not recommended for public access). API keys protect your server from unauthorized use.
                    </div>
                    <div class="form-group">
                        <div class="label-with-info">
                            <label>API Keys (one per line)</label>
                            <span class="info-icon">i
                                <span class="tooltip">API keys authenticate requests from your iOS app. Each line is a separate valid key. You can have multiple keys for different devices or users. Keys should be at least 32 characters. Store keys securely—they're like passwords for your server.</span>
                            </span>
                        </div>
                        <textarea class="form-control" id="security-api-keys" rows="5" placeholder="Enter API keys, one per line"></textarea>
                        <span class="help-text">Generate with: openssl rand -hex 32</span>
                    </div>
                    <button class="btn btn-info" onclick="generateApiKey()">🔑 Generate New API Key</button>
                </div>
                
                <div class="section">
                    <div class="section-header">Rate Limiting</div>
                    <div class="form-group">
                        <div class="label-with-info">
                            <label>Max Requests per Hour</label>
                            <span class="info-icon">i
                                <span class="tooltip">Prevents abuse by limiting how many download requests each client can make per hour. Set based on your usage: 100 is reasonable for personal use, 1000+ for shared/family use. Clients exceeding this limit receive a "rate limited" error.</span>
                            </span>
                        </div>
                        <input type="number" class="form-control" id="security-rate-limit" min="1" max="10000" placeholder="100">
                        <span class="help-text">Maximum requests per client per hour</span>
                    </div>
                </div>
                
                <div class="section">
                    <div class="section-header">Allowed Domains</div>
                    <div class="form-group">
                        <div class="label-with-info">
                            <label>Whitelisted Domains (one per line)</label>
                            <span class="info-icon">i
                                <span class="tooltip">Only accept download requests from these domains. This prevents your server from being used to download from arbitrary websites. Include parent domains (e.g., "tiktok.com" covers "www.tiktok.com", "vm.tiktok.com", etc.).</span>
                            </span>
                        </div>
                        <textarea class="form-control" id="security-domains" rows="4" placeholder="tiktok.com&#10;instagram.com"></textarea>
                        <span class="help-text">Only URLs from these domains will be accepted</span>
                    </div>
                </div>
            </div>
            
            <!-- Logging Tab -->
            <div id="tab-logging" class="tab-content">
                <div class="section">
                    <div class="section-header">Logging Settings</div>
                    <div class="two-columns">
                        <div class="form-group">
                            <label>Log Level</label>
                            <select class="form-control" id="logging-level">
                                <option value="DEBUG">DEBUG</option>
                                <option value="INFO">INFO</option>
                                <option value="WARNING">WARNING</option>
                                <option value="ERROR">ERROR</option>
                                <option value="CRITICAL">CRITICAL</option>
                            </select>
                            <span class="help-text">Use DEBUG for development, INFO for production</span>
                        </div>
                        <div class="form-group">
                            <label>Log File Path</label>
                            <input type="text" class="form-control" id="logging-file" placeholder="logs/server.log">
                            <span class="help-text">Path to log file</span>
                        </div>
                    </div>
                    <div class="two-columns">
                        <div class="form-group">
                            <label>Max Log Size</label>
                            <input type="text" class="form-control" id="logging-max-size" placeholder="10MB">
                            <span class="help-text">e.g., 10MB, 100KB</span>
                        </div>
                        <div class="form-group">
                            <label>Backup Files</label>
                            <input type="number" class="form-control" id="logging-backup" min="0" max="100" placeholder="5">
                            <span class="help-text">Number of old log files to keep</span>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="footer">
            <div>
                <button class="btn btn-secondary" onclick="loadConfig()">🔄 Reload</button>
                <button class="btn btn-danger" onclick="resetToDefaults()">⚠️ Reset to Defaults</button>
            </div>
            <button class="btn btn-primary" onclick="saveConfig()">💾 Save Configuration</button>
        </div>
    </div>
    
    <script>
        let config = {};
        let projectDir = '';
        
        // Update SSL field states based on checkbox values
        function updateSSLFieldStates() {
            const sslEnabled = document.getElementById('ssl-enabled').checked;
            const letsencryptEnabled = document.getElementById('ssl-letsencrypt').checked;
            
            const sslConfigSection = document.getElementById('ssl-config-section');
            const domainField = document.getElementById('ssl-domain');
            const emailField = document.getElementById('ssl-email');
            const certField = document.getElementById('ssl-cert');
            const keyField = document.getElementById('ssl-key');
            const letsencryptCheckbox = document.getElementById('ssl-letsencrypt');
            
            if (!sslEnabled) {
                // SSL disabled - disable everything
                sslConfigSection.style.opacity = '0.5';
                sslConfigSection.style.pointerEvents = 'none';
                letsencryptCheckbox.disabled = true;
                domainField.disabled = true;
                emailField.disabled = true;
                certField.disabled = true;
                keyField.disabled = true;
            } else {
                // SSL enabled - show section
                sslConfigSection.style.opacity = '1';
                sslConfigSection.style.pointerEvents = 'auto';
                letsencryptCheckbox.disabled = false;
                
                if (letsencryptEnabled) {
                    // Let's Encrypt mode - enable domain/email, disable cert/key
                    domainField.disabled = false;
                    emailField.disabled = false;
                    certField.disabled = true;
                    keyField.disabled = true;
                } else {
                    // Manual certificate mode - disable domain/email, enable cert/key
                    domainField.disabled = true;
                    emailField.disabled = true;
                    certField.disabled = false;
                    keyField.disabled = false;
                }
            }
        }
        
        // Update Let's Encrypt command preview with actual domain and email
        function updateLetsEncryptCommand() {
            const domain = document.getElementById('ssl-domain').value.trim();
            const email = document.getElementById('ssl-email').value.trim();
            const commandElement = document.getElementById('letsencrypt-command');
            const permissionElement = document.getElementById('permission-commands');
            
            // Use actual values if provided, otherwise use placeholders
            const domainText = domain || 'your-domain.com';
            const emailText = email || 'your@email.com';
            
            // Update setup command
            if (commandElement) {
                // Use absolute path if we have projectDir, otherwise use relative path
                const scriptPath = projectDir ? `"${projectDir}/scripts/setup_letsencrypt.sh"` : './scripts/setup_letsencrypt.sh';
                
                commandElement.textContent = `sudo ${scriptPath} ${domainText} ${emailText}`;
                
                // Add visual feedback when values are entered
                if (domain && email) {
                    commandElement.style.background = '#e8f5e9';
                    commandElement.style.color = '#2e7d32';
                } else {
                    commandElement.style.background = '';
                    commandElement.style.color = '';
                }
            }
            
            // Update permission commands with actual domain
            if (permissionElement) {
                const permissionCommands = `sudo chmod 755 /etc/letsencrypt/live
sudo chmod 755 /etc/letsencrypt/archive
sudo chmod 755 /etc/letsencrypt/live/${domainText}
sudo chmod 644 /etc/letsencrypt/live/${domainText}/fullchain.pem
sudo chmod 644 /etc/letsencrypt/live/${domainText}/privkey.pem`;
                
                permissionElement.textContent = permissionCommands;
                
                // Add visual feedback when domain is entered
                if (domain) {
                    permissionElement.style.borderLeft = '3px solid #4caf50';
                } else {
                    permissionElement.style.borderLeft = '';
                }
            }
            
            // Update "After Setup" URL with actual domain
            const httpsUrlElement = document.getElementById('https-domain-url');
            if (httpsUrlElement) {
                httpsUrlElement.textContent = `https://${domainText}:8443`;
            }
        }
        
        // Show tab
        function showTab(tabName, event) {
            console.log('showTab called:', tabName);
            
            // Hide all tab contents and buttons
            document.querySelectorAll('.tab-content').forEach(t => {
                t.classList.remove('active');
                t.style.display = 'none'; // Explicitly hide
            });
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            
            // Show selected tab
            const tabElement = document.getElementById('tab-' + tabName);
            console.log('Tab element found:', tabElement);
            
            if (tabElement) {
                tabElement.classList.add('active');
                tabElement.style.display = 'block'; // Explicitly show
            } else {
                console.error('Tab not found:', 'tab-' + tabName);
            }
            
            // Highlight the button
            if (event && event.target) {
                event.target.classList.add('active');
            }
            
            console.log('Tab switched to:', tabName);
        }
        
        // Show alert
        function showAlert(message, type = 'info') {
            const container = document.getElementById('alert-container');
            const alert = document.createElement('div');
            alert.className = `alert alert-${type}`;
            alert.textContent = message;
            container.innerHTML = '';
            container.appendChild(alert);
            
            // Auto-dismiss after 5 seconds
            setTimeout(() => alert.remove(), 5000);
        }
        
        // Load configuration
        async function loadConfig() {
            try {
                document.getElementById('loading').style.display = 'block';
                document.querySelectorAll('.tab-content').forEach(t => t.style.display = 'none');
                
                const response = await fetch('/api/v1/config');
                if (!response.ok) throw new Error('Failed to load configuration');
                
                config = await response.json();
                populateForm(config);
                
                document.getElementById('loading').style.display = 'none';
                document.querySelectorAll('.tab-content').forEach(t => t.style.display = 'block');
                document.querySelectorAll('.tab-content:not(.active)').forEach(t => t.style.display = 'none');
                
                showAlert('Configuration loaded successfully!', 'success');
            } catch (error) {
                showAlert('Error loading configuration: ' + error.message, 'error');
                document.getElementById('loading').style.display = 'none';
            }
        }
        
        // Convert seconds to human-readable time
        function formatSeconds(seconds) {
            if (seconds < 60) return `${seconds} seconds`;
            if (seconds < 3600) {
                const mins = Math.floor(seconds / 60);
                const secs = seconds % 60;
                return secs > 0 ? `${mins}m ${secs}s` : `${mins} minutes`;
            }
            const hours = Math.floor(seconds / 3600);
            const mins = Math.floor((seconds % 3600) / 60);
            return mins > 0 ? `${hours}h ${mins}m` : `${hours} hours`;
        }
        
        // Update retry delay fields based on max_retries value
        function updateRetryDelayFields() {
            const maxRetries = parseInt(document.getElementById('downloads-retries').value) || 0;
            const container = document.getElementById('retry-delays-container');
            
            if (maxRetries === 0) {
                container.innerHTML = '<div class="alert alert-info">No retries configured. Failed downloads will not be retried.</div>';
                return;
            }
            
            // Get existing values
            const existingDelays = [];
            for (let i = 0; i < maxRetries; i++) {
                const input = document.getElementById(`retry-delay-${i}`);
                if (input) {
                    existingDelays.push(parseInt(input.value) || 0);
                }
            }
            
            // Default delays if none exist
            const defaultDelays = [60, 300, 900, 1800, 3600, 7200, 14400, 28800, 57600, 86400];
            
            // Build HTML for retry delay fields
            let html = '';
            for (let i = 0; i < maxRetries; i++) {
                const delay = existingDelays[i] || defaultDelays[i] || (60 * Math.pow(2, i));
                const humanTime = formatSeconds(delay);
                
                html += `
                    <div style="display: flex; align-items: center; gap: 15px; padding: 15px; background: #f8f9fa; border-radius: 8px; border-left: 4px solid #667eea;">
                        <div style="min-width: 120px; font-weight: 600; color: #495057;">
                            Retry ${i + 1}:
                        </div>
                        <div style="flex: 1; display: flex; align-items: center; gap: 10px;">
                            <input 
                                type="number" 
                                class="form-control" 
                                id="retry-delay-${i}" 
                                value="${delay}"
                                min="1"
                                max="86400"
                                style="max-width: 120px;"
                                oninput="updateRetryTimeDisplay(${i})"
                            >
                            <span style="color: #6c757d; font-size: 14px;">seconds</span>
                            <span id="retry-time-${i}" style="color: #667eea; font-weight: 500; font-size: 14px;">
                                (${humanTime})
                            </span>
                        </div>
                    </div>
                `;
            }
            
            container.innerHTML = html;
        }
        
        // Update time display for a specific retry
        function updateRetryTimeDisplay(index) {
            const input = document.getElementById(`retry-delay-${index}`);
            const display = document.getElementById(`retry-time-${index}`);
            if (input && display) {
                const seconds = parseInt(input.value) || 0;
                display.textContent = seconds > 0 ? `(${formatSeconds(seconds)})` : '(invalid)';
            }
        }
        
        // Populate form with config data
        function populateForm(data) {
            // Extract project directory from metadata (for absolute paths in commands)
            if (data._metadata && data._metadata.project_dir) {
                projectDir = data._metadata.project_dir;
            }
            
            // Server
            document.getElementById('server-access-level').value = data.server?.access_level || 'local';
            document.getElementById('server-port').value = data.server?.port || '';
            document.getElementById('ssl-enabled').checked = data.server?.ssl?.enabled || false;
            document.getElementById('ssl-domain').value = data.server?.ssl?.domain || '';
            document.getElementById('ssl-email').value = data.server?.ssl?.letsencrypt_email || '';
            document.getElementById('ssl-letsencrypt').checked = data.server?.ssl?.use_letsencrypt || false;
            document.getElementById('ssl-cert').value = data.server?.ssl?.cert_file || '';
            document.getElementById('ssl-key').value = data.server?.ssl?.key_file || '';
            document.getElementById('database-path').value = data.database?.path || '';
            
            // Update SSL field states and command preview after populating
            updateSSLFieldStates();
            updateLetsEncryptCommand();
            
            // Downloads
            document.getElementById('downloads-output').value = data.downloads?.root_directory || '';
            document.getElementById('downloads-concurrent').value = data.downloads?.max_concurrent || 1;
            document.getElementById('downloads-retries').value = data.downloads?.max_retries || 3;
            
            // Store retry delays for later use
            window.currentRetryDelays = data.downloads?.retry_delays || [60, 300, 900];
            
            // Update retry delay fields
            updateRetryDelayFields();
            
            // Downloader
            document.getElementById('downloader-rate').value = data.downloader?.rate_limit || '';
            document.getElementById('downloader-timeout').value = data.downloader?.timeout || 300;
            document.getElementById('downloader-ua-rotation').checked = data.downloader?.user_agent_rotation || false;
            document.getElementById('downloader-cookies').value = data.downloader?.cookie_file || '';
            
            // Security
            document.getElementById('security-api-keys').value = (data.security?.api_keys || []).join('\\n');
            document.getElementById('security-rate-limit').value = data.security?.rate_limit_per_client || 100;
            document.getElementById('security-domains').value = (data.security?.allowed_domains || []).join('\\n');
            
            // Logging
            document.getElementById('logging-level').value = data.logging?.level || 'INFO';
            document.getElementById('logging-file').value = data.logging?.file || '';
            document.getElementById('logging-max-size').value = data.logging?.max_size || '';
            document.getElementById('logging-backup').value = data.logging?.backup_count || 5;
            
            // Populate retry delays after creating fields
            const retryDelays = data.downloads?.retry_delays || [60, 300, 900];
            retryDelays.forEach((delay, index) => {
                const input = document.getElementById(`retry-delay-${index}`);
                if (input) {
                    input.value = delay;
                    updateRetryTimeDisplay(index);
                }
            });
        }
        
        // Collect form data
        function collectFormData() {
            // Collect retry delays from individual fields
            const maxRetries = parseInt(document.getElementById('downloads-retries').value) || 0;
            const retryDelays = [];
            for (let i = 0; i < maxRetries; i++) {
                const input = document.getElementById(`retry-delay-${i}`);
                if (input) {
                    const delay = parseInt(input.value) || 0;
                    if (delay > 0) {
                        retryDelays.push(delay);
                    }
                }
            }
            
            // Ensure we have at least one delay if retries are enabled
            if (maxRetries > 0 && retryDelays.length === 0) {
                retryDelays.push(60); // Default to 60 seconds
            }
            
            const apiKeysStr = document.getElementById('security-api-keys').value;
            const apiKeys = apiKeysStr.split('\\n').map(s => s.trim()).filter(s => s.length > 0);
            
            const domainsStr = document.getElementById('security-domains').value;
            const domains = domainsStr.split('\\n').map(s => s.trim()).filter(s => s.length > 0);
            
            const rateLimit = document.getElementById('downloader-rate').value.trim();
            const cookieFile = document.getElementById('downloader-cookies').value.trim();
            const sslDomain = document.getElementById('ssl-domain').value.trim();
            const sslEmail = document.getElementById('ssl-email').value.trim();
            
            return {
                server: {
                    access_level: document.getElementById('server-access-level').value,
                    port: parseInt(document.getElementById('server-port').value),
                    ssl: {
                        enabled: document.getElementById('ssl-enabled').checked,
                        domain: sslDomain || null,
                        use_letsencrypt: document.getElementById('ssl-letsencrypt').checked,
                        letsencrypt_email: sslEmail || null,
                        cert_file: document.getElementById('ssl-cert').value,
                        key_file: document.getElementById('ssl-key').value
                    }
                },
                database: {
                    path: document.getElementById('database-path').value
                },
                downloads: {
                    root_directory: document.getElementById('downloads-output').value,
                    max_concurrent: parseInt(document.getElementById('downloads-concurrent').value),
                    max_retries: parseInt(document.getElementById('downloads-retries').value),
                    retry_delays: retryDelays
                },
                downloader: {
                    rate_limit: rateLimit || null,
                    user_agent_rotation: document.getElementById('downloader-ua-rotation').checked,
                    timeout: parseInt(document.getElementById('downloader-timeout').value),
                    cookie_file: cookieFile || null
                },
                security: {
                    api_keys: apiKeys,
                    rate_limit_per_client: parseInt(document.getElementById('security-rate-limit').value),
                    allowed_domains: domains
                },
                logging: {
                    level: document.getElementById('logging-level').value,
                    file: document.getElementById('logging-file').value,
                    max_size: document.getElementById('logging-max-size').value,
                    backup_count: parseInt(document.getElementById('logging-backup').value)
                }
            };
        }
        
        // Save configuration
        async function saveConfig() {
            try {
                // Show loading state
                showAlert('Saving configuration and restarting server...', 'info');
                const saveButton = document.querySelector('button[onclick="saveConfig()"]');
                if (saveButton) {
                    saveButton.disabled = true;
                    saveButton.textContent = '⏳ Saving...';
                }
                
                const data = collectFormData();
                
                const response = await fetch('/api/v1/config', {
                    method: 'PUT',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(data)
                });
                
                if (!response.ok) {
                    const error = await response.json();
                    throw new Error(error.detail || 'Failed to save configuration');
                }
                
                const result = await response.json();
                
                // Show success message with countdown
                if (result.restarting) {
                    // Pass the new SSL state so we can redirect to the correct protocol
                    const newSslEnabled = document.getElementById('ssl-enabled').checked;
                    showRestartCountdown(newSslEnabled);
                } else {
                    showAlert('Configuration saved successfully!', 'success');
                    if (saveButton) {
                        saveButton.disabled = false;
                        saveButton.textContent = '💾 Save Configuration';
                    }
                }
            } catch (error) {
                showAlert('Error saving configuration: ' + error.message, 'error');
                const saveButton = document.querySelector('button[onclick="saveConfig()"]');
                if (saveButton) {
                    saveButton.disabled = false;
                    saveButton.textContent = '💾 Save Configuration';
                }
            }
        }
        
        // Show restart countdown and reload page with correct protocol
        function showRestartCountdown(newSslEnabled) {
            const container = document.getElementById('alert-container');
            const alert = document.createElement('div');
            alert.className = 'alert alert-success';
            
            // Determine the new protocol and URL
            const newProtocol = newSslEnabled ? 'https' : 'http';
            const currentProtocol = window.location.protocol.replace(':', '');
            const protocolChanged = newProtocol !== currentProtocol;
            
            // Build the new URL with the correct protocol
            const newUrl = `${newProtocol}://${window.location.host}${window.location.pathname}`;
            
            let message = '<strong>✅ Configuration saved!</strong><br>Server is restarting...';
            if (protocolChanged) {
                message += `<br><small>Switching to ${newProtocol.toUpperCase()}...</small>`;
            }
            message += `<br><span id="countdown">Page will reload in <strong>5</strong> seconds</span>`;
            
            alert.innerHTML = message;
            container.innerHTML = '';
            container.appendChild(alert);
            
            let seconds = 5;
            const countdownEl = document.getElementById('countdown');
            
            const interval = setInterval(() => {
                seconds--;
                if (seconds > 0) {
                    countdownEl.innerHTML = `Page will reload in <strong>${seconds}</strong> seconds`;
                } else {
                    clearInterval(interval);
                    countdownEl.textContent = 'Redirecting...';
                    setTimeout(() => {
                        // Redirect to the correct protocol
                        window.location.href = newUrl;
                    }, 500);
                }
            }, 1000);
        }
        
        // Reset to defaults
        async function resetToDefaults() {
            if (!confirm('Are you sure you want to reset all settings to defaults? This will overwrite your current configuration!')) {
                return;
            }
            
            try {
                const response = await fetch('/api/v1/config/reset', {
                    method: 'POST'
                });
                
                if (!response.ok) throw new Error('Failed to reset configuration');
                
                await loadConfig();
                showAlert('Configuration reset to defaults!', 'success');
            } catch (error) {
                showAlert('Error resetting configuration: ' + error.message, 'error');
            }
        }
        
        // Generate API key
        async function generateApiKey() {
            try {
                const response = await fetch('/api/v1/config/generate-key', {
                    method: 'POST'
                });
                
                if (!response.ok) throw new Error('Failed to generate API key');
                
                const data = await response.json();
                const currentKeys = document.getElementById('security-api-keys').value;
                const newKeys = currentKeys ? currentKeys + '\\n' + data.api_key : data.api_key;
                document.getElementById('security-api-keys').value = newKeys;
                
                // Copy to clipboard
                navigator.clipboard.writeText(data.api_key);
                showAlert('New API key generated and copied to clipboard!', 'success');
            } catch (error) {
                showAlert('Error generating API key: ' + error.message, 'error');
            }
        }
        
        // Handle directory selection
        document.addEventListener('DOMContentLoaded', function() {
            const directoryInput = document.getElementById('directory-input');
            if (directoryInput) {
                directoryInput.addEventListener('change', function(e) {
                    if (e.target.files && e.target.files.length > 0) {
                        // Get the first file's path
                        const firstFile = e.target.files[0];
                        
                        // Extract directory path from the file path
                        // webkitRelativePath gives us something like "FolderName/subfolder/file.txt"
                        const relativePath = firstFile.webkitRelativePath || firstFile.name;
                        
                        // Get just the root folder name (first part before /)
                        const folderName = relativePath.split('/')[0];
                        
                        // Construct a reasonable path
                        // We can't get the full absolute path for security reasons,
                        // so we'll use common conventions
                        let suggestedPath;
                        
                        // Check if current path has a pattern we can use
                        const currentPath = document.getElementById('downloads-output').value;
                        if (currentPath && currentPath.includes('/')) {
                            // Replace the last directory component
                            const parts = currentPath.split('/');
                            parts[parts.length - 1] = folderName;
                            suggestedPath = parts.join('/');
                        } else {
                            // Use common defaults
                            suggestedPath = `~/Downloads/${folderName}`;
                        }
                        
                        document.getElementById('downloads-output').value = suggestedPath;
                        showAlert(`Folder selected: ${folderName}. Please verify the full path is correct.`, 'success');
                    }
                });
            }
        });
        
        // Load config on page load
        window.addEventListener('DOMContentLoaded', loadConfig);
    </script>
</body>
</html>
    """
    return HTMLResponse(content=html_content)


@router.get("")
async def read_config():
    """Get current configuration"""
    try:
        if not CONFIG_PATH.exists():
            raise HTTPException(status_code=404, detail="Configuration file not found")
        
        with open(CONFIG_PATH, 'r') as f:
            config = yaml.safe_load(f)
        
        # Add project directory path for use in UI (for absolute paths in commands)
        config['_metadata'] = {
            'project_dir': str(PROJECT_DIR)
        }
        
        return config
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error reading config: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to read configuration: {str(e)}")


@router.put("")
async def update_config(config: Dict[str, Any]):
    """Update configuration with validation and backup"""
    try:
        # Validate required top-level sections
        required_sections = ['server', 'database', 'downloads', 'downloader', 'security', 'logging']
        missing_sections = [s for s in required_sections if s not in config]
        if missing_sections:
            raise HTTPException(
                status_code=400, 
                detail=f"Missing required configuration sections: {', '.join(missing_sections)}"
            )
        
        # Validate server configuration
        server_config = config.get('server', {})
        if 'access_level' not in server_config:
            raise HTTPException(status_code=400, detail="server.access_level is required")
        
        # Validate access_level value
        valid_access_levels = ['localhost', 'local', 'public']
        if server_config['access_level'] not in valid_access_levels:
            raise HTTPException(status_code=400, detail=f"server.access_level must be one of: {', '.join(valid_access_levels)}")
        
        if 'port' not in server_config:
            raise HTTPException(status_code=400, detail="server.port is required")
        
        # Validate port number
        try:
            port = int(server_config['port'])
            if port < 1024 or port > 65535:
                raise HTTPException(status_code=400, detail="Port must be between 1024 and 65535")
        except (ValueError, TypeError):
            raise HTTPException(status_code=400, detail="Port must be a valid integer")
        
        # Validate SSL configuration
        if server_config.get('ssl', {}).get('enabled'):
            ssl_config = server_config['ssl']
            if ssl_config.get('use_letsencrypt'):
                if not ssl_config.get('domain'):
                    raise HTTPException(status_code=400, 
                                      detail="Domain name is required when using Let's Encrypt")
                if not ssl_config.get('letsencrypt_email'):
                    raise HTTPException(status_code=400, 
                                      detail="Email is required when using Let's Encrypt")
            else:
                # Validate manual cert paths
                if not ssl_config.get('cert_file'):
                    raise HTTPException(status_code=400, detail="Certificate file path is required")
                if not ssl_config.get('key_file'):
                    raise HTTPException(status_code=400, detail="Key file path is required")
        
        # Test YAML serialization
        try:
            test_yaml = yaml.dump(config, default_flow_style=False, sort_keys=False)
            # Test parsing it back
            yaml.safe_load(test_yaml)
        except yaml.YAMLError as e:
            raise HTTPException(status_code=400, detail=f"Invalid YAML structure: {str(e)}")
        
        # Create backup of current config
        if CONFIG_PATH.exists():
            from datetime import datetime
            import shutil
            backup_dir = PROJECT_DIR / "config" / "backups"
            backup_dir.mkdir(exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = backup_dir / f"config.yaml.backup_{timestamp}"
            
            try:
                shutil.copy(CONFIG_PATH, backup_path)
                logger.info(f"Created config backup: {backup_path}")
            except Exception as e:
                logger.warning(f"Failed to create backup: {e}")
                # Continue anyway - backup failure shouldn't block update
        
        # Save configuration
        with open(CONFIG_PATH, 'w') as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)
        
        logger.info("Configuration updated successfully")
        
        # Schedule server restart after response is sent
        import asyncio
        import os
        import signal
        import subprocess
        import sys
        
        async def restart_server():
            """Restart the server after a delay"""
            await asyncio.sleep(2)  # Give time for response to be sent
            logger.info("Triggering server restart due to configuration change...")
            
            try:
                manage_script = PROJECT_DIR / "manage.sh"
                venv_python = PROJECT_DIR / "venv" / "bin" / "python"
                server_script = PROJECT_DIR / "server.py"
                log_file = PROJECT_DIR / "logs" / "nohup.log"
                
                # Create a shell script that waits for us to die, then starts the server
                restart_cmd = f'''
                    sleep 2
                    cd "{PROJECT_DIR}"
                    "{venv_python}" "{server_script}" >> "{log_file}" 2>&1 &
                    echo $! > "{PROJECT_DIR}/server.pid"
                '''
                
                logger.info("Scheduling server restart...")
                # Start the restart script in background shell
                subprocess.Popen(
                    ['bash', '-c', restart_cmd],
                    start_new_session=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                
                # Now terminate ourselves
                await asyncio.sleep(0.1)
                logger.info("Terminating current server process...")
                os.kill(os.getpid(), signal.SIGTERM)
                
            except Exception as e:
                logger.error(f"Failed to restart server: {e}")
                # Last resort: just terminate
                pid = os.getpid()
                os.kill(pid, signal.SIGTERM)
        
        # Schedule restart in background
        asyncio.create_task(restart_server())
        
        return {"message": "Configuration saved successfully. Server will restart in 2 seconds.", "restarting": True}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error saving config: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to save configuration: {str(e)}")


@router.post("/reset")
async def reset_config():
    """Reset configuration to defaults"""
    try:
        if not CONFIG_EXAMPLE_PATH.exists():
            raise HTTPException(status_code=404, detail="Example configuration not found")
        
        import shutil
        shutil.copy(CONFIG_EXAMPLE_PATH, CONFIG_PATH)
        
        logger.info("Configuration reset to defaults")
        return {"message": "Configuration reset to defaults"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resetting config: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to reset configuration: {str(e)}")


@router.post("/generate-key")
async def generate_api_key():
    """Generate a new API key"""
    try:
        api_key = secrets.token_hex(32)
        return {"api_key": api_key}
    except Exception as e:
        logger.error(f"Error generating API key: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate API key: {str(e)}")


@router.get("/connection")
async def get_connection_info():
    """Get server connection information for client setup
    
    Returns network configuration including LAN and WAN IPs,
    port, protocol, and optional API key. Used for QR code setup.
    
    Returns:
        Connection configuration dictionary
    """
    try:
        config = get_config()
        network_service = get_network_service()
        
        # Get network info with error handling
        port = config.server.port
        ssl_enabled = config.server.ssl.enabled
        
        try:
            network_info = await network_service.get_network_info(port=port, ssl_enabled=ssl_enabled)
        except Exception as e:
            logger.warning(f"Network detection failed: {e}")
            # Provide fallback values
            network_info = {
                "lan": {"ip": "127.0.0.1", "url": f"http://127.0.0.1:{port}", "available": False},
                "wan": {"ip": None, "url": None, "available": False},
                "port": port,
                "protocol": "https" if ssl_enabled else "http",
                "detected_at": None,
                "error": "Network detection unavailable"
            }
        
        # Get API key if configured (use first one)
        api_key = None
        if config.security.api_keys and len(config.security.api_keys) > 0:
            api_key = config.security.api_keys[0]
        
        # Get domain if Let's Encrypt is enabled
        domain = None
        if ssl_enabled and config.server.ssl.use_letsencrypt and config.server.ssl.domain:
            domain = config.server.ssl.domain
        
        # Build response
        response = {
            "server_name": "Video Download Server",
            "version": "2.0.0",
            "domain": domain,  # Domain name (for Let's Encrypt SSL)
            "lan": network_info["lan"],
            "wan": network_info["wan"],
            "port": port,
            "protocol": network_info["protocol"],
            "ssl_enabled": ssl_enabled,
            "api_key": api_key,
            "supported_genres": ["tiktok", "instagram", "youtube", "pdf", "ebook"],
            "setup_timestamp": network_info["detected_at"]
        }
        
        logger.info(f"Connection info requested: LAN={network_info['lan']['ip']}, WAN={network_info['wan']['ip']}")
        return response
        
    except Exception as e:
        logger.error(f"Error getting connection info: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get connection info: {str(e)}")


@router.get("/qr")
@router.get("/qr.png")
async def get_qr_code(format: str = "png", size: int = 10):
    """Generate QR code for easy client setup
    
    Generates a QR code containing server connection information.
    iOS app can scan this to automatically configure connection.
    
    Args:
        format: Output format (png or svg, default: png)
        size: QR code size/scale (1-20, default: 10)
        
    Returns:
        QR code image (PNG or SVG)
    """
    try:
        config = get_config()
        network_service = get_network_service()
        
        # Get network info with error handling
        port = config.server.port
        ssl_enabled = config.server.ssl.enabled
        
        try:
            network_info = await network_service.get_network_info(port=port, ssl_enabled=ssl_enabled)
        except Exception as e:
            logger.warning(f"Network detection failed for QR code: {e}")
            # Provide fallback values
            network_info = {
                "lan": {"ip": "127.0.0.1"},
                "wan": {"ip": None},
                "protocol": "https" if ssl_enabled else "http"
            }
        
        # Get API key if configured
        api_key = None
        if config.security.api_keys and len(config.security.api_keys) > 0:
            api_key = config.security.api_keys[0]
        
        # Get domain if Let's Encrypt is enabled
        domain = None
        if ssl_enabled and config.server.ssl.use_letsencrypt and config.server.ssl.domain:
            domain = config.server.ssl.domain
        
        # Build connection config for QR code
        protocol = network_info.get("protocol", "https" if ssl_enabled else "http")
        qr_data = {
            "domain": domain,  # Domain name (for Let's Encrypt SSL)
            "lan": f"{network_info['lan']['ip']}:{port}",
            "wan": f"{network_info['wan']['ip']}:{port}" if network_info['wan']['ip'] else None,
            "protocol": protocol,
            "key": api_key,
            "v": "2.0"
        }
        
        # Encode as JSON
        qr_content = json.dumps(qr_data)
        
        # Generate QR code
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=max(1, min(20, size)),
            border=4,
        )
        qr.add_data(qr_content)
        qr.make(fit=True)
        
        if format.lower() == "svg":
            # SVG format
            factory = qrcode.image.svg.SvgPathImage
            img = qr.make_image(image_factory=factory)
            
            # Convert to bytes
            buffer = io.BytesIO()
            img.save(buffer)
            buffer.seek(0)
            
            return Response(
                content=buffer.getvalue(),
                media_type="image/svg+xml",
                headers={
                    "Content-Disposition": "inline; filename=server-setup.svg",
                    "Cache-Control": "no-cache"
                }
            )
        else:
            # PNG format (default)
            img = qr.make_image(fill_color="black", back_color="white")
            
            # Convert to bytes
            buffer = io.BytesIO()
            img.save(buffer, format="PNG")
            buffer.seek(0)
            
            return Response(
                content=buffer.getvalue(),
                media_type="image/png",
                headers={
                    "Content-Disposition": "inline; filename=server-setup.png",
                    "Cache-Control": "no-cache"
                }
            )
        
    except Exception as e:
        logger.error(f"Error generating QR code: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to generate QR code: {str(e)}")

