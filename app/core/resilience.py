"""Resilience patterns: retry mechanisms, circuit breakers, and failure handling."""

import time
import asyncio
import random
from typing import Optional, Callable, Any, Dict, Union, Type
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, field
from functools import wraps

from app.core.logging_config import get_logger
from app.core.metrics import metrics
from app.core.exceptions import ExternalServiceException, DatabaseException

logger = get_logger(__name__)


class CircuitState(str, Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, rejecting requests
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class RetryConfig:
    """Configuration for retry mechanisms."""
    max_attempts: int = 3
    initial_delay: float = 1.0  # seconds
    max_delay: float = 60.0     # seconds
    exponential_base: float = 2.0
    jitter: bool = True
    retry_on: tuple = (ExternalServiceException, ConnectionError, TimeoutError)


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker."""
    failure_threshold: int = 5
    success_threshold: int = 3
    timeout: float = 60.0  # seconds
    failure_rate_threshold: float = 0.5  # 50%
    minimum_requests: int = 10


@dataclass
class CircuitBreakerState:
    """Current state of a circuit breaker."""
    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    success_count: int = 0
    last_failure_time: Optional[datetime] = None
    last_state_change: datetime = field(default_factory=datetime.utcnow)
    total_requests: int = 0
    successful_requests: int = 0


class RetryStrategy:
    """Base retry strategy."""

    def __init__(self, config: RetryConfig):
        self.config = config

    def get_delay(self, attempt: int) -> float:
        """Calculate delay for given attempt number."""
        if attempt <= 0:
            return 0

        # Exponential backoff
        delay = self.config.initial_delay * (self.config.exponential_base ** (attempt - 1))
        delay = min(delay, self.config.max_delay)

        # Add jitter to prevent thundering herd
        if self.config.jitter:
            delay = delay * (0.5 + random.random() * 0.5)

        return delay

    def should_retry(self, attempt: int, exception: Exception) -> bool:
        """Determine if we should retry given the attempt and exception."""
        if attempt >= self.config.max_attempts:
            return False

        return isinstance(exception, self.config.retry_on)


class CircuitBreaker:
    """Circuit breaker implementation."""

    def __init__(self, name: str, config: CircuitBreakerConfig):
        self.name = name
        self.config = config
        self.state = CircuitBreakerState()
        self._lock = asyncio.Lock()

    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with circuit breaker protection."""
        async with self._lock:
            if self.state.state == CircuitState.OPEN:
                if self._should_attempt_reset():
                    self._transition_to_half_open()
                else:
                    raise ExternalServiceException(
                        service=self.name,
                        message="Circuit breaker is OPEN"
                    )

        # Execute the function
        try:
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)

            await self._record_success()
            return result

        except Exception as e:
            await self._record_failure(e)
            raise

    async def _record_success(self):
        """Record a successful operation."""
        async with self._lock:
            self.state.total_requests += 1
            self.state.successful_requests += 1

            if self.state.state == CircuitState.HALF_OPEN:
                self.state.success_count += 1
                if self.state.success_count >= self.config.success_threshold:
                    self._transition_to_closed()
            elif self.state.state == CircuitState.CLOSED:
                # Reset failure count on success
                self.state.failure_count = 0

            self._record_metrics("success")

    async def _record_failure(self, exception: Exception):
        """Record a failed operation."""
        async with self._lock:
            self.state.total_requests += 1
            self.state.failure_count += 1
            self.state.last_failure_time = datetime.utcnow()

            # Check if we should open the circuit
            if self.state.state == CircuitState.CLOSED:
                if self._should_open_circuit():
                    self._transition_to_open()
            elif self.state.state == CircuitState.HALF_OPEN:
                self._transition_to_open()

            self._record_metrics("failure", exception)

    def _should_open_circuit(self) -> bool:
        """Determine if circuit should be opened."""
        if self.state.total_requests < self.config.minimum_requests:
            return False

        failure_rate = 1 - (self.state.successful_requests / self.state.total_requests)
        return (
            self.state.failure_count >= self.config.failure_threshold or
            failure_rate >= self.config.failure_rate_threshold
        )

    def _should_attempt_reset(self) -> bool:
        """Determine if we should attempt to reset from OPEN state."""
        if not self.state.last_failure_time:
            return True

        time_since_failure = datetime.utcnow() - self.state.last_failure_time
        return time_since_failure.total_seconds() >= self.config.timeout

    def _transition_to_open(self):
        """Transition to OPEN state."""
        self.state.state = CircuitState.OPEN
        self.state.last_state_change = datetime.utcnow()
        logger.warning(f"Circuit breaker '{self.name}' opened")

    def _transition_to_half_open(self):
        """Transition to HALF_OPEN state."""
        self.state.state = CircuitState.HALF_OPEN
        self.state.success_count = 0
        self.state.last_state_change = datetime.utcnow()
        logger.info(f"Circuit breaker '{self.name}' half-opened")

    def _transition_to_closed(self):
        """Transition to CLOSED state."""
        self.state.state = CircuitState.CLOSED
        self.state.failure_count = 0
        self.state.success_count = 0
        self.state.last_state_change = datetime.utcnow()
        logger.info(f"Circuit breaker '{self.name}' closed")

    def _record_metrics(self, result: str, exception: Exception = None):
        """Record circuit breaker metrics."""
        tags = {
            "circuit_breaker": self.name,
            "state": self.state.state.value,
            "result": result
        }

        if exception:
            tags["exception_type"] = type(exception).__name__

        metrics.increment_counter("circuit_breaker_operations", tags=tags)

    def get_state(self) -> Dict[str, Any]:
        """Get current circuit breaker state."""
        return {
            "name": self.name,
            "state": self.state.state.value,
            "failure_count": self.state.failure_count,
            "success_count": self.state.success_count,
            "total_requests": self.state.total_requests,
            "successful_requests": self.state.successful_requests,
            "failure_rate": 1 - (self.state.successful_requests / max(self.state.total_requests, 1)),
            "last_failure_time": self.state.last_failure_time.isoformat() if self.state.last_failure_time else None,
            "last_state_change": self.state.last_state_change.isoformat()
        }


