#!/bin/bash

# Feed Scheduler - Background Mode with proper daemon handling
# This version runs the scheduler as a proper background daemon

set -e

PROJECT_ROOT="/home/cytrex/news-mcp"
PIDFILE="$PROJECT_ROOT/.feed-scheduler.pid"
LOGFILE="$PROJECT_ROOT/logs/scheduler.log"

cd "$PROJECT_ROOT"

# Ensure logs directory exists
mkdir -p "$PROJECT_ROOT/logs"

# Function to check if scheduler is already running
check_existing_process() {
    if [[ -f "$PIDFILE" ]]; then
        local pid=$(cat "$PIDFILE")
        if ps -p "$pid" > /dev/null 2>&1; then
            echo "⚠️  Feed scheduler is already running (PID: $pid)"
            echo "Use 'kill $pid' or './scripts/stop-all.sh' to stop it first"
            exit 1
        else
            # Stale PID file - clean it up
            rm -f "$PIDFILE"
        fi
    fi
}

# Check for existing processes
check_existing_process

# Check if virtual environment exists
if [[ ! -d "venv" ]]; then
    echo "❌ Virtual environment not found at $PROJECT_ROOT/venv"
    exit 1
fi

echo "🚀 Starting Feed Scheduler in background mode..."

# Start the scheduler in background with nohup
nohup bash -c "
    source venv/bin/activate
    export PYTHONPATH='$PROJECT_ROOT'

    python -c '
import asyncio
import logging
from app.services.feed_scheduler import start_scheduler

# Configure logging to file
logging.basicConfig(
    level=logging.INFO,
    format=\"%(asctime)s - %(name)s - %(levelname)s - %(message)s\",
    handlers=[
        logging.FileHandler(\"$LOGFILE\"),
        logging.StreamHandler()
    ]
)

print(\"📡 Feed Scheduler starting in background...\")
try:
    asyncio.run(start_scheduler())
except KeyboardInterrupt:
    print(\"⏹️  Feed Scheduler stopped by user\")
except Exception as e:
    print(f\"❌ Feed Scheduler error: {e}\")
    raise
'
" > "$LOGFILE" 2>&1 &

# Get the PID of the background process
SCHEDULER_PID=$!

# Save the correct PID
echo $SCHEDULER_PID > "$PIDFILE"

# Give it a moment to start
sleep 2

# Check if it's still running
if ps -p $SCHEDULER_PID > /dev/null; then
    echo "✅ Feed scheduler started successfully (PID: $SCHEDULER_PID)"
    echo "📝 Logs: tail -f $LOGFILE"
    echo "🛑 Stop: kill $SCHEDULER_PID or ./scripts/stop-all.sh"
else
    echo "❌ Feed scheduler failed to start"
    echo "Check logs: $LOGFILE"
    rm -f "$PIDFILE"
    exit 1
fi