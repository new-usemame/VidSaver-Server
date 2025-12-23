"""Unit Tests for Configuration System

Tests configuration loading, validation, environment variable overrides,
and Pydantic model validation.
"""

import pytest
import os
import tempfile
import yaml
from pathlib import Path

from app.core.config import (
    Config,
    ServerConfig,
    DatabaseConfig,
    DownloadsConfig,
    DownloaderConfig,
    SecurityConfig,
    LoggingConfig,
    get_config,
    set_config,
)


class TestServerConfig:
    """Test ServerConfig model"""
    
    def test_default_values(self):
        """Test default server configuration"""
        config = ServerConfig()
        
        assert config.access_level == "local"
        assert config.host == "0.0.0.0"  # resolved from access_level
        assert config.port == 58443
        assert config.ssl.cert_file == "certs/server.crt"
        assert config.ssl.key_file == "certs/server.key"
    
    def test_custom_values(self):
        """Test custom server configuration"""
        from app.core.config import SSLConfig
        config = ServerConfig(
            access_level="localhost",
            port=9443,
            ssl=SSLConfig(
                cert_file="custom/cert.crt",
                key_file="custom/key.key"
            )
        )
        
        assert config.access_level == "localhost"
        assert config.host == "127.0.0.1"  # resolved from access_level
        assert config.port == 9443
        assert config.ssl.cert_file == "custom/cert.crt"
        assert config.ssl.key_file == "custom/key.key"
    
    def test_port_validation(self):
        """Test port number validation"""
        # Valid ports
        ServerConfig(port=1)
        ServerConfig(port=8080)
        ServerConfig(port=65535)
        
        # Invalid ports
        with pytest.raises(ValueError):
            ServerConfig(port=0)
        with pytest.raises(ValueError):
            ServerConfig(port=65536)
        with pytest.raises(ValueError):
            ServerConfig(port=-1)


class TestDatabaseConfig:
    """Test DatabaseConfig model"""
    
    def test_default_values(self):
        """Test default database configuration"""
        config = DatabaseConfig()
        assert config.path == "data/downloads.db"
    
    def test_path_expansion(self):
        """Test home directory expansion"""
        config = DatabaseConfig(path="~/test/db.sqlite")
        assert "~" not in config.path
        assert config.path.startswith(os.path.expanduser("~"))


class TestDownloadsConfig:
    """Test DownloadsConfig model"""
    
    def test_default_values(self):
        """Test default downloads configuration"""
        config = DownloadsConfig()
        
        assert "~" not in config.root_directory  # Should be expanded
        assert config.max_concurrent == 1
        assert config.max_retries == 3
        assert config.retry_delays == [60, 300, 900]
    
    def test_max_concurrent_validation(self):
        """Test max_concurrent validation"""
        DownloadsConfig(max_concurrent=1)
        DownloadsConfig(max_concurrent=10)
        
        with pytest.raises(ValueError):
            DownloadsConfig(max_concurrent=0)
        with pytest.raises(ValueError):
            DownloadsConfig(max_concurrent=11)
    
    def test_max_retries_validation(self):
        """Test max_retries validation"""
        DownloadsConfig(max_retries=0)
        DownloadsConfig(max_retries=10)
        
        with pytest.raises(ValueError):
            DownloadsConfig(max_retries=-1)
        with pytest.raises(ValueError):
            DownloadsConfig(max_retries=11)
    
    def test_retry_delays_validation(self):
        """Test retry_delays validation"""
        # Valid
        DownloadsConfig(retry_delays=[10, 20, 30])
        
        # Empty list not allowed
        with pytest.raises(ValueError, match="cannot be empty"):
            DownloadsConfig(retry_delays=[])
        
        # Negative values not allowed
        with pytest.raises(ValueError, match="must be positive"):
            DownloadsConfig(retry_delays=[10, -20, 30])
        
        # Zero not allowed
        with pytest.raises(ValueError, match="must be positive"):
            DownloadsConfig(retry_delays=[0, 20, 30])


