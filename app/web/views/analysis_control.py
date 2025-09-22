from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from typing import Optional, List
import logging

from app.domain.analysis.control import (
    AnalysisRun, RunStatus, SLO_TARGETS
)
from app.repositories.analysis_control import AnalysisControlRepo
from sqlmodel import Session, text
from app.database import engine
from app.repositories.analysis import AnalysisRepo

router = APIRouter(prefix="/htmx/analysis", tags=["htmx-analysis-control"])
logger = logging.getLogger(__name__)

templates = Jinja2Templates(directory="templates")

@router.get("/quick-actions", response_class=HTMLResponse)
def get_quick_actions_partial() -> str:
    """Quick actions have been removed - returns empty content"""
    return ""

@router.get("/feeds", response_class=HTMLResponse)
def get_feeds_partial() -> str:
    """Render feed selection checkboxes"""
    try:
        with Session(engine) as session:
            results = session.execute(text("""
                SELECT f.id, f.title, f.url, COUNT(i.id) as item_count,
                       COUNT(CASE WHEN a.item_id IS NULL THEN 1 END) as unanalyzed_count
                FROM feeds f
                LEFT JOIN items i ON i.feed_id = f.id
                LEFT JOIN item_analysis a ON a.item_id = i.id
                GROUP BY f.id, f.title, f.url
                ORDER BY f.title ASC
            """)).fetchall()

        html = '<div class="row">'
        for row in results:
            feed_id, title, url, item_count, unanalyzed_count = row
            display_title = title or url[:50] + "..."

            html += f"""
            <div class="col-md-6 mb-2">
                <div class="form-check">
                    <input class="form-check-input" type="checkbox" value="{feed_id}"
                           id="feed_{feed_id}" x-model="scope.feed_ids" @change="updatePreview()">
                    <label class="form-check-label" for="feed_{feed_id}">
                        <strong>{display_title}</strong><br>
                        <small class="text-muted">
                            {item_count} items, {unanalyzed_count} unanalyzed
                        </small>
                    </label>
                </div>
            </div>
            """

        html += '</div>'
        return html

    except Exception as e:
        logger.error(f"Failed to get feeds: {e}")
        return '<div class="alert alert-danger">Failed to load feeds</div>'

@router.get("/stats", response_class=HTMLResponse)
def get_stats_partial() -> str:
    """Render overall statistics"""
    try:
        stats = AnalysisRepo.get_analysis_stats()
        pending_count = AnalysisRepo.count_pending_analysis()

        total_items = stats.get("total_analyzed", 0) + pending_count
        coverage = stats.get("total_analyzed", 0) / max(total_items, 1)
        coverage_percent = round(coverage * 100, 1)

        # Coverage SLO indicators
        coverage_slo_class = "slo-green" if coverage >= 0.9 else "slo-yellow" if coverage >= 0.75 else "slo-red"

        sentiment_dist = stats.get("sentiment_distribution", {})
        positive = sentiment_dist.get("positive", 0)
        negative = sentiment_dist.get("negative", 0)
        neutral = sentiment_dist.get("neutral", 0)

        html = f"""
        <div class="row text-center">
            <div class="col-6 col-md-3 mb-3">
                <div class="metric-card p-3 border rounded">
                    <h4 class="text-primary mb-1">{total_items:,}</h4>
                    <small class="text-muted">Total Items</small>
                </div>
            </div>
            <div class="col-6 col-md-3 mb-3">
                <div class="metric-card p-3 border rounded">
                    <h4 class="text-success mb-1">{stats.get('total_analyzed', 0):,}</h4>
                    <small class="text-muted">Analyzed</small>
                </div>
            </div>
            <div class="col-6 col-md-3 mb-3">
                <div class="metric-card p-3 border rounded">
                    <h4 class="text-warning mb-1">{pending_count:,}</h4>
                    <small class="text-muted">Pending</small>
                </div>
            </div>
            <div class="col-6 col-md-3 mb-3">
                <div class="metric-card p-3 border rounded">
                    <h4 class="mb-1">
                        <span class="slo-indicator {coverage_slo_class}"></span>
                        {coverage_percent}%
                    </h4>
                    <small class="text-muted">Coverage</small>
                </div>
            </div>
        </div>

        <div class="mt-3">
            <h6><i class="fas fa-chart-pie"></i> Sentiment Distribution</h6>
            <div class="row text-center">
                <div class="col-4">
                    <span class="badge bg-success fs-6">{positive}</span><br>
                    <small>Positive</small>
                </div>
                <div class="col-4">
                    <span class="badge bg-secondary fs-6">{neutral}</span><br>
                    <small>Neutral</small>
                </div>
                <div class="col-4">
                    <span class="badge bg-danger fs-6">{negative}</span><br>
                    <small>Negative</small>
                </div>
            </div>
        </div>

        <div class="mt-3">
            <div class="row">
                <div class="col-6">
                    <strong>Avg Impact:</strong> {stats.get('avg_impact', 0):.2f}
                </div>
                <div class="col-6">
                    <strong>Avg Urgency:</strong> {stats.get('avg_urgency', 0):.2f}
                </div>
            </div>
        </div>
        """

        return html

    except Exception as e:
        logger.error(f"Failed to get stats: {e}")
        return '<div class="alert alert-danger">Failed to load statistics</div>'

