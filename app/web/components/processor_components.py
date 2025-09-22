"""Processor management HTMX components."""

from fastapi import APIRouter, Depends, Query
from fastapi.responses import HTMLResponse
from sqlmodel import Session, select, func, desc
from typing import Optional
from datetime import datetime, timedelta

from app.database import get_session
from app.models import (
    FeedProcessorConfig, Feed, ProcessorTemplate, ContentProcessingLog,
    ProcessorType, ProcessingStatus
)
from .base_component import BaseComponent

router = APIRouter(tags=["htmx-processors"])


class ProcessorComponent(BaseComponent):
    """Component for processor-related HTMX endpoints."""

    @staticmethod
    def get_processor_badge_color(processor_type: str) -> str:
        """Get badge color for processor type."""
        return {
            'universal': 'primary',
            'cointelegraph': 'warning',
            'heise': 'success',
            'custom': 'info'
        }.get(processor_type, 'secondary')

    @staticmethod
    def get_status_badge_color(status: str) -> str:
        """Get badge color for processing status."""
        return {
            'success': 'success',
            'failed': 'danger',
            'partial': 'warning',
            'skipped': 'secondary'
        }.get(status, 'secondary')

    @staticmethod
    def build_config_table_row(config: FeedProcessorConfig, feed: Feed) -> str:
        """Build HTML for a processor config table row."""
        feed_name = feed.title or feed.url[:50] + "..."
        status_badge = "success" if config.is_active else "secondary"
        status_text = "Active" if config.is_active else "Inactive"

        return f'''
        <tr>
            <td>
                <strong>{feed_name}</strong><br>
                <small class="text-muted">{feed.url[:60]}{'...' if len(feed.url) > 60 else ''}</small>
            </td>
            <td>
                <span class="badge bg-{ProcessorComponent.get_processor_badge_color(config.processor_type.value)}">{config.processor_type.value}</span>
            </td>
            <td>
                <span class="badge bg-{status_badge}">{status_text}</span>
            </td>
            <td>
                <small>{ProcessorComponent.format_date(config.created_at)}</small>
            </td>
            <td>
                <div class="btn-group btn-group-sm">
                    <button class="btn btn-outline-primary"
                            data-bs-toggle="modal"
                            data-bs-target="#editConfigModal"
                            hx-get="/htmx/processor-config-form/{config.id}"
                            hx-target="#edit-config-form">
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
        '''

    @staticmethod
    def build_template_card(template: ProcessorTemplate) -> str:
        """Build HTML for a processor template card."""
        status_badge = "success" if template.is_active else "secondary"
        status_text = "Active" if template.is_active else "Inactive"
        builtin_badge = "warning" if template.is_builtin else "info"
        builtin_text = "Built-in" if template.is_builtin else "Custom"

        delete_button = "" if template.is_builtin else f'''
        <button class="btn btn-outline-danger"
                hx-delete="/api/processors/templates/{template.id}"
                hx-target="#processor-templates"
                hx-confirm="Really delete template?">
            <i class="bi bi-trash"></i>
        </button>
        '''

        return f'''
        <div class="col-md-6 mb-3">
            <div class="card h-100">
                <div class="card-header d-flex justify-content-between align-items-center">
                    <h6 class="mb-0">{template.name}</h6>
                    <div>
                        <span class="badge bg-{builtin_badge} me-1">{builtin_text}</span>
                        <span class="badge bg-{status_badge}">{status_text}</span>
                    </div>
                </div>
                <div class="card-body">
                    <p class="card-text">
                        <strong>Type:</strong> <span class="badge bg-{ProcessorComponent.get_processor_badge_color(template.processor_type.value)}">{template.processor_type.value}</span>
                    </p>
                    {f'<p class="card-text small text-muted">{template.description}</p>' if template.description else ''}
                    <p class="card-text">
                        <small class="text-muted">
                            Created: {ProcessorComponent.format_date(template.created_at)}<br>
                            Updated: {ProcessorComponent.format_date(template.updated_at)}
                        </small>
                    </p>
                </div>
                <div class="card-footer">
                    <div class="btn-group btn-group-sm w-100">
                        <button class="btn btn-outline-primary"
                                data-bs-toggle="modal"
                                data-bs-target="#editTemplateModal"
                                hx-get="/htmx/processor-template-form/{template.id}"
                                hx-target="#edit-template-form">
                            <i class="bi bi-pencil"></i> Edit
                        </button>
                        <button class="btn btn-outline-info"
                                hx-post="/api/processors/templates/{template.id}/apply"
                                hx-target="#processor-templates"
                                hx-confirm="Template auf alle passenden Feeds anwenden?">
                            <i class="bi bi-check2-all"></i> Apply
                        </button>
                        {delete_button}
                    </div>
                </div>
            </div>
        </div>
        '''


