"""
SQLModel database models for Content Distribution System.

These models map to the database tables created by the migration:
- ContentTemplate
- GeneratedContent
- DistributionChannel
- DistributionLog
- PendingContentGeneration
"""

from sqlmodel import SQLModel, Field, Relationship, Column, JSON
from sqlalchemy import ARRAY, Integer, Text
from sqlalchemy.dialects.postgresql import JSONB
from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal


class ContentTemplate(SQLModel, table=True):
    """
    Content template for generating structured briefings.

    Defines what content to generate, how to structure it, and when to generate it.
    """
    __tablename__ = "content_templates"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(..., max_length=200, unique=True, index=True)
    description: Optional[str] = Field(None, sa_column=Column(Text))
    target_audience: Optional[str] = Field(None, max_length=100)

    # Selection criteria (JSONB)
    selection_criteria: Dict[str, Any] = Field(..., sa_column=Column(JSONB, nullable=False))

    # Content structure (JSONB)
    content_structure: Dict[str, Any] = Field(..., sa_column=Column(JSONB, nullable=False))

    # LLM configuration
    llm_prompt_template: str = Field(..., sa_column=Column(Text, nullable=False))
    llm_model: str = Field(default="gpt-4o-mini", max_length=50)
    llm_temperature: Decimal = Field(default=Decimal("0.7"))

    # Enhanced LLM instructions (for modular extensibility)
    system_instruction: Optional[str] = Field(None, sa_column=Column(Text))
    output_format: str = Field(default="markdown", max_length=50)
    output_constraints: Optional[Dict[str, Any]] = Field(None, sa_column=Column(JSONB))
    few_shot_examples: Optional[Dict[str, Any]] = Field(None, sa_column=Column(JSONB))
    validation_rules: Optional[Dict[str, Any]] = Field(None, sa_column=Column(JSONB))

    # Enrichment placeholder (future: CVE lookup, web search, scraping)
    enrichment_config: Optional[Dict[str, Any]] = Field(None, sa_column=Column(JSONB))

    # Scheduling
    generation_schedule: Optional[str] = Field(None, max_length=100, index=True)

    # Status
    is_active: bool = Field(default=True, index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Metadata
    version: int = Field(default=1)
    tags: Optional[Dict[str, Any]] = Field(None, sa_column=Column(JSONB))

    # Relationships
    generated_contents: List["GeneratedContent"] = Relationship(back_populates="template", cascade_delete=True)
    distribution_channels: List["DistributionChannel"] = Relationship(back_populates="template", cascade_delete=True)
    pending_generations: List["PendingContentGeneration"] = Relationship(back_populates="template", cascade_delete=True)


class GeneratedContent(SQLModel, table=True):
    """
    Generated content instance from a template.

    Stores the actual generated briefing/report content.
    """
    __tablename__ = "generated_content"

    id: Optional[int] = Field(default=None, primary_key=True)
    template_id: int = Field(..., foreign_key="content_templates.id", index=True)

    # Generated content
    title: Optional[str] = Field(None, max_length=500)
    content_html: Optional[str] = Field(None, sa_column=Column(Text))
    content_markdown: Optional[str] = Field(None, sa_column=Column(Text))
    content_json: Optional[Dict[str, Any]] = Field(None, sa_column=Column(JSONB))

    # Metadata
    generated_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    generation_job_id: Optional[str] = Field(None, max_length=100)

    # Source tracking
    source_article_ids: List[int] = Field(..., sa_column=Column(ARRAY(Integer), nullable=False))
    articles_count: int = Field(...)

    # Quality metrics
    word_count: Optional[int] = None
    generation_cost_usd: Optional[Decimal] = None
    generation_time_seconds: Optional[int] = None
    llm_model_used: Optional[str] = Field(None, max_length=50)

    # Status
    status: str = Field(default="generated", max_length=20, index=True)
    published_at: Optional[datetime] = None
    error_message: Optional[str] = Field(None, sa_column=Column(Text))

    # Relationships
    template: "ContentTemplate" = Relationship(back_populates="generated_contents")
    distribution_logs: List["DistributionLog"] = Relationship(back_populates="content", cascade_delete=True)


class DistributionChannel(SQLModel, table=True):
    """
    Distribution channel configuration for a template.

    Defines where and how to distribute generated content (email, web, RSS, API).
    """
    __tablename__ = "distribution_channels"

    id: Optional[int] = Field(default=None, primary_key=True)
    template_id: int = Field(..., foreign_key="content_templates.id", index=True)

    # Channel configuration
    channel_type: str = Field(..., max_length=20, index=True)  # email, web, rss, api
    channel_name: str = Field(..., max_length=200)
    channel_config: Dict[str, Any] = Field(..., sa_column=Column(JSONB, nullable=False))

    # Status
    is_active: bool = Field(default=True, index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_used_at: Optional[datetime] = None

    # Relationships
    template: "ContentTemplate" = Relationship(back_populates="distribution_channels")
    distribution_logs: List["DistributionLog"] = Relationship(back_populates="channel", cascade_delete=True)


class DistributionLog(SQLModel, table=True):
    """
    Log of content distribution attempts.

    Tracks delivery status, recipients, errors for each distribution.
    """
    __tablename__ = "distribution_log"

    id: Optional[int] = Field(default=None, primary_key=True)
    content_id: int = Field(..., foreign_key="generated_content.id", index=True)
    channel_id: int = Field(..., foreign_key="distribution_channels.id", index=True)

    # Distribution status
    status: str = Field(default="pending", max_length=20, index=True)  # pending, sent, failed, retry
    sent_at: Optional[datetime] = Field(None, index=True)

    # Delivery details
    recipient_count: Optional[int] = None
    recipients_list: Optional[Dict[str, Any]] = Field(None, sa_column=Column(JSONB))
    error_message: Optional[str] = Field(None, sa_column=Column(Text))
    retry_count: int = Field(default=0)

    # Tracking (optional)
    open_count: int = Field(default=0)
    click_count: int = Field(default=0)
    tracking_enabled: bool = Field(default=False)

    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    content: "GeneratedContent" = Relationship(back_populates="distribution_logs")
    channel: "DistributionChannel" = Relationship(back_populates="distribution_logs")


class PendingContentGeneration(SQLModel, table=True):
    """
    Queue table for pending content generation jobs.

    Similar to pending_auto_analysis for analysis runs.
    """
    __tablename__ = "pending_content_generation"

    id: Optional[int] = Field(default=None, primary_key=True)
    template_id: int = Field(..., foreign_key="content_templates.id", index=True)

    # Queue status
    status: str = Field(default="pending", max_length=20, index=True)  # pending, processing, completed, failed
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # Processing info
    worker_id: Optional[str] = Field(None, max_length=100)
    generated_content_id: Optional[int] = Field(None, foreign_key="generated_content.id")
    error_message: Optional[str] = Field(None, sa_column=Column(Text))
    retry_count: int = Field(default=0)

    # Metadata
    triggered_by: str = Field(default="manual", max_length=50)  # manual, scheduled, realtime

    # Relationships
    template: "ContentTemplate" = Relationship(back_populates="pending_generations")


# Update relationships after all models are defined
GeneratedContent.update_forward_refs()
ContentTemplate.update_forward_refs()
DistributionChannel.update_forward_refs()
DistributionLog.update_forward_refs()
PendingContentGeneration.update_forward_refs()
