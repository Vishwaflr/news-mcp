# 📘 Repository Cutover Pattern – Team Standard

**Version:** 1.0
**Status:** Production Standard
**Anwendbar auf:** Alle Raw-SQL → Repository Migrationen

## 🎯 Ziel

Risikofreie Migration von Raw-SQL oder Legacy-Code zu einem Repository-Layer durch klar strukturierte Phasen:

**Checkliste → Validation Tools → Feature Flags → Shadow Compare → Canary Rollout → CI-Prevention → Cleanup**

## 🔑 Kernprinzipien

### Shadow Safety
- Alte und neue Implementierung laufen parallel
- Unterschiede werden automatisch gemessen und geloggt
- Mismatch-Rate < 2% als Go-Live Kriterium

### Canary Rollout
- Neue Implementierung nur schrittweise aktiviert (5% → 100%)
- Mindestens 2h stabil pro Stufe
- Auto-Rollback bei SLO-Verletzungen

### Feature Flags
- Zentral steuerbar über Admin API
- Auto-Fallback bei kritischen Metriken
- Emergency Stop in <5min möglich

### Observability
- SLO-basierte Metriken (Latenz, Error-Rate, Data Consistency)
- Real-time Monitoring während Rollout
- Post-Cutover Coverage Tracking

### Enforcement
- CI/CD verhindert Rückfälle in Raw-SQL
- Pre-commit Hooks als erste Verteidigungslinie
- Repository Pattern als einziger zugelassener DB-Access

### Cleanup
- Legacy-Pfad innerhalb von 14 Tagen nach Full-Cutover entfernt
- Dokumentation und Runbooks aktualisiert
- CI-Regeln dauerhaft aktiviert

---

## 📋 Standard-Phasen

### 1️⃣ Preparation

#### Repository Implementation
- [ ] **CRUD Operations** vollständig implementiert
- [ ] **DTOs und Schemas** für Type Safety
- [ ] **Error Handling** mit domänen-spezifischen Exceptions
- [ ] **Unit Tests** mit >90% Coverage
- [ ] **Integration Tests** gegen Test-DB

#### Documentation
- [ ] **Go-Live Checkliste** in `/docs/GO_LIVE_CHECKLIST_<repo>.md`
- [ ] **Validation Tool** in `/scripts/go_live_check_<repo>.py`
- [ ] **Required Indexes** dokumentiert und Performance-getestet
- [ ] **Repository API Docs** mit Beispielen

#### Prerequisites
```bash
# Standard validation command
python scripts/go_live_check_<repo>.py
# Expected: All checks ✅ READY
```

### 2️⃣ Validation

#### Automated Checks
- [ ] **Database Health**: Connectivity, Pool Size, Latency
- [ ] **Index Coverage**: Alle Required Indexes vorhanden
- [ ] **Repository Implementation**: Import, Instantiation, Key Methods
- [ ] **Legacy Comparison**: 50+ Stichproben identische Results

#### Shadow Compare Setup
```python
# Standard pattern in app/utils/<repo>_shadow_compare.py
class <Repo>ShadowComparer:
    def compare_<operation>(self, legacy_result, repo_result):
        # Compare, log mismatches, update metrics
```

#### Data Integrity
- [ ] **No Duplicate Keys** in Primary Tables
- [ ] **Foreign Key Consistency** across related tables
- [ ] **JSON Schema Validation** für JSONB Fields
- [ ] **Temporal Consistency** (created_at, updated_at)

### 3️⃣ Feature Flags

#### Admin API Setup
```bash
# Feature flag pattern: <repo>_repo
curl -X POST "http://localhost:8000/api/admin/feature-flags/<repo>_repo" \
  -d '{"status": "off", "rollout_percentage": 0}'
```

#### Auto-Fallback Configuration
- [ ] **Error-Rate Threshold**: >5% → Emergency Rollback
- [ ] **Latency Threshold**: P95 > +30% vs Legacy → Rollback
- [ ] **Shadow-Mismatch Threshold**: >2% → Alert + Investigation
- [ ] **Manual Emergency Stop**: `emergency_off` status verfügbar

#### Circuit Breaker Logic
```python
# Standard pattern in Repository
if feature_flags.is_enabled('<repo>_repo'):
    result = new_repository_method()
    if shadow_compare_enabled:
        legacy_result = legacy_method()
        shadow_comparer.compare(legacy_result, result)
else:
    result = legacy_method()
```

### 4️⃣ Canary Rollout

#### Rollout Timeline
```bash
# Phase 1: 5% Traffic (30min stable)
curl -X POST "/api/admin/feature-flags/<repo>_repo" \
  -d '{"status": "canary", "rollout_percentage": 5}'

# Phase 2: 10% → 25% → 50% → 75% (≥2h stable each)
# Phase 3: 100% Full Traffic (24h observation)
curl -X POST "/api/admin/feature-flags/<repo>_repo" \
  -d '{"status": "on", "rollout_percentage": 100}'
```

#### SLO Monitoring (je Stufe)
- [ ] **P95 Latency**: ≤ Legacy +20%
- [ ] **Error Rate**: <0.5%
- [ ] **Shadow Mismatch**: <2%
- [ ] **No Emergency Rollbacks**: Circuit Breaker nicht getriggert

