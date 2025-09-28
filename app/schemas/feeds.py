"""Feed schemas for API responses and requests."""

from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, List
from datetime import datetime
from enum import Enum


class FeedStatus(str, Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    ERROR = "ERROR"


class FeedCreate(BaseModel):
    """Schema for creating a new feed."""
    url: str
    title: Optional[str] = None
    description: Optional[str] = None
    category_id: Optional[int] = None
    category_ids: Optional[List[int]] = None
    fetch_interval_minutes: int = Field(default=60, ge=5, le=1440)
    status: FeedStatus = FeedStatus.ACTIVE
    auto_analyze_enabled: bool = False
    source_id: Optional[int] = None


class FeedUpdate(BaseModel):
    """Schema for updating an existing feed."""
    title: Optional[str] = None
    description: Optional[str] = None
    category_id: Optional[int] = None
    category_ids: Optional[List[int]] = None
    fetch_interval_minutes: Optional[int] = Field(None, ge=5, le=1440)
    status: Optional[FeedStatus] = None
    auto_analyze_enabled: Optional[bool] = None


class FeedResponse(BaseModel):
    """Schema for feed API responses."""
    id: int
    url: str
    title: Optional[str] = None
    description: Optional[str] = None
    category_id: Optional[int] = None
    fetch_interval_minutes: int
    status: FeedStatus
    created_at: datetime
    updated_at: Optional[datetime] = None
    last_fetched_at: Optional[datetime] = None

    # Optional fields
    category_name: Optional[str] = None
    items_count: Optional[int] = None
    error_count: Optional[int] = None

    class Config:
        from_attributes = True


class FeedStats(BaseModel):
    """Feed statistics schema."""
    total_feeds: int
    active_feeds: int
    error_feeds: int
    total_items: int
    items_today: int
    average_items_per_feed: float