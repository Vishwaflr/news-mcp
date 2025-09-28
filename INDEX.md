# INDEX.md – News-MCP Datei-Map

**Zweck:** Vollständige Dateistruktur-Übersicht für schnelle Navigation
**Version:** 3.1.0
**Stand:** 2025-09-28
**Python-Dateien:** 132

---

## 📂 Projekt-Struktur (Top-Level)

```
news-mcp/
├── 📄 CLAUDE.md                    # Arbeitsregeln für Claude
├── 📄 NAVIGATOR.md                 # System-Navigator (3-Spalten, Hotspots, Roadmap)
├── 📄 ENDPOINTS.md                 # API-Gedächtnis (167 Endpunkte)
├── 📄 INDEX.md                     # Diese Datei
├── 📄 README.md                    # Haupt-Dokumentation
├── 📄 CHANGELOG.md                 # Version History
├── 📄 CONTRIBUTING.md              # Contribution Guidelines
├── 📄 LICENSE                      # MIT License
├── 📄 pyproject.toml               # Python Project Config
├── 📄 requirements.txt             # Python Dependencies
├── 📄 pytest.ini                   # Pytest Config
├── 📄 alembic.ini                  # Alembic Migrations Config
├── 📄 docker-compose.yml           # Docker Setup
├── 📄 .env.example                 # Environment Template
├── 📄 .ruff.toml                   # Ruff Linter Config
├── 📄 .pre-commit-config.yaml     # Pre-commit Hooks
│
├── 📁 app/                         # Application Code (132 .py Dateien)
├── 📁 templates/                   # Jinja2 Templates
├── 📁 static/                      # Static Assets (CSS, JS, Images)
├── 📁 docs/                        # Dokumentation (28 Dateien)
├── 📁 tests/                       # Test Suite
├── 📁 scripts/                     # Management Scripts
├── 📁 alembic/                     # Database Migrations
├── 📁 data/                        # Data Files
├── 📁 logs/                        # Log Files
├── 📁 tools/                       # Utility Tools
├── 📁 systemd/                     # Systemd Service Files
├── 📁 venv/                        # Virtual Environment (ignored)
└── 📁 .git/                        # Git Repository (ignored)
```

---

## 🎯 app/ – Application Code

### app/ (Root Level)
```
app/
├── __init__.py
├── main.py                         # FastAPI Application Entry Point
├── config.py                       # App Configuration
├── database.py                     # Database Connection & Tables
├── dependencies.py                 # FastAPI Dependencies
├── schemas.py                      # Pydantic Schemas (Legacy)
```

### app/api/ – API Routes (24 Dateien)
```
app/api/
├── __init__.py
├── feeds.py                        # Feed Management API
├── feeds_simple.py                 # Simple Feed List API
├── items.py                        # Item/Article API
├── health.py                       # Health Check API
├── categories.py                   # Categories API
├── sources.py                      # Sources API
├── templates.py                    # Template API
├── processors.py                   # Processor API
├── statistics.py                   # Statistics API
├── metrics.py                      # Metrics API
├── database.py                     # Database Admin API
├── scheduler.py                    # Scheduler API
├── feed_limits.py                  # Feed Limits API
├── system.py                       # System Control API
├── user_settings.py                # User Settings API
├── feature_flags_admin.py          # Feature Flags API
│
├── analysis_control.py             # Analysis Control (Legacy + Current)
├── analysis_management.py          # Centralized Run Manager API
├── analysis_selection.py           # Selection Cache API
├── analysis_jobs.py                # Job-based Preview System
├── analysis_worker_api.py          # Worker Control API
│
├── htmx.py                         # HTMX Components (Legacy)
└── websocket_endpoint.py           # WebSocket Endpoint
```

