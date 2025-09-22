# 📋 Go-Live Freigabe – ItemsRepo Cutover

**Datum:** `[AUSFÜLLEN]`
**Version:** v3.0 Repository Pattern Migration
**Verantwortlich:** `[TEAM]`
**Emergency Contact:** `[ON-CALL]`

## ✅ Vorbedingungen (MÜSSEN erfüllt sein)

### 🔍 Shadow Compare Validation
- [ ] **200+ Requests** in letzten 24h durchgeführt
- [ ] **0 kritische HTML-Diffs** (nur Whitespace/IDs erlaubt)
- [ ] **Item-Count ±0** zwischen Legacy und Repository
- [ ] **Ties (Sortierung) konsistent** bei identischen Timestamps

**Prüfen:**
```bash
curl "http://localhost:8000/api/admin/feature-flags/metrics/shadow-comparison" | jq '.total_comparisons, .match_rate, .mismatch_count'
# Erwartung: >200, >0.98, <5
```

### ⚡ Performance Validation
- [ ] **P95 ≤ Legacy +20%** über 24h Zeitraum
- [ ] **Error-Rate <0.5%** über letzten 1000 Requests
- [ ] **Keine Auto-Rollback Events** in letzten 48h
- [ ] **Memory/CPU Usage stabil** (<80% sustained)

**Prüfen:**
```bash
curl "http://localhost:8000/api/admin/feature-flags/metrics/performance" | jq '.comparison_metrics'
python monitoring_dashboard.py --mode check
```

### 🔥 Hot-Filters Load Test
- [ ] **feed_ids + search** Kombination getestet (Peak-Load)
- [ ] **sentiment + impact_min** Filter unter Last
- [ ] **Pagination** stabil bei hohem Ingest
- [ ] **Complex Multi-Filter** Queries <300ms P95

**Prüfen:**
```bash
# Load test critical filter combinations
for i in {1..50}; do
  curl "http://localhost:8000/api/items?feed_ids=1,2,3&search=bitcoin&sentiment=positive&impact_min=0.5" \
    -H "X-User-ID: load-test-$i" &
done
wait
```

### 🗄️ Index Health
- [ ] **Alle Required Indexes** vorhanden
- [ ] **VACUUM/ANALYZE** in letzten 24h
- [ ] **0 "missing index" Warnungen** im Reality-Check
- [ ] **Query Plans optimiert** für Repository Patterns

**Prüfen:**
```bash
python scripts/index_check.py
# Erwartung: Alle Tests PASSED, keine fehlenden Indexes
```

### 💰 Budget Guard (LLM)
- [ ] **Worker-Durchsatz stabil** (keine Throttle-Stürme)
- [ ] **Tagescap getestet** ohne Rate-Limit Hits
- [ ] **Cost-per-1k Items** im Budget
- [ ] **Analysis Queue** unter 100 Items backlog

**Prüfen:**
```bash
curl "http://localhost:8000/api/analysis/stats" | jq '.queue_length, .daily_cost'
python monitoring_dashboard.py | grep "Analysis"
```

---

## 🚦 Cutover-Prozess

### Phase 1: Canary Start (5%)
```bash
curl -X POST "http://localhost:8000/api/admin/feature-flags/items_repo" \
  -H "Content-Type: application/json" \
  -d '{"status": "canary", "rollout_percentage": 5}'
```
- [ ] **30 min stabil** bei 5% ohne Errors
- [ ] **Shadow Compare aktiv** und sammelt Daten
- [ ] **Circuit Breaker** nicht getriggert

### Phase 2: Schrittweise Erhöhung
```bash
# 10% (nach 30 min)
curl -X POST "http://localhost:8000/api/admin/feature-flags/items_repo" \
  -d '{"status": "canary", "rollout_percentage": 10}'

# 25% (nach 2h stabil)
curl -X POST "http://localhost:8000/api/admin/feature-flags/items_repo" \
  -d '{"status": "canary", "rollout_percentage": 25}'

# 50% (nach 2h stabil)
curl -X POST "http://localhost:8000/api/admin/feature-flags/items_repo" \
  -d '{"status": "canary", "rollout_percentage": 50}'

# 75% (nach 2h stabil)
curl -X POST "http://localhost:8000/api/admin/feature-flags/items_repo" \
  -d '{"status": "canary", "rollout_percentage": 75}'
```

