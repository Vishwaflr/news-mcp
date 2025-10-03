"""
HTMX endpoints for Processors page components.
Returns formatted HTML instead of JSON for better UX.
"""
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select
from typing import Dict, Any
from datetime import datetime, timedelta

from app.database import get_session
from app.models import ProcessorType, ProcessingStatus
from app.models.content import ContentProcessingLog
from app.processors.factory import ProcessorFactory
from app.services.processor_bootstrap import ProcessorBootstrap

router = APIRouter(prefix="/htmx", tags=["htmx-processors"])
templates = Jinja2Templates(directory="templates")


@router.get("/processor-health-badge", response_class=HTMLResponse)
async def get_health_badge(request: Request, session: Session = Depends(get_session)):
    """Get formatted health status badge for metrics card"""

    # Get recent processing activity
    recent_logs = session.exec(
        select(ContentProcessingLog).where(
            ContentProcessingLog.processed_at >= datetime.utcnow() - timedelta(hours=24)
        )
    ).all()

    # Calculate metrics
    total_processed = len(recent_logs)
    successful = len([log for log in recent_logs if log.processing_status == ProcessingStatus.SUCCESS])
    failed = len([log for log in recent_logs if log.processing_status == ProcessingStatus.FAILED])

    success_rate = (successful / total_processed) if total_processed > 0 else 0

    # Determine health status
    if success_rate > 0.9:
        health = "healthy"
        badge_class = "success"
        icon = "✓"
    elif success_rate > 0.7:
        health = "degraded"
        badge_class = "warning"
        icon = "⚠"
    else:
        health = "unhealthy"
        badge_class = "danger"
        icon = "✗"

    html = f"""
    <div class="health-indicator {health}"></div>
    <span class="badge bg-{badge_class} badge-large">{icon} {health.upper()}</span>
    <div class="mt-2 small">
        <div>{success_rate:.1%} Success Rate</div>
        <div class="text-muted">{total_processed} processed (24h)</div>
    </div>
    """

    # Update other metric cards via JavaScript
    script = f"""
    <script>
        document.getElementById('active-processors').textContent = '{len(ProcessorFactory.get_available_processors())}';
        document.getElementById('processed-24h').textContent = '{total_processed:,}';
        document.getElementById('success-rate').textContent = '{success_rate:.1%}';
    </script>
    """

    return html + script


@router.get("/processor-types-list", response_class=HTMLResponse)
async def get_processor_types_list(request: Request):
    """Get formatted list of available processor types"""

    available = ProcessorFactory.get_available_processors()

    descriptions = {
        "universal": "Basic content cleaning and normalization",
        "heise": "Specialized for Heise Online feeds with German prefixes",
        "cointelegraph": "Handles Cointelegraph truncation and formatting",
        "custom": "Custom processor configuration"
    }

    html_parts = []
    for proc_type, processor_class in available.items():
        desc = descriptions.get(proc_type, "No description available")

        html_parts.append(f"""
        <div class="card processor-type-card mb-3">
            <div class="card-body">
                <div class="d-flex justify-content-between align-items-start">
                    <div>
                        <h6 class="mb-1">
                            <i class="bi bi-cpu"></i> <strong>{proc_type.title()}</strong>
                        </h6>
                        <p class="text-muted small mb-0">{desc}</p>
                    </div>
                    <span class="badge bg-primary">Active</span>
                </div>
            </div>
        </div>
        """)

    return "\n".join(html_parts) if html_parts else '<div class="alert alert-info">No processors available</div>'


