"""
MCP Resources - Automatic Feature Discovery for Claude Desktop

Provides static resources that Claude Desktop can load automatically
without requiring tool calls, enabling proactive guidance.
"""

import json
import logging
from pathlib import Path
from typing import List
from mcp.types import Resource
from sqlmodel import Session, select
from app.database import engine
from app.models import Category, Feed

logger = logging.getLogger(__name__)

# Path to documentation files
DOCS_DIR = Path("/home/cytrex/news-mcp/docs")


class NewsResourceProvider:
    """Provides MCP Resources for News-MCP system"""

    @staticmethod
    def list_resources() -> List[Resource]:
        """Return list of available resources"""
        return [
            Resource(
                uri="news-mcp://system-overview",
                name="System Overview",
                description="Executive summary of News-MCP capabilities - RSS aggregation, AI analysis, research pipeline, special reports",
                mimeType="text/markdown"
            ),
            Resource(
                uri="news-mcp://features/feed-management",
                name="Feed Management Features",
                description="RSS feed operations: add/update/delete feeds, health monitoring, auto-refresh, template assignment",
                mimeType="text/markdown"
            ),
            Resource(
                uri="news-mcp://features/analysis",
                name="AI Analysis Features",
                description="LLM-powered sentiment and impact analysis using GPT-5/GPT-4/Claude models with cost estimation",
                mimeType="text/markdown"
            ),
            Resource(
                uri="news-mcp://features/research",
                name="Research Pipeline Features",
                description="Article filtering → LLM query generation → Perplexity research with citations",
                mimeType="text/markdown"
            ),
            Resource(
                uri="news-mcp://features/special-reports",
                name="Special Reports Features",
                description="Automated LLM-based report generation with article selection criteria and scheduling",
                mimeType="text/markdown"
            ),
            Resource(
                uri="news-mcp://data/available-categories",
                name="Available Categories",
                description="Current article categories in the system (live data)",
                mimeType="application/json"
            ),
            Resource(
                uri="news-mcp://data/active-feeds",
                name="Active Feeds",
                description="Currently monitored RSS feeds (live data)",
                mimeType="application/json"
            ),
            Resource(
                uri="news-mcp://data/system-stats",
                name="System Statistics",
                description="Current system scale: article count, analysis coverage, feeds, models",
                mimeType="application/json"
            ),
            Resource(
                uri="news-mcp://workflows/common",
                name="Common Workflows",
                description="Step-by-step guides for typical tasks (add feed, run analysis, generate report, research)",
                mimeType="text/markdown"
            ),
            Resource(
                uri="news-mcp://guide/quick-start",
                name="Quick Start Guide",
                description="Get started with News-MCP in 5 minutes - essential tools and workflows",
                mimeType="text/markdown"
            )
        ]

    @staticmethod
    def read_resource(uri: str) -> str:
        """Return resource content based on URI"""

        # System Overview
        if uri == "news-mcp://system-overview":
            return NewsResourceProvider._get_system_overview()

        # Feature Guides
        elif uri == "news-mcp://features/feed-management":
            return NewsResourceProvider._extract_section("## 1. Feed Management")

        elif uri == "news-mcp://features/analysis":
            return NewsResourceProvider._extract_section("## 3. AI Analysis System")

        elif uri == "news-mcp://features/research":
            return NewsResourceProvider._extract_section("## 4. Research Pipeline")

        elif uri == "news-mcp://features/special-reports":
            return NewsResourceProvider._extract_section("## 5. Special Reports")

        # Live Data
        elif uri == "news-mcp://data/available-categories":
            return NewsResourceProvider._get_available_categories()

        elif uri == "news-mcp://data/active-feeds":
            return NewsResourceProvider._get_active_feeds()

        elif uri == "news-mcp://data/system-stats":
            return NewsResourceProvider._get_system_stats()

        # Workflows
        elif uri == "news-mcp://workflows/common":
            return NewsResourceProvider._get_common_workflows()

        elif uri == "news-mcp://guide/quick-start":
            return NewsResourceProvider._get_quick_start()

        else:
            return json.dumps({
                "error": f"Resource not found: {uri}",
                "available": [r.uri for r in NewsResourceProvider.list_resources()]
            })

    @staticmethod
    def _get_system_overview() -> str:
        """Return executive summary of News-MCP"""
        features_file = DOCS_DIR / "FEATURES.md"

        try:
            with open(features_file, 'r') as f:
                content = f.read()

            # Extract Executive Summary + Table of Contents
            # Find start of Executive Summary
            start = content.find("## Executive Summary")
            if start == -1:
                return "# News-MCP System Overview\n\nDocumentation not found."

            # Find end (start of Feature Catalog)
            end = content.find("## Feature Catalog")
            if end == -1:
                # Return first 6000 chars if no clear section boundary
                return content[start:start+6000]

            overview = content[start:end]
            overview += "\n\n**For detailed features, see other resources:**\n"
            overview += "- `news-mcp://features/feed-management`\n"
            overview += "- `news-mcp://features/analysis`\n"
            overview += "- `news-mcp://features/research`\n"
            overview += "- `news-mcp://features/special-reports`\n"

            return overview

        except Exception as e:
            logger.error(f"Error loading system overview: {e}")
            return f"# News-MCP System Overview\n\nError loading documentation: {str(e)}"

    @staticmethod
    def _extract_section(section_header: str) -> str:
        """Extract a specific section from FEATURES.md"""
        features_file = DOCS_DIR / "FEATURES.md"

        try:
            with open(features_file, 'r') as f:
                content = f.read()

            # Find section start
            start = content.find(section_header)
            if start == -1:
                return f"# Section Not Found\n\n{section_header} not found in documentation."

            # Find next ## header (end of section)
            # Look for next "## " after current position
            end = content.find("\n## ", start + len(section_header))
            if end == -1:
                # If no next section, take rest of doc (or limit to 10000 chars)
                section_content = content[start:start+10000]
            else:
                section_content = content[start:end]

            return section_content

        except Exception as e:
            logger.error(f"Error extracting section {section_header}: {e}")
            return f"# Error\n\nFailed to extract {section_header}: {str(e)}"

    @staticmethod
    def _get_available_categories() -> str:
        """Return list of current categories (live data)"""
        try:
            with Session(engine) as session:
                categories = session.exec(select(Category)).all()

                category_data = [
                    {
                        "id": cat.id,
                        "name": cat.name,
                        "description": getattr(cat, 'description', None)
                    }
                    for cat in categories
                ]

                return json.dumps({
                    "categories": category_data,
                    "count": len(category_data),
                    "note": "Use these category names in research_filter_articles or latest_articles tools"
                }, indent=2)

        except Exception as e:
            logger.error(f"Error getting categories: {e}")
            return json.dumps({"error": str(e), "categories": []})

    @staticmethod
    def _get_active_feeds() -> str:
        """Return list of active feeds (live data)"""
        try:
            with Session(engine) as session:
                feeds = session.exec(
                    select(Feed).where(Feed.status == "ACTIVE")
                ).all()

                feed_data = [
                    {
                        "id": feed.id,
                        "title": feed.title,
                        "url": feed.url,
                        "fetch_interval_minutes": feed.fetch_interval_minutes,
                        "auto_analyze_enabled": getattr(feed, 'auto_analyze_enabled', False)
                    }
                    for feed in feeds
                ]

                return json.dumps({
                    "feeds": feed_data,
                    "count": len(feed_data),
                    "note": "Use feed IDs in analysis_run, latest_articles, or other feed-specific tools"
                }, indent=2)

        except Exception as e:
            logger.error(f"Error getting feeds: {e}")
            return json.dumps({"error": str(e), "feeds": []})

    @staticmethod
    def _get_system_stats() -> str:
        """Return current system statistics (live data)"""
        try:
            from sqlalchemy import text

            with Session(engine) as session:
                # Count feeds
                feed_count = session.exec(
                    select(Feed).where(Feed.status == "ACTIVE")
                ).all()
                total_feeds = len(feed_count)

                # Count articles
                article_count = session.execute(
                    text("SELECT COUNT(*) FROM items")
                ).scalar()

                # Count analyzed articles
                analyzed_count = session.execute(
                    text("SELECT COUNT(DISTINCT item_id) FROM item_analysis")
                ).scalar()

                # Analysis coverage
                coverage = (analyzed_count / article_count * 100) if article_count > 0 else 0

                return json.dumps({
                    "feeds": {
                        "active": total_feeds,
                        "total": session.execute(text("SELECT COUNT(*) FROM feeds")).scalar()
                    },
                    "articles": {
                        "total": article_count,
                        "analyzed": analyzed_count,
                        "coverage_percent": round(coverage, 2)
                    },
                    "analysis": {
                        "total_runs": session.execute(text("SELECT COUNT(*) FROM analysis_runs")).scalar(),
                        "models_available": ["gpt-5-nano", "gpt-5-mini", "gpt-5", "gpt-4.1-nano", "gpt-4.1-mini", "gpt-4.1", "gpt-4o-mini", "gpt-4o"]
                    },
                    "note": "Live data from database - current as of request time"
                }, indent=2)

        except Exception as e:
            logger.error(f"Error getting system stats: {e}")
            return json.dumps({"error": str(e)})

    @staticmethod
    def _get_common_workflows() -> str:
        """Return common workflow guides"""
        features_file = DOCS_DIR / "FEATURES.md"

        try:
            with open(features_file, 'r') as f:
                content = f.read()

            # Extract "Common Workflows" section
            start = content.find("## Common Workflows")
            if start == -1:
                return NewsResourceProvider._generate_workflow_guide()

            end = content.find("\n## ", start + 20)
            if end == -1:
                workflows = content[start:]
            else:
                workflows = content[start:end]

            return workflows

        except Exception as e:
            logger.error(f"Error loading workflows: {e}")
            return NewsResourceProvider._generate_workflow_guide()

    @staticmethod
    def _generate_workflow_guide() -> str:
        """Generate workflow guide if FEATURES.md not available"""
        return """# Common Workflows

## Workflow 1: Add and Monitor a Feed

1. Test feed URL first:
   ```
   test_feed(url="https://example.com/rss", show_items=5)
   ```

2. Add feed:
   ```
   add_feed(url="https://example.com/rss", title="Example Feed", auto_analyze_enabled=True)
   ```

3. Check health after first fetch:
   ```
   feed_diagnostics(feed_id=<returned_id>)
   ```

## Workflow 2: Run Bulk Analysis

1. Preview cost:
   ```
   analysis_preview(model="gpt-5-nano", selector={"latest": 100})
   ```

2. Start analysis:
   ```
   analysis_run(model="gpt-5-nano", selector={"latest": 100}, persist=True)
   ```

3. View analyzed articles:
   ```
   latest_articles(min_sentiment=0.5, limit=20)
   ```

## Workflow 3: Research Pipeline

1. Filter articles:
   ```
   research_filter_articles(timeframe="last_7d", impact_min=0.7, max_articles=20)
   ```

2. Execute full research:
   ```
   research_execute_full(filter_config={...}, prompt="Analyze geopolitical implications")
   ```

## Workflow 4: Generate Special Report

Use Web UI at http://192.168.178.72:8000/admin/special-reports to configure report templates.
"""

    @staticmethod
    def _get_quick_start() -> str:
        """Return quick start guide"""
        return """# News-MCP Quick Start Guide

## Get Started in 5 Minutes

### 1. Check System Status
```
get_dashboard()
```
See: Total feeds, articles, health overview

### 2. View Available Data
Check what's already in the system:
- `list_feeds()` - See all RSS feeds
- `latest_articles(limit=20)` - See recent articles
- Read resource: `news-mcp://data/available-categories` - See categories

### 3. Add Your First Feed
```
# Test feed first
test_feed(url="https://techcrunch.com/feed/", show_items=5)

# Add if looks good
add_feed(url="https://techcrunch.com/feed/", title="TechCrunch", auto_analyze_enabled=True)
```

### 4. Run Your First Analysis
```
# Preview cost
analysis_preview(model="gpt-5-nano", selector={"latest": 50})

# Run if cost acceptable
analysis_run(model="gpt-5-nano", selector={"latest": 50}, persist=True)
```

### 5. Search Analyzed Articles
```
# High-impact positive articles
latest_articles(min_sentiment=0.5, min_impact=0.6, limit=10)

# Search by keyword
search_articles(query="AI regulation", limit=20)
```

## Key Tools to Know

**Feed Management:**
- `list_feeds()` - View all feeds
- `add_feed()` - Add new RSS feed
- `feed_diagnostics(feed_id=X)` - Check feed health

**Article Access:**
- `latest_articles()` - Get recent articles with filters
- `search_articles(query="...")` - Full-text search
- `trending_topics()` - Discover trending keywords

**AI Analysis:**
- `analysis_preview()` - Estimate cost before running
- `analysis_run()` - Execute batch analysis
- `analysis_history()` - View past runs

**Research:**
- `research_filter_articles()` - Filter by criteria
- `research_execute_full()` - Full pipeline (filter → generate → research)

**System:**
- `get_dashboard()` - System overview
- `system_health()` - Health check

## Next Steps

1. **Explore Features:** Read `news-mcp://system-overview` resource
2. **Learn Workflows:** Read `news-mcp://workflows/common` resource
3. **Check Live Data:** Read `news-mcp://data/system-stats` resource

## Web UI

Access admin interface at: **http://192.168.178.72:8000/admin/feeds**

Pages available:
- `/admin/feeds` - Feed management
- `/admin/statistics` - System dashboard
- `/admin/analysis-manager` - Analysis control
- `/admin/special-reports` - Report generation
- `/admin/database` - Database explorer

## Need Help?

- **System Overview:** Read `news-mcp://system-overview`
- **Specific Feature:** Read `news-mcp://features/<area>` resources
- **Live Data:** Check `news-mcp://data/*` resources
"""
