#!/bin/bash
# Start News MCP Feed Scheduler

set -e

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

echo "Starting News MCP Feed Scheduler..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo -e "${RED}Error: Virtual environment not found. Run setup first.${NC}"
    exit 1
fi

# Check if .env exists
if [ ! -f ".env" ]; then
    echo -e "${RED}Error: .env file not found. Copy .env.example and configure it.${NC}"
    exit 1
fi

# Activate virtual environment
source venv/bin/activate

# Load environment variables (skip comments and empty lines)
while IFS='=' read -r key value; do
    # Skip comments and empty lines
    if [[ ! "$key" =~ ^[[:space:]]*# && -n "$key" ]]; then
        export "$key=$value"
    fi
done < <(grep -v '^[[:space:]]*#' .env | grep -v '^[[:space:]]*$')

# Check if already running (clean check with actual process verification)
if [ -f /tmp/news-mcp-scheduler.pid ]; then
    OLD_PID=$(cat /tmp/news-mcp-scheduler.pid)
    if ps -p $OLD_PID > /dev/null 2>&1 && ps -p $OLD_PID | grep -q "scheduler_runner"; then
        echo -e "${RED}Feed scheduler is already running!${NC}"
        echo "PID: $OLD_PID"
        exit 1
    else
        # Stale PID file, clean it up
        rm /tmp/news-mcp-scheduler.pid
    fi
fi

# Double check with pgrep
if pgrep -f "python.*scheduler_runner" > /dev/null; then
    RUNNING_PID=$(pgrep -f 'python.*scheduler_runner' | head -1)
    echo -e "${RED}Feed scheduler is already running!${NC}"
    echo "PID: $RUNNING_PID"
    echo "Use './scripts/stop-all.sh' to stop it first"
    exit 1
fi

# Start scheduler
echo "Starting feed scheduler..."

nohup python -B app/services/scheduler_runner.py \
    > logs/scheduler.log 2>&1 &

SCHEDULER_PID=$!
echo $SCHEDULER_PID > /tmp/news-mcp-scheduler.pid

# Wait a moment and check if it started successfully
sleep 2

if ps -p $SCHEDULER_PID > /dev/null; then
    echo -e "${GREEN}✓ Feed scheduler started successfully!${NC}"
    echo "PID: $SCHEDULER_PID"
    echo "Logs: $PROJECT_DIR/logs/scheduler.log"
else
    echo -e "${RED}✗ Failed to start scheduler. Check logs/scheduler.log${NC}"
    exit 1
fi
