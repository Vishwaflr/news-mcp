"""
Metrics Service

Service for tracking and aggregating feed metrics, costs, and performance data.
"""

from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Optional
from sqlmodel import Session, select, func
from app.core.logging_config import get_logger
from app.database import engine
from app.models.feed_metrics import FeedMetrics, QueueMetrics
from app.models.core import Feed
from app.models.analysis import AnalysisRun
from app.models.run_queue import QueuedRun, RunStatus
from app.domain.analysis.control import MODEL_PRICING

logger = get_logger(__name__)


class MetricsService:
    """
    Service for collecting, aggregating, and reporting metrics.

    Handles feed-level metrics, cost tracking, and queue performance monitoring.
    """

    def __init__(self):
        self.model_pricing = MODEL_PRICING

    def record_analysis_completion(
        self,
        feed_id: int,
        analysis_run: Dict[str, Any],
        triggered_by: str,
        items_processed: int,
        successful_items: int,
        failed_items: int,
        tokens_used: Dict[str, int],
        cost_breakdown: Dict[str, float],
        processing_time_seconds: float
    ):
        """Record completion of an analysis run for metrics tracking"""
        try:
            with Session(engine) as session:
                today = date.today()

                # Get or create feed metrics for today
                feed_metrics = session.exec(
                    select(FeedMetrics).where(
                        FeedMetrics.feed_id == feed_id,
                        FeedMetrics.metric_date == today
                    )
                ).first()

                if not feed_metrics:
                    feed_metrics = FeedMetrics(
                        feed_id=feed_id,
                        metric_date=today
                    )
                    session.add(feed_metrics)

                # Update analysis counts
                feed_metrics.total_analyses += 1
                if triggered_by == "auto":
                    feed_metrics.auto_analyses += 1
                elif triggered_by == "manual":
                    feed_metrics.manual_analyses += 1
                elif triggered_by == "scheduled":
                    feed_metrics.scheduled_analyses += 1

                # Update item counts
                feed_metrics.total_items_processed += items_processed
                feed_metrics.successful_items += successful_items
                feed_metrics.failed_items += failed_items

                # Update costs
                feed_metrics.total_cost_usd += cost_breakdown.get("total", 0.0)
                feed_metrics.input_cost_usd += cost_breakdown.get("input", 0.0)
                feed_metrics.output_cost_usd += cost_breakdown.get("output", 0.0)
                feed_metrics.cached_cost_usd += cost_breakdown.get("cached", 0.0)

                # Update token usage
                feed_metrics.total_tokens_used += tokens_used.get("total", 0)
                feed_metrics.input_tokens += tokens_used.get("input", 0)
                feed_metrics.output_tokens += tokens_used.get("output", 0)
                feed_metrics.cached_tokens += tokens_used.get("cached", 0)

                # Update performance metrics (weighted average)
                total_runs = feed_metrics.total_analyses
                if total_runs > 1:
                    # Weighted average of processing times
                    prev_total_time = feed_metrics.avg_processing_time_seconds * (total_runs - 1)
                    feed_metrics.avg_processing_time_seconds = (prev_total_time + processing_time_seconds) / total_runs

                    # Weighted average of items per run
                    prev_total_items = feed_metrics.avg_items_per_run * (total_runs - 1)
                    feed_metrics.avg_items_per_run = (prev_total_items + items_processed) / total_runs
                else:
                    feed_metrics.avg_processing_time_seconds = processing_time_seconds
                    feed_metrics.avg_items_per_run = items_processed

                # Update success rate
                if feed_metrics.total_items_processed > 0:
                    feed_metrics.success_rate = (feed_metrics.successful_items / feed_metrics.total_items_processed) * 100

                # Update model usage breakdown
                model_tag = analysis_run.get("model_tag", "unknown")
                if not feed_metrics.model_usage:
                    feed_metrics.model_usage = {}

                if model_tag not in feed_metrics.model_usage:
                    feed_metrics.model_usage[model_tag] = {
                        "runs": 0,
                        "items": 0,
                        "cost": 0.0,
                        "tokens": 0
                    }

                feed_metrics.model_usage[model_tag]["runs"] += 1
                feed_metrics.model_usage[model_tag]["items"] += items_processed
                feed_metrics.model_usage[model_tag]["cost"] += cost_breakdown.get("total", 0.0)
                feed_metrics.model_usage[model_tag]["tokens"] += tokens_used.get("total", 0)

                feed_metrics.updated_at = datetime.utcnow()

                session.commit()
                logger.info(f"Updated feed metrics for feed {feed_id}: {items_processed} items, ${cost_breakdown.get('total', 0.0):.4f}")

        except Exception as e:
            logger.error(f"Error recording analysis completion metrics: {e}")

    def record_queue_processing(
        self,
        queued_run_id: int,
        processing_time_seconds: float,
        queue_time_seconds: float,
        priority: str,
        success: bool
    ):
        """Record queue processing metrics"""
        try:
            with Session(engine) as session:
                now = datetime.utcnow()
                today = now.date()
                current_hour = now.hour

                # Get or create queue metrics for this hour
                queue_metrics = session.exec(
                    select(QueueMetrics).where(
                        QueueMetrics.metric_date == today,
                        QueueMetrics.metric_hour == current_hour
                    )
                ).first()

                if not queue_metrics:
                    queue_metrics = QueueMetrics(
                        metric_date=today,
                        metric_hour=current_hour
                    )
                    session.add(queue_metrics)

                # Update processing counts
                if success:
                    queue_metrics.items_processed += 1
                else:
                    queue_metrics.items_failed += 1

                # Update processing times
                total_items = queue_metrics.items_processed + queue_metrics.items_failed
                if total_items > 1:
                    # Weighted average
                    prev_total = queue_metrics.avg_processing_time_seconds * (total_items - 1)
                    queue_metrics.avg_processing_time_seconds = (prev_total + processing_time_seconds) / total_items

                    prev_queue_total = queue_metrics.avg_queue_time_seconds * (total_items - 1)
                    queue_metrics.avg_queue_time_seconds = (prev_queue_total + queue_time_seconds) / total_items
                else:
                    queue_metrics.avg_processing_time_seconds = processing_time_seconds
                    queue_metrics.avg_queue_time_seconds = queue_time_seconds

                queue_metrics.total_processing_time_seconds += processing_time_seconds
                queue_metrics.total_queue_time_seconds += queue_time_seconds

                # Update min/max times
                if queue_metrics.min_processing_time_seconds == 0 or processing_time_seconds < queue_metrics.min_processing_time_seconds:
                    queue_metrics.min_processing_time_seconds = processing_time_seconds

                if processing_time_seconds > queue_metrics.max_processing_time_seconds:
                    queue_metrics.max_processing_time_seconds = processing_time_seconds

                if queue_metrics.min_queue_time_seconds == 0 or queue_time_seconds < queue_metrics.min_queue_time_seconds:
                    queue_metrics.min_queue_time_seconds = queue_time_seconds

                if queue_time_seconds > queue_metrics.max_queue_time_seconds:
                    queue_metrics.max_queue_time_seconds = queue_time_seconds

                # Update priority breakdown
                if priority == "HIGH":
                    queue_metrics.high_priority_processed += 1
                elif priority == "MEDIUM":
                    queue_metrics.medium_priority_processed += 1
                elif priority == "LOW":
                    queue_metrics.low_priority_processed += 1

                queue_metrics.updated_at = datetime.utcnow()

                session.commit()
                logger.debug(f"Updated queue metrics: {processing_time_seconds:.2f}s processing, {queue_time_seconds:.2f}s queue")

        except Exception as e:
            logger.error(f"Error recording queue processing metrics: {e}")

    def get_feed_metrics(self, feed_id: int, days: int = 7) -> List[Dict[str, Any]]:
        """Get feed metrics for the last N days"""
        try:
            with Session(engine) as session:
                start_date = date.today() - timedelta(days=days)

                metrics = session.exec(
                    select(FeedMetrics)
                    .where(
                        FeedMetrics.feed_id == feed_id,
                        FeedMetrics.metric_date >= start_date
                    )
                    .order_by(FeedMetrics.metric_date.desc())
                ).all()

                return [metric.to_dict() for metric in metrics]

        except Exception as e:
            logger.error(f"Error getting feed metrics: {e}")
            return []

    def get_feed_summary(self, feed_id: int) -> Dict[str, Any]:
        """Get summary metrics for a feed (with fallback to raw data calculation)"""
        try:
            with Session(engine) as session:
                # Get today's metrics
                today = date.today()
                today_metrics = session.exec(
                    select(FeedMetrics).where(
                        FeedMetrics.feed_id == feed_id,
                        FeedMetrics.metric_date == today
                    )
                ).first()

                # Get last 7 days total
                week_ago = today - timedelta(days=7)
                week_metrics = session.exec(
                    select(
                        func.sum(FeedMetrics.total_analyses).label("total_analyses"),
                        func.sum(FeedMetrics.total_cost_usd).label("total_cost"),
                        func.sum(FeedMetrics.total_items_processed).label("total_items"),
                        func.avg(FeedMetrics.success_rate).label("avg_success_rate")
                    ).where(
                        FeedMetrics.feed_id == feed_id,
                        FeedMetrics.metric_date >= week_ago
                    )
                ).first()

                # Get feed name
                feed = session.get(Feed, feed_id)
                feed_name = feed.title if feed else f"Feed {feed_id}"

                # If feed_metrics table has no data, calculate from raw data
                if not today_metrics and not (week_metrics and week_metrics.total_analyses):
                    logger.info(f"No feed_metrics data for feed {feed_id}, calculating from raw data")
                    return self._calculate_feed_summary_from_raw(session, feed_id, feed_name, today)

                return {
                    "feed_id": feed_id,
                    "feed_name": feed_name,
                    "today": today_metrics.to_dict() if today_metrics else None,
                    "last_7_days": {
                        "total_analyses": week_metrics.total_analyses or 0,
                        "total_cost_usd": float(week_metrics.total_cost or 0.0),
                        "total_items": week_metrics.total_items or 0,
                        "avg_success_rate": float(week_metrics.avg_success_rate or 0.0)
                    } if week_metrics else {
                        "total_analyses": 0,
                        "total_cost_usd": 0.0,
                        "total_items": 0,
                        "avg_success_rate": 0.0
                    }
                }

        except Exception as e:
            logger.error(f"Error getting feed summary: {e}")
            return {"error": str(e)}

    def get_system_overview(self) -> Dict[str, Any]:
        """Get system-wide metrics overview (calculated from raw data if metrics table is empty)"""
        try:
            with Session(engine) as session:
                today = date.today()

                # Try to get from metrics table first
                today_totals = session.exec(
                    select(
                        func.sum(FeedMetrics.total_analyses).label("total_analyses"),
                        func.sum(FeedMetrics.total_cost_usd).label("total_cost"),
                        func.sum(FeedMetrics.total_items_processed).label("total_items"),
                        func.count(FeedMetrics.feed_id).label("active_feeds")
                    ).where(FeedMetrics.metric_date == today)
                ).first()

                # If no metrics data available, calculate from raw data
                if not today_totals or not today_totals.total_analyses or today_totals.total_analyses == 0:
                    logger.info("No metrics in feed_metrics table, calculating from raw data")
                    return self._calculate_system_overview_from_raw(session, today)

                # Queue metrics for today
                queue_totals = session.exec(
                    select(
                        func.sum(QueueMetrics.items_processed).label("items_processed"),
                        func.sum(QueueMetrics.items_failed).label("items_failed"),
                        func.avg(QueueMetrics.avg_queue_time_seconds).label("avg_queue_time")
                    ).where(QueueMetrics.metric_date == today)
                ).first()

                # Top spending feeds today
                top_feeds = session.exec(
                    select(FeedMetrics.feed_id, FeedMetrics.total_cost_usd)
                    .where(FeedMetrics.metric_date == today)
                    .order_by(FeedMetrics.total_cost_usd.desc())
                    .limit(5)
                ).all()

                return {
                    "date": today.isoformat(),
                    "system_totals": {
                        "total_analyses": today_totals.total_analyses or 0,
                        "total_cost_usd": float(today_totals.total_cost or 0.0),
                        "total_items": today_totals.total_items or 0,
                        "active_feeds": today_totals.active_feeds or 0
                    },
                    "queue_performance": {
                        "items_processed": queue_totals.items_processed or 0 if queue_totals else 0,
                        "items_failed": queue_totals.items_failed or 0 if queue_totals else 0,
                        "avg_queue_time_seconds": float(queue_totals.avg_queue_time or 0.0) if queue_totals else 0.0
                    },
                    "top_spending_feeds": [
                        {"feed_id": feed.feed_id, "cost_usd": float(feed.total_cost_usd)}
                        for feed in top_feeds
                    ]
                }

        except Exception as e:
            logger.error(f"Error getting system overview: {e}")
            return {"error": str(e)}

    def _calculate_system_overview_from_raw(self, session: Session, today: date) -> Dict[str, Any]:
        """Calculate system overview directly from analysis_runs and analysis_run_items tables"""
        from app.models.analysis import AnalysisRunItem

        # Get today's analysis runs
        today_start = datetime.combine(today, datetime.min.time())
        today_end = datetime.combine(today, datetime.max.time())

        # Count analyses and get distinct feeds
        analyses_today = session.exec(
            select(AnalysisRun).where(
                AnalysisRun.created_at >= today_start,
                AnalysisRun.created_at <= today_end
            )
        ).all()

        total_analyses = len(analyses_today)

        # Extract feed IDs from scope_json
        feed_ids = set()
        for run in analyses_today:
            try:
                # scope_json might be a string or dict
                scope = run.scope_json
                if isinstance(scope, str):
                    import json
                    scope = json.loads(scope)

                if scope and "feed_ids" in scope and scope["feed_ids"]:
                    feed_ids.update(scope["feed_ids"])
            except Exception as e:
                logger.debug(f"Error parsing scope_json for run {run.id}: {e}")
                continue

        active_feeds = len(feed_ids)

        # Calculate costs and items from analysis_run_items
        total_cost = 0.0
        total_items = 0
        items_processed = 0
        items_failed = 0
        total_duration_seconds = 0.0
        completed_runs_count = 0

        for run in analyses_today:
            # Get run items
            run_items = session.exec(
                select(AnalysisRunItem).where(AnalysisRunItem.run_id == run.id)
            ).all()

            total_items += len(run_items)
            for item in run_items:
                if item.state == "completed":
                    items_processed += 1
                elif item.state == "failed":
                    items_failed += 1

            # Calculate analysis duration
            if run.status == "completed" and run.started_at and run.completed_at:
                duration = (run.completed_at - run.started_at).total_seconds()
                total_duration_seconds += duration
                completed_runs_count += 1
            elif run.status == "cancelled" or run.status == "failed":
                items_failed += len(run_items)  # Count cancelled/failed runs' items as failed

            # Calculate cost from params_json (token usage might be stored there)
            try:
                params = run.params_json
                if isinstance(params, str):
                    import json
                    params = json.loads(params)

                if params and "model_tag" in params:
                    model_tag = params.get("model_tag", "claude-3-5-sonnet-20241022")
                    # Estimate cost based on items processed (rough estimate)
                    # Assume average 1000 tokens per item
                    estimated_tokens = {
                        "input": len(run_items) * 500,
                        "output": len(run_items) * 500,
                        "cached": 0
                    }
                    cost_breakdown = self.calculate_cost(model_tag, estimated_tokens)
                    total_cost += cost_breakdown["total"]
            except Exception as e:
                logger.debug(f"Error calculating cost for run {run.id}: {e}")

        # Get top spending feeds (count analyses per feed)
        feed_analysis_count = {}
        for run in analyses_today:
            try:
                scope = run.scope_json
                if isinstance(scope, str):
                    import json
                    scope = json.loads(scope)

                if scope and "feed_ids" in scope and scope["feed_ids"]:
                    for feed_id in scope["feed_ids"]:
                        feed_analysis_count[feed_id] = feed_analysis_count.get(feed_id, 0) + 1
            except Exception as e:
                logger.debug(f"Error parsing scope for run {run.id}: {e}")
                continue

        top_feeds = [
            {"feed_id": feed_id, "cost_usd": 0.0}  # We don't have per-feed cost breakdown without proper metrics
            for feed_id in sorted(feed_analysis_count.keys(), key=lambda x: feed_analysis_count[x], reverse=True)[:5]
        ]

        # Calculate average analysis duration
        avg_duration = (total_duration_seconds / completed_runs_count) if completed_runs_count > 0 else 0.0

        return {
            "date": today.isoformat(),
            "system_totals": {
                "total_analyses": total_analyses,
                "total_cost_usd": round(total_cost, 4),
                "total_items": total_items,
                "active_feeds": active_feeds
            },
            "queue_performance": {
                "items_processed": items_processed,
                "items_failed": items_failed,
                "avg_queue_time_seconds": round(avg_duration, 2)
            },
            "top_spending_feeds": top_feeds
        }

    def _calculate_feed_summary_from_raw(self, session: Session, feed_id: int, feed_name: str, today: date) -> Dict[str, Any]:
        """Calculate feed summary directly from analysis_run_items when feed_metrics is empty"""
        from app.models.analysis import AnalysisRunItem
        from app.models.core import Item

        # Calculate today's metrics
        today_start = datetime.combine(today, datetime.min.time())
        today_end = datetime.combine(today, datetime.max.time())

        # Get today's analysis run items for this feed
        today_items = session.exec(
            select(AnalysisRunItem)
            .join(Item, AnalysisRunItem.item_id == Item.id)
            .join(AnalysisRun, AnalysisRunItem.run_id == AnalysisRun.id)
            .where(
                Item.feed_id == feed_id,
                AnalysisRun.created_at >= today_start,
                AnalysisRun.created_at <= today_end
            )
        ).all()

        # Get unique run IDs for today
        today_run_ids = set(item.run_id for item in today_items)
        total_analyses_today = len(today_run_ids)

        # Count completed/failed items for today
        today_completed = sum(1 for item in today_items if item.state == "completed")
        today_failed = sum(1 for item in today_items if item.state == "failed")
        total_today_items = len(today_items)

        # Calculate today's success rate
        today_success_rate = (today_completed / total_today_items * 100) if total_today_items > 0 else 0.0

        # Estimate today's cost
        estimated_today_cost = total_today_items * 0.001

        # Calculate last 7 days metrics
        week_ago = today - timedelta(days=7)
        week_start = datetime.combine(week_ago, datetime.min.time())

        week_items = session.exec(
            select(AnalysisRunItem)
            .join(Item, AnalysisRunItem.item_id == Item.id)
            .join(AnalysisRun, AnalysisRunItem.run_id == AnalysisRun.id)
            .where(
                Item.feed_id == feed_id,
                AnalysisRun.created_at >= week_start,
                AnalysisRun.created_at <= today_end
            )
        ).all()

        # Get unique run IDs for last 7 days
        week_run_ids = set(item.run_id for item in week_items)
        total_analyses_week = len(week_run_ids)

        # Count completed/failed items
        week_completed = sum(1 for item in week_items if item.state == "completed")
        week_failed = sum(1 for item in week_items if item.state == "failed")
        total_week_items = len(week_items)

        # Calculate success rate
        avg_success_rate = (week_completed / total_week_items * 100) if total_week_items > 0 else 0.0

        # Estimate cost (rough estimate based on items)
        # Assume ~1000 tokens per item, using default pricing
        estimated_cost = total_week_items * 0.001  # Very rough estimate

        logger.info(
            f"Calculated feed {feed_id} metrics from raw data: "
            f"Today: {total_analyses_today} analyses, {total_today_items} items, {today_completed} completed; "
            f"Week: {total_analyses_week} analyses, {total_week_items} items, {week_completed} completed"
        )

        # Build today's metrics structure (matching FeedMetrics.to_dict() format)
        today_data = {
            "metric_date": today.isoformat(),
            "analysis_counts": {
                "total": total_analyses_today,
                "auto": 0,  # We don't track this in raw data
                "manual": 0,
                "scheduled": 0
            },
            "item_counts": {
                "total_processed": total_today_items,
                "successful": today_completed,
                "failed": today_failed
            },
            "costs": {
                "total_usd": round(estimated_today_cost, 4),
                "input_usd": 0.0,
                "output_usd": 0.0,
                "cached_usd": 0.0
            },
            "tokens": {
                "total": 0,
                "input": 0,
                "output": 0,
                "cached": 0
            },
            "performance": {
                "avg_processing_time": 0.0,
                "avg_items_per_run": (total_today_items / total_analyses_today) if total_analyses_today > 0 else 0.0,
                "success_rate": round(today_success_rate, 1)
            },
            "queue_metrics": {
                "total_queue_time": 0.0,
                "avg_queue_time": 0.0,
                "max_queue_time": 0.0
            },
            "model_usage": {}
        } if total_today_items > 0 else None

        return {
            "feed_id": feed_id,
            "feed_name": feed_name,
            "today": today_data,
            "last_7_days": {
                "total_analyses": total_analyses_week,
                "total_cost_usd": round(estimated_cost, 4),
                "total_items": total_week_items,
                "avg_success_rate": round(avg_success_rate, 1)
            }
        }

    def calculate_cost(self, model_tag: str, tokens_used: Dict[str, int]) -> Dict[str, float]:
        """Calculate cost breakdown for token usage"""
        if model_tag not in self.model_pricing:
            logger.warning(f"Unknown model tag: {model_tag}")
            return {"total": 0.0, "input": 0.0, "output": 0.0, "cached": 0.0}

        pricing = self.model_pricing[model_tag]

        # Convert tokens to millions for pricing calculation
        input_millions = tokens_used.get("input", 0) / 1_000_000
        output_millions = tokens_used.get("output", 0) / 1_000_000
        cached_millions = tokens_used.get("cached", 0) / 1_000_000

        input_cost = input_millions * pricing["input"]
        output_cost = output_millions * pricing["output"]
        cached_cost = cached_millions * pricing["cached"]
        total_cost = input_cost + output_cost + cached_cost

        return {
            "total": total_cost,
            "input": input_cost,
            "output": output_cost,
            "cached": cached_cost
        }


# Singleton instance
_metrics_service = None


def get_metrics_service() -> MetricsService:
    """Get the singleton metrics service instance"""
    global _metrics_service
    if _metrics_service is None:
        _metrics_service = MetricsService()
    return _metrics_service