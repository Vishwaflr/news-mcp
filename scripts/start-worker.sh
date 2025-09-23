#!/bin/bash

# News Analysis Worker Startup Script
# Usage: ./scripts/start-worker.sh [--dry-run] [--verbose]
# Prevents multiple instances from running

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
WORKER_SCRIPT="$PROJECT_ROOT/app/worker/analysis_worker.py"
ENV_FILE="$PROJECT_ROOT/.env.worker"
PIDFILE="$PROJECT_ROOT/.analysis-worker.pid"

cd "$PROJECT_ROOT"

# Function to check if worker is already running
check_existing_process() {
    # Check by process name
    if pgrep -f "analysis_worker.py" > /dev/null; then
        echo "⚠️  Analysis worker is already running"
        echo "Use 'pkill -f analysis_worker.py' to stop it first"
        exit 1
    fi

    # Check by PID file
    if [[ -f "$PIDFILE" ]]; then
        local pid=$(cat "$PIDFILE")
        if ps -p "$pid" > /dev/null 2>&1; then
            echo "⚠️  Analysis worker is already running (PID: $pid)"
            echo "Use 'kill $pid' to stop it first"
            exit 1
        else
            # Stale PID file
            rm -f "$PIDFILE"
        fi
    fi
}

# Function to cleanup on exit
cleanup() {
    rm -f "$PIDFILE"
}

# Set trap for cleanup
trap cleanup EXIT

echo "🚀 Starting News Analysis Worker..."

# Check for existing processes
check_existing_process

# Check if virtual environment exists
if [[ ! -d "venv" ]]; then
    echo "❌ Virtual environment not found at $PROJECT_ROOT/venv"
    echo "Please create it first: python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt"
    exit 1
fi

# Check if worker script exists
if [[ ! -f "$WORKER_SCRIPT" ]]; then
    echo "❌ Worker script not found at $WORKER_SCRIPT"
    exit 1
fi

# Load environment variables if .env.worker exists
if [[ -f "$ENV_FILE" ]]; then
    export $(grep -v '^#' "$ENV_FILE" | xargs)
fi

# Set PYTHONPATH
export PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH"

echo "📁 Project Root: $PROJECT_ROOT"
echo "🐍 Worker Script: $WORKER_SCRIPT"
echo "🔧 Environment: $ENV_FILE"
echo "📋 Arguments: $@"
echo ""

# Store PID and activate virtual environment
echo $$ > "$PIDFILE"
source venv/bin/activate

echo "✅ Analysis worker starting (PID: $$)"
exec python "$WORKER_SCRIPT" "$@"