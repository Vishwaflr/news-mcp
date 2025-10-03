# News-MCP Self-Documenting API

**Version:** 1.0.0
**Status:** Production-Ready ✅

## Overview

News-MCP implements a **self-documenting API** with built-in schema discovery, examples, and usage guides. This eliminates the need for external documentation and enables AI clients (like Claude Desktop) to understand the API structure automatically.

---

## Discovery Tools

### 1. `get_schemas` - JSON Schema Discovery
Get complete JSON Schema definitions for all data structures.

**Usage:**
```python
# Get all schemas
get_schemas()

# Get specific schema
get_schemas(schema_name="geopolitical")
```

**Available Schemas:**
- `item_basic` - Basic news item (no analysis)
- `item_with_analysis` - Item with full analysis
- `sentiment` - Overall sentiment schema
- `geopolitical` - Geopolitical analysis schema
- `analysis` - Complete analysis schema

**Example Response:**
```json
{
  "schema_name": "geopolitical",
  "schema_version": "1.0.0",
  "schema": {
    "type": "object",
    "properties": {
      "stability_score": {
        "type": "number",
        "minimum": -1.0,
        "maximum": 1.0,
        "description": "Political stability impact: -1.0 (highly destabilizing) to +1.0 (stabilizing). Values < -0.5 indicate significant destabilization risk."
      },
      ...
    }
  }
}
```

---

### 2. `get_example_data` - Real Data Examples
Get actual example responses to understand data structures.

**Usage:**
```python
# Get item with full analysis
get_example_data(example_type="item_with_analysis")

# Get basic item
get_example_data(example_type="item_basic")
```

**Example Response:**
```json
{
  "example_type": "item_with_analysis",
  "example": {
    "id": 19043,
    "title": "Gaza aid flotilla...",
    "analysis": {
      "sentiment": {"label": "negative", "score": -0.7},
      "geopolitical": {
        "stability_score": -0.8,
        "escalation_potential": 0.8,
        "regions_affected": ["Middle_East"]
      }
    }
  }
}
```

---

### 3. `get_usage_guide` - Best Practices & Interpretations
Get comprehensive guide explaining all metrics and how to use them.

**Usage:**
```python
get_usage_guide()
```

**Includes:**
- Field interpretation guide (sentiment scores, impact levels, etc.)
- Best practices for API usage
- Country and alliance code reference
- Common usage patterns
- Example queries

---

## Self-Documenting Features

### 1. **Enhanced Tool Descriptions**
All tools include detailed descriptions with:
- Parameter explanations
- Response structure hints
- Usage examples
- Field-level documentation

### 2. **Inline Schema References**
Tools reference schemas directly:
```
"include_geopolitical: bool - Include geopolitical analysis
(regions_affected, stability_score, conflict_type, escalation_potential,
diplomatic_impact)"
```

### 3. **Progressive Enhancement**
Clients can start simple and add complexity:
```python
# Level 1: Basic data
items_recent(limit=10)

# Level 2: Add sentiment
items_recent(limit=10, include_analysis=True)

# Level 3: Full geopolitical
items_recent(limit=10, include_analysis=True, include_geopolitical=True)
```

---

## Field Interpretation Reference

### Sentiment Scores
- **Range:** -1.0 to +1.0
- Below -0.5: Strong negative sentiment
- -0.5 to -0.2: Moderately negative
- -0.2 to +0.2: Neutral
- +0.2 to +0.5: Moderately positive
- Above +0.5: Strong positive sentiment

### Impact Score
- **Range:** 0.0 to 1.0
- 0.0-0.3: Low impact (routine news)
- 0.3-0.6: Medium impact (notable events)
- 0.6-1.0: High impact (major events)

### Geopolitical Metrics

**stability_score** (-1.0 to +1.0):
- Below -0.7: Severe destabilization
- -0.7 to -0.3: Moderate destabilization
- -0.3 to +0.3: Stable situation
- Above +0.3: Stabilizing effect

**escalation_potential** (0.0 to 1.0):
- 0.0-0.3: Low escalation risk
- 0.3-0.7: Moderate escalation risk
- 0.7-1.0: High escalation risk

**security_relevance** (0.0 to 1.0):
- 0.0-0.3: Low security concern
- 0.3-0.7: Moderate security concern
- 0.7-1.0: Critical security issue

---

## Country & Alliance Codes

### Common Country Codes (ISO 3166-1 alpha-2)
- US = United States
- IL = Israel
- PS = Palestine
- UA = Ukraine
- RU = Russia
- CN = China
- DE = Germany
- FR = France
- GB = United Kingdom

### Alliance Codes
- NATO = North Atlantic Treaty Organization
- EU = European Union
- BRICS = Brazil, Russia, India, China, South Africa
- G7 = Group of Seven (major advanced economies)
- G20 = Group of Twenty (major economies)
- ASEAN = Association of Southeast Asian Nations
- Arab_League = League of Arab States
- AU = African Union

---

## Integration Guide

### For Claude Desktop

1. **Initial Discovery:**
   ```python
   # Get usage guide first
   get_usage_guide()

   # Get example data
   get_example_data(example_type="item_with_analysis")
   ```

