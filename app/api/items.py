from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select, and_, or_
from sqlalchemy import desc, case
from typing import List, Optional
from datetime import datetime, timedelta
from app.database import get_session
from app.models import Item, Feed, Category, FeedCategory
# from app.schemas import ItemResponse
# TODO: Fix schema imports
from typing import Any
ItemResponse = Any
from app.repositories.items import ItemsRepo

router = APIRouter(prefix="/items", tags=["items"])

@router.get("/", response_model=List[ItemResponse])
def list_items(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    category_id: Optional[int] = None,
    feed_id: Optional[int] = None,
    since_hours: Optional[int] = Query(None, ge=1),
    search: Optional[str] = None,
    # Analysis filters
    impact_min: Optional[float] = Query(None, ge=0.0, le=1.0, description="Minimum impact score (0-1)"),
    sentiment: Optional[str] = Query(None, regex="^(positive|neutral|negative)$", description="Sentiment filter"),
    urgency_min: Optional[float] = Query(None, ge=0.0, le=1.0, description="Minimum urgency score (0-1)"),
    session: Session = Depends(get_session)
):
    query = select(Item)

    if category_id:
        query = query.join(Feed).join(FeedCategory).where(FeedCategory.category_id == category_id)

    if feed_id:
        query = query.where(Item.feed_id == feed_id)

    if since_hours:
        since_time = datetime.utcnow() - timedelta(hours=since_hours)
        query = query.where(Item.created_at >= since_time)

    if search:
        search_term = f"%{search}%"
        query = query.where(
            or_(
                Item.title.contains(search_term),
                Item.description.contains(search_term),
                Item.content.contains(search_term)
            )
        )

    # Order by published date first (actual article date), then by created_at (when added to our system)
    # This ensures articles are sorted by their real publication date, not when we fetched them
    query = query.order_by(
        desc(case(
            (Item.published.is_(None), Item.created_at),
            else_=Item.published
        ))
    ).offset(skip).limit(limit)
    items = session.exec(query).all()
    return items

@router.get("/analyzed", response_model=List[dict])
def list_analyzed_items(
    impact_min: Optional[float] = Query(None, ge=0.0, le=1.0, description="Minimum impact score (0-1)"),
    sentiment: Optional[str] = Query(None, regex="^(positive|neutral|negative)$", description="Sentiment filter"),
    urgency_min: Optional[float] = Query(None, ge=0.0, le=1.0, description="Minimum urgency score (0-1)"),
    limit: int = Query(50, ge=1, le=500, description="Maximum items to return")
):
    """Get items with analysis data, optionally filtered by impact, sentiment, or urgency"""
    try:
        items = ItemsRepo.query_with_analysis(
            impact_min=impact_min,
            sentiment=sentiment,
            urgency_min=urgency_min,
            limit=limit
        )
        return items
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
def get_item(item_id: int, session: Session = Depends(get_session)):
    item = session.get(Item, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return item

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