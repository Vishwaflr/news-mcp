#!/bin/bash
# Stop all News MCP services

set -e

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "Stopping News MCP services..."

# Stop API server
if [ -f /tmp/news-mcp-api.pid ]; then
    API_PID=$(cat /tmp/news-mcp-api.pid)
    if ps -p $API_PID > /dev/null 2>&1; then
        echo "Stopping API server (PID: $API_PID)..."
        kill $API_PID
        # Wait for process to actually terminate (max 5 seconds)
        for i in {1..10}; do
            if ! ps -p $API_PID > /dev/null 2>&1; then
                break
            fi
            sleep 0.5
        done
        # Force kill if still running
        if ps -p $API_PID > /dev/null 2>&1; then
            echo "Process still running, force killing..."
            kill -9 $API_PID
            sleep 1
        fi
        rm /tmp/news-mcp-api.pid
        echo -e "${GREEN}✓ API server stopped${NC}"
    else
        echo -e "${YELLOW}API server not running (stale PID file)${NC}"
        rm /tmp/news-mcp-api.pid
    fi
else
    # Try to find and kill any running uvicorn process
    if pgrep -f "uvicorn app.main:app" > /dev/null; then
        echo "Found running API server, stopping..."
        pkill -f "uvicorn app.main:app"
        sleep 2
        echo -e "${GREEN}✓ API server stopped${NC}"
    else
        echo "No API server running"
    fi
fi

# Stop Worker
if [ -f /tmp/news-mcp-worker.pid ]; then
    WORKER_PID=$(cat /tmp/news-mcp-worker.pid)
    if ps -p $WORKER_PID > /dev/null 2>&1; then
        echo "Stopping analysis worker (PID: $WORKER_PID)..."
        kill $WORKER_PID
        # Wait for process to actually terminate (max 5 seconds)
        for i in {1..10}; do
            if ! ps -p $WORKER_PID > /dev/null 2>&1; then
                break
            fi
            sleep 0.5
        done
        # Force kill if still running
        if ps -p $WORKER_PID > /dev/null 2>&1; then
            echo "Process still running, force killing..."
            kill -9 $WORKER_PID
            sleep 1
        fi
        rm /tmp/news-mcp-worker.pid
        echo -e "${GREEN}✓ Analysis worker stopped${NC}"
    else
        echo -e "${YELLOW}Analysis worker not running (stale PID file)${NC}"
        rm /tmp/news-mcp-worker.pid
    fi
else
    # Try to find and kill any running worker process
    if pgrep -f "python.*analysis_worker" > /dev/null; then
        echo "Found running analysis worker, stopping..."
        pkill -f "python.*analysis_worker"
        sleep 2
        echo -e "${GREEN}✓ Analysis worker stopped${NC}"
    else
        echo "No analysis worker running"
    fi
fi

# Stop Scheduler
if [ -f /tmp/news-mcp-scheduler.pid ]; then
    SCHEDULER_PID=$(cat /tmp/news-mcp-scheduler.pid)
    if ps -p $SCHEDULER_PID > /dev/null 2>&1; then
        echo "Stopping feed scheduler (PID: $SCHEDULER_PID)..."
        kill $SCHEDULER_PID
        # Wait for process to actually terminate (max 5 seconds)
        for i in {1..10}; do
            if ! ps -p $SCHEDULER_PID > /dev/null 2>&1; then
                break
            fi
            sleep 0.5
        done
        # Force kill if still running
        if ps -p $SCHEDULER_PID > /dev/null 2>&1; then
            echo "Process still running, force killing..."
            kill -9 $SCHEDULER_PID
            sleep 1
        fi
        rm /tmp/news-mcp-scheduler.pid
        echo -e "${GREEN}✓ Feed scheduler stopped${NC}"
    else
        echo -e "${YELLOW}Feed scheduler not running (stale PID file)${NC}"
        rm /tmp/news-mcp-scheduler.pid
    fi
else
    # Try to find and kill any running scheduler process
    if pgrep -f "python.*scheduler_runner" > /dev/null; then
        echo "Found running feed scheduler, stopping..."
        pkill -f "python.*scheduler_runner"
        sleep 2
        echo -e "${GREEN}✓ Feed scheduler stopped${NC}"
    else
        echo "No feed scheduler running"
    fi
fi

echo -e "${GREEN}All services stopped${NC}"
