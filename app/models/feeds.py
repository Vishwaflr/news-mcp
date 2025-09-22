"""Feed-related models for the News MCP application."""

from typing import Optional, List, TYPE_CHECKING
from datetime import datetime

from .base import BaseTableModel, SourceType, FeedStatus

if TYPE_CHECKING:
    from .content import Item
    from ..models import Feed, FetchLog
    from .processors import FeedProcessorConfig
    from .configuration import FeedTemplateAssignment, FeedConfigurationChange


class Source(BaseTableModel, table=True):
    """Source of feeds (RSS, API, manual)."""
    __tablename__ = "sources"

    name: str = BaseTableModel.Field(index=True)
    type: SourceType
    description: Optional[str] = None

    feeds: List["Feed"] = BaseTableModel.Relationship(back_populates="source")


class Category(BaseTableModel, table=True):
    """Category for organizing feeds."""
    __tablename__ = "categories"

    name: str = BaseTableModel.Field(unique=True, index=True)
    description: Optional[str] = None
    color: Optional[str] = None


class FeedType(BaseTableModel, table=True):
    """Type of feed with default settings."""
    __tablename__ = "feed_types"

    name: str = BaseTableModel.Field(unique=True, index=True)
    default_interval_minutes: int
    description: Optional[str] = None

    feeds: List["Feed"] = BaseTableModel.Relationship(back_populates="feed_type")


class FeedCategory(BaseTableModel, table=True):
    """Many-to-many relationship between feeds and categories."""
    __tablename__ = "feed_categories"

    feed_id: int = BaseTableModel.Field(foreign_key="feeds.id", primary_key=True)
    category_id: int = BaseTableModel.Field(foreign_key="categories.id", primary_key=True)


# Feed and FetchLog are now in models.py to avoid duplication
# They will be imported from app.models when needed by other modules


class FeedHealth(BaseTableModel, table=True):
    """Health metrics for feeds."""
    __tablename__ = "feed_health"

    feed_id: int = BaseTableModel.Field(foreign_key="feeds.id", unique=True)
    ok_ratio: float = BaseTableModel.Field(default=1.0)
    consecutive_failures: int = BaseTableModel.Field(default=0)
    avg_response_time_ms: Optional[float] = None
    last_success: Optional[datetime] = None
    last_failure: Optional[datetime] = None
    uptime_24h: float = BaseTableModel.Field(default=1.0)
    uptime_7d: float = BaseTableModel.Field(default=1.0)

    # Relationships
    feed: "Feed" = BaseTableModel.Relationship(back_populates="health")