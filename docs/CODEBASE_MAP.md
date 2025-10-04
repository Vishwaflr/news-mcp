# News-MCP Codebase Map

**Generated:** 2025-10-04
**Purpose:** Discover phase - Inventory of all major files, sizes, last changes, and refactoring recommendations

## Executive Summary

**Templates:** 7,624 total lines across all templates
**Unreferenced Templates:** 10 files (potential for deletion)
**Large Files (>300 LOC):** 8 templates, 15 Python files
**Budget Violations (>500 LOC):** 3 templates, 6 Python files

---

## 1. Templates Inventory

### Top 10 Largest Templates (Refactoring Candidates)

| File | Lines | Last Modified | Component | Status | Recommendation |
|------|-------|---------------|-----------|--------|----------------|
| admin/analysis_manager.html | 720 | 2025-10-04 | Admin/Analysis | 🔴 CRITICAL | **SPLIT** into components (like analysis_cockpit_v4) |
| admin/processors.html | 594 | 2025-10-04 | Admin/Processors | 🔴 CRITICAL | **SPLIT** into components + extract JS |
| admin/database.html | 555 | 2025-10-04 | Admin/Database | 🔴 CRITICAL | **SPLIT** into components |
| analysis/scripts.html | 493 | 2025-10-04 | Analysis/JS | 🟡 WARNING | **MODULARIZE** JS into separate files |
| admin/statistics.html | 492 | 2025-10-04 | Admin/Stats | 🟡 WARNING | **SPLIT** into components |
| admin/special_report_edit.html | 489 | 2025-10-04 | Admin/Reports | 🟡 WARNING | **SPLIT** form sections |
| admin/feeds.html | 444 | 2025-10-04 | Admin/Feeds | 🟡 WARNING | **EXTRACT** feed table component |
| admin/partials/feed_detail.html | 360 | 2025-10-04 | Admin/Feeds | 🟢 OK | Consider splitting if grows |
| index.html | 335 | 2025-10-04 | Dashboard | 🟢 OK | Keep as-is |
| base.html | 314 | 2025-10-04 | Shared/Layout | 🟢 OK | Keep as-is |

### Unreferenced Templates (Dead Code - Safe to Delete)

| File | Lines | Last Modified | Reason |
|------|-------|---------------|--------|
| partials/analysis_additional_filters.html | ? | ? | No references in code |
| partials/analysis_settings.html | ? | ? | No references in code |
| partials/analysis_preview_start.html | ? | ? | No references in code |
| partials/analysis_active_runs.html | ? | ? | No references in code |
| partials/analysis_model_params.html | ? | ? | No references in code |
| partials/analysis_additional_settings.html | ? | ? | No references in code |
| partials/analysis_target_selection.html | 129 | 2025-09-26 | **OLD VERSION** - replaced by analysis/components/ |
| components/job_status_panel.html | ? | ? | No references in code |
| components/job_confirmation_modal.html | 184 | 2025-09-26 | No references in code |
| admin/special_reports_old.html | 232 | 2025-09-18 | **OLD** - suffix indicates deprecated |

**Estimated cleanup:** ~1,000 lines of dead code

---

## 2. Python Backend Inventory

### Top 15 Largest Python Files

| File | Lines | Component | Status | Recommendation |
|------|-------|-----------|--------|----------------|
| web/views/feed_views.py | 1,150 | Web/Feeds | 🔴 CRITICAL | **SPLIT** - extract to multiple view classes |
| api/v1/analysis.py | 811 | API/Analysis | 🔴 CRITICAL | **SPLIT** by endpoint groups |
| web/components/feed_components.py | 790 | Web/Feeds | 🔴 CRITICAL | **SPLIT** - extract separate components |
| web/views/special_report_views.py | 756 | Web/Reports | 🔴 CRITICAL | **SPLIT** by CRUD operations |
| services/metrics_service.py | 637 | Services/Metrics | 🔴 CRITICAL | **SPLIT** - separate metric types |
| services/analysis_orchestrator.py | 586 | Services/Analysis | 🔴 CRITICAL | **SPLIT** - extract strategies |
| web/views/system_views.py | 549 | Web/Admin | 🟡 WARNING | Extract database/stats to separate files |
| utils/feeds_shadow_compare.py | 515 | Utils/Feeds | 🟡 WARNING | Move to services/ and split |
| routes/processors_htmx.py | 512 | Routes/HTMX | 🟡 WARNING | Extract to view components |
| api/analysis_control.py | 509 | API/Analysis | 🟡 WARNING | Merge with api/v1/analysis.py or split |
| core/resilience.py | 490 | Core | 🟢 OK | Single responsibility - keep |
| services/feed_limits_service.py | 487 | Services/Feeds | 🟢 OK | Single responsibility - keep |
| worker/content_generator_worker.py | 481 | Worker/Reports | 🟢 OK | Single responsibility - keep |
| services/dynamic_template_manager.py | 481 | Services/Templates | 🟢 OK | Single responsibility - keep |
| services/error_recovery.py | 480 | Services/Errors | 🟢 OK | Single responsibility - keep |

---

## 3. Component Ownership Map

### Admin Interface (Web UI)

