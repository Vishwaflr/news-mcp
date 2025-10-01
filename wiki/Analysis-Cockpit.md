# Analysis Cockpit v4 - Manual Analysis Interface

The **Analysis Cockpit v4** is the flagship web interface for manual AI-powered analysis of RSS feed items.

**URL:** `http://localhost:8000/admin/analysis`

---

## 🎯 Overview

The Analysis Cockpit provides a complete workflow for:

1. **Target Selection** - Choose what to analyze (feeds, categories, date ranges)
2. **Preview** - See exactly what will be analyzed before starting
3. **Execution** - Start analysis runs with real-time progress tracking
4. **Monitoring** - Watch progress with live updates and detailed metrics

### Key Features

- ✅ **Alpine.js v3** - Reactive UI with client-side state management
- ✅ **HTMX** - Server-side rendering for dynamic components
- ✅ **Dark Mode** - Professional dark theme optimized for long sessions
- ✅ **Real-time Updates** - WebSocket + polling for live progress
- ✅ **Preview System** - See selection before committing to analysis
- ✅ **Queue Management** - View active runs and queue status

---

## 🚀 Quick Start

### Step 1: Access the Cockpit

Navigate to: `http://localhost:8000/admin/analysis`

### Step 2: Select Analysis Target

Choose one of three targeting modes:

- **By Feed** - Analyze specific feeds
- **By Category** - Analyze all feeds in a category
- **By Date Range** - Analyze items from specific time period

### Step 3: Configure Parameters

Set analysis parameters:

- **Scope Limit** - Maximum items to analyze (default: 50)
- **Date Range** - From/To dates (optional)
- **Skip Analyzed** - Skip items already analyzed (recommended)

### Step 4: Preview Selection

Click **"Preview Selection"** to see:

- Number of items that will be analyzed
- Estimated cost (OpenAI API usage)
- List of items to be processed

### Step 5: Start Analysis

Click **"Start Analysis"** to begin processing. Monitor progress in real-time.

---

## 📊 Interface Sections

### 1. Control Panel (Top Section)

The main control area for configuring and launching analysis runs.

#### Target Selection

**Feed-Based Targeting:**
```html
<select name="feed_id">
  <option value="">-- Select Feed --</option>
  <option value="1">TechCrunch</option>
  <option value="2">The Verge</option>
  ...
</select>
```

**Category-Based Targeting:**
```html
<select name="category_id">
  <option value="">-- Select Category --</option>
  <option value="1">Technology</option>
  <option value="2">Business</option>
  ...
</select>
```

**Date Range Targeting:**
```html
<input type="date" name="date_from" placeholder="From Date">
<input type="date" name="date_to" placeholder="To Date">
```

#### Analysis Parameters

**Scope Limit:**
- Controls maximum items to analyze in one run
- Default: 50
- Range: 1-1000
- Use lower values for testing, higher for production

**Skip Analyzed Items:**
- Checkbox to skip items already analyzed
- Enabled by default
- Prevents duplicate analysis costs

---

### 2. Preview Panel

Shows selection details before analysis starts.

**Preview Information:**

| Field | Description | Example |
|-------|-------------|---------|
| **Items Found** | Total items matching criteria | 127 items |
| **Already Analyzed** | Items already processed | 45 items |
| **Will Analyze** | Items to be processed | 82 items |
| **Estimated Cost** | OpenAI API cost estimate | ~$0.41 |
| **Estimated Time** | Processing time estimate | ~27 seconds |

**Sample Preview Output:**
```
Selection Preview
─────────────────────────────────────────
Target: Feed "TechCrunch"
Date Range: 2025-09-25 to 2025-10-01
Scope Limit: 50

Items Found: 127
Already Analyzed: 45
Will Analyze: 50 (limited by scope)

Estimated Cost: $0.25
Estimated Time: 17 seconds
─────────────────────────────────────────
```

---

### 3. Progress Monitoring

Real-time progress tracking during analysis execution.

#### Progress Bar

- **Visual progress** - Animated progress bar (0-100%)
- **Item counter** - "15/50 items processed"
- **Status text** - Current operation status
- **ETA** - Estimated time remaining

#### Live Metrics

```
┌─────────────────────────────────────────┐
│ Progress: ▓▓▓▓▓▓▓▓▓▓░░░░░░░░ 50%       │
│ Items: 25/50 processed                  │
│ Speed: 3.2 items/second                 │
│ ETA: 8 seconds remaining                │
│ Errors: 0                               │
└─────────────────────────────────────────┘
```

#### Status Indicators

| Status | Color | Meaning |
|--------|-------|---------|
| **Pending** | 🟡 Yellow | Run queued, waiting to start |
| **Running** | 🔵 Blue | Currently processing |
| **Completed** | 🟢 Green | Successfully finished |
| **Failed** | 🔴 Red | Error occurred |
| **Cancelled** | ⚫ Gray | Manually stopped |

---

### 4. Active Runs Panel

