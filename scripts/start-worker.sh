#!/bin/bash
# Start News MCP Analysis Worker

set -e

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

echo "Starting News MCP Analysis Worker..."

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
if [ -f /tmp/news-mcp-worker.pid ]; then
    OLD_PID=$(cat /tmp/news-mcp-worker.pid)
    if ps -p $OLD_PID > /dev/null 2>&1 && ps -p $OLD_PID | grep -q "analysis_worker"; then
        echo -e "${RED}Analysis worker is already running!${NC}"
        echo "PID: $OLD_PID"
        exit 1
    else
        # Stale PID file, clean it up
        rm /tmp/news-mcp-worker.pid
    fi
fi

# Double check with pgrep
if pgrep -f "python.*analysis_worker" > /dev/null; then
    RUNNING_PID=$(pgrep -f 'python.*analysis_worker' | head -1)
    echo -e "${RED}Analysis worker is already running!${NC}"
    echo "PID: $RUNNING_PID"
    echo "Use './scripts/stop-all.sh' to stop it first"
    exit 1
fi

# Start worker
echo "Starting analysis worker..."

nohup python -B app/worker/analysis_worker.py --verbose \
    > logs/worker.log 2>&1 &

WORKER_PID=$!
echo $WORKER_PID > /tmp/news-mcp-worker.pid

# Wait a moment and check if it started successfully
sleep 2

if ps -p $WORKER_PID > /dev/null; then
    echo -e "${GREEN}✓ Analysis worker started successfully!${NC}"
    echo "PID: $WORKER_PID"
    echo "Logs: $PROJECT_DIR/logs/worker.log"
else
    echo -e "${RED}✗ Failed to start worker. Check logs/worker.log${NC}"
    exit 1
fi
