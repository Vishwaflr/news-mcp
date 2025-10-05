# News-MCP Feature Reference

**Version:** 1.0.0
**Last Updated:** 2025-10-05
**Purpose:** Comprehensive reference of all application capabilities for MCP clients

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [System Overview](#system-overview)
3. [Feature Catalog](#feature-catalog)
   - [Feed Management](#1-feed-management)
   - [Article Processing & Search](#2-article-processing--search)
   - [AI Analysis System](#3-ai-analysis-system)
   - [Research Pipeline](#4-research-pipeline)
   - [Special Reports](#5-special-reports)
   - [Monitoring & Health](#6-monitoring--health)
   - [Database Operations](#7-database-operations)
   - [Templates & Processing](#8-templates--processing)
   - [Categories & Sources](#9-categories--sources)
   - [Scheduler & Workers](#10-scheduler--workers)
   - [Auto-Analysis System](#11-auto-analysis-system)
   - [Web UI & Admin Interface](#12-web-ui--admin-interface)
4. [Common Workflows](#common-workflows)
5. [Access Methods](#access-methods)
6. [System Statistics](#system-statistics)

---

## Executive Summary

**News-MCP** is a comprehensive RSS feed aggregation and AI analysis platform that:

- **Aggregates** news from 37+ RSS/Atom feeds
- **Analyzes** articles using GPT-4o, Claude, and other LLMs for sentiment and impact scoring
- **Generates** automated special reports based on article selection criteria
- **Researches** topics using LLM-driven query generation + Perplexity AI
- **Monitors** feed health, system performance, and API costs
- **Provides** 260+ REST API endpoints, 51 MCP tools, and 6 admin UI pages

**Current Scale:**
- 37+ active feeds monitored
- 11,600+ articles stored and analyzed
- 17.67% of articles have geopolitical risk analysis
- Multiple LLM providers supported (OpenAI, Anthropic, Perplexity)

---

## System Overview

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Access Layer                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   MCP Tools  │  │  REST API    │  │   Web UI     │      │
│  │  (51 tools)  │  │ (260+ endpt) │  │  (6 pages)   │      │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘      │
└─────────┼──────────────────┼──────────────────┼─────────────┘
          │                  │                  │
┌─────────┼──────────────────┼──────────────────┼─────────────┐
│         ▼                  ▼                  ▼              │
│                   Core Services Layer                        │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Feed Management | Analysis Orchestrator | Research  │   │
│  │  Auto-Analysis   | Special Reports        | Health   │   │
│  └──────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────┘
          │
┌─────────┼───────────────────────────────────────────────────┐
│         ▼                                                     │
│              Background Workers Layer                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐     │
│  │  Scheduler  │  │  Analysis   │  │    Content      │     │
│  │   Runner    │  │   Worker    │  │   Generator     │     │
│  └─────────────┘  └─────────────┘  └─────────────────┘     │
└──────────────────────────────────────────────────────────────┘
          │
┌─────────┼───────────────────────────────────────────────────┐
│         ▼                                                     │
│                    Data Layer                                 │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  PostgreSQL Database (35 tables)                      │   │
│  │  - Feeds, Items, Analysis Results                     │   │
│  │  - Health Metrics, Run Logs                           │   │
│  │  - Templates, Categories, Sources                     │   │
│  └──────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────┘
```

### Key Components

1. **Feed System** - RSS/Atom feed monitoring with auto-refresh
2. **Analysis Engine** - LLM-powered sentiment & impact analysis
3. **Research Pipeline** - Article filtering → Query generation → Perplexity research
4. **Special Reports** - Automated LLM-based report generation
5. **Processing Templates** - Customizable article extraction rules
6. **Health Monitoring** - Feed health tracking, Prometheus metrics
7. **Background Workers** - Scheduler, analysis worker, content generator
8. **Web Interface** - Bootstrap 5 admin UI with HTMX live updates

---

## Feature Catalog

## 1. Feed Management

### Overview
Manage RSS/Atom feed sources with automatic fetching, health monitoring, and template-based content extraction.

### Core Capabilities

#### 1.1 Feed CRUD Operations

**Purpose:** Add, configure, and manage RSS feed sources

**Access Methods:**
- **MCP Tools:** `list_feeds`, `add_feed`, `update_feed`, `delete_feed`
- **REST API:** `/feeds/*`
- **Web UI:** `/admin/feeds`

**Features:**
- ✅ Add RSS/Atom feeds with URL validation
- ✅ Automatic template assignment based on feed domain
- ✅ Configure fetch interval (5-1440 minutes per feed)
- ✅ Set feed status (ACTIVE/PAUSED/ERROR)
- ✅ Enable/disable auto-analysis per feed
- ✅ Assign feeds to multiple categories
- ✅ Delete feeds with cascade (removes all articles)
- ✅ Test feed URL before adding (preview 5-20 sample articles)

**Example Usage (MCP):**
```python
# Test a feed before adding
test_feed(url="https://techcrunch.com/feed/", show_items=5)

# Add feed with auto-analysis enabled
add_feed(
    url="https://techcrunch.com/feed/",
    title="TechCrunch",
    fetch_interval_minutes=15,
    auto_assign_template=True
)

# Update feed interval
update_feed(feed_id=5, fetch_interval_minutes=30)

# Pause problematic feed
update_feed(feed_id=5, status="PAUSED")
```

#### 1.2 Feed Health Monitoring

**Purpose:** Track feed reliability, performance, and errors

**Access Methods:**
- **MCP Tools:** `feeds_health`, `feed_diagnostics`, `feed_performance`
- **REST API:** `/feeds/health/*`
- **Web UI:** Health indicators in feed list

**Metrics Tracked:**
- Success rate (last 7/30 days)
- Average response time (ms)
- Uptime percentage
- Consecutive failure count
- Last successful/failed fetch timestamp
- Items per fetch average
- Error patterns and frequency

**Health Status Levels:**
- 🟢 **OK:** Success rate > 95%, response time < 2s
- 🟡 **WARN:** Success rate 80-95% OR response time 2-5s
- 🔴 **FAIL:** Success rate < 80% OR response time > 5s OR 5+ consecutive failures

**Example Usage (MCP):**
```python
# Get health for all feeds
feeds_health()

# Diagnose specific problematic feed
feed_diagnostics(feed_id=8)

# Analyze feed performance over 30 days
feed_performance(feed_id=12, days=30)
```

#### 1.3 Manual Feed Refresh

**Purpose:** Trigger immediate feed update, bypassing scheduler

**Access Methods:**
- **MCP Tool:** `refresh_feed`
- **REST API:** `POST /feeds/{feed_id}/refresh`
- **Web UI:** Refresh button in feed list

**Features:**
- ✅ Immediate fetch (ignores scheduler intervals)
- ✅ Force option to bypass rate limiting
- ✅ Returns fetch results immediately
- ✅ Useful after fixing feed URL or testing template changes

**Example Usage (MCP):**
```python
# Standard refresh
refresh_feed(feed_id=10)

# Force refresh (skip rate limit check)
refresh_feed(feed_id=10, force=True)
```

### Related Features
- **Feed Scheduler** (see [Scheduler & Workers](#10-scheduler--workers)) - Automated periodic fetching
- **Template Assignment** (see [Templates & Processing](#8-templates--processing)) - Content extraction rules
- **Auto-Analysis** (see [Auto-Analysis System](#11-auto-analysis-system)) - Automatic article analysis

---

## 2. Article Processing & Search

### Overview
Access, search, and filter news articles with advanced criteria including sentiment scores, impact ratings, and keyword matching.

### Core Capabilities

#### 2.1 Article Retrieval

**Purpose:** List and filter articles with pagination and sorting

**Access Methods:**
- **MCP Tools:** `latest_articles`, `items_recent`
- **REST API:** `/items/*`, `/api/v1/items/*`
- **Web UI:** Article lists in dashboard and feed views

**Filter Options:**
- Feed ID (specific feed)
- Time range (since N hours, date range)
- Keywords (include/exclude)
- Sentiment score range (-1.0 to 1.0)
- Impact score range (0.0 to 1.0)
- Category
- Deduplication (remove duplicate content by hash)

**Sort Options:**
- `created_at` - Newest first (default)
- `published` - By original publication date
- `sentiment_score` - Most positive/negative first
- `impact_score` - Highest impact first

**Example Usage (MCP):**
```python
# Get 20 latest articles from last 24h
latest_articles(limit=20, since_hours=24)

# Get highly positive articles from specific feed
latest_articles(
    feed_id=5,
    min_sentiment=0.5,
    sort_by="sentiment_score",
    limit=10
)

# Get high-impact articles excluding certain keywords
latest_articles(
    min_impact=0.7,
    exclude_keywords=["sports", "entertainment"],
    sort_by="impact_score"
)

# Recent items with deduplication
items_recent(
    limit=50,
    since="2025-10-01T00:00:00Z",
    dedupe=True
)
```

#### 2.2 Full-Text Search

**Purpose:** Search articles by content across title and description

**Access Methods:**
- **MCP Tools:** `search_articles`, `items_search`
- **REST API:** `/items/search`, `/api/v1/items/search`
- **Web UI:** Search bar in admin interface

**Features:**
- ✅ Search across title + description fields
- ✅ Date range filtering
- ✅ Feed-specific search
- ✅ Category filtering
- ✅ Pagination support (offset/limit)
- ✅ Case-insensitive matching

**Example Usage (MCP):**
```python
# Basic search
search_articles(query="AI regulation", limit=50)

# Search with date range
search_articles(
    query="climate change",
    date_from="2025-09-01",
    date_to="2025-09-30"
)

# Feed-specific search
search_articles(
    query="blockchain",
    feed_id=12,
    limit=20
)

# Advanced search with pagination
items_search(
    q="Ukraine conflict",
    time_range={"from": "2025-09-01T00:00:00Z", "to": "2025-09-30T23:59:59Z"},
    limit=50,
    offset=100
)
```

#### 2.3 Trending Topics Analysis

**Purpose:** Discover emerging themes by keyword frequency

**Access Methods:**
- **MCP Tool:** `trending_topics`
- **REST API:** `/items/trending`
- **Web UI:** Trending section in statistics dashboard

**Features:**
- ✅ Keyword frequency analysis over time window
- ✅ Configurable minimum frequency threshold (filter noise)
- ✅ Top N results (default 20)
- ✅ Time window selection (hours)

**Example Usage (MCP):**
```python
# Get top 20 trending keywords from last 24 hours
trending_topics(hours=24, min_frequency=3, top_n=20)

# Find major topics from last 48 hours
trending_topics(hours=48, min_frequency=5, top_n=30)
```

#### 2.4 Data Export

**Purpose:** Export articles for external analysis, backups, or reporting

**Access Methods:**
- **MCP Tool:** `export_data`
- **REST API:** `/export/*`
- **Web UI:** Export button in feed/article views

**Formats:**
- JSON (structured data, default)
- CSV (spreadsheet-compatible)
- XML (legacy systems)

**Export Types:**
- `articles` - News items with analysis
- `feeds` - Feed configurations
- `statistics` - System metrics

**Example Usage (MCP):**
```python
# Export last 7 days of articles as CSV
export_data(
    format="csv",
    data_type="articles",
    since_days=7,
    limit=5000
)

# Export articles from specific feed as JSON
export_data(
    format="json",
    data_type="articles",
    feed_id=25,
    limit=1000
)

# Export all feed configurations
export_data(
    format="json",
    data_type="feeds"
)
```

### Related Features
- **Sentiment Analysis** (see [AI Analysis System](#3-ai-analysis-system)) - Enables sentiment filtering
- **Impact Scoring** (see [AI Analysis System](#3-ai-analysis-system)) - Enables impact filtering
- **Feed Management** (see [Feed Management](#1-feed-management)) - Source of articles

---

## 3. AI Analysis System

### Overview
Run LLM-powered sentiment and impact analysis on articles using GPT-4o, Claude, and other models. Includes cost estimation, run management, and automated analysis queuing.

### Core Capabilities

#### 3.1 Analysis Run Control

**Purpose:** Execute batch AI analysis with cost estimation and run management

**Access Methods:**
- **MCP Tools:** `analysis_preview`, `analysis_run`, `analysis_history`
- **REST API:** `/api/analysis/*`, `/api/v1/analysis/*`
- **Web UI:** `/admin/analysis-manager` (Analysis Control Interface)

**Workflow:**
1. **Preview** - Estimate cost and item selection
2. **Start** - Trigger analysis run
3. **Monitor** - Track progress
4. **Review** - View results and costs

**Analysis Scopes:**
- **Items** - Analyze specific article IDs
- **Feeds** - Analyze all items from selected feeds
- **Smart** - Analyze unanalyzed recent items (recommended)

**Supported Models:**
- `gpt-5-nano` - $0.05/$0.40 per 1M tokens (cheapest)
- `gpt-5-mini` - $0.25/$2.00 per 1M tokens
- `gpt-5` - $1.25/$10.00 per 1M tokens
- `gpt-4.1-nano` - $0.10/$0.40 per 1M tokens
- `gpt-4.1-mini` - $0.40/$1.60 per 1M tokens
- `gpt-4.1` - $2.00/$8.00 per 1M tokens
- `gpt-4o-mini` - $0.15/$0.60 per 1M tokens
- `gpt-4o` - $2.50/$10.00 per 1M tokens

**Example Usage (MCP):**
```python
# Preview analysis of latest 100 articles
analysis_preview(
    model="gpt-5-nano",
    selector={"latest": 100},
    cost_estimate=True
)

# Start analysis run with persistence
analysis_run(
    model="gpt-5-nano",
    selector={"latest": 50},
    persist=True,
    tags=["daily-batch"]
)

# Analyze specific feeds
analysis_run(
    model="gpt-4.1-nano",
    selector={"feeds": [5, 12, 18]},
    persist=True
)

# View analysis history
analysis_history(limit=50, status="done")
```

#### 3.2 Analysis Output

**Purpose:** Structured AI-generated insights stored with each article

**Data Generated:**
- **Sentiment Analysis:**
  - Label: positive/neutral/negative
  - Score: -1.0 (very negative) to +1.0 (very positive)
  - Confidence: 0.0 to 1.0

- **Impact Scores:**
  - Overall impact: 0.0 (low) to 1.0 (high)
  - Regional impact levels
  - Sectoral impact (economy, politics, etc.)
  - Geopolitical risk assessment (17.67% coverage)

- **Urgency Scoring:**
  - Time sensitivity rating
  - Breaking news detection

- **Content Processing:**
  - Auto-generated summaries
  - Entity extraction (people, organizations, locations)
  - Keyword/tag extraction

**Geopolitical Analysis (Advanced):**
For 17.67% of analyzed articles, additional geopolitical metrics:
- Stability score: -1.0 (destabilizing) to +1.0 (stabilizing)
- Escalation potential: 0.0 to 1.0
- Security relevance: 0.0 to 1.0
- Affected regions/countries
- Conflict type classification
- Diplomatic impact assessment

#### 3.3 Run Management & Limits

**Purpose:** Prevent runaway costs and API abuse

**Daily Limits:**
- **Total runs:** 5 per day (configurable)
- **Auto-analysis runs:** 3 per day (subset of total)
- **Manual runs:** Remaining quota after auto-runs

**Hourly Limits:**
- **Max runs per hour:** 2

**Concurrent Limits:**
- **Max simultaneous runs:** 2

**Queue Behavior:**
- Runs exceeding limits are queued
- Queue processed FIFO when slots available
- View queue status via `/api/analysis/queue-status`

**Emergency Controls:**
- **System-wide halt:** Stop all analysis immediately
- **Resume:** Restart analysis after halt
- **Cancel run:** Stop specific run in progress

**Example Usage (REST API):**
```bash
# Emergency halt (stops all analysis)
POST /api/analysis/emergency-halt

# Resume after halt
POST /api/analysis/resume

# Cancel specific run
POST /api/analysis/runs/{run_id}/cancel
```

#### 3.4 Cost Tracking

**Purpose:** Monitor and control LLM API spending

**Features:**
- ✅ Pre-run cost estimation with token counts
- ✅ Per-run cost recording
- ✅ Daily/monthly cost aggregation
- ✅ Cost breakdown by model
- ✅ Budget recommendations

**Cost Metrics:**
- Input tokens used
- Output tokens used
- Total cost (USD)
- Cost per article average

**Example Cost Calculation:**
```
Analyzing 100 articles with gpt-5-nano:
- Average article: ~500 tokens
- System prompt: ~200 tokens
- Total input: 100 * 700 = 70,000 tokens
- Average output: ~150 tokens per article = 15,000 tokens
- Input cost: 70,000 / 1M * $0.05 = $0.0035
- Output cost: 15,000 / 1M * $0.40 = $0.0060
- Total: ~$0.0095 (~$0.0001 per article)
```

### Related Features
- **Auto-Analysis** (see [Auto-Analysis System](#11-auto-analysis-system)) - Automated analysis on new items
- **Run Queue Manager** - Handles concurrency and limits
- **Idempotency System** - Prevents duplicate analysis

---

## 4. Research Pipeline

### Overview
LLM-driven research system that filters articles, generates research queries using Claude/GPT, and executes those queries via Perplexity AI with citation tracking.

### Core Capabilities

#### 4.1 Article Filtering

**Purpose:** Select articles for research based on sophisticated criteria

**Access Methods:**
- **MCP Tool:** `research_filter_articles`
- **REST API:** `/api/research/filter`

**Filter Criteria:**
- **Time range:** last_24h, last_7d, last_30d
- **Categories:** Filter by article categories
- **Semantic tags:**
  - Actors (e.g., "Trump", "Biden", "Putin")
  - Themes (e.g., "trade war", "climate policy")
  - Regions (e.g., "Middle East", "Europe", "Asia")
- **Sentiment:** positive, neutral, negative
- **Impact scores:** Min/max impact thresholds
- **Sorting:** published_desc, impact_desc, created_desc
- **Limit:** Max articles to return (1-100)

**Example Usage (MCP):**
```python
# Filter high-impact geopolitical articles
research_filter_articles(
    timeframe="last_30d",
    categories=["geopolitics_security"],
    actors=["Trump", "Xi Jinping"],
    impact_min=0.7,
    max_articles=20,
    order_by="impact_desc"
)

# Filter negative sentiment articles about specific themes
research_filter_articles(
    timeframe="last_7d",
    themes=["trade war", "sanctions"],
    sentiment=["negative"],
    regions=["Asia"],
    max_articles=30
)
```

#### 4.2 Query Generation

**Purpose:** Generate targeted research questions from filtered articles using LLM

**Access Methods:**
- **MCP Tool:** `research_generate_queries`
- **REST API:** `/api/research/generate-queries`

**Features:**
- ✅ LLM-powered query generation (GPT-4o, GPT-4o-mini)
- ✅ Custom user prompts for query direction
- ✅ Generates 3-10 research questions based on article content
- ✅ Context-aware (uses article summaries and metadata)

**Example Usage (MCP):**
```python
# Generate geopolitical research queries
research_generate_queries(
    filter_config={
        "timeframe": "last_30d",
        "categories": ["geopolitics_security"],
        "impact_min": 0.6
    },
    prompt="Generate questions about geopolitical implications and security concerns",
    model="gpt-4o-mini"
)

# Generate economic analysis queries
research_generate_queries(
    filter_config={
        "timeframe": "last_7d",
        "themes": ["inflation", "recession"]
    },
    prompt="Generate questions analyzing economic trends and policy impacts",
    model="gpt-4o"
)
```

#### 4.3 Full Research Execution

**Purpose:** Execute complete pipeline: Filter → Generate → Research

**Access Methods:**
- **MCP Tool:** `research_execute_full`
- **REST API:** `/api/research/execute`

**Perplexity Models:**
- `sonar` - Standard research (fast, cost-effective)
- `sonar-pro` - Enhanced research (deeper analysis)
- `sonar-reasoning` - Advanced reasoning (most thorough)

**Output:**
- Generated research queries
- Perplexity research results for each query
- Citations and sources
- Synthesized insights

**Example Usage (MCP):**
```python
# Full research pipeline on recent geopolitical events
research_execute_full(
    filter_config={
        "timeframe": "last_7d",
        "categories": ["geopolitics_security"],
        "impact_min": 0.7,
        "max_articles": 20
    },
    prompt="Analyze geopolitical developments and their implications for global stability",
    llm_model="gpt-4o-mini",
    perplexity_model="sonar-pro"
)
```

**Typical Workflow:**
```
1. User specifies article filter criteria
2. System filters articles from database
3. LLM generates 5-10 research queries based on articles
4. Each query sent to Perplexity API
5. Perplexity returns research with citations
6. System aggregates results
7. User receives comprehensive research report
```

### Use Cases

**Political Analysis:**
```python
research_execute_full(
    filter_config={
        "timeframe": "last_30d",
        "actors": ["Trump", "Harris"],
        "themes": ["election", "policy"]
    },
    prompt="Analyze political developments and campaign strategies"
)
```

**Market Research:**
```python
research_execute_full(
    filter_config={
        "timeframe": "last_7d",
        "themes": ["AI", "regulation", "market"],
        "impact_min": 0.5
    },
    prompt="Research AI regulation trends and market impact"
)
```

### Related Features
- **Sentiment Analysis** - Enables sentiment-based filtering
- **Article Search** - Provides article pool for research

---

## 5. Special Reports

### Overview
Automated LLM-based report generation system that selects articles based on criteria and generates comprehensive reports using configurable templates.

### Core Capabilities

#### 5.1 Report Template Management

**Purpose:** Define reusable report configurations with article selection rules

**Access Methods:**
- **REST API:** `/api/v2/special-reports/*`
- **Web UI:** `/admin/special-reports`

**Template Configuration:**
- **Name & Description:** Report identification
- **Target Audience:** Who the report is for
- **Active Status:** Enable/disable without deletion
- **Article Selection Criteria:**
  - Feed selection (specific feeds or all)
  - Time range (e.g., last 24 hours, last week)
  - Maximum articles (limit for LLM context)
  - Keyword filters (include/exclude)
  - Impact/sentiment thresholds
- **LLM Configuration:**
  - Model selection (GPT-4o, Claude, etc.)
  - Custom system prompt template
  - Output format specification
- **Schedule:** (Planned) Automatic periodic generation

**Example Configuration:**
```json
{
  "name": "Daily Tech News Summary",
  "description": "AI-generated summary of top tech stories",
  "target_audience": "Tech executives",
  "active": true,
  "selection_criteria": {
    "feeds": [5, 12, 18],
    "timeframe": "last_24h",
    "max_articles": 50,
    "impact_min": 0.5,
    "keywords": ["AI", "cloud", "security"]
  },
  "llm_config": {
    "model": "gpt-4o-mini",
    "system_prompt": "Generate executive summary...",
    "max_tokens": 1500
  }
}
```

#### 5.2 Report Generation

**Purpose:** Trigger on-demand or scheduled report generation

**Access Methods:**
- **REST API:** `POST /api/v2/special-reports/{id}/generate`
- **Web UI:** Generate button in report template list

**Generation Process:**
1. **Article Selection:** Query database using template criteria
2. **Preview:** Show selected articles and cost estimate
3. **LLM Generation:** Send articles to LLM with system prompt
4. **Output Processing:** Format generated content
5. **Storage:** Save report with metadata
6. **Delivery:** (Planned) Email, API webhook, or PDF export

**Cost Estimation:**
```python
# Calculate tokens for selected articles
article_tokens = sum([estimate_tokens(article.content) for article in selected])
system_prompt_tokens = estimate_tokens(template.system_prompt)
total_input_tokens = article_tokens + system_prompt_tokens
estimated_output_tokens = template.max_tokens

# Calculate cost based on model pricing
cost = (total_input_tokens / 1M * input_price) + (estimated_output_tokens / 1M * output_price)
```

#### 5.3 Generation Queue

**Purpose:** Manage async report generation jobs

**Access Methods:**
- **REST API:** `/api/v2/special-reports/generations`
- **Database:** `pending_content_generation` table
- **Worker:** `content_generator_worker.py`

**Queue Features:**
- ✅ Async job processing (non-blocking)
- ✅ Status tracking (pending, processing, completed, failed)
- ✅ Progress reporting (percentage complete)
- ✅ Error handling with retry logic
- ✅ Result storage with metadata

**Generation Statuses:**
- `pending` - Queued, not started
- `processing` - LLM call in progress
- `completed` - Successfully generated
- `failed` - Error occurred (see error log)

### Use Cases

**Daily Executive Summary:**
```json
{
  "name": "C-Suite Daily Brief",
  "selection_criteria": {
    "timeframe": "last_24h",
    "impact_min": 0.7,
    "max_articles": 30
  },
  "llm_config": {
    "model": "gpt-4o",
    "system_prompt": "Create an executive summary highlighting key business developments, risks, and opportunities. Focus on actionable insights."
  }
}
```

**Weekly Industry Report:**
```json
{
  "name": "FinTech Weekly Roundup",
  "selection_criteria": {
    "timeframe": "last_7d",
    "feeds": [15, 23, 31],  // FinTech-focused feeds
    "keywords": ["fintech", "blockchain", "payments"],
    "max_articles": 50
  },
  "llm_config": {
    "model": "gpt-5-mini",
    "system_prompt": "Generate comprehensive weekly report on FinTech trends, regulations, and innovations."
  }
}
```

### Related Features
- **Content Query Builder** - Builds article selection SQL
- **Pending Content Generation** - Queue management
- **Analysis Results** - Provides impact/sentiment data for filtering

---

## 6. Monitoring & Health

### Overview
Comprehensive system health monitoring including feed health tracking, performance metrics, Prometheus integration, and diagnostic tools.

### Core Capabilities

#### 6.1 System Health Dashboard

**Purpose:** Real-time overview of system status and metrics

**Access Methods:**
- **MCP Tool:** `system_health`, `get_dashboard`
- **REST API:** `/health/*`, `/api/metrics/*`
- **Web UI:** `/admin/statistics` (Statistics Dashboard)

**Monitored Components:**
- **Database:** Connection status, query performance, table sizes
- **Scheduler:** Active jobs, queue depth, heartbeat
- **Disk Space:** Available storage, growth rate
- **Memory:** Usage percentage, swap status
- **API:** Response times, error rates

**Dashboard Metrics:**
- Total feeds (active/paused/error)
- Total articles stored
- Articles analyzed percentage
- Analysis runs (today/this week)
- Feed health summary (ok/warn/fail counts)
- Hourly activity graphs (24h)
- Storage statistics

**Example Usage (MCP):**
```python
# Get comprehensive dashboard
dashboard = get_dashboard()

# Check system health
health = system_health()
# Returns: {
#   "database": "healthy",
#   "scheduler": "running",
#   "disk_space": "82% used",
#   "memory": "45% used",
#   "api_status": "responsive"
# }
```

#### 6.2 Feed Health Tracking

**Purpose:** Monitor individual feed reliability and performance

**Access Methods:**
- **MCP Tools:** `feeds_health`, `feed_diagnostics`, `feed_performance`
- **REST API:** `/feeds/health/*`
- **Database:** `feed_health` table

**Metrics per Feed:**
- **Success Rate:** Percentage of successful fetches (7d, 30d)
- **Response Time:** Average HTTP response time (ms)
- **Uptime:** Percentage of time feed is reachable
- **Consecutive Failures:** Current failure streak
- **Last Success/Failure:** Timestamps and error details
- **Items per Fetch:** Average article count per update
- **Error Patterns:** Common error types and frequencies

**Health Calculation:**
```python
def calculate_health_status(feed):
    success_rate_7d = feed.successful_fetches / feed.total_fetches_7d
    avg_response_time = feed.avg_response_time_ms
    consecutive_failures = feed.consecutive_failure_count

    if success_rate_7d > 0.95 and avg_response_time < 2000 and consecutive_failures == 0:
        return "OK"
    elif success_rate_7d > 0.80 and avg_response_time < 5000 and consecutive_failures < 3:
        return "WARN"
    else:
        return "FAIL"
```

**Example Usage (MCP):**
```python
# Get health for all feeds
all_health = feeds_health()

# Diagnose specific problematic feed
diagnostics = feed_diagnostics(feed_id=8)
# Returns:
# {
#   "feed_id": 8,
#   "status": "FAIL",
#   "consecutive_failures": 5,
#   "last_error": "Connection timeout after 30s",
#   "success_rate_7d": 0.42,
#   "avg_response_time": 8500,
#   "suggested_action": "Check feed URL or increase timeout"
# }

# Analyze performance over time
perf = feed_performance(feed_id=12, days=30)
```

#### 6.3 Prometheus Metrics

**Purpose:** Export system metrics for Grafana/Prometheus monitoring

**Access Methods:**
- **REST API:** `/api/metrics/prometheus`
- **Service:** `PrometheusMetrics`

**Exported Metrics:**

**Analysis Metrics:**
- `news_mcp_analysis_runs_total{status}` (counter)
- `news_mcp_analysis_items_processed{model}` (counter)
- `news_mcp_analysis_duration_seconds` (histogram)
- `news_mcp_analysis_cost_usd{model}` (counter)

**Feed Metrics:**
- `news_mcp_feed_fetch_total{feed_id,status}` (counter)
- `news_mcp_feed_fetch_duration_seconds{feed_id}` (histogram)
- `news_mcp_feed_items_discovered{feed_id}` (counter)
- `news_mcp_feed_health_score{feed_id}` (gauge)

**Queue Metrics:**
- `news_mcp_queue_depth{queue_type}` (gauge)
- `news_mcp_queue_processing_rate` (gauge)
- `news_mcp_queue_wait_time_seconds` (histogram)

**System Metrics:**
- `news_mcp_database_size_bytes` (gauge)
- `news_mcp_api_requests_total{endpoint,status}` (counter)
- `news_mcp_api_duration_seconds{endpoint}` (histogram)

**Example Prometheus Query:**
```promql
# Average analysis cost per model (last 24h)
sum by (model) (rate(news_mcp_analysis_cost_usd[24h]))

# Feed health distribution
count by (status) (news_mcp_feed_health_score)

# Queue depth over time
news_mcp_queue_depth{queue_type="analysis"}
```

#### 6.4 Error Analysis

**Purpose:** Identify error patterns and provide solutions

**Access Methods:**
- **MCP Tool:** `error_analysis`
- **REST API:** `/api/analysis/errors`

**Features:**
- ✅ Recent error aggregation
- ✅ Error pattern detection
- ✅ Affected feeds identification
- ✅ Suggested fixes
- ✅ Error frequency trends

**Example Usage (MCP):**
```python
# Analyze errors from last 48 hours
error_analysis(hours=48)

# Errors for specific feed
error_analysis(hours=24, feed_id=5)
```

#### 6.5 Log Analysis

**Purpose:** Analyze system logs for patterns and issues

**Access Methods:**
- **MCP Tool:** `log_analysis`
- **REST API:** `/api/logs/analyze`

**Features:**
- Filter by log level (ERROR, WARNING, INFO)
- Filter by component (scheduler, fetcher, api, templates)
- Time range selection
- Pattern detection
- Frequency analysis

**Example Usage (MCP):**
```python
# Analyze ERROR logs from scheduler (last 24h)
log_analysis(
    hours=24,
    log_level="ERROR",
    component="scheduler"
)
```

### Related Features
- **Feed Scheduler** - Generates fetch logs and health data
- **Feed Health Service** - Calculates health metrics
- **Metrics Service** - Collects and aggregates metrics

---

## 7. Database Operations

### Overview
Direct database access tools for advanced data exploration, reporting, and administration with safety controls.

### Core Capabilities

#### 7.1 Safe SQL Execution

**Purpose:** Execute read-only SQL queries for custom data analysis

**Access Methods:**
- **MCP Tool:** `execute_query`
- **REST API:** `/api/database/query`
- **Web UI:** `/admin/database` (Query executor)

**Safety Features:**
- ✅ Read-only enforcement (SELECT only)
- ✅ Whitelist-based table access
- ✅ SQL injection prevention
- ✅ Query complexity limits (no recursive CTEs, etc.)
- ✅ Result size limits (default 100, max 1000 rows)
- ✅ Timeout protection (30s query timeout)

**Allowed Operations:**
- `SELECT` queries
- `JOIN` operations
- `GROUP BY`, `ORDER BY`, `LIMIT`
- Aggregate functions (COUNT, SUM, AVG, etc.)
- Window functions
- CTEs (non-recursive only)

**Blocked Operations:**
- `INSERT`, `UPDATE`, `DELETE`
- `DROP`, `TRUNCATE`, `ALTER`
- `CREATE` (tables, indexes, etc.)
- Recursive CTEs
- Functions modifying data

**Example Usage (MCP):**
```python
# Count articles by feed (last 7 days)
execute_query(
    query="""
        SELECT feed_id, COUNT(*) as article_count
        FROM items
        WHERE created_at > NOW() - INTERVAL '7 days'
        GROUP BY feed_id
        ORDER BY article_count DESC
    """,
    limit=100
)

# Get high-impact analyzed articles
execute_query(
    query="""
        SELECT i.title, ia.impact_score, ia.sentiment_label
        FROM items i
        JOIN item_analysis ia ON i.id = ia.item_id
        WHERE ia.impact_score > 0.7
        ORDER BY ia.impact_score DESC
    """,
    limit=50
)
```

#### 7.2 Schema Exploration

**Purpose:** Inspect database structure and table definitions

**Access Methods:**
- **MCP Tool:** `table_info`
- **REST API:** `/api/database/schema`
- **Web UI:** `/admin/database` (Schema browser)

**Features:**
- ✅ List all accessible tables
- ✅ View column definitions (name, type, nullable, default)
- ✅ Inspect indexes and constraints
- ✅ See foreign key relationships
- ✅ Optional sample data preview

**Available Tables (35 total):**

**Core Tables:**
- `feeds` - RSS feed configurations
- `items` - News articles
- `sources` - News sources
- `categories` - Content categories
- `feed_categories` - Feed-category relationships

**Analysis Tables:**
- `item_analysis` - AI analysis results
- `analysis_runs` - Analysis job tracking
- `analysis_run_items` - Run item details
- `pending_auto_analysis` - Auto-analysis queue

**Health & Monitoring:**
- `feed_health` - Feed health metrics
- `fetch_log` - Feed fetch history
- `content_processing_logs` - Processing logs

**Templates & Processing:**
- `dynamic_feed_templates` - Content extraction templates
- `feed_template_assignments` - Template-feed mappings
- `feed_configuration_changes` - Change tracking

**Special Reports:**
- `special_reports` - Report templates
- `generated_content` - Generated reports
- `pending_content_generation` - Generation queue

**Example Usage (MCP):**
```python
# List all tables
table_info()

# Get schema for items table
table_info(table_name="items")

# Get schema with sample data
table_info(table_name="item_analysis", include_sample_data=True)
```

#### 7.3 Quick Queries

**Purpose:** Execute predefined useful queries safely

**Access Methods:**
- **MCP Tool:** `quick_queries`
- **REST API:** `/api/database/quick-query`
- **Web UI:** Quick query dropdown in database page

**Available Quick Queries:**

**`feed_overview`:**
```sql
SELECT
    f.id, f.title, f.status, f.fetch_interval_minutes,
    COUNT(i.id) as total_items,
    COUNT(ia.id) as analyzed_items,
    fh.success_rate_7d,
    fh.avg_response_time_ms
FROM feeds f
LEFT JOIN items i ON f.id = i.feed_id
LEFT JOIN item_analysis ia ON i.id = ia.item_id
LEFT JOIN feed_health fh ON f.id = fh.feed_id
GROUP BY f.id, fh.success_rate_7d, fh.avg_response_time_ms
ORDER BY total_items DESC
```

**`recent_activity`:**
```sql
SELECT
    DATE_TRUNC('hour', created_at) as hour,
    COUNT(*) as articles_added
FROM items
WHERE created_at > NOW() - INTERVAL '24 hours'
GROUP BY hour
ORDER BY hour DESC
```

**`error_analysis`:**
```sql
SELECT
    feed_id,
    error_type,
    COUNT(*) as error_count,
    MAX(occurred_at) as last_occurrence
FROM fetch_log
WHERE status = 'error' AND occurred_at > NOW() - INTERVAL '7 days'
GROUP BY feed_id, error_type
ORDER BY error_count DESC
```

**`performance_stats`:**
```sql
SELECT
    f.title,
    AVG(fl.duration_ms) as avg_fetch_time,
    AVG(fl.items_count) as avg_items_per_fetch,
    SUM(CASE WHEN fl.status = 'success' THEN 1 ELSE 0 END)::float / COUNT(*) as success_rate
FROM feeds f
JOIN fetch_log fl ON f.id = fl.feed_id
WHERE fl.occurred_at > NOW() - INTERVAL '30 days'
GROUP BY f.id, f.title
ORDER BY success_rate ASC
```

**`template_usage`:**
```sql
SELECT
    dft.name as template_name,
    COUNT(fta.feed_id) as assigned_feeds,
    AVG(cpl.processing_time_ms) as avg_processing_time
FROM dynamic_feed_templates dft
LEFT JOIN feed_template_assignments fta ON dft.id = fta.template_id
LEFT JOIN content_processing_logs cpl ON fta.template_id = cpl.template_id
GROUP BY dft.id, dft.name
ORDER BY assigned_feeds DESC
```

**Example Usage (MCP):**
```python
# Get feed overview
quick_queries(query_name="feed_overview")

# Analyze recent errors
quick_queries(query_name="error_analysis")

# Check feed performance
quick_queries(query_name="performance_stats")
```

### Security Considerations

**Whitelist-based Access:**
Only these tables are accessible via query tools:
- All tables listed in section 7.2 above
- System tables like `pg_stat_user_tables` (read-only metadata)

**Blocked Tables:**
- `alembic_version` (migration metadata)
- `user_credentials` (if exists)
- Any tables with `_internal` suffix

**Query Validation:**
```python
def validate_query(sql: str) -> bool:
    # Block non-SELECT queries
    if not sql.strip().upper().startswith("SELECT"):
        raise ValueError("Only SELECT queries allowed")

    # Block table modifications
    blocked_keywords = ["INSERT", "UPDATE", "DELETE", "DROP", "TRUNCATE", "ALTER", "CREATE"]
    if any(keyword in sql.upper() for keyword in blocked_keywords):
        raise ValueError("Modification queries not allowed")

    # Check table whitelist
    mentioned_tables = extract_tables(sql)
    if not all(table in ALLOWED_TABLES for table in mentioned_tables):
        raise ValueError("Access to this table is not permitted")

    return True
```

### Related Features
- **Statistics Dashboard** - Uses quick queries
- **Prometheus Metrics** - Queries system tables for metrics

---

## 8. Templates & Processing

### Overview
Customizable content extraction and processing system that controls how articles are parsed from different feed sources using CSS/XPath selectors and transformation rules.

### Core Capabilities

#### 8.1 Dynamic Templates

**Purpose:** Define feed-specific content extraction rules

**Access Methods:**
- **MCP Tools:** `list_templates`, `templates_create`, `templates_test`, `templates_assign`
- **REST API:** `/templates/*`
- **Web UI:** `/admin/templates`

**Template Components:**

**1. Match Rules:**
Define which feeds this template applies to
```json
{
  "match_rules": [
    {
      "type": "domain",
      "pattern": "techcrunch.com",
      "priority": 100
    },
    {
      "type": "url_regex",
      "pattern": "https://.*\\.reuters\\.com/.*",
      "priority": 90
    }
  ]
}
```

**2. Extraction Config:**
CSS/XPath selectors for content extraction
```json
{
  "extraction_config": {
    "title": {
      "selector": "h1.article-title",
      "type": "css",
      "required": true
    },
    "content": {
      "selector": "//article//div[@class='content']",
      "type": "xpath",
      "required": true
    },
    "author": {
      "selector": "span.author-name",
      "type": "css",
      "required": false
    },
    "published_date": {
      "selector": "time[datetime]",
      "attribute": "datetime",
      "type": "css"
    }
  }
}
```

**3. Processing Rules:**
Content transformations and validation
```json
{
  "processing_rules": {
    "min_content_length": 100,
    "max_content_length": 50000,
    "strip_html": true,
    "remove_patterns": ["Advertisement", "Subscribe Now"],
    "normalize_whitespace": true,
    "extract_links": false
  }
}
```

**Example Usage (MCP):**
```python
# Create new template for TechCrunch
templates_create(
    name="TechCrunch Extractor",
    description="Custom extraction for TechCrunch articles",
    match_rules=[{
        "type": "domain",
        "pattern": "techcrunch.com"
    }],
    extraction_config={
        "title": {"selector": "h1.article-title", "type": "css"},
        "content": {"selector": "div.article-content", "type": "css"}
    },
    processing_rules={
        "min_content_length": 200,
        "strip_html": True
    }
)

# Test template against sample URL
templates_test(
    template_id=5,
    sample_url="https://techcrunch.com/2025/10/05/sample-article/"
)

# Assign template to feed
templates_assign(
    template_id=5,
    feed_id=12,
    priority=200
)
```

#### 8.2 Processor Types

**Purpose:** Different content processing strategies for various feed formats

**Access Methods:**
- **REST API:** `/processors/*`
- **Web UI:** `/admin/processors`

**Available Processors:**

**Universal Processor (Default):**
- Standard RSS/Atom parsing
- Fallback for unmatched feeds
- Generic content extraction
- Basic cleaning and normalization

**RSS Processor:**
- Optimized for RSS 2.0 format
- Channel metadata extraction
- Item-level field mapping
- Media enclosure handling

**Atom Processor:**
- Atom 1.0 format support
- Namespace handling
- Author and category parsing
- Link relation support

**Custom Domain Processors:**
- Site-specific extraction logic
- Advanced parsing for non-standard feeds
- JavaScript rendering support (if needed)
- API-based content fetching

**Processor Selection Logic:**
```python
def select_processor(feed):
    # 1. Check if feed has template assignment
    template = get_assigned_template(feed.id)
    if template and template.processor_override:
        return template.processor_override

    # 2. Check feed content type
    if feed.content_type == "application/rss+xml":
        return RSSProcessor
    elif feed.content_type == "application/atom+xml":
        return AtomProcessor

    # 3. Check domain-specific processors
    domain_processor = match_domain_processor(feed.url)
    if domain_processor:
        return domain_processor

    # 4. Fallback to universal
    return UniversalProcessor
```

#### 8.3 Template Management

**Purpose:** List, update, and analyze template performance

**Access Methods:**
- **MCP Tools:** `list_templates`, `template_performance`
- **REST API:** `/templates/*`
- **Web UI:** `/admin/templates`

**Template Listing:**
```python
# List all active templates with assignments
list_templates(
    active_only=True,
    include_assignments=True
)

# Returns:
# [
#   {
#     "id": 5,
#     "name": "TechCrunch Extractor",
#     "active": true,
#     "assigned_feeds": [12, 18],
#     "created_at": "2025-09-15T10:30:00Z"
#   }
# ]
```

**Performance Analysis:**
```python
# Analyze template performance over 14 days
template_performance(template_id=3, days=14)

# Returns:
# {
#   "template_id": 3,
#   "avg_processing_time_ms": 145,
#   "success_rate": 0.987,
#   "total_items_processed": 2450,
#   "common_errors": [
#     {"error": "Title selector not found", "count": 12}
#   ]
# }
```

#### 8.4 Content Processing Pipeline

**Purpose:** Step-by-step article processing workflow

**Processing Steps:**

**1. Feed Fetch:**
```
Scheduler triggers feed update
→ HTTP request to feed URL
→ Response validation (200 OK, valid content-type)
→ Raw XML/HTML content stored
```

**2. Template Matching:**
```
Extract feed domain/URL
→ Query templates with matching rules
→ Select highest priority matching template
→ If no match, use universal template
```

**3. Content Extraction:**
```
Apply extraction_config selectors
→ Extract title, content, author, date, etc.
→ Validate required fields present
→ Apply attribute extraction (e.g., href, datetime)
```

**4. Processing Rules Application:**
```
Validate content length (min/max)
→ Strip HTML tags if configured
→ Remove advertisement patterns
→ Normalize whitespace
→ Extract embedded links/media
```

**5. Deduplication:**
```
Calculate content hash (SHA-256)
→ Check against existing items
→ Skip if duplicate found
→ Otherwise, proceed to save
```

**6. Database Persistence:**
```
Create item record in database
→ Link to feed_id
→ Store processing metadata
→ Trigger auto-analysis if enabled
→ Log processing result
```

**7. Logging:**
```
Create content_processing_logs entry
→ Record template used
→ Track processing time
→ Log any errors/warnings
→ Update feed statistics
```

### Use Cases

**Standard RSS Feed (No Custom Template):**
```
TechCrunch RSS → Universal Processor → Standard extraction
→ Title from <title>, content from <description>
→ Default processing (HTML stripping)
→ Save to database
```

**Custom Domain Template:**
```
Reuters Article → Domain matcher finds "Reuters Template"
→ Custom selectors: h1.article-headline, div.article-body__content
→ Custom processing: Remove "Register to continue" text
→ Enhanced metadata extraction
→ Save with template_id reference
```

**Failed Extraction:**
```
Feed updated → Template applied → Selector not found
→ Log error: "Title selector 'h1.title' returned no results"
→ Fallback to default RSS fields
→ Item saved with warning flag
→ Template performance degraded in metrics
```

### Related Features
- **Feed Management** - Templates assigned to feeds
- **Configuration Watcher** - Reloads templates on changes
- **Feed Change Tracker** - Tracks template modifications

---

## 9. Categories & Sources

### Overview
Hierarchical organization system for feeds and articles using categories and news sources with metadata tracking.

### Core Capabilities

#### 9.1 Category Management

**Purpose:** Organize feeds and articles by topic/theme

**Access Methods:**
- **MCP Tools:** `categories_list`, `categories_add`, `categories_update`, `categories_delete`, `categories_assign`
- **REST API:** `/categories/*`
- **Web UI:** Category selectors in feed forms

**Category Features:**
- ✅ Create custom categories
- ✅ Multi-category assignment (one feed → many categories)
- ✅ Category metadata (name, description, color)
- ✅ Category statistics (feed count, item count)
- ✅ Hierarchical organization (parent-child relationships)

**Example Categories:**
- Technology
- Politics
- Business
- Science
- Health
- Sports
- Entertainment
- Finance
- Security
- Environment

**Example Usage (MCP):**
```python
# List all categories with stats
categories_list(
    include_feeds=True,
    include_stats=True
)

# Create new category
categories_add(
    name="Cybersecurity",
    description="Security news and cyber threats",
    color="#FF5733"
)

# Update category
categories_update(
    category_id=3,
    name="Web3 & Blockchain",
    color="#00FF00"
)

# Assign feed to categories
categories_assign(
    feed_id=12,
    category_ids=[1, 3, 7]  # Technology, Cybersecurity, Finance
)

# Delete category
categories_delete(category_id=5)
```

#### 9.2 Source Management

**Purpose:** Track news publishers and their trust levels

**Access Methods:**
- **MCP Tools:** `sources_list`, `sources_add`, `sources_update`, `sources_delete`, `sources_stats`
- **REST API:** `/sources/*`

**Source Attributes:**
- **Name:** Publisher name (e.g., "Reuters", "TechCrunch")
- **URL:** Homepage URL
- **Trust Level:** 1-5 rating (1=unverified, 5=highly trusted)
- **Source Type:** RSS, API, Manual
- **Country:** Publisher country code
- **Language:** Primary language
- **Political Bias:** Left/Center/Right classification
- **Fact Check Rating:** Third-party verification score

**Source Statistics:**
- Total feeds from this source
- Total articles published
- Average sentiment score
- Update frequency
- Content quality metrics

**Example Usage (MCP):**
```python
# List all sources
sources_list()

# Add high-trust source
sources_add(
    name="Reuters",
    url="https://reuters.com",
    trust_level=5,
    country="UK",
    language="en",
    political_bias="center"
)

# Update source metadata
sources_update(
    source_id=8,
    trust_level=4,
    fact_check_rating=4.5
)

# Get source statistics
sources_stats(source_id=8)

# Delete source
sources_delete(source_id=10)
```

### Use Cases

**Categorized Feed Discovery:**
```python
# Find all technology feeds
feeds = feeds_search(category="Technology")

# Find all high-trust politics feeds
feeds = feeds_search(
    category="Politics",
    min_trust_level=4
)
```

**Content Filtering by Category:**
```python
# Get latest tech articles
latest_articles(category="Technology", limit=50)

# Research pipeline with category filter
research_filter_articles(
    timeframe="last_7d",
    categories=["Politics", "Security"]
)
```

**Source-Based Analysis:**
```python
# Compare sentiment across sources
SELECT
    s.name,
    AVG(ia.sentiment_score) as avg_sentiment
FROM sources s
JOIN feeds f ON s.id = f.source_id
JOIN items i ON f.id = i.feed_id
JOIN item_analysis ia ON i.id = ia.item_id
GROUP BY s.name
```

### Related Features
- **Feed Management** - Uses categories and sources
- **Article Search** - Filter by category
- **Research Pipeline** - Category-based article filtering

---

## 10. Scheduler & Workers

### Overview
Background processing infrastructure for automated feed fetching, analysis execution, and content generation using async workers and queue management.

### Core Capabilities

#### 10.1 Feed Scheduler

**Purpose:** Automated periodic feed fetching with dynamic intervals

**Access Methods:**
- **MCP Tools:** `scheduler_status`, `scheduler_set_interval`, `scheduler_heartbeat`
- **REST API:** `/scheduler/*`
- **Service:** `scheduler_runner.py`
- **Script:** `./scripts/start-scheduler.sh`

**Scheduler Features:**
- ✅ Dynamic per-feed intervals (5-1440 minutes)
- ✅ Global interval override option
- ✅ Concurrent fetch limit (default 10)
- ✅ Automatic error handling with backoff
- ✅ Stale operation detection (kills stuck fetches)
- ✅ Pause/resume all feeds or specific feed
- ✅ Heartbeat monitoring

**Scheduling Logic:**
```python
def schedule_next_fetch(feed):
    if feed.status != "ACTIVE":
        return  # Skip paused/error feeds

    if feed.consecutive_failures >= 5:
        # Exponential backoff for failing feeds
        interval = feed.fetch_interval_minutes * (2 ** min(feed.consecutive_failures - 5, 3))
    else:
        interval = feed.fetch_interval_minutes

    next_fetch = datetime.utcnow() + timedelta(minutes=interval)
    schedule_job(feed_id=feed.id, run_at=next_fetch)
```

**Example Usage (MCP):**
```python
# Get scheduler status
scheduler_status(action="status")

# Set global fetch interval to 30 minutes
scheduler_set_interval(minutes=30)

# Set interval for specific feed
scheduler_set_interval(minutes=5, feed_id=12)

# Get detailed heartbeat
scheduler_heartbeat()
# Returns:
# {
#   "status": "running",
#   "last_heartbeat": "2025-10-05T14:32:15Z",
#   "active_jobs": 3,
#   "queue_depth": 12,
#   "next_scheduled": [
#     {"feed_id": 5, "scheduled_at": "2025-10-05T14:35:00Z"},
#     {"feed_id": 12, "scheduled_at": "2025-10-05T14:38:00Z"}
#   ]
# }
```

#### 10.2 Analysis Worker

**Purpose:** Process analysis run queue asynchronously

**Access Methods:**
- **Service:** `analysis_worker.py`
- **Script:** `./scripts/start-worker.sh`
- **Queue:** `analysis_runs` table (status: queued)

**Worker Responsibilities:**
1. **Poll Queue:**
   ```python
   while True:
       pending_runs = get_pending_runs(limit=5)
       for run in pending_runs:
           process_analysis_run(run)
       sleep(30)  # Check every 30 seconds
   ```

2. **Execute Analysis:**
   ```python
   def process_analysis_run(run):
       # Update status to "running"
       run.status = "running"
       run.started_at = datetime.utcnow()

       # Fetch articles for analysis
       articles = fetch_articles(run.selector)

       # Call LLM for each article
       for article in articles:
           analysis = call_llm(article.content, model=run.model)
           save_analysis(article_id=article.id, analysis=analysis)
           run.processed_count += 1

       # Update run status
       run.status = "completed"
       run.completed_at = datetime.utcnow()
   ```

3. **Handle Failures:**
   ```python
   try:
       process_analysis_run(run)
   except LLMAPIError as e:
       if run.retry_count < 3:
           run.retry_count += 1
           run.status = "queued"  # Retry later
       else:
           run.status = "failed"
           run.error_message = str(e)
   ```

**Worker Configuration:**
- **Concurrency:** Process up to 2 runs simultaneously
- **Retry Logic:** Up to 3 retries with exponential backoff
- **Timeout:** 30 minutes per run (kills long-running jobs)
- **Rate Limiting:** Respects LLM API rate limits

#### 10.3 Auto-Analysis Service

**Purpose:** Automatically queue analysis for new items from designated feeds

**Access Methods:**
- **Service:** `AutoAnalysisService`, `PendingAnalysisProcessor`
- **Database:** `pending_auto_analysis` table

**Auto-Analysis Workflow:**

**1. Item Creation Trigger:**
```python
def on_item_created(item):
    feed = get_feed(item.feed_id)
    if feed.auto_analyze_enabled:
        queue_for_auto_analysis(item.id, feed.id)
```

**2. Pending Queue Management:**
```python
# pending_auto_analysis table
{
  "id": 1234,
  "feed_id": 5,
  "item_ids": [10001, 10002, 10003],  # Batch items
  "status": "pending",
  "created_at": "2025-10-05T14:00:00Z",
  "processed_at": null,
  "analysis_run_id": null
}
```

**3. Batch Processing:**
```python
def process_pending_auto_analysis():
    # Group items by feed for efficient processing
    pending_batches = get_pending_batches()

    for batch in pending_batches:
        # Check daily limits
        if feed_exceeds_auto_limits(batch.feed_id):
            continue  # Skip, will retry tomorrow

        # Create analysis run
        run = create_analysis_run(
            selector={"items": batch.item_ids},
            model="gpt-5-nano",  # Auto-analysis uses cheapest model
            triggered_by="auto-analysis"
        )

        # Link to pending batch
        batch.analysis_run_id = run.id
        batch.status = "processing"
```

**4. Completion:**
```python
def on_analysis_run_completed(run):
    # Update pending batch
    batch = get_batch_by_run_id(run.id)
    batch.status = "completed"
    batch.processed_at = datetime.utcnow()
```

**Auto-Analysis Limits:**
- **Daily limit:** 3 auto-runs per feed (configurable)
- **Batch size:** Max 200 items per run
- **Model:** Defaults to `gpt-5-nano` (cost-effective)
- **Deduplication:** Skips already-analyzed items

#### 10.4 Content Generator Worker

**Purpose:** Process special report generation queue

**Access Methods:**
- **Service:** `content_generator_worker.py`
- **Queue:** `pending_content_generation` table

**Generation Process:**

**1. Poll Queue:**
```python
while True:
    pending = get_pending_generations(limit=3)
    for gen in pending:
        process_generation(gen)
    sleep(60)
```

**2. Execute Generation:**
```python
def process_generation(gen):
    # Fetch report template
    template = get_special_report(gen.report_id)

    # Select articles based on criteria
    articles = filter_articles(template.selection_criteria)

    # Build LLM prompt
    prompt = build_report_prompt(template, articles)

    # Call LLM
    report = call_llm(
        prompt=prompt,
        model=template.llm_config.model,
        max_tokens=template.llm_config.max_tokens
    )

    # Save generated content
    save_generated_content(
        report_id=gen.report_id,
        content=report,
        metadata={
            "articles_used": len(articles),
            "model": template.llm_config.model,
            "cost": calculate_cost(prompt, report)
        }
    )

    gen.status = "completed"
```

**3. Error Handling:**
```python
try:
    process_generation(gen)
except Exception as e:
    gen.status = "failed"
    gen.error_message = str(e)
    notify_admin(gen)
```

### Scheduler Configuration

**Global Settings:**
```python
# config/scheduler.json
{
  "default_fetch_interval_minutes": 15,
  "max_concurrent_fetches": 10,
  "stale_operation_timeout_seconds": 300,
  "heartbeat_interval_seconds": 60,
  "error_threshold_for_pause": 5,
  "backoff_multiplier": 2
}
```

**Per-Feed Overrides:**
```python
# Feed table
{
  "id": 12,
  "fetch_interval_minutes": 5,  # Override for breaking news feed
  "status": "ACTIVE"
}
```

### Monitoring Scheduler

**Health Checks:**
```python
# Check if scheduler is alive
GET /scheduler/heartbeat

# Response:
{
  "status": "running",
  "last_heartbeat": "2025-10-05T14:32:15Z",
  "uptime_seconds": 86400
}
```

**View Scheduled Jobs:**
```python
GET /scheduler/status

# Response:
{
  "active_jobs": 3,
  "queue_depth": 12,
  "next_scheduled": [...]
}
```

### Related Features
- **Feed Health Service** - Monitors scheduler activity
- **Run Queue Manager** - Manages analysis scheduling
- **Backpressure System** - Enforces concurrency limits

---

## 11. Auto-Analysis System

### Overview
Automated background analysis that monitors designated feeds and queues new articles for AI analysis without manual intervention.

### Core Capabilities

#### 11.1 Per-Feed Auto-Analysis Configuration

**Purpose:** Enable automatic analysis for specific feeds

**Access Methods:**
- **REST API:** Feed update endpoint with `auto_analyze_enabled` flag
- **Web UI:** Toggle in feed edit form
- **Database:** `feeds.auto_analyze_enabled` column

**Configuration:**
```python
# Enable auto-analysis for feed
update_feed(
    feed_id=12,
    auto_analyze_enabled=True
)

# Feed record:
{
  "id": 12,
  "title": "TechCrunch",
  "auto_analyze_enabled": True,
  "created_at": "2025-09-15T10:00:00Z"
}
```

#### 11.2 Auto-Analysis Queue

**Purpose:** Track pending auto-analysis jobs

**Access Methods:**
- **Database:** `pending_auto_analysis` table
- **Service:** `PendingAnalysisProcessor`

**Queue Record Structure:**
```python
{
  "id": 1234,
  "feed_id": 5,
  "item_ids": [10001, 10002, 10003],  # Batched items
  "status": "pending",  # pending, processing, completed, failed
  "created_at": "2025-10-05T14:00:00Z",
  "processed_at": null,
  "analysis_run_id": null,  # Linked run when processing
  "error_message": null
}
```

**Queue Status Values:**
- `pending` - Queued, awaiting processing
- `processing` - Analysis run in progress
- `completed` - Successfully analyzed
- `failed` - Error occurred during analysis

#### 11.3 Processing Workflow

**Step 1: Item Creation Trigger**
```python
# When new item saved from feed fetch
def on_item_created(item):
    feed = get_feed(item.feed_id)

    # Check if auto-analysis enabled for this feed
    if not feed.auto_analyze_enabled:
        return

    # Check if item already analyzed
    if has_analysis(item.id):
        return  # Skip duplicates

    # Add to pending queue (or update existing batch)
    add_to_pending_queue(
        feed_id=feed.id,
        item_id=item.id
    )
```

**Step 2: Batch Aggregation**
```python
# Pending processor groups items for efficiency
def batch_pending_items():
    # Get items from last 5 minutes
    recent_items = get_recent_pending_items(minutes=5)

    # Group by feed
    batches = {}
    for item in recent_items:
        if item.feed_id not in batches:
            batches[item.feed_id] = []
        batches[item.feed_id].append(item.id)

    # Create batch records
    for feed_id, item_ids in batches.items():
        create_pending_batch(
            feed_id=feed_id,
            item_ids=item_ids
        )
```

**Step 3: Analysis Run Creation**
```python
# Pending processor creates analysis runs
def process_pending_batches():
    batches = get_pending_batches()

    for batch in batches:
        # Check daily limits
        if feed_exceeds_auto_limits(batch.feed_id):
            # Wait for tomorrow, keep status as pending
            continue

        # Create analysis run
        run = create_analysis_run(
            selector={"items": batch.item_ids},
            model="gpt-5-nano",  # Auto uses cheapest
            triggered_by="auto-analysis",
            tags=["auto"]
        )

        # Update batch
        batch.analysis_run_id = run.id
        batch.status = "processing"
        save(batch)
```

**Step 4: Execution by Analysis Worker**
```python
# Analysis worker picks up run
# (See section 10.2 Analysis Worker)

# When run completes:
def on_run_completed(run):
    # Find associated batch
    batch = get_batch_by_run_id(run.id)

    if run.status == "completed":
        batch.status = "completed"
        batch.processed_at = datetime.utcnow()
    else:
        batch.status = "failed"
        batch.error_message = run.error_message

    save(batch)
```

#### 11.4 Limits and Safeguards

**Daily Run Limits:**
```python
# config/auto_analysis_config.json
{
  "max_runs_per_day": 100,        # System-wide daily limit
  "max_items_per_run": 200,       # Items per batch
  "ai_model": "gpt-5-nano",       # Default model
  "check_interval": 30,           # Processor check frequency (seconds)
  "rate_per_second": 2.5          # LLM API rate limit
}
```

**Per-Feed Limits:**
- Auto-analysis runs count against feed's daily quota
- Respects global analysis limits (5 runs/day total)
- Auto runs are subset of total (e.g., 3 auto + 2 manual = 5 total)

**Cost Protection:**
```python
def should_process_batch(batch):
    # Check daily cost accumulation
    daily_cost = get_daily_auto_analysis_cost()
    if daily_cost > MAX_DAILY_COST:
        return False

    # Estimate batch cost
    estimated_cost = estimate_analysis_cost(
        item_count=len(batch.item_ids),
        model="gpt-5-nano"
    )

    if daily_cost + estimated_cost > MAX_DAILY_COST:
        return False

    return True
```

**Deduplication:**
```python
def add_to_pending_queue(feed_id, item_id):
    # Check if already analyzed
    if item_has_analysis(item_id):
        return

    # Check if already in queue
    if item_in_pending_queue(item_id):
        return

    # Check if in active run
    if item_in_active_run(item_id):
        return

    # Safe to add
    create_pending_entry(feed_id, item_id)
```

#### 11.5 Monitoring Auto-Analysis

**Queue Statistics:**
```python
# Get queue stats
GET /api/auto-analysis/stats

# Response:
{
  "pending_batches": 5,
  "processing_batches": 2,
  "completed_today": 12,
  "failed_today": 1,
  "items_queued": 234,
  "items_processed_today": 1450,
  "estimated_daily_cost": 0.12
}
```

**Per-Feed Status:**
```python
# Get auto-analysis status for feed
GET /feeds/12/auto-analysis-status

# Response:
{
  "feed_id": 12,
  "enabled": true,
  "runs_today": 2,
  "items_pending": 45,
  "items_analyzed_today": 89,
  "last_run_at": "2025-10-05T12:30:00Z",
  "next_batch_estimated": "2025-10-05T15:00:00Z"
}
```

### Use Cases

**Enable Auto-Analysis for Breaking News Feed:**
```python
# High-frequency feed with auto-analysis
update_feed(
    feed_id=8,
    title="Reuters Breaking News",
    fetch_interval_minutes=5,      # Fetch every 5 minutes
    auto_analyze_enabled=True      # Auto-analyze new items
)

# Result:
# - Feed fetched every 5 minutes
# - New items batched every 5 minutes
# - Auto-analysis runs 3x/day (respecting limits)
# - Analyzed articles available for filtered search
```

**Monitor Auto-Analysis Costs:**
```python
# Daily cost tracking
SELECT
    DATE(ar.created_at) as date,
    COUNT(*) as auto_runs,
    SUM(ar.estimated_cost) as total_cost
FROM analysis_runs ar
WHERE ar.triggered_by = 'auto-analysis'
    AND ar.created_at > NOW() - INTERVAL '30 days'
GROUP BY DATE(ar.created_at)
ORDER BY date DESC
```

### Related Features
- **Analysis Runs** - Executes the actual analysis
- **Feed Management** - Configure auto-analysis per feed
- **Run Queue Manager** - Enforces limits
- **Idempotency System** - Prevents duplicate analysis

---

## 12. Web UI & Admin Interface

### Overview
Bootstrap 5-based admin interface with HTMX for live updates, providing visual access to all system features without requiring API knowledge.

### Core Capabilities

#### 12.1 Admin Pages

**Base URL:** `http://192.168.178.72:8000/admin/*`

**Available Pages:**

**1. Feed Management (`/admin/feeds`)**
- List all feeds with health indicators
- Add new feeds with URL validation
- Edit feed configuration (interval, status, categories)
- Delete feeds with confirmation
- Toggle auto-analysis per feed
- View feed statistics (total items, analyzed %, health score)
- Manual refresh button

**2. Statistics Dashboard (`/admin/statistics`)**
- System overview cards (total feeds, items, analysis runs)
- Hourly activity graph (last 24 hours)
- Feed performance table (top/bottom performers)
- Category distribution chart
- Health status summary (ok/warn/fail counts)
- Storage statistics (database size, growth rate)

**3. Database Explorer (`/admin/database`)**
- Table browser with schema viewer
- SQL query executor (read-only, safety-validated)
- Quick queries dropdown (predefined useful queries)
- Query result export (CSV)
- Sample data preview
- Table statistics (row count, size)

**4. Analysis Manager (`/admin/analysis-manager`)**
- Start analysis run form
  - Scope selection (items, feeds, smart)
  - Model dropdown (GPT-4o, Claude, etc.)
  - Cost preview before running
- Active runs monitoring
  - Progress bars
  - Cancel/pause buttons
  - Live status updates (HTMX polling)
- Run history table
  - Past runs with status, cost, item count
  - Filter by status, date range
  - Pagination

**5. Processors (`/admin/processors`)**
- Processor type list (Universal, RSS, Atom, Custom)
- Feed-processor assignments
- Template management
  - List templates with assignments
  - Create/edit templates
  - Test templates against sample URLs
- Processing statistics
  - Success rates by processor
  - Average processing times
  - Error patterns

**6. Special Reports (`/admin/special-reports`)**
- Report template list
- Create/edit template form
  - Article selection criteria builder
  - LLM config (model, prompt, max_tokens)
  - Active/inactive toggle
- Test/preview button (dry-run)
- Generate button (triggers async generation)
- Generated reports history
- Download/view generated content

**7. Auto-Analysis System (`/admin/auto-analysis`)**
- System configuration editor
  - Max runs per day
  - Max items per run
  - AI model selection
  - Rate per second
  - Check interval
- Dashboard widget (live stats)
  - Pending jobs count
  - Completed jobs today
  - Items analyzed today
  - Success rate
- Pending queue viewer
- Recent history table

#### 12.2 UI Technologies

**Frontend Stack:**
- **Bootstrap 5.3** - Responsive layout, components
- **Alpine.js** - Reactive UI components (dropdowns, modals)
- **HTMX** - Dynamic content updates without page reload
- **Chart.js** - Data visualizations (graphs, charts)
- **Font Awesome / Bootstrap Icons** - UI icons

**HTMX Features:**
```html
<!-- Auto-refresh dashboard every 30 seconds -->
<div hx-get="/htmx/auto-analysis-dashboard"
     hx-trigger="load, every 30s"
     hx-swap="innerHTML">
    <div class="spinner">Loading...</div>
</div>

<!-- Form submission without page reload -->
<form hx-post="/htmx/auto-analysis-config"
      hx-target="#config-view"
      hx-swap="outerHTML">
    <input type="number" name="max_runs_per_day" value="100">
    <button type="submit">Save</button>
</form>

<!-- Load more items (infinite scroll) -->
<button hx-get="/items?offset=50&limit=20"
        hx-target="#item-list"
        hx-swap="beforeend">
    Load More
</button>
```

**Alpine.js Components:**
```html
<!-- Dropdown with state -->
<div x-data="{ open: false }">
    <button @click="open = !open">Options</button>
    <div x-show="open" @click.away="open = false">
        <a href="#">Edit</a>
        <a href="#">Delete</a>
    </div>
</div>

<!-- Form validation -->
<form x-data="{
    url: '',
    isValid: false,
    validate() { this.isValid = this.url.startsWith('http') }
}">
    <input type="url" x-model="url" @input="validate()">
    <button :disabled="!isValid">Submit</button>
</form>
```

#### 12.3 Layout Structure

**Base Template (`base.html`):**
```html
<!DOCTYPE html>
<html>
<head>
    <title>{% block title %}News-MCP Admin{% endblock %}</title>
    <link href="bootstrap.min.css" rel="stylesheet">
    <script src="htmx.min.js"></script>
    <script src="alpinejs.min.js"></script>
</head>
<body>
    <!-- Navbar (centered, max-width 1320px) -->
    <nav class="navbar">
        <div class="container">
            <a href="/admin/feeds">Feeds</a>
            <a href="/admin/statistics">Statistics</a>
            <a href="/admin/database">Database</a>
            <a href="/admin/analysis-manager">Analysis</a>
            <a href="/admin/processors">Processors</a>
            <a href="/admin/special-reports">Reports</a>
            <a href="/admin/auto-analysis">Auto-Analysis</a>
        </div>
    </nav>

    <!-- Content (full width, 20px padding) -->
    <div class="container-fluid px-5 mt-4">
        {% block content %}{% endblock %}
    </div>
</body>
</html>
```

**Page Template Example:**
```html
{% extends "base.html" %}

{% block title %}Feed Management{% endblock %}

{% block content %}
<div class="d-flex justify-content-between align-items-center mb-4">
    <h1>Feed Management</h1>
    <button class="btn btn-primary" data-bs-toggle="modal" data-bs-target="#addFeedModal">
        Add Feed
    </button>
</div>

<!-- Feed list with HTMX live updates -->
<div id="feed-list"
     hx-get="/htmx/feeds-list"
     hx-trigger="load, every 60s"
     hx-swap="innerHTML">
    <div class="spinner">Loading feeds...</div>
</div>

<!-- Add Feed Modal -->
<div class="modal" id="addFeedModal">
    <form hx-post="/htmx/feeds/add" hx-target="#feed-list">
        <input type="url" name="url" placeholder="RSS URL" required>
        <button type="submit">Add</button>
    </form>
</div>
{% endblock %}
```

#### 12.4 UI Components

**Health Indicator Badge:**
```html
{% if feed.health_status == 'OK' %}
    <span class="badge bg-success">🟢 OK</span>
{% elif feed.health_status == 'WARN' %}
    <span class="badge bg-warning">🟡 WARN</span>
{% else %}
    <span class="badge bg-danger">🔴 FAIL</span>
{% endif %}
```

**Live Activity Graph:**
```html
<canvas id="activityChart"></canvas>
<script>
const ctx = document.getElementById('activityChart').getContext('2d');
new Chart(ctx, {
    type: 'line',
    data: {
        labels: {{ hourly_labels | tojson }},
        datasets: [{
            label: 'Articles Added',
            data: {{ hourly_counts | tojson }},
            borderColor: '#0d6efd',
            tension: 0.1
        }]
    }
});
</script>
```

**Auto-Refresh Stats Card:**
```html
<div class="card"
     hx-get="/htmx/auto-analysis-dashboard"
     hx-trigger="load, every 30s"
     hx-swap="innerHTML">
    <!-- Stats loaded dynamically -->
</div>
```

### Responsive Design

**Mobile-Friendly:**
- Bootstrap grid system (col-xs/sm/md/lg/xl)
- Collapsible navbar on small screens
- Card layouts stack vertically on mobile
- Touch-friendly button sizes

**Desktop-Optimized:**
- Full-width content area (container-fluid)
- Multi-column layouts for data density
- Hover tooltips and dropdowns
- Keyboard navigation support

### Related Features
- **All REST APIs** - Power the UI backend
- **HTMX Views** - Partial HTML endpoints for live updates

---

## Common Workflows

### Workflow 1: Add and Monitor a Feed

**Goal:** Add a new RSS feed and enable automatic analysis

**Steps:**
1. **Test Feed:**
   ```python
   test_feed(url="https://techcrunch.com/feed/", show_items=5)
   ```
   Preview articles to verify feed works

2. **Add Feed:**
   ```python
   add_feed(
       url="https://techcrunch.com/feed/",
       title="TechCrunch",
       fetch_interval_minutes=15,
       auto_assign_template=True
   )
   # Returns: {"feed_id": 12, "status": "ACTIVE"}
   ```

3. **Enable Auto-Analysis:**
   ```python
   update_feed(feed_id=12, auto_analyze_enabled=True)
   ```

4. **Assign to Category:**
   ```python
   categories_assign(feed_id=12, category_ids=[1])  # Technology
   ```

5. **Monitor Health:**
   ```python
   # Wait for first fetch (15 minutes)
   # Then check health
   feed_diagnostics(feed_id=12)
   ```

6. **View Analyzed Articles:**
   ```python
   # After auto-analysis runs
   latest_articles(feed_id=12, limit=20)
   ```

**Result:** Feed is active, fetching every 15 minutes, auto-analyzing new articles, categorized as Technology

---

### Workflow 2: Run Bulk Analysis

**Goal:** Analyze recent unanalyzed articles with cost control

**Steps:**
1. **Preview Analysis:**
   ```python
   preview = analysis_preview(
       model="gpt-5-nano",
       selector={"latest": 100},
       cost_estimate=True
   )
   # Returns:
   # {
   #   "articles_selected": 100,
   #   "estimated_input_tokens": 70000,
   #   "estimated_output_tokens": 15000,
   #   "estimated_cost": 0.0095
   # }
   ```

2. **Adjust Scope if Needed:**
   ```python
   # If cost too high, reduce scope
   preview = analysis_preview(
       model="gpt-5-nano",
       selector={"latest": 50},
       cost_estimate=True
   )
   ```

3. **Start Analysis Run:**
   ```python
   run = analysis_run(
       model="gpt-5-nano",
       selector={"latest": 50},
       persist=True,
       tags=["daily-batch"]
   )
   # Returns: {"run_id": 1234, "status": "queued"}
   ```

4. **Monitor Progress:**
   ```python
   # Check status periodically
   status = get_run_status(run_id=1234)
   # {
   #   "status": "running",
   #   "processed": 25,
   #   "total": 50,
   #   "progress": 0.5
   # }
   ```

5. **View Results:**
   ```python
   # After completion
   latest_articles(
       limit=50,
       min_sentiment=0.5,
       sort_by="sentiment_score"
   )
   ```

**Result:** 50 articles analyzed for ~$0.01, sentiment/impact scores available for filtering

---

### Workflow 3: Generate Special Report

**Goal:** Create automated weekly summary report

**Steps:**
1. **Create Report Template:**
   ```python
   POST /api/v2/special-reports
   {
     "name": "Weekly Tech Summary",
     "target_audience": "Tech executives",
     "selection_criteria": {
       "timeframe": "last_7d",
       "feeds": [5, 12, 18],
       "impact_min": 0.5,
       "max_articles": 50
     },
     "llm_config": {
       "model": "gpt-5-mini",
       "system_prompt": "Generate executive summary highlighting key developments, trends, and opportunities in technology sector.",
       "max_tokens": 1500
     },
     "active": true
   }
   # Returns: {"report_id": 42}
   ```

2. **Test Template:**
   ```python
   POST /api/v2/special-reports/42/test
   # Returns:
   # {
   #   "articles_selected": 47,
   #   "estimated_tokens": 8500,
   #   "estimated_cost": 0.025,
   #   "sample_articles": [...]
   # }
   ```

3. **Trigger Generation:**
   ```python
   POST /api/v2/special-reports/42/generate
   # Returns: {"generation_id": 789, "status": "pending"}
   ```

4. **Monitor Generation:**
   ```python
   GET /api/v2/special-reports/generations/789
   # {
   #   "status": "processing",
   #   "progress": 0.6
   # }
   ```

5. **Retrieve Report:**
   ```python
   GET /api/v2/special-reports/generations/789
   # {
   #   "status": "completed",
   #   "content": "### Weekly Tech Summary\n\n...",
   #   "metadata": {
   #     "articles_used": 47,
   #     "cost": 0.023
   #   }
   # }
   ```

**Result:** Automated weekly report generated, ready for distribution

---

### Workflow 4: Research Pipeline

**Goal:** Research geopolitical developments with citations

**Steps:**
1. **Filter Articles:**
   ```python
   articles = research_filter_articles(
       timeframe="last_30d",
       categories=["geopolitics_security"],
       actors=["Trump", "Xi Jinping"],
       impact_min=0.7,
       max_articles=20,
       order_by="impact_desc"
   )
   # Returns: 20 high-impact geopolitical articles
   ```

2. **Generate Research Queries:**
   ```python
   queries = research_generate_queries(
       filter_config={
           "timeframe": "last_30d",
           "categories": ["geopolitics_security"],
           "impact_min": 0.7
       },
       prompt="Generate research questions analyzing geopolitical implications and security concerns",
       model="gpt-4o-mini"
   )
   # Returns:
   # {
   #   "queries": [
   #     "What are the implications of recent US-China trade tensions?",
   #     "How might escalating conflicts affect global security?",
   #     ...
   #   ]
   # }
   ```

3. **Execute Full Research:**
   ```python
   research = research_execute_full(
       filter_config={
           "timeframe": "last_7d",
           "categories": ["geopolitics_security"],
           "impact_min": 0.7
       },
       prompt="Analyze recent geopolitical developments",
       llm_model="gpt-4o-mini",
       perplexity_model="sonar-pro"
   )
   # Returns:
   # {
   #   "queries": [...],
   #   "research_results": [
   #     {
   #       "query": "What are the implications...",
   #       "answer": "Recent developments suggest...",
   #       "citations": [
   #         {"url": "...", "title": "..."}
   #       ]
   #     }
   #   ]
   # }
   ```

**Result:** Comprehensive research report with LLM-generated insights and Perplexity citations

---

## Access Methods

### REST API

**Base URL:** `http://192.168.178.72:8000`

**Authentication:** None (LAN-only access)

**Endpoints:** 260+ endpoints organized by resource

**Example:**
```bash
# Get latest articles
curl http://192.168.178.72:8000/items?limit=20

# Start analysis run
curl -X POST http://192.168.178.72:8000/api/analysis/runs \
  -H "Content-Type: application/json" \
  -d '{"model": "gpt-5-nano", "selector": {"latest": 50}}'
```

### MCP Tools (Claude Desktop)

**Connection:** Via HTTP MCP Server at `http://localhost:8001`

**Protocol:** JSON-RPC 2.0 over HTTP

**Tools:** 51 MCP tools across all feature areas

**Example:**
```python
# Claude Desktop uses MCP tools natively
# User: "Show me the latest tech articles"
# Claude calls: latest_articles(limit=20, category="Technology")
```

### Web UI

**URL:** `http://192.168.178.72:8000/admin/*`

**Pages:** 7 admin pages (feeds, statistics, database, analysis, processors, reports, auto-analysis)

**Features:** Visual interface for all operations, no API knowledge required

---

## System Statistics

**Current Scale (as of 2025-10-05):**
- **Feeds:** 37+ active feeds monitored
- **Articles:** 11,600+ articles stored
- **Analysis Coverage:** 17.67% of articles analyzed
- **Geopolitical Analysis:** 17.67% of analyzed articles
- **API Endpoints:** 260+
- **MCP Tools:** 51
- **Database Tables:** 35
- **Background Workers:** 3 (scheduler, analysis, content generator)
- **Code Size:** ~60k lines (37k core + 23k overhead)

**Supported LLM Models:**
- OpenAI: GPT-5 series, GPT-4.1 series, GPT-4o series
- Anthropic: Claude-3.5-sonnet, Claude-3-haiku (planned)
- Perplexity: sonar, sonar-pro, sonar-reasoning

**Export Formats:** JSON, CSV, XML

**Access Interfaces:** REST API, MCP Tools, Web UI

---

**End of Feature Reference**

For implementation details, see codebase in `/home/cytrex/news-mcp/`.
For API reference, see `/home/cytrex/news-mcp/docs/ENDPOINTS.md`.
For MCP integration, see `/home/cytrex/news-mcp/docs/MCP_DISCOVERY.md`.
