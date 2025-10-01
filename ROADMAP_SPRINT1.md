# ROADMAP Sprint 1 - Production Readiness
**Projekt:** News-MCP Scale & Operability
**Zeitraum:** 7 Tage (Tag 1-7)
**Ziel:** Basis für 500 Feeds / 150k Items schaffen
**Datum:** 2025-10-01

---

## 🎯 Sprint-Ziele

**Messbare KPIs nach Sprint 1:**
- ✅ Idempotenz: Keine doppelten Analysen mehr
- ✅ Backpressure: Max 50 Items gleichzeitig in Queue
- ✅ Metriken: Dashboard zeigt `queue_depth`, `items_processed/s`, `feed_lag`
- ✅ DB-Performance: Indizes für häufige Queries optimiert
- ✅ Fehlerrate messbar: Klassifizierte Fehlergründe

---

## 📅 Tag 1-2: Baseline & Idempotenz

### Tag 1 (Mittwoch): Baseline-Messung + Setup

#### 1.1 Baseline-Metriken erfassen (2h)
**Zweck:** Ist-Zustand dokumentieren für Vergleich

**Aufgaben:**
```bash
# Feed-Lag messen
SELECT
  f.id,
  f.title,
  NOW() - f.last_fetched_at as lag,
  COUNT(i.id) as item_count
FROM feeds f
LEFT JOIN items i ON f.id = i.feed_id
  AND i.created_at > NOW() - INTERVAL '24 hours'
WHERE f.status = 'active'
GROUP BY f.id, f.title, f.last_fetched_at
ORDER BY lag DESC
LIMIT 20;

# Analyse-Durchsatz messen (letzte 24h)
SELECT
  COUNT(*) as total_analyzed,
  COUNT(*) / 1440.0 as items_per_minute,
  AVG(EXTRACT(EPOCH FROM (analyzed_at - created_at))) as avg_processing_time_seconds
FROM item_analysis
WHERE analyzed_at > NOW() - INTERVAL '24 hours';

# Fehlerrate ermitteln
SELECT
  status,
  COUNT(*) as count,
  ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) as percentage
FROM analysis_run_items
GROUP BY status;
```

**Ergebnisse dokumentieren in:**
- `docs/BASELINE_METRICS.md`

**Dateien:** Nur neue Doku-Datei

---

#### 1.2 Idempotenz-Schema vorbereiten (3h)
**Zweck:** Duplikate verhindern, Kosten sparen

**Schema-Änderungen:**
```sql
-- Neue Spalte für Dedup-Key
ALTER TABLE items ADD COLUMN dedup_key VARCHAR(64);
CREATE UNIQUE INDEX idx_items_dedup_key ON items(dedup_key)
  WHERE dedup_key IS NOT NULL;

-- Funktion zum Generieren des Keys
CREATE OR REPLACE FUNCTION generate_item_dedup_key(
  p_feed_id BIGINT,
  p_url TEXT,
  p_title TEXT,
  p_published TIMESTAMP
) RETURNS VARCHAR(64) AS $$
BEGIN
  RETURN MD5(
    p_feed_id::TEXT ||
    COALESCE(p_url, '') ||
    COALESCE(p_title, '') ||
    COALESCE(p_published::TEXT, '')
  );
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Backfill für existierende Items
UPDATE items
SET dedup_key = generate_item_dedup_key(feed_id, url, title, published)
WHERE dedup_key IS NULL;
```

**Alembic Migration erstellen:**
```bash
alembic revision -m "add_item_deduplication"
# In migration file: SQL von oben einfügen
alembic upgrade head
```

**Dateien:**
- `alembic/versions/XXXX_add_item_deduplication.py` (neu)
- `app/models/__init__.py` (Item model erweitern)

---

### Tag 2 (Donnerstag): Idempotenz implementieren

#### 2.1 Feed Fetcher anpassen (3h)
**Zweck:** Dedup-Key beim Speichern setzen

**Änderungen in `app/services/feed_fetcher_sync.py`:**
```python
def _save_item(self, feed_id: int, entry: dict) -> Optional[Item]:
    """Save item with deduplication"""

    # Generate dedup key
    dedup_key = hashlib.md5(
        f"{feed_id}{entry.get('link', '')}{entry.get('title', '')}{entry.get('published', '')}".encode()
    ).hexdigest()

    # Check if item already exists
    existing = self.session.exec(
        select(Item).where(Item.dedup_key == dedup_key)
    ).first()

    if existing:
        logger.debug(f"Item already exists: {dedup_key}")
        return None  # Skip duplicate

    # Create new item
    item = Item(
        feed_id=feed_id,
        title=entry.get('title'),
        url=entry.get('link'),
        dedup_key=dedup_key,
        # ... rest of fields
    )

    self.session.add(item)
    return item
```

