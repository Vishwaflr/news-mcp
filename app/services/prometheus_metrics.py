"""
Prometheus Metrics Service

Provides instrumentation for monitoring system performance:
- Counters for events (items processed, errors)
- Gauges for current state (queue depth, active items)
- Histograms for latency (analysis duration, API calls)
"""

from prometheus_client import Counter, Gauge, Histogram, Info
from typing import Optional
from app.core.logging_config import get_logger

logger = get_logger(__name__)


class PrometheusMetricsService:
    """
    Centralized Prometheus metrics for News-MCP.

    Tracks analysis operations, queue state, errors, and performance.
    """

    def __init__(self):
        """Initialize all metrics."""

        # ===== COUNTERS (cumulative) =====

        self.items_processed_total = Counter(
            'analysis_items_processed_total',
            'Total number of items processed',
            ['status', 'triggered_by']  # status: completed, failed, skipped
        )

        self.errors_total = Counter(
            'analysis_errors_total',
            'Total number of errors encountered',
            ['error_type', 'component']
        )

        self.api_calls_total = Counter(
            'analysis_api_calls_total',
            'Total number of AI API calls',
            ['model', 'status']  # status: success, failure, timeout
        )

        self.feeds_fetched_total = Counter(
            'feeds_fetched_total',
            'Total number of feed fetches',
            ['status']  # status: success, failure
        )

        self.circuit_breaker_state_changes = Counter(
            'circuit_breaker_state_changes_total',
            'Total number of circuit breaker state changes',
            ['from_state', 'to_state']
        )

        # ===== GAUGES (current value) =====

        self.queue_depth = Gauge(
            'analysis_queue_depth',
            'Current number of items in analysis queue'
        )

        self.active_items = Gauge(
            'analysis_active_items',
            'Current number of items being processed'
        )

        self.queue_utilization = Gauge(
            'analysis_queue_utilization_percent',
            'Queue utilization percentage (0-100)'
        )

        self.circuit_breaker_state = Gauge(
            'circuit_breaker_state',
            'Circuit breaker state (0=closed, 1=half_open, 2=open)',
            ['component']
        )

        self.pending_auto_analysis_jobs = Gauge(
            'pending_auto_analysis_jobs',
            'Number of pending auto-analysis jobs'
        )

        self.active_feeds = Gauge(
            'active_feeds_count',
            'Number of active feeds'
        )

        self.analyzed_items_ratio = Gauge(
            'analyzed_items_ratio',
            'Ratio of analyzed to total items (0-1)'
        )

        self.current_rate_limit = Gauge(
            'rate_limiter_current_rate',
            'Current rate limit (requests per second)'
        )

        # ===== HISTOGRAMS (distributions) =====

        self.analysis_duration = Histogram(
            'analysis_duration_seconds',
            'Time taken to analyze a single item',
            buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0]
        )

        self.api_request_duration = Histogram(
            'api_request_duration_seconds',
            'Time taken for AI API requests',
            ['model'],
            buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0]
        )

        self.queue_wait_time = Histogram(
            'queue_wait_time_seconds',
            'Time items spend waiting in queue',
            buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 5.0, 10.0, 60.0]
        )

        self.batch_size = Histogram(
            'analysis_batch_size',
            'Number of items in analysis batches',
            buckets=[1, 5, 10, 20, 50, 100, 200, 500]
        )

        self.feed_lag_minutes = Histogram(
            'feed_lag_minutes',
            'Lag between article publish time and ingestion',
            ['feed_id'],
            buckets=[1, 5, 10, 30, 60, 120, 360, 1440]  # 1min to 1day
        )

        # ===== INFO (static metadata) =====

        self.build_info = Info(
            'news_mcp_build',
            'Build information for News-MCP'
        )

        logger.info("PrometheusMetricsService initialized with all metrics")

    # ===== HELPER METHODS =====

    def record_item_processed(self, status: str, triggered_by: str = "manual"):
        """
        Record an item being processed.

        Args:
            status: completed, failed, or skipped
            triggered_by: manual, auto, or scheduled
        """
        self.items_processed_total.labels(
            status=status,
            triggered_by=triggered_by
        ).inc()

    def record_error(self, error_type: str, component: str):
        """
        Record an error.

        Args:
            error_type: Type of error (e.g., 'api_timeout', 'db_error')
            component: Component where error occurred
        """
        self.errors_total.labels(
            error_type=error_type,
            component=component
        ).inc()

    def record_api_call(self, model: str, status: str):
        """
        Record an API call.

        Args:
            model: AI model used
            status: success, failure, or timeout
        """
        self.api_calls_total.labels(
            model=model,
            status=status
        ).inc()

    def record_feed_fetch(self, status: str):
        """
        Record a feed fetch operation.

        Args:
            status: success or failure
        """
        self.feeds_fetched_total.labels(status=status).inc()

    def record_circuit_breaker_change(self, from_state: str, to_state: str):
        """
        Record a circuit breaker state change.

        Args:
            from_state: Previous state (closed, half_open, open)
            to_state: New state
        """
        self.circuit_breaker_state_changes.labels(
            from_state=from_state,
            to_state=to_state
        ).inc()

    def update_queue_metrics(self, depth: int, active: int, utilization: float):
        """
        Update queue-related gauges.

        Args:
            depth: Number of items in queue
            active: Number of active items
            utilization: Utilization percentage (0-100)
        """
        self.queue_depth.set(depth)
        self.active_items.set(active)
        self.queue_utilization.set(utilization)

    def update_circuit_breaker_state(self, component: str, state: str):
        """
        Update circuit breaker state gauge.

        Args:
            component: Component name
            state: closed, half_open, or open
        """
        state_map = {
            'closed': 0,
            'half_open': 1,
            'open': 2
        }
        self.circuit_breaker_state.labels(component=component).set(
            state_map.get(state, -1)
        )

    def update_rate_limit(self, rate: float):
        """
        Update current rate limit gauge.

        Args:
            rate: Current rate in requests per second
        """
        self.current_rate_limit.set(rate)

    def set_build_info(self, version: str, commit: str = "", build_date: str = ""):
        """
        Set build information.

        Args:
            version: Version string
            commit: Git commit hash
            build_date: Build timestamp
        """
        self.build_info.info({
            'version': version,
            'commit': commit,
            'build_date': build_date
        })


# Global singleton instance
_global_metrics: Optional[PrometheusMetricsService] = None


def get_metrics() -> PrometheusMetricsService:
    """
    Get or create global metrics service instance.

    Returns:
        PrometheusMetricsService instance
    """
    global _global_metrics

    if _global_metrics is None:
        _global_metrics = PrometheusMetricsService()

    return _global_metrics
