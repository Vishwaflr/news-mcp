"""Feed management HTMX components."""

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse
from sqlmodel import Session, select
from typing import Optional
from app.core.logging_config import get_logger

from app.database import get_session
from app.models import Feed, Source, Category, Item, FeedHealth, FeedCategory, FeedType, FeedStatus
from app.utils.feed_detector import FeedTypeDetector
from .base_component import BaseComponent
import feedparser

router = APIRouter(tags=["htmx-feeds"])
logger = get_logger(__name__)


class FeedComponent(BaseComponent):
    """Component for feed-related HTMX endpoints."""

    @staticmethod
    def build_feed_card(feed: Feed, source: Source, categories: list, article_count: int, analysis_stats: dict = None, auto_analysis_only: str = None, latest_article_date = None, geopolitical_stats: dict = None) -> str:
        """Build HTML for a single feed card."""
        has_articles = article_count > 0
        status_badge = FeedComponent.status_badge(feed.status.value)
        category_badges = FeedComponent.category_badges(categories)

        # Build edit URL with optional query parameter
        edit_url = f'/htmx/feed-edit-form/{feed.id}'
        if auto_analysis_only:
            edit_url += f'?auto_analysis_only={auto_analysis_only}'

        # Article count badge
        article_badge = (
            f'<span class="badge bg-info ms-1">{article_count} Articles</span>'
            if has_articles else
            '<span class="badge bg-warning ms-1">No Articles</span>'
        )

        # Analysis statistics badge
        analysis_badge = ""
        if analysis_stats and analysis_stats.get('analyzed_count', 0) > 0:
            analyzed_count = analysis_stats['analyzed_count']
            total_count = article_count
            percentage = int((analyzed_count / total_count) * 100) if total_count > 0 else 0
            analysis_badge = f'<span class="badge bg-success ms-1">{analyzed_count} Analyzed ({percentage}%)</span>'
        elif has_articles:
            analysis_badge = '<span class="badge bg-secondary ms-1">Not Analyzed</span>'

        # Auto-analysis badge
        auto_analysis_badge = ""
        if hasattr(feed, 'auto_analyze_enabled') and feed.auto_analyze_enabled:
            auto_analysis_badge = '<span class="badge bg-info ms-1" title="Auto-analysis enabled for new articles"><i class="bi bi-robot"></i> Auto</span>'

        # Load button for feeds without articles
        load_button = ""
        if not has_articles:
            load_button = FeedComponent.load_button(feed.id)

        # Action buttons
        buttons = [
            {
                'classes': 'btn btn-sm btn-outline-primary',
                'attrs': {
                    'hx-get': f'/htmx/feed-health/{feed.id}',
                    'hx-target': '#health-modal-content',
                    'data-bs-toggle': 'modal',
                    'data-bs-target': '#healthModal'
                },
                'icon': 'heart-pulse'
            },
            {
                'classes': 'btn btn-sm btn-outline-secondary',
                'attrs': {
                    'hx-get': edit_url,
                    'hx-target': '#edit-modal-content',
                    'data-bs-toggle': 'modal',
                    'data-bs-target': '#editFeedModal'
                },
                'icon': 'pencil'
            }
        ]

        toggle_status = 'inactive' if feed.status.value == 'active' else 'active'
        toggle_icon = 'pause' if feed.status.value == 'active' else 'play'
        toggle_color = 'success' if feed.status.value == 'active' else 'warning'
        toggle_title = 'Deactivate feed' if feed.status.value == 'active' else 'Activate feed'

        # Add fetch now, toggle and delete buttons
        action_buttons = f'''
        {load_button}
        <button class="btn btn-sm btn-outline-info"
                hx-post="/api/feeds/{feed.id}/fetch"
                hx-target="closest .card"
                hx-swap="outerHTML"
                title="Fetch new articles now">
            <i class="bi bi-download"></i>
        </button>
        <button class="btn btn-sm btn-outline-{toggle_color}"
                hx-post="/htmx/feed-toggle-status/{feed.id}"
                title="{toggle_title}">
            <i class="bi bi-{toggle_icon}"></i>
        </button>
        <button class="btn btn-sm btn-outline-danger"
                hx-delete="/api/feeds/{feed.id}"
                hx-target="#feeds-list"
                hx-confirm="Really delete feed?">
            <i class="bi bi-trash"></i>
        </button>
        '''

        # Combine last fetch and latest article in one line
        last_fetch_text = (
            f'<strong>Last Fetch:</strong> {FeedComponent.format_date(feed.last_fetched)}'
            if feed.last_fetched else
            '<strong>Last Fetch:</strong> <span class="text-warning">Never</span>'
        )

        latest_article_text = (
            f' | <strong>Latest Article:</strong> {FeedComponent.format_date(latest_article_date)}'
            if latest_article_date else
            ''
        )

        fetch_info = f'<p class="card-text small text-muted">{last_fetch_text}{latest_article_text}</p>'

        return f'''
        <div class="card mb-2">
            <div class="card-body">
                <div class="d-flex justify-content-between align-items-start">
                    <div>
                        <h6 class="card-title mb-1">
                            {feed.title or 'Untitled Feed'}
                            {status_badge}
                            {article_badge}
                            {analysis_badge}
                            {auto_analysis_badge}
                            {category_badges}
                        </h6>
                        <p class="card-text small text-muted mb-1">
                            <strong>URL:</strong> <a href="{feed.url}" target="_blank" class="text-decoration-none">{feed.url}</a>
                        </p>
                        <p class="card-text small text-muted mb-1">
                            <strong>Source:</strong> {source.name} |
                            <strong>Interval:</strong> {feed.fetch_interval_minutes} min
                        </p>
                        {FeedComponent.analysis_summary(analysis_stats)}
                        {FeedComponent.geopolitical_summary(geopolitical_stats)}
                        {fetch_info}
                        <div id="fetch-status-{feed.id}"></div>
                    </div>
                    <div class="btn-group">
                        {FeedComponent.button_group(buttons)}
                        {action_buttons}
                    </div>
                </div>
            </div>
        </div>
        '''

    @staticmethod
    def analysis_summary(analysis_stats: dict) -> str:
        """Build HTML for financial analysis statistics summary."""
        # Always show analysis section, even when no data available
        stats = analysis_stats or {}
        sentiment_counts = stats.get('sentiment_counts', {})
        avg_impact = stats.get('avg_impact_score', 0)
        analyzed_count = stats.get('analyzed_count', 0)

        # Total articles badge
        articles_badge = f'<span class="badge bg-info me-1">Articles: {analyzed_count}</span>'

        # Sentiment distribution - show all sentiment types even if 0
        sentiment_badges = ""
        all_sentiments = {'positive': 'success', 'negative': 'danger', 'neutral': 'secondary'}
        for sentiment, color in all_sentiments.items():
            count = sentiment_counts.get(sentiment, 0)
            sentiment_badges += f'<span class="badge bg-{color} me-1">{sentiment.title()}: {count}</span>'

        # Impact score badge
        impact_color = 'success' if avg_impact >= 7 else 'warning' if avg_impact >= 4 else 'secondary'
        impact_badge = f'<span class="badge bg-{impact_color} me-1">Impact: {avg_impact:.1f}/10</span>'

        return f'''
        <p class="card-text small text-muted mb-1">
            <strong>Financial Analysis:</strong> {articles_badge} {sentiment_badges} {impact_badge}
        </p>
        '''

    @staticmethod
    def geopolitical_summary(geopolitical_stats: dict) -> str:
        """Build HTML for geopolitical analysis summary."""
        if not geopolitical_stats or geopolitical_stats.get('total_geo_articles', 0) == 0:
            return ""

        total_geo = geopolitical_stats['total_geo_articles']
        conflict_types = geopolitical_stats.get('conflict_types', [])

        # Total articles badge
        articles_badge = f'<span class="badge bg-info me-1">Articles: {total_geo}</span>'

        # Calculate aggregated metrics across all conflict types
        total_count = sum(c['count'] for c in conflict_types)
        avg_security = sum(c['avg_security'] * c['count'] for c in conflict_types) / total_count if total_count > 0 else 0
        avg_escalation = sum(c['avg_escalation'] * c['count'] for c in conflict_types) / total_count if total_count > 0 else 0
        avg_stability = sum(c['avg_stability'] * c['count'] for c in conflict_types) / total_count if total_count > 0 else 0

        # Conflict type distribution badges
        conflict_badges = ""
        conflict_type_names = {
            'diplomatic': 'Diplomatic',
            'economic': 'Economic',
            'interstate_war': 'Military',
            'military': 'Military'
        }

        for conflict in conflict_types[:3]:  # Show max 3 conflict types
            conflict_type = conflict_type_names.get(conflict['type'].lower(), conflict['type'].replace('_', ' ').title())
            count = conflict['count']
            conflict_badges += f'<span class="badge bg-secondary me-1">{conflict_type}: {count}</span>'

        # Metric badges with color coding
        # Security relevance: higher is more relevant (0-1 scale)
        security_color = 'danger' if avg_security > 0.6 else 'warning' if avg_security > 0.3 else 'success'
        security_badge = f'<span class="badge bg-{security_color} me-1" title="Relevance to security topics">Security: {avg_security:.1f}/1.0</span>'

        # Escalation potential: higher is more dangerous (0-1 scale)
        escalation_color = 'danger' if avg_escalation > 0.6 else 'warning' if avg_escalation > 0.3 else 'success'
        escalation_badge = f'<span class="badge bg-{escalation_color} me-1" title="Risk of escalation">Risk: {avg_escalation:.1f}/1.0</span>'

        # Stability score: more negative = less stable (-1 to +1 scale)
        stability_color = 'danger' if avg_stability < -0.3 else 'warning' if avg_stability < 0 else 'success'
        stability_badge = f'<span class="badge bg-{stability_color} me-1" title="Regional stability impact">Stability: {avg_stability:+.1f}</span>'

        return f'''
        <p class="card-text small text-muted mb-1">
            <strong>Geopolitical Analysis:</strong> {articles_badge} {conflict_badges} {security_badge} {escalation_badge} {stability_badge}
        </p>
        '''


