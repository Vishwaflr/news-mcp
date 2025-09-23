from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse
from sqlmodel import Session, select
from typing import Optional
from app.core.logging_config import get_logger
import time

from app.database import get_session
from app.models import Item, Feed, Category, FeedCategory
from app.utils.feature_flags import is_feature_enabled, record_feature_success, record_feature_error
from app.utils.shadow_compare import shadow_comparer
from app.utils.monitoring import repo_monitor
from app.db.session import get_db_session, DatabaseSession
from app.repositories.items_repo import ItemsRepository
from app.schemas.items import ItemQuery

router = APIRouter(tags=["htmx-items"])
logger = get_logger(__name__)

# feeds-options and categories-options are already defined in htmx.router
# Only define the missing items-list route here

async def _get_items_list_legacy(
    session: Session,
    feed_id: Optional[int] = None,
    category_id: Optional[int] = None,
    page: int = 1,
    limit: int = 20
) -> str:
    """Legacy Raw-SQL implementation for comparison."""
    # Legacy implementation (original code moved here)
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
        logger.error(f"Error loading items list (legacy): {e}")
        return f'<div class="alert alert-danger">Error loading articles: {str(e)}</div>'


async def _get_items_list_repo(
    items_repo: ItemsRepository,
    feed_id: Optional[int] = None,
    category_id: Optional[int] = None,
    page: int = 1,
    limit: int = 20,
    search: Optional[str] = None,
    sentiment: Optional[str] = None
) -> str:
    """New Repository-based implementation."""
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

        # Execute through repository
        with repo_monitor.monitor_query("items", "list", {
            "has_filters": any([feed_id, category_id, search, sentiment]),
            "has_joins": True,
            "limit": limit
        }):
            items = await items_repo.query(query, limit=limit, offset=offset)

        if not items:
            return '<div class="alert alert-info">No articles found.</div>'

        # Build HTML response
        html_parts = []
        for item in items:
            # Format published date
            pub_date = item.published.strftime("%d.%m.%Y %H:%M") if item.published else item.created_at.strftime("%d.%m.%Y %H:%M")

            # Truncate content for preview
            content_preview = ""
            if item.content:
                content_preview = item.content[:200] + "..." if len(item.content) > 200 else item.content
            elif item.description:
                content_preview = item.description[:200] + "..." if len(item.description) > 200 else item.description

            # Sentiment display (temporarily disabled until repository provides analysis data)
            sentiment_html = ""
            if hasattr(item, 'sentiment_label') and item.sentiment_label:
                color = "success" if item.sentiment_label == "positive" else "danger" if item.sentiment_label == "negative" else "secondary"
                icon = "🟢" if item.sentiment_label == "positive" else "🔴" if item.sentiment_label == "negative" else "⚪"
                score = getattr(item, 'sentiment_score', 0) or 0
                impact_score = getattr(item, 'impact_score', None)
                urgency_score = getattr(item, 'urgency_score', None)
                sentiment_html = f'''
                <div class="mb-2">
                    <span class="sentiment-icon">{icon}</span>
                    <span class="badge bg-{color} me-1">{score:.1f}</span>
                    {f'<span class="badge bg-info">📊 {impact_score:.1f}</span>' if impact_score else ''}
                    {f'<span class="badge bg-warning">⚡ {urgency_score}</span>' if urgency_score else ''}
                </div>
                '''

            html_parts.append(f'''
            <div class="card mb-3" id="item-{item.id}">
                <div class="card-body">
                    <div class="d-flex justify-content-between align-items-start mb-2">
                        <h5 class="card-title mb-1">
                            <a href="{item.link}" target="_blank" class="text-decoration-none">{item.title}</a>
                        </h5>
                        <small class="text-muted">{pub_date}</small>
                    </div>

                    {sentiment_html}

                    <p class="card-text text-muted small mb-2">
                        <strong>Feed:</strong> {item.feed_title or item.feed_url or 'Unknown'}
                    </p>
                    {f'<p class="card-text">{content_preview}</p>' if content_preview else ''}
                    <div class="d-flex justify-content-between align-items-center">
                        <small class="text-muted">
                            <i class="bi bi-calendar"></i> {pub_date}
                            {f'<span class="ms-2"><i class="bi bi-person"></i> {item.author}</span>' if item.author else ''}
                        </small>
                        <div>
                            <a href="{item.link}" target="_blank" class="btn btn-sm btn-outline-primary">
                                <i class="bi bi-box-arrow-up-right"></i> Read
                            </a>
                        </div>
                    </div>
                </div>
            </div>
            ''')

        # Add pagination
        total_count = await items_repo.count(query)
        has_more = (offset + limit) < total_count

        if has_more:
            next_page = page + 1
            params = []
            if feed_id:
                params.append(f"feed_id={feed_id}")
            if category_id:
                params.append(f"category_id={category_id}")
            if search:
                params.append(f"search={search}")
            if sentiment:
                params.append(f"sentiment={sentiment}")

            param_string = "&".join(params)
            pagination_html = f'''
            <div class="text-center mt-3">
                <button class="btn btn-outline-secondary"
                        hx-get="/htmx/items-list?page={next_page}&limit={limit}&{param_string}"
                        hx-target="#items-list"
                        hx-swap="beforeend">
                    Load More ({total_count - offset - limit} remaining)
                </button>
            </div>
            '''
            html_parts.append(pagination_html)

        return "".join(html_parts)

    except Exception as e:
        logger.error(f"Error loading items list (repo): {e}")
        return f'<div class="alert alert-danger">Error loading articles: {str(e)}</div>'


