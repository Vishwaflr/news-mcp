"""Metrics collection and monitoring system."""

import time
import threading
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime, timedelta
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum
from fastapi import Request, Response
from fastapi.routing import APIRoute

from app.core.logging_config import get_logger

logger = get_logger(__name__)


class MetricType(str, Enum):
    """Types of metrics."""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"


@dataclass
class MetricValue:
    """Individual metric measurement."""
    value: float
    timestamp: datetime = field(default_factory=datetime.utcnow)
    tags: Dict[str, str] = field(default_factory=dict)


@dataclass
class Metric:
    """Metric definition and storage."""
    name: str
    type: MetricType
    description: str
    values: List[MetricValue] = field(default_factory=list)
    total_value: float = 0.0
    count: int = 0
    tags: Dict[str, str] = field(default_factory=dict)

    def add_value(self, value: float, tags: Optional[Dict[str, str]] = None) -> None:
        """Add a new value to the metric."""
        metric_value = MetricValue(value=value, tags=tags or {})
        self.values.append(metric_value)

        if self.type == MetricType.COUNTER:
            self.total_value += value
        elif self.type == MetricType.GAUGE:
            self.total_value = value
        elif self.type in [MetricType.HISTOGRAM, MetricType.TIMER]:
            self.total_value += value

        self.count += 1

        # Keep only recent values (last 1000)
        if len(self.values) > 1000:
            self.values = self.values[-1000:]

    def get_current_value(self) -> float:
        """Get current metric value."""
        if self.type == MetricType.GAUGE:
            return self.total_value
        elif self.type == MetricType.COUNTER:
            return self.total_value
        elif self.type in [MetricType.HISTOGRAM, MetricType.TIMER]:
            return self.total_value / max(self.count, 1)
        return 0.0

    def get_statistics(self, time_window: Optional[timedelta] = None) -> Dict[str, Any]:
        """Get statistical summary of the metric."""
        if time_window:
            cutoff = datetime.utcnow() - time_window
            values = [v.value for v in self.values if v.timestamp >= cutoff]
        else:
            values = [v.value for v in self.values]

        if not values:
            return {"count": 0}

        return {
            "count": len(values),
            "sum": sum(values),
            "min": min(values),
            "max": max(values),
            "avg": sum(values) / len(values),
            "current": self.get_current_value()
        }


class MetricsCollector:
    """Central metrics collection system."""

    def __init__(self):
        self.metrics: Dict[str, Metric] = {}
        self._lock = threading.Lock()

    def register_metric(
        self,
        name: str,
        metric_type: MetricType,
        description: str,
        tags: Optional[Dict[str, str]] = None
    ) -> None:
        """Register a new metric."""
        with self._lock:
            self.metrics[name] = Metric(
                name=name,
                type=metric_type,
                description=description,
                tags=tags or {}
            )
            logger.debug(f"Registered metric: {name} ({metric_type.value})")

    def increment_counter(
        self,
        name: str,
        value: float = 1.0,
        tags: Optional[Dict[str, str]] = None
    ) -> None:
        """Increment a counter metric."""
        self._add_metric_value(name, MetricType.COUNTER, value, tags)

    def set_gauge(
        self,
        name: str,
        value: float,
        tags: Optional[Dict[str, str]] = None
    ) -> None:
        """Set a gauge metric value."""
        self._add_metric_value(name, MetricType.GAUGE, value, tags)

    def record_histogram(
        self,
        name: str,
        value: float,
        tags: Optional[Dict[str, str]] = None
    ) -> None:
        """Record a histogram value."""
        self._add_metric_value(name, MetricType.HISTOGRAM, value, tags)

    def record_timer(
        self,
        name: str,
        duration_ms: float,
        tags: Optional[Dict[str, str]] = None
    ) -> None:
        """Record a timer value."""
        self._add_metric_value(name, MetricType.TIMER, duration_ms, tags)

    def _add_metric_value(
        self,
        name: str,
        expected_type: MetricType,
        value: float,
        tags: Optional[Dict[str, str]] = None
    ) -> None:
        """Add value to metric, creating it if needed."""
        with self._lock:
            if name not in self.metrics:
                self.register_metric(name, expected_type, f"Auto-registered {expected_type.value}")

            metric = self.metrics[name]
            if metric.type != expected_type:
                logger.warning(f"Metric type mismatch for '{name}': expected {expected_type}, got {metric.type}")
                return

            metric.add_value(value, tags)

    def get_metric(self, name: str) -> Optional[Metric]:
        """Get a specific metric."""
        return self.metrics.get(name)

    def get_all_metrics(self) -> Dict[str, Metric]:
        """Get all registered metrics."""
        with self._lock:
            return self.metrics.copy()

    def get_metrics_summary(self, time_window: Optional[timedelta] = None) -> Dict[str, Any]:
        """Get summary of all metrics."""
        summary = {}
        with self._lock:
            for name, metric in self.metrics.items():
                summary[name] = {
                    "type": metric.type.value,
                    "description": metric.description,
                    "tags": metric.tags,
                    **metric.get_statistics(time_window)
                }
        return summary

    def clear_metrics(self) -> None:
        """Clear all metrics (for testing)."""
        with self._lock:
            self.metrics.clear()


