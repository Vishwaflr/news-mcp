# Analysis Cockpit - Complete Requirements Specification

**Version:** 4.0 (Rebuild Specification)
**Date:** September 26, 2025
**Purpose:** Vollständige Neuimplementierung des Analysis Control Centers
**Status:** 🎯 Production Requirements

---

## 📋 Document Overview

Diese Datei definiert **alle Anforderungen** für das Analysis Cockpit - ein zentrales Command Center zur Verwaltung von AI-basierten Sentiment- und Impact-Analysen für News-Artikel.

**Verwendung:** Diese Spezifikation dient als einzige Quelle der Wahrheit für einen kompletten Neuaufbau des Systems.

---

## 1. Funktionale Anforderungen

### 1.1 Article Target Selection System

#### FR-1.1.1: Latest Articles Mode
**Beschreibung:** Benutzer kann die N neuesten Artikel zur Analyse auswählen
**Input:** Anzahl (1-1000)
**Behavior:**
- Sortierung: `published DESC`
- Default: 50 Artikel
- Zeigt Live-Preview der Artikel rechts an
- Aktualisiert Preview-Statistiken sofort

```python
# Example Scope
{
    "type": "global",
    "limit": 50,
    "unanalyzed_only": True,  # Standard
    "newest_first": True
}
```

#### FR-1.1.2: Time Range Mode
**Beschreibung:** Artikel aus bestimmtem Zeitraum analysieren
**Input:** Tage (0-365) + Stunden (0-23)
**Behavior:**
- Berechnet: `start_time = now() - (days*24 + hours)`
- Alle Artikel im Zeitraum werden berücksichtigt
- **WICHTIG:** Limit wird NICHT angewendet auf Time Range
- Zeigt tatsächliche Anzahl im Preview an

```python
# Example Scope
{
    "type": "timerange",
    "start_time": "2025-09-19T00:00:00Z",
    "end_time": "2025-09-26T12:00:00Z",
    "unanalyzed_only": True
}
```

#### FR-1.1.3: Unanalyzed Mode
**Beschreibung:** Alle noch nicht analysierten Artikel
**Input:** Keine (verwendet Model Limit)
**Behavior:**
- Query: `WHERE id NOT IN (SELECT item_id FROM item_analysis)`
- Verwendet `params.limit` für Begrenzung
- Priorität: Neueste zuerst

```python
# Example Scope
{
    "type": "global",
    "unanalyzed_only": True,
    "limit": 200  # From model params
}
```

### 1.2 Feed Filtering System

#### FR-1.2.1: Optional Feed Filter
**Beschreibung:** Limitierung auf spezifischen Feed
**Input:** Feed-Auswahl aus Dropdown
**Behavior:**
- Checkbox: "Limit to specific feed"
- Dropdown: Alle aktiven Feeds mit Item-Counts
- Kombinierbar mit allen Selection-Modes
- Button: "Apply Feed Filter" triggert Preview-Update
- Button: "Clear Filter" entfernt Feed-Einschränkung

```python
# Feed Filter Applied
{
    "type": "feeds",
    "feed_ids": [48],  # Deutsche Welle
    "unanalyzed_only": True
}
```

#### FR-1.2.2: Feed List Loading
**API:** `/api/feeds` oder `/htmx/analysis/feeds-list-options`
**Response:**
```json
[
    {
        "id": 48,
        "title": "Deutsche Welle",
        "item_count": 347,
        "unanalyzed_count": 258
    }
]
```

### 1.3 Preview System

#### FR-1.3.1: Live Preview Calculation
**Beschreibung:** Zeigt Vorschau was analysiert würde
**Trigger:** Änderung von Selection, Feed-Filter, Model-Params
**API:** `POST /api/analysis/preview`
**Response:**
```json
{
    "item_count": 201,
    "total_items": 500,
    "already_analyzed_count": 142,
    "new_items_count": 358,
    "estimated_cost_usd": 0.0358,
    "estimated_duration_minutes": 6,
    "has_conflicts": true,
    "sample_item_ids": [11264, 11263, ...]
}
```

#### FR-1.3.2: Preview Display Components
**UI Elements:**
- **Total Selected:** Anzahl Artikel im Scope (blau)
- **Already Analyzed:** Bereits analysierte Artikel (grau)
- **To Analyze (LIMIT!):** Tatsächlich zu analysierende (primär/rot wenn Limit)
- **Estimated Cost:** In USD (grün)
- **Est. Minutes:** Geschätzte Dauer (gelb)

**Calculation Logic:**
```python
# Cost per item = (AVG_TOKENS * MODEL_PRICE_PER_1M) / 1_000_000
AVG_TOKENS_PER_ITEM = 500
cost_per_item = (500 * MODEL_PRICING[model]["input"]) / 1_000_000
total_cost = cost_per_item * items_to_analyze

# Duration
duration_minutes = (items_to_analyze / rate_per_second) / 60
```

### 1.4 Model & Parameters Configuration

#### FR-1.4.1: Model Selection
**Beschreibung:** Auswahl des AI-Modells für Analyse
**Models Supported:**

| Model | Input ($/1M) | Output ($/1M) | Cached ($/1M) | Empfehlung |
|-------|-------------|---------------|---------------|------------|
| gpt-4.1-nano | $0.20 | $0.80 | $0.05 | ✅ Default |
| gpt-4.1-mini | $0.70 | $2.80 | $0.175 | Balanced |
| gpt-4.1 | $3.50 | $14.00 | $0.875 | High Quality |
| gpt-4o-mini | $0.25 | $1.00 | $0.125 | Cost-Effective |
| gpt-5-mini | $0.45 | $3.60 | $0.045 | Latest |

**UI:** Dropdown mit Preisen im Label

#### FR-1.4.2: Rate Limiting
**Beschreibung:** Processing-Geschwindigkeit
**Range:** 0.2 - 3.0 requests/second
**Default:** 1.0 req/sec
**UI:** Number input

