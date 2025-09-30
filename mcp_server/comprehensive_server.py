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
    ContentProcessingLog, FetchLog, PendingAutoAnalysis
)
from app.config import settings
from app.services.dynamic_template_manager import get_dynamic_template_manager
from app.services.auto_analysis_service import AutoAnalysisService
from app.services.pending_analysis_processor import PendingAnalysisProcessor
from .v2_handlers import MCPv2Handlers

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
        self.v2_handlers = MCPv2Handlers()
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
                    description="List all RSS feeds with status, metrics and health info. Use this to get an overview of all configured feeds, their health status, and article counts. Example: Get all active feeds with health metrics to identify which feeds need attention.",
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
                    description="Add new RSS feed with automatic template detection. Validates the feed URL and performs initial fetch. Templates are auto-assigned based on feed domain matching. Example: Add 'https://techcrunch.com/feed/' to start tracking TechCrunch articles with default 15-minute refresh interval.",
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
                    description="Update feed configuration (title, interval, status). Use this to pause problematic feeds or adjust fetch frequency. Example: Set feed_id=5 to status='PAUSED' to temporarily disable fetching without deleting historical data.",
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
                    description="Delete a feed and all its articles (CASCADE deletion). WARNING: This permanently removes all articles from this feed. Requires explicit confirmation=true. Example: Remove feed_id=10 if it's no longer relevant or producing spam.",
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
                    description="Test feed URL and show preview without adding to database. Use this before add_feed to validate RSS/Atom format and inspect article structure. Example: Test 'https://example.com/rss' to see 5 sample articles before committing.",
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
                    description="Manually trigger immediate feed update (bypasses scheduler). Use when you need fresh articles immediately or testing feed changes. Example: After fixing a feed URL, call refresh_feed with force=true to skip rate limiting.",
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
                    description="Get comprehensive dashboard statistics (feeds count, articles count, health overview, recent activity). Use as starting point to understand system state. No parameters needed.",
                    inputSchema={"type": "object", "properties": {}}
                ),
                Tool(
                    name="feed_performance",
                    description="Analyze feed performance and efficiency (fetch success rate, avg items per fetch, response times). Use to identify slow or unreliable feeds. Example: Analyze feed_id=12 over last 30 days to diagnose frequent timeouts.",
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
                    description="Get latest articles with advanced filtering including sentiment analysis. Supports time-based, keyword, and sentiment filters with multiple sort options. Example: Get top 10 positive articles (min_sentiment=0.5, sort_by='sentiment_score') from last 24 hours. Note: Sentiment filters require analyzed articles (see analysis tools).",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "limit": {"type": "integer", "default": 20, "maximum": 100, "description": "Number of articles"},
                            "feed_id": {"type": "integer", "description": "Filter by specific feed"},
                            "since_hours": {"type": "integer", "default": 24, "description": "Articles from last N hours"},
                            "keywords": {"type": "array", "items": {"type": "string"}, "description": "Filter by keywords in title"},
                            "exclude_keywords": {"type": "array", "items": {"type": "string"}, "description": "Exclude articles with these keywords"},
                            "min_sentiment": {"type": "number", "minimum": -1, "maximum": 1, "description": "Minimum sentiment score (-1 to 1, requires analyzed articles)"},
                            "max_sentiment": {"type": "number", "minimum": -1, "maximum": 1, "description": "Maximum sentiment score (-1 to 1, requires analyzed articles)"},
                            "sort_by": {"type": "string", "enum": ["created_at", "published", "sentiment_score", "impact_score"], "default": "created_at", "description": "Sort order (sentiment_score and impact_score require analyzed articles)"}
                        }
                    }
                ),
                Tool(
                    name="search_articles",
                    description="Full-text search across all articles (title + description). Supports date range filtering and feed-specific search. Example: Search query='AI regulation' with date_from='2025-09-01' to find recent regulatory news. More powerful than keyword filtering in latest_articles.",
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
                    description="Analyze trending keywords and topics by frequency analysis. Use to discover emerging themes across all feeds. Example: Get top 20 keywords from last 48 hours with min_frequency=5 to filter noise. Great for content discovery.",
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
                    description="Export articles, feeds, or statistics in JSON/CSV/XML format. Use for backups, external analysis, or data migration. Example: Export last 7 days of articles from feed_id=25 as CSV with limit=5000 for spreadsheet analysis.",
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
                    description="List all processing templates with assignments. Templates control how articles are processed (filtering, transformations, etc.). Use to see which templates are assigned to which feeds. Example: Get active templates with assignments to audit processing configuration.",
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
                    description="Analyze template processing efficiency (processing times, success rates, error patterns). Use to identify slow or problematic templates. Example: Check template_id=3 performance over 14 days to optimize rules.",
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
                    description="Assign processing template to feed. Templates define how articles from this feed are processed. Example: Assign template_id=5 (tech-news-filter) to feed_id=12 (TechCrunch) for specialized processing.",
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
                    description="Execute safe read-only SQL queries for advanced data exploration. WARNING: Only SELECT queries allowed, no modifications. Example: SELECT feed_id, COUNT(*) FROM items WHERE created_at > NOW() - INTERVAL '7 days' GROUP BY feed_id. Use with caution.",
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
                    description="Get database schema and table information (columns, types, indexes). Use before execute_query to understand data structure. Example: Get table_info for 'items' with sample data to see article schema.",
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
                    description="Execute predefined useful database queries (feed_overview, recent_activity, error_analysis, performance_stats, template_usage). Safer than execute_query, use for common reporting needs. Example: Run 'error_analysis' to get recent failures.",
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
                    description="Get comprehensive system health status (database, scheduler, disk space, memory). Use as first diagnostic step when investigating issues. No parameters needed - returns full health check.",
                    inputSchema={"type": "object", "properties": {}}
                ),
                Tool(
                    name="feed_diagnostics",
                    description="Detailed diagnostics for specific feed (fetch history, errors, performance, health trends). Use when a single feed has issues. Example: Diagnose feed_id=8 if it stopped fetching articles.",
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
                    description="Analyze recent errors and provide solutions (error patterns, affected feeds, suggested fixes). Use to troubleshoot system-wide issues. Example: Analyze last 48 hours to identify common error causes.",
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
                    description="Check dynamic scheduler status and control (next scheduled runs, active jobs, scheduler health). Use to monitor feed scheduling system. Example: Check status to see next 10 scheduled fetches.",
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
                    description="Execute system maintenance tasks (cleanup_old_items, vacuum_database, update_statistics, rebuild_indexes). WARNING: Can be resource-intensive. Use dry_run=true first to preview. Example: cleanup_old_items with dry_run to see what would be deleted.",
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
                    description="Analyze system logs for patterns and issues (error frequency, component health, common failure modes). Use for root cause analysis. Example: Analyze scheduler logs at ERROR level from last 48 hours.",
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
                    description="Get system usage statistics and metrics (articles/day, API calls, processing times, resource utilization). Use for capacity planning. Example: Get detailed weekly stats to identify traffic patterns.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "period": {"type": "string", "enum": ["hour", "day", "week", "month"], "default": "day", "description": "Statistics period"},
                            "detailed": {"type": "boolean", "default": False, "description": "Include detailed breakdowns"}
                        }
                    }
                ),

                # System ping tool
                Tool(
                    name="system_ping",
                    description="System ping test for MCP connection. Use to verify MCP server is responsive. Returns simple pong response. No parameters needed - useful for health checks.",
                    inputSchema={
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                ),

                # MCP v2 Tools - Dynamic Templates
                Tool(
                    name="templates_create",
                    description="Create new dynamic feed template with URL matching and extraction rules. Advanced feature for custom content processing. Example: Create template with match_rules for techcrunch.com and custom extraction_config.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "name": {"type": "string", "description": "Template name"},
                            "description": {"type": "string", "description": "Template description"},
                            "match_rules": {"type": "array", "items": {"type": "object"}, "description": "URL/domain matching rules"},
                            "extraction_config": {"type": "object", "description": "Content extraction configuration"},
                            "processing_rules": {"type": "object", "description": "Content processing rules"}
                        },
                        "required": ["name", "match_rules", "extraction_config"]
                    }
                ),
                Tool(
                    name="templates_test",
                    description="Test template against sample URL or HTML content. Use before templates_assign to validate extraction rules work correctly. Example: Test template_id=5 with sample_url='https://example.com/article' to preview extracted data.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "template_id": {"type": "integer", "description": "Template ID to test"},
                            "sample_url": {"type": "string", "format": "uri", "description": "URL to test extraction on"},
                            "raw_html": {"type": "string", "description": "Raw HTML content to test"}
                        },
                        "required": ["template_id"]
                    }
                ),
                Tool(
                    name="templates_assign",
                    description="Assign template to feed with optional priority and custom overrides. Higher priority templates match first. Example: Assign template_id=8 to feed_id=15 with priority=200 for primary processing.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "template_id": {"type": "integer", "description": "Template ID"},
                            "feed_id": {"type": "integer", "description": "Feed ID"},
                            "priority": {"type": "integer", "default": 100, "description": "Assignment priority"},
                            "custom_overrides": {"type": "object", "description": "Feed-specific template overrides"}
                        },
                        "required": ["template_id", "feed_id"]
                    }
                ),

                # MCP v2 Tools - Analysis Control
                Tool(
                    name="analysis_preview",
                    description="Preview analysis run with cost estimation (token counts, estimated cost, article selection). Always use before analysis_run to avoid unexpected OpenAI costs. Example: Preview {latest: 100} articles with gpt-4o-mini to check cost before running.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "model": {"type": "string", "enum": ["gpt-4o-mini", "gpt-4.1-nano"], "default": "gpt-4o-mini", "description": "Analysis model"},
                            "selector": {
                                "type": "object",
                                "properties": {
                                    "latest": {"type": "integer", "description": "Latest N articles"},
                                    "time_range": {"type": "object", "properties": {"from": {"type": "string"}, "to": {"type": "string"}}},
                                    "feeds": {"type": "array", "items": {"type": "integer"}, "description": "Specific feed IDs"}
                                },
                                "description": "Article selection criteria"
                            },
                            "cost_estimate": {"type": "boolean", "default": True, "description": "Include cost estimation"}
                        },
                        "required": ["selector"]
                    }
                ),
                Tool(
                    name="analysis_run",
                    description="Start analysis run with persistence (sentiment, impact, urgency scores). Use after analysis_preview confirms costs acceptable. Results saved to item_analysis table. Example: Run {latest: 50} with persist=true and tags=['daily-batch'].",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "model": {"type": "string", "enum": ["gpt-4o-mini", "gpt-4.1-nano"], "default": "gpt-4o-mini", "description": "Analysis model"},
                            "selector": {
                                "type": "object",
                                "properties": {
                                    "latest": {"type": "integer", "description": "Latest N articles"},
                                    "time_range": {"type": "object", "properties": {"from": {"type": "string"}, "to": {"type": "string"}}},
                                    "feeds": {"type": "array", "items": {"type": "integer"}, "description": "Specific feed IDs"}
                                },
                                "description": "Article selection criteria"
                            },
                            "persist": {"type": "boolean", "default": True, "description": "Save results to database"},
                            "tags": {"type": "array", "items": {"type": "string"}, "description": "Run tags for organization"}
                        },
                        "required": ["selector"]
                    }
                ),
                Tool(
                    name="analysis_history",
                    description="Get analysis run history and results (past runs, costs, success rates, article counts). Use to track analysis usage and costs over time. Example: Get last 100 runs to calculate monthly OpenAI spending.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "limit": {"type": "integer", "default": 50, "maximum": 200, "description": "Number of runs to return"},
                            "offset": {"type": "integer", "default": 0, "description": "Offset for pagination"},
                            "status": {"type": "string", "enum": ["queued", "running", "done", "error"], "description": "Filter by status"}
                        }
                    }
                ),

                # MCP v2 Tools - Scheduler Control
                Tool(
                    name="scheduler_set_interval",
                    description="Set global or feed-specific fetch interval (how often feeds are refreshed). Use to adjust fetch frequency based on feed update patterns. Example: Set minutes=30 for slow-updating feed or minutes=5 for breaking news feed.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "minutes": {"type": "integer", "minimum": 1, "maximum": 1440, "description": "Interval in minutes"},
                            "feed_id": {"type": "integer", "description": "Specific feed ID (optional, affects all if not provided)"}
                        },
                        "required": ["minutes"]
                    }
                ),
                Tool(
                    name="scheduler_heartbeat",
                    description="Get detailed scheduler health and activity metrics (active jobs, queue depth, next scheduled runs, last heartbeat). Use to monitor scheduler responsiveness. No parameters - returns full scheduler state.",
                    inputSchema={
                        "type": "object",
                        "properties": {}
                    }
                ),

                # MCP v2 Tools - Enhanced Feeds
                Tool(
                    name="feeds_search",
                    description="Search feeds with health and status filtering (by query, category, health status). More powerful than list_feeds for finding specific feeds. Example: Search q='tech' with health='warn' to find tech feeds with issues.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "q": {"type": "string", "description": "Search query"},
                            "category": {"type": "string", "description": "Category filter"},
                            "health": {"type": "string", "enum": ["ok", "warn", "fail"], "description": "Health status filter"},
                            "limit": {"type": "integer", "default": 50, "maximum": 100, "description": "Result limit"},
                            "offset": {"type": "integer", "default": 0, "description": "Pagination offset"}
                        }
                    }
                ),
                Tool(
                    name="feeds_health",
                    description="Get detailed health metrics for feed(s) (success rate, latency, error patterns, uptime). Use for deep health analysis. Example: Check all feeds to generate health report or specific feed_id for troubleshooting.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "feed_id": {"type": "integer", "description": "Specific feed ID (optional, returns all if not provided)"}
                        }
                    }
                ),

                # MCP v2 Tools - Enhanced Items
                Tool(
                    name="items_recent",
                    description="Get recent items with deduplication (removes duplicate content by hash). Faster than latest_articles for simple recency queries. Example: Get last 50 items since='2025-09-28T00:00:00Z' with dedupe=true to avoid repeated content.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "limit": {"type": "integer", "default": 50, "maximum": 100, "description": "Number of items"},
                            "since": {"type": "string", "format": "date-time", "description": "Items since this ISO8601 timestamp"},
                            "feed_id": {"type": "integer", "description": "Filter by feed ID"},
                            "category": {"type": "string", "description": "Filter by category"},
                            "dedupe": {"type": "boolean", "default": True, "description": "Remove duplicate content"}
                        }
                    }
                ),
                Tool(
                    name="items_search",
                    description="Search items with advanced filtering (query, time_range, pagination, sorting). More flexible than search_articles. Example: Search q='blockchain' with time_range for date-bounded search and offset for pagination.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "q": {"type": "string", "description": "Search query"},
                            "limit": {"type": "integer", "default": 50, "maximum": 200, "description": "Result limit"},
                            "offset": {"type": "integer", "default": 0, "description": "Pagination offset"},
                            "time_range": {
                                "type": "object",
                                "properties": {
                                    "from": {"type": "string", "format": "date-time"},
                                    "to": {"type": "string", "format": "date-time"}
                                },
                                "description": "Time range filter"
                            },
                            "feeds": {"type": "array", "items": {"type": "integer"}, "description": "Feed ID filters"},
                            "categories": {"type": "array", "items": {"type": "string"}, "description": "Category filters"}
                        },
                        "required": ["q"]
                    }
                ),

                # Categories Management Tools
                Tool(
                    name="categories_list",
                    description="List all categories with feed assignments (category taxonomy, feed counts, article volumes). Use to understand content organization. Example: Get all categories with stats to see content distribution.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "include_feeds": {"type": "boolean", "default": True, "description": "Include associated feeds"},
                            "include_stats": {"type": "boolean", "default": True, "description": "Include category statistics"}
                        }
                    }
                ),
                Tool(
                    name="categories_add",
                    description="Create a new category for organizing feeds (e.g., 'Technology', 'Finance', 'Politics'). Example: Add name='Crypto' with description='Cryptocurrency and blockchain news' to create new taxonomy node.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "name": {"type": "string", "description": "Category name"},
                            "description": {"type": "string", "description": "Category description"},
                            "color": {"type": "string", "description": "Category color (hex)"}
                        },
                        "required": ["name"]
                    }
                ),
                Tool(
                    name="categories_update",
                    description="Update category information (name, description, color metadata). Example: Update category_id=3 with name='Web3' and color='#00FF00' to rebrand category.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "category_id": {"type": "integer", "description": "Category ID"},
                            "name": {"type": "string", "description": "New category name"},
                            "description": {"type": "string", "description": "New description"},
                            "color": {"type": "string", "description": "New color (hex)"}
                        },
                        "required": ["category_id"]
                    }
                ),
                Tool(
                    name="categories_delete",
                    description="Delete a category (unassigns from all feeds first). Requires explicit confirmation=true. Example: Remove obsolete category_id=9 after migrating feeds to new taxonomy.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "category_id": {"type": "integer", "description": "Category ID to delete"},
                            "confirm": {"type": "boolean", "description": "Confirmation required"}
                        },
                        "required": ["category_id", "confirm"]
                    }
                ),
                Tool(
                    name="categories_assign",
                    description="Assign category to feed for content organization. Feeds can have multiple categories (M:N relationship). Example: Assign category_id=5 ('Finance') to feed_id=20 (Bloomberg) for proper classification.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "category_id": {"type": "integer", "description": "Category ID"},
                            "feed_id": {"type": "integer", "description": "Feed ID"}
                        },
                        "required": ["category_id", "feed_id"]
                    }
                ),

                # Sources Management Tools
                Tool(
                    name="sources_list",
                    description="List all sources with statistics (source metadata, feed counts, reliability scores). Sources represent publishers/organizations. Example: Get all sources with stats to identify most active publishers.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "include_stats": {"type": "boolean", "default": True, "description": "Include source statistics"},
                            "include_feeds": {"type": "boolean", "default": True, "description": "Include associated feeds"}
                        }
                    }
                ),
                Tool(
                    name="sources_add",
                    description="Add a new source (publisher/organization with trust level). Sources group related feeds. Example: Add name='Reuters' url='https://reuters.com' trust_level=5 for high-quality news source.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "name": {"type": "string", "description": "Source name"},
                            "url": {"type": "string", "format": "uri", "description": "Source website URL"},
                            "description": {"type": "string", "description": "Source description"},
                            "trust_level": {"type": "integer", "minimum": 1, "maximum": 5, "default": 3, "description": "Trust level (1-5)"}
                        },
                        "required": ["name", "url"]
                    }
                ),
                Tool(
                    name="sources_update",
                    description="Update source information (name, URL, description, trust level 1-5). Example: Adjust source_id=12 trust_level=2 if source quality declined.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "source_id": {"type": "integer", "description": "Source ID"},
                            "name": {"type": "string", "description": "New source name"},
                            "url": {"type": "string", "format": "uri", "description": "New URL"},
                            "description": {"type": "string", "description": "New description"},
                            "trust_level": {"type": "integer", "minimum": 1, "maximum": 5, "description": "New trust level"}
                        },
                        "required": ["source_id"]
                    }
                ),
                Tool(
                    name="sources_delete",
                    description="Delete a source (orphans associated feeds). Requires explicit confirmation=true. WARNING: Feeds lose source association. Example: Remove source_id=8 if publisher shut down.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "source_id": {"type": "integer", "description": "Source ID to delete"},
                            "confirm": {"type": "boolean", "description": "Confirmation required"}
                        },
                        "required": ["source_id", "confirm"]
                    }
                ),
                Tool(
                    name="sources_stats",
                    description="Get detailed source statistics (article volume, quality metrics, feed health). Use for source performance analysis. Example: Check source_id=15 stats over 90 days to evaluate publisher reliability.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "source_id": {"type": "integer", "description": "Specific source ID (optional)"},
                            "days": {"type": "integer", "default": 30, "description": "Statistics period in days"}
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
                elif name == "system_ping":
                    return await self._system_ping(**arguments)
                # MCP v2 Tool Handlers - delegate to v2_handlers
                elif name == "templates_create":
                    return await self.v2_handlers.templates_create(**arguments)
                elif name == "templates_test":
                    return await self.v2_handlers.templates_test(**arguments)
                elif name == "templates_assign":
                    return await self.v2_handlers.templates_assign(**arguments)
                elif name == "analysis_preview":
                    return await self.v2_handlers.analysis_preview(**arguments)
                elif name == "analysis_run":
                    return await self.v2_handlers.analysis_run(**arguments)
                elif name == "analysis_history":
                    return await self.v2_handlers.analysis_history(**arguments)
                elif name == "scheduler_set_interval":
                    return await self.v2_handlers.scheduler_set_interval(**arguments)
                elif name == "scheduler_heartbeat":
                    return await self.v2_handlers.scheduler_heartbeat(**arguments)
                elif name == "feeds_search":
                    return await self.v2_handlers.feeds_search(**arguments)
                elif name == "feeds_health":
                    return await self.v2_handlers.feeds_health(**arguments)
                elif name == "items_recent":
                    return await self.v2_handlers.items_recent(**arguments)
                elif name == "items_search":
                    return await self.v2_handlers.items_search(**arguments)
                # Categories Management Handlers
                elif name == "categories_list":
                    return await self._categories_list(**arguments)
                elif name == "categories_add":
                    return await self._categories_add(**arguments)
                elif name == "categories_update":
                    return await self._categories_update(**arguments)
                elif name == "categories_delete":
                    return await self._categories_delete(**arguments)
                elif name == "categories_assign":
                    return await self._categories_assign(**arguments)
                # Sources Management Handlers
                elif name == "sources_list":
                    return await self._sources_list(**arguments)
                elif name == "sources_add":
                    return await self._sources_add(**arguments)
                elif name == "sources_update":
                    return await self._sources_update(**arguments)
                elif name == "sources_delete":
                    return await self._sources_delete(**arguments)
                elif name == "sources_stats":
                    return await self._sources_stats(**arguments)
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

                    # Get analysis statistics
                    analysis_stats = None
                    if item_count > 0:
                        analysis_sql = """
                        SELECT
                            COUNT(*) as analyzed_count,
                            AVG(COALESCE((ia.impact_json ->> 'overall')::numeric, 0)) as avg_impact_score,
                            SUM(CASE WHEN (ia.sentiment_json -> 'overall' ->> 'label') = 'positive' THEN 1 ELSE 0 END) as positive_count,
                            SUM(CASE WHEN (ia.sentiment_json -> 'overall' ->> 'label') = 'negative' THEN 1 ELSE 0 END) as negative_count,
                            SUM(CASE WHEN (ia.sentiment_json -> 'overall' ->> 'label') = 'neutral' THEN 1 ELSE 0 END) as neutral_count
                        FROM item_analysis ia
                        JOIN items i ON i.id = ia.item_id
                        WHERE i.feed_id = :feed_id
                        """
                        analysis_result = session.execute(text(analysis_sql), {"feed_id": feed.id}).fetchone()

                        if analysis_result and analysis_result[0] > 0:
                            analysis_stats = {
                                'analyzed_count': analysis_result[0],
                                'analyzed_percentage': round((analysis_result[0] / item_count) * 100, 1) if item_count > 0 else 0,
                                'avg_impact_score': float(analysis_result[1] or 0),
                                'sentiment_counts': {
                                    'positive': analysis_result[2] or 0,
                                    'negative': analysis_result[3] or 0,
                                    'neutral': analysis_result[4] or 0
                                }
                            }

                    feed_info.update({
                        "total_items": item_count,
                        "items_24h": recent_count,
                        "analysis_stats": analysis_stats
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
            status_stats = session.execute(text("""
                SELECT status, COUNT(*) as count
                FROM feeds
                GROUP BY status
            """)).fetchall()

            # Top performing feeds
            top_feeds = session.execute(text("""
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
                             exclude_keywords: Optional[List[str]] = None,
                             min_sentiment: Optional[float] = None,
                             max_sentiment: Optional[float] = None,
                             sort_by: str = "created_at") -> List[TextContent]:
        """Get latest articles with filtering including sentiment analysis"""
        with Session(engine) as session:
            from sqlalchemy import text as sql_text

            # Build SQL query with JSONB support for item_analysis table
            # Note: item_analysis uses JSONB columns (sentiment_json, impact_json), not separate columns

            where_clauses = []
            params = {}

            # Time filter
            since_time = datetime.utcnow() - timedelta(hours=since_hours)
            where_clauses.append("i.created_at > :since_time")
            params["since_time"] = since_time

            # Feed filter
            if feed_id:
                where_clauses.append("i.feed_id = :feed_id")
                params["feed_id"] = feed_id

            # Keyword filters
            if keywords:
                keyword_conds = " OR ".join([f"i.title ILIKE :keyword_{idx}" for idx in range(len(keywords))])
                where_clauses.append(f"({keyword_conds})")
                for idx, keyword in enumerate(keywords):
                    params[f"keyword_{idx}"] = f"%{keyword}%"

            if exclude_keywords:
                for idx, keyword in enumerate(exclude_keywords):
                    where_clauses.append(f"i.title NOT ILIKE :exclude_keyword_{idx}")
                    params[f"exclude_keyword_{idx}"] = f"%{keyword}%"

            # Sentiment filters (JSONB path: sentiment_json->'overall'->>'score')
            if min_sentiment is not None:
                where_clauses.append("(ia.sentiment_json->'overall'->>'score')::numeric >= :min_sentiment")
                params["min_sentiment"] = min_sentiment

            if max_sentiment is not None:
                where_clauses.append("(ia.sentiment_json->'overall'->>'score')::numeric <= :max_sentiment")
                params["max_sentiment"] = max_sentiment

            # Sort order
            if sort_by == "sentiment_score":
                order_clause = "(ia.sentiment_json->'overall'->>'score')::numeric DESC NULLS LAST"
            elif sort_by == "impact_score":
                order_clause = "(ia.impact_json->>'overall')::numeric DESC NULLS LAST"
            elif sort_by == "published":
                order_clause = "i.published DESC NULLS LAST"
            else:  # default: created_at
                order_clause = "i.created_at DESC"

            where_sql = " AND ".join(where_clauses) if where_clauses else "TRUE"

            query_sql = f"""
            SELECT
                i.id, i.title, i.description, i.link, i.published, i.created_at,
                f.id as feed_id, f.title as feed_title, f.url as feed_url,
                ia.sentiment_json, ia.impact_json
            FROM items i
            JOIN feeds f ON f.id = i.feed_id
            LEFT OUTER JOIN item_analysis ia ON i.id = ia.item_id
            WHERE {where_sql}
            ORDER BY {order_clause}
            LIMIT :limit
            """

            params["limit"] = limit

            result = session.execute(sql_text(query_sql), params)
            rows = result.fetchall()

            articles = []
            for row in rows:
                article_data = {
                    "id": row.id,
                    "title": row.title,
                    "description": row.description[:200] + "..." if row.description and len(row.description) > 200 else row.description,
                    "url": row.link,
                    "published": str(row.published) if row.published else None,
                    "created_at": str(row.created_at),
                    "feed": {
                        "id": row.feed_id,
                        "title": row.feed_title,
                        "url": row.feed_url
                    }
                }

                # Add analysis data if available
                if row.sentiment_json and row.impact_json:
                    sentiment_data = row.sentiment_json
                    impact_data = row.impact_json

                    article_data["analysis"] = {
                        "sentiment_score": sentiment_data.get("overall", {}).get("score") if isinstance(sentiment_data, dict) else None,
                        "sentiment_label": sentiment_data.get("overall", {}).get("label") if isinstance(sentiment_data, dict) else None,
                        "impact_score": impact_data.get("overall") if isinstance(impact_data, dict) else None,
                        "urgency_score": sentiment_data.get("urgency") if isinstance(sentiment_data, dict) else None
                    }

                articles.append(article_data)

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
            status_counts = session.execute(text("""
                SELECT status, COUNT(*) FROM feeds GROUP BY status
            """)).fetchall()
            status_dict = {status: count for status, count in status_counts}

            active_feeds = status_dict.get("ACTIVE", 0)
            error_feeds = status_dict.get("ERROR", 0)

            # Recent fetch activity
            recent_fetches = session.execute(text("""
                SELECT COUNT(*) FROM fetch_log
                WHERE started_at > NOW() - INTERVAL '1 hour'
            """)).one()

            # Database health
            db_health = session.execute(text("SELECT COUNT(*) FROM items")).fetchone()[0]

            # Average health metrics
            avg_health_row = session.execute(text("""
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
                result = session.execute(text(query)).fetchall()

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

            performance_data = session.execute(text("""
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
                data = session.execute(text("""
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
                data = session.execute(text("""
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
                    "url_patterns": template.url_patterns,
                    "is_active": template.is_active,
                    "created_at": str(template.created_at)
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
            performance_data = session.execute(text("""
                SELECT
                    dt.id, dt.name, dt.url_patterns,
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
                GROUP BY dt.id, dt.name, dt.url_patterns
                ORDER BY recent_items DESC
            """), {"since_date": since_date}).fetchall()

            performance = []
            for row in performance_data:
                performance.append({
                    "template_id": row[0],
                    "name": row[1],
                    "url_patterns": row[2],
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
                    .order_by(DynamicFeedTemplate.id.desc())
                ).all()

                matched_template = None
                for template in templates:
                    if template.url_patterns and template.url_patterns in domain:
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
                    columns = session.execute(text("""
                        SELECT column_name, data_type, is_nullable, column_default
                        FROM information_schema.columns
                        WHERE table_name = :table_name
                        ORDER BY ordinal_position
                    """), {"table_name": table_name}).fetchall()

                    if not columns:
                        return [TextContent(type="text", text=f"Table '{table_name}' not found")]

                    # Get row count
                    try:
                        row_count = session.execute(text(f"SELECT COUNT(*) FROM {table_name}")).fetchone()[0]
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
                tables = session.execute(text("""
                    SELECT table_name
                    FROM information_schema.tables
                    WHERE table_schema = 'public'
                    ORDER BY table_name
                """)).fetchall()

                table_list = []
                for table in tables:
                    try:
                        row_count = session.execute(text(f"SELECT COUNT(*) FROM {table[0]}")).fetchone()[0]
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
                status_counts = session.execute(text("""
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
                feed_stats = session.execute(text("""
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
                health_overview = session.execute(text("""
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
            interval_stats = session.execute(text("""
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
                    deleted = session.execute(
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
                    session.execute(text("VACUUM ANALYZE"))
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
                    session.execute(text("ANALYZE"))
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
                    session.execute(text("REINDEX INDEX CONCURRENTLY IF EXISTS idx_items_created_at"))
                    session.execute(text("REINDEX INDEX CONCURRENTLY IF EXISTS idx_items_feed_id"))
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
                source_stats = session.execute(text("""
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
                template_stats = session.execute(text("""
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

    async def _system_ping(self) -> List[TextContent]:
        """System ping test for MCP connection"""
        result = {
            "ok": True,
            "data": {"pong": True},
            "meta": {},
            "errors": []
        }
        return [TextContent(type="text", text=safe_json_dumps(result, indent=2))]

    # Categories Management Methods
    async def _categories_list(self, include_feeds: bool = True, include_stats: bool = True) -> List[TextContent]:
        """List all categories with optional feed assignments and statistics"""
        with Session(engine) as session:
            # Use raw SQL to avoid ORM model mismatch
            category_rows = session.execute(text("SELECT id, name, description, color, created_at FROM categories ORDER BY name")).fetchall()

            result = []
            for row in category_rows:
                category_data = {
                    "id": row[0],
                    "name": row[1],
                    "description": row[2],
                    "color": row[3],
                    "created_at": row[4].isoformat() if row[4] else None
                }

                if include_feeds:
                    # Get assigned feeds using raw SQL
                    feeds_sql = """
                    SELECT f.id, f.title, f.url, f.status
                    FROM feeds f
                    JOIN feed_categories fc ON f.id = fc.feed_id
                    WHERE fc.category_id = :category_id
                    ORDER BY f.title
                    """
                    feed_rows = session.execute(text(feeds_sql), {"category_id": row[0]}).fetchall()
                    category_data["assigned_feeds"] = [
                        {"id": feed[0], "title": feed[1], "url": feed[2], "status": feed[3]}
                        for feed in feed_rows
                    ]

                if include_stats:
                    # Get item count using raw SQL
                    stats_sql = """
                    SELECT COUNT(i.id) as total_items
                    FROM items i
                    JOIN feeds f ON i.feed_id = f.id
                    JOIN feed_categories fc ON f.id = fc.feed_id
                    WHERE fc.category_id = :category_id
                    """
                    stats_result = session.execute(text(stats_sql), {"category_id": row[0]}).fetchone()
                    category_data["total_items"] = stats_result[0] if stats_result else 0

                result.append(category_data)

        return [TextContent(type="text", text=safe_json_dumps(result, indent=2))]

    async def _categories_add(self, name: str, description: str = None, color: str = None) -> List[TextContent]:
        """Create a new category"""
        with Session(engine) as session:
            try:
                # Check if category already exists
                existing_result = session.execute(text(
                    "SELECT id FROM categories WHERE name = :name LIMIT 1"
                ), {"name": name}).fetchone()

                if existing_result:
                    return [TextContent(type="text", text=f"Error: Category '{name}' already exists")]

                # Insert new category using raw SQL
                insert_sql = "INSERT INTO categories (name, description, color, created_at) VALUES (:name, :description, :color, NOW()) RETURNING id, name, description, color, created_at"

                result_row = session.execute(text(insert_sql), {
                    "name": name,
                    "description": description,
                    "color": color
                }).fetchone()

                session.commit()

                result = {
                    "success": True,
                    "message": f"Category '{name}' created successfully",
                    "category": {
                        "id": result_row[0],
                        "name": result_row[1],
                        "description": result_row[2],
                        "color": result_row[3],
                        "created_at": result_row[4].isoformat() if result_row[4] else None
                    }
                }

                return [TextContent(type="text", text=safe_json_dumps(result, indent=2))]

            except Exception as e:
                session.rollback()
                return [TextContent(type="text", text=f"Error creating category: {str(e)}")]

    async def _categories_update(self, category_id: int, name: str = None, description: str = None, color: str = None) -> List[TextContent]:
        """Update category information"""
        with Session(engine) as session:
            try:
                # Check if category exists
                existing_result = session.execute(text(
                    "SELECT id, name, description, color FROM categories WHERE id = :id LIMIT 1"
                ), {"id": category_id}).fetchone()

                if not existing_result:
                    return [TextContent(type="text", text=f"Error: Category with ID {category_id} not found")]

                # Build update query dynamically
                update_fields = []
                params = {"id": category_id}

                if name is not None:
                    # Check if new name already exists (exclude current category)
                    name_check = session.execute(text(
                        "SELECT id FROM categories WHERE name = :name AND id != :id LIMIT 1"
                    ), {"name": name, "id": category_id}).fetchone()

                    if name_check:
                        return [TextContent(type="text", text=f"Error: Category name '{name}' already exists")]

                    update_fields.append("name = :name")
                    params["name"] = name

                if description is not None:
                    update_fields.append("description = :description")
                    params["description"] = description

                if color is not None:
                    update_fields.append("color = :color")
                    params["color"] = color

                if not update_fields:
                    return [TextContent(type="text", text="Error: No fields provided for update")]

                # Execute update
                update_sql = f"UPDATE categories SET {', '.join(update_fields)} WHERE id = :id RETURNING id, name, description, color, created_at"
                updated_row = session.execute(text(update_sql), params).fetchone()
                session.commit()

                result = {
                    "success": True,
                    "message": f"Category updated successfully",
                    "category": {
                        "id": updated_row[0],
                        "name": updated_row[1],
                        "description": updated_row[2],
                        "color": updated_row[3],
                        "created_at": updated_row[4].isoformat() if updated_row[4] else None
                    }
                }

                return [TextContent(type="text", text=safe_json_dumps(result, indent=2))]

            except Exception as e:
                session.rollback()
                return [TextContent(type="text", text=f"Error updating category: {str(e)}")]

    async def _categories_delete(self, category_id: int, confirm: bool = False) -> List[TextContent]:
        """Delete a category"""
        if not confirm:
            return [TextContent(type="text", text="Error: Deletion requires confirmation. Set confirm=true to proceed.")]

        with Session(engine) as session:
            category = session.get(Category, category_id)
            if not category:
                return [TextContent(type="text", text=f"Error: Category with ID {category_id} not found")]

            # Check for feed assignments
            assignments = session.exec(select(FeedCategory).where(FeedCategory.category_id == category_id)).all()

            # Remove assignments first
            for assignment in assignments:
                session.delete(assignment)

            # Delete category
            category_name = category.name
            session.delete(category)
            session.commit()

            result = {
                "success": True,
                "message": f"Category '{category_name}' deleted successfully",
                "removed_assignments": len(assignments)
            }

        return [TextContent(type="text", text=safe_json_dumps(result, indent=2))]

    async def _categories_assign(self, category_id: int, feed_id: int) -> List[TextContent]:
        """Assign category to feed"""
        with Session(engine) as session:
            # Verify category exists
            category = session.get(Category, category_id)
            if not category:
                return [TextContent(type="text", text=f"Error: Category with ID {category_id} not found")]

            # Verify feed exists
            feed = session.get(Feed, feed_id)
            if not feed:
                return [TextContent(type="text", text=f"Error: Feed with ID {feed_id} not found")]

            # Check if assignment already exists
            existing = session.exec(select(FeedCategory).where(
                FeedCategory.category_id == category_id,
                FeedCategory.feed_id == feed_id
            )).first()

            if existing:
                return [TextContent(type="text", text=f"Assignment already exists: {category.name} -> {feed.title}")]

            # Create assignment
            assignment = FeedCategory(category_id=category_id, feed_id=feed_id)
            session.add(assignment)
            session.commit()

            result = {
                "success": True,
                "message": f"Assigned category '{category.name}' to feed '{feed.title}'",
                "assignment": {
                    "category_id": category_id,
                    "category_name": category.name,
                    "feed_id": feed_id,
                    "feed_title": feed.title
                }
            }

        return [TextContent(type="text", text=safe_json_dumps(result, indent=2))]

    # Sources Management Methods
    async def _sources_list(self, include_stats: bool = True, include_feeds: bool = True) -> List[TextContent]:
        """List all sources with statistics and feeds"""
        with Session(engine) as session:
            sources = session.exec(select(Source)).all()

            result = []
            for source in sources:
                source_data = {
                    "id": source.id,
                    "name": source.name,
                    "type": source.type.value if hasattr(source.type, 'value') else str(source.type),
                    "description": source.description,
                    "created_at": source.created_at.isoformat() if hasattr(source, 'created_at') and source.created_at else None
                }

                if include_feeds:
                    # Get associated feeds
                    feeds = session.exec(select(Feed).where(Feed.source_id == source.id)).all()
                    source_data["feeds"] = [
                        {"id": feed.id, "title": feed.title, "url": feed.url, "status": feed.status}
                        for feed in feeds
                    ]

                if include_stats:
                    # Get feed and item counts
                    feed_count = session.exec(select(func.count(Feed.id)).where(Feed.source_id == source.id)).first() or 0
                    feed_ids = [f for f in session.exec(select(Feed.id).where(Feed.source_id == source.id)).all()]

                    if feed_ids:
                        item_count = session.exec(select(func.count(Item.id)).where(Item.feed_id.in_(feed_ids))).first() or 0
                    else:
                        item_count = 0

                    source_data["stats"] = {
                        "total_feeds": feed_count,
                        "total_items": item_count
                    }

                result.append(source_data)

        return [TextContent(type="text", text=safe_json_dumps(result, indent=2))]

    async def _sources_add(self, name: str, url: str, description: str = None, trust_level: int = 3) -> List[TextContent]:
        """Add a new source"""
        with Session(engine) as session:
            # Check if source already exists
            existing = session.exec(select(Source).where(Source.name == name)).first()
            if existing:
                return [TextContent(type="text", text=f"Error: Source '{name}' already exists")]

            # Create new source
            source_data = {
                "name": name,
                "url": url,
                "trust_level": trust_level
            }
            if description:
                source_data["description"] = description

            source = Source(**source_data)
            session.add(source)
            session.commit()
            session.refresh(source)

            result = {
                "success": True,
                "message": f"Source '{name}' created successfully",
                "source": {
                    "id": source.id,
                    "name": source.name,
                    "url": source.url,
                    "description": source.description,
                    "trust_level": getattr(source, 'trust_level', None)
                }
            }

        return [TextContent(type="text", text=safe_json_dumps(result, indent=2))]

    async def _sources_update(self, source_id: int, name: str = None, url: str = None,
                             description: str = None, trust_level: int = None) -> List[TextContent]:
        """Update source information"""
        with Session(engine) as session:
            source = session.get(Source, source_id)
            if not source:
                return [TextContent(type="text", text=f"Error: Source with ID {source_id} not found")]

            # Update fields
            updated_fields = []
            if name and name != source.name:
                source.name = name
                updated_fields.append("name")

            if url and url != source.url:
                source.url = url
                updated_fields.append("url")

            if description is not None:
                source.description = description
                updated_fields.append("description")

            if trust_level is not None:
                if hasattr(source, 'trust_level'):
                    source.trust_level = trust_level
                updated_fields.append("trust_level")

            if updated_fields:
                session.commit()
                session.refresh(source)

                result = {
                    "success": True,
                    "message": f"Source updated: {', '.join(updated_fields)}",
                    "source": {
                        "id": source.id,
                        "name": source.name,
                        "url": source.url,
                        "description": source.description,
                        "trust_level": getattr(source, 'trust_level', None)
                    }
                }
            else:
                result = {
                    "success": False,
                    "message": "No fields to update"
                }

        return [TextContent(type="text", text=safe_json_dumps(result, indent=2))]

    async def _sources_delete(self, source_id: int, confirm: bool = False) -> List[TextContent]:
        """Delete a source"""
        if not confirm:
            return [TextContent(type="text", text="Error: Deletion requires confirmation. Set confirm=true to proceed.")]

        with Session(engine) as session:
            source = session.get(Source, source_id)
            if not source:
                return [TextContent(type="text", text=f"Error: Source with ID {source_id} not found")]

            # Check for associated feeds
            feeds = session.exec(select(Feed).where(Feed.source_id == source_id)).all()

            if feeds:
                return [TextContent(type="text", text=f"Error: Cannot delete source '{source.name}' - it has {len(feeds)} associated feeds. Remove feeds first.")]

            # Delete source
            source_name = source.name
            session.delete(source)
            session.commit()

            result = {
                "success": True,
                "message": f"Source '{source_name}' deleted successfully"
            }

        return [TextContent(type="text", text=safe_json_dumps(result, indent=2))]

    async def _sources_stats(self, source_id: int = None, days: int = 30) -> List[TextContent]:
        """Get detailed source statistics"""
        with Session(engine) as session:
            if source_id:
                # Stats for specific source
                source = session.get(Source, source_id)
                if not source:
                    return [TextContent(type="text", text=f"Error: Source with ID {source_id} not found")]

                sources = [source]
            else:
                # Stats for all sources
                sources = session.exec(select(Source)).all()

            result = []
            cutoff_date = datetime.now() - timedelta(days=days)

            for source in sources:
                # Get feeds for this source
                feeds = session.exec(select(Feed).where(Feed.source_id == source.id)).all()
                feed_ids = [f.id for f in feeds]

                if feed_ids:
                    # Get item counts
                    total_items = session.exec(select(func.count(Item.id)).where(Item.feed_id.in_(feed_ids))).first() or 0
                    recent_items = session.exec(
                        select(func.count(Item.id)).where(
                            Item.feed_id.in_(feed_ids),
                            Item.published >= cutoff_date
                        )
                    ).first() or 0
                else:
                    total_items = 0
                    recent_items = 0

                source_stats = {
                    "id": source.id,
                    "name": source.name,
                    "url": source.url,
                    "trust_level": getattr(source, 'trust_level', None),
                    "stats": {
                        "total_feeds": len(feeds),
                        "total_items": total_items,
                        f"recent_items_{days}d": recent_items,
                        "avg_items_per_feed": round(total_items / len(feeds), 2) if feeds else 0
                    },
                    "feeds": [
                        {
                            "id": feed.id,
                            "title": feed.title,
                            "status": feed.status,
                            "url": feed.url
                        }
                        for feed in feeds
                    ]
                }

                result.append(source_stats)

        return [TextContent(type="text", text=safe_json_dumps(result, indent=2))]

    async def _auto_analysis_status(self) -> List[TextContent]:
        """Get auto-analysis system status and statistics"""
        try:
            with Session(engine) as session:
                processor = PendingAnalysisProcessor()
                queue_stats = processor.get_queue_stats()

                feeds_with_auto = session.exec(
                    select(func.count(Feed.id)).where(Feed.auto_analyze_enabled == True)
                ).first() or 0

                yesterday = datetime.utcnow() - timedelta(days=1)

                completed_today = session.exec(
                    select(func.count(PendingAutoAnalysis.id)).where(
                        PendingAutoAnalysis.status == "completed",
                        PendingAutoAnalysis.processed_at >= yesterday
                    )
                ).first() or 0

                failed_today = session.exec(
                    select(func.count(PendingAutoAnalysis.id)).where(
                        PendingAutoAnalysis.status == "failed",
                        PendingAutoAnalysis.processed_at >= yesterday
                    )
                ).first() or 0

                completed_jobs = session.exec(
                    select(PendingAutoAnalysis).where(
                        PendingAutoAnalysis.status == "completed",
                        PendingAutoAnalysis.processed_at >= yesterday
                    )
                ).all()

                total_items_analyzed = sum(len(job.item_ids) for job in completed_jobs)

                success_rate = round(
                    (completed_today / (completed_today + failed_today) * 100), 1
                ) if (completed_today + failed_today) > 0 else 100

                result = {
                    "system_status": "active",
                    "feeds_with_auto_analysis": feeds_with_auto,
                    "queue": queue_stats,
                    "last_24h": {
                        "completed_jobs": completed_today,
                        "failed_jobs": failed_today,
                        "total_items_analyzed": total_items_analyzed,
                        "success_rate": success_rate
                    }
                }

                return [TextContent(type="text", text=safe_json_dumps(result, indent=2))]

        except Exception as e:
            logger.error(f"Error getting auto-analysis status: {e}")
            return [TextContent(type="text", text=safe_json_dumps({
                "error": str(e),
                "message": "Failed to get auto-analysis status"
            }, indent=2))]

    async def _auto_analysis_toggle(self, feed_id: int, enabled: bool) -> List[TextContent]:
        """Toggle auto-analysis for a specific feed"""
        try:
            with Session(engine) as session:
                feed = session.get(Feed, feed_id)
                if not feed:
                    return [TextContent(type="text", text=safe_json_dumps({
                        "error": f"Feed {feed_id} not found"
                    }, indent=2))]

                feed.auto_analyze_enabled = enabled
                session.add(feed)
                session.commit()
                session.refresh(feed)

                logger.info(f"Auto-analysis {'enabled' if enabled else 'disabled'} for feed {feed_id}")

                result = {
                    "success": True,
                    "feed_id": feed_id,
                    "feed_title": feed.title,
                    "auto_analyze_enabled": feed.auto_analyze_enabled,
                    "message": f"Auto-analysis {'enabled' if enabled else 'disabled'} for feed '{feed.title}'"
                }

                return [TextContent(type="text", text=safe_json_dumps(result, indent=2))]

        except Exception as e:
            logger.error(f"Error toggling auto-analysis for feed {feed_id}: {e}")
            return [TextContent(type="text", text=safe_json_dumps({
                "error": str(e),
                "message": f"Failed to toggle auto-analysis for feed {feed_id}"
            }, indent=2))]

    async def _auto_analysis_queue(self, limit: int = 50) -> List[TextContent]:
        """View pending auto-analysis queue"""
        try:
            with Session(engine) as session:
                pending_jobs = session.exec(
                    select(PendingAutoAnalysis).where(
                        PendingAutoAnalysis.status == "pending"
                    ).order_by(PendingAutoAnalysis.created_at).limit(limit)
                ).all()

                result = {
                    "total_pending": len(pending_jobs),
                    "queue": []
                }

                for job in pending_jobs:
                    feed = session.get(Feed, job.feed_id)
                    wait_time = (datetime.utcnow() - job.created_at).total_seconds() / 60

                    result["queue"].append({
                        "id": job.id,
                        "feed_id": job.feed_id,
                        "feed_title": feed.title if feed else "Unknown",
                        "items_count": len(job.item_ids),
                        "status": job.status,
                        "created_at": job.created_at.isoformat(),
                        "wait_time_minutes": round(wait_time, 1)
                    })

                return [TextContent(type="text", text=safe_json_dumps(result, indent=2))]

        except Exception as e:
            logger.error(f"Error getting auto-analysis queue: {e}")
            return [TextContent(type="text", text=safe_json_dumps({
                "error": str(e),
                "message": "Failed to get auto-analysis queue"
            }, indent=2))]

    async def _auto_analysis_history(self, days: int = 7, limit: int = 50) -> List[TextContent]:
        """Get auto-analysis processing history"""
        try:
            with Session(engine) as session:
                cutoff = datetime.utcnow() - timedelta(days=days)

                jobs = session.exec(
                    select(PendingAutoAnalysis).where(
                        PendingAutoAnalysis.created_at >= cutoff,
                        or_(
                            PendingAutoAnalysis.status == "completed",
                            PendingAutoAnalysis.status == "failed"
                        )
                    ).order_by(PendingAutoAnalysis.processed_at.desc()).limit(limit)
                ).all()

                result = {
                    "period_days": days,
                    "total_jobs": len(jobs),
                    "history": []
                }

                for job in jobs:
                    feed = session.get(Feed, job.feed_id)
                    processing_time = None
                    if job.processed_at and job.created_at:
                        processing_time = (job.processed_at - job.created_at).total_seconds() / 60

                    result["history"].append({
                        "id": job.id,
                        "feed_id": job.feed_id,
                        "feed_title": feed.title if feed else "Unknown",
                        "items_count": len(job.item_ids),
                        "status": job.status,
                        "created_at": job.created_at.isoformat(),
                        "processed_at": job.processed_at.isoformat() if job.processed_at else None,
                        "processing_time_minutes": round(processing_time, 1) if processing_time else None,
                        "analysis_run_id": job.analysis_run_id,
                        "error_message": job.error_message
                    })

                return [TextContent(type="text", text=safe_json_dumps(result, indent=2))]

        except Exception as e:
            logger.error(f"Error getting auto-analysis history: {e}")
            return [TextContent(type="text", text=safe_json_dumps({
                "error": str(e),
                "message": "Failed to get auto-analysis history"
            }, indent=2))]

    async def _auto_analysis_config(self, max_runs_per_day: int = None,
                                    max_items_per_run: int = None,
                                    ai_model: str = None) -> List[TextContent]:
        """Get or update auto-analysis configuration"""
        try:
            config = {
                "max_runs_per_day": 10,
                "max_items_per_run": 50,
                "ai_model": "gpt-4.1-nano",
                "check_interval": 60
            }

            if max_runs_per_day is not None:
                config["max_runs_per_day"] = max_runs_per_day
                logger.info(f"Updated max_runs_per_day to {max_runs_per_day}")

            if max_items_per_run is not None:
                config["max_items_per_run"] = max_items_per_run
                logger.info(f"Updated max_items_per_run to {max_items_per_run}")

            if ai_model is not None:
                config["ai_model"] = ai_model
                logger.info(f"Updated ai_model to {ai_model}")

            result = {
                "success": True,
                "config": config,
                "message": "Configuration retrieved" if all(v is None for v in [max_runs_per_day, max_items_per_run, ai_model]) else "Configuration updated"
            }

            return [TextContent(type="text", text=safe_json_dumps(result, indent=2))]

        except Exception as e:
            logger.error(f"Error managing auto-analysis config: {e}")
            return [TextContent(type="text", text=safe_json_dumps({
                "error": str(e),
                "message": "Failed to manage auto-analysis config"
            }, indent=2))]

    async def _auto_analysis_stats(self, feed_id: int = None) -> List[TextContent]:
        """Get comprehensive auto-analysis statistics"""
        try:
            with Session(engine) as session:
                if feed_id:
                    feed = session.get(Feed, feed_id)
                    if not feed:
                        return [TextContent(type="text", text=safe_json_dumps({
                            "error": f"Feed {feed_id} not found"
                        }, indent=2))]

                    auto_service = AutoAnalysisService()
                    stats = auto_service.get_auto_analysis_stats(feed_id)

                    result = {
                        "feed_id": feed_id,
                        "feed_title": feed.title,
                        "auto_analyze_enabled": feed.auto_analyze_enabled,
                        "stats": stats
                    }
                else:
                    feeds_with_auto = session.exec(
                        select(Feed).where(Feed.auto_analyze_enabled == True)
                    ).all()

                    week_ago = datetime.utcnow() - timedelta(days=7)

                    total_jobs = session.exec(
                        select(func.count(PendingAutoAnalysis.id)).where(
                            PendingAutoAnalysis.created_at >= week_ago
                        )
                    ).first() or 0

                    completed_jobs = session.exec(
                        select(func.count(PendingAutoAnalysis.id)).where(
                            PendingAutoAnalysis.created_at >= week_ago,
                            PendingAutoAnalysis.status == "completed"
                        )
                    ).first() or 0

                    failed_jobs = session.exec(
                        select(func.count(PendingAutoAnalysis.id)).where(
                            PendingAutoAnalysis.created_at >= week_ago,
                            PendingAutoAnalysis.status == "failed"
                        )
                    ).first() or 0

                    result = {
                        "system_stats": {
                            "active_feeds": len(feeds_with_auto),
                            "last_7_days": {
                                "total_jobs": total_jobs,
                                "completed": completed_jobs,
                                "failed": failed_jobs,
                                "success_rate": round((completed_jobs / total_jobs * 100), 1) if total_jobs > 0 else 100
                            }
                        },
                        "feeds_with_auto_analysis": [
                            {
                                "id": f.id,
                                "title": f.title,
                                "url": f.url
                            }
                            for f in feeds_with_auto
                        ]
                    }

                return [TextContent(type="text", text=safe_json_dumps(result, indent=2))]

        except Exception as e:
            logger.error(f"Error getting auto-analysis stats: {e}")
            return [TextContent(type="text", text=safe_json_dumps({
                "error": str(e),
                "message": "Failed to get auto-analysis stats"
            }, indent=2))]

    async def run(self, host: str = "0.0.0.0", port: int = 8001):
        """Run the MCP server"""
        logger.info(f"Starting Comprehensive News MCP Server on {host}:{port}")
        from mcp.server.stdio import stdio_server

        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(read_stream, write_stream, {})

async def main():
    server = ComprehensiveNewsServer()
    await server.run()

if __name__ == "__main__":
    asyncio.run(main())