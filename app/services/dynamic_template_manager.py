"""
Dynamic Template Manager Service

Manages database-stored feed templates and their assignments to feeds.
Replaces the static YAML-based template system with dynamic database configuration.
"""
import logging
import hashlib
import re
from typing import Dict, List, Any, Optional
from datetime import datetime
from sqlmodel import Session, select

from ..models import (
    Feed, DynamicFeedTemplate, FeedTemplateAssignment,
    FeedConfigurationChange
)
from ..database import engine
from .feed_change_tracker import FeedChangeTracker, track_template_changes

logger = logging.getLogger(__name__)

class DynamicTemplateManager:
    """Manages database-stored feed templates and assignments"""

    def __init__(self, session: Optional[Session] = None):
        self.session = session
        self._should_close_session = session is None

    def __enter__(self):
        if self.session is None:
            self.session = Session(engine)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._should_close_session and self.session:
            self.session.close()

    def create_template(self, name: str, description: str = None,
                       url_patterns: List[str] = None,
                       field_mappings: Dict[str, str] = None,
                       content_processing_rules: List[Dict[str, Any]] = None,
                       quality_filters: Dict[str, Any] = None,
                       categorization_rules: Dict[str, Any] = None,
                       fetch_settings: Dict[str, Any] = None,
                       created_by: str = None) -> DynamicFeedTemplate:
        """Create a new dynamic feed template"""

        template = DynamicFeedTemplate(
            name=name,
            description=description,
            created_by=created_by
        )

        # Set configuration using properties
        template.url_pattern_list = url_patterns or []
        template.field_mapping_dict = field_mappings or {}
        template.content_rules_list = content_processing_rules or []

        # Set JSON fields directly
        template.quality_filters = self._to_json(quality_filters or {})
        template.categorization_rules = self._to_json(categorization_rules or {})
        template.fetch_settings = self._to_json(fetch_settings or {})

        self.session.add(template)
        self.session.commit()
        self.session.refresh(template)

        # Log the template creation for change detection
        FeedChangeTracker.log_template_created(template, created_by)

        logger.info(f"Created dynamic template: {name} (ID: {template.id})")
        return template

    def update_template(self, template_id: int, updated_by: str = None, **kwargs) -> Optional[DynamicFeedTemplate]:
        """Update an existing template"""
        template = self.session.get(DynamicFeedTemplate, template_id)
        if not template:
            return None

        # Track old config for change detection
        old_config = self._template_to_config_dict(template)

        # Update fields
        for field, value in kwargs.items():
            if field == 'url_patterns':
                template.url_pattern_list = value
            elif field == 'field_mappings':
                template.field_mapping_dict = value
            elif field == 'content_processing_rules':
                template.content_rules_list = value
            elif hasattr(template, field):
                if field in ['quality_filters', 'categorization_rules', 'fetch_settings']:
                    setattr(template, field, self._to_json(value))
                else:
                    setattr(template, field, value)

        template.updated_at = datetime.utcnow()

        self.session.add(template)
        self.session.commit()

        # Log the template update for change detection
        FeedChangeTracker.log_template_updated(template, old_config, updated_by)

        logger.info(f"Updated template: {template.name} (ID: {template_id})")
        return template

    def delete_template(self, template_id: int) -> bool:
        """Delete a template and all its assignments"""
        template = self.session.get(DynamicFeedTemplate, template_id)
        if not template:
            return False

        # Remove all assignments first
        assignments = self.session.exec(
            select(FeedTemplateAssignment).where(
                FeedTemplateAssignment.template_id == template_id
            )
        ).all()

        for assignment in assignments:
            self.session.delete(assignment)

        # Log the template deletion before deleting
        old_config = self._template_to_config_dict(template)

        # Delete the template
        self.session.delete(template)
        self.session.commit()

        # Log the template deletion for change detection
        FeedChangeTracker.log_template_deleted(template_id, old_config)

        logger.info(f"Deleted template: {template.name} (ID: {template_id})")
        return True

    def assign_template_to_feed(self, feed_id: int, template_id: int,
                               custom_overrides: Dict[str, Any] = None,
                               priority: int = 100,
                               assigned_by: str = None) -> FeedTemplateAssignment:
        """Assign a template to a feed with optional custom overrides"""

        # Check if assignment already exists
        existing = self.session.exec(
            select(FeedTemplateAssignment).where(
                FeedTemplateAssignment.feed_id == feed_id,
                FeedTemplateAssignment.template_id == template_id,
                FeedTemplateAssignment.is_active == True
            )
        ).first()

        if existing:
            # Update existing assignment
            existing.custom_overrides = self._to_json(custom_overrides or {})
            existing.priority = priority
            existing.assigned_by = assigned_by
            existing.updated_at = datetime.utcnow()
            assignment = existing
        else:
            # Create new assignment
            assignment = FeedTemplateAssignment(
                feed_id=feed_id,
                template_id=template_id,
                custom_overrides=self._to_json(custom_overrides or {}),
                priority=priority,
                assigned_by=assigned_by
            )
            self.session.add(assignment)

        self.session.commit()
        self.session.refresh(assignment)

        # Log the template assignment for change detection
        FeedChangeTracker.log_template_assigned(feed_id, template_id, assigned_by)

        logger.info(f"Assigned template {template_id} to feed {feed_id}")
        return assignment

    def unassign_template_from_feed(self, feed_id: int, template_id: int) -> bool:
        """Remove template assignment from a feed"""
        assignment = self.session.exec(
            select(FeedTemplateAssignment).where(
                FeedTemplateAssignment.feed_id == feed_id,
                FeedTemplateAssignment.template_id == template_id,
                FeedTemplateAssignment.is_active == True
            )
        ).first()

        if not assignment:
            return False

        assignment.is_active = False
        assignment.updated_at = datetime.utcnow()

        self.session.add(assignment)
        self.session.commit()

        # Log the template unassignment for change detection
        FeedChangeTracker.log_template_unassigned(feed_id, template_id)

        logger.info(f"Unassigned template {template_id} from feed {feed_id}")
        return True

    def auto_assign_templates_to_feeds(self) -> int:
        """Auto-assign templates to feeds based on URL patterns"""
        feeds = self.session.exec(select(Feed)).all()
        templates = self.session.exec(
            select(DynamicFeedTemplate).where(DynamicFeedTemplate.is_active == True)
        ).all()

        assignments_made = 0

        for feed in feeds:
            for template in templates:
                if self._template_matches_feed_url(template, feed.url):
                    # Check if already assigned
                    existing = self.session.exec(
                        select(FeedTemplateAssignment).where(
                            FeedTemplateAssignment.feed_id == feed.id,
                            FeedTemplateAssignment.template_id == template.id,
                            FeedTemplateAssignment.is_active == True
                        )
                    ).first()

                    if not existing:
                        self.assign_template_to_feed(
                            feed.id, template.id,
                            assigned_by='auto_assignment'
                        )
                        assignments_made += 1

        logger.info(f"Auto-assigned {assignments_made} templates to feeds")
        return assignments_made

    def get_template_for_feed(self, feed_id: int) -> Optional[DynamicFeedTemplate]:
        """Get the best template for a feed (highest priority active assignment)"""
        assignment = self.session.exec(
            select(FeedTemplateAssignment)
            .join(DynamicFeedTemplate)
            .where(
                FeedTemplateAssignment.feed_id == feed_id,
                FeedTemplateAssignment.is_active == True,
                DynamicFeedTemplate.is_active == True
            )
            .order_by(FeedTemplateAssignment.priority.asc())
        ).first()

        return assignment.template if assignment else None

    def get_effective_template_config(self, feed_id: int) -> Optional[Dict[str, Any]]:
        """Get the effective template configuration for a feed (including overrides)"""
        assignment = self.session.exec(
            select(FeedTemplateAssignment)
            .join(DynamicFeedTemplate)
            .where(
                FeedTemplateAssignment.feed_id == feed_id,
                FeedTemplateAssignment.is_active == True,
                DynamicFeedTemplate.is_active == True
            )
            .order_by(FeedTemplateAssignment.priority.asc())
        ).first()

        if not assignment:
            return None

        template = assignment.template
        config = {
            'name': template.name,
            'version': template.version,
            'field_mappings': template.field_mapping_dict,
            'content_processing_rules': template.content_rules_list,
            'quality_filters': self._from_json(template.quality_filters),
            'categorization_rules': self._from_json(template.categorization_rules),
            'fetch_settings': self._from_json(template.fetch_settings)
        }

        # Apply custom overrides
        overrides = assignment.override_dict
        if overrides:
            config = self._merge_config_with_overrides(config, overrides)

        return config

    def get_active_template_for_feed(self, feed_id: int) -> Optional[DynamicFeedTemplate]:
        """Get the active template for a feed - alias for get_template_for_feed for compatibility"""
        return self.get_template_for_feed(feed_id)

    def create_builtin_templates(self):
        """Create built-in templates for common feed sources"""
        builtin_templates = [
            {
                'name': 'Heise Online',
                'description': 'Template für Heise.de RSS Feeds',
                'url_patterns': ['.*heise\\.de.*'],
                'field_mappings': {
                    'title': 'entry.title',
                    'description': 'entry.summary',
                    'link': 'entry.link',
                    'author': 'entry.author',
                    'published': 'entry.published_parsed',
                    'guid': 'entry.id'
                },
                'content_processing_rules': [
                    {'type': 'html_extract', 'max_length': 2000},
                    {'type': 'text_normalize', 'rules': ['fix_german_umlauts', 'normalize_quotes']}
                ],
                'categorization_rules': {
                    'default_category': 'Tech News',
                    'rules': [
                        {'if_title_contains': ['Security', 'Sicherheit'], 'then_category': 'Security'},
                        {'if_title_contains': ['KI', 'AI', 'Machine Learning'], 'then_category': 'AI/ML'}
                    ]
                },
                'quality_filters': {
                    'min_title_length': 10,
                    'max_title_length': 200
                }
            },
            {
                'name': 'Cointelegraph',
                'description': 'Template für Cointelegraph.com RSS Feeds',
                'url_patterns': ['.*cointelegraph\\.com.*'],
                'field_mappings': {
                    'title': 'entry.title',
                    'description': 'entry.summary',
                    'link': 'entry.link',
                    'author': 'entry.author',
                    'published': 'entry.published_parsed',
                    'guid': 'entry.id'
                },
                'content_processing_rules': [
                    {'type': 'html_extract', 'max_length': 1500},
                    {'type': 'remove_tracking'}
                ],
                'categorization_rules': {
                    'default_category': 'Crypto',
                    'rules': [
                        {'if_title_contains': ['Bitcoin', 'BTC'], 'then_category': 'Bitcoin'},
                        {'if_title_contains': ['Ethereum', 'ETH'], 'then_category': 'Ethereum'},
                        {'if_title_contains': ['DeFi'], 'then_category': 'DeFi'}
                    ]
                }
            },
            {
                'name': 'Wall Street Journal',
                'description': 'Template für WSJ RSS Feeds',
                'url_patterns': ['.*feeds\\.content\\.dowjones\\.io.*', '.*wsj\\.com.*'],
                'field_mappings': {
                    'title': 'entry.title',
                    'description': 'entry.summary',
                    'link': 'entry.link',
                    'author': 'entry.author',
                    'published': 'entry.published_parsed',
                    'guid': 'entry.id'
                },
                'content_processing_rules': [
                    {'type': 'html_extract', 'max_length': 2000}
                ],
                'categorization_rules': {
                    'default_category': 'Finance',
                    'rules': [
                        {'if_title_contains': ['Stock', 'Market', 'Trading'], 'then_category': 'Markets'},
                        {'if_title_contains': ['Bank', 'Banking'], 'then_category': 'Banking'},
                        {'if_title_contains': ['Crypto', 'Bitcoin'], 'then_category': 'Crypto'}
                    ]
                },
                'fetch_settings': {
                    'interval_minutes': 15
                }
            }
        ]

        created_count = 0
        for template_config in builtin_templates:
            # Check if template already exists
            existing = self.session.exec(
                select(DynamicFeedTemplate).where(
                    DynamicFeedTemplate.name == template_config['name']
                )
            ).first()

            if not existing:
                self.create_template(
                    **template_config,
                    created_by='system'
                )
                # Mark as builtin
                template = self.session.exec(
                    select(DynamicFeedTemplate).where(
                        DynamicFeedTemplate.name == template_config['name']
                    )
                ).first()
                template.is_builtin = True
                self.session.add(template)
                self.session.commit()
                created_count += 1

        logger.info(f"Created {created_count} built-in templates")
        return created_count

    def _template_matches_feed_url(self, template: DynamicFeedTemplate, url: str) -> bool:
        """Check if template URL patterns match the feed URL"""
        patterns = template.url_pattern_list
        for pattern in patterns:
            if re.search(pattern, url, re.IGNORECASE):
                return True
        return False

    def _template_to_config_dict(self, template: DynamicFeedTemplate) -> Dict[str, Any]:
        """Convert template to config dictionary for change tracking"""
        return {
            'name': template.name,
            'version': template.version,
            'url_patterns': template.url_pattern_list,
            'field_mappings': template.field_mapping_dict,
            'content_processing_rules': template.content_rules_list,
            'quality_filters': self._from_json(template.quality_filters),
            'categorization_rules': self._from_json(template.categorization_rules),
            'fetch_settings': self._from_json(template.fetch_settings),
            'updated_at': template.updated_at.isoformat() if template.updated_at else None
        }

    def _merge_config_with_overrides(self, base_config: Dict[str, Any],
                                   overrides: Dict[str, Any]) -> Dict[str, Any]:
        """Merge base template config with feed-specific overrides"""
        merged = base_config.copy()

        # Deep merge for nested dictionaries
        for key, value in overrides.items():
            if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
                merged[key] = {**merged[key], **value}
            else:
                merged[key] = value

        return merged

    def _log_configuration_change(self, change_type: str, feed_id: int = None,
                                 template_id: int = None, old_config: Dict[str, Any] = None,
                                 new_config: Dict[str, Any] = None):
        """Log configuration change for scheduler detection"""
        change = FeedConfigurationChange(
            feed_id=feed_id,
            template_id=template_id,
            change_type=change_type,
            old_config=self._to_json(old_config),
            new_config=self._to_json(new_config)
        )

        self.session.add(change)
        # Don't commit here - let the calling method handle the transaction

    def _to_json(self, obj: Any) -> str:
        """Convert object to JSON string"""
        import json
        return json.dumps(obj) if obj is not None else "{}"

    def _from_json(self, json_str: str) -> Any:
        """Parse JSON string to object"""
        import json
        try:
            return json.loads(json_str) if json_str else {}
        except json.JSONDecodeError:
            return {}


# Convenience functions
def get_dynamic_template_manager(session: Session = None) -> DynamicTemplateManager:
    """Get a template manager instance"""
    return DynamicTemplateManager(session)


def initialize_builtin_templates():
    """Initialize built-in templates - call this during app startup"""
    with get_dynamic_template_manager() as manager:
        return manager.create_builtin_templates()


def auto_assign_all_templates():
    """Auto-assign templates to all feeds - useful for migration"""
    with get_dynamic_template_manager() as manager:
        return manager.auto_assign_templates_to_feeds()