@router.get("/sources-options", response_class=HTMLResponse)
def get_sources_options(session: Session = Depends(get_session)):
    """Get HTML options for source select dropdown."""
    try:
        from sqlmodel import text
        results = session.execute(
            text("SELECT id, name FROM sources ORDER BY name")
        ).fetchall()

        html = ""
        for row in results:
            html += f'<option value="{row[0]}">{row[1]}</option>'
        return html
    except Exception as e:
        logger.error(f"Failed to get sources: {e}")
        return '<option value="">Error loading sources</option>'


@router.get("/categories-options", response_class=HTMLResponse)
def get_categories_options(session: Session = Depends(get_session)):
    """Get HTML options for category select dropdown."""
    try:
        from sqlmodel import text
        results = session.execute(
            text("SELECT id, name FROM categories ORDER BY name")
        ).fetchall()

        html = ""
        for row in results:
            html += f'<option value="{row[0]}">{row[1]}</option>'
        return html
    except Exception as e:
        logger.error(f"Failed to get categories: {e}")
        return '<option value="">Error loading categories</option>'


@router.get("/feeds-options", response_class=HTMLResponse)
def get_feeds_options(session: Session = Depends(get_session)):
    """Get HTML options for feed select dropdown."""
    try:
        from sqlmodel import text
        results = session.execute(
            text("SELECT id, title, url FROM feeds ORDER BY title")
        ).fetchall()

        html = ""
        for row in results:
            title = row[1] or (row[2][:50] + "..." if len(row[2]) > 50 else row[2])
            html += f'<option value="{row[0]}">{title}</option>'
        return html
    except Exception as e:
        logger.error(f"Failed to get feeds: {e}")
        return '<option value="">Error loading feeds</option>'


