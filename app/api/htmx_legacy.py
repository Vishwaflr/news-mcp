from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse
from sqlmodel import Session, select
from typing import Optional
from app.database import get_session
from app.models import Feed, Source, Category, Item, FeedHealth, FeedCategory, FeedProcessorConfig, ProcessorTemplate, ProcessorType, FeedType, ItemAnalysis
from app.utils.feed_detector import FeedTypeDetector
# Old template engine removed - now using dynamic templates
import feedparser
import logging

router = APIRouter(prefix="/htmx", tags=["htmx"])
logger = logging.getLogger(__name__)

@router.get("/sources-options", response_class=HTMLResponse)
def get_sources_options(session: Session = Depends(get_session)):
    sources = session.exec(select(Source)).all()
    html = ""
    for source in sources:
        html += f'<option value="{source.id}">{source.name}</option>'
    return html

@router.get("/categories-options", response_class=HTMLResponse)
def get_categories_options(session: Session = Depends(get_session)):
    categories = session.exec(select(Category)).all()
    html = ""
    for category in categories:
        html += f'<option value="{category.id}">{category.name}</option>'
    return html

@router.get("/feeds-options", response_class=HTMLResponse)
def get_feeds_options(session: Session = Depends(get_session)):
    feeds = session.exec(select(Feed)).all()
    html = ""
    for feed in feeds:
        title = feed.title or feed.url[:50] + "..."
        html += f'<option value="{feed.id}">{title}</option>'
    return html

@router.post("/feed-fetch-now/{feed_id}", response_class=HTMLResponse)
def fetch_feed_now_htmx(feed_id: int, session: Session = Depends(get_session)):
    """HTMX endpoint to fetch a feed immediately and return status"""
    try:
        from app.services.feed_fetcher_sync import SyncFeedFetcher

        feed = session.get(Feed, feed_id)
        if not feed:
            return '<div class="alert alert-danger">Feed not found</div>'

        logger.info(f"HTMX immediate fetch requested for feed {feed_id}: {feed.title}")

        fetcher = SyncFeedFetcher()
        success, items_count = fetcher.fetch_feed_sync(feed_id)

        if success:
            if items_count > 0:
                return f'<div class="alert alert-success">✅ {items_count} new articles loaded!</div>'
            else:
                return '<div class="alert alert-info">✅ Feed fetched successfully (no new articles)</div>'
        else:
            return '<div class="alert alert-warning">❌ Error loading articles</div>'

    except Exception as e:
        logger.error(f"Error in HTMX feed fetch: {e}")
        return f'<div class="alert alert-danger">❌ Error: {str(e)}</div>'

