# Perplexity API Reference

**Last Updated:** 2025-10-05
**API Version:** Current (2025)
**Official Docs:** https://docs.perplexity.ai/

## Overview

Perplexity API provides real-time web search and AI-powered question answering with automatic citations. The API is OpenAI-compatible and offers two main endpoints for different use cases.

## API Endpoints

### 1. Chat Completions (Primary)
**Endpoint:** `https://api.perplexity.ai/chat/completions`
**Method:** POST
**Use Case:** AI-generated responses with web search context and citations

**Current Usage in News-MCP:**
```python
# app/services/research_service.py
async def execute_perplexity_research(query: str, context: str):
    response = await client.post(
        "https://api.perplexity.ai/chat/completions",
        json={
            "model": "sonar-pro",
            "messages": [
                {"role": "system", "content": "You are a research assistant..."},
                {"role": "user", "content": f"{context}\n\nQuery: {query}"}
            ],
            "max_tokens": 2000,
            "temperature": 0.2,
            "return_citations": true
        }
    )
```

### 2. Search API
**Endpoint:** `https://api.perplexity.ai/search`
**Method:** POST
**Use Case:** Direct web search with ranked results (titles + URLs)

**Example:**
```bash
curl -X POST https://api.perplexity.ai/search \
  -H "Authorization: Bearer $PERPLEXITY_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "latest AI breakthroughs 2025",
    "search_domain_filter": ["arxiv.org"],
    "search_recency_filter": "month"
  }'
```

## Models

### sonar
- **Speed:** Fast
- **Cost:** Low
- **Use Case:** Lightweight Q&A, simple queries
- **Context Window:** Standard
- **Citations:** Included

### sonar-pro
- **Speed:** Moderate
- **Cost:** Higher
- **Use Case:** Multi-step queries, in-depth research
- **Context Window:** Larger (up to 128K tokens)
- **Citations:** 2x more than sonar on average
- **Reasoning:** Advanced multi-step reasoning

**Recommendation:** Use `sonar-pro` for News-MCP research (current setting) due to complex geopolitical analysis requirements.

## Parameters

### Common Parameters

| Parameter | Type | Description | Example |
|-----------|------|-------------|---------|
| `model` | string | Model to use | `"sonar-pro"` |
| `messages` | array | Chat history | `[{"role":"user","content":"..."}]` |
| `max_tokens` | integer | Response length limit | `2000` |
| `temperature` | float | Randomness (0-1) | `0.2` (factual) |
| `return_citations` | boolean | Include source URLs | `true` |

### Advanced Search Parameters

| Parameter | Type | Description | Example |
|-----------|------|-------------|---------|
| `search_domain_filter` | array | Limit to specific domains | `["arxiv.org", "nature.com"]` |
| `search_recency_filter` | string | Time constraint | `"week"`, `"month"`, `"year"` |
| `response_format` | object | JSON schema output | See JSON Mode below |

### JSON Mode (Structured Outputs)

```json
{
  "response_format": {
    "type": "json_schema",
    "json_schema": {
      "name": "research_report",
      "schema": {
        "type": "object",
        "properties": {
          "summary": {"type": "string"},
          "key_findings": {
            "type": "array",
            "items": {"type": "string"}
          },
          "sources": {
            "type": "array",
            "items": {
              "type": "object",
              "properties": {
                "url": {"type": "string"},
                "title": {"type": "string"}
              }
            }
          }
        },
        "required": ["summary", "key_findings", "sources"]
      }
    }
  }
}
```

## Authentication

**Method:** Bearer Token
**Header:** `Authorization: Bearer YOUR_API_KEY`

**Environment Variable in News-MCP:**
```bash
export PERPLEXITY_API_KEY="your_api_key_here"
```

**Config Location:** `.env` file or environment

## Response Format

### Chat Completions Response

```json
{
  "id": "cmpl-abc123",
  "object": "chat.completion",
  "created": 1704067200,
  "model": "sonar-pro",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "Based on recent developments...",
        "citations": [
          "https://example.com/article1",
          "https://arxiv.org/abs/2401.12345"
        ]
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 150,
    "completion_tokens": 500,
    "total_tokens": 650
  }
}
```

### Key Response Fields

- `choices[0].message.content` - AI-generated response text
- `choices[0].message.citations` - Array of source URLs used
- `usage.total_tokens` - Token consumption for billing