@router.post("/feed-fetch-now/{feed_id}", response_class=HTMLResponse)
def fetch_feed_now_htmx(feed_id: int, session: Session = Depends(get_session)):
    """HTMX endpoint to fetch a feed immediately and return status."""
    try:
        from app.services.feed_fetcher_sync import SyncFeedFetcher

        feed = session.get(Feed, feed_id)
        if not feed:
            return BaseComponent.alert_box('Feed not found', 'danger')

        logger.info(f"HTMX immediate fetch requested for feed {feed_id}: {feed.title}")

        fetcher = SyncFeedFetcher()
        success, items_count = fetcher.fetch_feed_sync(feed_id)

        if success:
            if items_count > 0:
                return BaseComponent.alert_box(f'✅ {items_count} new articles loaded!', 'success')
            else:
                return BaseComponent.alert_box('✅ Feed fetched successfully (no new articles)', 'info')
        else:
            return BaseComponent.alert_box('❌ Error loading articles', 'warning')

    except Exception as e:
        logger.error(f"Error in HTMX feed fetch: {e}")
        return BaseComponent.alert_box(f'❌ Error: {str(e)}', 'danger')


@router.post("/feed-toggle-status/{feed_id}", response_class=HTMLResponse)
def toggle_feed_status(feed_id: int, request: Request, session: Session = Depends(get_session)):
    """HTMX endpoint to toggle feed active/inactive status."""
    try:
        feed = session.get(Feed, feed_id)
        if not feed:
            return BaseComponent.alert_box('Feed not found', 'danger')

        # Toggle status between ACTIVE and INACTIVE
        if feed.status == FeedStatus.ACTIVE:
            feed.status = FeedStatus.INACTIVE
            new_status_text = "inactive"
        else:
            feed.status = FeedStatus.ACTIVE
            new_status_text = "active"

        session.commit()
        session.refresh(feed)

        logger.info(f"Toggled status for feed {feed_id} ({feed.title}) to {feed.status.value}")

        # Return success message with HX-Refresh header to reload the page
        from fastapi.responses import Response
        response = Response(
            content=BaseComponent.alert_box(f'✅ Feed status changed to {new_status_text}', 'success'),
            media_type="text/html"
        )
        response.headers["HX-Refresh"] = "true"
        return response

    except Exception as e:
        logger.error(f"Error toggling feed status: {e}")
        return BaseComponent.alert_box(f'❌ Error: {str(e)}', 'danger')


