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

from fastapi import FastAPI, Request, HTTPException, Body, APIRouter, Query
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, create_model
import jsonschema
from jsonschema import ValidationError

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

# Cache for dynamic tool schemas
_tools_schema_cache: Optional[List[Dict[str, Any]]] = None


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
                            "version": "1.0.0",
                            "description": "News MCP System - RSS Feed Aggregator with AI Sentiment Analysis. Provides access to 37 news sources, 11,600+ articles with full-text search and sentiment filtering. Use GET /mcp/system/info for detailed system overview and common workflows."
                        },
                        "capabilities": {
                            "tools": {
                                "listChanged": True
                            },
                            "prompts": {},
                            "resources": {}
                        }
                    }
                )

            elif request.method == "prompts/list":
                return JSONRPCResponse(
                    id=request.id,
                    result={"prompts": []}
                )

            elif request.method == "resources/list":
                return JSONRPCResponse(
                    id=request.id,
                    result={"resources": []}
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
            global _tools_schema_cache

            if _tools_schema_cache is not None:
                return _tools_schema_cache

            tools = await get_dynamic_tools_from_mcp()
            return tools

        except Exception as e:
            logger.error(f"Error getting tools list: {e}")
            return []

    async def _call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call a specific tool on the MCP server"""
        try:
            # Use dynamic tool lookup instead of hardcoded map
            method = get_tool_method(tool_name)

            if method is None:
                raise ValueError(f"Tool not found: {tool_name}")

            # Call the method directly
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


def validate_tool_params(tool_name: str, params: Dict[str, Any], input_schema: Dict[str, Any]) -> Optional[List[str]]:
    """
    Validate tool parameters against JSON Schema (inputSchema)

    Returns:
        None if validation succeeds
        List of error messages if validation fails
    """
    if not input_schema:
        return None

    try:
        jsonschema.validate(instance=params, schema=input_schema)
        return None
    except ValidationError as e:
        error_path = ".".join(str(p) for p in e.path) if e.path else "root"
        error_msg = f"Validation error at '{error_path}': {e.message}"
        return [error_msg]
    except jsonschema.SchemaError as e:
        logger.error(f"Invalid schema for tool {tool_name}: {e}")
        return [f"Internal error: Invalid schema for tool {tool_name}"]
    except Exception as e:
        logger.error(f"Unexpected validation error for tool {tool_name}: {e}")
        return [f"Validation error: {str(e)}"]


# Common Tool Dispatch Function
async def tool_dispatch(tool_name: str, params: Dict[str, Any]) -> BaseResponse:
    """Common function to dispatch tool calls - used by both /tools/* and compatibility routes"""
    global mcp_server_instance, _tools_schema_cache

    if mcp_server_instance is None:
        return BaseResponse(
            ok=False,
            data={},
            meta={},
            errors=["MCP server not initialized"]
        )

    try:
        # Get method directly
        method = get_tool_method(tool_name)

        if method is None:
            return BaseResponse(
                ok=False,
                data={},
                meta={"tool": tool_name},
                errors=[f"Tool not found: {tool_name}"]
            )

        # Validate parameters against inputSchema
        if _tools_schema_cache:
            tool_schema = next((t for t in _tools_schema_cache if t['name'] == tool_name), None)
            if tool_schema and 'inputSchema' in tool_schema:
                validation_errors = validate_tool_params(tool_name, params, tool_schema['inputSchema'])
                if validation_errors:
                    return BaseResponse(
                        ok=False,
                        data={},
                        meta={"tool": tool_name, "validation": "failed"},
                        errors=validation_errors
                    )

        # Filter out None values to let MCP method use its defaults
        params_dict = {k: v for k, v in params.items() if v is not None}

        # Call the MCP tool method directly
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
def get_tool_method(tool_name: str):
    """
    Get method reference for a tool name using dynamic lookup.

    Lookup order:
    1. v2_handlers.{tool_name} - for newer tools (items_recent, get_schemas, etc.)
    2. _{tool_name} - for standard tools (get_dashboard, list_feeds, etc.)
    3. Dotted name mapping - for namespace tools (feeds.list -> _list_feeds)
    """
    global mcp_server_instance

    if mcp_server_instance is None:
        return None

    # 1. Try v2_handlers first (newer tools like items_recent, get_schemas)
    if hasattr(mcp_server_instance, 'v2_handlers'):
        v2_method = getattr(mcp_server_instance.v2_handlers, tool_name, None)
        if v2_method and callable(v2_method):
            return v2_method

    # 2. Try direct method _{tool_name} (standard tools like _get_dashboard, _list_feeds)
    method_name = f"_{tool_name}"
    if hasattr(mcp_server_instance, method_name):
        method = getattr(mcp_server_instance, method_name)
        if callable(method):
            return method

    # 3. Try dotted name mapping (feeds.list -> _list_feeds, system.ping -> _system_ping)
    if "." in tool_name:
        namespace, action = tool_name.split(".", 1)
        # Try both patterns: namespace.action -> _action_namespace OR _namespace_action
        for pattern in [f"_{action}_{namespace}", f"_{namespace}_{action}"]:
            if hasattr(mcp_server_instance, pattern):
                method = getattr(mcp_server_instance, pattern)
                if callable(method):
                    return method

    return None


def get_mcp_tools_registry() -> Dict[str, Dict[str, Any]]:
    """Get all available MCP tools with their parameter schemas (legacy compatibility)"""
    global mcp_server_instance, _tools_schema_cache

    if mcp_server_instance is None:
        return {}

    # Use cached dynamic tools if available
    dynamic_tools = _tools_schema_cache if _tools_schema_cache else []

    # Build registry from dynamic tools
    tool_methods = {}

    for tool in dynamic_tools:
        tool_name = tool['name']
        tool_desc = tool.get('description', f"MCP tool: {tool_name}")

        # Get method reference
        method = get_tool_method(tool_name)

        # Extract params from inputSchema
        params = []
        if 'inputSchema' in tool and tool['inputSchema']:
            schema = tool['inputSchema']
            if 'properties' in schema:
                params = list(schema['properties'].keys())

        tool_methods[tool_name] = {
            "method": method,
            "params": params,
            "description": tool_desc
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

        # Also register under /mcp/tools/ for Open WebUI compatibility
        endpoint_func2, _ = create_dynamic_tool_endpoint(tool_name, tool_info)
        app.post(
            f"/mcp/tools/{tool_name}",
            response_model=BaseResponse,
            tags=["mcp-tools", namespace],
            summary=tool_description,
            description=f"{tool_description}\n\nParameters: {params_list}",
            operation_id=f"tool_endpoint_mcp_tools_{tool_name.replace('.', '_')}_post"
        )(endpoint_func2)

        logger.info(f"Registered MCP compatibility route: POST /mcp/tools/{tool_name}")


async def get_dynamic_tools_from_mcp() -> List[Dict[str, Any]]:
    """Get tools dynamically from MCP server with full inputSchemas"""
    global mcp_server_instance, _tools_schema_cache

    if mcp_server_instance is None:
        logger.warning("MCP server not initialized, returning empty tools list")
        return []

    # Return cached tools if available
    if _tools_schema_cache is not None:
        return _tools_schema_cache

    try:
        from mcp.types import ListToolsRequest

        # Access MCP server's request handlers
        server = mcp_server_instance.server
        handlers = server.request_handlers

        # Get the ListToolsRequest handler
        if ListToolsRequest in handlers:
            handler = handlers[ListToolsRequest]
            request = ListToolsRequest()

            # Call the handler
            result = await handler(request)

            # Extract tools from the result
            if hasattr(result, 'model_dump'):
                result_dict = result.model_dump()
                if 'tools' in result_dict:
                    tools_data = result_dict['tools']

                    # Convert to our format
                    tools = []
                    for tool in tools_data:
                        tools.append({
                            "name": tool['name'],
                            "description": tool['description'],
                            "inputSchema": tool['inputSchema']
                        })

                    # Cache the results
                    _tools_schema_cache = tools
                    logger.info(f"Loaded {len(tools)} tools from MCP server with full schemas")
                    return tools

        logger.warning("MCP server ListToolsRequest handler not available")
        return []

    except Exception as e:
        logger.error(f"Error getting dynamic tools from MCP: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return []


def convert_json_schema_to_openapi_params(json_schema: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert JSON Schema (MCP inputSchema) to OpenAPI 3.0 parameter schema

    JSON Schema (MCP format):
    {
        "type": "object",
        "properties": {
            "feed_id": {"type": "string", "description": "Feed ID"}
        },
        "required": ["feed_id"]
    }

    OpenAPI format:
    {
        "feed_id": {
            "type": "string",
            "description": "Feed ID",
            "required": true
        }
    }
    """
    if not json_schema or not isinstance(json_schema, dict):
        return {}

    properties = json_schema.get("properties", {})
    required_fields = json_schema.get("required", [])

    openapi_params = {}

    for param_name, param_schema in properties.items():
        openapi_param = dict(param_schema)  # Copy original schema
        openapi_param["required"] = param_name in required_fields
        openapi_params[param_name] = openapi_param

    return openapi_params


@app.get("/tools", response_model=List[Dict[str, Any]], tags=["tools"])
async def list_tools(format: Optional[str] = Query(None, description="Output format: 'openapi' or default (json-schema)")):
    """
    List all available MCP tools with their full schemas

    - Default format: Returns tools with JSON Schema inputSchema (MCP native format)
    - format=openapi: Returns tools with OpenAPI 3.0 compatible parameters
    """
    # Get tools dynamically from MCP server
    tools = await get_dynamic_tools_from_mcp()

    if not tools:
        # Fallback to registry if dynamic discovery fails
        logger.warning("Falling back to hardcoded registry")
        tools_registry = get_mcp_tools_registry()

        tools_list = []
        for tool_name, tool_info in tools_registry.items():
            tools_list.append({
                "name": tool_name,
                "params": tool_info["params"],
                "description": tool_info.get("description", f"MCP tool: {tool_name}")
            })
        tools = tools_list

    # Convert to OpenAPI format if requested
    if format == "openapi":
        openapi_tools = []
        for tool in tools:
            openapi_tool = {
                "name": tool["name"],
                "description": tool.get("description", f"MCP tool: {tool['name']}"),
            }

            # Convert inputSchema to OpenAPI parameters
            if "inputSchema" in tool:
                openapi_tool["parameters"] = convert_json_schema_to_openapi_params(tool["inputSchema"])
            elif "params" in tool:
                # Legacy fallback for old format
                openapi_tool["parameters"] = {p: {"type": "any", "required": False} for p in tool["params"]}
            else:
                openapi_tool["parameters"] = {}

            openapi_tools.append(openapi_tool)

        return openapi_tools

    # Default: return JSON Schema format
    return tools


def generate_mcp_openapi_spec() -> Dict[str, Any]:
    """
    Generate OpenAPI 3.0 specification from MCP tools

    Returns complete OpenAPI spec with paths for all MCP tools
    """
    global _tools_schema_cache

    tools = _tools_schema_cache if _tools_schema_cache else []

    # Base OpenAPI 3.0 structure
    spec = {
        "openapi": "3.0.0",
        "info": {
            "title": "News MCP - MCP Tools API",
            "description": """News MCP System - RSS Feed Aggregator with AI-Powered Sentiment Analysis

SYSTEM OVERVIEW:
News MCP is an intelligent RSS feed aggregation system that collects, analyzes, and provides access to news articles from major global sources. The system includes AI-powered sentiment analysis to help you filter and discover news based on emotional tone and impact.

CURRENT DATA (Live):
• 37 active RSS feeds from major news sources
• 11,600+ articles in database
• 3,300+ articles with AI sentiment analysis
• 700+ new articles daily
• Real-time updates every 30-120 minutes

TOP NEWS SOURCES:
The Guardian, The Independent, South China Morning Post, Bloomberg, Al Jazeera, NBC News, Japan Times, New York Times, Axios, TechMeme, BBC, CNN, Reuters, and more.

KEY FEATURES:
1. RSS Feed Management - Add, update, monitor feed health
2. Article Retrieval - Get latest articles with advanced filtering
3. Full-Text Search - Search across all articles and sources
4. Sentiment Analysis - Filter by positive/negative/neutral sentiment
5. Real-Time Updates - Fresh content from all sources
6. Template System - Create dynamic feed filters

COMMON WORKFLOWS:
1. Discover News Sources:
   → Use 'list_feeds' to see all 37 available sources
   → Check feed health and article counts

2. Get Latest News:
   → Use 'latest_articles' with limit=10 for top stories
   → Add 'since_hours=24' for last 24 hours only
   → Use 'keywords' to filter by topic

3. Find Positive/Negative News:
   → Use 'latest_articles' with 'min_sentiment=0.5' for positive news
   → Use 'max_sentiment=-0.3' for negative/critical news
   → Sort by 'sort_by=sentiment_score' for most positive first

4. Search Specific Topics:
   → Use 'search_articles' with query='climate change'
   → Combine with sentiment filters for opinion analysis

5. Get System Status:
   → Use 'get_dashboard' for overview of feeds and articles
   → Use 'system_health' for system diagnostics

SENTIMENT ANALYSIS:
• Sentiment Score: -1.0 (very negative) to +1.0 (very positive)
• Impact Score: 0.0 (low impact) to 1.0 (high impact)
• Available on 28% of articles (automatically analyzing new content)
• Use filters: min_sentiment, max_sentiment, sort_by=sentiment_score

DATA FRESHNESS:
• Articles updated every 30-120 minutes per feed
• Sentiment analysis runs automatically on new articles
• Last update: Real-time (check last_article_time in responses)

API DESIGN:
All MCP tools are exposed as REST endpoints at /tools/{tool_name}
Use base URL http://localhost:8001/mcp when configuring clients like Open WebUI
Responses follow BaseResponse format: {ok, data, meta, errors}""",
            "version": "1.0.0",
            "contact": {
                "name": "News MCP API Support"
            }
        },
        "servers": [
            {
                "url": "http://localhost:8001",
                "description": "Local development server"
            }
        ],
        "paths": {},
        "components": {
            "schemas": {
                "BaseResponse": {
                    "type": "object",
                    "required": ["ok", "data", "meta", "errors"],
                    "properties": {
                        "ok": {
                            "type": "boolean",
                            "description": "Success status"
                        },
                        "data": {
                            "type": "object",
                            "description": "Response data"
                        },
                        "meta": {
                            "type": "object",
                            "description": "Metadata about the response"
                        },
                        "errors": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Error messages (empty on success)"
                        }
                    }
                }
            }
        },
        "tags": []
    }

    # Track unique tags
    tags_set = set()

    # Generate paths for each tool
    for tool in tools:
        tool_name = tool["name"]
        description = tool.get("description", f"MCP tool: {tool_name}")
        input_schema = tool.get("inputSchema", {})

        # Extract tag from tool name (e.g., "feeds.list" -> "feeds")
        tag = tool_name.split(".")[0] if "." in tool_name else tool_name.split("_")[0]
        tags_set.add(tag)

        # Build request body schema from inputSchema
        request_body = None
        if input_schema and input_schema.get("properties"):
            request_body = {
                "required": True,
                "content": {
                    "application/json": {
                        "schema": input_schema
                    }
                }
            }

        # Create path for this tool (relative path, will be combined with base URL by clients)
        path = f"/tools/{tool_name}"
        spec["paths"][path] = {
            "post": {
                "summary": description.split(".")[0] if "." in description else description[:100],
                "description": description,
                "operationId": f"call_tool_{tool_name.replace('.', '_')}",
                "tags": [tag],
                "responses": {
                    "200": {
                        "description": "Successful tool execution",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/BaseResponse"
                                }
                            }
                        }
                    },
                    "400": {
                        "description": "Validation error or bad request",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/BaseResponse"
                                }
                            }
                        }
                    },
                    "500": {
                        "description": "Internal server error",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/BaseResponse"
                                }
                            }
                        }
                    }
                }
            }
        }

        # Add request body if tool has parameters
        if request_body:
            spec["paths"][path]["post"]["requestBody"] = request_body

    # Add tags with descriptions
    # Tag descriptions mapping
    tag_descriptions = {
        "add": "Add new resources: feeds, sources, categories. Use these to expand your news collection.",
        "analysis": "AI sentiment analysis tools: preview costs, run analysis, view history. Analyze articles for sentiment, impact, and urgency scores.",
        "assign": "Assign relationships: templates to feeds, categories to sources. Manage data associations.",
        "categories": "Manage article categories: list, add, update, delete categories for organizing news topics.",
        "delete": "Delete resources: remove feeds, sources, or categories. Destructive operations requiring confirmation.",
        "error": "Error diagnostics: analyze system errors, failed fetches, and troubleshoot issues.",
        "execute": "Execute database queries: run custom SQL queries for advanced data access.",
        "export": "Data export tools: export articles, feeds, and analysis results in various formats.",
        "feed": "Individual feed operations: get specific feed details, update settings, test feed URLs.",
        "feeds": "Feed management: list all RSS feeds (37 sources), monitor health, manage fetch intervals. Start here to discover news sources.",
        "get": "Retrieve system information: dashboards, statistics, and overview data.",
        "items": "Article operations: access recent items, search articles by content and metadata.",
        "latest": "Get latest content: most recent articles with optional filtering by time, keywords, and sentiment.",
        "list": "List resources: browse all feeds, templates, categories, and sources in the system.",
        "log": "System logs: analyze application logs, debug issues, monitor system activity.",
        "maintenance": "System maintenance: cleanup tasks, database optimization, cache management.",
        "quick": "Quick queries: pre-defined database queries for common data access patterns.",
        "refresh": "Refresh data: manually trigger feed updates, force re-fetch articles.",
        "scheduler": "Scheduler control: manage feed fetch intervals, check scheduler status, set heartbeat.",
        "search": "Full-text search: search across all 11,600+ articles by title, description, and content.",
        "sources": "News source management: manage RSS source metadata, track source statistics.",
        "system": "System diagnostics: health checks, ping, status monitoring, system-wide statistics.",
        "table": "Database table operations: get table info, inspect schema, analyze data structure.",
        "template": "Template operations: work with individual dynamic feed templates.",
        "templates": "Dynamic feed templates: create custom feed filters, test templates, view performance.",
        "test": "Testing tools: test feed URLs before adding, validate templates, dry-run operations.",
        "trending": "Trending topics: discover popular topics and keywords across all articles.",
        "update": "Update resources: modify existing feeds, sources, categories, and settings.",
        "usage": "Usage statistics: track API usage, analyze system utilization, monitor resource consumption."
    }

    # Build tags list with descriptions
    spec["tags"] = [
        {
            "name": tag,
            "description": tag_descriptions.get(tag, f"{tag.title()} related tools")
        }
        for tag in sorted(tags_set)
    ]

    return spec


@app.on_event("startup")
async def startup_event():
    """Initialize the MCP server on startup"""
    global mcp_server_instance, _tools_schema_cache

    logger.info("Starting News MCP HTTP Server...")

    # Set environment variables
    os.environ["PYTHONPATH"] = str(project_root)

    # Clear tools cache on startup
    _tools_schema_cache = None

    try:
        # Create MCP server instance
        mcp_server_instance = ComprehensiveNewsServer()
        logger.info("MCP server instance created successfully")

        # Pre-load tools into cache
        tools = await get_dynamic_tools_from_mcp()
        logger.info(f"Pre-loaded {len(tools)} tools with schemas")

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

    Returns complete OpenAPI 3.0 spec with all MCP tools as REST endpoints
    """
    return generate_mcp_openapi_spec()


@app.get("/mcp/system/info", tags=["system"])
async def mcp_system_info():
    """
    System Information Endpoint

    Provides comprehensive overview of the News MCP system including:
    - Live statistics (feeds, articles, analysis coverage)
    - System capabilities and features
    - Top news sources
    - Common workflows and usage examples
    - Data freshness and update intervals

    This endpoint is designed to give AI clients context about the system
    before they start making tool calls.
    """
    from sqlmodel import Session
    from app.database import engine

    try:
        with Session(engine) as session:
            # Get live statistics
            from sqlalchemy import text

            stats_query = text("""
                SELECT
                    (SELECT COUNT(*) FROM feeds WHERE status = 'ACTIVE') as active_feeds,
                    (SELECT COUNT(*) FROM feeds) as total_feeds,
                    (SELECT COUNT(*) FROM items) as total_articles,
                    (SELECT COUNT(*) FROM item_analysis) as analyzed_articles,
                    (SELECT COUNT(DISTINCT feed_id) FROM items WHERE created_at > NOW() - INTERVAL '24 hours') as active_last_24h,
                    (SELECT COUNT(*) FROM items WHERE created_at > NOW() - INTERVAL '24 hours') as articles_last_24h,
                    (SELECT MAX(created_at) FROM items) as last_article_time
            """)

            result = session.execute(stats_query).fetchone()

            # Get top sources
            top_sources_query = text("""
                SELECT feeds.title, COUNT(items.id) as article_count
                FROM feeds
                LEFT JOIN items ON feeds.id = items.feed_id
                WHERE feeds.status = 'ACTIVE'
                GROUP BY feeds.id, feeds.title
                ORDER BY article_count DESC
                LIMIT 10
            """)

            top_sources = session.execute(top_sources_query).fetchall()

            # Build response
            return {
                "system": "News MCP",
                "version": "1.0.0",
                "type": "RSS Aggregator with AI Sentiment Analysis",
                "description": "Intelligent news aggregation system with 37 RSS feeds and AI-powered sentiment analysis",

                "capabilities": [
                    "RSS feed aggregation from 37 major news sources",
                    "Full-text article search across 11,600+ articles",
                    "AI sentiment analysis (positive/negative/neutral scoring)",
                    "Real-time feed health monitoring",
                    "Dynamic feed templates for custom filtering",
                    "Advanced article filtering (time, keywords, sentiment)",
                    "Historical analysis data and trending topics"
                ],

                "statistics": {
                    "active_feeds": result.active_feeds,
                    "total_feeds": result.total_feeds,
                    "total_articles": result.total_articles,
                    "analyzed_articles": result.analyzed_articles,
                    "analysis_coverage": f"{round(100 * result.analyzed_articles / result.total_articles, 1)}%",
                    "active_last_24h": result.active_last_24h,
                    "articles_last_24h": result.articles_last_24h,
                    "last_article_time": result.last_article_time.isoformat() if result.last_article_time else None
                },

                "top_sources": [
                    {"name": row.title, "article_count": row.article_count}
                    for row in top_sources
                ],

                "common_workflows": [
                    {
                        "name": "Discover News Sources",
                        "description": "See all available news sources and their status",
                        "steps": ["Call 'list_feeds' to get all 37 sources", "Check 'status' and article counts per feed"],
                        "example_tool": "list_feeds"
                    },
                    {
                        "name": "Get Latest News",
                        "description": "Retrieve most recent articles with optional filtering",
                        "steps": ["Call 'latest_articles' with limit=10", "Add filters: since_hours=24, keywords=['climate']"],
                        "example_tool": "latest_articles",
                        "example_params": {"limit": 10, "since_hours": 24}
                    },
                    {
                        "name": "Find Positive News",
                        "description": "Filter articles by positive sentiment",
                        "steps": ["Call 'latest_articles' with min_sentiment=0.5", "Sort by sentiment_score for most positive first"],
                        "example_tool": "latest_articles",
                        "example_params": {"limit": 20, "min_sentiment": 0.5, "sort_by": "sentiment_score"}
                    },
                    {
                        "name": "Find Negative/Critical News",
                        "description": "Filter articles by negative sentiment",
                        "steps": ["Call 'latest_articles' with max_sentiment=-0.3"],
                        "example_tool": "latest_articles",
                        "example_params": {"limit": 20, "max_sentiment": -0.3}
                    },
                    {
                        "name": "Search Specific Topics",
                        "description": "Full-text search across all articles",
                        "steps": ["Call 'search_articles' with query='climate change'", "Combine with sentiment filters for opinion analysis"],
                        "example_tool": "search_articles",
                        "example_params": {"query": "artificial intelligence", "limit": 20}
                    },
                    {
                        "name": "Get System Status",
                        "description": "Check overall system health and metrics",
                        "steps": ["Call 'get_dashboard' for overview", "Call 'system_health' for diagnostics"],
                        "example_tool": "get_dashboard"
                    }
                ],

                "sentiment_analysis": {
                    "description": "AI-powered sentiment analysis using GPT-4",
                    "sentiment_score_range": {"min": -1.0, "max": 1.0, "description": "Negative to Positive"},
                    "impact_score_range": {"min": 0.0, "max": 1.0, "description": "Low to High Impact"},
                    "coverage": f"{result.analyzed_articles} of {result.total_articles} articles analyzed",
                    "filters_available": ["min_sentiment", "max_sentiment", "sort_by sentiment_score/impact_score"]
                },

                "data_freshness": {
                    "update_interval": "30-120 minutes per feed",
                    "auto_analysis": "New articles analyzed automatically",
                    "last_article_time": result.last_article_time.isoformat() if result.last_article_time else None,
                    "articles_last_24h": result.articles_last_24h
                },

                "api_info": {
                    "base_url": "http://localhost:8001",
                    "openapi_spec": "http://localhost:8001/mcp/openapi.json",
                    "tool_endpoint_pattern": "/mcp/tools/{tool_name}",
                    "response_format": "BaseResponse: {ok, data, meta, errors}",
                    "total_tools": len(_tools_schema_cache) if _tools_schema_cache else 0
                }
            }

    except Exception as e:
        logger.error(f"Error in system info endpoint: {e}")
        return {
            "system": "News MCP",
            "version": "1.0.0",
            "error": str(e),
            "message": "Unable to fetch live statistics"
        }


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


# =============================================================================
# Debug Endpoints
# =============================================================================

@app.get("/debug/tools/schema", tags=["debug"])
async def debug_tool_schema(tool_name: str = Query(..., description="Tool name to inspect")):
    """
    Debug endpoint: Get detailed schema information for a specific tool

    Returns:
    - Full JSON Schema (inputSchema)
    - OpenAPI parameter format
    - Validation constraints
    - Required fields
    """
    global _tools_schema_cache

    if not _tools_schema_cache:
        return JSONResponse(
            status_code=503,
            content={"error": "Tool cache not initialized"}
        )

    tool = next((t for t in _tools_schema_cache if t["name"] == tool_name), None)

    if not tool:
        available_tools = [t["name"] for t in _tools_schema_cache]
        return JSONResponse(
            status_code=404,
            content={
                "error": f"Tool '{tool_name}' not found",
                "available_tools": available_tools
            }
        )

    input_schema = tool.get("inputSchema", {})

    debug_info = {
        "tool_name": tool_name,
        "description": tool.get("description"),
        "json_schema": {
            "full": input_schema,
            "properties": input_schema.get("properties", {}),
            "required": input_schema.get("required", []),
            "type": input_schema.get("type")
        },
        "openapi_format": convert_json_schema_to_openapi_params(input_schema),
        "validation_info": {
            "required_fields": input_schema.get("required", []),
            "optional_fields": [
                prop for prop in input_schema.get("properties", {}).keys()
                if prop not in input_schema.get("required", [])
            ],
            "total_parameters": len(input_schema.get("properties", {}))
        }
    }

    return debug_info


@app.post("/debug/tools/diff", tags=["debug"])
async def debug_tool_diff(
    tool1: str = Query(..., description="First tool name"),
    tool2: str = Query(..., description="Second tool name")
):
    """
    Debug endpoint: Compare schemas of two tools

    Useful for:
    - Understanding schema differences
    - Debugging schema changes
    - Finding common patterns
    """
    global _tools_schema_cache

    if not _tools_schema_cache:
        return JSONResponse(
            status_code=503,
            content={"error": "Tool cache not initialized"}
        )

    t1 = next((t for t in _tools_schema_cache if t["name"] == tool1), None)
    t2 = next((t for t in _tools_schema_cache if t["name"] == tool2), None)

    if not t1 or not t2:
        return JSONResponse(
            status_code=404,
            content={
                "error": f"One or both tools not found: {tool1}, {tool2}",
                "available_tools": [t["name"] for t in _tools_schema_cache]
            }
        )

    s1 = t1.get("inputSchema", {})
    s2 = t2.get("inputSchema", {})

    props1 = set(s1.get("properties", {}).keys())
    props2 = set(s2.get("properties", {}).keys())

    required1 = set(s1.get("required", []))
    required2 = set(s2.get("required", []))

    diff = {
        "tool1": tool1,
        "tool2": tool2,
        "properties": {
            "common": sorted(props1 & props2),
            "only_in_tool1": sorted(props1 - props2),
            "only_in_tool2": sorted(props2 - props1),
            "total_tool1": len(props1),
            "total_tool2": len(props2)
        },
        "required_fields": {
            "common": sorted(required1 & required2),
            "only_in_tool1": sorted(required1 - required2),
            "only_in_tool2": sorted(required2 - required1)
        },
        "descriptions": {
            "tool1": t1.get("description"),
            "tool2": t2.get("description")
        }
    }

    return diff


@app.post("/debug/validate-call", tags=["debug"])
async def debug_validate_call(
    tool_name: str = Query(..., description="Tool to validate against"),
    params: Dict[str, Any] = Body(..., description="Parameters to validate")
):
    """
    Debug endpoint: Validate a tool call without executing it

    Tests:
    - Parameter validation against inputSchema
    - Required fields check
    - Type validation
    - Constraint validation

    Returns validation result with detailed error messages
    """
    global _tools_schema_cache

    if not _tools_schema_cache:
        return JSONResponse(
            status_code=503,
            content={"error": "Tool cache not initialized"}
        )

    tool = next((t for t in _tools_schema_cache if t["name"] == tool_name), None)

    if not tool:
        return JSONResponse(
            status_code=404,
            content={
                "error": f"Tool '{tool_name}' not found",
                "available_tools": [t["name"] for t in _tools_schema_cache]
            }
        )

    input_schema = tool.get("inputSchema", {})

    if not input_schema:
        return {
            "valid": True,
            "message": "No schema validation required (tool has no inputSchema)",
            "tool_name": tool_name,
            "params_provided": params
        }

    # Validate using the same function as tool_dispatch
    validation_errors = validate_tool_params(tool_name, params, input_schema)

    if validation_errors:
        return {
            "valid": False,
            "tool_name": tool_name,
            "errors": validation_errors,
            "params_provided": params,
            "schema": input_schema,
            "hint": "Fix the errors above to make the call valid"
        }

    return {
        "valid": True,
        "tool_name": tool_name,
        "params_provided": params,
        "message": "Validation passed - call would be accepted by tool_dispatch"
    }


if __name__ == "__main__":
    import uvicorn

    # Run the server
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8001,
        log_level="info"
    )