@router.get("/status", response_class=HTMLResponse)
def get_status_partial() -> str:
    """Render status overview"""
    try:
        active_runs = AnalysisControlRepo.get_active_runs()
        stats = AnalysisRepo.get_analysis_stats()
        pending_count = AnalysisRepo.count_pending_analysis()

        total_items = stats.get("total_analyzed", 0) + pending_count
        coverage = stats.get("total_analyzed", 0) / max(total_items, 1)
        coverage_percent = round(coverage * 100, 1)

        html = f"""
        <div class="row">
            <div class="col-md-3">
                <div class="card text-center">
                    <div class="card-body">
                        <h5 class="card-title">{len(active_runs)}</h5>
                        <p class="card-text">Active Runs</p>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card text-center">
                    <div class="card-body">
                        <h5 class="card-title">{pending_count:,}</h5>
                        <p class="card-text">Pending Items</p>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card text-center">
                    <div class="card-body">
                        <h5 class="card-title">{coverage_percent}%</h5>
                        <p class="card-text">Coverage</p>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card text-center">
                    <div class="card-body">
                        <h5 class="card-title">{stats.get('total_analyzed', 0):,}</h5>
                        <p class="card-text">Analyzed</p>
                    </div>
                </div>
            </div>
        </div>
        """
        return html

    except Exception as e:
        logger.error(f"Failed to get status: {e}")
        return '<div class="alert alert-danger">Failed to load status</div>'

