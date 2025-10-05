from fastapi import APIRouter, Depends, Query, Request, HTTPException
from fastapi.responses import HTMLResponse
from sqlmodel import Session, select, func
from typing import Optional
from app.core.logging_config import get_logger
from fastapi.templating import Jinja2Templates

from app.database import get_session
from app.models import Feed, Source, Category, Item, FeedHealth, FeedCategory, FeedProcessorConfig, ProcessorTemplate, ProcessorType, FeedType
from app.utils.feed_detector import FeedTypeDetector
from app.services.feed_health_service import FeedHealthScorer, update_all_feed_health_scores
from app.dependencies import get_feed_service

router = APIRouter(tags=["htmx-feeds"])
logger = get_logger(__name__)
templates = Jinja2Templates(directory="templates")

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

@router.post("/feed-toggle-status/{feed_id}", response_class=HTMLResponse)
def toggle_feed_status(feed_id: int, session: Session = Depends(get_session)):
    """HTMX endpoint to toggle feed active/inactive status"""
    try:
        feed = session.get(Feed, feed_id)
        if not feed:
            return '<div class="alert alert-danger">Feed not found</div>'

        # Toggle status between active and inactive
        from app.models.core import FeedStatus
        if feed.status == FeedStatus.ACTIVE:
            feed.status = FeedStatus.INACTIVE
        else:
            feed.status = FeedStatus.ACTIVE

        session.commit()
        session.refresh(feed)

        logger.info(f"Toggled status for feed {feed_id} to {feed.status.value}")

        return get_feeds_list(session)

    except Exception as e:
        logger.error(f"Error toggling feed status: {e}")
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
        geopolitical_stats = None

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

                # Get geopolitical analysis summary
                geo_query = text("""
                    SELECT
                        COUNT(*) as geo_count,
                        sentiment_json->'geopolitical'->>'conflict_type' as conflict_type,
                        ROUND(AVG((sentiment_json->'geopolitical'->>'security_relevance')::numeric), 2) as avg_security,
                        ROUND(AVG((sentiment_json->'geopolitical'->>'escalation_potential')::numeric), 2) as avg_escalation,
                        ROUND(AVG((sentiment_json->'geopolitical'->>'stability_score')::numeric), 2) as avg_stability
                    FROM item_analysis ia
                    JOIN items i ON ia.item_id = i.id
                    WHERE i.feed_id = :feed_id
                        AND ia.sentiment_json->'geopolitical'->>'conflict_type' IS NOT NULL
                    GROUP BY sentiment_json->'geopolitical'->>'conflict_type'
                    ORDER BY geo_count DESC
                    LIMIT 3
                """)

                with session.get_bind().connect() as conn:
                    geo_results = conn.execute(geo_query, {"feed_id": feed.id}).fetchall()
                    if geo_results:
                        geopolitical_stats = {
                            'total_geo_articles': sum(row[0] for row in geo_results),
                            'conflict_types': []
                        }
                        for row in geo_results:
                            geopolitical_stats['conflict_types'].append({
                                'type': row[1],
                                'count': row[0],
                                'avg_security': float(row[2]) if row[2] else 0,
                                'avg_escalation': float(row[3]) if row[3] else 0,
                                'avg_stability': float(row[4]) if row[4] else 0
                            })

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

        # Build geopolitical summary
        geopolitical_info = ""
        logger.info(f"Feed {feed.id}: geopolitical_stats = {geopolitical_stats}")
        if geopolitical_stats and geopolitical_stats.get('total_geo_articles', 0) > 0:
            total_geo = geopolitical_stats['total_geo_articles']
            conflict_types = geopolitical_stats['conflict_types']

            # Build conflict type badges
            conflict_badges = ""
            for conflict in conflict_types[:3]:  # Show max 3 conflict types
                conflict_type = conflict['type'].replace('_', ' ').title()
                count = conflict['count']
                security = conflict['avg_security']
                escalation = conflict['avg_escalation']
                stability = conflict['avg_stability']

                # Color based on escalation potential
                badge_color = 'danger' if escalation > 0.6 else 'warning' if escalation > 0.3 else 'info'

                conflict_badges += f'''
                    <span class="badge bg-{badge_color} me-1"
                          title="Security: {security:.2f} | Escalation: {escalation:.2f} | Stability: {stability:.2f}">
                        {conflict_type}: {count}
                    </span>
                '''

            geopolitical_info = f'''
                <div class="mt-2 p-2 rounded" style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); color: white;">
                    <div class="d-flex justify-content-between align-items-center mb-1">
                        <small><strong>🌍 Geopolitical Analysis ({total_geo} articles):</strong></small>
                    </div>
                    <div>{conflict_badges}</div>
                </div>
            '''

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
                        {geopolitical_info}
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
                                hx-post="/htmx/feed-toggle-status/{feed.id}"
                                hx-target="#feeds-list"
                                hx-swap="innerHTML"
                                title="Toggle active/inactive">
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

            <hr class="my-4">
            <h6 class="mb-3"><i class="bi bi-globe me-2"></i>Content Scraping</h6>

            <div class="mb-3">
                <div class="form-check form-switch">
                    <input class="form-check-input" type="checkbox" name="scrape_full_content" id="scrape_full_content"
                           {'checked' if feed.scrape_full_content else ''}>
                    <label class="form-check-label" for="scrape_full_content">
                        <strong>Scrape Full Content</strong>
                        <div class="text-muted small">Extract full article text from URLs (increases fetch time)</div>
                    </label>
                </div>
            </div>

            <div class="mb-3">
                <label class="form-label">Scrape Method</label>
                <select class="form-select" name="scrape_method">
                    <option value="auto" {'selected' if feed.scrape_method == 'auto' else ''}>Auto (httpx → Playwright fallback)</option>
                    <option value="httpx" {'selected' if feed.scrape_method == 'httpx' else ''}>httpx only (fast)</option>
                </select>
                <div class="form-text">Auto mode falls back to Playwright for JavaScript-heavy sites</div>
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


