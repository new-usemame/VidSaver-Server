"""Cross-Platform Utilities

Provides platform-independent utilities for process management,
path handling, and network detection. Works on Windows, Linux, and macOS.
"""

import os
import sys
import socket
import signal
import subprocess
import logging
from pathlib import Path
from typing import Optional, Tuple, Dict, Any
from datetime import datetime

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

logger = logging.getLogger(__name__)

# Project paths
PROJECT_DIR = Path(__file__).parent.parent.parent.absolute()
PID_FILE = PROJECT_DIR / "server.pid"
TRAY_PID_FILE = PROJECT_DIR / "tray_app.pid"
LOG_DIR = PROJECT_DIR / "logs"
SERVER_LOG = LOG_DIR / "server.log"
NOHUP_LOG = LOG_DIR / "nohup.log"
CONFIG_FILE = PROJECT_DIR / "config" / "config.yaml"


def get_platform() -> str:
    """Get current platform name.
    
    Returns:
        'windows', 'linux', or 'darwin' (macOS)
    """
    if sys.platform.startswith('win'):
        return 'windows'
    elif sys.platform.startswith('linux'):
        return 'linux'
    elif sys.platform == 'darwin':
        return 'darwin'
    else:
        return sys.platform


def get_venv_python() -> Path:
    """Get path to Python executable in virtual environment.
    
    Returns:
        Path to venv Python, accounting for platform differences
    """
    venv_dir = PROJECT_DIR / "venv"
    
    if get_platform() == 'windows':
        return venv_dir / "Scripts" / "python.exe"
    else:
        return venv_dir / "bin" / "python"


def get_venv_pip() -> Path:
    """Get path to pip executable in virtual environment.
    
    Returns:
        Path to venv pip
    """
    venv_dir = PROJECT_DIR / "venv"
    
    if get_platform() == 'windows':
        return venv_dir / "Scripts" / "pip.exe"
    else:
        return venv_dir / "bin" / "pip"


def read_pid_file(pid_file: Path = PID_FILE) -> Optional[int]:
    """Read PID from file.
    
    Args:
        pid_file: Path to PID file
        
    Returns:
        PID as integer or None if file doesn't exist or is invalid
    """
    try:
        if not pid_file.exists():
            return None
        
        with open(pid_file, 'r') as f:
            pid_str = f.read().strip()
            return int(pid_str)
    except (ValueError, IOError) as e:
        logger.debug(f"Error reading PID file {pid_file}: {e}")
        return None


def write_pid_file(pid: int, pid_file: Path = PID_FILE) -> bool:
    """Write PID to file.
    
    Args:
        pid: Process ID to write
        pid_file: Path to PID file
        
    Returns:
        True if successful
    """
    try:
        pid_file.parent.mkdir(parents=True, exist_ok=True)
        with open(pid_file, 'w') as f:
            f.write(str(pid))
        return True
    except IOError as e:
        logger.error(f"Error writing PID file {pid_file}: {e}")
        return False


def remove_pid_file(pid_file: Path = PID_FILE) -> bool:
    """Remove PID file.
    
    Args:
        pid_file: Path to PID file
        
    Returns:
        True if removed or didn't exist
    """
    try:
        if pid_file.exists():
            pid_file.unlink()
        return True
    except IOError as e:
        logger.error(f"Error removing PID file {pid_file}: {e}")
        return False


def is_process_running(pid: int) -> bool:
    """Check if a process with given PID is running.
    
    Uses psutil if available, falls back to os.kill signal 0.
    
    Args:
        pid: Process ID to check
        
    Returns:
        True if process is running
    """
    if HAS_PSUTIL:
        try:
            process = psutil.Process(pid)
            return process.is_running() and process.status() != psutil.STATUS_ZOMBIE
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return False
    else:
        # Fallback for when psutil is not available
        try:
            if get_platform() == 'windows':
                # On Windows, we need a different approach without psutil
                import ctypes
                kernel32 = ctypes.windll.kernel32
                handle = kernel32.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
                if handle:
                    kernel32.CloseHandle(handle)
                    return True
                return False
            else:
                # Unix: signal 0 doesn't send a signal but checks if process exists
                os.kill(pid, 0)
                return True
        except (OSError, PermissionError):
            return False


def is_server_running() -> Tuple[bool, Optional[int]]:
    """Check if the video server is running.
    
    Returns:
        Tuple of (is_running, pid)
    """
    pid = read_pid_file(PID_FILE)
    
    if pid is None:
        return False, None
    
    if is_process_running(pid):
        return True, pid
    else:
        # Stale PID file - clean it up
        remove_pid_file(PID_FILE)
        return False, None


