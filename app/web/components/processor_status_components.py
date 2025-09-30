"""Processor reprocessing status HTMX components."""

from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse
from sqlmodel import Session, select, func
from datetime import datetime, timedelta
from typing import Dict, Any

from app.database import get_session
from app.models import Feed, Item, ContentProcessingLog
from .base_component import BaseComponent

router = APIRouter(tags=["htmx-processor-status"])


class ProcessorStatusComponent(BaseComponent):
    """Component for reprocessing status monitoring."""

    @staticmethod
    def calculate_reprocessing_stats(session: Session) -> Dict[str, Any]:
        """Calculate reprocessing statistics."""
        # Get total items
        total_items = session.exec(select(func.count(Item.id))).one()

        # Get items processed in last 24h
        since_24h = datetime.utcnow() - timedelta(hours=24)
        processed_24h = session.exec(
            select(func.count(func.distinct(ContentProcessingLog.item_id)))
            .where(ContentProcessingLog.processed_at >= since_24h)
        ).one()

        # Get items processed in last 7 days
        since_7d = datetime.utcnow() - timedelta(days=7)
        processed_7d = session.exec(
            select(func.count(func.distinct(ContentProcessingLog.item_id)))
            .where(ContentProcessingLog.processed_at >= since_7d)
        ).one()

        # Get items that have never been processed
        never_processed = session.exec(
            select(func.count(Item.id))
            .where(~Item.id.in_(
                select(ContentProcessingLog.item_id).distinct()
            ))
        ).one()

        return {
            'total_items': total_items,
            'processed_24h': processed_24h,
            'processed_7d': processed_7d,
            'never_processed': never_processed,
            'coverage_percentage': ((total_items - never_processed) / total_items * 100) if total_items > 0 else 0
        }

    @staticmethod
    def get_feed_processing_status(session: Session) -> list:
        """Get processing status for each feed."""
        # Get all feeds with their item counts
        feeds = session.exec(
            select(
                Feed,
                func.count(Item.id).label('item_count')
            )
            .join(Item, Feed.id == Item.feed_id, isouter=True)
            .group_by(Feed.id)
            .order_by(Feed.title)
        ).all()

        feed_status = []
        for feed, item_count in feeds:
            # Get processed items count for this feed
            processed_count = session.exec(
                select(func.count(func.distinct(ContentProcessingLog.item_id)))
                .where(ContentProcessingLog.feed_id == feed.id)
            ).one()

            # Get last processing time
            last_processed = session.exec(
                select(func.max(ContentProcessingLog.processed_at))
                .where(ContentProcessingLog.feed_id == feed.id)
            ).one()

            feed_status.append({
                'feed': feed,
                'item_count': item_count or 0,
                'processed_count': processed_count,
                'last_processed': last_processed,
                'coverage': (processed_count / item_count * 100) if item_count else 0
            })

        return feed_status


