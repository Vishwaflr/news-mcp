# 📋 Go-Live Freigabe – AnalysisRepo Cutover

**Datum:** `[AUSFÜLLEN]`
**Version:** v3.1 Analysis Repository Pattern Migration
**Verantwortlich:** `[TEAM]`
**Emergency Contact:** `[ON-CALL]`

## ✅ Vorbedingungen (MÜSSEN erfüllt sein)

### 🔬 Repository Implementation
- [ ] **AnalysisRepo kapselt alle Reads/Writes** (upsert, get_by_item_id, status, aggregations)
- [ ] **Worker nutzt ausschließlich Repo** (keine Raw SQL in jobs/)
- [ ] **Control-Center über Repo** (analysis_control.py migriert)
- [ ] **HTMX-Endpoints über Repo** (keine direkten DB-Calls)

**Prüfen:**
```bash
# Check for raw SQL in analysis code
rg "session\.exec.*analysis" app/worker app/api --type py
# Erwartung: 0 results (nur Repository calls)

# Verify repository methods
python -c "
from app.repositories.analysis_repo import AnalysisRepository
from app.db.session import db_session
repo = AnalysisRepository(db_session)
print('✅ AnalysisRepo available:', hasattr(repo, 'upsert_analysis'))
"
```

### 🔒 Data Integrity
- [ ] **Unique Constraint** auf `item_analysis.item_id` vorhanden
- [ ] **Keine doppelten Einträge** in item_analysis
- [ ] **50 Stichproben** Repo-Result = Alt-Result validiert
- [ ] **JSON Schema konsistent** zwischen Legacy und Repo

**Prüfen:**
```bash
# Check for duplicate item_ids
PGPASSWORD=news_password psql -h localhost -U news_user -d news_db \
  -c "SELECT item_id, COUNT(*) FROM item_analysis GROUP BY item_id HAVING COUNT(*) > 1;"
# Erwartung: 0 rows

# Verify unique constraint exists
PGPASSWORD=news_password psql -h localhost -U news_user -d news_db \
  -c "\d item_analysis" | grep "PRIMARY KEY\|UNIQUE"
```

### 🤖 Worker Health
- [ ] **Worker Heartbeat stabil** <10s zwischen Updates
- [ ] **RPS-Policy eingehalten** (±5% of target rate)
- [ ] **Deferred/Retry-Logik getestet** (429, Timeout scenarios)
- [ ] **Queue Processing stabil** (keine Stau-Bildung)

**Prüfen:**
```bash
# Check worker status
curl "http://localhost:8000/api/analysis/worker/status" | jq '.heartbeat_age_seconds, .rps_current, .queue_length'
# Erwartung: <10, ~1.0, <100

# Test deferred handling
curl "http://localhost:8000/api/analysis/test-deferred" -X POST
```

### 📊 Run-Status Konsistenz
- [ ] **analysis_runs Aggregation korrekt** (queued, processing, completed, failed)
- [ ] **analysis_run_items Status** stimmt mit Worker-State überein
- [ ] **Dashboard-Counts** = DB-Queries (±0.5%)
- [ ] **Run Progress** wird korrekt getrackt

**Prüfen:**
```bash
# Verify run status consistency
PGPASSWORD=news_password psql -h localhost -U news_user -d news_db -c "
SELECT
  ar.status as run_status,
  COUNT(ari.item_id) as item_count,
  COUNT(CASE WHEN ari.status = 'completed' THEN 1 END) as completed_count
FROM analysis_runs ar
LEFT JOIN analysis_run_items ari ON ar.id = ari.run_id
WHERE ar.created_at > NOW() - INTERVAL '24 hours'
GROUP BY ar.id, ar.status;
"

# Check dashboard consistency
curl "http://localhost:8000/api/analysis/stats" | jq '.run_stats'
```

### 🗄️ Index Health
- [ ] **Primary Key** `item_analysis.item_id` optimiert
- [ ] **JSONB-GIN Index** oder First-Class Spalten für sentiment/impact
- [ ] **analysis_run_items(run_id, status)** Index für Status-Queries
- [ ] **Keine "missing index" Warnungen** für Analysis-Queries

**Prüfen:**
```bash
# Run analysis-specific index check
python scripts/go_live_check_analysis.py --check-indexes

# Verify critical indexes exist
PGPASSWORD=news_password psql -h localhost -U news_user -d news_db -c "
SELECT indexname, indexdef FROM pg_indexes
WHERE tablename IN ('item_analysis', 'analysis_runs', 'analysis_run_items')
ORDER BY tablename, indexname;
"
```

---

## 🚦 Cutover-Prozess