@router.get("/processor-quick-stats", response_class=HTMLResponse)
async def get_quick_stats(request: Request, session: Session = Depends(get_session), days: int = 1):
    """Get quick statistics in formatted HTML"""

    # Get recent logs
    since = datetime.utcnow() - timedelta(days=days)
    recent_logs = session.exec(
        select(ContentProcessingLog).where(
            ContentProcessingLog.processed_at >= since
        )
    ).all()

    # Calculate stats
    total = len(recent_logs)
    successful = len([log for log in recent_logs if log.processing_status == ProcessingStatus.SUCCESS])
    failed = len([log for log in recent_logs if log.processing_status == ProcessingStatus.FAILED])
    success_rate = (successful / total * 100) if total > 0 else 100

    # Get processor breakdown
    breakdown = {}
    for log in recent_logs:
        proc_type = log.processor_type.value
        if proc_type not in breakdown:
            breakdown[proc_type] = {"success": 0, "failed": 0}

        if log.processing_status == ProcessingStatus.SUCCESS:
            breakdown[proc_type]["success"] += 1
        else:
            breakdown[proc_type]["failed"] += 1

    html = f"""
    <div class="row text-center mb-4">
        <div class="col-4">
            <div class="p-3 bg-primary bg-opacity-10 rounded">
                <h3 class="mb-1">{total:,}</h3>
                <small class="text-muted">Total Processed</small>
            </div>
        </div>
        <div class="col-4">
            <div class="p-3 bg-success bg-opacity-10 rounded">
                <h3 class="mb-1 text-success">{successful:,}</h3>
                <small class="text-muted">Successful</small>
            </div>
        </div>
        <div class="col-4">
            <div class="p-3 bg-danger bg-opacity-10 rounded">
                <h3 class="mb-1 text-danger">{failed:,}</h3>
                <small class="text-muted">Failed</small>
            </div>
        </div>
    </div>

    <div class="mb-3">
        <div class="d-flex justify-content-between mb-2">
            <span>Success Rate</span>
            <strong>{success_rate:.1f}%</strong>
        </div>
        <div class="progress" style="height: 8px;">
            <div class="progress-bar bg-success" style="width: {success_rate}%"></div>
        </div>
    </div>
    """

    # Add processor breakdown if exists
    if breakdown:
        html += '<hr><h6 class="mb-3">By Processor Type:</h6>'
        for proc_type, stats in breakdown.items():
            total_proc = stats['success'] + stats['failed']
            rate = (stats['success'] / total_proc * 100) if total_proc > 0 else 0

            html += f"""
            <div class="mb-2">
                <div class="d-flex justify-content-between small">
                    <span><i class="bi bi-cpu"></i> {proc_type.title()}</span>
                    <span>{total_proc} items ({rate:.0f}% success)</span>
                </div>
            </div>
            """

    return html if total > 0 else f'<div class="alert alert-info">No processing activity in the last {days} day(s)</div>'


@router.get("/processor-stats-table", response_class=HTMLResponse)
async def get_stats_table(request: Request, session: Session = Depends(get_session), days: int = 7):
    """Get detailed statistics table"""

    since = datetime.utcnow() - timedelta(days=days)
    logs = session.exec(
        select(ContentProcessingLog).where(
            ContentProcessingLog.processed_at >= since
        ).order_by(ContentProcessingLog.processed_at.desc())
    ).all()

    if not logs:
        return f'<div class="alert alert-info">No processing activity in the last {days} days</div>'

    # Group by processor type
    stats_by_type = {}
    for log in logs:
        proc_type = log.processor_type.value
        if proc_type not in stats_by_type:
            stats_by_type[proc_type] = {
                "total": 0,
                "success": 0,
                "failed": 0,
                "avg_duration": []
            }

        stats_by_type[proc_type]["total"] += 1
        if log.processing_status == ProcessingStatus.SUCCESS:
            stats_by_type[proc_type]["success"] += 1
        else:
            stats_by_type[proc_type]["failed"] += 1

        if log.processing_time_ms:
            stats_by_type[proc_type]["avg_duration"].append(log.processing_time_ms)

    # Build table
    html = f"""
    <div class="table-responsive">
        <table class="table table-hover stats-table">
            <thead>
                <tr>
                    <th>Processor Type</th>
                    <th class="text-center">Total Processed</th>
                    <th class="text-center">Success</th>
                    <th class="text-center">Failed</th>
                    <th class="text-center">Success Rate</th>
                    <th class="text-center">Avg Duration</th>
                </tr>
            </thead>
            <tbody>
    """

    for proc_type, stats in stats_by_type.items():
        success_rate = (stats["success"] / stats["total"] * 100) if stats["total"] > 0 else 0
        avg_duration = sum(stats["avg_duration"]) / len(stats["avg_duration"]) if stats["avg_duration"] else 0

        badge_color = "success" if success_rate > 90 else "warning" if success_rate > 70 else "danger"

        html += f"""
        <tr>
            <td><i class="bi bi-cpu"></i> <strong>{proc_type.title()}</strong></td>
            <td class="text-center">{stats["total"]:,}</td>
            <td class="text-center text-success">{stats["success"]:,}</td>
            <td class="text-center text-danger">{stats["failed"]:,}</td>
            <td class="text-center">
                <span class="badge bg-{badge_color}">{success_rate:.1f}%</span>
            </td>
            <td class="text-center">{avg_duration:.0f}ms</td>
        </tr>
        """

    html += """
            </tbody>
        </table>
    </div>
    """

    # Add summary
    total_all = sum(s["total"] for s in stats_by_type.values())
    success_all = sum(s["success"] for s in stats_by_type.values())
    overall_rate = (success_all / total_all * 100) if total_all > 0 else 0

    html += f"""
    <div class="alert alert-secondary mt-3">
        <strong>Period Summary ({days} days):</strong>
        {total_all:,} items processed with {overall_rate:.1f}% success rate
    </div>
    """

    return html


