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
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    ERROR = "ERROR"


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


class BaseCreatedOnly(SQLModel):
    """Base model for append-only tables (only created_at)."""
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Make Field, Relationship, Column, JSON available as class attributes
    Field: ClassVar = Field
    Relationship: ClassVar = Relationship
    Column: ClassVar = Column
    JSON: ClassVar = JSON


class BaseCreatedUpdated(SQLModel):
    """Base model for mutable tables (created_at + updated_at)."""
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Make Field, Relationship, Column, JSON available as class attributes
    Field: ClassVar = Field
    Relationship: ClassVar = Relationship
    Column: ClassVar = Column
    JSON: ClassVar = JSON


# Legacy compatibility - will be phased out
class BaseModel(BaseCreatedUpdated):
    """Legacy base model - use BaseCreatedOnly or BaseCreatedUpdated instead."""
    pass


class BaseTableModel(BaseCreatedUpdated):
    """Legacy base table model - use specific base classes instead."""
    id: Optional[int] = Field(default=None, primary_key=True)