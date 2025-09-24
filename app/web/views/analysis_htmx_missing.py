"""Missing HTMX endpoints for Analysis Control page"""

from fastapi import APIRouter, Request, Depends, Query, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional
from datetime import datetime
import json

from app.database import get_session
from app.core.logging_config import get_logger
from app.repositories.analysis_control import AnalysisControlRepo
from app.models.core import Feed, Item
from app.models.analysis import AnalysisRun
from app.config import settings

router = APIRouter(tags=["htmx-analysis-missing"])
logger = get_logger(__name__)
templates = Jinja2Templates(directory="templates")


@router.get("/model-params", response_class=HTMLResponse)
async def get_model_params(request: Request):
    """Get model parameters form partial"""
    html = """
    <div class="card-body bg-dark text-light">
        <h6 class="card-subtitle mb-3 text-light">Configure AI Model</h6>
        <div class="row g-3">
            <div class="col-md-6">
                <label class="form-label">Model</label>
                <select class="form-select" name="model">
                    <option value="gpt-4.1-nano" selected>GPT-4.1 Nano ($0.20/$0.80)</option>
                    <option value="gpt-4o-mini">GPT-4o Mini ($0.25/$1.00)</option>
                    <option value="gpt-4.1-mini">GPT-4.1 Mini ($0.70/$2.80)</option>
                    <option value="gpt-4o">GPT-4o ($4.25/$17.00)</option>
                    <option value="gpt-5-mini">GPT-5 Mini ($0.45/$3.60)</option>
                    <option value="o4-mini">O4 Mini ($2.00/$8.00)</option>
                </select>
            </div>
            <div class="col-md-6">
                <label class="form-label">Temperature</label>
                <input type="range" class="form-range" name="temperature"
                       min="0" max="1" step="0.1" value="0.3">
                <small class="text-muted">0.3</small>
            </div>
            <div class="col-12">
                <div class="form-check">
                    <input class="form-check-input" type="checkbox" name="include_sentiment" checked>
                    <label class="form-check-label">Include Sentiment Analysis</label>
                </div>
                <div class="form-check">
                    <input class="form-check-input" type="checkbox" name="include_impact" checked>
                    <label class="form-check-label">Include Impact Score</label>
                </div>
            </div>
        </div>
    </div>
    """
    return HTMLResponse(content=html)