@router.get("/processor-bootstrap-status", response_class=HTMLResponse)
async def get_bootstrap_status(session: Session = Depends(get_session)):
    """Get bootstrap status alert for processors page"""

    bootstrap = ProcessorBootstrap(session)
    status = bootstrap.get_bootstrap_status()

    if "error" in status:
        return f"""
        <div class="alert alert-danger">
            <i class="bi bi-exclamation-triangle"></i> Error checking system status: {status['error']}
        </div>
        """

    if status["needs_bootstrap"]:
        # System needs configuration
        unconfigured = status["unconfigured_feeds"]
        total = status["total_feeds"]
        percentage = status["configuration_percentage"]

        return f"""
        <div class="alert alert-warning border-warning" style="border-left: 4px solid #ffc107;">
            <div class="d-flex justify-content-between align-items-start">
                <div>
                    <h5 class="alert-heading mb-2">
                        <i class="bi bi-exclamation-triangle-fill"></i> Processor System Not Configured
                    </h5>
                    <p class="mb-2">
                        <strong>{unconfigured}</strong> of <strong>{total}</strong> feeds have no processor assignment
                        ({percentage}% configured)
                    </p>
                    <p class="mb-0 text-muted small">
                        <i class="bi bi-info-circle"></i> The content processing system requires each feed to have an assigned processor.
                        Use auto-configure to assign processors based on feed URLs.
                    </p>
                </div>
                <div class="ms-3">
                    <button
                        class="btn btn-warning"
                        hx-post="/htmx/processor-bootstrap/auto-configure"
                        hx-target="#bootstrap-status"
                        hx-swap="outerHTML"
                        hx-indicator="#bootstrap-spinner">
                        <i class="bi bi-magic"></i> Auto-Configure All Feeds
                    </button>
                    <div id="bootstrap-spinner" class="htmx-indicator spinner-border spinner-border-sm ms-2" role="status">
                        <span class="visually-hidden">Loading...</span>
                    </div>
                </div>
            </div>
        </div>
        """
    else:
        # System is configured
        total = status["total_feeds"]
        configured = status["configured_feeds"]

        return f"""
        <div class="alert alert-success border-success" style="border-left: 4px solid #28a745;">
            <div class="d-flex justify-content-between align-items-center">
                <div>
                    <h6 class="mb-1">
                        <i class="bi bi-check-circle-fill"></i> Processor System Configured
                    </h6>
                    <p class="mb-0 text-muted small">
                        All {total} feeds have assigned processors ({configured} active configurations)
                    </p>
                </div>
                <button
                    class="btn btn-sm btn-outline-success"
                    hx-get="/htmx/processor-feed-assignments"
                    hx-target="#feed-assignments-table"
                    hx-swap="innerHTML">
                    <i class="bi bi-eye"></i> View Assignments
                </button>
            </div>
        </div>
        """


