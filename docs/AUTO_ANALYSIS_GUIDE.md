# Auto-Analysis System - User Guide

**Version:** 2.0.0
**Status:** ✅ Production - 12 Feeds Active
**Last Updated:** 2025-10-03
**Performance:** 1,523 analysis runs, 8,591 items analyzed, >95% success rate

---

## 📋 Overview

The Auto-Analysis System enables automatic AI analysis of new articles immediately after feed fetching. As soon as a feed retrieves new items, they are automatically queued for analysis and processed by the Analysis Worker.

### Features

- ✅ **Feed-Level Toggle**: Enable/disable auto-analysis per feed
- ✅ **Queue-Based Processing**: Async processing with `pending_auto_analysis` table
- ✅ **Rate Limiting**: Concurrent run limits (6 max), configurable via .env
- ✅ **Error Handling**: Categorized errors with fallback results
- ✅ **Live Dashboard**: HTMX-based real-time overview at `/admin/auto-analysis`
- ✅ **Cost Control**: Optimized models (gpt-4o-mini) for auto-analyses
- ✅ **Background Worker**: Dedicated analysis worker service

---

## 🚀 Quick Start

### 1. Enable Auto-Analysis for a Feed

**Via API:**
```bash
curl -X POST "http://localhost:8000/api/feeds/1/toggle-auto-analysis?enabled=true"
```

**Response:**
```json
{
  "success": true,
  "feed_id": 1,
  "auto_analyze_enabled": true,
  "message": "Auto-analysis enabled for feed 'TechCrunch'"
}
```

**Via UI:**
1. Open `/admin/feeds`
2. Click the green/gray "🤖 ON/OFF" button for the desired feed
3. Feed card refreshes automatically

### 2. Check Status

**Via API:**
```bash
curl "http://localhost:8000/api/feeds/1/auto-analysis-status"
```

**Response:**
```json
{
  "success": true,
  "feed_id": 1,
  "feed_title": "TechCrunch",
  "auto_analyze_enabled": true,
  "stats": {
    "auto_runs_last_7_days": 5,
    "auto_analysis_enabled": true,
    "last_auto_run": "2025-09-27T18:30:00Z"
  }
}
```

### 3. View Dashboards

**Feed Management:**
```
http://localhost:8000/admin/feeds
```
- 🟢 Green "Auto-Analysis ON" = Active
- 🔘 Gray "Auto-Analysis OFF" = Disabled

**Auto-Analysis Dashboard:**
```
http://localhost:8000/admin/auto-analysis
```
- Real-time queue status
- Success/failure metrics
- Per-feed configuration
- Recent analysis history

---

## 🔧 System Architecture

### Workflow

```
1. Feed Scheduler triggers fetch (every N minutes)
           ↓
2. SyncFeedFetcher retrieves new items
           ↓
3. Check: Feed.auto_analyze_enabled = True?
           ↓ YES
4. Create PendingAutoAnalysis job
           ↓
5. Worker retrieves job from queue
           ↓
6. PendingAnalysisProcessor → Analysis Run
           ↓
7. Store results in item_analysis
```

### Components

| Component | File | Description |
|-----------|------|-------------|
| **Auto-Analysis Service** | `app/services/auto_analysis_service.py` | Direct trigger + stats |
| **Pending Processor** | `app/services/pending_analysis_processor.py` | Queue processing |
| **Feed Fetcher** | `app/services/feed_fetcher_sync.py` | Integration hook |
| **API Endpoints** | `app/api/feeds.py` | Toggle + status |
| **HTMX Views** | `app/web/views/auto_analysis_views.py` | Dashboard + queue |

### Database Schema

**`pending_auto_analysis` Table:**
```sql
CREATE TABLE pending_auto_analysis (
    id SERIAL PRIMARY KEY,
    feed_id INTEGER REFERENCES feeds(id) ON DELETE CASCADE,
    item_ids JSON NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT NOW(),
    processed_at TIMESTAMP,
    analysis_run_id INTEGER REFERENCES analysis_runs(id),
    error_message TEXT
);

CREATE INDEX idx_pending_auto_analysis_status ON pending_auto_analysis(status);
CREATE INDEX idx_pending_auto_analysis_created ON pending_auto_analysis(created_at);
```

