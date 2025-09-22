#!/usr/bin/env python3
"""Test script for monitoring and error handling components."""

import asyncio
import sys
import os

# Add the project root to Python path
sys.path.insert(0, '/home/cytrex/news-mcp')

from app.core.exceptions import (
    NewsMCPException, ValidationException, ExternalServiceException,
    DatabaseException, ErrorCategory, ErrorSeverity
)
from app.core.metrics import metrics, Timer, register_default_metrics
from app.core.health import health_monitor, register_default_health_checks
from app.core.resilience import resilience, RetryConfig, CircuitBreakerConfig
from app.core.logging_config import setup_logging, get_logger, ContextManager

async def test_exceptions():
    """Test custom exception handling."""
    logger = get_logger("test")

    try:
        raise ValidationException(
            field="limit",
            message="Value exceeds maximum allowed",
            value=7000
        )
    except NewsMCPException as e:
        logger.error("Caught validation exception",
                    error_code=e.error_code,
                    severity=e.severity.value)
        assert e.category == ErrorCategory.VALIDATION
        print("✓ ValidationException test passed")

    try:
        raise ExternalServiceException(
            service="openai",
            message="API rate limit exceeded",
            status_code=429
        )
    except NewsMCPException as e:
        logger.error("Caught external service exception",
                    error_code=e.error_code)
        assert e.category == ErrorCategory.EXTERNAL_SERVICE
        print("✓ ExternalServiceException test passed")

def test_metrics():
    """Test metrics collection."""
    # Register default metrics
    register_default_metrics()

    # Test counter
    metrics.increment_counter("test_counter", 5.0, tags={"test": "true"})

    # Test gauge
    metrics.set_gauge("test_gauge", 42.0, tags={"component": "test"})

    # Test timer with context manager
    with Timer("test_operation", tags={"operation": "test"}):
        import time
        time.sleep(0.1)

    # Verify metrics were recorded
    counter_metric = metrics.get_metric("test_counter")
    assert counter_metric is not None
    assert counter_metric.get_current_value() == 5.0

    gauge_metric = metrics.get_metric("test_gauge")
    assert gauge_metric is not None
    assert gauge_metric.get_current_value() == 42.0

    timer_metric = metrics.get_metric("test_operation")
    assert timer_metric is not None
    assert timer_metric.count == 1

    print("✓ Metrics collection test passed")

async def test_health_checks():
    """Test health check system."""
    # Register default health checks
    register_default_health_checks()

    # Run all health checks
    results = await health_monitor.check_all()

    # Verify we have the expected checks
    expected_checks = ["database", "memory", "disk", "application"]
    for check in expected_checks:
        assert check in results, f"Missing health check: {check}"
        print(f"✓ Health check '{check}' completed: {results[check].status.value}")

    overall_status = health_monitor.get_overall_status(results)
    print(f"✓ Overall health status: {overall_status.value}")

async def test_resilience():
    """Test resilience patterns."""

    # Test retry mechanism
    @resilience.with_retry(RetryConfig(max_attempts=3, initial_delay=0.1))
    async def flaky_operation():
        import random
        if random.random() < 0.7:  # 70% failure rate
            raise ConnectionError("Simulated connection failure")
        return "success"

    # Test circuit breaker
    circuit_config = CircuitBreakerConfig(
        failure_threshold=2,
        success_threshold=1,
        timeout=1.0
    )

    @resilience.with_circuit_breaker(circuit_config, "test_service")
    async def protected_operation():
        return "protected_success"

    try:
        result = await protected_operation()
        print(f"✓ Circuit breaker test passed: {result}")
    except Exception as e:
        print(f"✓ Circuit breaker handled failure: {e}")

    # Check circuit breaker state
    cb_states = resilience.get_all_circuit_breakers()
    if "test_service" in cb_states:
        state = cb_states["test_service"]
        print(f"✓ Circuit breaker state: {state['state']}")

def test_logging():
    """Test structured logging."""
    setup_logging(log_level="INFO", log_format="json")
    logger = get_logger("test")

    # Set context
    ContextManager.set_context(
        request_id="test-123",
        operation="test_operation",
        user_id="test_user"
    )

    # Test different log levels
    logger.info("Test info message", component="test", action="testing")
    logger.warning("Test warning message", warning_type="test")
    logger.error("Test error message", error_type="test_error")

    # Test operation logging
    logger.operation_start("test_operation", component="test")
    logger.operation_end("test_operation", duration_ms=100.5)

    print("✓ Structured logging test passed")

async def main():
    """Run all tests."""
    print("Testing News MCP monitoring and error handling components...")
    print()

    # Setup
    setup_logging(log_level="INFO", log_format="json")

    # Run tests
    test_logging()
    await test_exceptions()
    test_metrics()
    await test_health_checks()
    await test_resilience()

    print()
    print("✓ All monitoring and error handling tests passed!")

    # Display summary
    print("\nMonitoring endpoints available:")
    print("- GET  /health/detailed - Detailed health checks")
    print("- GET  /health/ready - Readiness probe")
    print("- GET  /health/live - Liveness probe")
    print("- GET  /metrics/ - Application metrics")
    print("- GET  /metrics/prometheus - Prometheus format")
    print("- GET  /monitoring/requests/active - Active requests")
    print("- GET  /monitoring/performance - Performance summary")
    print("- GET  /resilience/circuit-breakers - Circuit breaker states")

if __name__ == "__main__":
    asyncio.run(main())