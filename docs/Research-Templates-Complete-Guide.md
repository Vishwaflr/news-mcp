# Research Templates - Complete Implementation Guide

**Version:** 1.0
**Status:** Ready for Implementation
**Strategy:** Feature-Flag basierte In-App Development

---

## Executive Summary

Ein professionelles System zur Verwaltung von Perplexity Research Templates mit Web-UI, API und MCP-Integration - entwickelt **sicher innerhalb der bestehenden Anwendung** ohne separate Server oder komplexe Infrastruktur.

**Kernkonzept:**
- Feature Flag gesteuert (`RESEARCH_ENABLED=true/false`)
- Code isoliert in `app/research/` Modul
- Ein Server, ein Prozess, ein Deployment
- Instant Rollback bei Problemen
- Graduelle Aktivierung möglich

---

## Table of Contents

1. [Development Strategy](#development-strategy)
2. [Features & Requirements](#features--requirements)
3. [Database Schema](#database-schema)
4. [Backend Implementation](#backend-implementation)
5. [Frontend Implementation](#frontend-implementation)
6. [MCP Integration](#mcp-integration)
7. [Implementation Phases](#implementation-phases)
8. [Testing Strategy](#testing-strategy)
9. [Deployment & Rollback](#deployment--rollback)

---

## Development Strategy

### Feature Flag Pattern

**Konzept:** Neue Features werden in der bestehenden App entwickelt, aber durch Feature Flags kontrolliert aktiviert/deaktiviert.

```python
# .env
RESEARCH_ENABLED=false  # Disabled by default - Main App safe!
RESEARCH_USE_SEPARATE_DB=false
```

**Wenn disabled (`RESEARCH_ENABLED=false`):**
- ❌ Kein `/api/research/*` Endpoint verfügbar
- ❌ Kein Research UI sichtbar
- ❌ Keine Research Models geladen
- ✅ Main App läuft exakt wie vorher
- ✅ Null Performance Impact

**Wenn enabled (`RESEARCH_ENABLED=true`):**
- ✅ Research API verfügbar
- ✅ Research UI sichtbar
- ✅ Volle Funktionalität
- ✅ Isoliert in `app/research/` Modul

### Code Structure

```
news-mcp/
├── .env                           # RESEARCH_ENABLED=false
│
├── app/
│   ├── main.py                    # +2 lines: Conditional import
│   ├── core/
│   │   └── config.py              # +3 lines: Feature flags
│   │
│   ├── models/                    # Unverändert
│   ├── services/                  # Unverändert
│   ├── web/                       # Unverändert
│   │
│   └── research/                  # NEU: Isoliertes Research Modul
│       ├── __init__.py
│       ├── models.py              # Research Models
│       ├── database.py            # Optional: Separate DB support
│       ├── service.py             # Business Logic
│       ├── routes.py              # API Endpoints
│       └── views.py               # Web UI Routes
│
├── templates/
│   ├── admin/                     # Bestehende Templates
│   └── research/                  # NEU: Research Templates
│       ├── templates_list.html
│       └── template_edit.html
│
├── alembic/
│   └── versions/
│       └── xxx_research.py        # Optional migration
│
└── docs/
    └── Research-Templates-Complete-Guide.md  # Diese Datei
```

**Minimale Änderungen an bestehender App:**

```python
# app/core/config.py
class Settings(BaseSettings):
    # ... existing settings ...

    # Research Feature Flags (NEU: +3 Zeilen)
    research_enabled: bool = False
    research_use_separate_db: bool = False
    research_database_url: str | None = None
```

```python
# app/main.py
# ... existing code ...

# Conditional Research Routes (NEU: +3 Zeilen)
if settings.research_enabled:
    from app.research.routes import router as research_router
    app.include_router(research_router)
```

**Das war's! Nur 6 Zeilen Änderung an bestehender App.**

### Graduelle Aktivierung

**Phase 1: Development (Disabled)**
```bash
RESEARCH_ENABLED=false
```
- Code entwickeln in `app/research/`
- Unit Tests laufen
- Main App vollständig unberührt
- Keine Routes verfügbar

**Phase 2: Backend Testing (Enabled + Separate DB)**
```bash
RESEARCH_ENABLED=true
RESEARCH_USE_SEPARATE_DB=true
RESEARCH_DATABASE_URL=postgresql://news_user:news_password@localhost:5432/news_research_test
```
- Research API verfügbar
- Separate Test-Datenbank
- Main DB komplett sicher
- UI optional noch versteckt

**Phase 3: Frontend Testing (Enabled + UI visible)**
```bash
RESEARCH_ENABLED=true
RESEARCH_USE_SEPARATE_DB=true
```
- Research UI sichtbar
- Testen der kompletten UX
- Immer noch separate DB

**Phase 4: Integration (Enabled + Main DB Schema)**
```bash
RESEARCH_ENABLED=true
RESEARCH_USE_SEPARATE_DB=false
```
- Nutzt `news_db` mit Schema `research`
- Joins zwischen Main + Research möglich
- Produktionsbereit

**Phase 5: Production (Always enabled)**
```bash
RESEARCH_ENABLED=true
```
- Feature Flag kann entfernt werden
- Voll integriert

### Rollback Strategy

**Instant Rollback:**
```bash
# Bei Problemen:
RESEARCH_ENABLED=false

# Restart
./scripts/start-api.sh

# Fertig! Research deaktiviert, Main App läuft wie vorher ✅
```

**Code Rollback:**
```bash
# Research Code isoliert in einem Ordner
rm -rf app/research/

# oder
git checkout HEAD -- app/research/

# Main App funktioniert weiter!
```

**Database Rollback:**
```bash
# Wenn separate DB:
DROP DATABASE news_research_test;
# Main DB unberührt ✅

# Wenn Schema in Main DB:
DROP SCHEMA research CASCADE;
# Andere Schemas unberührt ✅
```

---

## Features & Requirements

### 5 Kern-Template-Typen

#### 1. Domain-Filtered Research (Höchste Priorität)

**Use Case:** Nur vertrauenswürdige Quellen nutzen

**Configuration:**
```json
{
  "name": "Geopolitical Verified Sources",
  "template_type": "domain_filtered",
  "model": "sonar-pro",
  "query_template": "Analyze geopolitical implications: {topic}",
  "domain_filter": ["reuters.com", "apnews.com", ".gov", "un.org"],
  "recency_filter": "week"
}
```

**Example Execution:**
```python
execute_template(
    template_id=1,
    variables={"topic": "European energy crisis"}
)
# → Perplexity search limited to: reuters.com, apnews.com, .gov, un.org
# → Only results from last week
```

#### 2. Structured JSON Research

**Use Case:** Konsistente, maschinenlesbare Outputs

**Configuration:**
```json
{
  "name": "Financial Impact Analysis",
  "template_type": "structured",
  "model": "sonar-pro",
  "query_template": "Analyze financial impact: {topic}",
  "json_schema": {
    "type": "object",
    "properties": {
      "executive_summary": {"type": "string"},
      "affected_sectors": {
        "type": "array",
        "items": {
          "type": "object",
          "properties": {
            "sector": {"type": "string"},
            "impact_level": {"type": "string", "enum": ["high", "medium", "low"]},
            "description": {"type": "string"}
          }
        }
      },
      "market_predictions": {"type": "array", "items": {"type": "string"}},
      "risk_factors": {"type": "array", "items": {"type": "string"}}
    },
    "required": ["executive_summary", "affected_sectors"]
  }
}
```

**Example Response:**
```json
{
  "executive_summary": "The energy crisis has significant impact on...",
  "affected_sectors": [
    {"sector": "Manufacturing", "impact_level": "high", "description": "..."},
    {"sector": "Transportation", "impact_level": "medium", "description": "..."}
  ],
  "market_predictions": ["Oil prices likely to rise...", "..."],
  "risk_factors": ["Supply chain disruption", "..."]
}
```

#### 3. Multi-Step Pipeline

**Use Case:** Komplexe Analysen mit mehreren Research-Schritten

**Configuration:**
```json
{
  "name": "Deep Geopolitical Analysis",
  "template_type": "pipeline",
  "pipeline_steps": [
    {
      "step": 1,
      "query": "What are the key aspects of {topic}?",
      "model": "sonar",
      "max_tokens": 500
    },
    {
      "step": 2,
      "query": "For each aspect from step 1, provide expert opinions: {step_1_result}",
      "model": "sonar-pro",
      "domain_filter": ["brookings.edu", "cfr.org", "chathamhouse.org"],
      "max_tokens": 2000
    },
    {
      "step": 3,
      "query": "Synthesize findings from steps 1-2 into comprehensive analysis",
      "model": "sonar-pro",
      "max_tokens": 3000
    }
  ]
}
```

**Execution Flow:**
```
Step 1: Identify key aspects (fast, cheap with sonar)
  ↓
Step 2: Deep dive per aspect (detailed with sonar-pro + domain filter)
  ↓
Step 3: Synthesize all findings (comprehensive with sonar-pro)
```

#### 4. Time-Filtered Research

**Use Case:** Breaking news vs. historische Analyse

**Configuration:**
```json
{
  "name": "Breaking News Analysis",
  "template_type": "time_filtered",
  "model": "sonar-pro",
  "query_template": "Latest developments: {topic}",
  "recency_filter": "day"
}
```

#### 5. Cost Analytics Template

**Use Case:** Token/Kosten-Tracking pro Template

**Built-in:** Automatisch für alle Templates

**Metrics:**
- Token usage per execution
- Cost per execution
- Average latency
- Success rate
- Citation count

### Web UI Features

**1. Templates List Page**
- Grid view aller Templates
- Filter by type (domain_filtered, structured, pipeline, etc.)
- Usage statistics (call count, last used)
- Status badges (active/inactive)
- Quick actions (Edit, Test, Analytics, Delete)

**2. Template Editor (Split-View)**
- **Left Panel:** Configuration
  - Basic info (name, description, type)
  - Perplexity config (model, query template)
  - Filters (domain, recency)
  - Advanced (JSON schema, pipeline steps)
- **Right Panel:** Live Preview
  - Test variables input
  - Run test query button
  - Real-time results display
  - Cost estimate
  - Citations list

**3. Analytics Dashboard**
- Usage over time (chart)
- Cost breakdown by template
- Token consumption trends
- Success/failure rates
- Average latency

---

## Database Schema

### Schema Strategy

**Option A: Separate Test Database (Development)**
```sql
-- Temporary test database
CREATE DATABASE news_research_test;
GRANT ALL PRIVILEGES ON DATABASE news_research_test TO news_user;
```

**Option B: Schema in Main Database (Production)**
```sql
-- Isolated schema in main database
CREATE SCHEMA IF NOT EXISTS research;
GRANT ALL ON SCHEMA research TO news_user;
```

### Tables

#### research.templates

```sql
CREATE TABLE research.templates (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    description TEXT,
    template_type VARCHAR(50) NOT NULL,  -- domain_filtered, structured, pipeline, time_filtered

    -- Perplexity Configuration
    model VARCHAR(50) NOT NULL DEFAULT 'sonar-pro',
    query_template TEXT NOT NULL,

    -- Filters (JSONB for flexibility)
    domain_filter JSONB,  -- ["reuters.com", "apnews.com"]
    recency_filter VARCHAR(20),  -- day, week, month, year

    -- Output Configuration
    json_schema JSONB,  -- For structured outputs
    max_tokens INTEGER DEFAULT 2000,
    temperature FLOAT DEFAULT 0.2,

    -- Pipeline Configuration
    pipeline_steps JSONB,  -- For multi-step research

    -- Metadata
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    created_by VARCHAR(100),
    is_active BOOLEAN DEFAULT TRUE,

    -- Usage Stats
    usage_count INTEGER DEFAULT 0,
    last_used_at TIMESTAMP,

    CONSTRAINT valid_template_type CHECK (
        template_type IN ('domain_filtered', 'structured', 'pipeline', 'time_filtered')
    ),
    CONSTRAINT valid_recency_filter CHECK (
        recency_filter IS NULL OR recency_filter IN ('day', 'week', 'month', 'year')
    )
);

CREATE INDEX idx_templates_type ON research.templates(template_type);
CREATE INDEX idx_templates_active ON research.templates(is_active);
```

#### research.executions

```sql
CREATE TABLE research.executions (
    id SERIAL PRIMARY KEY,
    template_id INTEGER NOT NULL REFERENCES research.templates(id) ON DELETE CASCADE,

    -- Execution Details
    query TEXT NOT NULL,
    context TEXT,
    executed_at TIMESTAMP DEFAULT NOW(),

    -- Results
    response TEXT,
    citations JSONB,  -- Array of URLs

    -- Performance Metrics
    tokens_used INTEGER,
    latency_ms INTEGER,
    cost_estimate DECIMAL(10, 6),

    -- Status
    status VARCHAR(20) DEFAULT 'pending',  -- pending, running, success, failed
    error_message TEXT,

    -- Triggered By
    triggered_by VARCHAR(50),  -- mcp, api, special_report, manual
    triggered_by_id INTEGER,  -- ID of triggering entity

    CONSTRAINT valid_status CHECK (
        status IN ('pending', 'running', 'success', 'failed', 'timeout')
    )
);

CREATE INDEX idx_executions_template ON research.executions(template_id);
CREATE INDEX idx_executions_date ON research.executions(executed_at);
CREATE INDEX idx_executions_status ON research.executions(status);
```

#### research.cost_analytics

```sql
CREATE TABLE research.cost_analytics (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    template_id INTEGER REFERENCES research.templates(id) ON DELETE SET NULL,

    -- Daily Aggregates
    total_executions INTEGER DEFAULT 0,
    total_tokens INTEGER DEFAULT 0,
    total_cost DECIMAL(10, 4) DEFAULT 0,

    -- Average Metrics
    avg_latency_ms DECIMAL(10, 2),
    avg_citations DECIMAL(10, 2),

    CONSTRAINT unique_daily_analytics UNIQUE(date, template_id)
);

CREATE INDEX idx_analytics_date ON research.cost_analytics(date);
CREATE INDEX idx_analytics_template ON research.cost_analytics(template_id);
```

---

## Backend Implementation

### Models

**File:** `app/research/models.py`

```python
"""
Research Templates Models

Conditional module - only loaded when RESEARCH_ENABLED=true
"""

from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List
from datetime import datetime
from pydantic import field_validator

class ResearchTemplate(SQLModel, table=True):
    """Research template for Perplexity queries"""
    __tablename__ = "templates"
    __table_args__ = {'schema': 'research'}

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(max_length=255, unique=True, index=True)
    description: Optional[str] = None
    template_type: str = Field(max_length=50)

    # Perplexity Config
    model: str = Field(default="sonar-pro", max_length=50)
    query_template: str

    # Filters
    domain_filter: Optional[List[str]] = Field(
        default=None,
        sa_column_kwargs={"type_": "JSONB"}
    )
    recency_filter: Optional[str] = Field(default=None, max_length=20)

    # Output Config
    json_schema: Optional[dict] = Field(
        default=None,
        sa_column_kwargs={"type_": "JSONB"}
    )
    max_tokens: int = Field(default=2000)
    temperature: float = Field(default=0.2)

    # Pipeline Config
    pipeline_steps: Optional[List[dict]] = Field(
        default=None,
        sa_column_kwargs={"type_": "JSONB"}
    )

    # Metadata
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    created_by: Optional[str] = None
    is_active: bool = Field(default=True)

    # Usage Stats
    usage_count: int = Field(default=0)
    last_used_at: Optional[datetime] = None

    # Relationships
    executions: List["ResearchExecution"] = Relationship(back_populates="template")

    @field_validator("template_type")
    def validate_type(cls, v):
        allowed = ["domain_filtered", "structured", "pipeline", "time_filtered"]
        if v not in allowed:
            raise ValueError(f"template_type must be one of {allowed}")
        return v

    @field_validator("recency_filter")
    def validate_recency(cls, v):
        if v is not None:
            allowed = ["day", "week", "month", "year"]
            if v not in allowed:
                raise ValueError(f"recency_filter must be one of {allowed}")
        return v


class ResearchExecution(SQLModel, table=True):
    """Research execution tracking"""
    __tablename__ = "executions"
    __table_args__ = {'schema': 'research'}

    id: Optional[int] = Field(default=None, primary_key=True)
    template_id: int = Field(foreign_key="research.templates.id")

    # Execution
    query: str
    context: Optional[str] = None
    executed_at: datetime = Field(default_factory=datetime.now)

    # Results
    response: Optional[str] = None
    citations: Optional[List[str]] = Field(
        default=None,
        sa_column_kwargs={"type_": "JSONB"}
    )

    # Metrics
    tokens_used: Optional[int] = None
    latency_ms: Optional[int] = None
    cost_estimate: Optional[float] = None

    # Status
    status: str = Field(default="pending", max_length=20)
    error_message: Optional[str] = None

    # Triggered By
    triggered_by: Optional[str] = Field(default=None, max_length=50)
    triggered_by_id: Optional[int] = None

    # Relationships
    template: ResearchTemplate = Relationship(back_populates="executions")


class ResearchCostAnalytics(SQLModel, table=True):
    """Daily cost analytics"""
    __tablename__ = "cost_analytics"
    __table_args__ = {'schema': 'research'}

    id: Optional[int] = Field(default=None, primary_key=True)
    date: datetime
    template_id: Optional[int] = Field(foreign_key="research.templates.id")

    # Aggregates
    total_executions: int = Field(default=0)
    total_tokens: int = Field(default=0)
    total_cost: float = Field(default=0.0)

    # Averages
    avg_latency_ms: Optional[float] = None
    avg_citations: Optional[float] = None
```

### Database Connection

**File:** `app/research/database.py`

```python
"""
Research Database Connection

Supports both separate test database and main database with schema
"""

from sqlmodel import create_engine, Session
from app.core.config import settings

def get_research_engine():
    """Get database engine for research"""
    if settings.research_use_separate_db and settings.research_database_url:
        # Separate test database
        return create_engine(
            settings.research_database_url,
            echo=settings.debug
        )
    else:
        # Use main database with schema
        from app.database import engine
        return engine


def get_research_session():
    """Get database session for research"""
    engine = get_research_engine()
    with Session(engine) as session:
        yield session


def init_research_db():
    """Initialize research database (development only)"""
    from sqlmodel import SQLModel
    from .models import ResearchTemplate, ResearchExecution, ResearchCostAnalytics

    engine = get_research_engine()

    # Create schema if using main database
    if not settings.research_use_separate_db:
        with engine.connect() as conn:
            conn.execute("CREATE SCHEMA IF NOT EXISTS research")
            conn.commit()

    # Create tables
    SQLModel.metadata.create_all(engine)
    print("✓ Research database initialized")
```

### Service Layer

**File:** `app/research/service.py`

```python
"""
Research Template Service

Core business logic for managing and executing research templates
"""

import httpx
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from sqlmodel import Session, select
import time

from app.core.config import settings
from .models import ResearchTemplate, ResearchExecution, ResearchCostAnalytics


class ResearchTemplateService:
    """Service for managing research templates"""

    def __init__(self, session: Session):
        self.session = session
        self.perplexity_api_key = settings.perplexity_api_key
        self.perplexity_url = "https://api.perplexity.ai/chat/completions"

    # CRUD Operations

    def list_templates(
        self,
        template_type: Optional[str] = None,
        is_active: Optional[bool] = None
    ) -> List[ResearchTemplate]:
        """List templates with optional filters"""
        query = select(ResearchTemplate)

        if template_type:
            query = query.where(ResearchTemplate.template_type == template_type)
        if is_active is not None:
            query = query.where(ResearchTemplate.is_active == is_active)

        return self.session.exec(query.order_by(ResearchTemplate.name)).all()

    def get_template(self, template_id: int) -> Optional[ResearchTemplate]:
        """Get template by ID"""
        return self.session.get(ResearchTemplate, template_id)

    def create_template(self, data: dict) -> ResearchTemplate:
        """Create new template"""
        template = ResearchTemplate(**data)
        self.session.add(template)
        self.session.commit()
        self.session.refresh(template)
        return template

    def update_template(self, template_id: int, data: dict) -> ResearchTemplate:
        """Update template"""
        template = self.get_template(template_id)
        if not template:
            raise ValueError(f"Template {template_id} not found")

        for key, value in data.items():
            setattr(template, key, value)

        template.updated_at = datetime.now()
        self.session.commit()
        self.session.refresh(template)
        return template

    def delete_template(self, template_id: int) -> bool:
        """Soft delete template"""
        template = self.get_template(template_id)
        if not template:
            return False

        template.is_active = False
        self.session.commit()
        return True

    # Execution

    async def execute_template(
        self,
        template_id: int,
        variables: Dict[str, str],
        triggered_by: str = "api",
        triggered_by_id: Optional[int] = None
    ) -> ResearchExecution:
        """Execute research template"""

        template = self.get_template(template_id)
        if not template or not template.is_active:
            raise ValueError(f"Template {template_id} not found or inactive")

        # Render query
        try:
            query = template.query_template.format(**variables)
        except KeyError as e:
            raise ValueError(f"Missing variable in template: {e}")

        # Create execution record
        execution = ResearchExecution(
            template_id=template_id,
            query=query,
            context=variables.get("context"),
            triggered_by=triggered_by,
            triggered_by_id=triggered_by_id,
            status="running"
        )
        self.session.add(execution)
        self.session.commit()

        start_time = time.time()

        try:
            # Execute based on type
            if template.template_type == "pipeline":
                result = await self._execute_pipeline(template, variables)
            else:
                result = await self._execute_single(template, query)

            # Calculate metrics
            latency_ms = int((time.time() - start_time) * 1000)

            # Update execution
            execution.response = result["response"]
            execution.citations = result.get("citations", [])
            execution.tokens_used = result.get("tokens_used")
            execution.latency_ms = latency_ms
            execution.cost_estimate = self._calculate_cost(
                result.get("tokens_used", 0),
                template.model
            )
            execution.status = "success"

            # Update template stats
            template.usage_count += 1
            template.last_used_at = datetime.now()

            self.session.commit()
            self.session.refresh(execution)

            # Update analytics
            self._update_analytics(template_id, execution)

            return execution

        except Exception as e:
            execution.status = "failed"
            execution.error_message = str(e)
            self.session.commit()
            raise

    async def _execute_single(
        self,
        template: ResearchTemplate,
        query: str
    ) -> Dict[str, Any]:
        """Execute single Perplexity query"""

        # Build payload
        payload = {
            "model": template.model,
            "messages": [{"role": "user", "content": query}],
            "max_tokens": template.max_tokens,
            "temperature": template.temperature,
            "return_citations": True
        }

        # Add filters
        if template.domain_filter:
            payload["search_domain_filter"] = template.domain_filter
        if template.recency_filter:
            payload["search_recency_filter"] = template.recency_filter
        if template.json_schema:
            payload["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": "research_output",
                    "schema": template.json_schema
                }
            }

        # Execute API call
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.perplexity_url,
                headers={
                    "Authorization": f"Bearer {self.perplexity_api_key}",
                    "Content-Type": "application/json"
                },
                json=payload,
                timeout=60.0
            )
            response.raise_for_status()
            data = response.json()

        return {
            "response": data["choices"][0]["message"]["content"],
            "citations": data["choices"][0]["message"].get("citations", []),
            "tokens_used": data["usage"]["total_tokens"]
        }

    async def _execute_pipeline(
        self,
        template: ResearchTemplate,
        variables: Dict[str, str]
    ) -> Dict[str, Any]:
        """Execute multi-step pipeline"""

        if not template.pipeline_steps:
            raise ValueError("Pipeline template has no steps configured")

        results = []
        all_citations = []
        total_tokens = 0
        context = variables.copy()

        for step_config in template.pipeline_steps:
            # Render query with current context
            query = step_config["query"].format(**context)

            # Build temporary template for step
            step_template = ResearchTemplate(
                name=f"{template.name}_step_{step_config['step']}",
                template_type="single",
                model=step_config.get("model", template.model),
                query_template=query,
                domain_filter=step_config.get("domain_filter", template.domain_filter),
                recency_filter=step_config.get("recency_filter"),
                max_tokens=step_config.get("max_tokens", template.max_tokens),
                temperature=step_config.get("temperature", template.temperature)
            )

            # Execute step
            step_result = await self._execute_single(step_template, query)

            # Store results
            results.append({
                "step": step_config["step"],
                "query": query,
                "response": step_result["response"],
                "citations": step_result["citations"]
            })

            all_citations.extend(step_result["citations"])
            total_tokens += step_result["tokens_used"]

            # Update context for next step
            context[f"step_{step_config['step']}_result"] = step_result["response"]

        # Combine results
        combined = self._combine_pipeline_results(results)

        return {
            "response": combined,
            "citations": list(set(all_citations)),  # Deduplicate
            "tokens_used": total_tokens,
            "pipeline_results": results
        }

    def _combine_pipeline_results(self, results: List[Dict]) -> str:
        """Combine pipeline step results"""
        combined = "# Multi-Step Research Results\n\n"

        for result in results:
            combined += f"## Step {result['step']}\n"
            combined += f"**Query:** {result['query']}\n\n"
            combined += f"{result['response']}\n\n"
            combined += "---\n\n"

        return combined

    def _calculate_cost(self, tokens_used: int, model: str) -> float:
        """Calculate cost estimate"""
        pricing = {
            "sonar": 0.0003,      # $0.30 per 1M tokens
            "sonar-pro": 0.0009   # $0.90 per 1M tokens
        }
        rate = pricing.get(model, pricing["sonar-pro"])
        return (tokens_used / 1000) * rate

    def _update_analytics(self, template_id: int, execution: ResearchExecution):
        """Update daily analytics"""
        from sqlalchemy import func

        today = date.today()

        # Get or create analytics record
        analytics = self.session.exec(
            select(ResearchCostAnalytics).where(
                ResearchCostAnalytics.date == today,
                ResearchCostAnalytics.template_id == template_id
            )
        ).first()

        if not analytics:
            analytics = ResearchCostAnalytics(
                date=today,
                template_id=template_id
            )
            self.session.add(analytics)

        # Update aggregates
        analytics.total_executions += 1
        analytics.total_tokens += execution.tokens_used or 0
        analytics.total_cost += execution.cost_estimate or 0.0

        # Recalculate averages
        executions_today = self.session.exec(
            select(ResearchExecution).where(
                ResearchExecution.template_id == template_id,
                func.date(ResearchExecution.executed_at) == today,
                ResearchExecution.status == "success"
            )
        ).all()

        if executions_today:
            analytics.avg_latency_ms = sum(
                e.latency_ms or 0 for e in executions_today
            ) / len(executions_today)

            analytics.avg_citations = sum(
                len(e.citations or []) for e in executions_today
            ) / len(executions_today)

        self.session.commit()

    # Analytics

    def get_template_analytics(
        self,
        template_id: int,
        days: int = 30
    ) -> Dict[str, Any]:
        """Get analytics for template"""
        from datetime import timedelta

        start_date = date.today() - timedelta(days=days)

        analytics = self.session.exec(
            select(ResearchCostAnalytics).where(
                ResearchCostAnalytics.template_id == template_id,
                ResearchCostAnalytics.date >= start_date
            ).order_by(ResearchCostAnalytics.date)
        ).all()

        return {
            "template_id": template_id,
            "period_days": days,
            "total_executions": sum(a.total_executions for a in analytics),
            "total_tokens": sum(a.total_tokens for a in analytics),
            "total_cost": sum(a.total_cost for a in analytics),
            "avg_latency_ms": (
                sum(a.avg_latency_ms or 0 for a in analytics) / len(analytics)
                if analytics else 0
            ),
            "avg_citations": (
                sum(a.avg_citations or 0 for a in analytics) / len(analytics)
                if analytics else 0
            ),
            "daily_breakdown": [
                {
                    "date": str(a.date),
                    "executions": a.total_executions,
                    "tokens": a.total_tokens,
                    "cost": float(a.total_cost)
                }
                for a in analytics
            ]
        }
```

### API Routes

**File:** `app/research/routes.py`

```python
"""
Research API Routes

Conditional routes - only registered when RESEARCH_ENABLED=true
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session
from typing import List, Optional

from app.database import get_session
from .service import ResearchTemplateService
from .models import ResearchTemplate

router = APIRouter(
    prefix="/api/research",
    tags=["Research Templates"]
)


@router.get("/templates")
async def list_templates(
    template_type: Optional[str] = None,
    is_active: Optional[bool] = True,
    session: Session = Depends(get_session)
):
    """List all research templates"""
    service = ResearchTemplateService(session)
    templates = service.list_templates(template_type, is_active)

    return {
        "templates": [
            {
                "id": t.id,
                "name": t.name,
                "description": t.description,
                "template_type": t.template_type,
                "model": t.model,
                "usage_count": t.usage_count,
                "last_used_at": t.last_used_at.isoformat() if t.last_used_at else None,
                "is_active": t.is_active
            }
            for t in templates
        ]
    }


@router.get("/templates/{template_id}")
async def get_template(
    template_id: int,
    session: Session = Depends(get_session)
):
    """Get template by ID"""
    service = ResearchTemplateService(session)
    template = service.get_template(template_id)

    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    return template


@router.post("/templates")
async def create_template(
    data: dict,
    session: Session = Depends(get_session)
):
    """Create new template"""
    service = ResearchTemplateService(session)
    template = service.create_template(data)

    return {
        "id": template.id,
        "name": template.name,
        "message": "Template created successfully"
    }


@router.put("/templates/{template_id}")
async def update_template(
    template_id: int,
    data: dict,
    session: Session = Depends(get_session)
):
    """Update template"""
    service = ResearchTemplateService(session)

    try:
        template = service.update_template(template_id, data)
        return {"message": "Template updated successfully"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/templates/{template_id}")
async def delete_template(
    template_id: int,
    session: Session = Depends(get_session)
):
    """Delete template (soft delete)"""
    service = ResearchTemplateService(session)

    if service.delete_template(template_id):
        return {"message": "Template deleted successfully"}
    else:
        raise HTTPException(status_code=404, detail="Template not found")


@router.post("/templates/{template_id}/execute")
async def execute_template(
    template_id: int,
    request: dict,
    session: Session = Depends(get_session)
):
    """Execute research template"""
    service = ResearchTemplateService(session)

    try:
        execution = await service.execute_template(
            template_id,
            variables=request.get("variables", {}),
            triggered_by=request.get("triggered_by", "api")
        )

        return {
            "execution_id": execution.id,
            "status": execution.status,
            "response": execution.response,
            "citations": execution.citations,
            "tokens_used": execution.tokens_used,
            "latency_ms": execution.latency_ms,
            "cost_estimate": float(execution.cost_estimate) if execution.cost_estimate else 0.0
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Execution failed: {str(e)}")


@router.get("/templates/{template_id}/analytics")
async def get_template_analytics(
    template_id: int,
    days: int = 30,
    session: Session = Depends(get_session)
):
    """Get analytics for template"""
    service = ResearchTemplateService(session)
    return service.get_template_analytics(template_id, days)
```

### Module Initialization

**File:** `app/research/__init__.py`

```python
"""
Research Templates Module

Optional module controlled by RESEARCH_ENABLED feature flag.
When disabled, this module is not loaded.
"""

from app.core.config import settings

ENABLED = settings.research_enabled

if ENABLED:
    print("✓ Research System: Enabled")

    # Initialize database on first import (development only)
    if settings.debug and settings.research_use_separate_db:
        try:
            from .database import init_research_db
            init_research_db()
        except Exception as e:
            print(f"⚠ Research DB initialization failed: {e}")
else:
    print("ℹ Research System: Disabled (set RESEARCH_ENABLED=true to enable)")
```

### Main App Integration

**File:** `app/core/config.py` (Minimal changes)

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # ... existing settings ...

    # Research Feature Flags (NEU)
    research_enabled: bool = False
    research_use_separate_db: bool = False
    research_database_url: str | None = None

    class Config:
        env_file = ".env"

settings = Settings()
```

**File:** `app/main.py` (Minimal changes)

```python
from fastapi import FastAPI
from app.core.config import settings

app = FastAPI(title="News-MCP")

# ... existing routes registration ...

# Conditional Research Routes (NEU: +4 Zeilen)
if settings.research_enabled:
    from app.research.routes import router as research_router
    app.include_router(research_router)
    print("✓ Research routes registered")
```

---

## Frontend Implementation

### Templates List Page

**File:** `templates/research/templates_list.html`

```html
{% extends "base.html" %}

{% block title %}Research Templates{% endblock %}

{% block content %}
<div class="d-flex justify-content-between align-items-center mb-4">
    <h1><i class="bi bi-search"></i> Research Templates</h1>
    <a href="/admin/research-templates/create" class="btn btn-primary">
        <i class="bi bi-plus-circle"></i> New Template
    </a>
</div>

<!-- Filter Tabs -->
<ul class="nav nav-tabs mb-3" id="type-filter">
    <li class="nav-item">
        <a class="nav-link active" data-type="all">All</a>
    </li>
    <li class="nav-item">
        <a class="nav-link" data-type="domain_filtered">Domain Filtered</a>
    </li>
    <li class="nav-item">
        <a class="nav-link" data-type="structured">Structured</a>
    </li>
    <li class="nav-item">
        <a class="nav-link" data-type="pipeline">Pipeline</a>
    </li>
    <li class="nav-item">
        <a class="nav-link" data-type="time_filtered">Time Filtered</a>
    </li>
</ul>

<!-- Templates Grid -->
<div class="row" id="templates-grid">
    <div class="col-12 text-center py-5">
        <div class="spinner-border" role="status"></div>
        <p>Loading templates...</p>
    </div>
</div>

<script>
let templates = [];

async function loadTemplates() {
    try {
        const response = await fetch('/api/research/templates');
        const data = await response.json();
        templates = data.templates;
        renderTemplates();
    } catch (error) {
        document.getElementById('templates-grid').innerHTML = `
            <div class="col-12">
                <div class="alert alert-danger">
                    Failed to load templates: ${error.message}
                </div>
            </div>
        `;
    }
}

function renderTemplates(filterType = 'all') {
    const grid = document.getElementById('templates-grid');

    const filtered = filterType === 'all'
        ? templates
        : templates.filter(t => t.template_type === filterType);

    if (filtered.length === 0) {
        grid.innerHTML = `
            <div class="col-12 text-center py-5">
                <p class="text-muted">No templates found</p>
            </div>
        `;
        return;
    }

    grid.innerHTML = filtered.map(t => `
        <div class="col-md-6 col-lg-4 mb-3">
            <div class="card h-100">
                <div class="card-body">
                    <div class="d-flex justify-content-between align-items-start mb-2">
                        <h5 class="card-title">${t.name}</h5>
                        <span class="badge bg-${getTypeBadgeColor(t.template_type)}">
                            ${t.template_type}
                        </span>
                    </div>

                    <p class="card-text text-muted small">${t.description || ''}</p>

                    <div class="small mb-3">
                        <div><strong>Model:</strong> ${t.model}</div>
                        <div><strong>Used:</strong> ${t.usage_count} times</div>
                    </div>

                    <div class="btn-group w-100">
                        <a href="/admin/research-templates/${t.id}/edit"
                           class="btn btn-sm btn-outline-primary">
                            <i class="bi bi-pencil"></i> Edit
                        </a>
                        <button class="btn btn-sm btn-outline-success"
                                onclick="testTemplate(${t.id})">
                            <i class="bi bi-play"></i> Test
                        </button>
                        <a href="/admin/research-templates/${t.id}/analytics"
                           class="btn btn-sm btn-outline-info">
                            <i class="bi bi-graph-up"></i> Stats
                        </a>
                    </div>
                </div>
            </div>
        </div>
    `).join('');
}

function getTypeBadgeColor(type) {
    const colors = {
        'domain_filtered': 'primary',
        'structured': 'success',
        'pipeline': 'warning',
        'time_filtered': 'info'
    };
    return colors[type] || 'secondary';
}

// Tab filtering
document.getElementById('type-filter').addEventListener('click', (e) => {
    if (e.target.tagName === 'A') {
        e.preventDefault();
        document.querySelectorAll('.nav-link').forEach(l => l.classList.remove('active'));
        e.target.classList.add('active');
        renderTemplates(e.target.dataset.type);
    }
});

// Load on page load
loadTemplates();
</script>
{% endblock %}
```

### Template Editor (Split-View)

**File:** `templates/research/template_edit.html`

```html
{% extends "base.html" %}

{% block title %}Edit Template{% endblock %}

{% block content %}
<div class="mb-3">
    <a href="/admin/research-templates" class="btn btn-sm btn-outline-secondary">
        <i class="bi bi-arrow-left"></i> Back
    </a>
</div>

<h1 class="mb-4">{{ template.name if template else 'New Template' }}</h1>

<!-- Split View -->
<div class="row">
    <!-- Left: Configuration -->
    <div class="col-lg-6">
        <div class="card">
            <div class="card-header">
                <h5 class="mb-0">Configuration</h5>
            </div>
            <div class="card-body">
                <form id="templateForm">
                    <div class="mb-3">
                        <label class="form-label">Name</label>
                        <input type="text" class="form-control" name="name"
                               value="{{ template.name if template else '' }}" required>
                    </div>

                    <div class="mb-3">
                        <label class="form-label">Description</label>
                        <textarea class="form-control" name="description" rows="2">{{ template.description if template else '' }}</textarea>
                    </div>

                    <div class="mb-3">
                        <label class="form-label">Type</label>
                        <select class="form-select" name="template_type" required>
                            <option value="domain_filtered">Domain Filtered</option>
                            <option value="structured">Structured JSON</option>
                            <option value="pipeline">Multi-Step Pipeline</option>
                            <option value="time_filtered">Time Filtered</option>
                        </select>
                    </div>

                    <div class="mb-3">
                        <label class="form-label">Model</label>
                        <select class="form-select" name="model">
                            <option value="sonar">sonar (Fast, Cheap)</option>
                            <option value="sonar-pro" selected>sonar-pro (Deep, Expensive)</option>
                        </select>
                    </div>

                    <div class="mb-3">
                        <label class="form-label">Query Template</label>
                        <textarea class="form-control font-monospace" name="query_template"
                                  rows="4" required>{{ template.query_template if template else '' }}</textarea>
                        <small class="text-muted">Use {topic}, {context} as variables</small>
                    </div>

                    <div class="mb-3">
                        <label class="form-label">Domain Filter (one per line)</label>
                        <textarea class="form-control font-monospace" name="domain_filter" rows="3"></textarea>
                        <small class="text-muted">e.g., reuters.com, .gov, arxiv.org</small>
                    </div>

                    <div class="mb-3">
                        <label class="form-label">Recency Filter</label>
                        <select class="form-select" name="recency_filter">
                            <option value="">None</option>
                            <option value="day">Last 24 Hours</option>
                            <option value="week">Last Week</option>
                            <option value="month">Last Month</option>
                        </select>
                    </div>

                    <div class="d-flex gap-2">
                        <button type="submit" class="btn btn-primary flex-fill">
                            <i class="bi bi-save"></i> Save
                        </button>
                        <button type="button" class="btn btn-outline-secondary" onclick="location.reload()">
                            Reset
                        </button>
                    </div>
                </form>
            </div>
        </div>
    </div>

    <!-- Right: Live Test -->
    <div class="col-lg-6">
        <div class="card sticky-top" style="top: 20px;">
            <div class="card-header">
                <h5 class="mb-0">Live Test</h5>
            </div>
            <div class="card-body">
                <div class="mb-3">
                    <label class="form-label">Test Variables</label>
                    <textarea class="form-control font-monospace" id="testVariables" rows="4">{
  "topic": "European energy crisis"
}</textarea>
                </div>

                <button class="btn btn-success w-100 mb-3" onclick="runTest()">
                    <i class="bi bi-play-circle"></i> Run Test
                </button>

                <div id="testResults" style="display: none;">
                    <div class="alert alert-info">
                        <strong>Results</strong>
                        <span class="badge bg-info float-end" id="testCost"></span>
                    </div>

                    <div class="mb-3">
                        <label class="small text-muted">Response</label>
                        <div class="border rounded p-3 bg-light" id="testResponse"
                             style="max-height: 300px; overflow-y: auto;"></div>
                    </div>

                    <div class="mb-3">
                        <label class="small text-muted">Citations</label>
                        <ul class="list-unstyled small" id="testCitations"></ul>
                    </div>

                    <div class="row small text-muted">
                        <div class="col-6">Tokens: <span id="testTokens"></span></div>
                        <div class="col-6">Latency: <span id="testLatency"></span>ms</div>
                    </div>
                </div>

                <div id="testLoading" style="display: none;" class="text-center py-4">
                    <div class="spinner-border text-primary"></div>
                    <p class="mt-2">Running query...</p>
                </div>

                <div id="testError" style="display: none;" class="alert alert-danger"></div>
            </div>
        </div>
    </div>
</div>

<script>
const templateId = {{ template.id if template else 'null' }};

document.getElementById('templateForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const formData = new FormData(e.target);
    const data = Object.fromEntries(formData);

    // Parse domain filter
    if (data.domain_filter) {
        data.domain_filter = data.domain_filter.split('\n').filter(d => d.trim());
    }

    const url = templateId
        ? `/api/research/templates/${templateId}`
        : '/api/research/templates';

    const method = templateId ? 'PUT' : 'POST';

    try {
        const response = await fetch(url, {
            method,
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(data)
        });

        if (response.ok) {
            alert('Template saved!');
            if (!templateId) {
                const result = await response.json();
                window.location.href = `/admin/research-templates/${result.id}/edit`;
            }
        } else {
            alert('Failed to save template');
        }
    } catch (error) {
        alert('Error: ' + error.message);
    }
});

async function runTest() {
    if (!templateId) {
        alert('Please save template first');
        return;
    }

    const variables = JSON.parse(document.getElementById('testVariables').value);

    document.getElementById('testResults').style.display = 'none';
    document.getElementById('testError').style.display = 'none';
    document.getElementById('testLoading').style.display = 'block';

    try {
        const response = await fetch(`/api/research/templates/${templateId}/execute`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({variables})
        });

        if (!response.ok) throw new Error('Test failed');

        const data = await response.json();

        document.getElementById('testLoading').style.display = 'none';
        document.getElementById('testResults').style.display = 'block';

        document.getElementById('testResponse').innerText = data.response;
        document.getElementById('testCost').innerText = `$${data.cost_estimate.toFixed(4)}`;
        document.getElementById('testTokens').innerText = data.tokens_used;
        document.getElementById('testLatency').innerText = data.latency_ms;

        const citationsList = document.getElementById('testCitations');
        citationsList.innerHTML = (data.citations || []).map(url =>
            `<li><a href="${url}" target="_blank"><i class="bi bi-link-45deg"></i> ${url}</a></li>`
        ).join('');

    } catch (error) {
        document.getElementById('testLoading').style.display = 'none';
        document.getElementById('testError').style.display = 'block';
        document.getElementById('testError').innerText = 'Error: ' + error.message;
    }
}
</script>
{% endblock %}
```

### Web Views

**File:** `app/research/views.py`

```python
"""
Research Web UI Views

Conditional views - only registered when RESEARCH_ENABLED=true
"""

from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session

from app.core.config import settings
from app.database import get_session
from .service import ResearchTemplateService

router = APIRouter(prefix="/admin/research-templates", tags=["Research UI"])
templates = Jinja2Templates(directory="templates")


@router.get("", response_class=HTMLResponse)
async def templates_list(request: Request):
    """Templates list page"""
    if not settings.research_enabled:
        raise HTTPException(status_code=404, detail="Research system disabled")

    return templates.TemplateResponse(
        "research/templates_list.html",
        {"request": request}
    )


@router.get("/{template_id}/edit", response_class=HTMLResponse)
async def template_edit(
    request: Request,
    template_id: int,
    session: Session = Depends(get_session)
):
    """Template editor page"""
    if not settings.research_enabled:
        raise HTTPException(status_code=404, detail="Research system disabled")

    service = ResearchTemplateService(session)
    template = service.get_template(template_id)

    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    return templates.TemplateResponse(
        "research/template_edit.html",
        {"request": request, "template": template}
    )


@router.get("/create", response_class=HTMLResponse)
async def template_create(request: Request):
    """Create template page"""
    if not settings.research_enabled:
        raise HTTPException(status_code=404, detail="Research system disabled")

    return templates.TemplateResponse(
        "research/template_edit.html",
        {"request": request, "template": None}
    )
```

**Register Web Views in main.py:**

```python
# app/main.py

if settings.research_enabled:
    from app.research.routes import router as research_api_router
    from app.research.views import router as research_web_router

    app.include_router(research_api_router)
    app.include_router(research_web_router)
```

---

## MCP Integration

### Perplexity Tools for Claude Desktop

**File:** `mcp_server/perplexity_tools.py`

```python
"""
Perplexity MCP Tools

Exposes Perplexity research capabilities to Claude Desktop via MCP
"""

from typing import List, Optional
from mcp.types import Tool, TextContent
import httpx

from app.core.config import settings


async def perplexity_search(
    query: str,
    model: str = "sonar-pro",
    domain_filter: Optional[List[str]] = None,
    recency_filter: Optional[str] = None
) -> List[TextContent]:
    """
    Execute Perplexity search query

    Simple wrapper for direct web search via Perplexity
    """

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": query}],
        "max_tokens": 2000,
        "temperature": 0.2,
        "return_citations": True
    }

    if domain_filter:
        payload["search_domain_filter"] = domain_filter
    if recency_filter:
        payload["search_recency_filter"] = recency_filter

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.perplexity.ai/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.perplexity_api_key}",
                "Content-Type": "application/json"
            },
            json=payload,
            timeout=60.0
        )
        response.raise_for_status()
        data = response.json()

    answer = data["choices"][0]["message"]["content"]
    citations = data["choices"][0]["message"].get("citations", [])

    result = f"{answer}\n\n"
    if citations:
        result += "## Sources\n"
        for i, url in enumerate(citations, 1):
            result += f"{i}. {url}\n"

    return [TextContent(type="text", text=result)]


async def research_with_context(
    query: str,
    article_context: bool = True,
    impact_min: float = 0.7,
    timeframe_hours: int = 24,
    model: str = "sonar-pro"
) -> List[TextContent]:
    """
    Research using Perplexity with News-MCP article context

    Combines News-MCP database articles with Perplexity web search
    """

    context_articles = []

    if article_context:
        # Get relevant articles from database
        from app.database import engine
        from app.models.items import Item
        from app.models.analysis import ItemAnalysis
        from sqlmodel import Session, select
        from datetime import datetime, timedelta

        cutoff = datetime.now() - timedelta(hours=timeframe_hours)

        with Session(engine) as session:
            articles = session.exec(
                select(Item)
                .join(ItemAnalysis)
                .where(
                    Item.published >= cutoff,
                    ItemAnalysis.impact_score >= impact_min
                )
                .order_by(ItemAnalysis.impact_score.desc())
                .limit(10)
            ).all()

            context_articles = [
                f"- {a.title} (Impact: {a.analysis.impact_score:.2f})"
                for a in articles
            ]

    # Build query with context
    perplexity_query = query
    if context_articles:
        perplexity_query = f"""Context from News-MCP database:
{chr(10).join(context_articles)}

Research Question: {query}

Analyze considering both the article context and current web information.
"""

    # Execute Perplexity search
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.perplexity.ai/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.perplexity_api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": model,
                "messages": [{"role": "user", "content": perplexity_query}],
                "max_tokens": 3000,
                "temperature": 0.2,
                "return_citations": True
            },
            timeout=90.0
        )
        response.raise_for_status()
        data = response.json()

    answer = data["choices"][0]["message"]["content"]
    citations = data["choices"][0]["message"].get("citations", [])
    tokens = data["usage"]["total_tokens"]

    result = "# Research Results\n\n"

    if context_articles:
        result += "## News-MCP Context\n"
        result += f"Analyzed {len(context_articles)} recent high-impact articles\n\n"

    result += "## Analysis\n"
    result += f"{answer}\n\n"

    if citations:
        result += "## External Sources\n"
        for i, url in enumerate(citations, 1):
            result += f"{i}. {url}\n"

    result += f"\n---\n**Tokens:** {tokens} | **Model:** {model}\n"

    return [TextContent(type="text", text=result)]


# Tool Definitions
PERPLEXITY_TOOLS = [
    Tool(
        name="perplexity_search",
        description="""Search the web using Perplexity AI with real-time information and citations.

Use when you need:
- Current, up-to-date web information
- Factual answers with verified sources
- Research on recent events or topics
- Domain-specific research (academic, news, government)

Examples:
- "Latest developments in quantum computing"
- "Current European energy crisis status"
- "Recent AI regulation policies"
""",
        inputSchema={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query or research question"
                },
                "model": {
                    "type": "string",
                    "enum": ["sonar", "sonar-pro"],
                    "default": "sonar-pro",
                    "description": "sonar (fast, cheap) or sonar-pro (deep, expensive)"
                },
                "domain_filter": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Limit to specific domains (e.g., ['reuters.com', '.gov'])"
                },
                "recency_filter": {
                    "type": "string",
                    "enum": ["day", "week", "month", "year"],
                    "description": "Time filter for results"
                }
            },
            "required": ["query"]
        }
    ),

    Tool(
        name="research_with_context",
        description="""Research using Perplexity AI combined with News-MCP article database.

Combines:
1. High-impact articles from News-MCP database
2. Real-time web search from Perplexity
3. Dual source citations

Use when you want:
- Research grounded in tracked news articles
- Web-verified information about analyzed topics
- Context-aware analysis combining internal + external sources

Best for topics related to tracked news feeds.
""",
        inputSchema={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Research question"
                },
                "article_context": {
                    "type": "boolean",
                    "default": True,
                    "description": "Include News-MCP articles as context"
                },
                "impact_min": {
                    "type": "number",
                    "default": 0.7,
                    "description": "Minimum impact score for context articles"
                },
                "timeframe_hours": {
                    "type": "integer",
                    "default": 24,
                    "description": "Timeframe for context articles (hours)"
                },
                "model": {
                    "type": "string",
                    "enum": ["sonar", "sonar-pro"],
                    "default": "sonar-pro"
                }
            },
            "required": ["query"]
        }
    )
]
```

**Register in comprehensive_server.py:**

```python
# mcp_server/comprehensive_server.py

