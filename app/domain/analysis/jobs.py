from pydantic import BaseModel, Field
from typing import Literal, List, Optional, Dict, Any, Union
from datetime import datetime
import uuid
from .control import RunScope, RunParams, RunPreview, ScopeType

# Job Status Types
JobStatus = Literal["preview", "confirmed", "running", "completed", "failed", "cancelled"]

# Selection Mode Types (Frontend → Backend mapping)
SelectionMode = Literal["latest", "timeRange", "unanalyzed", "feed", "custom"]

class SelectionConfig(BaseModel):
    """Frontend selection configuration"""
    mode: SelectionMode
    count: Optional[int] = None  # For 'latest' mode
    days: Optional[int] = None   # For 'timeRange' mode
    hours: Optional[int] = None  # For 'timeRange' mode
    feed_id: Optional[int] = None  # For 'feed' mode
    item_ids: Optional[List[int]] = None  # For 'custom' mode

class ModelParameters(BaseModel):
    """AI Model configuration parameters"""
    model_tag: str = "gpt-4.1-nano"
    temperature: float = Field(default=0.3, ge=0.0, le=2.0)
    include_sentiment: bool = True
    include_impact: bool = True
    rate_per_second: float = Field(default=1.0, ge=0.2, le=3.0)

class AnalysisFilters(BaseModel):
    """Additional analysis filters"""
    use_feed_filter: bool = False
    feed_id: Optional[int] = None
    unanalyzed_only: bool = True
    override_existing: bool = False
    min_impact_threshold: Optional[float] = None
    max_impact_threshold: Optional[float] = None

class PreviewJob(BaseModel):
    """Job configuration for preview and execution"""
    job_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    status: JobStatus = "preview"
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Frontend Configuration
    selection: SelectionConfig
    parameters: ModelParameters
    filters: AnalysisFilters = Field(default_factory=AnalysisFilters)

    # Calculated Results (filled by preview service)
    estimates: Optional[RunPreview] = None

    # Execution Tracking
    run_id: Optional[int] = None  # Set when job becomes actual run
    triggered_by: str = "manual"

    def to_run_scope(self) -> RunScope:
        """Convert job to RunScope for backend processing"""
        scope = RunScope()

        if self.selection.mode == "latest":
            scope.type = "global"
            scope.unanalyzed_only = self.filters.unanalyzed_only

        elif self.selection.mode == "timeRange":
            scope.type = "timerange"
            if self.selection.days or self.selection.hours:
                total_hours = (self.selection.days or 0) * 24 + (self.selection.hours or 0)
                end_time = datetime.utcnow()
                start_time = end_time.replace(hour=end_time.hour - total_hours) if total_hours < 24 else end_time.replace(day=end_time.day - (total_hours // 24))
                scope.start_time = start_time
                scope.end_time = end_time
            scope.unanalyzed_only = self.filters.unanalyzed_only

        elif self.selection.mode == "unanalyzed":
            scope.type = "global"
            scope.unanalyzed_only = True

        elif self.selection.mode == "feed":
            scope.type = "feeds"
            if self.selection.feed_id:
                scope.feed_ids = [self.selection.feed_id]
            elif self.filters.feed_id:
                scope.feed_ids = [self.filters.feed_id]
            scope.unanalyzed_only = self.filters.unanalyzed_only

        elif self.selection.mode == "custom":
            scope.type = "items"
            scope.item_ids = self.selection.item_ids or []

        # Apply additional filters
        if self.filters.min_impact_threshold is not None:
            scope.min_impact_threshold = self.filters.min_impact_threshold
        if self.filters.max_impact_threshold is not None:
            scope.max_impact_threshold = self.filters.max_impact_threshold

        return scope

    def to_run_params(self) -> RunParams:
        """Convert job to RunParams for backend processing"""
        return RunParams(
            limit=self.selection.count or 200,
            rate_per_second=self.parameters.rate_per_second,
            model_tag=self.parameters.model_tag,
            override_existing=self.filters.override_existing,
            newest_first=True,
            retry_failed=True,
            triggered_by=self.triggered_by
        )

    def get_description(self) -> str:
        """Get human-readable description of the job"""
        if self.selection.mode == "latest":
            return f"Latest {self.selection.count or 50} articles"
        elif self.selection.mode == "timeRange":
            days = self.selection.days or 0
            hours = self.selection.hours or 0
            if days > 0 and hours > 0:
                return f"Last {days} days and {hours} hours"
            elif days > 0:
                return f"Last {days} day{'s' if days > 1 else ''}"
            elif hours > 0:
                return f"Last {hours} hour{'s' if hours > 1 else ''}"
            else:
                return "All time"
        elif self.selection.mode == "unanalyzed":
            return "All unanalyzed articles"
        elif self.selection.mode == "feed":
            return f"Feed {self.selection.feed_id or 'filtered'} articles"
        else:
            return "Custom selection"

class JobResult(BaseModel):
    """Result of job operations"""
    success: bool
    job_id: str
    estimates: Optional[RunPreview] = None
    error: Optional[str] = None
    message: Optional[str] = None