from fastapi import APIRouter, Depends, Query
from fastapi.responses import HTMLResponse
from sqlmodel import Session, select
from typing import Optional
from app.core.logging_config import get_logger

from app.database import get_session
from app.models import Feed, Source, Category, Item, FeedHealth, FeedCategory, FeedProcessorConfig, ProcessorTemplate, ProcessorType, FeedType
from app.utils.feed_detector import FeedTypeDetector

router = APIRouter(tags=["htmx-feeds"])
logger = get_logger(__name__)

@router.get("/feeds-options", response_class=HTMLResponse)
def get_feeds_options(session: Session = Depends(get_session)):
    """Optimized feeds dropdown - loads only necessary fields"""
    # Only select id, title, url for performance
    stmt = select(Feed.id, Feed.title, Feed.url).order_by(Feed.title)
    results = session.exec(stmt).all()

    # Use list comprehension for faster HTML building
    options = [
        f'<option value="{feed_id}">{title or url[:50] + "..."}</option>'
        for feed_id, title, url in results
    ]

    return "".join(options)

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

@router.post("/feed-toggle-auto-analysis/{feed_id}", response_class=HTMLResponse)
def toggle_feed_auto_analysis(feed_id: int, session: Session = Depends(get_session)):
    """HTMX endpoint to toggle auto-analysis for a feed"""
    try:
        feed = session.get(Feed, feed_id)
        if not feed:
            return '<div class="alert alert-danger">Feed not found</div>'

        feed.auto_analyze_enabled = not feed.auto_analyze_enabled
        session.commit()
        session.refresh(feed)

        logger.info(f"Toggled auto-analysis for feed {feed_id} to {feed.auto_analyze_enabled}")

        return get_feeds_list(session)

    except Exception as e:
        logger.error(f"Error toggling auto-analysis: {e}")
        return f'<div class="alert alert-danger">❌ Error: {str(e)}</div>'

