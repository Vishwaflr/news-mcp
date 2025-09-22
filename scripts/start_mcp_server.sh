#!/bin/bash

# News MCP Server Start Script
# Usage: ./start_mcp_server.sh [mode]
# Modes:
#   stdio (default) - Traditional MCP server for Claude Desktop
#   http           - HTTP MCP server for Open WebUI integration

MODE=${1:-stdio}

cd /home/cytrex/news-mcp
source venv/bin/activate
export PYTHONPATH=/home/cytrex/news-mcp

case $MODE in
    "stdio")
        echo "Starting News MCP Server in STDIO mode (Claude Desktop)..."
        exec python mcp_server/server.py
        ;;
    "http")
        echo "Starting News MCP HTTP Server on port 8001 (Open WebUI)..."
        exec python http_mcp_server.py
        ;;
    *)
        echo "Invalid mode: $MODE"
        echo "Usage: $0 [stdio|http]"
        echo "  stdio - Traditional MCP server for Claude Desktop (default)"
        echo "  http  - HTTP MCP server for Open WebUI integration"
        exit 1
        ;;
esac