@router.get("/active-runs", response_class=HTMLResponse)
def get_active_runs_partial() -> str:
    """Render active runs status"""
    try:
        active_runs = AnalysisControlRepo.get_active_runs()

        if not active_runs:
            return """
            <div class="text-center text-muted py-4">
                <i class="fas fa-sleep fa-2x mb-2"></i><br>
                No active runs
            </div>
            """

        html = ""
        for run in active_runs:
            # Status badge
            status_colors = {
                "pending": "secondary",
                "running": "primary",
                "paused": "warning"
            }
            status_color = status_colors.get(run.status, "secondary")

            # Progress calculation
            progress = run.metrics.progress_percent

            # SLO indicators
            error_slo_class = "slo-green" if run.metrics.error_rate <= SLO_TARGETS["error_rate"] else "slo-red"

            # Control buttons
            controls = ""
            if run.status == "running":
                controls = f"""
                <button class="btn btn-sm btn-warning me-1"
                        hx-post="/api/analysis/pause/{run.id}"
                        hx-target="#active-runs">
                    <i class="fas fa-pause"></i>
                </button>
                """
            elif run.status == "paused":
                controls = f"""
                <button class="btn btn-sm btn-success me-1"
                        hx-post="/api/analysis/start/{run.id}"
                        hx-target="#active-runs">
                    <i class="fas fa-play"></i>
                </button>
                """

            controls += f"""
            <button class="btn btn-sm btn-danger"
                    hx-post="/api/analysis/cancel/{run.id}"
                    hx-target="#active-runs"
                    hx-confirm="Cancel this run?">
                <i class="fas fa-stop"></i>
            </button>
            """

            eta_text = f"{run.metrics.eta_seconds // 60}m {run.metrics.eta_seconds % 60}s" if run.metrics.eta_seconds else "Calculating..."

            html += f"""
            <div class="card mb-3">
                <div class="card-body">
                    <div class="d-flex justify-content-between align-items-start mb-2">
                        <h6 class="mb-1">
                            Run #{run.id}
                            <span class="badge bg-{status_color}">{run.status}</span>
                        </h6>
                        <div>
                            {controls}
                        </div>
                    </div>

                    <div class="progress mb-2" style="height: 6px;">
                        <div class="progress-bar bg-primary" role="progressbar"
                             style="width: {progress}%"
                             aria-valuenow="{progress}" aria-valuemin="0" aria-valuemax="100">
                        </div>
                    </div>

                    <div class="row text-center small">
                        <div class="col-3">
                            <strong>{run.metrics.processed_count}</strong><br>
                            <span class="text-muted">Done</span>
                        </div>
                        <div class="col-3">
                            <strong>{run.metrics.queued_count}</strong><br>
                            <span class="text-muted">Queue</span>
                        </div>
                        <div class="col-3">
                            <strong>{run.metrics.items_per_minute:.1f}/m</strong><br>
                            <span class="text-muted">Rate</span>
                        </div>
                        <div class="col-3">
                            <span class="slo-indicator {error_slo_class}"></span>
                            <strong>{run.metrics.error_rate:.1%}</strong><br>
                            <span class="text-muted">Errors</span>
                        </div>
                    </div>

                    <div class="mt-2 small">
                        <div class="d-flex justify-content-between">
                            <span><i class="fas fa-clock"></i> ETA: {eta_text}</span>
                            <span><i class="fas fa-dollar-sign"></i> ${run.metrics.actual_cost_usd:.4f}</span>
                        </div>
                    </div>
                </div>
            </div>
            """

        return html

    except Exception as e:
        logger.error(f"Failed to get active runs: {e}")
        return '<div class="alert alert-danger">Failed to load active runs</div>'

@router.get("/history", response_class=HTMLResponse)
def get_history_partial(page: int = Query(1, ge=1)) -> str:
    """Render complete run history table with pagination"""
    try:
        limit = 10
        offset = (page - 1) * limit
        runs = AnalysisControlRepo.get_recent_runs(limit=limit + 1, offset=offset)  # Get one extra to check if there are more

        # Check if there are more pages
        has_more = len(runs) > limit
        if has_more:
            runs = runs[:limit]  # Remove the extra record

        # Get total count for pagination
        total_runs = _get_total_runs_count()
        total_pages = (total_runs + limit - 1) // limit  # Ceiling division

        if not runs:
            return """
            <div class="text-center text-muted py-4">
                <i class="fas fa-history fa-2x mb-2"></i><br>
                No run history
            </div>
            """

        html = """
        <div class="table-responsive">
            <table class="table table-hover">
                <thead>
                    <tr>
                        <th>ID</th>
                        <th>Started</th>
                        <th>Status</th>
                        <th>Items</th>
                        <th>Duration</th>
                        <th>Cost</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody>
        """

        # Add rows using the shared function
        html += _render_history_rows(runs)

        html += """
                </tbody>
            </table>
        </div>
        """

        # Add pagination controls
        if total_pages > 1:
            html += _render_pagination(page, total_pages)

        html += _get_history_scripts()
        return html

    except Exception as e:
        logger.error(f"Failed to get run history: {e}")
        return '<div class="alert alert-danger">Failed to load run history</div>'