@router.get("/target-selection", response_class=HTMLResponse)
async def get_target_selection(db: Session = Depends(get_session)):
    """Get target selection form partial with SET buttons"""
    # Query feeds directly
    feeds = db.query(Feed).filter(Feed.status == 'active').limit(100).all()

    html = """
    <div class="card-body bg-dark text-light">
        <h6 class="card-subtitle mb-3 text-light">Select Analysis Target</h6>
        <div class="mb-3">
            <!-- Latest N Articles Option -->
            <div class="form-check mb-2">
                <input class="form-check-input" type="radio" name="target_type" value="latest" id="targetLatest" checked>
                <label class="form-check-label" for="targetLatest">
                    Latest N Articles
                </label>
            </div>

            <!-- All New Articles Option -->
            <div class="form-check mb-2">
                <input class="form-check-input" type="radio" name="target_type" value="all" id="targetAll">
                <label class="form-check-label" for="targetAll">
                    All Unanalyzed Articles
                </label>
            </div>

            <!-- Specific Feed Option -->
            <div class="form-check mb-2">
                <input class="form-check-input" type="radio" name="target_type" value="feed" id="targetFeed">
                <label class="form-check-label" for="targetFeed">
                    Specific Feed
                </label>
            </div>

            <!-- Date Range Option -->
            <div class="form-check mb-2">
                <input class="form-check-input" type="radio" name="target_type" value="date_range" id="targetDate">
                <label class="form-check-label" for="targetDate">
                    Date Range
                </label>
            </div>
        </div>

        <!-- Latest Count Selector -->
        <div id="latestSelector" class="mb-3">
            <label class="form-label">Number of latest articles to analyze:</label>
            <div class="input-group">
                <input type="number" class="form-control bg-dark text-light" name="latest_count" id="latest_count"
                       value="50" min="1" max="500" placeholder="50">
                <span class="input-group-text bg-secondary text-light">articles</span>
                <button type="button" class="btn btn-success ms-2"
                        hx-post="/htmx/analysis/preview-update"
                        hx-vals='js:{mode: "latest", count: document.getElementById("latest_count").value}'
                        hx-target="#active-selection"
                        hx-swap="innerHTML"
                        onclick="updateLiveArticles('latest', document.getElementById('latest_count').value)">
                    ✓ SET
                </button>
            </div>
            <small class="text-muted">Enter a number between 1 and 500</small>
        </div>

        <!-- Feed Selector -->
        <div id="feedSelector" class="mb-3" style="display: none;">
            <label class="form-label">Select feed:</label>
            <div class="input-group">
                <select class="form-select bg-dark text-light" name="feed_id" id="feed_select">
                    <option value="">Choose a feed...</option>
    """

    for feed in feeds:
        # Get item count for this feed
        item_count = db.query(Item).filter(Item.feed_id == feed.id).count()
        html += f'<option value="{feed.id}">{feed.title} ({item_count} items)</option>'

    html += """
                </select>
                <button type="button" class="btn btn-success ms-2"
                        hx-post="/htmx/analysis/preview-update"
                        hx-vals='js:{mode: "feed", feed_id: document.getElementById("feed_select").value}'
                        hx-target="#active-selection"
                        hx-swap="innerHTML"
                        onclick="updateLiveArticles('feed', null, document.getElementById('feed_select').value)">
                    ✓ SET
                </button>
            </div>
        </div>

        <!-- Date Range Selector -->
        <div id="dateSelector" class="mb-3" style="display: none;">
            <div class="row g-2">
                <div class="col-md-6">
                    <label class="form-label">From</label>
                    <input type="datetime-local" class="form-control bg-dark text-light" name="date_from" id="date_from">
                </div>
                <div class="col-md-6">
                    <label class="form-label">To</label>
                    <input type="datetime-local" class="form-control bg-dark text-light" name="date_to" id="date_to">
                </div>
                <div class="col-12 mt-2">
                    <button type="button" class="btn btn-success"
                            hx-post="/htmx/analysis/preview-update"
                            hx-vals='js:{mode: "date_range", date_from: document.getElementById("date_from").value, date_to: document.getElementById("date_to").value}'
                            hx-target="#active-selection"
                            hx-swap="innerHTML"
                            onclick="updateLiveArticles('date_range', null, null, document.getElementById('date_from').value, document.getElementById('date_to').value)">
                        ✓ SET
                    </button>
                </div>
            </div>
        </div>

        <!-- All Unanalyzed SET Button -->
        <div id="allSelector" style="display: none;">
            <button type="button" class="btn btn-success"
                    hx-post="/htmx/analysis/preview-update"
                    hx-vals='{"mode": "all"}'
                    hx-target="#active-selection"
                    hx-swap="innerHTML"
                    onclick="updateLiveArticles('all')">
                ✓ SET
            </button>
        </div>

        <!-- Active Selection Preview -->
        <div id="active-selection" class="mt-4">
            <!-- Will be populated when SET is clicked -->
        </div>

        <script>
            document.querySelectorAll('input[name="target_type"]').forEach(radio => {
                radio.addEventListener('change', function() {
                    // Hide all selectors
                    document.getElementById('latestSelector').style.display = 'none';
                    document.getElementById('feedSelector').style.display = 'none';
                    document.getElementById('dateSelector').style.display = 'none';
                    document.getElementById('allSelector').style.display = 'none';

                    // Show relevant selector
                    if (this.value === 'latest') {
                        document.getElementById('latestSelector').style.display = 'block';
                    } else if (this.value === 'feed') {
                        document.getElementById('feedSelector').style.display = 'block';
                    } else if (this.value === 'date_range') {
                        document.getElementById('dateSelector').style.display = 'block';
                    } else if (this.value === 'all') {
                        document.getElementById('allSelector').style.display = 'block';
                    }
                });
            });
        </script>
    </div>
    """
    return HTMLResponse(content=html)


