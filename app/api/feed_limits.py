"""
Feed Limits API

API endpoints for managing feed-specific limits and monitoring violations.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
from app.core.logging_config import get_logger
from app.services.feed_limits_service import get_feed_limits_service

router = APIRouter(prefix="/api/feed-limits", tags=["feed-limits"])
logger = get_logger(__name__)


class FeedLimitsRequest(BaseModel):
    """Request model for setting feed limits"""
    max_analyses_per_day: Optional[int] = None
    max_analyses_per_hour: Optional[int] = None
    min_interval_minutes: Optional[int] = None
    daily_cost_limit: Optional[float] = None
    monthly_cost_limit: Optional[float] = None
    cost_alert_threshold: Optional[float] = None
    max_items_per_analysis: Optional[int] = None
    emergency_stop_enabled: Optional[bool] = None
    auto_disable_on_error_rate: Optional[float] = None
    auto_disable_on_cost_breach: Optional[bool] = None
    alert_email: Optional[str] = None
    custom_settings: Optional[Dict[str, Any]] = None


@router.get("/feeds/{feed_id}")
async def get_feed_limits(feed_id: int) -> Dict[str, Any]:
    """Get limits configuration for a specific feed"""
    try:
        limits_service = get_feed_limits_service()
        limits = limits_service.get_feed_limits(feed_id)

        if not limits:
            return {
                "success": True,
                "data": {
                    "feed_id": feed_id,
                    "has_limits": False,
                    "message": "No limits configured for this feed"
                }
            }

        return {
            "success": True,
            "data": {
                "feed_id": feed_id,
                "has_limits": True,
                "limits": limits.to_dict()
            }
        }

    except Exception as e:
        logger.error(f"Error getting limits for feed {feed_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get feed limits: {str(e)}")


@router.post("/feeds/{feed_id}")
async def set_feed_limits(feed_id: int, limits_request: FeedLimitsRequest) -> Dict[str, Any]:
    """Set or update limits for a specific feed"""
    try:
        limits_service = get_feed_limits_service()

        # Convert request to kwargs
        limits_data = limits_request.dict(exclude_unset=True)

        limits = limits_service.set_feed_limits(feed_id, **limits_data)

        return {
            "success": True,
            "data": {
                "message": f"Limits updated for feed {feed_id}",
                "limits": limits.to_dict()
            }
        }

    except Exception as e:
        logger.error(f"Error setting limits for feed {feed_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to set feed limits: {str(e)}")


@router.delete("/feeds/{feed_id}")
async def remove_feed_limits(feed_id: int) -> Dict[str, Any]:
    """Remove limits for a specific feed"""
    try:
        limits_service = get_feed_limits_service()

        # Set all limits to None to effectively remove them
        limits = limits_service.set_feed_limits(
            feed_id,
            max_analyses_per_day=None,
            max_analyses_per_hour=None,
            min_interval_minutes=None,
            daily_cost_limit=None,
            monthly_cost_limit=None,
            cost_alert_threshold=None,
            max_items_per_analysis=None,
            emergency_stop_enabled=False,
            auto_disable_on_error_rate=None,
            auto_disable_on_cost_breach=False
        )

        return {
            "success": True,
            "data": {
                "message": f"Limits removed for feed {feed_id}",
                "limits": limits.to_dict()
            }
        }

    except Exception as e:
        logger.error(f"Error removing limits for feed {feed_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to remove feed limits: {str(e)}")


@router.post("/feeds/{feed_id}/check")
async def check_analysis_allowed(
    feed_id: int,
    items_count: int = Query(0, ge=0, description="Number of items to process")
) -> Dict[str, Any]:
    """Check if an analysis is allowed for a feed"""
    try:
        limits_service = get_feed_limits_service()
        is_allowed, reason = limits_service.check_analysis_allowed(feed_id, items_count)

        return {
            "success": True,
            "data": {
                "feed_id": feed_id,
                "items_count": items_count,
                "is_allowed": is_allowed,
                "reason": reason,
                "status": "allowed" if is_allowed else "blocked"
            }
        }

    except Exception as e:
        logger.error(f"Error checking analysis permission for feed {feed_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to check analysis permission: {str(e)}")


@router.post("/feeds/{feed_id}/enable")
async def enable_feed(feed_id: int) -> Dict[str, Any]:
    """Enable a disabled feed"""
    try:
        limits_service = get_feed_limits_service()
        success = limits_service.enable_feed(feed_id)

        if success:
            return {
                "success": True,
                "data": {
                    "message": f"Feed {feed_id} has been enabled",
                    "feed_id": feed_id,
                    "status": "enabled"
                }
            }
        else:
            raise HTTPException(status_code=404, detail=f"Feed {feed_id} not found or no limits configured")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error enabling feed {feed_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to enable feed: {str(e)}")


@router.get("/feeds/{feed_id}/violations")
async def get_feed_violations(
    feed_id: int,
    days: int = Query(7, ge=1, le=30, description="Number of days to include"),
    violation_type: Optional[str] = Query(None, description="Filter by violation type")
) -> Dict[str, Any]:
    """Get recent violations for a specific feed"""
    try:
        limits_service = get_feed_limits_service()
        violations = limits_service.get_feed_violations(feed_id, days, violation_type)

        return {
            "success": True,
            "data": {
                "feed_id": feed_id,
                "days": days,
                "violation_type_filter": violation_type,
                "violations_count": len(violations),
                "violations": [v.to_dict() for v in violations]
            }
        }

    except Exception as e:
        logger.error(f"Error getting violations for feed {feed_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get feed violations: {str(e)}")


@router.get("/violations/summary")
async def get_violations_summary(
    days: int = Query(7, ge=1, le=30, description="Number of days to include")
) -> Dict[str, Any]:
    """Get system-wide violations summary"""
    try:
        limits_service = get_feed_limits_service()
        summary = limits_service.get_system_violations_summary(days)

        return {
            "success": True,
            "data": summary
        }

    except Exception as e:
        logger.error(f"Error getting violations summary: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get violations summary: {str(e)}")


@router.post("/feeds/{feed_id}/emergency-stop")
async def emergency_stop_feed(feed_id: int) -> Dict[str, Any]:
    """Emergency stop for a feed - immediately disable all processing"""
    try:
        limits_service = get_feed_limits_service()

        # Set emergency stop
        limits = limits_service.set_feed_limits(
            feed_id,
            emergency_stop_enabled=True
        )

        return {
            "success": True,
            "data": {
                "message": f"Emergency stop activated for feed {feed_id}",
                "feed_id": feed_id,
                "status": "emergency_stopped",
                "limits": limits.to_dict()
            }
        }

    except Exception as e:
        logger.error(f"Error activating emergency stop for feed {feed_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to activate emergency stop: {str(e)}")


@router.get("/presets")
async def get_limit_presets() -> Dict[str, Any]:
    """Get predefined limit presets for common use cases"""
    presets = {
        "conservative": {
            "name": "Conservative",
            "description": "Low frequency, strict cost controls",
            "max_analyses_per_day": 5,
            "max_analyses_per_hour": 1,
            "min_interval_minutes": 60,
            "daily_cost_limit": 1.0,
            "cost_alert_threshold": 80.0,
            "max_items_per_analysis": 50,
            "auto_disable_on_error_rate": 0.5,
            "auto_disable_on_cost_breach": True
        },
        "moderate": {
            "name": "Moderate",
            "description": "Balanced frequency and cost controls",
            "max_analyses_per_day": 20,
            "max_analyses_per_hour": 3,
            "min_interval_minutes": 30,
            "daily_cost_limit": 5.0,
            "cost_alert_threshold": 75.0,
            "max_items_per_analysis": 100,
            "auto_disable_on_error_rate": 0.7,
            "auto_disable_on_cost_breach": True
        },
        "aggressive": {
            "name": "Aggressive",
            "description": "High frequency, higher cost tolerance",
            "max_analyses_per_day": 50,
            "max_analyses_per_hour": 10,
            "min_interval_minutes": 15,
            "daily_cost_limit": 20.0,
            "cost_alert_threshold": 90.0,
            "max_items_per_analysis": 200,
            "auto_disable_on_error_rate": 0.8,
            "auto_disable_on_cost_breach": False
        },
        "development": {
            "name": "Development",
            "description": "Minimal limits for testing",
            "max_analyses_per_day": 100,
            "max_analyses_per_hour": 20,
            "min_interval_minutes": 5,
            "daily_cost_limit": 0.5,
            "cost_alert_threshold": 95.0,
            "max_items_per_analysis": 20,
            "auto_disable_on_error_rate": 0.9,
            "auto_disable_on_cost_breach": True
        }
    }

    return {
        "success": True,
        "data": {
            "presets": presets,
            "usage": "Apply a preset by copying its values to the feed limits configuration"
        }
    }