def is_tray_app_running() -> Tuple[bool, Optional[int]]:
    """Check if the tray app is running.
    
    Returns:
        Tuple of (is_running, pid)
    """
    pid = read_pid_file(TRAY_PID_FILE)
    
    if pid is None:
        return False, None
    
    if is_process_running(pid):
        return True, pid
    else:
        # Stale PID file - clean it up
        remove_pid_file(TRAY_PID_FILE)
        return False, None


def find_process_by_name(name: str) -> list:
    """Find processes by name pattern.
    
    Args:
        name: Process name or pattern to match
        
    Returns:
        List of matching process info dicts
    """
    if not HAS_PSUTIL:
        logger.warning("psutil not available, cannot find processes by name")
        return []
    
    matches = []
    for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'create_time']):
        try:
            info = proc.info
            cmdline = ' '.join(info.get('cmdline') or [])
            
            if name in info.get('name', '') or name in cmdline:
                matches.append({
                    'pid': info['pid'],
                    'name': info['name'],
                    'cmdline': cmdline,
                    'create_time': info.get('create_time')
                })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    
    return matches


def kill_process(pid: int, force: bool = False) -> bool:
    """Kill a process by PID.
    
    Args:
        pid: Process ID to kill
        force: If True, use SIGKILL instead of SIGTERM
        
    Returns:
        True if process was killed or doesn't exist
    """
    if not is_process_running(pid):
        return True
    
    try:
        if get_platform() == 'windows':
            if HAS_PSUTIL:
                proc = psutil.Process(pid)
                if force:
                    proc.kill()
                else:
                    proc.terminate()
            else:
                # Fallback: use taskkill
                flag = '/F' if force else ''
                subprocess.run(['taskkill', flag, '/PID', str(pid)], 
                             capture_output=True, check=True)
        else:
            sig = signal.SIGKILL if force else signal.SIGTERM
            os.kill(pid, sig)
        
        return True
    except Exception as e:
        logger.error(f"Error killing process {pid}: {e}")
        return False


def stop_server(timeout: int = 10) -> bool:
    """Stop the video server gracefully.
    
    Args:
        timeout: Seconds to wait for graceful shutdown before forcing
        
    Returns:
        True if server was stopped
    """
    running, pid = is_server_running()
    
    if not running:
        logger.info("Server is not running")
        return True
    
    logger.info(f"Stopping server (PID: {pid})...")
    
    # Try graceful shutdown first
    if not kill_process(pid, force=False):
        return False
    
    # Wait for process to exit
    if HAS_PSUTIL:
        try:
            proc = psutil.Process(pid)
            proc.wait(timeout=timeout)
        except psutil.TimeoutExpired:
            logger.warning("Server didn't stop gracefully, forcing...")
            kill_process(pid, force=True)
        except psutil.NoSuchProcess:
            pass
    else:
        # Without psutil, just wait a bit
        import time
        for _ in range(timeout):
            if not is_process_running(pid):
                break
            time.sleep(1)
        else:
            logger.warning("Server didn't stop gracefully, forcing...")
            kill_process(pid, force=True)
    
    remove_pid_file(PID_FILE)
    logger.info("Server stopped")
    return True


def start_server(with_tray: bool = False) -> Tuple[bool, Optional[int]]:
    """Start the video server.
    
    Args:
        with_tray: Also start the tray app (on supported platforms)
        
    Returns:
        Tuple of (success, pid)
    """
    running, pid = is_server_running()
    
    if running:
        logger.warning(f"Server is already running (PID: {pid})")
        return True, pid
    
    # Ensure log directory exists
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    
    python = get_venv_python()
    server_script = PROJECT_DIR / "server.py"
    
    if not python.exists():
        logger.error(f"Python not found: {python}")
        return False, None
    
    if not server_script.exists():
        logger.error(f"Server script not found: {server_script}")
        return False, None
    
    try:
        # Start server in background
        if get_platform() == 'windows':
            # Windows: use CREATE_NEW_PROCESS_GROUP and DETACHED_PROCESS
            DETACHED_PROCESS = 0x00000008
            CREATE_NEW_PROCESS_GROUP = 0x00000200
            
            with open(NOHUP_LOG, 'a') as log:
                process = subprocess.Popen(
                    [str(python), str(server_script)],
                    stdout=log,
                    stderr=log,
                    creationflags=DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP,
                    cwd=str(PROJECT_DIR)
                )
        else:
            # Unix: use start_new_session
            with open(NOHUP_LOG, 'a') as log:
                process = subprocess.Popen(
                    [str(python), str(server_script)],
                    stdout=log,
                    stderr=log,
                    start_new_session=True,
                    cwd=str(PROJECT_DIR)
                )
        
        # Save PID
        write_pid_file(process.pid)
        
        logger.info(f"Server started (PID: {process.pid})")
        
        # Optionally start tray app
        if with_tray:
            start_tray_app()
        
        return True, process.pid
        
    except Exception as e:
        logger.error(f"Error starting server: {e}")
        return False, None


