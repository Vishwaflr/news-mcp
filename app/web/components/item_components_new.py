"""Refactored Item management HTMX components using Repository pattern."""

from fastapi import APIRouter, Depends, Query
from fastapi.responses import HTMLResponse
from typing import Optional
from datetime import datetime, timedelta
from app.core.logging_config import get_logger

from app.db.session import get_db_session, DatabaseSession
from app.repositories.items_repo import ItemsRepository
from app.schemas.items import ItemQuery
from .base_component import BaseComponent

router = APIRouter(tags=["htmx-items-new"])
logger = get_logger(__name__)


class ItemComponentNew(BaseComponent):
    """Refactored component using Repository pattern."""

    @staticmethod
    def get_items_repository(db_session: DatabaseSession = Depends(get_db_session)) -> ItemsRepository:
        """Dependency injection for items repository."""
        return ItemsRepository(db_session)

    @staticmethod
    def build_item_card(item_data: dict) -> str:
        """Build HTML for a single item card."""
        published_date = ItemComponentNew.format_date(item_data.get('published')) if item_data.get('published') else ItemComponentNew.format_date(item_data.get('created_at'))
        description = ItemComponentNew.truncate_text(item_data.get('description', ''), 200)

        # Clean and escape content
        clean_title = ItemComponentNew.clean_html_attr(item_data.get('title', 'Untitled'))
        clean_description = ItemComponentNew.clean_html_attr(description)
        feed_name = item_data.get('feed_title', item_data.get('feed_url', 'Unknown Feed')[:30] + "...")

        author_info = f'<span><i class="bi bi-person me-1"></i>{item_data.get("author")}</span>' if item_data.get('author') else ''

        # Sentiment analysis display
        sentiment_html = ItemComponentNew.generate_sentiment_display(item_data)

        return f"""
        <div class="card mb-3" id="item-{item_data.get('id')}">
            <div class="card-body">
                <div class="d-flex justify-content-between align-items-start mb-2">
                    <h5 class="card-title mb-1">
                        <a href="{item_data.get('link', '#')}" target="_blank" class="text-decoration-none">
                            {clean_title}
                        </a>
                    </h5>
                    <small class="text-muted flex-shrink-0 ms-2">{published_date}</small>
                </div>

                {sentiment_html}

                <p class="card-text">{clean_description}</p>

                <div class="d-flex justify-content-between align-items-center">
                    <div class="text-muted small">
                        <span><i class="bi bi-rss me-1"></i>{feed_name}</span>
                        {author_info}
                    </div>
                    <div class="btn-group btn-group-sm" role="group">
                        <a href="{item_data.get('link', '#')}" target="_blank" class="btn btn-outline-primary btn-sm">
                            <i class="bi bi-box-arrow-up-right"></i> Read
                        </a>
                    </div>
                </div>
            </div>
        </div>
        """

    @staticmethod
    def generate_sentiment_display(item_data: dict) -> str:
        """Generate HTML for sentiment analysis display."""
        if not item_data.get('sentiment_label'):
            return '<div class="sentiment-analysis mb-2"><span class="badge bg-secondary">No Analysis</span></div>'

        label = item_data.get('sentiment_label', 'neutral')
        score = item_data.get('sentiment_score', 0.0)
        impact = item_data.get('impact_score', 0.0)
        urgency = item_data.get('urgency_score', 0.0)

        # Sentiment icon and color
        if label == 'positive':
            icon = '🟢'
            color = 'success'
        elif label == 'negative':
            icon = '🔴'
            color = 'danger'
        else:
            icon = '⚪'
            color = 'secondary'

        return f"""
        <div class="sentiment-analysis mb-2">
            <div class="d-flex align-items-center gap-2">
                <span class="sentiment-icon">{icon}</span>
                <span class="badge bg-{color}">{score:.1f}</span>
                <span class="badge bg-warning">⚡ {urgency:.1f}</span>
                <span class="badge bg-info">📊 {impact:.1f}</span>
            </div>
        </div>
        """