# Global metrics collector
metrics = MetricsCollector()


class Timer:
    """Context manager for timing operations."""

    def __init__(self, metric_name: str, tags: Optional[Dict[str, str]] = None):
        self.metric_name = metric_name
        self.tags = tags or {}
        self.start_time = None

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time:
            duration_ms = (time.time() - self.start_time) * 1000

            # Add error tag if exception occurred
            tags = self.tags.copy()
            if exc_type:
                tags["error"] = "true"
                tags["error_type"] = exc_type.__name__
            else:
                tags["error"] = "false"

            metrics.record_timer(self.metric_name, duration_ms, tags)


def timer(metric_name: str, tags: Optional[Dict[str, str]] = None):
    """Decorator for timing function execution."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            with Timer(metric_name, tags):
                return func(*args, **kwargs)

        async def async_wrapper(*args, **kwargs):
            with Timer(metric_name, tags):
                return await func(*args, **kwargs)

        return async_wrapper if hasattr(func, '__call__') and getattr(func, '__code__', None) else wrapper
    return decorator


class MetricsMiddleware:
    """Middleware for collecting HTTP request metrics."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        start_time = time.time()

        # Extract request information
        method = scope["method"]
        path = scope["path"]

        # Track request start
        metrics.increment_counter("http_requests_total", tags={
            "method": method,
            "path": path
        })

        # Wrap send to capture response information
        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                status_code = message["status"]
                duration_ms = (time.time() - start_time) * 1000

                # Record response metrics
                metrics.record_timer("http_request_duration_ms", duration_ms, tags={
                    "method": method,
                    "path": path,
                    "status_code": str(status_code)
                })

                metrics.increment_counter("http_responses_total", tags={
                    "method": method,
                    "path": path,
                    "status_code": str(status_code)
                })

            await send(message)

        await self.app(scope, receive, send_wrapper)


def register_default_metrics():
    """Register default application metrics."""

    # HTTP metrics
    metrics.register_metric(
        "http_requests_total",
        MetricType.COUNTER,
        "Total number of HTTP requests"
    )

    metrics.register_metric(
        "http_responses_total",
        MetricType.COUNTER,
        "Total number of HTTP responses"
    )

    metrics.register_metric(
        "http_request_duration_ms",
        MetricType.TIMER,
        "HTTP request duration in milliseconds"
    )

    # Database metrics
    metrics.register_metric(
        "database_queries_total",
        MetricType.COUNTER,
        "Total number of database queries"
    )

    metrics.register_metric(
        "database_query_duration_ms",
        MetricType.TIMER,
        "Database query duration in milliseconds"
    )

    # Application metrics
    metrics.register_metric(
        "feeds_fetched_total",
        MetricType.COUNTER,
        "Total number of feeds fetched"
    )

    metrics.register_metric(
        "items_processed_total",
        MetricType.COUNTER,
        "Total number of items processed"
    )

    metrics.register_metric(
        "analysis_runs_total",
        MetricType.COUNTER,
        "Total number of analysis runs"
    )

    metrics.register_metric(
        "active_connections",
        MetricType.GAUGE,
        "Number of active connections"
    )

    # Error metrics
    metrics.register_metric(
        "errors_total",
        MetricType.COUNTER,
        "Total number of errors"
    )


