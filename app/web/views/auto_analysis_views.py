"""HTMX views for auto-analysis monitoring and statistics"""

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, text
from app.core.logging_config import get_logger
from datetime import datetime, timedelta

from app.database import get_session, engine
from app.models import Feed, PendingAutoAnalysis
from app.services.pending_analysis_processor import PendingAnalysisProcessor
from app.services.auto_analysis_config import auto_analysis_config

router = APIRouter(tags=["htmx-auto-analysis"])
logger = get_logger(__name__)
templates = Jinja2Templates(directory="templates")


@router.get("/auto-analysis-dashboard", response_class=HTMLResponse)
def get_auto_analysis_dashboard(session: Session = Depends(get_session)):
    """Dashboard widget showing auto-analysis statistics"""
    try:
        processor = PendingAnalysisProcessor()
        stats = processor.get_queue_stats()

        feeds_with_auto = session.query(Feed).filter(
            Feed.auto_analyze_enabled == True
        ).count()

        # Use analysis_runs table (the actual runs) instead of pending_auto_analysis
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

        # Get today's completed runs
        today_runs_result = session.execute(
            text("""
                SELECT
                    COUNT(*) as total_runs,
                    COUNT(*) FILTER (WHERE status = 'completed') as completed,
                    COUNT(*) FILTER (WHERE status = 'failed') as failed
                FROM analysis_runs
                WHERE created_at >= :today_start
            """),
            {"today_start": today_start}
        ).fetchone()

        # Get items processed today
        items_result = session.execute(
            text("""
                SELECT
                    COUNT(DISTINCT ari.item_id) as total_items,
                    COUNT(*) FILTER (WHERE ari.state = 'completed') as successful,
                    COUNT(*) FILTER (WHERE ari.state = 'failed') as failed
                FROM analysis_run_items ari
                JOIN analysis_runs ar ON ari.run_id = ar.id
                WHERE ar.created_at >= :today_start
            """),
            {"today_start": today_start}
        ).fetchone()

        pending = stats.get("pending", 0)
        completed_today = today_runs_result[1] if today_runs_result else 0
        failed_today = today_runs_result[2] if today_runs_result else 0

        total_items_analyzed = items_result[0] if items_result else 0
        items_successful = items_result[1] if items_result else 0
        items_failed = items_result[2] if items_result else 0

        # Calculate success rate based on items, not runs
        success_rate = round((items_successful / total_items_analyzed * 100), 1) if total_items_analyzed > 0 else 100

        status_color = "success" if pending < 5 else "warning" if pending < 20 else "danger"

        html = f"""
        <div class="card">
            <div class="card-header d-flex justify-content-between align-items-center">
                <h6 class="mb-0"><i class="bi bi-robot"></i> Auto-Analysis System</h6>
                <span class="badge bg-{status_color}">{pending} Pending</span>
            </div>
            <div class="card-body">
                <div class="row text-center mb-3">
                    <div class="col-6">
                        <div class="stat-card">
                            <div class="stat-value text-primary">{feeds_with_auto}</div>
                            <div class="stat-label">Active Feeds</div>
                        </div>
                    </div>
                    <div class="col-6">
                        <div class="stat-card">
                            <div class="stat-value text-success">{completed_today}</div>
                            <div class="stat-label">Jobs Today</div>
                        </div>
                    </div>
                </div>

                <div class="row text-center mb-3">
                    <div class="col-4">
                        <small class="text-muted">
                            <strong>{total_items_analyzed}</strong><br>
                            Items Analyzed
                        </small>
                    </div>
                    <div class="col-4">
                        <small class="text-muted">
                            <strong>{success_rate}%</strong><br>
                            Success Rate
                        </small>
                    </div>
                    <div class="col-4">
                        <small class="text-danger">
                            <strong>{items_failed}</strong><br>
                            Failed
                        </small>
                    </div>
                </div>

                {f'<div class="alert alert-warning mb-0"><small><i class="bi bi-exclamation-triangle"></i> {pending} jobs waiting in queue</small></div>' if pending > 0 else '<div class="alert alert-success mb-0"><small><i class="bi bi-check-circle"></i> Queue is empty</small></div>'}
            </div>
        </div>
        """

        return html

    except Exception as e:
        logger.error(f"Error getting auto-analysis dashboard: {e}")
        return f'<div class="alert alert-danger">Error loading dashboard: {str(e)}</div>'


