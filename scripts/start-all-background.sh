#!/bin/bash

# Start all News MCP services in background mode
# Services will persist even after terminal/session closes

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

echo "🚀 Starting all News MCP services in background mode..."
echo "="
echo ""

# Function to start a service in background
start_service_background() {
    local service_name="$1"
    local pidfile="$2"
    local logfile="$3"
    local command="$4"

    # Check if already running
    if [[ -f "$pidfile" ]]; then
        local pid=$(cat "$pidfile")
        if ps -p "$pid" > /dev/null 2>&1; then
            echo "⚠️  $service_name already running (PID: $pid)"
            return 0
        else
            rm -f "$pidfile"
        fi
    fi

    echo "Starting $service_name..."

    # Start in background with nohup
    nohup bash -c "
        source venv/bin/activate
        export PYTHONPATH='$PROJECT_ROOT'
        $command
    " > "$logfile" 2>&1 &

    local pid=$!
    echo $pid > "$pidfile"

    # Check if started successfully
    sleep 2
    if ps -p $pid > /dev/null; then
        echo "✅ $service_name started (PID: $pid)"
    else
        echo "❌ $service_name failed to start - check $logfile"
        rm -f "$pidfile"
        return 1
    fi
}

# Ensure logs directory exists
mkdir -p "$PROJECT_ROOT/logs"

# Check virtual environment
if [[ ! -d "venv" ]]; then
    echo "❌ Virtual environment not found. Please set up first:"
    echo "   python3 -m venv venv"
    echo "   source venv/bin/activate"
    echo "   pip install -r requirements.txt"
    exit 1
fi

# Start Web Server
start_service_background \
    "Web Server" \
    "$PROJECT_ROOT/.web-server.pid" \
    "$PROJECT_ROOT/logs/web-server.log" \
    "uvicorn app.main:app --host 0.0.0.0 --port 8000"

# Start Feed Scheduler
start_service_background \
    "Feed Scheduler" \
    "$PROJECT_ROOT/.feed-scheduler.pid" \
    "$PROJECT_ROOT/logs/scheduler.log" \
    "python -c 'import asyncio; from app.services.feed_scheduler import start_scheduler; asyncio.run(start_scheduler())'"

# Start Analysis Worker
if [[ -f "$PROJECT_ROOT/app/worker/analysis_worker.py" ]]; then
    start_service_background \
        "Analysis Worker" \
        "$PROJECT_ROOT/.analysis-worker.pid" \
        "$PROJECT_ROOT/logs/analysis-worker.log" \
        "python app/worker/analysis_worker.py --verbose"
fi

# Optional: Start MCP Server (HTTP mode for Open WebUI)
read -p "Start MCP HTTP Server? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    start_service_background \
        "MCP HTTP Server" \
        "$PROJECT_ROOT/.mcp-server-http.pid" \
        "$PROJECT_ROOT/logs/mcp-http.log" \
        "uvicorn http_mcp_server:app --host 0.0.0.0 --port 8001"
fi

echo ""
echo "="
echo "✨ All services started in background mode"
echo ""
echo "📊 Status check: ps aux | grep -E 'uvicorn|scheduler|worker'"
echo "📝 View logs: tail -f logs/*.log"
echo "🛑 Stop all: ./scripts/stop-all.sh"
echo ""
echo "Services will continue running after you close this terminal!"