@router.get("/feeds-list", response_class=HTMLResponse)
def get_feeds_list(
    session: Session = Depends(get_session),
    category_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None)
):
    # Build base query with source and categories
    query = select(Feed, Source).join(Source)

    # Apply filters
    if category_id and category_id > 0:  # Only filter if category_id is provided and not 0 (All Categories)
        query = query.join(FeedCategory).where(FeedCategory.category_id == category_id)

    if status and status.strip():
        query = query.where(Feed.status == status.strip())

    results = session.exec(query).all()

    html = ""
    for feed, source in results:
        # Get feed categories
        feed_categories = session.exec(
            select(Category)
            .join(FeedCategory, FeedCategory.category_id == Category.id)
            .where(FeedCategory.feed_id == feed.id)
        ).all()

        category_badges = ""
        for category in feed_categories:
            category_badges += f'<span class="badge bg-primary ms-1" title="{category.description}">{category.name}</span>'

        if not category_badges:
            category_badges = '<span class="badge bg-secondary ms-1">No Category</span>'
        # Check if feed has articles
        article_count = len(session.exec(select(Item).where(Item.feed_id == feed.id)).all())
        has_articles = article_count > 0

        status_badge = {
            "active": "success",
            "inactive": "warning",
            "error": "danger"
        }.get(feed.status.value, "secondary")

        # Add "Load Articles" button for feeds without articles
        load_button = ""
        if not has_articles:
            load_button = f"""
                        <button class="btn btn-sm btn-success"
                                hx-post="/htmx/feed-fetch-now/{feed.id}"
                                hx-target="#fetch-status-{feed.id}"
                                hx-swap="innerHTML"
                                title="Load articles immediately">
                            <i class="bi bi-download"></i> Load
                        </button>"""

        html += f"""
        <div class="card mb-2">
            <div class="card-body">
                <div class="d-flex justify-content-between align-items-start">
                    <div>
                        <h6 class="card-title mb-1">
                            {feed.title or 'Untitled Feed'}
                            <span class="badge bg-{status_badge} ms-2">{feed.status.value}</span>
                            {f'<span class="badge bg-info ms-1">{article_count} Articles</span>' if has_articles else '<span class="badge bg-warning ms-1">No Articles</span>'}
                            {category_badges}
                        </h6>
                        <p class="card-text small text-muted mb-1">
                            <strong>URL:</strong> <a href="{feed.url}" target="_blank" class="text-decoration-none">{feed.url}</a>
                        </p>
                        <p class="card-text small text-muted mb-1">
                            <strong>Source:</strong> {source.name} |
                            <strong>Interval:</strong> {feed.fetch_interval_minutes} min
                        </p>
                        {f'<p class="card-text small text-muted"><strong>Last Fetch:</strong> {feed.last_fetched.strftime("%d.%m.%Y %H:%M")}</p>' if feed.last_fetched else '<p class="card-text small text-warning"><strong>Never fetched</strong></p>'}
                        <div id="fetch-status-{feed.id}"></div>
                    </div>
                    <div class="btn-group">
                        <button class="btn btn-sm btn-outline-primary"
                                hx-get="/htmx/feed-health/{feed.id}"
                                hx-target="#health-modal-content"
                                data-bs-toggle="modal"
                                data-bs-target="#healthModal">
                            <i class="bi bi-heart-pulse"></i>
                        </button>
                        <button class="btn btn-sm btn-outline-secondary"
                                hx-get="/htmx/feed-edit-form/{feed.id}"
                                hx-target="#edit-modal-content"
                                data-bs-toggle="modal"
                                data-bs-target="#editFeedModal">
                            <i class="bi bi-pencil"></i>
                        </button>
                        {load_button}
                        <button class="btn btn-sm btn-outline-warning"
                                hx-put="/api/feeds/{feed.id}"
                                hx-vals='{{"status": "{'inactive' if feed.status.value == 'active' else 'active'}"}}'"
                                hx-target="closest .card"
                                hx-swap="outerHTML">
                            <i class="bi bi-{'pause' if feed.status.value == 'active' else 'play'}"></i>
                        </button>
                        <button class="btn btn-sm btn-outline-danger"
                                hx-delete="/api/feeds/{feed.id}"
                                hx-target="#feeds-list"
                                hx-confirm="Really delete feed?">
                            <i class="bi bi-trash"></i>
                        </button>
                    </div>
                </div>
            </div>
        </div>
        """

    if not html:
        html = '<div class="alert alert-info">No feeds found.</div>'

    return html

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
    from sqlmodel import or_, outerjoin

    # Join with sentiment analysis data
    query = select(Item, Feed, ItemAnalysis).join(Feed).outerjoin(ItemAnalysis, Item.id == ItemAnalysis.item_id)

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
    for item, feed, analysis in results:
        published_date = item.published.strftime("%d.%m.%Y %H:%M") if item.published else item.created_at.strftime("%d.%m.%Y %H:%M")
        description = item.description[:200] + "..." if item.description and len(item.description) > 200 else item.description or ""

        # Clean and escape content
        clean_title = item.title.replace('"', '&quot;') if item.title else 'Untitled'
        clean_description = description.replace('"', '&quot;') if description else ''
        feed_name = (feed.title or feed.url[:30] + "...") if feed else 'Unknown Feed'

        # Generate sentiment display
        sentiment_display = generate_sentiment_display(analysis)

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
                {sentiment_display}
                {f'<p class="card-text text-body-secondary">{clean_description}</p>' if clean_description else ''}
            </div>
        </div>
        """

    if not html:
        html = '<div class="alert alert-info">No articles found.</div>'

    return html

def generate_sentiment_display(analysis):
    """Generate HTML for sentiment analysis display with expandable details"""
    if not analysis or not analysis.sentiment_json:
        return '<div class="sentiment-analysis mb-2"><span class="badge bg-secondary">No Analysis</span></div>'

    sentiment = analysis.sentiment_json
    impact = analysis.impact_json
    model = analysis.model_tag or 'unknown'

    # Extract key values
    overall = sentiment.get('overall', {})
    market = sentiment.get('market', {})
    label = overall.get('label', 'neutral')
    score = overall.get('score', 0.0)
    confidence = overall.get('confidence', 0.0)
    urgency = sentiment.get('urgency', 0.0)
    impact_overall = impact.get('overall', 0.0)
    impact_volatility = impact.get('volatility', 0.0)
    themes = sentiment.get('themes', [])

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

    # Compact display (always visible)
    compact_html = f"""
    <div class="sentiment-analysis mb-2">
        <div class="d-flex align-items-center gap-2 sentiment-compact" style="cursor: pointer;" onclick="toggleSentimentDetails(this)">
            <span class="sentiment-icon">{icon}</span>
            <span class="badge bg-{color}">{score:.1f}</span>
            <span class="badge bg-warning">⚡ {urgency:.1f}</span>
            <span class="badge bg-info">📊 {impact_overall:.1f}</span>
            <small class="text-muted">Details ⌄</small>
        </div>
