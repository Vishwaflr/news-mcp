"""
Research Pipeline Models
SQLModel definitions for research templates, runs, queries, and results
"""
from typing import Optional, Dict, Any, List
from datetime import datetime
from sqlmodel import Field, SQLModel, Relationship, JSON, Column
from sqlalchemy.dialects.postgresql import JSONB


class ResearchTemplate(SQLModel, table=True):
    """Template for research runs with filter and prompt configuration"""
    __tablename__ = "research_templates"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(max_length=200, index=True)
    description: Optional[str] = Field(default=None, sa_type=JSONB)

    # Filter Configuration
    filter_config: Dict[str, Any] = Field(sa_column=Column(JSONB))

    # LLM Prompt Configuration
    agent_role: str
    task_description: str
    query_template: Optional[str] = None

    # Output Schema Definition
    output_schema: Dict[str, Any] = Field(sa_column=Column(JSONB))

    # Storage Configuration
    storage_config: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSONB))

    # Metadata
    active: bool = Field(default=True, index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None

    # Relationships
    runs: List["ResearchRun"] = Relationship(back_populates="template")


class ResearchRun(SQLModel, table=True):
    """Execution instance of a research template"""
    __tablename__ = "research_runs"

    id: Optional[int] = Field(default=None, primary_key=True)
    template_id: Optional[int] = Field(default=None, foreign_key="research_templates.id")

    # Configuration snapshot
    filter_used: Dict[str, Any] = Field(sa_column=Column(JSONB))
    prompt_used: str

    # Status tracking
    status: str = Field(default="pending", max_length=50, index=True)
    error_message: Optional[str] = None

    # Timing
    started_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    completed_at: Optional[datetime] = None

    # Metrics
    articles_count: Optional[int] = None
    queries_generated: Optional[int] = None
    queries_executed: Optional[int] = None

    # Relationships
    template: Optional[ResearchTemplate] = Relationship(back_populates="runs")
    queries: List["ResearchQuery"] = Relationship(back_populates="run", sa_relationship_kwargs={"cascade": "all, delete-orphan"})
    results: List["ResearchResult"] = Relationship(back_populates="run", sa_relationship_kwargs={"cascade": "all, delete-orphan"})
    article_links: List["ResearchArticleLink"] = Relationship(back_populates="research_run", sa_relationship_kwargs={"cascade": "all, delete-orphan"})


class ResearchQuery(SQLModel, table=True):
    """LLM-generated research query for Perplexity execution"""
    __tablename__ = "research_queries"

    id: Optional[int] = Field(default=None, primary_key=True)
    run_id: int = Field(foreign_key="research_runs.id", index=True)
    query_text: str
    priority: str = Field(default="medium", max_length=20)

    # Perplexity execution
    perplexity_executed: bool = Field(default=False, index=True)
    perplexity_response: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSONB))
    sources: Optional[List[Dict[str, Any]]] = Field(default=None, sa_column=Column(JSONB))

    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    executed_at: Optional[datetime] = None

    # Relationships
    run: ResearchRun = Relationship(back_populates="queries")
    results: List["ResearchResult"] = Relationship(back_populates="query")


class ResearchResult(SQLModel, table=True):
    """Processed and structured research result"""
    __tablename__ = "research_results"

    id: Optional[int] = Field(default=None, primary_key=True)
    run_id: int = Field(foreign_key="research_runs.id", index=True)
    query_id: Optional[int] = Field(default=None, foreign_key="research_queries.id")

    # Result classification
    result_type: str = Field(max_length=50, index=True)

    # Structured data (based on output_schema)
    structured_data: Dict[str, Any] = Field(sa_column=Column(JSONB))

    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    run: ResearchRun = Relationship(back_populates="results")
    query: Optional[ResearchQuery] = Relationship(back_populates="results")


class ResearchArticleLink(SQLModel, table=True):
    """Many-to-many link between research runs and articles"""
    __tablename__ = "research_article_links"

    research_run_id: int = Field(foreign_key="research_runs.id", primary_key=True)
    item_id: int = Field(foreign_key="items.id", primary_key=True, index=True)
    relevance_score: Optional[float] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    research_run: ResearchRun = Relationship(back_populates="article_links")
