"""Certificate Utilities

Provides utilities for SSL/TLS certificate validation, expiry checking,
and Let's Encrypt path management.
"""

import os
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Tuple
import subprocess


def get_letsencrypt_paths(domain: str) -> Tuple[str, str]:
    """Get Let's Encrypt certificate paths for a domain
    
    Args:
        domain: Domain name
        
    Returns:
        Tuple of (cert_path, key_path)
    """
    cert_path = f"/etc/letsencrypt/live/{domain}/fullchain.pem"
    key_path = f"/etc/letsencrypt/live/{domain}/privkey.pem"
    return cert_path, key_path


def check_certificate_exists(cert_path: str, key_path: str) -> bool:
    """Check if certificate and key files exist
    
    Args:
        cert_path: Path to certificate file
        key_path: Path to private key file
        
    Returns:
        True if both files exist
    """
    cert_file = Path(cert_path)
    key_file = Path(key_path)
    return cert_file.exists() and key_file.exists()


def get_certificate_expiry(cert_path: str) -> Optional[datetime]:
    """Get certificate expiration date
    
    Args:
        cert_path: Path to certificate file
        
    Returns:
        Datetime of expiration, or None if cannot be determined
    """
    try:
        result = subprocess.run(
            ["openssl", "x509", "-enddate", "-noout", "-in", cert_path],
            capture_output=True,
            text=True,
            check=True
        )
        
        # Output format: "notAfter=Dec 31 23:59:59 2025 GMT"
        date_str = result.stdout.strip().split("=")[1]
        expiry = datetime.strptime(date_str, "%b %d %H:%M:%S %Y %Z")
        return expiry
        
    except (subprocess.CalledProcessError, IndexError, ValueError):
        return None


def check_certificate_expiry(cert_path: str, days_warning: int = 30) -> Tuple[bool, Optional[int], Optional[str]]:
    """Check if certificate is expiring soon
    
    Args:
        cert_path: Path to certificate file
        days_warning: Number of days before expiry to warn (default: 30)
        
    Returns:
        Tuple of (needs_renewal, days_remaining, message)
    """
    if not Path(cert_path).exists():
        return True, None, "Certificate file not found"
    
    expiry = get_certificate_expiry(cert_path)
    if not expiry:
        return False, None, "Cannot determine certificate expiry"
    
    now = datetime.utcnow()
    days_remaining = (expiry - now).days
    
    if days_remaining < 0:
        return True, days_remaining, f"Certificate expired {abs(days_remaining)} days ago"
    elif days_remaining < days_warning:
        return True, days_remaining, f"Certificate expires in {days_remaining} days (renewal recommended)"
    else:
        return False, days_remaining, f"Certificate valid for {days_remaining} more days"


def validate_certificate(cert_path: str, key_path: str, domain: Optional[str] = None) -> Tuple[bool, str]:
    """Validate certificate and key match, and optionally check domain
    
    Args:
        cert_path: Path to certificate file
        key_path: Path to private key file
        domain: Optional domain to validate against
        
    Returns:
        Tuple of (is_valid, message)
    """
    # Check files exist
    if not check_certificate_exists(cert_path, key_path):
        return False, "Certificate or key file not found"
    
    try:
        # Get certificate modulus
        cert_result = subprocess.run(
            ["openssl", "x509", "-noout", "-modulus", "-in", cert_path],
            capture_output=True,
            text=True,
            check=True
        )
        cert_modulus = cert_result.stdout.strip()
        
        # Get key modulus
        key_result = subprocess.run(
            ["openssl", "rsa", "-noout", "-modulus", "-in", key_path],
            capture_output=True,
            text=True,
            check=True
        )
        key_modulus = key_result.stdout.strip()
        
        # Compare moduli
        if cert_modulus != key_modulus:
            return False, "Certificate and key do not match"
        
        # Check domain if provided
        if domain:
            subject_result = subprocess.run(
                ["openssl", "x509", "-noout", "-subject", "-in", cert_path],
                capture_output=True,
                text=True,
                check=True
            )
            subject = subject_result.stdout.strip()
            
            if domain.lower() not in subject.lower():
                return False, f"Certificate is not for domain '{domain}'"
        
        return True, "Certificate validation successful"
        
    except subprocess.CalledProcessError as e:
        return False, f"Validation error: {e}"


def is_certbot_installed() -> bool:
    """Check if certbot is installed
    
    Returns:
        True if certbot is available
    """
    try:
        subprocess.run(
            ["certbot", "--version"],
            capture_output=True,
            check=True
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def get_certificate_info(cert_path: str) -> dict:
    """Get detailed certificate information
    
    Args:
        cert_path: Path to certificate file
        
    Returns:
        Dictionary with certificate information
    """
    info = {
        "exists": False,
        "valid": False,
        "subject": None,
        "issuer": None,
        "expiry": None,
        "days_remaining": None,
        "needs_renewal": False,
    }
    
    if not Path(cert_path).exists():
        return info
    
    info["exists"] = True
    
    try:
        # Get subject
        result = subprocess.run(
            ["openssl", "x509", "-noout", "-subject", "-in", cert_path],
            capture_output=True,
            text=True,
            check=True
        )
        info["subject"] = result.stdout.strip().split("=", 1)[1] if "=" in result.stdout else result.stdout.strip()
        
        # Get issuer
        result = subprocess.run(
            ["openssl", "x509", "-noout", "-issuer", "-in", cert_path],
            capture_output=True,
            text=True,
            check=True
        )
        info["issuer"] = result.stdout.strip().split("=", 1)[1] if "=" in result.stdout else result.stdout.strip()
        
        # Get expiry
        expiry = get_certificate_expiry(cert_path)
        if expiry:
            info["expiry"] = expiry
            days_remaining = (expiry - datetime.utcnow()).days
            info["days_remaining"] = days_remaining
            info["needs_renewal"] = days_remaining < 30
        
        info["valid"] = True
        
    except subprocess.CalledProcessError:
        pass
    
    return info

