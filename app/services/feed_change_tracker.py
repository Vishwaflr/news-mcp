"""
Feed Change Tracker

Automatically tracks changes to feeds and templates by hooking into
database operations. This ensures all configuration changes are logged
for the scheduler's change detection system.
"""
from app.core.logging_config import get_logger
import json
import hashlib
from typing import Dict, Any, Optional
from datetime import datetime
from sqlmodel import Session

from ..models import Feed, DynamicFeedTemplate, FeedConfigurationChange
from ..database import engine

logger = get_logger(__name__)

class FeedChangeTracker:
    """Tracks and logs changes to feed configurations for scheduler notification"""

    @staticmethod
    def log_feed_created(feed: Feed, created_by: str = None):
        """Log when a feed is created"""
        FeedChangeTracker._log_change(
            change_type='feed_created',
            feed_id=feed.id,
            new_config=FeedChangeTracker._feed_to_dict(feed),
            created_by=created_by
        )

    @staticmethod
    def log_feed_updated(feed: Feed, old_feed_data: Dict[str, Any], updated_by: str = None):
        """Log when a feed is updated"""
        FeedChangeTracker._log_change(
            change_type='feed_updated',
            feed_id=feed.id,
            old_config=old_feed_data,
            new_config=FeedChangeTracker._feed_to_dict(feed),
            created_by=updated_by
        )

    @staticmethod
    def log_feed_deleted(feed_id: int, old_feed_data: Dict[str, Any], deleted_by: str = None):
        """Log when a feed is deleted"""
        FeedChangeTracker._log_change(
            change_type='feed_deleted',
            feed_id=feed_id,
            old_config=old_feed_data,
            created_by=deleted_by
        )

    @staticmethod
    def log_template_created(template: DynamicFeedTemplate, created_by: str = None):
        """Log when a template is created"""
        FeedChangeTracker._log_change(
            change_type='template_created',
            template_id=template.id,
            new_config=FeedChangeTracker._template_to_dict(template),
            created_by=created_by
        )

    @staticmethod
    def log_template_updated(template: DynamicFeedTemplate, old_template_data: Dict[str, Any],
                           updated_by: str = None):
        """Log when a template is updated"""
        FeedChangeTracker._log_change(
            change_type='template_updated',
            template_id=template.id,
            old_config=old_template_data,
            new_config=FeedChangeTracker._template_to_dict(template),
            created_by=updated_by
        )

    @staticmethod
    def log_template_deleted(template_id: int, old_template_data: Dict[str, Any],
                           deleted_by: str = None):
        """Log when a template is deleted"""
        FeedChangeTracker._log_change(
            change_type='template_deleted',
            template_id=template_id,
            old_config=old_template_data,
            created_by=deleted_by
        )

    @staticmethod
    def log_template_assigned(feed_id: int, template_id: int, assigned_by: str = None):
        """Log when a template is assigned to a feed"""
        FeedChangeTracker._log_change(
            change_type='feed_template_assigned',
            feed_id=feed_id,
            template_id=template_id,
            new_config={'template_id': template_id, 'feed_id': feed_id},
            created_by=assigned_by
        )

    @staticmethod
    def log_template_unassigned(feed_id: int, template_id: int, unassigned_by: str = None):
        """Log when a template is unassigned from a feed"""
        FeedChangeTracker._log_change(
            change_type='feed_template_unassigned',
            feed_id=feed_id,
            template_id=template_id,
            old_config={'template_id': template_id, 'feed_id': feed_id},
            created_by=unassigned_by
        )

    @staticmethod
    def update_feed_configuration_hash(feed: Feed):
        """Update the feed's configuration hash for change detection"""
        config_data = FeedChangeTracker._feed_to_dict(feed)
        config_json = json.dumps(config_data, sort_keys=True)
        feed.configuration_hash = hashlib.sha256(config_json.encode()).hexdigest()

    @staticmethod
    def _log_change(change_type: str, feed_id: Optional[int] = None,
                   template_id: Optional[int] = None, old_config: Dict[str, Any] = None,
                   new_config: Dict[str, Any] = None, created_by: Optional[str] = None):
        """Internal method to log a configuration change"""
        try:
            with Session(engine) as session:
                change = FeedConfigurationChange(
                    feed_id=feed_id,
                    template_id=template_id,
                    change_type=change_type,
                    old_config=json.dumps(old_config) if old_config else None,
                    new_config=json.dumps(new_config) if new_config else None,
                    created_by=created_by
                )

                session.add(change)
                session.commit()

                logger.info(f"Logged configuration change: {change_type} "
                           f"(feed={feed_id}, template={template_id})")

        except Exception as e:
            logger.error(f"Failed to log configuration change: {e}")

    @staticmethod
    def _feed_to_dict(feed: Feed) -> Dict[str, Any]:
        """Convert feed to dictionary for logging"""
        return {
            'id': feed.id,
            'url': feed.url,
            'title': feed.title,
            'description': feed.description,
            'status': feed.status.value if feed.status else None,
            'fetch_interval_minutes': feed.fetch_interval_minutes,
            'last_fetched': feed.last_fetched.isoformat() if feed.last_fetched else None,
            'next_fetch_scheduled': feed.next_fetch_scheduled.isoformat() if feed.next_fetch_scheduled else None,
            'source_id': feed.source_id,
            'feed_type_id': feed.feed_type_id,
            'created_at': feed.created_at.isoformat() if feed.created_at else None,
            'updated_at': feed.updated_at.isoformat() if feed.updated_at else None
        }

    @staticmethod
    def _template_to_dict(template: DynamicFeedTemplate) -> Dict[str, Any]:
        """Convert template to dictionary for logging"""
        return {
            'id': template.id,
            'name': template.name,
            'description': template.description,
            'version': template.version,
            'url_patterns': template.url_pattern_list,
            'field_mappings': template.field_mapping_dict,
            'content_processing_rules': template.content_rules_list,
            'quality_filters': json.loads(template.quality_filters) if template.quality_filters else {},
            'categorization_rules': json.loads(template.categorization_rules) if template.categorization_rules else {},
            'fetch_settings': json.loads(template.fetch_settings) if template.fetch_settings else {},
            'is_active': template.is_active,
            'is_builtin': template.is_builtin,
            'created_by': template.created_by,
            'created_at': template.created_at.isoformat() if template.created_at else None,
            'updated_at': template.updated_at.isoformat() if template.updated_at else None
        }