### app/services/ – Business Logic (22 Dateien)
```
app/services/
├── analysis_run_manager.py        # Run Lifecycle Manager
├── analysis_orchestrator.py       # Analysis Orchestration
├── selection_cache.py              # In-Memory Selection Cache
├── run_queue_manager.py            # Queue Management
├── queue_processor.py              # Queue Processing Logic
├── llm_client.py                   # OpenAI LLM Client
├── cost_estimator.py               # Cost Calculation
│
├── auto_analysis_service.py        # ✅ Auto-Analysis Service (Phase 2 Sprint 4)
├── pending_analysis_processor.py   # ✅ Pending Queue Processor (Phase 2 Sprint 4)
│
├── feed_scheduler.py               # Feed Scheduling
├── feed_fetcher_sync.py            # Feed Fetching
├── feed_limits_service.py          # Feed Rate Limiting
├── feed_change_tracker.py          # Feed Config Change Tracking
│
├── dynamic_template_manager.py     # Template Hot-Reload
├── configuration_watcher.py        # Config File Watcher
├── metrics_service.py              # Metrics Collection
│
└── domain/                         # Domain Services
    ├── __init__.py
    ├── base.py                     # Base Service
    ├── feed_service.py             # Feed Domain Logic
    ├── item_service.py             # Item Domain Logic
    ├── analysis_service.py         # Analysis Domain Logic
    ├── processor_service.py        # Processor Domain Logic
    └── job_service.py              # Job Domain Logic
```

### app/web/ – Web Views & Components
```
app/web/
├── __init__.py
├── items_htmx.py                   # Item HTMX Components (Legacy)
│
├── components/                     # Reusable HTMX Components
│   ├── __init__.py
│   ├── base_component.py           # Base Component Class
│   ├── feed_components.py          # Feed UI Components
│   ├── item_components.py          # Item UI Components
│   ├── item_components_new.py      # Item Components (New)
│   ├── system_components.py        # System UI Components
│   └── processor_components.py     # Processor UI Components
│
└── views/                          # HTMX View Handlers
    ├── __init__.py
    ├── feed_views.py               # Feed Views
    ├── item_views.py               # Item Views
    ├── system_views.py             # System Views
    ├── auto_analysis_views.py      # ✅ Auto-Analysis Views (Phase 2 Sprint 4)
    │
    └── analysis/                   # Analysis Cockpit Views
        ├── __init__.py
        ├── target_selection.py     # Target Selection View
        ├── preview.py              # Preview View
        ├── runs.py                 # Runs View
        ├── articles.py             # Articles View
        ├── stats.py                # Stats View
        └── settings.py             # Settings View
```

### app/worker/ – Background Workers
```
app/worker/
├── __init__.py
└── analysis_worker.py              # Analysis Worker Process
```

### app/models/ – Data Models
```
app/models/
├── __init__.py                     # SQLModel Models (Feeds, Items, Runs, etc.)
```

### app/schemas/ – Pydantic Schemas
```
app/schemas/
├── __init__.py                     # Request/Response Schemas
```

### app/core/ – Core Infrastructure
```
app/core/
├── __init__.py
├── config.py                       # Configuration Management
├── logging_config.py               # Structured Logging
├── health.py                       # Health Check System
├── error_handlers.py               # Exception Handlers
└── (future: metrics.py, tracing.py, resilience.py)
```

### app/repositories/ – Data Access Layer
```
app/repositories/
├── __init__.py
├── base_repository.py              # Base Repository Pattern
├── item_repository.py              # Item Data Access
└── (future: feed_repository.py, analysis_repository.py)
```

### app/processors/ – Content Processors
```
app/processors/
├── __init__.py
├── base_processor.py               # Base Processor
└── content_processor.py            # Content Processing Logic
```

### app/domain/ – Domain Models
```
app/domain/
├── __init__.py
├── models.py                       # Domain Models
└── events.py                       # Domain Events
```

### app/routes/ – Additional Routes
```
app/routes/
├── __init__.py
└── templates.py                    # Template Routes
```

### app/websocket/ – WebSocket Logic
```
app/websocket/
├── __init__.py
├── manager.py                      # WebSocket Connection Manager
└── handlers.py                     # WebSocket Event Handlers
```

### app/utils/ – Utilities
```
app/utils/
├── __init__.py
├── helpers.py                      # Helper Functions
└── validators.py                   # Validation Utilities
```

### app/jobs/ – Background Jobs
```
app/jobs/
├── __init__.py
└── (future: scheduled_jobs.py)
```

---

## 📄 templates/ – Jinja2 Templates

