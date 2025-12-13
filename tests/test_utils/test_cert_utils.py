"""Unit Tests for Certificate Utilities

Tests certificate validation, expiry checking, and Let's Encrypt path management.
"""

import pytest
import tempfile
import os
from pathlib import Path
from datetime import datetime, timedelta
import subprocess

from app.utils.cert_utils import (
    get_letsencrypt_paths,
    check_certificate_exists,
    get_certificate_expiry,
    check_certificate_expiry,
    validate_certificate,
    is_certbot_installed,
    get_certificate_info,
)


class TestLetsEncryptPaths:
    """Test Let's Encrypt path utilities"""
    
    def test_get_letsencrypt_paths(self):
        """Test getting Let's Encrypt certificate paths"""
        domain = "example.com"
        cert_path, key_path = get_letsencrypt_paths(domain)
        
        assert cert_path == "/etc/letsencrypt/live/example.com/fullchain.pem"
        assert key_path == "/etc/letsencrypt/live/example.com/privkey.pem"
    
    def test_get_letsencrypt_paths_subdomain(self):
        """Test paths for subdomain"""
        domain = "video.example.com"
        cert_path, key_path = get_letsencrypt_paths(domain)
        
        assert cert_path == "/etc/letsencrypt/live/video.example.com/fullchain.pem"
        assert key_path == "/etc/letsencrypt/live/video.example.com/privkey.pem"


class TestCertificateExistence:
    """Test certificate existence checking"""
    
    def test_check_nonexistent_certificates(self):
        """Test checking nonexistent certificates"""
        result = check_certificate_exists("/nonexistent/cert.pem", "/nonexistent/key.pem")
        assert result is False
    
    def test_check_existing_certificates(self, tmp_path):
        """Test checking existing certificates"""
        cert_file = tmp_path / "cert.pem"
        key_file = tmp_path / "key.pem"
        
        cert_file.touch()
        key_file.touch()
        
        result = check_certificate_exists(str(cert_file), str(key_file))
        assert result is True
    
    def test_check_partial_certificates(self, tmp_path):
        """Test when only one file exists"""
        cert_file = tmp_path / "cert.pem"
        key_file = tmp_path / "key.pem"
        
        cert_file.touch()  # Only create cert
        
        result = check_certificate_exists(str(cert_file), str(key_file))
        assert result is False


class TestCertbotDetection:
    """Test certbot installation detection"""
    
    def test_certbot_detection(self):
        """Test certbot detection (may be installed or not)"""
        result = is_certbot_installed()
        # Result depends on system, just check it's boolean
        assert isinstance(result, bool)


class TestCertificateInfo:
    """Test certificate information extraction"""
    
    def test_get_info_nonexistent_cert(self):
        """Test getting info for nonexistent certificate"""
        info = get_certificate_info("/nonexistent/cert.pem")
        
        assert info["exists"] is False
        assert info["valid"] is False
        assert info["subject"] is None
        assert info["issuer"] is None
    
    def test_check_certificate_expiry_nonexistent(self):
        """Test checking expiry of nonexistent certificate"""
        needs_renewal, days, message = check_certificate_expiry("/nonexistent/cert.pem")
        
        assert needs_renewal is True
        assert days is None
        assert "not found" in message.lower()


class TestCertificateValidation:
    """Test certificate validation"""
    
    def test_validate_nonexistent_certificates(self):
        """Test validation of nonexistent certificates"""
        is_valid, message = validate_certificate(
            "/nonexistent/cert.pem",
            "/nonexistent/key.pem"
        )
        
        assert is_valid is False
        assert "not found" in message.lower()