# Context managers for tracking changes
class TrackFeedChanges:
    """Context manager for tracking feed changes automatically"""

    def __init__(self, session: Session, user: str = None):
        self.session = session
        self.user = user
        self.original_feeds: Dict[int, Dict[str, Any]] = {}

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:  # Only log if no exception occurred
            # Check for changes in tracked feeds
            for feed_id, old_data in self.original_feeds.items():
                feed = self.session.get(Feed, feed_id)
                if feed:
                    # Update configuration hash and log change
                    FeedChangeTracker.update_feed_configuration_hash(feed)
                    FeedChangeTracker.log_feed_updated(feed, old_data, self.user)

    def track_feed(self, feed: Feed):
        """Start tracking changes to a feed"""
        self.original_feeds[feed.id] = FeedChangeTracker._feed_to_dict(feed)

    def log_new_feed(self, feed: Feed):
        """Log a newly created feed"""
        FeedChangeTracker.update_feed_configuration_hash(feed)
        FeedChangeTracker.log_feed_created(feed, self.user)

    def log_deleted_feed(self, feed: Feed):
        """Log a deleted feed"""
        old_data = FeedChangeTracker._feed_to_dict(feed)
        FeedChangeTracker.log_feed_deleted(feed.id, old_data, self.user)


class TrackTemplateChanges:
    """Context manager for tracking template changes automatically"""

    def __init__(self, session: Session, user: str = None):
        self.session = session
        self.user = user
        self.original_templates: Dict[int, Dict[str, Any]] = {}

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:  # Only log if no exception occurred
            # Check for changes in tracked templates
            for template_id, old_data in self.original_templates.items():
                template = self.session.get(DynamicFeedTemplate, template_id)
                if template:
                    FeedChangeTracker.log_template_updated(template, old_data, self.user)

    def track_template(self, template: DynamicFeedTemplate):
        """Start tracking changes to a template"""
        self.original_templates[template.id] = FeedChangeTracker._template_to_dict(template)

    def log_new_template(self, template: DynamicFeedTemplate):
        """Log a newly created template"""
        FeedChangeTracker.log_template_created(template, self.user)

    def log_deleted_template(self, template: DynamicFeedTemplate):
        """Log a deleted template"""
        old_data = FeedChangeTracker._template_to_dict(template)
        FeedChangeTracker.log_template_deleted(template.id, old_data, self.user)


# Convenience functions
def track_feed_changes(session: Session, user: str = None) -> TrackFeedChanges:
    """Create a feed change tracking context"""
    return TrackFeedChanges(session, user)

def track_template_changes(session: Session, user: str = None) -> TrackTemplateChanges:
    """Create a template change tracking context"""
    return TrackTemplateChanges(session, user)