#### FR-1.4.3: Item Limit
**Beschreibung:** Max Anzahl Artikel pro Run
**Range:** 1 - 1000
**Default:** 200
**Behavior:** Wird bei Time Range ignoriert

#### FR-1.4.4: Additional Settings
- **Checkbox:** "Re-analyze already processed articles"
  - `override_existing: true` → Ignoriert bereits analysierte Artikel
  - Warning: "This will override existing analysis results"

### 1.5 Analysis Execution

#### FR-1.5.1: Start Analysis
**Button:** "🚀 Start Analysis"
**Disabled When:**
- Kein Selection-Mode aktiv
- Andere Analysis läuft bereits
- Loading State

**API Call:**
```javascript
POST /api/analysis/start
Body: {
    "scope": { ... },
    "params": { ... }
}
Response: {
    "id": 54,
    "status": "running",
    "started_at": "2025-09-26T12:00:00Z"
}
```

**Post-Start Behavior:**
- Job Status Panel zeigt: "Analyzing X articles... Job ID: 54"
- Frontend startet 3s-Polling auf `/api/analysis/runs/54`
- Nach Completion: Auto-Clear nach 5s
- Active Runs Panel updates automatisch

#### FR-1.5.2: Refresh Preview
**Button:** "🔄 Refresh Preview"
**Behavior:**
- Ruft `updatePreview()` manuell auf
- Disabled während Analysis läuft
- Zeigt Loading-State kurz an

### 1.6 Progress Tracking System

#### FR-1.6.1: Live Progress Display
**Location:** Active Runs Panel (oben)
**Update Frequency:** 3 Sekunden (HTMX polling)
**Query:**
```sql
SELECT
    ar.id,
    ar.status,
    ar.started_at,
    COUNT(*) as total_count,
    COUNT(*) FILTER (WHERE ari.state IN ('completed', 'failed', 'skipped')) as processed_count,
    COUNT(*) FILTER (WHERE ari.state = 'failed') as failed_count
FROM analysis_runs ar
LEFT JOIN analysis_run_items ari ON ari.run_id = ar.id
WHERE ar.status IN ('pending', 'running', 'paused')
GROUP BY ar.id, ar.status, ar.started_at
ORDER BY ar.created_at DESC
```

**Display:**
```
Analysis Run #54
Started: 2025-09-26 12:14:50
[=============>      ] 65%
130/200 items processed
```

#### FR-1.6.2: Auto-Completion Detection
**Worker Logic:**
```python
# In analysis_orchestrator.py
def _check_run_completion(run_id):
    total = count(analysis_run_items WHERE run_id = run_id)
    completed = count(WHERE run_id = run_id AND state IN ('completed', 'failed', 'skipped'))

    if completed == total:
        UPDATE analysis_runs
        SET status = 'completed', completed_at = now()
        WHERE id = run_id
```

#### FR-1.6.3: Frontend Completion Polling
**JavaScript Logic:**
```javascript
// Poll every 3s during run
setInterval(async () => {
    const response = await fetch(`/api/analysis/runs/${runId}`);
    const data = await response.json();

    if (data.status === 'completed') {
        showCompletionMessage();
        setTimeout(() => clearJobStatus(), 5000);
        clearInterval(pollInterval);
    }
}, 3000);
```

### 1.7 Run History & Management

#### FR-1.7.1: History Display
**API:** `GET /htmx/analysis/runs/history?page=1&limit=10`
**Display:**
- Run ID, Started At, Duration, Status
- Items: Processed/Total/Failed
- Progress Bar mit Prozent
- Model Tag

**Status Badges:**
- `completed` → Green Badge
- `failed` → Red Badge
- `cancelled` → Gray Badge

#### FR-1.7.2: Run Details
**On Click:** Expandable Details
**Shows:**
- Scope Configuration (JSON)
- Parameters Used
- Cost Tracking
- Error Messages (if failed)
- Item-Level Results

### 1.8 Statistics Dashboard

#### FR-1.8.1: Horizontal Stats Bar
**Location:** Top of page
**Update:** Every 30 seconds
**Metrics:**

1. **Total Articles**: Count from `items` table
2. **Analyzed**: Count from `item_analysis` table
3. **Coverage**: `(analyzed / total) * 100`
4. **Active Runs**: Count with `status IN ('running', 'pending')`

**Display:**
```
┌─────────────┬──────────┬──────────┬─────────────┐
│ 10,326      │ 2,866    │ 27.8%    │ 0           │
│ TOTAL       │ ANALYZED │ COVERAGE │ ACTIVE RUNS │
└─────────────┴──────────┴──────────┴─────────────┘
```

---

## 2. Technische Architektur

### 2.1 Frontend Stack

#### 2.1.1 Alpine.js Reactive State
**Version:** 3.x
**Main State Object:**
```javascript
Alpine.data('analysisControl', () => ({
    // Central run configuration
    futureRun: {
        selection: {
            mode: 'latest',      // latest | timeRange | unanalyzed
            count: 50,
            days: 7,
            hours: 0,
            feed_id: null
        },
        model: {
            tag: 'gpt-4.1-nano',
            rate_per_second: 1.0,
            limit: 200
        },
        settings: {
            override_existing: false
        },
        computed: {
            articles_to_analyze: 50,
            estimated_cost: 0.005,
            estimated_minutes: 1,
            limit_exceeded: false
        }
    },

    // UI state
    preview: {
        total_items: 0,
        already_analyzed_count: 0,
        new_items_count: 0,
        estimated_cost_usd: 0,
        estimated_duration_minutes: 0
    },

    currentJobStatus: {
        status: 'idle',  // idle | running | done | error
        message: '',
        id: null
    }
}))
```

