from fastapi import APIRouter, Depends, Query
from fastapi.responses import HTMLResponse
from sqlmodel import Session, select
from typing import Optional
from app.core.logging_config import get_logger

from app.database import get_session
from app.models import (
    Feed, Source, Category, Item, FeedHealth, FeedProcessorConfig,
    ProcessorTemplate, ProcessorType, ContentProcessingLog
)

router = APIRouter(tags=["htmx-system"])
logger = get_logger(__name__)

@router.get("/sources-options", response_class=HTMLResponse)
def get_sources_options(session: Session = Depends(get_session)):
    sources = session.exec(select(Source)).all()
    html = ""
    for source in sources:
        html += f'<option value="{source.id}">{source.name}</option>'
    return html

@router.get("/categories-options", response_class=HTMLResponse)
def get_categories_options(session: Session = Depends(get_session)):
    categories = session.exec(select(Category)).all()
    html = ""
    for category in categories:
        html += f'<option value="{category.id}">{category.name}</option>'
    return html

@router.get("/system-status", response_class=HTMLResponse)
def get_system_status(session: Session = Depends(get_session)):
    from datetime import datetime, timedelta

    total_feeds = len(session.exec(select(Feed)).all())
    active_feeds = len(session.exec(select(Feed).where(Feed.status == "active")).all())
    error_feeds = len(session.exec(select(Feed).where(Feed.status == "error")).all())

    recent_items = len(session.exec(
        select(Item).where(Item.created_at >= datetime.utcnow() - timedelta(hours=24))
    ).all())

    health_pct = (active_feeds / total_feeds * 100) if total_feeds > 0 else 100

    status_color = "success" if health_pct >= 90 else "warning" if health_pct >= 70 else "danger"
    status_text = "Excellent" if health_pct >= 90 else "Good" if health_pct >= 70 else "Needs Attention"

    html = f"""
    <div class="row">
        <div class="col-md-3">
            <div class="card text-center">
                <div class="card-body">
                    <h2 class="text-primary">{total_feeds}</h2>
                    <p class="card-text">Total Feeds</p>
                </div>
            </div>
        </div>
        <div class="col-md-3">
            <div class="card text-center">
                <div class="card-body">
                    <h2 class="text-success">{active_feeds}</h2>
                    <p class="card-text">Active Feeds</p>
                </div>
            </div>
        </div>
        <div class="col-md-3">
            <div class="card text-center">
                <div class="card-body">
                    <h2 class="text-danger">{error_feeds}</h2>
                    <p class="card-text">Error Feeds</p>
                </div>
            </div>
        </div>
        <div class="col-md-3">
            <div class="card text-center">
                <div class="card-body">
                    <h2 class="text-info">{recent_items}</h2>
                    <p class="card-text">Items (24h)</p>
                </div>
            </div>
        </div>
    </div>
    <div class="row mt-3">
        <div class="col-12">
            <div class="alert alert-{status_color}">
                <h5>System Health: {health_pct:.1f}%</h5>
                <p class="mb-0">Status: {status_text}</p>
            </div>
        </div>
    </div>
    """

    return html

@router.get("/processor-configs", response_class=HTMLResponse)
def get_processor_configs(session: Session = Depends(get_session)):
    """Get feed processor configurations table"""
    query = select(FeedProcessorConfig, Feed).join(Feed)
    results = session.exec(query).all()

    html = """
    <div class="table-responsive">
        <table class="table table-striped">
            <thead>
                <tr>
                    <th>Feed</th>
                    <th>Processor Type</th>
                    <th>Status</th>
                    <th>Created</th>
                    <th>Actions</th>
                </tr>
            </thead>
            <tbody>
    """

    if results:
        for config, feed in results:
            feed_name = feed.title or feed.url[:50] + "..."
            status_badge = "success" if config.is_active else "secondary"
            status_text = "Active" if config.is_active else "Inactive"

            html += f"""
                <tr>
                    <td>
                        <strong>{feed_name}</strong><br>
                        <small class="text-muted">{feed.url[:60]}{'...' if len(feed.url) > 60 else ''}</small>
                    </td>
                    <td>
                        <span class="badge bg-primary">{config.processor_type.value}</span>
                    </td>
                    <td>
                        <span class="badge bg-{status_badge}">{status_text}</span>
                    </td>
                    <td>
                        <small>{config.created_at.strftime("%d.%m.%Y %H:%M")}</small>
                    </td>
                    <td>
                        <div class="btn-group btn-group-sm">
                            <button class="btn btn-outline-primary"
                                    data-bs-toggle="modal"
                                    data-bs-target="#editConfigModal"
                                    onclick="loadConfigForEdit({config.id})">
                                <i class="bi bi-pencil"></i>
                            </button>
                            <button class="btn btn-outline-danger"
                                    hx-delete="/api/processors/config/{config.id}"
                                    hx-target="#feed-configurations"
                                    hx-confirm="Really delete configuration?">
                                <i class="bi bi-trash"></i>
                            </button>
                        </div>
                    </td>
                </tr>
            """
    else:
        html += """
            <tr>
                <td colspan="5" class="text-center text-muted">
                    No processor configurations found.
                </td>
            </tr>
        """

    html += """
            </tbody>
        </table>
    </div>
    """

    return html