## Use Cases for News-MCP

### 1. Current Implementation (Multi-Step Research)

**Workflow:** Article Selection → Query Generation → Perplexity Research

```python
# Step 1: Filter articles by criteria
articles = filter_articles(impact_min=0.7, timeframe="last_7d")

# Step 2: Generate research queries using LLM
queries = generate_queries(articles, prompt="Analyze geopolitical implications")

# Step 3: Execute Perplexity research for each query
for query in queries:
    research = await perplexity_research(
        query=query,
        context=articles_summary,
        model="sonar-pro"
    )
```

### 2. Potential Enhancements

#### A. Domain-Filtered Research (Specialized Sources)

```python
# Only search academic sources
"search_domain_filter": ["arxiv.org", "nature.com", "science.org"]

# Only search news agencies
"search_domain_filter": ["reuters.com", "apnews.com", "bbc.com"]

# Only search government sources
"search_domain_filter": [".gov", "europa.eu", "un.org"]
```

**Use Case:** Special Reports with verified sources only

#### B. Recency-Filtered Research (Breaking News)

```python
# Only last 24 hours
"search_recency_filter": "day"

# Only last week
"search_recency_filter": "week"

# Only last month
"search_recency_filter": "month"
```

**Use Case:** Real-time event tracking and updates

#### C. Structured JSON Output (Automated Processing)

```python
response_format = {
    "type": "json_schema",
    "json_schema": {
        "name": "geopolitical_analysis",
        "schema": {
            "type": "object",
            "properties": {
                "impact_assessment": {"type": "string"},
                "affected_regions": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                "key_actors": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                "timeline": {"type": "string"},
                "confidence_level": {
                    "type": "string",
                    "enum": ["high", "medium", "low"]
                }
            }
        }
    }
}
```

**Use Case:** Automated report generation with consistent structure

#### D. Multi-Step Reasoning Chains

```python
# Step 1: Identify main themes
themes = perplexity("What are the main themes in these articles?")

# Step 2: Deep dive per theme
analyses = []
for theme in themes:
    analysis = perplexity(
        f"Analyze {theme} with expert opinions",
        search_domain_filter=["expert_sites"]
    )
    analyses.append(analysis)

# Step 3: Synthesize findings
synthesis = perplexity(
    f"Synthesize these analyses: {analyses}",
    max_tokens=4000
)
```

**Use Case:** Complex research reports with multiple perspectives

## Rate Limits & Costs

### Current Limits (Standard Tier)
- **Requests:** Varies by plan
- **Tokens:** 128K context window max

### Planned Increase (2025)
- **Enterprise Tier:** Up to 100K requests/minute
- **For:** High-growth startups and enterprises

### Cost Considerations

**Model Pricing (Approximate):**
- `sonar`: Lower cost per token
- `sonar-pro`: Higher cost, more comprehensive results

**Optimization Tips:**
1. Use `sonar` for simple factual queries
2. Use `sonar-pro` for complex multi-step research
3. Set appropriate `max_tokens` limits
4. Cache results when possible
5. Batch queries when real-time isn't required

## 2025 Roadmap Features

### 1. Video Upload (August 2025)
**Status:** Planned
**Capabilities:**
- Video content analysis
- Frame-by-frame processing
- Visual scene understanding
- Multimodal search

**Potential Use:** Analyze video news content, extract key moments

### 2. File Search & Connectors
**Status:** In Development
**Capabilities:**
- Search across multiple file types
- External data source integration
- Enterprise connectors (SharePoint, Drive, etc.)

**Potential Use:** Search internal news archives, policy documents

### 3. Expanded Structured Outputs
**Status:** Rolling Out
**Features:**
- Universal JSON support across all models
- Complete regex support
- Advanced schema validation
- Pre-built output templates

**Potential Use:** Consistent report formatting, automated workflows

### 4. URL Content Integration
**Status:** Planned 2025
**Capabilities:**
- Specify URLs in prompts
- Direct web page content analysis
- URL parsing and extraction

**Potential Use:** Analyze specific news articles in detail

**Example:**
```python
messages = [{
    "role": "user",
    "content": "Analyze this article: https://example.com/article and compare with recent events"
}]
```