class ResilienceManager:
    """Manager for retry and circuit breaker functionality."""

    def __init__(self):
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.retry_strategies: Dict[str, RetryStrategy] = {}

    def get_circuit_breaker(self, name: str, config: Optional[CircuitBreakerConfig] = None) -> CircuitBreaker:
        """Get or create a circuit breaker."""
        if name not in self.circuit_breakers:
            config = config or CircuitBreakerConfig()
            self.circuit_breakers[name] = CircuitBreaker(name, config)
        return self.circuit_breakers[name]

    def get_retry_strategy(self, name: str, config: Optional[RetryConfig] = None) -> RetryStrategy:
        """Get or create a retry strategy."""
        if name not in self.retry_strategies:
            config = config or RetryConfig()
            self.retry_strategies[name] = RetryStrategy(config)
        return self.retry_strategies[name]

    async def execute_with_resilience(
        self,
        func: Callable,
        circuit_breaker_name: Optional[str] = None,
        retry_strategy_name: Optional[str] = None,
        *args,
        **kwargs
    ) -> Any:
        """Execute function with retry and circuit breaker protection."""
        operation_name = func.__name__ if hasattr(func, '__name__') else "unknown"

        # Get circuit breaker if specified
        circuit_breaker = None
        if circuit_breaker_name:
            circuit_breaker = self.get_circuit_breaker(circuit_breaker_name)

        # Get retry strategy if specified
        retry_strategy = None
        if retry_strategy_name:
            retry_strategy = self.get_retry_strategy(retry_strategy_name)

        # Execute with retry logic
        attempt = 0
        last_exception = None

        while attempt < (retry_strategy.config.max_attempts if retry_strategy else 1):
            attempt += 1

            try:
                # Execute with circuit breaker if available
                if circuit_breaker:
                    return await circuit_breaker.call(func, *args, **kwargs)
                else:
                    if asyncio.iscoroutinefunction(func):
                        return await func(*args, **kwargs)
                    else:
                        return func(*args, **kwargs)

            except Exception as e:
                last_exception = e

                # Check if we should retry
                if retry_strategy and retry_strategy.should_retry(attempt, e):
                    delay = retry_strategy.get_delay(attempt)
                    logger.warning(
                        f"Operation '{operation_name}' failed, retrying in {delay:.2f}s",
                        attempt=attempt,
                        max_attempts=retry_strategy.config.max_attempts,
                        error=str(e)
                    )

                    # Record retry metrics
                    metrics.increment_counter(
                        "operation_retries",
                        tags={
                            "operation": operation_name,
                            "attempt": str(attempt),
                            "exception_type": type(e).__name__
                        }
                    )

                    await asyncio.sleep(delay)
                    continue
                else:
                    # No more retries or not retryable
                    break

        # All retries exhausted
        logger.error(
            f"Operation '{operation_name}' failed after {attempt} attempts",
            final_error=str(last_exception)
        )

        metrics.increment_counter(
            "operation_failures",
            tags={
                "operation": operation_name,
                "total_attempts": str(attempt),
                "exception_type": type(last_exception).__name__
            }
        )

        raise last_exception

    def get_all_circuit_breakers(self) -> Dict[str, Dict[str, Any]]:
        """Get state of all circuit breakers."""
        return {name: cb.get_state() for name, cb in self.circuit_breakers.items()}


