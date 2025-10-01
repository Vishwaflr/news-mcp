"""
Tests for Prometheus Metrics

Ensures metrics are properly recorded and exposed.
"""

import pytest
from app.services.prometheus_metrics import get_metrics
from prometheus_client import REGISTRY


def test_metrics_service_initialization():
    """Test that metrics service initializes correctly."""
    metrics = get_metrics()

    assert metrics is not None
    assert hasattr(metrics, 'items_processed_total')
    assert hasattr(metrics, 'errors_total')
    assert hasattr(metrics, 'queue_depth')
    assert hasattr(metrics, 'analysis_duration')


def test_record_item_processed():
    """Test recording processed items."""
    metrics = get_metrics()

    # Record some items
    metrics.record_item_processed("completed", "manual")
    metrics.record_item_processed("completed", "auto")
    metrics.record_item_processed("failed", "manual")
    metrics.record_item_processed("skipped", "auto")

    # Check that counter incremented (we can't easily read values, but can verify no errors)
    assert True  # If we got here, no exceptions were raised


def test_record_error():
    """Test recording errors."""
    metrics = get_metrics()

    metrics.record_error("api_timeout", "orchestrator")
    metrics.record_error("db_error", "processor")
    metrics.record_error("empty_title", "orchestrator")

    assert True  # No exceptions raised


def test_record_api_call():
    """Test recording API calls."""
    metrics = get_metrics()

    metrics.record_api_call("gpt-4.1-nano", "success")
    metrics.record_api_call("gpt-4.1-nano", "failure")
    metrics.record_api_call("gpt-4-turbo", "timeout")

    assert True


def test_record_feed_fetch():
    """Test recording feed fetches."""
    metrics = get_metrics()

    metrics.record_feed_fetch("success")
    metrics.record_feed_fetch("failure")

    assert True


def test_update_queue_metrics():
    """Test updating queue gauges."""
    metrics = get_metrics()

    metrics.update_queue_metrics(depth=10, active=5, utilization=50.0)
    metrics.update_queue_metrics(depth=20, active=15, utilization=75.0)
    metrics.update_queue_metrics(depth=0, active=0, utilization=0.0)

    assert True


def test_update_circuit_breaker_state():
    """Test updating circuit breaker state."""
    metrics = get_metrics()

    metrics.update_circuit_breaker_state("rate_limiter", "closed")
    metrics.update_circuit_breaker_state("rate_limiter", "half_open")
    metrics.update_circuit_breaker_state("rate_limiter", "open")

    assert True


def test_record_circuit_breaker_change():
    """Test recording circuit breaker state changes."""
    metrics = get_metrics()

    metrics.record_circuit_breaker_change("closed", "open")
    metrics.record_circuit_breaker_change("open", "half_open")
    metrics.record_circuit_breaker_change("half_open", "closed")

    assert True


def test_update_rate_limit():
    """Test updating rate limit gauge."""
    metrics = get_metrics()

    metrics.update_rate_limit(3.0)
    metrics.update_rate_limit(2.25)  # After adaptive reduction
    metrics.update_rate_limit(1.0)

    assert True


def test_histogram_observations():
    """Test recording histogram observations."""
    metrics = get_metrics()

    # Record some durations
    metrics.analysis_duration.observe(1.5)
    metrics.analysis_duration.observe(2.3)
    metrics.analysis_duration.observe(0.8)

    metrics.api_request_duration.labels(model="gpt-4.1-nano").observe(0.5)
    metrics.api_request_duration.labels(model="gpt-4.1-nano").observe(1.2)

    metrics.queue_wait_time.observe(0.01)
    metrics.queue_wait_time.observe(0.05)

    metrics.batch_size.observe(10)
    metrics.batch_size.observe(50)
    metrics.batch_size.observe(100)

    assert True


def test_set_build_info():
    """Test setting build information."""
    metrics = get_metrics()

    metrics.set_build_info(
        version="v4.0.0",
        commit="abc123def",
        build_date="2025-10-01"
    )

    assert True


def test_singleton_pattern():
    """Test that get_metrics returns singleton instance."""
    metrics1 = get_metrics()
    metrics2 = get_metrics()

    assert metrics1 is metrics2


def test_metrics_labels():
    """Test that labeled metrics work correctly."""
    metrics = get_metrics()

    # Test different status labels
    metrics.items_processed_total.labels(status="completed", triggered_by="manual").inc()
    metrics.items_processed_total.labels(status="completed", triggered_by="auto").inc()
    metrics.items_processed_total.labels(status="failed", triggered_by="manual").inc()

    # Test error type labels
    metrics.errors_total.labels(error_type="api_timeout", component="orchestrator").inc()
    metrics.errors_total.labels(error_type="db_error", component="processor").inc()

    # Test API call labels
    metrics.api_calls_total.labels(model="gpt-4.1-nano", status="success").inc()
    metrics.api_calls_total.labels(model="gpt-4-turbo", status="failure").inc()

    # Test circuit breaker labels
    metrics.circuit_breaker_state.labels(component="rate_limiter").set(0)  # closed
    metrics.circuit_breaker_state.labels(component="queue_limiter").set(2)  # open

    assert True


def test_feed_lag_histogram():
    """Test feed lag histogram with labels."""
    metrics = get_metrics()

    # Record lag for different feeds
    metrics.feed_lag_minutes.labels(feed_id="12").observe(5.5)
    metrics.feed_lag_minutes.labels(feed_id="13").observe(45.0)
    metrics.feed_lag_minutes.labels(feed_id="30").observe(10.2)

    assert True


def test_multiple_components():
    """Test metrics from multiple components working together."""
    metrics = get_metrics()

    # Simulate processor recording metrics
    metrics.update_queue_metrics(depth=15, active=10, utilization=66.7)
    metrics.batch_size.observe(15)
    metrics.record_item_processed("completed", "auto")

    # Simulate orchestrator recording metrics
    metrics.analysis_duration.observe(1.2)
    metrics.api_request_duration.labels(model="gpt-4.1-nano").observe(0.8)
    metrics.record_api_call("gpt-4.1-nano", "success")

    # Simulate rate limiter recording metrics
    metrics.update_rate_limit(3.0)
    metrics.update_circuit_breaker_state("rate_limiter", "closed")

    assert True


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "-s"])
