#!/bin/bash
cd /home/cytrex/news-mcp
source venv/bin/activate
export PYTHONPATH=/home/cytrex/news-mcp
exec python mcp_server/server.py