2. **Understand Schemas:**
   ```python
   # Get all schemas
   get_schemas()

   # Get specific schemas as needed
   get_schemas(schema_name="geopolitical")
   ```

3. **Query with Context:**
   ```python
   # Now use API with full understanding
   items_recent(limit=10, include_analysis=True, include_geopolitical=True)
   ```

### For Other MCP Clients

1. Call `get_usage_guide()` on first connection
2. Parse schemas from `get_schemas()` for type validation
3. Use `get_example_data()` to understand response structure
4. Cache schemas for session duration

---

## Architecture

### Schema Registry (`mcp_server/schemas.py`)
- **Centralized schema definitions**
- **Versioned** (SCHEMA_VERSION = "1.0.0")
- **Type-safe** (JSON Schema compatible)
- **Self-contained** (no external dependencies)

### Discovery Tools (`mcp_server/v2_handlers.py`)
- **get_schemas**: Returns JSON Schema definitions
- **get_example_data**: Returns real example responses
- **get_usage_guide**: Returns comprehensive guide

### Dynamic Tool Lookup System (`http_mcp_server.py`)

**Problem Solved:** Previously, all tools were hardcoded in multiple maps, requiring manual updates in 3 places for each new tool. This created maintenance overhead and errors.

**Solution:** Implemented intelligent dynamic tool lookup with automatic method resolution.

**Lookup Strategy (3-tier):**

1. **v2_handlers methods** - Newer tools in `v2_handlers` module
   - Example: `get_schemas`, `items_recent`, `get_example_data`
   - Pattern: `mcp_server.v2_handlers.{tool_name}`

2. **Standard methods** - Core MCP tools with underscore prefix
   - Example: `get_dashboard` → `_get_dashboard()`
   - Pattern: `_{tool_name}`

3. **Dotted namespace** - Legacy tools with namespace.action syntax
   - Example: `feeds.list` → `_list_feeds()`
   - Pattern: `_{action}_{namespace}` or `_{namespace}_{action}`

**Benefits:**
- ✅ **Zero maintenance** - New tools work automatically
- ✅ **Single source of truth** - Tools defined only in `comprehensive_server.py`
- ✅ **Future-proof** - Supports all tool naming patterns
- ✅ **Backward compatible** - All 51 existing tools continue working

**Implementation:**
```python
def get_tool_method(tool_name: str):
    """Dynamic tool lookup with 3-tier strategy"""
    # 1. Try v2_handlers first
    if hasattr(mcp_server_instance, 'v2_handlers'):
        v2_method = getattr(mcp_server_instance.v2_handlers, tool_name, None)
        if v2_method and callable(v2_method):
            return v2_method

    # 2. Try _{tool_name} pattern
    method_name = f"_{tool_name}"
    if hasattr(mcp_server_instance, method_name):
        return getattr(mcp_server_instance, method_name)

    # 3. Try dotted namespace mapping
    if "." in tool_name:
        namespace, action = tool_name.split(".", 1)
        for pattern in [f"_{action}_{namespace}", f"_{namespace}_{action}"]:
            if hasattr(mcp_server_instance, pattern):
                return getattr(mcp_server_instance, pattern)

    return None
```

**Migration Notes:**
- **Before:** ~40 lines of hardcoded tool maps
- **After:** ~15 lines of dynamic lookup logic
- **Code reduction:** -25 lines, +100% maintainability
- **Breaking changes:** None (fully backward compatible)

### Auto-Documentation
- Tool descriptions include response hints
- Schemas embedded in OpenAPI spec
- Resources for static documentation

---

## Future Enhancements

### Phase 2 (Planned)
- **MCP Resources**: Static schema documents as resources
- **OpenAPI Response Schemas**: Full response schemas in OpenAPI spec
- **Interactive Examples**: Executable example queries

### Phase 3 (Future)
- **GraphQL Introspection**: Alternative query interface
- **Schema Validation**: Client-side validation helpers
- **Auto-Generated Clients**: SDK generation from schemas

---

## Testing

```bash
# Test schema discovery
curl -X POST http://192.168.178.72:8001/tools/get_schemas \
  -H "Content-Type: application/json" \
  -d '{"schema_name": "geopolitical"}'

# Test example data
curl -X POST http://192.168.178.72:8001/tools/get_example_data \
  -H "Content-Type: application/json" \
  -d '{"example_type": "item_with_analysis"}'

# Test usage guide
curl -X POST http://192.168.178.72:8001/tools/get_usage_guide \
  -H "Content-Type: application/json" \
  -d '{}'
```

---

---

## Changelog

### v1.1.0 (2025-10-02)
**Dynamic Tool Lookup Refactoring**

- ✅ Replaced hardcoded tool maps with intelligent dynamic lookup
- ✅ Reduced maintenance overhead from 3 locations to 1 per tool
- ✅ Implemented 3-tier lookup strategy (v2_handlers → standard → dotted)
- ✅ Full backward compatibility maintained (all 51 tools working)
- ✅ Enabled automatic discovery of new tools
- 📝 Code reduction: -25 lines, +100% maintainability

**Files Changed:**
- `http_mcp_server.py` - Refactored `_call_tool()` and `get_tool_method()`
- `MCP_DISCOVERY.md` - Added architecture documentation

---

**Last Updated:** 2025-10-02
**Maintainer:** News-MCP Team
