#!/bin/bash

# Stop Docker services
set -e

echo "🛑 Stopping News-MCP Docker Services..."

docker compose --env-file .env.docker down

echo ""
echo "✅ All services stopped!"