"""Auto-analysis models for pending analysis queue."""

from typing import Optional, List
from datetime import datetime
from sqlmodel import SQLModel, Field, Column, JSON

class PendingAutoAnalysis(SQLModel, table=True):
    """Queue for pending auto-analysis jobs."""
    __tablename__ = "pending_auto_analysis"

    id: Optional[int] = Field(default=None, primary_key=True)
    feed_id: int = Field(foreign_key="feeds.id", index=True)
    item_ids: List[int] = Field(sa_column=Column(JSON))
    status: str = Field(default="pending", index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    processed_at: Optional[datetime] = None
    analysis_run_id: Optional[int] = Field(default=None, foreign_key="analysis_runs.id")
    error_message: Optional[str] = None