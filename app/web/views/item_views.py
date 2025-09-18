from fastapi import APIRouter, Depends, Query
from fastapi.responses import HTMLResponse
from sqlmodel import Session, select
from typing import Optional
import logging

from app.database import get_session
from app.models import Item, Feed, FeedCategory

router = APIRouter(tags=["htmx-items"])
logger = logging.getLogger(__name__)

@router.get("/items-list", response_class=HTMLResponse)
def get_items_list(
    session: Session = Depends(get_session),
    category_id: Optional[str] = None,
    feed_id: Optional[str] = None,
    search: Optional[str] = None,
    since_hours: Optional[str] = None,
    skip: int = 0,
    limit: int = 20
):
    from datetime import datetime, timedelta
    from sqlmodel import or_

    query = select(Item, Feed).join(Feed)

    # Convert string parameters to int, handle empty strings
    try:
        category_id_int = int(category_id) if category_id and category_id.strip() else None
    except ValueError:
        category_id_int = None

    try:
        feed_id_int = int(feed_id) if feed_id and feed_id.strip() else None
    except ValueError:
        feed_id_int = None

    try:
        since_hours_int = int(since_hours) if since_hours and since_hours.strip() else None
    except ValueError:
        since_hours_int = None

    if category_id_int:
        query = query.join(FeedCategory).where(FeedCategory.category_id == category_id_int)

    if feed_id_int:
        query = query.where(Item.feed_id == feed_id_int)

    if since_hours_int:
        since_time = datetime.utcnow() - timedelta(hours=since_hours_int)
        query = query.where(Item.created_at >= since_time)

    if search:
        search_term = f"%{search}%"
        query = query.where(
            or_(
                Item.title.contains(search_term),
                Item.description.contains(search_term)
            )
        )

    # Order by published date first (actual article date), then by created_at (when added to our system)
    # This ensures articles are sorted by their real publication date, not when we fetched them
    from sqlalchemy import desc, case
    query = query.order_by(
        desc(case(
            (Item.published.is_(None), Item.created_at),
            else_=Item.published
        ))
    ).offset(skip).limit(limit)
    results = session.exec(query).all()

    html = ""
    for item, feed in results:
        published_date = item.published.strftime("%d.%m.%Y %H:%M") if item.published else item.created_at.strftime("%d.%m.%Y %H:%M")
        description = item.description[:200] + "..." if item.description and len(item.description) > 200 else item.description or ""

        # Clean and escape content
        clean_title = item.title.replace('"', '&quot;') if item.title else 'Untitled'
        clean_description = description.replace('"', '&quot;') if description else ''
        feed_name = (feed.title or feed.url[:30] + "...") if feed else 'Unknown Feed'

        html += f"""
        <div class="card mb-3 shadow-sm">
            <div class="card-body">
                <h5 class="card-title mb-2">
                    <a href="{item.link}" target="_blank" class="text-decoration-none text-primary">
                        {clean_title}
                    </a>
                </h5>
                <div class="d-flex flex-wrap gap-3 text-muted small mb-2">
                    <span><i class="bi bi-calendar me-1"></i>{published_date}</span>
                    <span><i class="bi bi-rss me-1"></i>{feed_name}</span>
                    {f'<span><i class="bi bi-person me-1"></i>{item.author}</span>' if item.author else ''}
                </div>
                {f'<p class="card-text text-body-secondary">{clean_description}</p>' if clean_description else ''}
            </div>
        </div>
        """

    if not html:
        html = '<div class="alert alert-info">No articles found.</div>'

    return html