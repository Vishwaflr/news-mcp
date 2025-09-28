#!/usr/bin/env python3
"""
HTTP MCP Server for News MCP System
Dynamic MCP→REST exporter for Open WebUI

Provides JSON-RPC over HTTP interface + OpenAPI REST endpoints for News-MCP system

Features:
- JSON-RPC 2.0 over HTTP at /mcp
- OpenAPI specification at /mcp/openapi.json (for Open WebUI integration)
- Dynamic REST endpoints for ALL MCP tools at /tools/{tool_name}
- Documentation UI at /docs

Open WebUI Integration:
- Point Open WebUI to: http://localhost:8001/mcp/openapi.json
- For new MCP-Tools: REST routes appear automatically after restart

Dynamic Tool Mapping:
- Each MCP tool gets its own REST endpoint: POST /tools/{tool_name}
- tool_name format: <namespace>.<name> (e.g., "templates.create")
- Body: generic JSON object with MCP tool parameters
- Response: {ok, data, meta, errors} format
"""

import asyncio
import json
import logging
import sys
import os
from pathlib import Path
from typing import Any, Dict, Optional, List, Union
import typing

from fastapi import FastAPI, Request, HTTPException, Body, APIRouter
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, create_model

# Add the project root to the path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from mcp_server.comprehensive_server import ComprehensiveNewsServer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# FastAPI app instance
app = FastAPI(
    title="News MCP (HTTP)",
    description="HTTP endpoints & JSON-RPC bridge for news-mcp tools",
    version="1.0.0",
    openapi_url="/openapi.json",
    docs_url="/docs"
)

# Add CORS middleware for Open WebUI integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global MCP server instance
mcp_server_instance: Optional[ComprehensiveNewsServer] = None


class JSONRPCRequest(BaseModel):
    """JSON-RPC 2.0 Request model"""
    jsonrpc: str = "2.0"
    method: str
    params: Optional[Dict[str, Any]] = None
    id: Optional[str | int] = None


class JSONRPCResponse(BaseModel):
    """JSON-RPC 2.0 Response model"""
    jsonrpc: str = "2.0"
    result: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None
    id: Optional[str | int] = None


# REST API Response Models
class BaseResponse(BaseModel):
    """Standard response format for all REST endpoints"""
    ok: bool = Field(description="Success status")
    data: Union[Dict[str, Any], Any] = Field(description="Response data")
    meta: Dict[str, Any] = Field(default_factory=dict, description="Metadata")
    errors: List[str] = Field(default_factory=list, description="Error messages")


# REST API Input Models
class AnalysisPreviewIn(BaseModel):
    """Input model for analysis preview endpoint"""
    model: str = Field(description="AI model to use for analysis", example="gpt-4o-mini")
    selector: Dict[str, Any] = Field(description="Item selector criteria", example={"latest": 5})
    cost_estimate: bool = Field(default=True, description="Include cost estimation")


