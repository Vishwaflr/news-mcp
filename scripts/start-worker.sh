#!/bin/bash

# News Analysis Worker Startup Script
# Usage: ./scripts/start-worker.sh [--dry-run] [--verbose]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
WORKER_SCRIPT="$PROJECT_ROOT/app/worker/analysis_worker.py"
ENV_FILE="$PROJECT_ROOT/.env.worker"

cd "$PROJECT_ROOT"

# Check if virtual environment exists
if [[ ! -d "venv" ]]; then
    echo "Error: Virtual environment not found at $PROJECT_ROOT/venv"
    echo "Please create it first: python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt"
    exit 1
fi

# Check if worker script exists
if [[ ! -f "$WORKER_SCRIPT" ]]; then
    echo "Error: Worker script not found at $WORKER_SCRIPT"
    exit 1
fi

# Load environment variables if .env.worker exists
if [[ -f "$ENV_FILE" ]]; then
    export $(grep -v '^#' "$ENV_FILE" | xargs)
fi

# Set PYTHONPATH
export PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH"

echo "Starting News Analysis Worker..."
echo "Project Root: $PROJECT_ROOT"
echo "Worker Script: $WORKER_SCRIPT"
echo "Environment: $ENV_FILE"
echo "Arguments: $@"
echo ""

# Activate virtual environment and start worker
source venv/bin/activate
exec python "$WORKER_SCRIPT" "$@"