# Application-specific metric helpers
def record_feed_fetch(success: bool, duration_ms: float, feed_id: int):
    """Record feed fetch metrics."""
    tags = {
        "success": str(success).lower(),
        "feed_id": str(feed_id)
    }

    metrics.increment_counter("feeds_fetched_total", tags=tags)
    metrics.record_timer("feed_fetch_duration_ms", duration_ms, tags=tags)


def record_item_processing(success: bool, processor_type: str, duration_ms: float):
    """Record item processing metrics."""
    tags = {
        "success": str(success).lower(),
        "processor_type": processor_type
    }

    metrics.increment_counter("items_processed_total", tags=tags)
    metrics.record_timer("item_processing_duration_ms", duration_ms, tags=tags)


def record_analysis_run(status: str, item_count: int, duration_ms: float):
    """Record analysis run metrics."""
    tags = {
        "status": status,
        "item_count_bucket": _get_bucket(item_count, [10, 50, 100, 500, 1000])
    }

    metrics.increment_counter("analysis_runs_total", tags=tags)
    metrics.record_timer("analysis_run_duration_ms", duration_ms, tags=tags)
    metrics.record_histogram("analysis_run_item_count", item_count, tags=tags)


def record_error(error_type: str, operation: str, severity: str = "medium"):
    """Record error metrics."""
    tags = {
        "error_type": error_type,
        "operation": operation,
        "severity": severity
    }

    metrics.increment_counter("errors_total", tags=tags)


def _get_bucket(value: int, buckets: List[int]) -> str:
    """Get bucket label for a value."""
    for bucket in buckets:
        if value <= bucket:
            return f"<={bucket}"
    return f">{buckets[-1]}"


# Metrics API endpoints
from fastapi import APIRouter

def create_metrics_router() -> APIRouter:
    """Create metrics API router."""
    router = APIRouter(prefix="/metrics", tags=["metrics"])

    @router.get("/")
    async def get_metrics():
        """Get all metrics in JSON format."""
        return metrics.get_metrics_summary()

    @router.get("/prometheus")
    async def get_prometheus_metrics():
        """Get metrics in Prometheus format."""
        lines = []

        for name, metric in metrics.get_all_metrics().items():
            # Add help and type comments
            lines.append(f"# HELP {name} {metric.description}")
            lines.append(f"# TYPE {name} {metric.type.value}")

            if metric.type == MetricType.COUNTER:
                lines.append(f"{name}_total {metric.get_current_value()}")
            elif metric.type == MetricType.GAUGE:
                lines.append(f"{name} {metric.get_current_value()}")
            elif metric.type in [MetricType.HISTOGRAM, MetricType.TIMER]:
                stats = metric.get_statistics()
                lines.append(f"{name}_sum {stats.get('sum', 0)}")
                lines.append(f"{name}_count {stats.get('count', 0)}")

        return "\n".join(lines), {"Content-Type": "text/plain"}

    @router.get("/{metric_name}")
    async def get_single_metric(metric_name: str):
        """Get a specific metric."""
        metric = metrics.get_metric(metric_name)
        if not metric:
            return {"error": f"Metric '{metric_name}' not found"}, 404

        return {
            "name": metric.name,
            "type": metric.type.value,
            "description": metric.description,
            "tags": metric.tags,
            **metric.get_statistics()
        }

    @router.post("/reset")
    async def reset_metrics():
        """Reset all metrics (development only)."""
        metrics.clear_metrics()
        register_default_metrics()
        return {"message": "Metrics reset successfully"}

    return router