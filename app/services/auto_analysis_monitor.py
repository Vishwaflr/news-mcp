"""
Auto-Analysis Monitoring Service

Provides monitoring, metrics, and alerting for the auto-analysis system.
"""

from app.core.logging_config import get_logger
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from sqlmodel import Session, select, func
from dataclasses import dataclass
import json

from app.database import engine
from app.models.core import Feed
from app.models.analysis import AnalysisRun

logger = get_logger(__name__)


@dataclass
class AutoAnalysisMetrics:
    """Container for auto-analysis metrics."""
    total_runs_today: int = 0
    successful_runs: int = 0
    failed_runs: int = 0
    shadow_runs: int = 0
    items_analyzed_today: int = 0
    average_items_per_run: float = 0.0
    average_run_duration_seconds: float = 0.0
    estimated_cost_today: float = 0.0
    feeds_with_auto_analysis: int = 0
    feeds_in_rollout: int = 0
    queue_backlog: int = 0
    error_rate: float = 0.0


@dataclass
class FeedAnalysisMetrics:
    """Metrics for a specific feed's auto-analysis."""
    feed_id: int
    feed_title: str
    runs_today: int
    items_analyzed_today: int
    last_run_at: Optional[datetime]
    success_rate: float
    average_duration_seconds: float
    estimated_cost: float


