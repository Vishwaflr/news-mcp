"""
Consolidated Analysis API v1

This module consolidates functionality from:
- analysis_control.py (765 lines)
- analysis_management.py (408 lines)
- analysis_jobs.py
- analysis_worker_api.py

Provides a single, unified API for all analysis operations.
"""

from fastapi import APIRouter, HTTPException, Query, Body, Depends, BackgroundTasks
from fastapi.responses import JSONResponse
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from pydantic import BaseModel

from app.core.logging_config import get_logger
from app.domain.analysis.control import (
    RunScope, RunParams, RunPreview, AnalysisRun, AnalysisPreset,
    SLO_TARGETS
)
from app.services.domain.analysis_service import AnalysisService
from app.dependencies import get_analysis_service
from app.repositories.analysis_control import AnalysisControlRepo
from app.services.cost_estimator import get_cost_estimator
from app.services.analysis_run_manager import get_run_manager as get_analysis_run_manager
from app.database import get_session, engine
from sqlmodel import Session
from app.utils.feature_flags import feature_flags
import psutil
import os

router = APIRouter(prefix="/api/v1/analysis", tags=["analysis-v1"])
logger = get_logger(__name__)


# ============================================================================
# CORE OPERATIONS - Run Management
# ============================================================================

@router.post("/preview", response_model=RunPreview)
async def preview_analysis(
    scope: RunScope = Body(...),
    params: RunParams = Body(RunParams()),
    analysis_service: AnalysisService = Depends(get_analysis_service)
) -> RunPreview:
    """
    Preview what would be analyzed without starting a run.
    Shows items count, cost estimate, and duration estimate.
    """
    result = analysis_service.preview_analysis_run(scope, params)

    if not result.success:
        raise HTTPException(status_code=400, detail=result.error)

    return result.data


@router.post("/runs", response_model=AnalysisRun)
async def start_analysis_run(
    scope: RunScope = Body(...),
    params: RunParams = Body(RunParams()),
    triggered_by: str = Body("manual"),
    analysis_service: AnalysisService = Depends(get_analysis_service)
) -> AnalysisRun:
    """
    Start a new analysis run.

    Args:
        scope: Defines what to analyze (items, feeds, categories, time range)
        params: Run parameters (model, rate limit, etc.)
        triggered_by: Who/what triggered the run (manual, auto, scheduled)
    """
    result = await analysis_service.start_analysis_run(scope, params, triggered_by)

    if not result.success:
        raise HTTPException(status_code=400, detail=result.error)

    return result.data


@router.get("/runs", response_model=List[AnalysisRun])
async def list_analysis_runs(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    status: Optional[str] = Query(None),
    triggered_by: Optional[str] = Query(None),
    since: Optional[datetime] = Query(None),
    analysis_service: AnalysisService = Depends(get_analysis_service)
) -> List[AnalysisRun]:
    """
    List all analysis runs with optional filtering.

    Args:
        limit: Maximum number of runs to return
        offset: Number of runs to skip
        status: Filter by status (pending, running, completed, failed)
        triggered_by: Filter by trigger source (manual, auto, scheduled)
        since: Only show runs created after this time
    """
    with Session(engine) as session:
        repo = AnalysisControlRepo(session)
        runs = repo.list_runs(
            limit=limit,
            offset=offset,
            status=status,
            triggered_by=triggered_by,
            since=since
        )
        return runs