class HTTPMCPServerWrapper:
    """Wrapper class to handle HTTP-based MCP communication"""

    def __init__(self, mcp_server: ComprehensiveNewsServer):
        self.mcp_server = mcp_server
        # Store direct reference to the comprehensive server for tool access
        self.comprehensive_server = mcp_server

    async def handle_request(self, request: JSONRPCRequest) -> JSONRPCResponse:
        """Handle a JSON-RPC request and return response"""
        try:
            # Map JSON-RPC methods to MCP operations
            if request.method == "tools/list":
                # List available tools
                tools = await self._get_tools_list()
                return JSONRPCResponse(
                    id=request.id,
                    result={"tools": tools}
                )

            elif request.method == "system.ping":
                # Direct system ping method
                result = await self._call_tool("system_ping", {})
                return JSONRPCResponse(
                    id=request.id,
                    result=result
                )

            elif request.method == "tools/call":
                # Call a specific tool
                if not request.params:
                    raise ValueError("Missing parameters for tool call")

                tool_name = request.params.get("name")
                tool_arguments = request.params.get("arguments", {})

                if not tool_name:
                    raise ValueError("Missing tool name")

                result = await self._call_tool(tool_name, tool_arguments)
                return JSONRPCResponse(
                    id=request.id,
                    result=result
                )

            elif request.method == "initialize":
                # Initialize the connection
                return JSONRPCResponse(
                    id=request.id,
                    result={
                        "serverInfo": {
                            "name": "news-mcp-http",
                            "version": "1.0.0"
                        },
                        "capabilities": {
                            "tools": {}
                        }
                    }
                )

            else:
                # Unknown method
                return JSONRPCResponse(
                    id=request.id,
                    error={
                        "code": -32601,
                        "message": f"Method not found: {request.method}"
                    }
                )

        except Exception as e:
            logger.error(f"Error handling request: {e}")
            return JSONRPCResponse(
                id=request.id,
                error={
                    "code": -32603,
                    "message": f"Internal error: {str(e)}"
                }
            )

    async def _get_tools_list(self) -> list:
        """Get list of available tools from MCP server"""
        try:
            # Access the server's tool registry directly
            tools = []
            server = self.mcp_server.server

            # Use the list_tools handler if available
            if hasattr(server, '_list_tools_handler') and server._list_tools_handler:
                try:
                    tool_list = await server._list_tools_handler()
                    if tool_list:
                        for tool in tool_list:
                            tools.append({
                                "name": tool.name,
                                "description": tool.description,
                                "inputSchema": tool.inputSchema
                            })
                        return tools
                except Exception as e:
                    logger.warning(f"Could not get tools from list_tools handler: {e}")

            # Fallback: Get tool handlers from the server
            for tool_name, handler in server._tool_handlers.items():
                tool_info = {
                    "name": tool_name,
                    "description": f"MCP tool: {tool_name}",
                    "inputSchema": {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                }
                tools.append(tool_info)

            return tools

        except Exception as e:
            logger.error(f"Error getting tools list: {e}")
            return []

    async def _call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call a specific tool on the MCP server"""
        try:
            # Map tool calls to the comprehensive server methods directly
            # This bypasses the MCP protocol layer and calls methods directly

            tool_methods = {
                "system_ping": self.comprehensive_server._system_ping,
                "system_health": self.comprehensive_server._system_health,
                "list_feeds": self.comprehensive_server._list_feeds,
                "add_feed": self.comprehensive_server._add_feed,
                "update_feed": self.comprehensive_server._update_feed,
                "delete_feed": self.comprehensive_server._delete_feed,
                "test_feed": self.comprehensive_server._test_feed,
                "refresh_feed": self.comprehensive_server._refresh_feed,
                "feed_performance": self.comprehensive_server._feed_performance,
                "feed_diagnostics": self.comprehensive_server._feed_diagnostics,
                "latest_articles": self.comprehensive_server._latest_articles,
                "search_articles": self.comprehensive_server._search_articles,
                "assign_template": self.comprehensive_server._assign_template,
                "export_data": self.comprehensive_server._export_data
            }

            if tool_name not in tool_methods:
                raise ValueError(f"Tool not found: {tool_name}")

            # Call the method directly
            method = tool_methods[tool_name]
            result = await method(**arguments)

            # Format the result - result should be List[TextContent]
            if isinstance(result, list):
                content = []
                for item in result:
                    if hasattr(item, 'text'):
                        content.append({
                            "type": "text",
                            "text": item.text
                        })
                    else:
                        content.append({
                            "type": "text",
                            "text": str(item)
                        })
                return {
                    "content": content,
                    "isError": False
                }
            else:
                return {
                    "content": [{
                        "type": "text",
                        "text": str(result)
                    }],
                    "isError": False
                }

        except Exception as e:
            logger.error(f"Error calling tool {tool_name}: {e}")
            return {
                "content": [{
                    "type": "text",
                    "text": f"Error: {str(e)}"
                }],
                "isError": True
            }


# Common Tool Dispatch Function
async def tool_dispatch(tool_name: str, params: Dict[str, Any]) -> BaseResponse:
    """Common function to dispatch tool calls - used by both /tools/* and compatibility routes"""
    global mcp_server_instance

    if mcp_server_instance is None:
        return BaseResponse(
            ok=False,
            data={},
            meta={},
            errors=["MCP server not initialized"]
        )

    try:
        # Get tool registry and method
        tools_registry = get_mcp_tools_registry()

        if tool_name not in tools_registry:
            return BaseResponse(
                ok=False,
                data={},
                meta={"tool": tool_name},
                errors=[f"Tool not found: {tool_name}"]
            )

        tool_info = tools_registry[tool_name]

        # Filter out None values to let MCP method use its defaults
        params_dict = {k: v for k, v in params.items() if v is not None}

        # Call the MCP tool method directly
        method = tool_info["method"]
        result = await method(**params_dict)

        # Format result as MCP-style response
        if isinstance(result, list) and result:
            # Extract text from TextContent objects
            content = []
            for item in result:
                if hasattr(item, 'text'):
                    content.append(item.text)
                else:
                    content.append(str(item))

            return BaseResponse(
                ok=True,
                data={"content": content},
                meta={"tool": tool_name},
                errors=[]
            )
        else:
            return BaseResponse(
                ok=True,
                data={"result": str(result) if result else "success"},
                meta={"tool": tool_name},
                errors=[]
            )

    except Exception as e:
        logger.error(f"Error calling tool {tool_name}: {e}")
        return BaseResponse(
            ok=False,
            data={},
            meta={"tool": tool_name},
            errors=[str(e)]
        )


# Compatibility Router for paths without /tools prefix
compat = APIRouter()

# Alias mapping for compatibility routes
alias_map = {
    "/system/ping": "system.ping",
    "/system/health": "system.health",
    "/feeds/list": "feeds.list",
    "/feeds/add": "feeds.add",
    "/feeds/update": "feeds.update",
    "/feeds/delete": "feeds.delete",
    "/feeds/test": "feeds.test",
    "/feeds/refresh": "feeds.refresh",
    "/feeds/performance": "feeds.performance",
    "/feeds/diagnostics": "feeds.diagnostics",
    "/articles/latest": "articles.latest",
    "/articles/search": "articles.search",
    "/templates/assign": "templates.assign",
    "/data/export": "data.export",
    # Categories and Sources endpoints
    "/categories/list": "categories_list",
    "/categories/add": "categories_add",
    "/categories/update": "categories_update",
    "/categories/delete": "categories_delete",
    "/categories/assign": "categories_assign",
    "/sources/list": "sources_list",
    "/sources/add": "sources_add",
    "/sources/update": "sources_update",
    "/sources/delete": "sources_delete",
    # Extended Templates endpoints
    "/templates/list": "list_templates",
    "/templates/performance": "template_performance",
    "/templates/create": "templates_create",
    "/templates/test": "templates_test",
    "/templates/assign": "templates_assign",
    # AI Analysis Control endpoints
    "/analysis/preview": "analysis_preview",
    "/analysis/run": "analysis_run",
    "/analysis/history": "analysis_history",
    # Open WebUI prefix routes
    "/mcp/tools/system.ping": "system.ping",
    "/mcp/tools/system.health": "system.health",
    "/mcp/tools/feeds.list": "feeds.list",
    "/mcp/tools/feeds.add": "feeds.add",
    "/mcp/tools/feeds.update": "feeds.update",
    "/mcp/tools/feeds.delete": "feeds.delete",
    "/mcp/tools/feeds.test": "feeds.test",
    "/mcp/tools/feeds.refresh": "feeds.refresh",
    "/mcp/tools/feeds.performance": "feeds.performance",
    "/mcp/tools/feeds.diagnostics": "feeds.diagnostics",
    "/mcp/tools/articles.latest": "articles.latest",
    "/mcp/tools/articles.search": "articles.search",
    "/mcp/tools/templates.assign": "templates.assign",
    "/mcp/tools/data.export": "data.export",
    # Open WebUI prefix routes for Categories and Sources
    "/mcp/tools/categories_list": "categories_list",
    "/mcp/tools/categories_add": "categories_add",
    "/mcp/tools/categories_update": "categories_update",
    "/mcp/tools/categories_delete": "categories_delete",
    "/mcp/tools/categories_assign": "categories_assign",
    "/mcp/tools/sources_list": "sources_list",
    "/mcp/tools/sources_add": "sources_add",
    "/mcp/tools/sources_update": "sources_update",
    "/mcp/tools/sources_delete": "sources_delete",
    # Open WebUI prefix routes for Extended Templates
    "/mcp/tools/list_templates": "list_templates",
    "/mcp/tools/template_performance": "template_performance",
    "/mcp/tools/templates_create": "templates_create",
    "/mcp/tools/templates_test": "templates_test",
    "/mcp/tools/templates_assign": "templates_assign",
    # Open WebUI prefix routes for AI Analysis Control
    "/mcp/tools/analysis_preview": "analysis_preview",
    "/mcp/tools/analysis_run": "analysis_run",
    "/mcp/tools/analysis_history": "analysis_history",
    # Tools listing endpoints
    "/tools/list": "tools.list",
    "/mcp/tools/tools.list": "tools.list",
    # Additional OpenWebUI compatibility routes (without 'tools' in path)
    "/mcp/system/ping": "system.ping",
    "/mcp/system/health": "system.health",
    "/mcp/feeds/list": "feeds.list",
    "/mcp/feeds/add": "feeds.add",
    "/mcp/feeds/update": "feeds.update",
    "/mcp/feeds/delete": "feeds.delete",
    "/mcp/feeds/test": "feeds.test",
    "/mcp/feeds/refresh": "feeds.refresh",
    "/mcp/feeds/performance": "feeds.performance",
    "/mcp/feeds/diagnostics": "feeds.diagnostics",
    "/mcp/articles/latest": "articles.latest",
    "/mcp/articles/search": "articles.search",
    "/mcp/templates/assign": "templates.assign",
    "/mcp/data/export": "data.export",
    "/mcp/categories/list": "categories_list",
    "/mcp/categories/add": "categories_add",
    "/mcp/categories/update": "categories_update",
    "/mcp/categories/delete": "categories_delete",
    "/mcp/categories/assign": "categories_assign",
    "/mcp/sources/list": "sources_list",
    "/mcp/sources/add": "sources_add",
    "/mcp/sources/update": "sources_update",
    "/mcp/sources/delete": "sources_delete",
    "/mcp/templates/list": "list_templates",
    "/mcp/templates/performance": "template_performance",
    "/mcp/templates/create": "templates_create",
    "/mcp/templates/test": "templates_test",
    "/mcp/analysis/preview": "analysis_preview",
    "/mcp/analysis/run": "analysis_run",
    "/mcp/analysis/history": "analysis_history"
}

def register_compatibility_routes():
    """Register compatibility routes dynamically after MCP server is ready"""
    # Register compatibility routes dynamically
    for alias_path, tool_name in alias_map.items():
        # Extract namespace for tags
        namespace = tool_name.split('.')[0] if '.' in tool_name else "misc"

        # Create handler function with closure over tool_name
        def create_compat_handler(target_tool_name: str):
            async def compat_handler(request: Request):
                """Compatibility handler that forwards to tool_dispatch"""
                try:
                    # Parse JSON payload if present
                    if request.headers.get("content-type", "").startswith("application/json"):
                        payload = await request.json()
                    else:
                        payload = {}

                    # Dispatch to common tool handler
                    return await tool_dispatch(target_tool_name, payload)

                except Exception as e:
                    logger.error(f"Error in compatibility handler for {target_tool_name}: {e}")
                    return BaseResponse(
                        ok=False,
                        data={},
                        meta={"tool": target_tool_name},
                        errors=[str(e)]
                    )

            return compat_handler

        # Register the route (both POST and GET for maximum compatibility)
        compat.post(
            alias_path,
            response_model=BaseResponse,
            tags=["compat", namespace],
            summary=f"Compatibility endpoint for {tool_name}",
            description=f"Compatibility alias for /tools/{tool_name} - forwards requests to the main tool handler",
            operation_id=f"tool_endpoint_{tool_name.replace('.', '_')}_post"
        )(create_compat_handler(tool_name))

        # Also register GET route for Open WebUI compatibility
        compat.get(
            alias_path,
            response_model=BaseResponse,
            tags=["compat", namespace],
            summary=f"Compatibility endpoint for {tool_name} (GET)",
            description=f"GET compatibility alias for /tools/{tool_name} - forwards requests to the main tool handler",
            operation_id=f"tool_endpoint_{tool_name.replace('.', '_')}_get"
        )(create_compat_handler(tool_name))

        logger.info(f"Registered compatibility routes: POST/GET {alias_path} -> {tool_name}")


# Dynamic MCP Tool Registry and Route Generator
def get_mcp_tools_registry() -> Dict[str, Dict[str, Any]]:
    """Get all available MCP tools with their parameter schemas"""
    global mcp_server_instance

    if mcp_server_instance is None:
        return {}

    # Extract tools from the comprehensive server's method mapping
    tool_methods = {
        "system.ping": {"method": mcp_server_instance._system_ping, "params": [], "description": "Health check ping for connectivity testing"},
        "system.health": {"method": mcp_server_instance._system_health, "params": [], "description": "Overall system health status and diagnostics"},
        "feeds.list": {"method": mcp_server_instance._list_feeds, "params": ["status", "include_health", "include_stats", "limit"], "description": "List all RSS feed sources (NYT, Guardian, etc.) with status, metrics and health info"},
        "feeds.add": {"method": mcp_server_instance._add_feed, "params": ["url", "title", "fetch_interval_minutes", "auto_assign_template"], "description": "Add new RSS feed source with automatic template detection"},
        "feeds.update": {"method": mcp_server_instance._update_feed, "params": ["feed_id", "title", "fetch_interval_minutes", "status"], "description": "Update feed source configuration (title, interval, status)"},
        "feeds.delete": {"method": mcp_server_instance._delete_feed, "params": ["feed_id", "confirm"], "description": "Delete a feed source and all its articles"},
        "feeds.test": {"method": mcp_server_instance._test_feed, "params": ["url", "show_items"], "description": "Test RSS feed URL and preview items without adding"},
        "feeds.refresh": {"method": mcp_server_instance._refresh_feed, "params": ["feed_id"], "description": "Manually trigger immediate feed update to fetch new articles"},
        "feeds.performance": {"method": mcp_server_instance._feed_performance, "params": ["days", "limit"], "description": "Analyze feed source performance and efficiency metrics"},
        "feeds.diagnostics": {"method": mcp_server_instance._feed_diagnostics, "params": ["feed_id", "include_logs"], "description": "Detailed feed health analysis and error diagnostics"},
        "articles.latest": {"method": mcp_server_instance._latest_articles, "params": ["limit", "feed_id", "category_filter"], "description": "Get latest news articles from all feeds, sorted by publication date"},
        "articles.search": {"method": mcp_server_instance._search_articles, "params": ["query", "limit", "feed_id", "date_filter"], "description": "Full-text search across all news articles"},
        "templates.assign": {"method": mcp_server_instance._assign_template, "params": ["feed_id", "template_id", "auto_assign"], "description": "Assign content extraction template to a feed"},
        "data.export": {"method": mcp_server_instance._export_data, "params": ["format", "table", "limit"], "description": "Export data to JSON or CSV format"},
        # Categories Management
        "categories_list": {"method": mcp_server_instance._categories_list, "params": ["include_feeds", "include_stats"], "description": "List all article categories with feed assignments and statistics"},
        "categories_add": {"method": mcp_server_instance._categories_add, "params": ["name", "description", "color"], "description": "Create new category for organizing feeds"},
        "categories_update": {"method": mcp_server_instance._categories_update, "params": ["category_id", "name", "description", "color"], "description": "Update category properties (name, description, color)"},
        "categories_delete": {"method": mcp_server_instance._categories_delete, "params": ["category_id", "confirm"], "description": "Delete category (requires confirmation)"},
        "categories_assign": {"method": mcp_server_instance._categories_assign, "params": ["feed_id", "category_ids", "replace"], "description": "Assign categories to a specific feed"},
        # Sources Management
        "sources_list": {"method": mcp_server_instance._sources_list, "params": ["include_feeds", "include_stats"], "description": "List news publisher sources with trust ratings and metrics"},
        "sources_add": {"method": mcp_server_instance._sources_add, "params": ["name", "description", "url", "contact_email"], "description": "Add new news publisher source"},
        "sources_update": {"method": mcp_server_instance._sources_update, "params": ["source_id", "name", "description", "url", "contact_email"], "description": "Update news publisher source properties"},
        "sources_delete": {"method": mcp_server_instance._sources_delete, "params": ["source_id", "confirm"], "description": "Delete news publisher source (requires confirmation)"},
        # Extended Templates Management
        "list_templates": {"method": mcp_server_instance._list_templates, "params": ["include_performance", "include_assignments", "status_filter"], "description": "List content extraction templates with usage statistics"},
        "template_performance": {"method": mcp_server_instance._template_performance, "params": ["days", "template_id"], "description": "Analyze template extraction success rates and performance"},
        "templates_create": {"method": mcp_server_instance.v2_handlers.templates_create, "params": ["name", "description", "patterns", "processing_rules", "category_assignments"], "description": "Create new content extraction template with rules"},
        "templates_test": {"method": mcp_server_instance.v2_handlers.templates_test, "params": ["template_id", "test_feeds", "sample_size"], "description": "Test template against sample feeds to verify extraction rules"},
        "templates_assign": {"method": mcp_server_instance.v2_handlers.templates_assign, "params": ["template_id", "feed_id", "auto_assign"], "description": "Assign template to feed with optional auto-detection"},
        # AI Analysis Control
        "analysis_preview": {"method": mcp_server_instance.v2_handlers.analysis_preview, "params": ["selector", "model", "cost_estimate"], "description": "Preview AI sentiment analysis scope and cost estimate"},
        "analysis_run": {"method": mcp_server_instance.v2_handlers.analysis_run, "params": ["selector", "model", "limit", "dry_run"], "description": "Run AI sentiment analysis on selected articles"},
        "analysis_history": {"method": mcp_server_instance.v2_handlers.analysis_history, "params": ["limit", "offset", "status"], "description": "Get history of AI analysis runs with results"},
        "analysis_results": {"method": mcp_server_instance.v2_handlers.analysis_results, "params": ["run_id", "limit"], "description": "Get detailed sentiment results (scores, labels, topics) for a completed analysis run"},
        # Auto-Analysis Management
        "auto_analysis_status": {"method": mcp_server_instance._auto_analysis_status, "params": [], "description": "Get automatic sentiment analysis system status"},
        "auto_analysis_toggle": {"method": mcp_server_instance._auto_analysis_toggle, "params": ["feed_id", "enabled"], "description": "Enable or disable automatic analysis for a feed"},
        "auto_analysis_queue": {"method": mcp_server_instance._auto_analysis_queue, "params": ["limit"], "description": "View pending articles in automatic analysis queue"},
        "auto_analysis_history": {"method": mcp_server_instance._auto_analysis_history, "params": ["days", "limit"], "description": "Get automatic analysis processing history and results"},
        "auto_analysis_config": {"method": mcp_server_instance._auto_analysis_config, "params": ["max_runs_per_day", "max_items_per_run", "ai_model"], "description": "View or update automatic analysis system configuration"},
        "auto_analysis_stats": {"method": mcp_server_instance._auto_analysis_stats, "params": ["feed_id"], "description": "Get comprehensive automatic analysis statistics and metrics"},
        "tools.list": {"method": None, "params": [], "description": "List all available MCP tools with descriptions"}  # Special handler for listing tools
    }

    return tool_methods


def create_dynamic_tool_endpoint(tool_name: str, tool_info: Dict[str, Any]):
    """Create a dynamic FastAPI endpoint for an MCP tool"""

    # Create dynamic Pydantic model for parameters
    param_fields = {}
    for param in tool_info["params"]:
        # Make all parameters optional with default None
        param_fields[param] = (typing.Optional[typing.Any], None)

    if param_fields:
        ToolParamsModel = create_model(f"{tool_name.replace('.', '_').title()}Params", **param_fields)
    else:
        # Empty model for tools with no parameters
        class ToolParamsModel(BaseModel):
            pass

    async def tool_endpoint(params: ToolParamsModel = Body(...)):
        """Dynamic tool endpoint - uses common tool_dispatch function"""
        try:
            # Convert Pydantic model to dict and filter out None values
            params_dict = params.dict() if hasattr(params, 'dict') else {}
            # Remove None values to let MCP method use its defaults
            params_dict = {k: v for k, v in params_dict.items() if v is not None}

            # Use common tool dispatch function
            return await tool_dispatch(tool_name, params_dict)

        except Exception as e:
            logger.error(f"Error in dynamic tool endpoint for {tool_name}: {e}")
            return BaseResponse(
                ok=False,
                data={},
                meta={"tool": tool_name},
                errors=[str(e)]
            )

    return tool_endpoint, ToolParamsModel


def register_dynamic_tool_routes():
    """Register all MCP tools as dynamic REST endpoints"""
    tools_registry = get_mcp_tools_registry()

    for tool_name, tool_info in tools_registry.items():
        # Create endpoint function and model
        endpoint_func, params_model = create_dynamic_tool_endpoint(tool_name, tool_info)

        # Extract namespace for tags
        namespace = tool_name.split('.')[0] if '.' in tool_name else "misc"

        # Register the route
        tool_description = tool_info.get('description', f"Execute {tool_name} MCP tool")
        params_list = ', '.join(tool_info['params']) if tool_info['params'] else 'None'

        app.post(
            f"/tools/{tool_name}",
            response_model=BaseResponse,
            tags=["tools", namespace],
            summary=tool_description,
            description=f"{tool_description}\n\nParameters: {params_list}",
            operation_id=f"tool_endpoint_tools_{tool_name.replace('.', '_')}_post"
        )(endpoint_func)

        logger.info(f"Registered dynamic route: POST /tools/{tool_name}")


@app.get("/tools", response_model=List[Dict[str, Any]], tags=["tools"])
async def list_tools():
    """List all available MCP tools with their parameters"""
    tools_registry = get_mcp_tools_registry()

    tools_list = []
    for tool_name, tool_info in tools_registry.items():
        tools_list.append({
            "name": tool_name,
            "params": tool_info["params"],
            "description": f"MCP tool: {tool_name}"
        })

    return tools_list


@app.on_event("startup")
async def startup_event():
    """Initialize the MCP server on startup"""
    global mcp_server_instance

    logger.info("Starting News MCP HTTP Server...")

    # Set environment variables
    os.environ["PYTHONPATH"] = str(project_root)

    try:
        # Create MCP server instance
        mcp_server_instance = ComprehensiveNewsServer()
        logger.info("MCP server instance created successfully")

        # Register dynamic tool routes after MCP server is ready
        register_dynamic_tool_routes()
        logger.info("Dynamic tool routes registered successfully")

        # Register compatibility routes after MCP server is ready
        register_compatibility_routes()
        logger.info("Compatibility routes registered successfully")

        # Include compatibility router
        app.include_router(compat)
        logger.info("Compatibility router included successfully")

    except Exception as e:
        logger.error(f"Failed to create MCP server: {e}")
        raise


@app.on_event("shutdown")
async def shutdown_event():
    """Clean up on shutdown"""
    global mcp_server_instance
    logger.info("Shutting down News MCP HTTP Server...")
    mcp_server_instance = None


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "ok",
        "message": "News MCP HTTP Server is running",
        "version": "1.0.0"
    }


@app.get("/health")
async def health_check():
    """Detailed health check"""
    global mcp_server_instance

    if mcp_server_instance is None:
        raise HTTPException(status_code=503, detail="MCP server not initialized")

    return {
        "status": "healthy",
        "mcp_server": "initialized",
        "timestamp": asyncio.get_event_loop().time()
    }


@app.get("/mcp")
async def mcp_openapi():
    """
    OpenAPI specification endpoint for Open WebUI integration
    Returns the OpenAPI specification that Open WebUI expects
    """
    return app.openapi()


@app.get("/mcp/openapi.json")
async def mcp_openapi_json():
    """
    OpenAPI specification endpoint at /mcp/openapi.json
    Open WebUI expects this specific path when configured with http://host:port/mcp
    """
    return app.openapi()


@app.get("/openapi")
async def openapi_endpoint():
    """
    Alternative OpenAPI specification endpoint
    Provides the same OpenAPI spec at /openapi path for better compatibility
    """
    return app.openapi()


@app.post("/mcp")
async def mcp_endpoint(request: Request):
    """
    Main MCP endpoint for JSON-RPC over HTTP
    Accepts JSON-RPC requests and forwards them to the MCP server
    """
    global mcp_server_instance

    if mcp_server_instance is None:
        raise HTTPException(status_code=503, detail="MCP server not initialized")

    try:
        # Parse JSON-RPC request
        body = await request.json()

        # Validate JSON-RPC format
        if not isinstance(body, dict) or body.get("jsonrpc") != "2.0":
            raise HTTPException(status_code=400, detail="Invalid JSON-RPC request")

        jsonrpc_request = JSONRPCRequest(**body)

        # Create wrapper and handle request
        wrapper = HTTPMCPServerWrapper(mcp_server_instance)
        response = await wrapper.handle_request(jsonrpc_request)

        # Return JSON-RPC response
        return JSONResponse(content=response.dict(exclude_none=True))

    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON")
    except Exception as e:
        logger.error(f"Error in MCP endpoint: {e}")
        error_response = JSONRPCResponse(
            id=getattr(jsonrpc_request, 'id', None) if 'jsonrpc_request' in locals() else None,
            error={
                "code": -32603,
                "message": f"Internal server error: {str(e)}"
            }
        )
        return JSONResponse(
            content=error_response.dict(exclude_none=True),
            status_code=500
        )


# REST API Endpoints for Open WebUI Integration
@app.post("/tools/system/ping", response_model=BaseResponse, tags=["tools", "system"])
async def system_ping_rest():
    """
    System ping endpoint - checks if the MCP server is responsive
    Returns a simple pong response to verify system health
    """
    try:
        return BaseResponse(
            ok=True,
            data={"pong": True},
            meta={},
            errors=[]
        )
    except Exception as e:
        logger.error(f"Error in system ping: {e}")
        return BaseResponse(
            ok=False,
            data={},
            meta={},
            errors=[str(e)]
        )


@app.post("/tools/analysis/preview", response_model=BaseResponse, tags=["tools", "analysis"])
async def analysis_preview_rest(request: AnalysisPreviewIn):
    """
    Analysis preview endpoint - estimates cost and scope for analysis tasks
    Provides cost estimation and item counts before running actual analysis
    """
    global mcp_server_instance

    if mcp_server_instance is None:
        return BaseResponse(
            ok=False,
            data={},
            meta={},
            errors=["MCP server not initialized"]
        )

    try:
        # Try to import cost estimator service or use placeholder values
        try:
            # Attempt to access existing cost estimation logic
            # This is a placeholder implementation with example values
            # In production, this would integrate with app/services/cost_estimator.py

            # Simple heuristic based on selector
            items_considered = 0
            if "latest" in request.selector:
                items_considered = request.selector["latest"]
            elif "limit" in request.selector:
                items_considered = request.selector["limit"]
            else:
                items_considered = 10  # default

            # Cost estimation heuristic (placeholder values)
            cost_per_item = 0.001  # $0.001 per item for gpt-4o-mini
            if "gpt-4" in request.model.lower() and "mini" not in request.model.lower():
                cost_per_item = 0.01  # Higher cost for full GPT-4

            estimated_cost = items_considered * cost_per_item
            duplicate_items_skipped = max(0, int(items_considered * 0.1))  # 10% duplicates

            response_data = {
                "items_considered": items_considered,
                "estimated_cost_usd": round(estimated_cost, 4),
                "duplicate_items_skipped": duplicate_items_skipped,
                "model": request.model,
                "selector": request.selector
            }

            return BaseResponse(
                ok=True,
                data=response_data,
                meta={"note": "Placeholder implementation - integrate with actual cost estimator"},
                errors=[]
            )

        except ImportError:
            # Fallback placeholder values
            return BaseResponse(
                ok=True,
                data={
                    "items_considered": 5,
                    "estimated_cost_usd": 0.005,
                    "duplicate_items_skipped": 1
                },
                meta={"note": "Using placeholder values - cost estimator service not available"},
                errors=[]
            )

    except Exception as e:
        logger.error(f"Error in analysis preview: {e}")
        return BaseResponse(
            ok=False,
            data={},
            meta={},
            errors=[str(e)]
        )


if __name__ == "__main__":
    import uvicorn

    # Run the server
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8001,
        log_level="info"
    )