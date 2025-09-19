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

# Model pricing (per 1K tokens) - Realistic market prices
MODEL_PRICING = {
    "gpt-4.1-nano": {"input": 0.020, "output": 0.080, "cached": 0.005},
    "gpt-4o-mini": {"input": 0.025, "output": 0.100, "cached": 0.0125},
    "gpt-4.1-mini": {"input": 0.070, "output": 0.280, "cached": 0.0175},
    "o4-mini": {"input": 0.200, "output": 0.800, "cached": 0.050},
    "gpt-4.1": {"input": 0.350, "output": 1.400, "cached": 0.0875},
    "gpt-4o": {"input": 0.425, "output": 1.700, "cached": 0.2125}
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
    limit: int = Field(default=200, ge=1, le=1000)
    rate_per_second: float = Field(default=1.0, ge=0.2, le=3.0)
    dry_run: bool = False
    model_tag: str = "gpt-4.1-nano"

    # Priority settings
    newest_first: bool = True
    retry_failed: bool = True
    override_existing: bool = False

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

    @classmethod
    def calculate(cls, item_count: int, rate_per_second: float = 1.0, model_tag: str = "gpt-4.1-nano") -> "RunPreview":
        """Calculate preview metrics"""
        # Get model pricing
        model_pricing = MODEL_PRICING.get(model_tag, MODEL_PRICING["gpt-4.1-nano"])
        # Use input pricing for estimation (conservative estimate)
        cost_per_1k_tokens = model_pricing["input"]

        estimated_cost = (item_count * AVG_TOKENS_PER_ITEM * cost_per_1k_tokens) / 1000
        estimated_duration = (item_count / rate_per_second) / 60  # minutes

        return cls(
            item_count=item_count,
            estimated_cost_usd=round(estimated_cost, 4),
            estimated_duration_minutes=int(estimated_duration),
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