### 5. Context Management / Memory
**Status:** Planned 2025
**Features:**
- Efficient context storage
- Session-based memory
- Maintain context across multiple API calls

**Potential Use:** Long-running research sessions, iterative analysis

### 6. Enhanced Error Handling
**Status:** In Progress
**Improvements:**
- More descriptive error messages
- Clearer troubleshooting guidance
- Better API selection guidance

## Best Practices for News-MCP

### 1. Query Construction

**Good:**
```python
query = """
Based on these geopolitical events:
- Event 1: [summary]
- Event 2: [summary]

Analyze potential impacts on European energy security.
Focus on: supply routes, alternative sources, timeline.
"""
```

**Bad:**
```python
query = "What about energy?"  # Too vague
```

### 2. Temperature Settings

- **Factual Research:** `temperature=0.2` (current setting ✓)
- **Creative Writing:** `temperature=0.7-0.9`
- **Brainstorming:** `temperature=1.0`

### 3. Citation Handling

Always enable citations for research:
```python
"return_citations": true  # ✓ Currently enabled in News-MCP
```

Then store citations with research results:
```python
research_result = {
    "query": query,
    "answer": response.choices[0].message.content,
    "citations": response.choices[0].message.citations,
    "timestamp": datetime.now(),
    "model": "sonar-pro"
}
```

### 4. Error Handling

```python
try:
    response = await perplexity_api.call(...)
except httpx.HTTPStatusError as e:
    if e.response.status_code == 429:
        # Rate limit - implement backoff
        await asyncio.sleep(60)
        retry()
    elif e.response.status_code == 400:
        # Bad request - check parameters
        log.error(f"Invalid request: {e.response.text}")
    else:
        # Other errors
        raise
```

### 5. Token Management

Monitor token usage to control costs:
```python
usage = response.usage
print(f"Prompt tokens: {usage.prompt_tokens}")
print(f"Completion tokens: {usage.completion_tokens}")
print(f"Total tokens: {usage.total_tokens}")

# Store for analytics
save_usage_metrics(usage, query_id)
```

## Integration Examples

### Example 1: Domain-Filtered Geopolitical Research

```python
async def research_geopolitical_event(event_summary: str):
    """Research geopolitical event using only trusted sources"""

    response = await perplexity_client.post(
        "https://api.perplexity.ai/chat/completions",
        json={
            "model": "sonar-pro",
            "messages": [{
                "role": "user",
                "content": f"Analyze geopolitical implications: {event_summary}"
            }],
            "max_tokens": 2000,
            "temperature": 0.2,
            "return_citations": true,
            # Only search government and international org sources
            "search_domain_filter": [
                ".gov", "state.gov", "defense.gov",
                "europa.eu", "un.org", "nato.int",
                "reuters.com", "apnews.com"
            ],
            "search_recency_filter": "week"  # Only last 7 days
        }
    )

    return {
        "analysis": response.choices[0].message.content,
        "sources": response.choices[0].message.citations,
        "tokens_used": response.usage.total_tokens
    }
```

### Example 2: Structured Financial Impact Report

```python
async def generate_financial_impact_report(articles: list):
    """Generate structured financial impact analysis"""

    schema = {
        "type": "object",
        "properties": {
            "executive_summary": {"type": "string"},
            "affected_sectors": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "sector": {"type": "string"},
                        "impact_level": {
                            "type": "string",
                            "enum": ["high", "medium", "low"]
                        },
                        "description": {"type": "string"}
                    }
                }
            },
            "market_predictions": {
                "type": "array",
                "items": {"type": "string"}
            },
            "risk_factors": {
                "type": "array",
                "items": {"type": "string"}
            }
        }
    }

    response = await perplexity_client.post(
        "https://api.perplexity.ai/chat/completions",
        json={
            "model": "sonar-pro",
            "messages": [{
                "role": "user",
                "content": f"Analyze financial impact of: {articles}"
            }],
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "financial_impact",
                    "schema": schema
                }
            },
            "search_domain_filter": [
                "bloomberg.com", "reuters.com", "ft.com"
            ]
        }
    )

    # Response will be valid JSON matching schema
    return json.loads(response.choices[0].message.content)
```

### Example 3: Multi-Step Research Pipeline

