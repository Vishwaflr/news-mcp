#!/bin/bash
# Start News MCP API Server (Stable/Production Mode)
# This version runs without --reload for better stability

set -e

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

echo "Starting News MCP API Server (Stable Mode)..."

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

# Check if already running
if pgrep -f "uvicorn app.main:app" > /dev/null; then
    RUNNING_PID=$(pgrep -f 'uvicorn app.main:app' | head -1)
    echo -e "${YELLOW}API server is already running!${NC}"
    echo "PID: $RUNNING_PID"
    echo "Use './scripts/stop-all.sh' to stop it first"
    exit 1
fi

# Configure uvicorn options for stability
WORKERS=${UVICORN_WORKERS:-2}  # Multiple workers for resilience
HOST="${API_HOST:-0.0.0.0}"
PORT="${API_PORT:-8000}"
LOG_LEVEL="${LOG_LEVEL:-info}"

echo -e "${GREEN}Starting uvicorn with:${NC}"
echo "  Host: $HOST:$PORT"
echo "  Workers: $WORKERS"
echo "  Log Level: $LOG_LEVEL"
echo "  Mode: Production (no auto-reload)"
echo ""

# Start API server with multiple workers and no reload
# Using --workers automatically disables --reload
nohup uvicorn app.main:app \
    --host "$HOST" \
    --port "$PORT" \
    --workers "$WORKERS" \
    --log-level "$LOG_LEVEL" \
    --access-log \
    --use-colors \
    > logs/api-stable.log 2>&1 &

API_PID=$!
echo $API_PID > /tmp/news-mcp-api.pid

# Wait a moment and check if it started successfully
sleep 3

if ps -p $API_PID > /dev/null; then
    echo -e "${GREEN}✓ API server started successfully in STABLE mode!${NC}"
    echo "PID: $API_PID"
    echo "URL: http://$HOST:$PORT"
    echo "Logs: $PROJECT_DIR/logs/api-stable.log"
    echo ""
    echo -e "${GREEN}Features:${NC}"
    echo "  • Multiple workers for resilience"
    echo "  • No auto-reload (stable)"
    echo "  • Better performance"
    echo "  • Automatic worker restart on failure"
else
    echo -e "${RED}✗ Failed to start API server. Check logs/api-stable.log${NC}"
    tail -20 logs/api-stable.log
    exit 1
fi