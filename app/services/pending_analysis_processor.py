"""
Pending Analysis Processor

Processes pending auto-analysis jobs from the queue.
This service runs as part of the analysis worker and picks up
jobs queued by the feed fetcher.
"""

from app.core.logging_config import get_logger
from datetime import datetime, timedelta
from typing import Optional
from sqlmodel import Session, select

from app.database import engine
from app.models import PendingAutoAnalysis, Feed, Item
from app.domain.analysis.control import RunScope, RunParams
from app.services.domain.analysis_service import AnalysisService
from app.dependencies import get_analysis_service

logger = get_logger(__name__)


class PendingAnalysisProcessor:
    """Processes pending auto-analysis jobs from the queue"""

    def __init__(self):
        self.max_daily_auto_runs_per_feed = 10
        self.max_age_hours = 24

    async def process_pending_queue(self) -> int:
        """
        Process all pending auto-analysis jobs.

        Returns:
            Number of jobs processed
        """
        processed_count = 0

        try:
            with Session(engine) as session:
                pending_jobs = session.exec(
                    select(PendingAutoAnalysis).where(
                        PendingAutoAnalysis.status == "pending"
                    ).order_by(PendingAutoAnalysis.created_at)
                ).all()

                logger.info(f"Found {len(pending_jobs)} pending auto-analysis jobs")

                for job in pending_jobs:
                    try:
                        if await self._process_job(job):
                            processed_count += 1
                    except Exception as e:
                        logger.error(f"Error processing job {job.id}: {e}")
                        self._mark_job_failed(job.id, str(e))

        except Exception as e:
            logger.error(f"Error in process_pending_queue: {e}")

        return processed_count

    async def _process_job(self, job: PendingAutoAnalysis) -> bool:
        """
        Process a single pending auto-analysis job.

        Args:
            job: The pending job to process

        Returns:
            True if job was processed successfully, False otherwise
        """
        with Session(engine) as session:
            feed = session.get(Feed, job.feed_id)
            if not feed:
                logger.warning(f"Feed {job.feed_id} not found for job {job.id}")
                self._mark_job_failed(job.id, "Feed not found")
                return False

            if not feed.auto_analyze_enabled:
                logger.info(f"Auto-analysis disabled for feed {job.feed_id}, skipping job {job.id}")
                self._mark_job_failed(job.id, "Auto-analysis disabled")
                return False

            if self._is_too_old(job):
                logger.warning(f"Job {job.id} is too old (created {job.created_at}), skipping")
                self._mark_job_failed(job.id, "Job expired")
                return False

            if not self._check_daily_limits(session, job.feed_id):
                logger.warning(f"Daily limit exceeded for feed {job.feed_id}, skipping job {job.id}")
                self._mark_job_failed(job.id, "Daily limit exceeded")
                return False

            valid_items = self._validate_items(session, job.item_ids)
            if not valid_items:
                logger.warning(f"No valid items for job {job.id}")
                self._mark_job_failed(job.id, "No valid items")
                return False

            try:
                scope = RunScope(type="items", item_ids=valid_items)
                params = RunParams(
                    limit=len(valid_items),
                    rate_per_second=1.0,
                    model_tag="gpt-4.1-nano",
                    triggered_by="auto"
                )

                analysis_service = get_analysis_service()
                result = await analysis_service.start_analysis_run(scope, params, "auto")

                if result.success:
                    run_data = result.data
                    self._mark_job_completed(job.id, run_data.id)
                    logger.info(f"Job {job.id} completed successfully, created run {run_data.id}")
                    return True
                else:
                    logger.error(f"Failed to start analysis for job {job.id}: {result.error}")
                    self._mark_job_failed(job.id, result.error)
                    return False

            except Exception as e:
                logger.error(f"Error starting analysis for job {job.id}: {e}")
                self._mark_job_failed(job.id, str(e))
                return False

    def _is_too_old(self, job: PendingAutoAnalysis) -> bool:
        """Check if job is too old to process"""
        age = datetime.utcnow() - job.created_at
        return age > timedelta(hours=self.max_age_hours)

    def _validate_items(self, session: Session, item_ids: list[int]) -> list[int]:
        """Validate that items exist and return valid IDs"""
        valid_ids = []
        for item_id in item_ids:
            item = session.get(Item, item_id)
            if item:
                valid_ids.append(item_id)
        return valid_ids

    def _check_daily_limits(self, session: Session, feed_id: int) -> bool:
        """
        Check if feed is within daily auto-analysis limits.

        Uses completed pending_auto_analysis jobs to count daily runs per feed.

        Args:
            session: Database session
            feed_id: Feed ID to check

        Returns:
            True if within limits, False otherwise
        """
        try:
            yesterday = datetime.utcnow() - timedelta(days=1)

            completed_jobs_today = session.exec(
                select(PendingAutoAnalysis).where(
                    PendingAutoAnalysis.feed_id == feed_id,
                    PendingAutoAnalysis.status == "completed",
                    PendingAutoAnalysis.processed_at >= yesterday
                )
            ).all()

            runs_count = len(completed_jobs_today)
            logger.debug(f"Feed {feed_id} has {runs_count} completed auto-analysis runs in last 24h (limit: {self.max_daily_auto_runs_per_feed})")

            return runs_count < self.max_daily_auto_runs_per_feed

        except Exception as e:
            logger.error(f"Error checking daily limits for feed {feed_id}: {e}")
            return False

    def _mark_job_completed(self, job_id: int, analysis_run_id: int):
        """Mark job as completed"""
        try:
            with Session(engine) as session:
                job = session.get(PendingAutoAnalysis, job_id)
                if job:
                    job.status = "completed"
                    job.processed_at = datetime.utcnow()
                    job.analysis_run_id = analysis_run_id
                    session.commit()
        except Exception as e:
            logger.error(f"Error marking job {job_id} as completed: {e}")

    def _mark_job_failed(self, job_id: int, error_message: str):
        """Mark job as failed"""
        try:
            with Session(engine) as session:
                job = session.get(PendingAutoAnalysis, job_id)
                if job:
                    job.status = "failed"
                    job.processed_at = datetime.utcnow()
                    job.error_message = error_message[:500]
                    session.commit()
        except Exception as e:
            logger.error(f"Error marking job {job_id} as failed: {e}")

    def cleanup_old_jobs(self, days: int = 7):
        """
        Clean up old completed/failed jobs.

        Args:
            days: Number of days to keep jobs
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)

            with Session(engine) as session:
                old_jobs = session.exec(
                    select(PendingAutoAnalysis).where(
                        PendingAutoAnalysis.created_at < cutoff_date,
                        PendingAutoAnalysis.status.in_(["completed", "failed"])
                    )
                ).all()

                count = len(old_jobs)
                for job in old_jobs:
                    session.delete(job)

                session.commit()
                logger.info(f"Cleaned up {count} old auto-analysis jobs")

        except Exception as e:
            logger.error(f"Error cleaning up old jobs: {e}")

    def get_queue_stats(self) -> dict:
        """Get statistics about the pending queue"""
        try:
            with Session(engine) as session:
                pending_count = session.exec(
                    select(PendingAutoAnalysis).where(
                        PendingAutoAnalysis.status == "pending"
                    )
                ).all()

                completed_today = session.exec(
                    select(PendingAutoAnalysis).where(
                        PendingAutoAnalysis.status == "completed",
                        PendingAutoAnalysis.processed_at >= datetime.utcnow() - timedelta(days=1)
                    )
                ).all()

                failed_today = session.exec(
                    select(PendingAutoAnalysis).where(
                        PendingAutoAnalysis.status == "failed",
                        PendingAutoAnalysis.processed_at >= datetime.utcnow() - timedelta(days=1)
                    )
                ).all()

                return {
                    "pending": len(pending_count),
                    "completed_today": len(completed_today),
                    "failed_today": len(failed_today),
                    "oldest_pending": min([j.created_at for j in pending_count]) if pending_count else None
                }

        except Exception as e:
            logger.error(f"Error getting queue stats: {e}")
            return {"error": str(e)}