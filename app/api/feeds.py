from fastapi import APIRouter, Depends, HTTPException, Query, Form, Response
from fastapi.responses import HTMLResponse
from sqlmodel import Session
from typing import List, Optional, Dict, Any
from app.core.logging_config import get_logger
from app.database import get_session
from app.models.feeds import Source, FeedCategory
from app.schemas import FeedCreate, FeedUpdate, FeedResponse
from app.services.domain.feed_service import FeedService
from app.services.auto_analysis_service import AutoAnalysisService
from app.dependencies import get_feed_service

router = APIRouter(prefix="/feeds", tags=["feeds"])
logger = get_logger(__name__)


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
    source_name: Optional[str] = Form(None),
    category_id: Optional[int] = Form(None),
    categories: Optional[list[int]] = Form(None),
    auto_analyze_enabled: Optional[str] = Form(None),
    feed_service: FeedService = Depends(get_feed_service),
    session: Session = Depends(get_session)
):
    from app.models import SourceType
    from sqlmodel import select

    # Find or create source by name
    source_id = None
    if source_name:
        existing_source = session.exec(
            select(Source).where(Source.name == source_name)
        ).first()
        if existing_source:
            source_id = existing_source.id
        else:
            new_source = Source(name=source_name, type=SourceType.RSS)
            session.add(new_source)
            session.commit()
            session.refresh(new_source)
            source_id = new_source.id
    else:
        default_source = session.exec(
            select(Source).where(Source.type == SourceType.RSS)
        ).first()
        if not default_source:
            raise HTTPException(status_code=400, detail="No source specified and no default RSS source available")
        source_id = default_source.id

    # Handle categories - support both single category_id and multiple categories
    category_ids = []
    if categories:
        category_ids = categories
    elif category_id and category_id > 0:
        category_ids = [category_id]

    # Handle auto_analyze_enabled checkbox
    auto_analyze = auto_analyze_enabled == "true" if auto_analyze_enabled else False

    # Create feed data
    feed_data = FeedCreate(
        url=url,
        title=title,
        description=description,
        fetch_interval_minutes=fetch_interval_minutes,
        source_id=source_id,
        category_ids=category_ids,
        auto_analyze_enabled=auto_analyze
    )

    result = feed_service.create(feed_data)

    if not result.success:
        if "already exists" in result.error:
            raise HTTPException(status_code=409, detail=result.error)
        elif "not found" in result.error:
            raise HTTPException(status_code=404, detail=result.error)
        raise HTTPException(status_code=400, detail=result.error)

    # Return updated feed list as HTML
    from app.web.components.feed_components import get_feeds_list
    html_content = get_feeds_list(session, category_id=None, status=None, auto_analysis_only=None)

    return HTMLResponse(
        content=html_content,
        headers={
            "HX-Trigger": "closeModal"
        }
    )

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
    url: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    source_id: Optional[int] = Form(None),
    fetch_interval_minutes: Optional[int] = Form(None),
    status: Optional[str] = Form(None),
    categories: Optional[list[int]] = Form(None),
    auto_analyze_enabled: Optional[str] = Form(None),
    auto_analysis_only: Optional[str] = Form(None),
    scrape_full_content: Optional[str] = Form(None),
    scrape_method: Optional[str] = Form(None),
    session: Session = Depends(get_session)
):

    # Build update data - only include fields that FeedUpdate accepts
    update_data = {}
    if title is not None:
        update_data['title'] = title
    # Note: url and source_id are not in FeedUpdate schema, don't include them
    if description is not None:
        update_data['description'] = description
    if fetch_interval_minutes is not None:
        update_data['fetch_interval_minutes'] = fetch_interval_minutes
    if status is not None:
        from app.models import FeedStatus
        update_data['status'] = FeedStatus(status)

    # Always explicitly set auto_analyze_enabled based on checkbox value
    if auto_analyze_enabled is not None:
        update_data['auto_analyze_enabled'] = auto_analyze_enabled == "true"
    else:
        # Checkbox unchecked = False
        update_data['auto_analyze_enabled'] = False

    # Handle scraper settings - checkbox and select
    if scrape_full_content is not None:
        update_data['scrape_full_content'] = scrape_full_content == "on"
    else:
        # Checkbox unchecked = False
        update_data['scrape_full_content'] = False

    if scrape_method is not None:
        update_data['scrape_method'] = scrape_method

    # Handle category assignment
    if categories is not None:
        update_data['category_ids'] = categories

    feed_update = FeedUpdate(**update_data)
    feed_service = FeedService(session)
    result = feed_service.update(feed_id, feed_update)

    if not result.success:
        if "not found" in result.error:
            raise HTTPException(status_code=404, detail=result.error)
        raise HTTPException(status_code=400, detail=result.error)

    # Return updated feed list as HTML
    from app.web.components.feed_components import get_feeds_list
    html_content = get_feeds_list(session, category_id=None, status=None, auto_analysis_only=auto_analysis_only)

    # Return response with header to close modal
    return HTMLResponse(
        content=html_content,
        headers={
            "HX-Trigger": "closeModal"
        }
    )

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
    from app.web.components.feed_components import get_feeds_list
    return get_feeds_list(session, category_id=None, status=None, auto_analysis_only=None)


@router.post("/{feed_id}/toggle-auto-analysis")
def toggle_auto_analysis(
    feed_id: int,
    enabled: bool = Query(..., description="Enable or disable auto-analysis"),
    session: Session = Depends(get_session)
):
    """Toggle auto-analysis for a feed"""
    from app.models import Feed

    feed = session.get(Feed, feed_id)
    if not feed:
        raise HTTPException(status_code=404, detail=f"Feed {feed_id} not found")

    feed.auto_analyze_enabled = enabled
    session.add(feed)
    session.commit()
    session.refresh(feed)

    logger.info(f"Auto-analysis {'enabled' if enabled else 'disabled'} for feed {feed_id}")

    return {
        "success": True,
        "feed_id": feed_id,
        "auto_analyze_enabled": feed.auto_analyze_enabled,
        "message": f"Auto-analysis {'enabled' if enabled else 'disabled'} for feed '{feed.title}'"
    }


@router.get("/{feed_id}/auto-analysis-status")
def get_auto_analysis_status(
    feed_id: int,
    session: Session = Depends(get_session)
):
    """Get auto-analysis status and statistics for a feed"""
    from app.models import Feed

    feed = session.get(Feed, feed_id)
    if not feed:
        raise HTTPException(status_code=404, detail=f"Feed {feed_id} not found")

    auto_analysis_service = AutoAnalysisService()
    stats = auto_analysis_service.get_auto_analysis_stats(feed_id)

    return {
        "success": True,
        "feed_id": feed_id,
        "feed_title": feed.title,
        "auto_analyze_enabled": feed.auto_analyze_enabled,
        "stats": stats
    }