@router.get("/items-list-new", response_class=HTMLResponse)
async def get_items_list_new(
    feed_id: Optional[int] = Query(None),
    category_id: Optional[int] = Query(None),
    search: Optional[str] = Query(None),
    sentiment: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    items_repo: ItemsRepository = Depends(ItemComponentNew.get_items_repository)
):
    """
    New items list endpoint using Repository pattern.
    This replaces the Raw SQL implementation.
    """
    try:
        # Build query object
        feed_ids = [feed_id] if feed_id else None
        query = ItemQuery(
            feed_ids=feed_ids,
            category_id=category_id,
            search=search,
            sentiment=sentiment,
            sort_by="created_at",
            sort_desc=True
        )

        # Calculate pagination
        offset = (page - 1) * limit

        # Execute query through repository
        items = await items_repo.query(query, limit=limit, offset=offset)

        if not items:
            return '<div class="alert alert-info">No articles found.</div>'

        # Build HTML response
        html_parts = []
        for item in items:
            item_dict = item.dict()
            html_parts.append(ItemComponentNew.build_item_card(item_dict))

        # Add pagination info
        total_count = await items_repo.count(query)
        has_more = (offset + limit) < total_count

        pagination_html = ""
        if has_more:
            next_page = page + 1
            pagination_html = f"""
            <div class="text-center mt-3">
                <button class="btn btn-outline-secondary"
                        hx-get="/htmx/items-list-new?page={next_page}&feed_id={feed_id or ''}&category_id={category_id or ''}&search={search or ''}&sentiment={sentiment or ''}"
                        hx-target="#items-container"
                        hx-swap="beforeend">
                    Load More ({total_count - offset - limit} remaining)
                </button>
            </div>
            """

        return "".join(html_parts) + pagination_html

    except Exception as e:
        logger.error(f"Error in items list: {e}")
        return f'<div class="alert alert-danger">Error loading items: {str(e)}</div>'


@router.get("/items-statistics-new", response_class=HTMLResponse)
async def get_items_statistics_new(
    items_repo: ItemsRepository = Depends(ItemComponentNew.get_items_repository)
):
    """Get items statistics using Repository pattern."""
    try:
        stats = await items_repo.get_statistics()

        return f"""
        <div class="row g-3">
            <div class="col-md-3">
                <div class="card text-center">
                    <div class="card-body">
                        <h5 class="card-title text-primary">{stats.total_count:,}</h5>
                        <p class="card-text">Total Articles</p>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card text-center">
                    <div class="card-body">
                        <h5 class="card-title text-success">{stats.today_count:,}</h5>
                        <p class="card-text">Today</p>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card text-center">
                    <div class="card-body">
                        <h5 class="card-title text-info">{stats.last_24h_count:,}</h5>
                        <p class="card-text">Last 24h</p>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card text-center">
                    <div class="card-body">
                        <h5 class="card-title text-warning">{stats.last_week_count:,}</h5>
                        <p class="card-text">This Week</p>
                    </div>
                </div>
            </div>
        </div>

        <div class="row mt-4">
            <div class="col-md-6">
                <h6>Top Feeds</h6>
                <div class="list-group">
                    {"".join([f'''
                    <div class="list-group-item d-flex justify-content-between align-items-center">
                        {feed['feed_title'][:50]}...
                        <span class="badge bg-primary rounded-pill">{feed['count']}</span>
                    </div>
                    ''' for feed in stats.by_feed[:5]])}
                </div>
            </div>
            <div class="col-md-6">
                <h6>Sentiment Analysis</h6>
                <div class="list-group">
                    {"".join([f'''
                    <div class="list-group-item d-flex justify-content-between align-items-center">
                        {sentiment.title()}
                        <span class="badge bg-secondary rounded-pill">{count}</span>
                    </div>
                    ''' for sentiment, count in stats.by_sentiment.items()])}
                </div>
            </div>
        </div>
        """

    except Exception as e:
        logger.error(f"Error in items statistics: {e}")
        return f'<div class="alert alert-danger">Error loading statistics: {str(e)}</div>'