@router.get("/processor-templates", response_class=HTMLResponse)
def get_processor_templates(session: Session = Depends(get_session)):
    """Get processor templates grid"""
    templates = session.exec(select(ProcessorTemplate).order_by(ProcessorTemplate.name)).all()

    html = '<div class="row">'

    if templates:
        for template in templates:
            pattern_count = len(template.patterns) if template.patterns else 0
            config_items = len(template.config) if template.config else 0

            # Type specific styling
            type_colors = {
                ProcessorType.HEISE: "primary",
                ProcessorType.COINTELEGRAPH: "warning",
                ProcessorType.UNIVERSAL: "success"
            }
            type_color = type_colors.get(template.processor_type, "secondary")

            html += f"""
        <div class="col-md-6 col-lg-4 mb-3">
            <div class="card">
                <div class="card-header d-flex justify-content-between align-items-center">
                    <span class="badge bg-{type_color}">{template.processor_type.value}</span>
                    <span class="badge bg-{'success' if template.is_active else 'secondary'}">
                        {'Active' if template.is_active else 'Inactive'}
                    </span>
                </div>
                <div class="card-body">
                    <h6 class="card-title">{template.name}</h6>
                    <p class="card-text small text-muted">{template.description or 'No description'}</p>

                    <div class="small mb-2">
                        <div><strong>Patterns:</strong> {pattern_count}</div>
                        <div><strong>Config Items:</strong> {config_items}</div>
                        <div><strong>Built-in:</strong> {'Yes' if template.is_builtin else 'No'}</div>
                    </div>
                </div>
                <div class="card-footer">
                    <div class="btn-group w-100">
                        <button class="btn btn-outline-primary btn-sm"
                                data-bs-toggle="modal"
                                data-bs-target="#templateModal"
                                onclick="loadTemplate({template.id})">
                            <i class="bi bi-eye"></i> View
                        </button>
                        {"" if template.is_builtin else f'''
                        <button class="btn btn-outline-secondary btn-sm"
                                data-bs-toggle="modal"
                                data-bs-target="#editTemplateModal"
                                onclick="editTemplate({template.id})">
                            <i class="bi bi-pencil"></i>
                        </button>
                        <button class="btn btn-outline-danger btn-sm"
                                hx-delete="/api/processors/templates/{template.id}"
                                hx-target="#processor-templates"
                                hx-confirm="Really delete template?">
                            <i class="bi bi-trash"></i>
                        </button>
                        '''}
                    </div>
                </div>
            </div>
        </div>
            """
    else:
        html += """
        <div class="col-12">
            <div class="alert alert-info text-center">
                <i class="bi bi-info-circle me-2"></i>
                No processor templates found.
            </div>
        </div>
        """

    html += '</div>'
    return html

