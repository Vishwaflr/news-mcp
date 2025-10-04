#!/bin/bash

# View logs for Docker services
SERVICE=$1
LINES=${2:-100}

if [ -z "$SERVICE" ]; then
    echo "📋 Showing logs for ALL services (last $LINES lines)..."
    docker compose --env-file .env.docker logs --tail=$LINES -f
else
    echo "📋 Showing logs for $SERVICE (last $LINES lines)..."
    docker compose --env-file .env.docker logs --tail=$LINES -f $SERVICE
fi