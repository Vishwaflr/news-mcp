"""
Configuration Change Detection System

Detects changes to feed configurations and templates,
notifies the scheduler for hot-reloading of feed configurations.
"""
import logging
import hashlib
import json
from typing import Dict, List, Any, Optional, Set
from datetime import datetime, timedelta
from sqlmodel import Session, select

from ..models import (
    Feed, DynamicFeedTemplate, FeedTemplateAssignment,
    FeedConfigurationChange, FeedSchedulerState
)
from ..database import engine

logger = logging.getLogger(__name__)

class ConfigurationChange:
    """Represents a configuration change event"""

    def __init__(self, change_type: str, feed_id: Optional[int] = None,
                 template_id: Optional[int] = None, old_config: Dict = None,
                 new_config: Dict = None, timestamp: datetime = None):
        self.change_type = change_type
        self.feed_id = feed_id
        self.template_id = template_id
        self.old_config = old_config or {}
        self.new_config = new_config or {}
        self.timestamp = timestamp or datetime.utcnow()

    def __repr__(self):
        return f"ConfigurationChange({self.change_type}, feed={self.feed_id}, template={self.template_id})"


class ConfigurationWatcher:
    """Watches for configuration changes and notifies scheduler"""

    def __init__(self, session: Optional[Session] = None, scheduler_instance: str = "default"):
        self.session = session
        self._should_close_session = session is None
        self.scheduler_instance = scheduler_instance

    def __enter__(self):
        if self.session is None:
            self.session = Session(engine)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._should_close_session and self.session:
            self.session.close()

    def detect_changes_since_last_check(self) -> List[ConfigurationChange]:
        """Detect all changes since the last scheduler check"""
        scheduler_state = self._get_or_create_scheduler_state()
        last_check = scheduler_state.last_config_check or datetime.min

        # Get unprocessed configuration changes
        unprocessed_changes = self.session.exec(
            select(FeedConfigurationChange)
            .where(
                FeedConfigurationChange.created_at > last_check,
                FeedConfigurationChange.applied_at.is_(None)
            )
            .order_by(FeedConfigurationChange.created_at.asc())
        ).all()

        changes = []
        for change_record in unprocessed_changes:
            change = ConfigurationChange(
                change_type=change_record.change_type,
                feed_id=change_record.feed_id,
                template_id=change_record.template_id,
                old_config=change_record.old_config_dict,
                new_config=change_record.new_config_dict,
                timestamp=change_record.created_at
            )
            changes.append(change)

        # Update scheduler state
        scheduler_state.last_config_check = datetime.utcnow()
        scheduler_state.last_heartbeat = datetime.utcnow()
        self.session.add(scheduler_state)
        self.session.commit()

        logger.info(f"Detected {len(changes)} configuration changes since last check")
        return changes

    def detect_configuration_drift(self) -> Dict[str, Any]:
        """Detect configuration drift by comparing current state with stored hashes"""
        scheduler_state = self._get_or_create_scheduler_state()

        # Calculate current configuration hashes
        current_feed_hash = self._calculate_feed_config_hash()
        current_template_hash = self._calculate_template_config_hash()

        drift_detected = {
            'feed_config_changed': current_feed_hash != scheduler_state.last_feed_config_hash,
            'template_config_changed': current_template_hash != scheduler_state.last_template_config_hash,
            'current_feed_hash': current_feed_hash,
            'current_template_hash': current_template_hash,
            'stored_feed_hash': scheduler_state.last_feed_config_hash,
            'stored_template_hash': scheduler_state.last_template_config_hash
        }

        # Update stored hashes if changed
        if drift_detected['feed_config_changed'] or drift_detected['template_config_changed']:
            scheduler_state.last_feed_config_hash = current_feed_hash
            scheduler_state.last_template_config_hash = current_template_hash
            scheduler_state.updated_at = datetime.utcnow()
            self.session.add(scheduler_state)
            self.session.commit()

            logger.warning(f"Configuration drift detected: {drift_detected}")

        return drift_detected

    def get_feeds_requiring_schedule_update(self) -> List[Dict[str, Any]]:
        """Get feeds that need their schedule updated"""
        changes = self.detect_changes_since_last_check()

        feeds_to_update = []
        processed_feed_ids: Set[int] = set()

        for change in changes:
            if change.feed_id and change.feed_id not in processed_feed_ids:
                feed = self.session.get(Feed, change.feed_id)
                if feed:
                    feeds_to_update.append({
                        'feed_id': feed.id,
                        'feed_title': feed.title,
                        'old_interval': change.old_config.get('fetch_interval_minutes'),
                        'new_interval': feed.fetch_interval_minutes,
                        'change_type': change.change_type,
                        'url': feed.url,
                        'status': feed.status
                    })
                    processed_feed_ids.add(change.feed_id)

        return feeds_to_update

    def get_new_feeds_to_schedule(self) -> List[Dict[str, Any]]:
        """Get newly created feeds that need to be scheduled"""
        changes = self.detect_changes_since_last_check()

        new_feeds = []
        for change in changes:
            if change.change_type == 'feed_created' and change.feed_id:
                feed = self.session.get(Feed, change.feed_id)
                if feed:
                    new_feeds.append({
                        'feed_id': feed.id,
                        'feed_title': feed.title,
                        'url': feed.url,
                        'interval_minutes': feed.fetch_interval_minutes,
                        'status': feed.status
                    })

        return new_feeds

    def get_deleted_feeds_to_unschedule(self) -> List[int]:
        """Get deleted feeds that need to be unscheduled"""
        changes = self.detect_changes_since_last_check()

        deleted_feed_ids = []
        for change in changes:
            if change.change_type == 'feed_deleted' and change.feed_id:
                deleted_feed_ids.append(change.feed_id)

        return deleted_feed_ids

    def get_template_changes_affecting_feeds(self) -> Dict[int, List[Dict[str, Any]]]:
        """Get template changes and the feeds they affect"""
        changes = self.detect_changes_since_last_check()

        affected_feeds = {}

        for change in changes:
            if change.change_type in ['template_updated', 'feed_template_assigned', 'feed_template_unassigned']:
                if change.template_id:
                    # Find all feeds using this template
                    assignments = self.session.exec(
                        select(FeedTemplateAssignment)
                        .where(
                            FeedTemplateAssignment.template_id == change.template_id,
                            FeedTemplateAssignment.is_active == True
                        )
                    ).all()

                    for assignment in assignments:
                        feed_id = assignment.feed_id
                        if feed_id not in affected_feeds:
                            affected_feeds[feed_id] = []

                        affected_feeds[feed_id].append({
                            'change_type': change.change_type,
                            'template_id': change.template_id,
                            'old_config': change.old_config,
                            'new_config': change.new_config
                        })

        return affected_feeds

    def mark_changes_as_applied(self, change_ids: List[int] = None):
        """Mark configuration changes as applied by the scheduler"""
        if change_ids:
            # Mark specific changes as applied
            changes = self.session.exec(
                select(FeedConfigurationChange)
                .where(FeedConfigurationChange.id.in_(change_ids))
            ).all()
        else:
            # Mark all unprocessed changes as applied
            scheduler_state = self._get_or_create_scheduler_state()
            last_check = scheduler_state.last_config_check or datetime.min

            changes = self.session.exec(
                select(FeedConfigurationChange)
                .where(
                    FeedConfigurationChange.created_at <= last_check,
                    FeedConfigurationChange.applied_at.is_(None)
                )
            ).all()

        applied_count = 0
        for change in changes:
            change.applied_at = datetime.utcnow()
            self.session.add(change)
            applied_count += 1

        self.session.commit()
        logger.info(f"Marked {applied_count} configuration changes as applied")
        return applied_count

    def cleanup_old_changes(self, days_to_keep: int = 30):
        """Clean up old configuration change records"""
        cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)

        old_changes = self.session.exec(
            select(FeedConfigurationChange)
            .where(
                FeedConfigurationChange.created_at < cutoff_date,
                FeedConfigurationChange.applied_at.is_not(None)
            )
        ).all()

        deleted_count = 0
        for change in old_changes:
            self.session.delete(change)
            deleted_count += 1

        self.session.commit()
        logger.info(f"Cleaned up {deleted_count} old configuration changes")
        return deleted_count

    def get_configuration_summary(self) -> Dict[str, Any]:
        """Get a summary of current configuration state"""
        with Session(engine) as session:
            feed_count = len(session.exec(select(Feed)).all())
            template_count = len(session.exec(select(DynamicFeedTemplate)).all())
            assignment_count = len(session.exec(
                select(FeedTemplateAssignment)
                .where(FeedTemplateAssignment.is_active == True)
            ).all())

            unprocessed_changes = len(session.exec(
                select(FeedConfigurationChange)
                .where(FeedConfigurationChange.applied_at.is_(None))
            ).all())

            scheduler_state = self._get_or_create_scheduler_state()

            return {
                'feeds': feed_count,
                'templates': template_count,
                'active_assignments': assignment_count,
                'unprocessed_changes': unprocessed_changes,
                'scheduler_instance': self.scheduler_instance,
                'scheduler_active': scheduler_state.is_active,
                'last_config_check': scheduler_state.last_config_check,
                'last_heartbeat': scheduler_state.last_heartbeat,
                'feed_config_hash': scheduler_state.last_feed_config_hash,
                'template_config_hash': scheduler_state.last_template_config_hash
            }

    def _get_or_create_scheduler_state(self) -> FeedSchedulerState:
        """Get or create scheduler state record"""
        state = self.session.exec(
            select(FeedSchedulerState)
            .where(FeedSchedulerState.scheduler_instance == self.scheduler_instance)
        ).first()

        if not state:
            state = FeedSchedulerState(
                scheduler_instance=self.scheduler_instance,
                started_at=datetime.utcnow(),
                last_heartbeat=datetime.utcnow()
            )
            self.session.add(state)
            self.session.commit()
            self.session.refresh(state)

        return state

    def _calculate_feed_config_hash(self) -> str:
        """Calculate hash of all feed configurations"""
        feeds = self.session.exec(select(Feed).order_by(Feed.id)).all()

        config_data = []
        for feed in feeds:
            config_data.append({
                'id': feed.id,
                'url': feed.url,
                'status': feed.status.value,
                'fetch_interval_minutes': feed.fetch_interval_minutes,
                'updated_at': feed.updated_at.isoformat() if feed.updated_at else None
            })

        config_json = json.dumps(config_data, sort_keys=True)
        return hashlib.sha256(config_json.encode()).hexdigest()

    def _calculate_template_config_hash(self) -> str:
        """Calculate hash of all template configurations"""
        templates = self.session.exec(
            select(DynamicFeedTemplate).order_by(DynamicFeedTemplate.id)
        ).all()

        assignments = self.session.exec(
            select(FeedTemplateAssignment)
            .where(FeedTemplateAssignment.is_active == True)
            .order_by(FeedTemplateAssignment.id)
        ).all()

        config_data = {
            'templates': [],
            'assignments': []
        }

        for template in templates:
            config_data['templates'].append({
                'id': template.id,
                'name': template.name,
                'url_patterns': template.url_pattern_list,
                'field_mappings': template.field_mapping_dict,
                'content_rules': template.content_rules_list,
                'updated_at': template.updated_at.isoformat() if template.updated_at else None
            })

        for assignment in assignments:
            config_data['assignments'].append({
                'feed_id': assignment.feed_id,
                'template_id': assignment.template_id,
                'priority': assignment.priority,
                'custom_overrides': assignment.override_dict,
                'updated_at': assignment.updated_at.isoformat() if assignment.updated_at else None
            })

        config_json = json.dumps(config_data, sort_keys=True)
        return hashlib.sha256(config_json.encode()).hexdigest()


