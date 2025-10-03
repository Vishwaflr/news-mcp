#!/bin/bash
# Start all News MCP services

set -e

GREEN='\033[0;32m'
NC='\033[0m'

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

echo "Starting all News MCP services..."
echo "================================"
echo ""

# Start API server
./scripts/start-api.sh

echo ""

# Start Analysis Worker
./scripts/start-worker.sh

echo ""

# Start Feed Scheduler
./scripts/start-scheduler.sh

echo ""
echo -e "${GREEN}================================${NC}"
echo -e "${GREEN}All services started!${NC}"
echo ""
echo "Access points:"
echo "  - Web UI:  http://$(grep API_HOST .env | cut -d= -f2):$(grep API_PORT .env | cut -d= -f2)/"
echo "  - API Docs: http://$(grep API_HOST .env | cut -d= -f2):$(grep API_PORT .env | cut -d= -f2)/docs"
echo ""
echo "To stop all services: ./scripts/stop-all.sh"
echo "To view logs: tail -f logs/api.log"