@router.get("/runs/{run_id}", response_model=AnalysisRun)
async def get_analysis_run(
    run_id: str,
    analysis_service: AnalysisService = Depends(get_analysis_service)
) -> AnalysisRun:
    """Get details of a specific analysis run."""
    # Convert string run_id to int
    try:
        run_id_int = int(run_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid run ID")

    # Use the static method directly - no session needed
    run = AnalysisControlRepo.get_run(run_id_int)

    if not run:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")

    return run


@router.delete("/runs/{run_id}")
async def cancel_analysis_run(
    run_id: str,
    analysis_service: AnalysisService = Depends(get_analysis_service)
) -> Dict[str, str]:
    """
    Cancel a running or queued analysis run.

    Returns:
        Success message with final run status
    """
    result = await analysis_service.cancel_analysis_run(run_id)

    if not result.success:
        raise HTTPException(status_code=400, detail=result.error)

    return {"message": f"Run {run_id} cancelled", "status": result.data.get("status")}


@router.post("/runs/{run_id}/pause")
async def pause_analysis_run(
    run_id: str,
    analysis_service: AnalysisService = Depends(get_analysis_service)
) -> Dict[str, str]:
    """Pause a running analysis run."""
    result = await analysis_service.pause_analysis_run(run_id)

    if not result.success:
        raise HTTPException(status_code=400, detail=result.error)

    return {"message": f"Run {run_id} paused", "status": "paused"}


@router.post("/runs/{run_id}/resume")
async def resume_analysis_run(
    run_id: str,
    analysis_service: AnalysisService = Depends(get_analysis_service)
) -> Dict[str, str]:
    """Resume a paused analysis run."""
    result = await analysis_service.resume_analysis_run(run_id)

    if not result.success:
        raise HTTPException(status_code=400, detail=result.error)

    return {"message": f"Run {run_id} resumed", "status": "running"}


@router.get("/runs/{run_id}/items")
async def get_analyzed_items(
    run_id: str,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0)
) -> Dict[str, Any]:
    """Get items that were analyzed in a specific run."""
    with Session(engine) as session:
        repo = AnalysisControlRepo(session)
        run = repo.get_run(run_id)

        if not run:
            raise HTTPException(status_code=404, detail=f"Run {run_id} not found")

        # Parse scope to get item IDs
        import json
        scope_data = json.loads(run.scope_json) if isinstance(run.scope_json, str) else run.scope_json
        item_ids = scope_data.get("item_ids", [])

        # Get items with their analysis results
        from app.models.core import Item
        from app.models.analysis import ItemAnalysis, AnalysisRunItem
        from sqlmodel import select

        items_query = select(Item, ItemAnalysis).join(
            AnalysisRunItem, Item.id == AnalysisRunItem.item_id
        ).join(
            ItemAnalysis, Item.id == ItemAnalysis.item_id, isouter=True
        ).where(
            AnalysisRunItem.run_id == run_id
        ).offset(offset).limit(limit)

        results = session.exec(items_query).all()

        items = []
        for item, analysis in results:
            analysis_data = None
            if analysis:
                analysis_data = {
                    "sentiment_score": analysis.sentiment_score,
                    "sentiment_label": analysis.sentiment_label,
                    "impact_score": analysis.impact_score,
                    "urgency_score": analysis.urgency_score,
                    "relevance_score": analysis.relevance_score,
                    "impact_overall": analysis.impact_overall,
                    "model_tag": analysis.model_tag,
                    "processed_at": analysis.created_at
                }

            items.append({
                "id": item.id,
                "title": item.title,
                "feed_id": item.feed_id,
                "published": item.published,
                "analysis": analysis_data
            })

        return {
            "run_id": run_id,
            "total_items": len(item_ids),
            "items": items,
            "limit": limit,
            "offset": offset
        }


# ============================================================================
# PRESETS - Saved Configurations
# ============================================================================

@router.get("/presets", response_model=List[AnalysisPreset])
async def list_presets() -> List[AnalysisPreset]:
    """List all saved analysis presets."""
    with Session(engine) as session:
        repo = AnalysisControlRepo(session)
        return repo.list_presets()


@router.post("/presets", response_model=AnalysisPreset)
async def create_preset(
    name: str = Body(...),
    description: Optional[str] = Body(None),
    scope: RunScope = Body(...),
    params: RunParams = Body(...)
) -> AnalysisPreset:
    """Create a new analysis preset."""
    with Session(engine) as session:
        repo = AnalysisControlRepo(session)
        preset = repo.create_preset(name, description, scope, params)
        return preset


