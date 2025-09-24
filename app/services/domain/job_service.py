from typing import Dict, Optional
from datetime import datetime, timedelta
import asyncio

from app.domain.analysis.jobs import PreviewJob, JobResult, JobStatus
from app.domain.analysis.control import RunPreview
from app.repositories.analysis_control import AnalysisControlRepo
from app.core.logging_config import get_logger
from app.services.domain.base import ServiceResult

logger = get_logger(__name__)

class JobService:
    """Service for managing preview jobs and calculations"""

    def __init__(self):
        self._job_store: Dict[str, PreviewJob] = {}  # In-memory store for preview jobs

    def create_preview_job(self, job_config: PreviewJob) -> ServiceResult[JobResult]:
        """Create a new preview job and calculate estimates"""
        try:
            # Store job in memory for later retrieval
            job_config.status = "preview"
            job_config.created_at = datetime.utcnow()

            # Calculate estimates using existing repository
            scope = job_config.to_run_scope()
            params = job_config.to_run_params()

            logger.info(f"Creating preview job {job_config.job_id} with scope: {scope.type}, params: limit={params.limit}")

            # Get preview from existing repository
            preview = AnalysisControlRepo.preview_run(scope, params)
            job_config.estimates = preview

            # Store job
            self._job_store[job_config.job_id] = job_config

            # Clean up old jobs (keep last 100)
            self._cleanup_old_jobs()

            result = JobResult(
                success=True,
                job_id=job_config.job_id,
                estimates=preview,
                message=f"Preview job created: {job_config.get_description()}"
            )

            logger.info(f"Preview job {job_config.job_id} created successfully: {preview.item_count} items, ${preview.estimated_cost_usd:.4f}")
            return ServiceResult.success(result)

        except Exception as e:
            logger.error(f"Failed to create preview job: {e}")
            return ServiceResult.error(f"Failed to create preview job: {str(e)}")

    def get_job(self, job_id: str) -> Optional[PreviewJob]:
        """Retrieve a job by ID"""
        return self._job_store.get(job_id)

    def update_job_status(self, job_id: str, status: JobStatus, run_id: Optional[int] = None) -> ServiceResult[bool]:
        """Update job status (e.g., when it becomes a run)"""
        try:
            job = self._job_store.get(job_id)
            if not job:
                return ServiceResult.error(f"Job {job_id} not found")

            job.status = status
            if run_id:
                job.run_id = run_id

            logger.info(f"Updated job {job_id} status to {status}" + (f" with run_id {run_id}" if run_id else ""))
            return ServiceResult.success(True)

        except Exception as e:
            logger.error(f"Failed to update job {job_id} status: {e}")
            return ServiceResult.error(f"Failed to update job status: {str(e)}")

    def refresh_job_estimates(self, job_id: str) -> ServiceResult[JobResult]:
        """Recalculate estimates for an existing job"""
        try:
            job = self._job_store.get(job_id)
            if not job:
                return ServiceResult.error(f"Job {job_id} not found")

            # Recalculate with current data
            scope = job.to_run_scope()
            params = job.to_run_params()

            preview = AnalysisControlRepo.preview_run(scope, params)
            job.estimates = preview

            result = JobResult(
                success=True,
                job_id=job_id,
                estimates=preview,
                message="Estimates refreshed"
            )

            logger.info(f"Refreshed estimates for job {job_id}: {preview.item_count} items")
            return ServiceResult.success(result)

        except Exception as e:
            logger.error(f"Failed to refresh job {job_id} estimates: {e}")
            return ServiceResult.error(f"Failed to refresh estimates: {str(e)}")

    def list_active_jobs(self) -> ServiceResult[Dict[str, PreviewJob]]:
        """List all active preview jobs"""
        try:
            # Filter jobs created in last hour
            cutoff = datetime.utcnow() - timedelta(hours=1)
            active_jobs = {
                job_id: job for job_id, job in self._job_store.items()
                if job.created_at > cutoff and job.status == "preview"
            }

            return ServiceResult.success(active_jobs)

        except Exception as e:
            logger.error(f"Failed to list active jobs: {e}")
            return ServiceResult.error(f"Failed to list jobs: {str(e)}")

    def _cleanup_old_jobs(self):
        """Remove old jobs to prevent memory leaks"""
        try:
            # Keep only last 100 jobs and jobs from last 24 hours
            cutoff = datetime.utcnow() - timedelta(hours=24)

            # Sort by creation time, newest first
            jobs_by_time = sorted(
                self._job_store.items(),
                key=lambda x: x[1].created_at,
                reverse=True
            )

            # Keep newest 100 or jobs newer than cutoff
            jobs_to_keep = {}
            for job_id, job in jobs_by_time[:100]:
                if job.created_at > cutoff or len(jobs_to_keep) < 50:
                    jobs_to_keep[job_id] = job

            removed_count = len(self._job_store) - len(jobs_to_keep)
            if removed_count > 0:
                self._job_store = jobs_to_keep
                logger.debug(f"Cleaned up {removed_count} old preview jobs")

        except Exception as e:
            logger.error(f"Failed to cleanup old jobs: {e}")

# Global service instance
_job_service = None

def get_job_service() -> JobService:
    """Get the global job service instance"""
    global _job_service
    if _job_service is None:
        _job_service = JobService()
    return _job_service