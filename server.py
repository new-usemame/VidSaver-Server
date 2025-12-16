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
5. Auto-launch tray app (cross-platform) or menu bar app (macOS)

By default, the server runs in HTTP mode for simple local network usage.
Enable SSL in config.yaml if you need HTTPS encryption.

Cross-Platform Support:
- Windows: Uses tray_app.py (pystray-based)
- Linux: Uses tray_app.py (pystray-based)
- macOS: Uses tray_app.py (pystray) or menubar_app.py (rumps, legacy)
"""

import sys
import os
from pathlib import Path

# Add app directory to path
sys.path.insert(0, str(Path(__file__).parent))

from app.main import run_server
from app.utils.platform_utils import (
    get_platform, get_venv_python, is_tray_app_running,
    is_process_running, find_process_by_name,
    start_tray_app, PROJECT_DIR, write_pid_file, PID_FILE,
)


def is_menubar_app_running() -> bool:
    """Check if the macOS menu bar app is already running.
    
    Uses cross-platform process detection (psutil if available).
    """
    # Try using the platform utils first
    processes = find_process_by_name("menubar_app.py")
    if processes:
        return True
    
    # Fallback: check PID file
    menubar_pid_file = PROJECT_DIR / "menubar_app.pid"
    if menubar_pid_file.exists():
        try:
            with open(menubar_pid_file, 'r') as f:
                pid = int(f.read().strip())
            return is_process_running(pid)
        except (ValueError, IOError):
            pass
    
        return False


def is_watchdog_running() -> bool:
    """Check if the watchdog is already running."""
    processes = find_process_by_name("menubar_watchdog.py")
    if processes:
        return True
    
    watchdog_pid_file = PROJECT_DIR / "menubar_watchdog.pid"
    if watchdog_pid_file.exists():
        try:
            with open(watchdog_pid_file, 'r') as f:
                pid = int(f.read().strip())
            return is_process_running(pid)
        except (ValueError, IOError):
            pass
    
        return False


def launch_watchdog() -> bool:
    """Launch the watchdog to monitor menu bar app (macOS only)."""
    import subprocess
    
    venv_python = get_venv_python()
    watchdog_script = PROJECT_DIR / "menubar_watchdog.py"
    
    if not watchdog_script.exists():
        return False
    
    try:
        subprocess.Popen(
            [str(venv_python), str(watchdog_script)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
            cwd=str(PROJECT_DIR)
        )
        return True
    except Exception:
        return False


def launch_tray_app() -> bool:
    """Launch the cross-platform tray app.
    
    Returns:
        True if tray app was launched or is already running
    """
    running, pid = is_tray_app_running()
    
    if running:
        print("✅ Tray app already running")
        return True
    
    # Check if tray_app.py exists
    tray_script = PROJECT_DIR / "tray_app.py"
    if not tray_script.exists():
        print("⚠️  Tray app script not found")
        return False
    
    # Check if pystray is available
    try:
        import pystray
    except ImportError:
        print("⚠️  Tray app not available (pystray not installed)")
        print("   Install with: pip install pystray Pillow")
        return False
    
    # Launch tray app
    success, pid = start_tray_app()
    
    if success:
        print(f"🚀 Launched tray app (PID: {pid})")
        return True
    else:
        print("⚠️  Could not launch tray app")
        return False


def launch_menubar_app_macos() -> bool:
    """Launch the macOS-specific menu bar app (legacy, rumps-based).
    
    This is kept for backwards compatibility. The cross-platform
    tray_app.py is preferred on all platforms.
    
    Returns:
        True if menubar app was launched or is already running
    """
    import subprocess
    
    # Only on macOS
    if get_platform() != "darwin":
        return False
    
    # Check if rumps is installed
    try:
        import rumps
    except ImportError:
        return False
    
    menubar_script = PROJECT_DIR / "menubar_app.py"
    
    if not menubar_script.exists():
        return False
    
    # Check if already running
    if is_menubar_app_running():
        print("✅ Menu bar app already running")
        return True
    
        # Launch menu bar app in background
    venv_python = get_venv_python()
    
        try:
            subprocess.Popen(
                [str(venv_python), str(menubar_script)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            cwd=str(PROJECT_DIR)
            )
            print("🚀 Launched menu bar app")
    
    # Launch watchdog to monitor menu bar app
    if not is_watchdog_running():
        if launch_watchdog():
            print("🐕 Launched menu bar watchdog")
    else:
        print("✅ Watchdog already running")
        
        return True
        
    except Exception as e:
        print(f"⚠️  Could not launch menu bar app: {e}")
        return False


def launch_ui_app():
    """Launch the appropriate UI app based on platform and available libraries.
    
    Priority:
    1. Cross-platform tray app (tray_app.py with pystray) - preferred
    2. macOS menu bar app (menubar_app.py with rumps) - legacy fallback
    """
    platform = get_platform()
    
    # Try cross-platform tray app first
    if launch_tray_app():
        return
    
    # On macOS, try legacy menu bar app as fallback
    if platform == "darwin":
        launch_menubar_app_macos()


if __name__ == "__main__":
    # Write our PID file
    write_pid_file(os.getpid(), PID_FILE)
    
    # Try to launch UI app before starting server
    launch_ui_app()
    
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
