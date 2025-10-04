# News-MCP Refactoring Plan

**Version:** 1.0
**Created:** 2025-10-04
**Status:** Planning → Execution Ready

## Overview

This plan outlines the concrete, step-by-step execution strategy for cleaning up the News-MCP codebase based on findings in `CODEBASE_MAP.md` and policies in `CLEANUP_POLICY.md`.

---

## Execution Strategy

### Principles

1. **Small, Reversible Steps:** Each phase = 1 git commit, fully rollback-able
2. **No Regression:** System must work after every step
3. **Test First:** Manual smoke test before AND after each change
4. **Feature Flags:** For UI changes that users interact with
5. **Documentation:** Update CODEBASE_MAP.md after each phase

### Phase Sequence

```
Phase 1: Quick Wins (Dead Code Removal)        → 1-2 days
Phase 2: Template Refactoring                  → 3-5 days
Phase 3: Python Backend Refactoring            → 5-7 days
Phase 4: Service Layer Cleanup                 → 3-4 days
```

**Total Estimated Time:** 12-18 days

---

## Phase 1: Quick Wins (Dead Code Removal)

**Goal:** Remove unreferenced files without functional changes
**Risk:** ⚫ LOW (no code references)
**Estimated Time:** 1-2 days

### Step 1.1: Verification (Day 1, Morning)

**Action:** Double-check no references exist

```bash
# For each file in unreferenced list:
for file in \
  "templates/partials/analysis_additional_filters.html" \
  "templates/partials/analysis_settings.html" \
  "templates/partials/analysis_preview_start.html" \
  "templates/partials/analysis_active_runs.html" \
  "templates/partials/analysis_model_params.html" \
  "templates/partials/analysis_additional_settings.html" \
  "templates/partials/analysis_target_selection.html" \
  "templates/components/job_status_panel.html" \
  "templates/components/job_confirmation_modal.html" \
  "templates/admin/special_reports_old.html"; do

  name=$(basename "$file" .html)
  echo "=== Checking $name ==="
  grep -r "$name" app/ templates/ --include="*.py" --include="*.html" || echo "✓ Not referenced"
done
```

**Expected Outcome:** All files show "✓ Not referenced"

### Step 1.2: Move to Deprecated (Day 1, Afternoon)

**Action:** Create deprecated folder and move files

```bash
# Create deprecated directory
mkdir -p templates/_deprecated/2025-10-04

# Move files (one by one for safety)
mv templates/partials/analysis_additional_filters.html templates/_deprecated/2025-10-04/
mv templates/partials/analysis_settings.html templates/_deprecated/2025-10-04/
mv templates/partials/analysis_preview_start.html templates/_deprecated/2025-10-04/
mv templates/partials/analysis_active_runs.html templates/_deprecated/2025-10-04/
mv templates/partials/analysis_model_params.html templates/_deprecated/2025-10-04/
mv templates/partials/analysis_additional_settings.html templates/_deprecated/2025-10-04/
mv templates/partials/analysis_target_selection.html templates/_deprecated/2025-10-04/
mv templates/components/job_status_panel.html templates/_deprecated/2025-10-04/
mv templates/components/job_confirmation_modal.html templates/_deprecated/2025-10-04/
mv templates/admin/special_reports_old.html templates/_deprecated/2025-10-04/

# Git commit
git add templates/_deprecated/
git commit -m "Move unreferenced templates to deprecated (10 files, ~971 LOC)

Files moved for 14-day grace period before permanent deletion:
- partials/analysis_*.html (7 files)
- components/job_*.html (2 files)
- admin/special_reports_old.html (1 file)

Total: ~971 lines of dead code

Sunset: 2025-10-18 (if no 404s or issues)

🤖 Generated with [Claude Code](https://claude.com/claude-code)
Co-Authored-By: Claude <noreply@anthropic.com>"
```

### Step 1.3: Monitor Grace Period (Day 1-14)

**Action:** Watch logs for any 404s or import errors

```bash
# Check server logs daily
tail -f /var/log/news-mcp/app.log | grep "404\|FileNotFoundError"
```

**Expected Outcome:** No errors for 14 days

### Step 1.4: Permanent Deletion (Day 15)

**Action:** If grace period clean, delete permanently

