# Perplexity via MCP for Claude Desktop - Integration Analysis

## Frage: Kann Claude Desktop über MCP auf Perplexity zugreifen?

**Antwort: Ja, mit verschiedenen Architektur-Optionen!**

## Aktuelle Situation

### Was Claude Desktop JETZT hat:

✅ **MCP Connection zu News-MCP Server**
- 54 Tools verfügbar (inkl. 3 Discovery Tools)
- 10 Resources (System Overview, Features, etc.)
- Zugriff auf News-MCP Funktionen

❌ **KEIN direkter Perplexity Zugriff**
- Claude Desktop hat kein natives Perplexity Tool
- Muss über News-MCP Server laufen

### Was News-MCP JETZT hat:

✅ **Perplexity Integration in Research Service**
```python
# app/services/research_service.py
async def execute_perplexity_research(query: str):
    response = await client.post(
        "https://api.perplexity.ai/chat/completions",
        json={
            "model": "sonar-pro",
            "messages": [{"role": "user", "content": query}],
            "return_citations": true
        }
    )
```

✅ **MCP Tools für Research**
- `research_filter_articles`
- `research_generate_queries`
- `research_execute_full` ← Nutzt Perplexity intern

## Integration-Optionen

### Option 1: Wrapper MCP Tool (Einfachste Lösung)

**Konzept:** Expose Perplexity direkt als MCP Tool

```python
# mcp_server/v2_handlers.py

async def perplexity_search(
    self,
    query: str,
    model: str = "sonar-pro",
    domain_filter: Optional[List[str]] = None,
    recency_filter: Optional[str] = None
) -> List[TextContent]:
    """
    Execute Perplexity search query with optional filters

    Args:
        query: Search query or question
        model: Perplexity model (sonar or sonar-pro)
        domain_filter: Limit to specific domains (e.g., ["reuters.com", ".gov"])
        recency_filter: Time filter (day, week, month, year)

    Returns:
        Research results with citations
    """

    try:
        # Build request
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": query}],
            "max_tokens": 2000,
            "temperature": 0.2,
            "return_citations": True
        }

        if domain_filter:
            payload["search_domain_filter"] = domain_filter
        if recency_filter:
            payload["search_recency_filter"] = recency_filter

        # Execute
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.perplexity.ai/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.PERPLEXITY_API_KEY}",
                    "Content-Type": "application/json"
                },
                json=payload,
                timeout=60.0
            )
            response.raise_for_status()
            data = response.json()

        # Format response
        answer = data["choices"][0]["message"]["content"]
        citations = data["choices"][0]["message"].get("citations", [])

        result = f"{answer}\n\n"
        if citations:
            result += "## Sources\n"
            for i, url in enumerate(citations, 1):
                result += f"{i}. {url}\n"

        return [TextContent(type="text", text=result)]

    except Exception as e:
        logger.error(f"Perplexity search failed: {e}")
        return [TextContent(
            type="text",
            text=f"Error executing Perplexity search: {str(e)}"
        )]
```

**Tool Registration:**

```python
# mcp_server/comprehensive_server.py

Tool(
    name="perplexity_search",
    description="""Search the web using Perplexity AI with real-time information and citations.

Use this when you need:
- Current, up-to-date information from the web
- Factual answers with verified sources
- Research on recent events or topics
- Domain-specific research (academic, news, government sources)

Examples:
- "Latest developments in AI regulation"
- "Current status of European energy crisis"
- "Recent scientific papers on climate change"
""",
    inputSchema={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query or question to research"
            },
            "model": {
                "type": "string",
                "enum": ["sonar", "sonar-pro"],
                "default": "sonar-pro",
                "description": "Perplexity model: sonar (fast, cheap) or sonar-pro (deep, expensive)"
            },
            "domain_filter": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Limit search to specific domains (e.g., ['reuters.com', '.gov'])"
            },
            "recency_filter": {
                "type": "string",
                "enum": ["day", "week", "month", "year"],
                "description": "Time filter for search results"
            }
        },
        "required": ["query"]
    }
)
```

**Claude Desktop Usage:**

```
User in Claude Desktop:
"What are the latest developments in quantum computing?"

Claude Desktop:
- Calls MCP tool: perplexity_search(query="latest developments in quantum computing", recency_filter="week")
- Gets response with citations
- Formats answer for user
```

**Vorteile:**
✅ Einfachste Implementation
✅ Claude Desktop hat direkten Web-Zugriff
✅ Citations automatisch inkludiert
✅ Flexible Parameter (domain/recency filter)

