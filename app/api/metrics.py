"""
Metrics API

API endpoints for accessing feed metrics, costs, and performance data.
"""

from fastapi import APIRouter, HTTPException, Query, Response
from typing import Dict, Any, List, Optional
from app.core.logging_config import get_logger
from app.services.metrics_service import get_metrics_service
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

router = APIRouter(prefix="/api/metrics", tags=["metrics"])
logger = get_logger(__name__)


@router.get("/prometheus")
async def prometheus_metrics():
    """
    Prometheus metrics endpoint.

    Returns metrics in Prometheus text format for scraping.
    SPRINT 1 DAY 3: New endpoint for Prometheus integration.
    """
    try:
        metrics_data = generate_latest()
        return Response(content=metrics_data, media_type=CONTENT_TYPE_LATEST)
    except Exception as e:
        logger.error(f"Error generating Prometheus metrics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate metrics: {str(e)}")


@router.get("/system/overview")
async def get_system_overview() -> Dict[str, Any]:
    """Get system-wide metrics overview"""
    try:
        metrics_service = get_metrics_service()
        overview = metrics_service.get_system_overview()

        return {
            "success": True,
            "data": overview
        }
    except Exception as e:
        logger.error(f"Error getting system overview: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get system overview: {str(e)}")


@router.get("/feeds/{feed_id}")
async def get_feed_metrics(
    feed_id: int,
    days: int = Query(7, ge=1, le=30, description="Number of days to include")
) -> Dict[str, Any]:
    """Get metrics for a specific feed"""
    try:
        metrics_service = get_metrics_service()
        metrics = metrics_service.get_feed_metrics(feed_id, days)

        return {
            "success": True,
            "data": {
                "feed_id": feed_id,
                "days": days,
                "metrics": metrics
            }
        }
    except Exception as e:
        logger.error(f"Error getting feed metrics for feed {feed_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get feed metrics: {str(e)}")


@router.get("/feeds/{feed_id}/summary")
async def get_feed_summary(feed_id: int) -> Dict[str, Any]:
    """Get summary metrics for a feed (today + last 7 days)"""
    try:
        metrics_service = get_metrics_service()
        summary = metrics_service.get_feed_summary(feed_id)

        return {
            "success": True,
            "data": summary
        }
    except Exception as e:
        logger.error(f"Error getting feed summary for feed {feed_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get feed summary: {str(e)}")


@router.get("/costs/breakdown")
async def get_cost_breakdown(
    days: int = Query(7, ge=1, le=30, description="Number of days to include")
) -> Dict[str, Any]:
    """Get cost breakdown by feed and model"""
    try:
        metrics_service = get_metrics_service()

        # This would be implemented to get cost breakdown across feeds
        # For now, return system overview
        overview = metrics_service.get_system_overview()

        return {
            "success": True,
            "data": {
                "days": days,
                "breakdown": overview
            }
        }
    except Exception as e:
        logger.error(f"Error getting cost breakdown: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get cost breakdown: {str(e)}")


@router.get("/performance/queue")
async def get_queue_performance() -> Dict[str, Any]:
    """Get queue processing performance metrics"""
    try:
        # This would get queue performance metrics from QueueMetrics table
        # For now, return basic info
        return {
            "success": True,
            "data": {
                "message": "Queue performance metrics endpoint - implementation in progress"
            }
        }
    except Exception as e:
        logger.error(f"Error getting queue performance: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get queue performance: {str(e)}")


@router.get("/feeds")
async def get_all_feeds_summary() -> Dict[str, Any]:
    """Get summary metrics for all feeds"""
    try:
        # This would get metrics for all feeds
        # For now, return system overview
        metrics_service = get_metrics_service()
        overview = metrics_service.get_system_overview()

        return {
            "success": True,
            "data": {
                "system_overview": overview,
                "feeds": []  # Would be populated with per-feed summaries
            }
        }
    except Exception as e:
        logger.error(f"Error getting all feeds summary: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get feeds summary: {str(e)}")


