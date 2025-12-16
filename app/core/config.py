"""Configuration Management

Handles loading and validation of application configuration from YAML files
and environment variables. Uses Pydantic for type validation and settings management.

Configuration priority (highest to lowest):
1. Environment variables (VIDEO_SERVER_*)
2. config.yaml file
3. Default values
"""

import os
from pathlib import Path
from typing import Optional, List
import yaml
from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class SSLConfig(BaseSettings):
    """SSL/TLS configuration"""
    
    enabled: bool = Field(
        default=False,
        description="Enable SSL/TLS (false = HTTP, true = HTTPS)"
    )
    domain: Optional[str] = Field(
        default=None,
        description="Domain name for Let's Encrypt certificates (e.g., 'your-domain.com')"
    )
    use_letsencrypt: bool = Field(
        default=False,
        description="Use Let's Encrypt for automatic SSL certificates"
    )
    letsencrypt_email: Optional[str] = Field(
        default=None,
        description="Email for Let's Encrypt certificate notifications"
    )
    cert_file: str = Field(
        default="certs/server.crt",
        description="Path to SSL certificate file"
    )
    key_file: str = Field(
        default="certs/server.key",
        description="Path to SSL private key file"
    )
    
    model_config = SettingsConfigDict(
        env_prefix="VIDEO_SERVER_SSL_",
        case_sensitive=False
    )
    
    @field_validator("domain")
    @classmethod
    def validate_domain(cls, v: Optional[str]) -> Optional[str]:
        """Validate domain format"""
        if v:
            # Basic domain validation
            v = v.lower().strip()
            if v.startswith("http://") or v.startswith("https://"):
                raise ValueError("Domain should not include http:// or https://")
            if ":" in v:
                raise ValueError("Domain should not include port number")
        return v
    
    @model_validator(mode='after')
    def validate_letsencrypt_config(self):
        """Validate Let's Encrypt configuration"""
        if self.enabled and self.use_letsencrypt:
            if not self.domain:
                raise ValueError("ssl.domain is required when ssl.use_letsencrypt is True")
            if not self.letsencrypt_email:
                raise ValueError("ssl.letsencrypt_email is required when ssl.use_letsencrypt is True")
        return self


class ServerConfig(BaseSettings):
    """Server configuration"""
    
    access_level: str = Field(
        default="local",
        description="Network access level: 'localhost' (this device only), 'local' (LAN access), or 'public' (LAN + internet with port forwarding)"
    )
    port: int = Field(
        default=58443,
        ge=1,
        le=65535,
        description="Server port number"
    )
    ssl: SSLConfig = Field(
        default_factory=SSLConfig,
        description="SSL/TLS configuration"
    )
    
    model_config = SettingsConfigDict(
        env_prefix="VIDEO_SERVER_SERVER_",
        case_sensitive=False
    )
    
    @field_validator("access_level")
    @classmethod
    def validate_access_level(cls, v: str) -> str:
        """Validate and normalize access level"""
        valid_levels = ["localhost", "local", "public"]
        v_lower = v.lower()
        if v_lower not in valid_levels:
            raise ValueError(f"access_level must be one of {valid_levels}, got: {v}")
        return v_lower
    
    @property
    def host(self) -> str:
        """Get the actual host address to bind to based on access level
        
        Returns:
            Host IP address for uvicorn binding
        """
        if self.access_level == "localhost":
            return "127.0.0.1"
        else:  # "local" or "public" - both bind to all interfaces
            return "0.0.0.0"


class DatabaseConfig(BaseSettings):
    """Database configuration"""
    
    path: str = Field(
        default="data/downloads.db",
        description="Path to SQLite database file"
    )
    
    model_config = SettingsConfigDict(
        env_prefix="VIDEO_SERVER_DB_",
        case_sensitive=False
    )
    
    @field_validator("path")
    @classmethod
    def validate_path(cls, v: str) -> str:
        """Expand user home directory in path"""
        return os.path.expanduser(v)


