# SSL/HTTPS Certificate Setup Guide

This guide covers setting up SSL/TLS certificates for the Video Download Server. We **strongly recommend using Let's Encrypt** for production deployments.

## 🎯 Quick Start (Recommended)

### Let's Encrypt Setup - iOS Just Works!

**Advantages:**
- ✅ **Zero iOS setup** - Certificates are trusted automatically
- ✅ **Free** - No cost
- ✅ **Auto-renewal** - Certificates renew before expiry
- ✅ **Professional** - Same certificates used by major websites
- ✅ **Portable** - Move between machines by updating DNS

**Requirements:**
1. A domain name (e.g., `video.yourdomain.com`)
2. DNS A record pointing to your server's IP
3. Port 80 accessible (for validation)

**Setup:**

```bash
# 1. Point your domain to this server's IP
# Update DNS A record: video.yourdomain.com → your-server-ip

# 2. Run setup script
sudo ./scripts/setup_letsencrypt.sh video.yourdomain.com your@email.com

# 3. Update config.yaml
server:
  domain: "video.yourdomain.com"
  use_letsencrypt: true
  letsencrypt_email: "your@email.com"

# 4. Start server
python server.py

# Done! iOS devices will trust the certificate automatically.
```

---

## 📖 Detailed Setup Instructions

### Option A: Let's Encrypt (Production)

#### Step 1: Install Certbot

**macOS:**
```bash
brew install certbot
```

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install certbot
```

**CentOS/RHEL:**
```bash
sudo yum install certbot
```

#### Step 2: Configure DNS

Point your domain's A record to your server's IP address:

```
Type: A
Name: video (or @ for root domain)
Value: <your-server-ip>
TTL: 300 (or default)
```

**Verify DNS:**
```bash
dig video.yourdomain.com
# Should return your server's IP
```

#### Step 3: Run Setup Script

```bash
sudo ./scripts/setup_letsencrypt.sh video.yourdomain.com your@email.com
```

The script will:
1. Obtain certificate from Let's Encrypt
2. Set up automatic renewal
3. Update your config.yaml
4. Configure cron job for renewal checks

#### Step 4: Update Configuration

If not done automatically, edit `config/config.yaml`:

```yaml
server:
  domain: "video.yourdomain.com"
  use_letsencrypt: true
  letsencrypt_email: "your@email.com"
  # These paths are auto-managed by Let's Encrypt
  cert_file: "/etc/letsencrypt/live/video.yourdomain.com/fullchain.pem"
  key_file: "/etc/letsencrypt/live/video.yourdomain.com/privkey.pem"
```

#### Step 5: Start Server

```bash
python server.py
```

#### Step 6: Test HTTPS

```bash
curl https://video.yourdomain.com:8443/api/v1/health
```

**From iOS:**
- Open Safari or your app
- Connect to `https://video.yourdomain.com:8443`
- ✅ Should work immediately with no warnings!

---

### Option B: Self-Signed Certificate (Development Only)

⚠️ **Not recommended for production** - Requires manual iOS setup

#### When to Use

- Quick local development
- Testing without domain
- Offline development

#### Generate Certificate

```bash
./scripts/generate_selfsigned.sh your-computer-name.local
```

#### iOS Setup Required

1. **Copy certificate to iOS:**
   ```bash
   # Certificate is at: certs/server.crt
   # Send via AirDrop, email, or iCloud Drive
   ```

2. **Install on iOS:**
   - Tap the `.crt` file
   - Tap "Allow" to download profile
   - Go to Settings → Profile Downloaded
   - Tap "Install" (enter passcode if prompted)

3. **Trust certificate:**
   - Settings → General → About
   - Scroll to bottom: "Certificate Trust Settings"
   - Enable trust for your certificate
   - Tap "Continue" on warning

4. **Verify:**
   - Open Safari
   - Visit: `https://your-computer-ip:8443/api/v1/health`
   - Should work without warnings

---

## 🔄 Certificate Management

### Check Certificate Status

```bash
# View certificate info
sudo certbot certificates

# Check expiry
openssl x509 -enddate -noout -in /etc/letsencrypt/live/your-domain/fullchain.pem
```

### Manual Renewal

```bash
# Test renewal (dry run)
sudo certbot renew --dry-run

# Force renewal
sudo certbot renew --force-renewal
```

### Automatic Renewal

Let's Encrypt setup script automatically configures:
- Cron job runs twice daily
- Checks if renewal is needed (< 30 days until expiry)
- Renews certificate if needed
- Reloads server automatically

**Check renewal logs:**
```bash
tail -f /var/log/videoserver-cert-renewal.log
```

### Update DNS (Moving Servers)

When moving between dev/production machines:

1. **Update DNS** to point to new server:
   ```
   video.yourdomain.com → new-server-ip
   ```

2. **Run setup on new server:**
   ```bash
   sudo ./scripts/setup_letsencrypt.sh video.yourdomain.com your@email.com
   ```

3. **Start server** - Done!

---

## 🔍 Troubleshooting

### Issue: "Domain does not resolve"

**Check DNS:**
```bash
dig video.yourdomain.com
# Should return your server's IP
```

**Wait for propagation:**
- DNS changes can take 5-60 minutes
- Check: https://dnschecker.org