#### 2.1.2 HTMX Integration
**Version:** 1.9.x
**Pattern:** Server-Side Rendering mit Partial Updates
**Example:**
```html
<div id="active-runs-container"
     hx-get="/htmx/analysis/runs/active"
     hx-trigger="load, every 3s"
     hx-swap="innerHTML">
    <!-- Server renders HTML here -->
</div>
```

#### 2.1.3 Bootstrap 5
**Theme:** Dark Mode optimiert
**Color Palette:**
- Headers: `#e9ecef` (bright white)
- Main Text: `#dee2e6` (light gray)
- Secondary Text: `#adb5bd` (medium gray)
- Card Backgrounds: `rgba(255,255,255,0.05)`
- Borders: `rgba(255,255,255,0.1)`

### 2.2 Backend Stack

#### 2.2.1 FastAPI Router Structure
```
app/
├── api/
│   ├── analysis_control.py      # REST API
│   ├── analysis_jobs.py          # Preview/Confirm Pattern
│   └── analysis_management.py    # Admin Operations
├── web/views/
│   ├── analysis_htmx_clean.py   # HTMX Partials (13 endpoints)
│   ├── analysis_control.py       # Main Page Render
│   └── analysis_monitoring.py    # Monitoring UI
├── services/
│   ├── analysis_orchestrator.py  # Worker Logic
│   ├── analysis_run_manager.py   # Run Management
│   └── auto_analysis_service.py  # Auto-Trigger
├── repositories/
│   ├── analysis_control.py       # DB Access Layer
│   └── analysis_queue.py         # Queue Management
└── domain/analysis/
    └── control.py                # Domain Models
```

#### 2.2.2 Database Schema

**Table: `analysis_runs`**
```sql
CREATE TABLE analysis_runs (
    id SERIAL PRIMARY KEY,
    created_at TIMESTAMP DEFAULT NOW(),
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    status VARCHAR(50) NOT NULL,  -- pending, running, paused, completed, failed
    scope_hash VARCHAR(32),
    triggered_by VARCHAR(50) DEFAULT 'manual',
    filters JSONB,
    total_items INTEGER,
    processed_items INTEGER,
    failed_items INTEGER,
    error_message TEXT,
    avg_processing_time FLOAT,
    model_tag VARCHAR(50)
);
CREATE INDEX idx_analysis_runs_status ON analysis_runs(status);
CREATE INDEX idx_analysis_runs_created_at ON analysis_runs(created_at);
```

**Table: `analysis_run_items`**
```sql
CREATE TABLE analysis_run_items (
    id BIGSERIAL PRIMARY KEY,
    run_id INTEGER NOT NULL REFERENCES analysis_runs(id),
    item_id INTEGER NOT NULL REFERENCES items(id),
    state VARCHAR(50) NOT NULL,  -- queued, processing, completed, failed, skipped
    processing_started_at TIMESTAMP,
    processing_completed_at TIMESTAMP,
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX idx_analysis_run_items_run_id ON analysis_run_items(run_id);
CREATE INDEX idx_analysis_run_items_state ON analysis_run_items(state);
```

**Table: `item_analysis`**
```sql
CREATE TABLE item_analysis (
    item_id INTEGER PRIMARY KEY REFERENCES items(id),
    sentiment_json JSONB,
    impact_json JSONB,
    model_tag VARCHAR(50),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

#### 2.2.3 SQLModel Models
```python
class AnalysisRun(SQLModel, table=True):
    __tablename__ = "analysis_runs"

    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    status: str = Field(index=True)  # RunStatus literal
    scope_hash: Optional[str] = Field(index=True)
    triggered_by: str = "manual"
    filters: Optional[dict] = Field(sa_column=Column(JSON))
    total_items: Optional[int] = None
    processed_items: Optional[int] = None
    failed_items: Optional[int] = None
    model_tag: Optional[str] = None
```

### 2.3 Design Patterns

#### 2.3.1 Repository Pattern
**Purpose:** Abstraktion der Datenbankzugriffe
**Example:**
```python
class AnalysisControlRepo:
    @staticmethod
    def preview_run(scope: RunScope, params: RunParams) -> RunPreview:
        with Session(engine) as session:
            query = AnalysisControlRepo._build_scope_query(scope)
            # ... complex query logic
            return RunPreview(...)

    @staticmethod
    def create_run(scope: RunScope, params: RunParams) -> AnalysisRun:
        # ... create logic
```

#### 2.3.2 Domain Model Pattern
**Purpose:** Business-Logik in Pydantic Models
**Example:**
```python
class RunPreview(BaseModel):
    item_count: int
    estimated_cost_usd: float

    @classmethod
    def calculate(cls, item_count: int, rate: float, model: str):
        cost = (item_count * AVG_TOKENS * MODEL_PRICING[model]["input"]) / 1_000_000
        return cls(item_count=item_count, estimated_cost_usd=cost)
```

#### 2.3.3 Service Layer Pattern
**Purpose:** Orchestrierung von Business-Logik
**Example:**
```python
class AnalysisService:
    def preview_analysis_run(self, scope: RunScope, params: RunParams):
        # Validate inputs
        # Call repository
        # Apply business rules
        # Return result
```

---

## 3. API Spezifikation

### 3.1 REST API Endpoints

#### 3.1.1 Preview Analysis
```http
POST /api/analysis/preview
Content-Type: application/json

{
    "scope": {
        "type": "global",
        "feed_ids": [],
        "unanalyzed_only": true
    },
    "params": {
        "model_tag": "gpt-4.1-nano",
        "rate_per_second": 1.0,
        "limit": 50,
        "override_existing": false
    }
}

Response 200:
{
    "item_count": 201,
    "total_items": 500,
    "already_analyzed_count": 142,
    "new_items_count": 358,
    "estimated_cost_usd": 0.0358,
    "estimated_duration_minutes": 6,
    "has_conflicts": true,
    "sample_item_ids": [11264, 11263, 11261]
}
```

#### 3.1.2 Start Analysis Run
```http
POST /api/analysis/start
Content-Type: application/json