# ========== NEW V2 HTMX ROUTES ==========

@router.get("/feeds/list", response_class=HTMLResponse)
def get_feeds_list_v2(
    request: Request,
    filter: str = "all",
    sort: str = "health",
    search: str = None,
    session: Session = Depends(get_session)
):
    """V2 feed list with filters and sorting"""
    from app.models.core import FeedStatus

    query = select(Feed)

    # Apply filters
    if filter == "active":
        query = query.where(Feed.status == FeedStatus.ACTIVE)
    elif filter == "inactive":
        query = query.where(Feed.status == FeedStatus.INACTIVE)
    elif filter == "errors":
        query = query.where(Feed.status == FeedStatus.ERROR)

    # Apply search
    if search:
        query = query.where(
            (Feed.title.contains(search)) | (Feed.url.contains(search)) | (Feed.source_label.contains(search))
        )

    # Apply sorting
    if sort == "health":
        query = query.order_by(Feed.health_score.desc().nulls_last())
    elif sort == "name":
        query = query.order_by(Feed.title.asc().nulls_last())
    elif sort == "activity":
        query = query.order_by(Feed.last_fetched.desc().nulls_last())
    elif sort == "volume":
        query = query.order_by(Feed.articles_24h.desc().nulls_last())
    elif sort == "created":
        query = query.order_by(Feed.created_at.desc().nulls_last())

    feeds = session.exec(query).all()

    return templates.TemplateResponse(
        "admin/partials/feed_list.html",
        {"request": request, "feeds": feeds}
    )


@router.get("/feeds/search", response_class=HTMLResponse)
def search_feeds_v2(
    request: Request,
    search: str = "",
    filter: str = "all",
    session: Session = Depends(get_session)
):
    """Search feeds endpoint"""
    return get_feeds_list_v2(request, filter=filter, search=search, session=session)


@router.get("/feeds/{feed_id}/detail", response_class=HTMLResponse)
def get_feed_detail_v2(
    request: Request,
    feed_id: int,
    session: Session = Depends(get_session)
):
    """Get feed detail panel"""
    feed = session.get(Feed, feed_id)

    return templates.TemplateResponse(
        "admin/partials/feed_detail.html",
        {"request": request, "feed": feed}
    )


