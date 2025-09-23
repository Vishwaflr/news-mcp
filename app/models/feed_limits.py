"""
Feed Limits Models

Database models for configuring and tracking feed-specific limits and quotas.
"""

from datetime import datetime, date
from typing import Optional, Dict, Any
from sqlmodel import SQLModel, Field, Column, JSON
from sqlalchemy import DateTime, Date, Index


class FeedLimit(SQLModel, table=True):
    """
    Feed-specific limits and quotas configuration.

    Defines limits for analysis frequency, cost budgets, and resource usage per feed.
    """
    __tablename__ = "feed_limits"

    id: Optional[int] = Field(default=None, primary_key=True)

    # Feed identification
    feed_id: int = Field(foreign_key="feeds.id", index=True, unique=True)

    # Analysis frequency limits
    max_analyses_per_day: Optional[int] = Field(default=None)
    max_analyses_per_hour: Optional[int] = Field(default=None)
    min_interval_minutes: Optional[int] = Field(default=30)  # Minimum time between analyses

    # Cost limits (in USD)
    daily_cost_limit: Optional[float] = Field(default=None)
    monthly_cost_limit: Optional[float] = Field(default=None)
    cost_alert_threshold: Optional[float] = Field(default=None)  # Alert when reaching this % of limit

    # Processing limits
    max_items_per_analysis: Optional[int] = Field(default=None)
    max_queue_priority: Optional[str] = Field(default="MEDIUM")  # HIGH, MEDIUM, LOW

    # Emergency controls
    emergency_stop_enabled: bool = Field(default=False)
    auto_disable_on_error_rate: Optional[float] = Field(default=0.8)  # Disable if error rate > 80%
    auto_disable_on_cost_breach: bool = Field(default=True)

    # Notification settings
    alert_email: Optional[str] = Field(default=None)
    alert_on_limit_breach: bool = Field(default=True)
    alert_on_cost_threshold: bool = Field(default=True)

    # Custom configurations (JSON)
    custom_settings: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))

    # Status tracking
    is_active: bool = Field(default=True)
    violations_count: int = Field(default=0)
    last_violation_at: Optional[datetime] = Field(default=None, sa_column=Column(DateTime(timezone=True)))

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow, sa_column=Column(DateTime(timezone=True)))
    updated_at: datetime = Field(default_factory=datetime.utcnow, sa_column=Column(DateTime(timezone=True)))

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses"""
        return {
            "id": self.id,
            "feed_id": self.feed_id,
            "limits": {
                "max_analyses_per_day": self.max_analyses_per_day,
                "max_analyses_per_hour": self.max_analyses_per_hour,
                "min_interval_minutes": self.min_interval_minutes,
                "max_items_per_analysis": self.max_items_per_analysis
            },
            "cost_controls": {
                "daily_cost_limit": self.daily_cost_limit,
                "monthly_cost_limit": self.monthly_cost_limit,
                "cost_alert_threshold": self.cost_alert_threshold
            },
            "emergency_controls": {
                "emergency_stop_enabled": self.emergency_stop_enabled,
                "auto_disable_on_error_rate": self.auto_disable_on_error_rate,
                "auto_disable_on_cost_breach": self.auto_disable_on_cost_breach
            },
            "notifications": {
                "alert_email": self.alert_email,
                "alert_on_limit_breach": self.alert_on_limit_breach,
                "alert_on_cost_threshold": self.alert_on_cost_threshold
            },
            "status": {
                "is_active": self.is_active,
                "violations_count": self.violations_count,
                "last_violation_at": self.last_violation_at.isoformat() if self.last_violation_at else None
            },
            "custom_settings": self.custom_settings,
            "updated_at": self.updated_at.isoformat()
        }


class FeedViolation(SQLModel, table=True):
    """
    Feed limit violations tracking.

    Records when feeds exceed their configured limits for monitoring and analysis.
    """
    __tablename__ = "feed_violations"

    id: Optional[int] = Field(default=None, primary_key=True)

    # Violation details
    feed_id: int = Field(foreign_key="feeds.id", index=True)
    violation_type: str = Field(index=True)  # COST_LIMIT, FREQUENCY_LIMIT, ERROR_RATE, etc.
    violation_date: date = Field(index=True)
    violation_time: datetime = Field(sa_column=Column(DateTime(timezone=True)))

    # Violation context
    limit_value: Optional[float] = Field(default=None)  # The limit that was exceeded
    actual_value: Optional[float] = Field(default=None)  # The actual value that caused violation
    threshold_percentage: Optional[float] = Field(default=None)  # How much over the limit (%)

    # Action taken
    action_taken: str = Field(default="LOGGED")  # LOGGED, DISABLED, ALERT_SENT, EMERGENCY_STOP
    auto_resolved: bool = Field(default=False)
    resolved_at: Optional[datetime] = Field(default=None, sa_column=Column(DateTime(timezone=True)))

    # Additional context
    analysis_run_id: Optional[int] = Field(default=None, foreign_key="analysis_runs.id")
    error_message: Optional[str] = Field(default=None)
    violation_metadata: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow, sa_column=Column(DateTime(timezone=True)))

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses"""
        return {
            "id": self.id,
            "feed_id": self.feed_id,
            "violation_type": self.violation_type,
            "violation_date": self.violation_date.isoformat(),
            "violation_time": self.violation_time.isoformat(),
            "limits": {
                "limit_value": self.limit_value,
                "actual_value": self.actual_value,
                "threshold_percentage": self.threshold_percentage
            },
            "resolution": {
                "action_taken": self.action_taken,
                "auto_resolved": self.auto_resolved,
                "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None
            },
            "context": {
                "analysis_run_id": self.analysis_run_id,
                "error_message": self.error_message,
                "metadata": self.violation_metadata
            },
            "created_at": self.created_at.isoformat()
        }


# Create indexes for better query performance
Index("ix_feed_limits_feed_active", FeedLimit.feed_id, FeedLimit.is_active)
Index("ix_feed_violations_feed_date", FeedViolation.feed_id, FeedViolation.violation_date)
Index("ix_feed_violations_type_date", FeedViolation.violation_type, FeedViolation.violation_date)