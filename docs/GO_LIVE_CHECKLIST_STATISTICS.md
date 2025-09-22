# 📋 Go-Live Freigabe – StatisticsRepo Cutover

**Datum:** `[AUSFÜLLEN]`
**Version:** v3.3 StatisticsRepository Pattern Migration
**Verantwortlich:** `[TEAM]`
**Emergency Contact:** `[ON-CALL]`

## ✅ Vorbedingungen (MÜSSEN erfüllt sein)

### 🔬 Repository Implementation
- [ ] **StatisticsRepository kapselt alle Aggregationen** (keine Raw-SQL in Views/HTMX)
- [ ] **Kern-APIs implementiert**:
  - `global_summary(period)` - Dashboard Hauptstatistiken
  - `feed_summary(feed_ids, period)` - Feed-spezifische Aggregationen
  - `coverage_slo()` - Analysis Coverage SLO Tracking
  - `trend_series(metric, period, bucket)` - Zeitserien für Charts
  - `topk_feeds(k, period)` - Top Feeds nach Metriken
- [ ] **DTOs vollständig** (StatsSummary, TrendSeries, FeedStats, CoverageSLO)
- [ ] **Error Handling** mit domänen-spezifischen Exceptions

**Prüfen:**
```bash
# Check for raw SQL in statistics code
rg "session\\.exec.*(COUNT|SUM|AVG|GROUP BY)" app/web app/api --type py | grep -v repositories
# Erwartung: 0 results (nur Repository calls)

# Verify repository methods
python -c "
from app.repositories.statistics_repo import StatisticsRepository
from app.db.session import db_session
repo = StatisticsRepository(db_session)
methods = ['global_summary', 'feed_summary', 'coverage_slo', 'trend_series', 'topk_feeds']
print('✅ StatisticsRepository methods:', all(hasattr(repo, m) for m in methods))
"
```

### 🧭 Deterministische Definitionen
- [ ] **Metriken fachlich präzise dokumentiert**
  - `impact_overall` = mean(impact.overall) auf Items mit published_at ∈ period, nur analyzed=true
  - `neg_pct` = Anteil Items mit sentiment.overall.label='negative' im Zeitfenster
  - `urgent_pct` = Anteil Items mit sentiment.urgency > 0.7 im Zeitfenster
  - `analyzed_pct` = Anteil Items mit item_analysis.item_id IS NOT NULL
- [ ] **Zeitfenster vereinheitlicht** (Presets: 2h | 24h | 7d | 30d)
- [ ] **Buckets standardisiert** (5m | 1h | 1d für Trend-Series)
- [ ] **Zeitzone fixiert** (UTC im Backend, UI lokalisiert)
- [ ] **Datenquellen klar** (nur items, item_analysis, feeds, feed_health)

### 🗄️ Aggregation-optimierte Indexes
- [ ] **Items Zeitindex** `items(published_at DESC)` für Zeitfenster-Queries
- [ ] **Partial Index** `items(published_at) WHERE published_at >= now()-interval '30 days'`
- [ ] **Analysis Join Index** `item_analysis(item_id)` bereits vorhanden
- [ ] **JSONB Expression Indexes** für häufige Aggregationen:
  - `((impact_json->>'overall')::numeric)` für Impact-Aggregationen
  - `(sentiment_json->'overall'->>'label')` für Sentiment-Filtering
  - `((sentiment_json->>'urgency')::numeric)` für Urgency-Filtering
- [ ] **Feed Join Index** `items(feed_id, published_at)` für Feed-Summary

**Prüfen:**
```bash
# Check statistics-specific indexes
PGPASSWORD=news_password psql -h localhost -U news_user -d news_db -c "
SELECT indexname, indexdef FROM pg_indexes
WHERE tablename IN ('items', 'item_analysis')
AND (indexdef LIKE '%published_at%' OR indexdef LIKE '%impact_json%' OR indexdef LIKE '%sentiment_json%')
ORDER BY tablename, indexname;
"

# Run statistics index reality check
python scripts/go_live_check_statistics.py --check-indexes
# Erwartung: Alle Performance-kritischen Indexes vorhanden
```

### 🎯 Performance Validation & SLO Targets
- [ ] **Global Summary 24h** P95 ≤ 400ms (Single call pro Dashboard-Load)
- [ ] **Feed Summary 24h** P95 ≤ 600ms (Multi-select, 5-10 Feeds)
- [ ] **Trend Series 24h/1h** P95 ≤ 800ms (24-48 Datenpunkte)
- [ ] **Trend Series 7d/1h** P95 ≤ 1.5s (168 Datenpunkte)
- [ ] **Top-K Feeds (k≤10)** P95 ≤ 400ms (sort by impact/volume)
- [ ] **Coverage SLO** P95 ≤ 300ms (einfache Counts)
- [ ] **Error-Rate** <0.5% für alle Statistics-Endpoints

