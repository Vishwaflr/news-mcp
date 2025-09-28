# NAVIGATOR.md – News-MCP System-Navigator

**Zweck:** Zentrale Orientierung für strukturierte Entwicklung
**Version:** 3.1.0
**Stand:** 2025-09-28
**Aktueller Fokus:** Production Rollout Auto-Analysis (Phase 2 Sprint 4)

---

## 📊 3-Spalten-Übersicht: System auf einen Blick

| Was | Wo | Status |
|-----|-----|--------|
| **Core System** | | |
| FastAPI Web Server | `app/main.py` | ✅ Läuft (Port 8000, PID 368256) |
| Analysis Worker | `app/worker/analysis_worker.py` | ✅ Läuft (PID 365993) |
| Feed Scheduler | `app/services/feed_scheduler.py` | ✅ Läuft (PID 365974) |
| PostgreSQL DB | localhost:5432 | ✅ Aktiv (30 Tabellen) |
| | | |
| **Content Layer** | | |
| Feeds Management | `app/api/feeds.py` | ✅ Produktiv (37 Feeds) |
| Items/Articles | `app/api/items.py` | ✅ Produktiv (10.903 Items) |
| Categories | `app/api/categories.py` | ✅ Produktiv |
| Sources | `app/api/sources.py` | ✅ Produktiv (38 Sources) |
| | | |
| **Analysis System** | | |
| Analysis Control | `app/api/analysis_control.py` | ✅ Legacy Support |
| Analysis Management | `app/api/analysis_management.py` | ✅ Centralized Manager |
| Analysis Jobs | `app/api/analysis_jobs.py` | ✅ Preview System |
| Selection Cache | `app/services/selection_cache.py` | ✅ In-Memory Cache |
| Run Manager | `app/services/analysis_run_manager.py` | ✅ Queue Manager |
| Worker API | `app/api/analysis_worker_api.py` | ✅ Worker Control |
| **Auto-Analysis** | `app/services/auto_analysis_service.py` | 🚧 **IN ARBEIT** |
| Auto-Analysis Views | `app/web/views/auto_analysis_views.py` | 🚧 **IN ARBEIT** |
| Pending Processor | `app/services/pending_analysis_processor.py` | 🚧 **IN ARBEIT** |
| | | |
| **Template System** | | |
| Templates API | `app/api/templates.py` | ✅ Produktiv |
| Template Manager | `app/services/dynamic_template_manager.py` | ✅ Hot-Reload |
| | | |
| **Processing** | | |
| Processors API | `app/api/processors.py` | ✅ Produktiv |
| Content Processing | `app/processors/` | ✅ Modular |
| LLM Client | `app/services/llm_client.py` | ✅ OpenAI Integration |
| | | |
| **Infrastructure** | | |
| Database Layer | `app/database.py` | ✅ SQLModel/Alembic |
| Health Checks | `app/core/health.py` | ✅ K8s-ready |
| Feature Flags | `app/api/feature_flags_admin.py` | ✅ A/B Testing |
| Metrics | `app/api/metrics.py` | ✅ Monitoring |
| | | |
| **Web UI** | | |
| Analysis Cockpit | `templates/analysis_cockpit_v4.html` | ✅ Alpine.js v4 |
| HTMX Components | `app/web/components/` | ✅ Progressive Enhancement |
| HTMX Views | `app/api/htmx.py` | ✅ SSR Components |
| WebSocket | `app/api/websocket_endpoint.py` | ✅ Real-time Updates |

---

## 🎯 Hotspots: Kritische Bereiche

### Hotspot 1: Auto-Analysis System (AKTUELLER FOKUS)
**Zweck:** Automatische Analyse neuer Feed-Items
**Status:** 🚧 In Entwicklung (Phase 2)
**Priorität:** ⚡ Hoch

**Komponenten:**
- Auto-Analysis Service (Core Logic)
- Pending Analysis Processor (Queue Processor)
- Auto-Analysis Views (HTMX UI)
- Feed-Level Config (Toggle, Interval)

**Herausforderungen:**
- Rate Limiting (OpenAI API)
- Queue Management (Backpressure)
- Feed-spezifische Konfiguration
- Fehlerbehandlung bei API-Failures

---

### Hotspot 2: Analysis Core System
**Zweck:** Zentrale Analysis-Infrastruktur
**Status:** ✅ Stabil
**Priorität:** 🔧 Wartung

**Komponenten:**
- Run Manager (Queue + Status)
- Selection Cache (Performance)
- Worker Pool (Processing)
- Job Preview System

**Verantwortlichkeiten:**
- Run Lifecycle Management
- Queue Processing
- Rate Limiting
- Progress Tracking

---

### Hotspot 3: Feed Management
**Zweck:** RSS Feed Ingestion & Health
**Status:** ✅ Produktiv
**Priorität:** 🔧 Wartung