class TestDownloaderConfig:
    """Test DownloaderConfig model"""
    
    def test_default_values(self):
        """Test default downloader configuration"""
        config = DownloaderConfig()
        
        assert config.rate_limit is None
        assert config.user_agent_rotation is True
        assert config.timeout == 300
        assert config.cookie_file is None
    
    def test_timeout_validation(self):
        """Test timeout validation"""
        DownloaderConfig(timeout=10)
        DownloaderConfig(timeout=3600)
        
        with pytest.raises(ValueError):
            DownloaderConfig(timeout=9)
        with pytest.raises(ValueError):
            DownloaderConfig(timeout=3601)
    
    def test_cookie_file_expansion(self):
        """Test cookie file path expansion"""
        config = DownloaderConfig(cookie_file="~/cookies.txt")
        assert "~" not in config.cookie_file
        assert config.cookie_file.startswith(os.path.expanduser("~"))
    
    def test_optional_fields(self):
        """Test optional fields"""
        config = DownloaderConfig(rate_limit="1M", cookie_file="/path/to/cookies.txt")
        assert config.rate_limit == "1M"
        assert config.cookie_file == "/path/to/cookies.txt"


class TestSecurityConfig:
    """Test SecurityConfig model"""
    
    def test_default_values(self):
        """Test default security configuration"""
        config = SecurityConfig()
        
        assert config.api_keys == []
        assert config.rate_limit_per_client == 100
        assert config.allowed_domains == ["tiktok.com", "instagram.com"]
    
    def test_custom_api_keys(self):
        """Test custom API keys"""
        config = SecurityConfig(api_keys=["key1", "key2", "key3"])
        assert len(config.api_keys) == 3
        assert "key1" in config.api_keys
    
    def test_rate_limit_validation(self):
        """Test rate limit validation"""
        SecurityConfig(rate_limit_per_client=1)
        SecurityConfig(rate_limit_per_client=10000)
        
        with pytest.raises(ValueError):
            SecurityConfig(rate_limit_per_client=0)
        with pytest.raises(ValueError):
            SecurityConfig(rate_limit_per_client=10001)


class TestLoggingConfig:
    """Test LoggingConfig model"""
    
    def test_default_values(self):
        """Test default logging configuration"""
        config = LoggingConfig()
        
        assert config.level == "INFO"
        assert config.file == "logs/server.log"
        assert config.max_size == "10MB"
        assert config.backup_count == 15
    
    def test_log_level_validation(self):
        """Test log level validation"""
        # Valid levels
        for level in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
            config = LoggingConfig(level=level)
            assert config.level == level
        
        # Case insensitive
        config = LoggingConfig(level="debug")
        assert config.level == "DEBUG"
        
        # Invalid level
        with pytest.raises(ValueError, match="must be one of"):
            LoggingConfig(level="INVALID")
    
    def test_max_size_validation(self):
        """Test max_size validation"""
        # Valid sizes
        LoggingConfig(max_size="10B")
        LoggingConfig(max_size="100KB")
        LoggingConfig(max_size="50MB")
        LoggingConfig(max_size="1GB")
        
        # Case insensitive
        config = LoggingConfig(max_size="10mb")
        assert config.max_size == "10MB"
        
        # Invalid format
        with pytest.raises(ValueError):
            LoggingConfig(max_size="10")
        with pytest.raises(ValueError):
            LoggingConfig(max_size="10TB")
        with pytest.raises(ValueError):
            LoggingConfig(max_size="invalid")
    
    def test_get_max_bytes(self):
        """Test converting max_size to bytes"""
        config = LoggingConfig(max_size="10B")
        assert config.get_max_bytes() == 10
        
        config = LoggingConfig(max_size="5KB")
        assert config.get_max_bytes() == 5 * 1024
        
        config = LoggingConfig(max_size="10MB")
        assert config.get_max_bytes() == 10 * 1024 * 1024
        
        config = LoggingConfig(max_size="2GB")
        assert config.get_max_bytes() == 2 * 1024 * 1024 * 1024
    
    def test_backup_count_validation(self):
        """Test backup_count validation"""
        LoggingConfig(backup_count=0)
        LoggingConfig(backup_count=100)
        
        with pytest.raises(ValueError):
            LoggingConfig(backup_count=-1)
        with pytest.raises(ValueError):
            LoggingConfig(backup_count=101)


