# 📋 Go-Live Freigabe – FeedsRepo Cutover

**Datum:** `[AUSFÜLLEN]`
**Version:** v3.2 FeedsRepository Pattern Migration
**Verantwortlich:** `[TEAM]`
**Emergency Contact:** `[ON-CALL]`

## ✅ Vorbedingungen (MÜSSEN erfüllt sein)

### 🔬 Repository Implementation
- [ ] **FeedsRepository kapselt alle CRUD Operations** (get_by_id, list, create, update, delete)
- [ ] **Health-Methoden implementiert** (get_health, list_health_summary, get_status_counts)
- [ ] **Feed Management über Repository** (keine Raw SQL in feed_management/)
- [ ] **HTMX-Endpoints über Repository** (keine direkten DB-Calls in feed views)
- [ ] **DTOs vollständig** (FeedCreate, FeedUpdate, FeedResponse, FeedHealthResponse)

**Prüfen:**
```bash
# Check for raw SQL in feeds code
rg "session\\.exec.*feeds|session\\.exec.*feed_health" app/web app/api --type py
# Erwartung: 0 results (nur Repository calls)

# Verify repository methods
python -c "
from app.repositories.feeds_repo import FeedsRepository
from app.db.session import db_session
repo = FeedsRepository(db_session)
methods = ['get_by_id', 'list', 'create', 'update', 'delete', 'get_health', 'list_health_summary']
print('✅ FeedsRepository methods:', all(hasattr(repo, m) for m in methods))
"
```

### 🔒 Data Integrity
- [ ] **Unique Constraint** auf `feeds.url` vorhanden
- [ ] **Referentielle Integrität** items → feeds FK konsistent
- [ ] **Health Records konsistent** jeder aktive Feed hat Health-Einträge
- [ ] **50 Stichproben** Repo-Result = Legacy-Result validiert
- [ ] **CRUD Konsistenz** Create→Read→Update→Delete Cycle getestet

**Prüfen:**
```bash
# Check for URL duplicates
PGPASSWORD=news_password psql -h localhost -U news_user -d news_db \
  -c "SELECT url, COUNT(*) FROM feeds GROUP BY url HAVING COUNT(*) > 1;"
# Erwartung: 0 rows

# Verify feeds have health records
PGPASSWORD=news_password psql -h localhost -U news_user -d news_db \
  -c "SELECT COUNT(*) as feeds_without_health FROM feeds f LEFT JOIN feed_health fh ON f.id = fh.feed_id WHERE fh.feed_id IS NULL;"
# Erwartung: 0 (or sehr wenige)
```

### 🗄️ Index Health
- [ ] **Primary Key Index** `feeds(id)` optimiert
- [ ] **Unique Index** `feeds(url)` für URL-Constraints
- [ ] **Feed Health Index** `feed_health(feed_id, created_at DESC)` für neuesten Status
- [ ] **Active Feeds Index** `feeds(active, created_at)` für Listen-Queries
- [ ] **Feed Categories Index** `feed_categories(feed_id)` falls verwendet

**Prüfen:**
```bash
# Check feed-specific indexes
PGPASSWORD=news_password psql -h localhost -U news_user -d news_db -c "
SELECT indexname, indexdef FROM pg_indexes
WHERE tablename IN ('feeds', 'feed_health', 'feed_categories')
ORDER BY tablename, indexname;
"

# Run feeds index reality check
python scripts/go_live_check_feeds.py --check-indexes
# Erwartung: Alle Tests PASSED
```

### 🚀 Performance Validation
- [ ] **Feed List P95 <100ms** für 50+ Feeds
- [ ] **Feed Details P95 <50ms** pro Feed
- [ ] **Health Summary P95 <200ms** für alle Feeds
- [ ] **CRUD Operations P95 <100ms** (Create/Update/Delete)
- [ ] **Pagination stabil** bei hoher Feed-Anzahl

### 🌐 API Health
- [ ] **Feed Endpoints verfügbar** (/api/feeds, /api/feeds/{id})
- [ ] **Health Endpoints verfügbar** (/api/feeds/{id}/health, /api/health/feeds)
- [ ] **HTMX Partials funktional** (feed lists, health status)
- [ ] **Feature Flag API** feeds_repo konfiguriert

**Prüfen:**
```bash
# Test feed API endpoints
curl "http://localhost:8000/api/feeds?limit=5" | jq '.feeds | length'
curl "http://localhost:8000/api/feeds/1" | jq '.id'
curl "http://localhost:8000/api/feeds/1/health" | jq '.status'

# Check feature flag availability
curl "http://localhost:8000/api/admin/feature-flags/feeds_repo" | jq '.status'
```

