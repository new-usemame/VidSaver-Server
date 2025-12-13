# Menu Bar App Crash Recovery System

## What Happened?

**Your server didn't crash** - it was running fine and responding to requests.  
**The menu bar app crashed** - it exited silently, causing the icon to disappear.

## Why Did the Menu Bar App Crash?

GUI applications can crash for various reasons:
- macOS system updates
- Memory pressure
- Python runtime issues
- GUI framework (rumps) issues
- User accidentally force-quit it

The server is a separate process, so it keeps running even if the menu bar app crashes.

## Solution: Auto-Recovery Watchdog 🐕

We've implemented a **watchdog** that monitors the menu bar app and automatically restarts it if it crashes.

### The System Now Has 3 Components:

```
┌─────────────────┐
│  Video Server   │ ← Main server process
│   (server.py)   │   Handles all video downloads
└────────┬────────┘
         │
         ├─── Launches ───┐
         │                 │
         │         ┌───────▼──────────┐
         │         │   Menu Bar App   │ ← GUI control panel
         │         │ (menubar_app.py) │   The icon you see
         │         └───────▲──────────┘
         │                 │
         │                 │ Monitors & Restarts
         │         ┌───────┴────────────┐
         └─────────│     Watchdog       │ ← Auto-recovery system
                   │ (menubar_watchdog)  │   Restarts if crashed
                   └────────────────────┘
```

### How It Works

1. **Server starts** → Launches menu bar app → Launches watchdog
2. **Watchdog monitors** every 10 seconds
3. **If menu bar app crashes** → Watchdog detects it → Restarts it automatically
4. **Notification shown** when reconnected
5. **Server unaffected** throughout the process

### Features

✅ **Automatic restart** - Menu bar app restarts within 10 seconds of crash  
✅ **Smart throttling** - Won't restart more than once per minute (prevents loops)  
✅ **Server monitoring** - Stops if server is down (no point watching)  
✅ **Crash counting** - Tracks how many times it has restarted  
✅ **Clean shutdown** - Stops gracefully when server stops  
✅ **Silent operation** - Works in background, no user interaction needed  

## Testing Performed

```bash
# Killed menu bar app (simulating crash)
kill 50508

# Watchdog detected crash and restarted within 10 seconds
# New PID: 50685 ✅

# Menu bar icon reappeared automatically! 🎉
```

## How to Check Status

### See all running components:
```bash
ps aux | grep -E "(server\.py|menubar_app|menubar_watchdog)" | grep -v grep
```

You should see:
- ✅ server.py
- ✅ menubar_app.py
- ✅ menubar_watchdog.py

### Check watchdog logs:
```bash
# Watchdog logs are sent to /dev/null by default
# To see watchdog output, run it manually:
./venv/bin/python menubar_watchdog.py
```

## Manual Control

### Start everything:
```bash
./manage.sh start
# Starts: server + menu bar app + watchdog
```

### Stop everything:
```bash
./manage.sh stop
# Stops: server + watchdog (leaves menu bar app for manual control)
```

### Restart watchdog only:
```bash
./venv/bin/python menubar_watchdog.py > /dev/null 2>&1 &
```

### Check if watchdog is running:
```bash
pgrep -f "menubar_watchdog.py"
```

## Watchdog Configuration

Located in: `menubar_watchdog.py`

Key settings:
- **CHECK_INTERVAL**: 10 seconds (how often it checks)
- **Restart throttle**: Won't restart more than once per minute
- **Auto-stop**: Stops if server is not running

## What Gets Logged

The watchdog logs to stdout (redirected to /dev/null in auto-start):
```
[22:45:31] 🐕 Menu Bar Watchdog started (PID: 50637)
[22:45:31] Monitoring menu bar app every 10 seconds
[22:46:15] ⚠️  Menu bar app crashed! Restarting (#1)...
[22:46:15] 🚀 Launched menu bar app
```

## Troubleshooting

### Menu bar icon still not appearing?

1. **Check all processes running:**
   ```bash
   ps aux | grep -E "(server|menubar)" | grep -v grep
   ```

2. **Manually restart menu bar app:**
   ```bash
   ./venv/bin/python menubar_app.py
   ```

3. **Check for rumps installation:**
   ```bash
   pip list | grep rumps
   ```

4. **View system logs:**
   ```bash
   tail -f logs/server.log
   ```

### Watchdog not starting?

1. **Check if it's running:**
   ```bash
   pgrep -f "menubar_watchdog"
   ```

2. **Start manually to see output:**
   ```bash
   ./venv/bin/python menubar_watchdog.py
   ```

3. **Check PID file:**
   ```bash
   cat menubar_watchdog.pid
   ```

### Too many restarts?

If menu bar app keeps crashing in a loop:

1. **Stop watchdog:**
   ```bash
   kill $(pgrep -f "menubar_watchdog")
   ```

2. **Check for errors:**
   ```bash
   ./venv/bin/python menubar_app.py
   # Watch for error messages
   ```

3. **Check dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

## Files Added/Modified

**New Files:**
- `menubar_watchdog.py` - The watchdog script
- `menubar_watchdog.pid` - Watchdog process ID (auto-generated)
- `CRASH_RECOVERY.md` - This documentation

**Modified Files:**
- `server.py` - Now launches watchdog on startup
- `manage.sh` - Stops watchdog on server stop
- `menubar_app.py` - Shows notification when reconnecting

## Technical Details

### Process Hierarchy
```
Parent: server.py (PID 50581)
  ├─ Child: menubar_app.py (PID 50685)
  └─ Child: menubar_watchdog.py (PID 50637)
       └─ Monitors: menubar_app.py
```

### Detection Method
Uses `pgrep -f "menubar_app.py"` to check if process exists.

### Restart Logic
1. Detect crash (no PID found)
2. Check last restart time (throttle to 1/minute)
3. Launch new instance via subprocess.Popen
4. Wait 2 seconds for startup
5. Continue monitoring

### Signal Handling
Watchdog responds to:
- **SIGTERM** - Graceful shutdown
- **SIGINT** - Ctrl+C shutdown
- Both clean up PID file on exit

## Future Enhancements

Potential improvements:
- [ ] Log crashes to file with timestamps
- [ ] Email/notification on repeated crashes
- [ ] Configurable check interval
- [ ] Health check via HTTP endpoint
- [ ] Crash dump collection
- [ ] Automatic bug reporting

## Summary

Your menu bar icon disappeared because the **menu bar app crashed**, not the server. The server was fine the whole time!

We've now implemented:
1. **Auto-launch** - Menu bar app starts with server
2. **Auto-recovery** - Watchdog restarts it if it crashes
3. **Resilience** - Server keeps running regardless

**You should never see the icon disappear again!** 🎉

