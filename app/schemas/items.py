"""Item-related DTOs and schemas."""

from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field


class ItemQuery(BaseModel):
    """Filter object for item queries"""
    feed_ids: Optional[List[int]] = None
    category_id: Optional[int] = None
    from_date: Optional[datetime] = None
    to_date: Optional[datetime] = None
    search: Optional[str] = None  # Full-text search in title/description

    # Analysis filters
    sentiment: Optional[str] = None  # "positive", "negative", "neutral"
    impact_min: Optional[float] = None
    urgency_min: Optional[float] = None
    has_analysis: Optional[bool] = None

    # Sorting
    sort_by: str = Field(default="created_at", pattern="^(created_at|published|impact_score|title)$")
    sort_desc: bool = True


class ItemResponse(BaseModel):
    """Response DTO for item data"""
    id: int
    title: str
    link: str
    description: Optional[str] = None
    content: Optional[str] = None
    author: Optional[str] = None
    published: Optional[datetime] = None
    guid: Optional[str] = None
    content_hash: str
    feed_id: int
    created_at: datetime

    # Feed information (joined)
    feed_title: Optional[str] = None
    feed_url: Optional[str] = None

    # Analysis information (joined)
    sentiment_label: Optional[str] = None
    sentiment_score: Optional[float] = None
    impact_score: Optional[float] = None
    urgency_score: Optional[float] = None
    analysis_id: Optional[int] = None


class ItemCreate(BaseModel):
    """DTO for creating new items"""
    title: str
    link: str
    description: Optional[str] = None
    content: Optional[str] = None
    author: Optional[str] = None
    published: Optional[datetime] = None
    guid: Optional[str] = None
    content_hash: str
    feed_id: int


class ItemUpdate(BaseModel):
    """DTO for updating items (rarely used - items are mostly immutable)"""
    title: Optional[str] = None
    description: Optional[str] = None
    content: Optional[str] = None
    author: Optional[str] = None
    published: Optional[datetime] = None


class ItemStatistics(BaseModel):
    """DTO for item statistics"""
    total_count: int
    today_count: int
    last_24h_count: int
    last_week_count: int
    by_feed: List[dict] = []
    by_sentiment: dict = {}


class ItemsListResponse(BaseModel):
    """Paginated response for item lists"""
    items: List[ItemResponse]
    total_count: Optional[int] = None
    limit: int
    offset: int
    has_more: bool = False
    query: ItemQuery