@router.delete("/presets/{preset_id}")
async def delete_preset(preset_id: str) -> Dict[str, str]:
    """Delete an analysis preset."""
    with Session(engine) as session:
        repo = AnalysisControlRepo(session)
        success = repo.delete_preset(preset_id)

        if not success:
            raise HTTPException(status_code=404, detail=f"Preset {preset_id} not found")

        return {"message": f"Preset {preset_id} deleted"}


# ============================================================================
# STATISTICS & MONITORING
# ============================================================================

@router.get("/stats")
async def get_analysis_statistics(
    days: int = Query(7, ge=1, le=90)
) -> Dict[str, Any]:
    """
    Get comprehensive analysis statistics.

    Returns:
        - Total runs, success rate, items analyzed
        - Average run duration and cost
        - Breakdown by trigger type (manual, auto, scheduled)
        - Top categories analyzed
    """
    with Session(engine) as session:
        from app.models.analysis import AnalysisRun, AnalysisRunItem
        from sqlmodel import select, func

        since = datetime.utcnow() - timedelta(days=days)

        # Basic stats
        runs_query = select(AnalysisRun).where(AnalysisRun.created_at >= since)
        runs = session.exec(runs_query).all()

        total_runs = len(runs)
        successful_runs = sum(1 for r in runs if r.status == "completed")
        failed_runs = sum(1 for r in runs if r.status in ["failed", "error"])

        # Items analyzed
        items_query = select(func.count(AnalysisRunItem.id)).join(
            AnalysisRun, AnalysisRunItem.run_id == AnalysisRun.id
        ).where(AnalysisRun.created_at >= since)
        items_analyzed = session.exec(items_query).one()

        # Average duration
        durations = []
        for run in runs:
            if run.completed_at and run.started_at:
                duration = (run.completed_at - run.started_at).total_seconds()
                durations.append(duration)

        avg_duration = sum(durations) / len(durations) if durations else 0

        # Breakdown by trigger
        trigger_breakdown = {}
        for run in runs:
            trigger = run.triggered_by or "manual"
            trigger_breakdown[trigger] = trigger_breakdown.get(trigger, 0) + 1

        return {
            "period_days": days,
            "total_runs": total_runs,
            "successful_runs": successful_runs,
            "failed_runs": failed_runs,
            "success_rate": (successful_runs / total_runs * 100) if total_runs > 0 else 0,
            "items_analyzed": items_analyzed,
            "average_duration_seconds": avg_duration,
            "trigger_breakdown": trigger_breakdown,
            "daily_average": total_runs / days if days > 0 else 0
        }


@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """
    Health check for the analysis system.

    Returns:
        - System status
        - Worker status
        - Queue status
        - Resource usage
    """
    manager = get_analysis_run_manager()

    # Check worker process
    worker_pid = None
    worker_running = False

    try:
        # Check if worker process is running
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            if proc.info['cmdline'] and 'analysis_worker' in ' '.join(proc.info['cmdline']):
                worker_pid = proc.info['pid']
                worker_running = True
                break
    except Exception as e:
        logger.error(f"Error checking worker process: {e}")

    return {
        "status": "healthy" if worker_running else "degraded",
        "timestamp": datetime.utcnow(),
        "components": {
            "api": "healthy",
            "worker": "running" if worker_running else "stopped",
            "worker_pid": worker_pid,
            "database": "connected",
            "queue": {
                "pending": manager.get_queue_status()["total_queued"] if manager else 0,
                "processing": manager.get_status().get("active_runs", 0) if manager else 0
            }
        },
        "resources": {
            "cpu_percent": psutil.cpu_percent(),
            "memory_percent": psutil.virtual_memory().percent
        }
    }