{
    "scope": { ... },
    "params": { ... }
}

Response 200:
{
    "id": 54,
    "created_at": "2025-09-26T12:00:00Z",
    "started_at": "2025-09-26T12:00:01Z",
    "status": "running",
    "scope_hash": "abc123...",
    "total_items": 50,
    "processed_items": 0,
    "failed_items": 0
}

Response 400:
{
    "detail": "Analysis limit exceeded. Maximum 200 articles per run."
}
```

#### 3.1.3 Get Run Status
```http
GET /api/analysis/runs/54

Response 200:
{
    "id": 54,
    "status": "running",
    "started_at": "2025-09-26T12:00:01Z",
    "total_items": 50,
    "processed_items": 32,
    "failed_items": 2,
    "progress_percent": 68.0
}
```

#### 3.1.4 List Runs
```http
GET /api/analysis/runs?status=completed&limit=10

Response 200:
[
    {
        "id": 53,
        "status": "completed",
        "started_at": "2025-09-26T11:00:00Z",
        "completed_at": "2025-09-26T11:05:30Z",
        "total_items": 100,
        "processed_items": 98,
        "failed_items": 2
    }
]
```

### 3.2 HTMX Endpoints

| Endpoint | Trigger | Response | Update Frequency |
|----------|---------|----------|------------------|
| `/htmx/analysis/stats-horizontal` | load, every 30s | Stats HTML | 30s |
| `/htmx/analysis/runs/active` | load, every 3s | Active Runs HTML | 3s |
| `/htmx/analysis/runs/history` | load | History Table | On demand |
| `/htmx/analysis/articles-live` | Selection change | Article List | On change |
| `/htmx/analysis/preview-start` | Parameter change | Preview HTML | On change |
| `/htmx/analysis/feeds-list-options` | load | Feed Dropdown | Once |
| `/htmx/analysis/target-selection` | load | Selection Form | Once |

---

## 4. Business Rules & Logic

### 4.1 Cost Calculation Rules

**BR-4.1.1: Token Estimation**
```python
AVG_TOKENS_PER_ITEM = 500  # Conservative estimate

# Formula
tokens_per_run = item_count * AVG_TOKENS_PER_ITEM
cost_per_run = (tokens_per_run * MODEL_PRICE_PER_1M) / 1_000_000
```

**BR-4.1.2: Model Pricing (per 1M tokens)**
- Nutze `MODEL_PRICING` Dictionary aus `app/domain/analysis/control.py`
- Bei unbekanntem Model: Fallback zu gpt-4.1-nano
- Zeige Input-Preis im Preview (konservativ)

### 4.2 SLO Targets

**BR-4.2.1: Coverage Targets**
```python
SLO_TARGETS = {
    "coverage_10m": 0.90,   # 90% Coverage in 10 min
    "coverage_60m": 0.98,   # 98% Coverage in 60 min
    "error_rate": 0.05,     # Max 5% Error Rate
    "max_cost_per_run": 25.0  # Warning bei >$25
}
```

**BR-4.2.2: Error Rate Calculation**
```python
if processed_items + failed_items > 0:
    error_rate = failed_items / (processed_items + failed_items)

if error_rate > SLO_TARGETS["error_rate"]:
    # Trigger warning
```

### 4.3 Run Lifecycle Rules

**BR-4.3.1: Status Transitions**
```
pending → running → completed
         ↓         ↓
      paused → cancelled
         ↓
       failed
```

**BR-4.3.2: Auto-Completion Rule**
```python
# Worker checks after each item
if all items in ['completed', 'failed', 'skipped']:
    UPDATE analysis_runs
    SET status = 'completed', completed_at = NOW()
```

**BR-4.3.3: Conflict Detection**
```python
already_analyzed = count items WHERE item_id IN (
    SELECT item_id FROM item_analysis
)

if already_analyzed > 0 AND NOT override_existing:
    preview.has_conflicts = True
    preview.already_analyzed_count = already_analyzed
```

### 4.4 Rate Limiting Rules

**BR-4.4.1: Processing Rate**
- Min: 0.2 req/sec (5 seconds per item)
- Max: 3.0 req/sec (0.33 seconds per item)
- Default: 1.0 req/sec

**BR-4.4.2: Duration Estimation**
```python
duration_seconds = item_count / rate_per_second
duration_minutes = max(1, int(duration_seconds / 60))
```

### 4.5 Scope Resolution Rules

**BR-4.5.1: Scope Priority**
1. `type="items"` mit `item_ids` → Explizite Items
2. `type="feeds"` mit `feed_ids` → Feed-basiert
3. `type="timerange"` mit `start_time/end_time` → Zeit-basiert
4. `type="global"` → Alle Artikel (mit Filtern)

**BR-4.5.2: Filter Application Order**
1. Base Scope Query (type-specific)
2. Feed Filter (if `feed_ids` provided)
3. Time Filter (if `start_time/end_time`)
4. Unanalyzed Filter (if `unanalyzed_only=true`)
5. Limit Application (if provided AND NOT timerange)

---

## 5. UI/UX Spezifikation

### 5.1 Layout Structure

```
┌─────────────────────────────────────────────────────────┐
│ Navigation Bar                                           │
├─────────────────────────────────────────────────────────┤
│ [Statistics Dashboard - 4 Metrics Horizontal]           │
├──────────────────────┬──────────────────────────────────┤
│ Target Selection     │ Live Articles Preview            │
│ - Latest (Tab)       │ ┌──────────────────────────────┐ │
│ - Time Range (Tab)   │ │ Article 1                    │ │
│ - Unanalyzed (Tab)   │ │ Source | Date | Badges       │ │
│                      │ └──────────────────────────────┘ │
│ Feed Filter          │ ┌──────────────────────────────┐ │
│ [x] Limit to feed    │ │ Article 2                    │ │
│ [Dropdown]           │ │ Source | Date | Badges       │ │
│ [Apply] [Clear]      │ └──────────────────────────────┘ │
│                      │                                  │
│ Model & Parameters   │ (10 articles visible)            │
│ Model: [Dropdown]    │                                  │
│ Rate: [Input]        │                                  │
│ Limit: [Input]       │                                  │
│ [Apply]              │                                  │
│                      │                                  │
│ Additional Settings  │                                  │
│ [ ] Re-analyze       │                                  │
│                      │                                  │
│ Preview & Start      │                                  │
│ ┌──────────────────┐ │                                  │
│ │ 50   │ 5   │ 45  │ │                                  │
│ │ TOTAL│ANALYZED│TO │ │                                  │
│ ├──────┴─────┴─────┤ │                                  │
│ │ $0.005 │ 1 min  │ │                                  │
│ └────────┴─────────┘ │                                  │
│ [🚀 Start Analysis]  │                                  │
│ [🔄 Refresh Preview] │                                  │
├──────────────────────┴──────────────────────────────────┤
│ Active Runs Panel                                        │
│ ┌────────────────────────────────────────────────────┐  │
│ │ Analysis Run #54                                   │  │
│ │ Started: 12:00:00                                  │  │
│ │ [==============>       ] 65%                       │  │
│ │ 32/50 items processed                              │  │
│ └────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

