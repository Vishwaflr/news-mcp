from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
import json

class SourceType(str, Enum):
    RSS = "rss"
    API = "api"
    MANUAL = "manual"

class FeedStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"

class ProcessorType(str, Enum):
    UNIVERSAL = "universal"
    HEISE = "heise"
    COINTELEGRAPH = "cointelegraph"
    CUSTOM = "custom"

class ProcessingStatus(str, Enum):
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"
    SKIPPED = "skipped"

class Source(SQLModel, table=True):
    __tablename__ = "sources"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    type: SourceType
    description: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    feeds: List["Feed"] = Relationship(back_populates="source")

class Category(SQLModel, table=True):
    __tablename__ = "categories"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(unique=True, index=True)
    description: Optional[str] = None
    color: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

class FeedType(SQLModel, table=True):
    __tablename__ = "feed_types"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(unique=True, index=True)
    default_interval_minutes: int
    description: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    feeds: List["Feed"] = Relationship(back_populates="feed_type")

class FeedCategory(SQLModel, table=True):
    __tablename__ = "feed_categories"

    feed_id: int = Field(foreign_key="feeds.id", primary_key=True)
    category_id: int = Field(foreign_key="categories.id", primary_key=True)

class Feed(SQLModel, table=True):
    __tablename__ = "feeds"

    id: Optional[int] = Field(default=None, primary_key=True)
    url: str = Field(unique=True, index=True)
    title: Optional[str] = None
    description: Optional[str] = None
    status: FeedStatus = Field(default=FeedStatus.ACTIVE)
    fetch_interval_minutes: int = Field(default=60)
    last_fetched: Optional[datetime] = None
    next_fetch_scheduled: Optional[datetime] = None
    last_modified: Optional[str] = None
    etag: Optional[str] = None
    configuration_hash: Optional[str] = None  # For change detection
    source_id: int = Field(foreign_key="sources.id")
    feed_type_id: Optional[int] = Field(default=None, foreign_key="feed_types.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    source: Source = Relationship(back_populates="feeds")
    feed_type: Optional[FeedType] = Relationship(back_populates="feeds")
    items: List["Item"] = Relationship(back_populates="feed")
    fetch_logs: List["FetchLog"] = Relationship(back_populates="feed")
    health: Optional["FeedHealth"] = Relationship(back_populates="feed", sa_relationship_kwargs={"uselist": False})
    processor_config: Optional["FeedProcessorConfig"] = Relationship(sa_relationship_kwargs={"uselist": False})
    template_assignments: List["FeedTemplateAssignment"] = Relationship(back_populates="feed")
    configuration_changes: List["FeedConfigurationChange"] = Relationship(back_populates="feed")

class Item(SQLModel, table=True):
    __tablename__ = "items"

    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    link: str = Field(index=True)
    description: Optional[str] = None
    content: Optional[str] = None
    author: Optional[str] = None
    published: Optional[datetime] = None
    guid: Optional[str] = Field(index=True)
    content_hash: str = Field(unique=True, index=True)
    feed_id: int = Field(foreign_key="feeds.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)

    feed: Feed = Relationship(back_populates="items")
    tags: List["ItemTag"] = Relationship(back_populates="item")

class FetchLog(SQLModel, table=True):
    __tablename__ = "fetch_log"

    id: Optional[int] = Field(default=None, primary_key=True)
    feed_id: int = Field(foreign_key="feeds.id")
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    status: str
    items_found: int = Field(default=0)
    items_new: int = Field(default=0)
    error_message: Optional[str] = None
    response_time_ms: Optional[int] = None

    feed: Feed = Relationship(back_populates="fetch_logs")

class FeedHealth(SQLModel, table=True):
    __tablename__ = "feed_health"

    id: Optional[int] = Field(default=None, primary_key=True)
    feed_id: int = Field(foreign_key="feeds.id", unique=True)
    ok_ratio: float = Field(default=1.0)
    consecutive_failures: int = Field(default=0)
    avg_response_time_ms: Optional[float] = None
    last_success: Optional[datetime] = None
    last_failure: Optional[datetime] = None
    uptime_24h: float = Field(default=1.0)
    uptime_7d: float = Field(default=1.0)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    feed: Feed = Relationship(back_populates="health")

class ItemTag(SQLModel, table=True):
    __tablename__ = "item_tags"

    id: Optional[int] = Field(default=None, primary_key=True)
    item_id: int = Field(foreign_key="items.id")
    tag: str = Field(index=True)

    item: Item = Relationship(back_populates="tags")

class FeedProcessorConfig(SQLModel, table=True):
    __tablename__ = "feed_processor_configs"

    id: Optional[int] = Field(default=None, primary_key=True)
    feed_id: int = Field(foreign_key="feeds.id", unique=True)
    processor_type: ProcessorType = Field(default=ProcessorType.UNIVERSAL)
    config_json: str = Field(default="{}")  # JSON string for flexibility
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    feed: "Feed" = Relationship(back_populates="processor_config")

    @property
    def config(self) -> Dict[str, Any]:
        """Parse JSON config to dict"""
        try:
            return json.loads(self.config_json)
        except json.JSONDecodeError:
            return {}

    @config.setter
    def config(self, value: Dict[str, Any]):
        """Set config from dict"""
        self.config_json = json.dumps(value)

class ContentProcessingLog(SQLModel, table=True):
    __tablename__ = "content_processing_logs"

    id: Optional[int] = Field(default=None, primary_key=True)
    item_id: int = Field(foreign_key="items.id", index=True)
    feed_id: int = Field(foreign_key="feeds.id", index=True)
    processor_type: ProcessorType
    processing_status: ProcessingStatus
    original_title: Optional[str] = None
    processed_title: Optional[str] = None
    original_description: Optional[str] = None
    processed_description: Optional[str] = None
    transformations_applied: str = Field(default="[]")  # JSON array of transformation names
    error_message: Optional[str] = None
    processing_time_ms: Optional[int] = None
    processed_at: datetime = Field(default_factory=datetime.utcnow)

    item: Item = Relationship()
    feed: "Feed" = Relationship()

    @property
    def transformations(self) -> List[str]:
        """Parse JSON transformations to list"""
        try:
            return json.loads(self.transformations_applied)
        except json.JSONDecodeError:
            return []

    @transformations.setter
    def transformations(self, value: List[str]):
        """Set transformations from list"""
        self.transformations_applied = json.dumps(value)

class ProcessorTemplate(SQLModel, table=True):
    __tablename__ = "processor_templates"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(unique=True, index=True)
    processor_type: ProcessorType
    description: Optional[str] = None
    config_json: str = Field(default="{}")
    url_patterns: str = Field(default="[]")  # JSON array of URL regex patterns
    is_builtin: bool = Field(default=False)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    @property
    def config(self) -> Dict[str, Any]:
        """Parse JSON config to dict"""
        try:
            return json.loads(self.config_json)
        except json.JSONDecodeError:
            return {}

    @config.setter
    def config(self, value: Dict[str, Any]):
        """Set config from dict"""
        self.config_json = json.dumps(value)

    @property
    def patterns(self) -> List[str]:
        """Parse JSON patterns to list"""
        try:
            return json.loads(self.url_patterns)
        except json.JSONDecodeError:
            return []

    @patterns.setter
    def patterns(self, value: List[str]):
        """Set patterns from list"""
        self.url_patterns = json.dumps(value)

class DynamicFeedTemplate(SQLModel, table=True):
    """Database-stored feed templates replacing YAML files"""
    __tablename__ = "dynamic_feed_templates"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(unique=True, index=True)
    description: Optional[str] = None
    version: str = Field(default="1.0")

    # URL patterns for auto-assignment (JSON array)
    url_patterns: str = Field(default="[]")  # JSON array of regex patterns

    # Template configuration (JSON objects)
    field_mappings: str = Field(default="{}")  # RSS field -> DB field mapping
    content_processing_rules: str = Field(default="[]")  # Content processing steps
    quality_filters: str = Field(default="{}")  # Quality filter rules
    categorization_rules: str = Field(default="{}")  # Auto-categorization rules
    fetch_settings: str = Field(default="{}")  # Fetch configuration

    # Metadata
    is_active: bool = Field(default=True)
    is_builtin: bool = Field(default=False)  # System templates vs user templates
    created_by: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    assignments: List["FeedTemplateAssignment"] = Relationship(back_populates="template")

    @property
    def url_pattern_list(self) -> List[str]:
        """Parse JSON URL patterns to list"""
        try:
            return json.loads(self.url_patterns)
        except json.JSONDecodeError:
            return []

    @url_pattern_list.setter
    def url_pattern_list(self, value: List[str]):
        """Set URL patterns from list"""
        self.url_patterns = json.dumps(value)

    @property
    def field_mapping_dict(self) -> Dict[str, Any]:
        """Parse JSON field mappings to dict"""
        try:
            return json.loads(self.field_mappings)
        except json.JSONDecodeError:
            return {}

    @field_mapping_dict.setter
    def field_mapping_dict(self, value: Dict[str, Any]):
        """Set field mappings from dict"""
        self.field_mappings = json.dumps(value)

    @property
    def content_rules_list(self) -> List[Dict[str, Any]]:
        """Parse JSON content processing rules to list"""
        try:
            return json.loads(self.content_processing_rules)
        except json.JSONDecodeError:
            return []

    @content_rules_list.setter
    def content_rules_list(self, value: List[Dict[str, Any]]):
        """Set content processing rules from list"""
        self.content_processing_rules = json.dumps(value)

class FeedTemplateAssignment(SQLModel, table=True):
    """Assignment of templates to feeds with custom overrides"""
    __tablename__ = "feed_template_assignments"

    id: Optional[int] = Field(default=None, primary_key=True)
    feed_id: int = Field(foreign_key="feeds.id", index=True)
    template_id: int = Field(foreign_key="dynamic_feed_templates.id", index=True)

    # Custom overrides specific to this feed (JSON)
    custom_overrides: str = Field(default="{}")  # Feed-specific template modifications

    # Assignment metadata
    is_active: bool = Field(default=True)
    priority: int = Field(default=100)  # Lower number = higher priority if multiple templates match
    assigned_by: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    feed: "Feed" = Relationship()
    template: DynamicFeedTemplate = Relationship(back_populates="assignments")

    @property
    def override_dict(self) -> Dict[str, Any]:
        """Parse JSON custom overrides to dict"""
        try:
            return json.loads(self.custom_overrides)
        except json.JSONDecodeError:
            return {}

    @override_dict.setter
    def override_dict(self, value: Dict[str, Any]):
        """Set custom overrides from dict"""
        self.custom_overrides = json.dumps(value)

class FeedConfigurationChange(SQLModel, table=True):
    """Track configuration changes for hot-reload detection"""
    __tablename__ = "feed_configuration_changes"

    id: Optional[int] = Field(default=None, primary_key=True)
    feed_id: Optional[int] = Field(foreign_key="feeds.id", index=True)
    template_id: Optional[int] = Field(foreign_key="dynamic_feed_templates.id", index=True)

    # Change details
    change_type: str = Field(index=True)  # 'feed_created', 'feed_updated', 'feed_deleted', 'template_updated'
    old_config: Optional[str] = None  # JSON snapshot before change
    new_config: Optional[str] = None  # JSON snapshot after change

    # Change metadata
    applied_at: Optional[datetime] = None  # When scheduler applied the change
    created_by: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    feed: Optional["Feed"] = Relationship()
    template: Optional[DynamicFeedTemplate] = Relationship()

    @property
    def old_config_dict(self) -> Dict[str, Any]:
        """Parse JSON old config to dict"""
        try:
            return json.loads(self.old_config) if self.old_config else {}
        except json.JSONDecodeError:
            return {}

    @property
    def new_config_dict(self) -> Dict[str, Any]:
        """Parse JSON new config to dict"""
        try:
            return json.loads(self.new_config) if self.new_config else {}
        except json.JSONDecodeError:
            return {}

class FeedSchedulerState(SQLModel, table=True):
    """Track scheduler state and configuration versions"""
    __tablename__ = "feed_scheduler_state"

    id: Optional[int] = Field(default=None, primary_key=True)
    scheduler_instance: str = Field(unique=True, index=True)  # Unique scheduler ID

    # State tracking
    last_config_check: Optional[datetime] = None
    last_feed_config_hash: Optional[str] = None  # Hash of all feed configurations
    last_template_config_hash: Optional[str] = None  # Hash of all template configurations

    # Scheduler metadata
    is_active: bool = Field(default=True)
    started_at: Optional[datetime] = None
    last_heartbeat: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)