from fastapi import APIRouter, Depends, HTTPException, Query, Form
from fastapi.responses import HTMLResponse
from sqlmodel import Session
from typing import List, Optional, Dict, Any
import logging
from app.database import get_session
from app.models.feeds import Source, FeedCategory
from app.schemas import FeedCreate, FeedUpdate, FeedResponse
from app.services.domain.feed_service import FeedService
from app.dependencies import get_feed_service

router = APIRouter(prefix="/feeds", tags=["feeds"])
logger = logging.getLogger(__name__)


@router.get("/", response_model=List[FeedResponse])
def list_feeds(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    category_id: Optional[int] = None,
    status: Optional[str] = None,
    feed_service: FeedService = Depends(get_feed_service)
):
    filters = {}
    if category_id:
        filters['category_id'] = category_id
    if status:
        filters['status'] = status

    result = feed_service.list(skip=skip, limit=limit, filters=filters)
    if not result.success:
        raise HTTPException(status_code=500, detail=result.error)
    return result.data

@router.get("/{feed_id}", response_model=FeedResponse)
def get_feed(feed_id: int, feed_service: FeedService = Depends(get_feed_service)):
    result = feed_service.get_by_id(feed_id)
    if not result.success:
        if "not found" in result.error:
            raise HTTPException(status_code=404, detail=result.error)
        raise HTTPException(status_code=500, detail=result.error)
    return result.data

@router.post("/json", response_model=FeedResponse)
def create_feed_json(
    feed_data: FeedCreate,
    feed_service: FeedService = Depends(get_feed_service),
    session: Session = Depends(get_session)
):
    """Create a new feed via JSON API"""
    # If no source_id provided, use the first available RSS source
    if feed_data.source_id is None:
        from app.models import SourceType
        from sqlmodel import select
        default_source = session.exec(
            select(Source).where(Source.type == SourceType.RSS)
        ).first()
        if not default_source:
            raise HTTPException(status_code=400, detail="No RSS source available and none specified")
        feed_data.source_id = default_source.id

    result = feed_service.create(feed_data)

    if not result.success:
        if "already exists" in result.error:
            raise HTTPException(status_code=409, detail=result.error)
        elif "not found" in result.error:
            raise HTTPException(status_code=404, detail=result.error)
        raise HTTPException(status_code=400, detail=result.error)

    return result.data

@router.post("/")
def create_feed(
    url: str = Form(...),
    title: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    fetch_interval_minutes: int = Form(60),
    source_id: Optional[int] = Form(None),
    category_id: Optional[int] = Form(None),
    feed_service: FeedService = Depends(get_feed_service),
    session: Session = Depends(get_session)
):
    # If no source_id provided, use the first available RSS source
    if source_id is None:
        from app.models import SourceType
        from sqlmodel import select
        default_source = session.exec(
            select(Source).where(Source.type == SourceType.RSS)
        ).first()
        if not default_source:
            raise HTTPException(status_code=400, detail="No RSS source available and none specified")
        source_id = default_source.id

    # Create feed data
    feed_data = FeedCreate(
        url=url,
        title=title,
        description=description,
        fetch_interval_minutes=fetch_interval_minutes,
        source_id=source_id,
        category_ids=[category_id] if category_id and category_id > 0 else []
    )

    result = feed_service.create(feed_data)

    if not result.success:
        if "already exists" in result.error:
            raise HTTPException(status_code=409, detail=result.error)
        elif "not found" in result.error:
            raise HTTPException(status_code=404, detail=result.error)
        raise HTTPException(status_code=400, detail=result.error)

    # Return updated feed list as HTML
    from app.api.htmx import get_feeds_list
    return get_feeds_list(session)

@router.put("/{feed_id}", response_model=FeedResponse)
def update_feed(
    feed_id: int,
    feed_update: FeedUpdate,
    feed_service: FeedService = Depends(get_feed_service)
):
    result = feed_service.update(feed_id, feed_update)

    if not result.success:
        if "not found" in result.error:
            raise HTTPException(status_code=404, detail=result.error)
        raise HTTPException(status_code=400, detail=result.error)

    return result.data

@router.put("/{feed_id}/form", response_class=HTMLResponse)
def update_feed_form(
    feed_id: int,
    title: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    fetch_interval_minutes: Optional[int] = Form(None),
    status: Optional[str] = Form(None),
    category_id: Optional[int] = Form(None),
    session: Session = Depends(get_session)
):
    # Build update data
    update_data = {}
    if title is not None:
        update_data['title'] = title
    if description is not None:
        update_data['description'] = description
    if fetch_interval_minutes is not None:
        update_data['fetch_interval_minutes'] = fetch_interval_minutes
    if status is not None:
        from app.models import FeedStatus
        update_data['status'] = FeedStatus(status)

    # Handle category assignment
    if category_id is not None:
        category_ids = [category_id] if category_id > 0 else []
        update_data['category_ids'] = category_ids

    feed_update = FeedUpdate(**update_data)
    feed_service = FeedService(session)
    result = feed_service.update(feed_id, feed_update)

    if not result.success:
        if "not found" in result.error:
            raise HTTPException(status_code=404, detail=result.error)
        raise HTTPException(status_code=400, detail=result.error)

    # Return updated feed list as HTML
    from app.api.htmx import get_feeds_list
    return get_feeds_list(session)

@router.post("/{feed_id}/fetch")
def fetch_feed_now(feed_id: int, session: Session = Depends(get_session)):
    """Manually trigger an immediate fetch for a specific feed"""
    feed_service = FeedService(session)
    result = feed_service.trigger_immediate_fetch(feed_id)

    if not result.success:
        if "not found" in result.error:
            raise HTTPException(status_code=404, detail=result.error)
        raise HTTPException(status_code=500, detail=result.error)

    success, items_count = result.data
    if success:
        return {"success": True, "message": f"Feed fetched successfully, {items_count} new items loaded"}
    else:
        return {"success": False, "message": "Feed fetch failed"}

@router.delete("/{feed_id}", response_class=HTMLResponse)
def delete_feed(feed_id: int, session: Session = Depends(get_session)):
    feed_service = FeedService(session)
    result = feed_service.delete(feed_id)

    if not result.success:
        if "not found" in result.error:
            raise HTTPException(status_code=404, detail=result.error)
        raise HTTPException(status_code=500, detail=result.error)

    # Return updated feed list as HTML
    from app.api.htmx import get_feeds_list
    return get_feeds_list(session)