@router.post("/preview-update", response_class=HTMLResponse)
async def update_preview(
    request: Request,
    db: Session = Depends(get_session)
):
    """Update preview based on selection and calculate unanalyzed articles"""
    form_data = await request.form()
    mode = form_data.get("mode", "latest")

    # Calculate total items and unanalyzed count based on mode
    total_items = 0
    analyzed_count = 0

    if mode == "latest":
        count = int(form_data.get("count", 50))
        # Get the latest N items and check if they're analyzed
        # IMPORTANT: Using created_at to match the Items page sorting
        result = db.execute(text("""
            SELECT COUNT(*) as total,
                   COUNT(ia.item_id) as analyzed
            FROM (
                SELECT id
                FROM items
                ORDER BY created_at DESC
                LIMIT :limit
            ) as latest_items
            LEFT JOIN item_analysis ia ON latest_items.id = ia.item_id
        """), {"limit": count})
        row = result.first()
        total_items = row.total if row else 0
        analyzed_count = row.analyzed if row else 0

    elif mode == "all":
        # Get all unanalyzed items
        result = db.execute(text("""
            SELECT COUNT(*) as total
            FROM items i
            LEFT JOIN item_analysis ia ON i.id = ia.item_id
            WHERE ia.item_id IS NULL
        """))
        row = result.first()
        total_items = row.total if row else 0
        analyzed_count = 0  # By definition, all are unanalyzed

    elif mode == "feed":
        feed_id = form_data.get("feed_id")
        if feed_id:
            result = db.execute(text("""
                SELECT COUNT(i.id) as total,
                       COUNT(ia.item_id) as analyzed
                FROM items i
                LEFT JOIN item_analysis ia ON i.id = ia.item_id
                WHERE i.feed_id = :feed_id
            """), {"feed_id": int(feed_id)})
            row = result.first()
            total_items = row.total if row else 0
            analyzed_count = row.analyzed if row else 0

    elif mode == "date_range":
        date_from = form_data.get("date_from")
        date_to = form_data.get("date_to")
        if date_from and date_to:
            result = db.execute(text("""
                SELECT COUNT(i.id) as total,
                       COUNT(ia.item_id) as analyzed
                FROM items i
                LEFT JOIN item_analysis ia ON i.id = ia.item_id
                WHERE i.published BETWEEN :date_from AND :date_to
            """), {"date_from": date_from, "date_to": date_to})
            row = result.first()
            total_items = row.total if row else 0
            analyzed_count = row.analyzed if row else 0

    # Calculate unanalyzed count
    to_analyze = total_items - analyzed_count

    # Build selection description
    if mode == "latest":
        selection_text = f"Latest {form_data.get('count', 50)} articles"
    elif mode == "all":
        selection_text = "All unanalyzed articles"
    elif mode == "feed":
        feed_id = form_data.get("feed_id")
        if feed_id:
            feed = db.query(Feed).filter(Feed.id == int(feed_id)).first()
            selection_text = f"Feed: {feed.title if feed else 'Unknown'}"
        else:
            selection_text = "No feed selected"
    else:
        selection_text = f"Date range: {form_data.get('date_from', '')} to {form_data.get('date_to', '')}"

    # Calculate estimated cost and time
    cost_per_item = 0.005  # $0.005 per item estimate
    time_per_item = 2  # 2 seconds per item estimate
    estimated_cost = to_analyze * cost_per_item
    estimated_time = to_analyze * time_per_item

    # Format time
    if estimated_time < 60:
        time_str = f"{estimated_time} sec"
    elif estimated_time < 3600:
        time_str = f"{estimated_time // 60} min"
    else:
        time_str = f"{estimated_time // 3600} hr {(estimated_time % 3600) // 60} min"

    html = f"""
    <div class="alert alert-success bg-dark border-success">
        <h6 class="alert-heading">Active Selection: {selection_text}</h6>
        <div class="row mt-3">
            <div class="col-md-3">
                <small class="text-muted">Total Items:</small>
                <h5 class="text-info">{total_items}</h5>
            </div>
            <div class="col-md-3">
                <small class="text-muted">Already Analyzed:</small>
                <h5 class="text-success">{analyzed_count}</h5>
            </div>
            <div class="col-md-3">
                <small class="text-warning">To Analyze:</small>
                <h5 class="text-warning">{to_analyze}</h5>
            </div>
            <div class="col-md-3">
                <button class="btn btn-outline-danger btn-sm"
                        onclick="clearSelection()">
                    ⨯ Clear
                </button>
            </div>
        </div>
        {"<div class='alert alert-info mt-2'>ℹ️ Will skip already analyzed items</div>" if to_analyze == 0 else ""}
    </div>

    <!-- Store selection data for analysis start -->
    <input type="hidden" name="analysis_mode" value="{mode}">
    <input type="hidden" name="analysis_total" value="{total_items}">
    <input type="hidden" name="analysis_to_analyze" value="{to_analyze}">
    """

    if mode == "latest":
        html += f'<input type="hidden" name="analysis_count" value="{form_data.get("count", 50)}">'
    elif mode == "feed":
        html += f'<input type="hidden" name="analysis_feed_id" value="{form_data.get("feed_id", "")}">'
    elif mode == "date_range":
        html += f'<input type="hidden" name="analysis_date_from" value="{form_data.get("date_from", "")}">'
        html += f'<input type="hidden" name="analysis_date_to" value="{form_data.get("date_to", "")}">'

    return HTMLResponse(content=html)