**Komponenten:**
- Feed CRUD API
- Feed Scheduler
- Feed Health Monitoring
- Feed Limits Service

**Metriken:**
- 37 aktive Feeds
- ~450 Items/Tag
- Fetch Success Rate: >95%

---

### Hotspot 4: Web Interface (HTMX + Alpine.js)
**Zweck:** Modern Progressive Enhancement UI
**Status:** ✅ Produktiv
**Priorität:** 🔧 Wartung

**Komponenten:**
- Analysis Cockpit v4
- HTMX Components
- Alpine.js State Management
- WebSocket Updates

**Features:**
- Server-Side Rendering
- Real-time Updates
- Dark Mode Support

---

### Hotspot 5: Infrastructure (Monitoring + Feature Flags)
**Zweck:** Production-Ready Operations
**Status:** ✅ Stabil
**Priorität:** 🔧 Wartung

**Komponenten:**
- Health Checks
- Metrics Collection
- Feature Flags + Shadow Comparison
- Circuit Breaker

---

## 📁 Worksets: Genehmigte Arbeits-Dateien

### Workset 1: Auto-Analysis Implementation (MAX 8 DATEIEN)
**Status:** 🔓 Freigegeben für Änderungen
**Zweck:** Auto-Analysis für Feeds implementieren

```
1. app/services/auto_analysis_service.py        (Core Service)
2. app/services/pending_analysis_processor.py   (Queue Processor)
3. app/web/views/auto_analysis_views.py         (HTMX Views)
4. app/api/feeds.py                             (Feed Toggle API)
5. app/models/__init__.py                       (Schema Extensions)
6. templates/components/auto_analysis.html      (UI Components)
7. app/services/feed_scheduler.py               (Integration Hook)
8. app/database.py                              (Schema: pending_auto_analysis Table)
```

**Scope-Regeln:**
- ✅ Änderungen nur in diesen 8 Dateien
- ✅ Neue Tabelle: `pending_auto_analysis` (bereits vorhanden)
- ❌ Keine Änderungen in `analysis_run_manager.py` (außer API Calls)
- ❌ Keine Änderungen in Worker Logic (`analysis_worker.py`)

---

### Workset 2: Analysis Core (LOCKED - Nur bei Bugs)
**Status:** 🔒 Gesperrt (außer Bugfixes)

```
1. app/services/analysis_run_manager.py
2. app/services/selection_cache.py
3. app/api/analysis_management.py
4. app/worker/analysis_worker.py
```

---

### Workset 3: Feed System (LOCKED - Nur bei Bugs)
**Status:** 🔒 Gesperrt (außer Bugfixes)

```
1. app/services/feed_scheduler.py
2. app/services/feed_fetcher_sync.py
3. app/api/feeds.py
4. app/api/health.py
```

---

## 🗺️ Roadmap: Phase 2 – Auto-Analysis

### ✅ Phase 1: Foundation (ABGESCHLOSSEN)
- [x] Analysis Core System
- [x] Job Preview System
- [x] Selection Cache
- [x] Run Manager
- [x] Worker Pool
- [x] Analysis Cockpit UI

### 🚧 Phase 2: Auto-Analysis (Sprint 4 laufend)

#### ✅ Sprint 1: Core Implementation
- [x] Tabelle `pending_auto_analysis` erstellt
- [x] Auto-Analysis Service implementieren
  - [x] Feed-Level Config (enable/disable)
  - [x] Trigger on new items
  - [x] Queue to `pending_auto_analysis`
- [x] Pending Processor implementieren
  - [x] Batch Processing (10-50 items)
  - [x] Rate Limiting Integration
  - [x] Error Handling + Retry
- [x] Feed API erweitern
  - [x] `POST /api/feeds/{id}/toggle-auto-analysis`
  - [x] `GET /api/feeds/{id}/auto-analysis-status`

#### ✅ Sprint 2: UI Integration
- [x] HTMX Components erstellen
  - [x] Auto-Analysis Toggle Button
  - [x] Queue Status Badge
  - [x] History Timeline
- [x] Dashboard Integration
  - [x] `/htmx/auto-analysis-dashboard`
  - [x] `/htmx/auto-analysis-queue`
  - [x] `/htmx/auto-analysis-history`
- [x] WebSocket Updates (Optional - bereits via Polling)
  - [x] Real-time Queue Updates
  - [x] Status Changes

#### ✅ Sprint 3: Testing & Stabilization
- [x] Integration Tests
  - [x] End-to-End Flow (6/7 tests passed)
  - [x] Rate Limiting (Daily limits working)
  - [x] Error Scenarios (Disabled feeds, invalid items)
- [x] Performance Testing
  - [x] Query Performance (0.064s für 10 Feeds)
  - [x] Memory Check (OK)
