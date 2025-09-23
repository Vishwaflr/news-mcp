"""
Run Queue Manager Service

Manages the analysis run queue with priority-based scheduling.
"""

import asyncio
from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlmodel import Session, select, desc, and_
from app.core.logging_config import get_logger
from app.database import engine
from app.models.run_queue import QueuedRun, RunPriority, RunStatus
from app.domain.analysis.control import RunScope, RunParams
import json
import hashlib

logger = get_logger(__name__)


class RunQueueManager:
    """
    Manages the analysis run queue with priority-based scheduling.

    Features:
    - Priority-based queue (HIGH > MEDIUM > LOW)
    - Duplicate detection via scope hash
    - Database persistence
    - Queue position management
    """

    def __init__(self):
        self.priority_order = {
            RunPriority.HIGH: 1,
            RunPriority.MEDIUM: 2,
            RunPriority.LOW: 3
        }

    def _generate_scope_hash(self, scope: RunScope, params: RunParams) -> str:
        """Generate a hash for duplicate detection"""
        # Create a deterministic representation
        scope_data = {
            "type": scope.type,
            "item_ids": sorted(scope.item_ids) if scope.item_ids else None,
            "feed_ids": sorted(scope.feed_ids) if scope.feed_ids else None,
            "article_ids": sorted(scope.article_ids) if scope.article_ids else None,
            "start_time": scope.start_time.isoformat() if scope.start_time else None,
            "end_time": scope.end_time.isoformat() if scope.end_time else None,
            "model_tag": params.model_tag,
            "limit": params.limit
        }

        content = json.dumps(scope_data, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def _determine_priority(self, triggered_by: str) -> RunPriority:
        """Determine priority based on trigger type"""
        if triggered_by == "manual":
            return RunPriority.HIGH
        elif triggered_by == "scheduled":
            return RunPriority.MEDIUM
        elif triggered_by == "auto":
            return RunPriority.LOW
        else:
            return RunPriority.MEDIUM

    async def enqueue_run(
        self,
        scope: RunScope,
        params: RunParams,
        triggered_by: str = "manual"
    ) -> Dict[str, Any]:
        """
        Add a run to the queue.

        Args:
            scope: Analysis scope
            params: Analysis parameters
            triggered_by: Who/what triggered this run

        Returns:
            dict with success status and queue info
        """
        try:
            scope_hash = self._generate_scope_hash(scope, params)
            priority = self._determine_priority(triggered_by)

            with Session(engine) as session:
                # Check for duplicates in queue
                existing = session.exec(
                    select(QueuedRun).where(
                        and_(
                            QueuedRun.scope_hash == scope_hash,
                            QueuedRun.status.in_([RunStatus.QUEUED, RunStatus.RUNNING])
                        )
                    )
                ).first()

                if existing:
                    logger.info(f"Duplicate run detected, scope_hash: {scope_hash}")
                    return {
                        "success": False,
                        "reason": "Duplicate run already in queue",
                        "existing_run_id": existing.id
                    }

                # Calculate queue position
                queue_position = self._calculate_queue_position(session, priority)

                # Create queued run
                queued_run = QueuedRun(
                    priority=priority,
                    status=RunStatus.QUEUED,
                    scope_hash=scope_hash,
                    triggered_by=triggered_by,
                    scope_json=scope.dict(),
                    params_json=params.dict(),
                    queue_position=queue_position
                )

                session.add(queued_run)
                session.commit()
                session.refresh(queued_run)

                logger.info(f"Enqueued run {queued_run.id} with priority {priority}, position {queue_position}")

                return {
                    "success": True,
                    "queued_run_id": queued_run.id,
                    "priority": priority,
                    "queue_position": queue_position,
                    "scope_hash": scope_hash
                }

        except Exception as e:
            logger.error(f"Error enqueuing run: {e}")
            return {
                "success": False,
                "reason": f"Failed to enqueue run: {str(e)}"
            }

    def _calculate_queue_position(self, session: Session, priority: RunPriority) -> int:
        """Calculate the position in queue for a new run"""
        priority_value = self.priority_order[priority]

        # Count runs with higher or equal priority
        higher_priority_count = session.exec(
            select(QueuedRun).where(
                and_(
                    QueuedRun.status == RunStatus.QUEUED,
                    QueuedRun.priority.in_([p for p, v in self.priority_order.items() if v <= priority_value])
                )
            )
        ).all()

        return len(higher_priority_count) + 1

    async def get_next_run(self) -> Optional[QueuedRun]:
        """
        Get the next run from the queue based on priority.

        Returns:
            QueuedRun object or None if queue is empty
        """
        try:
            with Session(engine) as session:
                # Get the highest priority queued run
                next_run = session.exec(
                    select(QueuedRun)
                    .where(QueuedRun.status == RunStatus.QUEUED)
                    .order_by(
                        # Order by priority (HIGH=1, MEDIUM=2, LOW=3)
                        QueuedRun.priority.desc(),
                        # Then by creation time (FIFO within same priority)
                        QueuedRun.created_at.asc()
                    )
                ).first()

                if next_run:
                    # Mark as running
                    next_run.status = RunStatus.RUNNING
                    next_run.started_at = datetime.utcnow()
                    session.add(next_run)
                    session.commit()
                    session.refresh(next_run)

                    logger.info(f"Dequeued run {next_run.id} with priority {next_run.priority}")

                return next_run

        except Exception as e:
            logger.error(f"Error getting next run: {e}")
            return None

    async def mark_run_completed(self, queued_run_id: int, analysis_run_id: Optional[int] = None) -> bool:
        """Mark a queued run as completed"""
        try:
            with Session(engine) as session:
                queued_run = session.get(QueuedRun, queued_run_id)
                if queued_run:
                    queued_run.status = RunStatus.COMPLETED
                    queued_run.completed_at = datetime.utcnow()
                    if analysis_run_id:
                        queued_run.analysis_run_id = analysis_run_id
                    session.add(queued_run)
                    session.commit()
                    logger.info(f"Marked run {queued_run_id} as completed")
                    return True
                return False
        except Exception as e:
            logger.error(f"Error marking run completed: {e}")
            return False

    async def mark_run_failed(self, queued_run_id: int, error_message: str) -> bool:
        """Mark a queued run as failed"""
        try:
            with Session(engine) as session:
                queued_run = session.get(QueuedRun, queued_run_id)
                if queued_run:
                    queued_run.status = RunStatus.FAILED
                    queued_run.completed_at = datetime.utcnow()
                    queued_run.error_message = error_message
                    session.add(queued_run)
                    session.commit()
                    logger.warning(f"Marked run {queued_run_id} as failed: {error_message}")
                    return True
                return False
        except Exception as e:
            logger.error(f"Error marking run failed: {e}")
            return False

    async def cancel_run(self, queued_run_id: int) -> bool:
        """Cancel a queued run"""
        try:
            with Session(engine) as session:
                queued_run = session.get(QueuedRun, queued_run_id)
                if queued_run and queued_run.status == RunStatus.QUEUED:
                    queued_run.status = RunStatus.CANCELLED
                    queued_run.completed_at = datetime.utcnow()
                    session.add(queued_run)
                    session.commit()
                    logger.info(f"Cancelled queued run {queued_run_id}")
                    return True
                return False
        except Exception as e:
            logger.error(f"Error cancelling run: {e}")
            return False

    async def clear_queue(self) -> int:
        """Clear all queued runs (for emergency stop)"""
        try:
            with Session(engine) as session:
                queued_runs = session.exec(
                    select(QueuedRun).where(QueuedRun.status == RunStatus.QUEUED)
                ).all()

                count = len(queued_runs)
                for run in queued_runs:
                    run.status = RunStatus.CANCELLED
                    run.completed_at = datetime.utcnow()
                    session.add(run)

                session.commit()
                logger.info(f"Cleared {count} queued runs")
                return count

        except Exception as e:
            logger.error(f"Error clearing queue: {e}")
            return 0

    def get_queue_status(self) -> Dict[str, Any]:
        """Get current queue status"""
        try:
            with Session(engine) as session:
                # Count by status
                queued_count = len(session.exec(
                    select(QueuedRun).where(QueuedRun.status == RunStatus.QUEUED)
                ).all())

                running_count = len(session.exec(
                    select(QueuedRun).where(QueuedRun.status == RunStatus.RUNNING)
                ).all())

                # Count by priority
                high_priority = len(session.exec(
                    select(QueuedRun).where(
                        and_(
                            QueuedRun.status == RunStatus.QUEUED,
                            QueuedRun.priority == RunPriority.HIGH
                        )
                    )
                ).all())

                medium_priority = len(session.exec(
                    select(QueuedRun).where(
                        and_(
                            QueuedRun.status == RunStatus.QUEUED,
                            QueuedRun.priority == RunPriority.MEDIUM
                        )
                    )
                ).all())

                low_priority = len(session.exec(
                    select(QueuedRun).where(
                        and_(
                            QueuedRun.status == RunStatus.QUEUED,
                            QueuedRun.priority == RunPriority.LOW
                        )
                    )
                ).all())

                return {
                    "total_queued": queued_count,
                    "total_running": running_count,
                    "priority_breakdown": {
                        "high": high_priority,
                        "medium": medium_priority,
                        "low": low_priority
                    }
                }

        except Exception as e:
            logger.error(f"Error getting queue status: {e}")
            return {
                "total_queued": 0,
                "total_running": 0,
                "priority_breakdown": {"high": 0, "medium": 0, "low": 0}
            }

    def get_queue_list(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get list of queued runs"""
        try:
            with Session(engine) as session:
                runs = session.exec(
                    select(QueuedRun)
                    .where(QueuedRun.status.in_([RunStatus.QUEUED, RunStatus.RUNNING]))
                    .order_by(
                        QueuedRun.priority.desc(),
                        QueuedRun.created_at.asc()
                    )
                    .limit(limit)
                ).all()

                return [run.to_dict() for run in runs]

        except Exception as e:
            logger.error(f"Error getting queue list: {e}")
            return []


# Singleton instance
_queue_manager = None


def get_queue_manager() -> RunQueueManager:
    """Get the singleton queue manager instance"""
    global _queue_manager
    if _queue_manager is None:
        _queue_manager = RunQueueManager()
    return _queue_manager