**`feeds` Table (extended):**
```sql
ALTER TABLE feeds ADD COLUMN auto_analyze_enabled BOOLEAN DEFAULT FALSE;
```

---

## 📊 Limits & Configuration

### Daily Limits

- **Max Auto-Runs per Feed:** 10/24h
- **Max Items per Run:** 50
- **Job Expiry:** 24 hours

### Change Configuration

**In `app/services/auto_analysis_service.py`:**
```python
class AutoAnalysisService:
    def __init__(self):
        self.max_items_per_run = 50  # Items per run
        self.max_daily_auto_runs_per_feed = 10  # Runs per day
```

**In `app/services/pending_analysis_processor.py`:**
```python
class PendingAnalysisProcessor:
    def __init__(self):
        self.max_daily_auto_runs_per_feed = 10
        self.max_age_hours = 24  # Job expiry
```

### Model Selection

Auto-analyses use **gpt-4.1-nano** by default (cheaper):

```python
params = RunParams(
    limit=len(items_to_analyze),
    rate_per_second=1.0,
    model_tag="gpt-4.1-nano",  # Cost-effective for auto-analyses
    triggered_by="auto"
)
```

---

## 🖥️ HTMX Endpoints

### Dashboard Widget

**Endpoint:** `GET /htmx/auto-analysis-dashboard`

**Features:**
- Number of feeds with auto-analysis
- Jobs Today (Completed)
- Items Analyzed
- Success Rate
- Queue Status (Warning at >5 pending)

**Integration:**
```html
<div hx-get="/htmx/auto-analysis-dashboard"
     hx-trigger="load, every 30s"
     hx-swap="innerHTML">
    Loading...
</div>
```

### Queue Status

**Endpoint:** `GET /htmx/auto-analysis-queue`

**Shows:**
- Pending Jobs (max 10)
- Feed Name
- Items Count
- Age (Minutes/Hours)

### History Timeline

**Endpoint:** `GET /htmx/auto-analysis-history`

**Shows:**
- 20 most recent jobs
- Status (✅ Completed, ❌ Failed)
- Processed Time
- Run-ID Reference

---

## 🧪 Testing

### Run Integration Tests

```bash
source venv/bin/activate
python test_auto_analysis_integration.py
```

**Test Suite:**
1. ✅ Toggle Auto-Analysis
2. ✅ Fetch Triggers Queue
3. ✅ Process Queue
4. ✅ Daily Limit Check
5. ✅ Queue Statistics
6. ✅ Error Handling
7. ✅ Performance Check

**Expected Result:** 6-7/7 tests passed

### Manual Tests

**1. Enable + Fetch:**
```bash
# Enable auto-analysis
curl -X POST "http://localhost:8000/api/feeds/1/toggle-auto-analysis?enabled=true"

# Trigger fetch
curl -X POST "http://localhost:8000/api/feeds/1/fetch"

# Check queue
psql -U news_user -d news_db -c "SELECT * FROM pending_auto_analysis WHERE status='pending';"
```

**2. Process Queue:**
```bash
# Worker should run automatically, or manually:
source venv/bin/activate
python -c "
import asyncio
from app.services.pending_analysis_processor import PendingAnalysisProcessor
processor = PendingAnalysisProcessor()
asyncio.run(processor.process_pending_queue())
"
```

**3. Check Results:**
```bash
psql -U news_user -d news_db -c "
SELECT status, COUNT(*)
FROM pending_auto_analysis
GROUP BY status;
"
```

---

## 📈 Monitoring

### Queue Health Check

```bash
curl "http://localhost:8000/htmx/auto-analysis-queue"
```

**Indicators:**
- **Pending < 5:** ✅ Healthy
- **Pending 5-20:** ⚠️ Warning
- **Pending > 20:** 🔴 Critical - Worker overloaded

### Database Queries

**Active Feeds:**
```sql
SELECT COUNT(*)
FROM feeds
WHERE auto_analyze_enabled = TRUE
  AND status = 'ACTIVE';
```

**Jobs Today:**
```sql
SELECT
    status,
    COUNT(*) as count,
    COUNT(*) * 100.0 / SUM(COUNT(*)) OVER () as percentage
FROM pending_auto_analysis
WHERE processed_at >= CURRENT_DATE
GROUP BY status;
```

