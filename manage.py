#!/usr/bin/env python3
"""Video Download Server - Cross-Platform Management CLI

Provides command-line interface for managing the video server.
Works on Windows, Linux, and macOS.

Usage:
    python manage.py start      # Start the server
    python manage.py stop       # Stop the server
    python manage.py restart    # Restart the server
    python manage.py status     # Show server status
    python manage.py logs       # View server logs
    python manage.py info       # Show server info (headless)
    python manage.py console    # Interactive console mode
"""

import sys
import time
from pathlib import Path

# Add app directory to path
sys.path.insert(0, str(Path(__file__).parent))

try:
    import click
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.live import Live
    from rich.layout import Layout
    from rich.text import Text
    HAS_RICH = True
except ImportError:
    HAS_RICH = False
    click = None

from app.utils.platform_utils import (
    is_server_running, start_server, stop_server,
    start_tray_app, stop_tray_app, is_tray_app_running,
    get_server_info, get_server_urls, get_lan_ip,
    tail_log, open_in_browser, open_log_viewer,
    get_platform, PROJECT_DIR, NOHUP_LOG, CONFIG_FILE,
    get_server_config,
)

# Rich console for pretty output
rich_console = Console() if HAS_RICH else None


def print_status(message: str, style: str = ""):
    """Print status message (with or without rich)."""
    if rich_console and HAS_RICH:
        rich_console.print(message, style=style)
    else:
        # Strip rich markup for plain output
        import re
        plain = re.sub(r'\[.*?\]', '', message)
        print(plain)


def print_error(message: str):
    """Print error message."""
    print_status(f"[red]✗[/red] {message}", style="red")


def print_success(message: str):
    """Print success message."""
    print_status(f"[green]✓[/green] {message}", style="green")


def print_info(message: str):
    """Print info message."""
    print_status(f"[blue]ℹ[/blue] {message}", style="blue")


def print_warning(message: str):
    """Print warning message."""
    print_status(f"[yellow]⚠[/yellow] {message}", style="yellow")


# Check if click is available
if click is None:
    print("Error: 'click' package is not installed.")
    print("Install it with: pip install click rich")
    sys.exit(1)