**Nachteile:**
❌ Jeder Query kostet (kein Caching)
❌ Keine Kontext zu News-MCP Artikeln
❌ Claude Desktop sieht nicht, welche Feeds wir haben

---

### Option 2: Context-Aware Research Tool (Empfohlen)

**Konzept:** Perplexity mit News-MCP Kontext kombinieren

```python
# mcp_server/v2_handlers.py

async def research_with_context(
    self,
    query: str,
    article_context: bool = True,
    feed_filter: Optional[List[int]] = None,
    impact_min: float = 0.0,
    timeframe_hours: int = 24,
    model: str = "sonar-pro"
) -> List[TextContent]:
    """
    Research query using Perplexity with optional News-MCP article context

    This combines News-MCP's article database with Perplexity's web search
    to provide research grounded in both internal data and external sources.

    Args:
        query: Research question
        article_context: Include relevant News-MCP articles as context (default: True)
        feed_filter: Limit to specific feed IDs
        impact_min: Minimum impact score for context articles
        timeframe_hours: Timeframe for context articles
        model: Perplexity model

    Returns:
        Research results combining News-MCP data + Perplexity web search
    """

    context_articles = []

    # 1. Get relevant articles from News-MCP (if enabled)
    if article_context:
        try:
            # Filter articles from database
            from app.models.items import Item
            from app.models.analysis import ItemAnalysis
            from sqlmodel import select
            from datetime import datetime, timedelta

            cutoff = datetime.now() - timedelta(hours=timeframe_hours)

            query_builder = (
                select(Item)
                .join(ItemAnalysis, Item.id == ItemAnalysis.item_id)
                .where(
                    Item.published >= cutoff,
                    ItemAnalysis.impact_score >= impact_min
                )
            )

            if feed_filter:
                query_builder = query_builder.where(Item.feed_id.in_(feed_filter))

            async with get_session() as session:
                articles = session.exec(
                    query_builder.order_by(ItemAnalysis.impact_score.desc()).limit(10)
                ).all()

                context_articles = [
                    f"- {a.title} (Impact: {a.analysis.impact_score:.2f})"
                    for a in articles
                ]

        except Exception as e:
            logger.warning(f"Failed to get article context: {e}")

    # 2. Build Perplexity query with context
    perplexity_query = query

    if context_articles:
        perplexity_query = f"""Context: Recent high-impact articles from News-MCP database:
{chr(10).join(context_articles)}

Research Question: {query}

Please provide analysis considering both the article context and current web information.
"""

    # 3. Execute Perplexity search
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.perplexity.ai/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.PERPLEXITY_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": perplexity_query}],
                    "max_tokens": 3000,
                    "temperature": 0.2,
                    "return_citations": True
                },
                timeout=90.0
            )
            response.raise_for_status()
            data = response.json()

        # 4. Format response
        answer = data["choices"][0]["message"]["content"]
        citations = data["choices"][0]["message"].get("citations", [])
        tokens_used = data["usage"]["total_tokens"]

        result = "# Research Results\n\n"

        if context_articles:
            result += "## News-MCP Context\n"
            result += f"Analyzed {len(context_articles)} recent high-impact articles\n\n"

        result += "## Analysis\n"
        result += f"{answer}\n\n"

        if citations:
            result += "## External Sources\n"
            for i, url in enumerate(citations, 1):
                result += f"{i}. {url}\n"

        result += f"\n---\n**Tokens Used:** {tokens_used} | **Model:** {model}\n"

        return [TextContent(type="text", text=result)]

    except Exception as e:
        logger.error(f"Research with context failed: {e}")
        return [TextContent(
            type="text",
            text=f"Error: {str(e)}"
        )]
```

**Tool Registration:**

```python
Tool(
    name="research_with_context",
    description="""Research using Perplexity AI with optional News-MCP article context.

This tool combines:
1. News-MCP's database of analyzed articles
2. Perplexity's real-time web search

Use this when you want to:
- Research topics related to tracked news feeds
- Get web-verified information about high-impact articles
- Combine internal analysis with external sources

The tool automatically finds relevant articles from News-MCP and uses them
as context for Perplexity research, providing richer, more informed results.
""",
    inputSchema={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Research question or topic"
            },
            "article_context": {
                "type": "boolean",
                "default": True,
                "description": "Include News-MCP articles as context"
            },
            "feed_filter": {
                "type": "array",
                "items": {"type": "integer"},
                "description": "Limit to specific feed IDs (optional)"
            },
            "impact_min": {
                "type": "number",
                "default": 0.7,
                "description": "Minimum impact score for context articles"
            },
            "timeframe_hours": {
                "type": "integer",
                "default": 24,
                "description": "Timeframe for context articles in hours"
            },
            "model": {
                "type": "string",
                "enum": ["sonar", "sonar-pro"],
                "default": "sonar-pro"
            }
        },
        "required": ["query"]
    }
)
```