Shows all currently active analysis runs across the system.

**Information Displayed:**

- Run ID
- Target (feed/category name)
- Progress percentage
- Items processed/total
- Status (running/queued/completed)
- Actions (view details, cancel)

**Example:**
```
Active Runs
────────────────────────────────────────────────────
Run #123 | TechCrunch      | ▓▓▓▓░░░░ 45% | 23/50
Run #124 | Business (Cat)  | ▓░░░░░░░ 12% | 6/50
Run #125 | The Verge       | Queued        | 0/30
────────────────────────────────────────────────────
```

---

### 5. History Panel

Recent analysis run history with results.

**Columns:**

- **Run ID** - Unique identifier
- **Target** - What was analyzed
- **Items** - Total items processed
- **Status** - Final result (completed/failed)
- **Duration** - Total time taken
- **Timestamp** - When run started
- **Actions** - View results, re-run

**Example History:**
```
Recent Runs
──────────────────────────────────────────────────────────────
#122 | TechCrunch     | 50 items | ✅ Completed | 16s | 2m ago
#121 | Technology     | 127 items| ✅ Completed | 42s | 15m ago
#120 | The Verge      | 30 items | ❌ Failed    | 8s  | 1h ago
──────────────────────────────────────────────────────────────
```

---

## 🎨 User Interface Features

### Dark Mode Theme

**Color Scheme:**
- Background: `#1a1d20` (primary), `#2b2d30` (secondary)
- Text: `#e9ecef` (primary), `#dee2e6` (secondary)
- Accents: Bootstrap blue (`#0d6efd`) for actions
- Success: Green (`#198754`)
- Warning: Yellow (`#ffc107`)
- Danger: Red (`#dc3545`)

### Responsive Design

- **Desktop** (>1200px) - Full 3-column layout
- **Tablet** (768-1200px) - 2-column layout
- **Mobile** (<768px) - Stacked single column

### Interactive Elements

**Buttons:**
- **Primary Actions** - Large blue buttons (Start Analysis, Preview)
- **Secondary Actions** - Gray buttons (Cancel, Reset)
- **Danger Actions** - Red buttons (Stop, Delete)

**Form Controls:**
- Dark-themed inputs and selects
- Focus states with blue glow
- Placeholder text in muted gray

### Animations

- **Progress Bar** - Smooth width transitions (0.3s ease)
- **Metric Cards** - Hover lift effect (-2px translateY)
- **Buttons** - Ripple effect on click
- **Status Changes** - Color fade transitions

---

## 🔧 Technical Implementation

### Technology Stack

**Frontend:**
```html
<!-- Alpine.js for reactive state -->
<script src="https://cdn.jsdelivr.net/npm/alpinejs@3.13.5/dist/cdn.min.js"></script>

<!-- HTMX for server-side rendering -->
<script src="https://unpkg.com/htmx.org@1.9.10"></script>

<!-- Bootstrap 5 for UI components -->
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css">
```

**Backend:**
- FastAPI for API endpoints
- Jinja2 for template rendering
- WebSocket for real-time updates

### Alpine.js State Management

```javascript
x-data="{
  selectedFeed: null,
  selectedCategory: null,
  dateFrom: '',
  dateTo: '',
  scopeLimit: 50,
  skipAnalyzed: true,
  previewData: null,
  activeRuns: [],
  currentRun: null
}"
```

**Reactive Bindings:**
- `x-model` - Two-way data binding for form inputs
- `x-show` - Conditional visibility
- `x-if` - Conditional rendering
- `x-on` - Event handlers

### HTMX Integration

**Partial Updates:**
```html
<!-- Preview selection (HTMX) -->
<button hx-post="/api/analysis/preview"
        hx-target="#preview-panel"
        hx-swap="innerHTML">
  Preview Selection
</button>

<!-- Start analysis (HTMX) -->
<button hx-post="/api/analysis/runs"
        hx-target="#active-runs"
        hx-swap="afterbegin">
  Start Analysis
</button>
```

**Polling for Updates:**
```html
<!-- Auto-refresh active runs every 2 seconds -->
<div hx-get="/htmx/analysis/active-runs"
     hx-trigger="every 2s"
     hx-swap="innerHTML">
  Loading active runs...
</div>
```

### WebSocket Real-time Updates

