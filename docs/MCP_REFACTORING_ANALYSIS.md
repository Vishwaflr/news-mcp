# MCP Server Refactoring Analysis

**Date:** 2025-10-05
**Analyzed Files:**
- `mcp_server/comprehensive_server.py` (3,458 lines)
- `mcp_server/v2_handlers.py` (530 lines)
- `mcp_server/schemas.py` (390 lines)
- `http_mcp_server.py` (1,688 lines)

---

## Executive Summary

**Current State:**
- ✅ Working MCP server with 51 tools
- ✅ Dynamic tool lookup (refactored 2025-10-02)
- ❌ Missing MCP Resources (planned but not implemented)
- ❌ Missing MCP Prompts (not implemented)
- ⚠️ Large monolithic tool definitions (773 lines of Tool() declarations)
- ⚠️ Manual tool routing with 50+ elif branches
- ⚠️ Code duplication (`safe_json_dumps` in 2 files)
- ⚠️ No schema discovery tools (documented in MCP_DISCOVERY.md but not implemented)

**Refactoring Priority:**
1. **HIGH** - Add MCP Resources for automatic feature discovery
2. **HIGH** - Implement missing Discovery Tools (get_schemas, get_example_data, get_usage_guide)
3. **MEDIUM** - Extract tool definitions to separate files
4. **MEDIUM** - Replace manual routing with dynamic dispatch
5. **LOW** - Consolidate duplicate utility functions

---

## Issue 1: Missing MCP Resources

**Problem:**
Claude Desktop has no automatic context about News-MCP capabilities. Users must manually call tools to discover features.

**Current State:**
```python
# comprehensive_server.py has NO Resources or Prompts
@self.server.list_tools()  # ✅ Implemented
async def list_tools() -> List[Tool]:
    return [...]

# ❌ NOT IMPLEMENTED:
@self.server.list_resources()
async def list_resources() -> List[Resource]:
    pass

@self.server.list_prompts()
async def list_prompts() -> List[Prompt]:
    pass
```

**Impact:**
- Claude Desktop cannot provide proactive guidance
- Users don't know what features are available
- Must guess tool names or explore blindly

**Solution:**
Implement MCP Resources based on newly created `docs/FEATURES.md`:

```python
@self.server.list_resources()
async def list_resources() -> List[Resource]:
    """Provide automatic context to MCP clients"""
    return [
        Resource(
            uri="news-mcp://system-overview",
            name="System Overview",
            description="Complete guide to News-MCP capabilities",
            mimeType="text/markdown"
        ),
        Resource(
            uri="news-mcp://features/feed-management",
            name="Feed Management Features",
            description="RSS feed operations, health monitoring, templates",
            mimeType="text/markdown"
        ),
        Resource(
            uri="news-mcp://features/analysis",
            name="AI Analysis Features",
            description="LLM-powered sentiment and impact analysis",
            mimeType="text/markdown"
        ),
        Resource(
            uri="news-mcp://features/research",
            name="Research Pipeline Features",
            description="Article filtering, query generation, Perplexity research",
            mimeType="text/markdown"
        ),
        Resource(
            uri="news-mcp://data/available-categories",
            name="Available Categories",
            description="Current article categories in the system",
            mimeType="application/json"
        ),
        Resource(
            uri="news-mcp://data/active-feeds",
            name="Active Feeds",
            description="List of currently active RSS feeds",
            mimeType="application/json"
        ),
        Resource(
            uri="news-mcp://workflows/common",
            name="Common Workflows",
            description="Step-by-step guides for typical tasks",
            mimeType="text/markdown"
        )
    ]

@self.server.read_resource()
async def read_resource(uri: str) -> str:
    """Return resource content based on URI"""
    if uri == "news-mcp://system-overview":
        # Load from docs/FEATURES.md (Executive Summary + Table of Contents)
        with open("/home/cytrex/news-mcp/docs/FEATURES.md") as f:
            content = f.read()
            # Return first 5000 characters (overview section)
            return content[:5000] + "\n\n[Full documentation available in other resources]"

    elif uri == "news-mcp://features/feed-management":
        # Extract Feed Management section from FEATURES.md
        return extract_section("FEATURES.md", "## 1. Feed Management")

    elif uri == "news-mcp://data/available-categories":
        # Query database for current categories
        with Session(engine) as session:
            categories = session.query(Category).all()
            return json.dumps([{"id": c.id, "name": c.name} for c in categories])

    # ... etc
```