@router.post("/feeds/{feed_id}/fetch", response_class=HTMLResponse)
def fetch_feed_v2(
    request: Request,
    feed_id: int,
    session: Session = Depends(get_session)
):
    """Fetch feed and return updated detail panel"""
    try:
        from app.services.feed_fetcher_sync import SyncFeedFetcher

        feed = session.get(Feed, feed_id)
        if not feed:
            return '<div class="alert alert-danger">Feed not found</div>'

        fetcher = SyncFeedFetcher()
        success, items_count = fetcher.fetch_feed_sync(feed_id)

        # Refresh feed object
        session.refresh(feed)

        return templates.TemplateResponse(
            "admin/partials/feed_detail.html",
            {"request": request, "feed": feed}
        )
    except Exception as e:
        logger.error(f"Error fetching feed {feed_id}: {e}")
        return f'<div class="alert alert-danger">Error: {str(e)}</div>'


@router.post("/feeds/{feed_id}/toggle-status", response_class=HTMLResponse)
def toggle_feed_status_v2(
    request: Request,
    feed_id: int,
    session: Session = Depends(get_session)
):
    """Toggle feed status and return updated detail panel"""
    try:
        feed = session.get(Feed, feed_id)
        if not feed:
            return '<div class="alert alert-danger">Feed not found</div>'

        from app.models.core import FeedStatus
        feed.status = FeedStatus.INACTIVE if feed.status == FeedStatus.ACTIVE else FeedStatus.ACTIVE

        session.commit()
        session.refresh(feed)

        return templates.TemplateResponse(
            "admin/partials/feed_detail.html",
            {"request": request, "feed": feed}
        )
    except Exception as e:
        logger.error(f"Error toggling feed status: {e}")
        return f'<div class="alert alert-danger">Error: {str(e)}</div>'


@router.get("/feeds/{feed_id}/health-report", response_class=HTMLResponse)
def get_health_report_v2(
    feed_id: int,
    session: Session = Depends(get_session)
):
    """Get detailed health report for feed"""
    scorer = FeedHealthScorer(session)
    report = scorer.calculate_health_score(feed_id)

    html = f'''
    <div class="health-report">
        <div class="mb-3">
            <h6>Overall Health: {report["score"]}/100</h6>
            <div class="progress" style="height: 30px;">
                <div class="progress-bar {'bg-success' if report['score'] >= 80 else 'bg-warning' if report['score'] >= 60 else 'bg-danger'}"
                     style="width: {report['score']}%">
                    {report['score']}%
                </div>
            </div>
            <p class="text-muted mt-2">{report['recommendation']}</p>
        </div>

        <h6>Component Scores</h6>
        <table class="table table-sm">
            <thead>
                <tr>
                    <th>Component</th>
                    <th>Score</th>
                    <th>Weight</th>
                </tr>
            </thead>
            <tbody>
    '''

    for name, data in report['components'].items():
        html += f'''
                <tr>
                    <td class="text-capitalize">{name}</td>
                    <td>
                        <div class="progress" style="width: 100px; height: 20px;">
                            <div class="progress-bar {'bg-success' if data['score'] >= 80 else 'bg-warning' if data['score'] >= 60 else 'bg-danger'}"
                                 style="width: {data['score']}%">
                                {int(data['score'])}
                            </div>
                        </div>
                    </td>
                    <td>{data['weight']}%</td>
                </tr>
        '''

    html += '''
            </tbody>
        </table>
    </div>
    '''

    return html


@router.get("/feeds/{feed_id}/preview", response_class=HTMLResponse)
def get_feed_preview_v2(
    feed_id: int,
    session: Session = Depends(get_session)
):
    """Preview recent articles from feed"""
    items = session.exec(
        select(Item)
        .where(Item.feed_id == feed_id)
        .order_by(Item.created_at.desc())
        .limit(10)
    ).all()

    html = '<div class="list-group">'
    for item in items:
        html += f'''
        <div class="list-group-item">
            <h6 class="mb-1">{item.title or "No title"}</h6>
            <p class="mb-1 text-muted small">{item.created_at.strftime("%Y-%m-%d %H:%M") if item.created_at else "N/A"}</p>
            <a href="{item.link}" target="_blank" class="small">View Article →</a>
        </div>
        '''
    html += '</div>'

    return html if items else '<p class="text-muted">No articles found</p>'