class TestGeneratedCertificate:
    """Test with actual self-signed certificate"""
    
    @pytest.fixture
    def self_signed_cert(self, tmp_path):
        """Generate a self-signed certificate for testing"""
        cert_file = tmp_path / "test.crt"
        key_file = tmp_path / "test.key"
        
        # Generate key
        subprocess.run(
            ["openssl", "genrsa", "-out", str(key_file), "2048"],
            capture_output=True,
            check=True
        )
        
        # Generate certificate (valid for 365 days)
        subprocess.run([
            "openssl", "req", "-new", "-x509",
            "-key", str(key_file),
            "-out", str(cert_file),
            "-days", "365",
            "-subj", "/CN=test.example.com"
        ], capture_output=True, check=True)
        
        return str(cert_file), str(key_file)
    
    def test_certificate_exists(self, self_signed_cert):
        """Test that generated certificate exists"""
        cert_path, key_path = self_signed_cert
        assert check_certificate_exists(cert_path, key_path) is True
    
    def test_get_certificate_expiry(self, self_signed_cert):
        """Test getting certificate expiry date"""
        cert_path, _ = self_signed_cert
        expiry = get_certificate_expiry(cert_path)
        
        assert expiry is not None
        assert isinstance(expiry, datetime)
        # Should expire in roughly 365 days
        days_until_expiry = (expiry - datetime.utcnow()).days
        assert 360 < days_until_expiry < 370
    
    def test_check_certificate_expiry_valid(self, self_signed_cert):
        """Test checking expiry of valid certificate"""
        cert_path, _ = self_signed_cert
        needs_renewal, days, message = check_certificate_expiry(cert_path)
        
        assert needs_renewal is False  # Should not need renewal
        assert days > 300  # Should have many days left
        assert "valid" in message.lower()
    
    def test_validate_certificate_success(self, self_signed_cert):
        """Test successful certificate validation"""
        cert_path, key_path = self_signed_cert
        is_valid, message = validate_certificate(cert_path, key_path)
        
        assert is_valid is True
        assert "successful" in message.lower()
    
    def test_validate_certificate_with_domain(self, self_signed_cert):
        """Test certificate validation with domain check"""
        cert_path, key_path = self_signed_cert
        
        # Should match (certificate was created for test.example.com)
        is_valid, message = validate_certificate(
            cert_path, key_path, domain="test.example.com"
        )
        assert is_valid is True
        
        # Should not match
        is_valid, message = validate_certificate(
            cert_path, key_path, domain="wrong.example.com"
        )
        assert is_valid is False
        assert "not for domain" in message.lower()
    
    def test_get_certificate_info_valid(self, self_signed_cert):
        """Test getting info from valid certificate"""
        cert_path, _ = self_signed_cert
        info = get_certificate_info(cert_path)
        
        assert info["exists"] is True
        assert info["valid"] is True
        assert info["subject"] is not None
        assert "test.example.com" in info["subject"].lower()
        assert info["issuer"] is not None
        assert info["expiry"] is not None
        assert info["days_remaining"] is not None
        assert info["days_remaining"] > 300
        assert info["needs_renewal"] is False


class TestCertificateExpiry:
    """Test certificate expiry edge cases"""
    
    @pytest.fixture
    def expiring_cert(self, tmp_path):
        """Generate a certificate expiring in 20 days"""
        cert_file = tmp_path / "expiring.crt"
        key_file = tmp_path / "expiring.key"
        
        # Generate key
        subprocess.run(
            ["openssl", "genrsa", "-out", str(key_file), "2048"],
            capture_output=True,
            check=True
        )
        
        # Generate certificate valid for only 20 days
        subprocess.run([
            "openssl", "req", "-new", "-x509",
            "-key", str(key_file),
            "-out", str(cert_file),
            "-days", "20",
            "-subj", "/CN=expiring.example.com"
        ], capture_output=True, check=True)
        
        return str(cert_file), str(key_file)
    
    def test_expiring_certificate_warning(self, expiring_cert):
        """Test that expiring certificate triggers warning"""
        cert_path, _ = expiring_cert
        needs_renewal, days, message = check_certificate_expiry(cert_path, days_warning=30)
        
        assert needs_renewal is True  # Should need renewal (< 30 days)
        assert days is not None
        assert days < 30
        assert "expires in" in message.lower()
    
    def test_certificate_info_needs_renewal(self, expiring_cert):
        """Test that certificate info shows needs renewal"""
        cert_path, _ = expiring_cert
        info = get_certificate_info(cert_path)
        
        assert info["exists"] is True
        assert info["valid"] is True
        assert info["days_remaining"] < 30
        assert info["needs_renewal"] is True


class TestMismatchedCertificates:
    """Test validation with mismatched cert and key"""
    
    def test_mismatched_cert_key(self, tmp_path):
        """Test validation fails with mismatched certificate and key"""
        cert_file1 = tmp_path / "cert1.crt"
        key_file1 = tmp_path / "key1.key"
        cert_file2 = tmp_path / "cert2.crt"
        key_file2 = tmp_path / "key2.key"
        
        # Generate first pair
        subprocess.run(
            ["openssl", "genrsa", "-out", str(key_file1), "2048"],
            capture_output=True,
            check=True
        )
        subprocess.run([
            "openssl", "req", "-new", "-x509",
            "-key", str(key_file1),
            "-out", str(cert_file1),
            "-days", "365",
            "-subj", "/CN=test1.example.com"
        ], capture_output=True, check=True)
        
        # Generate second pair
        subprocess.run(
            ["openssl", "genrsa", "-out", str(key_file2), "2048"],
            capture_output=True,
            check=True
        )
        subprocess.run([
            "openssl", "req", "-new", "-x509",
            "-key", str(key_file2),
            "-out", str(cert_file2),
            "-days", "365",
            "-subj", "/CN=test2.example.com"
        ], capture_output=True, check=True)
        
        # Try to validate mismatched pair (cert1 with key2)
        is_valid, message = validate_certificate(str(cert_file1), str(key_file2))
        
        assert is_valid is False
        assert "do not match" in message.lower()