def _render_history_rows(runs) -> str:
    """Shared function to render history table rows"""
    html = ""

    for run in runs:
        # Status badge
        status_colors = {
            "completed": "success",
            "failed": "danger",
            "cancelled": "secondary",
            "running": "primary",
            "paused": "warning",
            "pending": "info"
        }
        status_color = status_colors.get(run.status, "secondary")

        # Duration calculation
        duration_str = "N/A"
        if run.started_at and run.completed_at:
            duration_seconds = int((run.completed_at - run.started_at).total_seconds())
            minutes = duration_seconds // 60
            seconds = duration_seconds % 60
            duration_str = f"{minutes}m {seconds}s"

        # Items processed - check actual analysis results for completed runs
        if run.status == "completed":
            # Count actual analyses for this run's items
            with Session(engine) as session:
                result = session.exec(text("""
                    SELECT COUNT(DISTINCT ia.item_id)
                    FROM analysis_run_items ari
                    JOIN item_analysis ia ON ari.item_id = ia.item_id
                    WHERE ari.run_id = :run_id
                """).params(run_id=run.id))
                actual_analyzed = result.scalar() or 0
            items_str = f"{actual_analyzed} / {run.metrics.total_count}"
        else:
            items_str = f"{run.metrics.processed_count} / {run.metrics.total_count}"

        # Format cost
        cost_str = f"${run.metrics.actual_cost_usd:.4f}"

        # Scope description
        scope_desc = "Global"
        if run.scope.type == "feeds" and run.scope.feed_ids:
            scope_desc = f"Feeds ({len(run.scope.feed_ids)})"
        elif run.scope.type == "timerange":
            scope_desc = "Time Range"

        html += f"""
        <tr>
            <td>
                <strong>#{run.id}</strong><br>
                <small class="text-muted">{scope_desc}</small>
            </td>
            <td>
                {run.created_at.strftime('%m/%d %H:%M')}<br>
                <small class="text-muted">{run.params.model_tag}</small>
            </td>
            <td>
                <span class="badge bg-{status_color}">{run.status}</span>
            </td>
            <td>{items_str}</td>
            <td>{duration_str}</td>
            <td>{cost_str}</td>
            <td>
                <button class="btn btn-sm btn-outline-primary"
                        onclick="showRunDetails({run.id})">
                    <i class="fas fa-eye"></i>
                </button>
                <button class="btn btn-sm btn-outline-success"
                        onclick="repeatRun({run.id})">
                    <i class="fas fa-redo"></i>
                </button>
            </td>
        </tr>
        """

    return html

def _get_total_runs_count() -> int:
    """Get total number of analysis runs"""
    try:
        with Session(engine) as session:
            result = session.execute(text("SELECT COUNT(*) FROM analysis_runs"))
            return result.scalar() or 0
    except Exception as e:
        logger.error(f"Failed to get total runs count: {e}")
        return 0

def _render_pagination(current_page: int, total_pages: int) -> str:
    """Render Bootstrap pagination controls"""
    if total_pages <= 1:
        return ""

    html = """
    <nav aria-label="Run history pagination" class="mt-3">
        <ul class="pagination justify-content-center">
    """

    # Previous button
    prev_disabled = "disabled" if current_page <= 1 else ""
    prev_page = max(1, current_page - 1)
    html += f"""
        <li class="page-item {prev_disabled}">
            <button class="page-link"
                    hx-get="/htmx/analysis/history?page={prev_page}"
                    hx-target="#run-history-table"
                    {"disabled" if prev_disabled else ""}>
                <i class="fas fa-chevron-left"></i> Previous
            </button>
        </li>
    """

    # Page numbers
    start_page = max(1, current_page - 2)
    end_page = min(total_pages, current_page + 2)

    # First page if not in range
    if start_page > 1:
        html += f"""
        <li class="page-item">
            <button class="page-link"
                    hx-get="/htmx/analysis/history?page=1"
                    hx-target="#run-history-table">1</button>
        </li>
        """
        if start_page > 2:
            html += '<li class="page-item disabled"><span class="page-link">...</span></li>'

    # Page range
    for page in range(start_page, end_page + 1):
        active = "active" if page == current_page else ""
        html += f"""
        <li class="page-item {active}">
            <button class="page-link"
                    hx-get="/htmx/analysis/history?page={page}"
                    hx-target="#run-history-table"
                    {"disabled" if active else ""}>{page}</button>
        </li>
        """

    # Last page if not in range
    if end_page < total_pages:
        if end_page < total_pages - 1:
            html += '<li class="page-item disabled"><span class="page-link">...</span></li>'
        html += f"""
        <li class="page-item">
            <button class="page-link"
                    hx-get="/htmx/analysis/history?page={total_pages}"
                    hx-target="#run-history-table">{total_pages}</button>
        </li>
        """

    # Next button
    next_disabled = "disabled" if current_page >= total_pages else ""
    next_page = min(total_pages, current_page + 1)
    html += f"""
        <li class="page-item {next_disabled}">
            <button class="page-link"
                    hx-get="/htmx/analysis/history?page={next_page}"
                    hx-target="#run-history-table"
                    {"disabled" if next_disabled else ""}>
                Next <i class="fas fa-chevron-right"></i>
            </button>
        </li>
    """

    html += """
        </ul>
    </nav>
    """

    return html