```
templates/
├── index.html                      # Dashboard Home
├── analysis_cockpit_v4.html        # Analysis Cockpit (Alpine.js v4)
│
├── admin/                          # Admin Pages
│   ├── feeds.html                  # Feed Management UI
│   ├── items.html                  # Item Browser UI
│   ├── health.html                 # Health Dashboard
│   ├── processors.html             # Processor Management
│   ├── statistics.html             # Statistics Dashboard
│   ├── database.html               # Database Admin
│   └── metrics.html                # Metrics Dashboard
│
└── components/                     # Reusable Components
    ├── feed_list.html              # Feed List Component
    ├── item_card.html              # Item Card Component
    ├── run_status.html             # Run Status Badge
    └── auto_analysis.html          # ✅ Auto-Analysis Component (Phase 2 Sprint 4)
```

---

## 🎨 static/ – Static Assets

```
static/
├── css/
│   ├── main.css                    # Main Stylesheet
│   ├── dark-mode.css               # Dark Mode Styles
│   └── components.css              # Component Styles
│
├── js/
│   ├── app.js                      # Main Application JS
│   ├── analysis.js                 # Analysis Cockpit Logic
│   └── htmx-extensions.js          # HTMX Custom Extensions
│
└── images/
    ├── logo.png                    # App Logo
    └── icons/                      # UI Icons
```

---

## 📚 docs/ – Dokumentation (28 Dateien)

```
docs/
├── README.md                       # Docs Overview
├── ARCHITECTURE.md                 # System Architecture
├── DATABASE_SCHEMA.md              # Database Schema Docs
├── ERD_MERMAID.md                  # Entity Relationship Diagram
├── API_DOCUMENTATION.md            # API Docs
├── API_EXAMPLES.md                 # API Usage Examples
├── DEVELOPER_SETUP.md              # Developer Setup Guide
├── DEPLOYMENT.md                   # Deployment Guide
├── TESTING.md                      # Testing Guide (im Root)
├── MONITORING.md                   # Monitoring Guide (im Root)
│
├── ANALYSIS_COCKPIT_REQUIREMENTS.md # Analysis Cockpit Specs
├── ANALYSIS_CONTROL_INTERFACE.md   # Analysis Control Docs
├── UI_COMPONENTS_GUIDE.md          # UI Components Guide
├── WORKER_README.md                # Worker Documentation
├── OPEN_WEBUI_INTEGRATION.md       # Open WebUI Integration
├── MCP_SERVER_README.md            # MCP Server Docs (im Root)
│
├── FEATURE_FLAGS.md                # Feature Flags Guide
├── SCHEMA_IMPORT_WORKAROUND.md     # Schema Import Fix
├── REPOSITORY_POLICY.md            # Repository Pattern Policy
├── REPOSITORY_CUTOVER_PATTERN.md   # Cutover Strategy
├── DOCUMENTATION_STATUS.md         # Docs Status Tracking
│
├── RELEASE_NOTES_3.4.md            # Release Notes v3.4
│
├── GO_LIVE_CHECKLIST.md            # General Go-Live Checklist
├── GO_LIVE_CHECKLIST_FEEDS.md      # Feeds Go-Live Checklist
├── GO_LIVE_CHECKLIST_ANALYSIS.md   # Analysis Go-Live Checklist
├── GO_LIVE_CHECKLIST_STATISTICS.md # Statistics Go-Live Checklist
├── GO_LIVE_CHECKLIST_TEMPLATE.md   # Go-Live Template
│
└── archive/                        # Archived Docs
    ├── README.md                   # Archive Overview
    ├── FIXES_DOCUMENTATION.md      # Historical Fixes
    └── sqlproblem.md               # SQL Issue Documentation
```

---

## 🧪 tests/ – Test Suite

```
tests/
├── __init__.py
│
├── unit/                           # Unit Tests
│   ├── test_services.py
│   ├── test_models.py
│   └── test_utils.py
│
├── integration/                    # Integration Tests
│   ├── test_api.py
│   ├── test_database.py
│   └── test_workers.py
│
├── contract/                       # Contract Tests (5 Tests)
│   ├── test_feed_contract.py
│   ├── test_analysis_contract.py
│   ├── test_auto_analysis_contract.py  # ✅ Phase 2 Sprint 4
│   ├── test_api_contract.py
│   └── test_schema_contract.py
│
└── load/                           # Load Tests
    └── locustfile.py
```

