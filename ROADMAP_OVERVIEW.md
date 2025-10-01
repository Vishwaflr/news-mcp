# ROADMAP Overview - News-MCP Scale & Operability
**Projekt-Ziel:** Production-Ready für 500 Feeds / 150k Items
**Zeitraum:** 8-12 Wochen (4-6 Sprints à 2 Wochen)
**Start:** 2025-10-01

---

## 🎯 Gesamt-Ziele (Definition of Success)

**Nach 8-12 Wochen erreicht:**

| KPI | Ist (Oktober 2025) | Ziel | Faktor |
|-----|-------------------|------|--------|
| **Feeds** | 37 | 500 | 13.5x |
| **Items** | 10.903 | 150.000 | 13.8x |
| **Analyse-Durchsatz** | ~30 Items/min | ≥20 Items/min | ✅ OK |
| **Feed-Lag p95** | Nicht gemessen | ≤5 min | Neu |
| **DB Query p95** | ~85ms | <150ms | ✅ OK |
| **Fehlerrate** | Unbekannt | <1% | Neu |
| **Kosten/Item** | Unbekannt | Definiert ±10% | Neu |
| **Queue-Stabilität** | Keine Staus | <30 min max | Neu |
| **Poison-Queue** | Keine Tracking | <0.5% | Neu |

---

## 📅 Sprint-Übersicht (4-6 Sprints)

### ✅ Sprint 0: Baseline & Wiki (ABGESCHLOSSEN)
**Dauer:** 2 Tage
**Status:** ✅ Fertig (2025-09-30 bis 2025-10-01)

**Ergebnisse:**
- ✅ Wiki vollständig (19 Seiten, 156 KB)
- ✅ GitHub Wiki hochgeladen
- ✅ Projekt-Backup erstellt
- ✅ Roadmap definiert

---

### 🔵 Sprint 1: Idempotenz, Backpressure, Metriken (AKTUELL)
**Dauer:** 7 Tage (Tag 1-7)
**Status:** 🔵 In Planung
**Details:** → `ROADMAP_SPRINT1.md`

**Ziele:**
- ✅ Idempotenz: Keine doppelten Analysen
- ✅ Backpressure: Max 50 Items concurrent
- ✅ Metriken: Prometheus + Grafana Dashboard
- ✅ DB-Indizes: Query p95 <150ms

**Team-Aufteilung (wenn 3 Devs):**
- **Dev A (Backend):** Idempotenz + Backpressure
- **Dev B (Data/DB):** Indizes + Queries
- **Dev C (Frontend):** Grafana Dashboard

---

### 🟡 Sprint 2: Retry-Logic, Poison-Queue, DB-Partitionierung
**Dauer:** 2 Wochen (Tag 8-21)
**Status:** 🟡 Geplant

**Ziele:**
- Retry-Politik (Exponential Backoff: 1min, 5min, 15min)
- Poison-Queue für dauerhaft fehlgeschlagene Items
- DB-Partitionierung (`fetch_log`, `items`)
- Operator-Cockpit v2 (Filter, Bulk-Ops)

**Neue Tables:**
```sql
CREATE TABLE analysis_failures (
  id BIGSERIAL PRIMARY KEY,
  item_id BIGINT REFERENCES items(id),
  attempt_count INT DEFAULT 0,
  status TEXT CHECK (status IN ('retry', 'poison')),
  error_type TEXT,
  error_message TEXT,
  last_attempt_at TIMESTAMP,
  next_retry_at TIMESTAMP
);
```

**Key Files:**
- `app/services/retry_manager.py` (neu)
- `app/services/poison_queue_handler.py` (neu)
- `alembic/versions/XXXX_add_partitioning.py` (neu)

**Team-Aufteilung:**
- **Dev A:** Retry-Manager + Poison-Queue
- **Dev B:** DB-Partitionierung + Archivierung
- **Dev C:** Operator-Cockpit v2 (Listen, Filter)

---

### 🟡 Sprint 3: Batching, Quota-Guard, Materialized Views
**Dauer:** 2 Wochen (Tag 22-35)
**Status:** 🟡 Geplant

**Ziele:**
- Analysis-Batching (N Artikel pro API-Call wo möglich)
- Quota-Guard (Token-Tracking, Budget-Alerts)
- Materialized Views (Dashboard-Performance)
- Drilldown-Flows (Item-Trace: fetch→analyze→persist)

**Batching Strategy:**
```python
# Statt 1 Item pro API-Call:
result = openai.chat.completions.create(
    model="gpt-3.5-turbo",
    messages=[{"role": "user", "content": analyze_single_item(item)}]
)

# Batch 5-10 Items:
batch_prompt = "\n\n".join([
    f"Article {i+1}:\n{item.title}\n{item.content[:500]}"
    for i, item in enumerate(batch_items)
])
result = openai.chat.completions.create(
    model="gpt-3.5-turbo",
    messages=[{"role": "user", "content": f"Analyze these {len(batch_items)} articles:\n\n{batch_prompt}"}]
)
```

