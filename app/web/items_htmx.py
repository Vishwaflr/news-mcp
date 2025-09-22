from fastapi import APIRouter, Depends, Query
from fastapi.responses import HTMLResponse
from sqlmodel import Session, select
from typing import Optional
import logging

from app.database import get_session
from app.models import Item, Feed, Category, FeedCategory

router = APIRouter(tags=["htmx-items"])
logger = logging.getLogger(__name__)

# feeds-options and categories-options are already defined in htmx.router
# Only define the missing items-list route here

@router.get("/items-list", response_class=HTMLResponse)
def get_items_list(
    session: Session = Depends(get_session),
    feed_id: Optional[int] = Query(None),
    category_id: Optional[int] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100)
):
    """Get items list with pagination and filters"""
    try:
        # Build base query
        query = select(Item, Feed).join(Feed, Item.feed_id == Feed.id)

        # Apply filters
        if feed_id:
            query = query.where(Item.feed_id == feed_id)

        if category_id:
            query = query.join(FeedCategory, FeedCategory.feed_id == Feed.id).where(FeedCategory.category_id == category_id)

        # Add ordering and pagination
        query = query.order_by(Item.published_at.desc())
        offset = (page - 1) * limit
        query = query.offset(offset).limit(limit)

        results = session.exec(query).all()

        if not results:
            return '<div class="alert alert-info">No articles found.</div>'

        html = ""
        for item, feed in results:
            # Format published date
            pub_date = item.published_at.strftime("%d.%m.%Y %H:%M") if item.published_at else "Unknown"

            # Truncate content for preview
            content_preview = ""
            if item.content:
                content_preview = item.content[:200] + "..." if len(item.content) > 200 else item.content
            elif item.description:
                content_preview = item.description[:200] + "..." if len(item.description) > 200 else item.description

            html += f'''
            <div class="card mb-3">
                <div class="card-body">
                    <div class="d-flex justify-content-between align-items-start mb-2">
                        <h5 class="card-title mb-1">
                            <a href="{item.url}" target="_blank" class="text-decoration-none">{item.title}</a>
                        </h5>
                        <small class="text-muted">{pub_date}</small>
                    </div>
                    <p class="card-text text-muted small mb-2">
                        <strong>Feed:</strong> {feed.title or feed.url}
                    </p>
                    {f'<p class="card-text">{content_preview}</p>' if content_preview else ''}
                    <div class="d-flex justify-content-between align-items-center">
                        <small class="text-muted">
                            <i class="bi bi-calendar"></i> {pub_date}
                        </small>
                        <div>
                            <a href="{item.url}" target="_blank" class="btn btn-sm btn-outline-primary">
                                <i class="bi bi-box-arrow-up-right"></i> Read
                            </a>
                        </div>
                    </div>
                </div>
            </div>
            '''

        # Add pagination controls
        count_query = select(Item)
        if feed_id:
            count_query = count_query.where(Item.feed_id == feed_id)
        if category_id:
            count_query = count_query.join(Feed, Item.feed_id == Feed.id).join(FeedCategory, FeedCategory.feed_id == Feed.id).where(FeedCategory.category_id == category_id)

        total_count = len(session.exec(count_query).all())
        total_pages = (total_count + limit - 1) // limit

        if total_pages > 1:
            pagination = f'''
            <div class="d-flex justify-content-center mt-3">
                <nav>
                    <ul class="pagination">
            '''

            # Previous button
            if page > 1:
                pagination += f'''
                    <li class="page-item">
                        <a class="page-link"
                           hx-get="/htmx/items-list?page={page-1}&limit={limit}{f'&feed_id={feed_id}' if feed_id else ''}{f'&category_id={category_id}' if category_id else ''}"
                           hx-target="#items-list">Previous</a>
                    </li>
                '''

            # Page numbers (show max 5 pages around current)
            start_page = max(1, page - 2)
            end_page = min(total_pages, page + 2)

            for p in range(start_page, end_page + 1):
                active = "active" if p == page else ""
                pagination += f'''
                    <li class="page-item {active}">
                        <a class="page-link"
                           hx-get="/htmx/items-list?page={p}&limit={limit}{f'&feed_id={feed_id}' if feed_id else ''}{f'&category_id={category_id}' if category_id else ''}"
                           hx-target="#items-list">{p}</a>
                    </li>
                '''

            # Next button
            if page < total_pages:
                pagination += f'''
                    <li class="page-item">
                        <a class="page-link"
                           hx-get="/htmx/items-list?page={page+1}&limit={limit}{f'&feed_id={feed_id}' if feed_id else ''}{f'&category_id={category_id}' if category_id else ''}"
                           hx-target="#items-list">Next</a>
                    </li>
                '''

            pagination += '''
                    </ul>
                </nav>
            </div>
            '''

            html += pagination

        return html

    except Exception as e:
        logger.error(f"Error loading items list: {e}")
        return f'<div class="alert alert-danger">Error loading articles: {str(e)}</div>'