- [x] Documentation
  - [x] API Docs Update (ENDPOINTS.md)
  - [x] System Docs (NAVIGATOR.md)

#### 🚧 Sprint 4: Production Rollout (IN ARBEIT)
- [ ] Feature Flag Setup
  - [ ] `auto_analysis_enabled` (Feed-Level bereits vorhanden)
  - [ ] Shadow Comparison (Optional)
- [ ] Gradual Rollout
  - [ ] 10% Feeds
  - [ ] 50% Feeds
  - [ ] 100% Feeds
- [ ] Monitoring Setup
  - [ ] Alerts für Queue Backlog
  - [ ] Cost Tracking
  - [ ] Success Rate Metrics

---

### 📋 Phase 3: Advanced Features (Q4 2025)
- [ ] Smart Scheduling
  - [ ] Adaptive Intervals basierend auf Feed Activity
  - [ ] Priority Queues
- [ ] Bulk Operations
  - [ ] Batch-Analysis für alle Feeds
  - [ ] Scheduled Runs
- [ ] Advanced Analytics
  - [ ] Trend Analysis
  - [ ] Anomaly Detection
- [ ] Multi-LLM Support
  - [ ] Claude Integration
  - [ ] Model Comparison

---

### 📋 Phase 4: Optimization (2026)
- [ ] Performance Optimizations
  - [ ] Caching Layer (Redis)
  - [ ] Database Partitioning
  - [ ] Read Replicas
- [ ] Scalability
  - [ ] Horizontal Worker Scaling
  - [ ] Load Balancing
  - [ ] Queue Sharding

---

## 🔧 Entwicklungs-Workflow

### 1. Vor Code-Änderungen
```bash
# 1. NAVIGATOR.md lesen → Workset prüfen
# 2. Datei in freigegebenem Workset? → OK
# 3. Datei außerhalb Workset? → STOPP, Plan erstellen

# 4. Plan erstellen (wenn neue Features)
# - Was wird geändert?
# - Welche Dateien betroffen?
# - Tests erforderlich?
# - Breaking Changes?
```

### 2. Während Entwicklung
```bash
# - Nur in freigegebenen Worksets arbeiten
# - ENDPOINTS.md für API-Referenz nutzen
# - Keine Streuänderungen
# - Tests lokal ausführen

# Contract Tests (5 Tests definiert):
pytest tests/contract/
```

### 3. Nach Code-Änderungen
```bash
# - Lint + Typecheck ausführen
ruff check app/
mypy app/

# - Tests ausführen
pytest

# - NAVIGATOR.md aktualisieren (wenn neue Features)
# - ENDPOINTS.md aktualisieren (wenn neue API Endpoints)
```

---

## 📝 Contract Tests (5 Definierte Tests)

1. **Feed Fetch Contract**
   - Feed kann erstellt werden
   - Feed kann gefetcht werden
   - Items werden korrekt gespeichert

2. **Analysis Run Contract**
   - Preview kann erstellt werden
   - Run kann gestartet werden
   - Run wird von Worker verarbeitet
   - Results werden gespeichert

3. **Auto-Analysis Contract** (NEU für Phase 2)
   - Feed Auto-Analysis kann aktiviert werden
   - Neue Items triggern Auto-Analysis
   - Items werden zu pending_auto_analysis hinzugefügt
   - Processor verarbeitet Queue

4. **API Response Contract**
   - Alle API Endpoints geben korrektes JSON zurück
   - Error Responses haben Standard-Format
   - Success Responses haben `success: true`

5. **Database Schema Contract**
   - Alle Tabellen existieren
   - Foreign Keys sind korrekt
   - Indizes sind vorhanden

---

## 🚨 Wichtige Regeln

### ✅ DO
- Nutze ENDPOINTS.md für API-Referenzen
- Halte dich an NAVIGATOR.md für Hotspots, Worksets, Roadmap
- Erstelle kleine, nachvollziehbare Diffs
- Folge der Phase-2-Roadmap Schritt für Schritt
- Beziehe dich auf die 5 Contract Tests
- Frage bei Unsicherheit

### ❌ DON'T
- Keine neuen Dependencies ohne Freigabe
- Keine Änderungen außerhalb genehmigter Worksets
- Keine Vermischung von Code und Freitext im Output
- Keine parallelen Änderungen an nicht freigegebenen Roadmap-Teilen
- Keine Annahmen treffen, wenn Unsicherheit besteht
- Niemals stillschweigend Entscheidungen treffen

---

## 📞 Kontakt & Freigaben

**Bei Bedarf für Freigaben:**
- Neue Dependencies
- Änderungen außerhalb Workset
- Breaking Changes
- Schema-Änderungen

**→ Immer Plan erstellen und Freigabe einholen, bevor Code geschrieben wird**

---

**Ende NAVIGATOR.md**