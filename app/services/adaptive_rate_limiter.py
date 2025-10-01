"""
Adaptive Rate Limiter with Circuit Breaker

Provides intelligent rate limiting for API calls with:
- Token bucket algorithm for smooth rate limiting
- Circuit breaker pattern for failure handling
- Adaptive rate adjustment based on error rates
"""

import asyncio
import time
from typing import Optional
from datetime import datetime, timedelta
from enum import Enum
from app.core.logging_config import get_logger

logger = get_logger(__name__)


class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Blocking requests due to failures
    HALF_OPEN = "half_open"  # Testing if service recovered


class AdaptiveRateLimiter:
    """
    Rate limiter with circuit breaker and adaptive rate control.

    Features:
    - Token bucket rate limiting
    - Circuit breaker on consecutive failures
    - Automatic rate reduction on errors
    - Metrics tracking
    """

    def __init__(
        self,
        rate_per_second: float = 3.0,
        max_burst: int = 5,
        circuit_threshold: int = 5,
        circuit_timeout_seconds: float = 30.0,
        min_rate: float = 0.5
    ):
        """
        Initialize adaptive rate limiter.

        Args:
            rate_per_second: Target requests per second
            max_burst: Maximum burst size (token bucket capacity)
            circuit_threshold: Consecutive failures to open circuit
            circuit_timeout_seconds: Time before trying half-open
            min_rate: Minimum rate when backing off
        """
        self.base_rate = rate_per_second
        self.current_rate = rate_per_second
        self.min_rate = min_rate
        self.max_burst = max_burst

        # Token bucket
        self._tokens = float(max_burst)
        self._last_update = time.monotonic()
        self._lock = asyncio.Lock()

        # Circuit breaker
        self.circuit_threshold = circuit_threshold
        self.circuit_timeout = circuit_timeout_seconds
        self._circuit_state = CircuitState.CLOSED
        self._consecutive_failures = 0
        self._circuit_opened_at: Optional[float] = None
        self._half_open_test_count = 0

        # Metrics
        self._total_requests = 0
        self._total_failures = 0
        self._total_wait_time_ms = 0
        self._circuit_opens = 0

        logger.info(
            f"AdaptiveRateLimiter initialized: "
            f"rate={rate_per_second}/s, burst={max_burst}, "
            f"circuit_threshold={circuit_threshold}"
        )

    async def acquire(self, timeout: Optional[float] = None) -> bool:
        """
        Acquire permission to make a request.

        Args:
            timeout: Optional timeout in seconds

        Returns:
            True if permission granted, False if circuit open or timeout

        Raises:
            asyncio.TimeoutError: If timeout exceeded
        """
        start_time = time.monotonic()

        # Check circuit breaker
        if not await self._check_circuit():
            return False

        # Wait for token
        async with self._lock:
            success = await self._wait_for_token(timeout)

            if success:
                self._total_requests += 1
                wait_time_ms = (time.monotonic() - start_time) * 1000
                self._total_wait_time_ms += wait_time_ms

                logger.debug(
                    f"Rate limit acquired (tokens: {self._tokens:.2f}, "
                    f"rate: {self.current_rate:.2f}/s, wait: {wait_time_ms:.1f}ms)"
                )

            return success

    async def _wait_for_token(self, timeout: Optional[float]) -> bool:
        """Wait until a token is available."""
        deadline = time.monotonic() + timeout if timeout else None

        while True:
            # Refill tokens based on elapsed time
            now = time.monotonic()
            elapsed = now - self._last_update
            self._tokens = min(
                self.max_burst,
                self._tokens + (elapsed * self.current_rate)
            )
            self._last_update = now

            # Check if token available
            if self._tokens >= 1.0:
                self._tokens -= 1.0
                return True

            # Check timeout
            if deadline and now >= deadline:
                logger.warning("Rate limit timeout exceeded")
                return False

            # Wait for next token
            wait_time = (1.0 - self._tokens) / self.current_rate
            await asyncio.sleep(min(wait_time, 0.1))

    async def _check_circuit(self) -> bool:
        """Check circuit breaker state."""
        if self._circuit_state == CircuitState.CLOSED:
            return True

        if self._circuit_state == CircuitState.OPEN:
            # Check if timeout elapsed
            if self._circuit_opened_at:
                elapsed = time.monotonic() - self._circuit_opened_at
                if elapsed >= self.circuit_timeout:
                    self._circuit_state = CircuitState.HALF_OPEN
                    self._half_open_test_count = 0
                    logger.info("Circuit breaker entering HALF_OPEN state")
                    return True

            logger.debug("Circuit breaker OPEN - blocking request")
            return False

        if self._circuit_state == CircuitState.HALF_OPEN:
            # Allow limited test requests
            if self._half_open_test_count < 3:
                self._half_open_test_count += 1
                logger.debug(f"Circuit HALF_OPEN - allowing test request {self._half_open_test_count}/3")
                return True
            else:
                logger.debug("Circuit HALF_OPEN - test quota exceeded")
                return False

        return False

    def record_success(self):
        """Record successful request."""
        self._consecutive_failures = 0

        if self._circuit_state == CircuitState.HALF_OPEN:
            # Successful requests in half-open → close circuit
            if self._half_open_test_count >= 2:
                self._circuit_state = CircuitState.CLOSED
                self.current_rate = self.base_rate  # Restore rate
                logger.info("Circuit breaker CLOSED - service recovered")

    def record_failure(self):
        """Record failed request and update circuit breaker."""
        self._total_failures += 1
        self._consecutive_failures += 1

        # Reduce rate adaptively
        if self._consecutive_failures >= 2:
            old_rate = self.current_rate
            self.current_rate = max(
                self.min_rate,
                self.current_rate * 0.75  # Reduce by 25%
            )
            if old_rate != self.current_rate:
                logger.warning(
                    f"Adaptive rate reduction: {old_rate:.2f} → {self.current_rate:.2f}/s "
                    f"(failures: {self._consecutive_failures})"
                )

        # Check circuit breaker threshold
        if self._consecutive_failures >= self.circuit_threshold:
            if self._circuit_state != CircuitState.OPEN:
                self._circuit_state = CircuitState.OPEN
                self._circuit_opened_at = time.monotonic()
                self._circuit_opens += 1
                logger.error(
                    f"Circuit breaker OPENED after {self._consecutive_failures} "
                    f"consecutive failures (total opens: {self._circuit_opens})"
                )

    def get_metrics(self) -> dict:
        """Get rate limiter metrics."""
        error_rate = (
            (self._total_failures / self._total_requests * 100)
            if self._total_requests > 0
            else 0
        )

        avg_wait_ms = (
            self._total_wait_time_ms / self._total_requests
            if self._total_requests > 0
            else 0
        )

        return {
            "base_rate": self.base_rate,
            "current_rate": self.current_rate,
            "circuit_state": self._circuit_state.value,
            "tokens_available": round(self._tokens, 2),
            "total_requests": self._total_requests,
            "total_failures": self._total_failures,
            "error_rate_pct": round(error_rate, 2),
            "consecutive_failures": self._consecutive_failures,
            "circuit_opens": self._circuit_opens,
            "avg_wait_ms": round(avg_wait_ms, 2)
        }

    def reset_metrics(self):
        """Reset statistics."""
        self._total_requests = 0
        self._total_failures = 0
        self._total_wait_time_ms = 0
        logger.info("Rate limiter metrics reset")


# Global instance
_global_rate_limiter: Optional[AdaptiveRateLimiter] = None


def get_rate_limiter(rate_per_second: float = 3.0) -> AdaptiveRateLimiter:
    """
    Get or create global rate limiter instance.

    Args:
        rate_per_second: Rate limit (only used on first call)

    Returns:
        AdaptiveRateLimiter instance
    """
    global _global_rate_limiter

    if _global_rate_limiter is None:
        _global_rate_limiter = AdaptiveRateLimiter(rate_per_second=rate_per_second)

    return _global_rate_limiter