@router.get("/feeds-list", response_class=HTMLResponse)
def get_feeds_list(
    session: Session = Depends(get_session),
    category_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    auto_analysis_only: Optional[str] = Query(None)
):
    """Get filtered HTML list of feeds."""
    try:
        from sqlmodel import text
        from dataclasses import dataclass
        from datetime import datetime
        from enum import Enum

        # Build SQL query with filters
        conditions = []
        params = {}

        if category_id and category_id > 0:
            conditions.append("EXISTS (SELECT 1 FROM feed_categories fc WHERE fc.feed_id = f.id AND fc.category_id = :category_id)")
            params["category_id"] = category_id

        if status and status.strip():
            conditions.append("f.status = :status")
            params["status"] = status.strip()

        if auto_analysis_only and auto_analysis_only.lower() in ["true", "1", "yes"]:
            conditions.append("f.auto_analyze_enabled = true")

        where_clause = ""
        if conditions:
            where_clause = "WHERE " + " AND ".join(conditions)

        # Get feeds with sources
        sql = f"""
        SELECT
            f.id, f.url, f.title, f.description, f.status, f.fetch_interval_minutes,
            f.last_fetched, f.next_fetch_scheduled, f.last_modified, f.etag,
            f.configuration_hash, f.source_id, f.feed_type_id, f.auto_analyze_enabled, f.created_at, f.updated_at,
            s.id as source_id, s.name as source_name, s.type as source_type, s.description as source_description
        FROM feeds f
        JOIN sources s ON s.id = f.source_id
        {where_clause}
        ORDER BY f.created_at DESC
        """

        feed_results = session.execute(text(sql), params).fetchall()

        html = ""
        for row in feed_results:
            # Create feed-like object from row data
            class MockFeed:
                def __init__(self, row):
                    self.id = row[0]
                    self.url = row[1]
                    self.title = row[2]
                    self.description = row[3]
                    self.status = MockStatus(row[4])
                    self.fetch_interval_minutes = row[5]
                    self.last_fetched = row[6]
                    self.next_fetch_scheduled = row[7]
                    self.last_modified = row[8]
                    self.etag = row[9]
                    self.configuration_hash = row[10]
                    self.source_id = row[11]
                    self.feed_type_id = row[12]
                    self.auto_analyze_enabled = row[13]

            class MockStatus:
                def __init__(self, value):
                    self.value = value

            class MockSource:
                def __init__(self, row):
                    self.id = row[16]
                    self.name = row[17]
                    self.type = row[18]
                    self.description = row[19]

            feed = MockFeed(row)
            source = MockSource(row)

            # Get feed categories
            cat_sql = """
            SELECT c.id, c.name, c.description, c.color
            FROM categories c
            JOIN feed_categories fc ON fc.category_id = c.id
            WHERE fc.feed_id = :feed_id
            """
            cat_results = session.execute(text(cat_sql), {"feed_id": feed.id}).fetchall()

            class MockCategory:
                def __init__(self, row):
                    self.id = row[0]
                    self.name = row[1]
                    self.description = row[2]
                    self.color = row[3]

            feed_categories = [MockCategory(cat_row) for cat_row in cat_results]

            # Get article count
            count_sql = "SELECT COUNT(*) FROM items WHERE feed_id = :feed_id"
            article_count = session.execute(text(count_sql), {"feed_id": feed.id}).scalar()

            # Get latest article date
            latest_article_sql = "SELECT MAX(published) FROM items WHERE feed_id = :feed_id"
            latest_article_date = session.execute(text(latest_article_sql), {"feed_id": feed.id}).scalar()

            # Get analysis statistics
            analysis_stats = None
            if article_count > 0:
                analysis_sql = """
                SELECT
                    COUNT(*) as analyzed_count,
                    AVG(COALESCE((ia.impact_json ->> 'overall')::numeric, 0)) as avg_impact_score,
                    SUM(CASE WHEN (ia.sentiment_json -> 'overall' ->> 'label') = 'positive' THEN 1 ELSE 0 END) as positive_count,
                    SUM(CASE WHEN (ia.sentiment_json -> 'overall' ->> 'label') = 'negative' THEN 1 ELSE 0 END) as negative_count,
                    SUM(CASE WHEN (ia.sentiment_json -> 'overall' ->> 'label') = 'neutral' THEN 1 ELSE 0 END) as neutral_count
                FROM item_analysis ia
                JOIN items i ON i.id = ia.item_id
                WHERE i.feed_id = :feed_id
                """
                analysis_result = session.execute(text(analysis_sql), {"feed_id": feed.id}).fetchone()

                if analysis_result and analysis_result[0] > 0:
                    analysis_stats = {
                        'analyzed_count': analysis_result[0],
                        'avg_impact_score': float(analysis_result[1] or 0),
                        'sentiment_counts': {
                            'positive': analysis_result[2] or 0,
                            'negative': analysis_result[3] or 0,
                            'neutral': analysis_result[4] or 0
                        }
                    }

            # Get geopolitical analysis summary
            geopolitical_stats = None
            if article_count > 0:
                geo_sql = """
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
                """
                geo_results = session.execute(text(geo_sql), {"feed_id": feed.id}).fetchall()

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

            html += FeedComponent.build_feed_card(feed, source, feed_categories, article_count, analysis_stats, auto_analysis_only, latest_article_date, geopolitical_stats)

        if not html:
            html = BaseComponent.alert_box('No feeds found.', 'info')

        return html

    except Exception as e:
        logger.error(f"Failed to get feeds list: {e}")
        return BaseComponent.alert_box('Error loading feeds.', 'danger')


