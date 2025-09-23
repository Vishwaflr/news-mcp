#!/bin/bash

# News MCP Server Start Script
# Usage: ./start_mcp_server.sh [mode]
# Modes:
#   stdio (default) - Traditional MCP server for Claude Desktop
#   http           - HTTP MCP server for Open WebUI integration
# Prevents multiple instances from running

set -e

MODE=${1:-stdio}
PROJECT_ROOT="/home/cytrex/news-mcp"
HTTP_PORT=8001
PIDFILE_HTTP="$PROJECT_ROOT/.mcp-server-http.pid"
PIDFILE_STDIO="$PROJECT_ROOT/.mcp-server-stdio.pid"

cd "$PROJECT_ROOT"

# Function to check if HTTP server is already running
check_existing_http_process() {
    # Check by port
    if netstat -tlnp 2>/dev/null | grep -q ":$HTTP_PORT "; then
        echo "⚠️  MCP HTTP server is already running on port $HTTP_PORT"
        echo "Use 'pkill -f http_mcp_server' to stop it first"
        exit 1
    fi

    # Check by PID file
    if [[ -f "$PIDFILE_HTTP" ]]; then
        local pid=$(cat "$PIDFILE_HTTP")
        if ps -p "$pid" > /dev/null 2>&1; then
            echo "⚠️  MCP HTTP server is already running (PID: $pid)"
            echo "Use 'kill $pid' to stop it first"
            exit 1
        else
            # Stale PID file
            rm -f "$PIDFILE_HTTP"
        fi
    fi
}

# Function to check if STDIO server is already running
check_existing_stdio_process() {
    # Check by process name
    if pgrep -f "mcp_server/server.py" > /dev/null; then
        echo "⚠️  MCP STDIO server is already running"
        echo "Use 'pkill -f mcp_server/server.py' to stop it first"
        exit 1
    fi

    # Check by PID file
    if [[ -f "$PIDFILE_STDIO" ]]; then
        local pid=$(cat "$PIDFILE_STDIO")
        if ps -p "$pid" > /dev/null 2>&1; then
            echo "⚠️  MCP STDIO server is already running (PID: $pid)"
            echo "Use 'kill $pid' to stop it first"
            exit 1
        else
            # Stale PID file
            rm -f "$PIDFILE_STDIO"
        fi
    fi
}

# Function to cleanup on exit
cleanup() {
    if [[ "$MODE" == "http" ]]; then
        rm -f "$PIDFILE_HTTP"
    else
        rm -f "$PIDFILE_STDIO"
    fi
}

# Set trap for cleanup
trap cleanup EXIT

# Activate virtual environment
if [[ ! -d "venv" ]]; then
    echo "❌ Virtual environment not found at $PROJECT_ROOT/venv"
    exit 1
fi

source venv/bin/activate
export PYTHONPATH="$PROJECT_ROOT"

case $MODE in
    "stdio")
        echo "🚀 Starting News MCP Server in STDIO mode (Claude Desktop)..."
        check_existing_stdio_process
        echo $$ > "$PIDFILE_STDIO"
        echo "✅ MCP STDIO server starting (PID: $$)"
        exec python mcp_server/server.py
        ;;
    "http")
        echo "🚀 Starting News MCP HTTP Server on port $HTTP_PORT (Open WebUI)..."
        check_existing_http_process
        echo $$ > "$PIDFILE_HTTP"
        echo "✅ MCP HTTP server starting (PID: $$)"
        exec python http_mcp_server.py
        ;;
    *)
        echo "❌ Invalid mode: $MODE"
        echo "Usage: $0 [stdio|http]"
        echo "  stdio - Traditional MCP server for Claude Desktop (default)"
        echo "  http  - HTTP MCP server for Open WebUI integration"
        exit 1
        ;;
esac