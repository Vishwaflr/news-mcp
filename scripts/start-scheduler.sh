#!/bin/bash

# Script to start the feed scheduler
# This should run in the background to automatically fetch feeds
# Prevents multiple instances from running

set -e

PROJECT_ROOT="/home/cytrex/news-mcp"
PIDFILE="$PROJECT_ROOT/.feed-scheduler.pid"

cd "$PROJECT_ROOT"

# Function to check if scheduler is already running
check_existing_process() {
    # Check by process name
    if pgrep -f "feed_scheduler" > /dev/null || pgrep -f "start_scheduler" > /dev/null; then
        echo "⚠️  Feed scheduler is already running"
        echo "Use 'pkill -f feed_scheduler' to stop it first"
        exit 1
    fi

    # Check by PID file
    if [[ -f "$PIDFILE" ]]; then
        local pid=$(cat "$PIDFILE")
        if ps -p "$pid" > /dev/null 2>&1; then
            echo "⚠️  Feed scheduler is already running (PID: $pid)"
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

echo "🚀 Starting Feed Scheduler..."

# Check for existing processes
check_existing_process

# Check if virtual environment exists
if [[ ! -d "venv" ]]; then
    echo "❌ Virtual environment not found at $PROJECT_ROOT/venv"
    exit 1
fi

# Store PID and activate virtual environment
echo $$ > "$PIDFILE"
source venv/bin/activate

# Set Python path
export PYTHONPATH="$PROJECT_ROOT"

echo "✅ Feed scheduler starting (PID: $$)"

# Start the scheduler with Python
exec python -c "
import asyncio
import logging
from app.services.feed_scheduler import start_scheduler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

print('📡 Feed Scheduler starting...')
try:
    asyncio.run(start_scheduler())
except KeyboardInterrupt:
    print('⏹️  Feed Scheduler stopped by user')
except Exception as e:
    print(f'❌ Feed Scheduler error: {e}')
    raise
"