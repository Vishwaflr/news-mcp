# Schema Reflection Architecture

**Version:** 1.0 (Phase 2 Complete)
**Last Updated:** 2025-09-28
**Status:** Production-Ready

---

## Executive Summary

Schema Reflection ist ein dynamisches System zur Laufzeit-Propagierung von Tool-Schemas vom MCP Server zum HTTP Bridge und weiter zu API-Clients. Es eliminiert hardcoded Tool-Registries und ermöglicht automatische OpenAPI-Spec-Generierung.

**Key Benefits:**
- ✅ **Zero Configuration**: Neue MCP Tools erscheinen automatisch als REST-Endpunkte
- ✅ **Type Safety**: Vollständige Request-Validierung gegen JSON Schemas
- ✅ **Auto-Documentation**: OpenAPI 3.0 Spec generiert sich selbst aus MCP Tools
- ✅ **Developer Experience**: Debug-Endpoints für Schema-Inspektion und Validierung

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Data Flow Diagrams](#data-flow-diagrams)
3. [Component Architecture](#component-architecture)
4. [Schema Transformation](#schema-transformation)
5. [Request Validation](#request-validation)
6. [Debug Interface](#debug-interface)
7. [Testing Strategy](#testing-strategy)

---

## System Overview

### Architecture Layers

```
┌──────────────────────────────────────────────────────────────┐
│                    CLIENT LAYER                              │
│  Claude Desktop, Open WebUI, Custom HTTP Clients            │
└────────────┬─────────────────────────────────────────────────┘
             │
             │ REST (JSON) / JSON-RPC 2.0
             │
┌────────────▼─────────────────────────────────────────────────┐
│              HTTP BRIDGE (FastAPI)                           │
│  http_mcp_server.py                                         │
│                                                              │
│  ┌────────────────────────────────────────────────────┐    │
│  │ Schema Reflection Layer                            │    │
│  │                                                     │    │
│  │  • Dynamic Tool Discovery                          │    │
│  │  • Schema Caching (_tools_schema_cache)            │    │
│  │  • JSON Schema → OpenAPI Transformation            │    │
│  │  • Request Validation (jsonschema)                 │    │
│  │  • OpenAPI Spec Generation                         │    │
│  │  • Debug Endpoints                                 │    │
│  └────────────────────────────────────────────────────┘    │
│                                                              │
└────────────┬─────────────────────────────────────────────────┘
             │
             │ MCP Protocol (Python SDK)
             │
┌────────────▼─────────────────────────────────────────────────┐
│              MCP SERVER (mcp)                                │
│  comprehensive_server.py                                     │
│                                                              │
│  • 48 Tools with inputSchemas                               │
│  • Enhanced Descriptions                                     │
│  • Sentiment Filtering (JSONB)                              │
│  • Business Logic                                            │
└──────────────────────────────────────────────────────────────┘
```

---

## Data Flow Diagrams

### 1. Startup Flow: Schema Discovery

```mermaid
sequenceDiagram
    participant HTTP as HTTP Bridge
    participant MCP as MCP Server
    participant Cache as _tools_schema_cache

    Note over HTTP: Server Startup

    HTTP->>MCP: get_dynamic_tools_from_mcp()
    MCP->>MCP: list_tools()
    MCP-->>HTTP: [Tool1, Tool2, ..., Tool48]

    loop For each tool
        HTTP->>HTTP: Extract name, description, inputSchema
    end

    HTTP->>Cache: Store all tools
    Cache-->>HTTP: Cache ready

    Note over HTTP: Ready to serve requests
```

**Code Reference:** `http_mcp_server.py:688-730`

**Key Variables:**
- `_tools_schema_cache`: Global list storing all tool schemas
- Populated once at startup
- Used by all endpoints for schema lookup

---

### 2. Request Flow: Tool Execution with Validation

```mermaid
sequenceDiagram
    participant Client
    participant HTTP as HTTP Bridge
    participant Validator as validate_tool_params()
    participant MCP as MCP Server
    participant DB as PostgreSQL

    Client->>HTTP: POST /tools/latest_articles<br/>{limit: 10, min_sentiment: 0.5}

    HTTP->>HTTP: Look up schema in cache

    alt Schema found
        HTTP->>Validator: validate(params, inputSchema)

        alt Validation passes
            Validator-->>HTTP: ✓ Valid

            HTTP->>MCP: call_tool("latest_articles", {...})
            MCP->>DB: SELECT ... WHERE sentiment >= 0.5
            DB-->>MCP: [articles]
            MCP-->>HTTP: TextContent(articles)

            HTTP-->>Client: BaseResponse(ok=True, data={...})

        else Validation fails
            Validator-->>HTTP: ✗ Errors: ["min_sentiment > max"]

            HTTP-->>Client: BaseResponse(ok=False, errors=[...])
        end

    else Schema not found
        HTTP-->>Client: 404 Tool not found
    end
```

**Code References:**
- `tool_dispatch()`: `http_mcp_server.py:326-390`
- `validate_tool_params()`: `http_mcp_server.py:301-324`
- `call_tool()`: `http_mcp_server.py:265-299`

---

### 3. Schema Transformation Flow

```mermaid
graph LR
    A[MCP JSON Schema] -->|"convert_json_schema_to_openapi_params()"| B[OpenAPI Format]
    B -->|"generate_mcp_openapi_spec()"| C[Full OpenAPI 3.0 Spec]
    C --> D[/mcp/openapi.json]
    C --> E[/tools?format=openapi]

    style A fill:#e3f2fd
    style B fill:#fff3e0
    style C fill:#e8f5e9
    style D fill:#f3e5f5
    style E fill:#f3e5f5
```

**Transformation Steps:**

1. **Input (MCP JSON Schema)**
   ```json
   {
     "type": "object",
     "properties": {
       "limit": {"type": "integer", "maximum": 100},
       "min_sentiment": {"type": "number", "minimum": -1, "maximum": 1}
     },
     "required": ["limit"]
   }
   ```

2. **Intermediate (OpenAPI Parameters)**
   ```json
   {
     "limit": {
       "type": "integer",
       "maximum": 100,
       "required": true
     },
     "min_sentiment": {
       "type": "number",
       "minimum": -1,
       "maximum": 1,
       "required": false
     }
   }
   ```

3. **Output (OpenAPI Path)**
   ```yaml
   /tools/latest_articles:
     post:
       requestBody:
         content:
           application/json:
             schema:
               type: object
               properties:
                 limit: {type: integer, maximum: 100}
                 min_sentiment: {type: number, minimum: -1, maximum: 1}
               required: [limit]
   ```

---

## Component Architecture

### HTTP Bridge Components

```
┌──────────────────────────────────────────────────────────────┐
│                   http_mcp_server.py                         │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Schema Discovery & Caching                          │   │
│  │  • get_dynamic_tools_from_mcp()                     │   │
│  │  • _tools_schema_cache (global)                     │   │
│  └─────────────────────────────────────────────────────┘   │
│           │                                                  │
│           ▼                                                  │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Schema Transformation                               │   │
│  │  • convert_json_schema_to_openapi_params()          │   │
│  │  • generate_mcp_openapi_spec()                      │   │
│  └─────────────────────────────────────────────────────┘   │
│           │                                                  │
│           ▼                                                  │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Request Validation                                  │   │
│  │  • validate_tool_params()                           │   │
│  │  • jsonschema.validate()                            │   │
│  └─────────────────────────────────────────────────────┘   │
│           │                                                  │
│           ▼                                                  │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Tool Execution                                      │   │
│  │  • tool_dispatch()                                  │   │
│  │  • call_tool()                                      │   │
│  └─────────────────────────────────────────────────────┘   │
│           │                                                  │
│           ▼                                                  │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Debug Interface                                     │   │
│  │  • /debug/tools/schema                              │   │
│  │  • /debug/tools/diff                                │   │
│  │  • /debug/validate-call                             │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

### Key Functions

#### 1. Dynamic Tool Discovery

```python
async def get_dynamic_tools_from_mcp() -> List[Dict[str, Any]]:
    """
    Load all MCP tools at startup and cache globally.

    Returns:
        List of tool dictionaries with:
        - name: str (e.g., "latest_articles")
        - description: str (enhanced with examples)
        - inputSchema: dict (JSON Schema)
    """
    global _tools_schema_cache

    if _tools_schema_cache:
        return _tools_schema_cache

    tools_list = []
    for tool in mcp_server.list_tools():
        tool_dict = {
            "name": tool.name,
            "description": tool.description,
            "inputSchema": tool.inputSchema
        }
        tools_list.append(tool_dict)

    _tools_schema_cache = tools_list
    logger.info(f"Dynamic tool discovery: found {len(tools_list)} tools")

    return tools_list
```

**Location:** `http_mcp_server.py:688-730`

**Features:**
- Global caching (only runs once)
- No hardcoded tool names
- Scales automatically with new tools

---

#### 2. Schema Transformation

```python
def convert_json_schema_to_openapi_params(
    json_schema: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Convert MCP JSON Schema to OpenAPI parameter format.

    Changes:
    - Move "required" from array to inline boolean
    - Preserve all constraints (min/max, enum, etc.)
    - Keep type, description, defaults

    Example:
    Input:
    {
      "properties": {"limit": {"type": "integer"}},
      "required": ["limit"]
    }

    Output:
    {
      "limit": {"type": "integer", "required": true}
    }
    """
    if not json_schema or not isinstance(json_schema, dict):
        return {}

    properties = json_schema.get("properties", {})
    required_fields = json_schema.get("required", [])

    openapi_params = {}
    for param_name, param_schema in properties.items():
        openapi_param = dict(param_schema)
        openapi_param["required"] = param_name in required_fields
        openapi_params[param_name] = openapi_param

    return openapi_params
```

**Location:** `http_mcp_server.py:733-760`

**Use Cases:**
- `/tools?format=openapi` endpoint
- OpenAPI spec generation
- Client-side schema consumption

---

#### 3. Request Validation

```python
def validate_tool_params(
    tool_name: str,
    params: Dict[str, Any],
    input_schema: Dict[str, Any]
) -> Optional[List[str]]:
    """
    Validate request parameters against JSON Schema.

    Validates:
    - Required fields present
    - Type correctness (int, float, str, bool, array)
    - Constraints (min/max, enum, format)

    Returns:
        None if valid, List[str] of error messages if invalid
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
        logger.error(f"Unexpected validation error: {e}")
        return [f"Validation error: {str(e)}"]
```

**Location:** `http_mcp_server.py:301-324`

**Validation Examples:**

| Input | Schema | Result |
|-------|--------|--------|
| `{"limit": 10}` | `required: ["limit"]` | ✓ Valid |
| `{"limit": "ten"}` | `type: integer` | ✗ Type error |
| `{"limit": 200}` | `maximum: 100` | ✗ Constraint violation |
| `{"min_sentiment": 2.0}` | `maximum: 1` | ✗ Out of range |

---

#### 4. Tool Dispatch

```python
async def tool_dispatch(
    tool_name: str,
    params: Dict[str, Any]
) -> BaseResponse:
    """
    Dispatch tool call with validation and error handling.

    Flow:
    1. Look up tool schema in cache
    2. Validate params against inputSchema
    3. If invalid, return error immediately (no MCP call)
    4. If valid, call MCP tool
    5. Format response as BaseResponse

    Returns:
        BaseResponse with:
        - ok: bool
        - data: dict
        - meta: dict (includes tool name, validation status)
        - errors: list[str]
    """
    # Step 1: Schema Lookup
    if _tools_schema_cache:
        tool_schema = next(
            (t for t in _tools_schema_cache if t['name'] == tool_name),
            None
        )

        # Step 2: Validation
        if tool_schema and 'inputSchema' in tool_schema:
            validation_errors = validate_tool_params(
                tool_name,
                params,
                tool_schema['inputSchema']
            )

            # Step 3: Early return on validation failure
            if validation_errors:
                return BaseResponse(
                    ok=False,
                    data={},
                    meta={"tool": tool_name, "validation": "failed"},
                    errors=validation_errors
                )

    # Step 4: MCP Tool Execution
    try:
        result = await call_tool(tool_name, params)

        # Step 5: Response Formatting
        return BaseResponse(
            ok=True,
            data=result,
            meta={"tool": tool_name},
            errors=[]
        )

    except Exception as e:
        logger.error(f"Tool execution error: {e}")
        return BaseResponse(
            ok=False,
            data={},
            meta={"tool": tool_name},
            errors=[str(e)]
        )
```

**Location:** `http_mcp_server.py:326-390`

---

## Schema Transformation

### JSON Schema → OpenAPI 3.0

#### Transformation Rules

| JSON Schema Feature | OpenAPI Equivalent | Notes |
|---------------------|-------------------|-------|
| `properties: {...}` | `properties: {...}` | Copied directly |
| `required: [...]` | `required: true/false` (inline) | Moved from array to boolean |
| `type: "integer"` | `type: integer` | Same |
| `minimum: N` | `minimum: N` | Same |
| `maximum: N` | `maximum: N` | Same |
| `enum: [...]` | `enum: [...]` | Same |
| `default: X` | `default: X` | Same |
| `description: "..."` | `description: "..."` | Same |

#### Example: latest_articles Tool

**JSON Schema (MCP):**
```json
{
  "type": "object",
  "properties": {
    "limit": {
      "type": "integer",
      "default": 20,
      "maximum": 100,
      "description": "Number of articles"
    },
    "min_sentiment": {
      "type": "number",
      "minimum": -1,
      "maximum": 1,
      "description": "Minimum sentiment score"
    },
    "sort_by": {
      "type": "string",
      "enum": ["created_at", "published", "sentiment_score", "impact_score"],
      "default": "created_at"
    }
  },
  "required": []
}
```

**OpenAPI 3.0 Path:**
```yaml
/tools/latest_articles:
  post:
    summary: "Get latest articles with sentiment filtering"
    description: "Get latest articles with advanced filtering..."
    tags: ["articles"]
    operationId: "call_tool_latest_articles"
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            properties:
              limit:
                type: integer
                default: 20
                maximum: 100
                description: "Number of articles"
              min_sentiment:
                type: number
                minimum: -1
                maximum: 1
                description: "Minimum sentiment score"
              sort_by:
                type: string
                enum: ["created_at", "published", "sentiment_score", "impact_score"]
                default: "created_at"
    responses:
      200:
        description: "Success"
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/BaseResponse'
      400:
        description: "Validation error"
      500:
        description: "Server error"
```

**Generated by:** `generate_mcp_openapi_spec()` in `http_mcp_server.py:864-1000`

---

### OpenAPI Spec Generation

**Full Spec Structure:**

```yaml
openapi: 3.0.0

info:
  title: "News MCP - MCP Tools API"
  description: "HTTP REST API for News MCP system..."
  version: "1.0.0"
  contact:
    name: "News MCP Team"

servers:
  - url: "http://localhost:8001"
    description: "Local development server"

paths:
  /tools/system_ping: {...}
  /tools/latest_articles: {...}
  /tools/search_articles: {...}
  # ... 48 paths total

components:
  schemas:
    BaseResponse:
      type: object
      properties:
        ok: {type: boolean}
        data: {type: object}
        meta: {type: object}
        errors: {type: array, items: {type: string}}

tags:
  - name: "system"
    description: "System tools (ping, health, dashboard)"
  - name: "feeds"
    description: "Feed management tools"
  - name: "articles"
    description: "Article retrieval and search tools"
  - name: "templates"
    description: "Dynamic feed template tools"
  - name: "analysis"
    description: "Sentiment analysis tools"
  - name: "sources"
    description: "News source management"
```

**Endpoint:** `GET /mcp/openapi.json`

**Use Cases:**
- Open WebUI integration
- Swagger UI documentation
- Client SDK generation (openapi-generator)
- API testing (Postman, Insomnia)

---

## Request Validation

### Validation Pipeline

```
Request → Parse JSON → Schema Lookup → Validation → Execution
   ↓          ↓             ↓              ↓            ↓
 Body      params      inputSchema    jsonschema    MCP call
```

### Validation Checks

#### 1. Required Fields

**Schema:**
```json
{
  "properties": {
    "query": {"type": "string"}
  },
  "required": ["query"]
}
```

**Test Cases:**
| Input | Result |
|-------|--------|
| `{"query": "AI"}` | ✓ Valid |
| `{}` | ✗ Missing required field 'query' |
| `{"limit": 10}` | ✗ Missing required field 'query' |

---

#### 2. Type Validation

**Schema:**
```json
{
  "properties": {
    "limit": {"type": "integer"},
    "min_sentiment": {"type": "number"},
    "keywords": {"type": "array", "items": {"type": "string"}}
  }
}
```

**Test Cases:**
| Input | Result |
|-------|--------|
| `{"limit": 10}` | ✓ Valid (integer) |
| `{"limit": "ten"}` | ✗ Type error: expected integer |
| `{"min_sentiment": 0.5}` | ✓ Valid (number) |
| `{"min_sentiment": "high"}` | ✗ Type error: expected number |
| `{"keywords": ["AI", "tech"]}` | ✓ Valid (array of strings) |
| `{"keywords": "AI"}` | ✗ Type error: expected array |

---

#### 3. Constraint Validation

**Schema:**
```json
{
  "properties": {
    "limit": {"type": "integer", "minimum": 1, "maximum": 100},
    "min_sentiment": {"type": "number", "minimum": -1, "maximum": 1},
    "sort_by": {"type": "string", "enum": ["created_at", "published"]}
  }
}
```

**Test Cases:**
| Input | Result |
|-------|--------|
| `{"limit": 50}` | ✓ Valid (within range) |
| `{"limit": 0}` | ✗ Constraint error: 0 < minimum 1 |
| `{"limit": 200}` | ✗ Constraint error: 200 > maximum 100 |
| `{"min_sentiment": 0.5}` | ✓ Valid (within range) |
| `{"min_sentiment": 2.0}` | ✗ Constraint error: 2.0 > maximum 1 |
| `{"sort_by": "created_at"}` | ✓ Valid (in enum) |
| `{"sort_by": "invalid"}` | ✗ Enum error: not in allowed values |

---

### Error Response Format

**Structure:**
```json
{
  "ok": false,
  "data": {},
  "meta": {
    "tool": "latest_articles",
    "validation": "failed"
  },
  "errors": [
    "Validation error at 'min_sentiment': 2.5 is greater than the maximum of 1"
  ]
}
```

**HTTP Status:** 200 OK (errors in response body, not HTTP status)

**Error Message Format:**
```
"Validation error at '<field_path>': <description>"
```

Examples:
- `"Validation error at 'limit': 200 is greater than the maximum of 100"`
- `"Validation error at 'query': 'query' is a required property"`
- `"Validation error at 'sort_by': 'invalid' is not one of ['created_at', 'published']"`

---

## Debug Interface

### 3 Debug Endpoints

#### 1. Schema Inspection: `/debug/tools/schema`

**Purpose:** Inspect detailed schema information for a tool

**Request:**
```http
GET /debug/tools/schema?tool_name=latest_articles
```

**Response:**
```json
{
  "tool_name": "latest_articles",
  "description": "Get latest articles with sentiment filtering...",
  "json_schema": {
    "full": {...},
    "properties": {...},
    "required": [],
    "type": "object"
  },
  "openapi_format": {
    "limit": {"type": "integer", "required": false, ...},
    "min_sentiment": {"type": "number", "required": false, ...}
  },
  "validation_info": {
    "required_fields": [],
    "optional_fields": ["limit", "min_sentiment", "max_sentiment", ...],
    "total_parameters": 8
  }
}
```

**Use Cases:**
- Understand parameter requirements
- Debug schema issues
- Compare JSON Schema vs OpenAPI format

---

#### 2. Schema Comparison: `/debug/tools/diff`

**Purpose:** Compare schemas of two tools

**Request:**
```http
POST /debug/tools/diff?tool1=latest_articles&tool2=search_articles
```

**Response:**
```json
{
  "tool1": "latest_articles",
  "tool2": "search_articles",
  "properties": {
    "common": ["limit", "feed_id"],
    "only_in_tool1": ["min_sentiment", "max_sentiment", "sort_by", "since_hours"],
    "only_in_tool2": ["query", "date_from", "date_to"],
    "total_tool1": 8,
    "total_tool2": 5
  },
  "required_fields": {
    "common": [],
    "only_in_tool1": [],
    "only_in_tool2": ["query"]
  },
  "descriptions": {
    "tool1": "Get latest articles with sentiment filtering...",
    "tool2": "Full-text search across all articles..."
  }
}
```

**Use Cases:**
- Understand tool differences
- Find common parameters
- Debug API design consistency

---

#### 3. Validation Testing: `/debug/validate-call`

**Purpose:** Test validation without executing tool

**Request:**
```http
POST /debug/validate-call?tool_name=latest_articles
Content-Type: application/json

{
  "limit": 10,
  "min_sentiment": 0.5
}
```

**Response (Valid):**
```json
{
  "valid": true,
  "tool_name": "latest_articles",
  "params_provided": {
    "limit": 10,
    "min_sentiment": 0.5
  },
  "message": "Validation passed - call would be accepted by tool_dispatch"
}
```

**Response (Invalid):**
```json
{
  "valid": false,
  "tool_name": "latest_articles",
  "errors": [
    "Validation error at 'min_sentiment': 2.5 is greater than the maximum of 1"
  ],
  "params_provided": {
    "limit": 10,
    "min_sentiment": 2.5
  },
  "schema": {...},
  "hint": "Fix the errors above to make the call valid"
}
```

**Use Cases:**
- Test API calls before sending
- Debug validation errors
- Understand parameter constraints

---

## Testing Strategy

### Integration Test Suite

**Location:** `tests/integration/`

**Structure:**
```
tests/integration/
├── conftest.py              # Pytest config, fixtures
├── test_schema_propagation.py   # 19 tests
├── test_request_validation.py   # 25 tests
├── test_sentiment_filter.py     # 22 tests
└── test_end_to_end.py           # 24 tests
```

**Total:** 90 tests, 100% pass rate, 3.86s runtime

---

### Test Categories

#### 1. Schema Propagation Tests (19 tests)

**Coverage:**
- Tool discovery completeness (48 tools)
- JSON Schema structure validation
- OpenAPI transformation correctness
- Required fields handling
- Schema cache consistency
- Concurrent access

**Key Tests:**
```python
def test_tools_endpoint_returns_all_tools(client):
    """Verify all 48 MCP tools are discovered"""
    response = client.get("/tools")
    tools = response.json()
    assert len(tools) == 48

def test_input_schema_completeness(client):
    """Verify inputSchema contains validation constraints"""
    response = client.get("/tools")
    tools = response.json()
    latest_articles = next(t for t in tools if t["name"] == "latest_articles")

    schema = latest_articles["inputSchema"]
    assert "properties" in schema
    assert "min_sentiment" in schema["properties"]
    assert schema["properties"]["min_sentiment"]["minimum"] == -1
    assert schema["properties"]["min_sentiment"]["maximum"] == 1

def test_openapi_format_conversion(client):
    """Verify JSON Schema → OpenAPI transformation"""
    response = client.get("/tools?format=openapi")
    tools = response.json()

    for tool in tools:
        assert "parameters" in tool
        params = tool["parameters"]

        for param_name, param_schema in params.items():
            assert "required" in param_schema  # OpenAPI format
            assert isinstance(param_schema["required"], bool)
```

---

#### 2. Request Validation Tests (25 tests)

**Coverage:**
- Required field validation
- Type validation (integer, number, string, boolean, array)
- Constraint validation (min/max, enum)
- Error message clarity
- Validation metadata

**Key Tests:**
```python
def test_missing_required_field_rejected(client):
    """Verify requests missing required fields are rejected"""
    response = client.post("/tools/add_feed", json={"title": "Test"})
    result = response.json()

    assert result["ok"] is False
    assert "url" in result["errors"][0].lower()
    assert "required" in result["errors"][0].lower()

def test_type_validation(client):
    """Verify type errors are caught"""
    response = client.post("/tools/update_feed", json={"feed_id": "abc"})
    result = response.json()

    assert result["ok"] is False
    assert any("integer" in err.lower() for err in result["errors"])

def test_constraint_validation(client):
    """Verify constraint violations are caught"""
    response = client.post(
        "/tools/latest_articles",
        json={"limit": 10, "min_sentiment": 2.5}
    )
    result = response.json()

    assert result["ok"] is False
    assert "maximum" in result["errors"][0].lower()
```

---

#### 3. Sentiment Filter Tests (22 tests)

**Coverage:**
- Schema includes sentiment parameters
- min_sentiment / max_sentiment filtering
- Sentiment range queries
- Sorting by sentiment_score / impact_score
- Extreme values (±1.0)
- Combining with other filters

**Key Tests:**
```python
def test_min_sentiment_filter(client):
    """Test filtering by minimum sentiment"""
    response = client.post(
        "/tools/latest_articles",
        json={"limit": 20, "min_sentiment": 0.5}
    )

    if result["ok"]:
        articles = json.loads(result["data"]["content"][0])

        for article in articles:
            if "analysis" in article and article["analysis"]:
                sentiment = article["analysis"]["sentiment_score"]
                assert sentiment >= 0.5

def test_sort_by_sentiment_descending(client):
    """Test sorting by sentiment score"""
    response = client.post(
        "/tools/latest_articles",
        json={"limit": 20, "sort_by": "sentiment_score"}
    )

    if result["ok"]:
        articles = json.loads(result["data"]["content"][0])

        sentiments = [
            a["analysis"]["sentiment_score"]
            for a in articles if "analysis" in a
        ]

        # Check descending order
        assert sentiments == sorted(sentiments, reverse=True)
```

---

#### 4. End-to-End Tests (24 tests)

**Coverage:**
- System health check
- Read-only tools (safe to run)
- Complex parameters
- Error handling (404, validation, execution)
- Response format consistency
- Concurrency (10 concurrent requests)
- Performance (response time < 5s)
- Data integrity

**Key Tests:**
```python
def test_health_endpoint(client):
    """Verify system health check"""
    response = client.get("/health")
    health = response.json()

    assert health["status"] == "healthy"
    assert health["mcp_server"] == "initialized"

def test_concurrent_requests(client):
    """Test 10 concurrent requests"""
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [
            executor.submit(lambda: client.post("/tools/latest_articles", json={"limit": 5}))
            for _ in range(10)
        ]
        results = [f.result().status_code for f in futures]

    assert all(code == 200 for code in results)

def test_response_format(client):
    """Verify BaseResponse format"""
    response = client.post("/tools/system_ping", json={})
    result = response.json()

    assert "ok" in result and isinstance(result["ok"], bool)
    assert "data" in result and isinstance(result["data"], dict)
    assert "meta" in result and isinstance(result["meta"], dict)
    assert "errors" in result and isinstance(result["errors"], list)
```

---

### Test Execution

**Run all tests:**
```bash
pytest tests/integration/ -v
```

**Run specific category:**
```bash
pytest tests/integration/test_schema_propagation.py -v
pytest tests/integration/test_request_validation.py -v
pytest tests/integration/test_sentiment_filter.py -v
pytest tests/integration/test_end_to_end.py -v
```

**Run with coverage:**
```bash
pytest tests/integration/ --cov=http_mcp_server --cov-report=html
```

**Results:**
```
====================== test session starts ======================
90 passed in 3.86s

Success Rate: 100%
Average Test Time: 43ms
```

---

## Performance Metrics

### Response Times (Average)

| Endpoint | Time | Notes |
|----------|------|-------|
| `GET /tools` | 2-5ms | Cached |
| `GET /tools?format=openapi` | 5-10ms | Transform |
| `GET /mcp/openapi.json` | 10-20ms | Full spec |
| `POST /tools/system_ping` | 3-5ms | No DB |
| `POST /tools/latest_articles` | 50-100ms | DB + JSONB |
| `GET /debug/tools/schema` | 2-5ms | Cached |
| `POST /debug/validate-call` | 2-5ms | Validation only |

### Scalability

**Tool Discovery:**
- O(1) after startup (global cache)
- Scales to 100+ tools without performance impact

**Schema Transformation:**
- O(n) where n = number of properties
- Typical: 5-10ms for 8-parameter tool

**Validation:**
- O(1) lookup + O(n) validation where n = parameters
- Typical: 2-5ms for 8-parameter request

**Concurrent Requests:**
- Tested: 10 concurrent requests, all succeed
- Cache is thread-safe (read-only after startup)

---

## Configuration & Deployment

### Environment Variables
```bash
# Database
DATABASE_URL=postgresql://news_user:news_password@localhost/news_db

# Server
HTTP_BRIDGE_HOST=0.0.0.0
HTTP_BRIDGE_PORT=8001

# Logging
LOG_LEVEL=INFO
```

### Startup
```bash
# Start HTTP Bridge
python3 http_mcp_server.py

# Background mode
python3 http_mcp_server.py > /tmp/http_mcp_server.log 2>&1 &

# Health check
curl http://localhost:8001/health
```

### Verification
```bash
# Check tool count
curl http://localhost:8001/tools | python3 -m json.tool | grep -c '"name"'
# Expected: 48

# Check OpenAPI spec
curl http://localhost:8001/mcp/openapi.json | python3 -m json.tool | grep '"openapi"'
# Expected: "openapi": "3.0.0"

# Test validation
curl -X POST http://localhost:8001/debug/validate-call?tool_name=latest_articles \
  -H "Content-Type: application/json" \
  -d '{"limit": 10, "min_sentiment": 0.5}'
# Expected: {"valid": true}
```

---

## Future Enhancements

### Phase 3 Roadmap

1. **Schema Versioning**
   - Track schema changes over time
   - Version history endpoint: `/tools/{name}/versions`
   - Backward compatibility checks

2. **Schema Diff History**
   - Store schema snapshots in database
   - Compare current vs historical schemas
   - Breaking change detection

3. **Client SDK Generation**
   - Generate TypeScript/Python clients from OpenAPI spec
   - Type-safe tool calls
   - Auto-completion in IDEs

4. **Schema Migration Tools**
   - Automated schema evolution
   - Data migration scripts
   - Rollback support

5. **Enhanced Validation**
   - Custom validators (regex, business rules)
   - Cross-field validation
   - Async validation (check DB constraints)

---

## Appendix

### Key Files

| File | Lines | Purpose |
|------|-------|---------|
| `http_mcp_server.py` | 1452 | HTTP Bridge with schema reflection |
| `comprehensive_server.py` | 1400+ | MCP Server with 48 tools |
| `tests/integration/conftest.py` | 108 | Pytest configuration |
| `tests/integration/test_schema_propagation.py` | 200+ | Schema tests |
| `tests/integration/test_request_validation.py` | 347 | Validation tests |
| `tests/integration/test_sentiment_filter.py` | 512 | Sentiment tests |
| `tests/integration/test_end_to_end.py` | 433 | E2E tests |

### Dependencies

```
fastapi==0.115.6
jsonschema==4.23.0
mcp==1.4.0
pydantic==2.10.6
sqlmodel==0.0.22
pytest==8.4.2
httpx==0.28.1
```

### API Endpoints Summary

**Tool Endpoints (48 dynamic):**
- `POST /tools/{tool_name}` - Execute any MCP tool

**Schema Endpoints:**
- `GET /tools` - List all tools (JSON Schema format)
- `GET /tools?format=openapi` - List all tools (OpenAPI format)
- `GET /mcp/openapi.json` - Full OpenAPI 3.0 spec

**Debug Endpoints:**
- `GET /debug/tools/schema?tool_name={name}` - Inspect schema
- `POST /debug/tools/diff?tool1={name1}&tool2={name2}` - Compare schemas
- `POST /debug/validate-call?tool_name={name}` - Test validation

**System Endpoints:**
- `GET /health` - Health check
- `POST /mcp` - JSON-RPC 2.0 endpoint
- `GET /docs` - Swagger UI

---

**Document Status:** Complete
**Phase:** 2 (Schema Reflection) - Complete
**Next Phase:** 3 (Observability & Optimization)
**Last Review:** 2025-09-28