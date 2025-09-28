# Auto-Analysis System - User Guide

**Version:** 1.0.0
**Status:** ✅ Production Ready
**Letzte Aktualisierung:** 2025-09-27

---

## 📋 Übersicht

Das Auto-Analysis System ermöglicht die automatische KI-Analyse neuer Artikel direkt nach dem Feed-Fetch. Sobald ein Feed neue Items abruft, werden diese automatisch zur Analyse in eine Queue eingereiht und vom Analysis Worker verarbeitet.

### Features

- ✅ **Feed-Level Toggle**: Aktiviere/Deaktiviere Auto-Analysis pro Feed
- ✅ **Queue-Based Processing**: Asynchrone Verarbeitung ohne Blockierung
- ✅ **Rate Limiting**: Automatische Limits (10 Runs/Tag pro Feed)
- ✅ **Error Handling**: Robuste Fehlerbehandlung mit Retry
- ✅ **Live Dashboard**: HTMX-basierte Echtzeit-Übersicht
- ✅ **Cost Control**: Günstigeres Modell (gpt-4.1-nano) für Auto-Analysen

---

## 🚀 Quick Start

### 1. Auto-Analysis für einen Feed aktivieren

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
1. Öffne `/admin/feeds`
2. Klicke auf den grünen/grauen "🤖 ON/OFF" Button beim gewünschten Feed
3. Feed-Karte refresht automatisch

### 2. Status prüfen

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

### 3. Dashboard anzeigen

**Via Browser:**
```
http://localhost:8000/admin/feeds
```

Im Dashboard siehst du:
- 🟢 Grüner Badge "🤖 Auto" = Auto-Analysis aktiv
- 🔘 Grauer Badge "🤖 Manual" = Auto-Analysis deaktiviert

---

## 🔧 System-Architektur

### Workflow

```
1. Feed Scheduler triggert Fetch (alle N Minuten)
           ↓
2. SyncFeedFetcher holt neue Items
           ↓
3. Prüfung: Feed.auto_analyze_enabled = True?
           ↓ JA
4. PendingAutoAnalysis Job erstellen
           ↓
5. Worker holt Job aus Queue
           ↓
6. PendingAnalysisProcessor → Analysis Run
           ↓
7. Results in item_analysis speichern
```

### Komponenten

| Komponente | Datei | Beschreibung |
|------------|-------|--------------|
| **Auto-Analysis Service** | `app/services/auto_analysis_service.py` | Direct-Trigger + Stats |
| **Pending Processor** | `app/services/pending_analysis_processor.py` | Queue Processing |
| **Feed Fetcher** | `app/services/feed_fetcher_sync.py` | Integration Hook |
| **API Endpoints** | `app/api/feeds.py` | Toggle + Status |
| **HTMX Views** | `app/web/views/auto_analysis_views.py` | Dashboard + Queue |

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

**`feeds` Table (erweitert):**
```sql
ALTER TABLE feeds ADD COLUMN auto_analyze_enabled BOOLEAN DEFAULT FALSE;
```

---

## 📊 Limits & Configuration

### Daily Limits

- **Max Auto-Runs pro Feed:** 10/24h
- **Max Items pro Run:** 50
- **Job Expiry:** 24 Stunden

### Konfiguration ändern

**In `app/services/auto_analysis_service.py`:**
```python
class AutoAnalysisService:
    def __init__(self):
        self.max_items_per_run = 50  # Items pro Run
        self.max_daily_auto_runs_per_feed = 10  # Runs pro Tag
```

**In `app/services/pending_analysis_processor.py`:**
```python
class PendingAnalysisProcessor:
    def __init__(self):
        self.max_daily_auto_runs_per_feed = 10
        self.max_age_hours = 24  # Job Expiry
```

### Model Selection

Auto-Analysen verwenden standardmäßig **gpt-4.1-nano** (günstiger):

```python
params = RunParams(
    limit=len(items_to_analyze),
    rate_per_second=1.0,
    model_tag="gpt-4.1-nano",  # Kostengünstig für Auto-Analysen
    triggered_by="auto"
)
```

---

## 🖥️ HTMX Endpoints

