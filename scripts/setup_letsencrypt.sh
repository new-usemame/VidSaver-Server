#!/bin/bash
# Let's Encrypt Certificate Setup Script
# 
# This script sets up SSL/TLS certificates using Let's Encrypt (certbot)
# for the Video Download Server.
#
# Usage:
#   sudo ./scripts/setup_letsencrypt.sh <domain> <email> [--staging]
#
# Arguments:
#   domain: Your domain name (e.g., video.yourdomain.com)
#   email:  Your email address (for expiry notifications)
#   --staging: Optional flag to use Let's Encrypt staging server (for testing)
#
# Requirements:
#   - Domain must point to this server's IP address
#   - Port 80 must be accessible from the internet (for HTTP-01 challenge)
#   - certbot must be installed
#
# Example:
#   sudo ./scripts/setup_letsencrypt.sh video.example.com admin@example.com

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print colored output
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    print_error "This script must be run as root (use sudo)"
    exit 1
fi

# Parse arguments
if [ "$#" -lt 2 ]; then
    print_error "Usage: $0 <domain> <email> [--staging]"
    echo ""
    echo "Arguments:"
    echo "  domain   Your domain name (e.g., video.yourdomain.com)"
    echo "  email    Your email address (for Let's Encrypt notifications)"
    echo "  --staging  Optional: Use staging server for testing"
    echo ""
    echo "Example:"
    echo "  sudo $0 video.example.com admin@example.com"
    exit 1
fi

DOMAIN="$1"
EMAIL="$2"
STAGING_FLAG=""

if [ "$#" -ge 3 ] && [ "$3" = "--staging" ]; then
    STAGING_FLAG="--staging"
    print_warning "Using Let's Encrypt STAGING server (certificates will not be trusted)"
fi

print_info "Setting up Let's Encrypt for domain: $DOMAIN"
print_info "Email: $EMAIL"

# Check if certbot is installed
if ! command -v certbot &> /dev/null; then
    print_error "certbot is not installed"
    echo ""
    echo "Install certbot:"
    echo "  macOS:  brew install certbot"
    echo "  Ubuntu: sudo apt-get install certbot"
    echo "  CentOS: sudo yum install certbot"
    exit 1
fi

print_success "certbot is installed"

# Check if domain resolves to this server
print_info "Checking DNS resolution for $DOMAIN..."

# Check both IPv4 and IPv6 DNS records
RESOLVED_IPV4=$(dig +short A "$DOMAIN" | tail -n1)
RESOLVED_IPV6=$(dig +short AAAA "$DOMAIN" | tail -n1)

# Get server's public IPs
SERVER_IPV4=$(curl -4 -s ifconfig.me 2>/dev/null || curl -4 -s icanhazip.com 2>/dev/null || echo "")
SERVER_IPV6=$(curl -6 -s ifconfig.me 2>/dev/null || curl -6 -s icanhazip.com 2>/dev/null || echo "")

# Check if at least one IP is configured
if [ -z "$RESOLVED_IPV4" ] && [ -z "$RESOLVED_IPV6" ]; then
    print_warning "Could not resolve domain $DOMAIN (no A or AAAA records found)"
    print_warning "Make sure your domain's DNS records point to this server's IP"
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
else
    # Check IPv4
    if [ -n "$RESOLVED_IPV4" ]; then
        print_success "Domain has A record (IPv4): $RESOLVED_IPV4"
        if [ -n "$SERVER_IPV4" ]; then
            print_info "This server's IPv4: $SERVER_IPV4"
            if [ "$RESOLVED_IPV4" = "$SERVER_IPV4" ]; then
                print_success "✓ IPv4 addresses match!"
            else
                print_warning "IPv4 mismatch: DNS=$RESOLVED_IPV4, Server=$SERVER_IPV4"
            fi
        fi
    else
        print_info "No A record (IPv4) configured for domain"
    fi
    
    # Check IPv6
    if [ -n "$RESOLVED_IPV6" ]; then
        print_success "Domain has AAAA record (IPv6): $RESOLVED_IPV6"
        if [ -n "$SERVER_IPV6" ]; then
            print_info "This server's IPv6: $SERVER_IPV6"
            if [ "$RESOLVED_IPV6" = "$SERVER_IPV6" ]; then
                print_success "✓ IPv6 addresses match!"
            else
                print_warning "IPv6 mismatch: DNS=$RESOLVED_IPV6, Server=$SERVER_IPV6"
                print_info "This is common if IPv6 privacy extensions are enabled"
            fi
        fi
    else
        print_info "No AAAA record (IPv6) configured for domain"
    fi
    
    # As long as at least ONE IP matches, we're good
    IPV4_MATCH=false
    IPV6_MATCH=false
    
    if [ -n "$RESOLVED_IPV4" ] && [ -n "$SERVER_IPV4" ] && [ "$RESOLVED_IPV4" = "$SERVER_IPV4" ]; then
        IPV4_MATCH=true
    fi
    
    if [ -n "$RESOLVED_IPV6" ] && [ -n "$SERVER_IPV6" ] && [ "$RESOLVED_IPV6" = "$SERVER_IPV6" ]; then
        IPV6_MATCH=true
    fi
    
    if [ "$IPV4_MATCH" = false ] && [ "$IPV6_MATCH" = false ]; then
        print_warning "No IP addresses match between DNS and server"
        print_warning "Certificate validation may fail if Let's Encrypt cannot reach your server"
        read -p "Continue anyway? (y/n) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    else
        print_success "DNS configuration looks good - at least one IP matches!"
    fi
fi

