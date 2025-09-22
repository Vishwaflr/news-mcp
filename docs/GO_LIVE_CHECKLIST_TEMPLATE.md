# 📋 Go-Live Freigabe – [REPO_NAME] Cutover

**Datum:** `[AUSFÜLLEN]`
**Version:** v[X.Y] [REPO_NAME] Repository Pattern Migration
**Verantwortlich:** `[TEAM]`
**Emergency Contact:** `[ON-CALL]`

## ✅ Vorbedingungen (MÜSSEN erfüllt sein)

### 🔬 Repository Implementation
- [ ] **[REPO_NAME]Repository kapselt alle Operations** (CRUD, Queries, Aggregations)
- [ ] **[MODULE] nutzt ausschließlich Repository** (keine Raw SQL in [area]/)
- [ ] **API-Endpoints über Repository** (keine direkten DB-Calls)
- [ ] **Error Handling vollständig** (Domain-specific Exceptions)

**Prüfen:**
```bash
# Check for raw SQL in [repo] code
rg "session\\.exec.*[table]" app/[module] app/api --type py
# Erwartung: 0 results (nur Repository calls)

# Verify repository methods
python -c "
from app.repositories.[repo]_repo import [REPO_NAME]Repository
from app.db.session import db_session
repo = [REPO_NAME]Repository(db_session)
print('✅ [REPO_NAME]Repository available:', hasattr(repo, '[key_method]'))
"
```

### 🔒 Data Integrity
- [ ] **Primary Keys/Unique Constraints** korrekt definiert
- [ ] **Keine doppelten Einträge** in [main_table]
- [ ] **50 Stichproben** Repo-Result = Legacy-Result validiert
- [ ] **Schema konsistent** zwischen Legacy und Repository

**Prüfen:**
```bash
# Check for duplicates in main table
PGPASSWORD=news_password psql -h localhost -U news_user -d news_db \
  -c "SELECT [key_field], COUNT(*) FROM [main_table] GROUP BY [key_field] HAVING COUNT(*) > 1;"
# Erwartung: 0 rows

# Verify constraints exist
PGPASSWORD=news_password psql -h localhost -U news_user -d news_db \
  -c "\\d [main_table]" | grep "PRIMARY KEY\\|UNIQUE"
```

### 🚀 Performance Validation (Read-Heavy Repos)
- [ ] **P95 ≤ Legacy +20%** über 24h Zeitraum
- [ ] **Error-Rate <0.5%** über letzten 1000 Requests
- [ ] **Complex Queries <300ms P95**
- [ ] **Pagination stabil** bei hoher Last

### 🤖 Worker Health (Write-Heavy Repos)
- [ ] **Worker Heartbeat stabil** <30s zwischen Updates
- [ ] **Processing Rate eingehalten** (±5% of target)
- [ ] **Queue Processing stabil** (keine Stau-Bildung)
- [ ] **Error Recovery getestet** (Retry/Deferred Logic)

**Prüfen:**
```bash
# Check worker/API status
curl "http://localhost:8000/api/[module]/status" | jq '.status, .queue_length'
# Erwartung: "healthy", <100
```

### 🗄️ Index Health
- [ ] **Alle Required Indexes** vorhanden
- [ ] **Query Plans optimiert** für Repository Patterns
- [ ] **0 "missing index" Warnungen** im Reality-Check
- [ ] **VACUUM/ANALYZE** in letzten 24h

**Prüfen:**
```bash
python scripts/go_live_check_[repo].py --check-indexes
# Erwartung: Alle Tests PASSED, keine fehlenden Indexes
```

---

## 🚦 Cutover-Prozess

### Phase 1: Canary Start (5%)
```bash
curl -X POST "http://localhost:8000/api/admin/feature-flags/[repo]_repo" \
  -H "Content-Type: application/json" \
  -d '{"status": "canary", "rollout_percentage": 5}'
```
- [ ] **30 min stabil** bei 5% ohne Errors
- [ ] **Shadow Compare aktiv** und sammelt Daten
- [ ] **Circuit Breaker** nicht getriggert

### Phase 2: Schrittweise Erhöhung
```bash
# 10% (nach 30 min)
curl -X POST "http://localhost:8000/api/admin/feature-flags/[repo]_repo" \
  -d '{"status": "canary", "rollout_percentage": 10}'

# 25% (nach 2h stabil)
curl -X POST "http://localhost:8000/api/admin/feature-flags/[repo]_repo" \
  -d '{"status": "canary", "rollout_percentage": 25}'

# 50% (nach 2h stabil)
curl -X POST "http://localhost:8000/api/admin/feature-flags/[repo]_repo" \
  -d '{"status": "canary", "rollout_percentage": 50}'

# 75% (nach 2h stabil)
curl -X POST "http://localhost:8000/api/admin/feature-flags/[repo]_repo" \
  -d '{"status": "canary", "rollout_percentage": 75}'
```

**Je Stufe checken:**
- [ ] **≥2h stabil** (SLOs erfüllt)
- [ ] **Error-Rate <0.5%** (Read) / **<5%** (Write)
- [ ] **P95 Latency in Target**
- [ ] **No Emergency Rollbacks**

