#!/bin/bash
# Self-Signed Certificate Generation Script
#
# This script generates a self-signed SSL certificate for development/testing.
# 
# ⚠️  WARNING: Self-signed certificates require manual installation on iOS devices!
# ⚠️  For production, use Let's Encrypt instead: ./scripts/setup_letsencrypt.sh
#
# Usage:
#   ./scripts/generate_selfsigned.sh [domain]
#
# Arguments:
#   domain: Optional domain name (default: localhost)

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Get domain from argument or use localhost
DOMAIN="${1:-localhost}"

# Create certs directory
mkdir -p certs

print_warning "Generating self-signed certificate for: $DOMAIN"
print_warning "This certificate is for DEVELOPMENT ONLY"
print_warning "iOS devices will require manual certificate installation"

# Generate private key
openssl genrsa -out certs/server.key 2048

# Generate certificate (valid for 365 days)
openssl req -new -x509 -key certs/server.key -out certs/server.crt -days 365 \
    -subj "/C=US/ST=State/L=City/O=Development/CN=$DOMAIN" \
    -addext "subjectAltName=DNS:$DOMAIN,DNS:localhost,IP:127.0.0.1"

print_success "Certificate generated successfully!"
echo ""
echo "Certificate location:"
echo "  Certificate: $(pwd)/certs/server.crt"
echo "  Private Key: $(pwd)/certs/server.key"
echo ""
print_warning "iOS Setup Required:"
echo "  1. Copy certs/server.crt to your iOS device (via AirDrop or email)"
echo "  2. Tap the certificate file to install it"
echo "  3. Go to Settings → General → About → Certificate Trust Settings"
echo "  4. Enable trust for the certificate"
echo ""
echo "For production, use Let's Encrypt instead:"
echo "  sudo ./scripts/setup_letsencrypt.sh your-domain.com your@email.com"

