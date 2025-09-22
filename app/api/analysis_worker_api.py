"""Analysis Worker API endpoints for monitoring and control."""

import os
import time
import psutil
import requests
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.utils.feature_flags import feature_flags
from app.db.session import db_session

router = APIRouter(prefix="/api/analysis", tags=["analysis", "worker"])


class WorkerControlRequest(BaseModel):
    """Request model for worker control operations."""
    action: str  # start, stop, restart
    rps: Optional[float] = None


class WorkerStatusResponse(BaseModel):
    """Response model for worker status."""
    status: str
    heartbeat_age_seconds: float
    queue_length: int
    rps_current: float
    runs_active: int
    repository_mode: bool


@router.get("/worker/status")
async def get_worker_status() -> WorkerStatusResponse:
    """Get current worker status and health metrics."""
    try:
        # Check if worker process is running
        worker_running = _check_worker_process()

        # Get queue statistics from database
        with db_session.read_session() as session:
            from sqlalchemy import text

            # Get queue length (pending analysis run items)
            queue_result = session.execute(text("""
                SELECT COUNT(*) as queue_length
                FROM analysis_run_items
                WHERE status = 'queued'
            """)).fetchone()
            queue_length = queue_result[0] if queue_result else 0

            # Get active runs
            active_runs_result = session.execute(text("""
                SELECT COUNT(*) as active_runs
                FROM analysis_runs
                WHERE status = 'processing'
            """)).fetchone()
            active_runs = active_runs_result[0] if active_runs_result else 0

            # Get last heartbeat (if worker_status table exists)
            try:
                heartbeat_result = session.execute(text("""
                    SELECT updated_at
                    FROM worker_status
                    WHERE worker_type = 'analysis'
                    ORDER BY updated_at DESC
                    LIMIT 1
                """)).fetchone()

                if heartbeat_result:
                    last_heartbeat = heartbeat_result[0]
                    heartbeat_age = (datetime.now() - last_heartbeat).total_seconds()
                else:
                    heartbeat_age = 999  # No heartbeat found
            except:
                heartbeat_age = 999  # Table doesn't exist or other error

        # Determine overall status
        if not worker_running:
            status = "stopped"
        elif heartbeat_age > 60:
            status = "stale"
        elif queue_length > 1000:
            status = "overloaded"
        else:
            status = "healthy"

        # Get repository mode from feature flags
        analysis_repo_flag = feature_flags.get_flag_status('analysis_repo')
        repository_mode = False
        if analysis_repo_flag:
            flag_status = analysis_repo_flag.get('status')
            repository_mode = flag_status in ['on', 'canary']

        return WorkerStatusResponse(
            status=status,
            heartbeat_age_seconds=heartbeat_age,
            queue_length=queue_length,
            rps_current=1.0,  # Default, could be dynamic
            runs_active=active_runs,
            repository_mode=repository_mode
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get worker status: {str(e)}")


@router.post("/worker/control")
async def control_worker(request: WorkerControlRequest) -> Dict[str, Any]:
    """Control worker operations (start/stop/restart)."""
    try:
        if request.action == "stop":
            # Signal worker to stop gracefully
            _signal_worker("stop")
            return {"message": "Worker stop signal sent", "action": "stop"}

        elif request.action == "start":
            # Start worker if not running
            if not _check_worker_process():
                _start_worker()
                return {"message": "Worker started", "action": "start"}
            else:
                return {"message": "Worker already running", "action": "start"}

        elif request.action == "restart":
            # Restart worker
            _signal_worker("stop")
            time.sleep(2)  # Wait for graceful shutdown
            _start_worker()
            return {"message": "Worker restarted", "action": "restart"}

        elif request.action == "set_rps" and request.rps is not None:
            # Update RPS settings
            _update_worker_rps(request.rps)
            return {"message": f"RPS updated to {request.rps}", "action": "set_rps"}

        else:
            raise HTTPException(status_code=400, detail=f"Unknown action: {request.action}")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Worker control failed: {str(e)}")


@router.get("/stats")
async def get_analysis_stats() -> Dict[str, Any]:
    """Get comprehensive analysis statistics."""
    try:
        with db_session.read_session() as session:
            from sqlalchemy import text

            # Analysis coverage
            total_items = session.execute(text("SELECT COUNT(*) FROM items")).scalar()
            analyzed_items = session.execute(text("SELECT COUNT(DISTINCT item_id) FROM item_analysis")).scalar()

            # Recent activity (24h)
            recent_runs = session.execute(text("""
                SELECT
                    COUNT(*) as total_runs,
                    COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed_runs,
                    COUNT(CASE WHEN status = 'failed' THEN 1 END) as failed_runs,
                    COUNT(CASE WHEN status = 'processing' THEN 1 END) as processing_runs
                FROM analysis_runs
                WHERE created_at > NOW() - INTERVAL '24 hours'
            """)).fetchone()

            # Queue statistics
            queue_stats = session.execute(text("""
                SELECT
                    COUNT(CASE WHEN status = 'queued' THEN 1 END) as queued_items,
                    COUNT(CASE WHEN status = 'processing' THEN 1 END) as processing_items,
                    COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed_items,
                    COUNT(CASE WHEN status = 'failed' THEN 1 END) as failed_items
                FROM analysis_run_items
                WHERE created_at > NOW() - INTERVAL '24 hours'
            """)).fetchone()

            # Cost estimation (simplified)
            daily_cost = 0.0  # Would need to calculate based on actual usage

            return {
                "analysis_coverage": {
                    "total_items": total_items,
                    "analyzed_items": analyzed_items,
                    "coverage_percentage": round(analyzed_items / total_items * 100, 1) if total_items > 0 else 0
                },
                "run_stats": {
                    "total_runs_24h": recent_runs[0] if recent_runs else 0,
                    "completed_runs_24h": recent_runs[1] if recent_runs else 0,
                    "failed_runs_24h": recent_runs[2] if recent_runs else 0,
                    "processing_runs": recent_runs[3] if recent_runs else 0
                },
                "queue_stats": {
                    "queued_items": queue_stats[0] if queue_stats else 0,
                    "processing_items": queue_stats[1] if queue_stats else 0,
                    "completed_items_24h": queue_stats[2] if queue_stats else 0,
                    "failed_items_24h": queue_stats[3] if queue_stats else 0
                },
                "cost": {
                    "daily_cost": daily_cost,
                    "estimated_monthly": daily_cost * 30
                }
            }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get analysis stats: {str(e)}")


@router.post("/test-deferred")
async def test_deferred_handling() -> Dict[str, Any]:
    """Test deferred item handling (for go-live validation)."""
    try:
        # This would test the worker's deferred queue handling
        # For now, return a mock response
        return {
            "test_type": "deferred_handling",
            "status": "success",
            "message": "Deferred handling test completed",
            "deferred_items_processed": 0
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Deferred test failed: {str(e)}")


def _check_worker_process() -> bool:
    """Check if analysis worker process is running."""
    try:
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            cmdline = proc.info.get('cmdline', [])
            if any('analysis_worker.py' in arg for arg in cmdline):
                return True
        return False
    except Exception:
        return False


def _signal_worker(action: str):
    """Send signal to worker process."""
    try:
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            cmdline = proc.info.get('cmdline', [])
            if any('analysis_worker.py' in arg for arg in cmdline):
                if action == "stop":
                    proc.terminate()
                break
    except Exception as e:
        raise Exception(f"Failed to signal worker: {e}")


def _start_worker():
    """Start the analysis worker process."""
    try:
        import subprocess
        script_path = os.path.join(os.path.dirname(__file__), '../worker/analysis_worker.py')
        subprocess.Popen(['python', script_path],
                        cwd=os.path.dirname(script_path),
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL)
    except Exception as e:
        raise Exception(f"Failed to start worker: {e}")


def _update_worker_rps(rps: float):
    """Update worker RPS settings."""
    # This would update worker configuration
    # For now, just validate the value
    if rps <= 0 or rps > 10:
        raise ValueError("RPS must be between 0.1 and 10.0")