**Je Stufe checken:**
- [ ] **≥2h stabil** (SLOs erfüllt)
- [ ] **Error-Rate <1%**
- [ ] **P95 Latency in Target**
- [ ] **No Emergency Rollbacks**

### Phase 3: Full Deployment (100%)
```bash
curl -X POST "http://localhost:8000/api/admin/feature-flags/items_repo" \
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
- [ ] **Latency Threshold** 30% über Baseline
- [ ] **Manual Override** funktional getestet

### Synthetic Canaries
```bash
# Setup continuous testing
while true; do
  curl "http://localhost:8000/api/items?limit=10" -H "X-Canary: true"
  curl "http://localhost:8000/htmx/items-list?limit=5" -H "X-Canary: true"
  sleep 20
done
```
- [ ] **3-5 Test-Requests/min** unabhängig vom User-Traffic
- [ ] **Success Rate >99%** für Canaries
- [ ] **Response Time monitoring** aktiv

### Emergency Stop Procedure
```bash
# EMERGENCY ROLLBACK
curl -X POST "http://localhost:8000/api/admin/feature-flags/items_repo" \
  -d '{"status": "emergency_off"}'

# Verify rollback
curl "http://localhost:8000/api/admin/feature-flags/items_repo" | jq '.status'
```

---

## 🔍 Post-Cutover Validation (innerhalb 48h)

### Zero Legacy Traffic
- [ ] **Telemetrie Legacy-Pfad = 0 Requests**
- [ ] **Monitoring Dashboard** zeigt 100% Repository Traffic
- [ ] **Log Analysis** bestätigt keine Legacy-Routen

```bash
# Check legacy route usage
grep "legacy\|raw_sql" logs/*.log | wc -l
# Erwartung: 0
```

### Dashboard Health Check
- [ ] **P50/P95/P99** Metrics within SLO
- [ ] **Error-Rate <0.1%** sustained
- [ ] **Cost-per-1k Items** im Target
- [ ] **Memory Usage** optimiert

### Data Integrity
- [ ] **Duplicate Detection** keine Doppel-Items
- [ ] **Pagination Stabilität** keine Sprünge
- [ ] **Sorting Consistency** bei Ties
- [ ] **Filter Accuracy** alle Kombinationen

```bash
# Test pagination stability
curl "http://localhost:8000/api/items?limit=20&page=1" > page1.json
curl "http://localhost:8000/api/items?limit=20&page=2" > page2.json
# Verify no overlaps
```

---

## 🧹 Aufräumen (nach 14 Tagen)

### Code Cleanup
- [ ] **Legacy HTMX-Endpoint entfernen**
  ```bash
  # Remove _get_items_list_legacy from app/web/items_htmx.py
  git rm app/web/legacy_items.py  # if exists
  ```
- [ ] **Raw-SQL im Items-Bereich löschen**
  ```bash
  # CI-Check enforced: no raw SQL outside repositories
  rg "session\.exec.*SELECT.*items" app/api app/web --type py
  # Erwartung: 0 results
  ```
- [ ] **Unused Imports cleanup**
- [ ] **Legacy Feature Flag Code** entfernen

### Documentation Updates
- [ ] **CHANGELOG.md** "ItemsRepo Cutover abgeschlossen"
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
   curl -X POST "http://localhost:8000/api/admin/feature-flags/items_repo" \
     -d '{"status": "emergency_off"}'
   ```
3. **Logs sichern:**
   ```bash
   grep ERROR logs/*.log | grep items_repo > /tmp/cutover_errors.log
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
| Cost per 1k Items | Within Budget | `[FILL]` | `[✅/❌]` |

**Overall Go-Live Status:** `[GO / NO-GO]`

---

*Diese Checkliste macht den Cutover prüfbar, wiederholbar und kommunizierbar.*