**Claude Desktop Usage:**

```
User in Claude Desktop:
"What are experts saying about the recent energy crisis developments?"

Claude Desktop internally:
1. Calls: research_with_context(
     query="expert opinions on recent energy crisis",
     article_context=True,
     impact_min=0.7,
     timeframe_hours=48
   )

2. News-MCP:
   - Finds 10 high-impact articles about energy crisis
   - Adds them as context to Perplexity query

3. Perplexity:
   - Searches web with article context
   - Returns analysis + citations

4. Claude Desktop:
   - Presents combined results to user
```

**Vorteile:**
✅ Best of both worlds (News-MCP + Perplexity)
✅ Context-aware research
✅ Nutzt bestehende analyzed articles
✅ Citations aus beiden Quellen

**Nachteile:**
❌ Komplexer
❌ Höhere Token-Kosten (mehr Context)

---

### Option 3: Research Templates als MCP Tools (Zukunft)

**Konzept:** Research Templates werden automatisch als MCP Tools exposed

```python
# Nach Research Template Implementation

# Wenn Template erstellt:
{
  "name": "Geopolitical Verified Sources",
  "template_type": "domain_filtered",
  "domain_filter": ["reuters.com", ".gov", "un.org"],
  "query_template": "Analyze: {query}"
}

# Wird automatisch zu MCP Tool:
Tool(
    name="research_geopolitical_verified_sources",
    description="Research geopolitical topics using only verified sources",
    inputSchema={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Research topic"}
        }
    }
)
```

**Claude Desktop sieht dann:**
- `research_geopolitical_verified_sources()`
- `research_financial_analysis()`
- `research_scientific_papers()`
- etc. - alle Templates als Tools!

---

## MCP Resources für Perplexity Guidance

**Claude Desktop sollte wissen, wann Perplexity zu nutzen ist.**

```python
# mcp_server/resources.py

Resource(
    uri="news-mcp://guide/when-to-use-perplexity",
    name="Perplexity Usage Guide",
    description="Guidelines for when to use Perplexity research vs internal News-MCP data",
    mimeType="text/markdown"
)
```

**Content:**

```markdown
# When to Use Perplexity Research

## Use Perplexity when:

✅ **Need current web information**
- Breaking news developments
- Real-time updates
- Recent expert opinions

✅ **Need external verification**
- Fact-checking News-MCP articles
- Cross-referencing sources
- Getting broader perspective

✅ **Need specialized domains**
- Academic research (arxiv.org, nature.com)
- Government sources (.gov, europa.eu)
- News agencies (reuters.com, apnews.com)

✅ **Need deep multi-step analysis**
- Complex geopolitical situations
- Financial market analysis
- Scientific literature reviews

## Use News-MCP internal data when:

✅ **Historical analysis**
- Trends over time from tracked feeds
- Impact score comparisons
- Sentiment tracking

✅ **Feed-specific research**
- Analysis of specific news sources
- Source reliability comparison
- Editorial perspective analysis

## Best Practice: Combine Both

Use `research_with_context()` to get:
- News-MCP article context (what we're tracking)
- Perplexity web search (what's happening now)
- Combined analysis with citations from both

## Cost Considerations

- **Perplexity sonar**: ~$0.30 per 1M tokens (fast, cheap)
- **Perplexity sonar-pro**: ~$0.90 per 1M tokens (deep, expensive)
- **News-MCP internal**: Free (already analyzed)

Prefer internal data when possible, use Perplexity for external verification.
```

---

## Implementation Roadmap

### Phase 1: Basic Perplexity Tool (Week 1)

```python
# Minimal viable implementation
@mcp_server.tool()
async def perplexity_search(query: str, model: str = "sonar-pro"):
    """Simple Perplexity search via MCP"""
    # ... basic implementation
```

**Testing:**
```bash
# Via Claude Desktop
"Search Perplexity for: latest AI developments"
→ Calls perplexity_search tool
→ Returns results with citations
```

### Phase 2: Context-Aware Research (Week 2)

```python
@mcp_server.tool()
async def research_with_context(query: str, article_context: bool = True):
    """Perplexity + News-MCP context"""
    # ... combines both sources
```