@router.get("/auto-analysis-queue", response_class=HTMLResponse)
def get_auto_analysis_queue(session: Session = Depends(get_session)):
    """Detailed view of pending auto-analysis queue"""
    try:
        pending_jobs = session.query(PendingAutoAnalysis).filter(
            PendingAutoAnalysis.status == "pending"
        ).order_by(PendingAutoAnalysis.created_at).limit(10).all()

        if not pending_jobs:
            return '<div class="alert alert-info">No pending jobs in queue</div>'

        html = '<div class="list-group">'

        for job in pending_jobs:
            feed = session.get(Feed, job.feed_id)
            age = datetime.utcnow() - job.created_at
            age_str = f"{int(age.total_seconds() / 60)} min" if age.total_seconds() < 3600 else f"{int(age.total_seconds() / 3600)}h"

            html += f"""
            <div class="list-group-item">
                <div class="d-flex justify-content-between align-items-start">
                    <div>
                        <h6 class="mb-1">{feed.title if feed else 'Unknown Feed'}</h6>
                        <small class="text-muted">
                            {len(job.item_ids)} items | Created {age_str} ago
                        </small>
                    </div>
                    <span class="badge bg-warning">Pending</span>
                </div>
            </div>
            """

        html += '</div>'
        return html

    except Exception as e:
        logger.error(f"Error getting queue: {e}")
        return f'<div class="alert alert-danger">Error: {str(e)}</div>'


@router.get("/auto-analysis-history", response_class=HTMLResponse)
def get_auto_analysis_history(session: Session = Depends(get_session)):
    """Recent auto-analysis history"""
    try:
        recent_jobs = session.query(PendingAutoAnalysis).filter(
            PendingAutoAnalysis.processed_at.isnot(None)
        ).order_by(PendingAutoAnalysis.processed_at.desc()).limit(20).all()

        if not recent_jobs:
            return '<div class="alert alert-info">No analysis history yet</div>'

        html = '<div class="table-responsive"><table class="table table-sm table-hover">'
        html += '<thead><tr><th>Feed</th><th>Items</th><th>Status</th><th>Processed</th><th>Run ID</th></tr></thead><tbody>'

        for job in recent_jobs:
            feed = session.get(Feed, job.feed_id)
            status_badge = "success" if job.status == "completed" else "danger"
            status_icon = "check-circle" if job.status == "completed" else "x-circle"

            processed_str = job.processed_at.strftime("%H:%M:%S") if job.processed_at else "-"

            html += f"""
            <tr>
                <td><small>{feed.title[:30] if feed and feed.title else 'Unknown'}...</small></td>
                <td><small>{len(job.item_ids)}</small></td>
                <td><span class="badge bg-{status_badge}"><i class="bi bi-{status_icon}"></i></span></td>
                <td><small>{processed_str}</small></td>
                <td><small>{'#' + str(job.analysis_run_id) if job.analysis_run_id else '-'}</small></td>
            </tr>
            """

        html += '</tbody></table></div>'
        return html

    except Exception as e:
        logger.error(f"Error getting history: {e}")
        return f'<div class="alert alert-danger">Error: {str(e)}</div>'