```python
async def comprehensive_research_pipeline(topic: str):
    """Multi-step research with increasing depth"""

    # Step 1: Identify key aspects
    aspects_response = await perplexity_call(
        query=f"What are the key aspects to consider for: {topic}?",
        model="sonar",  # Fast model for simple query
        max_tokens=500
    )

    aspects = extract_list(aspects_response.content)

    # Step 2: Deep dive on each aspect
    deep_dives = []
    for aspect in aspects:
        analysis = await perplexity_call(
            query=f"Provide detailed analysis of {aspect} related to {topic}",
            model="sonar-pro",  # Detailed model
            max_tokens=2000,
            search_recency_filter="month"
        )
        deep_dives.append({
            "aspect": aspect,
            "analysis": analysis.content,
            "citations": analysis.citations
        })

    # Step 3: Synthesize findings
    synthesis = await perplexity_call(
        query=f"""
        Synthesize these analyses into a comprehensive report:
        {json.dumps(deep_dives, indent=2)}

        Include: executive summary, key findings, recommendations
        """,
        model="sonar-pro",
        max_tokens=4000
    )

    return {
        "topic": topic,
        "aspects_analyzed": len(aspects),
        "detailed_analyses": deep_dives,
        "synthesis": synthesis.content,
        "all_citations": collect_all_citations(deep_dives, synthesis)
    }
```

## Monitoring & Analytics

### Metrics to Track

```python
# Track in database or logs
research_metrics = {
    "query_id": uuid4(),
    "timestamp": datetime.now(),
    "model": "sonar-pro",
    "query_length": len(query),
    "response_length": len(response),
    "tokens_used": response.usage.total_tokens,
    "citations_count": len(response.citations),
    "latency_ms": response_time,
    "cost_estimate": calculate_cost(response.usage),
    "domain_filter_used": domain_filter,
    "recency_filter_used": recency_filter
}
```

### Cost Tracking

```python
# Estimate costs based on token usage
def calculate_perplexity_cost(usage, model="sonar-pro"):
    # Example pricing (check actual rates)
    PRICING = {
        "sonar": {
            "input": 0.0001,   # per 1K tokens
            "output": 0.0002
        },
        "sonar-pro": {
            "input": 0.0003,
            "output": 0.0006
        }
    }

    input_cost = (usage.prompt_tokens / 1000) * PRICING[model]["input"]
    output_cost = (usage.completion_tokens / 1000) * PRICING[model]["output"]

    return input_cost + output_cost
```

## Troubleshooting

### Common Issues

**1. Empty Citations**
- **Cause:** Query too vague or no relevant web results
- **Solution:** Make query more specific, adjust domain filter

**2. Rate Limit Errors (429)**
- **Cause:** Exceeded requests per minute
- **Solution:** Implement exponential backoff, queue requests

**3. Token Limit Exceeded**
- **Cause:** Context + response > 128K tokens
- **Solution:** Reduce `max_tokens`, split into multiple queries

**4. Irrelevant Results**
- **Cause:** Query not specific enough
- **Solution:** Use domain filter, recency filter, better prompts

## Resources

- **Official Docs:** https://docs.perplexity.ai/
- **API Roadmap:** https://docs.perplexity.ai/feature-roadmap
- **Changelog:** https://www.perplexity.ai/changelog
- **API Platform:** https://www.perplexity.ai/api-platform

## Next Steps for News-MCP

### Immediate Enhancements (Can Implement Now)

1. **Add Domain Filtering**
   - Allow users to specify trusted sources in Special Reports
   - Pre-configured source lists (academic, news, government)

2. **Add Recency Filtering**
   - Configure time windows for research (day, week, month)
   - Useful for breaking news vs. historical analysis

3. **Implement Structured Outputs**
   - JSON schema for consistent report formatting
   - Easier automated processing and storage

4. **Cost Tracking Dashboard**
   - Monitor Perplexity API usage and costs
   - Per-report cost breakdown

### Future Enhancements (When Available)

1. **Video Analysis Integration** (August 2025)
   - Analyze video news content
   - Extract key moments and quotes

2. **URL Content Integration** (2025)
   - Direct article analysis
   - Compare News-MCP articles with external research

3. **Context/Memory Management** (2025)
   - Multi-session research tracking
   - Build on previous analyses

---

**Last Updated:** 2025-10-05
**Maintainer:** News-MCP System
**Version:** 1.0
