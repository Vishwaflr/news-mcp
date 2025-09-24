from pydantic import BaseModel, Field, validator
from typing import Literal, List, Optional, Dict, Any
from datetime import datetime, timedelta
from enum import Enum
import hashlib
import json

# Enums for Analysis Control Center
RunStatus = Literal["pending", "running", "paused", "completed", "failed", "cancelled"]
ItemState = Literal["queued", "processing", "completed", "failed", "skipped"]
ScopeType = Literal["global", "feeds", "items", "articles", "timerange", "filtered"]

# Cost estimation constants
AVG_TOKENS_PER_ITEM = 500  # Average tokens per news item

# Model pricing (per 1M tokens) - Official OpenAI pricing
MODEL_PRICING = {
    "gpt-5": {"input": 2.50, "output": 20.00, "cached": 0.25},
    "gpt-5-mini": {"input": 0.45, "output": 3.60, "cached": 0.045},
    "gpt-4.1": {"input": 3.50, "output": 14.00, "cached": 0.875},
    "gpt-4.1-mini": {"input": 0.70, "output": 2.80, "cached": 0.175},
    "gpt-4.1-nano": {"input": 0.20, "output": 0.80, "cached": 0.05},
    "gpt-4o": {"input": 4.25, "output": 17.00, "cached": 2.125},
    "gpt-4o-2024-05-13": {"input": 8.75, "output": 26.25, "cached": 0.0},  # No cached pricing listed
    "gpt-4o-mini": {"input": 0.25, "output": 1.00, "cached": 0.125},
    "o3": {"input": 3.50, "output": 14.00, "cached": 0.875},
    "o4-mini": {"input": 2.00, "output": 8.00, "cached": 0.50}
}

class RunScope(BaseModel):
    """Defines what items to analyze"""
    type: ScopeType = "global"

    # Feed-based scope
    feed_ids: List[int] = Field(default_factory=list)

    # Item-based scope
    item_ids: List[int] = Field(default_factory=list)

    # Article-based scope (specific articles selection)
    article_ids: List[int] = Field(default_factory=list)

    # Time-based scope
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None

    # Filters
    unanalyzed_only: bool = True
    model_tag_not_current: bool = False
    min_impact_threshold: Optional[float] = None
    max_impact_threshold: Optional[float] = None

    def generate_hash(self) -> str:
        """Generate unique hash for this scope to prevent duplicate runs"""
        scope_dict = self.model_dump()
        # Remove None values and sort for consistent hashing
        clean_dict = {k: v for k, v in scope_dict.items() if v is not None}
        scope_str = json.dumps(clean_dict, sort_keys=True, default=str)
        return hashlib.md5(scope_str.encode()).hexdigest()

class RunParams(BaseModel):
    """Parameters for running analysis"""
    limit: int = Field(default=200, ge=1, le=5000)
    rate_per_second: float = Field(default=1.0, ge=0.2, le=3.0)
    dry_run: bool = False
    model_tag: str = "gpt-4.1-nano"

    # Priority settings
    newest_first: bool = True
    retry_failed: bool = True
    override_existing: bool = False

    # Tracking
    triggered_by: str = "manual"  # manual, auto, scheduled

class RunPreview(BaseModel):
    """Preview of what a run would process"""
    item_count: int
    estimated_cost_usd: float
    estimated_duration_minutes: int
    sample_item_ids: List[int] = Field(default_factory=list)

    # Conflict detection
    already_analyzed_count: int = 0
    new_items_count: int = 0
    has_conflicts: bool = False

    # Additional stats for UI
    total_items: int = 0
    already_analyzed: int = 0

    @classmethod
    def calculate(cls, item_count: int, rate_per_second: float = 1.0, model_tag: str = "gpt-4.1-nano") -> "RunPreview":
        """Calculate preview metrics"""
        # Get model pricing
        model_pricing = MODEL_PRICING.get(model_tag, MODEL_PRICING["gpt-4.1-nano"])
        # Use input pricing for estimation (conservative estimate)
        cost_per_1m_tokens = model_pricing["input"]  # Price per 1M tokens

        estimated_cost = (item_count * AVG_TOKENS_PER_ITEM * cost_per_1m_tokens) / 1_000_000
        estimated_duration = (item_count / rate_per_second) / 60  # minutes

        # Round up to at least 1 minute if there are items to process
        duration_minutes = max(1, int(estimated_duration + 0.5)) if item_count > 0 else 0

        return cls(
            item_count=item_count,
            estimated_cost_usd=round(estimated_cost, 4),
            estimated_duration_minutes=duration_minutes,
            already_analyzed_count=0,
            new_items_count=0,
            has_conflicts=False
        )

class RunMetrics(BaseModel):
    """Live metrics for a running analysis"""
    queued_count: int = 0
    processed_count: int = 0
    failed_count: int = 0

    # Derived metrics
    total_count: int = 0
    progress_percent: float = 0.0
    error_rate: float = 0.0
    items_per_minute: float = 0.0
    eta_seconds: Optional[int] = None

    # Cost tracking
    actual_cost_usd: float = 0.0
    estimated_cost_usd: float = 0.0

    # SLO metrics
    coverage_10m: float = 0.0  # Coverage in last 10 minutes
    coverage_60m: float = 0.0  # Coverage in last 60 minutes

    def update_derived_metrics(self):
        """Update calculated fields"""
        self.total_count = self.queued_count + self.processed_count + self.failed_count

        if self.total_count > 0:
            completed = self.processed_count + self.failed_count
            self.progress_percent = round((completed / self.total_count) * 100, 1)

        if self.processed_count + self.failed_count > 0:
            self.error_rate = round(self.failed_count / (self.processed_count + self.failed_count), 4)

class AnalysisRun(BaseModel):
    """Complete analysis run model"""
    id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    # Configuration
    scope: RunScope
    params: RunParams
    scope_hash: str

    # Status
    status: RunStatus = "pending"
    started_at: Optional[datetime] = None
    triggered_by: str = "manual"  # manual, auto, scheduled
    completed_at: Optional[datetime] = None
    last_error: Optional[str] = None

    # Metrics
    metrics: RunMetrics = Field(default_factory=RunMetrics)

    @property
    def duration_seconds(self) -> Optional[int]:
        """Calculate run duration in seconds"""
        if self.started_at:
            end_time = self.completed_at or datetime.utcnow()
            return int((end_time - self.started_at).total_seconds())
        return None

    @property
    def is_active(self) -> bool:
        """Check if run is currently active"""
        return self.status in ["pending", "running", "paused"]

class RunItem(BaseModel):
    """Individual item in an analysis run"""
    id: Optional[int] = None
    run_id: int
    item_id: int

    state: ItemState = "queued"
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None

    # Cost tracking
    tokens_used: Optional[int] = None
    cost_usd: Optional[float] = None

class AnalysisPreset(BaseModel):
    """Saved analysis configuration preset"""
    id: Optional[int] = None
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)

    scope: RunScope
    params: RunParams

    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


# SLO thresholds
SLO_TARGETS = {
    "coverage_10m": 0.90,  # 90% coverage in 10 minutes
    "coverage_60m": 0.98,  # 98% coverage in 60 minutes
    "error_rate": 0.05,    # Max 5% error rate
    "max_cost_per_run": 25.0  # Max $25 per run warning
}