---

## 🚦 Cutover-Prozess

### Phase 1: Canary Start (10%)
```bash
curl -X POST "http://localhost:8000/api/admin/feature-flags/feeds_repo" \
  -H "Content-Type: application/json" \
  -d '{"status": "canary", "rollout_percentage": 10}'
```
- [ ] **30 min stabil** bei 10% ohne Errors
- [ ] **Shadow Compare aktiv** sammelt Feed-CRUD-Vergleiche
- [ ] **Circuit Breaker** nicht getriggert
- [ ] **UI funktional** für Repository-Traffic

### Phase 2: Schrittweise Erhöhung
```bash
# 25% (nach 2h stabil)
curl -X POST "http://localhost:8000/api/admin/feature-flags/feeds_repo" \
  -d '{"status": "canary", "rollout_percentage": 25}'

# 50% (nach 2h stabil)
curl -X POST "http://localhost:8000/api/admin/feature-flags/feeds_repo" \
  -d '{"status": "canary", "rollout_percentage": 50}'

# 75% (nach 2h stabil)
curl -X POST "http://localhost:8000/api/admin/feature-flags/feeds_repo" \
  -d '{"status": "canary", "rollout_percentage": 75}'
```

**Je Stufe checken:**
- [ ] **≥2h stabil** (SLOs erfüllt)
- [ ] **Error-Rate <0.5%** für CRUD Operations
- [ ] **P95 Latency in Target** (<200ms CRUD, <500ms Health)
- [ ] **UI Consistency** Feed-Listen und Details korrekt
- [ ] **No Emergency Rollbacks**

### Phase 3: Full Deployment (100%)
```bash
curl -X POST "http://localhost:8000/api/admin/feature-flags/feeds_repo" \
  -d '{"status": "on", "rollout_percentage": 100}'
```
- [ ] **24h Full Traffic** ohne kritische Issues
- [ ] **Legacy Traffic = 0%** bestätigt
- [ ] **Performance SLOs erfüllt**
- [ ] **Admin UI vollständig funktional**

---

## 🛡️ Schutzmechanismen (während Cutover)

### Circuit-Breaker
- [ ] **Auto-Rollback** bei P95 > +30% aktiviert
- [ ] **Emergency Disable** bei Error-Rate >5%
- [ ] **CRUD Failure Protection** bei >10% failed operations
- [ ] **Manual Override** funktional getestet

### Shadow Compare
- [ ] **Feed List Comparison** identische Anzahl und Reihenfolge
- [ ] **Feed Details Comparison** alle Felder konsistent
- [ ] **Health Status Comparison** Status-Aggregationen ±0.5%
- [ ] **CRUD Round-Trip** Create→Read→Update→Delete identisch

### Synthetic Canaries
```bash
# Setup continuous feed testing
while true; do
  curl "http://localhost:8000/api/feeds?limit=10" -H "X-Canary: feeds-test"
  curl "http://localhost:8000/api/feeds/1" -H "X-Canary: feeds-test"
  curl "http://localhost:8000/api/feeds/1/health" -H "X-Canary: feeds-test"
  sleep 30
done
```
- [ ] **3-5 Test-Requests/min** für alle CRUD Operations
- [ ] **Success Rate >99%** für Canaries
- [ ] **Health Check Coverage** alle aktiven Feeds

### Emergency Stop Procedure
```bash
# EMERGENCY ROLLBACK
curl -X POST "http://localhost:8000/api/admin/feature-flags/feeds_repo" \
  -d '{"status": "emergency_off"}'

# Verify rollback
curl "http://localhost:8000/api/admin/feature-flags/feeds_repo" | jq '.status'
```

---

## 🔍 Post-Cutover Validation (innerhalb 48h)

### Zero Legacy Traffic
- [ ] **Telemetrie Legacy-Feed-Routen = 0 Requests**
- [ ] **Monitoring Dashboard** zeigt 100% Repository Traffic
- [ ] **Log Analysis** bestätigt keine Legacy SQL für feeds/feed_health

```bash
# Check legacy feed route usage
grep "legacy.*feed\\|raw.*sql.*feed" logs/*.log | wc -l
# Erwartung: 0
```

### CRUD Health Check
- [ ] **Create Operations** funktional (neue Feeds erscheinen)
- [ ] **Read Operations** konsistent (Listen + Details)
- [ ] **Update Operations** sofort sichtbar (URL, Interval, Active-Status)
- [ ] **Delete Operations** vollständig (Feed + Health + Relations)
- [ ] **Health Queries** aktuell (<15min für aktive Feeds)