@router.get("/items-list", response_class=HTMLResponse)
async def get_items_list(
    request: Request,
    session: Session = Depends(get_session),
    db_session: DatabaseSession = Depends(get_db_session),
    feed_id: Optional[int] = Query(None),
    category_id: Optional[int] = Query(None),
    search: Optional[str] = Query(None),
    sentiment: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100)
):
    """Get items list with feature flag toggle between old and new implementation."""

    # Get user ID for feature flag (could be from session, header, etc.)
    user_id = request.headers.get("X-User-ID")

    # Check if new repository implementation is enabled
    use_repo = is_feature_enabled("items_repo", user_id)

    start_time = time.perf_counter()

    try:
        if use_repo:
            # New repository-based implementation
            items_repo = ItemsRepository(db_session)
            result = await _get_items_list_repo(
                items_repo, feed_id, category_id, page, limit, search, sentiment
            )

            duration_ms = (time.perf_counter() - start_time) * 1000
            record_feature_success("items_repo", duration_ms)

            # Run shadow comparison if enabled
            if shadow_comparer.should_compare():
                try:
                    legacy_func = lambda: _get_items_list_legacy(session, feed_id, category_id, page, limit)
                    repo_func = lambda: _get_items_list_repo(items_repo, feed_id, category_id, page, limit, search, sentiment)

                    comparison = await shadow_comparer.compare_items_list(
                        legacy_func, repo_func, feed_id, category_id, page, limit
                    )

                    logger.info(f"Shadow comparison: {comparison.result.value}, old: {comparison.old_duration_ms:.1f}ms, new: {comparison.new_duration_ms:.1f}ms")
                except Exception as e:
                    logger.warning(f"Shadow comparison failed: {e}")
        else:
            # Legacy implementation
            result = await _get_items_list_legacy(session, feed_id, category_id, page, limit)

            duration_ms = (time.perf_counter() - start_time) * 1000

            # Record baseline metrics for comparison
            repo_monitor.metrics.record_metric("items.legacy.duration_ms", duration_ms)

        return result

    except Exception as e:
        if use_repo:
            record_feature_error("items_repo")

        logger.error(f"Error in items list endpoint: {e}")
        return f'<div class="alert alert-danger">Error loading articles: {str(e)}</div>'