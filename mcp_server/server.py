import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from mcp.server import Server
from mcp.types import Tool, TextContent
from sqlmodel import Session, select, and_, or_
from app.database import engine
from app.models import Feed, Item, Category, FeedCategory, FeedHealth, Source
from app.config import settings

logger = logging.getLogger(__name__)

class NewsServer:
    def __init__(self):
        self.server = Server("news-mcp")
        self._setup_tools()

    def _setup_tools(self):
        @self.server.list_tools()
        async def list_tools() -> List[Tool]:
            return [
                Tool(
                    name="list_feeds",
                    description="List RSS feeds with optional filtering by tags/categories",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "tags": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Filter by category tags"
                            },
                            "status": {
                                "type": "string",
                                "enum": ["active", "inactive", "error"],
                                "description": "Filter by feed status"
                            }
                        }
                    }
                ),
                Tool(
                    name="add_feed",
                    description="Add a new RSS feed",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "url": {
                                "type": "string",
                                "format": "uri",
                                "description": "RSS feed URL"
                            },
                            "categories": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Category names for the feed"
                            },
                            "title": {
                                "type": "string",
                                "description": "Optional feed title"
                            },
                            "fetch_interval_minutes": {
                                "type": "integer",
                                "minimum": 5,
                                "default": 60,
                                "description": "Fetch interval in minutes"
                            }
                        },
                        "required": ["url"]
                    }
                ),
                Tool(
                    name="fetch_latest",
                    description="Fetch latest news items",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "limit": {
                                "type": "integer",
                                "minimum": 1,
                                "maximum": 100,
                                "default": 20,
                                "description": "Number of items to fetch"
                            },
                            "categories": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Filter by category names"
                            },
                            "since_hours": {
                                "type": "integer",
                                "minimum": 1,
                                "description": "Only items from last N hours"
                            }
                        }
                    }
                ),
                Tool(
                    name="search",
                    description="Search news items by query",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Search query"
                            },
                            "since_minutes": {
                                "type": "integer",
                                "minimum": 1,
                                "description": "Only items from last N minutes"
                            },
                            "categories": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Filter by category names"
                            },
                            "limit": {
                                "type": "integer",
                                "minimum": 1,
                                "maximum": 100,
                                "default": 20,
                                "description": "Number of results"
                            }
                        },
                        "required": ["query"]
                    }
                ),
                Tool(
                    name="feed_health",
                    description="Get health status of a specific feed",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "feed_id": {
                                "type": "integer",
                                "description": "Feed ID"
                            }
                        },
                        "required": ["feed_id"]
                    }
                ),
                Tool(
                    name="system_status",
                    description="Get overall system status and statistics",
                    inputSchema={
                        "type": "object",
                        "properties": {}
                    }
                )
            ]

        @self.server.call_tool()
        async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
            try:
                if name == "list_feeds":
                    return await self._list_feeds(**arguments)
                elif name == "add_feed":
                    return await self._add_feed(**arguments)
                elif name == "fetch_latest":
                    return await self._fetch_latest(**arguments)
                elif name == "search":
                    return await self._search(**arguments)
                elif name == "feed_health":
                    return await self._feed_health(**arguments)
                elif name == "system_status":
                    return await self._system_status()
                else:
                    return [TextContent(type="text", text=f"Unknown tool: {name}")]
            except Exception as e:
                logger.error(f"Error in tool {name}: {e}")
                return [TextContent(type="text", text=f"Error: {str(e)}")]

    async def _list_feeds(self, tags: Optional[List[str]] = None, status: Optional[str] = None) -> List[TextContent]:
        with Session(engine) as session:
            query = select(Feed)

            if tags:
                query = query.join(FeedCategory).join(Category).where(
                    Category.name.in_(tags)
                )

            if status:
                query = query.where(Feed.status == status)

            feeds = session.exec(query).all()

            if not feeds:
                return [TextContent(type="text", text="No feeds found")]

            result = "📡 RSS Feeds:\n\n"
            for feed in feeds:
                status_emoji = {"active": "✅", "inactive": "⏸️", "error": "❌"}.get(feed.status, "❓")
                result += f"{status_emoji} **{feed.title or 'Untitled'}**\n"
                result += f"   🔗 {feed.url}\n"
                result += f"   ⏱️ Every {feed.fetch_interval_minutes} minutes\n"
                if feed.last_fetched:
                    result += f"   📅 Last: {feed.last_fetched.strftime('%Y-%m-%d %H:%M')}\n"
                result += "\n"

            return [TextContent(type="text", text=result)]

    async def _add_feed(self, url: str, categories: Optional[List[str]] = None,
                       title: Optional[str] = None, fetch_interval_minutes: int = 60) -> List[TextContent]:
        with Session(engine) as session:
            existing = session.exec(select(Feed).where(Feed.url == url)).first()
            if existing:
                return [TextContent(type="text", text=f"❌ Feed already exists: {url}")]

            rss_source = session.exec(select(Source).where(Source.type == "rss")).first()
            if not rss_source:
                rss_source = Source(name="RSS", type="rss", description="RSS feeds")
                session.add(rss_source)
                session.commit()
                session.refresh(rss_source)

            feed = Feed(
                url=url,
                title=title,
                fetch_interval_minutes=fetch_interval_minutes,
                source_id=rss_source.id
            )

            session.add(feed)
            session.commit()
            session.refresh(feed)

            if categories:
                for cat_name in categories:
                    category = session.exec(select(Category).where(Category.name == cat_name)).first()
                    if not category:
                        category = Category(name=cat_name)
                        session.add(category)
                        session.commit()
                        session.refresh(category)

                    feed_category = FeedCategory(feed_id=feed.id, category_id=category.id)
                    session.add(feed_category)

                session.commit()

            return [TextContent(type="text", text=f"✅ Feed added successfully: {feed.title or url}\nID: {feed.id}")]

    async def _fetch_latest(self, limit: int = 20, categories: Optional[List[str]] = None,
                           since_hours: Optional[int] = None) -> List[TextContent]:
        with Session(engine) as session:
            query = select(Item)

            if categories:
                query = query.join(Feed).join(FeedCategory).join(Category).where(
                    Category.name.in_(categories)
                )

            if since_hours:
                since_time = datetime.utcnow() - timedelta(hours=since_hours)
                query = query.where(Item.created_at >= since_time)

            query = query.order_by(Item.created_at.desc()).limit(limit)
            items = session.exec(query).all()

            if not items:
                return [TextContent(type="text", text="📰 No recent news items found")]

            result = f"📰 Latest {len(items)} News Items:\n\n"
            for item in items:
                result += f"**{item.title}**\n"
                result += f"🔗 {item.link}\n"
                if item.author:
                    result += f"✍️ {item.author}\n"
                if item.published:
                    result += f"📅 {item.published.strftime('%Y-%m-%d %H:%M')}\n"
                if item.description:
                    desc = item.description[:200] + "..." if len(item.description) > 200 else item.description
                    result += f"📝 {desc}\n"
                result += "\n"

            return [TextContent(type="text", text=result)]

    async def _search(self, query: str, since_minutes: Optional[int] = None,
                     categories: Optional[List[str]] = None, limit: int = 20) -> List[TextContent]:
        with Session(engine) as session:
            db_query = select(Item)

            if categories:
                db_query = db_query.join(Feed).join(FeedCategory).join(Category).where(
                    Category.name.in_(categories)
                )

            if since_minutes:
                since_time = datetime.utcnow() - timedelta(minutes=since_minutes)
                db_query = db_query.where(Item.created_at >= since_time)

            search_term = f"%{query}%"
            db_query = db_query.where(
                or_(
                    Item.title.contains(search_term),
                    Item.description.contains(search_term),
                    Item.content.contains(search_term)
                )
            )

            db_query = db_query.order_by(Item.created_at.desc()).limit(limit)
            items = session.exec(db_query).all()

            if not items:
                return [TextContent(type="text", text=f"🔍 No results found for: {query}")]

            result = f"🔍 Search Results for '{query}' ({len(items)} items):\n\n"
            for item in items:
                result += f"**{item.title}**\n"
                result += f"🔗 {item.link}\n"
                if item.published:
                    result += f"📅 {item.published.strftime('%Y-%m-%d %H:%M')}\n"
                if item.description:
                    desc = item.description[:150] + "..." if len(item.description) > 150 else item.description
                    result += f"📝 {desc}\n"
                result += "\n"

            return [TextContent(type="text", text=result)]

    async def _feed_health(self, feed_id: int) -> List[TextContent]:
        with Session(engine) as session:
            feed = session.get(Feed, feed_id)
            if not feed:
                return [TextContent(type="text", text=f"❌ Feed {feed_id} not found")]

            health = session.exec(select(FeedHealth).where(FeedHealth.feed_id == feed_id)).first()

            result = f"🏥 Health Status for Feed {feed_id}:\n\n"
            result += f"**{feed.title or 'Untitled'}**\n"
            result += f"🔗 {feed.url}\n"
            result += f"📊 Status: {feed.status}\n\n"

            if health:
                result += f"✅ Success Rate: {health.ok_ratio:.1%}\n"
                result += f"❌ Consecutive Failures: {health.consecutive_failures}\n"
                result += f"⏱️ Avg Response Time: {health.avg_response_time_ms or 0:.0f}ms\n"
                result += f"📈 24h Uptime: {health.uptime_24h:.1%}\n"
                result += f"📈 7d Uptime: {health.uptime_7d:.1%}\n"

                if health.last_success:
                    result += f"✅ Last Success: {health.last_success.strftime('%Y-%m-%d %H:%M')}\n"
                if health.last_failure:
                    result += f"❌ Last Failure: {health.last_failure.strftime('%Y-%m-%d %H:%M')}\n"
            else:
                result += "📊 No health data available yet\n"

            return [TextContent(type="text", text=result)]

    async def _system_status(self) -> List[TextContent]:
        with Session(engine) as session:
            total_feeds = len(session.exec(select(Feed)).all())
            active_feeds = len(session.exec(select(Feed).where(Feed.status == "active")).all())
            error_feeds = len(session.exec(select(Feed).where(Feed.status == "error")).all())

            recent_items = len(session.exec(
                select(Item).where(Item.created_at >= datetime.utcnow() - timedelta(hours=24))
            ).all())

            health_pct = (active_feeds / total_feeds * 100) if total_feeds > 0 else 100

            result = "🏥 System Status:\n\n"
            result += f"📡 Total Feeds: {total_feeds}\n"
            result += f"✅ Active Feeds: {active_feeds}\n"
            result += f"❌ Error Feeds: {error_feeds}\n"
            result += f"📊 Health: {health_pct:.1f}%\n"
            result += f"📰 Items (24h): {recent_items}\n"

            status_emoji = "✅" if health_pct >= 90 else "⚠️" if health_pct >= 70 else "❌"
            result += f"\n{status_emoji} Overall Status: {'Excellent' if health_pct >= 90 else 'Good' if health_pct >= 70 else 'Needs Attention'}\n"

            return [TextContent(type="text", text=result)]

    async def run(self):
        from mcp.server.stdio import stdio_server

        logger.info(f"Starting News MCP server on port {settings.mcp_port}")

        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(read_stream, write_stream, {})

if __name__ == "__main__":
    async def main():
        logging.basicConfig(level=settings.log_level)
        server = NewsServer()
        await server.run()

    asyncio.run(main())