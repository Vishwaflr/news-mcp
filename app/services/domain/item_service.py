"""Item processing and management service."""

from typing import List, Optional, Dict, Any, Tuple
from sqlmodel import Session, select, or_
from datetime import datetime, timedelta
from app.core.logging_config import get_logger

from .base import BaseService, ServiceResult, NotFoundError, ValidationError
from app.models import Item, Feed, FeedCategory

# Try to import ItemAnalysis, handle gracefully if not available
try:
    from app.models import ItemAnalysis
except ImportError:
    ItemAnalysis = None

logger = get_logger(__name__)


class ItemService:
    """Service for item processing and management operations."""

    def __init__(self, session: Session):
        self.session = session

    def get_by_id(self, item_id: int) -> ServiceResult[Item]:
        """Get item by ID."""
        try:
            item = self.session.get(Item, item_id)
            if not item:
                return ServiceResult.error(f"Item with id {item_id} not found")
            return ServiceResult.ok(item)
        except Exception as e:
            logger.error(f"Error getting item {item_id}: {e}")
            return ServiceResult.error(f"Database error: {str(e)}")

    def list_with_filters(
        self,
        skip: int = 0,
        limit: int = 20,
        category_id: Optional[int] = None,
        feed_id: Optional[int] = None,
        search: Optional[str] = None,
        since_hours: Optional[int] = None,
        unanalyzed_only: bool = False
    ) -> ServiceResult[List[Tuple[Item, Feed, Optional[Any]]]]:
        """List items with comprehensive filtering options."""
        try:
            # Build base query with joins
            if ItemAnalysis:
                query = select(Item, Feed, ItemAnalysis).join(Feed).outerjoin(ItemAnalysis, Item.id == ItemAnalysis.item_id)
            else:
                query = select(Item, Feed).join(Feed)

            # Apply filters
            if category_id:
                query = query.join(FeedCategory).where(FeedCategory.category_id == category_id)

            if feed_id:
                query = query.where(Item.feed_id == feed_id)

            if since_hours:
                since_time = datetime.utcnow() - timedelta(hours=since_hours)
                query = query.where(Item.created_at >= since_time)

            if search:
                search_term = f"%{search}%"
                query = query.where(
                    or_(
                        Item.title.contains(search_term),
                        Item.description.contains(search_term)
                    )
                )

            if unanalyzed_only and ItemAnalysis:
                query = query.where(ItemAnalysis.id.is_(None))

            # Order by published date first, then by created_at
            from sqlalchemy import desc, case
            query = query.order_by(
                desc(case(
                    (Item.published.is_(None), Item.created_at),
                    else_=Item.published
                ))
            ).offset(skip).limit(limit)

            results = self.session.exec(query).all()

            # Convert results to consistent format
            processed_results = []
            for result in results:
                if ItemAnalysis:
                    item, feed, analysis = result
                else:
                    item, feed = result
                    analysis = None
                processed_results.append((item, feed, analysis))

            return ServiceResult.ok(processed_results)

        except Exception as e:
            logger.error(f"Error listing items: {e}")
            return ServiceResult.error(f"Database error: {str(e)}")

    def get_item_statistics(self, feed_id: Optional[int] = None) -> ServiceResult[Dict[str, Any]]:
        """Get item statistics, optionally filtered by feed."""
        try:
            base_query = select(Item)
            if feed_id:
                base_query = base_query.where(Item.feed_id == feed_id)

            # Total items
            total_items = len(self.session.exec(base_query).all())

            # Recent items (last 24h)
            recent_cutoff = datetime.utcnow() - timedelta(hours=24)
            recent_items = len(self.session.exec(
                base_query.where(Item.created_at >= recent_cutoff)
            ).all())

            # Items by date range
            week_cutoff = datetime.utcnow() - timedelta(days=7)
            week_items = len(self.session.exec(
                base_query.where(Item.created_at >= week_cutoff)
            ).all())

            month_cutoff = datetime.utcnow() - timedelta(days=30)
            month_items = len(self.session.exec(
                base_query.where(Item.created_at >= month_cutoff)
            ).all())

            stats = {
                "total_items": total_items,
                "recent_items_24h": recent_items,
                "recent_items_7d": week_items,
                "recent_items_30d": month_items,
                "growth_rate_24h": recent_items,
                "growth_rate_7d": week_items - recent_items if week_items > recent_items else 0
            }

            # Add analysis statistics if available
            if ItemAnalysis:
                analyzed_count = len(self.session.exec(
                    select(ItemAnalysis).join(Item, ItemAnalysis.item_id == Item.id)
                    .where(Item.feed_id == feed_id if feed_id else True)
                ).all())

                stats.update({
                    "analyzed_items": analyzed_count,
                    "unanalyzed_items": total_items - analyzed_count,
                    "analysis_coverage": (analyzed_count / total_items * 100) if total_items > 0 else 0
                })

            return ServiceResult.ok(stats)

        except Exception as e:
            logger.error(f"Error getting item statistics: {e}")
            return ServiceResult.error(f"Database error: {str(e)}")

    def get_items_for_analysis(
        self,
        limit: int = 200,
        feed_ids: Optional[List[int]] = None,
        unanalyzed_only: bool = True
    ) -> ServiceResult[List[Item]]:
        """Get items for analysis processing."""
        try:
            query = select(Item)

            if feed_ids:
                query = query.where(Item.feed_id.in_(feed_ids))

            if unanalyzed_only and ItemAnalysis:
                # Only get items that haven't been analyzed yet
                query = query.outerjoin(ItemAnalysis, Item.id == ItemAnalysis.item_id)\
                           .where(ItemAnalysis.id.is_(None))

            # Order by creation date (oldest first for fair processing)
            query = query.order_by(Item.created_at.asc()).limit(limit)

            items = self.session.exec(query).all()
            return ServiceResult.ok(list(items))

        except Exception as e:
            logger.error(f"Error getting items for analysis: {e}")
            return ServiceResult.error(f"Database error: {str(e)}")

    def get_items_by_feed(self, feed_id: int, limit: int = 100) -> ServiceResult[List[Item]]:
        """Get items for a specific feed."""
        try:
            # Verify feed exists
            feed = self.session.get(Feed, feed_id)
            if not feed:
                return ServiceResult.error(f"Feed with id {feed_id} not found")

            items = self.session.exec(
                select(Item)
                .where(Item.feed_id == feed_id)
                .order_by(Item.published.desc().nulls_last(), Item.created_at.desc())
                .limit(limit)
            ).all()

            return ServiceResult.ok(list(items))

        except Exception as e:
            logger.error(f"Error getting items for feed {feed_id}: {e}")
            return ServiceResult.error(f"Database error: {str(e)}")

    def search_items(
        self,
        query_text: str,
        limit: int = 50,
        feed_id: Optional[int] = None
    ) -> ServiceResult[List[Item]]:
        """Search items by text content."""
        try:
            search_term = f"%{query_text}%"
            query = select(Item).where(
                or_(
                    Item.title.contains(search_term),
                    Item.description.contains(search_term),
                    Item.content.contains(search_term) if hasattr(Item, 'content') else False
                )
            )

            if feed_id:
                query = query.where(Item.feed_id == feed_id)

            query = query.order_by(Item.created_at.desc()).limit(limit)

            items = self.session.exec(query).all()
            return ServiceResult.ok(list(items))

        except Exception as e:
            logger.error(f"Error searching items: {e}")
            return ServiceResult.error(f"Database error: {str(e)}")

    def get_trending_items(self, hours: int = 24, limit: int = 20) -> ServiceResult[List[Item]]:
        """Get trending items based on recent activity."""
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=hours)

            # For now, just return recent items
            # In the future, this could include engagement metrics, analysis scores, etc.
            items = self.session.exec(
                select(Item)
                .where(Item.created_at >= cutoff_time)
                .order_by(Item.created_at.desc())
                .limit(limit)
            ).all()

            return ServiceResult.ok(list(items))

        except Exception as e:
            logger.error(f"Error getting trending items: {e}")
            return ServiceResult.error(f"Database error: {str(e)}")

    def mark_items_as_processed(self, item_ids: List[int]) -> ServiceResult[int]:
        """Mark items as processed (utility method for batch operations)."""
        try:
            # This would typically update a 'processed' flag or timestamp
            # For now, we'll just count the items that exist
            existing_items = self.session.exec(
                select(Item).where(Item.id.in_(item_ids))
            ).all()

            processed_count = len(existing_items)

            # In a real implementation, you might update a processed_at timestamp
            # for item in existing_items:
            #     item.processed_at = datetime.utcnow()
            # self.session.commit()

            return ServiceResult.ok(processed_count)

        except Exception as e:
            logger.error(f"Error marking items as processed: {e}")
            return ServiceResult.error(f"Database error: {str(e)}")

    def get_item_content_summary(self, item_id: int) -> ServiceResult[Dict[str, Any]]:
        """Get content summary and metadata for an item."""
        try:
            item = self.session.get(Item, item_id)
            if not item:
                return ServiceResult.error(f"Item with id {item_id} not found")

            summary = {
                "id": item.id,
                "title": item.title,
                "description": item.description,
                "url": item.link,
                "published_at": item.published,
                "created_at": item.created_at,
                "author": getattr(item, 'author', None),
                "word_count": len(item.description.split()) if item.description else 0,
                "has_content": bool(item.description and len(item.description.strip()) > 10)
            }

            # Add analysis data if available
            if ItemAnalysis:
                analysis = self.session.exec(
                    select(ItemAnalysis).where(ItemAnalysis.item_id == item_id)
                ).first()

                if analysis:
                    summary["analysis"] = {
                        "sentiment": analysis.sentiment_json,
                        "impact": analysis.impact_json,
                        "model_tag": analysis.model_tag,
                        "analyzed_at": analysis.created_at
                    }

            return ServiceResult.ok(summary)

        except Exception as e:
            logger.error(f"Error getting item summary for {item_id}: {e}")
            return ServiceResult.error(f"Database error: {str(e)}")