**Materialized Views:**
```sql
CREATE MATERIALIZED VIEW mv_dashboard_stats AS
SELECT
  COUNT(DISTINCT f.id) as total_feeds,
  COUNT(DISTINCT i.id) as total_items,
  COUNT(DISTINCT ia.item_id) as analyzed_items,
  AVG(ia.sentiment_score) as avg_sentiment
FROM feeds f
LEFT JOIN items i ON f.id = i.feed_id
LEFT JOIN item_analysis ia ON i.id = ia.item_id;

-- Refresh every 5 minutes
CREATE INDEX ON mv_dashboard_stats (total_feeds);
```

**Key Files:**
- `app/services/batch_analyzer.py` (neu)
- `app/services/quota_guard.py` (neu)
- `alembic/versions/XXXX_materialized_views.py` (neu)

**Team-Aufteilung:**
- **Dev A:** Batch-Analyzer + Quota-Guard
- **Dev B:** Materialized Views + Refresh-Jobs
- **Dev C:** Drilldown-Flows UI

---

### 🟡 Sprint 4: Performance-Pass, Alerts, Archivierung
**Dauer:** 2 Wochen (Tag 36-49)
**Status:** 🟡 Geplant

**Ziele:**
- Query-Optimierung (p95 <150ms validiert)
- UX-Performance (perceived <400ms)
- Alert-System (Schwellen: Lag, Fehler-Spike, Quota)
- Archivierung (Items >6 Monate → archive-Tabelle)

**Alert-Rules:**
```yaml
# prometheus/alerts.yml
- alert: FeedLagCritical
  expr: quantile(0.95, news_mcp_feed_lag_seconds) > 300
  for: 10m
  labels:
    severity: critical
  annotations:
    summary: "95% of feeds lagging >5 minutes"

- alert: ErrorRateHigh
  expr: rate(news_mcp_items_processed_total{status="failed"}[5m]) > 0.01
  for: 5m
  labels:
    severity: critical

- alert: QuotaNearLimit
  expr: news_mcp_openai_tokens_used_monthly > 900000
  labels:
    severity: warning
  annotations:
    summary: "OpenAI quota at 90%"
```

**Archivierung:**
```sql
-- Move old items to archive
INSERT INTO items_archive
SELECT * FROM items
WHERE published < NOW() - INTERVAL '6 months';

DELETE FROM items
WHERE published < NOW() - INTERVAL '6 months';
```

**Key Files:**
- `app/services/archival_service.py` (neu)
- `scripts/archive_old_items.py` (neu)
- `prometheus/alerts.yml` (erweitern)

**Team-Aufteilung:**
- **Dev A:** Alert-System + Runbooks
- **Dev B:** Archivierung + Cleanup-Jobs
- **Dev C:** UX-Performance (Progressive Loading)

---

### 🟢 Sprint 5-6: Puffer, Lasttests, Tuning, Doku (Optional)
**Dauer:** 2-4 Wochen (Tag 50-77)
**Status:** 🟢 Puffer

**Ziele:**
- Lasttests (48h Dauerlast, synthetische Feeds)
- Edge-Cases beheben
- Runbooks erstellen
- Operator-Training
- Final-Doku

**Lasttest-Szenario:**
```bash
# Simulate 500 feeds
python scripts/load_test_feeds.py \
  --feeds 500 \
  --items-per-day 300 \
  --duration 48h

# Monitor KPIs:
# - Feed-Lag p95 ≤ 5 min ✅
# - Durchsatz ≥ 20 Items/min ✅
# - Fehlerrate <1% ✅
# - Queue-Staus <30 min ✅
```

**Runbooks:**
- `docs/runbooks/QUEUE_STUCK.md` - Queue blockiert
- `docs/runbooks/API_DOWN.md` - OpenAI API down
- `docs/runbooks/DB_HOT.md` - Datenbank überlastet
- `docs/runbooks/EMERGENCY_STOP.md` - Notfall-Stopp

**Team-Aufteilung:**
- **Dev A+B:** Lasttests + Tuning
- **Dev C:** Runbooks + Doku
- **Alle:** Edge-Cases beheben

---

## 📊 Sprint-Abhängigkeiten

```
Sprint 1 (Idempotenz, Backpressure, Metriken)
  ↓
Sprint 2 (Retry, Poison-Queue, Partitionierung)
  ↓
Sprint 3 (Batching, Quota-Guard, Mat. Views)
  ↓
Sprint 4 (Performance, Alerts, Archivierung)
  ↓
Sprint 5-6 (Puffer, Lasttests, Doku)
```