from mcp_server.perplexity_tools import PERPLEXITY_TOOLS, perplexity_search, research_with_context

class ComprehensiveNewsServer:
    def _setup_tools(self):
        # ... existing tools ...

        # Add Perplexity tools
        for tool in PERPLEXITY_TOOLS:
            self.server.tools.append(tool)

        # Register handlers
        @self.server.call_tool()
        async def call_tool(name: str, arguments: dict):
            if name == "perplexity_search":
                return await perplexity_search(**arguments)
            elif name == "research_with_context":
                return await research_with_context(**arguments)
            # ... existing handlers ...
```

---

## Implementation Phases

### Phase 1: Foundation (Week 1)

**Goal:** Basic structure + Feature flags

**Tasks:**
- [ ] Add feature flags to config
- [ ] Create `app/research/` module structure
- [ ] Implement basic models
- [ ] Create database schema (optional migration)
- [ ] Test: Feature flag disables/enables correctly

**Deliverables:**
- `app/research/__init__.py`
- `app/research/models.py`
- `app/research/database.py`
- Feature flags working

**Testing:**
```bash
# Disabled
RESEARCH_ENABLED=false
./scripts/start-api.sh
# → No /api/research routes

# Enabled
RESEARCH_ENABLED=true
./scripts/start-api.sh
# → /api/research routes available
```

### Phase 2: Backend (Week 2)

**Goal:** Service layer + API

**Tasks:**
- [ ] Implement ResearchTemplateService
- [ ] CRUD operations
- [ ] Perplexity integration
- [ ] API routes
- [ ] Unit tests

**Deliverables:**
- `app/research/service.py`
- `app/research/routes.py`
- API endpoints functional

**Testing:**
```bash
# Create template
curl -X POST http://localhost:8000/api/research/templates \
  -H "Content-Type: application/json" \
  -d '{"name":"Test","template_type":"domain_filtered",...}'

