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
        # Direct SQL query to avoid model issues
        result = db.execute(text("""
            SELECT id, status, started_at, queued_count,
                   processed_count, failed_count
            FROM analysis_runs
            WHERE status IN ('pending', 'running', 'paused')
            ORDER BY created_at DESC
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
            run_id, status, started_at, queued, processed, failed = run
            total = queued + processed + failed
            progress = (processed / total * 100) if total > 0 else 0

            status_badge = {
                'running': 'primary',
                'paused': 'warning',
                'pending': 'info'
            }.get(status, 'secondary')

            html += f"""
            <div class="list-group-item">
                <div class="d-flex justify-content-between align-items-center">
                    <div>
                        <h6 class="mb-1">Analysis Run #{run_id}</h6>
                        <p class="mb-1 text-muted">Started: {started_at or 'Pending'}</p>
                    </div>
                    <span class="badge bg-{status_badge}">{status.upper()}</span>
                </div>
                <div class="progress mt-2" style="height: 20px;">
                    <div class="progress-bar" role="progressbar"
                         style="width: {progress:.1f}%">{int(progress)}%</div>
                </div>
                <small class="text-muted">{processed}/{total} items processed</small>
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

        # Get runs
        result = db.execute(text("""
            SELECT id, started_at, completed_at, status,
                   queued_count, processed_count, failed_count
            FROM analysis_runs
            ORDER BY created_at DESC
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
            run_id, started, completed, status, queued, processed, failed = run
            total = queued + processed + failed
            success_rate = (processed / (processed + failed) * 100) if (processed + failed) > 0 else 0

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
        # Get statistics
        stats = db.execute(text("""
            SELECT
                (SELECT COUNT(*) FROM items) as total_items,
                (SELECT COUNT(*) FROM items WHERE analysis_result IS NOT NULL) as analyzed_items,
                (SELECT COUNT(*) FROM feeds WHERE status = 'active') as active_feeds,
                (SELECT COUNT(*) FROM analysis_runs WHERE status = 'running') as active_runs
        """)).fetchone()

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