@router.get("/storage/stats")
async def get_storage_stats() -> Dict[str, Any]:
    """Get database storage statistics"""
    try:
        from sqlalchemy import text
        from app.database import engine
        from sqlmodel import Session

        with Session(engine) as session:
            # Get table sizes
            table_sizes_query = text("""
                SELECT
                    tablename,
                    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS total_size,
                    pg_size_pretty(pg_relation_size(schemaname||'.'||tablename)) AS table_size,
                    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename) - pg_relation_size(schemaname||'.'||tablename)) AS indexes_size,
                    pg_total_relation_size(schemaname||'.'||tablename) AS total_bytes
                FROM pg_tables
                WHERE schemaname = 'public'
                ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
                LIMIT 10
            """)
            table_sizes = session.execute(table_sizes_query).fetchall()

            # Get database size
            db_size_query = text("SELECT pg_size_pretty(pg_database_size('news_db')) AS database_size")
            db_size_result = session.execute(db_size_query).fetchone()
            db_size = db_size_result[0] if db_size_result else "Unknown"

            # Get item and analysis counts
            item_count_query = text("SELECT COUNT(*) FROM items")
            analysis_count_query = text("SELECT COUNT(*) FROM item_analysis")
            item_count = session.execute(item_count_query).scalar() or 0
            analysis_count = session.execute(analysis_count_query).scalar() or 0

            # Get JSONB field sizes
            jsonb_sizes_query = text("""
                SELECT
                    'sentiment_json' AS field_type,
                    COUNT(*) AS entries,
                    pg_size_pretty(SUM(pg_column_size(sentiment_json))::bigint) AS total_size,
                    pg_size_pretty(AVG(pg_column_size(sentiment_json))::bigint) AS avg_size
                FROM item_analysis
                WHERE sentiment_json IS NOT NULL
                UNION ALL
                SELECT
                    'impact_json' AS field_type,
                    COUNT(*) AS entries,
                    pg_size_pretty(SUM(pg_column_size(impact_json))::bigint) AS total_size,
                    pg_size_pretty(AVG(pg_column_size(impact_json))::bigint) AS avg_size
                FROM item_analysis
                WHERE impact_json IS NOT NULL
            """)
            jsonb_sizes = session.execute(jsonb_sizes_query).fetchall()

            # Get geopolitical data stats
            geopolitical_query = text("""
                SELECT
                    COUNT(*) AS total_analyses,
                    COUNT(*) FILTER (WHERE sentiment_json ? 'geopolitical') AS with_geopolitical,
                    ROUND(100.0 * COUNT(*) FILTER (WHERE sentiment_json ? 'geopolitical') / NULLIF(COUNT(*), 0), 2) AS geopolitical_percentage,
                    pg_size_pretty(SUM(pg_column_size(sentiment_json)) FILTER (WHERE sentiment_json ? 'geopolitical')::bigint) AS geopolitical_json_size
                FROM item_analysis
            """)
            geopolitical_stats = session.execute(geopolitical_query).fetchone()

            # Get category sizes
            category_sizes_query = text("""
                SELECT
                    'RSS Feed Data' AS category,
                    pg_size_pretty(
                        pg_total_relation_size('items') +
                        pg_total_relation_size('feeds') +
                        pg_total_relation_size('fetch_log')
                    ) AS size,
                    (pg_total_relation_size('items') +
                     pg_total_relation_size('feeds') +
                     pg_total_relation_size('fetch_log')) AS bytes
                UNION ALL
                SELECT
                    'Sentiment Analysis Data' AS category,
                    pg_size_pretty(
                        pg_total_relation_size('item_analysis') +
                        pg_total_relation_size('analysis_runs') +
                        pg_total_relation_size('analysis_run_items')
                    ) AS size,
                    (pg_total_relation_size('item_analysis') +
                     pg_total_relation_size('analysis_runs') +
                     pg_total_relation_size('analysis_run_items')) AS bytes
                UNION ALL
                SELECT
                    'Auto-Analysis Queue' AS category,
                    pg_size_pretty(pg_total_relation_size('pending_auto_analysis')) AS size,
                    pg_total_relation_size('pending_auto_analysis') AS bytes
            """)
            category_sizes = session.execute(category_sizes_query).fetchall()

            # Get growth stats
            growth_query = text("""
                WITH stats AS (
                    SELECT
                        COUNT(*) AS total_items,
                        COUNT(*) FILTER (WHERE published >= NOW() - INTERVAL '7 days') AS items_last_7d,
                        MIN(published) AS oldest_item,
                        MAX(published) AS newest_item
                    FROM items
                )
                SELECT
                    total_items,
                    items_last_7d,
                    ROUND(items_last_7d * 52.0 / 1000, 1) AS estimated_items_per_year_k,
                    EXTRACT(DAY FROM (newest_item - oldest_item))::int AS data_age_days
                FROM stats
            """)
            growth_stats = session.execute(growth_query).fetchone()

            return {
                "success": True,
                "data": {
                    "database_size": db_size,
                    "item_count": item_count,
                    "analysis_count": analysis_count,
                    "analysis_coverage_percent": round((analysis_count / item_count * 100) if item_count > 0 else 0, 2),
                    "top_tables": [
                        {
                            "name": row[0],
                            "total_size": row[1],
                            "table_size": row[2],
                            "indexes_size": row[3],
                            "total_bytes": row[4]
                        } for row in table_sizes
                    ],
                    "jsonb_fields": [
                        {
                            "field_type": row[0],
                            "entries": row[1],
                            "total_size": row[2],
                            "avg_size": row[3]
                        } for row in jsonb_sizes
                    ],
                    "geopolitical": {
                        "total_analyses": geopolitical_stats[0] if geopolitical_stats else 0,
                        "with_geopolitical": geopolitical_stats[1] if geopolitical_stats else 0,
                        "percentage": float(geopolitical_stats[2]) if geopolitical_stats and geopolitical_stats[2] else 0.0,
                        "size": geopolitical_stats[3] if geopolitical_stats else "0 kB"
                    },
                    "category_sizes": [
                        {
                            "category": row[0],
                            "size": row[1],
                            "bytes": row[2]
                        } for row in category_sizes
                    ],
                    "growth": {
                        "total_items": growth_stats[0] if growth_stats else 0,
                        "items_per_week": growth_stats[1] if growth_stats else 0,
                        "estimated_items_per_year_k": float(growth_stats[2]) if growth_stats and growth_stats[2] else 0.0,
                        "data_age_days": growth_stats[3] if growth_stats else 0
                    }
                }
            }
    except Exception as e:
        logger.error(f"Error getting storage stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get storage stats: {str(e)}")


