"""
Research Models for Perplexity Integration
SQLModel definitions for research templates and execution runs
"""
from typing import Optional, Dict, Any
from datetime import datetime
from sqlmodel import Field, SQLModel, Column
from sqlalchemy import JSON, Numeric


class ResearchTemplate(SQLModel, table=True):
    """Template for Perplexity research with LLM processing configuration"""
    __tablename__ = "research_templates"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(max_length=200, index=True)
    description: Optional[str] = None

    # Perplexity Function Configuration
    perplexity_function: str = Field(max_length=100)
    function_parameters: Dict[str, Any] = Field(default={}, sa_column=Column(JSON))

    # LLM Configuration
    llm_model: str = Field(max_length=50)
    llm_prompt: str
    llm_temperature: float = Field(default=0.7, sa_column=Column(Numeric(precision=3, scale=2)))
    system_instruction: Optional[str] = None

    # Output Configuration
    output_format: str = Field(default="markdown", max_length=50)
    output_schema: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSON))

    # Scheduling
    schedule_enabled: bool = Field(default=False)
    cron_expression: Optional[str] = Field(default=None, max_length=100)

    # Metadata
    is_active: bool = Field(default=True, index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: Optional[str] = Field(default=None, max_length=100)
    tags: Optional[Dict[str, Any]] = Field(default=[], sa_column=Column(JSON))


class ResearchRun(SQLModel, table=True):
    """Execution instance of a research template"""
    __tablename__ = "research_runs"

    id: Optional[int] = Field(default=None, primary_key=True)
    template_id: Optional[int] = Field(default=None, foreign_key="research_templates.id")

    # Execution Tracking
    status: str = Field(max_length=50, index=True)  # pending, running, completed, failed
    trigger_type: str = Field(max_length=50)  # manual, scheduled, api

    # Query and Results
    query_text: Optional[str] = None
    result_content: Optional[str] = None
    result_metadata: Dict[str, Any] = Field(default={}, sa_column=Column(JSON))
    error_message: Optional[str] = None

    # Cost Tracking
    tokens_used: Optional[int] = None
    cost_usd: Optional[float] = Field(default=None, sa_column=Column(Numeric(precision=10, scale=6)))
    perplexity_cost_usd: Optional[float] = Field(default=None, sa_column=Column(Numeric(precision=10, scale=6)))
    llm_cost_usd: Optional[float] = Field(default=None, sa_column=Column(Numeric(precision=10, scale=6)))

    # Timing
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[int] = None

    # Audit
    triggered_by: Optional[str] = Field(default=None, max_length=100)