**Dateien:**
- `app/services/feed_fetcher_sync.py` (ändern)
- `app/models/__init__.py` (Item model erweitern)

---

#### 2.2 Analysis Idempotenz (2h)
**Zweck:** Item nicht mehrfach analysieren

**Änderungen in `app/services/pending_analysis_processor.py`:**
```python
async def _should_analyze_item(self, item_id: int) -> bool:
    """Check if item needs analysis"""

    # Check if already analyzed
    existing = await self.session.exec(
        select(ItemAnalysis).where(ItemAnalysis.item_id == item_id)
    ).first()

    if existing:
        logger.debug(f"Item {item_id} already analyzed, skipping")
        return False

    return True
```

**Dateien:**
- `app/services/pending_analysis_processor.py` (ändern)

---

#### 2.3 Tests für Idempotenz (2h)
**Test-Cases:**
```python
# tests/test_idempotency.py
def test_duplicate_item_not_saved():
    """Test that duplicate items are skipped"""
    # Given: Item mit gleicher URL/Title/Published
    # When: Item zweimal fetchen
    # Then: Nur 1 Item in DB

def test_item_not_reanalyzed():
    """Test that analyzed items are skipped"""
    # Given: Item bereits analysiert
    # When: Auto-Analysis triggered
    # Then: Item nicht in Queue
```

**Dateien:**
- `tests/test_idempotency.py` (neu)

---

## 📅 Tag 3-4: Backpressure & Rate-Limiting

### Tag 3 (Freitag): Pull-Window implementieren

#### 3.1 Queue-Limiter Service (4h)
**Zweck:** Max 50 Items gleichzeitig in Verarbeitung

**Neuer Service `app/services/queue_limiter.py`:**
```python
from typing import List
from app.models import PendingAutoAnalysis

class QueueLimiter:
    """Manages queue backpressure"""

    def __init__(self, max_concurrent: int = 50):
        self.max_concurrent = max_concurrent

    async def get_next_batch(
        self,
        session: AsyncSession,
        batch_size: int = 10
    ) -> List[PendingAutoAnalysis]:
        """Get next batch respecting concurrency limits"""

        # Count currently processing items
        processing_count = await self._count_processing(session)

        if processing_count >= self.max_concurrent:
            logger.info(f"Queue at capacity: {processing_count}/{self.max_concurrent}")
            return []

        # Calculate available slots
        available_slots = self.max_concurrent - processing_count
        actual_batch_size = min(batch_size, available_slots)

        # Fetch next items
        statement = (
            select(PendingAutoAnalysis)
            .where(PendingAutoAnalysis.status == "pending")
            .order_by(PendingAutoAnalysis.priority.desc(), PendingAutoAnalysis.created_at)
            .limit(actual_batch_size)
        )

        result = await session.execute(statement)
        return result.scalars().all()

    async def _count_processing(self, session: AsyncSession) -> int:
        """Count items currently being processed"""
        statement = select(func.count()).select_from(PendingAutoAnalysis).where(
            PendingAutoAnalysis.status == "processing"
        )
        result = await session.execute(statement)
        return result.scalar_one()
```

**Dateien:**
- `app/services/queue_limiter.py` (neu)
- `app/services/pending_analysis_processor.py` (integration)

---

#### 3.2 Adaptive Rate-Limiter (3h)
**Zweck:** API-Limits respektieren, Circuit-Breaker

