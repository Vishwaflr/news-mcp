#!/bin/bash

# Stop All Services Script
# Gracefully stops all News MCP services

echo "🛑 Stopping all News MCP services..."

# Function to stop a service
stop_service() {
    local service_name="$1"
    local process_pattern="$2"
    local port="$3"

    echo "🔄 Stopping $service_name..."

    # Kill by process pattern
    if pgrep -f "$process_pattern" > /dev/null; then
        pkill -f "$process_pattern"
        echo "✅ $service_name stopped"
    else
        echo "ℹ️  $service_name was not running"
    fi

    # Kill by port if specified
    if [[ -n "$port" ]]; then
        local pid=$(netstat -tlnp 2>/dev/null | grep ":$port " | awk '{print $7}' | cut -d'/' -f1)
        if [[ -n "$pid" ]]; then
            kill "$pid" 2>/dev/null && echo "✅ Process on port $port stopped"
        fi
    fi
}

# Stop all services
stop_service "Web Server" "uvicorn" "8000"
stop_service "MCP HTTP Server" "http_mcp_server" "8001"
stop_service "MCP STDIO Server" "mcp_server/server.py"
stop_service "Analysis Worker" "analysis_worker"
stop_service "Feed Scheduler" "feed_scheduler"

# Clean up PID files
echo "🧹 Cleaning up PID files..."
rm -f /home/cytrex/news-mcp/.web-server.pid
rm -f /home/cytrex/news-mcp/.mcp-server-http.pid
rm -f /home/cytrex/news-mcp/.mcp-server-stdio.pid
rm -f /home/cytrex/news-mcp/.analysis-worker.pid
rm -f /home/cytrex/news-mcp/.feed-scheduler.pid

echo "✨ All services stopped successfully"