@router.get("/feeds-list", response_class=HTMLResponse)
def get_feeds_list(
    session: Session = Depends(get_session),
    category_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    auto_analysis_only: Optional[str] = Query(None)
):
    logger.info(f"get_feeds_list called with auto_analysis_only={auto_analysis_only}")

    # Build base query with source and categories
    query = select(Feed, Source).join(Source)

    # Apply filters
    if category_id is not None and category_id > 0:  # Only filter if category_id is provided and not 0 (All Categories)
        query = query.join(FeedCategory).where(FeedCategory.category_id == category_id)

    if status and status.strip():
        query = query.where(Feed.status == status.strip())

    if auto_analysis_only and auto_analysis_only.lower() in ["true", "1", "yes"]:
        logger.info(f"Applying auto_analyze_enabled filter")
        query = query.where(Feed.auto_analyze_enabled == True)

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
        # Check if feed has articles and get analysis stats
        article_count = len(session.exec(select(Item).where(Item.feed_id == feed.id)).all())
        has_articles = article_count > 0

        # Get latest article date
        latest_article = session.exec(
            select(Item)
            .where(Item.feed_id == feed.id)
            .order_by(Item.published.desc())
            .limit(1)
        ).first()
        latest_article_date = latest_article.published if latest_article and latest_article.published else None

        # Get sentiment analysis statistics for this feed
        sentiment_stats = None
        analysis_count = 0

        if has_articles:
            try:
                # Use SQLAlchemy engine to get comprehensive feed metrics
                from sqlalchemy import text

                query = text("""
                    SELECT
                        COUNT(*) as total_analyzed,
                        COUNT(CASE WHEN sentiment_json->'overall'->>'label' = 'positive' THEN 1 END) as positive_count,
                        COUNT(CASE WHEN sentiment_json->'overall'->>'label' = 'negative' THEN 1 END) as negative_count,
                        COUNT(CASE WHEN sentiment_json->'overall'->>'label' = 'neutral' THEN 1 END) as neutral_count,
                        COUNT(CASE WHEN CAST(sentiment_json->>'urgency' AS NUMERIC) >= 0.7 THEN 1 END) as high_urgency,
                        COUNT(CASE WHEN CAST(impact_json->>'overall' AS NUMERIC) >= 0.7 THEN 1 END) as high_impact,
                        COUNT(CASE WHEN CAST(sentiment_json->>'urgency' AS NUMERIC) >= 0.7 AND CAST(impact_json->>'overall' AS NUMERIC) >= 0.7 THEN 1 END) as highly_relevant,
                        ROUND(AVG(CAST(sentiment_json->>'urgency' AS NUMERIC)), 2) as avg_urgency,
                        ROUND(AVG(CAST(impact_json->>'overall' AS NUMERIC)), 2) as avg_impact
                    FROM item_analysis ia
                    JOIN items i ON ia.item_id = i.id
                    WHERE i.feed_id = :feed_id
                """)

                # Execute raw SQL using the session's connection
                with session.get_bind().connect() as conn:
                    result = conn.execute(query, {"feed_id": feed.id}).fetchone()
                    if result and result[0] > 0:
                        analysis_count = result[0]
                        sentiment_stats = {
                            'total_analyzed': result[0],
                            'positive_count': result[1],
                            'negative_count': result[2],
                            'neutral_count': result[3],
                            'high_urgency': result[4],
                            'high_impact': result[5],
                            'highly_relevant': result[6],
                            'avg_urgency': float(result[7]) if result[7] else 0,
                            'avg_impact': float(result[8]) if result[8] else 0
                        }
            except Exception as e:
                logger.warning(f"Could not fetch sentiment stats for feed {feed.id}: {e}")
                analysis_count = 0

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

        # Build comprehensive analysis info
        analysis_info = ""
        if sentiment_stats and analysis_count > 0:
            positive_pct = round((sentiment_stats['positive_count'] / analysis_count) * 100, 1)
            negative_pct = round((sentiment_stats['negative_count'] / analysis_count) * 100, 1)
            neutral_pct = round((sentiment_stats['neutral_count'] / analysis_count) * 100, 1)

            # Calculate quality metrics
            analysis_coverage = round((analysis_count / article_count) * 100, 1) if article_count > 0 else 0
            relevance_pct = round((sentiment_stats['highly_relevant'] / analysis_count) * 100, 1)

            # Determine quality badge
            quality_badge = "secondary"
            quality_text = "Unknown"
            if relevance_pct >= 30:
                quality_badge = "success"
                quality_text = "High Quality"
            elif relevance_pct >= 15:
                quality_badge = "warning"
                quality_text = "Medium Quality"
            elif analysis_count >= 5:
                quality_badge = "danger"
                quality_text = "Low Quality"

            analysis_info = f"""
                        <div class="mt-2 p-2 bg-light rounded">
                            <div class="d-flex justify-content-between align-items-center mb-2">
                                <small class="text-muted"><strong>Analysis ({analysis_count}/{article_count} = {analysis_coverage}%):</strong></small>
                                <span class="badge bg-{quality_badge}">{quality_text}</span>
                            </div>

                            <!-- Sentiment Distribution -->
                            <div class="row text-center mb-2">
                                <div class="col-4">
                                    <span class="badge bg-success">{sentiment_stats['positive_count']} Pos ({positive_pct}%)</span>
                                </div>
                                <div class="col-4">
                                    <span class="badge bg-secondary">{sentiment_stats['neutral_count']} Neu ({neutral_pct}%)</span>
                                </div>
                                <div class="col-4">
                                    <span class="badge bg-danger">{sentiment_stats['negative_count']} Neg ({negative_pct}%)</span>
                                </div>
                            </div>

                            <!-- Quality Metrics -->
                            <div class="row text-center">
                                <div class="col-3">
                                    <small class="text-muted">📈 {sentiment_stats['highly_relevant']}<br>Relevant ({relevance_pct}%)</small>
                                </div>
                                <div class="col-3">
                                    <small class="text-muted">🚨 {sentiment_stats['high_urgency']}<br>Urgent</small>
                                </div>
                                <div class="col-3">
                                    <small class="text-muted">💥 {sentiment_stats['high_impact']}<br>Impact</small>
                                </div>
                                <div class="col-3">
                                    <small class="text-muted">⚡ {sentiment_stats['avg_urgency']}<br>Avg Urg</small>
                                </div>
                            </div>
                        </div>"""
        elif has_articles and analysis_count == 0:
            # Show warning for feeds with articles but no analysis
            analysis_coverage = 0
            analysis_info = f"""
                        <div class="mt-2 p-2 bg-warning bg-opacity-25 rounded">
                            <div class="d-flex justify-content-between align-items-center">
                                <small class="text-warning"><strong>⚠️ No analysis available</strong></small>
                                <small class="text-muted">{article_count} articles waiting for analysis</small>
                            </div>
                        </div>"""

        html += f"""
        <div class="card mb-2">
            <div class="card-body">
                <div class="d-flex justify-content-between align-items-start">
                    <div>
                        <h6 class="card-title mb-1">
                            {feed.title or 'Untitled Feed'}
                            <span class="badge bg-{status_badge} ms-2">{feed.status.value}</span>
                            {f'<span class="badge bg-info ms-1">{article_count} Articles</span>' if has_articles else '<span class="badge bg-warning ms-1">No Articles</span>'}
                            {f'<span class="badge bg-primary ms-1">{analysis_count} Analyzed</span>' if analysis_count > 0 else f'<span class="badge bg-secondary ms-1">0 Analyzed</span>' if has_articles else ''}
                            {'<span class="badge bg-success ms-1" title="Auto-Analysis aktiv"><i class="bi bi-robot"></i> Auto</span>' if feed.auto_analyze_enabled else '<span class="badge bg-secondary ms-1" title="Auto-Analysis deaktiviert"><i class="bi bi-robot"></i> Manual</span>'}
                            {category_badges}
                        </h6>
                        <p class="card-text small text-muted mb-1">
                            <strong>URL:</strong> <a href="{feed.url}" target="_blank" class="text-decoration-none">{feed.url}</a>
                        </p>
                        <p class="card-text small text-muted mb-1">
                            <strong>Source:</strong> {source.name} |
                            <strong>Interval:</strong> {feed.fetch_interval_minutes} min
                        </p>
                        {f'<p class="card-text small text-muted mb-1"><strong>Last Fetch:</strong> {feed.last_fetched.strftime("%d.%m.%Y %H:%M")}</p>' if feed.last_fetched else '<p class="card-text small text-warning mb-1"><strong>Never fetched</strong></p>'}
                        {f'<p class="card-text small text-muted"><strong>Latest Article:</strong> {latest_article_date.strftime("%d.%m.%Y %H:%M")}</p>' if latest_article_date else '<p class="card-text small text-muted"><strong>Latest Article:</strong> N/A</p>' if has_articles else ''}
                        <div id="fetch-status-{feed.id}"></div>
                        {analysis_info}
                    </div>
                    <div class="btn-group-vertical">
                        <div class="btn-group mb-1">
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
                        <button class="btn btn-sm {'btn-success' if feed.auto_analyze_enabled else 'btn-outline-secondary'}"
                                hx-post="/htmx/feed-toggle-auto-analysis/{feed.id}"
                                hx-target="closest .card"
                                hx-swap="outerHTML"
                                title="{'Deaktiviere' if feed.auto_analyze_enabled else 'Aktiviere'} Auto-Analysis">
                            <i class="bi bi-robot"></i> {'ON' if feed.auto_analyze_enabled else 'OFF'}
                        </button>
                    </div>
                </div>
            </div>
        </div>
        """

    if not html:
        html = '<div class="alert alert-info">No feeds found.</div>'

    return html