@router.post("/feeds/refresh-all", response_class=HTMLResponse)
def refresh_all_feeds_v2(
    request: Request,
    session: Session = Depends(get_session)
):
    """Refresh all active feeds"""
    # This would trigger background job - for now just return list
    return get_feeds_list_v2(request, session=session)


@router.post("/feeds/health-check", response_class=HTMLResponse)
def health_check_all_v2(
    request: Request,
    session: Session = Depends(get_session)
):
    """Run health check on all feeds"""
    updated_count = update_all_feed_health_scores(session)
    logger.info(f"Updated health scores for {updated_count} feeds")

    return get_feeds_list_v2(request, session=session)


@router.post("/feeds/create", response_class=HTMLResponse)
async def create_feed_v2(
    request: Request,
    session: Session = Depends(get_session),
    feed_service: "FeedService" = Depends(get_feed_service)
):
    """Create new feed via HTMX form (JSON body)"""
    from app.schemas.feeds import FeedCreate, FeedUpdate
    from app.models import SourceType, Source
    from sqlmodel import select
    import json

    # Parse JSON body
    body = await request.body()
    data = json.loads(body.decode())

    # Get or create source
    source_id = None
    source_label = data.get("source_label", "").strip()

    if source_label:
        existing_source = session.exec(
            select(Source).where(Source.name == source_label)
        ).first()
        if existing_source:
            source_id = existing_source.id
        else:
            new_source = Source(name=source_label, type=SourceType.RSS)
            session.add(new_source)
            session.commit()
            session.refresh(new_source)
            source_id = new_source.id
    else:
        # Use default RSS source
        default_source = session.exec(
            select(Source).where(Source.type == SourceType.RSS)
        ).first()
        if default_source:
            source_id = default_source.id

    if not source_id:
        raise HTTPException(status_code=400, detail="No source available")

    # Create feed
    feed_data = FeedCreate(
        url=data.get("url"),
        title=data.get("title") or None,
        description=data.get("description") or None,
        fetch_interval_minutes=int(data.get("fetch_interval_minutes", 60)),
        source_id=source_id,
        auto_analyze_enabled=bool(data.get("auto_analyze_enabled"))
    )

    result = feed_service.create(feed_data)

    if not result.success:
        raise HTTPException(status_code=400, detail=result.error)

    # Handle category assignment
    category_id = data.get("category_id")
    if category_id and str(category_id).strip():
        from app.models import FeedCategory
        feed_category = FeedCategory(
            feed_id=result.data.id,
            category_id=int(category_id)
        )
        session.add(feed_category)
        session.commit()

    # Return updated feed list
    return get_feeds_list_v2(request, session=session)


@router.get("/feeds/{feed_id}/edit-data")
async def get_feed_edit_data(
    feed_id: int,
    session: Session = Depends(get_session)
):
    """Get feed data for edit modal (JSON response)"""
    feed = session.get(Feed, feed_id)
    if not feed:
        raise HTTPException(status_code=404, detail="Feed not found")

    # Get source name
    from app.models.feeds import Source
    source = session.get(Source, feed.source_id) if feed.source_id else None
    source_name = source.name if source else (feed.source_label or "")

    # Get category_id if exists
    category_stmt = select(FeedCategory.category_id).where(FeedCategory.feed_id == feed_id)
    category_result = session.exec(category_stmt).first()

    return {
        "id": feed.id,
        "url": feed.url,
        "title": feed.title,
        "source_label": source_name,
        "description": feed.description,
        "fetch_interval_minutes": feed.fetch_interval_minutes,
        "auto_analyze_enabled": feed.auto_analyze_enabled,
        "is_critical": feed.is_critical,
        "category_id": category_result if category_result else None
    }


