"""Processor-related models for the News MCP application."""

from typing import Optional, List, Dict, Any, TYPE_CHECKING
from datetime import datetime
import json

from .base import BaseTableModel, ProcessorType

if TYPE_CHECKING:
    from .feeds import Feed


class FeedProcessorConfig(BaseTableModel, table=True):
    """Configuration for feed-specific processors."""
    __tablename__ = "feed_processor_configs"

    feed_id: int = BaseTableModel.Field(foreign_key="feeds.id", unique=True)
    processor_type: ProcessorType = BaseTableModel.Field(default=ProcessorType.UNIVERSAL)
    config_json: str = BaseTableModel.Field(default="{}")  # JSON string for flexibility
    is_active: bool = BaseTableModel.Field(default=True)

    # Relationships
    feed: "Feed" = BaseTableModel.Relationship(back_populates="processor_config")

    @property
    def config(self) -> Dict[str, Any]:
        """Parse JSON config to dict."""
        try:
            return json.loads(self.config_json)
        except json.JSONDecodeError:
            return {}

    @config.setter
    def config(self, value: Dict[str, Any]):
        """Set config from dict."""
        self.config_json = json.dumps(value)


class ProcessorTemplate(BaseTableModel, table=True):
    """Template configuration for processors."""
    __tablename__ = "processor_templates"

    name: str = BaseTableModel.Field(unique=True, index=True)
    processor_type: ProcessorType
    description: Optional[str] = None
    config_json: str = BaseTableModel.Field(default="{}")
    url_patterns: str = BaseTableModel.Field(default="[]")  # JSON array of URL regex patterns
    is_builtin: bool = BaseTableModel.Field(default=False)
    is_active: bool = BaseTableModel.Field(default=True)

    @property
    def config(self) -> Dict[str, Any]:
        """Parse JSON config to dict."""
        try:
            return json.loads(self.config_json)
        except json.JSONDecodeError:
            return {}

    @config.setter
    def config(self, value: Dict[str, Any]):
        """Set config from dict."""
        self.config_json = json.dumps(value)

    @property
    def patterns(self) -> List[str]:
        """Parse JSON patterns to list."""
        try:
            return json.loads(self.url_patterns)
        except json.JSONDecodeError:
            return []

    @patterns.setter
    def patterns(self, value: List[str]):
        """Set patterns from list."""
        self.url_patterns = json.dumps(value)


class DynamicFeedTemplate(BaseTableModel, table=True):
    """Database-stored feed templates replacing YAML files."""
    __tablename__ = "dynamic_feed_templates"

    name: str = BaseTableModel.Field(unique=True, index=True)
    description: Optional[str] = None
    version: str = BaseTableModel.Field(default="1.0")

    # URL patterns for auto-assignment (JSON array)
    url_patterns: str = BaseTableModel.Field(default="[]")  # JSON array of regex patterns

    # Template configuration (JSON objects)
    field_mappings: str = BaseTableModel.Field(default="{}")  # RSS field -> DB field mapping
    content_processing_rules: str = BaseTableModel.Field(default="[]")  # Content processing steps
    quality_filters: str = BaseTableModel.Field(default="{}")  # Quality filter rules
    categorization_rules: str = BaseTableModel.Field(default="{}")  # Auto-categorization rules
    fetch_settings: str = BaseTableModel.Field(default="{}")  # Fetch configuration

    # Metadata
    is_builtin: bool = BaseTableModel.Field(default=False)
    is_active: bool = BaseTableModel.Field(default=True)
    created_by: Optional[str] = None

    # Usage tracking (exists in DB, needed for operations)
    last_used: Optional[datetime] = None
    usage_count: int = BaseTableModel.Field(default=0)

    # JSON property helpers
    @property
    def url_pattern_list(self) -> List[str]:
        """Parse URL patterns from JSON."""
        try:
            return json.loads(self.url_patterns)
        except json.JSONDecodeError:
            return []

    @url_pattern_list.setter
    def url_pattern_list(self, value: List[str]):
        """Set URL patterns as JSON."""
        self.url_patterns = json.dumps(value)

    @property
    def field_mapping_dict(self) -> Dict[str, str]:
        """Parse field mappings from JSON."""
        try:
            return json.loads(self.field_mappings)
        except json.JSONDecodeError:
            return {}

    @field_mapping_dict.setter
    def field_mapping_dict(self, value: Dict[str, str]):
        """Set field mappings as JSON."""
        self.field_mappings = json.dumps(value)

    @property
    def processing_rules_list(self) -> List[Dict[str, Any]]:
        """Parse processing rules from JSON."""
        try:
            return json.loads(self.content_processing_rules)
        except json.JSONDecodeError:
            return []

    @processing_rules_list.setter
    def processing_rules_list(self, value: List[Dict[str, Any]]):
        """Set processing rules as JSON."""
        self.content_processing_rules = json.dumps(value)

    @property
    def quality_filter_dict(self) -> Dict[str, Any]:
        """Parse quality filters from JSON."""
        try:
            return json.loads(self.quality_filters)
        except json.JSONDecodeError:
            return {}

    @quality_filter_dict.setter
    def quality_filter_dict(self, value: Dict[str, Any]):
        """Set quality filters as JSON."""
        self.quality_filters = json.dumps(value)

    @property
    def categorization_dict(self) -> Dict[str, Any]:
        """Parse categorization rules from JSON."""
        try:
            return json.loads(self.categorization_rules)
        except json.JSONDecodeError:
            return {}

    @categorization_dict.setter
    def categorization_dict(self, value: Dict[str, Any]):
        """Set categorization rules as JSON."""
        self.categorization_rules = json.dumps(value)

    @property
    def fetch_settings_dict(self) -> Dict[str, Any]:
        """Parse fetch settings from JSON."""
        try:
            return json.loads(self.fetch_settings)
        except json.JSONDecodeError:
            return {}

    @fetch_settings_dict.setter
    def fetch_settings_dict(self, value: Dict[str, Any]):
        """Set fetch settings as JSON."""
        self.fetch_settings = json.dumps(value)