**Priority:** HIGH
**Effort:** 2-3 hours
**Impact:** Dramatically improves Claude Desktop UX

---

## Issue 2: Missing Discovery Tools

**Problem:**
`docs/MCP_DISCOVERY.md` documents 3 discovery tools (`get_schemas`, `get_example_data`, `get_usage_guide`) but they were never implemented.

**Documented but Not Implemented:**
```python
# From MCP_DISCOVERY.md (documentation exists):
- get_schemas(schema_name: Optional[str]) -> JSON Schema definitions
- get_example_data(example_type: str) -> Real example responses
- get_usage_guide() -> Comprehensive usage guide

# Current state in code:
# ❌ None of these exist in comprehensive_server.py or v2_handlers.py
```

**Impact:**
- No programmatic schema discovery
- Claude Desktop can't validate request/response structures
- No real examples to show users expected data format

**Solution:**
Implement discovery tools in `v2_handlers.py`:

```python
# v2_handlers.py additions
async def get_schemas(self, schema_name: Optional[str] = None) -> List[TextContent]:
    """Get JSON Schema definitions for data structures"""
    from .schemas import SCHEMAS, SCHEMA_VERSION

    if schema_name:
        if schema_name not in SCHEMAS:
            return [TextContent(
                type="text",
                text=f"Schema '{schema_name}' not found. Available: {list(SCHEMAS.keys())}"
            )]
        schema = SCHEMAS[schema_name]
    else:
        schema = SCHEMAS  # Return all schemas

    return [TextContent(
        type="text",
        text=json.dumps({
            "schema_version": SCHEMA_VERSION,
            "schemas": schema
        }, indent=2)
    )]

async def get_example_data(self, example_type: str) -> List[TextContent]:
    """Get real example data for understanding structures"""
    with Session(engine) as session:
        if example_type == "item_with_analysis":
            # Fetch real analyzed article
            item = session.exec(
                select(Item)
                .join(ItemAnalysis)
                .where(ItemAnalysis.sentiment_score.isnot(None))
                .limit(1)
            ).first()

            if item:
                return [TextContent(
                    type="text",
                    text=json.dumps({
                        "example_type": example_type,
                        "example": item.dict(include_analysis=True)
                    }, indent=2)
                )]

        elif example_type == "item_basic":
            item = session.exec(select(Item).limit(1)).first()
            # ... etc

async def get_usage_guide(self) -> List[TextContent]:
    """Get comprehensive usage guide"""
    guide = """
# News-MCP Usage Guide

## Field Interpretations

### Sentiment Scores
- Range: -1.0 to +1.0
- Below -0.5: Strong negative
- -0.2 to +0.2: Neutral
- Above +0.5: Strong positive

### Impact Score
- Range: 0.0 to 1.0
- 0.0-0.3: Low impact
- 0.3-0.6: Medium impact
- 0.6-1.0: High impact

[... rest of guide from FEATURES.md ...]
"""
    return [TextContent(type="text", text=guide)]
```

**Add to Tool Definitions:**
```python
# comprehensive_server.py - Add to tool list
Tool(
    name="get_schemas",
    description="Get JSON Schema definitions for data structures (items, analysis, etc). Use to understand API response formats.",
    inputSchema={
        "type": "object",
        "properties": {
            "schema_name": {
                "type": "string",
                "enum": ["item_basic", "item_with_analysis", "sentiment", "geopolitical", "analysis"],
                "description": "Specific schema name (optional, returns all if not provided)"
            }
        }
    }
),
Tool(
    name="get_example_data",
    description="Get real example responses to understand data structures. Returns actual data from the system.",
    inputSchema={
        "type": "object",
        "properties": {
            "example_type": {
                "type": "string",
                "enum": ["item_with_analysis", "item_basic", "feed_health", "analysis_run"],
                "description": "Type of example to retrieve"
            }
        },
        "required": ["example_type"]
    }
),
Tool(
    name="get_usage_guide",
    description="Get comprehensive usage guide explaining all metrics, best practices, and interpretations.",
    inputSchema={"type": "object", "properties": {}}
)
```