@router.get("/feed-health/{feed_id}", response_class=HTMLResponse)
def get_feed_health_modal(feed_id: int, session: Session = Depends(get_session)):
    """Get health modal content for a feed"""
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
        <p><strong>Last Check:</strong> {health.last_check_time.strftime('%Y-%m-%d %H:%M:%S') if health.last_check_time else 'Never'}</p>
        <p><strong>Success Rate:</strong> {health.success_rate:.1f}% ({health.successful_fetches}/{health.total_fetches} fetches)</p>
        <p><strong>Average Response Time:</strong> {health.avg_response_time:.2f}s</p>
        <p><strong>Consecutive Failures:</strong> {health.consecutive_failures}</p>
        """

        if health.last_error:
            html += f'<div class="alert alert-warning"><strong>Last Error:</strong> {health.last_error}</div>'
    else:
        html += '<div class="alert alert-info">No health data available yet.</div>'

    return html

@router.get("/feed-types-options", response_class=HTMLResponse)
def get_feed_types_options(session: Session = Depends(get_session)):
    feed_types = session.exec(select(FeedType)).all()
    html = '<option value="">Auto-detect</option>'
    for feed_type in feed_types:
        html += f'<option value="{feed_type.id}">{feed_type.name.replace("_", " ").title()}</option>'
    return html

@router.post("/feed-url-test", response_class=HTMLResponse)
def test_feed_url(url: str, session: Session = Depends(get_session)):
    """Test a feed URL and return preview"""
    import feedparser

    try:
        # Parse the feed
        parsed = feedparser.parse(url)

        if parsed.bozo and parsed.bozo_exception:
            return f'<div class="alert alert-warning">⚠️ Feed has parsing issues: {parsed.bozo_exception}</div>'

        if not parsed.entries:
            return '<div class="alert alert-danger">❌ No entries found in feed</div>'

        # Use detector to get recommendations
        detector = FeedTypeDetector()
        detected_type = detector.detect_feed_type(url, str(parsed))

        html = f'''
        <div class="alert alert-success">
            ✅ Feed is valid! Found {len(parsed.entries)} entries.
        </div>
        <div class="card">
            <div class="card-header"><strong>Feed Preview</strong></div>
            <div class="card-body">
                <p><strong>Title:</strong> {parsed.feed.get('title', 'No title')}</p>
                <p><strong>Description:</strong> {parsed.feed.get('description', 'No description')}</p>
                <p><strong>Detected Type:</strong> <span class="badge bg-info">{detected_type}</span></p>
                <p><strong>Recommended Interval:</strong> {detector.get_recommended_interval(detected_type)} minutes</p>

                <h6>Recent Entries:</h6>
                <ul class="list-group list-group-flush">
        '''

        # Show first 3 entries
        for entry in parsed.entries[:3]:
            title = entry.get('title', 'No title')
            published = entry.get('published', 'No date')
            html += f'<li class="list-group-item"><strong>{title}</strong><br><small class="text-muted">{published}</small></li>'

        html += '''
                </ul>
            </div>
        </div>
        '''

        return html

    except Exception as e:
        return f'<div class="alert alert-danger">❌ Error testing feed: {str(e)}</div>'

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
                        <label class="form-label">Feed Type</label>
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