"""
Queue Limiter Service

Provides backpressure control to prevent system overload.
Limits concurrent analysis tasks to a configurable maximum.
"""

import asyncio
from typing import Optional
from datetime import datetime
from app.core.logging_config import get_logger

logger = get_logger(__name__)


class QueueLimiter:
    """
    Limits concurrent analysis operations to prevent system overload.

    Uses a semaphore to control max concurrent items being processed.
    Provides metrics on queue depth and wait times.
    """

    def __init__(self, max_concurrent: int = 50):
        """
        Initialize queue limiter.

        Args:
            max_concurrent: Maximum number of concurrent analysis operations
        """
        self.max_concurrent = max_concurrent
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._active_count = 0
        self._total_processed = 0
        self._total_wait_time_ms = 0
        self._peak_queue_depth = 0

        logger.info(f"QueueLimiter initialized with max_concurrent={max_concurrent}")

    async def acquire(self, item_id: int, timeout: Optional[float] = None) -> bool:
        """
        Acquire a slot for processing an item.

        Args:
            item_id: Item ID being processed
            timeout: Optional timeout in seconds

        Returns:
            True if slot acquired, False if timeout exceeded
        """
        wait_start = datetime.utcnow()

        try:
            if timeout:
                await asyncio.wait_for(
                    self._semaphore.acquire(),
                    timeout=timeout
                )
            else:
                await self._semaphore.acquire()

            # Track metrics
            wait_time_ms = (datetime.utcnow() - wait_start).total_seconds() * 1000
            self._active_count += 1
            self._total_wait_time_ms += wait_time_ms

            if self._active_count > self._peak_queue_depth:
                self._peak_queue_depth = self._active_count

            logger.debug(
                f"Acquired slot for item {item_id} "
                f"(active: {self._active_count}/{self.max_concurrent}, "
                f"wait: {wait_time_ms:.1f}ms)"
            )

            return True

        except asyncio.TimeoutError:
            logger.warning(
                f"Timeout acquiring slot for item {item_id} after {timeout}s "
                f"(queue full: {self._active_count}/{self.max_concurrent})"
            )
            return False

    def release(self, item_id: int):
        """
        Release a processing slot.

        Args:
            item_id: Item ID that finished processing
        """
        self._semaphore.release()
        self._active_count = max(0, self._active_count - 1)
        self._total_processed += 1

        logger.debug(
            f"Released slot for item {item_id} "
            f"(active: {self._active_count}/{self.max_concurrent})"
        )

    def get_metrics(self) -> dict:
        """
        Get current queue metrics.

        Returns:
            Dict with queue statistics
        """
        avg_wait_ms = (
            self._total_wait_time_ms / self._total_processed
            if self._total_processed > 0
            else 0
        )

        return {
            "max_concurrent": self.max_concurrent,
            "active_count": self._active_count,
            "available_slots": self.max_concurrent - self._active_count,
            "utilization_pct": (self._active_count / self.max_concurrent) * 100,
            "total_processed": self._total_processed,
            "avg_wait_ms": round(avg_wait_ms, 2),
            "peak_queue_depth": self._peak_queue_depth
        }

    def is_available(self) -> bool:
        """Check if slots are available without blocking."""
        return self._active_count < self.max_concurrent

    def reset_metrics(self):
        """Reset statistics (useful for testing/monitoring)."""
        self._total_processed = 0
        self._total_wait_time_ms = 0
        self._peak_queue_depth = self._active_count
        logger.info("Queue limiter metrics reset")


# Global instance (singleton pattern)
_global_queue_limiter: Optional[QueueLimiter] = None


def get_queue_limiter(max_concurrent: int = 50) -> QueueLimiter:
    """
    Get or create global queue limiter instance.

    Args:
        max_concurrent: Max concurrent operations (only used on first call)

    Returns:
        QueueLimiter instance
    """
    global _global_queue_limiter

    if _global_queue_limiter is None:
        _global_queue_limiter = QueueLimiter(max_concurrent)

    return _global_queue_limiter