### 5.2 Dark Mode Color Scheme

**Primary Colors:**
```css
:root[data-theme="dark"] {
    --bg-primary: #1a1d20;
    --bg-secondary: #2b2d30;
    --bg-card: rgba(255,255,255,0.05);

    --text-primary: #e9ecef;      /* Headers */
    --text-secondary: #dee2e6;    /* Body */
    --text-muted: #adb5bd;        /* Labels */

    --border-default: rgba(255,255,255,0.1);
    --border-light: rgba(255,255,255,0.05);

    --accent-primary: #0d6efd;
    --accent-success: #198754;
    --accent-warning: #ffc107;
    --accent-danger: #dc3545;
}
```

### 5.3 Component Styling

#### 5.3.1 Progress Bars
```css
.progress {
    height: 24px;
    background: rgba(0,0,0,0.3);
    border-radius: 4px;
}

.progress-bar {
    font-size: 14px;
    font-weight: 500;
    transition: width 0.3s ease;
}
```

#### 5.3.2 Status Badges
```css
.badge-sentiment {
    background: var(--accent-primary);
}

.badge-urgency {
    background: var(--accent-warning);
}

.badge-impact {
    background: var(--accent-success);
}
```

#### 5.3.3 Card Styling
```css
.nmc-card {
    background: var(--bg-card);
    border: 1px solid var(--border-default);
    border-radius: 8px;
    padding: 1rem;
}
```

### 5.4 Responsive Breakpoints

```css
/* Mobile First */
@media (min-width: 576px) { /* Small devices */ }
@media (min-width: 768px) { /* Tablets */ }
@media (min-width: 992px) {
    /* Desktop - 2 Column Layout */
    .analysis-layout {
        display: grid;
        grid-template-columns: 40% 60%;
    }
}
@media (min-width: 1200px) { /* Large Desktop */ }
```

### 5.5 Accessibility Requirements

**ARIA Labels:**
```html
<button aria-label="Start Analysis"
        aria-describedby="preview-summary">
    🚀 Start Analysis
</button>

<div role="status" aria-live="polite" id="job-status">
    Analysis running: 32 of 50 items processed
</div>
```

**Keyboard Navigation:**
- Tab: Durchlaufe alle Inputs/Buttons
- Enter: Submit Forms / Click Buttons
- Escape: Close Modals / Cancel Actions

**Screen Reader:**
- Status-Updates als `aria-live="polite"`
- Error-Messages als `aria-live="assertive"`
- Progress-Updates mit `aria-valuenow/max/min`

---

## 6. Integration Points

### 6.1 Worker System Integration

**Process:**
```
1. Frontend calls POST /api/analysis/start
2. API creates AnalysisRun + AnalysisRunItems
3. Worker polls for pending runs
4. Worker processes items sequentially
5. Worker updates item state: queued → processing → completed/failed
6. Worker checks for run completion
7. Worker marks run as completed
```

**Worker API:**
```python
# analysis_orchestrator.py
class AnalysisOrchestrator:
    async def run_analysis(self, run_id: int):
        # Get run config
        # Fetch items to analyze
        # Process each item
        # Update states
        # Check completion
```

### 6.2 Database Integration

**Connection:**
- SQLModel Sessions via `app.database.engine`
- Connection Pool: 5-20 connections
- Timeout: 30 seconds

**Transaction Management:**
```python
with Session(engine) as session:
    try:
        # Operations
        session.commit()
    except Exception as e:
        session.rollback()
        raise
```

### 6.3 Frontend-Backend Communication

**Pattern 1: HTMX Polling**
```html
<div hx-get="/htmx/analysis/runs/active"
     hx-trigger="every 3s"
     hx-swap="innerHTML">
    <!-- Auto-updates every 3s -->
</div>
```

**Pattern 2: Alpine.js API Calls**
```javascript
async updatePreview() {
    const response = await fetch('/api/analysis/preview', {
        method: 'POST',
        body: JSON.stringify({ scope, params })
    });
    this.preview = await response.json();
}
```

---

## 7. Error Handling & Logging

### 7.1 Frontend Error Handling

**User-Facing Errors:**
```javascript
try {
    const response = await fetch('/api/analysis/start', {...});
    if (!response.ok) {
        const error = await response.json();
        showAlert('danger', error.detail);
    }
} catch (error) {
    showAlert('danger', 'Network error. Please try again.');
}
```

**Alert Display:**
```html
<div class="alert alert-danger" role="alert">
    <strong>Error:</strong> Analysis limit exceeded. Maximum 200 articles per run.
</div>
```

### 7.2 Backend Error Handling

