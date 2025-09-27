"""
Analysis runs endpoints - Active runs and history
"""

from fastapi import APIRouter, Depends, Query
from fastapi.responses import HTMLResponse
from sqlmodel import Session, text
from app.database import get_session
from app.core.logging_config import get_logger

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

        if total_pages > 1:
            html += '<nav><ul class="pagination justify-content-center">'

            if page > 1:
                html += f'''
                <li class="page-item">
                    <a class="page-link" href="#"
                       hx-get="/htmx/analysis/runs/history?page={page-1}&limit={limit}"
                       hx-target="#run-history-table">Previous</a>
                </li>
                '''

            for p in range(max(1, page-2), min(total_pages+1, page+3)):
                active = 'active' if p == page else ''
                html += f'''
                <li class="page-item {active}">
                    <a class="page-link" href="#"
                       hx-get="/htmx/analysis/runs/history?page={p}&limit={limit}"
                       hx-target="#run-history-table">{p}</a>
                </li>
                '''

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