### Dashboard Widget

**Endpoint:** `GET /htmx/auto-analysis-dashboard`

**Features:**
- Anzahl Feeds mit Auto-Analysis
- Jobs Today (Completed)
- Items Analyzed
- Success Rate
- Queue Status (Warning bei >5 pending)

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
- Feed-Name
- Items Count
- Age (Minutes/Hours)

### History Timeline

**Endpoint:** `GET /htmx/auto-analysis-history`

**Shows:**
- 20 neueste Jobs
- Status (✅ Completed, ❌ Failed)
- Processed Time
- Run-ID Referenz

---

## 🧪 Testing

### Integration Tests ausführen

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

**Erwartetes Ergebnis:** 6-7/7 tests passed

### Manuelle Tests

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
# Worker sollte automatisch laufen, oder manuell:
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

**Indikatoren:**
- **Pending < 5:** ✅ Healthy
- **Pending 5-20:** ⚠️ Warning
- **Pending > 20:** 🔴 Critical - Worker überlastet

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

### Problem: Jobs bleiben in "pending" Status

**Ursache:** Worker läuft nicht oder ist überlastet

**Lösung:**
```bash
# Check Worker Status
ps aux | grep analysis_worker

# Restart Worker
./scripts/start-worker.sh

# Check Worker Logs
tail -f logs/worker.log
```

### Problem: Jobs schlagen fehl ("failed")

**Ursache:** OpenAI API Error, Rate Limiting, Invalid Items

**Diagnose:**
```sql
SELECT error_message, COUNT(*)
FROM pending_auto_analysis
WHERE status = 'failed'
  AND processed_at >= CURRENT_DATE
GROUP BY error_message;
```

**Häufige Fehler:**
- `"Auto-analysis disabled"` → Feed wurde deaktiviert nach Job-Erstellung
- `"No valid items"` → Items wurden gelöscht
- `"Daily limit exceeded"` → 10 Runs/Tag Limit erreicht

### Problem: Feed erreicht Daily Limit

**Ursache:** Feed fetch_interval zu kurz + viele neue Items

**Lösung:**
```bash
# Increase interval
curl -X PUT "http://localhost:8000/api/feeds/1" \
  -H "Content-Type: application/json" \
  -d '{"fetch_interval_minutes": 60}'

# Oder: Limit in Code erhöhen (siehe Configuration)
```

---

## 🔐 Best Practices

### 1. Feed-Auswahl

✅ **Aktiviere Auto-Analysis für:**
- High-Value Feeds (wichtige Quellen)
- Feeds mit 5-50 neuen Items/Tag
- Stabile, qualitativ hochwertige Feeds

❌ **Deaktiviere für:**
- Test-Feeds
- Feeds mit >100 Items/Tag (Cost)
- Fehlerhafte/instabile Feeds

### 2. Cost Management

- **Model:** gpt-4.1-nano (günstiger als gpt-4)
- **Batch Size:** Max 50 Items/Run
- **Daily Limits:** 10 Runs/Feed/Tag
- **Monitoring:** Track costs via `analysis_runs` table

### 3. Performance

- **Worker:** Mindestens 1 Worker-Instanz laufen lassen
- **Queue:** Bei >20 pending Jobs: Mehr Worker starten
- **Database:** Indexes auf `pending_auto_analysis.status`, `.created_at`

### 4. Maintenance

**Wöchentlich:**
```bash
# Cleanup alte Jobs (>7 Tage)
python -c "
from app.services.pending_analysis_processor import PendingAnalysisProcessor
processor = PendingAnalysisProcessor()
processor.cleanup_old_jobs(days=7)
"
```

**Monatlich:**
- Cost-Analyse durchführen
- Feed-Performance reviewen
- Failed Jobs analysieren

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

## 📚 Weitere Dokumentation

- **NAVIGATOR.md** - System-Navigator mit Roadmap
- **ENDPOINTS.md** - Vollständige API-Referenz
- **INDEX.md** - Dateistruktur
- **ARCHITECTURE.md** - System-Architektur Details

---

**Ende AUTO_ANALYSIS_GUIDE.md**