class AutoAnalysisMonitor:
    """Monitor and track auto-analysis system health and metrics."""

    def __init__(self):
        self.alert_thresholds = {
            "queue_backlog_warning": 100,
            "queue_backlog_critical": 500,
            "error_rate_warning": 0.05,  # 5%
            "error_rate_critical": 0.10,  # 10%
            "daily_cost_warning": 50.0,  # $50
            "daily_cost_critical": 100.0,  # $100
            "run_duration_warning": 300,  # 5 minutes
            "run_duration_critical": 600,  # 10 minutes
        }
        self.cost_per_1k_tokens = {
            "gpt-4.1-nano": 0.002,  # $0.002 per 1K tokens
            "gpt-4o-mini": 0.00015,  # Cheaper alternative
            "gpt-3.5-turbo": 0.0005,
        }

    def get_system_metrics(self) -> AutoAnalysisMetrics:
        """Get comprehensive system-wide auto-analysis metrics."""
        metrics = AutoAnalysisMetrics()

        with Session(engine) as session:
            now = datetime.utcnow()
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

            # Get auto-triggered runs from today
            today_runs = session.exec(
                select(AnalysisRun).where(
                    AnalysisRun.created_at >= today_start,
                    AnalysisRun.triggered_by == "auto"
                )
            ).all()

            metrics.total_runs_today = len(today_runs)

            # Count status types
            for run in today_runs:
                if run.status == "completed":
                    metrics.successful_runs += 1
                elif run.status in ["failed", "error"]:
                    metrics.failed_runs += 1
                elif "shadow" in (run.scope_json or ""):
                    metrics.shadow_runs += 1

                # Count items analyzed
                try:
                    scope_data = json.loads(run.scope_json) if isinstance(run.scope_json, str) else run.scope_json
                    items = scope_data.get("item_ids", [])
                    metrics.items_analyzed_today += len(items)
                except:
                    pass

                # Calculate duration
                if run.completed_at and run.started_at:
                    duration = (run.completed_at - run.started_at).total_seconds()
                    metrics.average_run_duration_seconds += duration

            # Calculate averages
            if metrics.total_runs_today > 0:
                metrics.average_items_per_run = metrics.items_analyzed_today / metrics.total_runs_today
                metrics.average_run_duration_seconds = metrics.average_run_duration_seconds / metrics.total_runs_today
                metrics.error_rate = metrics.failed_runs / metrics.total_runs_today

                # Estimate cost (rough calculation)
                # Assume 500 tokens per item on average
                total_tokens = metrics.items_analyzed_today * 500
                metrics.estimated_cost_today = (total_tokens / 1000) * self.cost_per_1k_tokens.get("gpt-4.1-nano", 0.002)

            # Count feeds with auto-analysis
            feeds_with_auto = session.exec(
                select(Feed).where(Feed.auto_analyze_enabled == True)
            ).all()
            metrics.feeds_with_auto_analysis = len(feeds_with_auto)

            # Check rollout status
            from app.utils.feature_flags import feature_flags
            metrics.feeds_in_rollout = sum(
                1 for feed in feeds_with_auto
                if feature_flags.is_enabled("auto_analysis_global", str(feed.id))
            )

            # Check pending queue (simplified - would need pending_auto_analysis table)
            # For now, estimate based on recent fetch activity
            metrics.queue_backlog = 0  # Placeholder

        return metrics

    def get_feed_metrics(self, feed_id: int) -> FeedAnalysisMetrics:
        """Get metrics for a specific feed's auto-analysis."""
        with Session(engine) as session:
            feed = session.get(Feed, feed_id)
            if not feed:
                raise ValueError(f"Feed {feed_id} not found")

            now = datetime.utcnow()
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

            # Get feed's auto-analysis runs
            from app.models.core import Item
            feed_items = session.exec(
                select(Item.id).where(Item.feed_id == feed_id)
            ).all()
            feed_item_ids = set(feed_items)

            # Find runs that analyzed this feed's items
            all_auto_runs = session.exec(
                select(AnalysisRun).where(
                    AnalysisRun.created_at >= today_start,
                    AnalysisRun.triggered_by == "auto"
                )
            ).all()

            feed_runs = []
            items_analyzed = 0
            total_duration = 0
            successful = 0

            for run in all_auto_runs:
                try:
                    scope_data = json.loads(run.scope_json) if isinstance(run.scope_json, str) else run.scope_json
                    run_item_ids = set(scope_data.get("item_ids", []))

                    if run_item_ids.intersection(feed_item_ids):
                        feed_runs.append(run)
                        items_analyzed += len(run_item_ids.intersection(feed_item_ids))

                        if run.status == "completed":
                            successful += 1

                        if run.completed_at and run.started_at:
                            total_duration += (run.completed_at - run.started_at).total_seconds()
                except:
                    continue

            last_run = max(feed_runs, key=lambda r: r.created_at) if feed_runs else None

            return FeedAnalysisMetrics(
                feed_id=feed_id,
                feed_title=feed.title,
                runs_today=len(feed_runs),
                items_analyzed_today=items_analyzed,
                last_run_at=last_run.created_at if last_run else None,
                success_rate=(successful / len(feed_runs)) if feed_runs else 0.0,
                average_duration_seconds=(total_duration / len(feed_runs)) if feed_runs else 0.0,
                estimated_cost=(items_analyzed * 500 / 1000) * self.cost_per_1k_tokens.get("gpt-4.1-nano", 0.002)
            )

    def check_alerts(self) -> List[Dict[str, Any]]:
        """Check for alert conditions and return active alerts."""
        alerts = []
        metrics = self.get_system_metrics()

        # Queue backlog alerts
        if metrics.queue_backlog > self.alert_thresholds["queue_backlog_critical"]:
            alerts.append({
                "level": "critical",
                "type": "queue_backlog",
                "message": f"Critical: Queue backlog at {metrics.queue_backlog} items",
                "value": metrics.queue_backlog,
                "threshold": self.alert_thresholds["queue_backlog_critical"]
            })
        elif metrics.queue_backlog > self.alert_thresholds["queue_backlog_warning"]:
            alerts.append({
                "level": "warning",
                "type": "queue_backlog",
                "message": f"Warning: Queue backlog at {metrics.queue_backlog} items",
                "value": metrics.queue_backlog,
                "threshold": self.alert_thresholds["queue_backlog_warning"]
            })

        # Error rate alerts
        if metrics.error_rate > self.alert_thresholds["error_rate_critical"]:
            alerts.append({
                "level": "critical",
                "type": "error_rate",
                "message": f"Critical: Error rate at {metrics.error_rate:.1%}",
                "value": metrics.error_rate,
                "threshold": self.alert_thresholds["error_rate_critical"]
            })
        elif metrics.error_rate > self.alert_thresholds["error_rate_warning"]:
            alerts.append({
                "level": "warning",
                "type": "error_rate",
                "message": f"Warning: Error rate at {metrics.error_rate:.1%}",
                "value": metrics.error_rate,
                "threshold": self.alert_thresholds["error_rate_warning"]
            })

        # Cost alerts
        if metrics.estimated_cost_today > self.alert_thresholds["daily_cost_critical"]:
            alerts.append({
                "level": "critical",
                "type": "cost",
                "message": f"Critical: Daily cost at ${metrics.estimated_cost_today:.2f}",
                "value": metrics.estimated_cost_today,
                "threshold": self.alert_thresholds["daily_cost_critical"]
            })
        elif metrics.estimated_cost_today > self.alert_thresholds["daily_cost_warning"]:
            alerts.append({
                "level": "warning",
                "type": "cost",
                "message": f"Warning: Daily cost at ${metrics.estimated_cost_today:.2f}",
                "value": metrics.estimated_cost_today,
                "threshold": self.alert_thresholds["daily_cost_warning"]
            })

        # Duration alerts
        if metrics.average_run_duration_seconds > self.alert_thresholds["run_duration_critical"]:
            alerts.append({
                "level": "critical",
                "type": "duration",
                "message": f"Critical: Average run duration at {metrics.average_run_duration_seconds:.1f}s",
                "value": metrics.average_run_duration_seconds,
                "threshold": self.alert_thresholds["run_duration_critical"]
            })
        elif metrics.average_run_duration_seconds > self.alert_thresholds["run_duration_warning"]:
            alerts.append({
                "level": "warning",
                "type": "duration",
                "message": f"Warning: Average run duration at {metrics.average_run_duration_seconds:.1f}s",
                "value": metrics.average_run_duration_seconds,
                "threshold": self.alert_thresholds["run_duration_warning"]
            })

        return alerts

    def get_rollout_recommendations(self) -> Dict[str, Any]:
        """Get recommendations for rollout progression."""
        metrics = self.get_system_metrics()
        from app.utils.feature_flags import feature_flags

        current_flag = feature_flags.get_flag_status("auto_analysis_global")
        current_percentage = current_flag.get("rollout_percentage", 0) if current_flag else 0

        recommendations = {
            "current_rollout_percentage": current_percentage,
            "metrics_summary": {
                "error_rate": f"{metrics.error_rate:.1%}",
                "success_rate": f"{(1 - metrics.error_rate):.1%}",
                "daily_cost": f"${metrics.estimated_cost_today:.2f}",
                "feeds_in_rollout": metrics.feeds_in_rollout,
                "total_eligible_feeds": metrics.feeds_with_auto_analysis
            }
        }

        # Check if ready for expansion
        can_expand = (
            metrics.error_rate < 0.05 and  # Less than 5% error rate
            metrics.total_runs_today >= 10 and  # Sufficient sample size
            metrics.estimated_cost_today < 75  # Under budget
        )

        if current_percentage == 0:
            recommendations["recommendation"] = "Start with 10% rollout"
            recommendations["next_percentage"] = 10
            recommendations["action"] = "enable"
        elif current_percentage >= 100:
            recommendations["recommendation"] = "Fully rolled out"
            recommendations["next_percentage"] = 100
            recommendations["action"] = "maintain"
        elif can_expand:
            next_pct = min(current_percentage * 2, 100)
            recommendations["recommendation"] = f"Expand rollout to {next_pct}%"
            recommendations["next_percentage"] = next_pct
            recommendations["action"] = "expand"
        else:
            recommendations["recommendation"] = "Hold at current level - metrics need improvement"
            recommendations["next_percentage"] = current_percentage
            recommendations["action"] = "hold"
            recommendations["blockers"] = []

            if metrics.error_rate >= 0.05:
                recommendations["blockers"].append(f"Error rate too high: {metrics.error_rate:.1%}")
            if metrics.total_runs_today < 10:
                recommendations["blockers"].append(f"Insufficient data: only {metrics.total_runs_today} runs today")
            if metrics.estimated_cost_today >= 75:
                recommendations["blockers"].append(f"Cost too high: ${metrics.estimated_cost_today:.2f}")

        return recommendations


# Global monitor instance
auto_analysis_monitor = AutoAnalysisMonitor()