**Prüfen:**
```bash
# Performance smoke tests
python scripts/go_live_check_statistics.py --check-performance
# Erwartung: Alle SLO Targets erfüllt

# Manual performance verification
time curl "http://localhost:8000/api/statistics/global-summary?period=24h"
time curl "http://localhost:8000/api/statistics/feed-summary?feed_ids=1,2,3&period=24h"
time curl "http://localhost:8000/api/statistics/trends?metric=items&period=24h&bucket=1h"
```

### 🔍 Data Consistency & Shadow Compare
- [ ] **50+ Aggregation-Vergleiche** Repo vs Legacy/Reference-SQL
- [ ] **Toleranzen definiert**:
  - Counts: exakt (=)
  - Averages/Prozente: ±0.5 pp (percentage points)
  - Trends: pro Bucket ±1 Count / ±0.5 pp
  - Zeiträume: exakt gleiche UTC-Fenster
- [ ] **Shadow Compare aktiviert** (app/utils/statistics_shadow_compare.py)
- [ ] **100 Requests/Kombination** für Haupt-Zeitfenster (24h/7d × 3-4 Metriken)

---

## 🚦 Cutover-Prozess

### Phase 1: Canary Start (10%)
```bash
curl -X POST "http://localhost:8000/api/admin/feature-flags/statistics_repo" \
  -H "Content-Type: application/json" \
  -d '{"status": "canary", "rollout_percentage": 10}'
```
- [ ] **30 min stabil** bei 10% ohne Errors
- [ ] **Shadow Compare aktiv** sammelt Aggregation-Vergleiche
- [ ] **Dashboard lädt** ohne Performance-Regression
- [ ] **Circuit Breaker** nicht getriggert

### Phase 2: Schrittweise Erhöhung
```bash
# 25% (nach 2h stabil)
curl -X POST "http://localhost:8000/api/admin/feature-flags/statistics_repo" \
  -d '{"status": "canary", "rollout_percentage": 25}'

# 50% (nach 2h stabil)
curl -X POST "http://localhost:8000/api/admin/feature-flags/statistics_repo" \
  -d '{"status": "canary", "rollout_percentage": 50}'

# 75% (nach 2h stabil)
curl -X POST "http://localhost:8000/api/admin/feature-flags/statistics_repo" \
  -d '{"status": "canary", "rollout_percentage": 75}'
```

**Je Stufe checken:**
- [ ] **≥2h stabil** (SLOs erfüllt)
- [ ] **Error-Rate <0.5%** für Aggregation-Endpoints
- [ ] **P95 Latency in Target** (siehe SLO-Tabelle oben)
- [ ] **Dashboard Performance** keine User-sichtbare Verlangsamung
- [ ] **Shadow Mismatch** <2% (innerhalb Toleranzen)
- [ ] **No Emergency Rollbacks**

### Phase 3: Full Deployment (100%)
```bash
curl -X POST "http://localhost:8000/api/admin/feature-flags/statistics_repo" \
  -d '{"status": "on", "rollout_percentage": 100}'
```
- [ ] **24h Full Traffic** ohne kritische Issues
- [ ] **Legacy Traffic = 0%** bestätigt
- [ ] **Performance SLOs erfüllt** sustained
- [ ] **Dashboard-Last** unter Peak-Bedingungen getestet

---

## 🛡️ Schutzmechanismen (während Cutover)

### Circuit-Breaker (Statistics-spezifisch)
- [ ] **Auto-Rollback** bei P95 > +30% für Global Summary
- [ ] **Emergency Disable** bei Error-Rate >5%
- [ ] **Aggregation Timeout Protection** bei >10s Queries
- [ ] **Shadow Mismatch** bei >2% Abweichungen außerhalb Toleranz
- [ ] **Manual Override** funktional getestet

### Performance Monitoring
- [ ] **Query Duration Tracking** per Metric-Type (global, feed, trends, topk)
- [ ] **Rows Scanned Estimation** via EXPLAIN sampling
- [ ] **Cache Hit Ratio** (falls MVs/Cache verwendet)
- [ ] **Database Load** unter Aggregation-Last überwacht

