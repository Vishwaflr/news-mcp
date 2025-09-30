"""
Error Recovery Service with Circuit Breaker Pattern

Provides automatic error recovery, retry logic, and circuit breaker
functionality for critical system components.

Key Features:
- Exponential backoff retry
- Circuit breaker pattern
- Error classification and handling
- Automatic recovery strategies
- Metrics and monitoring

Created: 2025-09-30
"""

from typing import Optional, Callable, Any, Dict, List
from datetime import datetime, timedelta
from enum import Enum
import asyncio
import time
from dataclasses import dataclass, field
from app.core.logging_config import get_logger

logger = get_logger(__name__)


class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, rejecting requests
    HALF_OPEN = "half_open"  # Testing if recovered


class ErrorType(Enum):
    """Classified error types for targeted recovery"""
    RATE_LIMIT = "rate_limit"      # 429 errors
    SERVER_ERROR = "server_error"   # 5xx errors
    TIMEOUT = "timeout"             # Connection/timeout
    PARSE_ERROR = "parse_error"     # JSON/format errors
    AUTH_ERROR = "auth_error"       # Authentication issues
    NETWORK = "network"             # Network issues
    DATABASE = "database"           # Database errors
    UNKNOWN = "unknown"             # Unclassified


@dataclass
class ErrorStats:
    """Track error statistics for monitoring"""
    total_errors: int = 0
    errors_by_type: Dict[str, int] = field(default_factory=dict)
    last_error_time: Optional[datetime] = None
    consecutive_errors: int = 0
    recovery_attempts: int = 0
    successful_recoveries: int = 0


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker"""
    failure_threshold: int = 5          # Failures before opening
    success_threshold: int = 2          # Successes to close from half-open
    timeout_seconds: int = 60           # Time before trying half-open
    half_open_requests: int = 3         # Test requests in half-open


class CircuitBreaker:
    """
    Circuit Breaker implementation for fault tolerance.

    Prevents cascading failures by temporarily blocking requests
    to failing services.
    """

    def __init__(self, name: str, config: Optional[CircuitBreakerConfig] = None):
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        self.half_open_attempts = 0
        self.stats = ErrorStats()

    def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with circuit breaker protection"""
        # Check circuit state
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self._transition_to_half_open()
            else:
                raise Exception(f"Circuit breaker {self.name} is OPEN")

        # Execute function
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure(e)
            raise

    async def call_async(self, func: Callable, *args, **kwargs) -> Any:
        """Execute async function with circuit breaker protection"""
        # Check circuit state
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self._transition_to_half_open()
            else:
                raise Exception(f"Circuit breaker {self.name} is OPEN")

        # Execute function
        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure(e)
            raise

    def _on_success(self):
        """Handle successful execution"""
        self.failure_count = 0

        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.config.success_threshold:
                self._transition_to_closed()

        self.stats.consecutive_errors = 0

    def _on_failure(self, error: Exception):
        """Handle failed execution"""
        self.failure_count += 1
        self.last_failure_time = datetime.utcnow()

        # Update stats
        self.stats.total_errors += 1
        self.stats.consecutive_errors += 1
        self.stats.last_error_time = self.last_failure_time

        error_type = self._classify_error(error)
        self.stats.errors_by_type[error_type] = self.stats.errors_by_type.get(error_type, 0) + 1

        # State transitions
        if self.state == CircuitState.CLOSED:
            if self.failure_count >= self.config.failure_threshold:
                self._transition_to_open()
        elif self.state == CircuitState.HALF_OPEN:
            self._transition_to_open()

    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to try recovery"""
        if not self.last_failure_time:
            return True

        time_since_failure = (datetime.utcnow() - self.last_failure_time).total_seconds()
        return time_since_failure >= self.config.timeout_seconds

    def _transition_to_open(self):
        """Transition to OPEN state"""
        self.state = CircuitState.OPEN
        self.half_open_attempts = 0
        logger.warning(f"Circuit breaker {self.name} opened after {self.failure_count} failures")

    def _transition_to_half_open(self):
        """Transition to HALF_OPEN state"""
        self.state = CircuitState.HALF_OPEN
        self.success_count = 0
        self.half_open_attempts = 0
        logger.info(f"Circuit breaker {self.name} attempting recovery (half-open)")

    def _transition_to_closed(self):
        """Transition to CLOSED state"""
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.stats.successful_recoveries += 1
        logger.info(f"Circuit breaker {self.name} closed (recovered)")

    def _classify_error(self, error: Exception) -> str:
        """Classify error type for statistics"""
        error_str = str(error).lower()

        if "429" in error_str or "rate limit" in error_str:
            return ErrorType.RATE_LIMIT.value
        elif "500" in error_str or "502" in error_str or "503" in error_str:
            return ErrorType.SERVER_ERROR.value
        elif "timeout" in error_str or "connection" in error_str:
            return ErrorType.TIMEOUT.value
        elif "parse" in error_str or "json" in error_str:
            return ErrorType.PARSE_ERROR.value
        elif "auth" in error_str or "api" in error_str:
            return ErrorType.AUTH_ERROR.value
        elif "database" in error_str or "sqlalchemy" in error_str:
            return ErrorType.DATABASE.value
        else:
            return ErrorType.UNKNOWN.value

    def get_status(self) -> Dict[str, Any]:
        """Get current circuit breaker status"""
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "stats": {
                "total_errors": self.stats.total_errors,
                "consecutive_errors": self.stats.consecutive_errors,
                "errors_by_type": self.stats.errors_by_type,
                "recovery_attempts": self.stats.recovery_attempts,
                "successful_recoveries": self.stats.successful_recoveries,
                "last_error": self.stats.last_error_time.isoformat() if self.stats.last_error_time else None
            }
        }


class RetryStrategy:
    """
    Retry strategies with exponential backoff and jitter.
    """

    @staticmethod
    def exponential_backoff(
        attempt: int,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        jitter: bool = True
    ) -> float:
        """Calculate delay with exponential backoff"""
        delay = min(base_delay * (2 ** attempt), max_delay)

        if jitter:
            # Add random jitter to prevent thundering herd
            import random
            delay = delay * (0.5 + random.random())

        return delay

    @staticmethod
    async def retry_with_backoff(
        func: Callable,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        recoverable_errors: Optional[List[type]] = None
    ) -> Any:
        """
        Retry function with exponential backoff.

        Args:
            func: Function to retry
            max_attempts: Maximum retry attempts
            base_delay: Initial delay in seconds
            max_delay: Maximum delay in seconds
            recoverable_errors: List of error types to retry

        Returns:
            Function result

        Raises:
            Last exception if all retries fail
        """
        recoverable_errors = recoverable_errors or [Exception]
        last_exception = None

        for attempt in range(max_attempts):
            try:
                # Try to execute function
                if asyncio.iscoroutinefunction(func):
                    return await func()
                else:
                    return func()

            except tuple(recoverable_errors) as e:
                last_exception = e

                if attempt < max_attempts - 1:
                    # Calculate delay
                    delay = RetryStrategy.exponential_backoff(
                        attempt, base_delay, max_delay
                    )

                    logger.warning(
                        f"Attempt {attempt + 1}/{max_attempts} failed: {e}. "
                        f"Retrying in {delay:.1f}s..."
                    )

                    await asyncio.sleep(delay)
                else:
                    logger.error(f"All {max_attempts} attempts failed: {e}")

        raise last_exception


class ErrorRecoveryService:
    """
    Main error recovery service coordinating all recovery mechanisms.
    """

    def __init__(self):
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.recovery_strategies: Dict[str, Callable] = {
            ErrorType.RATE_LIMIT: self._recover_from_rate_limit,
            ErrorType.SERVER_ERROR: self._recover_from_server_error,
            ErrorType.TIMEOUT: self._recover_from_timeout,
            ErrorType.DATABASE: self._recover_from_database_error,
            ErrorType.AUTH_ERROR: self._recover_from_auth_error,
        }

    def get_circuit_breaker(self, name: str, config: Optional[CircuitBreakerConfig] = None) -> CircuitBreaker:
        """Get or create circuit breaker for service"""
        if name not in self.circuit_breakers:
            self.circuit_breakers[name] = CircuitBreaker(name, config)
        return self.circuit_breakers[name]

    async def execute_with_recovery(
        self,
        func: Callable,
        service_name: str,
        max_retries: int = 3,
        circuit_breaker: bool = True
    ) -> Any:
        """
        Execute function with full error recovery.

        Args:
            func: Function to execute
            service_name: Name of service (for circuit breaker)
            max_retries: Maximum retry attempts
            circuit_breaker: Whether to use circuit breaker

        Returns:
            Function result
        """
        # Use circuit breaker if enabled
        if circuit_breaker:
            cb = self.get_circuit_breaker(service_name)
            if asyncio.iscoroutinefunction(func):
                # For async functions, create wrapper that awaits the circuit breaker
                async def executor():
                    return await cb.call_async(func)
            else:
                # For sync functions, just use the circuit breaker
                executor = lambda: cb.call(func)
        else:
            executor = func

        # Execute with retry
        try:
            return await RetryStrategy.retry_with_backoff(
                executor,
                max_attempts=max_retries,
                recoverable_errors=[Exception]
            )
        except Exception as e:
            # Try specific recovery strategy
            error_type = self._classify_error_type(e)
            if error_type in self.recovery_strategies:
                logger.info(f"Attempting recovery for {error_type.value} error")
                return await self.recovery_strategies[error_type](func, e)
            raise

    def _classify_error_type(self, error: Exception) -> ErrorType:
        """Classify error into ErrorType"""
        error_str = str(error).lower()

        if "429" in error_str or "rate limit" in error_str:
            return ErrorType.RATE_LIMIT
        elif "500" in error_str or "502" in error_str or "503" in error_str:
            return ErrorType.SERVER_ERROR
        elif "timeout" in error_str or "connection" in error_str:
            return ErrorType.TIMEOUT
        elif "auth" in error_str or "api" in error_str:
            return ErrorType.AUTH_ERROR
        elif "database" in error_str or "sqlalchemy" in error_str:
            return ErrorType.DATABASE
        else:
            return ErrorType.UNKNOWN

    async def _recover_from_rate_limit(self, func: Callable, error: Exception) -> Any:
        """Recovery strategy for rate limit errors"""
        # Extract retry-after if available
        retry_after = 60  # Default to 60 seconds
        error_str = str(error)

        if "retry-after" in error_str.lower():
            # Try to extract retry-after value
            try:
                import re
                match = re.search(r'retry.after[:\s]+(\d+)', error_str, re.IGNORECASE)
                if match:
                    retry_after = int(match.group(1))
            except:
                pass

        logger.info(f"Rate limited. Waiting {retry_after} seconds before retry...")
        await asyncio.sleep(retry_after)

        # Retry with reduced rate
        return await func()

    async def _recover_from_server_error(self, func: Callable, error: Exception) -> Any:
        """Recovery strategy for server errors"""
        # Wait longer for server recovery
        logger.info("Server error detected. Waiting 30 seconds for recovery...")
        await asyncio.sleep(30)

        # Retry with exponential backoff
        return await RetryStrategy.retry_with_backoff(
            func,
            max_attempts=5,
            base_delay=5.0,
            max_delay=120.0
        )

    async def _recover_from_timeout(self, func: Callable, error: Exception) -> Any:
        """Recovery strategy for timeout errors"""
        logger.info("Timeout error. Retrying with increased timeout...")

        # If possible, increase timeout in function
        # This would need to be implemented based on specific function

        return await RetryStrategy.retry_with_backoff(
            func,
            max_attempts=3,
            base_delay=2.0
        )

    async def _recover_from_database_error(self, func: Callable, error: Exception) -> Any:
        """Recovery strategy for database errors"""
        from app.database import engine

        logger.info("Database error detected. Attempting connection recovery...")

        # Try to reset database connection
        try:
            engine.dispose()  # Close all connections
            await asyncio.sleep(2)
        except:
            pass

        # Retry with backoff
        return await RetryStrategy.retry_with_backoff(
            func,
            max_attempts=3,
            base_delay=1.0
        )

    async def _recover_from_auth_error(self, func: Callable, error: Exception) -> Any:
        """Recovery strategy for authentication errors"""
        logger.error("Authentication error. Manual intervention may be required.")

        # Could implement token refresh logic here
        # For now, just fail fast
        raise error

    def get_status(self) -> Dict[str, Any]:
        """Get status of all circuit breakers"""
        return {
            cb_name: cb.get_status()
            for cb_name, cb in self.circuit_breakers.items()
        }

    def reset_circuit_breaker(self, name: str):
        """Manually reset a circuit breaker"""
        if name in self.circuit_breakers:
            cb = self.circuit_breakers[name]
            cb.state = CircuitState.CLOSED
            cb.failure_count = 0
            cb.success_count = 0
            logger.info(f"Circuit breaker {name} manually reset")


# Global instance
error_recovery_service = ErrorRecoveryService()


def get_error_recovery_service() -> ErrorRecoveryService:
    """Get global error recovery service instance"""
    return error_recovery_service