@router.get("/history")
async def get_analysis_history(
    days: int = Query(30, ge=1, le=365),
    group_by: str = Query("day", regex="^(day|week|month)$")
) -> List[Dict[str, Any]]:
    """
    Get historical analysis data grouped by time period.

    Args:
        days: Number of days to look back
        group_by: Grouping period (day, week, month)

    Returns:
        Time series data with runs count and items analyzed
    """
    with Session(engine) as session:
        from app.models.analysis import AnalysisRun
        from sqlmodel import select

        since = datetime.utcnow() - timedelta(days=days)

        runs_query = select(AnalysisRun).where(
            AnalysisRun.created_at >= since
        ).order_by(AnalysisRun.created_at)

        runs = session.exec(runs_query).all()

        # Group by period
        grouped = {}
        for run in runs:
            if group_by == "day":
                key = run.created_at.date()
            elif group_by == "week":
                key = run.created_at.isocalendar()[1]  # Week number
            else:  # month
                key = f"{run.created_at.year}-{run.created_at.month:02d}"

            if key not in grouped:
                grouped[key] = {
                    "period": str(key),
                    "runs": 0,
                    "successful": 0,
                    "failed": 0,
                    "items": 0
                }

            grouped[key]["runs"] += 1
            if run.status == "completed":
                grouped[key]["successful"] += 1
            elif run.status in ["failed", "error"]:
                grouped[key]["failed"] += 1

            # Count items (parse scope)
            try:
                import json
                scope = json.loads(run.scope_json) if isinstance(run.scope_json, str) else run.scope_json
                grouped[key]["items"] += len(scope.get("item_ids", []))
            except Exception:
                pass

        return list(grouped.values())


# ============================================================================
# COST & BUDGET
# ============================================================================

@router.get("/cost/{model}")
async def get_model_cost(model: str) -> Dict[str, Any]:
    """Get cost information for a specific AI model."""
    cost_estimator = get_cost_estimator()

    if model not in cost_estimator.model_costs:
        raise HTTPException(status_code=404, detail=f"Model {model} not found")

    return {
        "model": model,
        "cost_per_1k_tokens": cost_estimator.model_costs[model],
        "estimated_cost_per_item": cost_estimator.estimate_item_cost(model),
        "tokens_per_item_avg": 500  # Rough estimate
    }


@router.get("/models/compare")
async def compare_models() -> List[Dict[str, Any]]:
    """Compare all available AI models for cost and performance."""
    cost_estimator = get_cost_estimator()

    models = []
    for model_name, cost in cost_estimator.model_costs.items():
        models.append({
            "model": model_name,
            "cost_per_1k_tokens": cost,
            "cost_per_100_items": cost_estimator.estimate_cost(100, model_name),
            "speed": "fast" if "nano" in model_name or "mini" in model_name else "normal",
            "quality": "high" if "gpt-4" in model_name else "standard"
        })

    return sorted(models, key=lambda x: x["cost_per_1k_tokens"])


@router.get("/budget")
async def get_budget_info() -> Dict[str, Any]:
    """Get current budget usage and limits."""
    with Session(engine) as session:
        from app.models.analysis import AnalysisRun
        from sqlmodel import select

        # Current month
        now = datetime.utcnow()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        # Get runs this month
        runs_query = select(AnalysisRun).where(
            AnalysisRun.created_at >= month_start
        )
        runs = session.exec(runs_query).all()

        # Calculate costs
        total_cost = 0
        cost_estimator = get_cost_estimator()

        for run in runs:
            try:
                import json
                scope = json.loads(run.scope_json) if isinstance(run.scope_json, str) else run.scope_json
                params = json.loads(run.params_json) if isinstance(run.params_json, str) else run.params_json

                items_count = len(scope.get("item_ids", []))
                model = params.get("model_tag", "gpt-4.1-nano")

                run_cost = cost_estimator.estimate_cost(items_count, model)
                total_cost += run_cost
            except Exception:
                pass

        # Budget limits (configurable)
        monthly_budget = 100.0  # $100 per month
        daily_budget = monthly_budget / 30

        return {
            "period": "month",
            "start_date": month_start,
            "spent": round(total_cost, 2),
            "budget": monthly_budget,
            "remaining": round(monthly_budget - total_cost, 2),
            "percentage_used": round((total_cost / monthly_budget * 100), 1) if monthly_budget > 0 else 0,
            "daily_average": round(total_cost / now.day, 2),
            "daily_budget": round(daily_budget, 2),
            "projected_monthly": round((total_cost / now.day) * 30, 2) if now.day > 0 else 0
        }


