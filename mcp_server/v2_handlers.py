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
                query = select(Item).join(Feed)

                if since:
                    from datetime import datetime
                    since_dt = datetime.fromisoformat(since.replace('Z', '+00:00'))
                    query = query.where(Item.published > since_dt)

                if feed_id:
                    query = query.where(Item.feed_id == feed_id)

                query = query.order_by(Item.published.desc()).limit(limit)
                items = session.exec(query).all()

                result = {
                    "ok": True,
                    "data": {
                        "items": [{
                            "id": i.id,
                            "title": i.title,
                            "description": i.description,
                            "link": i.link,
                            "published": str(i.published) if i.published else None,
                            "feed_id": i.feed_id
                        } for i in items]
                    },
                    "meta": {"limit": limit, "total": len(items), "dedupe_applied": dedupe},
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
                query = select(Item).join(Feed)

                # Full-text search simulation
                query = query.where(Item.title.contains(q) | Item.description.contains(q))

                if feeds:
                    query = query.where(Item.feed_id.in_(feeds))

                if time_range:
                    from datetime import datetime
                    if time_range.get("from"):
                        from_dt = datetime.fromisoformat(time_range["from"].replace('Z', '+00:00'))
                        query = query.where(Item.published >= from_dt)
                    if time_range.get("to"):
                        to_dt = datetime.fromisoformat(time_range["to"].replace('Z', '+00:00'))
                        query = query.where(Item.published <= to_dt)

                query = query.offset(offset).limit(limit)
                items = session.exec(query).all()

                result = {
                    "ok": True,
                    "data": {
                        "items": [{
                            "id": i.id,
                            "title": i.title,
                            "description": i.description,
                            "link": i.link,
                            "published": str(i.published) if i.published else None,
                            "feed_id": i.feed_id
                        } for i in items]
                    },
                    "meta": {"limit": limit, "offset": offset, "total": len(items), "query": q},
                    "errors": []
                }

                return [TextContent(type="text", text=safe_json_dumps(result, indent=2))]
        except Exception as e:
            logger.error(f"Error searching items: {e}")
            return [TextContent(type="text", text=f"Error searching items: {str(e)}")]