@router.get("/processor-configs", response_class=HTMLResponse)
def get_processor_configs(session: Session = Depends(get_session)):
    """Get feed processor configurations table."""
    query = select(FeedProcessorConfig, Feed).join(Feed)
    results = session.exec(query).all()

    html = '''
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
    '''

    if results:
        for config, feed in results:
            html += ProcessorComponent.build_config_table_row(config, feed)
    else:
        html += '''
            <tr>
                <td colspan="5" class="text-center text-muted">
                    No processor configurations found.
                </td>
            </tr>
        '''

    html += '''
            </tbody>
        </table>
    </div>
    '''

    return html


@router.get("/processor-templates", response_class=HTMLResponse)
def get_processor_templates(session: Session = Depends(get_session)):
    """Get processor templates list."""
    templates = session.exec(select(ProcessorTemplate)).all()

    html = '<div class="row">'

    if templates:
        for template in templates:
            html += ProcessorComponent.build_template_card(template)
    else:
        html += '''
        <div class="col-12">
            <div class="alert alert-info text-center">
                <i class="bi bi-info-circle me-2"></i>
                No processor templates found.
            </div>
        </div>
        '''

    html += '</div>'
    return html


@router.get("/processor-stats", response_class=HTMLResponse)
def get_processor_stats(session: Session = Depends(get_session), days: int = 7):
    """Get detailed processor statistics dashboard."""
    # Get time range
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)

    # Basic statistics
    total_query = select(func.count(ContentProcessingLog.id)).where(
        ContentProcessingLog.processed_at >= start_date
    )
    total_processed = session.exec(total_query).first() or 0

    success_query = select(func.count(ContentProcessingLog.id)).where(
        ContentProcessingLog.processed_at >= start_date,
        ContentProcessingLog.processing_status == "success"
    )
    success_count = session.exec(success_query).first() or 0

    # Processor breakdown
    breakdown_query = select(
        ContentProcessingLog.processor_type,
        func.count(ContentProcessingLog.id).label('count'),
        func.avg(ContentProcessingLog.processing_time_ms).label('avg_time')
    ).where(
        ContentProcessingLog.processed_at >= start_date
    ).group_by(ContentProcessingLog.processor_type)

    breakdown_results = session.exec(breakdown_query).all()
    success_rate = (success_count / total_processed * 100) if total_processed > 0 else 100

    if total_processed == 0:
        return BaseComponent.alert_box(
            'No processing data available for the selected time period.',
            'info',
            'info-circle'
        )

    html = f'''
    <div class="row">
        <!-- Summary Cards -->
        <div class="col-md-3 mb-3">
            <div class="card text-center bg-primary text-white">
                <div class="card-body">
                    <h2 class="display-6">{total_processed}</h2>
                    <p class="card-text">Total Processed</p>
                    <small>Last {days} day{'s' if days > 1 else ''}</small>
                </div>
            </div>
        </div>

        <div class="col-md-3 mb-3">
            <div class="card text-center bg-success text-white">
                <div class="card-body">
                    <h2 class="display-6">{success_count}</h2>
                    <p class="card-text">Successful</p>
                    <small>{success_rate:.1f}% success rate</small>
                </div>
            </div>
        </div>

        <div class="col-md-3 mb-3">
            <div class="card text-center bg-danger text-white">
                <div class="card-body">
                    <h2 class="display-6">{total_processed - success_count}</h2>
                    <p class="card-text">Failed</p>
                    <small>{(100 - success_rate):.1f}% failure rate</small>
                </div>
            </div>
        </div>

        <div class="col-md-3 mb-3">
            <div class="card text-center bg-info text-white">
                <div class="card-body">
                    <h2 class="display-6">{len(breakdown_results)}</h2>
                    <p class="card-text">Active Processors</p>
                    <small>In use</small>
                </div>
            </div>
        </div>
    </div>

    <div class="row">
        <!-- Processor Performance -->
        <div class="col-md-8 mb-3">
            <div class="card">
                <div class="card-header">
                    <h6><i class="bi bi-bar-chart"></i> Processor Performance Breakdown</h6>
                </div>
                <div class="card-body">
                    <div class="table-responsive">
                        <table class="table table-sm">
                            <thead>
                                <tr>
                                    <th>Processor Type</th>
                                    <th>Items Processed</th>
                                    <th>Avg Time (ms)</th>
                                    <th>Usage %</th>
                                </tr>
                            </thead>
                            <tbody>
    '''

    for result in breakdown_results:
        processor_type = result[0]
        count = result[1]
        avg_time = result[2] or 0
        usage_percent = (count / total_processed * 100) if total_processed > 0 else 0

        badge_color = ProcessorComponent.get_processor_badge_color(
            processor_type.value if hasattr(processor_type, 'value') else str(processor_type)
        )

        html += f'''
                                <tr>
                                    <td><span class="badge bg-{badge_color}">{processor_type.value if hasattr(processor_type, 'value') else processor_type}</span></td>
                                    <td>{count}</td>
                                    <td>{avg_time:.1f}</td>
                                    <td>
                                        <div class="progress" style="height: 20px;">
                                            <div class="progress-bar bg-{badge_color}" role="progressbar"
                                                 style="width: {usage_percent:.1f}%"
                                                 aria-valuenow="{usage_percent:.1f}" aria-valuemin="0" aria-valuemax="100">
                                                {usage_percent:.1f}%
                                            </div>
                                        </div>
                                    </td>
                                </tr>
        '''

    html += '''
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>

        <!-- Quick Actions -->
        <div class="col-md-4 mb-3">
            <div class="card">
                <div class="card-header">
                    <h6><i class="bi bi-tools"></i> Quick Actions</h6>
                </div>
                <div class="card-body">
                    <div class="d-grid gap-2">
                        <button class="btn btn-outline-primary btn-sm"
                                hx-get="/htmx/processor-stats?days=1"
                                hx-target="#detailed-statistics">
                            <i class="bi bi-calendar-day"></i> 24 Hours
                        </button>
                        <button class="btn btn-outline-primary btn-sm"
                                hx-get="/htmx/processor-stats?days=7"
                                hx-target="#detailed-statistics">
                            <i class="bi bi-calendar-week"></i> 7 Days
                        </button>
                        <button class="btn btn-outline-primary btn-sm"
                                hx-get="/htmx/processor-stats?days=30"
                                hx-target="#detailed-statistics">
                            <i class="bi bi-calendar-month"></i> 30 Days
                        </button>
                        <hr>
                        <button class="btn btn-outline-success btn-sm"
                                onclick="exportStats()">
                            <i class="bi bi-download"></i> Export Report
                        </button>
                        <button class="btn btn-outline-info btn-sm"
                                hx-get="/htmx/processor-health-details"
                                hx-target="#health-details-modal"
                                data-bs-toggle="modal"
                                data-bs-target="#healthDetailsModal">
                            <i class="bi bi-heart-pulse"></i> Health Details
                        </button>
                    </div>
                </div>
            </div>
        </div>
    </div>
    '''

    return html


