from fastapi import APIRouter, HTTPException, Query, Body, Depends
from fastapi.responses import HTMLResponse
from typing import List, Optional
from app.core.logging_config import get_logger

from app.domain.analysis.control import (
    RunScope, RunParams, RunPreview, AnalysisRun, AnalysisPreset,
    SLO_TARGETS
)
from app.services.domain.analysis_service import AnalysisService
from app.dependencies import get_analysis_service
from app.repositories.analysis_control import AnalysisControlRepo
from app.services.cost_estimator import get_cost_estimator

router = APIRouter(prefix="/analysis", tags=["analysis-control"])
logger = get_logger(__name__)

# Updated limit to 1000 articles - forced reload

@router.post("/preview")
async def preview_run(
    scope: Optional[RunScope] = Body(None),
    params: Optional[RunParams] = Body(None),
    item_ids: Optional[List[int]] = Body(None),
    analysis_service: AnalysisService = Depends(get_analysis_service)
) -> RunPreview:
    """Preview what a run would analyze - supports both new and legacy formats"""

    # Handle legacy format with just item_ids
    if item_ids is not None and scope is None:
        scope = RunScope(type="items", item_ids=item_ids)
        params = RunParams()  # Use defaults
    elif scope is None or params is None:
        raise HTTPException(
            status_code=400,
            detail="Either provide item_ids or both scope and params"
        )

    result = analysis_service.preview_analysis_run(scope, params)

    if not result.success:
        raise HTTPException(status_code=400, detail=result.error)

    return result.data

@router.post("/start")
async def start_run(
    scope: RunScope = Body(...),
    params: RunParams = Body(...),
    analysis_service: AnalysisService = Depends(get_analysis_service)
) -> AnalysisRun:
    """Start a new analysis run"""
    result = await analysis_service.start_analysis_run(scope, params)

    if not result.success:
        if "exceeds limit" in result.error or "concurrent runs" in result.error:
            raise HTTPException(status_code=400, detail=result.error)
        raise HTTPException(status_code=500, detail=result.error)

    return result.data