### Phase 1: Canary Run (Single Run Test)
```bash
# Start single analysis run with feature flag
curl -X POST "http://localhost:8000/api/admin/feature-flags/analysis_repo" \
  -H "Content-Type: application/json" \
  -d '{"status": "canary", "rollout_percentage": 0}'

# Create test run (200 items max)
curl -X POST "http://localhost:8000/api/analysis/runs" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Repository Canary Test",
    "target_selection": {"type": "latest", "limit": 200},
    "canary_test": true
  }'
```
- [ ] **Canary Run erfolgreich** ohne Errors
- [ ] **Shadow Compare aktiv** sammelt Vergleichsdaten
- [ ] **200 Items verarbeitet** in erwarteter Zeit
- [ ] **JSON Results konsistent** mit Legacy-Baseline

### Phase 2: Rollout-Stufen
```bash
# 10% Rollout
curl -X POST "http://localhost:8000/api/admin/feature-flags/analysis_repo" \
  -d '{"status": "canary", "rollout_percentage": 10}'

# 25% Rollout (nach 1 Tag stabil)
curl -X POST "http://localhost:8000/api/admin/feature-flags/analysis_repo" \
  -d '{"status": "canary", "rollout_percentage": 25}'

# 50% Rollout (nach 1 Tag stabil)
curl -X POST "http://localhost:8000/api/admin/feature-flags/analysis_repo" \
  -d '{"status": "canary", "rollout_percentage": 50}'

# 100% Rollout (nach 1 Tag stabil)
curl -X POST "http://localhost:8000/api/admin/feature-flags/analysis_repo" \
  -d '{"status": "on", "rollout_percentage": 100}'
```

**Je Stufe checken:**
- [ ] **≥1 Tag stabil** mit aktueller Stufe
- [ ] **Worker Error-Rate <5%**
- [ ] **Run Failure-Rate <10%**
- [ ] **Analysis Coverage ≥95%** (Items get analyzed)
- [ ] **Cost Budget eingehalten**

### Phase 3: Legacy Abschaltung
```bash
# Verify 100% Repository traffic
curl "http://localhost:8000/api/admin/feature-flags/metrics/dashboard" | \
  jq '.flag_status.analysis_repo'

# Deactivate shadow comparison (save CPU)
curl -X POST "http://localhost:8000/api/admin/feature-flags/analysis_shadow" \
  -d '{"status": "off"}'
```

---

## 🛡️ Schutzmechanismen

### Circuit Breaker
- [ ] **Auto-Rollback** bei Error-Rate >5% aktiviert
- [ ] **Run Failure Protection** bei >10% failed runs
- [ ] **Shadow Mismatch** bei >2% Abweichungen
- [ ] **Cost Explosion Protection** bei >150% Budget

### Worker Protection
- [ ] **Deferred Queue** funktional für 429/Timeout
- [ ] **Rate Limiting** respektiert API-Limits
- [ ] **Graceful Degradation** bei LLM-Ausfällen
- [ ] **Queue Backup** verhindert Item-Verlust

### Emergency Procedures
```bash
# EMERGENCY ROLLBACK
curl -X POST "http://localhost:8000/api/admin/feature-flags/analysis_repo" \
  -d '{"status": "emergency_off"}'

# Stop all analysis workers
curl -X POST "http://localhost:8000/api/analysis/worker/stop" \
  -H "Authorization: Admin"

# Verify rollback
curl "http://localhost:8000/api/admin/feature-flags/analysis_repo" | jq '.status'
# Should show "emergency_off"
```

---

## 🔍 Post-Cutover Validation (innerhalb 48h)

### Worker Kontinuität
- [ ] **Neue Items kontinuierlich verarbeitet** (keine Stau-Bildung)
- [ ] **Queue Length** <100 Items sustained
- [ ] **Processing Time** <60s per Item (P95)
- [ ] **Worker Restarts** funktional (State Recovery)

### Analysis Coverage
- [ ] **90% Items haben Sentiment/Impact** innerhalb 10 Min
- [ ] **98% Items vollständig analysiert** innerhalb 60 Min
- [ ] **Badge Display** korrekt im Frontend
- [ ] **Filter Funktionalität** (sentiment, impact) arbeitet

### Cost & Performance
- [ ] **Tagesbudget eingehalten** (±10%)
- [ ] **Cost-per-Item** im Target
- [ ] **API Response Time** <500ms für Analysis-Endpoints
- [ ] **Dashboard-Load** <2s für Analysis-Overview

### Data Consistency
- [ ] **Run Status korrekt** (completed runs zeigen 100% items)
- [ ] **Aggregation Counts** stimmen mit DB überein
- [ ] **Historical Data** unverändert
- [ ] **Backup/Recovery** getestet

```bash
# Validation test suite
python scripts/validate_analysis_migration.py --comprehensive

# Check analysis coverage
curl "http://localhost:8000/api/analysis/coverage-report" | \
  jq '.coverage_24h, .avg_processing_time, .error_rate'
```

---

## 🧹 Aufräumen (nach 14 Tagen)

### Code Cleanup
- [ ] **Legacy Analysis SQL** entfernt aus Worker
- [ ] **Raw SQL Blocks** aus analysis_control.py
- [ ] **Alte Helper Functions** für direkten DB-Access
- [ ] **Analysis Shadow Compare** Code entfernt

```bash
# Remove legacy analysis code
git rm app/worker/legacy_analysis.py  # if exists
git rm app/services/legacy_analysis_service.py  # if exists

# Verify no raw analysis SQL remains
rg "INSERT INTO item_analysis|UPDATE item_analysis" app/ --type py
# Erwartung: 0 results
```

### CI Enforcement
- [ ] **CI-Check** blockiert direkte `item_analysis` Writes
- [ ] **Pre-commit Hook** verhindert Raw Analysis-SQL
- [ ] **Code Review Template** checkt Repository-Usage

```yaml
# Add to .github/workflows/ci.yml
- name: Check for Raw Analysis SQL
  run: |
    if grep -r "INSERT INTO item_analysis\|UPDATE item_analysis" app/ --include="*.py"; then
      echo "❌ Direct item_analysis writes detected. Use AnalysisRepository instead."
      exit 1
    fi
```

### Documentation Updates
- [ ] **CHANGELOG.md** "AnalysisRepo Cutover abgeschlossen"
- [ ] **DEVELOPER_SETUP.md** nur Repository Pattern für Analysis
- [ ] **WORKER_README.md** Repository-Integration dokumentiert
- [ ] **RUNBOOK** Legacy-Procedures archiviert

---

## 📞 Analysis-Specific Emergency Runbook

### 🚨 Worker Failure Escalation
1. **Worker gestoppt/crashed**
   ```bash
   # Check worker status
   curl "http://localhost:8000/api/analysis/worker/status"

   # Restart worker if needed
   ./scripts/start-worker.sh restart
   ```

2. **LLM API Issues (429/5xx)**
   ```bash
   # Check deferred queue
   curl "http://localhost:8000/api/analysis/deferred-stats"

   # Temporarily reduce RPS
   curl -X POST "http://localhost:8000/api/analysis/worker/rps" \
     -d '{"rps": 0.5}'
   ```

3. **Cost Explosion**
   ```bash
   # Emergency stop all analysis
   curl -X POST "http://localhost:8000/api/analysis/worker/stop"

   # Check daily spending
   curl "http://localhost:8000/api/analysis/cost-report"
   ```

### 📊 Run Inconsistency Recovery
1. **Stuck Runs** (processing forever)
   ```bash
   # List stuck runs
   curl "http://localhost:8000/api/analysis/runs?status=processing&older_than=1h"

   # Force run completion
   curl -X POST "http://localhost:8000/api/analysis/runs/{run_id}/force-complete"
   ```

2. **Missing Analysis Results**
   ```bash
   # Requeue failed items
   curl -X POST "http://localhost:8000/api/analysis/runs/{run_id}/retry-failed"

   # Check analysis coverage
   python scripts/analysis_coverage_check.py --run-id {run_id}
   ```

---

## ✍️ Sign-Off

**Technical Lead:** `[UNTERSCHRIFT]` `[DATUM]`
**AI/ML Lead:** `[UNTERSCHRIFT]` `[DATUM]`
**Worker Infrastructure:** `[UNTERSCHRIFT]` `[DATUM]`
**Product Owner:** `[UNTERSCHRIFT]` `[DATUM]`

---

## 🎯 Success Criteria Summary

| **Metric** | **Target** | **Actual** | **Status** |
|------------|------------|------------|------------|
| Worker Error Rate | <5% | `[FILL]` | `[✅/❌]` |
| Analysis Coverage 24h | >95% | `[FILL]` | `[✅/❌]` |
| Run Failure Rate | <10% | `[FILL]` | `[✅/❌]` |
| Processing Time P95 | <60s | `[FILL]` | `[✅/❌]` |
| Cost per Item | Within Budget | `[FILL]` | `[✅/❌]` |
| Legacy Traffic After Cutover | 0% | `[FILL]` | `[✅/❌]` |
| Queue Length Sustained | <100 items | `[FILL]` | `[✅/❌]` |

**Overall Go-Live Status:** `[GO / NO-GO]`

---

*Diese Checkliste ist speziell auf Worker-basierte Analysis-Pipeline und Run-Konsistenz zugeschnitten.*