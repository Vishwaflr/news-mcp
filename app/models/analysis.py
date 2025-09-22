"""Analysis-related models for the News MCP application."""

from typing import Optional
from datetime import datetime
from sqlmodel import SQLModel, Field, Column, JSON
import sqlalchemy as sa

# These models represent existing analysis tables in the database
# They are defined here to prevent Alembic from dropping them

class ItemAnalysis(SQLModel, table=True):
    """AI analysis results for news items."""
    __tablename__ = "item_analysis"

    id: Optional[int] = Field(default=None, primary_key=True)
    item_id: int = Field(foreign_key="items.id", unique=True)
    sentiment_score: Optional[float] = None
    sentiment_label: Optional[str] = Field(index=True)
    impact_score: Optional[float] = None
    urgency_score: Optional[int] = Field(index=True)
    relevance_score: Optional[float] = None
    impact_overall: Optional[int] = Field(index=True)
    model_tag: Optional[str] = None
    raw_analysis_data: Optional[dict] = Field(sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(index=True)


class AnalysisRun(SQLModel, table=True):
    """Track bulk analysis operations."""
    __tablename__ = "analysis_runs"

    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    status: str = Field(index=True)
    scope_hash: Optional[str] = Field(index=True)
    filters: Optional[dict] = Field(sa_column=Column(JSON))
    total_items: Optional[int] = None
    processed_items: Optional[int] = None
    failed_items: Optional[int] = None
    error_message: Optional[str] = None
    avg_processing_time: Optional[float] = None
    model_tag: Optional[str] = None


class AnalysisRunItem(SQLModel, table=True):
    """Items processed in an analysis run."""
    __tablename__ = "analysis_run_items"

    id: Optional[int] = Field(default=None, primary_key=True)
    run_id: int = Field(foreign_key="analysis_runs.id", index=True)
    item_id: int = Field(foreign_key="items.id", index=True)
    state: str = Field(index=True)
    processing_started_at: Optional[datetime] = None
    processing_completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    retry_count: int = Field(default=0)


class AnalysisPreset(SQLModel, table=True):
    """Saved analysis configurations."""
    __tablename__ = "analysis_presets"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(unique=True)
    description: Optional[str] = None
    filters: Optional[dict] = Field(sa_column=Column(JSON))
    model_tag: str
    rate_per_second: float
    is_default: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None