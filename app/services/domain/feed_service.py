"""Feed management service with business logic."""

from typing import List, Optional, Dict, Any, Tuple
from sqlmodel import Session, select
from app.core.logging_config import get_logger
from datetime import datetime, timedelta

from .base import BaseService, ServiceResult, NotFoundError, ValidationError, BusinessLogicError
from app.models import Feed, Source, Category, FeedCategory, Item, FeedHealth, FetchLog
# from app.schemas import FeedCreate, FeedUpdate, FeedResponse
from typing import Any
FeedCreate = Any
FeedUpdate = Any
FeedResponse = Any
from app.services.feed_change_tracker import track_feed_changes

logger = get_logger(__name__)


class FeedService(BaseService[Feed, FeedCreate, FeedUpdate]):
    """Service for feed management operations."""

    def get_by_id(self, feed_id: int) -> ServiceResult[Feed]:
        """Get feed by ID."""
        try:
            feed = self.session.get(Feed, feed_id)
            if not feed:
                return ServiceResult.error(f"Feed with id {feed_id} not found")
            return ServiceResult.ok(feed)
        except Exception as e:
            logger.error(f"Error getting feed {feed_id}: {e}")
            return ServiceResult.error(f"Database error: {str(e)}")

    def list(self, skip: int = 0, limit: int = 100, filters: Optional[Dict[str, Any]] = None) -> ServiceResult[List[Feed]]:
        """List feeds with pagination and filters."""
        try:
            query = select(Feed)

            if filters:
                if 'category_id' in filters and filters['category_id']:
                    query = query.join(FeedCategory).where(FeedCategory.category_id == filters['category_id'])

                if 'status' in filters and filters['status']:
                    query = query.where(Feed.status == filters['status'])

                if 'source_id' in filters and filters['source_id']:
                    query = query.where(Feed.source_id == filters['source_id'])

            feeds = self.session.exec(query.offset(skip).limit(limit)).all()
            return ServiceResult.ok(list(feeds))

        except Exception as e:
            logger.error(f"Error listing feeds: {e}")
            return ServiceResult.error(f"Database error: {str(e)}")

    def create(self, create_data: FeedCreate) -> ServiceResult[Feed]:
        """Create new feed with validation and initial fetch."""
        try:
            # Validate source exists
            source = self.session.get(Source, create_data.source_id)
            if not source:
                return ServiceResult.error(f"Source with id {create_data.source_id} not found")

            # Check for duplicate URLs
            existing_feed = self.session.exec(
                select(Feed).where(Feed.url == create_data.url)
            ).first()
            if existing_feed:
                return ServiceResult.error(f"Feed with URL {create_data.url} already exists")

            # Create feed
            feed_data = create_data.model_dump()
            feed_data['created_at'] = datetime.utcnow()
            feed = Feed(**feed_data)

            self.session.add(feed)
            self.session.commit()
            self.session.refresh(feed)

            # Handle categories if provided
            if hasattr(create_data, 'category_ids') and create_data.category_ids:
                self._assign_categories(feed.id, create_data.category_ids)

            # Track the change
            FeedChangeTracker.log_feed_created(feed, created_by='system')

            # Trigger initial fetch
            self._trigger_initial_fetch(feed.id)

            logger.info(f"Created feed {feed.id}: {feed.title or feed.url}")
            return ServiceResult.ok(feed)

        except Exception as e:
            self.session.rollback()
            logger.error(f"Error creating feed: {e}")
            return ServiceResult.error(f"Failed to create feed: {str(e)}")

    def update(self, feed_id: int, update_data: FeedUpdate) -> ServiceResult[Feed]:
        """Update existing feed."""
        try:
            feed = self.session.get(Feed, feed_id)
            if not feed:
                return ServiceResult.error(f"Feed with id {feed_id} not found")

            # Store original values for change tracking
            original_values = {
                "title": feed.title,
                "url": feed.url,
                "status": feed.status,
                "fetch_interval_minutes": feed.fetch_interval_minutes
            }

            # Update fields
            update_dict = update_data.model_dump(exclude_unset=True)
            for field, value in update_dict.items():
                if hasattr(feed, field):
                    setattr(feed, field, value)

            feed.updated_at = datetime.utcnow()

            self.session.commit()
            self.session.refresh(feed)

            # Handle category updates if provided
            if hasattr(update_data, 'category_ids') and update_data.category_ids is not None:
                self._update_categories(feed_id, update_data.category_ids)

            # Track changes
            changes = {}
            for field, original_value in original_values.items():
                current_value = getattr(feed, field)
                if current_value != original_value:
                    changes[field] = {"from": original_value, "to": current_value}

            if changes:
                # Track the change with FeedChangeTracker
                FeedChangeTracker.log_feed_updated(feed, original_values, updated_by='system')

            logger.info(f"Updated feed {feed_id}: {changes}")
            return ServiceResult.ok(feed)

        except Exception as e:
            self.session.rollback()
            logger.error(f"Error updating feed {feed_id}: {e}")
            return ServiceResult.error(f"Failed to update feed: {str(e)}")

    def delete(self, feed_id: int) -> ServiceResult[bool]:
        """Delete feed and related data."""
        try:
            feed = self.session.get(Feed, feed_id)
            if not feed:
                return ServiceResult.error(f"Feed with id {feed_id} not found")

            # Store feed info for logging before deletion
            feed_title = feed.title or feed.url
            feed_data = FeedChangeTracker._feed_to_dict(feed)

            # Track the change before deletion (when relationships still exist)
            FeedChangeTracker.log_feed_deleted(feed_id, feed_data, deleted_by='system')

            # Delete related data in the correct order to avoid foreign key constraints

            # 1. Delete items related to this feed (and their related records)
            items_to_delete = self.session.exec(select(Item).where(Item.feed_id == feed_id)).all()
            for item in items_to_delete:
                # Delete content processing logs first
                from app.models.content import ContentProcessingLog
                processing_logs = self.session.exec(select(ContentProcessingLog).where(ContentProcessingLog.item_id == item.id)).all()
                for log in processing_logs:
                    self.session.delete(log)

                # Delete item tags
                from app.models.content import ItemTag
                item_tags = self.session.exec(select(ItemTag).where(ItemTag.item_id == item.id)).all()
                for tag in item_tags:
                    self.session.delete(tag)

                # Then delete the item itself
                self.session.delete(item)

            # 2. Delete fetch logs
            fetch_logs_to_delete = self.session.exec(select(FetchLog).where(FetchLog.feed_id == feed_id)).all()
            for fetch_log in fetch_logs_to_delete:
                self.session.delete(fetch_log)

            # 3. Delete feed health records
            feed_health_to_delete = self.session.exec(select(FeedHealth).where(FeedHealth.feed_id == feed_id)).all()
            for feed_health in feed_health_to_delete:
                self.session.delete(feed_health)

            # 4. Delete feed categories
            categories_to_delete = self.session.exec(select(FeedCategory).where(FeedCategory.feed_id == feed_id)).all()
            for category_link in categories_to_delete:
                self.session.delete(category_link)

            # 5. Delete feed template assignments
            from app.models.configuration import FeedTemplateAssignment
            template_assignments_to_delete = self.session.exec(select(FeedTemplateAssignment).where(FeedTemplateAssignment.feed_id == feed_id)).all()
            for assignment in template_assignments_to_delete:
                self.session.delete(assignment)

            # 6. Delete feed configuration changes
            from app.models.configuration import FeedConfigurationChange
            config_changes_to_delete = self.session.exec(select(FeedConfigurationChange).where(FeedConfigurationChange.feed_id == feed_id)).all()
            for config_change in config_changes_to_delete:
                self.session.delete(config_change)

            # 7. Finally delete the feed itself
            self.session.delete(feed)
            self.session.commit()

            logger.info(f"Deleted feed {feed_id}: {feed_title}")
            return ServiceResult.ok(True)

        except Exception as e:
            self.session.rollback()
            logger.error(f"Error deleting feed {feed_id}: {e}")
            return ServiceResult.error(f"Failed to delete feed: {str(e)}")

    def get_feed_health(self, feed_id: int) -> ServiceResult[Optional[FeedHealth]]:
        """Get feed health information."""
        try:
            health = self.session.exec(
                select(FeedHealth).where(FeedHealth.feed_id == feed_id)
            ).first()
            return ServiceResult.ok(health)
        except Exception as e:
            logger.error(f"Error getting feed health for {feed_id}: {e}")
            return ServiceResult.error(f"Database error: {str(e)}")

    def get_feed_statistics(self, feed_id: int) -> ServiceResult[Dict[str, Any]]:
        """Get comprehensive feed statistics."""
        try:
            feed = self.session.get(Feed, feed_id)
            if not feed:
                return ServiceResult.error(f"Feed with id {feed_id} not found")

            # Get item count
            item_count = len(self.session.exec(
                select(Item).where(Item.feed_id == feed_id)
            ).all())

            # Get recent items (last 24h)
            recent_cutoff = datetime.utcnow() - timedelta(hours=24)
            recent_items = len(self.session.exec(
                select(Item).where(
                    Item.feed_id == feed_id,
                    Item.created_at >= recent_cutoff
                )
            ).all())

            # Get last fetch info
            last_fetch = self.session.exec(
                select(FetchLog)
                .where(FetchLog.feed_id == feed_id)
                .order_by(FetchLog.created_at.desc())
                .limit(1)
            ).first()

            stats = {
                "total_items": item_count,
                "recent_items_24h": recent_items,
                "last_fetch_at": last_fetch.created_at if last_fetch else None,
                "last_fetch_status": last_fetch.status if last_fetch else None,
                "last_fetch_items": last_fetch.items_new if last_fetch else None
            }

            return ServiceResult.ok(stats)

        except Exception as e:
            logger.error(f"Error getting feed statistics for {feed_id}: {e}")
            return ServiceResult.error(f"Database error: {str(e)}")

    def trigger_immediate_fetch(self, feed_id: int) -> ServiceResult[Tuple[bool, int]]:
        """Trigger immediate fetch for a feed."""
        try:
            feed = self.session.get(Feed, feed_id)
            if not feed:
                return ServiceResult.error(f"Feed with id {feed_id} not found")

            success, items_count = self._trigger_initial_fetch(feed_id)
            return ServiceResult.ok((success, items_count))

        except Exception as e:
            logger.error(f"Error triggering fetch for feed {feed_id}: {e}")
            return ServiceResult.error(f"Failed to trigger fetch: {str(e)}")

    def _assign_categories(self, feed_id: int, category_ids: List[int]) -> None:
        """Assign categories to feed."""
        for category_id in category_ids:
            category = self.session.get(Category, category_id)
            if category:
                feed_category = FeedCategory(feed_id=feed_id, category_id=category_id)
                self.session.add(feed_category)
        self.session.commit()

    def _update_categories(self, feed_id: int, category_ids: List[int]) -> None:
        """Update feed categories (remove old, add new)."""
        # Remove existing categories
        existing = self.session.exec(
            select(FeedCategory).where(FeedCategory.feed_id == feed_id)
        ).all()
        for feed_category in existing:
            self.session.delete(feed_category)

        # Add new categories
        self._assign_categories(feed_id, category_ids)

    def _trigger_initial_fetch(self, feed_id: int) -> Tuple[bool, int]:
        """Trigger immediate initial fetch for a feed."""
        try:
            from app.services.feed_fetcher_sync import SyncFeedFetcher

            logger.info(f"Starting immediate synchronous fetch for feed {feed_id}")
            fetcher = SyncFeedFetcher()
            success, items_count = fetcher.fetch_feed_sync(feed_id)

            if success:
                logger.info(f"Initial fetch successful for feed {feed_id}: {items_count} items loaded")
            else:
                logger.warning(f"Initial fetch failed for feed {feed_id}")

            return success, items_count

        except Exception as e:
            logger.warning(f"Failed to trigger initial fetch for feed {feed_id}: {e}")
            return False, 0