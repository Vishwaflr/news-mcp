# ENDPOINTS.md – News-MCP API-Gedächtnis

**Zweck:** Komplette API-Referenz für News-MCP System (150+ Endpunkte strukturiert)
**Version:** 3.2.0
**Letzte Aktualisierung:** 2025-09-30

---

## 📋 Übersicht

| Kategorie | Endpunkte | Prefix | Status |
|-----------|-----------|--------|--------|
| [Feeds Management](#1-feeds-management) | 15 | `/api/feeds` | ✅ Aktiv |
| [Items/Articles](#2-itemsarticles) | 12 | `/api/items` | ✅ Aktiv |
| [Analysis System](#3-analysis-system) | 35 | `/api/analysis` | ✅ Aktiv |
| [Templates](#4-templates) | 8 | `/api/templates` | ✅ Aktiv |
| [Categories & Sources](#5-categories--sources) | 8 | `/api/categories`, `/api/sources` | ✅ Aktiv |
| [Processors](#6-processors) | 6 | `/api/processors` | ✅ Aktiv |
| [Statistics & Metrics](#7-statistics--metrics) | 13 | `/api/statistics`, `/api/metrics` | ✅ Aktiv |
| [Health & System](#8-health--system) | 10 | `/api/health`, `/api/system` | ✅ Aktiv |
| [HTMX Views](#9-htmx-views) | 30 | `/htmx/*` | ✅ Aktiv |
| [WebSocket](#10-websocket) | 1 | `/ws/*` | ✅ Aktiv |
| [Database Admin](#11-database-admin) | 4 | `/api/database` | ✅ Aktiv |
| [Feature Flags](#12-feature-flags) | 12 | `/admin/feature-flags` | ✅ Aktiv |
| [User Settings](#13-user-settings) | 4 | `/api/user-settings` | ✅ Aktiv |
| [Scheduler](#14-scheduler) | 6 | `/api/scheduler` | ✅ Aktiv |
| [Feed Limits](#15-feed-limits) | 9 | `/api/feed-limits` | ✅ Aktiv |

**Total:** 173 Endpunkte

---

## 1. Feeds Management

**Datei:** `app/api/feeds.py`, `app/api/feeds_simple.py`
**Beschreibung:** RSS Feed CRUD, Fetch, Status-Management

### Standard CRUD
```http
GET    /api/feeds/                          # Liste aller Feeds
GET    /api/feeds/{feed_id}                 # Feed Details
POST   /api/feeds/                          # Feed erstellen (Form)
POST   /api/feeds/json                      # Feed erstellen (JSON)
PUT    /api/feeds/{feed_id}                 # Feed aktualisieren
PUT    /api/feeds/{feed_id}/form            # Feed aktualisieren (HTMX)
DELETE /api/feeds/{feed_id}                 # Feed löschen
```

### Feed Operations
```http
POST   /api/feeds/{feed_id}/fetch                        # Manueller Feed-Fetch
GET    /list                                             # Simple Feed-Liste (UI)
POST   /api/feeds/{feed_id}/toggle-auto-analysis?enabled=true  # Toggle Auto-Analysis (NEU)
GET    /api/feeds/{feed_id}/auto-analysis-status         # Auto-Analysis Status + Stats (NEU)
```

### Feed Health
```http
GET    /api/health/feeds                    # Alle Feed Health Status
GET    /api/health/feeds/{feed_id}          # Einzelner Feed Health
GET    /api/health/logs/{feed_id}           # Feed Fetch Logs
GET    /api/health/status                   # System Health Overview
```

### Kontext
- Basis für Content-Ingestion
- Unterstützt RSS/Atom Feeds
- Automatischer Scheduler + manueller Trigger
- Health Monitoring mit Fetch Log

---

## 2. Items/Articles

**Datei:** `app/api/items.py`
**Beschreibung:** Nachrichtenartikel, Analysis-Status, Suche

### Article Retrieval
```http
GET    /api/items/                          # Liste aller Items (paginated)
GET    /api/items/{item_id}                 # Item Details
GET    /api/items/analyzed                  # Nur analysierte Items
GET    /api/items/analysis/stats            # Analysis-Statistiken
GET    /api/items/{item_id}/analysis        # Item Analysis Details
```

### HTMX Components
```http
GET    /htmx/items-list                     # HTMX Item-Liste
```

### Kontext
- 11.254 Items aktuell in DB
- Verknüpft mit Feeds (feed_id)
- Optional verknüpft mit item_analysis
- Support für Pagination, Filtering

---

## 3. Analysis System

**Dateien:** `app/api/analysis_control.py`, `app/api/analysis_management.py`, `app/api/analysis_selection.py`, `app/api/analysis_jobs.py`, `app/api/analysis_worker_api.py`
**Beschreibung:** KI-Analyse, Run Management, Queue, Preview, Worker Control

### 3.1 Analysis Control (Legacy + Current)
```http
POST   /api/preview                         # Preview erstellen (Alt)
POST   /api/start                           # Run starten (Alt)
POST   /api/runs                            # Run erstellen
GET    /api/runs                            # Run-Liste
POST   /api/pause/{run_id}                  # Run pausieren
POST   /api/start/{run_id}                  # Run starten/fortsetzen
POST   /api/cancel/{run_id}                 # Run abbrechen
GET    /api/status/{run_id}                 # Run Status
GET    /api/status                          # Alle Run Status
GET    /api/history                         # Run Historie
```

### 3.2 Analysis Presets
```http
POST   /api/presets                         # Preset erstellen
GET    /api/presets                         # Presets auflisten
DELETE /api/presets/{preset_id}             # Preset löschen
```

### 3.3 Quick Actions & Stats
```http
GET    /api/quick-actions                   # UI Quick Actions
GET    /api/articles                        # Articles für Analysis
GET    /api/feeds                           # Feeds für Selection
GET    /api/stats                           # Analysis Stats
GET    /api/history                         # Analysis History
```

### 3.4 Cost Estimation
```http
GET    /api/cost/{model}                    # Kosten für Model
GET    /api/models/compare                  # Model Vergleich
GET    /api/budget                          # Budget Info
```

### 3.5 Job System (Preview)
```http
POST   /api/analysis-jobs/preview           # Preview Job erstellen
GET    /api/analysis-jobs/{job_id}          # Job Status
POST   /api/analysis-jobs/{job_id}/refresh  # Preview aktualisieren
GET    /api/analysis-jobs/                  # Alle Jobs
POST   /api/analysis-jobs/{job_id}/confirm  # Preview → Run
POST   /api/analysis-jobs/{job_id}/cancel   # Job abbrechen
POST   /api/analysis-jobs/preview/legacy    # Legacy Preview
```

### 3.6 Run Management (Centralized)
```http
GET    /api/analysis/runs/{run_id}          # Run Details
POST   /api/analysis/runs/{run_id}/cancel   # Run abbrechen
GET    /api/analysis/manager/status         # Manager Status
POST   /api/analysis/manager/emergency-stop # Emergency Stop
POST   /api/analysis/manager/resume         # Betrieb fortsetzen
GET    /api/analysis/manager/limits         # System Limits
GET    /api/analysis/manager/queue          # Queue Status
POST   /api/analysis/manager/queue/process  # Queue manuell triggern
DELETE /api/analysis/manager/queue/{queued_run_id} # Queue Item löschen
GET    /api/analysis/health                 # Analysis Health
```

### 3.7 Selection Cache
```http
POST   /api/analysis/selection              # Selection erstellen
GET    /api/analysis/selection/{selection_id} # Selection Details
GET    /api/analysis/selection/{selection_id}/articles # Selection Articles
```

### 3.8 Worker API
```http
GET    /api/analysis-worker/worker/status   # Worker Status
POST   /api/analysis-worker/worker/control  # Worker Control (pause/resume/stop)
GET    /api/analysis-worker/stats           # Worker Stats
POST   /api/analysis-worker/test-deferred   # Test Deferred Analysis
```

### Kontext
- 75+ Analysis Runs im System
- Job-based Preview System (neu)
- Selection Cache für Performance
- Centralized Run Manager (5 concurrent runs)
- Worker Pool mit Status-Tracking
- **Auto-Analysis für Feeds** → ✅ Phase 2 Sprint 4 ABGESCHLOSSEN (100% Rollout, 9 Feeds)

---

## 4. Templates

**Datei:** `app/api/templates.py`, `app/routes/templates.py`
**Beschreibung:** Dynamic Feed Templates, Assignments

### Template CRUD
```http
GET    /api/templates/                      # Template-Liste
GET    /api/templates/{template_id}         # Template Details
POST   /api/templates/                      # Template erstellen
PUT    /api/templates/{template_id}         # Template aktualisieren
DELETE /api/templates/{template_id}         # Template löschen
```

### Template Assignments
```http
POST   /api/templates/{template_id}/assign/{feed_id}   # Feed zuweisen
DELETE /api/templates/{template_id}/assign/{feed_id}   # Zuweisung löschen
GET    /api/templates/performance           # Template Performance Stats
```

### Kontext
- Dynamische Config-Templates für Feeds
- Hot-reload ohne Server-Restart
- Performance-Tracking

---

## 5. Categories & Sources

**Dateien:** `app/api/categories.py`, `app/api/sources.py`
**Beschreibung:** Content-Kategorisierung, Source-Management

### Categories
```http
GET    /api/categories/                     # Kategorie-Liste
GET    /api/categories/{category_id}        # Kategorie Details
POST   /api/categories/                     # Kategorie erstellen
DELETE /api/categories/{category_id}        # Kategorie löschen
```

### Sources
```http
GET    /api/sources/                        # Source-Liste
GET    /api/sources/{source_id}             # Source Details
POST   /api/sources/                        # Source erstellen
DELETE /api/sources/{source_id}             # Source löschen
```

### Kontext
- 41 Sources im System
- M:N Relation Feeds ↔ Categories

---

## 6. Processors

**Datei:** `app/api/processors.py`
**Beschreibung:** Content Processing Pipelines, Templates

### Processor Management
```http
GET    /api/processors/types                # Processor Types
GET    /api/processors/configs              # Processor Configs
POST   /api/processors/configs              # Config erstellen
PUT    /api/processors/configs/{config_id}  # Config aktualisieren
GET    /api/processors/templates            # Processor Templates
POST   /api/processors/reprocess            # Items reprocessen
```

### Kontext
- Modular Processing Pipeline
- Template-basierte Config
- Bulk Reprocessing

---

## 7. Statistics & Metrics

**Dateien:** `app/api/statistics.py`, `app/api/metrics.py`
**Beschreibung:** System Metrics, Feed Performance, Costs

### System Statistics
```http
GET    /api/statistics/overview             # System Overview
GET    /api/statistics/feeds                # Feed Statistics
GET    /api/statistics/items                # Item Statistics
GET    /api/statistics/analysis             # Analysis Statistics
```

### Metrics (Detailed)
```http
GET    /api/metrics/system/overview         # System Metrics
GET    /api/metrics/feeds/{feed_id}         # Feed Metrics Detail
GET    /api/metrics/feeds/{feed_id}/summary # Feed Summary
GET    /api/metrics/costs/breakdown         # Cost Breakdown
GET    /api/metrics/performance/queue       # Queue Performance
GET    /api/metrics/feeds                   # All Feed Metrics
GET    /api/metrics/storage/stats           # Database Storage Statistics (NEU)
GET    /api/metrics/prometheus              # Prometheus Metrics Export
POST   /api/metrics/test/record             # Test Metric Recording
```

### Storage Statistics (NEU - 2025-10-02)
**Endpoint:** `GET /api/metrics/storage/stats`

**Response:**
```json
{
  "success": true,
  "data": {
    "database_size": "77 MB",
    "item_count": 19129,
    "analysis_count": 7999,
    "analysis_coverage_percent": 41.82,
    "top_tables": [
      {
        "name": "items",
        "total_size": "29 MB",
        "table_size": "13 MB",
        "indexes_size": "16 MB",
        "total_bytes": 30605312
      }
    ],
    "jsonb_fields": [
      {
        "field_type": "sentiment_json",
        "entries": 7998,
        "total_size": "3073 kB",
        "avg_size": "393 bytes"
      }
    ],
    "geopolitical": {
      "total_analyses": 7998,
      "with_geopolitical": 1413,
      "percentage": 17.67,
      "size": "1080 kB"
    },
    "category_sizes": [
      {
        "category": "RSS Feed Data",
        "size": "37 MB",
        "bytes": 38797312
      },
      {
        "category": "Sentiment Analysis Data",
        "size": "26 MB",
        "bytes": 27262976
      }
    ],
    "growth": {
      "total_items": 19096,
      "items_per_week": 10203,
      "estimated_items_per_year_k": 530.6,
      "data_age_days": 2298
    }
  }
}
```

**Verwendung:**
- Database-Größe überwachen
- Speicherwachstum tracken
- JSONB-Overhead analysieren
- Geopolitical Data Coverage prüfen
- Kapazitätsplanung

### Kontext
- Prometheus-Style Metrics
- Cost-Tracking für OpenAI
- Performance Monitoring
- P50/P95/P99 Latencies
- **Storage Monitoring** (Database-Größe, Wachstum, JSONB-Overhead)

---

## 8. Health & System

**Dateien:** `app/api/health.py`, `app/api/system.py`, `app/core/health.py`
**Beschreibung:** Health Checks, System Control

### Health Endpoints
```http
GET    /health                              # Liveness Probe
GET    /health/ready                        # Readiness Probe
GET    /health/detailed                     # Detaillierte Health Checks
GET    /api/health/feeds                    # Feed Health (siehe Feeds)
```

### System Control
```http
GET    /api/system/status                   # System Status
POST   /api/system/reload-config            # Config Reload
POST   /api/system/clear-cache              # Cache leeren
GET    /api/system/info                     # System Info
POST   /api/system/emergency-stop           # Emergency Stop All
POST   /api/system/resume                   # Resume All
```

### Kontext
- Multi-level Health Checks
- DB, OpenAI, Worker, Disk Checks
- K8s-ready Probes

---

## 9. HTMX Views

**Dateien:** `app/api/htmx.py`, `app/web/views/analysis/*.py`, `app/web/views/feed_views.py`, `app/web/views/item_views.py`, `app/web/views/system_views.py`, `app/web/views/auto_analysis_views.py`, `app/web/views/manager_views.py`
**Beschreibung:** Progressive Enhancement UI Components

### Analysis Cockpit
```http
GET    /htmx/analysis/target-selection      # Target Selection UI
GET    /htmx/analysis/preview-start         # Preview UI
GET    /htmx/analysis/runs/active           # Active Runs Component
GET    /htmx/analysis/runs/history          # Run History Component
GET    /htmx/analysis/stats-horizontal      # Stats Dashboard
GET    /htmx/analysis/articles-live         # Live Article Feed (paginated)
GET    /htmx/analysis/settings/form         # Settings Form
GET    /htmx/analysis/settings/slo          # SLO Settings
```

### Feed Components
```http
GET    /htmx/feeds-options                  # Feed Dropdown Options
POST   /htmx/feed-fetch-now/{feed_id}       # Trigger Fetch (HTMX)
POST   /htmx/feed-toggle-auto-analysis/{feed_id} # Toggle Auto-Analysis
GET    /htmx/feeds-list                     # Feed List Component
GET    /htmx/feed-health/{feed_id}          # Feed Health Badge
GET    /htmx/feed-types-options             # Feed Types Dropdown
POST   /htmx/feed-url-test                  # Test Feed URL
GET    /htmx/feed-edit-form/{feed_id}       # Feed Edit Form
```

### Item Components
```http
GET    /htmx/items-list                     # Item List Component
```

### System Components
```http
GET    /htmx/sources-options                # Sources Dropdown
GET    /htmx/categories-options             # Categories Dropdown
GET    /htmx/system-status                  # System Status Badge
GET    /htmx/processor-configs              # Processor Config List
GET    /htmx/processor-templates            # Processor Templates
GET    /htmx/processor-stats                # Processor Stats
GET    /htmx/reprocessing-status            # Reprocessing Status
GET    /htmx/processor-health-details       # Processor Health
```

### Auto-Analysis Views (Phase 2) ✅ PRODUKTIV
```http
GET    /htmx/auto-analysis-dashboard        # Auto-Analysis Dashboard
GET    /htmx/auto-analysis-queue            # Auto-Analysis Queue Status
GET    /htmx/auto-analysis-history          # Auto-Analysis History
GET    /htmx/auto-analysis-config           # Auto-Analysis Config Form
POST   /htmx/auto-analysis-config           # Update Auto-Analysis Config
```

### Manager Views (NEW - Sprint 4) ✅ PRODUKTIV
```http
GET    /htmx/manager-status                 # System Status Component (5s polling)
GET    /htmx/manager-queue                  # Queue Breakdown Component (5s polling)
GET    /htmx/manager-daily-stats            # Daily/Hourly Stats (10s polling)
GET    /htmx/manager-config                 # Configuration Display
GET    /htmx/manager-active-runs            # Active Runs Table (3s polling)
```

### Kontext
- Alpine.js State Management
- Server-Side Rendering (Jinja2)
- Progressive Enhancement Pattern
- Real-time Updates via Polling/SSE

---

## 10. WebSocket

**Datei:** `app/api/websocket_endpoint.py`
**Beschreibung:** Real-time Updates

### WebSocket Connection
```http
WS     /ws/updates                          # WebSocket für Real-time Updates
```

### Kontext
- Analysis Run Updates
- Feed Status Changes
- System Events
- JSON-basierte Messages

---

## 11. Database Admin

**Datei:** `app/api/database.py`
**Beschreibung:** DB-Introspection, Query-Execution

### Database Operations
```http
GET    /api/database/tables                 # Tabellen-Liste
GET    /api/database/schema/{table_name}    # Schema Details
POST   /api/database/query                  # SQL Query ausführen
GET    /api/database/quick-queries          # Vordefinierte Queries
```

### Kontext
- Admin-Tool für DB-Introspection
- Sicherheitsrelevant: Nur intern nutzen
- 30 Tabellen aktuell

---

## 12. Feature Flags

**Datei:** `app/api/feature_flags_admin.py`
**Beschreibung:** Feature Flag Management, A/B Testing, Shadow Comparison

### Flag Management
```http
GET    /admin/feature-flags/                # Alle Flags
GET    /admin/feature-flags/{flag_name}     # Flag Details
POST   /admin/feature-flags/{flag_name}     # Flag Update (enable/disable)
POST   /admin/feature-flags/{flag_name}/reset-metrics # Metrics zurücksetzen
```

### Shadow Comparison
```http
GET    /admin/feature-flags/metrics/shadow-comparison         # Item Shadow Stats
GET    /admin/feature-flags/metrics/analysis-shadow-comparison # Analysis Shadow Stats
GET    /admin/feature-flags/metrics/performance               # Performance Metrics
GET    /admin/feature-flags/metrics/dashboard                 # Metrics Dashboard
POST   /admin/feature-flags/shadow-comparison/reset           # Reset Item Shadow
POST   /admin/feature-flags/analysis-shadow-comparison/reset  # Reset Analysis Shadow
POST   /admin/feature-flags/analysis-shadow/{action}          # Shadow Control (enable/disable/reset)
GET    /admin/feature-flags/health                            # Feature Flag Health
```

### Kontext
- Gradual Rollout Pattern
- Circuit Breaker (5% Error, 30% Latency)
- A/B Testing mit Shadow Mode
- Repository Pattern Migration Support

---

## 13. User Settings

**Datei:** `app/api/user_settings.py`
**Beschreibung:** User Preferences, Config Persistence

### Settings CRUD
```http
GET    /api/user-settings/                  # Alle Settings
GET    /api/user-settings/{key}             # Setting abrufen
POST   /api/user-settings/                  # Setting setzen
DELETE /api/user-settings/{key}             # Setting löschen
```

### Kontext
- Key-Value Store
- JSON Values
- UI Preferences, Analysis Defaults

---

## 14. Scheduler

**Datei:** `app/api/scheduler.py`
**Beschreibung:** Feed Scheduling, State Management

### Scheduler Control
```http
GET    /api/scheduler/status                # Scheduler Status
POST   /api/scheduler/pause                 # Scheduler pausieren
POST   /api/scheduler/resume                # Scheduler fortsetzen
GET    /api/scheduler/state                 # Scheduler State
POST   /api/scheduler/trigger/{feed_id}     # Feed manuell triggern
GET    /api/scheduler/next-runs             # Nächste geplante Runs
```

### Kontext
- Cron-like Scheduler
- Dynamic Interval Adjustment
- Health-based Scheduling

---

## 15. Feed Limits

**Datei:** `app/api/feed_limits.py`
**Beschreibung:** Rate Limiting, Quota Management, Violations

### Feed Limit Management
```http
GET    /api/feed-limits/feeds/{feed_id}     # Feed Limits abrufen
POST   /api/feed-limits/feeds/{feed_id}     # Feed Limits setzen
DELETE /api/feed-limits/feeds/{feed_id}     # Feed Limits löschen
POST   /api/feed-limits/feeds/{feed_id}/check # Limit-Check
POST   /api/feed-limits/feeds/{feed_id}/enable # Limit aktivieren
GET    /api/feed-limits/feeds/{feed_id}/violations # Violations für Feed
GET    /api/feed-limits/violations/summary  # Violations Summary
POST   /api/feed-limits/feeds/{feed_id}/emergency-stop # Feed Emergency Stop
GET    /api/feed-limits/presets             # Limit Presets
```

### Kontext
- Quota Management (Requests/Hour, Items/Day)
- Violation Tracking
- Emergency Stop bei Überschreitung
- Preset-basierte Config

---

## 16. Admin Web Views

**Datei:** `app/main.py` (direkt)
**Beschreibung:** HTML Admin Pages

### Admin Pages
```http
GET    /                                    # Dashboard Home
GET    /admin                               # Admin Dashboard
GET    /admin/feeds                         # Feed Management UI
GET    /admin/items                         # Item Browser UI
GET    /admin/health                        # Health Dashboard UI
GET    /admin/processors                    # Processor Management UI
GET    /admin/statistics                    # Statistics Dashboard UI
GET    /admin/database                      # Database Admin UI
GET    /admin/analysis                      # Analysis Cockpit UI (v4)
GET    /admin/auto-analysis                 # Auto-Analysis Monitoring UI
GET    /admin/manager                       # Manager Control Center UI (includes metrics)
```

---

## 🔍 Schnell-Referenz: Häufigste Endpunkte

### Entwicklung
```bash
# System Health
curl http://localhost:8000/health/detailed

# Feeds holen
curl http://localhost:8000/api/feeds/

# Analysis Preview
curl -X POST http://localhost:8000/api/analysis-jobs/preview \
  -H "Content-Type: application/json" \
  -d '{"selection_mode": "recent_days", "params": {"days": 1}}'

# Manager Status
curl http://localhost:8000/api/analysis/manager/status
```

### Production Monitoring
```bash
# Health Checks
GET /health               # Liveness
GET /health/ready         # Readiness
GET /health/detailed      # Full Check

# Metrics
GET /api/metrics/system/overview
GET /api/statistics/overview
```

---

## 📝 Notes

### API-Versioning
- Aktuell: **v4.0.0**
- Legacy Endpunkte werden parallel unterstützt
- Feature Flags steuern Cutover

### Authentication
- Aktuell: **Keine Authentication** (Development)
- Geplant: OAuth2 + JWT für Production

### Rate Limiting
- Global: 100 req/s pro IP
- Analysis: Controlled via Queue + Worker Rate Limits
- Feed Limits: Per-Feed Quotas

### Error Responses
```json
{
  "success": false,
  "error": "Error description",
  "detail": "Detailed error info",
  "code": "ERROR_CODE"
}
```

---

**Ende ENDPOINTS.md**