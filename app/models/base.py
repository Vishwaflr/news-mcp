"""Base models and enums for the News MCP application."""

from sqlmodel import SQLModel, Field, Relationship, Column, JSON
from typing import Optional, List, Dict, Any, ClassVar
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


class BaseModel(SQLModel):
    """Base model with common fields."""
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default=None)


class BaseTableModel(BaseModel):
    """Base table model with ID and timestamps."""
    id: Optional[int] = Field(default=None, primary_key=True)

    # Make Field, Relationship, Column, JSON available as class attributes
    Field: ClassVar = Field
    Relationship: ClassVar = Relationship
    Column: ClassVar = Column
    JSON: ClassVar = JSON