@router.post("/test/record")
async def record_test_metrics(
    feed_id: int,
    items_processed: int = 10,
    cost_usd: float = 0.05
) -> Dict[str, Any]:
    """Test endpoint to record sample metrics"""
    try:
        metrics_service = get_metrics_service()

        # Create test data
        analysis_run = {
            "id": 999,
            "model_tag": "gpt-4.1-nano"
        }

        tokens_used = {
            "total": items_processed * 500,
            "input": items_processed * 400,
            "output": items_processed * 100,
            "cached": 0
        }

        cost_breakdown = metrics_service.calculate_cost("gpt-4.1-nano", tokens_used)

        metrics_service.record_analysis_completion(
            feed_id=feed_id,
            analysis_run=analysis_run,
            triggered_by="manual",
            items_processed=items_processed,
            successful_items=items_processed,
            failed_items=0,
            tokens_used=tokens_used,
            cost_breakdown=cost_breakdown,
            processing_time_seconds=30.0
        )

        return {
            "success": True,
            "data": {
                "message": f"Recorded test metrics for feed {feed_id}",
                "items_processed": items_processed,
                "cost_breakdown": cost_breakdown,
                "tokens_used": tokens_used
            }
        }
    except Exception as e:
        logger.error(f"Error recording test metrics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to record test metrics: {str(e)}")