```bash
rm -rf templates/_deprecated/2025-10-04/
git add templates/_deprecated/
git commit -m "Permanently delete unreferenced templates after 14-day grace period

No 404s or errors detected during grace period.

Deleted: 10 files, ~971 LOC

🤖 Generated with [Claude Code](https://claude.com/claude-code)
Co-Authored-By: Claude <noreply@anthropic.com>"
```

**Phase 1 Success Metrics:**
- ✅ -971 LOC
- ✅ 10 fewer files
- ✅ No 404 errors
- ✅ All tests pass

---

## Phase 2: Template Refactoring

**Goal:** Split large templates into components (like analysis_cockpit_v4 refactoring)
**Risk:** 🟡 MEDIUM (UI changes, needs testing)
**Estimated Time:** 3-5 days

### Target Files (Priority Order)

1. **analysis_manager.html** (720 LOC → 50 LOC + components)
2. **processors.html** (594 LOC → 60 LOC + components)
3. **database.html** (555 LOC → 60 LOC + components)
4. **statistics.html** (492 LOC → 60 LOC + components)

### Step 2.1: Refactor analysis_manager.html (Day 2-3)

**Pattern:** Follow analysis_cockpit_v4 refactoring

#### 2.1.1 Analyze Structure

```bash
# Read current file
wc -l templates/admin/analysis_manager.html  # Confirm 720 LOC

# Identify sections (manual review)
# Expected sections:
# - Stats dashboard (cards)
# - Active jobs table
# - Job history
# - Configuration form
# - JavaScript (Alpine.js logic)
# - CSS styles
```

#### 2.1.2 Create Component Structure

```bash
mkdir -p templates/admin/components/analysis_manager
mkdir -p templates/admin/scripts
mkdir -p templates/admin/styles
```

#### 2.1.3 Extract Components (one by one)

**Component Extraction Order:**
1. Extract CSS → `admin/styles/analysis_manager.css`
2. Extract JS → `admin/scripts/analysis_manager.js`
3. Extract Stats Cards → `admin/components/analysis_manager/stats_cards.html`
4. Extract Jobs Table → `admin/components/analysis_manager/jobs_table.html`
5. Extract History → `admin/components/analysis_manager/history.html`
6. Extract Config → `admin/components/analysis_manager/config_form.html`

**Per Component:**
```bash
# 1. Create component file
# 2. Copy relevant section (check line numbers with Read tool)
# 3. Remove leading whitespace
# 4. Verify no extra/missing </div>
# 5. Test in isolation (curl endpoint)
```

#### 2.1.4 Update Main Template

Replace with:
```jinja2
{% extends "base.html" %}

{% block title %}Analysis Manager - News MCP{% endblock %}

{% block extra_head %}
<script defer src="https://cdn.jsdelivr.net/npm/alpinejs@3.13.5/dist/cdn.min.js"></script>
{% include "admin/styles/analysis_manager.css" %}
{% endblock %}

{% block content %}
<div x-data="analysisManager()">
    <div class="row mb-2">
        <div class="col"><h1>Analysis Manager</h1></div>
    </div>

    <div class="row g-3 mb-3">
        <div class="col-12 col-lg-6">
            {% include "admin/components/analysis_manager/stats_cards.html" %}
        </div>
        <div class="col-12 col-lg-6">
            {% include "admin/components/analysis_manager/config_form.html" %}
        </div>
    </div>

    <div class="row g-3">
        <div class="col-12">
            {% include "admin/components/analysis_manager/jobs_table.html" %}
        </div>
    </div>

    <div class="row g-3">
        <div class="col-12">
            {% include "admin/components/analysis_manager/history.html" %}
        </div>
    </div>
</div>

{% include "admin/scripts/analysis_manager.js" %}
{% endblock %}
```

#### 2.1.5 Test Refactored Version

```bash
# 1. Restart server
./scripts/start-api.sh

# 2. Manual smoke test
# - Open http://192.168.178.72:8000/admin/analysis-manager
# - Verify all sections visible
# - Click buttons, test interactions
# - Check browser console for errors

# 3. Visual comparison
# - Screenshot before: analysis_manager_before.png
# - Screenshot after: analysis_manager_after.png
# - Compare side-by-side
```

#### 2.1.6 Commit

