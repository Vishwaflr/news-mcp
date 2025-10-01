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