### Admin UI Health
- [ ] **Feed Management Page** lädt ohne Errors
- [ ] **Feed Creation Form** funktional
- [ ] **Feed Editing** (Interval, URL, Template Assignment)
- [ ] **Feed Deletion** mit Confirmation
- [ ] **Health Status Display** mit korrekten Farben/Badges
- [ ] **Real-time Updates** via HTMX

```bash
# Test full CRUD cycle via API
FEED_ID=$(curl -X POST "http://localhost:8000/api/feeds" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://test.example.com/rss", "title": "Test Feed"}' | jq -r '.id')

curl "http://localhost:8000/api/feeds/$FEED_ID" | jq '.title'

curl -X PUT "http://localhost:8000/api/feeds/$FEED_ID" \
  -H "Content-Type: application/json" \
  -d '{"title": "Updated Test Feed"}'

curl -X DELETE "http://localhost:8000/api/feeds/$FEED_ID"
```

---

## 🧹 Aufräumen (nach 14 Tagen)

### Code Cleanup
- [ ] **Legacy Feed CRUD entfernen**
  ```bash
  git rm app/web/legacy_feed_management.py  # if exists
  git rm app/api/legacy_feeds.py  # if exists
  ```
- [ ] **Raw-SQL im Feed-Bereich löschen**
  ```bash
  # CI-Check enforced: no raw SQL outside repositories
  rg "session\\.exec.*(feeds|feed_health)" app/api app/web --type py
  # Erwartung: 0 results
  ```
- [ ] **Legacy HTMX-Endpoints** entfernen
- [ ] **Legacy Feature Flag Code** entfernen

### Documentation Updates
- [ ] **CHANGELOG.md** "FeedsRepo Cutover abgeschlossen"
- [ ] **README.md** Feed-Management nur über Repository
- [ ] **DEVELOPER_SETUP.md** Feeds-Repository-Pattern dokumentiert
- [ ] **RUNBOOK** Legacy Feed-Procedures archiviert

### Monitoring Cleanup
- [ ] **Shadow Compare deaktiviert** (CPU sparen)
- [ ] **Legacy Feed Metrics** aus Dashboard entfernt
- [ ] **Alert Rules** auf FeedsRepository umgestellt

---

## 📞 On-Call Runbook

### 🚨 Feed-Specific Escalation
1. **Feed CRUD Failure** (Create/Update/Delete nicht funktional)
2. **Sofort:** Admin-Flag auf `emergency_off`
   ```bash
   curl -X POST "http://localhost:8000/api/admin/feature-flags/feeds_repo" \
     -d '{"status": "emergency_off"}'
   ```
3. **Check Feed Locks:**
   ```bash
   PGPASSWORD=news_password psql -h localhost -U news_user -d news_db \
     -c "SELECT * FROM pg_locks WHERE relation::regclass::text = 'feeds';"
   ```
4. **Health Status Reset:**
   ```bash
   curl "http://localhost:8000/api/feeds/health/status" | jq '.summary'
   ```

### 📊 Feed-Specific Rollback Verification
- [ ] **Feed Creation** wieder funktional über Legacy
- [ ] **Health Updates** werden korrekt geschrieben
- [ ] **Admin UI** zeigt korrekte Feed-Listen
- [ ] **RSS Fetcher** kann Feed-Konfiguration lesen

---

## ✍️ Sign-Off

**Technical Lead:** `[UNTERSCHRIFT]` `[DATUM]`
**QA Lead:** `[UNTERSCHRIFT]` `[DATUM]`
**DevOps Lead:** `[UNTERSCHRIFT]` `[DATUM]`
**Product Owner:** `[UNTERSCHRIFT]` `[DATUM]`

---

## 🎯 Success Criteria Summary

| **Metric** | **Target** | **Actual** | **Status** |
|------------|------------|------------|------------|
| Shadow Compare Match Rate | >98% | `[FILL]` | `[✅/❌]` |
| CRUD P95 Latency | <200ms | `[FILL]` | `[✅/❌]` |
| Health Query P95 Latency | <500ms | `[FILL]` | `[✅/❌]` |
| Error Rate | <0.5% | `[FILL]` | `[✅/❌]` |
| Legacy Traffic After Cutover | 0% | `[FILL]` | `[✅/❌]` |
| UI Functionality | 100% | `[FILL]` | `[✅/❌]` |

**Overall Go-Live Status:** `[GO / NO-GO]`

---

*Diese Checkliste folgt dem Standard Repository Cutover Pattern. Siehe REPOSITORY_CUTOVER_PATTERN.md für Details.*