@router.get("/reprocessing-status", response_class=HTMLResponse)
def get_reprocessing_status(session: Session = Depends(get_session)):
    """Get reprocessing status and history."""
    # Recent reprocessing activity (last 24h)
    recent_cutoff = datetime.utcnow() - timedelta(hours=24)
    recent_logs = session.exec(
        select(ContentProcessingLog)
        .where(ContentProcessingLog.processed_at >= recent_cutoff)
        .order_by(desc(ContentProcessingLog.processed_at))
        .limit(10)
    ).all()

    # Statistics
    total_today = session.exec(
        select(func.count(ContentProcessingLog.id))
        .where(ContentProcessingLog.processed_at >= recent_cutoff)
    ).first() or 0

    success_today = session.exec(
        select(func.count(ContentProcessingLog.id))
        .where(
            ContentProcessingLog.processed_at >= recent_cutoff,
            ContentProcessingLog.processing_status == "success"
        )
    ).first() or 0

    success_rate = (success_today / total_today * 100) if total_today > 0 else 0

    html = f'''
    <div class="row mb-3">
        <div class="col-md-6">
            <div class="card border-info">
                <div class="card-header bg-info text-white">
                    <h6 class="mb-0"><i class="bi bi-info-circle"></i> 24h Processing Summary</h6>
                </div>
                <div class="card-body">
                    <div class="row text-center">
                        <div class="col-6">
                            <h4 class="text-primary">{total_today}</h4>
                            <small>Total Processed</small>
                        </div>
                        <div class="col-6">
                            <h4 class="text-success">{success_today}</h4>
                            <small>Successful</small>
                        </div>
                    </div>
                    <div class="progress mt-2">
                        <div class="progress-bar bg-success" role="progressbar"
                             style="width: {success_rate:.1f}%">
                            {success_rate:.1f}%
                        </div>
                    </div>
                </div>
            </div>
        </div>
        <div class="col-md-6">
            <div class="card border-warning">
                <div class="card-header bg-warning text-dark">
                    <h6 class="mb-0"><i class="bi bi-clock"></i> Quick Actions</h6>
                </div>
                <div class="card-body">
                    <div class="d-grid gap-2">
                        <button class="btn btn-sm btn-outline-primary"
                                hx-post="/api/processors/reprocess/all?force_all=false"
                                hx-target="#reprocessing-results"
                                hx-confirm="Reprocess all failed items?">
                            <i class="bi bi-arrow-repeat"></i> Retry Failed Items
                        </button>
                        <button class="btn btn-sm btn-outline-warning"
                                onclick="showBulkReprocessing()">
                            <i class="bi bi-list-check"></i> Bulk Operations
                        </button>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <div class="card">
        <div class="card-header">
            <h6><i class="bi bi-activity"></i> Recent Processing Activity</h6>
        </div>
        <div class="card-body">
            <div class="table-responsive">
                <table class="table table-sm table-hover">
                    <thead>
                        <tr>
                            <th>Time</th>
                            <th>Item ID</th>
                            <th>Feed</th>
                            <th>Processor</th>
                            <th>Status</th>
                            <th>Time (ms)</th>
                        </tr>
                    </thead>
                    <tbody>
    '''

    if recent_logs:
        for log in recent_logs:
            status_badge = ProcessorComponent.get_status_badge_color(log.processing_status)
            processor_badge = ProcessorComponent.get_processor_badge_color(
                log.processor_type.value if hasattr(log.processor_type, 'value') else str(log.processor_type)
            )

            html += f'''
                        <tr>
                            <td><small>{log.processed_at.strftime("%H:%M:%S")}</small></td>
                            <td><small>{log.item_id}</small></td>
                            <td><small>{log.feed_id}</small></td>
                            <td><span class="badge bg-{processor_badge}">{log.processor_type.value if hasattr(log.processor_type, 'value') else log.processor_type}</span></td>
                            <td><span class="badge bg-{status_badge}">{log.processing_status}</span></td>
                            <td><small>{log.processing_time_ms or 0}</small></td>
                        </tr>
            '''
    else:
        html += '''
                        <tr>
                            <td colspan="6" class="text-center text-muted">
                                No recent processing activity
                            </td>
                        </tr>
        '''

    html += '''
                    </tbody>
                </table>
            </div>
        </div>
    </div>
    '''

    return html