# ============================================================================
# MANAGER CONTROL (Admin)
# ============================================================================

@router.get("/manager/status")
async def get_manager_status() -> Dict[str, Any]:
    """Get the analysis manager status and configuration."""
    manager = get_analysis_run_manager()

    if not manager:
        raise HTTPException(status_code=503, detail="Analysis manager not available")

    status = manager.get_status()
    return {
        "emergency_stop": manager.emergency_stop,
        "active_runs": status["active_runs"],
        "queued_runs": status["queued_runs"],
        "limits": {
            "max_concurrent": manager.max_concurrent_runs,
            "max_daily": manager.max_daily_runs,
            "max_hourly": manager.max_hourly_runs
        },
        "current_usage": {
            "daily_runs": manager.get_daily_run_count(),
            "hourly_runs": manager.get_hourly_run_count()
        }
    }


@router.post("/manager/emergency-stop")
async def emergency_stop() -> Dict[str, str]:
    """Emergency stop all analysis runs."""
    manager = get_analysis_run_manager()

    if not manager:
        raise HTTPException(status_code=503, detail="Analysis manager not available")

    await manager.emergency_stop_all()

    return {"message": "Emergency stop activated", "status": "stopped"}


@router.post("/manager/resume")
async def resume_after_emergency() -> Dict[str, str]:
    """Resume normal operations after emergency stop."""
    manager = get_analysis_run_manager()

    if not manager:
        raise HTTPException(status_code=503, detail="Analysis manager not available")

    manager.emergency_stop = False

    return {"message": "Operations resumed", "status": "active"}


@router.get("/manager/queue")
async def get_queue_status() -> Dict[str, Any]:
    """Get detailed queue information."""
    manager = get_analysis_run_manager()

    if not manager:
        raise HTTPException(status_code=503, detail="Analysis manager not available")

    queue_status = manager.get_queue_status()
    status = manager.get_status()
    return {
        "queued_count": queue_status["total_queued"],
        "queued_runs": manager.get_queue_list(50),
        "processing": status["active_runs"],
        "can_process": not manager.emergency_stop and status["active_runs"] < manager.max_concurrent_runs
    }


@router.get("/manager/limits")
async def get_rate_limits() -> Dict[str, Any]:
    """Get current rate limiting configuration."""
    manager = get_analysis_run_manager()

    if not manager:
        raise HTTPException(status_code=503, detail="Analysis manager not available")

    return {
        "limits": {
            "concurrent_runs": manager.max_concurrent_runs,
            "daily_runs": manager.max_daily_runs,
            "hourly_runs": manager.max_hourly_runs,
            "daily_auto_runs": manager.max_daily_auto_runs
        },
        "current_usage": {
            "active_runs": manager.get_status()["active_runs"],
            "daily_runs_used": manager.get_daily_run_count(),
            "hourly_runs_used": manager.get_hourly_run_count(),
            "daily_auto_runs_used": manager.get_daily_auto_run_count()
        },
        "remaining": {
            "daily": max(0, manager.max_daily_runs - manager.get_daily_run_count()),
            "hourly": max(0, manager.max_hourly_runs - manager.get_hourly_run_count())
        }
    }


# ============================================================================
# WORKER CONTROL (Admin)
# ============================================================================

@router.get("/worker/status")
async def get_worker_status() -> Dict[str, Any]:
    """Get analysis worker process status."""
    worker_info = {
        "status": "unknown",
        "pid": None,
        "uptime": None,
        "memory_usage": None,
        "cpu_usage": None
    }

    try:
        # Find worker process
        for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'create_time']):
            if proc.info['cmdline'] and 'analysis_worker' in ' '.join(proc.info['cmdline']):
                worker_info["status"] = "running"
                worker_info["pid"] = proc.info['pid']

                # Calculate uptime
                create_time = datetime.fromtimestamp(proc.info['create_time'])
                uptime = datetime.now() - create_time
                worker_info["uptime"] = str(uptime)

                # Get resource usage
                try:
                    proc_obj = psutil.Process(proc.info['pid'])
                    worker_info["memory_usage"] = proc_obj.memory_info().rss / 1024 / 1024  # MB
                    worker_info["cpu_usage"] = proc_obj.cpu_percent()
                except Exception:
                    pass

                break
        else:
            worker_info["status"] = "stopped"
    except Exception as e:
        logger.error(f"Error checking worker status: {e}")
        worker_info["error"] = str(e)

    return worker_info


