#!/usr/bin/env python3
"""
Menu Bar App Watchdog
Monitors and auto-restarts the menu bar app if it crashes
"""

import os
import sys
import time
import subprocess
import signal
from pathlib import Path

PROJECT_DIR = Path(__file__).parent.absolute()
VENV_PYTHON = PROJECT_DIR / "venv" / "bin" / "python"
MENUBAR_SCRIPT = PROJECT_DIR / "menubar_app.py"
MENUBAR_PID_FILE = PROJECT_DIR / "menubar_app.pid"
WATCHDOG_PID_FILE = PROJECT_DIR / "menubar_watchdog.pid"
CHECK_INTERVAL = 10  # Check every 10 seconds


def is_menubar_running():
    """Check if menu bar app is running using PID file"""
    try:
        if not MENUBAR_PID_FILE.exists():
            return False
        
        with open(MENUBAR_PID_FILE, 'r') as f:
            pid = int(f.read().strip())
        
        # Check if process is actually running
        os.kill(pid, 0)
        return True
    except (OSError, ValueError, FileNotFoundError):
        # Process not running or PID file invalid
        if MENUBAR_PID_FILE.exists():
            try:
                MENUBAR_PID_FILE.unlink()
            except:
                pass
        return False


def is_server_running():
    """Check if server is running"""
    try:
        result = subprocess.run(
            ["pgrep", "-f", "server.py"],
            capture_output=True,
            text=True
        )
        # Filter out the watchdog itself
        pids = [pid for pid in result.stdout.strip().split('\n') if pid]
        return len(pids) > 0
    except:
        return False


def launch_menubar():
    """Launch the menu bar app"""
    try:
        subprocess.Popen(
            [str(VENV_PYTHON), str(MENUBAR_SCRIPT)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
            cwd=str(PROJECT_DIR)
        )
        print(f"[{time.strftime('%H:%M:%S')}] 🚀 Launched menu bar app")
        return True
    except Exception as e:
        print(f"[{time.strftime('%H:%M:%S')}] ❌ Failed to launch menu bar app: {e}")
        return False


def cleanup_and_exit(signum=None, frame=None):
    """Clean up and exit"""
    print(f"\n[{time.strftime('%H:%M:%S')}] Watchdog stopping...")
    if WATCHDOG_PID_FILE.exists():
        WATCHDOG_PID_FILE.unlink()
    sys.exit(0)


def main():
    """Main watchdog loop"""
    # Register signal handlers
    signal.signal(signal.SIGINT, cleanup_and_exit)
    signal.signal(signal.SIGTERM, cleanup_and_exit)
    
    # Save watchdog PID
    with open(WATCHDOG_PID_FILE, 'w') as f:
        f.write(str(os.getpid()))
    
    print(f"[{time.strftime('%H:%M:%S')}] 🐕 Menu Bar Watchdog started (PID: {os.getpid()})")
    print(f"[{time.strftime('%H:%M:%S')}] Monitoring menu bar app every {CHECK_INTERVAL} seconds")
    print(f"[{time.strftime('%H:%M:%S')}] Press Ctrl+C to stop\n")
    
    restart_count = 0
    last_restart_time = 0
    
    try:
        while True:
            # Check if server is still running - no point watching if server is down
            if not is_server_running():
                print(f"[{time.strftime('%H:%M:%S')}] ⚠️  Server not running, stopping watchdog")
                break
            
            # Check if menu bar app is running
            if not is_menubar_running():
                current_time = time.time()
                
                # Avoid restart loops (don't restart more than once per minute)
                if current_time - last_restart_time > 60:
                    restart_count += 1
                    print(f"[{time.strftime('%H:%M:%S')}] ⚠️  Menu bar app crashed! Restarting (#{restart_count})...")
                    
                    if launch_menubar():
                        last_restart_time = current_time
                        time.sleep(2)  # Give it time to start
                    else:
                        print(f"[{time.strftime('%H:%M:%S')}] ❌ Failed to restart, will retry in {CHECK_INTERVAL}s")
                else:
                    print(f"[{time.strftime('%H:%M:%S')}] ⚠️  Menu bar app crashed again too quickly, waiting before restart...")
            
            time.sleep(CHECK_INTERVAL)
            
    except KeyboardInterrupt:
        cleanup_and_exit()


if __name__ == "__main__":
    main()

