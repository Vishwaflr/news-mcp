"""Feature flags administration API."""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any, Optional
from pydantic import BaseModel

from app.utils.feature_flags import feature_flags, FeatureFlagStatus
from app.utils.shadow_compare import shadow_comparer
from app.utils.monitoring import metrics_collector, repo_monitor
from app.utils.analysis_shadow_compare import analysis_shadow_comparer

router = APIRouter(prefix="/api/admin/feature-flags", tags=["admin", "feature-flags"])


class FeatureFlagUpdate(BaseModel):
    """Request model for updating feature flags."""
    status: str
    rollout_percentage: Optional[int] = None


class MetricsResponse(BaseModel):
    """Response model for metrics data."""
    shadow_comparison: Dict[str, Any]
    performance_metrics: Dict[str, Any]
    flag_status: Dict[str, Any]


@router.get("/")
async def get_all_flags() -> Dict[str, Any]:
    """Get status of all feature flags."""
    return feature_flags.get_all_flags()


@router.get("/{flag_name}")
async def get_flag_status(flag_name: str) -> Dict[str, Any]:
    """Get status of specific feature flag."""
    flag_status = feature_flags.get_flag_status(flag_name)
    if not flag_status:
        raise HTTPException(status_code=404, detail=f"Flag {flag_name} not found")
    return flag_status


@router.post("/{flag_name}")
async def update_flag(flag_name: str, update: FeatureFlagUpdate) -> Dict[str, Any]:
    """Update feature flag configuration."""
    try:
        status = FeatureFlagStatus(update.status)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status. Must be one of: {[s.value for s in FeatureFlagStatus]}"
        )

    feature_flags.set_flag_status(flag_name, status, update.rollout_percentage)

    return {
        "flag_name": flag_name,
        "updated_status": status.value,
        "rollout_percentage": update.rollout_percentage,
        "message": f"Flag {flag_name} updated successfully"
    }


@router.post("/{flag_name}/reset-metrics")
async def reset_flag_metrics(flag_name: str) -> Dict[str, str]:
    """Reset metrics for a specific flag."""
    feature_flags.reset_flag_metrics(flag_name)
    return {"message": f"Metrics reset for flag {flag_name}"}


@router.get("/metrics/shadow-comparison")
async def get_shadow_comparison_metrics() -> Dict[str, Any]:
    """Get shadow comparison statistics."""
    return shadow_comparer.get_comparison_stats()


@router.get("/metrics/analysis-shadow-comparison")
async def get_analysis_shadow_comparison_metrics() -> Dict[str, Any]:
    """Get analysis shadow comparison statistics."""
    return analysis_shadow_comparer.get_comparison_stats()


@router.get("/metrics/performance")
async def get_performance_metrics() -> Dict[str, Any]:
    """Get performance metrics for repository operations."""
    return {
        "overall_summary": metrics_collector.get_performance_summary(),
        "comparison_metrics": metrics_collector.get_comparison_metrics("items.legacy.list", "items.list"),
        "recent_stats": {
            "items_repo_duration": metrics_collector.get_stats("items.list.duration_ms"),
            "legacy_duration": metrics_collector.get_stats("items.legacy.duration_ms")
        }
    }


@router.get("/metrics/dashboard")
async def get_metrics_dashboard() -> MetricsResponse:
    """Get comprehensive metrics dashboard."""
    return MetricsResponse(
        shadow_comparison=shadow_comparer.get_comparison_stats(),
        performance_metrics=metrics_collector.get_performance_summary(),
        flag_status=feature_flags.get_all_flags()
    )


@router.post("/shadow-comparison/reset")
async def reset_shadow_comparison() -> Dict[str, str]:
    """Reset shadow comparison metrics."""
    shadow_comparer.reset_metrics()
    return {"message": "Shadow comparison metrics reset"}


