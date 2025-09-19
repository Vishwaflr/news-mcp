from fastapi import APIRouter, HTTPException, Query, Body
from fastapi.responses import HTMLResponse
from typing import List, Optional
import logging

from app.domain.analysis.control import (
    RunScope, RunParams, RunPreview, AnalysisRun, AnalysisPreset,
    SLO_TARGETS
)
from app.repositories.analysis_control import AnalysisControlRepo

router = APIRouter(prefix="/analysis", tags=["analysis-control"])
logger = logging.getLogger(__name__)

@router.post("/preview")
async def preview_run(
    scope: RunScope = Body(...),
    params: RunParams = Body(...)
) -> RunPreview:
    """Preview what a run would analyze"""
    try:
        preview = AnalysisControlRepo.preview_run(scope, params)
        return preview
    except Exception as e:
        logger.error(f"Preview failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/start")
async def start_run(
    scope: RunScope = Body(...),
    params: RunParams = Body(...)
) -> AnalysisRun:
    """Start a new analysis run"""
    try:
        # Validate cost estimate
        preview = AnalysisControlRepo.preview_run(scope, params)
        if preview.estimated_cost_usd > SLO_TARGETS["max_cost_per_run"]:
            raise HTTPException(
                status_code=400,
                detail=f"Estimated cost ${preview.estimated_cost_usd:.2f} exceeds limit ${SLO_TARGETS['max_cost_per_run']:.2f}"
            )

        run = AnalysisControlRepo.create_run(scope, params)
        logger.info(f"Started analysis run {run.id} with {run.metrics.total_count} items")
        return run

    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to start run: {e}")
        raise HTTPException(status_code=500, detail=str(e))

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
async def cancel_run(run_id: int) -> dict:
    """Cancel an analysis run"""
    try:
        success = AnalysisControlRepo.update_run_status(run_id, "cancelled")
        if not success:
            raise HTTPException(status_code=404, detail="Run not found or cannot be cancelled")

        return {"status": "cancelled", "run_id": run_id}

    except Exception as e:
        logger.error(f"Failed to cancel run {run_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status/{run_id}")
async def get_run_status(run_id: int) -> AnalysisRun:
    """Get current status of an analysis run"""
    try:
        run = AnalysisControlRepo.get_run_by_id(run_id)
        if not run:
            raise HTTPException(status_code=404, detail="Run not found")

        return run

    except Exception as e:
        logger.error(f"Failed to get run status {run_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status")
async def get_active_runs() -> List[AnalysisRun]:
    """Get status of all active runs"""
    try:
        return AnalysisControlRepo.get_active_runs()
    except Exception as e:
        logger.error(f"Failed to get active runs: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/history")
async def get_run_history(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100)
) -> dict:
    """Get paginated run history"""
    try:
        offset = (page - 1) * limit
        runs = AnalysisControlRepo.get_recent_runs(limit=limit, offset=offset)

        return {
            "runs": runs,
            "page": page,
            "limit": limit,
            "has_more": len(runs) == limit
        }

    except Exception as e:
        logger.error(f"Failed to get run history: {e}")
        raise HTTPException(status_code=500, detail=str(e))

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
    limit: int = Query(50, ge=1, le=1000),
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
async def get_available_feeds() -> List[dict]:
    """Get available feeds for selection"""
    from sqlmodel import Session, text
    from app.database import engine

    try:
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

            return feeds

    except Exception as e:
        logger.error(f"Failed to get feeds: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stats")
async def get_analysis_stats() -> dict:
    """Get overall analysis statistics"""
    from app.repositories.analysis import AnalysisRepo

    try:
        stats = AnalysisRepo.get_analysis_stats()
        pending_count = AnalysisRepo.count_pending_analysis()

        # Calculate coverage metrics
        total_items = stats.get("total_analyzed", 0) + pending_count
        coverage = stats.get("total_analyzed", 0) / max(total_items, 1)

        return {
            "total_items": total_items,
            "analyzed_items": stats.get("total_analyzed", 0),
            "pending_items": pending_count,
            "coverage_percent": round(coverage * 100, 1),
            "sentiment_distribution": stats.get("sentiment_distribution", {}),
            "avg_impact": stats.get("avg_impact", 0.0),
            "avg_urgency": stats.get("avg_urgency", 0.0)
        }

    except Exception as e:
        logger.error(f"Failed to get analysis stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))