@router.get("/feed-health/{feed_id}", response_class=HTMLResponse)
def get_feed_health(feed_id: int, session: Session = Depends(get_session)):
    """Get feed health information for modal display."""
    try:
        from sqlmodel import text

        # Get feed info
        feed_result = session.execute(
            text("SELECT id, title FROM feeds WHERE id = :feed_id"),
            {"feed_id": feed_id}
        ).first()

        if not feed_result:
            return BaseComponent.alert_box('Feed not found', 'danger')

        feed_title = feed_result[1] or "Unknown Feed"

        # Get health data with available columns
        health_result = session.execute(
            text("""
                SELECT ok_ratio, consecutive_failures, avg_response_time_ms,
                       last_success, last_failure, uptime_24h, uptime_7d
                FROM feed_health
                WHERE feed_id = :feed_id
            """),
            {"feed_id": feed_id}
        ).first()

        if not health_result:
            return f'''
            <div class="modal-header">
                <h5 class="modal-title">Feed Health: {feed_title}</h5>
                <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
            </div>
            <div class="modal-body">
                {BaseComponent.alert_box('No health data available', 'info')}
            </div>
            '''

        ok_ratio = health_result[0] or 0
        consecutive_failures = health_result[1] or 0
        avg_response_time = health_result[2] or 0
        last_success = health_result[3]
        last_failure = health_result[4]
        uptime_24h = health_result[5] or 0
        uptime_7d = health_result[6] or 0

        success_rate = ok_ratio * 100  # Convert ratio to percentage

        return f'''
        <div class="modal-header">
            <h5 class="modal-title">Feed Health: {feed_title}</h5>
            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
        </div>
        <div class="modal-body">
            <div class="row">
                <div class="col-md-6">
                    <h6>Success Rate</h6>
                    <div class="progress mb-3">
                        <div class="progress-bar bg-{"success" if success_rate > 80 else "warning" if success_rate > 50 else "danger"}"
                             style="width: {success_rate}%">{success_rate:.1f}%</div>
                    </div>
                </div>
                <div class="col-md-6">
                    <h6>Average Response Time</h6>
                    <p class="h4">{avg_response_time:.0f}ms</p>
                </div>
            </div>

            <div class="row">
                <div class="col-md-6">
                    <h6>Last Successful Fetch</h6>
                    <p>{BaseComponent.format_date(last_success) if last_success else "Never"}</p>
                </div>
                <div class="col-md-6">
                    <h6>Consecutive Failures</h6>
                    <p class="h4 text-{"danger" if consecutive_failures > 3 else "warning" if consecutive_failures > 0 else "success"}">{consecutive_failures}</p>
                </div>
            </div>

            <div class="row">
                <div class="col-md-6">
                    <h6>24h Uptime</h6>
                    <p class="h4">{uptime_24h:.1f}%</p>
                </div>
                <div class="col-md-6">
                    <h6>7d Uptime</h6>
                    <p class="h4">{uptime_7d:.1f}%</p>
                </div>
            </div>
        </div>
        '''

    except Exception as e:
        logger.error(f"Failed to get feed health: {e}")
        return BaseComponent.alert_box('Error loading health data.', 'danger')