**Connection:**
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/analysis');

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);

  if (data.type === 'progress') {
    updateProgressBar(data.progress);
  }

  if (data.type === 'status') {
    updateRunStatus(data.run_id, data.status);
  }
};
```

**Event Types:**
- `progress` - Progress percentage updates
- `status` - Status changes (running → completed)
- `item_processed` - Individual item completion
- `error` - Error notifications

---

## 📡 API Endpoints Used

### Preview Selection

**Endpoint:** `POST /api/analysis/preview`

**Request:**
```json
{
  "feed_id": 1,
  "date_from": "2025-09-25",
  "date_to": "2025-10-01",
  "scope_limit": 50,
  "skip_analyzed": true
}
```

**Response:**
```json
{
  "total_items": 127,
  "already_analyzed": 45,
  "will_analyze": 50,
  "estimated_cost": 0.25,
  "estimated_time": 17
}
```

### Start Analysis Run

**Endpoint:** `POST /api/analysis/runs`

**Request:**
```json
{
  "selection_id": "abc123",
  "target_type": "feed",
  "target_id": 1
}
```

**Response:**
```json
{
  "run_id": 123,
  "status": "queued",
  "items_count": 50,
  "created_at": "2025-10-01T10:00:00Z"
}
```

### Get Active Runs

**Endpoint:** `GET /api/analysis/runs/active`

**Response:**
```json
{
  "runs": [
    {
      "run_id": 123,
      "status": "running",
      "progress": 45,
      "items_processed": 23,
      "items_total": 50
    }
  ]
}
```

### Cancel Run

**Endpoint:** `POST /api/analysis/runs/{run_id}/cancel`

**Response:**
```json
{
  "success": true,
  "run_id": 123,
  "status": "cancelled"
}
```

---

## ⚙️ Configuration

### Environment Variables

```bash
# Analysis settings
MAX_CONCURRENT_RUNS=5
MAX_DAILY_RUNS=100
OPENAI_API_KEY=sk-...

# UI settings (optional)
ENABLE_WEBSOCKET=true
POLLING_INTERVAL=2000  # milliseconds
```

### Rate Limits

**Daily Limits:**
- Manual runs: 100/day (configurable via `MAX_DAILY_RUNS`)
- Items per run: 1-1000 (default scope: 50)

**Concurrent Limits:**
- Simultaneous runs: 5 (configurable via `MAX_CONCURRENT_RUNS`)

**OpenAI API:**
- Rate: 3.0 requests/second (configurable via `AUTO_ANALYSIS_RATE_PER_SECOND`)

---

## 🎯 Use Cases

### 1. Quick Feed Analysis

**Scenario:** Analyze latest 50 items from a specific feed

**Steps:**
1. Select feed from dropdown
2. Leave date range empty (uses latest items)
3. Set scope limit: 50
4. Enable "Skip analyzed"
5. Preview → Start

**Time:** ~17 seconds
**Cost:** ~$0.25

### 2. Category-Wide Analysis

**Scenario:** Analyze all "Technology" category feeds

**Steps:**
1. Select "Technology" category
2. Set date range: last 7 days
3. Set scope limit: 200
4. Preview → Start

**Time:** ~1 minute
**Cost:** ~$1.00

### 3. Historical Analysis

**Scenario:** Analyze specific date range for research

**Steps:**
1. Select feed(s) or category
2. Set date range: 2025-09-01 to 2025-09-30
3. Set scope limit: 500
4. Disable "Skip analyzed" (re-analyze if needed)
5. Preview → Start

**Time:** ~2-3 minutes
**Cost:** ~$2.50

### 4. Quality Control

**Scenario:** Re-analyze items to verify sentiment accuracy

**Steps:**
1. Select feed
2. Set small scope (10-20 items)
3. Disable "Skip analyzed"
4. Preview → Start
5. Compare results with previous analysis

---

## 🐛 Troubleshooting

### Issue: Preview shows 0 items

**Cause:** No items match selection criteria

**Solutions:**
- Check date range (might be too narrow)
- Verify feed has items in database
- Try different feed/category
- Check if all items already analyzed (disable "Skip analyzed")

### Issue: Analysis run stuck at 0%

**Cause:** Worker not processing, queue issue

**Solutions:**
- Check worker status: `/admin/health`
- View worker logs: `tail -f logs/analysis-worker.log`
- Restart worker: `./scripts/start-worker.sh`
- Check queue: `/admin/manager`

### Issue: WebSocket not connecting

**Cause:** WebSocket server not running

**Solutions:**
- Check web server logs
- Verify WebSocket endpoint: `ws://localhost:8000/ws/analysis`
- Fall back to polling (auto-refresh still works)
- Check firewall/proxy settings

### Issue: High OpenAI costs

**Cause:** Large scope limits, frequent analysis

**Solutions:**
- Reduce scope limit (use 20-50 instead of 500)
- Enable "Skip analyzed" to avoid duplicates
- Use category targeting carefully (can process many items)
- Monitor daily usage: `/admin/metrics`

---

## 🔗 Related Pages

- **[Dashboard Overview](Dashboard-Overview)** - All dashboards
- **[Auto-Analysis Dashboard](Auto-Analysis-Dashboard)** - Automatic analysis
- **[Manager Control Center](Manager-Control-Center)** - System controls
- **[Analysis API](API-Analysis)** - Programmatic access
- **[Troubleshooting](Troubleshooting-Common)** - General issues

---

**Template File:** `templates/analysis_cockpit_v4.html`
**Last Updated:** 2025-10-01
**Version:** 4.0
