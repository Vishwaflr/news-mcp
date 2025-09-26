"""
Clean HTMX endpoints for Analysis Control Center
Directly works with database to avoid model conflicts
"""

from fastapi import APIRouter, Depends, Query
from fastapi.responses import HTMLResponse
from sqlmodel import Session, text
from app.database import get_session
from app.core.logging_config import get_logger
from datetime import datetime

logger = get_logger(__name__)
router = APIRouter(prefix="/htmx/analysis", tags=["htmx"])


@router.get("/runs/active", response_class=HTMLResponse)
async def get_active_runs(db: Session = Depends(get_session)):
    """Get active analysis runs - clean implementation"""
    try:
        result = db.execute(text("""
            SELECT
                ar.id,
                ar.status,
                ar.started_at,
                COUNT(*) as total_count,
                COUNT(*) FILTER (WHERE ari.state IN ('completed', 'failed', 'skipped')) as processed_count,
                COUNT(*) FILTER (WHERE ari.state = 'failed') as failed_count
            FROM analysis_runs ar
            LEFT JOIN analysis_run_items ari ON ari.run_id = ar.id
            WHERE ar.status IN ('pending', 'running', 'paused')
            GROUP BY ar.id, ar.status, ar.started_at
            ORDER BY ar.created_at DESC
            LIMIT 10
        """))
        runs = result.fetchall()

        if not runs:
            return HTMLResponse("""
            <div class="alert alert-info">
                <i class="bi bi-info-circle me-2"></i>
                No active analysis runs at the moment.
            </div>
            """)

        html = '<div class="list-group">'
        for run in runs:
            run_id, status, started_at, total, processed, failed = run
            progress = (processed / total * 100) if total > 0 else 0

            status_badge = {
                'running': 'primary',
                'paused': 'warning',
                'pending': 'info'
            }.get(status, 'secondary')

            html += f"""
            <div class="list-group-item" style="background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1);">
                <div class="d-flex justify-content-between align-items-center">
                    <div>
                        <h6 class="mb-1" style="color: #e9ecef;">Analysis Run #{run_id}</h6>
                        <p class="mb-1" style="color: #adb5bd;">Started: {started_at or 'Pending'}</p>
                    </div>
                    <span class="badge bg-{status_badge}">{status.upper()}</span>
                </div>
                <div class="progress mt-2" style="height: 24px; background: rgba(0,0,0,0.3);">
                    <div class="progress-bar bg-{status_badge}" role="progressbar"
                         style="width: {progress:.1f}%; font-size: 14px;">{int(progress)}%</div>
                </div>
                <small style="color: #dee2e6; font-size: 0.9rem;"><strong>{processed}/{total}</strong> items processed</small>
            </div>
            """
        html += '</div>'
        return HTMLResponse(html)

    except Exception as e:
        logger.error(f"Error in get_active_runs: {e}")
        return HTMLResponse("""
        <div class="alert alert-danger">
            <i class="bi bi-exclamation-triangle me-2"></i>
            Error loading active runs.
        </div>
        """)