### Phase 3: Full Deployment (100%)
```bash
curl -X POST "http://localhost:8000/api/admin/feature-flags/[repo]_repo" \
  -d '{"status": "on", "rollout_percentage": 100}'
```
- [ ] **24h Full Traffic** ohne kritische Issues
- [ ] **Legacy Traffic = 0%** bestätigt
- [ ] **Performance SLOs erfüllt**

---

## 🛡️ Schutzmechanismen (während Cutover)

### Circuit-Breaker
- [ ] **Auto-Rollback** bei P95 > +30% aktiviert
- [ ] **Emergency Disable** bei Error-Rate >5%
- [ ] **Shadow Mismatch** bei >2% Abweichungen
- [ ] **Manual Override** funktional getestet

### Synthetic Canaries
```bash
# Setup continuous testing
while true; do
  curl "http://localhost:8000/api/[module]?limit=10" -H "X-Canary: true"
  sleep 20
done
```
- [ ] **3-5 Test-Requests/min** unabhängig vom User-Traffic
- [ ] **Success Rate >99%** für Canaries
- [ ] **Response Time monitoring** aktiv

### Emergency Stop Procedure
```bash
# EMERGENCY ROLLBACK
curl -X POST "http://localhost:8000/api/admin/feature-flags/[repo]_repo" \
  -d '{"status": "emergency_off"}'

# Verify rollback
curl "http://localhost:8000/api/admin/feature-flags/[repo]_repo" | jq '.status'
```

---

## 🔍 Post-Cutover Validation (innerhalb 48h)

### Zero Legacy Traffic
- [ ] **Telemetrie Legacy-Pfad = 0 Requests**
- [ ] **Monitoring Dashboard** zeigt 100% Repository Traffic
- [ ] **Log Analysis** bestätigt keine Legacy-Routen

```bash
# Check legacy route usage
grep "legacy\\|raw_sql" logs/*.log | wc -l
# Erwartung: 0
```

### Performance Health Check
- [ ] **P50/P95/P99** Metrics within SLO
- [ ] **Error-Rate <0.1%** sustained
- [ ] **Memory Usage** optimiert
- [ ] **Query Performance** stable

### Data Integrity
- [ ] **No Data Loss** confirmed via row counts
- [ ] **Consistency Checks** pass
- [ ] **Constraint Validation** no violations
- [ ] **Backup/Recovery** tested

```bash
# Comprehensive validation
python scripts/validate_[repo]_migration.py --comprehensive
```

---

## 🧹 Aufräumen (nach 14 Tagen)

### Code Cleanup
- [ ] **Legacy [REPO] Module entfernen**
  ```bash
  git rm app/[module]/legacy_[repo].py
  git rm app/services/legacy_[repo]_service.py
  ```
- [ ] **Raw-SQL im [REPO]-Bereich löschen**
  ```bash
  # CI-Check enforced: no raw SQL outside repositories
  rg "session\\.exec.*[table]" app/api app/[module] --type py
  # Erwartung: 0 results
  ```
- [ ] **Unused Imports cleanup**
- [ ] **Legacy Feature Flag Code** entfernen

### Documentation Updates
- [ ] **CHANGELOG.md** "[REPO_NAME] Cutover abgeschlossen"
- [ ] **README.md** Legacy-Referenzen entfernt
- [ ] **DEVELOPER_SETUP.md** nur Repository Pattern
- [ ] **RUNBOOK** Rollback-Teil archiviert

### Monitoring Cleanup
- [ ] **Shadow Compare deaktiviert** (CPU sparen)
- [ ] **Legacy Metrics** aus Dashboard entfernt
- [ ] **Alert Rules** auf Repository Pattern umgestellt

---

## 📞 On-Call Runbook

### 🚨 Fehler-Escalation
1. **Monitoring Alert** > Threshold getriggert
2. **Sofort:** Admin-Flag auf `emergency_off`
   ```bash
   curl -X POST "http://localhost:8000/api/admin/feature-flags/[repo]_repo" \
     -d '{"status": "emergency_off"}'
   ```
3. **Logs sichern:**
   ```bash
   grep ERROR logs/*.log | grep [repo]_repo > /tmp/cutover_errors.log
   ```
4. **Shadow-Compare neu laufen lassen** für Baseline
5. **Root Cause Analysis** + Fix + Re-Test

### 📊 Rollback Verification
- [ ] **Flag Status** = `emergency_off` bestätigt
- [ ] **Traffic Route** = 100% Legacy bestätigt
- [ ] **Error Rate** normalisiert sich binnen 5 min
- [ ] **User Impact** = 0 (keine 5xx Responses)

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
| P95 Latency vs Baseline | <+20% | `[FILL]` | `[✅/❌]` |
| Error Rate | <0.5% | `[FILL]` | `[✅/❌]` |
| Legacy Traffic After Cutover | 0% | `[FILL]` | `[✅/❌]` |
| [REPO_SPECIFIC_METRIC] | [TARGET] | `[FILL]` | `[✅/❌]` |

**Overall Go-Live Status:** `[GO / NO-GO]`

---

*Diese Checkliste folgt dem Standard Repository Cutover Pattern. Siehe REPOSITORY_CUTOVER_PATTERN.md für Details.*