# Execute template
curl -X POST http://localhost:8000/api/research/templates/1/execute \
  -d '{"variables":{"topic":"AI regulation"}}'
```

### Phase 3: Frontend (Week 3)

**Goal:** Web UI

**Tasks:**
- [ ] Templates list page
- [ ] Template editor (split-view)
- [ ] Live test functionality
- [ ] Analytics dashboard
- [ ] Web views routing

**Deliverables:**
- `templates/research/templates_list.html`
- `templates/research/template_edit.html`
- `app/research/views.py`

**Testing:**
```bash
# Navigate to:
http://localhost:8000/admin/research-templates

# Create/Edit template via UI
# Test execution via Live Test panel
```

### Phase 4: MCP Integration (Week 4)

**Goal:** Claude Desktop integration

**Tasks:**
- [ ] Implement perplexity_search MCP tool
- [ ] Implement research_with_context MCP tool
- [ ] Register tools in comprehensive_server
- [ ] Test with Claude Desktop
- [ ] Add MCP resource for guidance

**Deliverables:**
- `mcp_server/perplexity_tools.py`
- Tools in comprehensive_server.py
- MCP resource for when to use Perplexity

**Testing:**
```bash
# Via Claude Desktop:
"Search Perplexity for: latest AI developments"

"Research European energy crisis using our articles + web"
```

### Phase 5: Polish & Documentation (Week 5)

**Goal:** Production ready

**Tasks:**
- [ ] Cost tracking dashboard
- [ ] Analytics visualization
- [ ] Error handling improvements
- [ ] Performance optimization
- [ ] User documentation
- [ ] Admin guide

**Deliverables:**
- Complete documentation
- Production deployment guide
- User training materials

---

## Testing Strategy

### Unit Tests

**File:** `tests/test_research_service.py`

```python
import pytest
from sqlmodel import Session, create_engine, SQLModel
from app.research.models import ResearchTemplate
from app.research.service import ResearchTemplateService