@router.post("/analysis-shadow-comparison/reset")
async def reset_analysis_shadow_comparison() -> Dict[str, str]:
    """Reset analysis shadow comparison metrics."""
    analysis_shadow_comparer.reset_metrics()
    return {"message": "Analysis shadow comparison metrics reset"}


@router.post("/analysis-shadow/{action}")
async def control_analysis_shadow(action: str, sample_rate: float = 0.1) -> Dict[str, str]:
    """Control analysis shadow comparison (enable/disable)."""
    if action == "enable":
        analysis_shadow_comparer.enable(sample_rate)
        return {"message": f"Analysis shadow comparison enabled with {sample_rate*100}% sample rate"}
    elif action == "disable":
        analysis_shadow_comparer.disable()
        return {"message": "Analysis shadow comparison disabled"}
    else:
        raise HTTPException(status_code=400, detail="Action must be 'enable' or 'disable'")


@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """Health check for feature flag system."""
    flags_count = len(feature_flags.get_all_flags())
    emergency_flags = [
        name for name, flag_data in feature_flags.get_all_flags().items()
        if flag_data.get("status") == "emergency_off"
    ]

    return {
        "status": "healthy" if not emergency_flags else "degraded",
        "total_flags": flags_count,
        "emergency_disabled": emergency_flags,
        "shadow_comparison_active": shadow_comparer.sample_rate > 0,
        "metrics_collector_active": len(metrics_collector.metrics) > 0
    }


@router.get("/auto-analysis/rollout-status")
async def get_auto_analysis_rollout_status() -> Dict[str, Any]:
    """Get detailed rollout status for auto-analysis feature."""
    from app.database import engine
    from sqlmodel import Session, select
    from app.models.core import Feed

    global_flag = feature_flags.get_flag_status("auto_analysis_global")
    shadow_flag = feature_flags.get_flag_status("auto_analysis_shadow")

    with Session(engine) as session:
        # Get all feeds with auto_analyze_enabled
        enabled_feeds = session.exec(
            select(Feed).where(Feed.auto_analyze_enabled == True)
        ).all()

        total_feeds = session.exec(select(Feed)).all()

        # Calculate which feeds are in rollout based on percentage
        rolled_out_feeds = []
        if global_flag:
            for feed in enabled_feeds:
                if feature_flags.is_enabled("auto_analysis_global", str(feed.id)):
                    rolled_out_feeds.append({
                        "id": feed.id,
                        "title": feed.title,
                        "status": feed.status
                    })

    return {
        "global_flag": global_flag,
        "shadow_flag": shadow_flag,
        "total_feeds": len(total_feeds),
        "feeds_with_auto_analyze_enabled": len(enabled_feeds),
        "feeds_in_rollout": len(rolled_out_feeds),
        "rollout_percentage_actual": (len(rolled_out_feeds) / len(enabled_feeds) * 100) if enabled_feeds else 0,
        "rolled_out_feed_details": rolled_out_feeds[:10],  # Limit to first 10 for display
        "recommendations": {
            "next_rollout_percentage": min(global_flag["rollout_percentage"] * 2, 100) if global_flag else 10,
            "ready_for_expansion": global_flag["error_count"] < 5 if global_flag else False
        }
    }


@router.post("/auto-analysis/set-rollout")
async def set_auto_analysis_rollout(percentage: int) -> Dict[str, Any]:
    """Set the rollout percentage for auto-analysis.

    Args:
        percentage: Rollout percentage (0-100)
    """
    if percentage < 0 or percentage > 100:
        raise HTTPException(status_code=400, detail="Percentage must be between 0 and 100")

    # Determine status based on percentage
    if percentage == 0:
        status = FeatureFlagStatus.OFF
    elif percentage == 100:
        status = FeatureFlagStatus.ON
    else:
        status = FeatureFlagStatus.CANARY

    feature_flags.set_flag_status("auto_analysis_global", status, percentage)

    return {
        "flag_name": "auto_analysis_global",
        "status": status.value,
        "rollout_percentage": percentage,
        "message": f"Auto-analysis rollout set to {percentage}%"
    }