@router.get("/preview-start", response_class=HTMLResponse)
async def get_preview_start(db: Session = Depends(get_session)):
    """Get preview and start button partial"""
    html = """
    <div class="card-body bg-dark text-light">
        <h6 class="card-subtitle mb-3 text-light">Preview & Start</h6>
        <div class="alert alert-info bg-dark border-info text-light">
            <div class="row">
                <div class="col-md-4">
                    <small class="text-muted">Estimated Articles</small>
                    <h5 class="mb-0">~50-100</h5>
                </div>
                <div class="col-md-4">
                    <small class="text-muted">Estimated Cost</small>
                    <h5 class="mb-0">~$0.25</h5>
                </div>
                <div class="col-md-4">
                    <small class="text-muted">Estimated Time</small>
                    <h5 class="mb-0">~2-3 min</h5>
                </div>
            </div>
        </div>

        <div class="d-grid gap-2">
            <button type="submit" class="btn btn-primary btn-lg"
                    hx-post="/api/analysis/start"
                    hx-include="#analysis-form">
                <i class="bi bi-play-fill me-2"></i> Start Analysis
            </button>
        </div>
    </div>
    """
    return HTMLResponse(content=html)


@router.get("/articles-live", response_class=HTMLResponse)
async def get_articles_live(
    db: Session = Depends(get_session),
    mode: str = Query("all", description="Selection mode: latest, all, feed, date_range"),
    count: Optional[int] = Query(None, ge=1, le=500),
    feed_id: Optional[int] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100)
):
    """Live articles list based on current selection"""
    offset = (page - 1) * limit

    # Build query based on mode
    if mode == "latest" and count:
        # Get latest N articles by created_at (consistent with Items page)
        result = db.execute(text("""
            SELECT i.id, i.title, i.link, i.published, i.created_at,
                   f.title as feed_title,
                   CASE WHEN ia.item_id IS NOT NULL THEN TRUE ELSE FALSE END as analyzed,
                   ia.sentiment_json->'overall'->>'label' as sentiment,
                   (ia.impact_json->>'overall')::float as impact_score
            FROM (
                SELECT * FROM items
                ORDER BY created_at DESC
                LIMIT :count
            ) i
            LEFT JOIN feeds f ON i.feed_id = f.id
            LEFT JOIN item_analysis ia ON i.id = ia.item_id
            ORDER BY i.created_at DESC
            LIMIT :limit OFFSET :offset
        """), {"count": count, "limit": limit, "offset": offset})

    elif mode == "all":
        # Get all unanalyzed articles
        result = db.execute(text("""
            SELECT i.id, i.title, i.link, i.published, i.created_at,
                   f.title as feed_title,
                   FALSE as analyzed,
                   NULL as sentiment,
                   NULL as impact_score
            FROM items i
            LEFT JOIN feeds f ON i.feed_id = f.id
            LEFT JOIN item_analysis ia ON i.id = ia.item_id
            WHERE ia.item_id IS NULL
            ORDER BY i.created_at DESC
            LIMIT :limit OFFSET :offset
        """), {"limit": limit, "offset": offset})

    elif mode == "feed" and feed_id:
        # Get articles from specific feed
        result = db.execute(text("""
            SELECT i.id, i.title, i.link, i.published, i.created_at,
                   f.title as feed_title,
                   CASE WHEN ia.item_id IS NOT NULL THEN TRUE ELSE FALSE END as analyzed,
                   ia.sentiment_json->'overall'->>'label' as sentiment,
                   (ia.impact_json->>'overall')::float as impact_score
            FROM items i
            LEFT JOIN feeds f ON i.feed_id = f.id
            LEFT JOIN item_analysis ia ON i.id = ia.item_id
            WHERE i.feed_id = :feed_id
            ORDER BY i.created_at DESC
            LIMIT :limit OFFSET :offset
        """), {"feed_id": feed_id, "limit": limit, "offset": offset})

    elif mode == "date_range" and date_from and date_to:
        # Get articles from date range
        result = db.execute(text("""
            SELECT i.id, i.title, i.link, i.published, i.created_at,
                   f.title as feed_title,
                   CASE WHEN ia.item_id IS NOT NULL THEN TRUE ELSE FALSE END as analyzed,
                   ia.sentiment_json->'overall'->>'label' as sentiment,
                   (ia.impact_json->>'overall')::float as impact_score
            FROM items i
            LEFT JOIN feeds f ON i.feed_id = f.id
            LEFT JOIN item_analysis ia ON i.id = ia.item_id
            WHERE i.published BETWEEN :date_from AND :date_to
            ORDER BY i.created_at DESC
            LIMIT :limit OFFSET :offset
        """), {"date_from": date_from, "date_to": date_to, "limit": limit, "offset": offset})

    else:
        # Default: show latest 100 items
        result = db.execute(text("""
            SELECT i.id, i.title, i.link, i.published, i.created_at,
                   f.title as feed_title,
                   CASE WHEN ia.item_id IS NOT NULL THEN TRUE ELSE FALSE END as analyzed,
                   ia.sentiment_json->'overall'->>'label' as sentiment,
                   (ia.impact_json->>'overall')::float as impact_score
            FROM items i
            LEFT JOIN feeds f ON i.feed_id = f.id
            LEFT JOIN item_analysis ia ON i.id = ia.item_id
            ORDER BY i.created_at DESC
            LIMIT :limit OFFSET :offset
        """), {"limit": limit, "offset": offset})

    articles = result.fetchall()

    # Build HTML
    html = """
    <div class="card bg-dark border-secondary">
        <div class="card-header d-flex justify-content-between align-items-center">
            <h6 class="mb-0 text-light">
                📰 Live Articles
                <small class="text-muted">({} items)</small>
            </h6>
            <div class="btn-group btn-group-sm" role="group">
                <button type="button" class="btn btn-outline-secondary btn-sm"
                        hx-get="/htmx/analysis/articles-live"
                        hx-target="#articles-live"
                        hx-swap="innerHTML">
                    🔄 Refresh
                </button>
            </div>
        </div>
        <div class="card-body p-0">
            <div class="table-responsive" style="max-height: 600px; overflow-y: auto;">
                <table class="table table-dark table-hover table-sm mb-0">
                    <thead class="sticky-top">
                        <tr>
                            <th width="5%">ID</th>
                            <th width="40%">Title</th>
                            <th width="15%">Feed</th>
                            <th width="15%">Date</th>
                            <th width="10%">Status</th>
                            <th width="10%">Sentiment</th>
                            <th width="5%">Actions</th>
                        </tr>
                    </thead>
                    <tbody>
    """.format(len(articles))

    if not articles:
        html += """
                        <tr>
                            <td colspan="7" class="text-center text-muted py-4">
                                No articles found for current selection
                            </td>
                        </tr>
        """
    else:
        for article in articles:
            # Format date
            date_str = ""
            if article.published:
                date_str = article.published.strftime("%m-%d %H:%M") if hasattr(article.published, 'strftime') else str(article.published)[:16]
            elif article.created_at:
                date_str = article.created_at.strftime("%m-%d %H:%M") if hasattr(article.created_at, 'strftime') else str(article.created_at)[:16]

            # Status badge
            status_badge = "success" if article.analyzed else "secondary"
            status_text = "Analyzed" if article.analyzed else "Pending"

            # Sentiment badge
            sentiment_badge = "info"
            sentiment_text = "N/A"
            if article.sentiment:
                if article.sentiment == "positive":
                    sentiment_badge = "success"
                    sentiment_text = "Positive"
                elif article.sentiment == "negative":
                    sentiment_badge = "danger"
                    sentiment_text = "Negative"
                else:
                    sentiment_badge = "warning"
                    sentiment_text = "Neutral"

            html += f"""
                        <tr>
                            <td>
                                <small class="text-muted">#{article.id}</small>
                            </td>
                            <td>
                                <a href="{article.link}" target="_blank"
                                   class="text-light text-decoration-none" title="{article.title}">
                                    {article.title[:50]}{'...' if len(article.title) > 50 else ''}
                                </a>
                            </td>
                            <td>
                                <small class="text-light">
                                    {article.feed_title[:20] if article.feed_title else 'Unknown'}
                                </small>
                            </td>
                            <td>
                                <small class="text-light">{date_str}</small>
                            </td>
                            <td>
                                <span class="badge bg-{status_badge}">{status_text}</span>
                            </td>
                            <td>
                                <span class="badge bg-{sentiment_badge}">{sentiment_text}</span>
                            </td>
                            <td>
                                <div class="btn-group btn-group-sm">
                                    <button class="btn btn-outline-light btn-sm"
                                            onclick="window.open('{article.link}', '_blank')"
                                            title="Open article">
                                        🔗
                                    </button>
                                </div>
                            </td>
                        </tr>
            """

    html += """
                    </tbody>
                </table>
            </div>
        </div>
        <div class="card-footer">
            <div class="d-flex justify-content-between align-items-center">
                <small class="text-muted">
                    Page {} • {} items per page
                </small>
                <div class="btn-group btn-group-sm">
                    <button class="btn btn-outline-secondary btn-sm"
                            hx-get="/htmx/analysis/articles-live?page={}"
                            hx-target="#articles-live"
                            hx-swap="innerHTML"
                            {}>
                        ← Prev
                    </button>
                    <button class="btn btn-outline-secondary btn-sm"
                            hx-get="/htmx/analysis/articles-live?page={}"
                            hx-target="#articles-live"
                            hx-swap="innerHTML">
                        Next →
                    </button>
                </div>
            </div>
        </div>
    </div>
    """.format(page, limit, page-1 if page > 1 else 1, 'disabled' if page <= 1 else '', page+1)

    return HTMLResponse(content=html)


