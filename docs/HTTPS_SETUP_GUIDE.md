# HTTPS Setup Guide - Using the Configuration Page

## Quick Access

1. **Via Menu Bar App:** Click "🎛️ Config Editor"
2. **Via Browser:** Navigate to `http://localhost:58443/api/v1/config/editor`

## SSL/HTTPS Setup Walkthrough

### Option 1: Let's Encrypt (Recommended for Production)

**Best for:** iOS devices (works automatically), production use, remote access

1. **Open the Configuration Page** (Server tab)
2. **Check "Enable SSL/HTTPS"** checkbox
3. **Check "✅ Use Let's Encrypt"** checkbox
4. **Fill in required fields:**
   - **Domain Name:** Your domain (e.g., `video.yourdomain.com`)
   - **Email Address:** Your email for renewal notifications

5. **Click the info icons (ℹ️)** for detailed explanations of each field

6. **Before saving**, complete these prerequisites:
   ```bash
   # Ensure your domain points to this server
   dig video.yourdomain.com  # Should show your server's IP
   
   # Run the Let's Encrypt setup script
   sudo ./scripts/setup_letsencrypt.sh video.yourdomain.com your@email.com
   ```

7. **Click "💾 Save Configuration"**
   - Server will restart automatically
   - Certificates auto-renew every 60 days

**✅ Result:** Your iOS app will trust the connection immediately—no manual certificate installation needed!

---

### Option 2: Self-Signed Certificate (Development/Testing)

**Best for:** Local development, offline testing, quick setup

1. **Open the Configuration Page** (Server tab)
2. **Check "Enable SSL/HTTPS"** checkbox
3. **Leave "Use Let's Encrypt" UNCHECKED**
4. **Generate a self-signed certificate:**
   ```bash
   ./scripts/generate_selfsigned.sh your-computer-name.local
   ```

5. **Fill in certificate paths:**
   - **Certificate File Path:** `certs/server.crt`
   - **Private Key File Path:** `certs/server.key`

6. **Click "💾 Save Configuration"**

**⚠️ iOS Setup Required:**
- You must manually install the certificate on each iOS device
- Settings → Profile Downloaded → Install
- Settings → General → About → Certificate Trust Settings
- Enable trust for your certificate

---

## Understanding the Interface

### Info Icons (ℹ️)
Hover over or click any **ℹ️ icon** to see detailed explanations about:
- What each field does
- When to use it
- Requirements and constraints
- Common pitfalls

### Disabled Fields
Fields are automatically **disabled/grayed out** when not applicable:
- SSL disabled → All SSL fields disabled
- Let's Encrypt enabled → Manual certificate fields disabled
- Manual certificates → Let's Encrypt fields disabled

### Visual Cues
- **Green background:** Recommended options (Let's Encrypt)
- **Yellow background:** Alternative options (Manual certificates)
- **Blue alerts:** Important information and instructions

---

## Common Scenarios

### Moving Between Dev/Production
**Scenario:** You want HTTPS on both your dev Mac and production server

**Solution:**
1. Use Let's Encrypt on both with different subdomains:
   - Dev: `dev.yourdomain.com` → Dev Mac IP
   - Prod: `video.yourdomain.com` → Production server IP

2. Update DNS to point to whichever machine you're using
3. Both machines work seamlessly with iOS

### Quick Testing Without Domain
**Scenario:** You want to test HTTPS but don't have a domain yet

**Solution:**
1. Use self-signed certificates (Option 2 above)
2. Accept the manual iOS setup requirement
3. Later upgrade to Let's Encrypt when ready

### Switching from Self-Signed to Let's Encrypt
**Scenario:** You started with self-signed, now want proper certificates

**Solution:**
1. Obtain a domain name and point it to your server
2. Run Let's Encrypt setup script
3. Open Config Editor → Server tab
4. Check "Use Let's Encrypt"
5. Fill in domain and email
6. Save configuration
7. Done! Certificate/key paths are auto-managed

---

## Troubleshooting

### "Domain not configured" Warning
- Ensure DNS A record points to your server's IP
- Wait 5-60 minutes for DNS propagation
- Check with: `dig your-domain.com`

### "Port 80 unavailable"
- Let's Encrypt needs port 80 for validation
- Check firewall: `sudo ufw allow 80/tcp` (Linux)
- Check router port forwarding

### Fields Won't Enable
- Check that "Enable SSL/HTTPS" is checked first
- Refresh the page if fields seem stuck
- Check browser console for JavaScript errors

### iOS Still Shows "Not Secure"
**For Let's Encrypt:** Should never happen—certificates are globally trusted
- Verify domain in browser matches certificate
- Check certificate expiry: `sudo certbot certificates`

**For Self-Signed:** 
- Verify certificate is installed on iOS device
- Verify trust is enabled in Certificate Trust Settings
- Restart iOS device after installation

---

## Tips for Best Experience

1. **Read the tooltips!** Hover over ℹ️ icons for detailed context
2. **Start with Let's Encrypt** if you have a domain—it's much easier for iOS
3. **Keep email notifications enabled** for Let's Encrypt renewal alerts
4. **Test locally first** with self-signed before going public
5. **Use strong API keys** when enabling public access
6. **Check logs** at `logs/server.log` if things don't work

---

**Need More Help?**
- Full SSL documentation: `docs/SSL_SETUP.md`
- iOS integration guide: `docs/iOS_INTEGRATION.md`
- Server logs: `tail -f logs/server.log`