def show_dashboard():
    """Show server status dashboard when no command is given."""
    running, pid = is_server_running()
    info = get_server_info()
    config = get_server_config()
    
    port = config.get('server', {}).get('port', 58443)
    ssl = config.get('server', {}).get('ssl', {}).get('enabled', False)
    protocol = 'https' if ssl else 'http'
    lan_ip = get_lan_ip()
    
    print()
    
    # Status header with big indicator
    if running:
        if HAS_RICH:
            from rich.panel import Panel
            from rich.text import Text
            
            status_text = Text()
            status_text.append("🟢 SERVER RUNNING", style="bold green")
            status_text.append(f"  (PID: {pid})", style="dim")
            rich_console.print(Panel(status_text, border_style="green"))
        else:
            print("=" * 50)
            print("🟢 SERVER RUNNING  (PID: {})".format(pid))
            print("=" * 50)
    else:
        if HAS_RICH:
            from rich.panel import Panel
            from rich.text import Text
            
            status_text = Text()
            status_text.append("🔴 SERVER STOPPED", style="bold red")
            rich_console.print(Panel(status_text, border_style="red"))
        else:
            print("=" * 50)
            print("🔴 SERVER STOPPED")
            print("=" * 50)
    
    print()
    
    # Show URLs if running
    if running:
        if HAS_RICH:
            # Show URLs in a cleaner format
            rich_console.print("[bold cyan]Access URLs[/bold cyan]")
            rich_console.print()
            
            rich_console.print("[bold]This Machine (localhost):[/bold]")
            rich_console.print(f"  [dim]Docs:[/dim]   {protocol}://localhost:{port}/docs")
            rich_console.print(f"  [dim]Config:[/dim] {protocol}://localhost:{port}/api/v1/config/editor")
            rich_console.print(f"  [dim]QR:[/dim]     {protocol}://localhost:{port}/api/v1/config/setup")
            
            rich_console.print()
            rich_console.print("[bold yellow]LAN (other devices):[/bold yellow]")
            rich_console.print(f"  [dim]Docs:[/dim]   [yellow]{protocol}://{lan_ip}:{port}/docs[/yellow]")
            rich_console.print(f"  [dim]Config:[/dim] [yellow]{protocol}://{lan_ip}:{port}/api/v1/config/editor[/yellow]")
            rich_console.print(f"  [dim]QR:[/dim]     [yellow]{protocol}://{lan_ip}:{port}/api/v1/config/setup[/yellow]")
        else:
            print("Access URLs:")
            print()
            print("  This Machine (localhost):")
            print(f"    API Docs:      {protocol}://localhost:{port}/docs")
            print(f"    Config Editor: {protocol}://localhost:{port}/api/v1/config/editor")
            print(f"    QR Setup:      {protocol}://localhost:{port}/api/v1/config/setup")
            print()
            print("  LAN (other devices):")
            print(f"    API Docs:      {protocol}://{lan_ip}:{port}/docs")
            print(f"    Config Editor: {protocol}://{lan_ip}:{port}/api/v1/config/editor")
            print(f"    QR Setup:      {protocol}://{lan_ip}:{port}/api/v1/config/setup")
        
        print()
    
    # Quick commands reference
    if HAS_RICH:
        from rich.table import Table
        
        cmd_table = Table(title="Quick Commands", show_header=False, box=None, padding=(0, 2))
        cmd_table.add_column("Command", style="cyan")
        cmd_table.add_column("Description", style="dim")
        
        if running:
            cmd_table.add_row("python manage.py stop", "Stop the server")
            cmd_table.add_row("python manage.py restart", "Restart the server")
            cmd_table.add_row("python manage.py docs", "Open API docs in browser")
            cmd_table.add_row("python manage.py editor", "Open config editor in browser")
            cmd_table.add_row("python manage.py qr", "Open QR setup in browser")
            cmd_table.add_row("python manage.py logs -f", "Follow server logs")
            cmd_table.add_row("python manage.py console", "Interactive console mode")
        else:
            cmd_table.add_row("python manage.py start", "Start the server")
            cmd_table.add_row("python manage.py start --tray", "Start server + system tray")
        
        cmd_table.add_row("python manage.py --help", "Show all commands")
        
        rich_console.print(cmd_table)
    else:
        print("Quick Commands:")
        if running:
            print("  python manage.py stop      - Stop the server")
            print("  python manage.py restart   - Restart the server")
            print("  python manage.py docs      - Open API docs in browser")
            print("  python manage.py editor    - Open config editor in browser")
            print("  python manage.py logs -f   - Follow server logs")
        else:
            print("  python manage.py start     - Start the server")
        print("  python manage.py --help    - Show all commands")
    
    print()


@click.group(invoke_without_command=True)
@click.version_option(version="1.0.0", prog_name="Video Download Server")
@click.pass_context
def cli(ctx):
    """Video Download Server - Cross-Platform Management CLI
    
    Manage your video download server from the command line.
    Works on Windows, Linux, and macOS.
    """
    # If no command is given, show the dashboard
    if ctx.invoked_subcommand is None:
        show_dashboard()


@cli.command()
@click.option('--tray/--no-tray', default=False, help='Also start the system tray app')
@click.option('--wait', default=2, help='Seconds to wait for startup verification')
def start(tray: bool, wait: int):
    """Start the video download server."""
    running, pid = is_server_running()
    
    if running:
        print_warning(f"Server is already running (PID: {pid})")
        info = get_server_info()
        if info.get('urls'):
            print_info(f"Access at: {info['urls'].get('local', 'N/A')}")
        return
    
    print_info("Starting server...")
    success, pid = start_server(with_tray=tray)
    
    if success:
        # Wait a moment for server to initialize
        time.sleep(wait)
        
        # Verify it's actually running
        running, pid = is_server_running()
        if running:
            print_success(f"Server started successfully (PID: {pid})")
            
            # Show access URLs
            info = get_server_info()
            urls = info.get('urls', {})
            
            print()
            print_status("[bold]Access URLs:[/bold]")
            print_status(f"  Local:  {urls.get('local', 'N/A')}")
            print_status(f"  LAN:    {urls.get('lan', 'N/A')}")
            print_status(f"  Docs:   {urls.get('docs', 'N/A')}")
            
            if tray:
                tray_running, tray_pid = is_tray_app_running()
                if tray_running:
                    print_success(f"Tray app started (PID: {tray_pid})")
        else:
            print_error("Server failed to start. Check logs with: python manage.py logs")
            sys.exit(1)
    else:
        print_error("Failed to start server")
        sys.exit(1)