# Check if port 80 is available
print_info "Checking if port 80 is available..."
if lsof -Pi :80 -sTCP:LISTEN -t >/dev/null 2>&1; then
    print_warning "Port 80 is already in use"
    print_info "certbot needs temporary access to port 80 for validation"
    print_info "Attempting to continue with --standalone mode..."
fi

# Obtain certificate using certbot
print_info "Obtaining certificate from Let's Encrypt..."
print_info "This may take a few moments..."

# Use standalone mode (temporary web server)
certbot certonly \
    --standalone \
    --preferred-challenges http \
    --domain "$DOMAIN" \
    --email "$EMAIL" \
    --agree-tos \
    --non-interactive \
    $STAGING_FLAG

if [ $? -eq 0 ]; then
    print_success "Certificate obtained successfully!"
else
    print_error "Failed to obtain certificate"
    echo ""
    echo "Common issues:"
    echo "  1. Domain does not point to this server"
    echo "  2. Port 80 is not accessible from the internet"
    echo "  3. Firewall is blocking port 80"
    echo ""
    echo "Troubleshooting:"
    echo "  - Check DNS: dig $DOMAIN"
    echo "  - Check port 80: nc -zv $(curl -s ifconfig.me) 80"
    echo "  - Check firewall: sudo ufw status (Ubuntu) or sudo firewall-cmd --list-all (CentOS)"
    exit 1
fi

# Show certificate location
CERT_PATH="/etc/letsencrypt/live/$DOMAIN/fullchain.pem"
KEY_PATH="/etc/letsencrypt/live/$DOMAIN/privkey.pem"

print_info "Certificate files:"
echo "  Certificate: $CERT_PATH"
echo "  Private Key: $KEY_PATH"

# Verify certificate
print_info "Verifying certificate..."
if openssl x509 -in "$CERT_PATH" -text -noout > /dev/null 2>&1; then
    print_success "Certificate is valid"
    
    # Show expiry date
    EXPIRY=$(openssl x509 -enddate -noout -in "$CERT_PATH" | cut -d= -f2)
    print_info "Certificate expires: $EXPIRY"
else
    print_error "Certificate verification failed"
    exit 1
fi

# Set up automatic renewal
print_info "Setting up automatic certificate renewal..."

# Create renewal script
RENEWAL_SCRIPT="/usr/local/bin/renew-videoserver-cert.sh"
cat > "$RENEWAL_SCRIPT" <<'EOF'
#!/bin/bash
# Automatic certificate renewal script for Video Download Server
# This script is run by cron to renew certificates before they expire

set -e

DOMAIN="DOMAIN_PLACEHOLDER"
LOG_FILE="/var/log/videoserver-cert-renewal.log"

echo "$(date): Checking certificate renewal for $DOMAIN" >> "$LOG_FILE"

# Attempt renewal
certbot renew --quiet --deploy-hook "systemctl reload videoserver || echo 'Note: Could not reload videoserver service'" >> "$LOG_FILE" 2>&1

if [ $? -eq 0 ]; then
    echo "$(date): Certificate renewal check completed successfully" >> "$LOG_FILE"
else
    echo "$(date): Certificate renewal check failed" >> "$LOG_FILE"
fi
EOF

# Replace placeholder with actual domain
sed -i'.bak' "s/DOMAIN_PLACEHOLDER/$DOMAIN/g" "$RENEWAL_SCRIPT"
rm "${RENEWAL_SCRIPT}.bak" 2>/dev/null || true

chmod +x "$RENEWAL_SCRIPT"
print_success "Created renewal script: $RENEWAL_SCRIPT"

# Set up cron job (runs twice daily)
CRON_JOB="0 0,12 * * * $RENEWAL_SCRIPT"
(crontab -l 2>/dev/null | grep -v "$RENEWAL_SCRIPT"; echo "$CRON_JOB") | crontab -
print_success "Set up automatic renewal (runs twice daily)"

# Update config.yaml if it exists
CONFIG_FILE="config/config.yaml"
if [ -f "$CONFIG_FILE" ]; then
    print_info "Updating $CONFIG_FILE with certificate paths..."
    
    # Backup config
    cp "$CONFIG_FILE" "${CONFIG_FILE}.backup"
    
    # Update config (basic sed replacement)
    sed -i'.tmp' \
        -e "s|cert_file:.*|cert_file: \"$CERT_PATH\"|" \
        -e "s|key_file:.*|key_file: \"$KEY_PATH\"|" \
        -e "s|domain:.*|domain: \"$DOMAIN\"|" \
        -e "s|use_letsencrypt:.*|use_letsencrypt: true|" \
        -e "s|letsencrypt_email:.*|letsencrypt_email: \"$EMAIL\"|" \
        "$CONFIG_FILE"
    rm "${CONFIG_FILE}.tmp" 2>/dev/null || true
    
    print_success "Updated $CONFIG_FILE"
else
    print_warning "Config file not found: $CONFIG_FILE"
    print_info "Please update your configuration manually"
fi

# Final instructions
echo ""
print_success "=== Setup Complete! ==="
echo ""
echo "Next steps:"
echo "  1. Update your config.yaml (if not done automatically):"
echo "     - domain: \"$DOMAIN\""
echo "     - use_letsencrypt: true"
echo "     - letsencrypt_email: \"$EMAIL\""
echo ""
echo "  2. Start your server:"
echo "     python server.py"
echo ""
echo "  3. Test HTTPS connection:"
echo "     curl https://$DOMAIN:8443/api/v1/health"
echo ""
echo "Certificate will auto-renew before expiration."
echo "Renewal logs: /var/log/videoserver-cert-renewal.log"
echo ""
print_success "iOS devices will trust this certificate automatically!"