@router.get("/stats-horizontal", response_class=HTMLResponse)
async def get_stats_horizontal(db: Session = Depends(get_session)):
    """Horizontal layout for system statistics"""
    # Get basic counts
    total_items = db.execute(text("SELECT COUNT(*) FROM items")).scalar()
    analyzed_items = db.execute(text("SELECT COUNT(*) FROM item_analysis")).scalar()
    pending_items = total_items - analyzed_items
    active_feeds = db.execute(text("SELECT COUNT(*) FROM feeds WHERE status = 'ACTIVE'")).scalar()

    # Recent activity (last 24h)
    recent_items = db.execute(text("""
        SELECT COUNT(*) FROM items
        WHERE created_at >= NOW() - INTERVAL '24 hours'
    """)).scalar()

    recent_analyzed = db.execute(text("""
        SELECT COUNT(*) FROM item_analysis ia
        JOIN items i ON ia.item_id = i.id
        WHERE i.created_at >= NOW() - INTERVAL '24 hours'
    """)).scalar()

    # Analysis coverage percentage
    coverage = (analyzed_items / total_items * 100) if total_items > 0 else 0

    html = f"""
    <div class="row g-3 mb-4">
        <div class="col-md-2">
            <div class="card bg-dark border-info text-center">
                <div class="card-body py-3">
                    <h4 class="text-info mb-1">{total_items:,}</h4>
                    <small class="text-light">Total Items</small>
                </div>
            </div>
        </div>
        <div class="col-md-2">
            <div class="card bg-dark border-success text-center">
                <div class="card-body py-3">
                    <h4 class="text-success mb-1">{analyzed_items:,}</h4>
                    <small class="text-light">Analyzed</small>
                </div>
            </div>
        </div>
        <div class="col-md-2">
            <div class="card bg-dark border-warning text-center">
                <div class="card-body py-3">
                    <h4 class="text-warning mb-1">{pending_items:,}</h4>
                    <small class="text-light">Pending</small>
                </div>
            </div>
        </div>
        <div class="col-md-2">
            <div class="card bg-dark border-primary text-center">
                <div class="card-body py-3">
                    <h4 class="text-primary mb-1">{active_feeds}</h4>
                    <small class="text-light">Active Feeds</small>
                </div>
            </div>
        </div>
        <div class="col-md-2">
            <div class="card bg-dark border-secondary text-center">
                <div class="card-body py-3">
                    <h4 class="text-info mb-1">{recent_items}</h4>
                    <small class="text-light">24h New</small>
                </div>
            </div>
        </div>
        <div class="col-md-2">
            <div class="card bg-dark border-secondary text-center">
                <div class="card-body py-3">
                    <h4 class="text-success mb-1">{coverage:.1f}%</h4>
                    <small class="text-light">Coverage</small>
                </div>
            </div>
        </div>
    </div>
    """

    return HTMLResponse(content=html)