**Keine Parallelisierung möglich:**
- Sprint 2 benötigt Metriken aus Sprint 1
- Sprint 3 benötigt Retry-Logic aus Sprint 2
- Sprint 4 benötigt Performance-Baseline aus Sprint 3

---

## 🔧 Worksets pro Sprint

### Sprint 1 Workset (MAX 10 Dateien)
```
1. app/models/__init__.py (dedup_key)
2. app/services/feed_fetcher_sync.py (idempotenz)
3. app/services/pending_analysis_processor.py (backpressure)
4. app/services/queue_limiter.py (NEU)
5. app/services/metrics_service.py (NEU)
6. app/services/llm_client.py (rate-limiter)
7. app/api/metrics.py (prometheus endpoint)
8. alembic/versions/XXXX_dedup.py (NEU)
9. alembic/versions/XXXX_indexes.py (NEU)
10. tests/test_idempotency.py (NEU)
```

### Sprint 2 Workset (MAX 10 Dateien)
```
1. app/services/retry_manager.py (NEU)
2. app/services/poison_queue_handler.py (NEU)
3. app/models/__init__.py (analysis_failures table)
4. app/services/pending_analysis_processor.py (retry integration)
5. app/web/views/operator_views.py (NEU - Cockpit v2)
6. alembic/versions/XXXX_partitioning.py (NEU)
7. alembic/versions/XXXX_analysis_failures.py (NEU)
8. templates/operator_cockpit_v2.html (NEU)
9. tests/test_retry_logic.py (NEU)
10. tests/test_poison_queue.py (NEU)
```

---

## 📈 KPI-Tracking pro Sprint

| KPI | Baseline | Sprint 1 | Sprint 2 | Sprint 3 | Sprint 4 | Ziel |
|-----|----------|----------|----------|----------|----------|------|
| **Feed-Lag p95** | ? | Messbar | <10 min | <7 min | <5 min | ≤5 min |
| **Durchsatz** | 30/min | 30/min | 25/min | 30/min | 20/min | ≥20/min |
| **Fehlerrate** | ? | Messbar | <2% | <1.5% | <1% | <1% |
| **Queue-Staus** | ? | Messbar | <60 min | <45 min | <30 min | <30 min |
| **DB Query p95** | 85ms | <150ms | <120ms | <100ms | <80ms | <150ms |
| **Poison-Queue** | 0% | 0% | <1% | <0.7% | <0.5% | <0.5% |

---

## 🚀 Getting Started

**Heute (Tag 1):**
1. ✅ Read `ROADMAP_SPRINT1.md` im Detail
2. ✅ Git Branch: `git checkout -b sprint1-production-ready`
3. ✅ Baseline messen: Run SQL queries in Sprint 1 Tag 1
4. ✅ Dependencies: `pip install prometheus-client==0.19.0`

**Diese Woche (Tag 1-7):**
- Sprint 1 komplett durchziehen
- Täglich Fortschritt in `NAVIGATOR.md` aktualisieren
- Am Ende: Sprint Review + KPI-Validierung

**Nächste Wochen:**
- Sprint 2 starten (nur wenn Sprint 1 Done)
- Keine parallelen Sprints!
- Worksets strikt einhalten

---

## 📞 Support & Ressourcen

**Dokumentation:**
- `ROADMAP_SPRINT1.md` - Detaillierter Sprint 1 Plan
- `NAVIGATOR.md` - System-Übersicht & Hotspots
- `ENDPOINTS.md` - API-Referenz (150+ Endpoints)
- `CLAUDE.md` - Working Rules

**Bei Fragen:**
- Check NAVIGATOR.md für Worksets
- Check ENDPOINTS.md für API-Details
- Check ROADMAP_SPRINT1.md für Tasks

---

## 🎯 Definition of Success (Gesamt-Projekt)

**Nach 8-12 Wochen erreicht:**
1. ✅ **Throughput:** 500 Feeds, 150k Items, 20 Items/min
2. ✅ **Reliability:** Feed-Lag p95 ≤5min, Fehlerrate <1%
3. ✅ **Operability:** Grafana Dashboard, Alerts, Runbooks
4. ✅ **Stability:** 48h Dauerlast ohne Staus oder Ausfälle
5. ✅ **Performance:** DB Query p95 <150ms, UX <400ms
6. ✅ **Cost Control:** Kosten/Item definiert, ±10% Varianz

**Abnahme-Kriterien:**
- [ ] KPIs über 48h Dauerlast erreicht
- [ ] Reproduzierbare Deploys (Docker Compose)
- [ ] Ein-Klick Pipeline-Reset
- [ ] Runbooks getestet (Queue-Stuck, API-Down, DB-Hot)
- [ ] Operator-Cockpit deckt Top-3 Tätigkeiten ab

---

**Erstellt:** 2025-10-01
**Nächster Review:** Nach Sprint 1 (Tag 8)
**Status:** Sprint 1 Ready to Start 🚀