@cli.command()
@click.option('--force', is_flag=True, help='Force stop (SIGKILL)')
def stop(force: bool):
    """Stop the video download server."""
    running, pid = is_server_running()
    
    if not running:
        print_warning("Server is not running")
        return
    
    print_info(f"Stopping server (PID: {pid})...")
    
    if stop_server(timeout=10 if not force else 1):
        print_success("Server stopped")
    else:
        print_error("Failed to stop server")
        sys.exit(1)


@cli.command()
@click.option('--tray/--no-tray', default=False, help='Also restart the tray app')
def restart(tray: bool):
    """Restart the video download server."""
    print_info("Restarting server...")
    
    running, _ = is_server_running()
    if running:
        stop_server()
        time.sleep(1)
    
    success, pid = start_server(with_tray=tray)
    
    if success:
        time.sleep(2)
        running, pid = is_server_running()
        if running:
            print_success(f"Server restarted (PID: {pid})")
            info = get_server_info()
            if info.get('urls'):
                print_info(f"Access at: {info['urls'].get('local', 'N/A')}")
        else:
            print_error("Server failed to restart")
            sys.exit(1)
    else:
        print_error("Failed to restart server")
        sys.exit(1)


@cli.command()
@click.option('--json', 'as_json', is_flag=True, help='Output as JSON')
def status(as_json: bool):
    """Show server status and health information."""
    info = get_server_info()
    
    if as_json:
        import json
        print(json.dumps(info, indent=2, default=str))
        return
    
    running = info.get('running', False)
    pid = info.get('pid')
    
    # Status header
    if running:
        print_success(f"Server is RUNNING (PID: {pid})")
    else:
        print_error("Server is STOPPED")
    
    print()
    
    # Create status table
    if HAS_RICH:
        table = Table(show_header=False, box=None)
        table.add_column("Key", style="cyan")
        table.add_column("Value")
        
        table.add_row("Platform", info.get('platform', 'unknown'))
        table.add_row("Port", str(info.get('port', 58443)))
        table.add_row("SSL", "Enabled" if info.get('ssl_enabled') else "Disabled")
        table.add_row("Project", str(info.get('project_dir', '')))
        
        if running and 'uptime' in info:
            uptime_secs = int(info['uptime'])
            hours, remainder = divmod(uptime_secs, 3600)
            minutes, seconds = divmod(remainder, 60)
            uptime_str = f"{hours}h {minutes}m {seconds}s"
            table.add_row("Uptime", uptime_str)
        
        if running and 'memory_mb' in info:
            table.add_row("Memory", f"{info['memory_mb']:.1f} MB")
        
        rich_console.print(table)
    else:
        print(f"Platform: {info.get('platform', 'unknown')}")
        print(f"Port: {info.get('port', 58443)}")
        print(f"SSL: {'Enabled' if info.get('ssl_enabled') else 'Disabled'}")
    
    # URLs
    if running:
        urls = info.get('urls', {})
        print()
        print_status("[bold]Access URLs:[/bold]")
        print_status(f"  Local:  {urls.get('local', 'N/A')}")
        print_status(f"  LAN:    {urls.get('lan', 'N/A')}")
        print_status(f"  Docs:   {urls.get('docs', 'N/A')}")
        print_status(f"  Config: {urls.get('config_editor', 'N/A')}")
        print_status(f"  QR:     {urls.get('qr_setup', 'N/A')}")
    
    # Health check
    if running:
        print()
        print_status("[bold]Health Check:[/bold]")
        try:
            import requests
            config = get_server_config()
            port = config.get('server', {}).get('port', 58443)
            ssl = config.get('server', {}).get('ssl', {}).get('enabled', False)
            protocol = 'https' if ssl else 'http'
            
            resp = requests.get(
                f"{protocol}://localhost:{port}/api/v1/health",
                timeout=5,
                verify=False  # Allow self-signed certs
            )
            if resp.status_code == 200:
                health = resp.json()
                print_success(f"  Status: {health.get('status', 'unknown')}")
                if 'database' in health:
                    print_status(f"  Database: {health['database'].get('status', 'unknown')}")
                if 'downloads' in health:
                    downloads = health['downloads']
                    print_status(f"  Queue: {downloads.get('pending', 0)} pending, {downloads.get('processing', 0)} processing")
            else:
                print_warning(f"  Health check returned: {resp.status_code}")
        except Exception as e:
            print_warning(f"  Could not reach health endpoint: {e}")


