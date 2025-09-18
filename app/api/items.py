from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select, and_, or_
from sqlalchemy import desc, case
from typing import List, Optional
from datetime import datetime, timedelta
from app.database import get_session
from app.models import Item, Feed, Category, FeedCategory
from app.schemas import ItemResponse

router = APIRouter(prefix="/items", tags=["items"])

@router.get("/", response_model=List[ItemResponse])
def list_items(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    category_id: Optional[int] = None,
    feed_id: Optional[int] = None,
    since_hours: Optional[int] = Query(None, ge=1),
    search: Optional[str] = None,
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

@router.get("/{item_id}", response_model=ItemResponse)
def get_item(item_id: int, session: Session = Depends(get_session)):
    item = session.get(Item, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return item