class WorkerControlRequest(BaseModel):
    action: str  # start, stop, restart


@router.post("/worker/control")
async def control_worker(
    request: WorkerControlRequest,
    background_tasks: BackgroundTasks
) -> Dict[str, str]:
    """
    Control the analysis worker process.

    Actions:
        - start: Start the worker if not running
        - stop: Stop the worker gracefully
        - restart: Stop and start the worker
    """
    import subprocess
    import signal

    if request.action == "start":
        # Check if already running
        for proc in psutil.process_iter(['pid', 'cmdline']):
            if proc.info['cmdline'] and 'analysis_worker' in ' '.join(proc.info['cmdline']):
                return {"message": "Worker already running", "status": "running"}

        # Start worker
        try:
            subprocess.Popen(
                ["python", "-m", "app.workers.analysis_worker"],
                cwd="/home/cytrex/news-mcp",
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            return {"message": "Worker started", "status": "starting"}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to start worker: {e}")

    elif request.action == "stop":
        # Find and stop worker
        stopped = False
        for proc in psutil.process_iter(['pid', 'cmdline']):
            if proc.info['cmdline'] and 'analysis_worker' in ' '.join(proc.info['cmdline']):
                try:
                    os.kill(proc.info['pid'], signal.SIGTERM)
                    stopped = True
                except Exception as e:
                    logger.error(f"Error stopping worker: {e}")

        if stopped:
            return {"message": "Worker stopped", "status": "stopped"}
        else:
            return {"message": "Worker not running", "status": "not_running"}

    elif request.action == "restart":
        # Stop first
        for proc in psutil.process_iter(['pid', 'cmdline']):
            if proc.info['cmdline'] and 'analysis_worker' in ' '.join(proc.info['cmdline']):
                try:
                    os.kill(proc.info['pid'], signal.SIGTERM)
                except Exception:
                    pass

        # Wait a bit
        import time
        time.sleep(2)

        # Start worker
        try:
            subprocess.Popen(
                ["python", "-m", "app.workers.analysis_worker"],
                cwd="/home/cytrex/news-mcp",
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            return {"message": "Worker restarted", "status": "restarting"}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to restart worker: {e}")

    else:
        raise HTTPException(status_code=400, detail=f"Invalid action: {request.action}")


# ============================================================================
# BACKWARDS COMPATIBILITY - Redirects from old endpoints
# ============================================================================

@router.post("/../../analysis/preview")
async def legacy_preview_redirect(
    scope: Optional[RunScope] = Body(None),
    params: Optional[RunParams] = Body(None),
    item_ids: Optional[List[int]] = Body(None),
    analysis_service: AnalysisService = Depends(get_analysis_service)
):
    """Legacy redirect from /analysis/preview"""
    logger.warning("Using deprecated endpoint /analysis/preview - use /api/v1/analysis/preview")

    # Handle legacy format
    if item_ids is not None and scope is None:
        scope = RunScope(type="items", item_ids=item_ids)
        params = RunParams()

    return await preview_analysis(scope, params or RunParams(), analysis_service)


@router.post("/../../analysis/start")
async def legacy_start_redirect(
    scope: RunScope = Body(...),
    params: RunParams = Body(RunParams()),
    analysis_service: AnalysisService = Depends(get_analysis_service)
):
    """Legacy redirect from /analysis/start"""
    logger.warning("Using deprecated endpoint /analysis/start - use /api/v1/analysis/runs")
    return await start_analysis_run(scope, params, "manual", analysis_service)