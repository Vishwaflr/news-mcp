#!/usr/bin/env python3
"""
HTTP Bridge Server for News MCP
Exposes MCP tools via HTTP API for Windows Bridge access
"""

import asyncio
import json
import logging
import sys
import os
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import uvicorn

# Add the project root to the path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from mcp_server.comprehensive_server import ComprehensiveNewsServer

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI(title="News MCP HTTP Bridge", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global MCP server instance
mcp_server = None

class MCPRequest(BaseModel):
    method: str
    params: Dict[str, Any] = {}

class MCPResponse(BaseModel):
    result: Any = None
    error: Optional[str] = None

@app.on_event("startup")
async def startup_event():
    global mcp_server
    logger.info("Initializing News MCP Server...")
    os.environ["PYTHONPATH"] = str(project_root)
    mcp_server = ComprehensiveNewsServer()
    logger.info("News MCP HTTP Bridge ready on port 3000")

@app.get("/")
async def root():
    return {"status": "News MCP HTTP Bridge running", "version": "1.0.0"}

@app.get("/tools")
async def list_tools():
    """List available MCP tools dynamically from the MCP server"""
    try:
        global mcp_server
        if not mcp_server:
            raise HTTPException(status_code=500, detail="MCP server not initialized")

        # Get actual tool definitions from MCP server
        # These are the actual tools available in ComprehensiveNewsServer
        available_tools = [
            # Feed Management
            {"name": "list_feeds", "description": "List all RSS feeds with status, metrics and health info"},
            {"name": "add_feed", "description": "Add new RSS feed with automatic template detection"},
            {"name": "update_feed", "description": "Update feed configuration (interval, status, title)"},
            {"name": "delete_feed", "description": "Remove feeds and all associated articles"},
            {"name": "test_feed", "description": "Test feed URLs without adding them"},
            {"name": "refresh_feed", "description": "Manually trigger feed updates"},

            # Analytics & Statistics
            {"name": "get_dashboard", "description": "Comprehensive dashboard statistics"},
            {"name": "feed_performance", "description": "Analyze feed performance over time"},
            {"name": "latest_articles", "description": "Get recent articles with filtering"},
            {"name": "search_articles", "description": "Full-text search across articles"},
            {"name": "trending_topics", "description": "Analyze trending keywords and topics"},
            {"name": "export_data", "description": "Export data in JSON/CSV formats"},

            # Template Management
            {"name": "list_templates", "description": "List dynamic feed templates"},
            {"name": "template_performance", "description": "Analyze template usage and performance"},
            {"name": "assign_template", "description": "Assign templates to feeds (manual or auto)"},

            # Database Operations
            {"name": "execute_query", "description": "Execute safe read-only SQL queries"},
            {"name": "table_info", "description": "Get database table structure and info"},
            {"name": "quick_queries", "description": "Predefined useful queries (summary, stats, errors)"},

            # Health Monitoring
            {"name": "system_health", "description": "Overall system health status"},
            {"name": "feed_diagnostics", "description": "Detailed feed health analysis"},
            {"name": "error_analysis", "description": "Analyze system errors and failures"},
            {"name": "scheduler_status", "description": "Check feed scheduler status"},

            # Administration
            {"name": "maintenance_tasks", "description": "System maintenance (cleanup, vacuum, etc.)"},
            {"name": "log_analysis", "description": "Analyze system logs for patterns"},
            {"name": "usage_stats", "description": "System usage statistics and metrics"}
        ]

        return {"tools": available_tools, "total": len(available_tools)}

    except Exception as e:
        logger.error(f"Error listing tools: {e}")
        return {"tools": [], "error": str(e)}

@app.post("/call")
async def call_tool(request: MCPRequest):
    """Call an MCP tool"""
    try:
        global mcp_server
        if not mcp_server:
            raise HTTPException(status_code=500, detail="MCP server not initialized")

        # Route to appropriate tool method
        method_name = f"_{request.method}"
        if hasattr(mcp_server, method_name):
            method = getattr(mcp_server, method_name)
            result = await method(**request.params)

            # Extract text content from MCP TextContent response
            if result and len(result) > 0 and hasattr(result[0], 'text'):
                response_text = result[0].text
                try:
                    # Try to parse as JSON for structured data
                    parsed_result = json.loads(response_text)
                    return MCPResponse(result=parsed_result)
                except json.JSONDecodeError:
                    # Return as plain text if not JSON
                    return MCPResponse(result={"text": response_text})
            else:
                return MCPResponse(result={"text": "No result returned"})
        else:
            return MCPResponse(error=f"Unknown method: {request.method}")

    except Exception as e:
        logger.error(f"Error calling tool {request.method}: {e}")
        return MCPResponse(error=str(e))

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "news-mcp-bridge"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=3001)