**Priority:** HIGH
**Effort:** 3-4 hours
**Impact:** Enables self-documenting API, reduces user confusion

---

## Issue 3: Monolithic Tool Definitions

**Problem:**
All 51 tool definitions in a single 773-line `list_tools()` function makes the code hard to navigate and maintain.

**Current Structure:**
```python
# comprehensive_server.py lines 55-773
@self.server.list_tools()
async def list_tools() -> List[Tool]:
    return [
        # Feed Management (6 tools, ~150 lines)
        Tool(name="list_feeds", ...),
        Tool(name="add_feed", ...),
        # ...

        # Analytics (5 tools, ~120 lines)
        Tool(name="get_dashboard", ...),
        # ...

        # Templates (3 tools, ~80 lines)
        # ... (continues for 773 lines)
    ]
```

**Impact:**
- Difficult to find specific tool definitions
- Hard to review changes in diffs
- Cognitive overload when editing

**Solution:**
Extract tool definitions to separate Python modules:

```python
# mcp_server/tool_definitions/feed_tools.py
from mcp.types import Tool

FEED_MANAGEMENT_TOOLS = [
    Tool(
        name="list_feeds",
        description="List all RSS feeds with status, metrics and health info...",
        inputSchema={...}
    ),
    Tool(
        name="add_feed",
        description="Add new RSS feed with automatic template detection...",
        inputSchema={...}
    ),
    # ... all 6 feed tools
]

# mcp_server/tool_definitions/analysis_tools.py
ANALYSIS_TOOLS = [
    Tool(name="analysis_preview", ...),
    Tool(name="analysis_run", ...),
    # ...
]

# mcp_server/tool_definitions/__init__.py
from .feed_tools import FEED_MANAGEMENT_TOOLS
from .analysis_tools import ANALYSIS_TOOLS
from .search_tools import SEARCH_TOOLS
from .template_tools import TEMPLATE_TOOLS
from .database_tools import DATABASE_TOOLS
from .health_tools import HEALTH_TOOLS
from .scheduler_tools import SCHEDULER_TOOLS
from .category_tools import CATEGORY_TOOLS
from .source_tools import SOURCE_TOOLS
from .research_tools import RESEARCH_TOOLS

ALL_TOOLS = (
    FEED_MANAGEMENT_TOOLS +
    ANALYSIS_TOOLS +
    SEARCH_TOOLS +
    TEMPLATE_TOOLS +
    DATABASE_TOOLS +
    HEALTH_TOOLS +
    SCHEDULER_TOOLS +
    CATEGORY_TOOLS +
    SOURCE_TOOLS +
    RESEARCH_TOOLS
)

# comprehensive_server.py - Simplified
from .tool_definitions import ALL_TOOLS

@self.server.list_tools()
async def list_tools() -> List[Tool]:
    return ALL_TOOLS
```

**Benefits:**
- ✅ Logical grouping by feature area
- ✅ Easier to find and edit specific tools
- ✅ Better git diffs (changes isolated to specific files)
- ✅ Can test tool definitions independently
- ✅ Matches structure of FEATURES.md documentation

**Priority:** MEDIUM
**Effort:** 2-3 hours (mostly moving code)
**Impact:** Improved maintainability, better developer experience

---

## Issue 4: Manual Tool Routing (50+ elif branches)

**Problem:**
Tool routing uses a massive if/elif chain with 50+ branches, duplicating tool names.

**Current Implementation:**
```python
# comprehensive_server.py lines 776-870+
@self.server.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
    """Route tool calls to appropriate handlers"""
    try:
        if name == "list_feeds":
            return await self._list_feeds(**arguments)
        elif name == "add_feed":
            return await self._add_feed(**arguments)
        elif name == "update_feed":
            return await self._update_feed(**arguments)
        elif name == "delete_feed":
            return await self._delete_feed(**arguments)
        # ... 46 more elif branches ...
        elif name == "categories_update":
            return await self._categories_update(**arguments)
        else:
            # Try v2_handlers
            if hasattr(self.v2_handlers, name):
                method = getattr(self.v2_handlers, name)
                return await method(**arguments)
            return [TextContent(type="text", text=f"Unknown tool: {name}")]
```

