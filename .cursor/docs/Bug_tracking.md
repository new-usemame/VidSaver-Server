# Bug Tracking and Resolution Log

## Purpose

This document tracks all bugs, errors, and issues encountered during the development of the Video Download Server, along with their root causes and resolution steps. **Always check this document before attempting to fix any error** to avoid repeating mistakes or implementing incorrect solutions.

## Document Guidelines

### When to Add an Entry:
- When encountering any error during development
- When discovering a bug in existing functionality
- When implementing a workaround for a known issue
- When finding an edge case that causes problems

### Entry Format:
```
## [SEVERITY] Bug Title
**Date:** YYYY-MM-DD
**Stage:** Implementation stage where bug was found
**Component:** Affected module/component
**Status:** Open | In Progress | Resolved | Wontfix

### Description:
Brief description of the bug and how it manifests.

### Root Cause:
Explanation of what caused the bug.

### Resolution:
Step-by-step solution that was implemented.

### Prevention:
How to prevent this bug in the future or what to watch out for.

---
```

### Severity Levels:
- **[CRITICAL]** - Data loss, security vulnerability, server crash
- **[HIGH]** - Feature broken, significant functionality impaired
- **[MEDIUM]** - Partial functionality impaired, workaround exists
- **[LOW]** - Minor issue, cosmetic, or edge case
- **[INFO]** - Not a bug, but important information to track

---

## Bug Entries

## [MEDIUM] Python 3.14 Not Supported - PyO3 Compatibility
**Date:** 2025-12-14  
**Stage:** Setup  
**Component:** requirements.txt / pip install  
**Status:** Resolved

### Description:
When running `pip install -r requirements.txt` with Python 3.14, installation fails with error:
`the configured Python interpreter version (3.14) is newer than PyO3's maximum supported version (3.13)`

### Root Cause:
Python 3.14 is still in alpha/beta. Many packages with Rust components (pydantic, uvicorn) use PyO3 for Python bindings, which hasn't added 3.14 support yet.

### Resolution:
Use Python 3.12 or 3.13 instead:
```bash
pyenv local 3.12.7
rm -rf venv
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Prevention:
README updated to specify Python 3.9-3.13 as supported versions.

---

## [MEDIUM] rumps Info.plist Missing in Virtual Environment (Mac)
**Date:** 2025-12-14  
**Stage:** Setup  
**Component:** menubar_app.py  
**Status:** Resolved

### Description:
When starting the menubar app, error appears:
`Failed to start server: Failed to setup the notification center. This issue occurs when the "Info.plist" file cannot be found or is missing "CFBundleIdentifier".`

### Root Cause:
The `rumps` library requires an Info.plist file with a bundle identifier when running from a virtual environment on macOS.

### Resolution:
Run this command to create the required plist file:
```bash
/usr/libexec/PlistBuddy -c 'Add :CFBundleIdentifier string "rumps"' venv/bin/Info.plist
```

### Prevention:
Document this step in setup instructions for Mac users using the menubar app.

---

## Known Issues

### Database-Related
*No known issues yet*

### API Endpoints
*No known issues yet*

### Download Queue
*No known issues yet*

### yt-dlp Integration
*No known issues yet*

### HTTPS/Certificates
*No known issues yet*

### Configuration
*No known issues yet*

### Security
*No known issues yet*

### Deployment
*No known issues yet*

---

## Common Pitfalls (To Be Populated During Development)

### Database Operations
- **Pitfall:** Not committing transaction before returning response
  - **Impact:** Data loss if server crashes after response sent
  - **Solution:** Always commit database transaction before sending HTTP response

### Queue Processing
- **Pitfall:** Not handling queue resume after server restart
  - **Impact:** Downloads stuck in "downloading" status after restart
  - **Solution:** On startup, reset any "downloading" status back to "queued"

### yt-dlp
- **Pitfall:** Not handling yt-dlp updates or breaking changes
  - **Impact:** Downloads fail silently or with cryptic errors
  - **Solution:** Pin yt-dlp version in requirements.txt, test before upgrading

### HTTPS Certificates
- **Pitfall:** Missing SAN (Subject Alternative Names) in certificate
  - **Impact:** iOS devices reject certificate
  - **Solution:** Always include SAN in OpenSSL configuration

---

## Statistics

- **Total Bugs Logged:** 2
- **Critical Bugs:** 0
- **Resolved Bugs:** 2
- **Open Bugs:** 0

---

## Notes

- This document will be actively maintained throughout development
- Always add an entry BEFORE fixing the bug to document the issue properly
- Include code snippets or error messages when helpful
- Link to relevant documentation or resources
- Update statistics when adding/resolving bugs

---

**Last Updated:** November 7, 2025  
**Status:** Initialized - No bugs logged yet

