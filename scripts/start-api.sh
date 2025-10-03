#!/bin/bash
# Start News MCP API Server

set -e

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

echo "Starting News MCP API Server..."

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

# Load environment variables (skip comments and empty lines)
while IFS='=' read -r key value; do
    # Skip comments and empty lines
    if [[ ! "$key" =~ ^[[:space:]]*# && -n "$key" ]]; then
        export "$key=$value"
    fi
done < <(grep -v '^[[:space:]]*#' .env | grep -v '^[[:space:]]*$')

# Activate virtual environment
source venv/bin/activate

# Check if already running (clean check with actual process verification)
if [ -f /tmp/news-mcp-api.pid ]; then
    OLD_PID=$(cat /tmp/news-mcp-api.pid)
    if ps -p $OLD_PID > /dev/null 2>&1 && ps -p $OLD_PID | grep -q "uvicorn"; then
        echo -e "${RED}API server is already running!${NC}"
        echo "PID: $OLD_PID"
        exit 1
    else
        # Stale PID file, clean it up
        rm /tmp/news-mcp-api.pid
    fi
fi

# Double check with pgrep
if pgrep -f "uvicorn app.main:app" > /dev/null; then
    RUNNING_PID=$(pgrep -f 'uvicorn app.main:app' | head -1)
    echo -e "${RED}API server is already running!${NC}"
    echo "PID: $RUNNING_PID"
    echo "Use './scripts/stop-all.sh' to stop it first"
    exit 1
fi

# Start API server
echo "Starting uvicorn on ${API_HOST:-0.0.0.0}:${API_PORT:-8000}..."

nohup uvicorn app.main:app \
    --host "${API_HOST:-0.0.0.0}" \
    --port "${API_PORT:-8000}" \
    --reload \
    > logs/api.log 2>&1 &

API_PID=$!
echo $API_PID > /tmp/news-mcp-api.pid

# Wait a moment and check if it started successfully
sleep 2

if ps -p $API_PID > /dev/null; then
    echo -e "${GREEN}✓ API server started successfully!${NC}"
    echo "PID: $API_PID"
    echo "URL: http://${API_HOST:-0.0.0.0}:${API_PORT:-8000}"
    echo "Logs: $PROJECT_DIR/logs/api.log"
else
    echo -e "${RED}✗ Failed to start API server. Check logs/api.log${NC}"
    exit 1
fi