class TestConfigLoading:
    """Test Config loading from various sources"""
    
    def test_default_config(self):
        """Test loading default configuration"""
        config = Config()
        
        assert config.server.port == 58443
        assert config.database.path == "data/downloads.db"
        assert config.downloads.max_concurrent == 1
        assert config.logging.level == "INFO"
    
    def test_load_from_yaml(self):
        """Test loading configuration from YAML file"""
        # Create temporary YAML config
        config_data = {
            'server': {
                'access_level': 'localhost',
                'port': 9443,
            },
            'database': {
                'path': '/tmp/test.db',
            },
            'logging': {
                'level': 'DEBUG',
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            config_path = f.name
        
        try:
            config = Config.from_yaml(config_path)
            
            assert config.server.access_level == "localhost"
            assert config.server.host == "127.0.0.1"  # resolved from access_level
            assert config.server.port == 9443
            assert config.database.path == "/tmp/test.db"
            assert config.logging.level == "DEBUG"
            
            # Unspecified values should use defaults
            assert config.server.ssl.cert_file == "certs/server.crt"
            assert config.downloads.max_concurrent == 1
        finally:
            os.unlink(config_path)
    
    def test_load_from_yaml_empty_file(self):
        """Test loading from empty YAML file"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("")  # Empty file
            config_path = f.name
        
        try:
            config = Config.from_yaml(config_path)
            # Should use all defaults
            assert config.server.port == 58443
        finally:
            os.unlink(config_path)
    
    def test_load_from_nonexistent_file(self):
        """Test loading from non-existent file"""
        with pytest.raises(FileNotFoundError):
            Config.from_yaml("/nonexistent/config.yaml")
    
    def test_load_with_fallback(self):
        """Test Config.load() with fallback logic"""
        # No config file exists, should use defaults
        config = Config.load()
        assert config.server.port == 58443
    
    def test_save_to_yaml(self):
        """Test saving configuration to YAML file"""
        config = Config(
            server=ServerConfig(access_level="local", port=9000),
            logging=LoggingConfig(level="DEBUG")
        )
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            config_path = f.name
        
        try:
            config.save_to_yaml(config_path)
            
            # Load it back
            loaded_config = Config.from_yaml(config_path)
            
            assert loaded_config.server.access_level == "local"
            assert loaded_config.server.port == 9000
            assert loaded_config.logging.level == "DEBUG"
        finally:
            os.unlink(config_path)


class TestConfigValidation:
    """Test configuration validation"""
    
    def test_validate_paths_success(self, tmp_path):
        """Test path validation when directories can be created"""
        from app.core.config import SSLConfig
        config = Config(
            server=ServerConfig(
                ssl=SSLConfig(
                    enabled=True,  # Enable SSL to trigger validation
                    use_letsencrypt=False,
                    cert_file=str(tmp_path / "nonexistent_cert.pem"),
                    key_file=str(tmp_path / "nonexistent_key.pem")
                )
            ),
            database=DatabaseConfig(path=str(tmp_path / "test.db")),
            downloads=DownloadsConfig(root_directory=str(tmp_path / "downloads")),
            logging=LoggingConfig(file=str(tmp_path / "logs" / "test.log"))
        )
        
        errors = config.validate_paths()
        
        # Should create directories successfully
        # SSL cert warnings are expected when not using Let's Encrypt
        ssl_errors = [e for e in errors if "SSL" in e or "certificate" in e or "key" in e]
        other_errors = [e for e in errors if e not in ssl_errors]
        
        assert len(other_errors) == 0
        assert len(ssl_errors) == 2  # cert and key warnings
    
    def test_validate_paths_missing_ssl(self):
        """Test validation reports missing SSL files"""
        from app.core.config import SSLConfig
        config = Config(
            server=ServerConfig(
                ssl=SSLConfig(
                    enabled=True,  # Enable SSL to trigger validation
                    use_letsencrypt=False,
                    cert_file="/nonexistent/path/cert.pem",
                    key_file="/nonexistent/path/key.pem"
                )
            )
        )
        errors = config.validate_paths()
        
        # Should warn about missing SSL files when not using Let's Encrypt
        ssl_errors = [e for e in errors if "certificate" in e or "key" in e]
        assert len(ssl_errors) >= 1


class TestGlobalConfig:
    """Test global configuration singleton"""
    
    def test_get_config(self):
        """Test getting global config instance"""
        config1 = get_config()
        config2 = get_config()
        
        # Should return same instance
        assert config1 is config2
    
    def test_get_config_reload(self):
        """Test reloading global config"""
        config1 = get_config()
        config2 = get_config(reload=True)
        
        # Should create new instance
        assert config1 is not config2
    
    def test_set_config(self):
        """Test setting global config instance"""
        custom_config = Config(server=ServerConfig(port=9999))
        set_config(custom_config)
        
        retrieved_config = get_config()
        assert retrieved_config.server.port == 9999
        
        # Reset for other tests
        set_config(Config())


class TestEnvironmentVariables:
    """Test environment variable overrides"""
    
    def test_env_var_override(self, monkeypatch):
        """Test that environment variables override config values"""
        # ServerConfig uses VIDEO_SERVER_SERVER_ prefix, so port is VIDEO_SERVER_SERVER_PORT
        monkeypatch.setenv("VIDEO_SERVER_SERVER_PORT", "9999")
        
        # Create ServerConfig directly - it should read env vars
        server_config = ServerConfig()
        assert server_config.port == 9999
        
        # Test with logging (LoggingConfig uses VIDEO_SERVER_LOG_ prefix)
        monkeypatch.setenv("VIDEO_SERVER_LOG_LEVEL", "DEBUG")
        logging_config = LoggingConfig()
        assert logging_config.level == "DEBUG"
    
    def test_nested_env_var(self, monkeypatch):
        """Test nested environment variable override"""
        monkeypatch.setenv("VIDEO_SERVER_DOWNLOADS_MAX_CONCURRENT", "5")
        
        config = Config()
        
        assert config.downloads.max_concurrent == 5


class TestEdgeCases:
    """Test edge cases and error handling"""
    
    def test_invalid_yaml_syntax(self):
        """Test handling of invalid YAML syntax"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("invalid: yaml: syntax: here:")
            config_path = f.name
        
        try:
            with pytest.raises(yaml.YAMLError):
                Config.from_yaml(config_path)
        finally:
            os.unlink(config_path)
    
    def test_invalid_config_values(self):
        """Test validation of invalid configuration values"""
        config_data = {
            'server': {'port': 99999},  # Invalid port
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            config_path = f.name
        
        try:
            with pytest.raises(ValueError):
                Config.from_yaml(config_path)
        finally:
            os.unlink(config_path)
    
    def test_partial_config(self):
        """Test loading partial configuration (some sections missing)"""
        config_data = {
            'server': {
                'port': 9443,
            }
            # Other sections missing
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            config_path = f.name
        
        try:
            config = Config.from_yaml(config_path)
            
            # Specified values
            assert config.server.port == 9443
            
            # Missing sections should use defaults
            assert config.database.path == "data/downloads.db"
            assert config.logging.level == "INFO"
        finally:
            os.unlink(config_path)