"""

    # Detailed display (initially hidden)
    market_display = f"📉 Bearish ({market.get('bearish', 0):.1f})" if market.get('bearish', 0) > 0.6 else f"📈 Bullish ({market.get('bullish', 0):.1f})" if market.get('bullish', 0) > 0.6 else "➡️ Neutral"
    time_horizon = market.get('time_horizon', 'medium').title()
    themes_display = ' • '.join([f"🏷️ {theme}" for theme in themes[:4]])  # Show max 4 themes

    detailed_html = f"""
        <div class="sentiment-details mt-2" style="display: none;">
            <div class="card border-light bg-light">
                <div class="card-header bg-transparent border-bottom-0 py-2">
                    <h6 class="mb-0 text-muted">📊 Sentiment Analysis ({model})</h6>
                </div>
                <div class="card-body py-2">
                    <div class="row g-2">
                        <div class="col-md-6">
                            <div class="mb-2">
                                <strong>Overall:</strong>
                                <span class="badge bg-{color}">{label.title()} ({score:.1f})</span>
                                <small class="text-muted">• {int(confidence*100)}% confident</small>
                            </div>
                            <div class="mb-2">
                                <strong>Market:</strong> {market_display} • {time_horizon}-term
                            </div>
                        </div>
                        <div class="col-md-6">
                            <div class="mb-2">
                                <strong>Impact:</strong> ⚡ {impact_overall:.1f} • Volatility: 📈 {impact_volatility:.1f}
                            </div>
                            <div class="mb-2">
                                <strong>Urgency:</strong> ⏰ {urgency:.1f}
                            </div>
                        </div>
                    </div>
                    {f'<div class="mt-2"><strong>Themes:</strong> {themes_display}</div>' if themes else ''}
                </div>
            </div>
        </div>
    </div>
    """

    return compact_html + detailed_html

@router.get("/system-status", response_class=HTMLResponse)
def get_system_status(session: Session = Depends(get_session)):
    from datetime import datetime, timedelta

    total_feeds = len(session.exec(select(Feed)).all())
    active_feeds = len(session.exec(select(Feed).where(Feed.status == "active")).all())
    error_feeds = len(session.exec(select(Feed).where(Feed.status == "error")).all())

    recent_items = len(session.exec(
        select(Item).where(Item.created_at >= datetime.utcnow() - timedelta(hours=24))
    ).all())

    health_pct = (active_feeds / total_feeds * 100) if total_feeds > 0 else 100

    status_color = "success" if health_pct >= 90 else "warning" if health_pct >= 70 else "danger"
    status_text = "Excellent" if health_pct >= 90 else "Good" if health_pct >= 70 else "Needs Attention"

    html = f"""
    <div class="row">
        <div class="col-md-3">
            <div class="card text-center">
                <div class="card-body">
                    <h2 class="text-primary">{total_feeds}</h2>
                    <p class="card-text">Total Feeds</p>
                </div>
            </div>
        </div>
        <div class="col-md-3">
            <div class="card text-center">
                <div class="card-body">
                    <h2 class="text-success">{active_feeds}</h2>
                    <p class="card-text">Active Feeds</p>
                </div>
            </div>
        </div>
        <div class="col-md-3">
            <div class="card text-center">
                <div class="card-body">
                    <h2 class="text-danger">{error_feeds}</h2>
                    <p class="card-text">Error Feeds</p>
                </div>
            </div>
        </div>
        <div class="col-md-3">
            <div class="card text-center">
                <div class="card-body">
                    <h2 class="text-info">{recent_items}</h2>
                    <p class="card-text">Items (24h)</p>
                </div>
            </div>
        </div>
    </div>
    <div class="row mt-3">
        <div class="col-12">
            <div class="alert alert-{status_color}">
                <h5>System Health: {health_pct:.1f}%</h5>
                <p class="mb-0">Status: {status_text}</p>
            </div>
        </div>
    </div>
    """

    return html

@router.get("/feed-health/{feed_id}", response_class=HTMLResponse)
def get_feed_health_modal(feed_id: int, session: Session = Depends(get_session)):
    feed = session.get(Feed, feed_id)
    if not feed:
        return '<div class="alert alert-danger">Feed not found</div>'

    health = session.exec(select(FeedHealth).where(FeedHealth.feed_id == feed_id)).first()

    html = f"""
    <h5>Health Status for: {feed.title or 'Untitled Feed'}</h5>
    <p><strong>URL:</strong> {feed.url}</p>
    <p><strong>Status:</strong> <span class="badge bg-{'success' if feed.status == 'active' else 'warning' if feed.status == 'inactive' else 'danger'}">{feed.status}</span></p>
    """

    if health:
        html += f"""
        <div class="row">
            <div class="col-6">
                <p><strong>Success Rate:</strong> {health.ok_ratio:.1%}</p>
                <p><strong>Consecutive Failures:</strong> {health.consecutive_failures}</p>
                <p><strong>24h Uptime:</strong> {health.uptime_24h:.1%}</p>
            </div>
            <div class="col-6">
                <p><strong>Avg Response Time:</strong> {health.avg_response_time_ms or 0:.0f}ms</p>
                <p><strong>7d Uptime:</strong> {health.uptime_7d:.1%}</p>
                <p><strong>Last Updated:</strong> {health.updated_at.strftime("%d.%m.%Y %H:%M")}</p>
            </div>
        </div>
        """

        if health.last_success:
            html += f'<p><strong>Last Success:</strong> {health.last_success.strftime("%d.%m.%Y %H:%M")}</p>'
        if health.last_failure:
            html += f'<p><strong>Last Failure:</strong> {health.last_failure.strftime("%d.%m.%Y %H:%M")}</p>'
    else:
        html += '<div class="alert alert-info">Noch keine Health-Daten verfügbar</div>'

    return html

@router.get("/processor-configs", response_class=HTMLResponse)
def get_processor_configs(session: Session = Depends(get_session)):
    """Get feed processor configurations table"""
    query = select(FeedProcessorConfig, Feed).join(Feed)
    results = session.exec(query).all()

    html = """
    <div class="table-responsive">
        <table class="table table-striped">
            <thead>
                <tr>
                    <th>Feed</th>
                    <th>Processor Type</th>
                    <th>Status</th>
                    <th>Created</th>
                    <th>Actions</th>
                </tr>
            </thead>
            <tbody>
    """

    if results:
        for config, feed in results:
            feed_name = feed.title or feed.url[:50] + "..."
            status_badge = "success" if config.is_active else "secondary"
            status_text = "Active" if config.is_active else "Inactive"

            html += f"""
                <tr>
                    <td>
                        <strong>{feed_name}</strong><br>
                        <small class="text-muted">{feed.url[:60]}{'...' if len(feed.url) > 60 else ''}</small>
                    </td>
                    <td>
                        <span class="badge bg-primary">{config.processor_type.value}</span>
                    </td>
                    <td>
                        <span class="badge bg-{status_badge}">{status_text}</span>
                    </td>
                    <td>
                        <small>{config.created_at.strftime("%d.%m.%Y %H:%M")}</small>
                    </td>
                    <td>
                        <div class="btn-group btn-group-sm">
                            <button class="btn btn-outline-primary"
                                    data-bs-toggle="modal"
                                    data-bs-target="#editConfigModal"
                                    hx-get="/htmx/processor-config-form/{config.id}"
                                    hx-target="#edit-config-form">
                                <i class="bi bi-pencil"></i>
                            </button>
                            <button class="btn btn-outline-danger"
                                    hx-delete="/api/processors/config/{config.id}"
                                    hx-target="#feed-configurations"
                                    hx-confirm="Really delete configuration?">
                                <i class="bi bi-trash"></i>
                            </button>
                        </div>
                    </td>
                </tr>
            """
    else:
        html += """
            <tr>
                <td colspan="5" class="text-center text-muted">
                    No processor configurations found.
                </td>
            </tr>
        """

    html += """
            </tbody>
        </table>
    </div>
    """

    return html

@router.get("/processor-templates", response_class=HTMLResponse)
def get_processor_templates(session: Session = Depends(get_session)):
    """Get processor templates list"""
    templates = session.exec(select(ProcessorTemplate)).all()

    html = """
    <div class="row">
    """

    if templates:
        for template in templates:
            status_badge = "success" if template.is_active else "secondary"
            status_text = "Active" if template.is_active else "Inactive"
            builtin_badge = "warning" if template.is_builtin else "info"
            builtin_text = "Built-in" if template.is_builtin else "Custom"

            html += f"""
            <div class="col-md-6 mb-3">
                <div class="card h-100">
                    <div class="card-header d-flex justify-content-between align-items-center">
                        <h6 class="mb-0">{template.name}</h6>
                        <div>
                            <span class="badge bg-{builtin_badge} me-1">{builtin_text}</span>
                            <span class="badge bg-{status_badge}">{status_text}</span>
                        </div>
                    </div>
                    <div class="card-body">
                        <p class="card-text">
                            <strong>Type:</strong> <span class="badge bg-primary">{template.processor_type.value}</span>
                        </p>
                        {f'<p class="card-text small text-muted">{template.description}</p>' if template.description else ''}
                        <p class="card-text">
                            <small class="text-muted">
                                Created: {template.created_at.strftime("%d.%m.%Y %H:%M")}<br>
                                Updated: {template.updated_at.strftime("%d.%m.%Y %H:%M")}
                            </small>
                        </p>
                    </div>
                    <div class="card-footer">
                        <div class="btn-group btn-group-sm w-100">
                            <button class="btn btn-outline-primary"
                                    data-bs-toggle="modal"
                                    data-bs-target="#editTemplateModal"
                                    hx-get="/htmx/processor-template-form/{template.id}"
                                    hx-target="#edit-template-form">
                                <i class="bi bi-pencil"></i> Edit
                            </button>
                            <button class="btn btn-outline-info"
                                    hx-post="/api/processors/templates/{template.id}/apply"
                                    hx-target="#processor-templates"
                                    hx-confirm="Template auf alle passenden Feeds anwenden?">
                                <i class="bi bi-check2-all"></i> Apply
                            </button>
                            {"" if template.is_builtin else f'''
                            <button class="btn btn-outline-danger"
                                    hx-delete="/api/processors/templates/{template.id}"
                                    hx-target="#processor-templates"
                                    hx-confirm="Really delete template?">
                                <i class="bi bi-trash"></i>
                            </button>
                            '''}
                        </div>
                    </div>
                </div>
            </div>
            """
    else:
        html += """
        <div class="col-12">
            <div class="alert alert-info text-center">
                <i class="bi bi-info-circle me-2"></i>
                No processor templates found.
            </div>
        </div>
        """

    html += """
    </div>
    """

    return html

@router.get("/processor-stats", response_class=HTMLResponse)
def get_processor_stats(session: Session = Depends(get_session), days: int = 7):
    """Get detailed processor statistics dashboard"""
    from datetime import datetime, timedelta
    from app.models import ContentProcessingLog, ProcessorType
    from sqlmodel import func

    # Get time range
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)

    # Basic statistics
    total_query = select(func.count(ContentProcessingLog.id)).where(
        ContentProcessingLog.processed_at >= start_date
    )
    total_processed = session.exec(total_query).first() or 0

    success_query = select(func.count(ContentProcessingLog.id)).where(
        ContentProcessingLog.processed_at >= start_date,
        ContentProcessingLog.processing_status == "success"
    )
    success_count = session.exec(success_query).first() or 0

    # Processor breakdown
    breakdown_query = select(
        ContentProcessingLog.processor_type,
        func.count(ContentProcessingLog.id).label('count'),
        func.avg(ContentProcessingLog.processing_time_ms).label('avg_time')
    ).where(
        ContentProcessingLog.processed_at >= start_date
    ).group_by(ContentProcessingLog.processor_type)

    breakdown_results = session.exec(breakdown_query).all()

    success_rate = (success_count / total_processed * 100) if total_processed > 0 else 100

    html = f"""
    <div class="row">
        <!-- Summary Cards -->
        <div class="col-md-3 mb-3">
            <div class="card text-center bg-primary text-white">
                <div class="card-body">
                    <h2 class="display-6">{total_processed}</h2>
                    <p class="card-text">Total Processed</p>
                    <small>Last {days} day{'s' if days > 1 else ''}</small>
                </div>
            </div>
        </div>

        <div class="col-md-3 mb-3">
            <div class="card text-center bg-success text-white">
                <div class="card-body">
                    <h2 class="display-6">{success_count}</h2>
                    <p class="card-text">Successful</p>
                    <small>{success_rate:.1f}% success rate</small>
                </div>
            </div>
        </div>

        <div class="col-md-3 mb-3">
            <div class="card text-center bg-danger text-white">
                <div class="card-body">
                    <h2 class="display-6">{total_processed - success_count}</h2>
                    <p class="card-text">Failed</p>
                    <small>{(100 - success_rate):.1f}% failure rate</small>
                </div>
            </div>
        </div>

        <div class="col-md-3 mb-3">
            <div class="card text-center bg-info text-white">
                <div class="card-body">
                    <h2 class="display-6">{len(breakdown_results)}</h2>
                    <p class="card-text">Active Processors</p>
                    <small>In use</small>
                </div>
            </div>
        </div>
    </div>

    <div class="row">
        <!-- Processor Performance -->
        <div class="col-md-8 mb-3">
            <div class="card">
                <div class="card-header">
                    <h6><i class="bi bi-bar-chart"></i> Processor Performance Breakdown</h6>
                </div>
                <div class="card-body">
                    <div class="table-responsive">
                        <table class="table table-sm">
                            <thead>
                                <tr>
                                    <th>Processor Type</th>
                                    <th>Items Processed</th>
                                    <th>Avg Time (ms)</th>
                                    <th>Usage %</th>
                                </tr>
                            </thead>
                            <tbody>
    """

    for result in breakdown_results:
        processor_type = result[0]
        count = result[1]
        avg_time = result[2] or 0
        usage_percent = (count / total_processed * 100) if total_processed > 0 else 0

        # Color coding based on processor type
        badge_color = {
            'universal': 'primary',
            'cointelegraph': 'warning',
            'heise': 'success',
            'custom': 'info'
        }.get(processor_type.value if hasattr(processor_type, 'value') else str(processor_type), 'secondary')

        html += f"""
                                <tr>
                                    <td><span class="badge bg-{badge_color}">{processor_type.value if hasattr(processor_type, 'value') else processor_type}</span></td>
                                    <td>{count}</td>
                                    <td>{avg_time:.1f}</td>
                                    <td>
                                        <div class="progress" style="height: 20px;">
                                            <div class="progress-bar bg-{badge_color}" role="progressbar"
                                                 style="width: {usage_percent:.1f}%"
                                                 aria-valuenow="{usage_percent:.1f}" aria-valuemin="0" aria-valuemax="100">
                                                {usage_percent:.1f}%
                                            </div>
                                        </div>
                                    </td>
                                </tr>
        """

    html += """
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>

        <!-- Quick Actions -->
        <div class="col-md-4 mb-3">
            <div class="card">
                <div class="card-header">
                    <h6><i class="bi bi-tools"></i> Quick Actions</h6>
                </div>
                <div class="card-body">
                    <div class="d-grid gap-2">
                        <button class="btn btn-outline-primary btn-sm"
                                hx-get="/htmx/processor-stats?days=1"
                                hx-target="#detailed-statistics">
                            <i class="bi bi-calendar-day"></i> 24 Hours
                        </button>
                        <button class="btn btn-outline-primary btn-sm"
                                hx-get="/htmx/processor-stats?days=7"
                                hx-target="#detailed-statistics">
                            <i class="bi bi-calendar-week"></i> 7 Days
                        </button>
                        <button class="btn btn-outline-primary btn-sm"
                                hx-get="/htmx/processor-stats?days=30"
                                hx-target="#detailed-statistics">
                            <i class="bi bi-calendar-month"></i> 30 Days
                        </button>
                        <hr>
                        <button class="btn btn-outline-success btn-sm"
                                onclick="exportStats()">
                            <i class="bi bi-download"></i> Export Report
                        </button>
                        <button class="btn btn-outline-info btn-sm"
                                hx-get="/htmx/processor-health-details"
                                hx-target="#health-details-modal"
                                data-bs-toggle="modal"
                                data-bs-target="#healthDetailsModal">
                            <i class="bi bi-heart-pulse"></i> Health Details
                        </button>
                    </div>
                </div>
            </div>
        </div>
    </div>
    """

    if total_processed == 0:
        html = """
        <div class="alert alert-info text-center">
            <i class="bi bi-info-circle me-2"></i>
            No processing data available for the selected time period.
        </div>
        """

    return html

@router.get("/reprocessing-status", response_class=HTMLResponse)
def get_reprocessing_status(session: Session = Depends(get_session)):
    """Get reprocessing status and history"""
    from datetime import datetime, timedelta
    from app.models import ContentProcessingLog
    from sqlmodel import func, desc

    # Recent reprocessing activity (last 24h)
    recent_cutoff = datetime.utcnow() - timedelta(hours=24)
    recent_logs = session.exec(
        select(ContentProcessingLog)
        .where(ContentProcessingLog.processed_at >= recent_cutoff)
        .order_by(desc(ContentProcessingLog.processed_at))
        .limit(10)
    ).all()

    # Statistics
    total_today = session.exec(
        select(func.count(ContentProcessingLog.id))
        .where(ContentProcessingLog.processed_at >= recent_cutoff)
    ).first() or 0

    success_today = session.exec(
        select(func.count(ContentProcessingLog.id))
        .where(
            ContentProcessingLog.processed_at >= recent_cutoff,
            ContentProcessingLog.processing_status == "success"
        )
    ).first() or 0

    html = f"""
    <div class="row mb-3">
        <div class="col-md-6">
            <div class="card border-info">
                <div class="card-header bg-info text-white">
                    <h6 class="mb-0"><i class="bi bi-info-circle"></i> 24h Processing Summary</h6>
                </div>
                <div class="card-body">
                    <div class="row text-center">
                        <div class="col-6">
                            <h4 class="text-primary">{total_today}</h4>
                            <small>Total Processed</small>
                        </div>
                        <div class="col-6">
                            <h4 class="text-success">{success_today}</h4>
                            <small>Successful</small>
                        </div>
                    </div>
                    <div class="progress mt-2">
                        <div class="progress-bar bg-success" role="progressbar"
                             style="width: {(success_today/total_today*100) if total_today > 0 else 0:.1f}%">
                            {(success_today/total_today*100) if total_today > 0 else 0:.1f}%
                        </div>
                    </div>
                </div>
            </div>
        </div>
        <div class="col-md-6">
            <div class="card border-warning">
                <div class="card-header bg-warning text-dark">
                    <h6 class="mb-0"><i class="bi bi-clock"></i> Quick Actions</h6>
                </div>
                <div class="card-body">
                    <div class="d-grid gap-2">
                        <button class="btn btn-sm btn-outline-primary"
                                hx-post="/api/processors/reprocess/all?force_all=false"
                                hx-target="#reprocessing-results"
                                hx-confirm="Reprocess all failed items?">
                            <i class="bi bi-arrow-repeat"></i> Retry Failed Items
                        </button>
                        <button class="btn btn-sm btn-outline-warning"
                                onclick="showBulkReprocessing()">
                            <i class="bi bi-list-check"></i> Bulk Operations
                        </button>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <div class="card">
        <div class="card-header">
            <h6><i class="bi bi-activity"></i> Recent Processing Activity</h6>
        </div>
        <div class="card-body">
            <div class="table-responsive">
                <table class="table table-sm table-hover">
                    <thead>
                        <tr>
                            <th>Time</th>
                            <th>Item ID</th>
                            <th>Feed</th>
                            <th>Processor</th>
                            <th>Status</th>
                            <th>Time (ms)</th>
                        </tr>
                    </thead>
                    <tbody>
    """

    if recent_logs:
        for log in recent_logs:
            status_badge = {
                'success': 'success',
                'failed': 'danger',
                'partial': 'warning',
                'skipped': 'secondary'
            }.get(log.processing_status, 'secondary')

            processor_badge = {
                'universal': 'primary',
                'cointelegraph': 'warning',
                'heise': 'success',
                'custom': 'info'
            }.get(log.processor_type.value if hasattr(log.processor_type, 'value') else str(log.processor_type), 'secondary')

            html += f"""
                        <tr>
                            <td><small>{log.processed_at.strftime("%H:%M:%S")}</small></td>
                            <td><small>{log.item_id}</small></td>
                            <td><small>{log.feed_id}</small></td>
                            <td><span class="badge bg-{processor_badge}">{log.processor_type.value if hasattr(log.processor_type, 'value') else log.processor_type}</span></td>
                            <td><span class="badge bg-{status_badge}">{log.processing_status}</span></td>
                            <td><small>{log.processing_time_ms or 0}</small></td>
                        </tr>
            """
    else:
        html += """
                        <tr>
                            <td colspan="6" class="text-center text-muted">
                                No recent processing activity
                            </td>
                        </tr>
        """

    html += """
                    </tbody>
                </table>
            </div>
        </div>
    </div>
    """

    return html
@router.get("/processor-health-details", response_class=HTMLResponse)
def get_processor_health_details(session: Session = Depends(get_session)):
    """Get detailed processor health monitoring dashboard"""
    from datetime import datetime, timedelta
    from app.models import ContentProcessingLog, FeedProcessorConfig, Feed
    from sqlmodel import func

    # Health metrics for each processor type
    processor_health = {}

    # Get all active processor configurations
    configs = session.exec(
        select(FeedProcessorConfig, Feed)
        .join(Feed)
        .where(FeedProcessorConfig.is_active == True)
    ).all()

    # Calculate health metrics for each processor
    for config, feed in configs:
        processor_type = config.processor_type.value

        if processor_type not in processor_health:
            processor_health[processor_type] = {
                'feeds': [],
                'total_items': 0,
                'success_items': 0,
                'last_24h': 0,
                'health_score': 100
            }

        # Get processing stats for this feed (last 7 days)
        week_ago = datetime.utcnow() - timedelta(days=7)

        feed_logs = session.exec(
            select(ContentProcessingLog)
            .where(
                ContentProcessingLog.feed_id == feed.id,
                ContentProcessingLog.processed_at >= week_ago
            )
        ).all()

        feed_total = len(feed_logs)
        feed_success = len([log for log in feed_logs if log.processing_status == "success"])

        # Last 24h activity
        day_ago = datetime.utcnow() - timedelta(hours=24)
        feed_24h = len([log for log in feed_logs if log.processed_at >= day_ago])

        processor_health[processor_type]['feeds'].append({
            'name': feed.title or feed.url[:30] + "...",
            'id': feed.id,
            'total': feed_total,
            'success': feed_success,
            'success_rate': (feed_success / feed_total * 100) if feed_total > 0 else 0,
            'activity_24h': feed_24h
        })

        processor_health[processor_type]['total_items'] += feed_total
        processor_health[processor_type]['success_items'] += feed_success
        processor_health[processor_type]['last_24h'] += feed_24h

    # Calculate aggregated metrics
    for proc_type in processor_health:
        data = processor_health[proc_type]
        if data['total_items'] > 0:
            data['success_rate'] = data['success_items'] / data['total_items'] * 100
            data['health_score'] = min(100, data['success_rate'] + (10 if data['last_24h'] > 0 else 0))
        else:
            data['success_rate'] = 0
            data['health_score'] = 50

    html = """
    <div class="row">
        <div class="col-12">
            <h5><i class="bi bi-heart-pulse"></i> Processor Health Monitoring</h5>
            <p class="text-muted">Detailed health status and performance metrics for all active processors</p>
        </div>
    </div>
    """

    if processor_health:
        for proc_type, data in processor_health.items():
            # Determine health status color
            if data['health_score'] >= 90:
                health_color = 'success'
                health_text = 'Excellent'
            elif data['health_score'] >= 70:
                health_color = 'warning'
                health_text = 'Good'
            else:
                health_color = 'danger'
                health_text = 'Needs Attention'

            # Processor type color
            proc_color = {
                'universal': 'primary',
                'cointelegraph': 'warning',
                'heise': 'success',
                'custom': 'info'
            }.get(proc_type, 'secondary')

            html += f"""
            <div class="card mb-3">
                <div class="card-header d-flex justify-content-between align-items-center">
                    <div>
                        <h6 class="mb-0">
                            <span class="badge bg-{proc_color} me-2">{proc_type.upper()}</span>
                            Processor Health
                        </h6>
                    </div>
                    <div>
                        <span class="badge bg-{health_color}">{health_text} ({data['health_score']:.0f}%)</span>
                    </div>
                </div>
                <div class="card-body">
                    <div class="row mb-3">
                        <div class="col-md-4">
                            <div class="text-center">
                                <h4 class="text-primary">{data['total_items']}</h4>
                                <small>Total Items (7d)</small>
                            </div>
                        </div>
                        <div class="col-md-4">
                            <div class="text-center">
                                <h4 class="text-success">{data['success_rate']:.1f}%</h4>
                                <small>Success Rate</small>
                            </div>
                        </div>
                        <div class="col-md-4">
                            <div class="text-center">
                                <h4 class="text-info">{data['last_24h']}</h4>
                                <small>Activity (24h)</small>
                            </div>
                        </div>
                    </div>

                    <h6>Feed Details:</h6>
                    <div class="table-responsive">
                        <table class="table table-sm">
                            <thead>
                                <tr>
                                    <th>Feed</th>
                                    <th>Items (7d)</th>
                                    <th>Success Rate</th>
                                    <th>24h Activity</th>
                                    <th>Status</th>
                                </tr>
                            </thead>
                            <tbody>
            """

            for feed in data['feeds']:
                status_color = 'success' if feed['success_rate'] >= 90 else 'warning' if feed['success_rate'] >= 70 else 'danger'

                html += f"""
                                <tr>
                                    <td><strong>{feed['name']}</strong></td>
                                    <td>{feed['total']}</td>
                                    <td>
                                        <div class="progress" style="height: 15px;">
                                            <div class="progress-bar bg-{status_color}" role="progressbar"
                                                 style="width: {feed['success_rate']:.1f}%">
                                                {feed['success_rate']:.1f}%
                                            </div>
                                        </div>
                                    </td>
                                    <td>
                                        <span class="badge bg-{'success' if feed['activity_24h'] > 0 else 'secondary'}">
                                            {feed['activity_24h']}
                                        </span>
                                    </td>
                                    <td>
                                        <span class="badge bg-{status_color}">
                                            {'Healthy' if feed['success_rate'] >= 90 else 'Warning' if feed['success_rate'] >= 70 else 'Critical'}
                                        </span>
                                    </td>
                                </tr>
                """

            html += """
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
            """
    else:
        html += """
        <div class="alert alert-info text-center">
            <i class="bi bi-info-circle me-2"></i>
            No active processor configurations found.
        </div>
        """

    return html


@router.get("/feed-types-options", response_class=HTMLResponse)
def get_feed_types_options(session: Session = Depends(get_session)):
    """Get feed types as HTML options."""
    feed_types = session.exec(select(FeedType)).all()
    html = '<option value="">Auto-detect</option>'
    for feed_type in feed_types:
        html += f'<option value="{feed_type.id}">{feed_type.name.replace("_", " ").title()}</option>'
    return html


@router.post("/feed-url-test", response_class=HTMLResponse)
def test_feed_url(url: str, session: Session = Depends(get_session)):
    """Test a feed URL and return preview information."""
    if not url:
        return '<div class="alert alert-danger">Please enter a URL</div>'

    try:
        # Parse the feed
        parsed = feedparser.parse(url)

        if not parsed.entries:
            return '<div class="alert alert-warning">No entries found in feed</div>'

        # Detect feed type
        feed_config = FeedTypeDetector.auto_configure_feed(session, url, parsed.feed.get('title'))
        # Note: Template detection now handled by dynamic template system

        # Preview HTML
        html = f'''
        <div class="alert alert-success">
            <h6>Feed Preview</h6>
            <strong>Title:</strong> {parsed.feed.get("title", "Unknown")}<br>
            <strong>Type:</strong> {feed_config["feed_type_name"].replace("_", " ").title()}<br>
            <strong>Template:</strong> Auto-assigned via dynamic templates<br>
            <strong>Recommended Interval:</strong> {feed_config["recommended_interval"]} minutes<br>
            <strong>Entries Found:</strong> {len(parsed.entries)}
        </div>
        <div class="mt-3">
            <h6>Recent Articles:</h6>
            <ul class="list-group list-group-flush">
        '''

        # Show first 3 articles
        for entry in parsed.entries[:3]:
            title = entry.get('title', 'No title')[:60]
            author = entry.get('author', 'Unknown')
            html += f'''
                <li class="list-group-item">
                    <strong>{title}</strong><br>
                    <small class="text-muted">by {author}</small>
                </li>
            '''

        html += '</ul></div>'

        # Hidden inputs for auto-filled form
        html += f'''
        <script>
            document.getElementById('feed-title').value = "{parsed.feed.get("title", "")}";
            document.getElementById('feed-description').value = "{parsed.feed.get("description", "")[:200]}";
            document.getElementById('feed-interval').value = "{feed_config["recommended_interval"]}";
            document.getElementById('feed-type').value = "{feed_config["feed_type_id"] or ""}";
        </script>
        '''

        return html

    except Exception as e:
        return f'<div class="alert alert-danger">Error testing feed: {str(e)}</div>'


# Old available-templates endpoint removed - now using dynamic templates at /admin/templates


@router.get("/feed-edit-form/{feed_id}", response_class=HTMLResponse)
def get_feed_edit_form(feed_id: int, session: Session = Depends(get_session)):
    """Get edit form for a specific feed."""
    feed = session.get(Feed, feed_id)
    if not feed:
        return '<div class="alert alert-danger">Feed not found</div>'

    # Get available feed types
    feed_types = session.exec(select(FeedType)).all()
    feed_type_options = '<option value="">Auto-detect</option>'
    for ft in feed_types:
        selected = 'selected' if feed.feed_type_id == ft.id else ''
        feed_type_options += f'<option value="{ft.id}" {selected}>{ft.name.replace("_", " ").title()}</option>'

    # Get available sources
    sources = session.exec(select(Source)).all()
    source_options = ''
    for source in sources:
        selected = 'selected' if feed.source_id == source.id else ''
        source_options += f'<option value="{source.id}" {selected}>{source.name}</option>'

    # Get current feed categories
    feed_categories = session.exec(select(FeedCategory).where(FeedCategory.feed_id == feed_id)).all()
    current_category_ids = [fc.category_id for fc in feed_categories]

    # Get available categories
    categories = session.exec(select(Category)).all()
    category_options = ''
    for category in categories:
        selected = 'selected' if category.id in current_category_ids else ''
        category_options += f'<option value="{category.id}" {selected}>{category.name}</option>'

    html = f'''
    <div class="modal-header">
        <h5 class="modal-title">Edit Feed: {feed.title or feed.url}</h5>
        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
    </div>
    <form hx-put="/api/feeds/{feed.id}/form" hx-target="#feeds-list"
          hx-on="htmx:afterRequest: if(event.detail.successful) {{ bootstrap.Modal.getInstance(document.getElementById('editFeedModal')).hide(); }}">
        <div class="modal-body">
            <div class="mb-3">
                <label class="form-label">Feed URL</label>
                <input type="url" class="form-control" name="url" value="{feed.url}" required>
            </div>

            <div class="row">
                <div class="col-md-6">
                    <div class="mb-3">
                        <label class="form-label">Title</label>
                        <input type="text" class="form-control" name="title" value="{feed.title or ''}">
                    </div>
                </div>
                <div class="col-md-6">
                    <div class="mb-3">
                        <label class="form-label">Feed Typ</label>
                        <select class="form-select" name="feed_type_id">
                            {feed_type_options}
                        </select>
                    </div>
                </div>
            </div>

            <div class="mb-3">
                <label class="form-label">Description</label>
                <textarea class="form-control" name="description" rows="2">{feed.description or ''}</textarea>
            </div>

            <div class="row">
                <div class="col-md-6">
                    <div class="mb-3">
                        <label class="form-label">Fetch Interval (Minutes)</label>
                        <input type="number" class="form-control" name="fetch_interval_minutes"
                               value="{feed.fetch_interval_minutes}" min="5" max="1440">
                    </div>
                </div>
                <div class="col-md-6">
                    <div class="mb-3">
                        <label class="form-label">Status</label>
                        <div class="form-control-plaintext">
                            <span class="badge bg-{'success' if feed.status.value == 'active' else 'warning' if feed.status.value == 'inactive' else 'danger'}">
                                {'Active' if feed.status.value == 'active' else 'Inactive' if feed.status.value == 'inactive' else 'Error'}
                            </span>
                            <small class="text-muted ms-2">(Set automatically)</small>
                        </div>
                    </div>
                </div>
            </div>

            <div class="row">
                <div class="col-md-6">
                    <div class="mb-3">
                        <label class="form-label">Source</label>
                        <select class="form-select" name="source_id" required>
                            {source_options}
                        </select>
                    </div>
                </div>
                <div class="col-md-6">
                    <div class="mb-3">
                        <label class="form-label">Category</label>
                        <select class="form-select" name="category_id">
                            <option value="0">No Category</option>
                            {category_options}
                        </select>
                    </div>
                </div>
            </div>

            <div class="row">
                <div class="col-md-6">
                    <div class="mb-3">
                        <label class="form-label">Last Fetch</label>
                        <input type="text" class="form-control" value="{feed.last_fetched or 'Never'}" readonly>
                    </div>
                </div>
                <div class="col-md-6">
                    <div class="mb-3">
                        <label class="form-label">Created</label>
                        <input type="text" class="form-control" value="{feed.created_at.strftime('%d.%m.%Y %H:%M')}" readonly>
                    </div>
                </div>
            </div>
        </div>
        <div class="modal-footer">
            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
            <button type="submit" class="btn btn-primary">
                <i class="bi bi-save"></i> Save
            </button>
        </div>
    </form>
    '''

    return html
