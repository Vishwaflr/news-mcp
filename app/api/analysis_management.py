"""
Analysis Management API

Provides endpoints for monitoring and controlling analysis runs.
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any
from app.core.logging_config import get_logger
from app.services.analysis_run_manager import get_run_manager

router = APIRouter(prefix="/api/analysis", tags=["analysis-management"])
logger = get_logger(__name__)

@router.get("/manager/status")
async def get_manager_status() -> Dict[str, Any]:
    """Get current RunManager status and limits"""
    try:
        run_manager = get_run_manager()
        status = run_manager.get_status()
        return {
            "success": True,
            "data": status
        }
    except Exception as e:
        logger.error(f"Error getting manager status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get manager status: {str(e)}")

@router.post("/manager/emergency-stop")
async def emergency_stop(reason: str = "Manual emergency stop via API") -> Dict[str, Any]:
    """
    Emergency stop all analysis processing.

    This will:
    - Stop accepting new runs
    - Clear the run queue
    - Signal running processes to stop
    """
    try:
        run_manager = get_run_manager()
        result = await run_manager.emergency_stop_all(reason)

        logger.critical(f"Emergency stop activated via API: {reason}")

        return {
            "success": True,
            "message": result["message"],
            "emergency_stop": True
        }
    except Exception as e:
        logger.error(f"Error activating emergency stop: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to activate emergency stop: {str(e)}")

@router.post("/manager/resume")
async def resume_operations() -> Dict[str, Any]:
    """
    Resume operations after emergency stop.
    """
    try:
        run_manager = get_run_manager()
        result = await run_manager.resume_operations()

        logger.info("Operations resumed via API")

        return {
            "success": True,
            "message": result["message"],
            "emergency_stop": False
        }
    except Exception as e:
        logger.error(f"Error resuming operations: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to resume operations: {str(e)}")

@router.get("/manager/limits")
async def get_limits() -> Dict[str, Any]:
    """Get current system limits and their status"""
    try:
        run_manager = get_run_manager()
        status = run_manager.get_status()

        return {
            "success": True,
            "data": {
                "concurrent_runs": {
                    "current": status["active_runs"],
                    "limit": status["max_concurrent"],
                    "at_limit": status["limits"]["at_concurrent_limit"]
                },
                "daily_runs": {
                    "total_today": status["daily_stats"]["total_runs"],
                    "auto_today": status["daily_stats"]["auto_runs"],
                    "limit_total": status["daily_stats"]["limit_total"],
                    "limit_auto": status["daily_stats"]["limit_auto"],
                    "at_limit": status["limits"]["at_daily_limit"]
                },
                "hourly_runs": {
                    "current": status["hourly_stats"]["runs_last_hour"],
                    "limit": status["hourly_stats"]["limit"],
                    "at_limit": status["limits"]["at_hourly_limit"]
                }
            }
        }
    except Exception as e:
        logger.error(f"Error getting limits: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get limits: {str(e)}")

@router.get("/manager/queue")
async def get_queue_status() -> Dict[str, Any]:
    """Get current queue status and list of queued runs"""
    try:
        run_manager = get_run_manager()

        # Get queue status and list
        queue_status = run_manager.get_queue_status()
        queue_list = run_manager.get_queue_list(limit=50)

        return {
            "success": True,
            "data": {
                "status": queue_status,
                "queue": queue_list
            }
        }
    except Exception as e:
        logger.error(f"Error getting queue status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get queue status: {str(e)}")

@router.post("/manager/queue/process")
async def process_queue() -> Dict[str, Any]:
    """Manually trigger queue processing (for testing)"""
    try:
        run_manager = get_run_manager()
        next_run = await run_manager.process_queue()

        if next_run:
            return {
                "success": True,
                "message": "Queue item processed",
                "data": next_run
            }
        else:
            return {
                "success": True,
                "message": "No items in queue or no capacity",
                "data": None
            }
    except Exception as e:
        logger.error(f"Error processing queue: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to process queue: {str(e)}")

@router.delete("/manager/queue/{queued_run_id}")
async def cancel_queued_run(queued_run_id: int) -> Dict[str, Any]:
    """Cancel a specific queued run"""
    try:
        run_manager = get_run_manager()
        success = await run_manager.queue_manager.cancel_run(queued_run_id)

        if success:
            return {
                "success": True,
                "message": f"Queued run {queued_run_id} cancelled"
            }
        else:
            return {
                "success": False,
                "message": f"Failed to cancel queued run {queued_run_id} (not found or already running)"
            }
    except Exception as e:
        logger.error(f"Error cancelling queued run {queued_run_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to cancel queued run: {str(e)}")

@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """Health check for analysis system"""
    try:
        run_manager = get_run_manager()
        status = run_manager.get_status()

        # Determine health status
        health = "healthy"
        issues = []

        if status.get("emergency_stop", False):
            health = "emergency_stop"
            issues.append("Emergency stop is active")

        if status["limits"]["at_concurrent_limit"]:
            health = "degraded" if health == "healthy" else health
            issues.append("At concurrent run limit")

        if status["limits"]["at_daily_limit"]:
            health = "degraded" if health == "healthy" else health
            issues.append("At daily run limit")

        if status["limits"]["at_hourly_limit"]:
            health = "degraded" if health == "healthy" else health
            issues.append("At hourly run limit")

        return {
            "success": True,
            "health": health,
            "issues": issues,
            "active_runs": status["active_runs"],
            "emergency_stop": status.get("emergency_stop", False),
            "timestamp": status.get("timestamp")
        }
    except Exception as e:
        logger.error(f"Error during health check: {e}")
        return {
            "success": False,
            "health": "error",
            "issues": [f"Health check failed: {str(e)}"],
            "active_runs": 0,
            "emergency_stop": False
        }