**Problems:**
- **Duplication:** Tool name appears in 3 places (Tool definition, routing, handler method)
- **Error-prone:** Easy to mistype tool name in elif
- **Hard to maintain:** Adding new tool requires updating routing
- **Verbose:** 50+ lines just for routing

**Solution:**
Use dynamic dispatch with fallback chain (already implemented in `http_mcp_server.py` - reuse pattern):

```python
# comprehensive_server.py - Replace entire routing block
@self.server.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
    """Dynamic tool dispatch with fallback chain"""
    try:
        # 1. Try v2_handlers first (newer tools)
        if hasattr(self.v2_handlers, name):
            method = getattr(self.v2_handlers, name)
            return await method(**arguments)

        # 2. Try _{tool_name} pattern (legacy tools)
        method_name = f"_{name}"
        if hasattr(self, method_name):
            method = getattr(self, method_name)
            return await method(**arguments)

        # 3. Not found
        return [TextContent(
            type="text",
            text=f"Unknown tool: {name}. Available tools: {', '.join([t.name for t in ALL_TOOLS])}"
        )]

    except TypeError as e:
        # Argument mismatch
        return [TextContent(
            type="text",
            text=f"Invalid arguments for {name}: {str(e)}"
        )]
    except Exception as e:
        logger.error(f"Error in tool {name}: {e}", exc_info=True)
        return [TextContent(
            type="text",
            text=f"Error executing {name}: {str(e)}"
        )]
```

**Benefits:**
- ✅ Reduces code from ~100 lines to ~20 lines
- ✅ No more manual tool name mapping
- ✅ Automatically supports new tools (if method exists)
- ✅ Consistent with `http_mcp_server.py` pattern
- ✅ Better error messages

**Note:** This pattern already exists in `http_mcp_server.py` (lines 190-230), proven to work well. Just port it to `comprehensive_server.py`.

**Priority:** MEDIUM
**Effort:** 1 hour
**Impact:** Reduced code, easier to add new tools

---

## Issue 5: Code Duplication

**Problem:**
`safe_json_dumps()` is duplicated in 2 files with identical implementation.

**Duplicated Code:**
```python
# mcp_server/comprehensive_server.py (lines 31-43)
def safe_json_dumps(obj, **kwargs):
    """JSON dumps with safe handling of SQLModel Row objects"""
    class RowEncoder(json.JSONEncoder):
        def default(self, obj):
            if hasattr(obj, '_asdict'):
                return obj._asdict()
            elif hasattr(obj, '__dict__'):
                return obj.__dict__
            elif isinstance(obj, (list, tuple)):
                return list(obj)
            return str(obj)
    return json.dumps(obj, cls=RowEncoder, **kwargs)

# mcp_server/v2_handlers.py (lines 17-29) - IDENTICAL CODE
def safe_json_dumps(obj, **kwargs):
    """JSON dumps with safe handling of SQLModel Row objects"""
    # ... exact same implementation
```

**Solution:**
Extract to shared utility module:

```python
# mcp_server/utils.py (NEW FILE)
"""Shared MCP server utilities"""
import json
from typing import Any

def safe_json_dumps(obj: Any, **kwargs) -> str:
    """JSON dumps with safe handling of SQLModel Row objects

    Handles:
    - SQLModel Row objects (_asdict method)
    - SQLModel model instances (__dict__)
    - Lists and tuples
    - Fallback to str() for unknown types
    """
    class RowEncoder(json.JSONEncoder):
        def default(self, obj):
            if hasattr(obj, '_asdict'):
                return obj._asdict()
            elif hasattr(obj, '__dict__'):
                return obj.__dict__
            elif isinstance(obj, (list, tuple)):
                return list(obj)
            return str(obj)

    return json.dumps(obj, cls=RowEncoder, **kwargs)

# comprehensive_server.py
from .utils import safe_json_dumps

# v2_handlers.py
from .utils import safe_json_dumps
```