@router.get("/feed-types-options", response_class=HTMLResponse)
def get_feed_types_options(session: Session = Depends(get_session)):
    """Get HTML options for feed type select dropdown."""
    try:
        from sqlmodel import text
        results = session.execute(
            text("SELECT id, name FROM feed_types ORDER BY name")
        ).fetchall()

        html = ""
        for row in results:
            html += f'<option value="{row[0]}">{row[1]}</option>'
        return html
    except Exception as e:
        logger.error(f"Failed to get feed types: {e}")
        return '<option value="">Error loading feed types</option>'


@router.post("/feed-url-test", response_class=HTMLResponse)
def test_feed_url(url: str, session: Session = Depends(get_session)):
    """Test a feed URL and return detection results."""
    try:
        detector = FeedTypeDetector()
        feed_data = feedparser.parse(url)

        if feed_data.bozo:
            return BaseComponent.alert_box(f'❌ Feed parsing error: {feed_data.bozo_exception}', 'danger')

        detected_type = detector.detect_feed_type(url, feed_data)
        entries_count = len(feed_data.entries)

        return f'''
        <div class="alert alert-success">
            ✅ Feed validated successfully!
            <br><strong>Type:</strong> {detected_type}
            <br><strong>Title:</strong> {feed_data.feed.get('title', 'Unknown')}
            <br><strong>Entries:</strong> {entries_count}
        </div>
        '''

    except Exception as e:
        return BaseComponent.alert_box(f'❌ Error testing feed: {str(e)}', 'danger')