@router.get("/processor-stats", response_class=HTMLResponse)
def get_processor_stats(session: Session = Depends(get_session), days: int = 7):
    """Get processor statistics"""
    from datetime import datetime, timedelta
    from app.models import ContentProcessingLog, ProcessorType

    since = datetime.utcnow() - timedelta(days=days)
    logs = session.exec(
        select(ContentProcessingLog)
        .where(ContentProcessingLog.created_at >= since)
        .order_by(ContentProcessingLog.created_at.desc())
    ).all()

    # Calculate stats
    total_processed = len(logs)
    successful = len([log for log in logs if log.status.value == 'success'])
    failed = len([log for log in logs if log.status.value == 'error'])

    success_rate = (successful / total_processed * 100) if total_processed > 0 else 0

    # Group by processor type
    by_type = {}
    for log in logs:
        ptype = log.processor_type.value if log.processor_type else 'unknown'
        if ptype not in by_type:
            by_type[ptype] = {'total': 0, 'success': 0, 'error': 0}
        by_type[ptype]['total'] += 1
        if log.status.value == 'success':
            by_type[ptype]['success'] += 1
        elif log.status.value == 'error':
            by_type[ptype]['error'] += 1

    html = f"""
    <div class="row mb-4">
        <div class="col-md-3">
            <div class="card text-center">
                <div class="card-body">
                    <h3 class="text-primary">{total_processed}</h3>
                    <p class="mb-0">Total Processed</p>
                    <small class="text-muted">Last {days} days</small>
                </div>
            </div>
        </div>
        <div class="col-md-3">
            <div class="card text-center">
                <div class="card-body">
                    <h3 class="text-success">{successful}</h3>
                    <p class="mb-0">Successful</p>
                    <small class="text-muted">{success_rate:.1f}% success rate</small>
                </div>
            </div>
        </div>
        <div class="col-md-3">
            <div class="card text-center">
                <div class="card-body">
                    <h3 class="text-danger">{failed}</h3>
                    <p class="mb-0">Failed</p>
                    <small class="text-muted">{100-success_rate:.1f}% failure rate</small>
                </div>
            </div>
        </div>
        <div class="col-md-3">
            <div class="card text-center">
                <div class="card-body">
                    <h3 class="text-info">{len(by_type)}</h3>
                    <p class="mb-0">Processor Types</p>
                    <small class="text-muted">Active types</small>
                </div>
            </div>
        </div>
    </div>
    """

    if by_type:
        html += """
        <div class="card">
            <div class="card-header">
                <h5 class="mb-0">Processing by Type</h5>
            </div>
            <div class="card-body">
                <div class="table-responsive">
                    <table class="table table-sm">
                        <thead>
                            <tr>
                                <th>Processor Type</th>
                                <th>Total</th>
                                <th>Success</th>
                                <th>Failed</th>
                                <th>Success Rate</th>
                            </tr>
                        </thead>
                        <tbody>
        """

        for ptype, stats in by_type.items():
            type_success_rate = (stats['success'] / stats['total'] * 100) if stats['total'] > 0 else 0
            html += f"""
                            <tr>
                                <td><span class="badge bg-primary">{ptype}</span></td>
                                <td>{stats['total']}</td>
                                <td><span class="text-success">{stats['success']}</span></td>
                                <td><span class="text-danger">{stats['error']}</span></td>
                                <td>
                                    <div class="progress" style="height: 20px;">
                                        <div class="progress-bar" role="progressbar"
                                             style="width: {type_success_rate}%"
                                             aria-valuenow="{type_success_rate}"
                                             aria-valuemin="0" aria-valuemax="100">
                                            {type_success_rate:.1f}%
                                        </div>
                                    </div>
                                </td>
                            </tr>
            """

        html += """
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
        """

    return html

@router.get("/reprocessing-status", response_class=HTMLResponse)
def get_reprocessing_status(session: Session = Depends(get_session)):
    """Get current reprocessing status"""
    from datetime import datetime, timedelta

    # Get recent processing logs (last hour)
    recent_logs = session.exec(
        select(ContentProcessingLog)
        .where(ContentProcessingLog.created_at >= datetime.utcnow() - timedelta(hours=1))
        .order_by(ContentProcessingLog.created_at.desc())
    ).all()

    if not recent_logs:
        return """
        <div class="alert alert-info">
            <i class="bi bi-info-circle me-2"></i>
            No reprocessing activity in the last hour.
        </div>
        """

    success_count = len([log for log in recent_logs if log.status.value == 'success'])
    error_count = len([log for log in recent_logs if log.status.value == 'error'])
    total_count = len(recent_logs)

    html = f"""
    <div class="alert alert-success">
        <h6><i class="bi bi-gear me-2"></i>Reprocessing Active</h6>
        <p class="mb-2">Processing activity in the last hour:</p>
        <div class="row">
            <div class="col-md-4">
                <strong>Total:</strong> {total_count}
            </div>
            <div class="col-md-4">
                <strong>Success:</strong> <span class="text-success">{success_count}</span>
            </div>
            <div class="col-md-4">
                <strong>Errors:</strong> <span class="text-danger">{error_count}</span>
            </div>
        </div>
    </div>
    """

    if error_count > 0:
        html += f"""
        <div class="alert alert-warning">
            <strong>Recent Errors:</strong>
            <ul class="mb-0">
        """

        error_logs = [log for log in recent_logs if log.status.value == 'error'][:5]
        for log in error_logs:
            html += f"<li>Item {log.item_id}: {log.error_message or 'Unknown error'}</li>"

        html += "</ul></div>"

    return html