```bash
git add templates/admin/analysis_manager.html \
        templates/admin/components/analysis_manager/ \
        templates/admin/scripts/analysis_manager.js \
        templates/admin/styles/analysis_manager.css

git commit -m "Refactor analysis_manager.html (720 → 50 LOC + components)

Extracted components following analysis_cockpit_v4 pattern:
- Stats cards component (120 LOC)
- Jobs table component (180 LOC)
- History component (150 LOC)
- Config form component (100 LOC)
- JavaScript module (200 LOC)
- CSS styles (120 LOC)

Main template: 720 → 50 LOC (-93%)

Testing:
✅ Manual smoke test passed
✅ All buttons functional
✅ No console errors
✅ Visual regression: identical

🤖 Generated with [Claude Code](https://claude.com/claude-code)
Co-Authored-By: Claude <noreply@anthropic.com>"
```

**Repeat Steps 2.1.1 - 2.1.6 for:**
- processors.html (Day 3-4)
- database.html (Day 4-5)
- statistics.html (Day 5-6)

**Phase 2 Success Metrics:**
- ✅ 4 files refactored
- ✅ All < 300 LOC
- ✅ ~2,200 LOC → ~800 LOC (main files)
- ✅ All smoke tests pass
- ✅ Zero console errors

---

## Phase 3: Python Backend Refactoring

**Goal:** Split monolithic view/service files
**Risk:** 🔴 HIGH (backend logic, needs thorough testing)
**Estimated Time:** 5-7 days

### Target Files (Priority Order)

1. **feed_views.py** (1,150 LOC → 3 files × ~380 LOC)
2. **api/v1/analysis.py** (811 LOC → 3 files × ~270 LOC)
3. **feed_components.py** (790 LOC → 3 files × ~260 LOC)
4. **special_report_views.py** (756 LOC → 3 files × ~250 LOC)

### Step 3.1: Refactor feed_views.py (Day 7-9)

#### 3.1.1 Analyze Responsibilities

```bash
# Read file and identify logical groups
grep "^def\|^class" app/web/views/feed_views.py | head -30

# Expected groups:
# - CRUD operations (create, read, update, delete feeds)
# - Health monitoring (health checks, status updates)
# - Statistics (metrics, charts, reports)
```

#### 3.1.2 Create Target Files

```python
# app/web/views/feed_crud_views.py
# Handles: list_feeds, create_feed, update_feed, delete_feed

# app/web/views/feed_health_views.py
# Handles: health_dashboard, check_feed_health, update_status

# app/web/views/feed_stats_views.py
# Handles: feed_metrics, feed_charts, export_stats
```

#### 3.1.3 Extract & Move Functions

```bash
# 1. Create new files
touch app/web/views/feed_crud_views.py
touch app/web/views/feed_health_views.py
touch app/web/views/feed_stats_views.py

# 2. Copy relevant imports to each new file
# 3. Move functions one group at a time
# 4. Update imports in feed_views.py to re-export
```

**Migration Pattern:**
```python
# OLD: app/web/views/feed_views.py
def list_feeds():
    ...
def create_feed():
    ...

# NEW: app/web/views/feed_crud_views.py
def list_feeds():
    ...
def create_feed():
    ...

# COMPATIBILITY: app/web/views/feed_views.py
from .feed_crud_views import list_feeds, create_feed
from .feed_health_views import health_dashboard
from .feed_stats_views import feed_metrics

# This allows existing imports to work:
# from app.web.views.feed_views import list_feeds  # Still works!
```

#### 3.1.4 Test Split

```bash
# 1. Run Python tests
pytest app/tests/web/test_feed_views.py -v

# 2. Manual endpoint test
curl http://192.168.178.72:8000/admin/feeds  # List feeds
curl -X POST http://192.168.178.72:8000/admin/feeds  # Create feed

# 3. Check no import errors
python -c "from app.web.views.feed_views import list_feeds; print('OK')"
```

#### 3.1.5 Commit

```bash
git add app/web/views/feed_*.py

git commit -m "Split feed_views.py into CRUD/Health/Stats (1,150 → 3 files)

Extracted modules:
- feed_crud_views.py (380 LOC) - CRUD operations
- feed_health_views.py (350 LOC) - Health monitoring
- feed_stats_views.py (320 LOC) - Statistics & metrics

Main file now re-exports for compatibility.

Testing:
✅ pytest app/tests/web/test_feed_views.py (all pass)
✅ Manual endpoint tests (feeds CRUD)
✅ No import errors

🤖 Generated with [Claude Code](https://claude.com/claude-code)
Co-Authored-By: Claude <noreply@anthropic.com>"
```

