"""Content-related models for the News MCP application."""

from typing import Optional, List, TYPE_CHECKING
from datetime import datetime
import json

from .base import BaseTableModel, ProcessorType, ProcessingStatus

# Import Item from main models.py - will be defined there
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..models import Item

if TYPE_CHECKING:
    from .feeds import Feed


class ItemTag(BaseTableModel, table=True):
    """Tags associated with news items."""
    __tablename__ = "item_tags"

    item_id: int = BaseTableModel.Field(foreign_key="items.id")
    tag: str = BaseTableModel.Field(index=True)

    # Relationships
    item: "Item" = BaseTableModel.Relationship(back_populates="tags")


class ContentProcessingLog(BaseTableModel, table=True):
    """Log of content processing operations."""
    __tablename__ = "content_processing_logs"

    item_id: int = BaseTableModel.Field(foreign_key="items.id", index=True)
    feed_id: int = BaseTableModel.Field(foreign_key="feeds.id", index=True)
    processor_type: ProcessorType
    processing_status: ProcessingStatus
    original_title: Optional[str] = None
    processed_title: Optional[str] = None
    original_description: Optional[str] = None
    processed_description: Optional[str] = None
    transformations_applied: str = BaseTableModel.Field(default="[]")  # JSON array of transformation names
    error_message: Optional[str] = None
    processing_time_ms: Optional[int] = None
    processed_at: datetime = BaseTableModel.Field(default_factory=datetime.utcnow)

    # Relationships
    item: "Item" = BaseTableModel.Relationship()
    feed: "Feed" = BaseTableModel.Relationship()

    @property
    def transformations(self) -> List[str]:
        """Parse JSON transformations to list."""
        try:
            return json.loads(self.transformations_applied)
        except json.JSONDecodeError:
            return []

    @transformations.setter
    def transformations(self, value: List[str]):
        """Set transformations from list."""
        self.transformations_applied = json.dumps(value)