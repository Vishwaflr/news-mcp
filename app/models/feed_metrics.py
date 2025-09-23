"""
Feed Metrics Models

Database models for tracking feed-specific metrics including costs, performance, and usage.
"""

from datetime import datetime, date
from typing import Optional, Dict, Any
from sqlmodel import SQLModel, Field, Column, JSON
from sqlalchemy import DateTime, Date, Index


class FeedMetrics(SQLModel, table=True):
    """
    Daily metrics for each feed including costs, analysis counts, and performance.

    This table aggregates metrics per feed per day for monitoring and billing.
    """
    __tablename__ = "feed_metrics"

    id: Optional[int] = Field(default=None, primary_key=True)

    # Feed identification
    feed_id: int = Field(foreign_key="feeds.id", index=True)
    metric_date: date = Field(index=True)

    # Analysis counts
    total_analyses: int = Field(default=0)
    auto_analyses: int = Field(default=0)
    manual_analyses: int = Field(default=0)
    scheduled_analyses: int = Field(default=0)

    # Items processed
    total_items_processed: int = Field(default=0)
    successful_items: int = Field(default=0)
    failed_items: int = Field(default=0)

    # Cost tracking (in USD)
    total_cost_usd: float = Field(default=0.0)
    input_cost_usd: float = Field(default=0.0)
    output_cost_usd: float = Field(default=0.0)
    cached_cost_usd: float = Field(default=0.0)

    # Token usage
    total_tokens_used: int = Field(default=0)
    input_tokens: int = Field(default=0)
    output_tokens: int = Field(default=0)
    cached_tokens: int = Field(default=0)

    # Performance metrics
    avg_processing_time_seconds: float = Field(default=0.0)
    avg_items_per_run: float = Field(default=0.0)
    success_rate: float = Field(default=0.0)  # Percentage

    # Queue metrics
    total_queue_time_seconds: float = Field(default=0.0)
    avg_queue_time_seconds: float = Field(default=0.0)
    max_queue_time_seconds: float = Field(default=0.0)

    # Model usage breakdown (JSON)
    model_usage: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow, sa_column=Column(DateTime(timezone=True)))
    updated_at: datetime = Field(default_factory=datetime.utcnow, sa_column=Column(DateTime(timezone=True)))

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses"""
        return {
            "id": self.id,
            "feed_id": self.feed_id,
            "metric_date": self.metric_date.isoformat(),
            "analysis_counts": {
                "total": self.total_analyses,
                "auto": self.auto_analyses,
                "manual": self.manual_analyses,
                "scheduled": self.scheduled_analyses
            },
            "item_counts": {
                "total_processed": self.total_items_processed,
                "successful": self.successful_items,
                "failed": self.failed_items
            },
            "costs": {
                "total_usd": self.total_cost_usd,
                "input_usd": self.input_cost_usd,
                "output_usd": self.output_cost_usd,
                "cached_usd": self.cached_cost_usd
            },
            "tokens": {
                "total": self.total_tokens_used,
                "input": self.input_tokens,
                "output": self.output_tokens,
                "cached": self.cached_tokens
            },
            "performance": {
                "avg_processing_time": self.avg_processing_time_seconds,
                "avg_items_per_run": self.avg_items_per_run,
                "success_rate": self.success_rate
            },
            "queue_metrics": {
                "total_queue_time": self.total_queue_time_seconds,
                "avg_queue_time": self.avg_queue_time_seconds,
                "max_queue_time": self.max_queue_time_seconds
            },
            "model_usage": self.model_usage,
            "updated_at": self.updated_at.isoformat()
        }


class QueueMetrics(SQLModel, table=True):
    """
    Queue processing metrics for monitoring queue performance.

    Tracks queue processing statistics and performance over time.
    """
    __tablename__ = "queue_metrics"

    id: Optional[int] = Field(default=None, primary_key=True)

    # Time period
    metric_date: date = Field(index=True)
    metric_hour: int = Field(index=True)  # 0-23 for hourly breakdowns

    # Queue processing counts
    items_processed: int = Field(default=0)
    items_failed: int = Field(default=0)
    items_cancelled: int = Field(default=0)

    # Processing times
    total_processing_time_seconds: float = Field(default=0.0)
    avg_processing_time_seconds: float = Field(default=0.0)
    min_processing_time_seconds: float = Field(default=0.0)
    max_processing_time_seconds: float = Field(default=0.0)

    # Queue times
    total_queue_time_seconds: float = Field(default=0.0)
    avg_queue_time_seconds: float = Field(default=0.0)
    min_queue_time_seconds: float = Field(default=0.0)
    max_queue_time_seconds: float = Field(default=0.0)

    # Priority breakdown
    high_priority_processed: int = Field(default=0)
    medium_priority_processed: int = Field(default=0)
    low_priority_processed: int = Field(default=0)

    # System state snapshots
    max_queue_length: int = Field(default=0)
    avg_queue_length: float = Field(default=0.0)
    emergency_stops: int = Field(default=0)

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow, sa_column=Column(DateTime(timezone=True)))
    updated_at: datetime = Field(default_factory=datetime.utcnow, sa_column=Column(DateTime(timezone=True)))


# Create composite indexes for better query performance
Index("ix_feed_metrics_feed_date", FeedMetrics.feed_id, FeedMetrics.metric_date)
Index("ix_queue_metrics_date_hour", QueueMetrics.metric_date, QueueMetrics.metric_hour)