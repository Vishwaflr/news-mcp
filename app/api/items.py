from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
from datetime import datetime, timedelta
from app.db.session import DatabaseSession, get_db_session
from app.repositories.items_repo import ItemsRepository
from app.schemas.items import ItemResponse, ItemQuery

router = APIRouter(prefix="/items", tags=["items"])

@router.get("/", response_model=List[ItemResponse])
async def list_items(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    category_id: Optional[int] = None,
    feed_id: Optional[int] = None,
    since_hours: Optional[int] = Query(None, ge=1),
    search: Optional[str] = None,
    db_session: DatabaseSession = Depends(get_db_session)
):
    """List items with optional filtering."""
    items_repo = ItemsRepository(db_session)

    # Build filter object
    filter_obj = ItemQuery()

    if feed_id:
        filter_obj.feed_ids = [feed_id]

    if category_id:
        filter_obj.category_id = category_id

    if since_hours:
        since_time = datetime.utcnow() - timedelta(hours=since_hours)
        filter_obj.from_date = since_time

    if search:
        filter_obj.search = search

    try:
        items = await items_repo.query(filter_obj, limit=limit, offset=skip)
        return items
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch items: {str(e)}")

@router.get("/analyzed", response_model=List[ItemResponse])
async def list_analyzed_items(
    impact_min: Optional[float] = Query(None, ge=0.0, le=1.0, description="Minimum impact score (0-1)"),
    sentiment: Optional[str] = Query(None, regex="^(positive|neutral|negative)$", description="Sentiment filter"),
    urgency_min: Optional[float] = Query(None, ge=0.0, le=1.0, description="Minimum urgency score (0-1)"),
    limit: int = Query(50, ge=1, le=500, description="Maximum items to return"),
    db_session: DatabaseSession = Depends(get_db_session)
):
    """Get items with analysis data, optionally filtered by impact, sentiment, or urgency"""
    items_repo = ItemsRepository(db_session)

    # Build filter object for analyzed items
    filter_obj = ItemQuery()

    try:
        # Get items with analysis filters - this needs to be implemented in ItemsRepository
        # For now, get all items and then we'll extend the repository
        items = await items_repo.query(filter_obj, limit=limit, offset=0)

        # Filter by analysis criteria (temporary implementation)
        filtered_items = []
        for item in items:
            if hasattr(item, 'analysis') and item.analysis:
                if impact_min is not None and (not hasattr(item.analysis, 'impact_score') or item.analysis.impact_score < impact_min):
                    continue
                if sentiment is not None and (not hasattr(item.analysis, 'sentiment_label') or item.analysis.sentiment_label != sentiment):
                    continue
                if urgency_min is not None and (not hasattr(item.analysis, 'urgency_score') or item.analysis.urgency_score < urgency_min):
                    continue
                filtered_items.append(item)

        return filtered_items[:limit]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch analyzed items: {str(e)}")

@router.get("/analysis/stats", response_model=dict)
def get_analysis_stats():
    """Get analysis statistics"""
    try:
        from app.repositories.analysis import AnalysisRepo
        stats = AnalysisRepo.get_analysis_stats()
        pending_count = AnalysisRepo.count_pending_analysis()
        stats["pending_analysis"] = pending_count
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch analysis stats: {str(e)}")

@router.get("/{item_id}", response_model=ItemResponse)
async def get_item(item_id: int, db_session: DatabaseSession = Depends(get_db_session)):
    """Get a single item by ID."""
    items_repo = ItemsRepository(db_session)
    try:
        item = await items_repo.get_by_id(item_id)
        if not item:
            raise HTTPException(status_code=404, detail="Item not found")
        return item
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch item: {str(e)}")

@router.get("/{item_id}/analysis", response_model=dict)
def get_item_analysis(item_id: int):
    """Get analysis data for a specific item"""
    try:
        from app.repositories.analysis import AnalysisRepo
        analysis = AnalysisRepo.get_by_item_id(item_id)
        if not analysis:
            raise HTTPException(status_code=404, detail="Analysis not found for this item")
        return analysis
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch item analysis: {str(e)}")