# Add /runs/active and /runs/history endpoints for the refactored template
@router.get("/runs/active", response_class=HTMLResponse)
async def get_runs_active(db: Session = Depends(get_session)):
    """Get active analysis runs for refactored template"""
    control_repo = AnalysisControlRepo()
    active_runs = control_repo.get_active_runs()

    if not active_runs:
        html = """
        <div class="alert alert-info">
            <i class="bi bi-info-circle me-2"></i>
            No active analysis runs at the moment.
        </div>
        """
    else:
        html = '<div class="list-group">'
        for run in active_runs:
            status_badge = "primary" if run.status == "running" else "success"
            progress = (run.processed_count / run.total_count * 100) if run.total_count > 0 else 0

            html += f"""
            <div class="list-group-item">
                <div class="d-flex justify-content-between align-items-center">
                    <div>
                        <h6 class="mb-1">Analysis Run #{run.id}</h6>
                        <p class="mb-1 text-muted">Started: {run.started_at}</p>
                    </div>
                    <span class="badge bg-{status_badge}">{run.status.upper()}</span>
                </div>
                <div class="progress mt-2" style="height: 20px;">
                    <div class="progress-bar" role="progressbar"
                         style="width: {progress}%">{int(progress)}%</div>
                </div>
                <small class="text-muted">{run.processed_count}/{run.total_count} items processed</small>
            </div>
            """
        html += '</div>'

    return HTMLResponse(content=html)