@pytest.fixture
def test_db():
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    yield engine

@pytest.fixture
def test_session(test_db):
    with Session(test_db) as session:
        yield session

def test_create_template(test_session):
    service = ResearchTemplateService(test_session)

    template = service.create_template({
        "name": "Test Template",
        "template_type": "domain_filtered",
        "model": "sonar-pro",
        "query_template": "Test: {topic}"
    })

    assert template.id is not None
    assert template.name == "Test Template"

def test_list_templates(test_session):
    service = ResearchTemplateService(test_session)

    service.create_template({
        "name": "Template 1",
        "template_type": "domain_filtered",
        "query_template": "Test"
    })

    templates = service.list_templates()
    assert len(templates) == 1
```

**Run tests:**
```bash
# Only run if research enabled
RESEARCH_ENABLED=true pytest tests/test_research* -v
```

### Integration Tests

**File:** `tests/test_research_api.py`

```python
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_list_templates_endpoint():
    response = client.get("/api/research/templates")
    assert response.status_code == 200
    assert "templates" in response.json()

def test_create_template_endpoint():
    response = client.post("/api/research/templates", json={
        "name": "API Test Template",
        "template_type": "domain_filtered",
        "model": "sonar-pro",
        "query_template": "Test: {topic}"
    })
    assert response.status_code == 200
    assert "id" in response.json()