| Route | Template | View | Lines (Template) | Lines (View) | Owner | Status |
|-------|----------|------|------------------|--------------|-------|--------|
| /admin/analysis | analysis_cockpit_v4.html | system_views.py | 46 | - | ✅ REFACTORED | 🟢 GOOD |
| /admin/analysis-manager | analysis_manager.html | system_views.py | 720 | 549 | ❌ NEEDS REFACTOR | 🔴 CRITICAL |
| /admin/feeds | feeds.html | feed_views.py | 444 | 1,150 | ❌ NEEDS REFACTOR | 🔴 CRITICAL |
| /admin/database | database.html | system_views.py | 555 | 549 | ❌ NEEDS REFACTOR | 🔴 CRITICAL |
| /admin/processors | processors.html | processors_htmx.py | 594 | 512 | ❌ NEEDS REFACTOR | 🔴 CRITICAL |
| /admin/statistics | statistics.html | system_views.py | 492 | 549 | ❌ NEEDS REFACTOR | 🟡 WARNING |
| /admin/special-reports | special_reports.html | special_report_views.py | 162 | 756 | ❌ NEEDS REFACTOR | 🟡 WARNING |

### API Endpoints

| Endpoint Group | File | Lines | Status |
|----------------|------|-------|--------|
| /api/v1/analysis/* | api/v1/analysis.py | 811 | 🔴 CRITICAL - Too large |
| /api/analysis/* | api/analysis_control.py | 509 | 🟡 Potential duplicate with v1? |

### Background Services

| Service | File | Lines | Status |
|---------|------|-------|--------|
| Feed Fetcher | services/feed_fetcher.py | ? | 🟢 OK |
| Analysis Worker | worker/analysis_worker.py | ? | 🟢 OK |
| Metrics | services/metrics_service.py | 637 | 🔴 CRITICAL - Split |
| Orchestrator | services/analysis_orchestrator.py | 586 | 🔴 CRITICAL - Split |

---

## 4. Quick Wins (Immediate Actions)

### A. Delete Unreferenced Templates (Low Risk)

```bash
# Safe to delete (10 files, ~1,000 lines):
rm templates/partials/analysis_additional_filters.html
rm templates/partials/analysis_settings.html
rm templates/partials/analysis_preview_start.html
rm templates/partials/analysis_active_runs.html
rm templates/partials/analysis_model_params.html
rm templates/partials/analysis_additional_settings.html
rm templates/partials/analysis_target_selection.html
rm templates/components/job_status_panel.html
rm templates/components/job_confirmation_modal.html
rm templates/admin/special_reports_old.html
```

**Impact:** -1,000 LOC, improved clarity, no functional change

### B. Refactor Top 3 Critical Templates (Medium Risk)

1. **analysis_manager.html (720 LOC) → Target: <300 LOC**
   - Extract: stats cards, active runs, job history
   - Pattern: Same as analysis_cockpit_v4 refactoring
   - Estimated: 720 → 50 LOC main + 7 components

2. **processors.html (594 LOC) → Target: <300 LOC**
   - Extract: processor table, config forms, status cards
   - Estimated: 594 → 60 LOC main + 5 components

3. **database.html (555 LOC) → Target: <300 LOC**
   - Extract: table views, query builder, stats
   - Estimated: 555 → 60 LOC main + 4 components

### C. Split Top 2 Critical Python Files (Higher Risk)

1. **feed_views.py (1,150 LOC) → Target: <400 LOC per file**
   - Split into: feed_list_views.py, feed_edit_views.py, feed_health_views.py
   - Estimated: 1,150 → 3 files × ~380 LOC

2. **api/v1/analysis.py (811 LOC) → Target: <400 LOC per file**
   - Split into: analysis_crud.py, analysis_runs.py, analysis_jobs.py
   - Estimated: 811 → 3 files × ~270 LOC

---

## 5. Size Budgets (Targets)

| Type | Budget | Current Violations | Target |
|------|--------|-------------------|--------|
| UI Templates | ≤ 300 LOC | 8 files | 0 violations |
| JS/CSS Files | ≤ 400 LOC | 1 file (scripts.html: 493) | 0 violations |
| Python Views | ≤ 500 LOC | 6 files | ≤ 2 files |
| Python Services | ≤ 500 LOC | 2 files | 0 violations |

---

## 6. Refactoring Priority Matrix

### Phase 1: Quick Wins (1-2 days)
- ✅ Delete 10 unreferenced templates
- ✅ Extract `special_reports_old.html` confirmation before delete

### Phase 2: Template Refactoring (3-5 days)
1. analysis_manager.html (720 → 50 + components)
2. processors.html (594 → 60 + components)
3. database.html (555 → 60 + components)
4. statistics.html (492 → 60 + components)

### Phase 3: Python Backend Refactoring (5-7 days)
1. feed_views.py (1,150 → 3 files)
2. api/v1/analysis.py (811 → 3 files)
3. web/components/feed_components.py (790 → 3 files)
4. special_report_views.py (756 → 3 files)

### Phase 4: Service Layer Cleanup (3-4 days)
1. metrics_service.py (637 → 2-3 files)
2. analysis_orchestrator.py (586 → 2-3 files)

---

## 7. Success Metrics

| Metric | Current | Target | Status |
|--------|---------|--------|--------|
| Templates > 300 LOC | 8 | 0 | 🔴 |
| Python files > 500 LOC | 6 | 2 | 🔴 |
| Unreferenced files | 10 | 0 | 🟡 (can delete now) |
| Total template LOC | 7,624 | 6,000 | 🟡 |
| Largest template | 720 | 300 | 🔴 |
| Largest Python file | 1,150 | 500 | 🔴 |

---

## 8. Next Steps

1. **Review & Approve** this map with stakeholders
2. **Execute Phase 1** (Quick Wins) - delete unreferenced files
3. **Create REFACTOR_PLAN.md** with detailed steps for Phases 2-4
4. **Create DEPRECATIONS.md** for sunset tracking
5. **Set up Feature Flags** for safe rollouts

---

**Last Updated:** 2025-10-04
**Maintained By:** Development Team
**Review Frequency:** Weekly during cleanup, Monthly after