@cli.command()
@click.option('-n', '--lines', default=50, help='Number of lines to show')
@click.option('-f', '--follow', is_flag=True, help='Follow log output (like tail -f)')
def logs(lines: int, follow: bool):
    """View server logs."""
    if not NOHUP_LOG.exists():
        print_warning("No log file found")
        return
    
    if follow:
        print_info(f"Following log output (Ctrl+C to stop)...")
        print()
        
        try:
            # Initial output
            log_lines = tail_log(lines)
            for line in log_lines:
                print(line.rstrip())
            
            # Follow mode
            last_pos = NOHUP_LOG.stat().st_size
            while True:
                time.sleep(0.5)
                current_size = NOHUP_LOG.stat().st_size
                
                if current_size > last_pos:
                    with open(NOHUP_LOG, 'r', encoding='utf-8', errors='replace') as f:
                        f.seek(last_pos)
                        new_content = f.read()
                        print(new_content, end='')
                    last_pos = current_size
                elif current_size < last_pos:
                    # File was truncated/rotated
                    last_pos = 0
        except KeyboardInterrupt:
            print()
            print_info("Stopped following logs")
    else:
        log_lines = tail_log(lines)
        
        if not log_lines:
            print_warning("Log file is empty")
            return
        
        print_info(f"Last {len(log_lines)} lines from {NOHUP_LOG.name}:")
        print()
        
        for line in log_lines:
            print(line.rstrip())


@cli.command()
@click.option('--json', 'as_json', is_flag=True, help='Output as JSON')
def info(as_json: bool):
    """Show server information (headless-friendly).
    
    Displays server status, configuration, and URLs in a format
    suitable for headless/scripted environments.
    """
    info_data = get_server_info()
    config = get_server_config()
    
    # Add config details
    info_data['config'] = {
        'port': config.get('server', {}).get('port', 58443),
        'host': config.get('server', {}).get('host', '0.0.0.0'),
        'ssl_enabled': config.get('server', {}).get('ssl', {}).get('enabled', False),
        'database': config.get('database', {}).get('path', 'data/downloads.db'),
        'downloads_dir': config.get('downloads', {}).get('root_directory', ''),
    }
    
    if as_json:
        import json
        print(json.dumps(info_data, indent=2, default=str))
        return
    
    # Plain text output for headless mode
    print("=" * 50)
    print("VIDEO DOWNLOAD SERVER - STATUS INFO")
    print("=" * 50)
    print()
    
    running = info_data.get('running', False)
    print(f"Status:   {'RUNNING' if running else 'STOPPED'}")
    if running:
        print(f"PID:      {info_data.get('pid', 'N/A')}")
    print(f"Platform: {info_data.get('platform', 'unknown')}")
    print()
    
    print("Configuration:")
    cfg = info_data.get('config', {})
    print(f"  Host:      {cfg.get('host', 'N/A')}")
    print(f"  Port:      {cfg.get('port', 'N/A')}")
    print(f"  SSL:       {'Enabled' if cfg.get('ssl_enabled') else 'Disabled'}")
    print(f"  Database:  {cfg.get('database', 'N/A')}")
    print(f"  Downloads: {cfg.get('downloads_dir', 'N/A')}")
    print()
    
    if running:
        urls = info_data.get('urls', {})
        print("Access URLs:")
        print(f"  Local:        {urls.get('local', 'N/A')}")
        print(f"  LAN:          {urls.get('lan', 'N/A')}")
        print(f"  API Docs:     {urls.get('docs', 'N/A')}")
        print(f"  Config:       {urls.get('config_editor', 'N/A')}")
        print(f"  QR Setup:     {urls.get('qr_setup', 'N/A')}")
        print()
        
        if 'uptime' in info_data:
            uptime_secs = int(info_data['uptime'])
            hours, remainder = divmod(uptime_secs, 3600)
            minutes, seconds = divmod(remainder, 60)
            print(f"Uptime:   {hours}h {minutes}m {seconds}s")
        
        if 'memory_mb' in info_data:
            print(f"Memory:   {info_data['memory_mb']:.1f} MB")
    
    print()
    print("=" * 50)