@router.get("/processor-health-details", response_class=HTMLResponse)
def get_processor_health_details(session: Session = Depends(get_session)):
    """Get detailed processor health monitoring dashboard."""
    # Health metrics for each processor type
    processor_health = {}

    # Get all active processor configurations
    configs = session.exec(
        select(FeedProcessorConfig, Feed)
        .join(Feed)
        .where(FeedProcessorConfig.is_active == True)
    ).all()

    # Calculate health metrics for each processor
    for config, feed in configs:
        processor_type = config.processor_type.value

        if processor_type not in processor_health:
            processor_health[processor_type] = {
                'feeds': [],
                'total_items': 0,
                'success_items': 0,
                'last_24h': 0,
                'health_score': 100
            }

        # Get processing stats for this feed (last 7 days)
        week_ago = datetime.utcnow() - timedelta(days=7)
        feed_logs = session.exec(
            select(ContentProcessingLog)
            .where(
                ContentProcessingLog.feed_id == feed.id,
                ContentProcessingLog.processed_at >= week_ago
            )
        ).all()

        feed_total = len(feed_logs)
        feed_success = len([log for log in feed_logs if log.processing_status == "success"])

        # Last 24h activity
        day_ago = datetime.utcnow() - timedelta(hours=24)
        feed_24h = len([log for log in feed_logs if log.processed_at >= day_ago])

        processor_health[processor_type]['feeds'].append({
            'name': feed.title or feed.url[:30] + "...",
            'id': feed.id,
            'total': feed_total,
            'success': feed_success,
            'success_rate': (feed_success / feed_total * 100) if feed_total > 0 else 0,
            'activity_24h': feed_24h
        })

        processor_health[processor_type]['total_items'] += feed_total
        processor_health[processor_type]['success_items'] += feed_success
        processor_health[processor_type]['last_24h'] += feed_24h

    # Calculate aggregated metrics
    for proc_type in processor_health:
        data = processor_health[proc_type]
        if data['total_items'] > 0:
            data['success_rate'] = data['success_items'] / data['total_items'] * 100
            data['health_score'] = min(100, data['success_rate'] + (10 if data['last_24h'] > 0 else 0))
        else:
            data['success_rate'] = 0
            data['health_score'] = 50

    html = '''
    <div class="row">
        <div class="col-12">
            <h5><i class="bi bi-heart-pulse"></i> Processor Health Monitoring</h5>
            <p class="text-muted">Detailed health status and performance metrics for all active processors</p>
        </div>
    </div>
    '''

    if not processor_health:
        html += BaseComponent.alert_box('No active processor configurations found.', 'info', 'info-circle')
        return html

    for proc_type, data in processor_health.items():
        # Determine health status color
        if data['health_score'] >= 90:
            health_color = 'success'
            health_text = 'Excellent'
        elif data['health_score'] >= 70:
            health_color = 'warning'
            health_text = 'Good'
        else:
            health_color = 'danger'
            health_text = 'Needs Attention'

        proc_color = ProcessorComponent.get_processor_badge_color(proc_type)

        html += f'''
        <div class="card mb-3">
            <div class="card-header d-flex justify-content-between align-items-center">
                <div>
                    <span class="badge bg-{proc_color} me-2">{proc_type.upper()}</span>
                    <strong>Health Score: {data['health_score']:.1f}</strong>
                    <span class="badge bg-{health_color} ms-2">{health_text}</span>
                </div>
                <small class="text-muted">{len(data['feeds'])} feeds configured</small>
            </div>
            <div class="card-body">
                <div class="row mb-3">
                    <div class="col-md-3">
                        <div class="text-center">
                            <h5 class="text-primary">{data['total_items']}</h5>
                            <small>Total Items (7d)</small>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="text-center">
                            <h5 class="text-success">{data['success_items']}</h5>
                            <small>Successful</small>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="text-center">
                            <h5 class="text-info">{data['last_24h']}</h5>
                            <small>Last 24h</small>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="text-center">
                            <div class="progress">
                                <div class="progress-bar bg-{health_color}" style="width: {data['success_rate']:.1f}%">
                                    {data['success_rate']:.1f}%
                                </div>
                            </div>
                            <small>Success Rate</small>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        '''

    return html