**Exception Handling:**
```python
@router.post("/start")
async def start_run(...):
    try:
        result = await analysis_service.start_analysis_run(scope, params)
        if not result.success:
            raise HTTPException(status_code=400, detail=result.error)
        return result.data
    except ValueError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception(f"Unexpected error in start_run: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
```

**Logging Strategy:**
```python
logger.info(f"Starting analysis run: scope={scope.type}, items={preview.item_count}")
logger.warning(f"Run {run_id} has high error rate: {error_rate:.2%}")
logger.error(f"Failed to process item {item_id}: {error}")
logger.debug(f"Preview calculation: {preview.model_dump()}")
```

### 7.3 Worker Error Handling

**Item-Level Errors:**
```python
try:
    result = await analyze_item(item_id)
    UPDATE analysis_run_items
    SET state = 'completed', processing_completed_at = NOW()
except Exception as e:
    UPDATE analysis_run_items
    SET state = 'failed', error_message = str(e)

    if retry_count < MAX_RETRIES:
        # Schedule retry
```

**Run-Level Errors:**
```python
try:
    await run_analysis(run_id)
except Exception as e:
    UPDATE analysis_runs
    SET status = 'failed', error_message = str(e)
    logger.exception(f"Run {run_id} failed")
```

---

## 8. Performance Requirements

### 8.1 Response Time Targets

| Operation | Target | Max Acceptable |
|-----------|--------|----------------|
| Page Load | <500ms | 1s |
| Preview Calculation | <200ms | 500ms |
| Start Run | <300ms | 1s |
| HTMX Partial Update | <100ms | 300ms |
| API Response | <200ms | 500ms |

### 8.2 Database Query Optimization

**Indexing Strategy:**
```sql
-- Critical Indexes
CREATE INDEX idx_analysis_runs_status ON analysis_runs(status);
CREATE INDEX idx_analysis_run_items_run_state ON analysis_run_items(run_id, state);
CREATE INDEX idx_item_analysis_item_id ON item_analysis(item_id);
CREATE INDEX idx_items_published ON items(published);
```

**Query Optimization:**
- Use `COUNT(*) FILTER (WHERE ...)` statt Subqueries
- LEFT JOIN statt mehrfache Queries
- LIMIT frühzeitig anwenden
- Vermeidung von `SELECT *`

### 8.3 Frontend Performance

**Bundle Size:**
- Alpine.js: ~15KB gzipped
- HTMX: ~12KB gzipped
- Custom JS: <20KB
- Total JS: <50KB

**Lazy Loading:**
```javascript
// Load article list only when visible
if (container.offsetHeight > 0) {
    updateArticlesDisplay();
}
```

**Debouncing:**
```javascript
// Debounce input changes
let debounceTimer;
input.addEventListener('input', () => {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => updatePreview(), 300);
});
```

---

## 9. Known Issues & Limitations

### 9.1 Current Problems (v3.4)

**PROBLEM-1: Dual JavaScript Systems**
- **Issue:** `analysis-controller.js` (legacy) + Inline Alpine.js konkurrieren
- **Impact:** State-Synchronisations-Probleme, doppelte Event-Handler
- **Workaround:** Input-Felder binden direkt an `futureRun`
- **Fix Required:** Vollständige Neuimplementierung nur mit Alpine.js

**PROBLEM-2: Preview nicht automatisch aktualisiert**
- **Issue:** Änderungen in Inputs triggern nicht `updatePreview()`
- **Impact:** Preview zeigt veraltete Werte
- **Workaround:** `@change="setLatestSelection()"` auf Inputs
- **Fix Required:** Reactive Watchers für alle relevanten Properties

**PROBLEM-3: Article Display zeigt analysierte Artikel**
- **Issue:** `unanalyzed_only` Filter nicht konsistent angewendet
- **Impact:** User sieht bereits analysierte Artikel in Preview
- **Workaround:** Manueller Filter in Query
- **Fix Required:** Einheitliche Filter-Logik

### 9.2 Technical Debt

**TD-1: Schema Import Issues**
```python
# Current workaround in multiple files
from typing import Any
RunScope = Any  # Should be: from app.domain.analysis.control import RunScope
```

**TD-2: Template Size**
- `analysis_control_refactored.html`: 1009 Zeilen
- **Issue:** Zu groß, schwer wartbar
- **Solution:** Split in Komponenten + Partials

**TD-3: Missing Tests**
- Unit Tests: 0%
- Integration Tests: 0%
- E2E Tests: 0%

### 9.3 Browser Compatibility Issues

- Safari <14: CSS Grid Layout problems
- Firefox <88: Alpine.js reactivity delays
- Edge <90: HTMX polling instability

---

## 10. Future Enhancements (v4.0+)

### 10.1 Planned Features

**FEAT-1: Bulk Operations**
- Multi-Select in History
- Batch Cancel/Retry
- Bulk Export

**FEAT-2: Advanced Filtering**
```javascript
filters: {
    sentiment_range: [-1.0, 1.0],
    impact_threshold: 0.5,
    sources: ['reuters', 'bloomberg'],
    keywords: ['bitcoin', 'crypto']
}
```

**FEAT-3: Export Functionality**
- CSV Export: Runs + Results
- JSON Export: Full Configuration
- PDF Report: Summary + Charts

