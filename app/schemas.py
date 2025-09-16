from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from app.models import SourceType, FeedStatus

class CategoryCreate(BaseModel):
    name: str
    description: Optional[str] = None
    color: Optional[str] = None

class CategoryResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    color: Optional[str]
    created_at: datetime

class SourceCreate(BaseModel):
    name: str
    type: SourceType
    description: Optional[str] = None

class SourceResponse(BaseModel):
    id: int
    name: str
    type: SourceType
    description: Optional[str]
    created_at: datetime

class FeedCreate(BaseModel):
    url: str
    title: Optional[str] = None
    description: Optional[str] = None
    fetch_interval_minutes: int = 60
    source_id: int
    category_ids: Optional[List[int]] = []

class FeedUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[FeedStatus] = None
    fetch_interval_minutes: Optional[int] = None

class FeedResponse(BaseModel):
    id: int
    url: str
    title: Optional[str]
    description: Optional[str]
    status: FeedStatus
    fetch_interval_minutes: int
    last_fetched: Optional[datetime]
    source_id: int
    created_at: datetime
    updated_at: datetime

class ItemResponse(BaseModel):
    id: int
    title: str
    link: str
    description: Optional[str]
    content: Optional[str]
    author: Optional[str]
    published: Optional[datetime]
    feed_id: int
    created_at: datetime

class FeedHealthResponse(BaseModel):
    feed_id: int
    ok_ratio: float
    consecutive_failures: int
    avg_response_time_ms: Optional[float]
    last_success: Optional[datetime]
    last_failure: Optional[datetime]
    uptime_24h: float
    uptime_7d: float
    updated_at: datetime

class FetchLogResponse(BaseModel):
    id: int
    feed_id: int
    started_at: datetime
    completed_at: Optional[datetime]
    status: str
    items_found: int
    items_new: int
    error_message: Optional[str]
    response_time_ms: Optional[int]