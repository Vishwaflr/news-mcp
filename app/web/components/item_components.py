"""Item management HTMX components."""

from fastapi import APIRouter, Depends, Query
from fastapi.responses import HTMLResponse
from sqlmodel import Session, text
from typing import Optional
from datetime import datetime, timedelta
import logging

from app.database import get_session
from .base_component import BaseComponent

router = APIRouter(tags=["htmx-items"])
logger = logging.getLogger(__name__)


class ItemComponent(BaseComponent):
    """Component for item-related HTMX endpoints."""

    @staticmethod
    def build_item_card(item_data: dict) -> str:
        """Build HTML for a single item card."""
        published_date = ItemComponent.format_date(item_data.get('published')) if item_data.get('published') else ItemComponent.format_date(item_data.get('created_at'))
        description = ItemComponent.truncate_text(item_data.get('description', ''), 200)

        # Clean and escape content
        clean_title = ItemComponent.clean_html_attr(item_data.get('title', 'Untitled'))
        clean_description = ItemComponent.clean_html_attr(description)
        feed_name = item_data.get('feed_title', item_data.get('feed_url', 'Unknown Feed')[:30] + "...")

        author_info = f'<span><i class="bi bi-person me-1"></i>{item_data.get("author")}</span>' if item_data.get('author') else ''

        return f'''
        <div class="card mb-3 shadow-sm">
            <div class="card-body">
                <h5 class="card-title mb-2">
                    <a href="{item_data.get('link', '#')}" target="_blank" class="text-decoration-none text-primary">
                        {clean_title}
                    </a>
                </h5>
                <div class="d-flex flex-wrap gap-3 text-muted small mb-2">
                    <span><i class="bi bi-calendar me-1"></i>{published_date}</span>
                    <span><i class="bi bi-rss me-1"></i>{feed_name}</span>
                    {author_info}
                </div>
                {f'<p class="card-text text-body-secondary">{clean_description}</p>' if clean_description else ''}
            </div>
        </div>
        '''


@router.get("/items-list", response_class=HTMLResponse)
def get_items_list(
    session: Session = Depends(get_session),
    category_id: Optional[int] = Query(None),
    feed_id: Optional[int] = Query(None),
    search: Optional[str] = Query(None),
    since_hours: Optional[int] = Query(None),
    skip: int = 0,
    limit: int = 20
):
    """Get filtered HTML list of items."""
    try:
        # Use raw SQL to avoid SQLModel issues
        where_clauses = []
        params = {}

        if category_id and category_id > 0:
            where_clauses.append("""
                i.feed_id IN (
                    SELECT feed_id FROM feed_categories WHERE category_id = :category_id
                )
            """)
            params['category_id'] = category_id

        if feed_id and feed_id > 0:
            where_clauses.append("i.feed_id = :feed_id")
            params['feed_id'] = feed_id

        if since_hours and since_hours > 0:
            since_time = datetime.utcnow() - timedelta(hours=since_hours)
            where_clauses.append("i.created_at >= :since_time")
            params['since_time'] = since_time

        if search:
            where_clauses.append("(i.title ILIKE :search OR i.description ILIKE :search)")
            params['search'] = f'%{search}%'

        where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

        sql = f"""
            SELECT
                i.id, i.title, i.link, i.description, i.author, i.published, i.created_at,
                f.id as feed_id, f.title as feed_title, f.url as feed_url
            FROM items i
            JOIN feeds f ON i.feed_id = f.id
            {where_sql}
            ORDER BY COALESCE(i.published, i.created_at) DESC
            LIMIT :limit OFFSET :skip
        """

        params['limit'] = limit
        params['skip'] = skip

        # Execute raw SQL
        result = session.execute(text(sql), params)
        items = result.fetchall()

        # Build HTML
        html = ""
        for row in items:
            item_data = {
                'id': row[0],
                'title': row[1],
                'link': row[2],
                'description': row[3],
                'author': row[4],
                'published': row[5],
                'created_at': row[6],
                'feed_id': row[7],
                'feed_title': row[8],
                'feed_url': row[9]
            }
            html += ItemComponent.build_item_card(item_data)

        if not html:
            html = BaseComponent.alert_box('No articles found.', 'info')

        return html

    except Exception as e:
        logger.error(f"Error in items-list: {e}")
        return BaseComponent.alert_box(f'Error loading articles: {str(e)}', 'danger')