**FEAT-4: WebSocket Live Updates**
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/analysis');
ws.onmessage = (event) => {
    const update = JSON.parse(event.data);
    if (update.type === 'progress') {
        updateProgressBar(update.data);
    }
};
```

**FEAT-5: Preset Management UI**
- Save Configuration as Preset
- Load Preset
- Share Presets (Export/Import JSON)
- Default Preset per User

### 10.2 Technical Improvements

**IMPROVE-1: React/Vue Migration**
- Replace Alpine.js + HTMX with Modern Framework
- Better State Management
- Component Reusability

**IMPROVE-2: GraphQL API**
```graphql
query GetRun($id: Int!) {
    analysisRun(id: $id) {
        id
        status
        items {
            id
            state
            article { title, source }
        }
    }
}
```

**IMPROVE-3: Caching Strategy**
- Redis für Preview-Cache (5min TTL)
- Browser LocalStorage für UI-State
- Query Result Caching (PostgreSQL)

### 10.3 Monitoring & Observability

**MONITOR-1: Metrics Dashboard**
- Grafana Dashboards
- Prometheus Metrics
- Custom SLO Tracking

**MONITOR-2: Error Tracking**
- Sentry Integration
- Error Rate Alerts
- Failed Run Notifications

**MONITOR-3: Performance Monitoring**
- Query Performance Tracking
- API Response Time Histograms
- Worker Processing Rate

---

## 11. Deployment & Operations

### 11.1 System Requirements

**Production Environment:**
- **CPU:** 4+ cores
- **RAM:** 8GB+ (2GB for web, 4GB for worker, 2GB for DB)
- **Storage:** 50GB+ SSD
- **Network:** 100Mbps+

**Database Requirements:**
- PostgreSQL 14+
- Connection Pool: 20-50 connections
- Disk: 20GB+ (grows with analysis results)

### 11.2 Configuration

**Environment Variables:**
```bash
# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/news_db

# Analysis Settings
MAX_CONCURRENT_RUNS=3
DEFAULT_MODEL_TAG=gpt-4.1-nano
DEFAULT_RATE_PER_SECOND=1.0
DEFAULT_LIMIT=200

# Worker Settings
WORKER_POLL_INTERVAL=5
WORKER_MAX_RETRIES=3

# API Settings
API_CORS_ORIGINS=http://localhost:3000,http://localhost:8000
```

### 11.3 Monitoring Commands

```bash
# Check server status
curl http://localhost:8000/admin/health

# Monitor active runs
curl http://localhost:8000/api/analysis/status

# Worker status
curl http://localhost:8000/api/analysis/worker/status

# Database stats
psql -U news_user -d news_db -c "
    SELECT status, COUNT(*)
    FROM analysis_runs
    GROUP BY status;
"
```

---

## 12. Testing Strategy

### 12.1 Unit Tests (Required)

**Test Coverage Targets:**
- Domain Models: 100%
- Repositories: 90%
- Services: 85%
- API Endpoints: 80%

**Example Test:**
```python
def test_preview_calculation():
    scope = RunScope(type="global", unanalyzed_only=True)
    params = RunParams(model_tag="gpt-4.1-nano", limit=50)

    preview = AnalysisControlRepo.preview_run(scope, params)

    assert preview.item_count <= 50
    assert preview.estimated_cost_usd > 0
    assert preview.estimated_duration_minutes > 0
```

### 12.2 Integration Tests (Required)

**Test Scenarios:**
1. Complete Analysis Run Lifecycle
2. Preview → Start → Progress → Completion
3. Error Handling & Recovery
4. Concurrent Run Management

**Example Test:**
```python
async def test_analysis_run_lifecycle():
    # 1. Preview
    preview_response = await client.post("/api/analysis/preview", json={...})
    assert preview_response.status_code == 200

    # 2. Start
    start_response = await client.post("/api/analysis/start", json={...})
    run_id = start_response.json()["id"]

    # 3. Monitor Progress
    for _ in range(30):
        status = await client.get(f"/api/analysis/runs/{run_id}")
        if status.json()["status"] == "completed":
            break
        await asyncio.sleep(1)

    # 4. Verify Results
    assert status.json()["processed_items"] > 0
```

### 12.3 E2E Tests (Optional)

**Playwright/Cypress Tests:**
```javascript
test('User can start analysis run', async ({ page }) => {
    // Navigate to analysis page
    await page.goto('http://localhost:8000/admin/analysis');

    // Select latest mode
    await page.click('text=Latest Articles');
    await page.fill('input[x-model="futureRun.selection.count"]', '10');
    await page.click('text=Apply');

    // Verify preview updates
    await expect(page.locator('.stat-value')).toContainText('10');

    // Start run
    await page.click('text=Start Analysis');

    // Wait for completion
    await page.waitForSelector('text=Analysis completed', { timeout: 60000 });
});
```

---

## 13. Migration Path (v3.4 → v4.0)

### 13.1 Database Migration

**Step 1: Backup**
```bash
pg_dump -U news_user -d news_db > backup_pre_v4.sql
```

**Step 2: Schema Updates**
```sql
-- Add new columns if needed
ALTER TABLE analysis_runs ADD COLUMN scope_json JSONB;
ALTER TABLE analysis_runs ADD COLUMN params_json JSONB;

-- Update indexes
CREATE INDEX idx_analysis_runs_scope_json ON analysis_runs USING GIN (scope_json);
```

**Step 3: Data Migration**
```python
# Migrate old filters JSON to new scope/params format
for run in old_runs:
    scope = convert_filters_to_scope(run.filters)
    params = extract_params(run)

    UPDATE analysis_runs
    SET scope_json = scope, params_json = params
    WHERE id = run.id
```

### 13.2 Code Migration

**Phase 1: Frontend Cleanup**
- Remove `analysis-controller.js` (legacy)
- Konsolidiere alle Logic in Alpine.js
- Entferne doppelte Event-Handler

**Phase 2: Backend Refactoring**
- Vereinheitliche API-Responses
- Konsolidiere HTMX Endpoints
- Refactor Repository-Layer

**Phase 3: Testing**
- Implementiere Unit Tests
- Implementiere Integration Tests
- Load Testing

### 13.3 Rollback Plan

**If Critical Issues:**
```bash
# Restore database
psql -U news_user -d news_db < backup_pre_v4.sql

# Revert code
git checkout v3.4-stable

