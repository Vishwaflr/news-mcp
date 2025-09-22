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

    async def analysis_run(self, selector: Dict[str, Any], model: str = "gpt-4o-mini", persist: bool = True,
                           tags: Optional[List[str]] = None) -> List[TextContent]:
        """Start analysis run"""
        try:
            api_url = f"{self.BASE_URL}/analysis/start"
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
                "params": {"model": model, "persist": persist, "tags": tags or []}
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
        # This would need to be implemented in the analysis_control API
        return [TextContent(type="text", text=json.dumps({
            "ok": False,
            "data": None,
            "errors": [{"code": "not_implemented", "message": "Analysis history not yet implemented"}]
        }, indent=2))]

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