**Testing:**
```bash
# Via Claude Desktop
"Research energy crisis using our articles + web sources"
→ Calls research_with_context
→ Finds relevant News-MCP articles
→ Adds them to Perplexity query
→ Returns combined analysis
```

### Phase 3: Template Integration (Week 3-4)

```python
# Dynamic tool generation from templates
for template in research_templates:
    register_mcp_tool(f"research_{template.name}", template)
```

**Testing:**
```bash
# Via Claude Desktop
"Use the verified sources template to research Ukraine conflict"
→ Lists available research templates
→ User picks: research_geopolitical_verified_sources
→ Executes with domain filters
→ Returns analysis from trusted sources only
```

### Phase 4: MCP Resource for Guidance (Week 4)

```python
# Add resource
Resource(
    uri="news-mcp://guide/perplexity",
    name="Perplexity Research Guide",
    content="..." # Usage guidelines
)
```

**Claude Desktop automatically:**
- Reads resource on startup
- Knows when to use Perplexity vs internal data
- Suggests appropriate tool based on query

---

## Usage Examples in Claude Desktop

### Example 1: Simple Web Search

**User:** "What's the current status of the Paris climate agreement?"

**Claude Desktop internally:**
```
1. Recognizes: Need current web information
2. Calls: perplexity_search(
     query="current status Paris climate agreement",
     recency_filter="month"
   )
3. Gets: Answer + citations from Perplexity
4. Formats: Presents to user with sources
```

### Example 2: Context-Aware Research

**User:** "Analyze the geopolitical implications of our recent high-impact articles"

**Claude Desktop internally:**
```
1. Recognizes: Need both News-MCP context + web analysis
2. Calls: research_with_context(
     query="geopolitical implications",
     article_context=True,
     impact_min=0.8,
     timeframe_hours=48
   )
3. News-MCP: Finds 10 high-impact articles
4. Perplexity: Searches web with article context
5. Returns: Combined analysis with dual sources
```

### Example 3: Domain-Filtered Research

**User:** "What do government sources say about energy security?"

**Claude Desktop internally:**
```
1. Recognizes: Need domain-specific search
2. Calls: perplexity_search(
     query="energy security government analysis",
     domain_filter=[".gov", "europa.eu", "un.org"],
     model="sonar-pro"
   )
3. Perplexity: Searches only government domains
4. Returns: Official sources + citations
```

### Example 4: Research Template (Future)

**User:** "Use our scientific research template to analyze quantum computing breakthroughs"

**Claude Desktop internally:**
```
1. Lists: available research templates
2. User picks: research_scientific_papers
3. Calls: research_scientific_papers(
     query="quantum computing breakthroughs"
   )
4. Template config:
   - domain_filter: ["arxiv.org", "nature.com", "science.org"]
   - recency_filter: "month"
   - model: "sonar-pro"
5. Returns: Academic analysis with paper citations
```

---

## Cost Management

### Tracking Perplexity Usage via MCP

```python
# Add to all Perplexity tools
async def perplexity_search(...):
    # Execute
    result = await call_perplexity(...)

    # Track usage
    from app.services.api_usage_tracker import APIUsageTracker

    async with get_session() as session:
        tracker = APIUsageTracker(session)
        tracker.log_perplexity_call(
            system="mcp",
            model=model,
            tokens_used=result["usage"]["total_tokens"],
            cost=calculate_cost(...),
            triggered_by="claude_desktop"
        )

    return formatted_result
```

**Dashboard View:**

```
Perplexity Usage by Source:
- Main App:        45 calls, $0.12
- Research System: 23 calls, $0.08
- MCP/Claude:      67 calls, $0.25  ← NEW!

Total Cost Today: $0.45
```

### Rate Limiting

```python
# Prevent Claude Desktop from spamming Perplexity

from app.services.rate_limiter import RateLimiter

perplexity_limiter = RateLimiter(
    max_calls_per_hour=50,
    max_calls_per_day=200
)

async def perplexity_search(query: str):
    # Check rate limit
    if not perplexity_limiter.allow_call(source="mcp"):
        return [TextContent(
            type="text",
            text="Rate limit exceeded. Please wait before making more Perplexity requests."
        )]

    # Execute...
```

---

## Security Considerations

### API Key Protection

```python
# NEVER expose API key to Claude Desktop

# ✅ CORRECT: Server-side execution
async def perplexity_search(query: str):
    # API key stays on server
    headers = {"Authorization": f"Bearer {settings.PERPLEXITY_API_KEY}"}
    # ...

# ❌ WRONG: Don't send API key to client
# Never include API key in tool responses!
```

