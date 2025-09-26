"""Analysis Control - Run Management Views"""

from fastapi import APIRouter, Query, Depends
from fastapi.responses import HTMLResponse
from typing import Optional
from sqlmodel import Session, text
from app.database import get_session
from app.core.logging_config import get_logger

router = APIRouter(tags=["htmx-analysis-runs"])
logger = get_logger(__name__)


@router.get("/status", response_class=HTMLResponse)
def get_status_partial() -> str:
    """Render current analysis status"""
    try:
        control_repo = AnalysisControlRepo()
        current_runs = control_repo.get_active_runs()

        if not current_runs:
            return """
            <div class="alert alert-info">
                <i class="fas fa-info-circle"></i> No active analysis runs
            </div>
            """

        html = '<div class="space-y-3">'
        for run in current_runs:
            # Handle both string and enum status values
            status_str = run.status.value if hasattr(run.status, 'value') else str(run.status).upper()

            status_color = {
                'RUNNING': 'primary',
                'COMPLETED': 'success',
                'FAILED': 'danger',
                'CANCELLED': 'warning'
            }.get(status_str, 'secondary')

            progress_percentage = (run.metrics.processed_count / run.metrics.total_count * 100) if run.metrics.total_count > 0 else 0

            html += f"""
            <div class="card">
                <div class="card-body">
                    <div class="d-flex justify-content-between align-items-center">
                        <h6 class="mb-1">Run #{run.id}</h6>
                        <span class="badge bg-{status_color}">{status_str}</span>
                    </div>
                    <p class="mb-1"><strong>Scope:</strong> {run.scope.type.title()} analysis</p>
                    <p class="mb-1"><strong>Progress:</strong> {run.metrics.processed_count}/{run.metrics.total_count} items</p>
                    <div class="progress mb-2">
                        <div class="progress-bar" role="progressbar"
                             style="width: {progress_percentage:.1f}%"
                             aria-valuenow="{progress_percentage:.1f}" aria-valuemin="0" aria-valuemax="100">
                        </div>
                    </div>
                    <p class="mb-0"><small class="text-muted">Started: {run.started_at}</small></p>
                </div>
            </div>
            """

        html += '</div>'
        return html

    except Exception as e:
        logger.error(f"Failed to get status: {e}")
        return '<div class="alert alert-danger">Failed to load status</div>'


@router.get("/active-runs", response_class=HTMLResponse)
async def get_active_runs_partial(db: Session = Depends(get_session)) -> str:
    """Render active analysis runs with dark mode styling"""
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
            return """
            <div class="alert alert-dark border-secondary text-center py-4" style="background: rgba(255,255,255,0.05);">
                <i class="bi bi-list-task" style="font-size: 3rem; color: #6c757d;"></i>
                <p class="mb-0 mt-3" style="color: #adb5bd;">No active analysis runs at the moment</p>
            </div>
            """

        html = '<div class="list-group" style="gap: 1rem;">'
        for run in runs:
            run_id, status, started_at, total, processed, failed = run
            progress = (processed / total * 100) if total > 0 else 0

            status_badge = {
                'running': ('primary', 'RUNNING'),
                'paused': ('warning', 'PAUSED'),
                'pending': ('info', 'PENDING')
            }.get(status, ('secondary', 'UNKNOWN'))

            html += f"""
            <div class="card bg-dark border-secondary" style="background: rgba(255,255,255,0.05) !important;">
                <div class="card-header bg-transparent border-secondary d-flex justify-content-between align-items-center">
                    <span style="color: #e9ecef;"><strong>Analysis Run #{run_id}</strong></span>
                    <span class="badge bg-{status_badge[0]}">{status_badge[1]}</span>
                </div>
                <div class="card-body">
                    <div class="row">
                        <div class="col-md-6">
                            <p style="color: #dee2e6;"><strong>Progress:</strong> {processed}/{total} items</p>
                            <div class="progress" style="height: 24px; background: rgba(0,0,0,0.3);">
                                <div class="progress-bar bg-{status_badge[0]}" role="progressbar"
                                     style="width: {progress:.1f}%; font-size: 14px;"
                                     aria-valuenow="{progress:.1f}" aria-valuemin="0" aria-valuemax="100">
                                    {progress:.0f}%
                                </div>
                            </div>
                        </div>
                        <div class="col-md-6">
                            <p style="color: #dee2e6;"><strong>Started:</strong> {started_at.strftime('%Y-%m-%d %H:%M:%S') if started_at else 'Pending'}</p>
                            <p style="color: #dee2e6;"><strong>Failed:</strong> <span class="text-danger">{failed}</span> / <span class="text-success">{processed - failed}</span> success</p>
                        </div>
                    </div>
                </div>
            </div>
            """

        html += '</div>'
        return html

    except Exception as e:
        logger.error(f"Failed to get active runs: {e}")
        return '<div class="alert alert-danger">Failed to load active runs</div>'


@router.get("/history", response_class=HTMLResponse)
async def get_history_partial(limit: int = Query(10, ge=1, le=100), db: Session = Depends(get_session)) -> str:
    """Render analysis run history with dark mode styling"""
    try:
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
            LIMIT :limit
        """), {"limit": limit})
        runs = result.fetchall()

        if not runs:
            return """
            <div class="alert alert-dark border-secondary text-center py-4" style="background: rgba(255,255,255,0.05);">
                <i class="bi bi-clock-history" style="font-size: 3rem; color: #6c757d;"></i>
                <p class="mb-0 mt-3" style="color: #adb5bd;">No analysis run history available</p>
            </div>
            """

        html = '<div class="table-responsive">'
        html += '''
        <table class="table table-dark table-hover" style="background: transparent;">
            <thead style="border-bottom: 2px solid #495057;">
                <tr>
                    <th style="color: #e9ecef; font-weight: 600;">Run ID</th>
                    <th style="color: #e9ecef; font-weight: 600;">Started</th>
                    <th style="color: #e9ecef; font-weight: 600;">Completed</th>
                    <th style="color: #e9ecef; font-weight: 600;">Status</th>
                    <th style="color: #e9ecef; font-weight: 600;">Items</th>
                    <th style="color: #e9ecef; font-weight: 600;">Success Rate</th>
                </tr>
            </thead>
            <tbody>
        '''

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
            completed_str = completed.strftime('%Y-%m-%d %H:%M') if completed else '-'

            html += f"""
            <tr style="border-bottom: 1px solid rgba(255,255,255,0.1);">
                <td style="color: #dee2e6;"><strong>#{run_id}</strong></td>
                <td style="color: #adb5bd;">{started_str}</td>
                <td style="color: #adb5bd;">{completed_str}</td>
                <td><span class="badge bg-{status_class}">{status.upper()}</span></td>
                <td style="color: #dee2e6;"><strong>{processed}/{total}</strong></td>
                <td style="color: #dee2e6;">{success_rate:.1f}%</td>
            </tr>
            """

        html += '</tbody></table></div>'
        return html

    except Exception as e:
        logger.error(f"Failed to get history: {e}")
        return '<div class="alert alert-danger">Failed to load history</div>'