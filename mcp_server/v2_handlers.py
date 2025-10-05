"""
MCP v2 Tool Handler Implementations
Provides HTTP-based API calls for new MCP v2 tools
"""
import logging
from typing import List, Dict, Any, Optional
from mcp.types import TextContent
import httpx
import json
from sqlmodel import Session, select
from sqlalchemy import text
from app.database import engine
from app.models import Feed, Item

logger = logging.getLogger(__name__)

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

class MCPv2Handlers:
    """MCP v2 tool handler implementations"""

    BASE_URL = "http://localhost:8000/api"

    # Template Tools
    async def templates_create(self, name: str, match_rules: List[Dict[str, Any]], extraction_config: Dict[str, Any],
                               description: Optional[str] = None, processing_rules: Optional[Dict[str, Any]] = None) -> List[TextContent]:
        """Create new dynamic feed template via API"""
        try:
            api_url = f"{self.BASE_URL}/templates/create"
            data = {
                "name": name,
                "description": description,
                "match_rules": match_rules,
                "extraction_config": extraction_config,
                "processing_rules": processing_rules or {}
            }

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(api_url, json=data)
                response.raise_for_status()
                result = response.json()

            return [TextContent(type="text", text=safe_json_dumps(result, indent=2))]
        except Exception as e:
            logger.error(f"Error creating template: {e}")
            return [TextContent(type="text", text=f"Error creating template: {str(e)}")]

    async def templates_test(self, template_id: int, sample_url: Optional[str] = None, raw_html: Optional[str] = None) -> List[TextContent]:
        """Test template against sample URL or HTML"""
        try:
            api_url = f"{self.BASE_URL}/templates/{template_id}/test"
            data = {}
            if sample_url:
                data["sample_url"] = sample_url
            if raw_html:
                data["raw_html"] = raw_html

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(api_url, json=data)
                response.raise_for_status()
                result = response.json()

            return [TextContent(type="text", text=safe_json_dumps(result, indent=2))]
        except Exception as e:
            logger.error(f"Error testing template: {e}")
            return [TextContent(type="text", text=f"Error testing template: {str(e)}")]

    async def templates_assign(self, template_id: int, feed_id: int, priority: int = 100,
                               custom_overrides: Optional[Dict[str, Any]] = None) -> List[TextContent]:
        """Assign template to feed"""
        try:
            api_url = f"{self.BASE_URL}/templates/{template_id}/assign"
            data = {
                "feed_id": feed_id,
                "priority": priority,
                "custom_overrides": custom_overrides
            }

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(api_url, json=data)
                response.raise_for_status()
                result = response.json()

            return [TextContent(type="text", text=safe_json_dumps(result, indent=2))]
        except Exception as e:
            logger.error(f"Error assigning template: {e}")
            return [TextContent(type="text", text=f"Error assigning template: {str(e)}")]

    # Analysis Tools
    async def analysis_preview(self, selector: Dict[str, Any], model: str = "gpt-4o-mini", cost_estimate: bool = True) -> List[TextContent]:
        """Preview analysis run with cost estimation"""
        try:
            api_url = f"{self.BASE_URL}/analysis/preview"
            # Convert selector to RunScope format
            scope_data = {"type": "custom"}
            if "latest" in selector:
                scope_data = {"type": "latest", "count": selector["latest"]}
            elif "time_range" in selector:
                scope_data = {"type": "time_range", **selector["time_range"]}
            elif "feeds" in selector:
                scope_data = {"type": "feeds", "feed_ids": selector["feeds"]}

            data = {
                "scope": scope_data,
                "params": {"model": model, "cost_estimate": cost_estimate}
            }

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(api_url, json=data)
                response.raise_for_status()
                result = response.json()

            return [TextContent(type="text", text=safe_json_dumps(result, indent=2))]
        except Exception as e:
            logger.error(f"Error previewing analysis: {e}")
            return [TextContent(type="text", text=f"Error previewing analysis: {str(e)}")]

    async def analysis_run(self, selector: Dict[str, Any], model: str = "gpt-4o-mini", limit: int = 200,
                           dry_run: bool = False) -> List[TextContent]:
        """Start analysis run"""
        try:
            api_url = f"{self.BASE_URL}/analysis/start"
            # Convert selector to RunScope format
            scope_data = {"type": "global"}
            if "latest" in selector:
                # For latest, we need to use global scope with limit
                scope_data = {"type": "global"}
                limit = selector["latest"]
            elif "time_range" in selector:
                scope_data = {"type": "global", "start_time": selector["time_range"].get("start"),
                             "end_time": selector["time_range"].get("end")}
            elif "feeds" in selector:
                scope_data = {"type": "feeds", "feed_ids": selector["feeds"]}
            elif "items" in selector:
                scope_data = {"type": "items", "item_ids": selector["items"]}

            data = {
                "scope": scope_data,
                "params": {
                    "model_tag": model,
                    "limit": limit,
                    "rate_per_second": 1.0,
                    "dry_run": dry_run,
                    "triggered_by": "mcp"
                }
            }

            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(api_url, json=data)
                response.raise_for_status()
                result = response.json()

            return [TextContent(type="text", text=safe_json_dumps(result, indent=2))]
        except Exception as e:
            logger.error(f"Error starting analysis: {e}")
            return [TextContent(type="text", text=f"Error starting analysis: {str(e)}")]

    async def analysis_history(self, limit: int = 50, offset: int = 0, status: Optional[str] = None) -> List[TextContent]:
        """Get analysis run history"""
        try:
            api_url = f"{self.BASE_URL}/analysis/runs"
            params = {"limit": limit}
            if status:
                params["status"] = status

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(api_url, params=params)
                response.raise_for_status()
                runs = response.json()

            # Format runs for readability
            result = {
                "ok": True,
                "data": {
                    "runs": [{
                        "id": run["id"],
                        "status": run["status"],
                        "triggered_by": run.get("triggered_by", "unknown"),
                        "started_at": run.get("started_at"),
                        "completed_at": run.get("completed_at"),
                        "metrics": {
                            "total": run["metrics"]["total_count"],
                            "processed": run["metrics"]["processed_count"],
                            "failed": run["metrics"]["failed_count"],
                            "progress": run["metrics"]["progress_percent"]
                        },
                        "scope": run.get("scope", {}),
                        "params": run.get("params", {})
                    } for run in runs[offset:offset+limit]]
                },
                "meta": {"limit": limit, "offset": offset, "total": len(runs)},
                "errors": []
            }

            return [TextContent(type="text", text=safe_json_dumps(result, indent=2))]
        except Exception as e:
            logger.error(f"Error getting analysis history: {e}")
            return [TextContent(type="text", text=f"Error getting analysis history: {str(e)}")]

    async def analysis_results(self, run_id: int, limit: int = 50) -> List[TextContent]:
        """Get detailed sentiment results for a completed analysis run"""
        try:
            # Query items analyzed in this run with their sentiment data
            with Session(engine) as session:
                # Get run info first
                api_url = f"{self.BASE_URL}/analysis/runs"
                async with httpx.AsyncClient(timeout=10.0) as client:
                    response = await client.get(api_url, params={"limit": 100})
                    runs = response.json()
                    run = next((r for r in runs if r["id"] == run_id), None)
                    if not run:
                        return [TextContent(type="text", text=json.dumps({
                            "ok": False,
                            "errors": [{"code": "not_found", "message": f"Run #{run_id} not found"}]
                        }, indent=2))]

                # Query analyzed items from database
                query = text("""
                    SELECT
                        i.id, i.title, i.link,
                        ia.sentiment_json,
                        ia.impact_json,
                        ia.model_tag,
                        ia.updated_at
                    FROM analysis_run_items ari
                    JOIN items i ON ari.item_id = i.id
                    LEFT JOIN item_analysis ia ON i.id = ia.item_id
                    WHERE ari.run_id = :run_id
                    ORDER BY i.published DESC
                    LIMIT :limit
                """)
                results = session.execute(
                    query,
                    {"run_id": run_id, "limit": limit}
                ).fetchall()

                articles = []
                for row in results:
                    # JSONB columns are already dicts, no need to parse
                    sentiment = row[3] if row[3] else {}
                    impact = row[4] if row[4] else {}

                    articles.append({
                        "id": row[0],
                        "title": row[1],
                        "link": row[2],
                        "sentiment": sentiment.get("overall", {}).get("label", "unknown"),
                        "sentiment_score": sentiment.get("overall", {}).get("confidence", 0.0),
                        "impact_score": impact.get("overall", 0.0),
                        "urgency": sentiment.get("urgency", 0.0),
                        "topics": sentiment.get("topics", []),
                        "model": row[5],
                        "analyzed_at": str(row[6])
                    })

                result = {
                    "ok": True,
                    "data": {
                        "run_id": run_id,
                        "run_status": run["status"],
                        "articles": articles
                    },
                    "meta": {"total": len(articles), "limit": limit},
                    "errors": []
                }

                return [TextContent(type="text", text=safe_json_dumps(result, indent=2))]

        except Exception as e:
            logger.error(f"Error getting analysis results: {e}")
            return [TextContent(type="text", text=f"Error getting analysis results: {str(e)}")]

    # Scheduler Tools
    async def scheduler_set_interval(self, minutes: int, feed_id: Optional[int] = None) -> List[TextContent]:
        """Set scheduler interval"""
        try:
            if feed_id:
                api_url = f"{self.BASE_URL}/scheduler/interval/{feed_id}"
            else:
                api_url = f"{self.BASE_URL}/scheduler/interval"

            data = {"minutes": minutes}

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(api_url, json=data)
                response.raise_for_status()
                result = response.json()

            return [TextContent(type="text", text=safe_json_dumps(result, indent=2))]
        except Exception as e:
            logger.error(f"Error setting interval: {e}")
            return [TextContent(type="text", text=f"Error setting interval: {str(e)}")]

    async def scheduler_heartbeat(self) -> List[TextContent]:
        """Get scheduler heartbeat"""
        try:
            api_url = f"{self.BASE_URL}/scheduler/heartbeat"

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(api_url)
                response.raise_for_status()
                result = response.json()

            return [TextContent(type="text", text=safe_json_dumps(result, indent=2))]
        except Exception as e:
            logger.error(f"Error getting heartbeat: {e}")
            return [TextContent(type="text", text=f"Error getting heartbeat: {str(e)}")]

    # Enhanced Feed Tools
    async def feeds_search(self, q: Optional[str] = None, category: Optional[str] = None,
                           health: Optional[str] = None, limit: int = 50, offset: int = 0) -> List[TextContent]:
        """Search feeds with filtering"""
        try:
            with Session(engine) as session:
                query = select(Feed)

                if q:
                    query = query.where(Feed.title.contains(q) | Feed.url.contains(q))
                if health:
                    # Map health status to feed status
                    if health == "ok":
                        query = query.where(Feed.status == "active")
                    elif health == "fail":
                        query = query.where(Feed.status == "error")
                    elif health == "warn":
                        query = query.where(Feed.status == "paused")

                query = query.offset(offset).limit(limit)
                feeds = session.exec(query).all()

                result = {
                    "ok": True,
                    "data": {
                        "feeds": [{
                            "id": f.id,
                            "title": f.title,
                            "url": f.url,
                            "status": f.status,
                            "fetch_interval_minutes": f.fetch_interval_minutes,
                            "last_fetch": str(f.last_fetch) if f.last_fetch else None
                        } for f in feeds]
                    },
                    "meta": {"limit": limit, "offset": offset, "total": len(feeds)},
                    "errors": []
                }

                return [TextContent(type="text", text=safe_json_dumps(result, indent=2))]
        except Exception as e:
            logger.error(f"Error searching feeds: {e}")
            return [TextContent(type="text", text=f"Error searching feeds: {str(e)}")]

    async def feeds_health(self, feed_id: Optional[int] = None) -> List[TextContent]:
        """Get feed health metrics"""
        try:
            if feed_id:
                api_url = f"{self.BASE_URL}/health/feeds/{feed_id}"
            else:
                api_url = f"{self.BASE_URL}/health/feeds"

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(api_url)
                response.raise_for_status()
                result = response.json()

            return [TextContent(type="text", text=safe_json_dumps(result, indent=2))]
        except Exception as e:
            logger.error(f"Error getting feed health: {e}")
            return [TextContent(type="text", text=f"Error getting feed health: {str(e)}")]

    # Enhanced Item Tools
    async def items_recent(self, limit: int = 50, since: Optional[str] = None, feed_id: Optional[int] = None,
                           category: Optional[str] = None, dedupe: bool = True) -> List[TextContent]:
        """Get recent items with deduplication"""
        try:
            with Session(engine) as session:
                # Query items with analysis data
                query = text("""
                    SELECT
                        i.id, i.title, i.description, i.link, i.published, i.feed_id,
                        a.sentiment_json::jsonb->>'category' as category,
                        a.sentiment_json::jsonb->'semantic_tags'->>'actor' as actor,
                        a.sentiment_json::jsonb->'semantic_tags'->>'theme' as theme,
                        a.sentiment_json::jsonb->'semantic_tags'->>'region' as region,
                        a.sentiment_json::jsonb->'overall'->>'label' as sentiment,
                        (a.sentiment_json::jsonb->'impact'->>'overall')::float as impact
                    FROM items i
                    LEFT JOIN item_analysis a ON a.item_id = i.id
                    WHERE 1=1
                        {since_filter}
                        {feed_filter}
                    ORDER BY i.published DESC
                    LIMIT :limit
                """)

                params = {"limit": limit}
                since_filter = ""
                feed_filter = ""

                if since:
                    from datetime import datetime
                    since_dt = datetime.fromisoformat(since.replace('Z', '+00:00'))
                    since_filter = "AND i.published > :since_dt"
                    params['since_dt'] = since_dt

                if feed_id:
                    feed_filter = "AND i.feed_id = :feed_id"
                    params['feed_id'] = feed_id

                # Format query with filters
                formatted_query = str(query).format(since_filter=since_filter, feed_filter=feed_filter)
                result_rows = session.execute(text(formatted_query), params).fetchall()

                result = {
                    "ok": True,
                    "data": {
                        "items": [{
                            "id": row[0],
                            "title": row[1],
                            "description": row[2],
                            "link": row[3],
                            "published": str(row[4]) if row[4] else None,
                            "feed_id": row[5],
                            "category": row[6] or "panorama",
                            "semantic_tags": {
                                "actor": row[7] or "Unknown",
                                "theme": row[8] or "General",
                                "region": row[9] or "Global"
                            },
                            "sentiment": row[10] or "neutral",
                            "impact": row[11] or 0.0
                        } for row in result_rows]
                    },
                    "meta": {"limit": limit, "total": len(result_rows), "dedupe_applied": dedupe},
                    "errors": []
                }

                return [TextContent(type="text", text=safe_json_dumps(result, indent=2))]
        except Exception as e:
            logger.error(f"Error getting recent items: {e}")
            return [TextContent(type="text", text=f"Error getting recent items: {str(e)}")]

    async def items_search(self, q: str, limit: int = 50, offset: int = 0,
                           time_range: Optional[Dict[str, str]] = None, feeds: Optional[List[int]] = None,
                           categories: Optional[List[str]] = None) -> List[TextContent]:
        """Search items with advanced filtering"""
        try:
            with Session(engine) as session:
                # Build WHERE conditions
                where_conditions = ["(i.title ILIKE :query OR i.description ILIKE :query)"]
                params = {"query": f"%{q}%", "limit": limit, "offset": offset}

                if feeds:
                    where_conditions.append("i.feed_id = ANY(:feeds)")
                    params['feeds'] = feeds

                if time_range:
                    from datetime import datetime
                    if time_range.get("from"):
                        from_dt = datetime.fromisoformat(time_range["from"].replace('Z', '+00:00'))
                        where_conditions.append("i.published >= :from_dt")
                        params['from_dt'] = from_dt
                    if time_range.get("to"):
                        to_dt = datetime.fromisoformat(time_range["to"].replace('Z', '+00:00'))
                        where_conditions.append("i.published <= :to_dt")
                        params['to_dt'] = to_dt

                if categories:
                    where_conditions.append("a.sentiment_json::jsonb->>'category' = ANY(:categories)")
                    params['categories'] = categories

                where_clause = " AND ".join(where_conditions)

                query = text(f"""
                    SELECT
                        i.id, i.title, i.description, i.link, i.published, i.feed_id,
                        a.sentiment_json::jsonb->>'category' as category,
                        a.sentiment_json::jsonb->'semantic_tags'->>'actor' as actor,
                        a.sentiment_json::jsonb->'semantic_tags'->>'theme' as theme,
                        a.sentiment_json::jsonb->'semantic_tags'->>'region' as region,
                        a.sentiment_json::jsonb->'overall'->>'label' as sentiment,
                        (a.sentiment_json::jsonb->'impact'->>'overall')::float as impact
                    FROM items i
                    LEFT JOIN item_analysis a ON a.item_id = i.id
                    WHERE {where_clause}
                    ORDER BY i.published DESC
                    OFFSET :offset
                    LIMIT :limit
                """)

                result_rows = session.execute(query, params).fetchall()

                result = {
                    "ok": True,
                    "data": {
                        "items": [{
                            "id": row[0],
                            "title": row[1],
                            "description": row[2],
                            "link": row[3],
                            "published": str(row[4]) if row[4] else None,
                            "feed_id": row[5],
                            "category": row[6] or "panorama",
                            "semantic_tags": {
                                "actor": row[7] or "Unknown",
                                "theme": row[8] or "General",
                                "region": row[9] or "Global"
                            },
                            "sentiment": row[10] or "neutral",
                            "impact": row[11] or 0.0
                        } for row in result_rows]
                    },
                    "meta": {"limit": limit, "offset": offset, "total": len(result_rows), "query": q},
                    "errors": []
                }

                return [TextContent(type="text", text=safe_json_dumps(result, indent=2))]
        except Exception as e:
            logger.error(f"Error searching items: {e}")
            return [TextContent(type="text", text=f"Error searching items: {str(e)}")]

    # Discovery Tools
    async def get_schemas(self, schema_name: Optional[str] = None) -> List[TextContent]:
        """Get JSON Schema definitions for data structures

        Returns schema definitions for understanding API response formats.
        """
        try:
            from .schemas import SCHEMAS, SCHEMA_VERSION

            if schema_name:
                if schema_name not in SCHEMAS:
                    available = list(SCHEMAS.keys())
                    return [TextContent(
                        type="text",
                        text=f"Schema '{schema_name}' not found.\n\nAvailable schemas: {', '.join(available)}"
                    )]
                schema_data = {schema_name: SCHEMAS[schema_name]}
            else:
                schema_data = SCHEMAS

            result = {
                "schema_version": SCHEMA_VERSION,
                "schemas": schema_data
            }

            return [TextContent(type="text", text=safe_json_dumps(result, indent=2))]

        except Exception as e:
            logger.error(f"Error getting schemas: {e}")
            return [TextContent(type="text", text=f"Error getting schemas: {str(e)}")]

    async def get_example_data(self, example_type: str) -> List[TextContent]:
        """Get real example data for understanding structures

        Returns actual data from the system to show expected formats.

        Args:
            example_type: Type of example (item_with_analysis, item_basic, feed_health, analysis_run)
        """
        try:
            with Session(engine) as session:
                if example_type == "item_with_analysis":
                    # Get a real analyzed article
                    from sqlalchemy import text
                    query = text("""
                        SELECT
                            i.id, i.title, i.description, i.link, i.published,
                            ia.sentiment_label, ia.sentiment_score,
                            ia.impact_score, ia.urgency_score
                        FROM items i
                        JOIN item_analysis ia ON i.id = ia.item_id
                        WHERE ia.sentiment_score IS NOT NULL
                        LIMIT 1
                    """)
                    row = session.execute(query).fetchone()

                    if row:
                        example = {
                            "example_type": example_type,
                            "example": {
                                "id": row[0],
                                "title": row[1],
                                "description": row[2],
                                "link": row[3],
                                "published": str(row[4]) if row[4] else None,
                                "analysis": {
                                    "sentiment": {
                                        "label": row[5],
                                        "score": float(row[6]) if row[6] else None
                                    },
                                    "impact_score": float(row[7]) if row[7] else None,
                                    "urgency_score": float(row[8]) if row[8] else None
                                }
                            },
                            "note": "This is real data from the system. Use it to understand expected data structure."
                        }
                    else:
                        example = {
                            "example_type": example_type,
                            "error": "No analyzed articles found in system",
                            "suggestion": "Run analysis_run first to generate analyzed data"
                        }

                elif example_type == "item_basic":
                    # Get a basic article (no analysis)
                    item = session.exec(select(Item).limit(1)).first()
                    if item:
                        example = {
                            "example_type": example_type,
                            "example": {
                                "id": item.id,
                                "title": item.title,
                                "description": item.description,
                                "link": item.link,
                                "published": str(item.published) if item.published else None,
                                "feed_id": item.feed_id,
                                "guid": item.guid
                            }
                        }
                    else:
                        example = {"example_type": example_type, "error": "No articles in system"}

                elif example_type == "feed_health":
                    # Get feed with health metrics
                    from sqlalchemy import text
                    query = text("""
                        SELECT
                            f.id, f.title, f.url, f.status,
                            fh.success_rate_7d, fh.avg_response_time_ms,
                            fh.consecutive_failure_count, fh.last_successful_fetch
                        FROM feeds f
                        LEFT JOIN feed_health fh ON f.id = fh.feed_id
                        LIMIT 1
                    """)
                    row = session.execute(query).fetchone()

                    if row:
                        example = {
                            "example_type": example_type,
                            "example": {
                                "feed": {
                                    "id": row[0],
                                    "title": row[1],
                                    "url": row[2],
                                    "status": row[3]
                                },
                                "health": {
                                    "success_rate_7d": float(row[4]) if row[4] else None,
                                    "avg_response_time_ms": float(row[5]) if row[5] else None,
                                    "consecutive_failures": row[6] or 0,
                                    "last_successful_fetch": str(row[7]) if row[7] else None
                                }
                            }
                        }
                    else:
                        example = {"example_type": example_type, "error": "No feeds in system"}

                elif example_type == "analysis_run":
                    # Get an analysis run
                    from sqlalchemy import text
                    query = text("""
                        SELECT
                            id, status, model, created_at, completed_at,
                            queued_count, processed_count, failed_count,
                            estimated_cost, triggered_by
                        FROM analysis_runs
                        LIMIT 1
                    """)
                    row = session.execute(query).fetchone()

                    if row:
                        example = {
                            "example_type": example_type,
                            "example": {
                                "id": row[0],
                                "status": row[1],
                                "model": row[2],
                                "created_at": str(row[3]) if row[3] else None,
                                "completed_at": str(row[4]) if row[4] else None,
                                "queued_count": row[5],
                                "processed_count": row[6],
                                "failed_count": row[7],
                                "estimated_cost": float(row[8]) if row[8] else None,
                                "triggered_by": row[9]
                            }
                        }
                    else:
                        example = {"example_type": example_type, "error": "No analysis runs in system"}

                else:
                    return [TextContent(
                        type="text",
                        text=f"Unknown example type: {example_type}\n\nAvailable: item_with_analysis, item_basic, feed_health, analysis_run"
                    )]

                return [TextContent(type="text", text=safe_json_dumps(example, indent=2))]

        except Exception as e:
            logger.error(f"Error getting example data: {e}")
            return [TextContent(type="text", text=f"Error getting example data: {str(e)}")]

    async def get_usage_guide(self) -> List[TextContent]:
        """Get comprehensive usage guide

        Returns detailed guide explaining all metrics, best practices, and interpretations.
        """
        guide = """# News-MCP Usage Guide

## Field Interpretations

### Sentiment Scores
- **Range:** -1.0 to +1.0
- **Below -0.5:** Strong negative sentiment (bad news, crises, conflicts)
- **-0.5 to -0.2:** Moderately negative
- **-0.2 to +0.2:** Neutral (factual reporting)
- **+0.2 to +0.5:** Moderately positive
- **Above +0.5:** Strong positive sentiment (achievements, breakthroughs)

**Example Usage:**
```python
# Get positive news only
latest_articles(min_sentiment=0.3, limit=20)

# Get crisis/negative news
latest_articles(max_sentiment=-0.5, limit=20)
```

### Impact Score
- **Range:** 0.0 to 1.0
- **0.0-0.3:** Low impact (routine news, minor updates)
- **0.3-0.6:** Medium impact (notable events, sector-specific news)
- **0.6-1.0:** High impact (major events, market-moving news, breaking developments)

**Example Usage:**
```python
# High-impact news only
latest_articles(min_impact=0.7, limit=10)

# Medium-impact technology news
search_articles(query="technology", min_impact=0.4, max_impact=0.7)
```

### Geopolitical Metrics (17.67% of analyzed articles)

**stability_score (-1.0 to +1.0):**
- **Below -0.7:** Severe destabilization (wars, coups, major conflicts)
- **-0.7 to -0.3:** Moderate destabilization (protests, sanctions, tensions)
- **-0.3 to +0.3:** Stable situation
- **Above +0.3:** Stabilizing effect (peace deals, cooperation)

**escalation_potential (0.0 to 1.0):**
- **0.0-0.3:** Low escalation risk
- **0.3-0.7:** Moderate escalation risk
- **0.7-1.0:** High escalation risk (likely to worsen)

**security_relevance (0.0 to 1.0):**
- **0.0-0.3:** Low security concern
- **0.3-0.7:** Moderate security concern
- **0.7-1.0:** Critical security issue

## Best Practices

### Article Discovery
1. **Start broad, then filter:**
   ```python
   latest_articles(limit=100)  # See what's available
   latest_articles(min_impact=0.5, limit=20)  # Filter for important news
   ```

2. **Use categories for focus:**
   ```python
   # First check available categories
   # Read resource: news-mcp://data/available-categories

   latest_articles(category="Technology", limit=30)
   ```

3. **Combine filters:**
   ```python
   # High-impact positive tech news
   latest_articles(
       category="Technology",
       min_sentiment=0.3,
       min_impact=0.6,
       limit=10
   )
   ```

### Analysis Runs
1. **Always preview first:**
   ```python
   # Check cost before running
   preview = analysis_preview(model="gpt-5-nano", selector={"latest": 100})
   # If estimated_cost acceptable, then run
   analysis_run(model="gpt-5-nano", selector={"latest": 100})
   ```

2. **Choose appropriate model:**
   - `gpt-5-nano`: Cheapest ($0.05/$0.40) - good for bulk analysis
   - `gpt-5-mini`: Balanced ($0.25/$2.00) - good quality/cost ratio
   - `gpt-4.1-nano`: Fast and cheap ($0.10/$0.40)
   - `gpt-4o`: Most expensive ($2.50/$10.00) - highest quality

3. **Use auto-analysis for routine processing:**
   ```python
   # Enable per feed
   update_feed(feed_id=12, auto_analyze_enabled=True)
   # New articles will be analyzed automatically using gpt-5-nano
   ```

### Research Pipeline
1. **Filter articles strategically:**
   ```python
   # Get high-impact articles on specific topic
   research_filter_articles(
       timeframe="last_7d",
       categories=["Politics", "Security"],
       impact_min=0.6,
       max_articles=20
   )
   ```

2. **Use full pipeline for deep research:**
   ```python
   # Filters → Generates queries → Executes research
   research_execute_full(
       filter_config={
           "timeframe": "last_7d",
           "impact_min=0.7
       },
       prompt="Analyze geopolitical implications and security risks",
       perplexity_model="sonar-pro"  # Use "sonar" for speed, "sonar-pro" for depth
   )
   ```

## Common Patterns

### Daily News Briefing
```python
# 1. Check system status
get_dashboard()

# 2. Get top stories from last 24h
latest_articles(
    since_hours=24,
    min_impact=0.6,
    sort_by="impact_score",
    limit=10
)

# 3. Check trending topics
trending_topics(hours=24, min_frequency=5, top_n=20)
```

### Feed Health Monitoring
```python
# 1. Get overall health
system_health()

# 2. Check specific feed issues
feeds_health()  # Get all with health indicators

# 3. Diagnose problems
feed_diagnostics(feed_id=<failing_feed_id>)
```

### Cost-Effective Analysis
```python
# 1. Analyze only unanalyzed articles
analysis_run(model="gpt-5-nano", selector={"smart": True})

# 2. Use auto-analysis for continuous coverage
# (Processes new items automatically)
update_feed(feed_id=X, auto_analyze_enabled=True)
```

## Country & Alliance Codes

### Common Country Codes (ISO 3166-1 alpha-2)
- `US` = United States
- `IL` = Israel
- `PS` = Palestine
- `UA` = Ukraine
- `RU` = Russia
- `CN` = China
- `DE` = Germany
- `FR` = France
- `GB` = United Kingdom

### Alliance Codes
- `NATO` = North Atlantic Treaty Organization
- `EU` = European Union
- `BRICS` = Brazil, Russia, India, China, South Africa
- `G7` = Group of Seven (major advanced economies)
- `G20` = Group of Twenty
- `ASEAN` = Association of Southeast Asian Nations
- `Arab_League` = League of Arab States
- `AU` = African Union

## Troubleshooting

### "No analyzed articles found"
**Solution:** Run analysis first:
```python
analysis_run(model="gpt-5-nano", selector={"latest": 100})
```

### "Feed health is FAIL"
**Solutions:**
1. Check diagnostics: `feed_diagnostics(feed_id=X)`
2. Test feed URL: `test_feed(url="...")`
3. Pause and fix: `update_feed(feed_id=X, status="PAUSED")`

### "Cost too high"
**Solutions:**
1. Reduce scope: Use smaller `latest` number
2. Use cheaper model: `gpt-5-nano` instead of `gpt-4o`
3. Enable auto-analysis: Spreads cost over time

## Additional Resources

- **System Overview:** Read resource `news-mcp://system-overview`
- **Feature Guides:** `news-mcp://features/<area>`
- **Live Data:** `news-mcp://data/*`
- **Workflows:** `news-mcp://workflows/common`
"""

        return [TextContent(type="text", text=guide)]