@router.post("/auto-analysis-config", response_class=HTMLResponse)
def update_auto_analysis_config(
    max_runs_per_day: int = Form(...),
    max_items_per_run: int = Form(...),
    ai_model: str = Form(...),
    check_interval: int = Form(...)
):
    """Update auto-analysis configuration"""
    try:
        # Update and save to persistent storage
        config_updates = {
            "max_runs_per_day": max_runs_per_day,
            "max_items_per_run": max_items_per_run,
            "ai_model": ai_model,
            "check_interval": check_interval
        }

        success = auto_analysis_config.update(config_updates)

        if not success:
            logger.error("Failed to save auto-analysis config")
            return HTMLResponse("""
                <div class="alert alert-danger">
                    <i class="bi bi-x-circle"></i> Failed to save configuration. Please check logs.
                </div>
            """)

        logger.info(f"Updated and saved auto-analysis config: {config_updates}")

        html = f"""
        <div id="config-view" class="row">
            <div class="col-md-4">
                <h6>Daily Limits</h6>
                <ul class="small">
                    <li><span id="view-max-runs">{max_runs_per_day}</span> Auto-Runs pro Feed/Tag</li>
                    <li>Max <span id="view-max-items">{max_items_per_run}</span> Items pro Run</li>
                    <li>Job Expiry: 24 Stunden</li>
                </ul>
            </div>
            <div class="col-md-4">
                <h6>Model</h6>
                <ul class="small">
                    <li>Default: <span id="view-model">{ai_model}</span></li>
                    <li>Cost-optimiert für Auto-Analyse</li>
                    <li>Rate: 1.0 req/s</li>
                </ul>
            </div>
            <div class="col-md-4">
                <h6>Queue Processing</h6>
                <ul class="small">
                    <li>Worker: Analysis Worker</li>
                    <li>Check Interval: <span id="view-interval">{check_interval}</span>s</li>
                    <li>Async Processing</li>
                </ul>
            </div>
        </div>
        <div class="alert alert-success mt-3">
            <i class="bi bi-check-circle"></i> Configuration saved successfully!
        </div>
        <script>
            document.getElementById('config-edit').style.display = 'none';
            document.getElementById('toggle-config-edit').style.display = 'inline-block';
        </script>
        """

        return html

    except Exception as e:
        logger.error(f"Error updating config: {e}")
        return f'<div class="alert alert-danger">Error: {str(e)}</div>'


@router.get("/auto-analysis-config", response_class=HTMLResponse)
def get_auto_analysis_config():
    """Get current auto-analysis configuration"""
    return auto_analysis_config.get_all()


@router.get("/analysis/run-stats/{run_id}")
async def get_run_stats(run_id: int, request: Request):
    """Get run statistics with skip tracking for display"""
    try:
        with Session(engine) as session:
            query = text("""
                SELECT
                    id, status, created_at, updated_at, started_at, completed_at,
                    queued_count, processed_count, failed_count,
                    planned_count, skipped_count, triggered_by
                FROM analysis_runs
                WHERE id = :run_id
            """)

            result = session.execute(query, {"run_id": run_id})
            row = result.fetchone()

            if not row:
                return HTMLResponse(f"""
                    <div class="alert alert-warning">
                        Run #{run_id} not found
                    </div>
                """)

            run = {
                "id": row[0],
                "status": row[1],
                "created_at": row[2],
                "updated_at": row[3],
                "started_at": row[4],
                "completed_at": row[5],
                "queued_count": row[6],
                "processed_count": row[7] or 0,
                "failed_count": row[8] or 0,
                "planned_count": row[9] or row[6],  # Fallback to queued_count
                "skipped_count": row[10] or 0,
                "triggered_by": row[11] or "manual"
            }

            return templates.TemplateResponse(
                "components/run_stats.html",
                {
                    "request": request,
                    "run": run
                }
            )

    except Exception as e:
        logger.error(f"Error getting run stats for {run_id}: {e}")
        return HTMLResponse(f"""
            <div class="alert alert-danger">
                Error loading run statistics: {str(e)}
            </div>
        """)