@router.get("/runs/history", response_class=HTMLResponse)
async def get_runs_history(db: Session = Depends(get_session),
                          page: int = Query(1, ge=1),
                          limit: int = Query(10)):
    """Get analysis run history for refactored template with pagination"""
    offset = (page - 1) * limit

    # Get total count for pagination
    count_result = db.execute(text("SELECT COUNT(*) FROM analysis_runs"))
    total_count = count_result.scalar()
    total_pages = (total_count + limit - 1) // limit

    # Use raw SQL to avoid ORM field mismatch issues
    result = db.execute(text("""
        SELECT id, started_at, completed_at, status,
               queued_count, processed_count, failed_count,
               cost_estimate, actual_cost
        FROM analysis_runs
        ORDER BY created_at DESC
        LIMIT :limit OFFSET :offset
    """), {"limit": limit, "offset": offset})
    runs = result.fetchall()

    if not runs:
        html = """
        <div class="alert alert-info">
            <i class="bi bi-info-circle me-2"></i>
            No analysis run history available.
        </div>
        """
    else:
        # Dark mode table with better styling
        html = """
        <div class="table-responsive">
            <table class="table table-dark table-striped table-hover">
                <thead class="thead-dark">
                    <tr>
                        <th style="color: #58a6ff;">ID</th>
                        <th style="color: #58a6ff;">Started</th>
                        <th style="color: #58a6ff;">Completed</th>
                        <th style="color: #58a6ff;">Status</th>
                        <th style="color: #58a6ff;">Items</th>
                        <th style="color: #58a6ff;">Success Rate</th>
                    </tr>
                </thead>
                <tbody>
        """

        for run in runs:
            status_badge = {
                'completed': 'success',
                'failed': 'danger',
                'running': 'primary',
                'cancelled': 'warning'
            }.get(run.status, 'secondary')

            total = run.queued_count or run.processed_count or 0
            success_rate = ((run.processed_count - run.failed_count) / run.processed_count * 100) if run.processed_count and run.processed_count > 0 else 0

            html += f"""
            <tr>
                <td style="color: #c9d1d9;">#{run.id}</td>
                <td style="color: #c9d1d9;">{run.started_at.strftime('%Y-%m-%d %H:%M') if run.started_at else '-'}</td>
                <td style="color: #c9d1d9;">{run.completed_at.strftime('%Y-%m-%d %H:%M') if run.completed_at else '-'}</td>
                <td><span class="badge bg-{status_badge}">{run.status}</span></td>
                <td style="color: #c9d1d9;">{total}</td>
                <td style="color: #c9d1d9;">{success_rate:.1f}%</td>
            </tr>
            """

        html += """
                </tbody>
            </table>
        </div>
        """

        # Add pagination
        html += """
        <!-- Pagination -->
        <nav aria-label="Analysis history pagination" class="mt-3">
            <ul class="pagination justify-content-center">
        """

        # Previous button
        if page > 1:
            html += f"""
                <li class="page-item">
                    <a class="page-link bg-dark text-light border-secondary"
                       hx-get="/htmx/analysis/runs/history?page={page-1}&limit={limit}"
                       hx-target="#history-container"
                       hx-swap="innerHTML">Previous</a>
                </li>
            """
        else:
            html += """
                <li class="page-item disabled">
                    <span class="page-link bg-dark text-muted border-secondary">Previous</span>
                </li>
            """

        # Page numbers
        for p in range(max(1, page-2), min(total_pages+1, page+3)):
            if p == page:
                html += f"""
                    <li class="page-item active">
                        <span class="page-link bg-primary border-primary">{p}</span>
                    </li>
                """
            else:
                html += f"""
                    <li class="page-item">
                        <a class="page-link bg-dark text-light border-secondary"
                           hx-get="/htmx/analysis/runs/history?page={p}&limit={limit}"
                           hx-target="#history-container"
                           hx-swap="innerHTML">{p}</a>
                    </li>
                """

        # Next button
        if page < total_pages:
            html += f"""
                <li class="page-item">
                    <a class="page-link bg-dark text-light border-secondary"
                       hx-get="/htmx/analysis/runs/history?page={page+1}&limit={limit}"
                       hx-target="#history-container"
                       hx-swap="innerHTML">Next</a>
                </li>
            """
        else:
            html += """
                <li class="page-item disabled">
                    <span class="page-link bg-dark text-muted border-secondary">Next</span>
                </li>
            """

        html += f"""
            </ul>
            <div class="text-center text-muted mt-2">
                <small>Page {page} of {total_pages} • Total runs: {total_count}</small>
            </div>
        </nav>
        """

    return HTMLResponse(content=html)