@router.get("/feed-edit-form/{feed_id}", response_class=HTMLResponse)
def get_feed_edit_form(
    feed_id: int,
    auto_analysis_only: Optional[str] = Query(None),
    session: Session = Depends(get_session)
):
    """Get feed edit form for modal display."""
    try:
        feed = session.get(Feed, feed_id)
        if not feed:
            return BaseComponent.alert_box('Feed not found', 'danger')

        # Get sources and categories for dropdowns
        sources = session.exec(select(Source)).all()
        categories = session.exec(select(Category)).all()

        # Get current feed categories
        current_categories = session.exec(
            select(FeedCategory).where(FeedCategory.feed_id == feed_id)
        ).all()
        current_category_ids = [fc.category_id for fc in current_categories]
    except Exception as e:
        logger.error(f"Error in feed edit form for feed {feed_id}: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return BaseComponent.alert_box(f'Error: {str(e)}', 'danger')

    sources_options = ""
    for source in sources:
        selected = "selected" if source.id == feed.source_id else ""
        sources_options += f'<option value="{source.id}" {selected}>{source.name}</option>'

    categories_checkboxes = ""
    for category in categories:
        checked = "checked" if category.id in current_category_ids else ""
        categories_checkboxes += f'''
        <div class="form-check">
            <input class="form-check-input" type="checkbox" value="{category.id}"
                   id="category_{category.id}" name="categories" {checked}>
            <label class="form-check-label" for="category_{category.id}">
                {category.name}
            </label>
        </div>
        '''

    hidden_auto_analysis = f'<input type="hidden" name="auto_analysis_only" value="{auto_analysis_only}">' if auto_analysis_only else ''

    return f'''
    <div class="modal-header">
        <h5 class="modal-title">Edit Feed: {feed.title}</h5>
    </div>
    <div class="modal-body">
        <form id="edit-feed-form-{feed_id}">
            {hidden_auto_analysis}
            <div class="mb-3">
                <label for="edit-title" class="form-label">Title</label>
                <input type="text" class="form-control" id="edit-title" name="title"
                       value="{BaseComponent.clean_html_attr(feed.title or '')}">
            </div>

            <div class="mb-3">
                <label for="edit-url" class="form-label">URL</label>
                <input type="url" class="form-control" id="edit-url" name="url"
                       value="{feed.url}" required>
            </div>

            <div class="mb-3">
                <label for="edit-source" class="form-label">Source</label>
                <select class="form-select" id="edit-source" name="source_id" required>
                    {sources_options}
                </select>
            </div>

            <div class="mb-3">
                <label for="edit-interval" class="form-label">Fetch Interval (minutes)</label>
                <input type="number" class="form-control" id="edit-interval" name="fetch_interval_minutes"
                       value="{feed.fetch_interval_minutes}" min="1" required>
            </div>

            <div class="mb-3">
                <div class="form-check form-switch">
                    <input class="form-check-input" type="checkbox" name="auto_analyze_enabled" value="true"
                           {'checked' if feed.auto_analyze_enabled else ''}>
                    <label class="form-check-label" for="auto-analyze-enabled">
                        <strong>Auto-Analyze New Articles</strong>
                        <br><small class="text-muted">Automatically analyze new articles for sentiment and impact when fetched</small>
                    </label>
                </div>
            </div>

            <hr class="my-4">
            <h6 class="mb-3"><i class="bi bi-globe me-2"></i>Content Scraping</h6>

            <div class="mb-3">
                <div class="form-check form-switch">
                    <input class="form-check-input" type="checkbox" name="scrape_full_content"
                           {'checked' if feed.scrape_full_content else ''}>
                    <label class="form-check-label">
                        <strong>Scrape Full Content</strong>
                        <br><small class="text-muted">Extract full article text from URLs (auto-runs during sentiment analysis)</small>
                    </label>
                </div>
            </div>

            <div class="mb-3">
                <label class="form-label">Scrape Method</label>
                <select class="form-select" name="scrape_method">
                    <option value="auto" {'selected' if feed.scrape_method == 'auto' else ''}>
                        Auto (httpx → Playwright fallback)
                    </option>
                    <option value="httpx" {'selected' if feed.scrape_method == 'httpx' else ''}>
                        httpx only (fast)
                    </option>
                </select>
                <div class="form-text">
                    Auto mode falls back to Playwright for JavaScript-heavy sites
                </div>
            </div>

            <div class="mb-3">
                <label class="form-label">Categories</label>
                {categories_checkboxes}
            </div>

            <div class="d-flex justify-content-end gap-2">
                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                <button type="button" class="btn btn-primary"
                        hx-put="/api/feeds/{feed_id}/form"
                        hx-include="#edit-feed-form-{feed_id}"
                        hx-target="#feeds-list"
                        hx-swap="innerHTML">
                    <i class="bi bi-save"></i> Save Changes
                </button>
            </div>
        </form>
    </div>
    '''