**Erweiterung `app/services/llm_client.py`:**
```python
from datetime import datetime, timedelta
from collections import deque

class AdaptiveRateLimiter:
    """Adaptive rate limiting with circuit breaker"""

    def __init__(self, max_per_second: float = 3.0):
        self.max_per_second = max_per_second
        self.requests = deque()
        self.error_count = 0
        self.circuit_open_until = None

    async def wait_if_needed(self):
        """Wait if rate limit would be exceeded"""

        # Check circuit breaker
        if self.circuit_open_until:
            if datetime.utcnow() < self.circuit_open_until:
                wait_seconds = (self.circuit_open_until - datetime.utcnow()).total_seconds()
                logger.warning(f"Circuit breaker open, waiting {wait_seconds}s")
                await asyncio.sleep(wait_seconds)
            else:
                logger.info("Circuit breaker closed, resuming")
                self.circuit_open_until = None
                self.error_count = 0

        # Rate limiting
        now = datetime.utcnow()
        cutoff = now - timedelta(seconds=1)

        # Remove old requests
        while self.requests and self.requests[0] < cutoff:
            self.requests.popleft()

        # Check if at limit
        if len(self.requests) >= self.max_per_second:
            wait_time = 1.0 - (now - self.requests[0]).total_seconds()
            if wait_time > 0:
                await asyncio.sleep(wait_time)

        self.requests.append(now)

    def record_error(self):
        """Record API error for circuit breaker"""
        self.error_count += 1

        if self.error_count >= 5:
            # Open circuit for 60 seconds
            self.circuit_open_until = datetime.utcnow() + timedelta(seconds=60)
            logger.error(f"Circuit breaker opened due to {self.error_count} errors")

    def record_success(self):
        """Record successful request"""
        if self.error_count > 0:
            self.error_count = max(0, self.error_count - 1)
```

**Dateien:**
- `app/services/llm_client.py` (ändern)

---

### Tag 4 (Samstag): Backpressure Integration & Tests

#### 4.1 Processor Integration (3h)
**Zweck:** Queue-Limiter in Processor einbauen

**Änderungen in `app/services/pending_analysis_processor.py`:**
```python
from app.services.queue_limiter import QueueLimiter

class PendingAnalysisProcessor:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.queue_limiter = QueueLimiter(max_concurrent=50)  # NEW
        self.rate_limiter = AdaptiveRateLimiter(max_per_second=3.0)

    async def process_queue(self):
        """Process queue with backpressure"""
        while True:
            # Use queue limiter instead of fixed batch
            batch = await self.queue_limiter.get_next_batch(
                self.session,
                batch_size=10
            )

            if not batch:
                await asyncio.sleep(30)
                continue

            for pending in batch:
                await self.rate_limiter.wait_if_needed()
                await self._process_item(pending)
```

**Dateien:**
- `app/services/pending_analysis_processor.py` (ändern)

---

#### 4.2 Backpressure Tests (2h)
**Test-Cases:**
```python
# tests/test_backpressure.py
async def test_queue_limiter_respects_max_concurrent():
    """Test that queue doesn't exceed max concurrent"""
    # Given: 100 pending items
    # When: Processing with max_concurrent=50
    # Then: Max 50 items in "processing" status at any time

async def test_circuit_breaker_opens_on_errors():
    """Test that circuit breaker opens after errors"""
    # Given: 5 consecutive API errors
    # When: Next request attempted
    # Then: Wait 60 seconds before retry
```

**Dateien:**
- `tests/test_backpressure.py` (neu)

---

#### 4.3 Load-Test mit 100 Items (2h)
**Zweck:** Backpressure unter Last verifizieren

```bash
# Load test script
python scripts/load_test_queue.py --items 100 --concurrent 50
```

**Metriken prüfen:**
- Max concurrent = 50? ✅
- Keine Queue-Staus? ✅
- Rate-Limiting aktiv? ✅

**Dateien:**
- `scripts/load_test_queue.py` (neu)

---

## 📅 Tag 5-6: Metriken & Monitoring

### Tag 5 (Sonntag): Prometheus Metrics

#### 5.1 Metrics Service (4h)
**Zweck:** Exportiere Metriken für Prometheus

**Neuer Service `app/services/metrics_service.py`:**
```python
from prometheus_client import Counter, Gauge, Histogram
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

# Define metrics
queue_depth_gauge = Gauge(
    'news_mcp_queue_depth',
    'Number of items in pending analysis queue'
)

items_processed_counter = Counter(
    'news_mcp_items_processed_total',
    'Total items processed',
    ['status']  # completed, failed
)

processing_duration_histogram = Histogram(
    'news_mcp_processing_duration_seconds',
    'Time to process one item'
)

feed_lag_gauge = Gauge(
    'news_mcp_feed_lag_seconds',
    'Time since last feed fetch',
    ['feed_id', 'feed_title']
)

class MetricsService:
    """Collect and expose metrics"""

    async def update_queue_depth(self, session: AsyncSession):
        """Update queue depth metric"""
        statement = select(func.count()).select_from(PendingAutoAnalysis).where(
            PendingAutoAnalysis.status.in_(["pending", "processing"])
        )
        result = await session.execute(statement)
        count = result.scalar_one()
        queue_depth_gauge.set(count)

    async def update_feed_lag(self, session: AsyncSession):
        """Update feed lag metrics"""
        statement = select(Feed).where(Feed.status == "active")
        result = await session.execute(statement)
        feeds = result.scalars().all()

        for feed in feeds:
            if feed.last_fetched_at:
                lag_seconds = (datetime.utcnow() - feed.last_fetched_at).total_seconds()
                feed_lag_gauge.labels(
                    feed_id=feed.id,
                    feed_title=feed.title
                ).set(lag_seconds)

    def record_item_processed(self, status: str, duration: float):
        """Record processed item"""
        items_processed_counter.labels(status=status).inc()
        processing_duration_histogram.observe(duration)
```