```

### Manual Testing Checklist

**Backend:**
- [ ] Create template via API
- [ ] List templates
- [ ] Update template
- [ ] Delete template
- [ ] Execute template (with mock Perplexity)
- [ ] Get analytics

**Frontend:**
- [ ] Load templates list page
- [ ] Filter by type
- [ ] Create new template via UI
- [ ] Edit existing template
- [ ] Live test execution
- [ ] View analytics dashboard

**MCP:**
- [ ] Claude Desktop sees perplexity_search tool
- [ ] Claude Desktop sees research_with_context tool
- [ ] Execute search via Claude Desktop
- [ ] Results include citations

---

## Deployment & Rollback

### Environment Configuration

**Development:**
```bash
# .env
RESEARCH_ENABLED=false
```

**Staging:**
```bash
# .env.staging
RESEARCH_ENABLED=true
RESEARCH_USE_SEPARATE_DB=true
RESEARCH_DATABASE_URL=postgresql://news_user:news_password@localhost:5432/news_research_staging
```

**Production:**
```bash
# .env.production
RESEARCH_ENABLED=true
RESEARCH_USE_SEPARATE_DB=false
# Uses main DB with schema 'research'
```

### Deployment Checklist

**Pre-Deployment:**
- [ ] All tests passing
- [ ] Code reviewed
- [ ] Database migration ready (if needed)
- [ ] Backup strategy in place
- [ ] Rollback plan documented

**Deployment Steps:**
1. Backup database
2. Deploy code
3. Run migrations (if separate DB)
4. Enable feature flag
5. Restart application
6. Verify routes available
7. Smoke test UI
8. Monitor logs

**Post-Deployment:**
- [ ] Routes responding
- [ ] UI loads correctly
- [ ] Create test template
- [ ] Execute test query
- [ ] Check analytics
- [ ] Monitor performance

### Rollback Procedures

**Level 1: Feature Flag Rollback** (Instant)
```bash
# .env
RESEARCH_ENABLED=false

