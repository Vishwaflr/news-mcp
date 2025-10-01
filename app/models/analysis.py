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

    # FIXED: item_id is the PRIMARY KEY (not id)
    # Database schema: item_analysis.item_id is PRIMARY KEY
    item_id: int = Field(foreign_key="items.id", primary_key=True)

    # FIXED: Actual DB schema uses JSONB fields (not individual columns)
    sentiment_json: dict = Field(default={}, sa_column=Column(JSON))
    impact_json: dict = Field(default={}, sa_column=Column(JSON))
    model_tag: Optional[str] = None
    updated_at: datetime = Field(default_factory=datetime.utcnow, index=True)


class AnalysisRun(SQLModel, table=True):
    """Track bulk analysis operations."""
    __tablename__ = "analysis_runs"

    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    status: str = Field(index=True)
    scope_hash: str = Field(default="", index=True)
    triggered_by: str = Field(default="manual")  # manual, auto, scheduled

    # Fields that exist in DB
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    scope_json: dict = Field(default={}, sa_column=Column(JSON))
    params_json: dict = Field(default={}, sa_column=Column(JSON))
    queued_count: int = Field(default=0)
    processed_count: int = Field(default=0)
    failed_count: int = Field(default=0)
    cost_estimate: Optional[float] = None
    actual_cost: Optional[float] = None
    error_rate: Optional[float] = None
    items_per_min: Optional[float] = None
    eta_seconds: Optional[int] = None
    coverage_10m: Optional[float] = None
    coverage_60m: Optional[float] = None
    last_error: Optional[str] = None
    job_id: Optional[str] = None
    planned_count: int = Field(default=0)
    skipped_count: int = Field(default=0)
    skipped_items: Optional[list] = Field(default=[], sa_column=Column(JSON))


class AnalysisRunItem(SQLModel, table=True):
    """Items processed in an analysis run."""
    __tablename__ = "analysis_run_items"

    id: Optional[int] = Field(default=None, primary_key=True)
    run_id: int = Field(foreign_key="analysis_runs.id", index=True)
    item_id: int = Field(foreign_key="items.id", index=True)
    state: str = Field(index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    tokens_used: Optional[int] = None
    cost_usd: Optional[float] = None

    # Skip tracking fields
    skip_reason: Optional[str] = Field(default=None, max_length=50)
    skipped_at: Optional[datetime] = None


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