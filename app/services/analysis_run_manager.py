"""
Analysis Run Manager

Manages concurrent analysis runs, prevents resource exhaustion,
and enforces limits for sustainable operation.
"""

from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from enum import Enum
import asyncio
from app.core.logging_config import get_logger
from app.repositories.analysis_control import AnalysisControlRepo
from app.domain.analysis.control import AnalysisRun, RunScope, RunParams, RunStatus
from app.services.run_queue_manager import get_queue_manager, RunPriority

logger = get_logger(__name__)

class AnalysisRunManager:
    """
    Manages analysis runs with resource limits and queuing.

    Prevents system overload by:
    - Limiting concurrent runs
    - Enforcing daily limits
    - Managing run priorities
    - Preventing duplicate runs
    """

    def __init__(self):
        # Configuration - these should be moved to database config later
        self.max_concurrent_runs = 2
        self.max_daily_runs = 100
        self.max_daily_auto_runs = 50
        self.max_hourly_runs = 10

        # Emergency brake
        self.emergency_stop = False

        # Queue manager
        self.queue_manager = get_queue_manager()
        self._lock = asyncio.Lock()

    async def can_start_run(self, scope: RunScope, params: RunParams, triggered_by: str = "manual") -> Dict[str, Any]:
        """
        Check if a new run can be started.

        Returns:
            dict with success: bool and reason: str if failed
        """
        async with self._lock:
            try:
                # Emergency stop check
                if self.emergency_stop:
                    return {"success": False, "reason": "Emergency stop activated"}

                # Check for duplicate runs
                if self._is_duplicate_run(scope):
                    return {"success": False, "reason": "Duplicate run detected (same scope already running)"}

                # Check concurrent runs limit
                active_runs = AnalysisControlRepo.get_active_runs()
                if len(active_runs) >= self.max_concurrent_runs:
                    # At capacity - queue high priority runs, reject others
                    from app.services.run_queue_manager import RunPriority
                    priority = self._determine_priority(triggered_by)
                    if priority == RunPriority.HIGH:
                        # Queue manual runs
                        queue_result = await self.queue_manager.enqueue_run(scope, params, triggered_by)
                        if queue_result["success"]:
                            return {"success": False, "reason": f"Queued due to capacity limit", "queued_run_id": queue_result["queued_run_id"]}
                        else:
                            return {"success": False, "reason": f"Failed to queue run: {queue_result['reason']}"}
                    else:
                        return {"success": False, "reason": f"Too many concurrent runs ({len(active_runs)}/{self.max_concurrent_runs}). Auto/scheduled runs rejected."}

                # Check daily limits
                daily_check = self._check_daily_limits(triggered_by)
                if not daily_check["success"]:
                    return daily_check

                # Check hourly limits
                hourly_check = self._check_hourly_limits()
                if not hourly_check["success"]:
                    return hourly_check

                return {"success": True, "reason": "Run can proceed"}

            except Exception as e:
                logger.error(f"Error checking run eligibility: {e}")
                return {"success": False, "reason": f"System error: {str(e)}"}

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

    def _is_duplicate_run(self, scope: RunScope) -> bool:
        """Check if there's already an active run with the same scope"""
        try:
            scope_hash = self._calculate_scope_hash(scope)
            active_runs = AnalysisControlRepo.get_active_runs()

            for run in active_runs:
                if run.scope_hash == scope_hash:
                    logger.warning(f"Duplicate run detected with scope_hash: {scope_hash}")
                    return True
            return False
        except Exception as e:
            logger.error(f"Error checking duplicate runs: {e}")
            return False

    def _calculate_scope_hash(self, scope: RunScope) -> str:
        """Calculate a hash for the scope to detect duplicates"""
        import hashlib
        import json

        # Create a deterministic string representation of the scope
        scope_dict = scope.dict() if hasattr(scope, 'dict') else scope.__dict__
        scope_str = json.dumps(scope_dict, sort_keys=True)
        return hashlib.sha256(scope_str.encode()).hexdigest()[:16]

    def _get_priority(self, triggered_by: str) -> RunPriority:
        """Get priority based on trigger type"""
        if triggered_by == "manual":
            return RunPriority.HIGH
        elif triggered_by == "scheduled":
            return RunPriority.MEDIUM
        else:  # auto
            return RunPriority.LOW

    def _check_daily_limits(self, triggered_by: str) -> Dict[str, Any]:
        """Check daily run limits"""
        try:
            today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

            # Get runs from today
            runs_today = AnalysisControlRepo.list_runs(limit=200, since=today_start)

            total_runs_today = len(runs_today)
            auto_runs_today = len([r for r in runs_today if r.triggered_by == "auto"])

            # Check total daily limit
            if total_runs_today >= self.max_daily_runs:
                return {"success": False, "reason": f"Daily run limit exceeded ({total_runs_today}/{self.max_daily_runs})"}

            # Check auto run daily limit
            if triggered_by == "auto" and auto_runs_today >= self.max_daily_auto_runs:
                return {"success": False, "reason": f"Daily auto-run limit exceeded ({auto_runs_today}/{self.max_daily_auto_runs})"}

            return {"success": True, "counts": {"total": total_runs_today, "auto": auto_runs_today}}

        except Exception as e:
            logger.error(f"Error checking daily limits: {e}")
            return {"success": False, "reason": f"Error checking daily limits: {str(e)}"}

    def _check_hourly_limits(self) -> Dict[str, Any]:
        """Check hourly run limits"""
        try:
            hour_ago = datetime.now() - timedelta(hours=1)
            runs_last_hour = AnalysisControlRepo.list_runs(limit=50, since=hour_ago)

            if len(runs_last_hour) >= self.max_hourly_runs:
                return {"success": False, "reason": f"Hourly run limit exceeded ({len(runs_last_hour)}/{self.max_hourly_runs})"}

            return {"success": True, "count": len(runs_last_hour)}

        except Exception as e:
            logger.error(f"Error checking hourly limits: {e}")
            return {"success": False, "reason": f"Error checking hourly limits: {str(e)}"}

    async def emergency_stop_all(self, reason: str = "Manual emergency stop"):
        """Emergency stop - halt all analysis processing"""
        async with self._lock:
            self.emergency_stop = True
            logger.critical(f"EMERGENCY STOP ACTIVATED: {reason}")

            # Cancel all queued runs
            self._run_queue.clear()

            # TODO: Signal running processes to stop gracefully
            # This would require worker integration

            return {"success": True, "message": f"Emergency stop activated: {reason}"}

    async def resume_operations(self):
        """Resume operations after emergency stop"""
        async with self._lock:
            self.emergency_stop = False
            logger.info("Operations resumed after emergency stop")
            return {"success": True, "message": "Operations resumed"}

    def get_status(self) -> Dict[str, Any]:
        """Get current manager status"""
        try:
            active_runs = AnalysisControlRepo.get_active_runs()

            # Get daily stats
            today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            runs_today = AnalysisControlRepo.list_runs(limit=200, since=today_start)

            # Get hourly stats
            hour_ago = datetime.now() - timedelta(hours=1)
            runs_last_hour = AnalysisControlRepo.list_runs(limit=50, since=hour_ago)

            auto_runs_today = len([r for r in runs_today if r.triggered_by == "auto"])

            # Get queue status
            queue_status = self.queue_manager.get_queue_status()

            return {
                "emergency_stop": self.emergency_stop,
                "active_runs": len(active_runs),
                "max_concurrent": self.max_concurrent_runs,
                "queued_runs": queue_status["total_queued"],
                "queue_breakdown": queue_status["priority_breakdown"],
                "daily_stats": {
                    "total_runs": len(runs_today),
                    "auto_runs": auto_runs_today,
                    "limit_total": self.max_daily_runs,
                    "limit_auto": self.max_daily_auto_runs
                },
                "hourly_stats": {
                    "runs_last_hour": len(runs_last_hour),
                    "limit": self.max_hourly_runs
                },
                "limits": {
                    "at_concurrent_limit": len(active_runs) >= self.max_concurrent_runs,
                    "at_daily_limit": len(runs_today) >= self.max_daily_runs,
                    "at_hourly_limit": len(runs_last_hour) >= self.max_hourly_runs
                }
            }

        except Exception as e:
            logger.error(f"Error getting manager status: {e}")
            return {"error": f"Error getting status: {str(e)}"}

    async def process_queue(self) -> Optional[Dict[str, Any]]:
        """
        Process the next item in the queue if we have capacity.

        Returns:
            dict with run info if started, None if no capacity or empty queue
        """
        async with self._lock:
            try:
                # Check if we have capacity
                active_runs = AnalysisControlRepo.get_active_runs()
                if len(active_runs) >= self.max_concurrent_runs:
                    logger.debug("No capacity to process queue")
                    return None

                if self.emergency_stop:
                    logger.debug("Emergency stop active, not processing queue")
                    return None

                # Get next run from queue
                next_run = await self.queue_manager.get_next_run()
                if not next_run:
                    logger.debug("Queue is empty")
                    return None

                # Reconstruct scope and params from queue entry
                from app.domain.analysis.control import RunScope, RunParams
                scope = RunScope(**next_run.scope_json)
                params = RunParams(**next_run.params_json)

                logger.info(f"Processing queued run {next_run.id} with priority {next_run.priority}")

                return {
                    "queued_run_id": next_run.id,
                    "scope": scope,
                    "params": params,
                    "triggered_by": next_run.triggered_by,
                    "priority": next_run.priority
                }

            except Exception as e:
                logger.error(f"Error processing queue: {e}")
                return None

    async def emergency_stop_all(self, reason: str = "Emergency stop activated") -> Dict[str, Any]:
        """Emergency stop all analysis processing"""
        async with self._lock:
            try:
                self.emergency_stop = True

                # Clear the queue
                cleared_count = await self.queue_manager.clear_queue()

                logger.critical(f"Emergency stop activated: {reason}. Cleared {cleared_count} queued runs.")

                return {
                    "success": True,
                    "message": f"Emergency stop activated. Cleared {cleared_count} queued runs.",
                    "cleared_runs": cleared_count
                }

            except Exception as e:
                logger.error(f"Error during emergency stop: {e}")
                return {
                    "success": False,
                    "message": f"Error during emergency stop: {str(e)}"
                }

    async def resume_operations(self) -> Dict[str, Any]:
        """Resume operations after emergency stop"""
        async with self._lock:
            try:
                self.emergency_stop = False
                logger.info("Operations resumed")

                return {
                    "success": True,
                    "message": "Operations resumed"
                }

            except Exception as e:
                logger.error(f"Error resuming operations: {e}")
                return {
                    "success": False,
                    "message": f"Error resuming operations: {str(e)}"
                }

    def get_queue_status(self) -> Dict[str, Any]:
        """Get current queue status"""
        return self.queue_manager.get_queue_status()

    def get_queue_list(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get list of queued runs"""
        return self.queue_manager.get_queue_list(limit)


# Singleton instance
_run_manager = None

def get_run_manager() -> AnalysisRunManager:
    """Get the singleton run manager instance"""
    global _run_manager
    if _run_manager is None:
        _run_manager = AnalysisRunManager()
    return _run_manager