### Synthetic Canaries
```bash
# Setup continuous statistics testing
while true; do
  curl "http://localhost:8000/api/statistics/global-summary?period=24h" -H "X-Canary: stats-test"
  curl "http://localhost:8000/api/statistics/feed-summary?feed_ids=1,2&period=24h" -H "X-Canary: stats-test"
  curl "http://localhost:8000/api/statistics/trends?metric=items&period=24h&bucket=1h" -H "X-Canary: stats-test"
  sleep 60  # Statistics weniger frequent testen (nicht UI-blocking)
done
```

### Emergency Stop Procedure
```bash
# EMERGENCY ROLLBACK
curl -X POST "http://localhost:8000/api/admin/feature-flags/statistics_repo" \
  -d '{"status": "emergency_off"}'

# Verify rollback
curl "http://localhost:8000/api/admin/feature-flags/statistics_repo" | jq '.status'
```

---

## 🔍 Post-Cutover Validation (innerhalb 48h)

### Zero Legacy Traffic
- [ ] **Telemetrie Legacy-Aggregation-Routen = 0 Requests**
- [ ] **Monitoring Dashboard** zeigt 100% Repository Traffic
- [ ] **Log Analysis** bestätigt keine Raw-SQL Aggregationen

```bash
# Check legacy aggregation usage
grep "raw.*sql.*(COUNT\\|SUM\\|AVG\\|GROUP BY)" logs/*.log | wc -l
# Erwartung: 0
```

### Aggregation Health Check
- [ ] **Global Summary** lädt konsistent <400ms
- [ ] **Feed Summaries** für Multi-Select <600ms
- [ ] **Trend Series** 24h/1h <800ms, 7d/1h <1.5s
- [ ] **Top-K Feeds** Rankings korrekt und <400ms
- [ ] **Coverage SLO** Real-time Tracking funktional

### Dashboard Integration
- [ ] **Main Dashboard** lädt ohne Verzögerung
- [ ] **Feed Analytics Page** Multi-Feed-Auswahl funktional
- [ ] **Trend Charts** rendern korrekt (Chart.js/D3.js Integration)
- [ ] **Real-time Updates** (falls WebSocket/SSE) funktional
- [ ] **Export Functions** (CSV/JSON) für Reports

```bash
# Test full statistics API cycle
curl "http://localhost:8000/api/statistics/global-summary?period=24h" | jq '.total_items, .analyzed_pct, .avg_impact'

curl "http://localhost:8000/api/statistics/coverage-slo" | jq '.coverage_10m, .coverage_60m'

curl "http://localhost:8000/api/statistics/topk-feeds?k=5&period=24h" | jq '.[].feed_title, .[].avg_impact'
```

### Data Consistency Verification
- [ ] **Cross-Time-Window Consistency** (2h ⊆ 24h ⊆ 7d ⊆ 30d)
- [ ] **Real-time vs Historical** Zahlen konsistent
- [ ] **Timezone Handling** UTC Backend, lokale UI-Zeit
- [ ] **Edge Cases** (keine Items im Zeitfenster, nur unanalyzed items)

---

## 🧹 Aufräumen (nach 14 Tagen)

### Code Cleanup
- [ ] **Legacy Aggregation-SQL entfernen**
  ```bash
  git rm app/web/legacy_statistics.py  # if exists
  git rm app/api/legacy_stats.py  # if exists
  ```
- [ ] **Raw-SQL im Statistics-Bereich löschen**
  ```bash
  # CI-Check enforced: no raw aggregation SQL outside repositories
  rg "session\\.exec.*(COUNT|SUM|AVG|GROUP BY)" app/api app/web --type py
  # Erwartung: 0 results
  ```
- [ ] **Legacy Dashboard-Endpoints** entfernen
- [ ] **Shadow Compare deaktivieren** (CPU-Last reduzieren)

### Documentation Updates
- [ ] **CHANGELOG.md** "StatisticsRepo Cutover abgeschlossen"
- [ ] **API_DOCS.md** Statistics-Endpoints nur über Repository
- [ ] **DASHBOARD_GUIDE.md** neue Performance-Metriken dokumentiert
- [ ] **RUNBOOK** Legacy Aggregation-Procedures archiviert

### Monitoring Cleanup
- [ ] **Shadow Compare deaktiviert** (CPU sparen)
- [ ] **Legacy Statistics Metrics** aus Dashboard entfernt
- [ ] **Alert Rules** auf StatisticsRepository SLOs umgestellt
- [ ] **Grafana Dashboards** auf neue Metriken-Struktur migriert

