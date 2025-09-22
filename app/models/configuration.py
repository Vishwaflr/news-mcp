"""Configuration-related models for the News MCP application."""

from typing import Optional, Dict, Any, TYPE_CHECKING
from datetime import datetime
import json

from .base import BaseTableModel

if TYPE_CHECKING:
    from .feeds import Feed
    from .processors import DynamicFeedTemplate


class FeedTemplateAssignment(BaseTableModel, table=True):
    """Assignment of templates to feeds with custom overrides."""
    __tablename__ = "feed_template_assignments"

    feed_id: int = BaseTableModel.Field(foreign_key="feeds.id", index=True)
    template_id: int = BaseTableModel.Field(foreign_key="dynamic_feed_templates.id", index=True)

    # Custom overrides specific to this feed (JSON)
    custom_overrides: str = BaseTableModel.Field(default="{}")  # Feed-specific template modifications

    # Assignment metadata
    is_active: bool = BaseTableModel.Field(default=True)
    priority: int = BaseTableModel.Field(default=100)  # Lower number = higher priority if multiple templates match
    assigned_by: Optional[str] = None

    # Relationships
    feed: "Feed" = BaseTableModel.Relationship(back_populates="template_assignments")
    template: "DynamicFeedTemplate" = BaseTableModel.Relationship()

    @property
    def override_dict(self) -> Dict[str, Any]:
        """Parse JSON custom overrides to dict."""
        try:
            return json.loads(self.custom_overrides)
        except json.JSONDecodeError:
            return {}

    @override_dict.setter
    def override_dict(self, value: Dict[str, Any]):
        """Set custom overrides from dict."""
        self.custom_overrides = json.dumps(value)


class FeedConfigurationChange(BaseTableModel, table=True):
    """Track configuration changes for hot-reload detection."""
    __tablename__ = "feed_configuration_changes"

    feed_id: Optional[int] = BaseTableModel.Field(foreign_key="feeds.id", index=True)
    template_id: Optional[int] = BaseTableModel.Field(foreign_key="dynamic_feed_templates.id", index=True)

    # Change details
    change_type: str = BaseTableModel.Field(index=True)  # 'feed_created', 'feed_updated', 'feed_deleted', 'template_updated'
    old_config: Optional[str] = None  # JSON snapshot before change
    new_config: Optional[str] = None  # JSON snapshot after change

    # Change metadata
    applied_at: Optional[datetime] = None  # When scheduler applied the change
    created_by: Optional[str] = None

    # Relationships
    feed: Optional["Feed"] = BaseTableModel.Relationship(back_populates="configuration_changes")
    template: Optional["DynamicFeedTemplate"] = BaseTableModel.Relationship()

    @property
    def old_config_dict(self) -> Dict[str, Any]:
        """Parse JSON old config to dict."""
        try:
            return json.loads(self.old_config) if self.old_config else {}
        except json.JSONDecodeError:
            return {}

    @property
    def new_config_dict(self) -> Dict[str, Any]:
        """Parse JSON new config to dict."""
        try:
            return json.loads(self.new_config) if self.new_config else {}
        except json.JSONDecodeError:
            return {}


class FeedSchedulerState(BaseTableModel, table=True):
    """Track scheduler state and configuration versions."""
    __tablename__ = "feed_scheduler_state"

    scheduler_instance: str = BaseTableModel.Field(unique=True, index=True)  # Unique scheduler ID

    # State tracking
    last_config_check: Optional[datetime] = None
    last_feed_config_hash: Optional[str] = None  # Hash of all feed configurations
    last_template_config_hash: Optional[str] = None  # Hash of all template configurations

    # Scheduler metadata
    is_active: bool = BaseTableModel.Field(default=True)
    started_at: Optional[datetime] = None
    last_heartbeat: Optional[datetime] = None