@router.get("/processor-health-details", response_class=HTMLResponse)
def get_processor_health_details(session: Session = Depends(get_session)):
    """Get detailed processor health information"""
    from datetime import datetime, timedelta

    # Get processing stats for the last 24 hours
    since_24h = datetime.utcnow() - timedelta(hours=24)
    recent_logs = session.exec(
        select(ContentProcessingLog)
        .where(ContentProcessingLog.created_at >= since_24h)
    ).all()

    # Get processing stats for the last 7 days
    since_7d = datetime.utcnow() - timedelta(days=7)
    week_logs = session.exec(
        select(ContentProcessingLog)
        .where(ContentProcessingLog.created_at >= since_7d)
    ).all()

    # Calculate metrics
    stats_24h = {
        'total': len(recent_logs),
        'success': len([log for log in recent_logs if log.status.value == 'success']),
        'error': len([log for log in recent_logs if log.status.value == 'error'])
    }

    stats_7d = {
        'total': len(week_logs),
        'success': len([log for log in week_logs if log.status.value == 'success']),
        'error': len([log for log in week_logs if log.status.value == 'error'])
    }

    success_rate_24h = (stats_24h['success'] / stats_24h['total'] * 100) if stats_24h['total'] > 0 else 100
    success_rate_7d = (stats_7d['success'] / stats_7d['total'] * 100) if stats_7d['total'] > 0 else 100

    # Determine health status
    if success_rate_24h >= 95:
        health_status = ("success", "Excellent")
    elif success_rate_24h >= 85:
        health_status = ("warning", "Good")
    else:
        health_status = ("danger", "Needs Attention")

    html = f"""
    <div class="row">
        <div class="col-md-6">
            <div class="card">
                <div class="card-header">
                    <h6 class="mb-0">24 Hour Stats</h6>
                </div>
                <div class="card-body">
                    <div class="row text-center">
                        <div class="col-4">
                            <h4 class="text-primary">{stats_24h['total']}</h4>
                            <small>Total</small>
                        </div>
                        <div class="col-4">
                            <h4 class="text-success">{stats_24h['success']}</h4>
                            <small>Success</small>
                        </div>
                        <div class="col-4">
                            <h4 class="text-danger">{stats_24h['error']}</h4>
                            <small>Errors</small>
                        </div>
                    </div>
                    <div class="mt-3">
                        <div class="progress">
                            <div class="progress-bar bg-success" style="width: {success_rate_24h}%">
                                {success_rate_24h:.1f}%
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        <div class="col-md-6">
            <div class="card">
                <div class="card-header">
                    <h6 class="mb-0">7 Day Stats</h6>
                </div>
                <div class="card-body">
                    <div class="row text-center">
                        <div class="col-4">
                            <h4 class="text-primary">{stats_7d['total']}</h4>
                            <small>Total</small>
                        </div>
                        <div class="col-4">
                            <h4 class="text-success">{stats_7d['success']}</h4>
                            <small>Success</small>
                        </div>
                        <div class="col-4">
                            <h4 class="text-danger">{stats_7d['error']}</h4>
                            <small>Errors</small>
                        </div>
                    </div>
                    <div class="mt-3">
                        <div class="progress">
                            <div class="progress-bar bg-success" style="width: {success_rate_7d}%">
                                {success_rate_7d:.1f}%
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
    <div class="row mt-3">
        <div class="col-12">
            <div class="alert alert-{health_status[0]}">
                <h5><i class="bi bi-heart-pulse me-2"></i>Processor Health: {health_status[1]}</h5>
                <p class="mb-0">Current 24h success rate: {success_rate_24h:.1f}%</p>
            </div>
        </div>
    </div>
    """

    return html