class DownloadsConfig(BaseSettings):
    """Downloads configuration"""
    
    root_directory: str = Field(
        default="~/Downloads/VidSaver",
        description="Root directory for user folders and downloaded content. "
                    "Structure: {root}/{username}/{genre}/ where genre is tiktok, instagram, youtube, pdf, ebook, or unknown"
    )
    max_concurrent: int = Field(
        default=1,
        ge=1,
        le=10,
        description="Maximum number of concurrent downloads"
    )
    max_retries: int = Field(
        default=3,
        ge=0,
        le=10,
        description="Maximum number of retry attempts for failed downloads"
    )
    retry_delays: List[int] = Field(
        default=[60, 300, 900],
        description="Delay in seconds between retries (exponential backoff)"
    )
    
    model_config = SettingsConfigDict(
        env_prefix="VIDEO_SERVER_DOWNLOADS_",
        case_sensitive=False
    )
    
    @field_validator("root_directory")
    @classmethod
    def validate_root_directory(cls, v: str) -> str:
        """Expand user home directory in path"""
        return os.path.expanduser(v)
    
    @field_validator("retry_delays")
    @classmethod
    def validate_retry_delays(cls, v: List[int]) -> List[int]:
        """Ensure all retry delays are positive"""
        if not v:
            raise ValueError("retry_delays cannot be empty")
        if any(delay <= 0 for delay in v):
            raise ValueError("All retry delays must be positive")
        return v


class DownloaderConfig(BaseSettings):
    """Video downloader (yt-dlp) configuration"""
    
    rate_limit: Optional[str] = Field(
        default=None,
        description="Download rate limit (e.g., '1M' for 1MB/s, None for unlimited)"
    )
    user_agent_rotation: bool = Field(
        default=True,
        description="Enable user agent rotation to avoid detection"
    )
    timeout: int = Field(
        default=300,
        ge=10,
        le=3600,
        description="Download timeout in seconds"
    )
    cookie_file: Optional[str] = Field(
        default=None,
        description="Path to cookie file for authenticated downloads"
    )
    
    model_config = SettingsConfigDict(
        env_prefix="VIDEO_SERVER_DOWNLOADER_",
        case_sensitive=False
    )
    
    @field_validator("cookie_file")
    @classmethod
    def validate_cookie_file(cls, v: Optional[str]) -> Optional[str]:
        """Expand user home directory in path if provided"""
        if v:
            return os.path.expanduser(v)
        return v


class AuthConfig(BaseSettings):
    """Authentication configuration for universal password protection"""
    
    enabled: bool = Field(
        default=False,
        description="Enable password authentication (protects all API endpoints)"
    )
    password_hash: Optional[str] = Field(
        default=None,
        description="Bcrypt hash of the universal access password (set via CLI: python manage.py auth set-password)"
    )
    session_timeout_hours: int = Field(
        default=24,
        ge=1,
        le=720,  # Max 30 days
        description="Session timeout in hours (how long before re-authentication is required)"
    )
    
    model_config = SettingsConfigDict(
        env_prefix="VIDEO_SERVER_AUTH_",
        case_sensitive=False
    )


class SecurityConfig(BaseSettings):
    """Security configuration"""
    
    api_keys: List[str] = Field(
        default_factory=list,
        description="List of valid API keys for authentication"
    )
    rate_limit_per_client: int = Field(
        default=100,
        ge=1,
        le=10000,
        description="Maximum requests per hour per client_id"
    )
    allowed_domains: List[str] = Field(
        default=["tiktok.com", "instagram.com"],
        description="Whitelisted domains for video downloads"
    )
    
    model_config = SettingsConfigDict(
        env_prefix="VIDEO_SERVER_SECURITY_",
        case_sensitive=False
    )


class LoggingConfig(BaseSettings):
    """Logging configuration"""
    
    level: str = Field(
        default="INFO",
        description="Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)"
    )
    file: str = Field(
        default="logs/server.log",
        description="Path to log file"
    )
    max_size: str = Field(
        default="10MB",
        description="Maximum log file size before rotation"
    )
    backup_count: int = Field(
        default=15,
        ge=0,
        le=100,
        description="Number of backup log files to keep"
    )
    
    model_config = SettingsConfigDict(
        env_prefix="VIDEO_SERVER_LOG_",
        case_sensitive=False
    )
    
    @field_validator("level")
    @classmethod
    def validate_level(cls, v: str) -> str:
        """Validate log level"""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        v_upper = v.upper()
        if v_upper not in valid_levels:
            raise ValueError(f"Log level must be one of {valid_levels}")
        return v_upper
    
    @field_validator("max_size")
    @classmethod
    def validate_max_size(cls, v: str) -> str:
        """Validate max_size format"""
        v_upper = v.upper()
        # Accept formats like "10MB", "100KB", "1GB"
        if not any(v_upper.endswith(suffix) for suffix in ["B", "KB", "MB", "GB"]):
            raise ValueError("max_size must end with B, KB, MB, or GB")
        # Extract number part
        try:
            number_part = v_upper.rstrip("KMGB")
            float(number_part)
        except ValueError:
            raise ValueError("max_size must start with a valid number")
        return v_upper
    
    def get_max_bytes(self) -> int:
        """Convert max_size to bytes"""
        max_size_upper = self.max_size.upper()
        number_part = max_size_upper.rstrip("KMGB")
        number = float(number_part)
        
        if max_size_upper.endswith("GB"):
            return int(number * 1024 * 1024 * 1024)
        elif max_size_upper.endswith("MB"):
            return int(number * 1024 * 1024)
        elif max_size_upper.endswith("KB"):
            return int(number * 1024)
        else:  # Bytes
            return int(number)


