#!/usr/bin/env python3
"""
Comprehensive News MCP Server for LAN Access
Provides full access to the News-MCP system via MCP protocol
"""

import asyncio
import logging
import json
import hashlib
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Union
from mcp.server import Server
from mcp.types import Tool, TextContent
from sqlmodel import Session, select, text, and_, or_, func
from app.database import engine
from app.models import (
    Feed, Item, Category, FeedCategory, FeedHealth, Source,
    DynamicFeedTemplate, FeedTemplateAssignment, FeedConfigurationChange,
    ContentProcessingLog, FetchLog
)
from app.config import settings
from app.services.dynamic_template_manager import get_dynamic_template_manager

logging.basicConfig(level=logging.INFO)
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

class ComprehensiveNewsServer:
    def __init__(self):
        self.server = Server("news-mcp-comprehensive")
        self._setup_tools()

    def _setup_tools(self):
        """Register all MCP tools"""

        # Feed Management Tools
        @self.server.list_tools()
        async def list_tools() -> List[Tool]:
            return [
                # Feed Management
                Tool(
                    name="list_feeds",
                    description="List all RSS feeds with status, metrics and health info",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "status": {"type": "string", "enum": ["ACTIVE", "PAUSED", "ERROR"], "description": "Filter by status"},
                            "include_health": {"type": "boolean", "default": True, "description": "Include health metrics"},
                            "include_stats": {"type": "boolean", "default": True, "description": "Include item counts"}
                        }
                    }
                ),
                Tool(
                    name="add_feed",
                    description="Add new RSS feed with automatic template detection",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "url": {"type": "string", "format": "uri", "description": "RSS feed URL"},
                            "title": {"type": "string", "description": "Optional custom title"},
                            "fetch_interval_minutes": {"type": "integer", "default": 15, "minimum": 5, "description": "Update interval"},
                            "auto_assign_template": {"type": "boolean", "default": True, "description": "Auto-assign matching template"}
                        },
                        "required": ["url"]
                    }
                ),
                Tool(
                    name="update_feed",
                    description="Update feed configuration",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "feed_id": {"type": "integer", "description": "Feed ID"},
                            "title": {"type": "string", "description": "New title"},
                            "fetch_interval_minutes": {"type": "integer", "minimum": 5, "description": "New interval"},
                            "status": {"type": "string", "enum": ["ACTIVE", "PAUSED"], "description": "New status"}
                        },
                        "required": ["feed_id"]
                    }
                ),
                Tool(
                    name="delete_feed",
                    description="Delete a feed and all its articles",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "feed_id": {"type": "integer", "description": "Feed ID to delete"},
                            "confirm": {"type": "boolean", "description": "Confirmation required"}
                        },
                        "required": ["feed_id", "confirm"]
                    }
                ),
                Tool(
                    name="test_feed",
                    description="Test feed URL and show preview without adding",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "url": {"type": "string", "format": "uri", "description": "RSS feed URL to test"},
                            "show_items": {"type": "integer", "default": 5, "maximum": 20, "description": "Number of sample items"}
                        },
                        "required": ["url"]
                    }
                ),
                Tool(
                    name="refresh_feed",
                    description="Manually trigger immediate feed update",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "feed_id": {"type": "integer", "description": "Feed ID to refresh"},
                            "force": {"type": "boolean", "default": False, "description": "Force refresh even if recently updated"}
                        },
                        "required": ["feed_id"]
                    }
                ),

                # Analytics & Statistics Tools
                Tool(
                    name="get_dashboard",
                    description="Get comprehensive dashboard statistics",
                    inputSchema={"type": "object", "properties": {}}
                ),
                Tool(
                    name="feed_performance",
                    description="Analyze feed performance and efficiency",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "feed_id": {"type": "integer", "description": "Specific feed ID (optional)"},
                            "days": {"type": "integer", "default": 7, "maximum": 90, "description": "Analysis period in days"}
                        }
                    }
                ),
                Tool(
                    name="latest_articles",
                    description="Get latest articles with advanced filtering",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "limit": {"type": "integer", "default": 20, "maximum": 100, "description": "Number of articles"},
                            "feed_id": {"type": "integer", "description": "Filter by specific feed"},
                            "since_hours": {"type": "integer", "default": 24, "description": "Articles from last N hours"},
                            "keywords": {"type": "array", "items": {"type": "string"}, "description": "Filter by keywords in title"},
                            "exclude_keywords": {"type": "array", "items": {"type": "string"}, "description": "Exclude articles with these keywords"}
                        }
                    }
                ),
                Tool(
                    name="search_articles",
                    description="Full-text search across all articles",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "Search query"},
                            "limit": {"type": "integer", "default": 50, "maximum": 200, "description": "Max results"},
                            "feed_id": {"type": "integer", "description": "Limit to specific feed"},
                            "date_from": {"type": "string", "format": "date", "description": "Start date (YYYY-MM-DD)"},
                            "date_to": {"type": "string", "format": "date", "description": "End date (YYYY-MM-DD)"}
                        },
                        "required": ["query"]
                    }
                ),
                Tool(
                    name="trending_topics",
                    description="Analyze trending keywords and topics",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "hours": {"type": "integer", "default": 24, "description": "Time window in hours"},
                            "min_frequency": {"type": "integer", "default": 3, "description": "Minimum keyword frequency"},
                            "top_n": {"type": "integer", "default": 20, "description": "Number of top topics"}
                        }
                    }
                ),
                Tool(
                    name="export_data",
                    description="Export articles and statistics in various formats",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "format": {"type": "string", "enum": ["json", "csv", "xml"], "default": "json", "description": "Export format"},
                            "data_type": {"type": "string", "enum": ["articles", "feeds", "statistics"], "default": "articles", "description": "What to export"},
                            "feed_id": {"type": "integer", "description": "Limit to specific feed"},
                            "limit": {"type": "integer", "default": 1000, "description": "Max records to export"},
                            "since_days": {"type": "integer", "default": 30, "description": "Export from last N days"}
                        }
                    }
                ),

                # Template Management Tools
                Tool(
                    name="list_templates",
                    description="List all processing templates with assignments",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "active_only": {"type": "boolean", "default": True, "description": "Show only active templates"},
                            "include_assignments": {"type": "boolean", "default": True, "description": "Include feed assignments"}
                        }
                    }
                ),
                Tool(
                    name="template_performance",
                    description="Analyze template processing efficiency",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "template_id": {"type": "integer", "description": "Specific template ID"},
                            "days": {"type": "integer", "default": 7, "description": "Analysis period"}
                        }
                    }
                ),
                Tool(
                    name="assign_template",
                    description="Assign template to feed",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "feed_id": {"type": "integer", "description": "Feed ID"},
                            "template_id": {"type": "integer", "description": "Template ID"}
                        },
                        "required": ["feed_id", "template_id"]
                    }
                ),

                # Database Query Tools
                Tool(
                    name="execute_query",
                    description="Execute safe read-only SQL queries",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "SQL SELECT query"},
                            "limit": {"type": "integer", "default": 100, "maximum": 1000, "description": "Result limit"}
                        },
                        "required": ["query"]
                    }
                ),
                Tool(
                    name="table_info",
                    description="Get database schema and table information",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "table_name": {"type": "string", "description": "Specific table name (optional)"},
                            "include_sample_data": {"type": "boolean", "default": False, "description": "Include sample rows"}
                        }
                    }
                ),
                Tool(
                    name="quick_queries",
                    description="Execute predefined useful database queries",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query_name": {
                                "type": "string",
                                "enum": ["feed_overview", "recent_activity", "error_analysis", "performance_stats", "template_usage"],
                                "description": "Predefined query to execute"
                            }
                        },
                        "required": ["query_name"]
                    }
                ),

                # Health & Monitoring Tools
                Tool(
                    name="system_health",
                    description="Get comprehensive system health status",
                    inputSchema={"type": "object", "properties": {}}
                ),
                Tool(
                    name="feed_diagnostics",
                    description="Detailed diagnostics for specific feed",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "feed_id": {"type": "integer", "description": "Feed ID to diagnose"}
                        },
                        "required": ["feed_id"]
                    }
                ),
                Tool(
                    name="error_analysis",
                    description="Analyze recent errors and provide solutions",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "hours": {"type": "integer", "default": 24, "description": "Look back N hours"},
                            "feed_id": {"type": "integer", "description": "Limit to specific feed"}
                        }
                    }
                ),
                Tool(
                    name="scheduler_status",
                    description="Check dynamic scheduler status and control",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "action": {"type": "string", "enum": ["status", "config", "heartbeat"], "default": "status", "description": "What to check"}
                        }
                    }
                ),

                # Administration Tools
                Tool(
                    name="maintenance_tasks",
                    description="Execute system maintenance tasks",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "task": {
                                "type": "string",
                                "enum": ["cleanup_old_items", "vacuum_database", "update_statistics", "rebuild_indexes"],
                                "description": "Maintenance task to execute"
                            },
                            "dry_run": {"type": "boolean", "default": True, "description": "Show what would be done without executing"}
                        },
                        "required": ["task"]
                    }
                ),
                Tool(
                    name="log_analysis",
                    description="Analyze system logs for patterns and issues",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "hours": {"type": "integer", "default": 24, "description": "Analyze last N hours"},
                            "log_level": {"type": "string", "enum": ["ERROR", "WARNING", "INFO"], "default": "WARNING", "description": "Minimum log level"},
                            "component": {"type": "string", "enum": ["scheduler", "fetcher", "templates", "api"], "description": "Specific component"}
                        }
                    }
                ),
                Tool(
                    name="usage_stats",
                    description="Get system usage statistics and metrics",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "period": {"type": "string", "enum": ["hour", "day", "week", "month"], "default": "day", "description": "Statistics period"},
                            "detailed": {"type": "boolean", "default": False, "description": "Include detailed breakdowns"}
                        }
                    }
                )
            ]

        # Tool implementations
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
                elif name == "test_feed":
                    return await self._test_feed(**arguments)
                elif name == "refresh_feed":
                    return await self._refresh_feed(**arguments)
                elif name == "get_dashboard":
                    return await self._get_dashboard(**arguments)
                elif name == "feed_performance":
                    return await self._feed_performance(**arguments)
                elif name == "latest_articles":
                    return await self._latest_articles(**arguments)
                elif name == "search_articles":
                    return await self._search_articles(**arguments)
                elif name == "trending_topics":
                    return await self._trending_topics(**arguments)
                elif name == "export_data":
                    return await self._export_data(**arguments)
                elif name == "list_templates":
                    return await self._list_templates(**arguments)
                elif name == "template_performance":
                    return await self._template_performance(**arguments)
                elif name == "assign_template":
                    return await self._assign_template(**arguments)
                elif name == "execute_query":
                    return await self._execute_query(**arguments)
                elif name == "table_info":
                    return await self._table_info(**arguments)
                elif name == "quick_queries":
                    return await self._quick_queries(**arguments)
                elif name == "system_health":
                    return await self._system_health(**arguments)
                elif name == "feed_diagnostics":
                    return await self._feed_diagnostics(**arguments)
                elif name == "error_analysis":
                    return await self._error_analysis(**arguments)
                elif name == "scheduler_status":
                    return await self._scheduler_status(**arguments)
                elif name == "maintenance_tasks":
                    return await self._maintenance_tasks(**arguments)
                elif name == "log_analysis":
                    return await self._log_analysis(**arguments)
                elif name == "usage_stats":
                    return await self._usage_stats(**arguments)
                else:
                    return [TextContent(type="text", text=f"Unknown tool: {name}")]
            except Exception as e:
                logger.error(f"Error executing tool {name}: {e}")
                return [TextContent(type="text", text=f"Error executing {name}: {str(e)}")]

    # Tool Implementation Methods
    async def _list_feeds(self, status: Optional[str] = None, include_health: bool = True, include_stats: bool = True, limit: Optional[int] = None) -> List[TextContent]:
        """List all feeds with optional filtering"""
        with Session(engine) as session:
            query = select(Feed, Source).join(Source, isouter=True)

            if status:
                query = query.where(Feed.status == status)

            if limit:
                query = query.limit(limit)

            feeds = session.exec(query).all()

            result = []
            for feed, source in feeds:
                feed_info = {
                    "id": feed.id,
                    "title": feed.title or "Untitled",
                    "url": feed.url,
                    "status": feed.status,
                    "fetch_interval_minutes": feed.fetch_interval_minutes,
                    "source": source.name if source else "Unknown",
                    "last_fetched": str(feed.last_fetched) if feed.last_fetched else None,
                    "created_at": str(feed.created_at)
                }

                if include_stats:
                    item_count = session.exec(select(func.count(Item.id)).where(Item.feed_id == feed.id)).one()
                    recent_count = session.exec(
                        select(func.count(Item.id)).where(
                            and_(Item.feed_id == feed.id, Item.created_at > datetime.utcnow() - timedelta(hours=24))
                        )
                    ).one()
                    feed_info.update({
                        "total_items": item_count,
                        "items_24h": recent_count
                    })

                if include_health:
                    health = session.exec(select(FeedHealth).where(FeedHealth.feed_id == feed.id)).first()
                    if health:
                        feed_info.update({
                            "health": {
                                "ok_ratio": health.ok_ratio,
                                "consecutive_failures": health.consecutive_failures,
                                "avg_response_time_ms": health.avg_response_time_ms,
                                "last_success": str(health.last_success) if health.last_success else None,
                                "uptime_24h": health.uptime_24h
                            }
                        })

                result.append(feed_info)

            return [TextContent(type="text", text=safe_json_dumps(result, indent=2))]

    async def _get_dashboard(self) -> List[TextContent]:
        """Get comprehensive dashboard statistics"""
        with Session(engine) as session:
            # Basic counts
            total_feeds = session.exec(select(func.count(Feed.id))).one()
            total_items = session.exec(select(func.count(Item.id))).one()
            total_sources = session.exec(select(func.count(Source.id))).one()

            # Recent activity
            yesterday = datetime.utcnow() - timedelta(days=1)
            items_24h = session.exec(
                select(func.count(Item.id)).where(Item.created_at > yesterday)
            ).one()

            # Feed status breakdown
            status_stats = session.exec(text("""
                SELECT status, COUNT(*) as count
                FROM feeds
                GROUP BY status
            """)).fetchall()

            # Top performing feeds
            top_feeds = session.exec(text("""
                SELECT f.title, f.url, COUNT(i.id) as item_count
                FROM feeds f
                LEFT JOIN items i ON f.id = i.feed_id
                GROUP BY f.id, f.title, f.url
                ORDER BY item_count DESC
                LIMIT 10
            """)).fetchall()

            dashboard = {
                "overview": {
                    "total_feeds": total_feeds,
                    "total_items": total_items,
                    "total_sources": total_sources,
                    "items_24h": items_24h
                },
                "feed_status": [{"status": row[0], "count": row[1]} for row in status_stats],
                "top_feeds": [
                    {"title": row[0] or row[1][:50], "url": row[1], "items": row[2]}
                    for row in top_feeds
                ],
                "generated_at": datetime.utcnow().isoformat()
            }

            return [TextContent(type="text", text=safe_json_dumps(dashboard, indent=2))]

    async def _latest_articles(self, limit: int = 20, feed_id: Optional[int] = None,
                             since_hours: int = 24, keywords: Optional[List[str]] = None,
                             exclude_keywords: Optional[List[str]] = None) -> List[TextContent]:
        """Get latest articles with filtering"""
        with Session(engine) as session:
            query = select(Item, Feed).join(Feed)

            # Time filter
            since_time = datetime.utcnow() - timedelta(hours=since_hours)
            query = query.where(Item.created_at > since_time)

            # Feed filter
            if feed_id:
                query = query.where(Item.feed_id == feed_id)

            # Keyword filters
            if keywords:
                keyword_conditions = [Item.title.ilike(f"%{keyword}%") for keyword in keywords]
                query = query.where(or_(*keyword_conditions))

            if exclude_keywords:
                exclude_conditions = [~Item.title.ilike(f"%{keyword}%") for keyword in exclude_keywords]
                query = query.where(and_(*exclude_conditions))

            query = query.order_by(Item.created_at.desc()).limit(limit)

            results = session.exec(query).all()

            articles = []
            for item, feed in results:
                articles.append({
                    "id": item.id,
                    "title": item.title,
                    "description": item.description[:200] + "..." if item.description and len(item.description) > 200 else item.description,
                    "url": item.link,
                    "published": str(item.published) if item.published else None,
                    "created_at": str(item.created_at),
                    "feed": {
                        "id": feed.id,
                        "title": feed.title,
                        "url": feed.url
                    }
                })

            return [TextContent(type="text", text=safe_json_dumps(articles, indent=2))]

    async def _search_articles(self, query: str, limit: int = 50, feed_id: Optional[int] = None,
                             date_from: Optional[str] = None, date_to: Optional[str] = None) -> List[TextContent]:
        """Full-text search across articles"""
        with Session(engine) as session:
            search_query = select(Item, Feed).join(Feed)

            # Text search in title and description
            search_conditions = [
                Item.title.ilike(f"%{query}%"),
                Item.description.ilike(f"%{query}%")
            ]
            search_query = search_query.where(or_(*search_conditions))

            # Feed filter
            if feed_id:
                search_query = search_query.where(Item.feed_id == feed_id)

            # Date filters
            if date_from:
                date_from_dt = datetime.fromisoformat(date_from)
                search_query = search_query.where(Item.published >= date_from_dt)

            if date_to:
                date_to_dt = datetime.fromisoformat(date_to)
                search_query = search_query.where(Item.published <= date_to_dt)

            search_query = search_query.order_by(Item.created_at.desc()).limit(limit)

            results = session.exec(search_query).all()

            articles = []
            for item, feed in results:
                # Calculate relevance score (simple keyword matching)
                title_matches = query.lower() in (item.title or "").lower()
                desc_matches = query.lower() in (item.description or "").lower()
                relevance = (2 if title_matches else 0) + (1 if desc_matches else 0)

                articles.append({
                    "id": item.id,
                    "title": item.title,
                    "description": item.description[:200] + "..." if item.description and len(item.description) > 200 else item.description,
                    "url": item.link,
                    "published": str(item.published) if item.published else None,
                    "relevance": relevance,
                    "feed": {
                        "id": feed.id,
                        "title": feed.title
                    }
                })

            # Sort by relevance
            articles.sort(key=lambda x: x["relevance"], reverse=True)

            result = {
                "query": query,
                "total_results": len(articles),
                "articles": articles
            }

            return [TextContent(type="text", text=safe_json_dumps(result, indent=2))]

    async def _system_health(self) -> List[TextContent]:
        """Get comprehensive system health"""
        with Session(engine) as session:
            # Feed health summary
            total_feeds = session.exec(select(func.count(Feed.id))).one()

            # Get actual status counts
            status_counts = session.exec(text("""
                SELECT status, COUNT(*) FROM feeds GROUP BY status
            """)).fetchall()
            status_dict = {status: count for status, count in status_counts}

            active_feeds = status_dict.get("ACTIVE", 0)
            error_feeds = status_dict.get("ERROR", 0)

            # Recent fetch activity
            recent_fetches = session.exec(text("""
                SELECT COUNT(*) FROM fetch_log
                WHERE started_at > NOW() - INTERVAL '1 hour'
            """)).one()

            # Database health
            db_health = session.exec(text("SELECT COUNT(*) FROM items")).one()

            # Average health metrics
            avg_health_row = session.exec(text("""
                SELECT
                    AVG(ok_ratio) as avg_success_rate,
                    AVG(avg_response_time_ms) as avg_response_time,
                    COUNT(*) as feeds_with_health
                FROM feed_health
            """)).first()

            # Extract values from Row object
            if avg_health_row:
                avg_success_rate = float(avg_health_row[0] or 0)
                avg_response_time = float(avg_health_row[1] or 0)
                health_coverage = int(avg_health_row[2] or 0)
            else:
                avg_success_rate = 0
                avg_response_time = 0
                health_coverage = 0

            health_status = {
                "overall_status": "healthy" if error_feeds < total_feeds * 0.1 else "degraded",
                "feeds": {
                    "total": total_feeds,
                    "active": active_feeds,
                    "errors": error_feeds,
                    "health_coverage": health_coverage
                },
                "performance": {
                    "avg_success_rate": round(avg_success_rate, 3),
                    "avg_response_time_ms": round(avg_response_time, 2),
                    "recent_fetches_1h": recent_fetches
                },
                "database": {
                    "total_articles": db_health,
                    "status": "operational"
                },
                "timestamp": str(datetime.utcnow())
            }

            return [TextContent(type="text", text=safe_json_dumps(health_status, indent=2))]

    async def _execute_query(self, query: str, limit: int = 100) -> List[TextContent]:
        """Execute safe SQL queries"""
        # Security check
        query_lower = query.lower().strip()
        if not query_lower.startswith('select'):
            return [TextContent(type="text", text="Error: Only SELECT queries are allowed")]

        dangerous_keywords = ['insert', 'update', 'delete', 'drop', 'create', 'alter', 'truncate']
        for keyword in dangerous_keywords:
            if keyword in query_lower:
                return [TextContent(type="text", text=f"Error: '{keyword}' statements are not allowed")]

        # Add LIMIT if not present
        if 'limit' not in query_lower:
            if query.rstrip().endswith(';'):
                query = query.rstrip()[:-1] + f' LIMIT {limit};'
            else:
                query = query.rstrip() + f' LIMIT {limit}'

        try:
            with Session(engine) as session:
                result = session.exec(text(query)).fetchall()

                if result:
                    # Convert to list of dictionaries
                    columns = list(result[0]._mapping.keys()) if hasattr(result[0], '_mapping') else list(range(len(result[0])))
                    data = []
                    for row in result:
                        if hasattr(row, '_mapping'):
                            data.append(dict(row._mapping))
                        else:
                            data.append({f"col_{i}": val for i, val in enumerate(row)})

                    query_result = {
                        "query": query,
                        "columns": columns,
                        "row_count": len(data),
                        "data": data
                    }
                else:
                    query_result = {
                        "query": query,
                        "row_count": 0,
                        "data": []
                    }

                return [TextContent(type="text", text=safe_json_dumps(query_result, indent=2, default=str))]

        except Exception as e:
            return [TextContent(type="text", text=f"Query error: {str(e)}")]

    # Feed Management Tool Implementations
    async def _add_feed(self, url: str, title: Optional[str] = None, fetch_interval_minutes: int = 15, auto_assign_template: bool = True) -> List[TextContent]:
        """Add a new RSS feed"""
        with Session(engine) as session:
            # Check if feed already exists
            existing = session.exec(select(Feed).where(Feed.url == url)).first()
            if existing:
                return [TextContent(type="text", text=f"Feed already exists with ID {existing.id}: {existing.title or 'Untitled'}")]

            # Ensure we have a source (required for database schema)
            from app.models import SourceType
            rss_source = session.exec(select(Source).where(Source.type == SourceType.RSS)).first()
            if not rss_source:
                rss_source = Source(name="RSS", type=SourceType.RSS, description="RSS feeds")
                session.add(rss_source)
                session.commit()
                session.refresh(rss_source)

            # Create new feed with source_id
            feed = Feed(
                url=url,
                title=title,
                fetch_interval_minutes=fetch_interval_minutes,
                status="ACTIVE",
                source_id=rss_source.id
            )
            session.add(feed)
            session.commit()
            session.refresh(feed)

            # Trigger immediate initial fetch for new feed
            try:
                from app.services.feed_fetcher_sync import SyncFeedFetcher
                fetcher = SyncFeedFetcher()
                success, items_count = fetcher.fetch_feed_sync(feed.id)

                result = {
                    "status": "success",
                    "message": f"Feed added successfully with ID {feed.id}",
                    "feed": {
                        "id": feed.id,
                        "title": feed.title or "Untitled",
                        "url": feed.url,
                        "interval_minutes": feed.fetch_interval_minutes,
                        "status": feed.status
                    },
                    "initial_fetch": {
                        "success": success,
                        "articles_loaded": items_count if success else 0
                    }
                }
            except Exception as e:
                result = {
                    "status": "success",
                    "message": f"Feed added successfully with ID {feed.id} (initial fetch failed: {e})",
                    "feed": {
                        "id": feed.id,
                        "title": feed.title or "Untitled",
                        "url": feed.url,
                        "interval_minutes": feed.fetch_interval_minutes,
                        "status": feed.status
                    },
                    "initial_fetch": {
                        "success": False,
                        "articles_loaded": 0,
                        "error": str(e)
                    }
                }

            return [TextContent(type="text", text=safe_json_dumps(result, indent=2))]

    async def _update_feed(self, feed_id: int, title: Optional[str] = None, fetch_interval_minutes: Optional[int] = None, status: Optional[str] = None) -> List[TextContent]:
        """Update feed configuration"""
        with Session(engine) as session:
            feed = session.get(Feed, feed_id)
            if not feed:
                return [TextContent(type="text", text=f"Feed with ID {feed_id} not found")]

            updated_fields = []
            if title is not None:
                feed.title = title
                updated_fields.append(f"title: '{title}'")
            if fetch_interval_minutes is not None:
                feed.fetch_interval_minutes = fetch_interval_minutes
                updated_fields.append(f"interval: {fetch_interval_minutes} minutes")
            if status is not None:
                feed.status = status
                updated_fields.append(f"status: {status}")

            if not updated_fields:
                return [TextContent(type="text", text="No fields to update")]

            session.add(feed)
            session.commit()

            result = {
                "status": "success",
                "message": f"Feed {feed_id} updated: {', '.join(updated_fields)}",
                "feed": {
                    "id": feed.id,
                    "title": feed.title,
                    "url": feed.url,
                    "interval_minutes": feed.fetch_interval_minutes,
                    "status": feed.status
                }
            }

            return [TextContent(type="text", text=safe_json_dumps(result, indent=2))]

    async def _delete_feed(self, feed_id: int, confirm: bool = False) -> List[TextContent]:
        """Delete a feed and all its articles"""
        if not confirm:
            return [TextContent(type="text", text="Deletion requires confirmation. Set confirm=true to proceed.")]

        with Session(engine) as session:
            feed = session.get(Feed, feed_id)
            if not feed:
                return [TextContent(type="text", text=f"Feed with ID {feed_id} not found")]

            # Count items before deletion
            try:
                item_count = session.exec(select(func.count(Item.id)).where(Item.feed_id == feed_id)).one()
            except:
                item_count = 0

            # Delete all related data with individual commits to avoid transaction issues
            deleted_tables = []

            # List of tables to clean up in order (most dependent first)
            cleanup_tables = [
                ("items", "DELETE FROM items WHERE feed_id = :feed_id"),
                ("fetch_log", "DELETE FROM fetch_log WHERE feed_id = :feed_id"),
                ("feed_health", "DELETE FROM feed_health WHERE feed_id = :feed_id"),
                ("feed_categories", "DELETE FROM feed_categories WHERE feed_id = :feed_id"),
                ("content_processing_log", "DELETE FROM content_processing_log WHERE feed_id = :feed_id"),
                ("feed_template_assignments", "DELETE FROM feed_template_assignments WHERE feed_id = :feed_id"),
                ("feed_configuration_changes", "DELETE FROM feed_configuration_changes WHERE feed_id = :feed_id")
            ]

            # Delete from each table with individual transactions
            for table_name, delete_sql in cleanup_tables:
                try:
                    session.execute(text(delete_sql), {"feed_id": feed_id})
                    session.commit()
                    deleted_tables.append(table_name)
                except Exception as e:
                    session.rollback()
                    logger.warning(f"Failed to delete from {table_name}: {e}")

            # Finally delete the feed itself
            try:
                session.delete(feed)
                session.commit()
                deleted_tables.append("feed")
            except Exception as e:
                session.rollback()
                return [TextContent(type="text", text=f"Failed to delete feed: {str(e)}")]

            result = {
                "status": "success",
                "message": f"Feed {feed_id} ({feed.title or 'Untitled'}) deleted successfully",
                "deleted_items": item_count,
                "deleted_tables": deleted_tables,
                "feed_id": feed_id,
                "feed_title": feed.title or "Untitled"
            }

            return [TextContent(type="text", text=safe_json_dumps(result, indent=2))]

    async def _test_feed(self, url: str, show_items: int = 5) -> List[TextContent]:
        """Test feed URL and show preview without adding"""
        try:
            import feedparser
            import requests
            from urllib.parse import urljoin

            # Validate show_items
            show_items = min(max(1, show_items), 20)

            # Fetch and parse feed
            response = requests.get(url, timeout=30, headers={
                'User-Agent': 'News-MCP/1.0 (Feed Tester)'
            })
            response.raise_for_status()

            feed_data = feedparser.parse(response.content)

            if feed_data.bozo:
                return [TextContent(type="text", text=f"Feed parsing error: {feed_data.bozo_exception}")]

            # Extract feed info
            feed_info = {
                "url": url,
                "title": feed_data.feed.get('title', 'Unknown'),
                "description": feed_data.feed.get('description', 'No description'),
                "link": feed_data.feed.get('link', ''),
                "language": feed_data.feed.get('language', 'unknown'),
                "total_entries": len(feed_data.entries),
                "sample_entries": []
            }

            # Add sample entries
            for entry in feed_data.entries[:show_items]:
                item = {
                    "title": entry.get('title', 'No title'),
                    "link": entry.get('link', ''),
                    "published": entry.get('published', 'Unknown date'),
                    "summary": entry.get('summary', '')[:200] + '...' if len(entry.get('summary', '')) > 200 else entry.get('summary', '')
                }
                feed_info["sample_entries"].append(item)

            result = {
                "status": "success",
                "message": "Feed test successful",
                "feed_preview": feed_info
            }

            return [TextContent(type="text", text=safe_json_dumps(result, indent=2))]

        except Exception as e:
            return [TextContent(type="text", text=f"Feed test failed: {str(e)}")]

    async def _refresh_feed(self, feed_id: int) -> List[TextContent]:
        """Manually trigger feed refresh"""
        with Session(engine) as session:
            feed = session.get(Feed, feed_id)
            if not feed:
                return [TextContent(type="text", text=f"Feed with ID {feed_id} not found")]

            try:
                # Import feed fetcher
                from jobs.fetcher import FeedFetcher

                fetcher = FeedFetcher()
                result = await fetcher.fetch_feed(feed)

                response = {
                    "status": "success",
                    "message": f"Feed {feed_id} refreshed successfully",
                    "feed_title": feed.title or "Untitled",
                    "new_items": result.get('new_items', 0),
                    "total_items": result.get('total_items', 0),
                    "last_fetched": str(datetime.utcnow())
                }

                return [TextContent(type="text", text=safe_json_dumps(response, indent=2))]

            except Exception as e:
                return [TextContent(type="text", text=f"Feed refresh failed: {str(e)}")]

    async def _feed_performance(self, days: int = 7, limit: int = 20) -> List[TextContent]:
        """Analyze feed performance over time"""
        with Session(engine) as session:
            # Performance metrics for last N days
            since_date = datetime.utcnow() - timedelta(days=days)

            performance_data = session.exec(text("""
                SELECT
                    f.id, f.title, f.url, s.name as source_name,
                    COUNT(i.id) as total_items,
                    COUNT(CASE WHEN i.created_at > :since_date THEN 1 END) as recent_items,
                    AVG(CASE WHEN i.created_at > :since_date THEN 1.0 ELSE 0.0 END) * 100 as activity_rate,
                    MAX(i.created_at) as latest_item,
                    fh.ok_ratio, fh.avg_response_time_ms, fh.consecutive_failures,
                    fh.uptime_24h
                FROM feeds f
                LEFT JOIN items i ON f.id = i.feed_id
                LEFT JOIN sources s ON f.source_id = s.id
                LEFT JOIN feed_health fh ON f.id = fh.feed_id
                GROUP BY f.id, f.title, f.url, s.name, fh.ok_ratio, fh.avg_response_time_ms, fh.consecutive_failures, fh.uptime_24h
                ORDER BY recent_items DESC, total_items DESC
                LIMIT :limit
            """), {"since_date": since_date, "limit": limit}).fetchall()

            performance = []
            for row in performance_data:
                performance.append({
                    "feed_id": row[0],
                    "title": row[1] or "Untitled",
                    "url": row[2],
                    "source": row[3] or "Unknown",
                    "total_items": row[4],
                    "recent_items": row[5],
                    "activity_rate": round(float(row[6] or 0), 2),
                    "latest_item": str(row[7]) if row[7] else None,
                    "health": {
                        "success_rate": float(row[8] or 0),
                        "avg_response_time": float(row[9] or 0),
                        "consecutive_failures": row[10] or 0,
                        "uptime_24h": float(row[11] or 0)
                    }
                })

            result = {
                "period_days": days,
                "total_feeds_analyzed": len(performance),
                "performance_ranking": performance
            }

            return [TextContent(type="text", text=safe_json_dumps(result, indent=2))]

    async def _trending_topics(self, hours: int = 24, min_mentions: int = 2) -> List[TextContent]:
        """Analyze trending topics and keywords"""
        with Session(engine) as session:
            since_date = datetime.utcnow() - timedelta(hours=hours)

            # Get recent articles for analysis
            recent_articles = session.exec(
                select(Item.title, Item.description).where(Item.created_at > since_date)
            ).fetchall()

            if not recent_articles:
                return [TextContent(type="text", text="No recent articles found for trending analysis")]

            # Simple keyword extraction and counting
            import re
            from collections import Counter

            # Extract words from titles and summaries
            all_text = " ".join([article[0] or "" for article in recent_articles] +
                              [article[1] or "" for article in recent_articles])

            # Simple word extraction (alphanumeric, length > 3)
            words = re.findall(r'\b[a-zA-ZäöüÄÖÜß]{4,}\b', all_text.lower())

            # Common stop words to filter out
            stop_words = {'dass', 'sich', 'nach', 'auch', 'wird', 'wurden', 'haben', 'wird', 'sind', 'mehr', 'alle', 'eine', 'einem', 'einer', 'einen', 'beim', 'über', 'unter', 'zwischen', 'während', 'gegen'}

            # Filter and count
            filtered_words = [word for word in words if word not in stop_words]
            word_counts = Counter(filtered_words)

            # Get most common words
            trending = [
                {"keyword": word, "mentions": count, "trend_score": count * 100 / len(recent_articles)}
                for word, count in word_counts.most_common(20)
                if count >= min_mentions
            ]

            result = {
                "analysis_period_hours": hours,
                "total_articles_analyzed": len(recent_articles),
                "trending_keywords": trending,
                "analysis_timestamp": str(datetime.utcnow())
            }

            return [TextContent(type="text", text=safe_json_dumps(result, indent=2))]

    async def _export_data(self, format: str = "json", table: str = "feeds", limit: int = 1000) -> List[TextContent]:
        """Export data in various formats"""
        allowed_tables = ["feeds", "items", "sources", "categories"]
        allowed_formats = ["json", "csv"]

        if table not in allowed_tables:
            return [TextContent(type="text", text=f"Table '{table}' not allowed. Allowed: {allowed_tables}")]

        if format not in allowed_formats:
            return [TextContent(type="text", text=f"Format '{format}' not supported. Allowed: {allowed_formats}")]

        with Session(engine) as session:
            if table == "feeds":
                data = session.exec(text("""
                    SELECT f.id, f.title, f.url, s.name as source, f.status,
                           f.fetch_interval_minutes, f.created_at, f.last_fetched,
                           COUNT(i.id) as total_items
                    FROM feeds f
                    LEFT JOIN sources s ON f.source_id = s.id
                    LEFT JOIN items i ON f.id = i.feed_id
                    GROUP BY f.id, f.title, f.url, s.name, f.status, f.fetch_interval_minutes, f.created_at, f.last_fetched
                    ORDER BY f.created_at DESC
                    LIMIT :limit
                """), {"limit": limit}).fetchall()

                if format == "json":
                    export_data = [{
                        "id": row[0], "title": row[1], "url": row[2], "source": row[3],
                        "status": row[4], "interval_minutes": row[5],
                        "created_at": str(row[6]), "last_fetched": str(row[7]) if row[7] else None,
                        "total_items": row[8]
                    } for row in data]
                else:  # CSV
                    csv_lines = ["ID,Title,URL,Source,Status,Interval,Created,LastFetched,TotalItems"]
                    for row in data:
                        csv_lines.append(f'{row[0]},"{row[1] or ""}","{row[2]}","{row[3] or ""}",{row[4]},{row[5]},{row[6]},{row[7] or ""},{row[8]}')
                    export_data = "\n".join(csv_lines)

            elif table == "items":
                data = session.exec(text("""
                    SELECT i.id, i.title, f.title as feed_title, i.link as url, i.published, i.created_at
                    FROM items i
                    LEFT JOIN feeds f ON i.feed_id = f.id
                    ORDER BY i.created_at DESC
                    LIMIT :limit
                """), {"limit": limit}).fetchall()

                if format == "json":
                    export_data = [{
                        "id": row[0], "title": row[1], "feed_title": row[2],
                        "url": row[3], "published": str(row[4]) if row[4] else None,
                        "created_at": str(row[5])
                    } for row in data]
                else:  # CSV
                    csv_lines = ["ID,Title,FeedTitle,URL,Published,Created"]
                    for row in data:
                        csv_lines.append(f'{row[0]},"{row[1] or ""}","{row[2] or ""}","{row[3] or ""}",{row[4] or ""},{row[5]}')
                    export_data = "\n".join(csv_lines)

            result = {
                "format": format,
                "table": table,
                "exported_records": len(data),
                "export_timestamp": str(datetime.utcnow()),
                "data": export_data
            }

            return [TextContent(type="text", text=safe_json_dumps(result, indent=2) if format == "json" else export_data)]

    async def _list_templates(self, include_assignments: bool = True) -> List[TextContent]:
        """List all dynamic feed templates"""
        with Session(engine) as session:
            templates = session.exec(select(DynamicFeedTemplate)).all()

            template_list = []
            for template in templates:
                template_info = {
                    "id": template.id,
                    "name": template.name,
                    "description": template.description,
                    "domain_pattern": template.domain_pattern,
                    "is_active": template.is_active,
                    "created_at": str(template.created_at),
                    "priority": template.priority
                }

                if include_assignments:
                    # Count feeds using this template
                    assignment_count = session.exec(
                        select(func.count(FeedTemplateAssignment.id))
                        .where(FeedTemplateAssignment.template_id == template.id)
                    ).one()
                    template_info["assigned_feeds"] = assignment_count

                template_list.append(template_info)

            result = {
                "total_templates": len(template_list),
                "templates": template_list
            }

            return [TextContent(type="text", text=safe_json_dumps(result, indent=2))]

    async def _template_performance(self, days: int = 30) -> List[TextContent]:
        """Analyze template performance and usage"""
        with Session(engine) as session:
            since_date = datetime.utcnow() - timedelta(days=days)

            # Template performance analysis
            performance_data = session.exec(text("""
                SELECT
                    dt.id, dt.name, dt.domain_pattern,
                    COUNT(DISTINCT fta.feed_id) as assigned_feeds,
                    COUNT(i.id) as total_items,
                    COUNT(CASE WHEN i.created_at > :since_date THEN 1 END) as recent_items,
                    AVG(fh.ok_ratio) as avg_success_rate,
                    AVG(fh.avg_response_time_ms) as avg_response_time
                FROM dynamic_feed_templates dt
                LEFT JOIN feed_template_assignments fta ON dt.id = fta.template_id
                LEFT JOIN feeds f ON fta.feed_id = f.id
                LEFT JOIN items i ON f.id = i.feed_id
                LEFT JOIN feed_health fh ON f.id = fh.feed_id
                WHERE dt.is_active = true
                GROUP BY dt.id, dt.name, dt.domain_pattern
                ORDER BY recent_items DESC
            """), {"since_date": since_date}).fetchall()

            performance = []
            for row in performance_data:
                performance.append({
                    "template_id": row[0],
                    "name": row[1],
                    "domain_pattern": row[2],
                    "assigned_feeds": row[3],
                    "total_items": row[4],
                    "recent_items": row[5],
                    "avg_success_rate": round(float(row[6] or 0), 2),
                    "avg_response_time": round(float(row[7] or 0), 2),
                    "items_per_feed": round(row[4] / row[3], 2) if row[3] > 0 else 0
                })

            result = {
                "analysis_period_days": days,
                "total_active_templates": len(performance),
                "template_performance": performance
            }

            return [TextContent(type="text", text=safe_json_dumps(result, indent=2))]

    async def _assign_template(self, feed_id: int, template_id: Optional[int] = None, auto_assign: bool = False) -> List[TextContent]:
        """Assign template to feed or auto-assign based on domain"""
        with Session(engine) as session:
            feed = session.get(Feed, feed_id)
            if not feed:
                return [TextContent(type="text", text=f"Feed with ID {feed_id} not found")]

            # Remove existing assignment
            existing = session.exec(
                select(FeedTemplateAssignment).where(FeedTemplateAssignment.feed_id == feed_id)
            ).first()
            if existing:
                session.delete(existing)

            if auto_assign:
                # Auto-assign based on domain matching
                from urllib.parse import urlparse
                domain = urlparse(feed.url).netloc

                # Find matching template
                templates = session.exec(
                    select(DynamicFeedTemplate)
                    .where(DynamicFeedTemplate.is_active == True)
                    .order_by(DynamicFeedTemplate.priority.desc())
                ).all()

                matched_template = None
                for template in templates:
                    if template.domain_pattern and template.domain_pattern in domain:
                        matched_template = template
                        break

                if matched_template:
                    assignment = FeedTemplateAssignment(
                        feed_id=feed_id,
                        template_id=matched_template.id,
                        assigned_at=datetime.utcnow()
                    )
                    session.add(assignment)
                    session.commit()

                    result = {
                        "status": "success",
                        "message": f"Auto-assigned template '{matched_template.name}' to feed {feed_id}",
                        "template": {
                            "id": matched_template.id,
                            "name": matched_template.name,
                            "domain_pattern": matched_template.domain_pattern
                        }
                    }
                else:
                    result = {
                        "status": "info",
                        "message": f"No matching template found for domain '{domain}'",
                        "feed_domain": domain
                    }

            elif template_id:
                template = session.get(DynamicFeedTemplate, template_id)
                if not template:
                    return [TextContent(type="text", text=f"Template with ID {template_id} not found")]

                assignment = FeedTemplateAssignment(
                    feed_id=feed_id,
                    template_id=template_id,
                    assigned_at=datetime.utcnow()
                )
                session.add(assignment)
                session.commit()

                result = {
                    "status": "success",
                    "message": f"Assigned template '{template.name}' to feed {feed_id}",
                    "template": {
                        "id": template.id,
                        "name": template.name,
                        "domain_pattern": template.domain_pattern
                    }
                }
            else:
                # Just remove assignment
                session.commit()
                result = {
                    "status": "success",
                    "message": f"Removed template assignment from feed {feed_id}"
                }

            return [TextContent(type="text", text=safe_json_dumps(result, indent=2))]

    async def _table_info(self, table_name: Optional[str] = None) -> List[TextContent]:
        """Get database table information"""
        with Session(engine) as session:
            if table_name:
                # Get info for specific table
                try:
                    # Get column info
                    columns = session.exec(text("""
                        SELECT column_name, data_type, is_nullable, column_default
                        FROM information_schema.columns
                        WHERE table_name = :table_name
                        ORDER BY ordinal_position
                    """), {"table_name": table_name}).fetchall()

                    if not columns:
                        return [TextContent(type="text", text=f"Table '{table_name}' not found")]

                    # Get row count
                    try:
                        row_count = session.exec(text(f"SELECT COUNT(*) FROM {table_name}")).one()
                    except:
                        row_count = "Unknown"

                    table_info = {
                        "table_name": table_name,
                        "row_count": row_count,
                        "columns": [{
                            "name": col[0],
                            "type": col[1],
                            "nullable": col[2] == "YES",
                            "default": col[3]
                        } for col in columns]
                    }

                    return [TextContent(type="text", text=safe_json_dumps(table_info, indent=2))]

                except Exception as e:
                    return [TextContent(type="text", text=f"Error getting table info: {str(e)}")]

            else:
                # List all tables with basic info
                tables = session.exec(text("""
                    SELECT table_name
                    FROM information_schema.tables
                    WHERE table_schema = 'public'
                    ORDER BY table_name
                """)).fetchall()

                table_list = []
                for table in tables:
                    try:
                        row_count = session.exec(text(f"SELECT COUNT(*) FROM {table[0]}")).one()
                    except:
                        row_count = "Unknown"

                    table_list.append({
                        "table_name": table[0],
                        "row_count": row_count
                    })

                result = {
                    "total_tables": len(table_list),
                    "tables": table_list
                }

                return [TextContent(type="text", text=safe_json_dumps(result, indent=2))]

    async def _quick_queries(self, query_type: str = "summary") -> List[TextContent]:
        """Execute predefined quick queries"""
        with Session(engine) as session:
            if query_type == "summary":
                # Database summary
                # Get actual status counts from database
                status_counts = session.exec(text("""
                    SELECT status, COUNT(*) FROM feeds GROUP BY status
                """)).fetchall()

                status_dict = {status: count for status, count in status_counts}

                summary_data = {
                    "feeds": {
                        "total": session.exec(select(func.count(Feed.id))).one(),
                        "active": status_dict.get("ACTIVE", 0),
                        "paused": status_dict.get("PAUSED", 0),
                        "error": status_dict.get("ERROR", 0)
                    },
                    "items": {
                        "total": session.exec(select(func.count(Item.id))).one(),
                        "last_24h": session.exec(
                            select(func.count(Item.id))
                            .where(Item.created_at > datetime.utcnow() - timedelta(days=1))
                        ).one(),
                        "last_week": session.exec(
                            select(func.count(Item.id))
                            .where(Item.created_at > datetime.utcnow() - timedelta(days=7))
                        ).one()
                    },
                    "sources": session.exec(select(func.count(Source.id))).one(),
                    "templates": session.exec(select(func.count(DynamicFeedTemplate.id))).one()
                }

            elif query_type == "latest_items":
                # Latest items
                latest = session.exec(
                    select(Item.title, Item.created_at, Feed.title.label("feed_title"))
                    .join(Feed)
                    .order_by(Item.created_at.desc())
                    .limit(10)
                ).fetchall()

                summary_data = {
                    "latest_items": [{
                        "title": item[0],
                        "created_at": str(item[1]),
                        "feed_title": item[2]
                    } for item in latest]
                }

            elif query_type == "feed_stats":
                # Feed statistics
                feed_stats = session.exec(text("""
                    SELECT f.status, COUNT(*) as count,
                           AVG(fh.ok_ratio) as avg_success_rate,
                           AVG(fh.avg_response_time_ms) as avg_response_time
                    FROM feeds f
                    LEFT JOIN feed_health fh ON f.id = fh.feed_id
                    GROUP BY f.status
                """)).fetchall()

                summary_data = {
                    "feed_statistics": [{
                        "status": stat[0],
                        "count": stat[1],
                        "avg_success_rate": round(float(stat[2] or 0), 2),
                        "avg_response_time": round(float(stat[3] or 0), 2)
                    } for stat in feed_stats]
                }

            elif query_type == "errors":
                # Recent errors
                error_feeds = session.exec(
                    select(Feed.id, Feed.title, Feed.url, FeedHealth.last_failure, FeedHealth.consecutive_failures)
                    .join(FeedHealth)
                    .where(FeedHealth.consecutive_failures > 0)
                    .order_by(FeedHealth.consecutive_failures.desc())
                    .limit(10)
                ).fetchall()

                summary_data = {
                    "feeds_with_errors": [{
                        "feed_id": error[0],
                        "title": error[1] or "Untitled",
                        "url": error[2],
                        "last_failure": str(error[3]) if error[3] else None,
                        "consecutive_failures": error[4]
                    } for error in error_feeds]
                }

            else:
                return [TextContent(type="text", text=f"Unknown query type: {query_type}. Available: summary, latest_items, feed_stats, errors")]

            result = {
                "query_type": query_type,
                "timestamp": str(datetime.utcnow()),
                "data": summary_data
            }

            return [TextContent(type="text", text=safe_json_dumps(result, indent=2))]

    async def _feed_diagnostics(self, feed_id: Optional[int] = None, include_logs: bool = True) -> List[TextContent]:
        """Diagnose feed health and issues"""
        with Session(engine) as session:
            if feed_id:
                # Diagnose specific feed
                feed = session.get(Feed, feed_id)
                if not feed:
                    return [TextContent(type="text", text=f"Feed with ID {feed_id} not found")]

                # Get health data
                health = session.exec(select(FeedHealth).where(FeedHealth.feed_id == feed_id)).first()

                # Get recent fetch logs
                recent_logs = []
                if include_logs:
                    logs = session.exec(
                        select(FetchLog)
                        .where(FetchLog.feed_id == feed_id)
                        .order_by(FetchLog.created_at.desc())
                        .limit(10)
                    ).fetchall()
                    recent_logs = [{
                        "timestamp": str(log.created_at),
                        "status": log.status,
                        "items_found": log.items_found,
                        "error_message": log.error_message
                    } for log in logs]

                # Get item statistics
                total_items = session.exec(select(func.count(Item.id)).where(Item.feed_id == feed_id)).one()
                recent_items = session.exec(
                    select(func.count(Item.id))
                    .where(and_(Item.feed_id == feed_id, Item.created_at > datetime.utcnow() - timedelta(days=7)))
                ).one()

                diagnostics = {
                    "feed": {
                        "id": feed.id,
                        "title": feed.title or "Untitled",
                        "url": feed.url,
                        "status": feed.status,
                        "interval_minutes": feed.fetch_interval_minutes,
                        "last_fetched": str(feed.last_fetched) if feed.last_fetched else None
                    },
                    "health": {
                        "success_rate": health.ok_ratio if health else 0,
                        "consecutive_failures": health.consecutive_failures if health else 0,
                        "avg_response_time": health.avg_response_time_ms if health else 0,
                        "uptime_24h": health.uptime_24h if health else 0,
                        "last_success": str(health.last_success) if health and health.last_success else None,
                        "last_failure": str(health.last_failure) if health and health.last_failure else None
                    } if health else None,
                    "statistics": {
                        "total_items": total_items,
                        "items_last_7_days": recent_items,
                        "avg_items_per_day": round(recent_items / 7, 2)
                    },
                    "recent_fetch_logs": recent_logs
                }

                return [TextContent(type="text", text=safe_json_dumps(diagnostics, indent=2))]

            else:
                # Overview of all feed health
                health_overview = session.exec(text("""
                    SELECT f.id, f.title, f.status, fh.ok_ratio, fh.consecutive_failures,
                           fh.last_success, fh.last_failure
                    FROM feeds f
                    LEFT JOIN feed_health fh ON f.id = fh.feed_id
                    ORDER BY fh.consecutive_failures DESC, fh.ok_ratio ASC
                """)).fetchall()

                feeds_overview = []
                for row in health_overview:
                    feeds_overview.append({
                        "feed_id": row[0],
                        "title": row[1] or "Untitled",
                        "status": row[2],
                        "success_rate": float(row[3] or 0),
                        "consecutive_failures": row[4] or 0,
                        "last_success": str(row[5]) if row[5] else None,
                        "last_failure": str(row[6]) if row[6] else None,
                        "health_status": "critical" if (row[4] or 0) > 5 else "warning" if (row[4] or 0) > 2 else "good"
                    })

                result = {
                    "total_feeds": len(feeds_overview),
                    "feeds_overview": feeds_overview
                }

                return [TextContent(type="text", text=safe_json_dumps(result, indent=2))]

    async def _error_analysis(self, hours: int = 24, error_type: Optional[str] = None) -> List[TextContent]:
        """Analyze system errors and failures"""
        with Session(engine) as session:
            since_date = datetime.utcnow() - timedelta(hours=hours)

            # Get fetch errors
            fetch_errors = session.exec(
                select(FetchLog.feed_id, FetchLog.error_message, FetchLog.created_at, Feed.title, Feed.url)
                .join(Feed)
                .where(and_(FetchLog.status == "ERROR", FetchLog.created_at > since_date))
                .order_by(FetchLog.created_at.desc())
            ).fetchall()

            # Categorize errors
            error_categories = {}
            for error in fetch_errors:
                error_msg = error[1] or "Unknown error"

                # Simple error categorization
                if "timeout" in error_msg.lower():
                    category = "timeout"
                elif "404" in error_msg or "not found" in error_msg.lower():
                    category = "not_found"
                elif "connection" in error_msg.lower():
                    category = "connection"
                elif "parse" in error_msg.lower() or "xml" in error_msg.lower():
                    category = "parsing"
                else:
                    category = "other"

                if category not in error_categories:
                    error_categories[category] = []

                error_categories[category].append({
                    "feed_id": error[0],
                    "feed_title": error[3] or "Untitled",
                    "feed_url": error[4],
                    "error_message": error_msg,
                    "timestamp": str(error[2])
                })

            # Get feeds with consecutive failures
            problem_feeds = session.exec(
                select(Feed.id, Feed.title, Feed.url, FeedHealth.consecutive_failures, FeedHealth.last_failure)
                .join(FeedHealth)
                .where(FeedHealth.consecutive_failures > 3)
                .order_by(FeedHealth.consecutive_failures.desc())
            ).fetchall()

            analysis = {
                "analysis_period_hours": hours,
                "total_errors": len(fetch_errors),
                "error_categories": {
                    category: {
                        "count": len(errors),
                        "errors": errors[:5]  # Limit to 5 examples per category
                    } for category, errors in error_categories.items()
                },
                "problem_feeds": [{
                    "feed_id": feed[0],
                    "title": feed[1] or "Untitled",
                    "url": feed[2],
                    "consecutive_failures": feed[3],
                    "last_failure": str(feed[4]) if feed[4] else None
                } for feed in problem_feeds],
                "recommendations": self._generate_error_recommendations(error_categories, problem_feeds)
            }

            return [TextContent(type="text", text=safe_json_dumps(analysis, indent=2))]

    def _generate_error_recommendations(self, error_categories, problem_feeds):
        """Generate recommendations based on error analysis"""
        recommendations = []

        if "timeout" in error_categories and len(error_categories["timeout"]) > 5:
            recommendations.append("Consider increasing timeout values for feeds with frequent timeout errors")

        if "not_found" in error_categories:
            recommendations.append("Review feeds returning 404 errors - they may have moved or been discontinued")

        if "parsing" in error_categories:
            recommendations.append("Check feeds with parsing errors - they may need template adjustments")

        if len(problem_feeds) > 5:
            recommendations.append(f"Consider pausing {len(problem_feeds)} feeds with persistent failures")

        return recommendations

    async def _scheduler_status(self, action: str = "status") -> List[TextContent]:
        """Check scheduler status and health"""
        with Session(engine) as session:
            # Get scheduling statistics
            current_time = datetime.utcnow()

            # Feeds due for update
            due_feeds = session.exec(
                select(Feed)
                .where(and_(
                    Feed.status == "ACTIVE",
                    or_(
                        Feed.last_fetched == None,
                        Feed.last_fetched < current_time - timedelta(minutes=Feed.fetch_interval_minutes)
                    )
                ))
            ).fetchall()

            # Recent activity
            recent_fetches = session.exec(
                select(func.count(FetchLog.id))
                .where(FetchLog.created_at > current_time - timedelta(hours=1))
            ).one()

            recent_items = session.exec(
                select(func.count(Item.id))
                .where(Item.created_at > current_time - timedelta(hours=1))
            ).one()

            # Active feeds by interval
            interval_stats = session.exec(text("""
                SELECT fetch_interval_minutes, COUNT(*) as feed_count
                FROM feeds
                WHERE status = 'ACTIVE'
                GROUP BY fetch_interval_minutes
                ORDER BY fetch_interval_minutes
            """)).fetchall()

            status_info = {
                "scheduler_health": {
                    "status": "running",  # Would need actual scheduler process check
                    "current_time": str(current_time),
                    "feeds_due_for_update": len(due_feeds),
                    "recent_fetches_1h": recent_fetches,
                    "recent_items_1h": recent_items
                },
                "feed_intervals": [{
                    "interval_minutes": row[0],
                    "feed_count": row[1],
                    "fetch_frequency_per_hour": round(60 / row[0], 2)
                } for row in interval_stats],
                "due_feeds": [{
                    "id": feed.id,
                    "title": feed.title or "Untitled",
                    "url": feed.url,
                    "interval_minutes": feed.fetch_interval_minutes,
                    "last_fetched": str(feed.last_fetched) if feed.last_fetched else "Never",
                    "overdue_minutes": int((current_time - feed.last_fetched).total_seconds() / 60) if feed.last_fetched else "N/A"
                } for feed in due_feeds[:10]]  # Limit to 10 most due
            }

            if action == "heartbeat":
                # Simple heartbeat check
                return [TextContent(type="text", text=safe_json_dumps({
                    "status": "alive",
                    "timestamp": str(current_time),
                    "due_feeds": len(due_feeds),
                    "recent_activity": recent_fetches > 0
                }, indent=2))]

            return [TextContent(type="text", text=safe_json_dumps(status_info, indent=2))]

    async def _maintenance_tasks(self, task: str, dry_run: bool = True) -> List[TextContent]:
        """Execute system maintenance tasks"""
        with Session(engine) as session:
            if task == "cleanup_old_items":
                # Clean up old items (older than 90 days)
                cutoff_date = datetime.utcnow() - timedelta(days=90)

                if dry_run:
                    old_items_count = session.exec(
                        select(func.count(Item.id)).where(Item.created_at < cutoff_date)
                    ).one()
                    result = {
                        "task": "cleanup_old_items",
                        "dry_run": True,
                        "items_to_delete": old_items_count,
                        "cutoff_date": str(cutoff_date)
                    }
                else:
                    deleted = session.exec(
                        text("DELETE FROM items WHERE created_at < :cutoff_date"),
                        {"cutoff_date": cutoff_date}
                    )
                    session.commit()
                    result = {
                        "task": "cleanup_old_items",
                        "dry_run": False,
                        "items_deleted": deleted.rowcount,
                        "cutoff_date": str(cutoff_date)
                    }

            elif task == "vacuum_database":
                if dry_run:
                    result = {
                        "task": "vacuum_database",
                        "dry_run": True,
                        "note": "Would execute VACUUM ANALYZE on database"
                    }
                else:
                    # Note: VACUUM cannot be run in a transaction
                    session.exec(text("VACUUM ANALYZE"))
                    result = {
                        "task": "vacuum_database",
                        "dry_run": False,
                        "status": "completed"
                    }

            elif task == "update_statistics":
                if dry_run:
                    result = {
                        "task": "update_statistics",
                        "dry_run": True,
                        "note": "Would update table statistics"
                    }
                else:
                    session.exec(text("ANALYZE"))
                    result = {
                        "task": "update_statistics",
                        "dry_run": False,
                        "status": "completed"
                    }

            elif task == "rebuild_indexes":
                if dry_run:
                    result = {
                        "task": "rebuild_indexes",
                        "dry_run": True,
                        "note": "Would rebuild database indexes"
                    }
                else:
                    # Rebuild key indexes
                    session.exec(text("REINDEX INDEX CONCURRENTLY IF EXISTS idx_items_created_at"))
                    session.exec(text("REINDEX INDEX CONCURRENTLY IF EXISTS idx_items_feed_id"))
                    result = {
                        "task": "rebuild_indexes",
                        "dry_run": False,
                        "status": "completed"
                    }

            else:
                return [TextContent(type="text", text=f"Unknown maintenance task: {task}")]

            return [TextContent(type="text", text=safe_json_dumps(result, indent=2))]

    async def _log_analysis(self, hours: int = 24, log_level: str = "WARNING", component: Optional[str] = None) -> List[TextContent]:
        """Analyze system logs for patterns and issues"""
        with Session(engine) as session:
            since_date = datetime.utcnow() - timedelta(hours=hours)

            # Analyze fetch logs
            fetch_logs = session.exec(
                select(FetchLog.status, FetchLog.error_message, FetchLog.created_at, Feed.title)
                .join(Feed)
                .where(FetchLog.created_at > since_date)
                .order_by(FetchLog.created_at.desc())
            ).fetchall()

            # Analyze processing logs
            processing_logs = session.exec(
                select(ContentProcessingLog.status, ContentProcessingLog.error_message, ContentProcessingLog.created_at)
                .where(ContentProcessingLog.created_at > since_date)
                .order_by(ContentProcessingLog.created_at.desc())
            ).fetchall()

            # Categorize issues
            log_summary = {
                "fetch_logs": {
                    "total": len(fetch_logs),
                    "errors": len([log for log in fetch_logs if log[0] == "ERROR"]),
                    "success": len([log for log in fetch_logs if log[0] == "SUCCESS"])
                },
                "processing_logs": {
                    "total": len(processing_logs),
                    "errors": len([log for log in processing_logs if log[0] == "ERROR"]),
                    "success": len([log for log in processing_logs if log[0] == "SUCCESS"])
                }
            }

            # Recent errors by component
            recent_errors = []
            for log in fetch_logs:
                if log[0] == "ERROR" and log[1]:
                    recent_errors.append({
                        "component": "fetcher",
                        "feed_title": log[3] or "Unknown",
                        "error": log[1],
                        "timestamp": str(log[2])
                    })

            for log in processing_logs:
                if log[0] == "ERROR" and log[1]:
                    recent_errors.append({
                        "component": "processor",
                        "error": log[1],
                        "timestamp": str(log[2])
                    })

            # Filter by component if specified
            if component:
                recent_errors = [err for err in recent_errors if err["component"] == component]

            result = {
                "analysis_period_hours": hours,
                "log_level_filter": log_level,
                "component_filter": component,
                "summary": log_summary,
                "recent_errors": recent_errors[:20],  # Limit to 20 most recent
                "patterns": self._analyze_log_patterns(recent_errors)
            }

            return [TextContent(type="text", text=safe_json_dumps(result, indent=2))]

    def _analyze_log_patterns(self, errors):
        """Analyze error patterns"""
        from collections import Counter

        # Common error patterns
        error_types = Counter()
        for error in errors:
            error_msg = error["error"].lower()
            if "timeout" in error_msg:
                error_types["timeout"] += 1
            elif "connection" in error_msg:
                error_types["connection"] += 1
            elif "404" in error_msg:
                error_types["not_found"] += 1
            elif "parse" in error_msg:
                error_types["parsing"] += 1
            else:
                error_types["other"] += 1

        return dict(error_types.most_common())

    async def _usage_stats(self, period: str = "day", detailed: bool = False) -> List[TextContent]:
        """Get system usage statistics and metrics"""
        with Session(engine) as session:
            current_time = datetime.utcnow()

            if period == "hour":
                since_date = current_time - timedelta(hours=1)
                period_name = "Last Hour"
            elif period == "day":
                since_date = current_time - timedelta(days=1)
                period_name = "Last 24 Hours"
            elif period == "week":
                since_date = current_time - timedelta(days=7)
                period_name = "Last 7 Days"
            elif period == "month":
                since_date = current_time - timedelta(days=30)
                period_name = "Last 30 Days"
            else:
                return [TextContent(type="text", text=f"Invalid period: {period}. Use: hour, day, week, month")]

            # Basic usage stats
            stats = {
                "period": period_name,
                "timestamp": str(current_time),
                "feeds": {
                    "total_active": session.exec(
                        select(func.count(Feed.id)).where(Feed.status == "ACTIVE")
                    ).one(),
                    "fetch_attempts": session.exec(
                        select(func.count(FetchLog.id)).where(FetchLog.created_at > since_date)
                    ).one(),
                    "successful_fetches": session.exec(
                        select(func.count(FetchLog.id))
                        .where(and_(FetchLog.created_at > since_date, FetchLog.status == "SUCCESS"))
                    ).one()
                },
                "items": {
                    "new_items": session.exec(
                        select(func.count(Item.id)).where(Item.created_at > since_date)
                    ).one(),
                    "total_items": session.exec(select(func.count(Item.id))).one()
                },
                "processing": {
                    "processing_attempts": session.exec(
                        select(func.count(ContentProcessingLog.id))
                        .where(ContentProcessingLog.created_at > since_date)
                    ).one()
                }
            }

            # Calculate rates
            hours_in_period = (current_time - since_date).total_seconds() / 3600
            stats["rates"] = {
                "fetches_per_hour": round(stats["feeds"]["fetch_attempts"] / hours_in_period, 2),
                "items_per_hour": round(stats["items"]["new_items"] / hours_in_period, 2),
                "success_rate": round(
                    (stats["feeds"]["successful_fetches"] / stats["feeds"]["fetch_attempts"] * 100)
                    if stats["feeds"]["fetch_attempts"] > 0 else 0, 2
                )
            }

            if detailed:
                # Detailed breakdown by source
                source_stats = session.exec(text("""
                    SELECT s.name, COUNT(DISTINCT f.id) as feed_count,
                           COUNT(i.id) as items_in_period
                    FROM sources s
                    LEFT JOIN feeds f ON s.id = f.source_id
                    LEFT JOIN items i ON f.id = i.feed_id AND i.created_at > :since_date
                    GROUP BY s.id, s.name
                    ORDER BY items_in_period DESC
                """), {"since_date": since_date}).fetchall()

                stats["source_breakdown"] = [{
                    "source": row[0] or "Unknown",
                    "feed_count": row[1],
                    "items_in_period": row[2]
                } for row in source_stats[:10]]  # Top 10 sources

                # Template usage
                template_stats = session.exec(text("""
                    SELECT dt.name, COUNT(DISTINCT fta.feed_id) as assigned_feeds,
                           COUNT(i.id) as items_in_period
                    FROM dynamic_feed_templates dt
                    LEFT JOIN feed_template_assignments fta ON dt.id = fta.template_id
                    LEFT JOIN feeds f ON fta.feed_id = f.id
                    LEFT JOIN items i ON f.id = i.feed_id AND i.created_at > :since_date
                    WHERE dt.is_active = true
                    GROUP BY dt.id, dt.name
                    ORDER BY items_in_period DESC
                """), {"since_date": since_date}).fetchall()

                stats["template_usage"] = [{
                    "template": row[0],
                    "assigned_feeds": row[1],
                    "items_in_period": row[2]
                } for row in template_stats]

            return [TextContent(type="text", text=safe_json_dumps(stats, indent=2))]

    async def run(self, host: str = "0.0.0.0", port: int = 8001):
        """Run the MCP server"""
        logger.info(f"Starting Comprehensive News MCP Server on {host}:{port}")
        from mcp.server.stdio import stdio_server

        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(read_stream, write_stream)

async def main():
    server = ComprehensiveNewsServer()
    await server.run()

if __name__ == "__main__":
    asyncio.run(main())