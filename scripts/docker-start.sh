#!/bin/bash

# Start Docker services
set -e

echo "🐳 Starting News-MCP Docker Services..."

# Check if .env file exists
if [ ! -f .env.docker ]; then
    echo "⚠️  Warning: .env.docker not found. Using defaults..."
fi

# Use development compose if specified
if [ "$1" == "dev" ] || [ "$1" == "development" ]; then
    echo "📦 Starting in DEVELOPMENT mode with hot-reload..."
    docker compose -f docker-compose.yml -f docker-compose.dev.yml --env-file .env.docker up -d --build
else
    echo "📦 Starting in PRODUCTION mode..."
    docker compose --env-file .env.docker up -d --build
fi

echo ""
echo "⏳ Waiting for services to be healthy..."
sleep 5

# Check service status
docker compose ps

echo ""
echo "✅ Services started!"
echo ""
echo "📍 Access points:"
echo "   - API: http://localhost:8000"
echo "   - PostgreSQL: localhost:5432"
echo "   - Redis: localhost:6379"
echo ""
echo "📊 View logs: docker-compose logs -f [service]"
echo "🛑 Stop all: ./scripts/docker-stop.sh"