# Restart
./scripts/start-api.sh

# Research immediately disabled ✅
```

**Level 2: Code Rollback** (If needed)
```bash
git revert HEAD  # or specific commit
git push

# Redeploy
# Research code removed
```

**Level 3: Database Rollback** (If needed)
```bash
# Separate DB:
DROP DATABASE news_research_db;

# Schema in main DB:
DROP SCHEMA research CASCADE;

# Main application unaffected ✅
```

### Monitoring

**Metrics to track:**
- API response times (`/api/research/*`)
- Perplexity API call count
- Token usage & costs
- Error rates
- Template execution success rate

**Logs to monitor:**
```bash
# Research-specific logs
tail -f logs/app.log | grep "research"

# Perplexity API calls
tail -f logs/app.log | grep "perplexity"

# Errors
tail -f logs/app.log | grep "ERROR.*research"
```

**Alerts:**
- High Perplexity costs (> $X/day)
- High error rate in research execution
- Slow response times (> 60s for Perplexity calls)

---

## Success Criteria

### MVP (Minimum Viable Product)

- [ ] User can create research templates via UI
- [ ] User can execute templates manually
- [ ] Results displayed with citations
- [ ] Cost tracking works
- [ ] Feature flag enables/disables system
- [ ] Zero impact on main app when disabled

### Phase 2 (Full Features)

- [ ] All 5 template types work (domain, structured, pipeline, time, analytics)
- [ ] Live test shows results before saving
- [ ] Analytics dashboard shows usage/costs
- [ ] MCP tools available in Claude Desktop
- [ ] Templates can be used in Special Reports

### Production Ready

- [ ] Comprehensive error handling
- [ ] Performance optimized (< 60s for queries)
- [ ] Security reviewed
- [ ] Documentation complete
- [ ] Training materials ready
- [ ] Monitoring in place

---

## Conclusion

This guide provides a **complete, safe implementation strategy** for Research Templates using:

✅ **Feature Flags** - Safe, gradual activation
✅ **In-App Development** - No separate servers/CORS
✅ **Isolated Code** - Minimal changes to main app
✅ **Instant Rollback** - Feature flag disable
✅ **Flexible Database** - Separate DB or schema
✅ **MCP Integration** - Claude Desktop ready

**Next Steps:**
1. Review this guide
2. Start Phase 1 (Foundation)
3. Test feature flag mechanism
4. Proceed phase by phase

**Estimated Timeline:** 4-5 weeks total
**Risk Level:** Low (feature flag protection)
**Complexity:** Medium (well-structured)

---

**Document Version:** 1.0
**Last Updated:** 2025-10-05
**Status:** Ready for Implementation