#### Synthetic Canaries
```bash
# Continuous health check during rollout
while true; do
  curl "http://localhost:8000/api/<repo>?limit=10" -H "X-Canary: true"
  sleep 20
done
```

### 5️⃣ Post-Cutover Validation

#### SLO Establishment
- [ ] **Performance SLOs**: P50, P95, P99 documented
- [ ] **Error Rate SLO**: <0.1% sustained
- [ ] **Coverage SLO** (für Worker): ≥90% in 10min, ≥98% in 60min
- [ ] **Cost SLO** (für LLM): Daily cap compliance

#### Dashboard Setup
- [ ] **Repo vs Legacy Performance** comparison
- [ ] **Repo-specific Metrics** (domain-relevant KPIs)
- [ ] **Error Analysis** und Alerting
- [ ] **Cost Tracking** (falls relevant)

#### Data Integrity Verification
- [ ] **Legacy Traffic = 0%**: Confirmed via telemetry
- [ ] **No Data Loss**: Row counts consistent
- [ ] **No Corruption**: Sample data verification
- [ ] **Performance within SLO**: 48h sustained

### 6️⃣ Cleanup

#### Code Removal (nach 14 Tagen)
```bash
# Remove legacy implementations
git rm app/<module>/legacy_<repo>.py
git rm app/services/legacy_<repo>_service.py

# Verify no raw SQL remains
rg "INSERT INTO <table>|UPDATE <table>" app/ --type py
# Expected: 0 results
```

#### CI Enforcement
```yaml
# Standard CI check in .github/workflows/<repo>-repo-check.yml
- name: Check for Raw <Repo> SQL
  run: |
    if grep -r "INSERT INTO <table>\\|UPDATE <table>" app/ --include="*.py"; then
      echo "❌ Direct <table> writes detected. Use <Repo>Repository instead."
      exit 1
    fi
```

#### Documentation Updates
- [ ] **CHANGELOG.md**: "<Repo> Cutover abgeschlossen"
- [ ] **DEVELOPER_SETUP.md**: Nur Repository Pattern dokumentiert
- [ ] **RUNBOOK**: Legacy Procedures archiviert
- [ ] **API Docs**: Repository Endpoints als Standard

---

## 🛡️ Standard-Schutzmechanismen

### Circuit Breaker
```python
class RepositoryCircuitBreaker:
    def check_health_metrics(self):
        if error_rate > 0.05:  # 5%
            self.trigger_emergency_rollback()
        if p95_latency > baseline * 1.3:  # +30%
            self.trigger_rollback()
```

### Shadow Compare
```python
# Standard sample rate: 10% during canary, 1% post-cutover
shadow_comparer.enable(sample_rate=0.1)
```

### Synthetic Canaries
- **Frequency**: 3-5 Requests/min unabhängig vom User-Traffic
- **Success Rate**: >99% erforderlich
- **Response Time**: Kontinuierliche Überwachung

### Index Reality Check
```bash
# Standard index performance check
python scripts/index_check.py --<repo>-specific
# Expected: All tests PASSED, no missing indexes
```

---

## 🧪 Standard-Teststrategie

### Unit Tests
```python
class Test<Repo>Repository:
    def test_crud_operations(self):
        # Create, Read, Update, Delete

    def test_filter_combinations(self):
        # All query filters work correctly

    def test_edge_cases(self):
        # Empty results, invalid inputs, constraints
```

### Contract Tests
```python
def test_repo_vs_legacy_results():
    # Same inputs → identical outputs
    legacy_result = legacy_service.get_items(query)
    repo_result = repository.query(query)
    assert normalize(legacy_result) == normalize(repo_result)
```

### Shadow Compare Tests
```python
def test_shadow_comparison_accuracy():
    # Verify shadow comparer detects differences correctly
    comparer.compare(result_a, result_b_different)
    assert comparer.stats["mismatches"] == 1
```

### Performance Tests
```python
def test_performance_slo():
    # Repository meets performance targets
    start = time.time()
    repository.query(complex_query)
    duration = time.time() - start
    assert duration < SLO_TARGET_SECONDS
```

### End-to-End Tests
```python
def test_cross_repo_consistency():
    # Full pipeline: Feed → Item → Analysis → Dashboard
    # Verify no data loss, consistent state
```

---

## 📂 Standard-Artefakte (pro Repository)

### Required Files
```
/docs/GO_LIVE_CHECKLIST_<repo>.md         # Repo-specific checklist
/scripts/go_live_check_<repo>.py          # Validation automation
/app/utils/<repo>_shadow_compare.py       # A/B testing framework
/app/repositories/<repo>_repo.py          # Repository implementation
/.github/workflows/<repo>-repo-check.yml  # CI enforcement
```

### Feature Flags
```bash
# Standard naming: <repo>_repo
# States: off, canary, on, emergency_off
```

### Pre-commit Hooks
```yaml
# In .pre-commit-config.yaml
- id: no-<repo>-raw-sql
  name: Prevent raw <repo> SQL outside Repository
  entry: scripts/check-<repo>-raw-sql.sh
```

