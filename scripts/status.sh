#!/bin/bash
# Check status of News MCP services

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "News MCP Service Status"
echo "======================="
echo ""

# Check API server
if pgrep -f "uvicorn app.main:app" > /dev/null; then
    API_PID=$(pgrep -f "uvicorn app.main:app")
    echo -e "${GREEN}✓ API Server: RUNNING${NC}"
    echo "  PID: $API_PID"

    # Try to get URL from .env
    if [ -f ".env" ]; then
        HOST=$(grep API_HOST .env | cut -d= -f2 | tr -d ' ')
        PORT=$(grep API_PORT .env | cut -d= -f2 | tr -d ' ')
        echo "  URL: http://${HOST:-0.0.0.0}:${PORT:-8000}"

        # Test if it responds
        if curl -s -o /dev/null -w "%{http_code}" "http://${HOST}:${PORT}/" | grep -q "200"; then
            echo -e "  Status: ${GREEN}Responding${NC}"
        else
            echo -e "  Status: ${YELLOW}Not responding${NC}"
        fi
    fi
else
    echo -e "${RED}✗ API Server: NOT RUNNING${NC}"
fi

echo ""

# Check Analysis Worker
if pgrep -f "python.*analysis_worker" > /dev/null; then
    WORKER_PID=$(pgrep -f "python.*analysis_worker")
    echo -e "${GREEN}✓ Analysis Worker: RUNNING${NC}"
    echo "  PID: $WORKER_PID"
else
    echo -e "${RED}✗ Analysis Worker: NOT RUNNING${NC}"
fi

echo ""

# Check Feed Scheduler
if pgrep -f "python.*scheduler_runner" > /dev/null; then
    SCHEDULER_PID=$(pgrep -f "python.*scheduler_runner")
    echo -e "${GREEN}✓ Feed Scheduler: RUNNING${NC}"
    echo "  PID: $SCHEDULER_PID"
else
    echo -e "${RED}✗ Feed Scheduler: NOT RUNNING${NC}"
fi

echo ""
echo "Recent API logs (last 3 lines):"
echo "--------------------------------"
if [ -f "logs/api.log" ]; then
    tail -3 logs/api.log | sed 's/^/  /'
else
    echo "  No API logs found"
fi

echo ""
echo "Recent Worker logs (last 3 lines):"
echo "-----------------------------------"
if [ -f "logs/worker.log" ]; then
    tail -3 logs/worker.log | sed 's/^/  /'
else
    echo "  No worker logs found"
fi

echo ""
echo "Recent Scheduler logs (last 3 lines):"
echo "--------------------------------------"
if [ -f "logs/scheduler.log" ]; then
    tail -3 logs/scheduler.log | sed 's/^/  /'
else
    echo "  No scheduler logs found"
fi
