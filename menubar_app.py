#!/usr/bin/env python3
"""
Video Download Server - Menu Bar App
Provides a macOS menu bar icon for easy server management
"""

import rumps
import subprocess
import os
import signal
import webbrowser
from pathlib import Path
import AppKit

# Project paths
PROJECT_DIR = Path(__file__).parent.absolute()
PID_FILE = PROJECT_DIR / "server.pid"
MENUBAR_PID_FILE = PROJECT_DIR / "menubar_app.pid"
LOG_FILE = PROJECT_DIR / "logs" / "nohup.log"
VENV_PYTHON = PROJECT_DIR / "venv" / "bin" / "python"


class VideoServerApp(rumps.App):
    def __init__(self):
        super(VideoServerApp, self).__init__(
            "📹",  # Video camera emoji as title
            quit_button=None  # We'll add our own quit button
        )
        
        # Hide dock icon - only show menu bar icon
        import AppKit
        info = AppKit.NSBundle.mainBundle().infoDictionary()
        info["LSUIElement"] = "1"
        
        # Create menu items
        self.status_item = rumps.MenuItem("Checking status...", callback=None)
        self.separator1 = rumps.separator
        self.start_item = rumps.MenuItem("▶️ Start Server", callback=self.start_server)
        self.stop_item = rumps.MenuItem("⏹️ Stop Server", callback=self.stop_server)
        self.restart_item = rumps.MenuItem("🔄 Restart Server", callback=self.restart_server)
        self.separator2 = rumps.separator
        self.qr_setup_item = rumps.MenuItem("📱 QR Code Setup", callback=self.open_qr_browser)
        self.docs_item = rumps.MenuItem("📖 Open API Docs", callback=self.open_docs)
        self.logs_item = rumps.MenuItem("📄 View Logs", callback=self.view_logs)
        self.config_editor_item = rumps.MenuItem("🎛️ Config Editor", callback=self.open_config_editor)
        self.config_item = rumps.MenuItem("📝 Edit Config File", callback=self.open_config)
        self.separator3 = rumps.separator
        self.quit_item = rumps.MenuItem("Quit Menu Bar App", callback=self.quit_app)
        
        # Build menu
        self.menu = [
            self.status_item,
            self.separator1,
            self.start_item,
            self.stop_item,
            self.restart_item,
            self.separator2,
            self.qr_setup_item,
            self.docs_item,
            self.logs_item,
            self.config_editor_item,
            self.config_item,
            self.separator3,
            self.quit_item
        ]
        
        # Update status immediately and set up timer
        self.update_status()
        self.timer = rumps.Timer(self.update_status, 5)  # Update every 5 seconds
        self.timer.start()
        
        # Show notification if server is already running when app starts
        if self.is_server_running():
            rumps.notification(
                "Video Server",
                "Menu Bar App Connected",
                "The server was already running",
                sound=False
            )
    
    def is_server_running(self):
        """Check if server is running"""
        try:
            if not PID_FILE.exists():
                return False
            
            with open(PID_FILE, 'r') as f:
                pid = int(f.read().strip())
            
            # Check if process is running
            os.kill(pid, 0)
            return True
        except (OSError, ValueError):
            if PID_FILE.exists():
                PID_FILE.unlink()
            return False
    
    def get_server_ip(self):
        """Get server IP address"""
        try:
            result = subprocess.run(
                ["ifconfig"],
                capture_output=True,
                text=True,
                timeout=2
            )
            for line in result.stdout.split('\n'):
                if 'inet ' in line and '127.0.0.1' not in line:
                    parts = line.split()
                    if len(parts) >= 2:
                        return parts[1]
        except:
            pass
        return "localhost"
    
    def get_server_protocol(self):
        """Get server protocol (http or https) based on config"""
        try:
            config_file = PROJECT_DIR / "config" / "config.yaml"
            if config_file.exists():
                import yaml
                with open(config_file, 'r') as f:
                    config = yaml.safe_load(f)
                    if config and 'server' in config and 'ssl' in config['server']:
                        if config['server']['ssl'].get('enabled', False):
                            return 'https'
        except:
            pass
        return 'http'
    
    @rumps.timer(5)
    def update_status(self, _=None):
        """Update menu items based on server status"""
        running = self.is_server_running()
        
        if running:
            self.title = "🟢"  # Green circle when running
            self.status_item.title = "✅ Server is Running"
            self.start_item.set_callback(None)  # Disable start
            self.stop_item.set_callback(self.stop_server)  # Enable stop
            self.restart_item.set_callback(self.restart_server)  # Enable restart
        else:
            self.title = "⚪️"  # White circle when stopped
            self.status_item.title = "⭕ Server is Stopped"
            self.start_item.set_callback(self.start_server)  # Enable start
            self.stop_item.set_callback(None)  # Disable stop
            self.restart_item.set_callback(None)  # Disable restart
    
    def start_server(self, _):
        """Start the server"""
        try:
            # Check if already running
            if self.is_server_running():
                rumps.alert(
                    "Server Already Running",
                    "The server is already running"
                )
                return
            
            os.chdir(PROJECT_DIR)
            
            # Ensure log directory exists
            LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
            
            # Start server in background
            with open(LOG_FILE, 'a') as log:
                process = subprocess.Popen(
                    [str(VENV_PYTHON), "server.py"],
                    stdout=log,
                    stderr=log,
                    start_new_session=True
                )
            
            # Save PID
            with open(PID_FILE, 'w') as f:
                f.write(str(process.pid))
            
            protocol = self.get_server_protocol()
            rumps.notification(
                "Video Server",
                "Server Started",
                f"Access at {protocol}://localhost:58443/docs",
                sound=False
            )
            
            self.update_status()
            
        except Exception as e:
            rumps.alert(
                "Error Starting Server",
                f"Failed to start server: {str(e)}"
            )
    
    def stop_server(self, _):
        """Stop the server"""
        try:
            if not PID_FILE.exists():
                rumps.alert("Server Not Running", "No PID file found")
                return
            
            with open(PID_FILE, 'r') as f:
                pid = int(f.read().strip())
            
            # Send SIGTERM
            os.kill(pid, signal.SIGTERM)
            PID_FILE.unlink()
            
            rumps.notification(
                "Video Server",
                "Server Stopped",
                "The server has been shut down",
                sound=False
            )
            
            self.update_status()
            
        except Exception as e:
            rumps.alert(
                "Error Stopping Server",
                f"Failed to stop server: {str(e)}"
            )
    
    def restart_server(self, _):
        """Restart the server"""
        self.stop_server(_)
        import time
        time.sleep(1)
        self.start_server(_)
    
    def open_qr_browser(self, _):
        """Open QR code setup page in browser"""
        running = self.is_server_running()
        ip = self.get_server_ip()
        protocol = self.get_server_protocol()
        
        if running:
            webbrowser.open(f"{protocol}://{ip}:58443/api/v1/config/setup")
        else:
            response = rumps.alert(
                "Server Not Running",
                "The server needs to be running to view QR setup. Start it now?",
                ok="Start Server",
                cancel="Cancel"
            )
            if response == 1:  # OK button
                self.start_server(_)
                import time
                time.sleep(2)  # Wait for server to start
                protocol = self.get_server_protocol()  # Re-check after starting
                webbrowser.open(f"{protocol}://{ip}:58443/api/v1/config/setup")
    
    def open_docs(self, _):
        """Open API documentation in browser"""
        running = self.is_server_running()
        ip = self.get_server_ip()
        protocol = self.get_server_protocol()
        
        if running:
            webbrowser.open(f"{protocol}://{ip}:58443/docs")
        else:
            response = rumps.alert(
                "Server Not Running",
                "The server needs to be running to view docs. Start it now?",
                ok="Start Server",
                cancel="Cancel"
            )
            if response == 1:  # OK button
                self.start_server(_)
                import time
                time.sleep(2)  # Wait for server to start
                protocol = self.get_server_protocol()  # Re-check after starting
                webbrowser.open(f"{protocol}://{ip}:58443/docs")
    
    def view_logs(self, _):
        """Open logs in Console.app"""
        try:
            subprocess.run(["open", "-a", "Console", str(LOG_FILE)])
        except Exception as e:
            rumps.alert(
                "Error Opening Logs",
                f"Failed to open log file: {str(e)}"
            )
    
    def open_config_editor(self, _):
        """Open the config editor in the main server"""
        running = self.is_server_running()
        ip = self.get_server_ip()
        protocol = self.get_server_protocol()
        
        if running:
            webbrowser.open(f"{protocol}://{ip}:58443/api/v1/config/editor")
        else:
            response = rumps.alert(
                "Server Not Running",
                "The server needs to be running to edit config. Start it now?",
                ok="Start Server",
                cancel="Cancel"
            )
            if response == 1:  # OK clicked
                self.start_server(None)
                import time
                time.sleep(2)  # Wait for server to start
                protocol = self.get_server_protocol()  # Re-check after starting
                webbrowser.open(f"{protocol}://{ip}:58443/api/v1/config/editor")
    
    def open_config(self, _):
        """Open config file in default editor"""
        config_file = PROJECT_DIR / "config" / "config.yaml"
        try:
            if not config_file.exists():
                rumps.alert(
                    "Config File Not Found",
                    "The config file doesn't exist yet. Create it from config.yaml.example first."
                )
                return
            
            # Open the config file with default editor
            subprocess.run(["open", str(config_file)])
        except Exception as e:
            rumps.alert(
                "Error Opening Config",
                f"Failed to open config file: {str(e)}"
            )
    
    def quit_app(self, _):
        """Quit the menu bar app"""
        running = self.is_server_running()
        
        if running:
            response = rumps.alert(
                "Server is Running",
                "The server is still running. What would you like to do?",
                ok="Stop Server & Quit",
                cancel="Quit Without Stopping",
                other="Cancel"
            )
            
            if response == 1:  # Stop & Quit
                self.stop_server(_)
                rumps.quit_application()
            elif response == 0:  # Quit without stopping
                rumps.quit_application()
            # else: Cancel, do nothing
        else:
            rumps.quit_application()


