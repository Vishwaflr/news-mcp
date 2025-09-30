"""
Auto-Analysis Monitoring API

Provides monitoring endpoints for the auto-analysis system.
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any, List

from app.services.auto_analysis_monitor import auto_analysis_monitor
from app.utils.feature_flags import feature_flags, FeatureFlagStatus

router = APIRouter(prefix="/api/auto-analysis/monitoring", tags=["monitoring", "auto-analysis"])


@router.get("/metrics")
async def get_auto_analysis_metrics() -> Dict[str, Any]:
    """Get comprehensive auto-analysis system metrics."""
    try:
        metrics = auto_analysis_monitor.get_system_metrics()
        return {
            "success": True,
            "metrics": {
                "runs": {
                    "total_today": metrics.total_runs_today,
                    "successful": metrics.successful_runs,
                    "failed": metrics.failed_runs,
                    "shadow": metrics.shadow_runs,
                    "error_rate": f"{metrics.error_rate:.1%}"
                },
                "items": {
                    "analyzed_today": metrics.items_analyzed_today,
                    "average_per_run": round(metrics.average_items_per_run, 1)
                },
                "performance": {
                    "average_duration_seconds": round(metrics.average_run_duration_seconds, 1),
                    "queue_backlog": metrics.queue_backlog
                },
                "cost": {
                    "estimated_today": f"${metrics.estimated_cost_today:.2f}",
                    "per_item": f"${(metrics.estimated_cost_today / max(metrics.items_analyzed_today, 1)):.4f}"
                },
                "rollout": {
                    "feeds_with_auto_analysis": metrics.feeds_with_auto_analysis,
                    "feeds_in_rollout": metrics.feeds_in_rollout,
                    "rollout_percentage": f"{(metrics.feeds_in_rollout / max(metrics.feeds_with_auto_analysis, 1) * 100):.1f}%"
                }
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/metrics/feed/{feed_id}")
async def get_feed_auto_analysis_metrics(feed_id: int) -> Dict[str, Any]:
    """Get auto-analysis metrics for a specific feed."""
    try:
        metrics = auto_analysis_monitor.get_feed_metrics(feed_id)
        return {
            "success": True,
            "feed": {
                "id": metrics.feed_id,
                "title": metrics.feed_title
            },
            "metrics": {
                "runs_today": metrics.runs_today,
                "items_analyzed_today": metrics.items_analyzed_today,
                "last_run_at": metrics.last_run_at.isoformat() if metrics.last_run_at else None,
                "success_rate": f"{metrics.success_rate:.1%}",
                "average_duration_seconds": round(metrics.average_duration_seconds, 1),
                "estimated_cost": f"${metrics.estimated_cost:.2f}"
            }
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/alerts")
async def get_auto_analysis_alerts() -> Dict[str, Any]:
    """Get active alerts for the auto-analysis system."""
    try:
        alerts = auto_analysis_monitor.check_alerts()

        # Group alerts by level
        critical_alerts = [a for a in alerts if a["level"] == "critical"]
        warning_alerts = [a for a in alerts if a["level"] == "warning"]

        return {
            "success": True,
            "alert_count": len(alerts),
            "critical_count": len(critical_alerts),
            "warning_count": len(warning_alerts),
            "alerts": {
                "critical": critical_alerts,
                "warning": warning_alerts
            },
            "status": "healthy" if not critical_alerts else "critical" if critical_alerts else "warning"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/rollout/recommendations")
async def get_rollout_recommendations() -> Dict[str, Any]:
    """Get recommendations for auto-analysis rollout progression."""
    try:
        recommendations = auto_analysis_monitor.get_rollout_recommendations()
        return {
            "success": True,
            "recommendations": recommendations
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/rollout/apply-recommendation")
async def apply_rollout_recommendation() -> Dict[str, Any]:
    """Apply the recommended rollout percentage."""
    try:
        recommendations = auto_analysis_monitor.get_rollout_recommendations()

        if recommendations["action"] == "maintain":
            return {
                "success": True,
                "message": "No action needed - system is fully rolled out",
                "current_percentage": recommendations["current_rollout_percentage"]
            }
        elif recommendations["action"] == "hold":
            return {
                "success": False,
                "message": "Cannot expand rollout - metrics need improvement",
                "blockers": recommendations.get("blockers", []),
                "current_percentage": recommendations["current_rollout_percentage"]
            }
        else:
            # Apply the recommendation
            new_percentage = recommendations["next_percentage"]

            # Determine status based on percentage
            if new_percentage == 0:
                status = FeatureFlagStatus.OFF
            elif new_percentage == 100:
                status = FeatureFlagStatus.ON
            else:
                status = FeatureFlagStatus.CANARY

            feature_flags.set_flag_status("auto_analysis_global", status, new_percentage)

            return {
                "success": True,
                "message": f"Rollout {recommendations['action']}ed to {new_percentage}%",
                "previous_percentage": recommendations["current_rollout_percentage"],
                "new_percentage": new_percentage,
                "action": recommendations["action"]
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dashboard")
async def get_monitoring_dashboard() -> Dict[str, Any]:
    """Get a comprehensive monitoring dashboard for auto-analysis."""
    try:
        metrics = auto_analysis_monitor.get_system_metrics()
        alerts = auto_analysis_monitor.check_alerts()
        recommendations = auto_analysis_monitor.get_rollout_recommendations()

        # Get feature flag status
        global_flag = feature_flags.get_flag_status("auto_analysis_global")
        shadow_flag = feature_flags.get_flag_status("auto_analysis_shadow")

        return {
            "success": True,
            "timestamp": datetime.utcnow().isoformat(),
            "feature_flags": {
                "global": global_flag,
                "shadow": shadow_flag
            },
            "metrics_summary": {
                "runs_today": metrics.total_runs_today,
                "success_rate": f"{(1 - metrics.error_rate):.1%}",
                "items_analyzed": metrics.items_analyzed_today,
                "estimated_cost": f"${metrics.estimated_cost_today:.2f}",
                "feeds_active": f"{metrics.feeds_in_rollout}/{metrics.feeds_with_auto_analysis}"
            },
            "health_status": "critical" if any(a["level"] == "critical" for a in alerts) else "warning" if alerts else "healthy",
            "alert_summary": {
                "total": len(alerts),
                "critical": len([a for a in alerts if a["level"] == "critical"]),
                "warning": len([a for a in alerts if a["level"] == "warning"])
            },
            "rollout_status": {
                "current_percentage": recommendations["current_rollout_percentage"],
                "recommendation": recommendations["recommendation"],
                "next_action": recommendations["action"]
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/alerts/thresholds")
async def update_alert_thresholds(thresholds: Dict[str, float]) -> Dict[str, Any]:
    """Update alert thresholds for monitoring."""
    try:
        for key, value in thresholds.items():
            if key in auto_analysis_monitor.alert_thresholds:
                auto_analysis_monitor.alert_thresholds[key] = value

        return {
            "success": True,
            "message": "Alert thresholds updated",
            "current_thresholds": auto_analysis_monitor.alert_thresholds
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Import datetime for timestamp
from datetime import datetime