# Restart services
./scripts/restart-all.sh
```

---

## Appendix A: Code Examples

### A.1 Complete Alpine.js Component
```javascript
Alpine.data('analysisControlV4', () => ({
    // State
    futureRun: {
        selection: {
            mode: 'latest',
            count: 50,
            days: 7,
            hours: 0,
            feed_id: null
        },
        model: {
            tag: 'gpt-4.1-nano',
            rate_per_second: 1.0,
            limit: 200
        },
        settings: {
            override_existing: false
        }
    },

    preview: {
        total_items: 0,
        already_analyzed_count: 0,
        new_items_count: 0,
        estimated_cost_usd: 0,
        estimated_duration_minutes: 0
    },

    currentJobStatus: {
        status: 'idle',
        message: '',
        id: null
    },

    availableFeeds: [],
    loading: false,

    // Lifecycle
    init() {
        this.loadFeeds();
        this.loadSavedState();
        this.updatePreview();
    },

    // Methods
    async loadFeeds() {
        const response = await fetch('/api/feeds');
        this.availableFeeds = await response.json();
    },

    loadSavedState() {
        const saved = localStorage.getItem('futureRun');
        if (saved) {
            this.futureRun = JSON.parse(saved);
        }
    },

    async updatePreview() {
        const scope = this.buildScope();
        const params = this.buildParams();

        const response = await fetch('/api/analysis/preview', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ scope, params })
        });

        this.preview = await response.json();
    },

    async startRun() {
        this.loading = true;

        try {
            const response = await fetch('/api/analysis/start', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    scope: this.buildScope(),
                    params: this.buildParams()
                })
            });

            const run = await response.json();
            this.currentJobStatus = {
                status: 'running',
                message: `Analyzing ${run.total_items} articles...`,
                id: run.id
            };

            this.pollRunStatus(run.id);
        } catch (error) {
            this.currentJobStatus = {
                status: 'error',
                message: error.message,
                id: null
            };
        } finally {
            this.loading = false;
        }
    },

    pollRunStatus(runId) {
        const pollInterval = setInterval(async () => {
            const response = await fetch(`/api/analysis/runs/${runId}`);
            const run = await response.json();

            if (run.status === 'completed') {
                this.currentJobStatus = {
                    status: 'done',
                    message: `Completed! Processed ${run.processed_items} items.`,
                    id: runId
                };

                clearInterval(pollInterval);

                setTimeout(() => {
                    this.currentJobStatus = { status: 'idle', message: '', id: null };
                }, 5000);
            }
        }, 3000);
    },

    buildScope() {
        const scope = {
            type: this.futureRun.selection.mode === 'latest' ? 'global' : this.futureRun.selection.mode,
            feed_ids: this.futureRun.selection.feed_id ? [this.futureRun.selection.feed_id] : [],
            unanalyzed_only: !this.futureRun.settings.override_existing
        };

        if (this.futureRun.selection.mode === 'timeRange') {
            const totalHours = this.futureRun.selection.days * 24 + this.futureRun.selection.hours;
            const endTime = new Date();
            const startTime = new Date(endTime.getTime() - totalHours * 60 * 60 * 1000);

            scope.start_time = startTime.toISOString();
            scope.end_time = endTime.toISOString();
        }

        return scope;
    },

    buildParams() {
        return {
            model_tag: this.futureRun.model.tag,
            rate_per_second: this.futureRun.model.rate_per_second,
            limit: this.futureRun.selection.count,
            override_existing: this.futureRun.settings.override_existing,
            newest_first: true
        };
    },

    // Watchers
    watch: {
        'futureRun.selection': {
            deep: true,
            handler() {
                this.updatePreview();
                this.saveState();
            }
        },
        'futureRun.model': {
            deep: true,
            handler() {
                this.updatePreview();
                this.saveState();
            }
        }
    },

    saveState() {
        localStorage.setItem('futureRun', JSON.stringify(this.futureRun));
    }
}))
```

---

## Appendix B: Database Queries

### B.1 Preview Query (Optimized)
```sql
-- Get count of items in scope
WITH scope_items AS (
    SELECT i.id
    FROM items i
    WHERE 1=1
      -- Feed filter
      AND (COALESCE(:feed_id::int, 0) = 0 OR i.feed_id = :feed_id)
      -- Time filter
      AND (COALESCE(:start_time::timestamp, '1970-01-01') <= i.published)
      AND (i.published <= COALESCE(:end_time::timestamp, NOW()))
    ORDER BY i.published DESC
    LIMIT :limit
),
analyzed_items AS (
    SELECT item_id
    FROM item_analysis
    WHERE item_id IN (SELECT id FROM scope_items)
)
SELECT
    COUNT(*) as total_items,
    COUNT(a.item_id) as already_analyzed,
    COUNT(*) - COUNT(a.item_id) as new_items
FROM scope_items s
LEFT JOIN analyzed_items a ON s.id = a.item_id;
```

### B.2 Active Runs Query (with Progress)
```sql
SELECT
    ar.id,
    ar.status,
    ar.started_at,
    COUNT(*) as total_count,
    COUNT(*) FILTER (WHERE ari.state IN ('completed', 'failed', 'skipped')) as processed_count,
    COUNT(*) FILTER (WHERE ari.state = 'failed') as failed_count,
    ROUND(
        COUNT(*) FILTER (WHERE ari.state IN ('completed', 'failed', 'skipped'))::numeric
        / NULLIF(COUNT(*), 0) * 100,
        1
    ) as progress_percent
FROM analysis_runs ar
LEFT JOIN analysis_run_items ari ON ari.run_id = ar.id
WHERE ar.status IN ('pending', 'running', 'paused')
GROUP BY ar.id, ar.status, ar.started_at
ORDER BY ar.created_at DESC;
```

---

## Document Change Log

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 1.0 | 2025-09-26 | Initial comprehensive requirements | Claude Code |

---

**END OF REQUIREMENTS SPECIFICATION**

_This document serves as the single source of truth for rebuilding the Analysis Cockpit from scratch._