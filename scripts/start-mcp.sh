#!/bin/bash
# Start News MCP Server (JSON-RPC over HTTP)

set -e

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

echo "Starting News MCP Server..."

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
if [ -f /tmp/news-mcp-server.pid ]; then
    OLD_PID=$(cat /tmp/news-mcp-server.pid)
    if ps -p $OLD_PID > /dev/null 2>&1 && ps -p $OLD_PID | grep -q "http_mcp_server"; then
        echo -e "${RED}MCP server is already running!${NC}"
        echo "PID: $OLD_PID"
        exit 1
    else
        # Stale PID file, clean it up
        rm /tmp/news-mcp-server.pid
    fi
fi

# Double check with pgrep
if pgrep -f "python.*http_mcp_server" > /dev/null; then
    RUNNING_PID=$(pgrep -f 'python.*http_mcp_server' | head -1)
    echo -e "${RED}MCP server is already running!${NC}"
    echo "PID: $RUNNING_PID"
    echo "Use './scripts/stop-all.sh' to stop it first"
    exit 1
fi

# Start MCP server
echo "Starting MCP server on ${API_HOST:-0.0.0.0}:${MCP_PORT:-8001}..."

nohup python http_mcp_server.py \
    > logs/mcp-server.log 2>&1 &

MCP_PID=$!
echo $MCP_PID > /tmp/news-mcp-server.pid

# Wait a moment and check if it started successfully
sleep 2

if ps -p $MCP_PID > /dev/null; then
    echo -e "${GREEN}✓ MCP server started successfully!${NC}"
    echo "PID: $MCP_PID"
    echo "URL: http://${API_HOST:-0.0.0.0}:${MCP_PORT:-8001}"
    echo "OpenAPI: http://${API_HOST:-0.0.0.0}:${MCP_PORT:-8001}/mcp/openapi.json"
    echo "Logs: $PROJECT_DIR/logs/mcp-server.log"
else
    echo -e "${RED}✗ Failed to start MCP server. Check logs/mcp-server.log${NC}"
    exit 1
fi
