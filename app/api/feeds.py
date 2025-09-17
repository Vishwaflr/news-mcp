from fastapi import APIRouter, Depends, HTTPException, Query, Form
from fastapi.responses import HTMLResponse
from sqlmodel import Session, select
from typing import List, Optional
from app.database import get_session
from app.models import Feed, Source, Category, FeedCategory, Item, FeedHealth, FetchLog
from app.schemas import FeedCreate, FeedUpdate, FeedResponse

router = APIRouter(prefix="/feeds", tags=["feeds"])

@router.get("/", response_model=List[FeedResponse])
def list_feeds(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    category_id: Optional[int] = None,
    status: Optional[str] = None,
    session: Session = Depends(get_session)
):
    query = select(Feed)

    if category_id:
        query = query.join(FeedCategory).where(FeedCategory.category_id == category_id)

    if status:
        query = query.where(Feed.status == status)

    query = query.offset(skip).limit(limit)
    feeds = session.exec(query).all()
    return feeds

@router.get("/{feed_id}", response_model=FeedResponse)
def get_feed(feed_id: int, session: Session = Depends(get_session)):
    feed = session.get(Feed, feed_id)
    if not feed:
        raise HTTPException(status_code=404, detail="Feed not found")
    return feed

@router.post("/")
def create_feed(
    url: str = Form(...),
    title: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    fetch_interval_minutes: int = Form(60),
    source_id: Optional[int] = Form(None),
    session: Session = Depends(get_session)
):
    # If no source_id provided, use the first available RSS source
    if source_id is None:
        from app.models import SourceType
        default_source = session.exec(
            select(Source).where(Source.type == SourceType.RSS)
        ).first()
        if not default_source:
            raise HTTPException(status_code=400, detail="No RSS source available and none specified")
        source_id = default_source.id

    source = session.get(Source, source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    existing_feed = session.exec(select(Feed).where(Feed.url == url)).first()
    if existing_feed:
        raise HTTPException(status_code=409, detail="Feed URL already exists")

    db_feed = Feed(
        url=url,
        title=title,
        description=description,
        fetch_interval_minutes=fetch_interval_minutes,
        source_id=source_id
    )
    session.add(db_feed)
    session.commit()
    session.refresh(db_feed)

    # Return updated feed list as HTML
    from app.api.htmx import get_feeds_list
    return get_feeds_list(session)

@router.put("/{feed_id}", response_model=FeedResponse)
def update_feed(feed_id: int, feed_update: FeedUpdate, session: Session = Depends(get_session)):
    feed = session.get(Feed, feed_id)
    if not feed:
        raise HTTPException(status_code=404, detail="Feed not found")

    update_data = feed_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(feed, field, value)

    session.add(feed)
    session.commit()
    session.refresh(feed)
    return feed

@router.put("/{feed_id}/form", response_class=HTMLResponse)
def update_feed_form(
    feed_id: int,
    title: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    fetch_interval_minutes: Optional[int] = Form(None),
    status: Optional[str] = Form(None),
    session: Session = Depends(get_session)
):
    feed = session.get(Feed, feed_id)
    if not feed:
        raise HTTPException(status_code=404, detail="Feed not found")

    # Update only provided fields
    if title is not None:
        feed.title = title
    if description is not None:
        feed.description = description
    if fetch_interval_minutes is not None:
        feed.fetch_interval_minutes = fetch_interval_minutes
    if status is not None:
        from app.models import FeedStatus
        feed.status = FeedStatus(status)

    session.add(feed)
    session.commit()
    session.refresh(feed)

    # Return updated feed list as HTML
    from app.api.htmx import get_feeds_list
    return get_feeds_list(session)

@router.delete("/{feed_id}", response_class=HTMLResponse)
def delete_feed(feed_id: int, session: Session = Depends(get_session)):
    feed = session.get(Feed, feed_id)
    if not feed:
        raise HTTPException(status_code=404, detail="Feed not found")

    try:
        # Delete associated items first if any
        items_query = select(Item).where(Item.feed_id == feed_id)
        items = session.exec(items_query).all()
        for item in items:
            session.delete(item)

        # Delete feed categories relationships
        from app.models import FeedCategory
        feed_cats_query = select(FeedCategory).where(FeedCategory.feed_id == feed_id)
        feed_cats = session.exec(feed_cats_query).all()
        for fc in feed_cats:
            session.delete(fc)

        # Delete feed health records
        from app.models import FeedHealth
        health_query = select(FeedHealth).where(FeedHealth.feed_id == feed_id)
        health_records = session.exec(health_query).all()
        for hr in health_records:
            session.delete(hr)

        # Delete fetch log records
        fetch_log_query = select(FetchLog).where(FetchLog.feed_id == feed_id)
        fetch_logs = session.exec(fetch_log_query).all()
        for fl in fetch_logs:
            session.delete(fl)

        # Finally delete the feed
        session.delete(feed)
        session.commit()

    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Error deleting feed: {str(e)}")

    # Return updated feed list as HTML
    from app.api.htmx import get_feeds_list
    return get_feeds_list(session)