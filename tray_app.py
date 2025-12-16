#!/usr/bin/env python3
"""Video Download Server - Cross-Platform System Tray App

Provides a system tray icon for easy server management.
Works on Windows, Linux, and macOS.

Uses pystray for cross-platform support:
- Windows: System tray notification area
- Linux: AppIndicator/StatusNotifier  
- macOS: NSStatusBar

Usage:
    python tray_app.py
    
    or via manage.py:
    
    python manage.py tray
"""

import sys
import os
import time
import threading
import webbrowser
import logging
from pathlib import Path
from io import BytesIO

# Add app directory to path
sys.path.insert(0, str(Path(__file__).parent))

# Check for required dependencies
try:
    import pystray
    from pystray import MenuItem as item
    from PIL import Image, ImageDraw
    HAS_PYSTRAY = True
except ImportError as e:
    print(f"Error: Required package not found: {e}")
    print("Install with: pip install pystray Pillow")
    sys.exit(1)

from app.utils.platform_utils import (
    is_server_running, start_server, stop_server,
    get_server_info, get_server_config, get_lan_ip,
    open_in_browser, open_log_viewer, open_in_editor,
    PROJECT_DIR, NOHUP_LOG, CONFIG_FILE, TRAY_PID_FILE,
    write_pid_file, remove_pid_file, read_pid_file,
    is_process_running, get_platform,
)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TrayApp:
    """Cross-platform system tray application for Video Download Server."""
    
    def __init__(self):
        self.icon = None
        self.running = True
        self._status_thread = None
        self._last_server_status = None
        
    def create_icon_image(self, running: bool = False) -> Image.Image:
        """Create tray icon image.
        
        Creates a simple icon:
        - Green circle when server is running
        - Red/gray circle when stopped
        
        Args:
            running: Whether server is running
            
        Returns:
            PIL Image for the tray icon
        """
        # Icon size (will be scaled by OS as needed)
        size = 64
        
        # Create image with transparency
        image = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        
        # Draw circle
        padding = 4
        if running:
            # Green circle for running
            fill_color = (76, 175, 80, 255)  # Material green
            outline_color = (56, 142, 60, 255)
        else:
            # Gray circle for stopped
            fill_color = (158, 158, 158, 255)  # Material gray
            outline_color = (117, 117, 117, 255)
        
        draw.ellipse(
            [padding, padding, size - padding, size - padding],
            fill=fill_color,
            outline=outline_color,
            width=2
        )
        
        # Draw play/stop symbol
        center = size // 2
        symbol_size = size // 4
        
        if running:
            # Draw "play" triangle (indicates running)
            draw.polygon([
                (center - symbol_size // 2, center - symbol_size),
                (center - symbol_size // 2, center + symbol_size),
                (center + symbol_size, center)
            ], fill=(255, 255, 255, 255))
        else:
            # Draw square (indicates stopped)
            draw.rectangle([
                center - symbol_size,
                center - symbol_size,
                center + symbol_size,
                center + symbol_size
            ], fill=(255, 255, 255, 255))
        
        return image
    
    def get_status_text(self) -> str:
        """Get status text for menu."""
        running, pid = is_server_running()
        if running:
            return f"✓ Server Running (PID: {pid})"
        else:
            return "✗ Server Stopped"
    
    def create_menu(self):
        """Create the tray menu."""
        running, _ = is_server_running()
        
        return pystray.Menu(
            item(self.get_status_text(), None, enabled=False),
            pystray.Menu.SEPARATOR,
            item(
                '▶ Start Server',
                self.on_start,
                enabled=not running
            ),
            item(
                '■ Stop Server',
                self.on_stop,
                enabled=running
            ),
            item(
                '↻ Restart Server',
                self.on_restart,
                enabled=running
            ),
            pystray.Menu.SEPARATOR,
            item('📱 QR Code Setup', self.on_qr_setup),
            item('📖 API Docs', self.on_open_docs),
            item('🎛 Config Editor', self.on_config_editor),
            item('📄 View Logs', self.on_view_logs),
            item('📝 Edit Config', self.on_edit_config),
            pystray.Menu.SEPARATOR,
            item('Quit', self.on_quit),
        )
    
    def update_icon(self):
        """Update icon based on server status."""
        if self.icon:
            running, _ = is_server_running()
            self.icon.icon = self.create_icon_image(running)
            # Update menu to reflect current state
            self.icon.menu = self.create_menu()
    
    def status_monitor(self):
        """Background thread to monitor server status and update icon."""
        while self.running:
            try:
                running, _ = is_server_running()
                
                # Only update if status changed
                if running != self._last_server_status:
                    self._last_server_status = running
                    self.update_icon()
                    logger.debug(f"Server status changed: {'running' if running else 'stopped'}")
            except Exception as e:
                logger.error(f"Error in status monitor: {e}")
            
            time.sleep(3)  # Check every 3 seconds
    
    def on_start(self, icon, item):
        """Start the server."""
        running, _ = is_server_running()
        if running:
            self.notify("Server Already Running", "The server is already running.")
            return
        
        logger.info("Starting server...")
        success, pid = start_server(with_tray=False)
        
        if success:
            time.sleep(2)  # Wait for startup
            self.update_icon()
            info = get_server_info()
            urls = info.get('urls', {})
            self.notify("Server Started", f"Running on {urls.get('local', 'localhost')}")
        else:
            self.notify("Start Failed", "Failed to start server. Check logs.")
    
    def on_stop(self, icon, item):
        """Stop the server."""
        running, _ = is_server_running()
        if not running:
            self.notify("Server Not Running", "The server is not running.")
            return
        
        logger.info("Stopping server...")
        if stop_server():
            self.update_icon()
            self.notify("Server Stopped", "The server has been stopped.")
        else:
            self.notify("Stop Failed", "Failed to stop server.")
    
    def on_restart(self, icon, item):
        """Restart the server."""
        logger.info("Restarting server...")
        
        running, _ = is_server_running()
        if running:
            stop_server()
            time.sleep(1)
        
        success, pid = start_server(with_tray=False)
        
        if success:
            time.sleep(2)
            self.update_icon()
            self.notify("Server Restarted", f"Now running (PID: {pid})")
        else:
            self.notify("Restart Failed", "Failed to restart server.")
    
    def on_qr_setup(self, icon, item):
        """Open QR code setup page."""
        running, _ = is_server_running()
        if not running:
            self.notify("Server Not Running", "Start the server first.")
            return
        
        info = get_server_info()
        url = info.get('urls', {}).get('qr_setup', '')
        if url:
            open_in_browser(url)
        else:
            self.notify("Error", "Could not determine QR setup URL.")
    
    def on_open_docs(self, icon, item):
        """Open API documentation."""
        running, _ = is_server_running()
        if not running:
            self.notify("Server Not Running", "Start the server first.")
            return
        
        info = get_server_info()
        url = info.get('urls', {}).get('docs', '')
        if url:
            open_in_browser(url)
        else:
            self.notify("Error", "Could not determine docs URL.")
    
    def on_config_editor(self, icon, item):
        """Open config editor in browser."""
        running, _ = is_server_running()
        if not running:
            self.notify("Server Not Running", "Start the server first.")
            return
        
        info = get_server_info()
        url = info.get('urls', {}).get('config_editor', '')
        if url:
            open_in_browser(url)
        else:
            self.notify("Error", "Could not determine config editor URL.")
    
    def on_view_logs(self, icon, item):
        """Open log viewer."""
        if not open_log_viewer():
            self.notify("Error", "Could not open log viewer.")
    
    def on_edit_config(self, icon, item):
        """Open config file in editor."""
        if CONFIG_FILE.exists():
            open_in_editor(CONFIG_FILE)
        else:
            self.notify("Config Not Found", "Config file does not exist yet.")
    
    def on_quit(self, icon, item):
        """Quit the tray app."""
        running, _ = is_server_running()
        
        if running:
            # On quit, just close tray app (leave server running)
            logger.info("Quitting tray app (server still running)")
        
        self.running = False
        icon.stop()
    
    def notify(self, title: str, message: str):
        """Show notification.
        
        Note: pystray notification support varies by platform.
        """
        try:
            if self.icon:
                self.icon.notify(message, title)
        except Exception as e:
            # Notifications may not be supported on all platforms
            logger.debug(f"Notification failed (may not be supported): {e}")
            print(f"[{title}] {message}")
    
    def run(self):
        """Run the tray application."""
        logger.info("Starting tray app...")
        
        # Check if already running
        existing_pid = read_pid_file(TRAY_PID_FILE)
        if existing_pid and is_process_running(existing_pid):
            logger.warning("Tray app is already running")
            print("Tray app is already running. Exiting.")
            return
        
        # Write PID file
        write_pid_file(os.getpid(), TRAY_PID_FILE)
        
        # Get initial server status
        running, _ = is_server_running()
        self._last_server_status = running
        
        # Create icon
        self.icon = pystray.Icon(
            "Video Server",
            self.create_icon_image(running),
            "Video Download Server",
            menu=self.create_menu()
        )
        
        # Start status monitor thread
        self._status_thread = threading.Thread(target=self.status_monitor, daemon=True)
        self._status_thread.start()
        
        logger.info("Tray app started")
        
        try:
            # Run icon (blocks until quit)
            self.icon.run()
        finally:
            self.running = False
            remove_pid_file(TRAY_PID_FILE)
            logger.info("Tray app stopped")


def main():
    """Main entry point."""
    # Change to project directory
    os.chdir(PROJECT_DIR)
    
    # Create and run tray app
    app = TrayApp()
    
    try:
        app.run()
    except KeyboardInterrupt:
        print("\nTray app interrupted")
    except Exception as e:
        logger.error(f"Tray app error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