**API Endpoint `app/api/metrics.py`:**
```python
from fastapi import Response
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

@router.get("/metrics")
async def metrics_endpoint():
    """Prometheus metrics endpoint"""
    # Update metrics
    await metrics_service.update_queue_depth(session)
    await metrics_service.update_feed_lag(session)

    # Return Prometheus format
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )
```

**Dateien:**
- `app/services/metrics_service.py` (neu)
- `app/api/metrics.py` (erweitern)
- `requirements.txt` (add: `prometheus-client==0.19.0`)

---

#### 5.2 Metrics Integration (3h)
**Zweck:** Metriken in Worker integrieren

**Änderungen in `app/services/pending_analysis_processor.py`:**
```python
from app.services.metrics_service import metrics_service

async def _process_item(self, pending: PendingAutoAnalysis):
    """Process item with metrics"""
    start_time = time.time()

    try:
        # ... processing logic ...

        duration = time.time() - start_time
        metrics_service.record_item_processed("completed", duration)

    except Exception as e:
        duration = time.time() - start_time
        metrics_service.record_item_processed("failed", duration)
        raise
```

**Dateien:**
- `app/services/pending_analysis_processor.py` (ändern)
- `app/worker/analysis_worker.py` (ändern)

---

### Tag 6 (Montag): Grafana Dashboard

#### 6.1 Grafana Setup (2h)
**Zweck:** Visualisierung der Metriken

**Docker Compose erweitern:**
```yaml
# docker-compose.metrics.yml
version: '3.8'

services:
  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    volumes:
      - grafana_data:/var/lib/grafana
      - ./grafana/dashboards:/etc/grafana/provisioning/dashboards
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin

volumes:
  prometheus_data:
  grafana_data:
```

**Prometheus Config `prometheus.yml`:**
```yaml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'news-mcp'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/api/metrics'
```

**Dateien:**
- `docker-compose.metrics.yml` (neu)
- `prometheus.yml` (neu)

---

#### 6.2 Dashboard erstellen (3h)
**Zweck:** Operator-Dashboard für Monitoring

**Dashboard-Panels:**
1. **Queue Depth** (Time Series)
   - Metric: `news_mcp_queue_depth`
   - Threshold: Warning bei >100

2. **Items Processed Rate** (Stat)
   - Metric: `rate(news_mcp_items_processed_total[5m])`
   - Target: ≥20/min

3. **Feed Lag p95** (Gauge)
   - Metric: `quantile(0.95, news_mcp_feed_lag_seconds)`
   - Target: ≤300s (5 min)

4. **Processing Duration p95** (Time Series)
   - Metric: `histogram_quantile(0.95, news_mcp_processing_duration_seconds)`

5. **Error Rate** (Stat)
   - Metric: `rate(news_mcp_items_processed_total{status="failed"}[5m])`
   - Target: <1%

**Dateien:**
- `grafana/dashboards/news-mcp-overview.json` (neu)

---

#### 6.3 Alerts konfigurieren (2h)
**Zweck:** Benachrichtigung bei Problemen

**Alerting Rules `prometheus/alerts.yml`:**
```yaml
groups:
  - name: news_mcp_alerts
    interval: 30s
    rules:
      - alert: QueueDepthHigh
        expr: news_mcp_queue_depth > 200
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Queue depth above 200 for 5 minutes"

      - alert: FeedLagHigh
        expr: quantile(0.95, news_mcp_feed_lag_seconds) > 600
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "95% of feeds have lag >10 minutes"

      - alert: HighErrorRate
        expr: rate(news_mcp_items_processed_total{status="failed"}[5m]) > 0.01
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "Error rate above 1%"
```

