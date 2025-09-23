#!/bin/bash

# News Web Server Start Script
# Prevents multiple instances from running

set -e

PROJECT_ROOT="/home/cytrex/news-mcp"
PORT=8000
PIDFILE="$PROJECT_ROOT/.web-server.pid"

cd "$PROJECT_ROOT"

# Function to check if server is already running
check_existing_process() {
    # Check by port
    if netstat -tlnp 2>/dev/null | grep -q ":$PORT "; then
        echo "⚠️  Web server is already running on port $PORT"
        echo "Use 'pkill -f uvicorn' to stop it first"
        exit 1
    fi

    # Check by PID file
    if [[ -f "$PIDFILE" ]]; then
        local pid=$(cat "$PIDFILE")
        if ps -p "$pid" > /dev/null 2>&1; then
            echo "⚠️  Web server is already running (PID: $pid)"
            echo "Use 'kill $pid' to stop it first"
            exit 1
        else
            # Stale PID file
            rm -f "$PIDFILE"
        fi
    fi
}

# Function to cleanup on exit
cleanup() {
    rm -f "$PIDFILE"
}

# Set trap for cleanup
trap cleanup EXIT

echo "🚀 Starting News Web Server on port $PORT..."

# Check for existing processes
check_existing_process

# Activate virtual environment
if [[ ! -d "venv" ]]; then
    echo "❌ Virtual environment not found at $PROJECT_ROOT/venv"
    exit 1
fi

source venv/bin/activate
export PYTHONPATH="$PROJECT_ROOT"

# Store PID and start server
echo $$ > "$PIDFILE"
echo "✅ Web server starting (PID: $$)"

exec python3 -m uvicorn app.main:app --host 0.0.0.0 --port $PORT --reload