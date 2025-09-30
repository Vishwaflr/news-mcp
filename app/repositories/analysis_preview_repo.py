"""
Analysis Preview Repository

Handles preview and scope operations for analysis.
Split from analysis_control.py for better maintainability.
"""

from typing import List, Dict, Any
from datetime import datetime, timedelta
from sqlmodel import Session, select, func, text
from app.database import engine
from app.models.core import Item, Feed
from app.models.feeds import FeedCategory
from app.models.analysis import ItemAnalysis
from app.domain.analysis.control import RunScope, RunParams, RunPreview
from app.services.cost_estimator import get_cost_estimator
from app.core.logging_config import get_logger

logger = get_logger(__name__)


class AnalysisPreviewRepo:
    """Repository for analysis preview operations"""

    @staticmethod
    def preview_run(scope: RunScope, params: RunParams) -> RunPreview:
        """Preview what a run would analyze without actually starting it"""
        with Session(engine) as session:
            # Use params.limit if scope.limit is not set
            if scope.limit is None and params.limit:
                scope.limit = params.limit

            # Build query to find matching items
            query = AnalysisPreviewRepo._build_preview_query(scope)

            # Execute query
            items_query = text(query)
            result = session.exec(items_query)
            items = result.fetchall()

            # Count already analyzed items
            item_ids = [item[0] for item in items]
            already_analyzed_count = 0

            if item_ids:
                analyzed_query = select(func.count(ItemAnalysis.item_id)).where(
                    ItemAnalysis.item_id.in_(item_ids)
                )
                already_analyzed_count = session.exec(analyzed_query).one()

            # Calculate estimates
            new_items = len(items) - already_analyzed_count
            cost_estimator = get_cost_estimator()
            estimated_cost = cost_estimator.estimate_cost(
                item_count=new_items,
                model_tag=params.model_tag
            )

            # Estimate duration (rough: 1 second per item with rate limiting)
            estimated_duration_minutes = (new_items / params.rate_per_second / 60) if params.rate_per_second > 0 else 0

            # Get sample item IDs (first 10)
            sample_ids = item_ids[:10] if item_ids else []

            return RunPreview(
                item_count=len(items),
                estimated_cost_usd=estimated_cost,
                estimated_duration_minutes=int(round(estimated_duration_minutes)),
                sample_item_ids=sample_ids,
                already_analyzed_count=already_analyzed_count,
                new_items_count=new_items,
                has_conflicts=False,
                total_items=len(items),
                already_analyzed=already_analyzed_count
            )

    @staticmethod
    def _build_preview_query(scope: RunScope) -> str:
        """Build SQL query for preview based on scope"""
        base_query = """
            SELECT DISTINCT i.id, i.title, i.published
            FROM items i
            LEFT JOIN feeds f ON i.feed_id = f.id
        """

        conditions = []

        # Add scope conditions
        if scope.type == "items" and scope.item_ids:
            conditions.append(f"i.id IN ({','.join(map(str, scope.item_ids))})")
        elif scope.type == "feeds" and scope.feed_ids:
            conditions.append(f"f.id IN ({','.join(map(str, scope.feed_ids))})")
        elif scope.type == "categories" and scope.category_ids:
            base_query = base_query.replace(
                "LEFT JOIN feeds f",
                "LEFT JOIN feeds f LEFT JOIN feed_categories fc ON f.id = fc.feed_id"
            )
            conditions.append(f"fc.category_id IN ({','.join(map(str, scope.category_ids))})")
        elif scope.type == "hours" and scope.hours:
            conditions.append(f"i.published >= NOW() - INTERVAL '{scope.hours} hours'")

        # Add time range filter
        if scope.hours and scope.type != "hours":
            conditions.append(f"i.published >= NOW() - INTERVAL '{scope.hours} hours'")

        # Add feed status filter
        if scope.feed_status:
            conditions.append(f"f.status = '{scope.feed_status}'")

        # Add unanalyzed only filter
        if scope.unanalyzed_only:
            base_query += " LEFT JOIN item_analysis ia ON i.id = ia.item_id"
            conditions.append("ia.item_id IS NULL")

        # Combine conditions
        where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""

        # Add ordering and limit
        order_by = " ORDER BY i.published DESC"
        limit_clause = f" LIMIT {scope.limit}" if scope.limit else " LIMIT 1000"

        return base_query + where_clause + order_by + limit_clause

    @staticmethod
    def get_scope_statistics(scope: RunScope) -> Dict[str, Any]:
        """Get statistics for a given scope"""
        with Session(engine) as session:
            query = AnalysisPreviewRepo._build_preview_query(scope)
            items_query = text(query)
            result = session.exec(items_query)
            items = result.fetchall()

            item_ids = [item[0] for item in items]

            # Get feed distribution
            feed_dist_query = text("""
                SELECT f.id, f.title, COUNT(i.id) as item_count
                FROM items i
                JOIN feeds f ON i.feed_id = f.id
                WHERE i.id IN :item_ids
                GROUP BY f.id, f.title
                ORDER BY item_count DESC
                LIMIT 10
            """)

            feed_dist = []
            if item_ids:
                result = session.exec(feed_dist_query, {"item_ids": tuple(item_ids)})
                feed_dist = [
                    {"feed_id": row[0], "feed_title": row[1], "count": row[2]}
                    for row in result
                ]

            # Get time distribution
            time_dist = {}
            if items:
                dates = [item[2] for item in items if item[2]]
                if dates:
                    oldest = min(dates)
                    newest = max(dates)
                    time_dist = {
                        "oldest": oldest.isoformat() if oldest else None,
                        "newest": newest.isoformat() if newest else None,
                        "span_days": (newest - oldest).days if oldest and newest else 0
                    }

            return {
                "total_items": len(items),
                "feed_distribution": feed_dist,
                "time_distribution": time_dist
            }