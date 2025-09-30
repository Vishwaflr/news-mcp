"""
Feed Limits Service

Service for managing and enforcing feed-specific limits and quotas.
"""

from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Optional, Tuple
from sqlmodel import Session, select, func
from app.core.logging_config import get_logger
from app.database import engine
from app.models.feed_limits import FeedLimit, FeedViolation
from app.models.feed_metrics import FeedMetrics

logger = get_logger(__name__)


class ViolationType:
    """Constants for violation types"""
    COST_LIMIT = "COST_LIMIT"
    FREQUENCY_LIMIT = "FREQUENCY_LIMIT"
    ERROR_RATE = "ERROR_RATE"
    ITEM_LIMIT = "ITEM_LIMIT"
    INTERVAL_LIMIT = "INTERVAL_LIMIT"


class ActionType:
    """Constants for actions taken on violations"""
    LOGGED = "LOGGED"
    DISABLED = "DISABLED"
    ALERT_SENT = "ALERT_SENT"
    EMERGENCY_STOP = "EMERGENCY_STOP"
    QUEUE_BLOCKED = "QUEUE_BLOCKED"


class FeedLimitsService:
    """
    Service for managing feed limits and monitoring violations.

    Provides functionality to:
    - Configure limits per feed
    - Check if operations are allowed
    - Record violations
    - Auto-disable feeds when limits are exceeded
    """

    def __init__(self):
        pass

    def get_feed_limits(self, feed_id: int) -> Optional[FeedLimit]:
        """Get limits configuration for a specific feed"""
        try:
            with Session(engine) as session:
                limits = session.exec(
                    select(FeedLimit).where(FeedLimit.feed_id == feed_id)
                ).first()
                return limits
        except Exception as e:
            logger.error(f"Error getting feed limits for feed {feed_id}: {e}")
            return None

    def set_feed_limits(
        self,
        feed_id: int,
        max_analyses_per_day: Optional[int] = None,
        max_analyses_per_hour: Optional[int] = None,
        min_interval_minutes: Optional[int] = None,
        daily_cost_limit: Optional[float] = None,
        monthly_cost_limit: Optional[float] = None,
        cost_alert_threshold: Optional[float] = None,
        max_items_per_analysis: Optional[int] = None,
        emergency_stop_enabled: bool = False,
        auto_disable_on_error_rate: Optional[float] = None,
        auto_disable_on_cost_breach: bool = True,
        alert_email: Optional[str] = None,
        custom_settings: Optional[Dict[str, Any]] = None
    ) -> FeedLimit:
        """Create or update limits for a feed"""
        try:
            with Session(engine) as session:
                # Get existing limits or create new
                limits = session.exec(
                    select(FeedLimit).where(FeedLimit.feed_id == feed_id)
                ).first()

                if not limits:
                    limits = FeedLimit(feed_id=feed_id)
                    session.add(limits)

                # Update values if provided
                if max_analyses_per_day is not None:
                    limits.max_analyses_per_day = max_analyses_per_day
                if max_analyses_per_hour is not None:
                    limits.max_analyses_per_hour = max_analyses_per_hour
                if min_interval_minutes is not None:
                    limits.min_interval_minutes = min_interval_minutes
                if daily_cost_limit is not None:
                    limits.daily_cost_limit = daily_cost_limit
                if monthly_cost_limit is not None:
                    limits.monthly_cost_limit = monthly_cost_limit
                if cost_alert_threshold is not None:
                    limits.cost_alert_threshold = cost_alert_threshold
                if max_items_per_analysis is not None:
                    limits.max_items_per_analysis = max_items_per_analysis
                if emergency_stop_enabled is not None:
                    limits.emergency_stop_enabled = emergency_stop_enabled
                if auto_disable_on_error_rate is not None:
                    limits.auto_disable_on_error_rate = auto_disable_on_error_rate
                if auto_disable_on_cost_breach is not None:
                    limits.auto_disable_on_cost_breach = auto_disable_on_cost_breach
                if alert_email is not None:
                    limits.alert_email = alert_email
                if custom_settings is not None:
                    limits.custom_settings = custom_settings

                limits.updated_at = datetime.utcnow()

                session.commit()
                session.refresh(limits)

                logger.info(f"Updated limits for feed {feed_id}")
                return limits

        except Exception as e:
            logger.error(f"Error setting feed limits for feed {feed_id}: {e}")
            raise

    def check_analysis_allowed(self, feed_id: int, items_count: int = 0) -> Tuple[bool, Optional[str]]:
        """
        Check if an analysis is allowed for a feed based on configured limits.

        Returns:
            Tuple[bool, Optional[str]]: (is_allowed, reason_if_blocked)
        """
        try:
            limits = self.get_feed_limits(feed_id)
            if not limits or not limits.is_active:
                return True, None

            # Check if feed is in emergency stop
            if limits.emergency_stop_enabled:
                return False, "Feed is in emergency stop mode"

            now = datetime.utcnow()
            today = now.date()

            with Session(engine) as session:
                # Check daily analysis limit
                if limits.max_analyses_per_day:
                    daily_metrics = session.exec(
                        select(FeedMetrics).where(
                            FeedMetrics.feed_id == feed_id,
                            FeedMetrics.metric_date == today
                        )
                    ).first()

                    if daily_metrics and daily_metrics.total_analyses >= limits.max_analyses_per_day:
                        self._record_violation(
                            feed_id,
                            ViolationType.FREQUENCY_LIMIT,
                            limits.max_analyses_per_day,
                            daily_metrics.total_analyses + 1,
                            ActionType.QUEUE_BLOCKED
                        )
                        return False, f"Daily analysis limit reached ({limits.max_analyses_per_day})"

                # Check hourly analysis limit using join with items
                if limits.max_analyses_per_hour:
                    from app.models.analysis import AnalysisRun, AnalysisRunItem
                    from app.models.core import Item

                    hour_ago = now - timedelta(hours=1)
                    recent_analyses = session.exec(
                        select(func.count(func.distinct(AnalysisRun.id)))
                        .select_from(AnalysisRun)
                        .join(AnalysisRunItem, AnalysisRunItem.run_id == AnalysisRun.id)
                        .join(Item, Item.id == AnalysisRunItem.item_id)
                        .where(
                            Item.feed_id == feed_id,
                            AnalysisRun.created_at >= hour_ago
                        )
                    ).first()

                    if recent_analyses and recent_analyses >= limits.max_analyses_per_hour:
                        self._record_violation(
                            feed_id,
                            ViolationType.FREQUENCY_LIMIT,
                            limits.max_analyses_per_hour,
                            recent_analyses + 1,
                            ActionType.QUEUE_BLOCKED
                        )
                        return False, f"Hourly analysis limit reached ({limits.max_analyses_per_hour})"

                # Check minimum interval using join with items
                if limits.min_interval_minutes:
                    from app.models.analysis import AnalysisRun, AnalysisRunItem
                    from app.models.core import Item

                    interval_ago = now - timedelta(minutes=limits.min_interval_minutes)
                    recent_analysis = session.exec(
                        select(AnalysisRun)
                        .join(AnalysisRunItem, AnalysisRunItem.run_id == AnalysisRun.id)
                        .join(Item, Item.id == AnalysisRunItem.item_id)
                        .where(
                            Item.feed_id == feed_id,
                            AnalysisRun.created_at >= interval_ago
                        )
                        .order_by(AnalysisRun.created_at.desc())
                    ).first()

                    if recent_analysis:
                        self._record_violation(
                            feed_id,
                            ViolationType.INTERVAL_LIMIT,
                            limits.min_interval_minutes,
                            (now - recent_analysis.created_at).total_seconds() / 60,
                            ActionType.QUEUE_BLOCKED
                        )
                        return False, f"Minimum interval not met (requires {limits.min_interval_minutes} minutes)"

                # Check items per analysis limit
                if limits.max_items_per_analysis and items_count > limits.max_items_per_analysis:
                    self._record_violation(
                        feed_id,
                        ViolationType.ITEM_LIMIT,
                        limits.max_items_per_analysis,
                        items_count,
                        ActionType.QUEUE_BLOCKED
                    )
                    return False, f"Items count exceeds limit ({limits.max_items_per_analysis})"

                # Check daily cost limit
                if limits.daily_cost_limit:
                    daily_metrics = session.exec(
                        select(FeedMetrics).where(
                            FeedMetrics.feed_id == feed_id,
                            FeedMetrics.metric_date == today
                        )
                    ).first()

                    if daily_metrics and daily_metrics.total_cost_usd >= limits.daily_cost_limit:
                        self._record_violation(
                            feed_id,
                            ViolationType.COST_LIMIT,
                            limits.daily_cost_limit,
                            daily_metrics.total_cost_usd,
                            ActionType.DISABLED if limits.auto_disable_on_cost_breach else ActionType.QUEUE_BLOCKED
                        )

                        if limits.auto_disable_on_cost_breach:
                            self._disable_feed(feed_id, "Daily cost limit exceeded")

                        return False, f"Daily cost limit reached (${limits.daily_cost_limit})"

            return True, None

        except Exception as e:
            logger.error(f"Error checking analysis permission for feed {feed_id}: {e}")
            return False, f"Internal error: {str(e)}"

    def check_cost_after_analysis(self, feed_id: int, analysis_cost: float) -> bool:
        """
        Check if the cost after an analysis would exceed limits.
        Used for post-analysis validation and alerts.
        """
        try:
            limits = self.get_feed_limits(feed_id)
            if not limits:
                return True

            today = date.today()

            with Session(engine) as session:
                daily_metrics = session.exec(
                    select(FeedMetrics).where(
                        FeedMetrics.feed_id == feed_id,
                        FeedMetrics.metric_date == today
                    )
                ).first()

                current_cost = daily_metrics.total_cost_usd if daily_metrics else 0.0
                new_total = current_cost + analysis_cost

                # Check daily cost limit
                if limits.daily_cost_limit and new_total > limits.daily_cost_limit:
                    self._record_violation(
                        feed_id,
                        ViolationType.COST_LIMIT,
                        limits.daily_cost_limit,
                        new_total,
                        ActionType.DISABLED if limits.auto_disable_on_cost_breach else ActionType.ALERT_SENT
                    )

                    if limits.auto_disable_on_cost_breach:
                        self._disable_feed(feed_id, "Daily cost limit exceeded after analysis")

                    return False

                # Check cost alert threshold
                if limits.cost_alert_threshold and limits.daily_cost_limit:
                    threshold_amount = limits.daily_cost_limit * (limits.cost_alert_threshold / 100)
                    if new_total > threshold_amount and current_cost <= threshold_amount:
                        logger.warning(f"Feed {feed_id} exceeded cost alert threshold: ${new_total:.4f}")
                        # Here you could send alert notifications

            return True

        except Exception as e:
            logger.error(f"Error checking post-analysis cost for feed {feed_id}: {e}")
            return True

    def get_feed_violations(
        self,
        feed_id: int,
        days: int = 7,
        violation_type: Optional[str] = None
    ) -> List[FeedViolation]:
        """Get recent violations for a feed"""
        try:
            with Session(engine) as session:
                start_date = date.today() - timedelta(days=days)

                query = select(FeedViolation).where(
                    FeedViolation.feed_id == feed_id,
                    FeedViolation.violation_date >= start_date
                )

                if violation_type:
                    query = query.where(FeedViolation.violation_type == violation_type)

                violations = session.exec(
                    query.order_by(FeedViolation.violation_time.desc())
                ).all()

                return list(violations)

        except Exception as e:
            logger.error(f"Error getting violations for feed {feed_id}: {e}")
            return []

    def get_system_violations_summary(self, days: int = 7) -> Dict[str, Any]:
        """Get system-wide violations summary"""
        try:
            with Session(engine) as session:
                start_date = date.today() - timedelta(days=days)

                # Count violations by type
                violation_counts = session.exec(
                    select(
                        FeedViolation.violation_type,
                        func.count(FeedViolation.id).label("count")
                    ).where(
                        FeedViolation.violation_date >= start_date
                    ).group_by(FeedViolation.violation_type)
                ).all()

                # Get feeds with most violations
                feed_violations = session.exec(
                    select(
                        FeedViolation.feed_id,
                        func.count(FeedViolation.id).label("count")
                    ).where(
                        FeedViolation.violation_date >= start_date
                    ).group_by(FeedViolation.feed_id)
                    .order_by(func.count(FeedViolation.id).desc())
                    .limit(10)
                ).all()

                # Get disabled feeds
                disabled_feeds = session.exec(
                    select(FeedLimit.feed_id).where(
                        FeedLimit.is_active == False
                    )
                ).all()

                return {
                    "violation_counts": {vtype: count for vtype, count in violation_counts},
                    "top_violating_feeds": [{"feed_id": fid, "violations": count} for fid, count in feed_violations],
                    "disabled_feeds": list(disabled_feeds),
                    "period_days": days
                }

        except Exception as e:
            logger.error(f"Error getting violations summary: {e}")
            return {"error": str(e)}

    def _record_violation(
        self,
        feed_id: int,
        violation_type: str,
        limit_value: float,
        actual_value: float,
        action_taken: str,
        analysis_run_id: Optional[int] = None,
        error_message: Optional[str] = None
    ):
        """Record a limit violation"""
        try:
            with Session(engine) as session:
                now = datetime.utcnow()
                threshold_percentage = ((actual_value - limit_value) / limit_value * 100) if limit_value > 0 else 0

                violation = FeedViolation(
                    feed_id=feed_id,
                    violation_type=violation_type,
                    violation_date=now.date(),
                    violation_time=now,
                    limit_value=limit_value,
                    actual_value=actual_value,
                    threshold_percentage=threshold_percentage,
                    action_taken=action_taken,
                    analysis_run_id=analysis_run_id,
                    error_message=error_message
                )

                session.add(violation)

                # Update feed limits violation count
                limits = session.exec(
                    select(FeedLimit).where(FeedLimit.feed_id == feed_id)
                ).first()

                if limits:
                    limits.violations_count += 1
                    limits.last_violation_at = now

                session.commit()

                logger.warning(
                    f"Recorded violation for feed {feed_id}: {violation_type} "
                    f"(limit: {limit_value}, actual: {actual_value}, action: {action_taken})"
                )

        except Exception as e:
            logger.error(f"Error recording violation for feed {feed_id}: {e}")

    def _disable_feed(self, feed_id: int, reason: str):
        """Disable a feed due to limit violation"""
        try:
            with Session(engine) as session:
                limits = session.exec(
                    select(FeedLimit).where(FeedLimit.feed_id == feed_id)
                ).first()

                if limits:
                    limits.is_active = False
                    limits.updated_at = datetime.utcnow()
                    session.commit()

                logger.error(f"DISABLED feed {feed_id}: {reason}")

        except Exception as e:
            logger.error(f"Error disabling feed {feed_id}: {e}")

    def enable_feed(self, feed_id: int) -> bool:
        """Re-enable a disabled feed"""
        try:
            with Session(engine) as session:
                limits = session.exec(
                    select(FeedLimit).where(FeedLimit.feed_id == feed_id)
                ).first()

                if limits:
                    limits.is_active = True
                    limits.emergency_stop_enabled = False
                    limits.updated_at = datetime.utcnow()
                    session.commit()

                    logger.info(f"Re-enabled feed {feed_id}")
                    return True

                return False

        except Exception as e:
            logger.error(f"Error enabling feed {feed_id}: {e}")
            return False


# Singleton instance
_feed_limits_service = None


def get_feed_limits_service() -> FeedLimitsService:
    """Get the singleton feed limits service instance"""
    global _feed_limits_service
    if _feed_limits_service is None:
        _feed_limits_service = FeedLimitsService()
    return _feed_limits_service