### Input Validation

```python
async def perplexity_search(query: str, ...):
    # Validate inputs
    if len(query) > 5000:
        raise ValueError("Query too long (max 5000 chars)")

    if domain_filter and len(domain_filter) > 50:
        raise ValueError("Too many domain filters (max 50)")

    # Sanitize query
    query = query.strip()

    # ...
```

---

## Comparison: Direct Perplexity vs News-MCP Context

### Scenario: "Analyze current energy crisis"

**Option A: Direct Perplexity (perplexity_search)**

```
Input: "Analyze current European energy crisis"

Perplexity:
- Searches entire web
- Returns general analysis
- Citations from random sources
- No connection to News-MCP data

Result: Generic web analysis
Cost: ~$0.001 per query
```

**Option B: With News-MCP Context (research_with_context)**

```
Input: "Analyze current European energy crisis"

Process:
1. News-MCP finds 10 relevant articles (impact > 0.7)
2. Context added: "Recent articles we tracked: ..."
3. Perplexity searches with context
4. Returns analysis considering both sources

Result:
- Grounded in News-MCP articles
- Enhanced with web research
- Dual citation sources (internal + external)

Cost: ~$0.002 per query (more context = more tokens)
Value: Much higher quality!
```

**Recommendation: Offer both!**

- Simple queries → `perplexity_search`
- Complex analysis → `research_with_context`
- Let Claude Desktop choose based on query

---

## Monitoring & Analytics

### MCP Tool Usage Dashboard

```python
# Track which MCP tools Claude Desktop uses most

SELECT
    tool_name,
    COUNT(*) as call_count,
    AVG(tokens_used) as avg_tokens,
    SUM(cost_estimate) as total_cost
FROM mcp_tool_usage
WHERE triggered_by = 'claude_desktop'
    AND timestamp >= NOW() - INTERVAL '7 days'
GROUP BY tool_name
ORDER BY call_count DESC;
```

**Expected Results:**

```
Tool Name                    | Calls | Avg Tokens | Total Cost
-----------------------------|-------|------------|------------
latest_articles              | 245   | 150        | $0.00
perplexity_search            | 89    | 1200       | $0.15
research_with_context        | 34    | 2500       | $0.12
search_articles              | 67    | 200        | $0.00
get_dashboard                | 45    | 100        | $0.00
```

**Insights:**
- Perplexity tools are expensive but valuable
- Context-aware research has highest value/cost ratio
- Most queries can be answered with internal data

---

## Recommended Implementation

### Start with Option 1 + Option 2

**Week 1: Basic Perplexity Tool**
```python
@mcp_tool("perplexity_search")
async def perplexity_search(query, model="sonar-pro", domain_filter=None):
    # Simple wrapper around Perplexity API
    # No News-MCP context
    # Fast to implement
```

**Week 2: Context-Aware Research**
```python
@mcp_tool("research_with_context")
async def research_with_context(query, article_context=True, ...):
    # Combines News-MCP articles + Perplexity
    # Higher value, more complex
```

**Week 3-4: Template Integration**
```python
# Dynamic tools from research templates
# Requires Research Template system to be implemented first
```

**Week 5: Resource + Guidance**
```python
# Add MCP resource explaining when to use each tool
# Claude Desktop learns optimal usage patterns
```

---

## Summary

**Ja, Claude Desktop kann Perplexity über MCP nutzen!**

**3 Implementierungs-Optionen:**

1. **Simple Wrapper** - Direkter Perplexity Zugriff
   - Schnell implementiert
   - Generische Web-Suche
   - Keine News-MCP Integration

2. **Context-Aware** - Kombiniert News-MCP + Perplexity ⭐ **Empfohlen**
   - Best of both worlds
   - Höchster Mehrwert
   - Nutzt bestehende Analyse

3. **Template-Based** - Research Templates als MCP Tools
   - Zukunft (nach Template-System)
   - Domain-spezifisch
   - Vorkonfiguriert

**Benefits:**
✅ Claude Desktop hat Web-Zugriff via Perplexity
✅ Kann News-MCP Kontext nutzen
✅ Citations automatisch inkludiert
✅ Flexible (Domain/Time Filter)
✅ Cost-Tracking integriert

**Nächster Schritt:**
Implementierung von `perplexity_search` + `research_with_context` als MCP Tools.

Soll ich damit beginnen?
