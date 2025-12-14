"""Network Detection Service

Detects LAN and WAN IP addresses for server connection configuration.
Used for QR code setup and automatic client configuration.
"""

import logging
import socket
import time
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import requests

logger = logging.getLogger(__name__)


class NetworkService:
    """Service for detecting network configuration
    
    Features:
    - Automatic LAN IP detection
    - WAN/Public IP detection via external service
    - IP caching with TTL to reduce external calls
    - Graceful error handling
    """
    
    # Cache configuration
    WAN_IP_CACHE_TTL = 300  # 5 minutes
    WAN_IP_SERVICES = [
        'https://api.ipify.org?format=json',
        'https://ifconfig.me/ip',
        'https://icanhazip.com',
    ]
    
    def __init__(self):
        """Initialize network service"""
        self._wan_ip_cache: Optional[str] = None
        self._wan_ip_cache_time: Optional[datetime] = None
        self._lan_ip_cache: Optional[str] = None
    
    async def get_lan_ip(self) -> str:
        """Get local area network (LAN) IP address
        
        Returns:
            LAN IP address as string (e.g., "192.168.1.100")
            Returns "127.0.0.1" if detection fails
        """
        # Return cached value if available
        if self._lan_ip_cache:
            return self._lan_ip_cache
        
        try:
            # Method 1: Connect to external address (doesn't actually send data)
            # This gets the local IP that would be used for internet connections
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.settimeout(0.1)
            try:
                # Connect to Google DNS (doesn't send any data)
                s.connect(('8.8.8.8', 80))
                lan_ip = s.getsockname()[0]
                self._lan_ip_cache = lan_ip
                logger.info(f"Detected LAN IP: {lan_ip}")
                return lan_ip
            finally:
                s.close()
        
        except Exception as e:
            logger.warning(f"Method 1 failed to detect LAN IP: {e}")
        
        try:
            # Method 2: Get hostname and resolve it
            hostname = socket.gethostname()
            lan_ip = socket.gethostbyname(hostname)
            
            # Avoid 127.0.0.1 if possible
            if lan_ip != "127.0.0.1":
                self._lan_ip_cache = lan_ip
                logger.info(f"Detected LAN IP via hostname: {lan_ip}")
                return lan_ip
        
        except Exception as e:
            logger.warning(f"Method 2 failed to detect LAN IP: {e}")
        
        # Fallback to localhost
        logger.warning("Could not detect LAN IP, using localhost")
        return "127.0.0.1"
    
    async def get_wan_ip(self, use_cache: bool = True) -> Optional[str]:
        """Get wide area network (WAN/Public) IP address
        
        Uses external services to detect public IP. Results are cached
        to avoid excessive external calls.
        
        Args:
            use_cache: If True, use cached value if available
            
        Returns:
            WAN IP address as string (e.g., "68.186.221.57")
            Returns None if detection fails or server is not publicly accessible
        """
        # Check cache
        if use_cache and self._wan_ip_cache and self._wan_ip_cache_time:
            cache_age = datetime.now() - self._wan_ip_cache_time
            if cache_age < timedelta(seconds=self.WAN_IP_CACHE_TTL):
                logger.debug(f"Using cached WAN IP: {self._wan_ip_cache}")
                return self._wan_ip_cache
        
        # Try each service until one works
        for service_url in self.WAN_IP_SERVICES:
            try:
                logger.debug(f"Attempting to get WAN IP from: {service_url}")
                response = requests.get(service_url, timeout=5)
                
                if response.status_code == 200:
                    # Handle JSON response (ipify)
                    if 'json' in response.headers.get('content-type', ''):
                        wan_ip = response.json().get('ip', '').strip()
                    else:
                        # Handle plain text response
                        wan_ip = response.text.strip()
                    
                    # Validate it looks like an IP
                    if self._is_valid_ip(wan_ip):
                        self._wan_ip_cache = wan_ip
                        self._wan_ip_cache_time = datetime.now()
                        logger.info(f"Detected WAN IP: {wan_ip} (via {service_url})")
                        return wan_ip
            
            except requests.RequestException as e:
                logger.debug(f"Failed to get WAN IP from {service_url}: {e}")
                continue
            
            except Exception as e:
                logger.debug(f"Unexpected error getting WAN IP from {service_url}: {e}")
                continue
        
        # All services failed
        logger.warning("Could not detect WAN IP from any service")
        return None
    
    def _is_valid_ip(self, ip: str) -> bool:
        """Validate IP address format
        
        Args:
            ip: IP address string to validate
            
        Returns:
            True if valid IPv4 address
        """
        try:
            parts = ip.split('.')
            if len(parts) != 4:
                return False
            
            for part in parts:
                num = int(part)
                if num < 0 or num > 255:
                    return False
            
            return True
        
        except (ValueError, AttributeError):
            return False
    
    async def get_network_info(self, port: int = 58443, ssl_enabled: bool = False, use_letsencrypt: bool = False) -> Dict[str, Any]:
        """Get complete network configuration information
        
        Args:
            port: Server port number
            ssl_enabled: Whether HTTPS is enabled
            use_letsencrypt: Whether using Let's Encrypt (domain-based SSL)
            
        Returns:
            Dictionary with complete network information
        """
        lan_ip = await self.get_lan_ip()
        wan_ip = await self.get_wan_ip()
        
        # For Let's Encrypt SSL, LAN must use HTTP since the cert is for the domain, not the IP
        # For self-signed SSL (installed on device), both can use HTTPS
        if ssl_enabled and use_letsencrypt:
            # Let's Encrypt: LAN uses HTTP, domain/WAN uses HTTPS
            lan_protocol = "http"
            wan_protocol = "https"
        elif ssl_enabled:
            # Self-signed: both use HTTPS (cert installed on device)
            lan_protocol = "https"
            wan_protocol = "https"
        else:
            # No SSL: both use HTTP
            lan_protocol = "http"
            wan_protocol = "http"
        
        info = {
            "lan": {
                "ip": lan_ip,
                "url": f"{lan_protocol}://{lan_ip}:{port}",
                "protocol": lan_protocol,
                "available": lan_ip != "127.0.0.1"
            },
            "wan": {
                "ip": wan_ip,
                "url": f"{wan_protocol}://{wan_ip}:{port}" if wan_ip else None,
                "protocol": wan_protocol,
                "available": wan_ip is not None
            },
            "port": port,
            "protocol": wan_protocol,  # Primary protocol (for domain/WAN)
            "ssl_enabled": ssl_enabled,
            "use_letsencrypt": use_letsencrypt,
            "detected_at": datetime.now().isoformat()
        }
        
        return info
    
    async def is_behind_cgnat(self) -> bool:
        """Check if server appears to be behind CGNAT
        
        CGNAT (Carrier-Grade NAT) makes port forwarding impossible.
        This is a best-effort detection, not 100% accurate.
        
        Returns:
            True if likely behind CGNAT
        """
        lan_ip = await self.get_lan_ip()
        wan_ip = await self.get_wan_ip()
        
        if not wan_ip:
            # Can't determine
            return False
        
        # CGNAT typically uses 100.64.0.0/10 range
        if lan_ip.startswith('100.64.') or lan_ip.startswith('100.65.') or \
           lan_ip.startswith('100.66.') or lan_ip.startswith('100.67.'):
            logger.warning("Detected CGNAT range (100.64.0.0/10)")
            return True
        
        return False
    
    async def test_wan_connectivity(self, port: int = 58443) -> bool:
        """Test if WAN IP is accessible from outside
        
        Note: This cannot actually test from outside the network.
        Returns False if WAN IP is not available.
        
        Args:
            port: Port to check
            
        Returns:
            True if WAN IP is available (doesn't guarantee accessibility)
        """
        wan_ip = await self.get_wan_ip()
        return wan_ip is not None
    
    def clear_cache(self):
        """Clear IP address cache
        
        Forces fresh detection on next call
        """
        self._wan_ip_cache = None
        self._wan_ip_cache_time = None
        self._lan_ip_cache = None
        logger.debug("Network cache cleared")


# Global instance
_network_service: Optional[NetworkService] = None


def get_network_service() -> NetworkService:
    """Get global network service instance
    
    Returns:
        NetworkService singleton instance
    """
    global _network_service
    
    if _network_service is None:
        _network_service = NetworkService()
    
    return _network_service