def start_tray_app() -> Tuple[bool, Optional[int]]:
    """Start the cross-platform tray app.
    
    Returns:
        Tuple of (success, pid)
    """
    running, pid = is_tray_app_running()
    
    if running:
        logger.info(f"Tray app is already running (PID: {pid})")
        return True, pid
    
    python = get_venv_python()
    tray_script = PROJECT_DIR / "tray_app.py"
    
    if not tray_script.exists():
        logger.warning("Tray app script not found")
        return False, None
    
    try:
        if get_platform() == 'windows':
            DETACHED_PROCESS = 0x00000008
            CREATE_NEW_PROCESS_GROUP = 0x00000200
            
            process = subprocess.Popen(
                [str(python), str(tray_script)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP,
                cwd=str(PROJECT_DIR)
            )
        else:
            process = subprocess.Popen(
                [str(python), str(tray_script)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
                cwd=str(PROJECT_DIR)
            )
        
        write_pid_file(process.pid, TRAY_PID_FILE)
        logger.info(f"Tray app started (PID: {process.pid})")
        return True, process.pid
        
    except Exception as e:
        logger.error(f"Error starting tray app: {e}")
        return False, None


def stop_tray_app() -> bool:
    """Stop the tray app.
    
    Returns:
        True if stopped
    """
    running, pid = is_tray_app_running()
    
    if not running:
        return True
    
    kill_process(pid)
    remove_pid_file(TRAY_PID_FILE)
    logger.info("Tray app stopped")
    return True


def is_port_in_use(port: int, host: str = '0.0.0.0') -> bool:
    """Check if a port is already in use.
    
    Args:
        port: Port number to check
        host: Host to bind to (default 0.0.0.0)
        
    Returns:
        True if port is in use, False if available
    """
    import socket
    
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind((host, port))
            return False  # Port is available
        except OSError:
            return True  # Port is in use


def get_port_process(port: int) -> Optional[Dict[str, Any]]:
    """Get information about the process using a port.
    
    Args:
        port: Port number to check
        
    Returns:
        Dict with process info (pid, name, cmdline, cwd) or None
    """
    # Try psutil first (cross-platform)
    if HAS_PSUTIL:
        try:
            for conn in psutil.net_connections(kind='inet'):
                if conn.laddr.port == port and conn.status == 'LISTEN':
                    try:
                        proc = psutil.Process(conn.pid)
                        return {
                            'pid': conn.pid,
                            'name': proc.name(),
                            'cmdline': ' '.join(proc.cmdline()),
                            'cwd': proc.cwd() if hasattr(proc, 'cwd') else None,
                        }
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        return {'pid': conn.pid, 'name': 'unknown', 'cmdline': '', 'cwd': None}
        except (psutil.AccessDenied, OSError):
            pass
    
    # Fallback: use lsof on Unix systems
    platform = get_platform()
    if platform in ('darwin', 'linux'):
        try:
            result = subprocess.run(
                ['lsof', '-i', f':{port}', '-t'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0 and result.stdout.strip():
                pid = int(result.stdout.strip().split('\n')[0])
                
                # Get more info about the process
                info = {'pid': pid, 'name': 'unknown', 'cmdline': '', 'cwd': None}
                
                if HAS_PSUTIL:
                    try:
                        proc = psutil.Process(pid)
                        info['name'] = proc.name()
                        info['cmdline'] = ' '.join(proc.cmdline())
                        try:
                            info['cwd'] = proc.cwd()
                        except (psutil.AccessDenied, OSError):
                            pass
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
                
                return info
        except (subprocess.TimeoutExpired, FileNotFoundError, ValueError):
            pass
    
    return None


def get_lan_ip() -> str:
    """Get LAN IP address (cross-platform).
    
    Returns:
        LAN IP address or '127.0.0.1' if detection fails
    """
    try:
        # Connect to external address to find local IP (doesn't actually send data)
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.1)
        try:
            s.connect(('8.8.8.8', 80))
            ip = s.getsockname()[0]
            return ip
        finally:
            s.close()
    except Exception:
        pass
    
    try:
        # Fallback: get hostname and resolve
        hostname = socket.gethostname()
        ip = socket.gethostbyname(hostname)
        if ip != '127.0.0.1':
            return ip
    except Exception:
        pass
    
    return '127.0.0.1'


def get_server_urls(port: int = 58443, ssl_enabled: bool = False) -> Dict[str, str]:
    """Get server URLs for access.
    
    Args:
        port: Server port
        ssl_enabled: Whether HTTPS is enabled
        
    Returns:
        Dict with 'local' and 'lan' URLs
    """
    protocol = 'https' if ssl_enabled else 'http'
    lan_ip = get_lan_ip()
    
    return {
        'local': f"{protocol}://localhost:{port}",
        'lan': f"{protocol}://{lan_ip}:{port}",
        'docs': f"{protocol}://localhost:{port}/docs",
        'config_editor': f"{protocol}://localhost:{port}/api/v1/config/editor",
        'qr_setup': f"{protocol}://{lan_ip}:{port}/api/v1/config/setup",
    }


def get_server_config() -> Dict[str, Any]:
    """Read server configuration.
    
    Returns:
        Configuration dict
    """
    try:
        import yaml
        
        if not CONFIG_FILE.exists():
            return {}
        
        with open(CONFIG_FILE, 'r') as f:
            config = yaml.safe_load(f)
            return config or {}
    except Exception as e:
        logger.error(f"Error reading config: {e}")
        return {}


def get_server_info() -> Dict[str, Any]:
    """Get comprehensive server information.
    
    Returns:
        Dict with server status, config, and URLs
    """
    running, pid = is_server_running()
    config = get_server_config()
    
    port = config.get('server', {}).get('port', 58443)
    ssl_enabled = config.get('server', {}).get('ssl', {}).get('enabled', False)
    
    info = {
        'running': running,
        'pid': pid,
        'platform': get_platform(),
        'project_dir': str(PROJECT_DIR),
        'port': port,
        'ssl_enabled': ssl_enabled,
        'urls': get_server_urls(port, ssl_enabled) if running else {},
    }
    
    # Add process info if running and psutil available
    if running and pid and HAS_PSUTIL:
        try:
            proc = psutil.Process(pid)
            info['uptime'] = datetime.now().timestamp() - proc.create_time()
            info['memory_mb'] = proc.memory_info().rss / 1024 / 1024
            info['cpu_percent'] = proc.cpu_percent(interval=0.1)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    
    return info


def tail_log(lines: int = 50) -> list:
    """Read last N lines from log file.
    
    Args:
        lines: Number of lines to read
        
    Returns:
        List of log lines
    """
    log_file = NOHUP_LOG if NOHUP_LOG.exists() else SERVER_LOG
    
    if not log_file.exists():
        return []
    
    try:
        with open(log_file, 'r', encoding='utf-8', errors='replace') as f:
            all_lines = f.readlines()
            return all_lines[-lines:]
    except Exception as e:
        logger.error(f"Error reading log: {e}")
        return []


def open_in_browser(url: str) -> bool:
    """Open URL in default browser (cross-platform).
    
    Args:
        url: URL to open
        
    Returns:
        True if successful
    """
    import webbrowser
    try:
        webbrowser.open(url)
        return True
    except Exception as e:
        logger.error(f"Error opening browser: {e}")
        return False


def open_in_editor(file_path: Path) -> bool:
    """Open file in default editor (cross-platform).
    
    Args:
        file_path: Path to file
        
    Returns:
        True if successful
    """
    try:
        platform = get_platform()
        
        if platform == 'windows':
            os.startfile(str(file_path))
        elif platform == 'darwin':
            subprocess.run(['open', str(file_path)], check=True)
        else:
            # Linux: try xdg-open
            subprocess.run(['xdg-open', str(file_path)], check=True)
        
        return True
    except Exception as e:
        logger.error(f"Error opening file in editor: {e}")
        return False


def open_log_viewer() -> bool:
    """Open log file in appropriate viewer.
    
    Returns:
        True if successful
    """
    log_file = NOHUP_LOG if NOHUP_LOG.exists() else SERVER_LOG
    
    if not log_file.exists():
        logger.warning("No log file found")
        return False
    
    platform = get_platform()
    
    try:
        if platform == 'darwin':
            # macOS: use Console.app
            subprocess.run(['open', '-a', 'Console', str(log_file)], check=True)
        elif platform == 'windows':
            # Windows: open in default text viewer
            os.startfile(str(log_file))
        else:
            # Linux: try common log viewers, fall back to xdg-open
            for viewer in ['gnome-system-log', 'ksystemlog', 'xdg-open']:
                try:
                    subprocess.run([viewer, str(log_file)], check=True)
                    return True
                except FileNotFoundError:
                    continue
            # Ultimate fallback
            subprocess.run(['xdg-open', str(log_file)], check=True)
        
        return True
    except Exception as e:
        logger.error(f"Error opening log viewer: {e}")
        return False