**Dateien:**
- `prometheus/alerts.yml` (neu)
- `prometheus.yml` (erweitern: rule_files)

---

## 📅 Tag 7: DB-Optimierung & Dokumentation

### Tag 7 (Dienstag): Finalisierung

#### 7.1 DB-Indizes erstellen (2h)
**Zweck:** Query-Performance optimieren

**SQL-Skript `scripts/optimize_indexes.sql`:**
```sql
-- Index für häufige Item-Abfragen
CREATE INDEX IF NOT EXISTS idx_items_feed_published
ON items(feed_id, published DESC);

-- Index für URL-Deduplication
CREATE INDEX IF NOT EXISTS idx_items_normalized_url
ON items(LOWER(url));

-- Index für Queue-Queries
CREATE INDEX IF NOT EXISTS idx_pending_status_priority
ON pending_auto_analysis(status, priority DESC, created_at);

-- Index für Analysis-Lookup
CREATE INDEX IF NOT EXISTS idx_item_analysis_item
ON item_analysis(item_id);

-- Partial Index für aktive Feeds
CREATE INDEX IF NOT EXISTS idx_feeds_active_lag
ON feeds(last_fetched_at DESC)
WHERE status = 'active';

-- Analyze tables
ANALYZE items;
ANALYZE pending_auto_analysis;
ANALYZE feeds;
ANALYZE item_analysis;
```

**Dateien:**
- `scripts/optimize_indexes.sql` (neu)
- `alembic/versions/XXXX_add_performance_indexes.py` (neu)

---

#### 7.2 Query-Performance testen (2h)
**Zweck:** Verifizieren dass p95 <150ms

**Test-Queries:**
```sql
-- Test 1: Item-Liste (häufigste Query)
EXPLAIN ANALYZE
SELECT i.id, i.title, i.published, f.title as feed_title
FROM items i
JOIN feeds f ON i.feed_id = f.id
WHERE i.published > NOW() - INTERVAL '7 days'
ORDER BY i.published DESC
LIMIT 50;
-- Target: <50ms

-- Test 2: Queue-Batch (Worker Query)
EXPLAIN ANALYZE
SELECT * FROM pending_auto_analysis
WHERE status = 'pending'
ORDER BY priority DESC, created_at
LIMIT 10;
-- Target: <10ms

-- Test 3: Feed-Health (Dashboard Query)
EXPLAIN ANALYZE
SELECT
  f.id,
  f.title,
  f.last_fetched_at,
  COUNT(i.id) as recent_items
FROM feeds f
LEFT JOIN items i ON f.id = i.feed_id
  AND i.created_at > NOW() - INTERVAL '24 hours'
WHERE f.status = 'active'
GROUP BY f.id, f.title, f.last_fetched_at;
-- Target: <100ms
```

**Performance dokumentieren in `docs/QUERY_PERFORMANCE.md`**

**Dateien:**
- `scripts/benchmark_queries.sql` (neu)
- `docs/QUERY_PERFORMANCE.md` (neu)

---

#### 7.3 Dokumentation finalisieren (3h)
**Zweck:** Sprint-Ergebnisse dokumentieren

**Dokumente erstellen/updaten:**

1. **`docs/SPRINT1_RESULTS.md`** (neu)
   - Erreichte KPIs
   - Baseline vs. Nach Sprint
   - Offene Punkte

2. **`NAVIGATOR.md`** (update)
   - Neue Services dokumentieren
   - Worksets aktualisieren
   - Roadmap-Status updaten

3. **`ENDPOINTS.md`** (update)
   - Neue Metrics-Endpoints
   - Geänderte API-Responses

4. **`README.md`** (update)
   - Prometheus/Grafana Setup
   - Neue Dependencies

**Dateien:**
- `docs/SPRINT1_RESULTS.md` (neu)
- `NAVIGATOR.md` (ändern)
- `ENDPOINTS.md` (ändern)
- `README.md` (ändern)

---

#### 7.4 Sprint Review vorbereiten (2h)
**Zweck:** Demo & Abnahme vorbereiten

**Sprint Review Checkliste:**