@router.get("/reprocessing-status", response_class=HTMLResponse)
def get_reprocessing_status(session: Session = Depends(get_session)):
    """Get comprehensive reprocessing status."""
    stats = ProcessorStatusComponent.calculate_reprocessing_stats(session)
    feed_status = ProcessorStatusComponent.get_feed_processing_status(session)

    # Build feed status rows
    feed_rows = []
    for status in feed_status:
        coverage_color = 'success' if status['coverage'] >= 90 else 'warning' if status['coverage'] >= 70 else 'danger'
        feed_rows.append(f'''
        <tr>
            <td>
                <strong>{status['feed'].title}</strong><br>
                <small class="text-muted">{status['feed'].url[:50]}...</small>
            </td>
            <td class="text-center">
                {status['item_count']:,}
            </td>
            <td class="text-center">
                {status['processed_count']:,}
            </td>
            <td class="text-center">
                <div class="progress" style="height: 20px; min-width: 100px;">
                    <div class="progress-bar bg-{coverage_color}"
                         role="progressbar"
                         style="width: {status['coverage']:.0f}%"
                         aria-valuenow="{status['coverage']:.0f}"
                         aria-valuemin="0"
                         aria-valuemax="100">
                        {status['coverage']:.0f}%
                    </div>
                </div>
            </td>
            <td>
                <small>
                    {ProcessorStatusComponent.format_date(status['last_processed']) if status['last_processed'] else 'Never'}
                </small>
            </td>
            <td class="text-center">
                <button class="btn btn-sm btn-outline-primary"
                        hx-post="/api/processors/reprocess-feed/{status['feed'].id}"
                        hx-target="#reprocess-status-{status['feed'].id}"
                        hx-swap="innerHTML">
                    <i class="bi bi-arrow-repeat"></i>
                </button>
                <span id="reprocess-status-{status['feed'].id}"></span>
            </td>
        </tr>
        ''')

    # Calculate overall progress
    overall_progress = stats['coverage_percentage']
    progress_color = 'success' if overall_progress >= 90 else 'warning' if overall_progress >= 70 else 'danger'

    return f'''
    <div class="container-fluid">
        <!-- Overall Stats -->
        <div class="row mb-4">
            <div class="col-md-3">
                <div class="card">
                    <div class="card-body text-center">
                        <h6 class="text-muted">Total Items</h6>
                        <h3 class="mb-0">{stats['total_items']:,}</h3>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card">
                    <div class="card-body text-center">
                        <h6 class="text-muted">Never Processed</h6>
                        <h3 class="mb-0 text-danger">{stats['never_processed']:,}</h3>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card">
                    <div class="card-body text-center">
                        <h6 class="text-muted">Last 24h</h6>
                        <h3 class="mb-0 text-success">{stats['processed_24h']:,}</h3>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card">
                    <div class="card-body text-center">
                        <h6 class="text-muted">Last 7 Days</h6>
                        <h3 class="mb-0 text-info">{stats['processed_7d']:,}</h3>
                    </div>
                </div>
            </div>
        </div>

        <!-- Overall Progress -->
        <div class="mb-4">
            <h5>Overall Processing Coverage</h5>
            <div class="progress" style="height: 30px;">
                <div class="progress-bar bg-{progress_color} progress-bar-striped progress-bar-animated"
                     role="progressbar"
                     style="width: {overall_progress:.1f}%"
                     aria-valuenow="{overall_progress:.1f}"
                     aria-valuemin="0"
                     aria-valuemax="100">
                    {overall_progress:.1f}% of all items processed
                </div>
            </div>
        </div>

        <!-- Feed Status Table -->
        <h5 class="mb-3">Processing Status by Feed</h5>
        <div class="table-responsive">
            <table class="table table-hover">
                <thead>
                    <tr>
                        <th>Feed</th>
                        <th class="text-center">Total Items</th>
                        <th class="text-center">Processed</th>
                        <th class="text-center">Coverage</th>
                        <th>Last Processed</th>
                        <th class="text-center">Actions</th>
                    </tr>
                </thead>
                <tbody>
                    {''.join(feed_rows) if feed_rows else '<tr><td colspan="6" class="text-center text-muted">No feeds available</td></tr>'}
                </tbody>
            </table>
        </div>

        <!-- Bulk Actions -->
        <div class="mt-4">
            <h5 class="mb-3">Bulk Reprocessing</h5>
            <div class="btn-group" role="group">
                <button class="btn btn-outline-warning"
                        hx-post="/api/processors/reprocess-unprocessed"
                        hx-confirm="This will process all {stats['never_processed']:,} unprocessed items. Continue?">
                    <i class="bi bi-exclamation-triangle"></i>
                    Process Unprocessed ({stats['never_processed']:,})
                </button>
                <button class="btn btn-outline-danger"
                        hx-post="/api/processors/reprocess-all"
                        hx-confirm="This will reprocess ALL {stats['total_items']:,} items. This operation may take a long time. Continue?">
                    <i class="bi bi-arrow-repeat"></i>
                    Reprocess All ({stats['total_items']:,})
                </button>
            </div>
        </div>
    </div>
    '''