---

## 🛠️ scripts/ – Management Scripts

```
scripts/
├── start-web-server.sh             # Web Server Starter
├── start-worker.sh                 # Worker Starter
├── start-scheduler.sh              # Scheduler Starter
├── start-all-background.sh         # Start All Services
├── stop-all.sh                     # Stop All Services
├── status.sh                       # Service Status
├── service-manager.sh              # Service Manager
├── start_mcp_server.sh             # MCP Server Starter
└── update_all_docs.sh              # Documentation Update Script
```

---

## 🗄️ alembic/ – Database Migrations

```
alembic/
├── versions/                       # Migration Versions
│   ├── 001_initial.py
│   ├── 002_add_analysis.py
│   ├── 003_add_templates.py
│   └── ...
├── env.py                          # Alembic Environment
├── script.py.mako                  # Migration Template
└── README                          # Alembic Instructions
```

---

## 📊 data/ – Data Files

```
data/
├── seeds/                          # Seed Data
│   ├── feeds.json
│   ├── categories.json
│   └── sources.json
└── exports/                        # Data Exports
```

---

## 🏗️ systemd/ – Systemd Service Files

```
systemd/
├── news-mcp-web.service            # Web Server Service
├── news-mcp-worker.service         # Worker Service
└── news-mcp-scheduler.service      # Scheduler Service
```

---

## 🔍 Schnell-Referenz: Wichtigste Dateien

### Core Application
```
app/main.py                         # Application Entry Point
app/config.py                       # Configuration
app/database.py                     # Database Setup
```

### Analysis System (Aktueller Fokus)
```
app/services/auto_analysis_service.py           # ✅ Auto-Analysis Core (Phase 2 Sprint 4)
app/services/pending_analysis_processor.py      # ✅ Queue Processor (Phase 2 Sprint 4)
app/web/views/auto_analysis_views.py            # ✅ HTMX Views (Phase 2 Sprint 4)
app/api/analysis_management.py                  # Run Manager API
app/services/analysis_run_manager.py            # Run Manager Service
app/worker/analysis_worker.py                   # Worker Process
```

### Feed System
```
app/api/feeds.py                    # Feed API
app/services/feed_scheduler.py      # Scheduler
app/services/feed_fetcher_sync.py   # Fetcher
```

### Web Interface
```
templates/analysis_cockpit_v4.html  # Main UI
app/web/components/                 # HTMX Components
app/api/htmx.py                     # HTMX Routes
```

### Infrastructure
```
app/core/health.py                  # Health Checks
app/core/logging_config.py          # Logging
app/api/feature_flags_admin.py      # Feature Flags
app/api/metrics.py                  # Metrics
```

---

## 📝 Datei-Namenskonventionen

### Python Files
- `*_service.py` - Service Layer (Business Logic)
- `*_repository.py` - Data Access Layer
- `*_views.py` - HTMX View Handlers
- `*_components.py` - Reusable HTMX Components
- `*_api.py` - API Route Handlers
- `test_*.py` - Test Files

### Templates
- `*.html` - Jinja2 Templates
- `*_v{N}.html` - Versioned Templates (e.g., analysis_cockpit_v4.html)

### Documentation
- `*.md` - Markdown Documentation
- `*_CHECKLIST.md` - Checklists
- `README*.md` - Readme Files

---

## 🔗 Verweise

- **NAVIGATOR.md** → System-Navigator (Hotspots, Worksets, Roadmap)
- **ENDPOINTS.md** → API-Gedächtnis (167 Endpunkte)
- **CLAUDE.md** → Arbeitsregeln
- **README.md** → Haupt-Dokumentation
- **docs/ARCHITECTURE.md** → Architektur-Details

---

## 📊 Statistiken

| Metrik | Wert |
|--------|------|
| Python-Dateien | 132 |
| API-Endpunkte | 167 |
| Dokumentation | 28 Dateien |
| Tabellen (DB) | 30 |
| Services | 22 |
| API Routes | 24 |
| Tests | ~50+ |

---

**Ende INDEX.md**