# Global resilience manager
resilience = ResilienceManager()


# Decorators for easy use
def with_retry(
    retry_config: Optional[RetryConfig] = None,
    strategy_name: Optional[str] = None
):
    """Decorator to add retry functionality to a function."""
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            strategy_name_to_use = strategy_name or func.__name__
            if retry_config:
                resilience.retry_strategies[strategy_name_to_use] = RetryStrategy(retry_config)

            return await resilience.execute_with_resilience(
                func,
                retry_strategy_name=strategy_name_to_use,
                *args,
                **kwargs
            )

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            return asyncio.run(async_wrapper(*args, **kwargs))

        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper

    return decorator


def with_circuit_breaker(
    circuit_config: Optional[CircuitBreakerConfig] = None,
    breaker_name: Optional[str] = None
):
    """Decorator to add circuit breaker functionality to a function."""
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            breaker_name_to_use = breaker_name or func.__name__
            if circuit_config:
                resilience.circuit_breakers[breaker_name_to_use] = CircuitBreaker(
                    breaker_name_to_use, circuit_config
                )

            return await resilience.execute_with_resilience(
                func,
                circuit_breaker_name=breaker_name_to_use,
                *args,
                **kwargs
            )

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            return asyncio.run(async_wrapper(*args, **kwargs))

        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper

    return decorator


def with_resilience(
    retry_config: Optional[RetryConfig] = None,
    circuit_config: Optional[CircuitBreakerConfig] = None,
    name: Optional[str] = None
):
    """Decorator to add both retry and circuit breaker functionality."""
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            name_to_use = name or func.__name__

            # Register configurations if provided
            if retry_config:
                resilience.retry_strategies[name_to_use] = RetryStrategy(retry_config)
            if circuit_config:
                resilience.circuit_breakers[name_to_use] = CircuitBreaker(name_to_use, circuit_config)

            return await resilience.execute_with_resilience(
                func,
                circuit_breaker_name=name_to_use if circuit_config else None,
                retry_strategy_name=name_to_use if retry_config else None,
                *args,
                **kwargs
            )

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            return asyncio.run(async_wrapper(*args, **kwargs))

        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper

    return decorator


# Predefined configurations for common use cases
EXTERNAL_SERVICE_RETRY = RetryConfig(
    max_attempts=3,
    initial_delay=1.0,
    max_delay=30.0,
    retry_on=(ExternalServiceException, ConnectionError, TimeoutError)
)

DATABASE_RETRY = RetryConfig(
    max_attempts=2,
    initial_delay=0.5,
    max_delay=5.0,
    retry_on=(DatabaseException, ConnectionError)
)

EXTERNAL_SERVICE_CIRCUIT_BREAKER = CircuitBreakerConfig(
    failure_threshold=5,
    success_threshold=3,
    timeout=60.0,
    failure_rate_threshold=0.5
)

CRITICAL_SERVICE_CIRCUIT_BREAKER = CircuitBreakerConfig(
    failure_threshold=3,
    success_threshold=2,
    timeout=30.0,
    failure_rate_threshold=0.3
)


# API endpoints for resilience monitoring
from fastapi import APIRouter

def create_resilience_router() -> APIRouter:
    """Create resilience monitoring API router."""
    router = APIRouter(prefix="/resilience", tags=["resilience"])

    @router.get("/circuit-breakers")
    async def get_circuit_breakers():
        """Get state of all circuit breakers."""
        return resilience.get_all_circuit_breakers()

    @router.get("/circuit-breakers/{name}")
    async def get_circuit_breaker(name: str):
        """Get state of a specific circuit breaker."""
        if name not in resilience.circuit_breakers:
            return {"error": f"Circuit breaker '{name}' not found"}, 404

        return resilience.circuit_breakers[name].get_state()

    @router.post("/circuit-breakers/{name}/reset")
    async def reset_circuit_breaker(name: str):
        """Reset a circuit breaker to closed state."""
        if name not in resilience.circuit_breakers:
            return {"error": f"Circuit breaker '{name}' not found"}, 404

        cb = resilience.circuit_breakers[name]
        cb._transition_to_closed()

        return {"message": f"Circuit breaker '{name}' reset to closed state"}

    return router