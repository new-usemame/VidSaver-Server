#!/bin/bash
# Video Server Management Script

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$SCRIPT_DIR"
PID_FILE="$PROJECT_DIR/server.pid"
LOG_FILE="$PROJECT_DIR/logs/nohup.log"

cd "$PROJECT_DIR"

case "$1" in
    start)
        if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
            echo "❌ Server is already running (PID: $(cat "$PID_FILE"))"
            exit 1
        fi
        
        echo "🚀 Starting server..."
        nohup ./venv/bin/python server.py > "$LOG_FILE" 2>&1 &
        SERVER_PID=$!
        echo "$SERVER_PID" > "$PID_FILE"
        sleep 2
        
        if kill -0 "$SERVER_PID" 2>/dev/null; then
            echo "✅ Server started successfully (PID: $SERVER_PID)"
            echo "📍 Access at: http://localhost:58443/docs"
            IP=$(ifconfig | grep "inet " | grep -v 127.0.0.1 | awk '{print $2}' | head -1)
            echo "📱 From iOS: http://$IP:58443/docs"
            
            # Launch menu bar app if on macOS and not already running
            if [[ "$OSTYPE" == "darwin"* ]]; then
                if ! pgrep -f "menubar_app.py" > /dev/null; then
                    echo "🎛️  Launching menu bar app..."
                    ./venv/bin/python menubar_app.py > /dev/null 2>&1 &
                else
                    echo "✅ Menu bar app already running"
                fi
            fi
        else
            echo "❌ Server failed to start. Check logs: tail -f $LOG_FILE"
            exit 1
        fi
        ;;
        
    stop)
        if [ ! -f "$PID_FILE" ]; then
            echo "❌ No PID file found. Is the server running?"
            exit 1
        fi
        
        PID=$(cat "$PID_FILE")
        if kill -0 "$PID" 2>/dev/null; then
            echo "🛑 Stopping server (PID: $PID)..."
            kill "$PID"
            rm "$PID_FILE"
            echo "✅ Server stopped"
        else
            echo "❌ Server not running (stale PID file removed)"
            rm "$PID_FILE"
        fi
        
        # Stop watchdog if running
        WATCHDOG_PID=$(pgrep -f "menubar_watchdog.py")
        if [ -n "$WATCHDOG_PID" ]; then
            echo "🛑 Stopping watchdog (PID: $WATCHDOG_PID)..."
            kill "$WATCHDOG_PID" 2>/dev/null
        fi
        
        # Stop menu bar app if user wants to
        # (leaving it running so user can start server from menu)
        ;;
        
    restart)
        $0 stop
        sleep 1
        $0 start
        ;;
        
    status)
        if [ -f "$PID_FILE" ] && kill -0 $(cat "$PID_FILE") 2>/dev/null; then
            PID=$(cat "$PID_FILE")
            echo "✅ Server is running (PID: $PID)"
            IP=$(ifconfig | grep "inet " | grep -v 127.0.0.1 | awk '{print $2}' | head -1)
            echo "📍 Local:  http://localhost:58443/docs"
            echo "📱 Remote: http://$IP:58443/docs"
            echo ""
            echo "Health check:"
            curl -s http://localhost:58443/api/v1/health | python3 -m json.tool 2>/dev/null || echo "Server not responding"
        else
            echo "❌ Server is not running"
            if [ -f "$PID_FILE" ]; then
                rm "$PID_FILE"
            fi
        fi
        ;;
        
    logs)
        if [ ! -f "$LOG_FILE" ]; then
            echo "❌ No log file found"
            exit 1
        fi
        echo "📄 Showing last 50 lines (Ctrl+C to exit):"
        tail -n 50 -f "$LOG_FILE"
        ;;
        
    *)
        echo "Video Download Server - Management Script"
        echo ""
        echo "Usage: $0 {start|stop|restart|status|logs}"
        echo ""
        echo "Commands:"
        echo "  start   - Start the server"
        echo "  stop    - Stop the server"
        echo "  restart - Restart the server"
        echo "  status  - Check server status"
        echo "  logs    - View server logs (live)"
        echo ""
        exit 1
        ;;
esac

