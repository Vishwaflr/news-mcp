#!/bin/bash

# Stop All Services Script
# Gracefully stops all News MCP services

PROJECT_ROOT="/home/cytrex/news-mcp"

echo "🛑 Stopping all News MCP services..."

# Function to stop a service
stop_service() {
    local service_name="$1"
    local pidfile="$2"
    local process_pattern="$3"
    local port="$4"

    echo "🔄 Stopping $service_name..."

    local stopped=false

    # Try to stop using PID file first (most accurate)
    if [[ -f "$pidfile" ]]; then
        local pid=$(cat "$pidfile")
        if ps -p "$pid" > /dev/null 2>&1; then
            kill "$pid" 2>/dev/null
            sleep 1
            if ! ps -p "$pid" > /dev/null 2>&1; then
                echo "✅ $service_name stopped (PID: $pid)"
                stopped=true
            else
                # Try SIGKILL if SIGTERM didn't work
                kill -9 "$pid" 2>/dev/null
                echo "✅ $service_name force stopped (PID: $pid)"
                stopped=true
            fi
        fi
        rm -f "$pidfile"
    fi

    # Also kill by process pattern to catch any strays
    if pgrep -f "$process_pattern" > /dev/null; then
        pkill -f "$process_pattern"
        echo "✅ $service_name processes stopped by pattern"
        stopped=true
    fi

    # Kill by port if specified
    if [[ -n "$port" ]]; then
        local pid=$(netstat -tlnp 2>/dev/null | grep ":$port " | awk '{print $7}' | cut -d'/' -f1)
        if [[ -n "$pid" ]]; then
            kill "$pid" 2>/dev/null && echo "✅ Process on port $port stopped"
            stopped=true
        fi
    fi

    if [[ "$stopped" == "false" ]]; then
        echo "ℹ️  $service_name was not running"
    fi
}

# Stop all services
stop_service "Web Server" \
    "$PROJECT_ROOT/.web-server.pid" \
    "uvicorn.*app.main:app" \
    "8000"

stop_service "MCP HTTP Server" \
    "$PROJECT_ROOT/.mcp-server-http.pid" \
    "http_mcp_server" \
    "8001"

stop_service "MCP STDIO Server" \
    "$PROJECT_ROOT/.mcp-server-stdio.pid" \
    "mcp_server/server.py" \
    ""

stop_service "Analysis Worker" \
    "$PROJECT_ROOT/.analysis-worker.pid" \
    "analysis_worker" \
    ""

stop_service "Feed Scheduler" \
    "$PROJECT_ROOT/.feed-scheduler.pid" \
    "feed_scheduler" \
    ""

# Clean up any remaining PID files (in case of crashes)
echo "🧹 Cleaning up PID files..."
rm -f "$PROJECT_ROOT"/.*.pid

echo "✨ All services stopped successfully"