"""
Run Queue Models

Database models for managing the analysis run queue with priorities.
"""

from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any
from sqlmodel import SQLModel, Field, Column, JSON
from sqlalchemy import DateTime


class RunPriority(str, Enum):
    """Priority levels for analysis runs"""
    HIGH = "HIGH"      # Manual runs - highest priority
    MEDIUM = "MEDIUM"  # Scheduled runs - medium priority
    LOW = "LOW"        # Auto-analysis - lowest priority


class RunStatus(str, Enum):
    """Status of queued runs"""
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class QueuedRun(SQLModel, table=True):
    """
    Represents a queued analysis run with priority.

    This table manages the run queue and ensures proper priority ordering.
    """
    __tablename__ = "queued_runs"

    id: Optional[int] = Field(default=None, primary_key=True)

    # Priority and scheduling
    priority: RunPriority = Field(default=RunPriority.MEDIUM)
    status: RunStatus = Field(default=RunStatus.QUEUED, index=True)

    # Run identification
    scope_hash: str = Field(index=True)  # For duplicate detection
    triggered_by: str = Field(default="manual")

    # Run configuration (stored as JSON)
    scope_json: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    params_json: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))

    # Timing
    created_at: datetime = Field(default_factory=datetime.utcnow, sa_column=Column(DateTime(timezone=True)))
    started_at: Optional[datetime] = Field(default=None, sa_column=Column(DateTime(timezone=True)))
    completed_at: Optional[datetime] = Field(default=None, sa_column=Column(DateTime(timezone=True)))

    # Result tracking
    analysis_run_id: Optional[int] = Field(default=None)  # Reference to actual AnalysisRun
    error_message: Optional[str] = Field(default=None)

    # Queue position (for ordering)
    queue_position: int = Field(default=0, index=True)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses"""
        return {
            "id": self.id,
            "priority": self.priority,
            "status": self.status,
            "scope_hash": self.scope_hash,
            "triggered_by": self.triggered_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "analysis_run_id": self.analysis_run_id,
            "queue_position": self.queue_position,
            "error_message": self.error_message
        }