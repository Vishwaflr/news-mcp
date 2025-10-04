#!/bin/bash

# Restart specific service or all services
set -e

SERVICE=$1

if [ -z "$SERVICE" ]; then
    echo "🔄 Restarting ALL Docker services..."
    docker compose --env-file .env.docker restart
else
    echo "🔄 Restarting service: $SERVICE..."
    docker compose --env-file .env.docker restart $SERVICE
fi

echo ""
docker compose ps
echo ""
echo "✅ Restart complete!"