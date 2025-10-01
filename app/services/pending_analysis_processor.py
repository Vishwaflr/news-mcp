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
from app.services.auto_analysis_config import auto_analysis_config
from app.services.queue_limiter import get_queue_limiter
from app.services.adaptive_rate_limiter import get_rate_limiter
from app.services.prometheus_metrics import get_metrics

logger = get_logger(__name__)


class PendingAnalysisProcessor:
    """Processes pending auto-analysis jobs from the queue"""

    def __init__(self):
        # Load from centralized config
        self.max_daily_auto_runs_per_feed = auto_analysis_config.max_daily_runs
        self.max_age_hours = 24
        # NEW: Increased batch size for efficient processing with skip logic
        self.batch_size = auto_analysis_config.max_items_per_run

        # SPRINT 1 DAY 2: Backpressure controls
        self.queue_limiter = get_queue_limiter(max_concurrent=50)
        self.rate_limiter = get_rate_limiter(rate_per_second=3.0)

        # SPRINT 1 DAY 3: Prometheus metrics
        self.metrics = get_metrics()

    async def process_pending_queue(self) -> int:
        """
        Process pending auto-analysis jobs in batches.

        IMPROVED: Now includes backpressure controls to prevent overload.

        Returns:
            Number of jobs processed
        """
        processed_count = 0

        # SPRINT 1 DAY 2: Check queue availability before processing
        if not self.queue_limiter.is_available():
            logger.warning(
                f"Queue limiter at capacity "
                f"({self.queue_limiter.get_metrics()['active_count']}/{self.queue_limiter.max_concurrent}), "
                f"deferring processing"
            )
            return 0

        try:
            # SPRINT 1 DAY 3: Update queue metrics
            queue_metrics = self.queue_limiter.get_metrics()
            self.metrics.update_queue_metrics(
                depth=queue_metrics['active_count'],
                active=queue_metrics['active_count'],
                utilization=queue_metrics['utilization_pct']
            )

            with Session(engine) as session:
                # Get pending jobs, limited to batch size
                pending_jobs = session.exec(
                    select(PendingAutoAnalysis).where(
                        PendingAutoAnalysis.status == "pending"
                    ).order_by(
                        PendingAutoAnalysis.created_at
                    ).limit(self.batch_size)  # NEW: Process in batches
                ).all()

                if not pending_jobs:
                    return 0

                logger.info(f"Processing batch of {len(pending_jobs)} pending auto-analysis jobs")

                # SPRINT 1 DAY 3: Record batch size
                self.metrics.batch_size.observe(len(pending_jobs))

                # Group jobs by feed for better batching
                jobs_by_feed = {}
                for job in pending_jobs:
                    if job.feed_id not in jobs_by_feed:
                        jobs_by_feed[job.feed_id] = []
                    jobs_by_feed[job.feed_id].append(job)

                # Process each feed's batch
                for feed_id, feed_jobs in jobs_by_feed.items():
                    try:
                        items_processed = await self._process_feed_batch(feed_id, feed_jobs)
                        processed_count += items_processed
                    except Exception as e:
                        logger.error(f"Error processing batch for feed {feed_id}: {e}")
                        for job in feed_jobs:
                            self._mark_job_failed(job.id, str(e))

        except Exception as e:
            logger.error(f"Error in process_pending_queue: {e}")

        return processed_count

    async def _process_feed_batch(self, feed_id: int, jobs: list[PendingAutoAnalysis]) -> int:
        """
        Process a batch of jobs for a single feed.

        This creates a single analysis run for all items, leveraging
        the skip logic in the worker to avoid duplicate analysis.

        Args:
            feed_id: Feed ID
            jobs: List of pending jobs for this feed

        Returns:
            Number of items successfully queued for analysis
        """
        with Session(engine) as session:
            # Check feed status
            feed = session.get(Feed, feed_id)
            if not feed or not feed.auto_analyze_enabled:
                logger.info(f"Feed {feed_id} not found or auto-analysis disabled")
                for job in jobs:
                    self._mark_job_failed(job.id, "Feed disabled or not found")
                return 0

            # Check daily limits once for the batch
            if not self._check_daily_limits(session, feed_id):
                logger.warning(f"Daily limit exceeded for feed {feed_id}")
                for job in jobs:
                    self._mark_job_failed(job.id, "Daily limit exceeded")
                return 0

            # Collect all item IDs from all jobs
            all_item_ids = []
            job_item_map = {}  # Track which items belong to which job

            for job in jobs:
                if not self._is_too_old(job):
                    for item_id in job.item_ids:
                        all_item_ids.append(item_id)
                        if item_id not in job_item_map:
                            job_item_map[item_id] = []
                        job_item_map[item_id].append(job.id)
                else:
                    self._mark_job_failed(job.id, "Job expired")

            if not all_item_ids:
                logger.info(f"No valid items for feed {feed_id} batch")
                return 0

            # Validate and deduplicate items
            valid_items = list(set(self._validate_items(session, all_item_ids)))

            logger.info(f"Processing batch: {len(valid_items)} unique items from {len(jobs)} jobs for feed {feed_id}")

            try:
                # Create a single analysis run for all items
                scope = RunScope(type="items", item_ids=valid_items)
                params = RunParams(
                    limit=len(valid_items),
                    rate_per_second=auto_analysis_config.rate_per_second,  # From config
                    model_tag=auto_analysis_config.ai_model,  # From config
                    triggered_by="auto"
                )

                analysis_service = get_analysis_service()
                result = await analysis_service.start_analysis_run(scope, params, "auto")

                if result.success:
                    run_data = result.data
                    # Mark all jobs as completed
                    for job in jobs:
                        self._mark_job_completed(job.id, run_data.id)

                    logger.info(f"Batch completed: Created run {run_data.id} with {len(valid_items)} items (will skip already analyzed)")
                    return len(valid_items)
                else:
                    logger.error(f"Failed to start batch analysis for feed {feed_id}: {result.error}")
                    for job in jobs:
                        self._mark_job_failed(job.id, result.error)
                    return 0

            except Exception as e:
                logger.error(f"Error in batch processing for feed {feed_id}: {e}")
                for job in jobs:
                    self._mark_job_failed(job.id, str(e))
                return 0

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
        """
        Validate that items exist and filter out already analyzed items.

        IMPROVED: Now checks item_analysis table to skip already analyzed items,
        preventing duplicate analysis and saving API costs.
        """
        from app.models import ItemAnalysis

        valid_ids = []
        for item_id in item_ids:
            # Check if item exists
            item = session.get(Item, item_id)
            if not item:
                continue

            # IMPROVED: Check if already analyzed (idempotency)
            # item_analysis.item_id is PRIMARY KEY, so we query directly
            existing_analysis = session.exec(
                select(ItemAnalysis).where(ItemAnalysis.item_id == item_id)
            ).first()

            if existing_analysis:
                logger.debug(f"Item {item_id} already analyzed, skipping")
                continue

            valid_ids.append(item_id)

        logger.info(f"Filtered {len(item_ids)} items → {len(valid_ids)} valid unanalyzed items")
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

                    # SPRINT 1 DAY 3: Record metrics
                    for item_id in job.item_ids:
                        self.metrics.record_item_processed("completed", "auto")
        except Exception as e:
            logger.error(f"Error marking job {job_id} as completed: {e}")
            self.metrics.record_error("mark_completed_failed", "pending_processor")

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

                    # SPRINT 1 DAY 3: Record metrics
                    for item_id in job.item_ids:
                        self.metrics.record_item_processed("failed", "auto")
                    self.metrics.record_error("job_failed", "pending_processor")
        except Exception as e:
            logger.error(f"Error marking job {job_id} as failed: {e}")
            self.metrics.record_error("mark_failed_failed", "pending_processor")

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

    def get_backpressure_metrics(self) -> dict:
        """
        Get backpressure control metrics.

        SPRINT 1 DAY 2: New method for monitoring backpressure.

        Returns:
            Combined metrics from queue limiter and rate limiter
        """
        return {
            "queue_limiter": self.queue_limiter.get_metrics(),
            "rate_limiter": self.rate_limiter.get_metrics()
        }