class Config(BaseSettings):
    """Main application configuration
    
    Loads configuration from:
    1. config.yaml file (if exists)
    2. Environment variables (VIDEO_SERVER_*)
    3. Default values
    
    Environment variables take precedence over config file.
    """
    
    server: ServerConfig = Field(default_factory=lambda: ServerConfig(_env_file=None))
    database: DatabaseConfig = Field(default_factory=lambda: DatabaseConfig(_env_file=None))
    downloads: DownloadsConfig = Field(default_factory=lambda: DownloadsConfig(_env_file=None))
    downloader: DownloaderConfig = Field(default_factory=lambda: DownloaderConfig(_env_file=None))
    auth: AuthConfig = Field(default_factory=lambda: AuthConfig(_env_file=None))
    security: SecurityConfig = Field(default_factory=lambda: SecurityConfig(_env_file=None))
    logging: LoggingConfig = Field(default_factory=lambda: LoggingConfig(_env_file=None))
    
    model_config = SettingsConfigDict(
        env_prefix="VIDEO_SERVER_",
        case_sensitive=False,
        env_nested_delimiter="__"
    )
    
    @classmethod
    def from_yaml(cls, config_path: str) -> "Config":
        """Load configuration from YAML file
        
        Args:
            config_path: Path to config.yaml file
            
        Returns:
            Config instance
            
        Raises:
            FileNotFoundError: If config file doesn't exist
            yaml.YAMLError: If config file is invalid
        """
        config_file = Path(config_path)
        
        if not config_file.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
        with open(config_file, 'r') as f:
            config_data = yaml.safe_load(f)
        
        if config_data is None:
            config_data = {}
        
        # Create nested config objects
        server_data = config_data.get('server', {})
        # Handle nested SSL config
        ssl_data = server_data.get('ssl', {})
        
        # Handle backwards compatibility: convert old 'host' to 'access_level'
        access_level = server_data.get('access_level')
        if not access_level and 'host' in server_data:
            # Old config format - convert host to access_level
            old_host = server_data.get('host', '0.0.0.0')
            if old_host == '127.0.0.1':
                access_level = 'localhost'
            else:
                access_level = 'local'  # Default to local for 0.0.0.0 or other values
        
        server_config = ServerConfig(
            access_level=access_level or 'local',
            port=server_data.get('port', 58443),
            ssl=SSLConfig(**ssl_data)
        )
        
        return cls(
            server=server_config,
            database=DatabaseConfig(**config_data.get('database', {})),
            downloads=DownloadsConfig(**config_data.get('downloads', {})),
            downloader=DownloaderConfig(**config_data.get('downloader', {})),
            auth=AuthConfig(**config_data.get('auth', {})),
            security=SecurityConfig(**config_data.get('security', {})),
            logging=LoggingConfig(**config_data.get('logging', {}))
        )
    
    @classmethod
    def load(cls, config_path: Optional[str] = None) -> "Config":
        """Load configuration with automatic fallback
        
        Tries to load from:
        1. Provided config_path
        2. config/config.yaml (default location)
        3. Environment variables only (if no file found)
        
        Args:
            config_path: Optional path to config file
            
        Returns:
            Config instance
        """
        # Try provided path first
        if config_path:
            try:
                return cls.from_yaml(config_path)
            except FileNotFoundError:
                raise
        
        # Try default location
        default_path = Path("config/config.yaml")
        if default_path.exists():
            return cls.from_yaml(str(default_path))
        
        # Fall back to environment variables and defaults
        return cls()
    
    def save_to_yaml(self, config_path: str):
        """Save current configuration to YAML file
        
        Args:
            config_path: Path where to save config.yaml
        """
        config_data = {
            'server': {
                'access_level': self.server.access_level,
                'port': self.server.port,
                'ssl': {
                    'enabled': self.server.ssl.enabled,
                    'domain': self.server.ssl.domain,
                    'use_letsencrypt': self.server.ssl.use_letsencrypt,
                    'letsencrypt_email': self.server.ssl.letsencrypt_email,
                    'cert_file': self.server.ssl.cert_file,
                    'key_file': self.server.ssl.key_file,
                },
            },
            'database': {
                'path': self.database.path,
            },
            'downloads': {
                'root_directory': self.downloads.root_directory,
                'max_concurrent': self.downloads.max_concurrent,
                'max_retries': self.downloads.max_retries,
                'retry_delays': self.downloads.retry_delays,
            },
            'downloader': {
                'rate_limit': self.downloader.rate_limit,
                'user_agent_rotation': self.downloader.user_agent_rotation,
                'timeout': self.downloader.timeout,
                'cookie_file': self.downloader.cookie_file,
            },
            'auth': {
                'enabled': self.auth.enabled,
                'password_hash': self.auth.password_hash,
                'session_timeout_hours': self.auth.session_timeout_hours,
            },
            'security': {
                'api_keys': self.security.api_keys,
                'rate_limit_per_client': self.security.rate_limit_per_client,
                'allowed_domains': self.security.allowed_domains,
            },
            'logging': {
                'level': self.logging.level,
                'file': self.logging.file,
                'max_size': self.logging.max_size,
                'backup_count': self.logging.backup_count,
            }
        }
        
        config_file = Path(config_path)
        config_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(config_file, 'w') as f:
            yaml.dump(config_data, f, default_flow_style=False, sort_keys=False)
    
    def validate_paths(self) -> List[str]:
        """Validate that required directories and files exist
        
        Returns:
            List of validation errors (empty if all valid)
        """
        errors = []
        
        # Check database directory
        db_dir = Path(self.database.path).parent
        if not db_dir.exists():
            try:
                db_dir.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                errors.append(f"Cannot create database directory: {e}")
        
        # Check downloads root directory
        download_dir = Path(self.downloads.root_directory)
        if not download_dir.exists():
            try:
                download_dir.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                errors.append(f"Cannot create downloads root directory: {e}")
        
        # Check log directory
        log_dir = Path(self.logging.file).parent
        if not log_dir.exists():
            try:
                log_dir.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                errors.append(f"Cannot create log directory: {e}")
        
        # Check SSL files (only if SSL is enabled)
        if self.server.ssl.enabled:
            if not self.server.ssl.use_letsencrypt:
                # Manual SSL certificates
                cert_file = Path(self.server.ssl.cert_file)
                key_file = Path(self.server.ssl.key_file)
                if not cert_file.exists():
                    errors.append(f"SSL certificate not found: {self.server.ssl.cert_file} (run ./scripts/generate_selfsigned.sh or use Let's Encrypt)")
                if not key_file.exists():
                    errors.append(f"SSL key not found: {self.server.ssl.key_file} (run ./scripts/generate_selfsigned.sh or use Let's Encrypt)")
            else:
                # Using Let's Encrypt - verify domain is set
                if self.server.ssl.domain:
                    from app.utils.cert_utils import get_letsencrypt_paths
                    cert_path, key_path = get_letsencrypt_paths(self.server.ssl.domain)
                    if not Path(cert_path).exists():
                        errors.append(f"Let's Encrypt certificate not found for {self.server.ssl.domain}. Run: sudo ./scripts/setup_letsencrypt.sh {self.server.ssl.domain} {self.server.ssl.letsencrypt_email}")
                else:
                    errors.append("ssl.domain is required when ssl.use_letsencrypt is True")
        
        # Check cookie file if specified
        if self.downloader.cookie_file:
            cookie_file = Path(self.downloader.cookie_file)
            if not cookie_file.exists():
                errors.append(f"Cookie file not found: {self.downloader.cookie_file}")
        
        return errors


# Global configuration instance
_config: Optional[Config] = None


def get_config(config_path: Optional[str] = None, reload: bool = False) -> Config:
    """Get global configuration instance
    
    Args:
        config_path: Optional path to config file
        reload: Force reload configuration
        
    Returns:
        Config instance
    """
    global _config
    
    if _config is None or reload:
        _config = Config.load(config_path)
    
    return _config


def set_config(config: Config):
    """Set global configuration instance (mainly for testing)
    
    Args:
        config: Config instance to set
    """
    global _config
    _config = config