### Issue: "Port 80 connection refused"

**Check firewall:**

**macOS:**
```bash
# No firewall by default, usually not needed
```

**Ubuntu:**
```bash
sudo ufw allow 80/tcp
sudo ufw allow 8443/tcp
sudo ufw status
```

**Test port:**
```bash
nc -zv $(curl -s ifconfig.me) 80
```

### Issue: "Certificate validation failed"

**Check certificate and key match:**
```bash
# Certificate modulus
openssl x509 -noout -modulus -in /path/to/cert.pem | openssl md5

# Key modulus
openssl rsa -noout -modulus -in /path/to/key.pem | openssl md5

# MD5 hashes should match
```

### Issue: "iOS still shows 'Not Secure'"

**Using self-signed:**
- Verify certificate is installed (Settings → General → VPN & Device Management)
- Verify trust is enabled (Settings → General → About → Certificate Trust Settings)

**Using Let's Encrypt:**
- Should never happen - certificate is globally trusted
- Check server is using correct domain name
- Verify certificate is valid: `openssl x509 -text -in /path/to/cert.pem`

### Issue: "Certificate expired"

**Let's Encrypt certificates expire in 90 days:**

```bash
# Check expiry
sudo certbot certificates

# Renew now
sudo certbot renew --force-renewal

# Restart server
```

---

## 📋 Best Practices

### Development Workflow

1. **Local development:**
   - Use self-signed certificate OR
   - Point dev subdomain to dev machine (recommended)

2. **Testing:**
   - Use Let's Encrypt staging server:
     ```bash
     sudo ./scripts/setup_letsencrypt.sh dev.yourdomain.com your@email.com --staging
     ```

3. **Production:**
   - Use Let's Encrypt production server
   - Point production subdomain to production machine

### Domain Strategy

```
dev.yourdomain.com     → Dev Mac (Let's Encrypt)
staging.yourdomain.com → Staging server (Let's Encrypt)
video.yourdomain.com   → Production server (Let's Encrypt)
```

Benefits:
- Same certificate setup everywhere
- Easy to switch machines (just update DNS)
- iOS always works

### Security Tips

1. **Protect private keys:**
   ```bash
   sudo chmod 600 /etc/letsencrypt/live/*/privkey.pem
   ```

2. **Monitor expiry:**
   - Let's Encrypt sends reminder emails
   - Check logs: `/var/log/videoserver-cert-renewal.log`

3. **Use strong ciphers:**
   - Uvicorn (our ASGI server) uses secure defaults
   - TLS 1.2 and 1.3 only

---

## 🎓 Understanding Let's Encrypt

### How It Works

1. **Domain validation:** Let's Encrypt verifies you control the domain
2. **HTTP-01 challenge:** Temporary file served on port 80
3. **Certificate issued:** Valid for 90 days
4. **Auto-renewal:** Certbot checks daily, renews at 30 days

### Why It's Perfect for Your Use Case

- **Domain-based:** Not tied to specific IP address
- **Free:** No annual fees
- **Automated:** Renewal is automatic
- **Trusted:** Works on all devices
- **Portable:** Move servers by updating DNS

### Certificate Locations

```
/etc/letsencrypt/live/your-domain/
├── fullchain.pem  → Certificate (use this)
├── privkey.pem    → Private key (use this)
├── cert.pem       → Certificate only (without chain)
└── chain.pem      → Chain only
```

**Always use `fullchain.pem` and `privkey.pem`**

---

## 📞 Getting Help

### Check Server Logs

```bash
# Server logs
tail -f logs/server.log

# Certificate renewal logs
tail -f /var/log/videoserver-cert-renewal.log

# Certbot logs
sudo tail -f /var/log/letsencrypt/letsencrypt.log
```

### Test Certificate

```bash
# Test with curl
curl -v https://your-domain:8443/api/v1/health

# Test with openssl
openssl s_client -connect your-domain:8443 -servername your-domain

# Check certificate details
echo | openssl s_client -connect your-domain:8443 -servername your-domain 2>/dev/null | openssl x509 -noout -dates -subject
```

### Common Let's Encrypt Commands

```bash
# List all certificates
sudo certbot certificates

# Renew all certificates
sudo certbot renew

# Revoke certificate
sudo certbot revoke --cert-path /etc/letsencrypt/live/your-domain/cert.pem

# Delete certificate
sudo certbot delete --cert-name your-domain
```

---

## 🎯 Quick Reference

### Development Setup
```bash
./scripts/generate_selfsigned.sh localhost
# or
sudo ./scripts/setup_letsencrypt.sh dev.yourdomain.com you@email.com --staging
```

### Production Setup
```bash
# Update DNS first
sudo ./scripts/setup_letsencrypt.sh video.yourdomain.com you@email.com
```

### Check Certificate
```bash
openssl x509 -enddate -noout -in <cert-path>
```

### Force Renewal
```bash
sudo certbot renew --force-renewal
```

### Move to New Server
```bash
# 1. Update DNS
# 2. Run on new server:
sudo ./scripts/setup_letsencrypt.sh your-domain.com you@email.com
```

---

**Updated:** November 7, 2025  
**Version:** 1.0.0

