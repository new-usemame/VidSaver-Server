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
5. Auto-launch menu bar app (macOS only)

By default, the server runs in HTTP mode for simple local network usage.
Enable SSL in config.yaml if you need HTTPS encryption.
"""

import sys
import os
import platform
import subprocess
from pathlib import Path

# Add app directory to path
sys.path.insert(0, str(Path(__file__).parent))

from app.main import run_server


def is_menubar_app_running():
    """Check if the menu bar app is already running"""
    try:
        result = subprocess.run(
            ["pgrep", "-f", "menubar_app.py"],
            capture_output=True,
            text=True
        )
        return bool(result.stdout.strip())
    except:
        return False


def is_watchdog_running():
    """Check if the watchdog is already running"""
    try:
        result = subprocess.run(
            ["pgrep", "-f", "menubar_watchdog.py"],
            capture_output=True,
            text=True
        )
        return bool(result.stdout.strip())
    except:
        return False


def launch_watchdog():
    """Launch the watchdog to monitor menu bar app"""
    project_dir = Path(__file__).parent
    venv_python = project_dir / "venv" / "bin" / "python"
    watchdog_script = project_dir / "menubar_watchdog.py"
    
    if not watchdog_script.exists():
        return False
    
    try:
        subprocess.Popen(
            [str(venv_python), str(watchdog_script)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
            cwd=str(project_dir)
        )
        return True
    except:
        return False


def launch_menubar_app():
    """Launch the menu bar app if on macOS and not already running"""
    # Only on macOS
    if platform.system() != "Darwin":
        return
    
    # Check if rumps is installed
    try:
        import rumps
    except ImportError:
        print("⚠️  Menu bar app not available (rumps not installed)")
        return
    
    project_dir = Path(__file__).parent
    venv_python = project_dir / "venv" / "bin" / "python"
    menubar_script = project_dir / "menubar_app.py"
    
    if not menubar_script.exists():
        print("⚠️  Menu bar app script not found")
        return
    
    # Check if already running
    if is_menubar_app_running():
        print("✅ Menu bar app already running")
    else:
        # Launch menu bar app in background
        try:
            subprocess.Popen(
                [str(venv_python), str(menubar_script)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
                cwd=str(project_dir)
            )
            print("🚀 Launched menu bar app")
        except Exception as e:
            print(f"⚠️  Could not launch menu bar app: {e}")
            return
    
    # Launch watchdog to monitor menu bar app
    if not is_watchdog_running():
        if launch_watchdog():
            print("🐕 Launched menu bar watchdog")
        else:
            print("⚠️  Could not launch watchdog (menu bar app may not auto-restart)")
    else:
        print("✅ Watchdog already running")


if __name__ == "__main__":
    # Try to launch menu bar app before starting server
    launch_menubar_app()
    
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