def _get_history_scripts() -> str:
    """Shared JavaScript for history functionality"""
    return """
    <script>
        function showRunDetails(runId) {
            // TODO: Implement run details modal
            alert('Run details for #' + runId + ' (TODO: implement modal)');
        }

        async function repeatRun(runId) {
            try {
                // Get the run details first
                const runResponse = await fetch(`/api/analysis/status/${runId}`);
                if (!runResponse.ok) {
                    alert('Failed to get run details');
                    return;
                }
                const run = await runResponse.json();

                // Start a new run with the same scope and params
                const startResponse = await fetch('/api/analysis/start', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        scope: run.scope,
                        params: run.params
                    })
                });

                if (!startResponse.ok) {
                    const error = await startResponse.json();
                    alert(`Failed to start new run: ${error.detail || 'Unknown error'}`);
                    return;
                }

                const newRun = await startResponse.json();
                alert(`Started new analysis run #${newRun.id}`);

                // Refresh the page to show the new run
                window.location.reload();
            } catch (error) {
                console.error('Error repeating run:', error);
                alert('Failed to repeat run: ' + error.message);
            }
        }
    </script>
    """

@router.get("/presets", response_class=HTMLResponse)
def get_presets_partial() -> str:
    """Render saved presets"""
    try:
        presets = AnalysisControlRepo.get_presets()

        if not presets:
            return """
            <div class="text-center text-muted py-3">
                <i class="fas fa-bookmark fa-2x mb-2"></i><br>
                No saved presets
            </div>
            """

        html = ""
        for preset in presets:
            scope_desc = "Global"
            if preset.scope.type == "feeds" and preset.scope.feed_ids:
                scope_desc = f"Feeds ({len(preset.scope.feed_ids)})"
            elif preset.scope.type == "timerange":
                scope_desc = "Time Range"

            html += f"""
            <div class="card mb-2">
                <div class="card-body py-2">
                    <div class="d-flex justify-content-between align-items-center">
                        <div>
                            <strong>{preset.name}</strong><br>
                            <small class="text-muted">
                                {scope_desc} • Limit: {preset.params.limit} • {preset.params.model_tag}
                            </small>
                        </div>
                        <div>
                            <button class="btn btn-sm btn-outline-primary me-1"
                                    onclick="loadPreset({preset.id})">
                                <i class="fas fa-download"></i>
                            </button>
                            <button class="btn btn-sm btn-outline-danger"
                                    hx-delete="/api/analysis/presets/{preset.id}"
                                    hx-target="#presets-list"
                                    hx-confirm="Delete preset '{preset.name}'?">
                                <i class="fas fa-trash"></i>
                            </button>
                        </div>
                    </div>
                </div>
            </div>
            """

        html += f"""
        <script>
            function loadPreset(presetId) {{
                // TODO: Load preset data into form
                alert('Load preset #' + presetId + ' (TODO: implement)');
            }}
        </script>
        """

        return html

    except Exception as e:
        logger.error(f"Failed to get presets: {e}")
        return '<div class="alert alert-danger">Failed to load presets</div>'