def is_menubar_already_running():
    """Check if another instance of menubar app is already running"""
    try:
        if not MENUBAR_PID_FILE.exists():
            return False
        
        with open(MENUBAR_PID_FILE, 'r') as f:
            pid = int(f.read().strip())
        
        # Check if process is running
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            # Process not running, clean up stale PID file
            MENUBAR_PID_FILE.unlink()
            return False
    except (ValueError, IOError):
        return False


def cleanup_pid_file():
    """Remove PID file on exit"""
    try:
        if MENUBAR_PID_FILE.exists():
            MENUBAR_PID_FILE.unlink()
    except:
        pass


def main():
    # Ensure we're in the correct directory
    os.chdir(PROJECT_DIR)
    
    # Check if already running
    if is_menubar_already_running():
        print("Menu bar app is already running. Exiting.")
        # Try to activate the existing instance
        try:
            import AppKit
            AppKit.NSApp.activateIgnoringOtherApps_(True)
        except:
            pass
        return
    
    # Write our PID file
    try:
        with open(MENUBAR_PID_FILE, 'w') as f:
            f.write(str(os.getpid()))
    except Exception as e:
        print(f"Warning: Could not write PID file: {e}")
    
    # Register cleanup on exit
    import atexit
    atexit.register(cleanup_pid_file)
    
    # Start the app
    try:
        app = VideoServerApp()
        app.run()
    finally:
        cleanup_pid_file()


if __name__ == "__main__":
    main()