**Benefits:**
- ✅ DRY principle (Don't Repeat Yourself)
- ✅ Single source of truth for utility functions
- ✅ Easier to fix bugs (change once)
- ✅ Can add tests for utils separately

**Priority:** LOW
**Effort:** 15 minutes
**Impact:** Cleaner code, easier maintenance

---

## Issue 6: Large File Sizes

**Problem:**
Single 3,458-line file is unwieldy.

**File Breakdown:**
```
comprehensive_server.py:
  - Lines 1-50:    Imports, class init
  - Lines 51-773:  Tool definitions (723 lines)
  - Lines 776-870: Tool routing (95 lines)
  - Lines 871-3458: Handler implementations (2,587 lines, 49 methods)
```

**Impact:**
- Slow to load in editor
- Hard to navigate
- Merge conflicts more likely
- Difficult to review in PRs

**Solution:**
Split into logical modules after other refactorings:

```
mcp_server/
├── __init__.py
├── server.py (100 lines)
│   └── ComprehensiveNewsServer class (orchestration only)
├── utils.py (50 lines)
│   └── Shared utilities
├── tool_definitions/
│   ├── __init__.py (exports ALL_TOOLS)
│   ├── feed_tools.py (150 lines)
│   ├── analysis_tools.py (120 lines)
│   ├── search_tools.py (80 lines)
│   ├── template_tools.py (80 lines)
│   ├── database_tools.py (90 lines)
│   ├── health_tools.py (70 lines)
│   ├── scheduler_tools.py (50 lines)
│   ├── category_tools.py (60 lines)
│   ├── source_tools.py (60 lines)
│   └── research_tools.py (90 lines)
├── handlers/
│   ├── __init__.py
│   ├── feed_handlers.py (400 lines)
│   ├── analysis_handlers.py (500 lines)
│   ├── search_handlers.py (200 lines)
│   ├── template_handlers.py (200 lines)
│   ├── database_handlers.py (300 lines)
│   ├── health_handlers.py (250 lines)
│   ├── scheduler_handlers.py (150 lines)
│   ├── category_handlers.py (200 lines)
│   ├── source_handlers.py (150 lines)
│   └── research_handlers.py (300 lines)
├── v2_handlers.py (530 lines - keep as is)
├── schemas.py (390 lines - keep as is)
└── resources.py (NEW - 200 lines)
    └── MCP Resources implementation
```

**Benefits:**
- ✅ Easier to find code by feature area
- ✅ Smaller files load faster
- ✅ Parallel development possible (less conflicts)
- ✅ Better IDE performance
- ✅ Matches FEATURES.md structure

**Priority:** LOW (do after other refactorings)
**Effort:** 4-5 hours
**Impact:** Long-term maintainability

---

## Issue 7: Missing Error Context

**Problem:**
Tool errors don't always provide helpful context for debugging.

**Current Error Handling:**
```python
# v2_handlers.py
except Exception as e:
    logger.error(f"Error creating template: {e}")
    return [TextContent(type="text", text=f"Error creating template: {str(e)}")]
```

**Issues:**
- No request context (what parameters were passed?)
- No stack trace in returned error
- Inconsistent error format across tools

**Solution:**
Standardized error handler wrapper:

```python
# mcp_server/utils.py additions
def format_error(tool_name: str, error: Exception, arguments: Dict[str, Any] = None) -> str:
    """Format error with context for debugging"""
    error_msg = f"Error in {tool_name}: {type(error).__name__}: {str(error)}"

    if arguments:
        # Sanitize sensitive data
        safe_args = {k: v for k, v in arguments.items() if k not in ['password', 'api_key', 'token']}
        error_msg += f"\n\nArguments: {json.dumps(safe_args, indent=2)}"

    # Include stack trace for debugging
    import traceback
    error_msg += f"\n\nStack trace:\n{traceback.format_exc()}"

    return error_msg

# Use in handlers:
except Exception as e:
    logger.error(f"Error in {tool_name}: {e}", exc_info=True)
    return [TextContent(
        type="text",
        text=format_error(tool_name="template_create", error=e, arguments=arguments)
    )]
```

**Priority:** LOW
**Effort:** 30 minutes
**Impact:** Better debugging, faster issue resolution

---

## Recommended Refactoring Sequence

**Phase 1: High-Priority Features (Week 1)**
1. ✅ Create `docs/FEATURES.md` (DONE)
2. Implement MCP Resources (`mcp_server/resources.py`)
3. Implement Discovery Tools in `v2_handlers.py`
4. Test with Claude Desktop

**Phase 2: Code Organization (Week 2)**
5. Extract `safe_json_dumps` to `mcp_server/utils.py`
6. Replace manual routing with dynamic dispatch
7. Extract tool definitions to `tool_definitions/` modules
8. Update imports in `comprehensive_server.py`

**Phase 3: Modularity (Week 3, optional)**
9. Split handlers into separate modules (`handlers/`)
10. Update `server.py` to orchestrate modules
11. Add comprehensive error handling

**Phase 4: Testing & Documentation (Week 4, optional)**
12. Add unit tests for utilities
13. Add integration tests for Resources
14. Update MCP_DISCOVERY.md with implemented features
15. Create migration guide for developers

---

## Testing Strategy

**Before Refactoring:**
```bash
# Ensure current MCP server works
./scripts/start-mcp.sh

# Test basic tool call
curl -X POST http://localhost:8001/tools/list_feeds \
  -H "Content-Type: application/json" \
  -d '{}'

# Test Claude Desktop connection
# (manual test - open Claude Desktop, verify tools load)
```

**After Each Refactoring Step:**
```bash
# Run same tests
# Verify no regressions
# Check logs for errors
```

**New Feature Tests:**
```bash
# Test MCP Resources
curl http://localhost:8001/resources

# Test Resource reading
curl http://localhost:8001/resources/news-mcp://system-overview

# Test Discovery Tools
curl -X POST http://localhost:8001/tools/get_schemas \
  -H "Content-Type: application/json" \
  -d '{"schema_name": "item_with_analysis"}'

curl -X POST http://localhost:8001/tools/get_example_data \
  -H "Content-Type: application/json" \
  -d '{"example_type": "item_with_analysis"}'

curl -X POST http://localhost:8001/tools/get_usage_guide \
  -H "Content-Type: application/json" \
  -d '{}'
```

---

## Risk Assessment

**Low Risk:**
- ✅ Adding MCP Resources (new feature, no breaking changes)
- ✅ Adding Discovery Tools (new features)
- ✅ Extracting utilities to shared module (pure refactor)

**Medium Risk:**
- ⚠️ Replacing manual routing (could break tool dispatch if not careful)
- ⚠️ Extracting tool definitions (imports need to be correct)

**High Risk:**
- ⛔ Splitting into multiple handler modules (large change, many files affected)

**Mitigation:**
- Make one change at a time
- Test after each change
- Keep git commits atomic
- Can rollback easily if issues found

---

## Success Criteria

**Phase 1 Success:**
- ✅ Claude Desktop shows available categories without calling tools
- ✅ Claude Desktop understands Research Pipeline without exploration
- ✅ Users can call `get_schemas()` to understand data structures
- ✅ Users can call `get_example_data()` to see real examples

**Phase 2 Success:**
- ✅ No more duplicate utility code
- ✅ Tool routing < 30 lines (from 95 lines)
- ✅ Tool definitions organized by feature area
- ✅ All existing tools still work correctly

**Phase 3 Success (Optional):**
- ✅ No file > 500 lines
- ✅ Feature area modules match FEATURES.md structure
- ✅ Developer can find any tool in < 10 seconds

---

## Conclusion

**Critical Path:**
1. MCP Resources implementation (enables Claude Desktop discovery)
2. Discovery Tools implementation (completes self-documenting API)

**Nice-to-Have:**
3. Code organization improvements (better developer experience)

**Total Estimated Effort:** 8-12 hours (spread over 1-2 weeks)

**Expected Outcome:**
- Much better Claude Desktop UX (users know what's available)
- Cleaner, more maintainable codebase
- Foundation for future growth (easy to add new features)

---

**Next Steps:**
1. Review this analysis with user
2. Get approval for Phase 1 implementation
3. Create implementation plan for MCP Resources
4. Implement Discovery Tools
5. Test with Claude Desktop