@cli.command()
def tray():
    """Start the system tray app."""
    running, pid = is_tray_app_running()
    
    if running:
        print_warning(f"Tray app is already running (PID: {pid})")
        return
    
    success, pid = start_tray_app()
    
    if success:
        print_success(f"Tray app started (PID: {pid})")
    else:
        print_error("Failed to start tray app")
        print_info("Make sure pystray is installed: pip install pystray")
        sys.exit(1)


@cli.command()
def docs():
    """Open API documentation in browser."""
    running, _ = is_server_running()
    
    if not running:
        print_error("Server is not running")
        print_info("Start it with: python manage.py start")
        sys.exit(1)
    
    info = get_server_info()
    docs_url = info.get('urls', {}).get('docs', '')
    
    if docs_url:
        print_info(f"Opening: {docs_url}")
        open_in_browser(docs_url)
    else:
        print_error("Could not determine docs URL")


@cli.command()
def qr():
    """Open QR Code Setup page in browser.
    
    Opens the QR code setup page which allows you to easily
    configure iOS devices by scanning a QR code.
    """
    running, _ = is_server_running()
    
    if not running:
        print_error("Server is not running")
        print_info("Start it with: python manage.py start")
        sys.exit(1)
    
    info = get_server_info()
    qr_url = info.get('urls', {}).get('qr_setup', '')
    
    if qr_url:
        print_info(f"Opening: {qr_url}")
        open_in_browser(qr_url)
    else:
        print_error("Could not determine QR setup URL")


@cli.command()
def editor():
    """Open Config Editor in browser.
    
    Opens the web-based configuration editor which provides
    a user-friendly interface for modifying server settings.
    """
    running, _ = is_server_running()
    
    if not running:
        print_error("Server is not running")
        print_info("Start it with: python manage.py start")
        sys.exit(1)
    
    info = get_server_info()
    editor_url = info.get('urls', {}).get('config_editor', '')
    
    if editor_url:
        print_info(f"Opening: {editor_url}")
        open_in_browser(editor_url)
    else:
        print_error("Could not determine config editor URL")


@cli.command('open-logs')
def open_logs():
    """Open log file in system viewer."""
    if open_log_viewer():
        print_success("Opened log viewer")
    else:
        print_error("Could not open log viewer")
        print_info(f"Log file: {NOHUP_LOG}")


@cli.command()
def config():
    """Show configuration file path."""
    if CONFIG_FILE.exists():
        print_info(f"Config file: {CONFIG_FILE}")
        print()
        print_status("[bold]Current configuration:[/bold]")
        cfg = get_server_config()
        
        if HAS_RICH:
            import yaml
            from rich.syntax import Syntax
            with open(CONFIG_FILE, 'r') as f:
                content = f.read()
            syntax = Syntax(content, "yaml", theme="monokai", line_numbers=True)
            rich_console.print(syntax)
        else:
            import yaml
            print(yaml.dump(cfg, default_flow_style=False))
    else:
        print_warning(f"Config file not found: {CONFIG_FILE}")
        print_info("Create from example: cp config/config.yaml.example config/config.yaml")