# Convenience functions
def get_configuration_watcher(session: Session = None, scheduler_instance: str = "default") -> ConfigurationWatcher:
    """Get a configuration watcher instance"""
    return ConfigurationWatcher(session, scheduler_instance)


def check_for_configuration_changes(scheduler_instance: str = "default") -> Dict[str, Any]:
    """Quick check for configuration changes - used by scheduler"""
    with get_configuration_watcher(scheduler_instance=scheduler_instance) as watcher:
        changes = watcher.detect_changes_since_last_check()

        return {
            'has_changes': len(changes) > 0,
            'change_count': len(changes),
            'changes': [
                {
                    'type': change.change_type,
                    'feed_id': change.feed_id,
                    'template_id': change.template_id,
                    'timestamp': change.timestamp.isoformat()
                }
                for change in changes
            ],
            'feeds_to_update': watcher.get_feeds_requiring_schedule_update(),
            'new_feeds': watcher.get_new_feeds_to_schedule(),
            'deleted_feeds': watcher.get_deleted_feeds_to_unschedule(),
            'template_changes': watcher.get_template_changes_affecting_feeds()
        }


def get_configuration_status(scheduler_instance: str = "default") -> Dict[str, Any]:
    """Get current configuration status - used for monitoring"""
    with get_configuration_watcher(scheduler_instance=scheduler_instance) as watcher:
        summary = watcher.get_configuration_summary()
        drift = watcher.detect_configuration_drift()

        return {
            **summary,
            'configuration_drift': drift
        }