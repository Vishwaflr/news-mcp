"""
Tests for Backpressure Controls

Ensures that queue limiter and rate limiter prevent system overload
and provide proper metrics.
"""

import pytest
import asyncio
from app.services.queue_limiter import QueueLimiter
from app.services.adaptive_rate_limiter import AdaptiveRateLimiter, CircuitState


@pytest.mark.asyncio
async def test_queue_limiter_basic():
    """Test basic queue limiter functionality."""
    limiter = QueueLimiter(max_concurrent=3)

    # Should be able to acquire slots
    assert await limiter.acquire(1)
    assert await limiter.acquire(2)
    assert await limiter.acquire(3)

    # Check metrics
    metrics = limiter.get_metrics()
    assert metrics["active_count"] == 3
    assert metrics["available_slots"] == 0
    assert metrics["utilization_pct"] == 100.0

    # Release a slot
    limiter.release(1)
    assert limiter.is_available()

    # Should be able to acquire again
    assert await limiter.acquire(4)


@pytest.mark.asyncio
async def test_queue_limiter_timeout():
    """Test queue limiter timeout behavior."""
    limiter = QueueLimiter(max_concurrent=2)

    # Fill queue
    await limiter.acquire(1)
    await limiter.acquire(2)

    # Try to acquire with timeout (should fail)
    acquired = await limiter.acquire(3, timeout=0.1)
    assert acquired is False

    # Metrics should show timeout
    metrics = limiter.get_metrics()
    assert metrics["active_count"] == 2


@pytest.mark.asyncio
async def test_queue_limiter_metrics():
    """Test queue limiter metrics tracking."""
    limiter = QueueLimiter(max_concurrent=5)

    # Process some items
    for i in range(3):
        await limiter.acquire(i)

    limiter.release(0)
    limiter.release(1)

    metrics = limiter.get_metrics()
    assert metrics["total_processed"] == 2
    assert metrics["active_count"] == 1
    assert metrics["peak_queue_depth"] == 3


@pytest.mark.asyncio
async def test_rate_limiter_basic():
    """Test basic rate limiter functionality."""
    limiter = AdaptiveRateLimiter(rate_per_second=10.0, max_burst=5)

    # Should allow burst immediately
    for i in range(5):
        acquired = await limiter.acquire(timeout=0.1)
        assert acquired is True

    # Should succeed after waiting
    acquired = await limiter.acquire(timeout=0.5)
    assert acquired is True

    metrics = limiter.get_metrics()
    assert metrics["total_requests"] == 6
    assert metrics["circuit_state"] == "closed"


@pytest.mark.asyncio
async def test_rate_limiter_timeout():
    """Test rate limiter timeout behavior."""
    limiter = AdaptiveRateLimiter(rate_per_second=2.0, max_burst=2)

    # Exhaust burst
    await limiter.acquire()
    await limiter.acquire()

    # Try immediate acquire with short timeout (should fail)
    acquired = await limiter.acquire(timeout=0.01)
    assert acquired is False


@pytest.mark.asyncio
async def test_circuit_breaker_opens():
    """Test circuit breaker opens after failures."""
    limiter = AdaptiveRateLimiter(
        rate_per_second=10.0,
        circuit_threshold=3
    )

    # Simulate failures
    for i in range(3):
        await limiter.acquire()
        limiter.record_failure()

    metrics = limiter.get_metrics()
    assert metrics["circuit_state"] == "open"
    assert metrics["consecutive_failures"] == 3
    assert metrics["circuit_opens"] == 1

    # Should block requests when circuit is open
    acquired = await limiter.acquire(timeout=0.1)
    assert acquired is False


@pytest.mark.asyncio
async def test_circuit_breaker_recovery():
    """Test circuit breaker recovers after timeout."""
    limiter = AdaptiveRateLimiter(
        rate_per_second=10.0,
        circuit_threshold=2,
        circuit_timeout_seconds=0.2
    )

    # Open circuit
    await limiter.acquire()
    limiter.record_failure()
    await limiter.acquire()
    limiter.record_failure()

    assert limiter.get_metrics()["circuit_state"] == "open"

    # Wait for timeout
    await asyncio.sleep(0.25)

    # Should allow test requests (half-open)
    acquired = await limiter.acquire(timeout=0.1)
    assert acquired is True
    limiter.record_success()

    # Need more successful test requests to close circuit
    acquired = await limiter.acquire(timeout=0.1)
    assert acquired is True
    limiter.record_success()

    acquired = await limiter.acquire(timeout=0.1)
    assert acquired is True
    limiter.record_success()

    # Circuit should be closed now after 3 successes
    metrics = limiter.get_metrics()
    assert metrics["circuit_state"] == "closed"
    assert metrics["consecutive_failures"] == 0


@pytest.mark.asyncio
async def test_adaptive_rate_reduction():
    """Test adaptive rate reduction on errors."""
    limiter = AdaptiveRateLimiter(
        rate_per_second=10.0,
        min_rate=1.0
    )

    initial_rate = limiter.current_rate

    # Simulate 2 failures (should reduce rate)
    await limiter.acquire()
    limiter.record_failure()
    await limiter.acquire()
    limiter.record_failure()

    # Rate should be reduced
    assert limiter.current_rate < initial_rate
    assert limiter.current_rate >= limiter.min_rate

    metrics = limiter.get_metrics()
    assert metrics["current_rate"] < metrics["base_rate"]


@pytest.mark.asyncio
async def test_concurrent_queue_usage():
    """Test queue limiter under concurrent load."""
    limiter = QueueLimiter(max_concurrent=5)

    async def process_item(item_id: int):
        acquired = await limiter.acquire(item_id, timeout=1.0)
        if acquired:
            await asyncio.sleep(0.05)  # Simulate work
            limiter.release(item_id)
        return acquired

    # Try to process 20 items concurrently
    tasks = [process_item(i) for i in range(20)]
    results = await asyncio.gather(*tasks)

    # All should succeed (waiting for slots)
    assert sum(results) == 20

    # Queue should be empty at end
    metrics = limiter.get_metrics()
    assert metrics["active_count"] == 0
    assert metrics["total_processed"] == 20
    assert metrics["peak_queue_depth"] <= 5


@pytest.mark.asyncio
async def test_rate_limiter_metrics():
    """Test rate limiter metrics accuracy."""
    limiter = AdaptiveRateLimiter(rate_per_second=20.0)

    # Process some requests
    for i in range(5):
        await limiter.acquire()
        if i % 2 == 0:
            limiter.record_success()
        else:
            limiter.record_failure()

    metrics = limiter.get_metrics()
    assert metrics["total_requests"] == 5
    assert metrics["total_failures"] == 2
    assert metrics["error_rate_pct"] == 40.0


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "-s"])