def _get_queue_stats() -> dict:
    """Get download queue statistics from the API."""
    try:
        import requests
        config = get_server_config()
        port = config.get('server', {}).get('port', 58443)
        ssl = config.get('server', {}).get('ssl', {}).get('enabled', False)
        protocol = 'https' if ssl else 'http'
        
        # Suppress SSL warnings for self-signed certs
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        
        resp = requests.get(
            f"{protocol}://localhost:{port}/api/v1/health",
            timeout=3,
            verify=False
        )
        if resp.status_code == 200:
            return resp.json().get('downloads', {})
    except Exception:
        pass
    return {}


def _get_recent_downloads(limit: int = 5) -> list:
    """Get recent downloads from the API."""
    try:
        import requests
        config = get_server_config()
        port = config.get('server', {}).get('port', 58443)
        ssl = config.get('server', {}).get('ssl', {}).get('enabled', False)
        protocol = 'https' if ssl else 'http'
        
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        
        resp = requests.get(
            f"{protocol}://localhost:{port}/api/v1/history?limit={limit}",
            timeout=3,
            verify=False
        )
        if resp.status_code == 200:
            return resp.json().get('downloads', [])
    except Exception:
        pass
    return []


def _format_uptime(seconds: float) -> str:
    """Format uptime in human-readable form."""
    secs = int(seconds)
    hours, remainder = divmod(secs, 3600)
    minutes, secs = divmod(remainder, 60)
    
    if hours > 0:
        return f"{hours}h {minutes}m {secs}s"
    elif minutes > 0:
        return f"{minutes}m {secs}s"
    else:
        return f"{secs}s"


def _create_console_layout(info: dict) -> Layout:
    """Create rich layout for console mode."""
    from rich.layout import Layout
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text
    
    layout = Layout()
    
    # Main layout sections
    layout.split_column(
        Layout(name="header", size=3),
        Layout(name="body"),
        Layout(name="footer", size=3)
    )
    
    # Header
    running = info.get('running', False)
    status_color = "green" if running else "red"
    status_text = "RUNNING" if running else "STOPPED"
    
    header_text = Text()
    header_text.append("VIDEO DOWNLOAD SERVER", style="bold white")
    header_text.append(" │ ", style="dim")
    header_text.append(f"[{status_text}]", style=f"bold {status_color}")
    
    if running and 'pid' in info:
        header_text.append(f" PID: {info['pid']}", style="dim")
    if running and 'uptime' in info:
        header_text.append(f" │ Uptime: {_format_uptime(info['uptime'])}", style="cyan")
    
    layout["header"].update(Panel(header_text, style="bold"))
    
    # Body - split into columns
    layout["body"].split_row(
        Layout(name="left", ratio=1),
        Layout(name="right", ratio=1)
    )
    
    # Left panel - Server Info & URLs
    left_content = Table.grid(padding=(0, 2))
    left_content.add_column("Key", style="cyan")
    left_content.add_column("Value")
    
    left_content.add_row("Platform:", info.get('platform', 'unknown'))
    left_content.add_row("Port:", str(info.get('port', 58443)))
    left_content.add_row("SSL:", "Enabled" if info.get('ssl_enabled') else "Disabled")
    
    if running and 'memory_mb' in info:
        left_content.add_row("Memory:", f"{info['memory_mb']:.1f} MB")
    if running and 'cpu_percent' in info:
        left_content.add_row("CPU:", f"{info['cpu_percent']:.1f}%")
    
    left_content.add_row("", "")  # Spacer
    
    if running:
        urls = info.get('urls', {})
        left_content.add_row("[bold]Access URLs[/bold]", "")
        left_content.add_row("  Local:", urls.get('local', 'N/A'))
        left_content.add_row("  LAN:", urls.get('lan', 'N/A'))
        left_content.add_row("  Docs:", urls.get('docs', 'N/A'))
    else:
        left_content.add_row("[yellow]Server stopped[/yellow]", "")
        left_content.add_row("Start with:", "python manage.py start")
    
    layout["left"].update(Panel(left_content, title="Server Info", border_style="blue"))
    
    # Right panel - Queue & Downloads
    right_content = Table.grid(padding=(0, 2))
    right_content.add_column("Info")
    
    if running:
        queue_stats = _get_queue_stats()
        
        queue_text = Text()
        queue_text.append("[bold]Download Queue[/bold]\n\n")
        queue_text.append(f"Pending: ", style="dim")
        queue_text.append(f"{queue_stats.get('pending', 0)}\n", style="yellow")
        queue_text.append(f"Processing: ", style="dim")
        queue_text.append(f"{queue_stats.get('processing', 0)}\n", style="cyan")
        queue_text.append(f"Completed: ", style="dim")
        queue_text.append(f"{queue_stats.get('completed', 0)}\n", style="green")
        queue_text.append(f"Failed: ", style="dim")
        queue_text.append(f"{queue_stats.get('failed', 0)}\n", style="red")
        
        right_content.add_row(queue_text)
        
        # Recent downloads
        recent = _get_recent_downloads(3)
        if recent:
            downloads_text = Text()
            downloads_text.append("\n[bold]Recent Downloads[/bold]\n\n")
            for dl in recent[:3]:
                status = dl.get('status', 'unknown')
                status_style = {
                    'completed': 'green',
                    'failed': 'red',
                    'processing': 'cyan',
                    'pending': 'yellow'
                }.get(status, 'dim')
                
                title = dl.get('title', dl.get('url', 'Unknown'))[:30]
                if len(dl.get('title', dl.get('url', ''))) > 30:
                    title += "..."
                
                downloads_text.append(f"[{status_style}]●[/{status_style}] {title}\n")
            
            right_content.add_row(downloads_text)
    else:
        right_content.add_row("[dim]Queue data not available[/dim]")
    
    layout["right"].update(Panel(right_content, title="Downloads", border_style="green"))
    
    # Footer
    footer_text = Text()
    footer_text.append("Press ", style="dim")
    footer_text.append("Ctrl+C", style="bold yellow")
    footer_text.append(" to exit │ ", style="dim")
    footer_text.append("Refreshing every 2s", style="dim")
    
    from datetime import datetime
    footer_text.append(f" │ {datetime.now().strftime('%H:%M:%S')}", style="dim cyan")
    
    layout["footer"].update(Panel(footer_text, style="dim"))
    
    return layout