**Repeat for:**
- api/v1/analysis.py (Day 9-11)
- feed_components.py (Day 11-12)
- special_report_views.py (Day 12-13)

**Phase 3 Success Metrics:**
- ✅ 4 large files split
- ✅ All files < 500 LOC
- ✅ All tests pass
- ✅ No import errors
- ✅ API endpoints functional

---

## Phase 4: Service Layer Cleanup

**Goal:** Split complex services
**Risk:** 🟡 MEDIUM (business logic, needs integration tests)
**Estimated Time:** 3-4 days

### Target Files

1. **metrics_service.py** (637 LOC → 2 files)
2. **analysis_orchestrator.py** (586 LOC → 2 files)

### Step 4.1: Split metrics_service.py (Day 14-15)

#### Split Strategy

```python
# metrics_service.py (637 LOC) →

# services/metrics/collector.py (320 LOC)
# - Metric collection logic
# - Data aggregation
# - Storage

# services/metrics/reporter.py (280 LOC)
# - Report generation
# - Export formats
# - Dashboards

# services/metrics_service.py (40 LOC - compatibility layer)
from .metrics.collector import MetricsCollector
from .metrics.reporter import MetricsReporter
```

### Step 4.2: Split analysis_orchestrator.py (Day 15-16)

#### Split Strategy

```python
# analysis_orchestrator.py (586 LOC) →

# services/analysis/orchestrator.py (300 LOC)
# - Main orchestration logic
# - Workflow coordination

# services/analysis/strategies.py (250 LOC)
# - Analysis strategies
# - Decision logic

# services/analysis_orchestrator.py (40 LOC - compatibility)
from .analysis.orchestrator import AnalysisOrchestrator
from .analysis.strategies import AnalysisStrategy
```

**Phase 4 Success Metrics:**
- ✅ 2 services split
- ✅ All < 500 LOC per file
- ✅ Integration tests pass
- ✅ No regressions in background jobs

---

## Rollback Procedures

### Per-Phase Rollback

```bash
# If issues discovered after commit:

# 1. Identify problem commit
git log --oneline | head -5

# 2. Revert commit
git revert <commit-hash>

# 3. Or hard reset (if not pushed)
git reset --hard HEAD~1

# 4. Verify system works
./scripts/start-api.sh
# Test affected endpoints
```

### Emergency Rollback (Complete)

```bash
# Restore from backup
cd /home/cytrex
tar -xzf news-mcp-backup-20251004-120046.tar.gz
cd news-mcp
./scripts/start-api.sh
```

---

## Progress Tracking

### Daily Checklist

- [ ] Start of day: Pull latest code, create branch
- [ ] Execute planned steps for the day
- [ ] Run tests after each change
- [ ] Commit with descriptive message
- [ ] Update CODEBASE_MAP.md with new metrics
- [ ] Push to remote
- [ ] Update this plan with actual vs. estimated time

### Weekly Review

**Every Friday:**
- Review KPIs in CLEANUP_POLICY.md
- Update CODEBASE_MAP.md metrics
- Document blockers/issues
- Adjust next week's plan if needed

---

## Dependencies & Blockers

### Prerequisites

- ✅ Backup created
- ✅ CODEBASE_MAP.md complete
- ✅ CLEANUP_POLICY.md approved
- ⏳ Team review of this plan

### Known Risks

1. **Breaking Changes:** Splitting Python files may break imports
   - **Mitigation:** Use re-export pattern for compatibility

2. **Visual Regressions:** Template refactoring may change layout
   - **Mitigation:** Screenshot comparisons, manual testing

3. **Performance:** Multiple small files vs. one large file
   - **Mitigation:** Profile before/after, acceptable if <10% degradation

---

## Success Criteria

### Phase Completion

Each phase is "Done" when:
- ✅ All planned files refactored
- ✅ All tests pass
- ✅ No console/server errors
- ✅ Manual smoke tests pass
- ✅ Git committed with descriptive message
- ✅ CODEBASE_MAP.md updated

### Overall Project Success

- ✅ 0 templates > 300 LOC
- ✅ ≤ 2 Python files > 500 LOC
- ✅ 0 unreferenced files
- ✅ All tests passing
- ✅ System stable (no new bugs)

---

**Next Actions:**
1. Review & approve this plan
2. Create feature branch: `refactor/cleanup-2025-10`
3. Execute Phase 1.1 (verification)

**Last Updated:** 2025-10-04
**Status:** ✅ Ready for Execution
