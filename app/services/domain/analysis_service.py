"""Analysis orchestration service with business logic."""

from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
from app.core.logging_config import get_logger

from .base import ServiceResult, NotFoundError, ValidationError, BusinessLogicError
from app.domain.analysis.control import (
    RunScope, RunParams, RunPreview, AnalysisRun, AnalysisPreset,
    SLO_TARGETS
)
from app.repositories.analysis_control import AnalysisControlRepo
from app.services.analysis_run_manager import get_run_manager

logger = get_logger(__name__)


class AnalysisService:
    """Service for analysis orchestration and management operations."""

    def __init__(self):
        # Analysis service uses repository pattern directly
        pass

    def preview_analysis_run(self, scope: RunScope, params: RunParams) -> ServiceResult[RunPreview]:
        """Preview what an analysis run would analyze."""
        try:
            # Validate parameters
            validation_result = self._validate_run_parameters(scope, params)
            if not validation_result.success:
                return validation_result

            preview = AnalysisControlRepo.preview_run(scope, params)

            # Add business logic validation
            if preview.estimated_cost_usd > SLO_TARGETS["max_cost_per_run"]:
                logger.warning(f"Preview shows cost ${preview.estimated_cost_usd:.2f} exceeds SLO limit ${SLO_TARGETS['max_cost_per_run']:.2f}")

            return ServiceResult.ok(preview)

        except Exception as e:
            logger.error(f"Preview failed: {e}")
            return ServiceResult.error(f"Preview failed: {str(e)}")

    async def start_analysis_run(self, scope: RunScope, params: RunParams, triggered_by: str = "manual") -> ServiceResult[AnalysisRun]:
        """Start a new analysis run with validation and orchestration."""
        try:
            # Validate parameters
            validation_result = self._validate_run_parameters(scope, params)
            if not validation_result.success:
                return validation_result

            # Check with RunManager first
            run_manager = get_run_manager()
            can_start = await run_manager.can_start_run(scope, params, triggered_by)
            if not can_start["success"]:
                return ServiceResult.error(can_start["reason"])

            # Get preview for cost validation
            preview = AnalysisControlRepo.preview_run(scope, params)

            # Business logic validation
            if preview.estimated_cost_usd > SLO_TARGETS["max_cost_per_run"]:
                return ServiceResult.error(
                    f"Estimated cost ${preview.estimated_cost_usd:.2f} exceeds limit ${SLO_TARGETS['max_cost_per_run']:.2f}"
                )

            # Create the run (RunManager already checked limits)
            run = AnalysisControlRepo.create_run(scope, params, triggered_by)

            total_items = run.metrics.queued_count if run and run.metrics else preview.item_count
            logger.info(f"Started analysis run {run.id if run else 'unknown'} with {total_items} items, estimated cost ${preview.estimated_cost_usd:.2f}, triggered by: {triggered_by}")

            # Trigger background processing (in a real implementation)
            self._trigger_background_processing(run.id)

            return ServiceResult.ok(run)

        except ValueError as e:
            return ServiceResult.error(str(e))
        except Exception as e:
            logger.error(f"Failed to start analysis run: {e}")
            return ServiceResult.error(f"Failed to start analysis: {str(e)}")

    def get_analysis_run(self, run_id: int) -> ServiceResult[AnalysisRun]:
        """Get analysis run by ID."""
        try:
            run = AnalysisControlRepo.get_run(run_id)
            if not run:
                return ServiceResult.error(f"Analysis run {run_id} not found")

            return ServiceResult.ok(run)
        except Exception as e:
            logger.error(f"Error getting analysis run {run_id}: {e}")
            return ServiceResult.error(f"Database error: {str(e)}")

    def list_analysis_runs(
        self,
        limit: int = 50,
        status_filter: Optional[str] = None,
        days_back: int = 30
    ) -> ServiceResult[List[AnalysisRun]]:
        """List analysis runs with filtering."""
        try:
            runs = AnalysisControlRepo.list_runs(
                limit=limit,
                since=datetime.utcnow() - timedelta(days=days_back)
            )

            # Apply status filter if provided
            if status_filter:
                runs = [run for run in runs if run.status == status_filter]

            return ServiceResult.ok(runs)

        except Exception as e:
            logger.error(f"Error listing analysis runs: {e}")
            return ServiceResult.error(f"Database error: {str(e)}")

    def get_active_runs(self) -> ServiceResult[List[AnalysisRun]]:
        """Get currently active analysis runs."""
        try:
            active_runs = AnalysisControlRepo.get_active_runs()
            return ServiceResult.ok(active_runs)
        except Exception as e:
            logger.error(f"Error getting active runs: {e}")
            return ServiceResult.error(f"Database error: {str(e)}")

    def cancel_analysis_run(self, run_id: int, reason: str = "User cancelled") -> ServiceResult[bool]:
        """Cancel a running analysis."""
        try:
            run = AnalysisControlRepo.get_run(run_id)
            if not run:
                return ServiceResult.error(f"Analysis run {run_id} not found")

            if run.status not in ["running", "pending"]:
                return ServiceResult.error(f"Cannot cancel run with status: {run.status}")

            # Update run status
            success = AnalysisControlRepo.update_run_status(run_id, "cancelled", {"cancellation_reason": reason})

            if success:
                logger.info(f"Cancelled analysis run {run_id}: {reason}")
                return ServiceResult.ok(True)
            else:
                return ServiceResult.error("Failed to cancel run")

        except Exception as e:
            logger.error(f"Error cancelling analysis run {run_id}: {e}")
            return ServiceResult.error(f"Failed to cancel run: {str(e)}")

    def get_analysis_statistics(self, days_back: int = 30) -> ServiceResult[Dict[str, Any]]:
        """Get analysis system statistics."""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_back)
            runs = AnalysisControlRepo.list_runs(limit=1000, since=cutoff_date)

            # Helper function to normalize status values (handle both enum and string)
            def normalize_status(status):
                if hasattr(status, 'value'):
                    return status.value.lower()
                return str(status).lower()

            total_runs = len(runs)
            completed_runs = len([r for r in runs if normalize_status(r.status) == "completed"])
            failed_runs = len([r for r in runs if normalize_status(r.status) == "failed"])
            cancelled_runs = len([r for r in runs if normalize_status(r.status) == "cancelled"])

            total_items_analyzed = sum(r.metrics.processed_count for r in runs if r.metrics)
            total_cost = sum(float(r.metrics.estimated_cost_usd or 0) for r in runs if r.metrics)

            # Calculate average processing time for completed runs
            completed_with_times = [r for r in runs if normalize_status(r.status) == "completed" and r.started_at and r.completed_at]
            avg_processing_time = None
            if completed_with_times:
                total_time = sum((r.completed_at - r.started_at).total_seconds() for r in completed_with_times)
                avg_processing_time = total_time / len(completed_with_times) / 60  # minutes

            stats = {
                "period_days": days_back,
                "total_runs": total_runs,
                "completed_runs": completed_runs,
                "failed_runs": failed_runs,
                "cancelled_runs": cancelled_runs,
                "success_rate": (completed_runs / total_runs * 100) if total_runs > 0 else 0,
                "total_items_analyzed": total_items_analyzed,
                "total_cost_usd": total_cost,
                "avg_cost_per_run": total_cost / total_runs if total_runs > 0 else 0,
                "avg_processing_time_minutes": avg_processing_time,
                "active_runs": len(AnalysisControlRepo.get_active_runs())
            }

            return ServiceResult.ok(stats)

        except Exception as e:
            logger.error(f"Error getting analysis statistics: {e}")
            return ServiceResult.error(f"Database error: {str(e)}")

    def get_available_feeds(self) -> ServiceResult[List[Dict[str, Any]]]:
        """Get feeds available for analysis."""
        try:
            # Use direct database query since AnalysisControlRepo doesn't have get_feeds
            from sqlmodel import Session, text
            from app.database import engine

            with Session(engine) as session:
                results = session.execute(text("""
                    SELECT f.id, f.title, f.url, COUNT(i.id) as item_count
                    FROM feeds f
                    LEFT JOIN items i ON i.feed_id = f.id
                    GROUP BY f.id, f.title, f.url
                    ORDER BY f.title ASC
                """)).fetchall()

                feeds = []
                for row in results:
                    feeds.append({
                        "id": row[0],
                        "title": row[1] or row[2][:50] + "...",
                        "url": row[2],
                        "item_count": row[3]
                    })

                return ServiceResult.ok(feeds)

        except Exception as e:
            logger.error(f"Error getting available feeds: {e}")
            return ServiceResult.error(f"Database error: {str(e)}")

    def create_analysis_preset(
        self,
        name: str,
        scope: RunScope,
        params: RunParams,
        description: Optional[str] = None
    ) -> ServiceResult[AnalysisPreset]:
        """Create a new analysis preset."""
        try:
            # Validate the configuration
            validation_result = self._validate_run_parameters(scope, params)
            if not validation_result.success:
                return validation_result

            preset = AnalysisPreset(
                name=name,
                description=description,
                scope=scope,
                params=params,
                created_at=datetime.utcnow()
            )

            # In a real implementation, this would save to database
            logger.info(f"Created analysis preset: {name}")
            return ServiceResult.ok(preset)

        except Exception as e:
            logger.error(f"Error creating analysis preset: {e}")
            return ServiceResult.error(f"Failed to create preset: {str(e)}")

    def estimate_analysis_cost(self, scope: RunScope, params: RunParams) -> ServiceResult[Dict[str, Any]]:
        """Estimate cost for analysis parameters."""
        try:
            preview = AnalysisControlRepo.preview_run(scope, params)

            cost_breakdown = {
                "items_to_analyze": preview.items_to_analyze,
                "estimated_tokens": preview.items_to_analyze * 500,  # Rough estimate
                "cost_per_1k_tokens": 0.002,  # Example rate
                "estimated_cost_usd": preview.estimated_cost_usd,
                "cost_within_limits": preview.estimated_cost_usd <= SLO_TARGETS["max_cost_per_run"],
                "estimated_duration_minutes": preview.items_to_analyze * 0.5  # Rough estimate
            }

            return ServiceResult.ok(cost_breakdown)

        except Exception as e:
            logger.error(f"Error estimating analysis cost: {e}")
            return ServiceResult.error(f"Cost estimation failed: {str(e)}")

    def _validate_run_parameters(self, scope: RunScope, params: RunParams) -> ServiceResult[bool]:
        """Validate analysis run parameters."""
        try:
            # Validate scope
            if scope.type not in ["all", "feeds", "categories", "timerange", "items", "global", "articles", "filtered"]:
                return ServiceResult.error(f"Invalid scope type: {scope.type}")

            if scope.type == "feeds" and not scope.feed_ids:
                return ServiceResult.error("Feed IDs required for feed scope")

            if scope.type == "categories" and not scope.category_ids:
                return ServiceResult.error("Category IDs required for category scope")

            if scope.type == "items" and not scope.item_ids:
                return ServiceResult.error("Item IDs required for items scope")

            # Validate parameters
            if params.limit < 1 or params.limit > 5000:
                return ServiceResult.error("Limit must be between 1 and 5000")

            if params.rate_per_second <= 0 or params.rate_per_second > 10:
                return ServiceResult.error("Rate per second must be between 0.1 and 10")

            if not params.model_tag:
                return ServiceResult.error("Model tag is required")

            return ServiceResult.ok(True)

        except Exception as e:
            return ServiceResult.error(f"Validation error: {str(e)}")

    def _trigger_background_processing(self, run_id: int) -> None:
        """Trigger background processing for analysis run."""
        try:
            # In a real implementation, this would:
            # 1. Queue the run for background processing
            # 2. Trigger worker processes
            # 3. Set up monitoring and progress tracking

            logger.info(f"Background processing triggered for run {run_id}")

            # For now, just log that processing would be triggered
            # In production, this might use Celery, RQ, or similar task queue

        except Exception as e:
            logger.error(f"Failed to trigger background processing for run {run_id}: {e}")