@cli.command()
@click.option('--refresh', default=2, help='Refresh interval in seconds')
def console(refresh: int):
    """Interactive console mode with live status updates.
    
    Displays continuously updated server information including
    status, queue, and recent downloads. Uses rich library for
    a beautiful terminal UI.
    
    Perfect for headless servers where you want to monitor
    the server status in real-time.
    """
    if not HAS_RICH:
        # Fallback for when rich is not available
        print("Console mode requires 'rich' library.")
        print("Install with: pip install rich")
        print()
        print("Falling back to basic mode...")
        print()
        
        try:
            while True:
                info = get_server_info()
                running = info.get('running', False)
                
                # Clear screen
                import os
                os.system('cls' if os.name == 'nt' else 'clear')
                
                print("=" * 50)
                print("VIDEO DOWNLOAD SERVER - CONSOLE")
                print("=" * 50)
                print()
                print(f"Status: {'RUNNING' if running else 'STOPPED'}")
                if running:
                    print(f"PID: {info.get('pid')}")
                    urls = info.get('urls', {})
                    print(f"Local: {urls.get('local', 'N/A')}")
                    print(f"LAN: {urls.get('lan', 'N/A')}")
                print()
                print("Press Ctrl+C to exit")
                
                time.sleep(refresh)
        except KeyboardInterrupt:
            print("\nExited")
        return
    
    # Rich console mode
    from rich.live import Live
    
    rich_console.print("[bold cyan]Starting console mode...[/bold cyan]")
    rich_console.print("[dim]Press Ctrl+C to exit[/dim]")
    rich_console.print()
    
    try:
        with Live(console=rich_console, refresh_per_second=1, screen=True) as live:
            while True:
                info = get_server_info()
                layout = _create_console_layout(info)
                live.update(layout)
                time.sleep(refresh)
    except KeyboardInterrupt:
        pass
    
    rich_console.print()
    rich_console.print("[bold cyan]Console mode exited[/bold cyan]")


if __name__ == "__main__":
    cli()