@router.post("/processor-bootstrap/auto-configure", response_class=HTMLResponse)
async def auto_configure_processors(session: Session = Depends(get_session)):
    """Auto-configure all feeds with appropriate processors"""

    bootstrap = ProcessorBootstrap(session)
    result = bootstrap.auto_configure_all_feeds()

    if not result["success"]:
        return f"""
        <div class="alert alert-danger" id="bootstrap-status">
            <h5 class="alert-heading">
                <i class="bi bi-x-circle-fill"></i> Auto-Configuration Failed
            </h5>
            <p class="mb-0">{result.get('error', 'Unknown error')}</p>
        </div>
        """

    # Success!
    configured = result["configured"]
    skipped = result["skipped"]
    total = result["total_feeds"]
    errors = result.get("errors", [])

    error_html = ""
    if errors:
        error_html = f"""
        <div class="mt-2">
            <strong>Errors ({len(errors)}):</strong>
            <ul class="small mb-0">
                {"".join([f"<li>{err}</li>" for err in errors[:5]])}
            </ul>
        </div>
        """

    return f"""
    <div class="alert alert-success" id="bootstrap-status">
        <h5 class="alert-heading">
            <i class="bi bi-check-circle-fill"></i> Auto-Configuration Successful!
        </h5>
        <p class="mb-2">
            <strong>{configured}</strong> feeds configured, <strong>{skipped}</strong> already configured
        </p>
        <div class="progress mb-2" style="height: 25px;">
            <div class="progress-bar bg-success" role="progressbar"
                 style="width: 100%;"
                 aria-valuenow="100" aria-valuemin="0" aria-valuemax="100">
                {total}/{total} Feeds Configured
            </div>
        </div>
        <p class="mb-0 text-muted small">
            <i class="bi bi-info-circle"></i> All feeds now have assigned processors.
            You can view and edit assignments in the Configuration tab.
        </p>
        {error_html}
    </div>
    <script>
        // Refresh the health metrics after configuration
        htmx.ajax('GET', '/htmx/processor-health-badge', {{target: '#health-status-badge'}});
    </script>
    """


@router.get("/processor-feed-assignments", response_class=HTMLResponse)
async def get_feed_assignments(session: Session = Depends(get_session)):
    """Get feed-to-processor assignments table"""

    bootstrap = ProcessorBootstrap(session)
    result = bootstrap.get_feed_assignments()

    if not result["success"]:
        return f"""
        <div class="alert alert-danger">
            Error loading assignments: {result.get('error', 'Unknown error')}
        </div>
        """

    assignments = result["assignments"]
    summary = result["summary"]

    # Build table
    html = f"""
    <div class="mb-3">
        <strong>Summary:</strong> {summary['configured']}/{summary['total']} feeds configured
        ({summary['unassigned']} unassigned)
    </div>

    <div class="table-responsive">
        <table class="table table-sm table-hover stats-table">
            <thead>
                <tr>
                    <th>Feed</th>
                    <th>URL</th>
                    <th>Assigned Processor</th>
                    <th>Auto-Detected</th>
                    <th>Status</th>
                    <th>Actions</th>
                </tr>
            </thead>
            <tbody>
    """

    for assignment in assignments:
        feed_title = assignment["feed_title"] or "Untitled Feed"
        feed_url_short = assignment["feed_url"][:50] + "..." if len(assignment["feed_url"]) > 50 else assignment["feed_url"]

        processor = assignment["processor_type"] or "None"
        auto_detected = assignment["auto_detected_type"]

        status_badge = "success" if assignment["has_config"] else "secondary"
        status_text = "Active" if assignment["is_active"] else "Unassigned"

        # Check if assigned matches auto-detected
        match_icon = "✓" if processor == auto_detected else "⚠"
        match_class = "text-success" if processor == auto_detected else "text-warning"

        html += f"""
        <tr>
            <td><strong>{feed_title[:30]}</strong></td>
            <td><small class="text-muted">{feed_url_short}</small></td>
            <td>
                <span class="badge bg-primary">{processor}</span>
            </td>
            <td>
                <small class="{match_class}">{match_icon} {auto_detected}</small>
            </td>
            <td>
                <span class="badge bg-{status_badge}">{status_text}</span>
            </td>
            <td>
                <button class="btn btn-sm btn-outline-primary"
                        hx-get="/htmx/processor-edit-config/{assignment['feed_id']}"
                        hx-target="#modal-body"
                        hx-swap="innerHTML"
                        data-bs-toggle="modal"
                        data-bs-target="#editModal">
                    <i class="bi bi-pencil"></i>
                </button>
            </td>
        </tr>
        """

    html += """
            </tbody>
        </table>
    </div>
    """

    return html