@router.get("/runs/history", response_class=HTMLResponse)
async def get_runs_history(
    db: Session = Depends(get_session),
    page: int = Query(1, ge=1),
    limit: int = Query(10)
):
    """Get analysis run history - clean implementation"""
    try:
        offset = (page - 1) * limit

        # Get total count
        count_result = db.execute(text("SELECT COUNT(*) FROM analysis_runs"))
        total_count = count_result.scalar() or 0
        total_pages = max(1, (total_count + limit - 1) // limit)

        result = db.execute(text("""
            SELECT
                ar.id,
                ar.started_at,
                ar.completed_at,
                ar.status,
                COUNT(*) as total_count,
                COUNT(*) FILTER (WHERE ari.state IN ('completed', 'failed', 'skipped')) as processed_count,
                COUNT(*) FILTER (WHERE ari.state = 'failed') as failed_count
            FROM analysis_runs ar
            LEFT JOIN analysis_run_items ari ON ari.run_id = ar.id
            GROUP BY ar.id, ar.started_at, ar.completed_at, ar.status
            ORDER BY ar.created_at DESC
            LIMIT :limit OFFSET :offset
        """), {"limit": limit, "offset": offset})
        runs = result.fetchall()

        if not runs:
            return HTMLResponse("""
            <div class="alert alert-info">
                <i class="bi bi-info-circle me-2"></i>
                No analysis run history available.
            </div>
            """)

        # Build table
        html = """
        <div class="table-responsive">
            <table class="table table-dark table-striped table-hover">
                <thead>
                    <tr>
                        <th>ID</th>
                        <th>Started</th>
                        <th>Completed</th>
                        <th>Status</th>
                        <th>Items</th>
                        <th>Success Rate</th>
                    </tr>
                </thead>
                <tbody>
        """

        for run in runs:
            run_id, started, completed, status, total, processed, failed = run
            success_count = processed - failed
            success_rate = (success_count / processed * 100) if processed > 0 else 0

            status_class = {
                'completed': 'success',
                'failed': 'danger',
                'cancelled': 'warning',
                'running': 'primary'
            }.get(status, 'secondary')

            started_str = started.strftime('%Y-%m-%d %H:%M') if started else 'N/A'
            completed_str = completed.strftime('%Y-%m-%d %H:%M') if completed else 'N/A'

            html += f"""
            <tr>
                <td>#{run_id}</td>
                <td>{started_str}</td>
                <td>{completed_str}</td>
                <td><span class="badge bg-{status_class}">{status}</span></td>
                <td>{processed}/{total}</td>
                <td>{success_rate:.1f}%</td>
            </tr>
            """

        html += """
                </tbody>
            </table>
        </div>
        """

        # Add pagination
        if total_pages > 1:
            html += '<nav><ul class="pagination justify-content-center">'

            # Previous button
            if page > 1:
                html += f'''
                <li class="page-item">
                    <a class="page-link" href="#"
                       hx-get="/htmx/analysis/runs/history?page={page-1}&limit={limit}"
                       hx-target="#run-history-table">Previous</a>
                </li>
                '''

            # Page numbers
            for p in range(max(1, page-2), min(total_pages+1, page+3)):
                active = 'active' if p == page else ''
                html += f'''
                <li class="page-item {active}">
                    <a class="page-link" href="#"
                       hx-get="/htmx/analysis/runs/history?page={p}&limit={limit}"
                       hx-target="#run-history-table">{p}</a>
                </li>
                '''

            # Next button
            if page < total_pages:
                html += f'''
                <li class="page-item">
                    <a class="page-link" href="#"
                       hx-get="/htmx/analysis/runs/history?page={page+1}&limit={limit}"
                       hx-target="#run-history-table">Next</a>
                </li>
                '''

            html += '</ul></nav>'

        return HTMLResponse(html)

    except Exception as e:
        logger.error(f"Error in get_runs_history: {e}")
        return HTMLResponse("""
        <div class="alert alert-danger">
            <i class="bi bi-exclamation-triangle me-2"></i>
            Error loading run history.
        </div>
        """)


@router.get("/stats-horizontal", response_class=HTMLResponse)
async def get_stats_horizontal(db: Session = Depends(get_session)):
    """Get horizontal statistics display"""
    try:
        # Get statistics with fallback queries
        try:
            total_items = db.execute(text("SELECT COUNT(*) FROM items")).scalar() or 0
        except:
            total_items = 0

        try:
            analyzed_items = db.execute(text("SELECT COUNT(DISTINCT item_id) FROM item_analysis WHERE item_id IS NOT NULL")).scalar() or 0
        except:
            analyzed_items = 0

        try:
            active_feeds = db.execute(text("SELECT COUNT(*) FROM feeds WHERE status = 'ACTIVE'")).scalar() or 0
        except:
            active_feeds = 0

        try:
            active_runs = db.execute(text("SELECT COUNT(*) FROM analysis_runs WHERE status = 'running'")).scalar() or 0
        except:
            active_runs = 0

        stats = (total_items, analyzed_items, active_feeds, active_runs)

        total, analyzed, feeds, runs = stats or (0, 0, 0, 0)
        coverage = (analyzed / total * 100) if total > 0 else 0

        html = f"""
        <div class="row g-3">
            <div class="col-md-3">
                <div class="stat-card">
                    <div class="stat-value">{total:,}</div>
                    <div class="stat-label">Total Articles</div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="stat-card">
                    <div class="stat-value">{analyzed:,}</div>
                    <div class="stat-label">Analyzed</div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="stat-card">
                    <div class="stat-value">{coverage:.1f}%</div>
                    <div class="stat-label">Coverage</div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="stat-card">
                    <div class="stat-value">{runs}</div>
                    <div class="stat-label">Active Runs</div>
                </div>
            </div>
        </div>
        """

        return HTMLResponse(html)

    except Exception as e:
        logger.error(f"Error in get_stats_horizontal: {e}")
        return HTMLResponse('<div class="alert alert-warning">Unable to load statistics</div>')


@router.get("/articles-live", response_class=HTMLResponse)
async def get_articles_live(
    db: Session = Depends(get_session),
    mode: str = Query("latest", description="Selection mode: latest, oldest, random, unanalyzed, time_range"),
    count: int = Query(5, ge=1, le=1000),
    feed_id: str = Query("", description="Optional feed filter"),
    date_from: str = Query("", description="Date filter from (YYYY-MM-DD)"),
    date_to: str = Query("", description="Date filter to (YYYY-MM-DD)"),
    hours: int = Query(0, ge=0, description="For time_range mode: hours to look back"),
    unanalyzed_only: bool = Query(False, description="Show only unanalyzed items")
):
    """Get live articles for analysis preview"""
    try:
        # Build dynamic query based on parameters
        conditions = []
        params = {"count": count}

        if feed_id and feed_id.strip():
            conditions.append("feed_id = :feed_id")
            params["feed_id"] = int(feed_id)

        if date_from and date_from.strip():
            conditions.append("published >= :date_from")
            params["date_from"] = date_from

        if date_to and date_to.strip():
            conditions.append("published <= :date_to")
            params["date_to"] = date_to

        # Handle time_range mode
        if mode == "time_range" and hours > 0:
            conditions.append(f"i.published >= NOW() - INTERVAL '{hours} hours'")

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        # Order clause based on mode
        order_clause = {
            "latest": "i.published DESC NULLS LAST, i.created_at DESC",
            "oldest": "i.published ASC NULLS LAST, i.created_at ASC",
            "random": "RANDOM()",
            "unanalyzed": "i.published DESC NULLS LAST, i.created_at DESC",
            "time_range": "i.published DESC NULLS LAST, i.created_at DESC"
        }.get(mode, "i.published DESC NULLS LAST, i.created_at DESC")

        # Only filter for unanalyzed if explicitly requested or mode is "unanalyzed"
        if mode == "unanalyzed" or unanalyzed_only:
            if where_clause == "1=1":
                where_clause = "i.id NOT IN (SELECT DISTINCT item_id FROM item_analysis WHERE item_id IS NOT NULL)"
            else:
                where_clause += " AND i.id NOT IN (SELECT DISTINCT item_id FROM item_analysis WHERE item_id IS NOT NULL)"

        query = f"""
        SELECT
            i.id,
            i.title,
            i.link,
            i.published,
            i.feed_id,
            i.author,
            i.description,
            f.title as feed_title,
            ia.sentiment_json->>'overall' as sentiment_label,
            ia.item_id as has_analysis
        FROM items i
        LEFT JOIN feeds f ON f.id = i.feed_id
        LEFT JOIN item_analysis ia ON ia.item_id = i.id
        WHERE {where_clause}
        ORDER BY {order_clause}
        LIMIT :count
        """

        result = db.execute(text(query), params)
        articles = result.fetchall()

        if not articles:
            return HTMLResponse("""
            <div class="alert alert-info">
                <i class="bi bi-info-circle me-2"></i>
                No articles found matching the current selection criteria.
            </div>
            """)

        html = """
        <div class="articles-live-container">
        """

        for article in articles:
            item_id, title, link, published, feed_id, author, description, feed_title, sentiment_label, has_analysis = article
            published_str = published.strftime('%d.%m.%Y %H:%M') if published else 'No date'

            # Truncate long titles for better layout
            display_title = title[:80] + "..." if len(title) > 80 else title

            # Truncate description
            display_desc = (description[:120] + "...") if description and len(description) > 120 else (description or "")

            # Analysis status badge
            if has_analysis and sentiment_label:
                if sentiment_label.lower() == 'positive':
                    analysis_badge = '<span class="badge bg-success">✅ Positive</span>'
                elif sentiment_label.lower() == 'negative':
                    analysis_badge = '<span class="badge bg-danger">❌ Negative</span>'
                else:
                    analysis_badge = '<span class="badge bg-secondary">➖ Neutral</span>'
            else:
                analysis_badge = '<span class="badge bg-warning">No Analysis</span>'

            html += f"""
            <div class="article-card mb-3">
                <div class="article-header">
                    <h6 class="article-title mb-2">{display_title}</h6>
                    <div class="d-flex justify-content-between align-items-center mb-2">
                        <div>
                            {analysis_badge}
                        </div>
                        <small class="text-muted">{published_str}</small>
                    </div>
                    <div class="article-meta">
                        <div class="text-info mb-1">
                            <strong>{feed_title or 'Unknown Feed'}</strong>
                        </div>
                        {f'<div class="text-muted small mb-1">By: {author}</div>' if author else ''}
                    </div>
                    {f'<div class="article-description text-muted small mt-2">{display_desc}</div>' if display_desc else ''}
                </div>
                <div class="article-actions mt-2">
                    {f'<a href="{link}" target="_blank" class="btn btn-sm btn-outline-light">📖 Read</a>' if link else ''}
                    <small class="text-muted ms-2">#{item_id}</small>
                </div>
            </div>
            """

        html += """
        </div>
        <div class="articles-footer mt-3">
            <small class="text-muted">
                <i class="bi bi-clock me-1"></i>
                Updated: """ + datetime.now().strftime('%H:%M:%S') + """
            </small>
        </div>

        <style>
        .articles-live-container {
            max-height: 600px;
            overflow-y: auto;
            padding-right: 10px;
        }
        .article-card {
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 8px;
            padding: 15px;
            transition: all 0.2s ease;
        }
        .article-card:hover {
            background: rgba(255, 255, 255, 0.08);
            border-color: rgba(255, 255, 255, 0.2);
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
        }
        .article-title {
            color: #e8e9ea;
            font-size: 1rem;
            line-height: 1.4;
            margin-bottom: 10px;
            font-weight: 500;
        }
        .article-meta {
            margin-bottom: 10px;
        }
        .article-description {
            line-height: 1.5;
            margin-top: 8px;
            padding-top: 8px;
            border-top: 1px solid rgba(255, 255, 255, 0.05);
        }
        .article-actions {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-top: 10px;
            padding-top: 10px;
            border-top: 1px solid rgba(255, 255, 255, 0.05);
        }
        .articles-footer {
            text-align: center;
            border-top: 1px solid rgba(255, 255, 255, 0.1);
            padding-top: 10px;
        }
        /* Scrollbar styling */
        .articles-live-container::-webkit-scrollbar {
            width: 8px;
        }
        .articles-live-container::-webkit-scrollbar-track {
            background: rgba(255, 255, 255, 0.05);
            border-radius: 4px;
        }
        .articles-live-container::-webkit-scrollbar-thumb {
            background: rgba(255, 255, 255, 0.2);
            border-radius: 4px;
        }
        .articles-live-container::-webkit-scrollbar-thumb:hover {
            background: rgba(255, 255, 255, 0.3);
        }
        </style>
        """

        return HTMLResponse(html)

    except Exception as e:
        logger.error(f"Error in get_articles_live: {e}")
        return HTMLResponse("""
        <div class="alert alert-danger">
            <i class="bi bi-exclamation-triangle me-2"></i>
            Error loading articles: """ + str(e) + """
        </div>
        """)


@router.get("/preview-start", response_class=HTMLResponse)
async def get_preview_start(
    db: Session = Depends(get_session),
    mode: str = Query("latest", description="Selection mode: latest, oldest, random"),
    count: int = Query(50, ge=1, le=1000),
    feed_id: str = Query("", description="Optional feed filter"),
    date_from: str = Query("", description="Date filter from (YYYY-MM-DD)"),
    date_to: str = Query("", description="Date filter to (YYYY-MM-DD)")
):
    """Get preview and start information for analysis"""
    try:
        # Count total items based on filters
        conditions = []
        params = {"count": count}

        if feed_id and feed_id.strip():
            conditions.append("i.feed_id = :feed_id")
            params["feed_id"] = int(feed_id)

        if date_from and date_from.strip():
            conditions.append("i.published >= :date_from")
            params["date_from"] = date_from

        if date_to and date_to.strip():
            conditions.append("i.published <= :date_to")
            params["date_to"] = date_to

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        # Get total count of items matching criteria
        total_query = f"""
        SELECT COUNT(*) FROM items i WHERE {where_clause}
        """
        total_result = db.execute(text(total_query), params)
        total_count = total_result.scalar() or 0

        # Get count of already analyzed items
        analyzed_query = f"""
        SELECT COUNT(*) FROM items i
        WHERE {where_clause}
        AND EXISTS (SELECT 1 FROM item_analysis ia WHERE ia.item_id = i.id)
        """
        analyzed_result = db.execute(text(analyzed_query), params)
        analyzed_count = analyzed_result.scalar() or 0

        # Calculate new items to analyze (respecting limit)
        new_items = min(count, total_count - analyzed_count)
        if new_items < 0:
            new_items = 0

        # Estimate costs (using GPT-4.1 Nano pricing as default)
        cost_per_item = 0.0001  # $0.10 per 1000 items
        estimated_cost = new_items * cost_per_item

        # Estimate time (1 item per second as default rate)
        estimated_minutes = max(1, new_items // 60)

        html = f"""
        <div class="preview-panel p-3 bg-dark rounded">
            <h5 class="mb-3">📊 Preview & Start</h5>

            <!-- Analysis Breakdown Row -->
            <div class="row text-center mb-3">
                <div class="col-4">
                    <div class="preview-stat">
                        <div class="stat-value text-info">{min(count, total_count)}</div>
                        <div class="stat-label text-white">Total Selected</div>
                    </div>
                </div>
                <div class="col-4">
                    <div class="preview-stat">
                        <div class="stat-value text-muted">{analyzed_count}</div>
                        <div class="stat-label text-white">Already Analyzed</div>
                    </div>
                </div>
                <div class="col-4">
                    <div class="preview-stat">
                        <div class="stat-value text-primary">{new_items}</div>
                        <div class="stat-label text-white">To Analyze</div>
                    </div>
                </div>
            </div>

            <!-- Cost and Time Row -->
            <div class="row text-center mb-3">
                <div class="col-6">
                    <div class="preview-stat">
                        <div class="stat-value text-success">${estimated_cost:.3f}</div>
                        <div class="stat-label text-white">Estimated Cost</div>
                    </div>
                </div>
                <div class="col-6">
                    <div class="preview-stat">
                        <div class="stat-value text-warning">{estimated_minutes}</div>
                        <div class="stat-label text-white">Est. Minutes</div>
                    </div>
                </div>
            </div>

            <div class="alert alert-info">
                <small>
                    <i class="bi bi-info-circle me-2"></i>
                    {f"Ready to analyze {new_items} new articles" if new_items > 0 else "No new articles to analyze with current selection"}
                </small>
            </div>
        </div>
        """

        return HTMLResponse(html)

    except Exception as e:
        logger.error(f"Error in get_preview_start: {e}")
        return HTMLResponse(f"""
        <div class="alert alert-danger">
            <i class="bi bi-exclamation-triangle me-2"></i>
            Error loading preview: {str(e)}
        </div>
        """)


@router.get("/settings/form", response_class=HTMLResponse)
async def get_settings_form(db: Session = Depends(get_session)):
    """Get analysis settings form"""
    try:
        # Get current default settings (could be from database or config)
        html = """
        <div class="card">
            <div class="card-header">
                <h6 class="card-title mb-0">
                    <i class="bi bi-gear me-2"></i>Analysis Settings
                </h6>
            </div>
            <div class="card-body">
                <form hx-post="/api/user-settings/default-params" hx-trigger="submit" hx-swap="outerHTML">
                    <div class="row g-3">
                        <div class="col-md-6">
                            <label for="model_tag" class="form-label">AI Model</label>
                            <select class="form-select" id="model_tag" name="model_tag">
                                <option value="gpt-4.1-nano" selected>GPT-4.1 Nano (Fast)</option>
                                <option value="gpt-4.1">GPT-4.1 (Standard)</option>
                                <option value="gpt-4.1-pro">GPT-4.1 Pro (Detailed)</option>
                            </select>
                        </div>
                        <div class="col-md-6">
                            <label for="batch_size" class="form-label">Batch Size</label>
                            <select class="form-select" id="batch_size" name="batch_size">
                                <option value="5" selected>5 articles</option>
                                <option value="10">10 articles</option>
                                <option value="25">25 articles</option>
                                <option value="50">50 articles</option>
                            </select>
                        </div>
                        <div class="col-md-6">
                            <label for="temperature" class="form-label">Temperature</label>
                            <input type="range" class="form-range" id="temperature" name="temperature"
                                   min="0" max="1" step="0.1" value="0.3">
                            <div class="form-text">
                                <span id="temperature-value">0.3</span> - Lower = more focused, Higher = more creative
                            </div>
                        </div>
                        <div class="col-md-6">
                            <label for="timeout" class="form-label">Timeout (seconds)</label>
                            <input type="number" class="form-control" id="timeout" name="timeout"
                                   min="30" max="300" value="120">
                        </div>
                    </div>
                    <div class="row g-3 mt-3">
                        <div class="col-12">
                            <div class="form-check">
                                <input class="form-check-input" type="checkbox" id="auto_analyze"
                                       name="auto_analyze" checked>
                                <label class="form-check-label" for="auto_analyze">
                                    Enable automatic analysis for new articles
                                </label>
                            </div>
                        </div>
                        <div class="col-12">
                            <div class="form-check">
                                <input class="form-check-input" type="checkbox" id="include_content"
                                       name="include_content">
                                <label class="form-check-label" for="include_content">
                                    Include full article content in analysis (slower but more detailed)
                                </label>
                            </div>
                        </div>
                    </div>
                    <div class="mt-4">
                        <button type="submit" class="btn btn-primary">
                            <i class="bi bi-save me-2"></i>Save Settings
                        </button>
                        <button type="button" class="btn btn-outline-secondary ms-2"
                                onclick="this.closest('form').reset()">
                            <i class="bi bi-arrow-clockwise me-2"></i>Reset
                        </button>
                    </div>
                </form>
            </div>
        </div>

        <script>
        // Update temperature display
        document.getElementById('temperature').addEventListener('input', function(e) {
            document.getElementById('temperature-value').textContent = e.target.value;
        });
        </script>
        """

        return HTMLResponse(html)

    except Exception as e:
        logger.error(f"Error in get_settings_form: {e}")
        return HTMLResponse("""
        <div class="alert alert-danger">
            <i class="bi bi-exclamation-triangle me-2"></i>
            Error loading settings form.
        </div>
        """)


@router.get("/settings/slo", response_class=HTMLResponse)
async def get_settings_slo(db: Session = Depends(get_session)):
    """Get SLO (Service Level Objectives) settings"""
    try:
        # Try to get current SLO metrics from database (table may not exist yet)
        try:
            slo_stats = db.execute(text("""
            SELECT
                COUNT(*) as total_runs,
                AVG(
                    CASE WHEN completed_at IS NOT NULL AND started_at IS NOT NULL
                    THEN EXTRACT(EPOCH FROM (completed_at - started_at)) / 60.0
                    END
                ) as avg_duration_minutes,
                COUNT(CASE WHEN status = 'completed' THEN 1 END) * 100.0 /
                    NULLIF(COUNT(CASE WHEN status IN ('completed', 'failed') THEN 1 END), 0) as success_rate
            FROM analysis_runs
            WHERE created_at > NOW() - INTERVAL '24 hours'
            """)).fetchone()
        except Exception:
            # Fallback to dummy data if table doesn't exist
            slo_stats = (0, 0, 100.0)

        total_runs, avg_duration, success_rate = slo_stats or (0, 0, 0)

        # SLO targets
        target_success_rate = 95.0
        target_max_duration = 30.0  # minutes

        # Status indicators
        success_status = "success" if (success_rate or 0) >= target_success_rate else "danger"
        duration_status = "success" if (avg_duration or 0) <= target_max_duration else "warning"

        html = f"""
        <div class="card">
            <div class="card-header">
                <h6 class="card-title mb-0">
                    <i class="bi bi-speedometer2 me-2"></i>Service Level Objectives
                </h6>
            </div>
            <div class="card-body">
                <div class="row g-3">
                    <div class="col-md-6">
                        <div class="d-flex justify-content-between align-items-center">
                            <div>
                                <div class="fw-semibold">Success Rate</div>
                                <div class="text-muted small">Last 24 hours</div>
                            </div>
                            <div class="text-end">
                                <div class="fs-4 fw-bold text-{success_status}">
                                    {success_rate:.1f}%
                                </div>
                                <div class="small text-muted">Target: {target_success_rate}%</div>
                            </div>
                        </div>
                        <div class="progress mt-2" style="height: 8px;">
                            <div class="progress-bar bg-{success_status}"
                                 style="width: {min(100, success_rate or 0):.1f}%"></div>
                        </div>
                    </div>
                    <div class="col-md-6">
                        <div class="d-flex justify-content-between align-items-center">
                            <div>
                                <div class="fw-semibold">Average Duration</div>
                                <div class="text-muted small">Per analysis run</div>
                            </div>
                            <div class="text-end">
                                <div class="fs-4 fw-bold text-{duration_status}">
                                    {avg_duration:.1f}m
                                </div>
                                <div class="small text-muted">Target: <{target_max_duration}m</div>
                            </div>
                        </div>
                        <div class="progress mt-2" style="height: 8px;">
                            <div class="progress-bar bg-{duration_status}"
                                 style="width: {min(100, (avg_duration or 0) / target_max_duration * 100):.1f}%"></div>
                        </div>
                    </div>
                </div>
                <hr class="my-3">
                <div class="row g-3">
                    <div class="col-md-4 text-center">
                        <div class="fs-3 fw-bold text-primary">{total_runs}</div>
                        <div class="text-muted">Total Runs Today</div>
                    </div>
                    <div class="col-md-4 text-center">
                        <div class="fs-3 fw-bold text-info">
                            {(success_rate * total_runs / 100):.0f}
                        </div>
                        <div class="text-muted">Successful Runs</div>
                    </div>
                    <div class="col-md-4 text-center">
                        <div class="fs-3 fw-bold text-warning">
                            {total_runs - (success_rate * total_runs / 100):.0f}
                        </div>
                        <div class="text-muted">Failed Runs</div>
                    </div>
                </div>
                <div class="mt-3">
                    <small class="text-muted">
                        <i class="bi bi-clock me-1"></i>
                        Last updated: {datetime.now().strftime('%H:%M:%S')}
                        <span class="ms-3">
                            <i class="bi bi-arrow-clockwise me-1"></i>
                            Auto-refresh: 30s
                        </span>
                    </small>
                </div>
            </div>
        </div>
        """

        return HTMLResponse(html)

    except Exception as e:
        logger.error(f"Error in get_settings_slo: {e}")
        return HTMLResponse("""
        <div class="alert alert-danger">
            <i class="bi bi-exclamation-triangle me-2"></i>
            Error loading SLO metrics.
        </div>
        """)


@router.get("/target-selection", response_class=HTMLResponse)
async def get_target_selection(db: Session = Depends(get_session)):
    """Get target selection panel with article selection options"""
    try:
        html = """
        <div class="card bg-dark border-secondary">
            <div class="card-header">
                <h6 class="card-title mb-0">🎯 Target Selection</h6>
            </div>
            <div class="card-body">
                <div class="mb-3">
                    <button type="button" class="btn btn-primary btn-sm active" onclick="selectLatestMode(this)">
                        📰 Latest Articles
                    </button>
                    <button type="button" class="btn btn-outline-primary btn-sm" onclick="selectUnanalyzedMode(this)">
                        🔍 Unanalyzed Only
                    </button>
                </div>

                <div class="mb-3">
                    <label for="article-count" class="form-label">Number of articles:</label>
                    <input type="number" class="form-control" id="article-count" value="50" min="1" max="1000">
                </div>

                <div class="active-selection mb-3">
                    <div class="alert alert-success">
                        <strong>✓ Active Selection:</strong> <span id="selection-summary">Latest 50 articles</span>
                    </div>
                </div>

                <button type="button" class="btn btn-success w-100" onclick="applySelection()">
                    ✅ Apply Selection
                </button>
            </div>
        </div>

        <script>
        let currentMode = 'latest';
        let currentCount = 50;

        function selectLatestMode(btn) {
            document.querySelectorAll('.btn').forEach(b => {
                b.classList.remove('btn-primary', 'active');
                b.classList.add('btn-outline-primary');
            });
            btn.classList.add('btn-primary', 'active');
            btn.classList.remove('btn-outline-primary');
            currentMode = 'latest';
            updateSummary();
        }

        function selectUnanalyzedMode(btn) {
            document.querySelectorAll('.btn').forEach(b => {
                b.classList.remove('btn-primary', 'active');
                b.classList.add('btn-outline-primary');
            });
            btn.classList.add('btn-primary', 'active');
            btn.classList.remove('btn-outline-primary');
            currentMode = 'unanalyzed';
            updateSummary();
        }

        function updateSummary() {
            const count = document.getElementById('article-count').value || 50;
            currentCount = count;
            let summary = '';
            if (currentMode === 'latest') {
                summary = 'Latest ' + count + ' articles';
            } else {
                summary = 'Latest ' + count + ' unanalyzed articles';
            }
            document.getElementById('selection-summary').textContent = summary;
        }

        function applySelection() {
            // Update live articles based on selection
            if (window.updateLiveArticles) {
                window.updateLiveArticles(currentMode, currentCount);
            }

            // Feedback
            const btn = event.target;
            const oldText = btn.innerHTML;
            btn.innerHTML = '✅ Applied!';
            setTimeout(() => { btn.innerHTML = oldText; }, 2000);
        }

        // Listen for count changes
        document.getElementById('article-count').addEventListener('input', updateSummary);

        // Initialize
        updateSummary();
        </script>
        """

        return HTMLResponse(html)

    except Exception as e:
        logger.error(f"Error in get_target_selection: {e}")
        return HTMLResponse("""
        <div class="alert alert-danger">
            <i class="bi bi-exclamation-triangle me-2"></i>
            Error loading target selection.
        </div>
        """)