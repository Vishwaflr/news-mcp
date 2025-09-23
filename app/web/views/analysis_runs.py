"""Analysis Control - Run Management Views"""

from fastapi import APIRouter, Query
from fastapi.responses import HTMLResponse
from typing import Optional
from app.core.logging_config import get_logger

from app.domain.analysis.control import AnalysisRun, RunStatus, SLO_TARGETS
from app.repositories.analysis_control import AnalysisControlRepo

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
def get_active_runs_partial() -> str:
    """Render active analysis runs"""
    try:
        control_repo = AnalysisControlRepo()
        active_runs = control_repo.get_active_runs()

        if not active_runs:
            return """
            <div class="text-center text-muted py-4">
                <i class="fas fa-tasks fa-3x mb-3"></i>
                <p>No active runs</p>
            </div>
            """

        html = ""
        for run in active_runs:
            progress_pct = (run.metrics.processed_count / run.metrics.total_count * 100) if run.metrics.total_count > 0 else 0
            duration = (run.completed_at or run.started_at) - run.started_at
            duration_str = str(duration).split('.')[0]  # Remove microseconds

            # Handle both string and enum status values
            status_str = run.status.value if hasattr(run.status, 'value') else str(run.status).upper()

            status_badge = {
                'RUNNING': '<span class="badge bg-primary">Running</span>',
                'COMPLETED': '<span class="badge bg-success">Completed</span>',
                'FAILED': '<span class="badge bg-danger">Failed</span>',
                'CANCELLED': '<span class="badge bg-warning">Cancelled</span>'
            }.get(status_str, '<span class="badge bg-secondary">Unknown</span>')

            html += f"""
            <div class="card mb-3">
                <div class="card-header d-flex justify-content-between align-items-center">
                    <span><strong>Run #{run.id}</strong> - {run.scope.type.title()} analysis</span>
                    {status_badge}
                </div>
                <div class="card-body">
                    <div class="row">
                        <div class="col-md-6">
                            <p><strong>Progress:</strong> {run.metrics.processed_count:,} / {run.metrics.total_count:,} items</p>
                            <div class="progress mb-2">
                                <div class="progress-bar" role="progressbar"
                                     style="width: {progress_pct:.1f}%"
                                     aria-valuenow="{progress_pct}" aria-valuemin="0" aria-valuemax="100">
                                    {progress_pct:.1f}%
                                </div>
                            </div>
                        </div>
                        <div class="col-md-6">
                            <p><strong>Started:</strong> {run.started_at.strftime('%Y-%m-%d %H:%M:%S') if run.started_at else 'Not started'}</p>
                            <p><strong>Duration:</strong> {duration_str}</p>
                            {f'<p><strong>Error:</strong> <span class="text-danger">{run.last_error}</span></p>' if run.last_error else ''}
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
def get_history_partial(limit: int = Query(10, ge=1, le=100)) -> str:
    """Render analysis run history"""
    try:
        control_repo = AnalysisControlRepo()
        runs = control_repo.get_recent_runs(limit=limit)

        if not runs:
            return """
            <div class="text-center text-muted py-4">
                <i class="fas fa-history fa-3x mb-3"></i>
                <p>No analysis history</p>
            </div>
            """

        html = '<div class="table-responsive">'
        html += '''
        <table class="table table-hover">
            <thead>
                <tr>
                    <th>Run ID</th>
                    <th>Scope</th>
                    <th>Status</th>
                    <th>Progress</th>
                    <th>Duration</th>
                    <th>Started</th>
                </tr>
            </thead>
            <tbody>
        '''

        for run in runs:
            # Handle both string and enum status values
            status_str = run.status.value if hasattr(run.status, 'value') else str(run.status).upper()

            status_badge = {
                'RUNNING': '<span class="badge bg-primary">Running</span>',
                'COMPLETED': '<span class="badge bg-success">Completed</span>',
                'FAILED': '<span class="badge bg-danger">Failed</span>',
                'CANCELLED': '<span class="badge bg-warning">Cancelled</span>'
            }.get(status_str, '<span class="badge bg-secondary">Unknown</span>')

            progress_pct = (run.metrics.processed_count / run.metrics.total_count * 100) if run.metrics.total_count > 0 else 0

            if run.completed_at:
                duration = run.completed_at - run.started_at
                duration_str = str(duration).split('.')[0]
            else:
                duration_str = "Running..."

            html += f"""
            <tr>
                <td>#{run.id}</td>
                <td>{run.scope.type.title()} analysis</td>
                <td>{status_badge}</td>
                <td>
                    <div class="progress" style="height: 20px;">
                        <div class="progress-bar" role="progressbar"
                             style="width: {progress_pct:.1f}%"
                             aria-valuenow="{progress_pct}" aria-valuemin="0" aria-valuemax="100">
                            {run.metrics.processed_count:,}/{run.metrics.total_count:,}
                        </div>
                    </div>
                </td>
                <td>{duration_str}</td>
                <td>{run.started_at.strftime('%Y-%m-%d %H:%M') if run.started_at else 'Not started'}</td>
            </tr>
            """

        html += '</tbody></table></div>'
        return html

    except Exception as e:
        logger.error(f"Failed to get history: {e}")
        return '<div class="alert alert-danger">Failed to load history</div>'