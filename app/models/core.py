"""Core models for the News MCP application - Feed, Item, FetchLog."""

from typing import Optional, List, TYPE_CHECKING
from datetime import datetime
from sqlmodel import SQLModel, Field, Relationship

from .base import FeedStatus

if TYPE_CHECKING:
    from .feeds import Source, FeedType, FeedHealth
    from .content import ItemTag
    from .processors import FeedProcessorConfig
    from .configuration import FeedTemplateAssignment, FeedConfigurationChange


class Feed(SQLModel, table=True):
    """Main feed model."""
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
    auto_analyze_enabled: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Analytics columns (Phase 1.1)
    health_score: Optional[int] = Field(default=50)
    last_error_message: Optional[str] = None
    last_error_at: Optional[datetime] = None
    total_articles: int = Field(default=0)
    articles_24h: int = Field(default=0)
    analyzed_count: int = Field(default=0)
    analyzed_percentage: float = Field(default=0.0)
    source_label: Optional[str] = None
    latest_article_at: Optional[datetime] = None  # Date of latest article (for health checks)

    # Lifecycle columns (Phase 2)
    archived_at: Optional[datetime] = None
    is_critical: bool = Field(default=False)

    # Relationships
    source: "Source" = Relationship(back_populates="feeds")
    feed_type: Optional["FeedType"] = Relationship(back_populates="feeds")
    items: List["Item"] = Relationship(back_populates="feed")
    fetch_logs: List["FetchLog"] = Relationship(back_populates="feed")
    health: Optional["FeedHealth"] = Relationship(back_populates="feed", sa_relationship_kwargs={"uselist": False})
    processor_config: Optional["FeedProcessorConfig"] = Relationship(sa_relationship_kwargs={"uselist": False})
    template_assignments: List["FeedTemplateAssignment"] = Relationship(back_populates="feed")
    configuration_changes: List["FeedConfigurationChange"] = Relationship(back_populates="feed")


class Item(SQLModel, table=True):
    """News item/article model - append-only table."""
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
    # No updated_at - items are immutable once created

    # Relationships
    feed: Feed = Relationship(back_populates="items")
    tags: List["ItemTag"] = Relationship(back_populates="item")


class FetchLog(SQLModel, table=True):
    """Log of feed fetch operations - uses custom timestamps."""
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
    # No created_at/updated_at - uses started_at/completed_at instead

    # Relationships
    feed: Feed = Relationship(back_populates="fetch_logs")