#!/bin/bash
cd /home/cytrex/news-mcp
source venv/bin/activate
export PYTHONPATH=/home/cytrex/news-mcp
exec python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload