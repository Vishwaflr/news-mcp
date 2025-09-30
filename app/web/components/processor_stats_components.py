"""Processor statistics and health HTMX components."""

from fastapi import APIRouter, Depends, Query
from fastapi.responses import HTMLResponse
from sqlmodel import Session, select, func, desc
from datetime import datetime, timedelta
from typing import Optional

from app.database import get_session
from app.models import (
    FeedProcessorConfig, Feed, ContentProcessingLog,
    ProcessorType, ProcessingStatus
)
from .base_component import BaseComponent

router = APIRouter(tags=["htmx-processor-stats"])


class ProcessorStatsComponent(BaseComponent):
    """Component for processor statistics and health monitoring."""

    @staticmethod
    def get_status_badge_color(status: str) -> str:
        """Get badge color for processing status."""
        return {
            'success': 'success',
            'failed': 'danger',
            'partial': 'warning',
            'skipped': 'secondary'
        }.get(status, 'secondary')


@router.get("/processor-stats", response_class=HTMLResponse)
def get_processor_stats(session: Session = Depends(get_session), days: int = 7):
    """Get processor statistics for the last N days."""
    since = datetime.utcnow() - timedelta(days=days)

    # Overall stats
    total_processed = session.exec(
        select(func.count(ContentProcessingLog.id))
        .where(ContentProcessingLog.processed_at >= since)
    ).one()

    success_count = session.exec(
        select(func.count(ContentProcessingLog.id))
        .where(ContentProcessingLog.processed_at >= since)
        .where(ContentProcessingLog.processing_status == ProcessingStatus.SUCCESS)
    ).one()

    failed_count = session.exec(
        select(func.count(ContentProcessingLog.id))
        .where(ContentProcessingLog.processed_at >= since)
        .where(ContentProcessingLog.processing_status == ProcessingStatus.FAILED)
    ).one()

    # Stats by processor type
    stats_by_type = session.exec(
        select(
            ContentProcessingLog.processor_type,
            ContentProcessingLog.processing_status,
            func.count(ContentProcessingLog.id).label('count')
        )
        .where(ContentProcessingLog.processed_at >= since)
        .group_by(ContentProcessingLog.processor_type, ContentProcessingLog.processing_status)
    ).all()

    # Group stats by processor type
    processor_stats = {}
    for processor_type, status, count in stats_by_type:
        if processor_type not in processor_stats:
            processor_stats[processor_type] = {
                'total': 0,
                'success': 0,
                'failed': 0,
                'partial': 0,
                'skipped': 0
            }
        processor_stats[processor_type]['total'] += count
        if status:
            processor_stats[processor_type][status.value] = count

    # Success rate
    success_rate = (success_count / total_processed * 100) if total_processed > 0 else 0

    # Build processor type cards
    processor_cards = []
    for proc_type, stats in processor_stats.items():
        type_success_rate = (stats['success'] / stats['total'] * 100) if stats['total'] > 0 else 0
        processor_cards.append(f'''
        <div class="col-md-6 col-lg-3">
            <div class="card mb-3">
                <div class="card-body">
                    <h6 class="card-title text-muted">{proc_type.value if proc_type else 'Unknown'}</h6>
                    <div class="d-flex justify-content-between align-items-center">
                        <h3 class="mb-0">{stats['total']:,}</h3>
                        <span class="badge bg-{'success' if type_success_rate >= 90 else 'warning' if type_success_rate >= 75 else 'danger'}">
                            {type_success_rate:.0f}%
                        </span>
                    </div>
                    <div class="mt-2">
                        <div class="progress" style="height: 6px;">
                            <div class="progress-bar bg-success"
                                 style="width: {stats['success'] / stats['total'] * 100 if stats['total'] > 0 else 0:.0f}%"></div>
                            <div class="progress-bar bg-warning"
                                 style="width: {stats['partial'] / stats['total'] * 100 if stats['total'] > 0 else 0:.0f}%"></div>
                            <div class="progress-bar bg-danger"
                                 style="width: {stats['failed'] / stats['total'] * 100 if stats['total'] > 0 else 0:.0f}%"></div>
                        </div>
                    </div>
                    <small class="text-muted">
                        ✅ {stats['success']:,} | ⚠️ {stats['partial']:,} | ❌ {stats['failed']:,}
                    </small>
                </div>
            </div>
        </div>
        ''')

    # Recent processing logs
    recent_logs = session.exec(
        select(ContentProcessingLog)
        .order_by(desc(ContentProcessingLog.processed_at))
        .limit(10)
    ).all()

    log_rows = []
    for log in recent_logs:
        status_color = ProcessorStatsComponent.get_status_badge_color(log.processing_status.value if log.processing_status else 'unknown')
        log_rows.append(f'''
        <tr>
            <td><small>{ProcessorStatsComponent.format_date(log.processed_at)}</small></td>
            <td>
                <span class="badge bg-secondary">
                    {log.processor_type.value if log.processor_type else 'Unknown'}
                </span>
            </td>
            <td>
                <span class="badge bg-{status_color}">
                    {log.processing_status.value if log.processing_status else 'Unknown'}
                </span>
            </td>
            <td>
                <small class="text-muted">
                    {log.processing_time_ms}ms
                </small>
            </td>
            <td>
                <small class="text-truncate d-inline-block" style="max-width: 200px;"
                       title="{log.error_message or 'No errors'}">
                    {log.error_message[:50] + '...' if log.error_message and len(log.error_message) > 50 else log.error_message or '-'}
                </small>
            </td>
        </tr>
        ''')

    return f'''
    <div class="container-fluid">
        <!-- Overall Stats -->
        <div class="row mb-4">
            <div class="col-md-3">
                <div class="card bg-primary text-white">
                    <div class="card-body">
                        <h6 class="card-title">Total Processed</h6>
                        <h2 class="mb-0">{total_processed:,}</h2>
                        <small>Last {days} days</small>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card bg-success text-white">
                    <div class="card-body">
                        <h6 class="card-title">Success Rate</h6>
                        <h2 class="mb-0">{success_rate:.1f}%</h2>
                        <small>{success_count:,} successful</small>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card bg-warning text-dark">
                    <div class="card-body">
                        <h6 class="card-title">Active Configs</h6>
                        <h2 class="mb-0">{len(processor_stats)}</h2>
                        <small>Processor types</small>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card bg-danger text-white">
                    <div class="card-body">
                        <h6 class="card-title">Failed</h6>
                        <h2 class="mb-0">{failed_count:,}</h2>
                        <small>Processing errors</small>
                    </div>
                </div>
            </div>
        </div>

        <!-- By Processor Type -->
        <h5 class="mb-3">Performance by Processor Type</h5>
        <div class="row mb-4">
            {''.join(processor_cards) if processor_cards else '<div class="col"><p class="text-muted">No processor statistics available</p></div>'}
        </div>

        <!-- Recent Logs -->
        <h5 class="mb-3">Recent Processing Activity</h5>
        <div class="table-responsive">
            <table class="table table-sm table-hover">
                <thead>
                    <tr>
                        <th>Time</th>
                        <th>Processor</th>
                        <th>Status</th>
                        <th>Duration</th>
                        <th>Error</th>
                    </tr>
                </thead>
                <tbody>
                    {''.join(log_rows) if log_rows else '<tr><td colspan="5" class="text-center text-muted">No recent processing logs</td></tr>'}
                </tbody>
            </table>
        </div>
    </div>
    '''


@router.get("/processor-health-details", response_class=HTMLResponse)
def get_processor_health_details(session: Session = Depends(get_session)):
    """Get detailed processor health information."""
    # Get all processor configs with their feeds
    configs = session.exec(
        select(FeedProcessorConfig, Feed)
        .join(Feed, FeedProcessorConfig.feed_id == Feed.id)
        .where(FeedProcessorConfig.is_active == True)
        .order_by(Feed.title)
    ).all()

    health_cards = []
    for config, feed in configs:
        # Get recent stats for this processor
        since = datetime.utcnow() - timedelta(hours=24)
        recent_stats = session.exec(
            select(
                ContentProcessingLog.processing_status,
                func.count(ContentProcessingLog.id).label('count')
            )
            .where(ContentProcessingLog.feed_id == feed.id)
            .where(ContentProcessingLog.processor_type == config.processor_type)
            .where(ContentProcessingLog.processed_at >= since)
            .group_by(ContentProcessingLog.processing_status)
        ).all()

        stats_dict = {status.value: count for status, count in recent_stats if status}
        total = sum(stats_dict.values())
        success_rate = (stats_dict.get('success', 0) / total * 100) if total > 0 else 0

        # Last processing time
        last_log = session.exec(
            select(ContentProcessingLog)
            .where(ContentProcessingLog.feed_id == feed.id)
            .where(ContentProcessingLog.processor_type == config.processor_type)
            .order_by(desc(ContentProcessingLog.processed_at))
            .limit(1)
        ).first()

        health_status = 'success' if success_rate >= 90 else 'warning' if success_rate >= 75 else 'danger'

        health_cards.append(f'''
        <div class="col-md-6 col-lg-4">
            <div class="card mb-3 border-{health_status}">
                <div class="card-header bg-{health_status} bg-opacity-10">
                    <div class="d-flex justify-content-between align-items-center">
                        <strong>{feed.title}</strong>
                        <span class="badge bg-{health_status}">{success_rate:.0f}%</span>
                    </div>
                </div>
                <div class="card-body">
                    <div class="mb-2">
                        <small class="text-muted">Processor:</small>
                        <span class="badge bg-secondary ms-2">{config.processor_type.value}</span>
                    </div>
                    <div class="mb-2">
                        <small class="text-muted">24h Stats:</small>
                        <div class="mt-1">
                            ✅ {stats_dict.get('success', 0)} |
                            ⚠️ {stats_dict.get('partial', 0)} |
                            ❌ {stats_dict.get('failed', 0)}
                        </div>
                    </div>
                    <div>
                        <small class="text-muted">Last Run:</small>
                        <div class="mt-1">
                            {ProcessorStatsComponent.format_date(last_log.processed_at) if last_log else 'Never'}
                        </div>
                    </div>
                </div>
            </div>
        </div>
        ''')

    return f'''
    <div class="row">
        {''.join(health_cards) if health_cards else '<div class="col"><div class="alert alert-info">No active processor configurations</div></div>'}
    </div>
    '''