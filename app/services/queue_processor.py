"""
Queue Processor Service

Processes queued analysis runs from the RunQueue system.
This integrates with the Worker to automatically start runs from the queue.
"""

import asyncio
import time
from datetime import datetime
from typing import Optional, Dict, Any
from app.core.logging_config import get_logger
from app.services.analysis_run_manager import get_run_manager
from app.services.metrics_service import get_metrics_service
from app.services.feed_limits_service import get_feed_limits_service
from app.dependencies import get_analysis_service
from app.domain.analysis.control import RunScope, RunParams

logger = get_logger(__name__)


class QueueProcessor:
    """
    Processes queued analysis runs and starts them when capacity is available.

    This service bridges the RunQueue system with the actual analysis execution.
    """

    def __init__(self, check_interval: float = 5.0):
        self.check_interval = check_interval
        self.run_manager = get_run_manager()
        self.analysis_service = get_analysis_service()
        self.metrics_service = get_metrics_service()
        self.limits_service = get_feed_limits_service()
        self.last_check = 0
        self.processing_active = True

    async def process_queue(self) -> Optional[Dict[str, Any]]:
        """
        Check for queued runs and start them if capacity allows.

        Returns:
            dict with run info if started, None otherwise
        """
        try:
            # Check if enough time has passed since last check
            current_time = time.time()
            if current_time - self.last_check < self.check_interval:
                return None

            self.last_check = current_time

            if not self.processing_active:
                logger.debug("Queue processing is paused")
                return None

            # Try to process next item in queue
            next_run_info = await self.run_manager.process_queue()

            if not next_run_info:
                logger.debug("No items in queue or no capacity available")
                return None

            # Extract run information
            queued_run_id = next_run_info["queued_run_id"]
            scope = next_run_info["scope"]
            params = next_run_info["params"]
            triggered_by = next_run_info["triggered_by"]
            priority = next_run_info["priority"]

            logger.info(f"Starting queued run {queued_run_id} with priority {priority}")

            # Check if analysis is allowed based on feed limits
            feed_id = self._extract_feed_id(scope)
            if feed_id:
                items_count = len(scope.item_ids) if scope.item_ids else 0
                is_allowed, block_reason = self.limits_service.check_analysis_allowed(feed_id, items_count)

                if not is_allowed:
                    logger.warning(f"Analysis blocked for feed {feed_id}: {block_reason}")

                    # Mark queued run as failed due to limits
                    await self.run_manager.queue_manager.mark_run_failed(
                        queued_run_id,
                        f"Blocked by limits: {block_reason}"
                    )

                    return None

            # Track timing for metrics
            processing_start = datetime.utcnow()
            queue_time_seconds = (processing_start - next_run_info.get("created_at", processing_start)).total_seconds()

            try:
                # Start the actual analysis run
                result = await self.analysis_service.start_analysis_run(scope, params, triggered_by)

                processing_end = datetime.utcnow()
                processing_time_seconds = (processing_end - processing_start).total_seconds()

                if result.success:
                    # Mark queued run as completed with reference to actual run
                    analysis_run_id = result.data.id
                    await self.run_manager.queue_manager.mark_run_completed(
                        queued_run_id,
                        analysis_run_id
                    )

                    # Record queue processing metrics
                    self.metrics_service.record_queue_processing(
                        queued_run_id=queued_run_id,
                        processing_time_seconds=processing_time_seconds,
                        queue_time_seconds=queue_time_seconds,
                        priority=str(priority),
                        success=True
                    )

                    logger.info(f"Successfully started analysis run {analysis_run_id} from queue item {queued_run_id}")

                    return {
                        "queued_run_id": queued_run_id,
                        "analysis_run_id": analysis_run_id,
                        "priority": priority,
                        "triggered_by": triggered_by,
                        "scope_type": scope.type,
                        "item_count": len(scope.item_ids) if scope.item_ids else 0,
                        "processing_time_seconds": processing_time_seconds,
                        "queue_time_seconds": queue_time_seconds
                    }
                else:
                    # Mark queued run as failed
                    await self.run_manager.queue_manager.mark_run_failed(
                        queued_run_id,
                        result.error
                    )

                    # Record failed processing metrics
                    self.metrics_service.record_queue_processing(
                        queued_run_id=queued_run_id,
                        processing_time_seconds=processing_time_seconds,
                        queue_time_seconds=queue_time_seconds,
                        priority=str(priority),
                        success=False
                    )

                    logger.error(f"Failed to start analysis run from queue item {queued_run_id}: {result.error}")
                    return None

            except Exception as e:
                processing_end = datetime.utcnow()
                processing_time_seconds = (processing_end - processing_start).total_seconds()

                # Mark queued run as failed
                await self.run_manager.queue_manager.mark_run_failed(
                    queued_run_id,
                    str(e)
                )

                # Record failed processing metrics
                self.metrics_service.record_queue_processing(
                    queued_run_id=queued_run_id,
                    processing_time_seconds=processing_time_seconds,
                    queue_time_seconds=queue_time_seconds,
                    priority=str(priority),
                    success=False
                )

                logger.error(f"Exception starting analysis run from queue item {queued_run_id}: {e}")
                return None

        except Exception as e:
            logger.error(f"Error in queue processing: {e}")
            return None

    def pause_processing(self):
        """Pause queue processing (for emergency stop scenarios)"""
        self.processing_active = False
        logger.info("Queue processing paused")

    def resume_processing(self):
        """Resume queue processing"""
        self.processing_active = True
        logger.info("Queue processing resumed")

    def is_processing_active(self) -> bool:
        """Check if queue processing is active"""
        return self.processing_active

    def set_check_interval(self, interval: float):
        """Update the check interval"""
        self.check_interval = interval
        logger.info(f"Queue check interval updated to {interval}s")

    def get_stats(self) -> Dict[str, Any]:
        """Get queue processor statistics"""
        return {
            "processing_active": self.processing_active,
            "check_interval": self.check_interval,
            "last_check": self.last_check,
            "time_since_last_check": time.time() - self.last_check if self.last_check > 0 else 0
        }

    def _extract_feed_id(self, scope: RunScope) -> Optional[int]:
        """Extract feed ID from RunScope for limits checking"""
        try:
            if scope.type == "feed" and scope.feed_ids:
                return scope.feed_ids[0]  # Use first feed ID for limits checking
            elif scope.type == "item" and scope.item_ids:
                # For item-based scopes, we'd need to look up the feed from items
                # For now, return None to skip limits checking for item scopes
                return None
            return None
        except Exception as e:
            logger.debug(f"Could not extract feed ID from scope: {e}")
            return None


# Singleton instance
_queue_processor = None


def get_queue_processor() -> QueueProcessor:
    """Get the singleton queue processor instance"""
    global _queue_processor
    if _queue_processor is None:
        _queue_processor = QueueProcessor()
    return _queue_processor