@router.post("/runs")
async def create_run(
    scope: RunScope = Body(...),
    params: RunParams = Body(...),
    analysis_service: AnalysisService = Depends(get_analysis_service)
) -> AnalysisRun:
    """Create a new analysis run (alias for /start for frontend compatibility)"""
    try:
        return await start_run(scope, params, analysis_service)
    except Exception as e:
        import traceback
        logger.error(f"Error in create_run endpoint: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise

@router.get("/runs")
async def list_runs(
    active_only: bool = Query(False),
    analysis_service: AnalysisService = Depends(get_analysis_service)
) -> List[AnalysisRun]:
    """List analysis runs (active by default, or all recent runs)"""
    if active_only:
        return await get_active_runs(analysis_service)
    else:
        result = analysis_service.list_analysis_runs(limit=50, days_back=7)
        if not result.success:
            raise HTTPException(status_code=500, detail=result.error)
        return result.data

@router.post("/pause/{run_id}")
async def pause_run(run_id: int) -> dict:
    """Pause an active analysis run"""
    try:
        success = AnalysisControlRepo.update_run_status(run_id, "paused")
        if not success:
            raise HTTPException(status_code=404, detail="Run not found or cannot be paused")

        return {"status": "paused", "run_id": run_id}

    except Exception as e:
        logger.error(f"Failed to pause run {run_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/start/{run_id}")
async def resume_run(run_id: int) -> dict:
    """Resume/start a paused or pending analysis run"""
    try:
        success = AnalysisControlRepo.update_run_status(run_id, "running")
        if not success:
            raise HTTPException(status_code=404, detail="Run not found or cannot be started")

        return {"status": "running", "run_id": run_id}

    except Exception as e:
        logger.error(f"Failed to start/resume run {run_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/cancel/{run_id}")
async def cancel_run(
    run_id: int,
    analysis_service: AnalysisService = Depends(get_analysis_service)
) -> dict:
    """Cancel an analysis run"""
    result = analysis_service.cancel_analysis_run(run_id, "User cancelled")

    if not result.success:
        if "not found" in result.error:
            raise HTTPException(status_code=404, detail=result.error)
        raise HTTPException(status_code=400, detail=result.error)

    return {"status": "cancelled", "run_id": run_id}

@router.get("/status/{run_id}")
async def get_run_status(
    run_id: int,
    analysis_service: AnalysisService = Depends(get_analysis_service)
) -> AnalysisRun:
    """Get current status of an analysis run"""
    result = analysis_service.get_analysis_run(run_id)

    if not result.success:
        if "not found" in result.error:
            raise HTTPException(status_code=404, detail=result.error)
        raise HTTPException(status_code=500, detail=result.error)

    return result.data

@router.get("/status")
async def get_active_runs(
    analysis_service: AnalysisService = Depends(get_analysis_service)
) -> List[AnalysisRun]:
    """Get status of all active runs"""
    result = analysis_service.get_active_runs()

    if not result.success:
        raise HTTPException(status_code=500, detail=result.error)

    return result.data

@router.get("/history")
async def get_run_history(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    analysis_service: AnalysisService = Depends(get_analysis_service)
) -> dict:
    """Get paginated run history"""
    result = analysis_service.list_analysis_runs(limit=limit, days_back=30)

    if not result.success:
        raise HTTPException(status_code=500, detail=result.error)

    runs = result.data
    offset = (page - 1) * limit
    paginated_runs = runs[offset:offset + limit]

    return {
        "runs": paginated_runs,
        "page": page,
        "limit": limit,
        "has_more": len(runs) > offset + limit
    }

# Preset endpoints
@router.post("/presets")
async def save_preset(preset: AnalysisPreset) -> AnalysisPreset:
    """Save an analysis preset"""
    try:
        return AnalysisControlRepo.save_preset(preset)
    except Exception as e:
        logger.error(f"Failed to save preset: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/presets")
async def get_presets() -> List[AnalysisPreset]:
    """Get all saved presets"""
    try:
        return AnalysisControlRepo.get_presets()
    except Exception as e:
        logger.error(f"Failed to get presets: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/presets/{preset_id}")
async def delete_preset(preset_id: int) -> dict:
    """Delete an analysis preset"""
    try:
        success = AnalysisControlRepo.delete_preset(preset_id)
        if not success:
            raise HTTPException(status_code=404, detail="Preset not found")

        return {"status": "deleted", "preset_id": preset_id}

    except Exception as e:
        logger.error(f"Failed to delete preset {preset_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Quick actions endpoint (deprecated - now returns empty list)
@router.get("/quick-actions")
async def get_quick_actions() -> List:
    """Quick actions have been removed"""
    return []

# Utility endpoints
@router.get("/articles")
async def get_available_articles(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=5000),
    feed_id: Optional[int] = Query(None),
    unanalyzed_only: bool = Query(True)
) -> dict:
    """Get available articles for selection"""
    from sqlmodel import Session, text
    from app.database import engine

    try:
        with Session(engine) as session:
            offset = (page - 1) * limit

            # Base query with optional filters
            conditions = []
            params = {"limit": limit, "offset": offset}

            if feed_id:
                conditions.append("i.feed_id = :feed_id")
                params["feed_id"] = feed_id

            if unanalyzed_only:
                conditions.append("a.item_id IS NULL")

            where_clause = " AND ".join(conditions) if conditions else "1=1"

            # Get articles with pagination
            query = f"""
                SELECT
                    i.id, i.title, i.link, i.created_at,
                    f.title as feed_title,
                    CASE WHEN a.item_id IS NOT NULL THEN true ELSE false END as analyzed
                FROM items i
                LEFT JOIN feeds f ON f.id = i.feed_id
                LEFT JOIN item_analysis a ON a.item_id = i.id
                WHERE {where_clause}
                ORDER BY i.created_at DESC
                LIMIT :limit OFFSET :offset
            """

            results = session.execute(text(query), params).fetchall()

            # Get total count
            count_query = f"""
                SELECT COUNT(*)
                FROM items i
                LEFT JOIN item_analysis a ON a.item_id = i.id
                WHERE {where_clause}
            """
            total_count = session.execute(text(count_query), {k: v for k, v in params.items() if k not in ["limit", "offset"]}).scalar()

            articles = []
            for row in results:
                articles.append({
                    "id": row[0],
                    "title": row[1] or "Untitled",
                    "link": row[2],
                    "created_at": row[3].isoformat() if row[3] else None,
                    "feed_title": row[4] or "Unknown Feed",
                    "analyzed": row[5]
                })

            return {
                "articles": articles,
                "page": page,
                "limit": limit,
                "total": total_count,
                "has_more": (page * limit) < total_count
            }

    except Exception as e:
        logger.error(f"Failed to get articles: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/feeds")
async def get_available_feeds(
    analysis_service: AnalysisService = Depends(get_analysis_service)
) -> List[dict]:
    """Get available feeds for selection"""
    result = analysis_service.get_available_feeds()

    if not result.success:
        raise HTTPException(status_code=500, detail=result.error)

    return result.data

@router.get("/stats")
async def get_analysis_stats(
    analysis_service: AnalysisService = Depends(get_analysis_service)
) -> dict:
    """Get overall analysis statistics"""
    result = analysis_service.get_analysis_statistics(days_back=30)

    if not result.success:
        raise HTTPException(status_code=500, detail=result.error)

    return result.data

# MCP v2 Enhanced Endpoints

@router.get("/history")
async def get_analysis_history(
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    status: Optional[str] = Query(None, regex="^(queued|running|done|error)$"),
    analysis_service: AnalysisService = Depends(get_analysis_service)
) -> dict:
    """Get analysis run history with pagination and filtering"""
    try:
        # This would need to be implemented in the analysis service
        # For now, return a placeholder structure
        runs = []  # Would query from database

        result = {
            "ok": True,
            "data": {
                "runs": runs,
                "pagination": {
                    "limit": limit,
                    "offset": offset,
                    "total": len(runs),
                    "has_more": False
                }
            },
            "meta": {"status_filter": status},
            "errors": []
        }

        return result
    except Exception as e:
        logger.error(f"Error getting analysis history: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/cost/{model}")
async def get_cost_estimate(
    model: str,
    article_count: int = Query(..., ge=1, le=10000),
    avg_article_length: int = Query(1000, ge=100, le=5000)
) -> dict:
    """Get cost estimation for analyzing articles with specified model"""
    try:
        cost_estimator = get_cost_estimator()

        # Get cost estimate
        estimate = cost_estimator.estimate_analysis_cost(
            model=model,
            article_count=article_count,
            avg_article_length=avg_article_length
        )

        if "error" in estimate:
            raise HTTPException(status_code=400, detail=estimate["error"])

        result = {
            "ok": True,
            "data": estimate,
            "meta": {"model": model, "article_count": article_count},
            "errors": []
        }

        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error calculating cost estimate: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/models/compare")
async def compare_model_costs(
    article_count: int = Query(..., ge=1, le=10000),
    avg_article_length: int = Query(1000, ge=100, le=5000)
) -> dict:
    """Compare costs across all available analysis models"""
    try:
        cost_estimator = get_cost_estimator()

        comparison = cost_estimator.compare_models(
            article_count=article_count,
            avg_article_length=avg_article_length
        )

        if "error" in comparison:
            raise HTTPException(status_code=400, detail=comparison["error"])

        result = {
            "ok": True,
            "data": comparison,
            "meta": {"article_count": article_count, "avg_article_length": avg_article_length},
            "errors": []
        }

        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error comparing model costs: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/budget")
async def get_budget_recommendations(
    budget_usd: float = Query(..., ge=0.01, le=1000.0),
    model: str = Query(...),
    avg_article_length: int = Query(1000, ge=100, le=5000)
) -> dict:
    """Get recommendations for article analysis within budget"""
    try:
        cost_estimator = get_cost_estimator()

        recommendations = cost_estimator.get_budget_recommendations(
            budget_usd=budget_usd,
            model=model,
            avg_article_length=avg_article_length
        )

        if "error" in recommendations:
            raise HTTPException(status_code=400, detail=recommendations["error"])

        result = {
            "ok": True,
            "data": recommendations,
            "meta": {"budget_usd": budget_usd, "model": model},
            "errors": []
        }

        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting budget recommendations: {e}")
        raise HTTPException(status_code=500, detail=str(e))