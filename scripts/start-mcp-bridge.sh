#!/bin/bash
# Start MCP HTTP Bridge Server for Windows clients

cd /home/cytrex/news-mcp

source venv/bin/activate
export PYTHONPATH='/home/cytrex/news-mcp'

echo "Starting MCP HTTP Bridge on port 3001..."
python mcp_http_server.py