**Demo-Skript erstellen:**
```markdown
# Sprint 1 Demo

## 1. Idempotenz Demo
- Item zweimal fetchen → Nur 1x in DB ✅
- Item reanalyze → Skipped ✅

## 2. Backpressure Demo
- 100 Items in Queue legen
- Max 50 concurrent zeigen (Grafana)
- Circuit Breaker triggern (API-Fehler simulieren)

## 3. Metriken Demo
- Grafana Dashboard zeigen
- Live Queue Depth
- Items/min Rate
- Feed Lag p95

## 4. Performance Demo
- Query-Benchmarks zeigen
- Vor/Nach Indizes Vergleich

## 5. KPIs Review
- ✅ Idempotenz funktioniert
- ✅ Max 50 concurrent
- ✅ Metriken exportiert
- ✅ DB p95 <150ms
```

**Dateien:**
- `docs/SPRINT1_DEMO.md` (neu)

---

## 📊 Sprint 1 KPIs - Definition of Done

### Functional Requirements
- [x] **Idempotenz:** Items nicht doppelt gespeichert (dedup_key)
- [x] **Idempotenz:** Items nicht doppelt analysiert (check existing)
- [x] **Backpressure:** Max 50 Items concurrent in Verarbeitung
- [x] **Rate-Limiting:** Adaptive 3 req/sec mit Circuit-Breaker
- [x] **Metriken:** Prometheus-Endpoint `/api/metrics` aktiv
- [x] **Dashboard:** Grafana zeigt 5 Key-Metrics

### Performance Requirements
- [x] **DB Query p95:** <150ms für Hot-Reads
- [x] **Queue-Query:** <10ms für Batch-Selection
- [x] **Feed-Lag:** Messbar via Metrics
- [x] **Throughput:** ≥20 Items/min (bereits erreicht)

### Testing Requirements
- [x] **Unit Tests:** Idempotenz (2 Tests)
- [x] **Unit Tests:** Backpressure (2 Tests)
- [x] **Load Test:** 100 Items ohne Queue-Stau
- [x] **Performance Tests:** Query-Benchmarks dokumentiert

### Documentation Requirements
- [x] **Baseline:** Ist-Zustand dokumentiert
- [x] **Results:** Sprint-Ergebnisse dokumentiert
- [x] **Navigator:** Neue Services eingetragen
- [x] **Endpoints:** API-Änderungen dokumentiert
- [x] **Demo:** Sprint Review vorbereitet

---

## 🔧 Geänderte/Neue Dateien (Übersicht)

### Neue Dateien (17)
```
alembic/versions/XXXX_add_item_deduplication.py
alembic/versions/XXXX_add_performance_indexes.py
app/services/queue_limiter.py
app/services/metrics_service.py
tests/test_idempotency.py
tests/test_backpressure.py
scripts/load_test_queue.py
scripts/optimize_indexes.sql
scripts/benchmark_queries.sql
docker-compose.metrics.yml
prometheus.yml
prometheus/alerts.yml
grafana/dashboards/news-mcp-overview.json
docs/BASELINE_METRICS.md
docs/QUERY_PERFORMANCE.md
docs/SPRINT1_RESULTS.md
docs/SPRINT1_DEMO.md
```

### Geänderte Dateien (8)
```
app/models/__init__.py (Item model + dedup_key)
app/services/feed_fetcher_sync.py (dedup logic)
app/services/pending_analysis_processor.py (backpressure + metrics)
app/services/llm_client.py (adaptive rate-limiter)
app/api/metrics.py (prometheus endpoint)
NAVIGATOR.md (status update)
ENDPOINTS.md (new endpoints)
README.md (setup instructions)
```

**Total:** 25 Dateien (17 neu, 8 geändert)

---

## 🚀 Sprint 1 Start Checklist

**Vor Tag 1:**
- [ ] Git Branch erstellen: `git checkout -b sprint1-production-ready`
- [ ] Dependencies installieren: `pip install prometheus-client==0.19.0`
- [ ] Backup erstellen: DB + Code
- [ ] Team-Kickoff: Roadmap durchgehen

**Nach Tag 7:**
- [ ] Sprint Review durchführen
- [ ] KPIs validieren
- [ ] Sprint 2 Planung
- [ ] Git Merge: `sprint1-production-ready` → `main`

---

## 📞 Support & Fragen

**Bei Blockern:**
- NAVIGATOR.md konsultieren
- ENDPOINTS.md für API-Details
- CLAUDE.md für Working Rules

**Bei Performance-Problemen:**
- Query Performance Guide
- Baseline Metrics vergleichen

---

**Erstellt:** 2025-10-01
**Sprint-Dauer:** 7 Tage
**Team:** Solo-Dev (anpassbar für Team)
**Status:** Ready to Start 🚀
