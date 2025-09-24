#!/bin/bash

# Check status of all News MCP services
# Shows running processes, ports, and PID files

PROJECT_ROOT="/home/cytrex/news-mcp"

echo "📊 News MCP Service Status"
echo "=========================="
echo ""

# Function to check service status
check_service() {
    local service_name="$1"
    local pidfile="$2"
    local port="$3"
    local process_pattern="$4"

    echo "🔍 $service_name:"

    # Check PID file
    if [[ -f "$pidfile" ]]; then
        local pid=$(cat "$pidfile")
        if ps -p "$pid" > /dev/null 2>&1; then
            echo "   ✅ Running (PID: $pid from pidfile)"
            # Show process details
            ps -p "$pid" -o pid,ppid,user,start,time,cmd --no-headers | sed 's/^/   /'
        else
            echo "   ⚠️  PID file exists but process not running (stale PID: $pid)"
        fi
    else
        echo "   📄 No PID file"
    fi

    # Check by process pattern
    local running_pids=$(pgrep -f "$process_pattern" 2>/dev/null)
    if [[ -n "$running_pids" ]]; then
        echo "   🔄 Found by pattern: PIDs $running_pids"
    fi

    # Check port if specified
    if [[ -n "$port" ]]; then
        if netstat -tlnp 2>/dev/null | grep -q ":$port " || ss -tlnp 2>/dev/null | grep -q ":$port "; then
            echo "   🌐 Port $port is in use"
        else
            echo "   ⭕ Port $port is free"
        fi
    fi

    echo ""
}

# Check each service
check_service "Web Server" \
    "$PROJECT_ROOT/.web-server.pid" \
    "8000" \
    "uvicorn.*app.main:app"

check_service "MCP HTTP Server" \
    "$PROJECT_ROOT/.mcp-server-http.pid" \
    "8001" \
    "http_mcp_server"

check_service "Feed Scheduler" \
    "$PROJECT_ROOT/.feed-scheduler.pid" \
    "" \
    "feed_scheduler"

check_service "Analysis Worker" \
    "$PROJECT_ROOT/.analysis-worker.pid" \
    "" \
    "analysis_worker"

# Show orphaned processes
echo "🔍 Checking for orphaned processes..."
echo ""

# Find any python processes in the project directory
orphans=$(ps aux | grep -E "python.*$PROJECT_ROOT" | grep -v grep | grep -v "status.sh")
if [[ -n "$orphans" ]]; then
    echo "⚠️  Found possible orphaned processes:"
    echo "$orphans" | while read line; do
        echo "   $line"
    done
else
    echo "✅ No orphaned processes found"
fi

echo ""
echo "="
echo "📝 Log files:"
if [[ -d "$PROJECT_ROOT/logs" ]]; then
    ls -lah "$PROJECT_ROOT/logs/"*.log 2>/dev/null | tail -5 || echo "   No log files found"
fi

echo ""
echo "💡 Commands:"
echo "   Start all: ./scripts/start-all-background.sh"
echo "   Stop all:  ./scripts/stop-all.sh"
echo "   View logs: tail -f logs/*.log"