**Feed Performance:**
```sql
SELECT
    f.id,
    f.title,
    COUNT(pa.id) as auto_runs_today,
    COUNT(CASE WHEN pa.status = 'completed' THEN 1 END) as successful,
    COUNT(CASE WHEN pa.status = 'failed' THEN 1 END) as failed
FROM feeds f
LEFT JOIN pending_auto_analysis pa
    ON f.id = pa.feed_id
    AND pa.created_at >= CURRENT_DATE
WHERE f.auto_analyze_enabled = TRUE
GROUP BY f.id, f.title
ORDER BY auto_runs_today DESC;
```

---

## 🐛 Troubleshooting

### Problem: Jobs remain in "pending" status

**Cause:** Worker not running or overloaded

**Solution:**
```bash
# Check Worker Status
ps aux | grep analysis_worker

# Restart Worker
./scripts/start-worker.sh

# Check Worker Logs
tail -f logs/worker.log
```

### Problem: Jobs fail ("failed")

**Cause:** OpenAI API Error, rate limiting, invalid items

**Diagnosis:**
```sql
SELECT error_message, COUNT(*)
FROM pending_auto_analysis
WHERE status = 'failed'
  AND processed_at >= CURRENT_DATE
GROUP BY error_message;
```

**Common Errors:**
- `"Auto-analysis disabled"` → Feed was disabled after job creation
- `"No valid items"` → Items were deleted
- `"Daily limit exceeded"` → 10 runs/day limit reached

### Problem: Feed reaches daily limit

**Cause:** Feed fetch_interval too short + many new items

**Solution:**
```bash
# Increase interval
curl -X PUT "http://localhost:8000/api/feeds/1" \
  -H "Content-Type: application/json" \
  -d '{"fetch_interval_minutes": 60}'

# Or: Increase limit in code (see Configuration)
```

---

## 🔐 Best Practices

### 1. Feed Selection

✅ **Enable Auto-Analysis for:**
- High-value feeds (important sources)
- Feeds with 5-50 new items/day
- Stable, high-quality feeds

❌ **Disable for:**
- Test feeds
- Feeds with >100 items/day (Cost)
- Faulty/unstable feeds

### 2. Cost Management

- **Model:** gpt-4.1-nano (cheaper than gpt-4)
- **Batch Size:** Max 50 items/run
- **Daily Limits:** 10 runs/feed/day
- **Monitoring:** Track costs via `analysis_runs` table

### 3. Performance

- **Worker:** Keep at least 1 worker instance running
- **Queue:** At >20 pending jobs: Start more workers
- **Database:** Indexes on `pending_auto_analysis.status`, `.created_at`

### 4. Maintenance

**Weekly:**
```bash
# Cleanup old jobs (>7 days)
python -c "
from app.services.pending_analysis_processor import PendingAnalysisProcessor
processor = PendingAnalysisProcessor()
processor.cleanup_old_jobs(days=7)
"
```

**Monthly:**
- Perform cost analysis
- Review feed performance
- Analyze failed jobs

---

## 📝 API Reference

### POST /api/feeds/{feed_id}/toggle-auto-analysis

**Query Parameters:**
- `enabled` (required): `true` or `false`

**Response:**
```json
{
  "success": true,
  "feed_id": 1,
  "auto_analyze_enabled": true,
  "message": "Auto-analysis enabled for feed 'Feed Name'"
}
```

### GET /api/feeds/{feed_id}/auto-analysis-status

**Response:**
```json
{
  "success": true,
  "feed_id": 1,
  "feed_title": "Feed Name",
  "auto_analyze_enabled": true,
  "stats": {
    "auto_runs_last_7_days": 5,
    "last_auto_run": "2025-09-27T18:30:00Z"
  }
}
```

---

## 📚 Further Documentation

- **NAVIGATOR.md** - System Navigator with Roadmap
- **ENDPOINTS.md** - Complete API Reference
- **INDEX.md** - File Structure
- **ARCHITECTURE.md** - System Architecture Details

---

**End AUTO_ANALYSIS_GUIDE.md**