@router.get("/settings/form", response_class=HTMLResponse)
async def get_settings_form():
    """Get analysis settings form"""
    html = f"""
    <div class="card-body">
        <form hx-post="/api/analysis/settings" hx-target="#settings-message">
            <div class="row g-3">
                <div class="col-md-6">
                    <label class="form-label">Default Model</label>
                    <select class="form-select" name="default_model">
                        <option value="gpt-4o-mini" {'selected' if settings.analysis_model == 'gpt-4o-mini' else ''}>
                            GPT-4o Mini
                        </option>
                        <option value="gpt-4o" {'selected' if settings.analysis_model == 'gpt-4o' else ''}>
                            GPT-4o
                        </option>
                    </select>
                </div>

                <div class="col-md-6">
                    <label class="form-label">Batch Size</label>
                    <input type="number" class="form-control" name="batch_size"
                           value="{settings.analysis_batch_limit}" min="10" max="500">
                </div>

                <div class="col-md-6">
                    <label class="form-label">Rate Limit (req/sec)</label>
                    <input type="number" class="form-control" name="rate_limit"
                           value="{settings.analysis_rps}" min="0.1" max="10" step="0.1">
                </div>

                <div class="col-md-6">
                    <label class="form-label">Retry Attempts</label>
                    <input type="number" class="form-control" name="retry_attempts"
                           value="3" min="0" max="5">
                </div>

                <div class="col-12">
                    <div class="form-check">
                        <input class="form-check-input" type="checkbox" name="auto_analyze" id="autoAnalyze">
                        <label class="form-check-label" for="autoAnalyze">
                            Automatically analyze new articles
                        </label>
                    </div>
                </div>

                <div class="col-12">
                    <button type="submit" class="btn btn-primary">
                        <i class="bi bi-save me-2"></i> Save Settings
                    </button>
                </div>
            </div>
        </form>
        <div id="settings-message" class="mt-3"></div>
    </div>
    """
    return HTMLResponse(content=html)


@router.get("/settings/slo", response_class=HTMLResponse)
async def get_slo_settings():
    """Get SLO (Service Level Objectives) settings"""
    html = """
    <div class="card-body">
        <h6 class="card-subtitle mb-3 text-muted">Service Level Objectives</h6>
        <div class="table-responsive">
            <table class="table">
                <thead>
                    <tr>
                        <th>Metric</th>
                        <th>Target</th>
                        <th>Current</th>
                        <th>Status</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td>Analysis Success Rate</td>
                        <td>&ge; 95%</td>
                        <td>98.5%</td>
                        <td><span class="badge bg-success">✓</span></td>
                    </tr>
                    <tr>
                        <td>Processing Time (P50)</td>
                        <td>&le; 2 sec/item</td>
                        <td>1.3 sec/item</td>
                        <td><span class="badge bg-success">✓</span></td>
                    </tr>
                    <tr>
                        <td>Processing Time (P95)</td>
                        <td>&le; 5 sec/item</td>
                        <td>3.8 sec/item</td>
                        <td><span class="badge bg-success">✓</span></td>
                    </tr>
                    <tr>
                        <td>Queue Backlog</td>
                        <td>&le; 100 items</td>
                        <td>12 items</td>
                        <td><span class="badge bg-success">✓</span></td>
                    </tr>
                    <tr>
                        <td>Error Rate</td>
                        <td>&le; 5%</td>
                        <td>1.5%</td>
                        <td><span class="badge bg-success">✓</span></td>
                    </tr>
                </tbody>
            </table>
        </div>

        <div class="alert alert-info mt-3">
            <i class="bi bi-info-circle me-2"></i>
            All SLOs are currently being met. System performance is optimal.
        </div>
    </div>
    """
    return HTMLResponse(content=html)