### API Endpoints
```bash
# Admin Control
GET  /api/admin/feature-flags/<repo>_repo
POST /api/admin/feature-flags/<repo>_repo

# Monitoring
GET  /api/admin/feature-flags/metrics/<repo>-shadow-comparison
POST /api/admin/feature-flags/<repo>-shadow/reset
```

---

## 🚦 Universal Exit-Kriterien

### Technical Criteria (immer identisch)
- [ ] **Legacy Traffic = 0%**: 14 Tage nach Full-Cutover bestätigt
- [ ] **SLOs erfüllt**: P95, Error-Rate, Coverage (falls relevant)
- [ ] **CI-Checks aktiv**: Raw-SQL Prevention enforced
- [ ] **Shadow Compare deaktiviert**: CPU-Last reduziert
- [ ] **Legacy Code entfernt**: Keine Raw-SQL-Pfade mehr

### Process Criteria
- [ ] **Team Sign-Off**: Technical Lead, QA, DevOps, Product
- [ ] **Monitoring etabliert**: Dashboards, Alerts, Runbooks
- [ ] **Documentation aktuell**: CHANGELOG, README, Developer Setup
- [ ] **Lessons Learned dokumentiert**: Was lief gut, was verbessern

### Quality Gates
- [ ] **Zero Data Loss**: Verified durch Sample-Checks
- [ ] **Performance Regression**: <5% vs. optimierte Legacy
- [ ] **Cost Impact**: Within Budget (falls LLM/Cloud-Services)
- [ ] **User Impact**: No customer-facing issues

---

## 🔧 Repository-Specific Customization

### Read-Heavy Repositories (Items, Feeds)
- **Focus**: Query Performance, Index Optimization, Caching
- **SLO**: P95 < 100ms, P99 < 500ms
- **Shadow Compare**: Result set consistency, pagination stability

### Write-Heavy Repositories (Analysis, Ingestion)
- **Focus**: Worker Integration, Queue Management, Deferred Handling
- **SLO**: Processing Time <60s P95, Error Rate <5%
- **Shadow Compare**: Upsert consistency, status transitions

### Aggregation Repositories (Statistics, Reports)
- **Focus**: Calculation Accuracy, Time Window Consistency
- **SLO**: Calculation Correctness 100%, Freshness <5min
- **Shadow Compare**: Numerical accuracy, time-based filters

---

## 📊 Success Metrics Template

| **Repository** | **Type** | **P95 SLO** | **Error SLO** | **Coverage SLO** | **Status** |
|---------------|----------|-------------|---------------|------------------|------------|
| ItemsRepo     | Read     | <100ms      | <0.1%         | N/A              | ✅ Live     |
| AnalysisRepo  | Write    | <60s        | <5%           | >95% in 10min    | 🚀 Cutover  |
| FeedsRepo     | CRUD     | <200ms      | <0.5%         | N/A              | 📋 Planned  |
| StatsRepo     | Agg      | <2s         | <0.1%         | >98% fresh       | 📋 Planned  |

---

## 🎯 Team Adoption Guidelines

### Onboarding neuer Repositories
1. **Copy Template**: `cp docs/GO_LIVE_CHECKLIST_TEMPLATE.md docs/GO_LIVE_CHECKLIST_<repo>.md`
2. **Customize SLOs**: Repo-spezifische Performance/Error Targets
3. **Adapt Shadow Compare**: Domain-relevante Comparison Logic
4. **Configure CI**: Repository-spezifische Raw-SQL Patterns

### Review Process
- [ ] **Architecture Review**: Repository Design, Interface, Error Handling
- [ ] **Security Review**: SQL Injection Prevention, Data Access Controls
- [ ] **Performance Review**: Index Strategy, Query Plans, Caching
- [ ] **Operations Review**: Monitoring, Alerting, Runbook Completeness

### Knowledge Transfer
- [ ] **Runbook Documentation**: Operational Procedures
- [ ] **Troubleshooting Guide**: Common Issues, Debug Steps
- [ ] **Performance Tuning**: Optimization Strategies
- [ ] **Emergency Procedures**: Rollback, Data Recovery

---

## 🔍 Lessons Learned Integration

### ItemsRepo Learnings
- **Shadow Compare Sample Rate**: 10% optimal für Read-heavy Operations
- **Index Creation**: CONCURRENTLY vermeidet Deployment-Locks
- **Feature Flag Granularity**: Percentage-based Rollout sehr effektiv

### AnalysisRepo Learnings
- **Worker Integration**: Feature Flag Check alle 30s ausreichend
- **Deferred Queue**: Kritisch für LLM Rate Limiting
- **Run Consistency**: Status Transitions müssen atomic sein

### Universal Patterns
- **Early Index Creation**: Vor Repository-Implementation
- **Shadow Compare First**: Nie ohne A/B Testing in Production
- **Cleanup Discipline**: 14-Tage-Regel strikt einhalten

---

*Dieses Dokument ist der verbindliche Standard für alle Repository-Migrationen im News MCP Team. Bei Änderungen: Team-Review erforderlich.*