---

## 📞 On-Call Runbook

### 🚨 Statistics-Specific Escalation
1. **Aggregation Performance Degradation** (P95 > SLO Target)
2. **Sofort:** Admin-Flag auf `emergency_off`
   ```bash
   curl -X POST "http://localhost:8000/api/admin/feature-flags/statistics_repo" \
     -d '{"status": "emergency_off"}'
   ```
3. **Check Query Performance:**
   ```bash
   # Check slow queries
   PGPASSWORD=news_password psql -h localhost -U news_user -d news_db \
     -c "SELECT query, mean_exec_time, calls FROM pg_stat_statements
         WHERE query LIKE '%items%analysis%'
         ORDER BY mean_exec_time DESC LIMIT 10;"
   ```
4. **Index Health Check:**
   ```bash
   python scripts/go_live_check_statistics.py --check-indexes
   ```

### 📊 Aggregation-Specific Rollback Verification
- [ ] **Global Summary** wieder <400ms über Legacy
- [ ] **Dashboard Load Time** normalisiert sich
- [ ] **Database CPU** reduziert sich binnen 5min
- [ ] **User Experience** keine Timeouts in Statistics-Views

### 🔧 Performance Emergency Procedures
```bash
# Check for missing indexes
PGPASSWORD=news_password psql -h localhost -U news_user -d news_db \
  -c "SELECT schemaname, tablename, attname, n_distinct, correlation
      FROM pg_stats
      WHERE tablename IN ('items', 'item_analysis')
      AND attname IN ('published_at', 'item_id');"

# Check table bloat
PGPASSWORD=news_password psql -h localhost -U news_user -d news_db \
  -c "SELECT relname, n_tup_ins, n_tup_upd, n_tup_del, n_live_tup, n_dead_tup
      FROM pg_stat_user_tables
      WHERE relname IN ('items', 'item_analysis');"
```

---

## ✍️ Sign-Off

**Technical Lead:** `[UNTERSCHRIFT]` `[DATUM]`
**Analytics Lead:** `[UNTERSCHRIFT]` `[DATUM]`
**Performance Engineer:** `[UNTERSCHRIFT]` `[DATUM]`
**Product Owner:** `[UNTERSCHRIFT]` `[DATUM]`

---

## 🎯 Success Criteria Summary

| **Metric** | **Target** | **Actual** | **Status** |
|------------|------------|------------|------------|
| Global Summary P95 | <400ms | `[FILL]` | `[✅/❌]` |
| Feed Summary P95 | <600ms | `[FILL]` | `[✅/❌]` |
| Trend Series 24h P95 | <800ms | `[FILL]` | `[✅/❌]` |
| Trend Series 7d P95 | <1.5s | `[FILL]` | `[✅/❌]` |
| Top-K Feeds P95 | <400ms | `[FILL]` | `[✅/❌]` |
| Coverage SLO P95 | <300ms | `[FILL]` | `[✅/❌]` |
| Error Rate | <0.5% | `[FILL]` | `[✅/❌]` |
| Shadow Mismatch Rate | <2% | `[FILL]` | `[✅/❌]` |
| Legacy Traffic After Cutover | 0% | `[FILL]` | `[✅/❌]` |

**Overall Go-Live Status:** `[GO / NO-GO]`

---

## 📈 Materialized Views Strategy (Optional - if SLOs fail)

### MV-Kandidaten (nur bei Performance-Problemen)
- [ ] **mv_item_daily**: pro Tag & Feed (count_items, count_analyzed, avg_impact, neg_pct, urgent_pct)
- [ ] **mv_item_hourly_recent**: letzte 7d, Bucket=Stunde
- [ ] **mv_feed_health_daily**: Erfolgs-/Fehlerraten pro Feed/Tag

### Refresh-Policy
- [ ] **Stündlich** für mv_item_hourly_recent
- [ ] **Täglich** für mv_item_daily
- [ ] **CONCURRENTLY Refresh** wenn möglich
- [ ] **Fallback**: Rollende Pre-Aggregation per Jobs

### Activation Criteria
- [ ] **>20% der Anfragen** reißen SLO Target
- [ ] **Gezielt für Hot-Endpoints** (Global Summary, Main Dashboard)
- [ ] **Erst messen, dann MV** - nicht prophylaktisch

---

*Diese Checkliste folgt dem Standard Repository Cutover Pattern mit Aggregation-spezifischen Erweiterungen. Siehe REPOSITORY_CUTOVER_PATTERN.md für Details.*