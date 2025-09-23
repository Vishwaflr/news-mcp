"""Performance monitoring and metrics collection for repository migration."""

import time
from app.core.logging_config import get_logger
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from contextlib import contextmanager
from dataclasses import dataclass, field
from collections import defaultdict, deque

logger = get_logger(__name__)


@dataclass
class MetricPoint:
    """Individual metric measurement."""
    timestamp: datetime
    value: float
    labels: Dict[str, str] = field(default_factory=dict)


@dataclass
class PerformanceMetrics:
    """Performance metrics for a specific operation."""
    operation: str
    duration_ms: float
    success: bool
    timestamp: datetime
    labels: Dict[str, str] = field(default_factory=dict)
    details: Optional[Dict[str, Any]] = None


class MetricsCollector:
    """Lightweight metrics collector for monitoring repository performance."""

    def __init__(self, max_points_per_metric: int = 1000):
        self.max_points = max_points_per_metric
        self.metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=self.max_points))
        self.performance_data: deque = deque(maxlen=self.max_points)

    def record_metric(self, name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """Record a metric point."""
        point = MetricPoint(
            timestamp=datetime.utcnow(),
            value=value,
            labels=labels or {}
        )
        self.metrics[name].append(point)

    def record_performance(
        self,
        operation: str,
        duration_ms: float,
        success: bool,
        labels: Optional[Dict[str, str]] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """Record performance data."""
        perf = PerformanceMetrics(
            operation=operation,
            duration_ms=duration_ms,
            success=success,
            timestamp=datetime.utcnow(),
            labels=labels or {},
            details=details
        )
        self.performance_data.append(perf)

        # Also record as separate metrics
        self.record_metric(f"{operation}.duration_ms", duration_ms, labels)
        self.record_metric(f"{operation}.success", 1.0 if success else 0.0, labels)

    @contextmanager
    def time_operation(
        self,
        operation: str,
        labels: Optional[Dict[str, str]] = None,
        auto_record: bool = True
    ):
        """Context manager to time an operation."""
        start_time = time.perf_counter()
        success = False
        error = None

        try:
            yield
            success = True
        except Exception as e:
            error = str(e)
            raise
        finally:
            duration_ms = (time.perf_counter() - start_time) * 1000

            if auto_record:
                details = {"error": error} if error else None
                self.record_performance(operation, duration_ms, success, labels, details)

    def get_stats(self, metric_name: str, since: Optional[datetime] = None) -> Dict[str, float]:
        """Get statistics for a metric."""
        if metric_name not in self.metrics:
            return {"count": 0}

        points = self.metrics[metric_name]

        # Filter by time if specified
        if since:
            points = [p for p in points if p.timestamp >= since]

        if not points:
            return {"count": 0}

        values = [p.value for p in points]
        return {
            "count": len(values),
            "avg": sum(values) / len(values),
            "min": min(values),
            "max": max(values),
            "p50": self._percentile(values, 50),
            "p95": self._percentile(values, 95),
            "p99": self._percentile(values, 99)
        }

    def get_performance_summary(
        self,
        operation: Optional[str] = None,
        since: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get performance summary for operations."""
        data = list(self.performance_data)

        # Filter by operation and time
        if operation:
            data = [d for d in data if d.operation == operation]
        if since:
            data = [d for d in data if d.timestamp >= since]

        if not data:
            return {"count": 0}

        # Group by operation
        by_operation = defaultdict(list)
        for d in data:
            by_operation[d.operation].append(d)

        summary = {}
        for op, ops_data in by_operation.items():
            durations = [d.duration_ms for d in ops_data]
            success_count = sum(1 for d in ops_data if d.success)
            error_count = len(ops_data) - success_count

            summary[op] = {
                "total_requests": len(ops_data),
                "success_count": success_count,
                "error_count": error_count,
                "success_rate": success_count / len(ops_data) if ops_data else 0,
                "duration_stats": {
                    "avg_ms": sum(durations) / len(durations) if durations else 0,
                    "min_ms": min(durations) if durations else 0,
                    "max_ms": max(durations) if durations else 0,
                    "p95_ms": self._percentile(durations, 95) if durations else 0,
                    "p99_ms": self._percentile(durations, 99) if durations else 0,
                }
            }

        return summary

    def get_comparison_metrics(self, old_operation: str, new_operation: str) -> Dict[str, Any]:
        """Compare metrics between old and new implementations."""
        since = datetime.utcnow() - timedelta(hours=1)  # Last hour

        old_stats = self.get_performance_summary(old_operation, since)
        new_stats = self.get_performance_summary(new_operation, since)

        if not old_stats or not new_stats:
            return {"error": "Insufficient data for comparison"}

        old_data = old_stats.get(old_operation, {})
        new_data = new_stats.get(new_operation, {})

        if not old_data or not new_data:
            return {"error": "No data for one or both operations"}

        old_p95 = old_data.get("duration_stats", {}).get("p95_ms", 0)
        new_p95 = new_data.get("duration_stats", {}).get("p95_ms", 0)

        old_success_rate = old_data.get("success_rate", 0)
        new_success_rate = new_data.get("success_rate", 0)

        return {
            "old_operation": old_operation,
            "new_operation": new_operation,
            "latency_comparison": {
                "old_p95_ms": old_p95,
                "new_p95_ms": new_p95,
                "improvement_factor": old_p95 / new_p95 if new_p95 > 0 else float('inf'),
                "regression_percent": ((new_p95 - old_p95) / old_p95 * 100) if old_p95 > 0 else 0
            },
            "reliability_comparison": {
                "old_success_rate": old_success_rate,
                "new_success_rate": new_success_rate,
                "reliability_delta": new_success_rate - old_success_rate
            },
            "volume_comparison": {
                "old_requests": old_data.get("total_requests", 0),
                "new_requests": new_data.get("total_requests", 0)
            }
        }

    def _percentile(self, data: List[float], p: int) -> float:
        """Calculate percentile of data."""
        if not data:
            return 0
        sorted_data = sorted(data)
        index = int((p / 100) * len(sorted_data))
        return sorted_data[min(index, len(sorted_data) - 1)]

    def export_metrics(self, format: str = "json") -> str:
        """Export metrics in specified format."""
        import json

        if format == "json":
            data = {
                "timestamp": datetime.utcnow().isoformat(),
                "metrics": {},
                "performance_summary": self.get_performance_summary()
            }

            # Export recent metrics
            since = datetime.utcnow() - timedelta(minutes=5)
            for metric_name in self.metrics:
                data["metrics"][metric_name] = self.get_stats(metric_name, since)

            return json.dumps(data, indent=2)

        # Add other formats as needed (Prometheus, etc.)
        raise ValueError(f"Unsupported format: {format}")


class RepositoryMonitor:
    """Specialized monitor for repository operations."""

    def __init__(self, metrics_collector: MetricsCollector):
        self.metrics = metrics_collector

    @contextmanager
    def monitor_query(
        self,
        repo_name: str,
        operation: str,
        filter_info: Optional[Dict[str, Any]] = None
    ):
        """Monitor a repository query operation."""
        labels = {
            "repo": repo_name,
            "operation": operation
        }

        # Add filter information to labels
        if filter_info:
            if filter_info.get("has_filters"):
                labels["has_filters"] = "true"
            if filter_info.get("has_joins"):
                labels["has_joins"] = "true"
            if filter_info.get("limit"):
                # Bucket limits for better aggregation
                limit = filter_info["limit"]
                if limit <= 20:
                    labels["limit_bucket"] = "small"
                elif limit <= 100:
                    labels["limit_bucket"] = "medium"
                else:
                    labels["limit_bucket"] = "large"

        operation_name = f"{repo_name}.{operation}"
        with self.metrics.time_operation(operation_name, labels):
            yield

    def record_query_result(
        self,
        repo_name: str,
        operation: str,
        row_count: int,
        cache_hit: bool = False
    ):
        """Record query result metrics."""
        labels = {
            "repo": repo_name,
            "operation": operation,
            "cache_hit": str(cache_hit).lower()
        }

        self.metrics.record_metric(f"{repo_name}.query.rows", row_count, labels)


# Global metrics collector
metrics_collector = MetricsCollector()
repo_monitor = RepositoryMonitor(metrics_collector)