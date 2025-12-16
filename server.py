#!/usr/bin/env python3
"""Video Download Server - Main Entry Point

This is the main entry point for running the server.

Usage:
    python server.py
    
    or
    
    ./server.py

The server will:
1. Load configuration from config/config.yaml
2. Initialize logging
3. Validate SSL certificates (if SSL is enabled)
4. Start the HTTP/HTTPS server on configured port

Cross-Platform Support:
- Windows: Full support (CLI + tray app)
- Linux: Full support (CLI + tray app)
- macOS: Full support (CLI + tray app)

Management:
- Use 'python manage.py' for CLI control
- Use 'python manage.py tray' for system tray app
- Visit the server URL for web interface
"""

import sys
import os
from pathlib import Path

# Add app directory to path
sys.path.insert(0, str(Path(__file__).parent))

from app.main import run_server
from app.utils.platform_utils import write_pid_file, PID_FILE


if __name__ == "__main__":
    # Write our PID file
    write_pid_file(os.getpid(), PID_FILE)
    
    try:
        run_server()
    except KeyboardInterrupt:
        print("\n\nServer stopped by user")
        sys.exit(0)
    except Exception as e:
        import traceback
        print(f"\n\nFatal error: {e}", file=sys.stderr)
        traceback.print_exc()
        sys.exit(1)