@router.put("/feeds/{feed_id}/update", response_class=HTMLResponse)
async def update_feed_v2(
    feed_id: int,
    request: Request,
    session: Session = Depends(get_session),
    feed_service: "FeedService" = Depends(get_feed_service)
):
    """Update feed via HTMX form (JSON body)"""
    from app.schemas.feeds import FeedUpdate
    import json

    # Parse JSON body
    body = await request.body()
    data = json.loads(body.decode())

    # Build update data
    update_data = FeedUpdate(
        title=data.get("title") or None,
        description=data.get("description") or None,
        fetch_interval_minutes=int(data.get("fetch_interval_minutes", 60)),
        auto_analyze_enabled=bool(data.get("auto_analyze_enabled"))
    )

    result = feed_service.update(feed_id, update_data)

    if not result.success:
        raise HTTPException(status_code=400, detail=result.error)

    # Update is_critical and source_label separately (not in FeedUpdate schema yet)
    feed = session.get(Feed, feed_id)
    if feed:
        feed.is_critical = bool(data.get("is_critical", False))
        # Update source_label if provided
        if "source_label" in data and data["source_label"]:
            feed.source_label = data["source_label"]
        session.commit()

    # Return updated detail panel
    return get_feed_detail_v2(request, feed_id, session)


@router.get("/feeds/{feed_id}/delete-preflight")
async def preflight_delete_feed(
    feed_id: int,
    session: Session = Depends(get_session)
):
    """Check what will be deleted and if feed is critical"""
    feed = session.get(Feed, feed_id)
    if not feed:
        raise HTTPException(status_code=404, detail="Feed not found")

    # Count referential data
    items_count = session.exec(select(func.count(Item.id)).where(Item.feed_id == feed_id)).one()

    # Check for processor configs
    processor_configs_count = session.exec(
        select(func.count(FeedProcessorConfig.id)).where(FeedProcessorConfig.feed_id == feed_id)
    ).one()

    # Check for feed categories
    categories_count = session.exec(
        select(func.count(FeedCategory.id)).where(FeedCategory.feed_id == feed_id)
    ).one()

    # Check for feed health records
    health_count = session.exec(
        select(func.count(FeedHealth.id)).where(FeedHealth.feed_id == feed_id)
    ).one()

    # Policy A (Strict): is_critical blocks delete if ANY references exist
    can_delete = True
    block_reason = None

    if feed.is_critical:
        total_refs = items_count + processor_configs_count + categories_count + health_count
        if total_refs > 0:
            can_delete = False
            block_reason = "Feed is marked as CRITICAL and has referenced data"

    # Check if archived (recommended workflow)
    is_archived = feed.archived_at is not None

    return {
        "feed_id": feed_id,
        "feed_title": feed.title or feed.url,
        "is_critical": feed.is_critical,
        "is_archived": is_archived,
        "can_delete": can_delete,
        "block_reason": block_reason,
        "references": {
            "items": items_count,
            "processor_configs": processor_configs_count,
            "categories": categories_count,
            "health_records": health_count,
            "total": items_count + processor_configs_count + categories_count + health_count
        }
    }


@router.post("/feeds/{feed_id}/archive", response_class=HTMLResponse)
async def archive_feed(
    feed_id: int,
    request: Request,
    session: Session = Depends(get_session)
):
    """Archive a feed (one-way transition, sets archived_at timestamp)"""
    from datetime import datetime, timezone

    feed = session.get(Feed, feed_id)
    if not feed:
        raise HTTPException(status_code=404, detail="Feed not found")

    # Check if already archived
    if feed.archived_at:
        raise HTTPException(status_code=400, detail="Feed is already archived")

    # Set archived timestamp (one-way transition)
    feed.archived_at = datetime.now(timezone.utc)

    # Also deactivate the feed
    from app.models.core import FeedStatus
    feed.status = FeedStatus.INACTIVE

    session.commit()
    session.refresh(feed)

    logger.info(f"Feed {feed_id} archived at {feed.archived_at}")

    # Return updated detail panel
    return get_feed_detail_v2(request, feed_id, session)


@router.delete("/feeds/{feed_id}", response_class=HTMLResponse)
def delete_feed_v2(
    feed_id: int,
    request: Request,
    session: Session = Depends(get_session),
    feed_service: "FeedService" = Depends(get_feed_service)
):
    """Delete feed"""
    result = feed_service.delete(feed_id)

    if not result.success:
        raise HTTPException(status_code=400, detail=result.error)

    # Return updated feed list
    return get_feeds_list_v2(request, session=session)