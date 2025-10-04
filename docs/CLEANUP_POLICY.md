# News-MCP Cleanup & Refactoring Policy

**Version:** 1.0
**Last Updated:** 2025-10-04
**Status:** Active

## Purpose

This document defines measurable policies, budgets, and conventions for maintaining code quality during the cleanup and refactoring phases.

---

## 1. File Size Budgets

### Templates (HTML/Jinja2)

| Type | Budget | Rationale | Enforcement |
|------|--------|-----------|-------------|
| UI Components | ≤ 300 LOC | Single responsibility, readability | Pre-commit hook (warning) |
| JavaScript Modules | ≤ 400 LOC | Maintainability, testability | Manual review |
| CSS/Styles | ≤ 300 LOC | Component-scoped styles | Manual review |
| Base Templates | ≤ 400 LOC | Layout-only, minimal logic | Manual review |

**Current Violations:**
- 8 files exceed 300 LOC (see CODEBASE_MAP.md)

**Target:** 0 violations by end of Phase 2

### Python Files

| Type | Budget | Rationale | Enforcement |
|------|--------|-----------|-------------|
| Views | ≤ 500 LOC | Single feature area | Pre-commit hook (warning) |
| Services | ≤ 500 LOC | Single responsibility | Manual review |
| Models | ≤ 400 LOC | Single entity + relationships | Manual review |
| Utils | ≤ 300 LOC | Single utility domain | Manual review |
| Routes/Controllers | ≤ 400 LOC | Single resource CRUD | Manual review |

**Current Violations:**
- 6 files exceed 500 LOC (see CODEBASE_MAP.md)

**Target:** ≤ 2 violations (complex orchestrators allowed)

---

## 2. Naming Conventions

### Files

| Pattern | Example | Purpose |
|---------|---------|---------|
| `*_old.html` | `special_reports_old.html` | Deprecated, scheduled for deletion |
| `*_v2.html` | `analysis_cockpit_v4.html` | Versioned iterative replacement |
| `*.backup` | Never commit | Local backups only |
| `*_temp.*` | Never commit | Temporary files |

### Components

| Pattern | Example | Scope |
|---------|---------|-------|
| `components/*.html` | `job_status_panel.html` | Reusable across features |
| `admin/partials/*.html` | `feed_detail.html` | Admin-specific partials |
| `analysis/components/*.html` | `target_selection.html` | Analysis-specific |

### Python Modules

| Pattern | Example | Purpose |
|---------|---------|---------|
| `*_views.py` | `feed_views.py` | Web UI route handlers |
| `*_service.py` | `metrics_service.py` | Business logic layer |
| `*_worker.py` | `analysis_worker.py` | Background tasks |
| `*_htmx.py` | `processors_htmx.py` | HTMX-specific endpoints |

---

## 3. Deprecation Policy

### Marking Deprecated Code

**Templates:**
```html
<!-- DEPRECATED: 2025-10-15 - Use analysis/components/target_selection.html instead -->
<!-- Sunset: 2025-11-01 -->
{% include "partials/analysis_target_selection.html" %}
```

**Python:**
```python
# DEPRECATED: 2025-10-15
# Replacement: services.metrics_service.MetricsCollector
# Sunset: 2025-11-01
def old_metrics_function():
    warnings.warn("Use MetricsCollector instead", DeprecationWarning)
    ...
```

### Sunset Timeline

| Type | Notice Period | Minimum Duration |
|------|---------------|------------------|
| Public API | 60 days | Must include 2 releases |
| Internal Views | 30 days | 1 release cycle |
| Templates | 14 days | Must verify no usage |
| Utilities | 30 days | Must have replacement |

### Tracking

All deprecations **MUST** be recorded in `DEPRECATIONS.md` with:
- File/function path
- Deprecation date
- Sunset date
- Replacement path
- Migration notes

---

## 4. Refactoring Standards

### When to Refactor (Triggers)

Refactor when **ANY** of these conditions are met:

1. **Size Violation:** File exceeds budget by >20%
2. **Complexity:** Cyclomatic complexity >15
3. **Duplication:** >3 instances of similar code blocks
4. **Change Frequency:** >5 edits in past sprint
5. **Bug Density:** >2 bugs per 100 LOC

### Refactoring Patterns

#### Template Splitting

**Before (720 LOC):**
```
admin/analysis_manager.html (all-in-one)
```

**After (<300 LOC):**
```
admin/analysis_manager.html (main - 50 LOC)
admin/components/analysis_stats.html
admin/components/analysis_runs.html
admin/components/analysis_jobs.html
admin/scripts/analysis_manager.js
admin/styles/analysis_manager.css
```

#### Python Class Splitting

**Before (1,150 LOC):**
```python
# web/views/feed_views.py
class FeedViews:
    def list_feeds()
    def create_feed()
    def edit_feed()
    def delete_feed()
    def feed_health()
    def feed_stats()
    ... (20+ methods)
```

**After (<500 LOC per file):**
```python
# web/views/feed_crud_views.py (300 LOC)
class FeedCRUDViews: ...

# web/views/feed_health_views.py (250 LOC)
class FeedHealthViews: ...

# web/views/feed_stats_views.py (200 LOC)
class FeedStatsViews: ...
```

---

## 5. Testing Requirements

### Pre-Refactor Checklist

- [ ] Current functionality documented
- [ ] Smoke tests defined (manual or automated)
- [ ] Rollback plan documented
- [ ] Feature flag created (if applicable)

### Post-Refactor Validation

- [ ] All smoke tests pass
- [ ] No new console errors (browser DevTools)
- [ ] No new Python warnings/errors
- [ ] Visual regression check (screenshot diff)
- [ ] Performance: No >10% degradation

### Minimum Test Coverage

| Change Type | Required Tests |
|-------------|---------------|
| Template split | Manual smoke test (load page, click buttons) |
| Python refactor | Unit tests for public methods |
| API change | Integration test for endpoint |
| Service split | Service-level tests |

---

## 6. Dead Code Identification

### Criteria for "Unreferenced"

A file is unreferenced if:

1. **Templates:** No `{% include %}`, `{% extends %}`, or `render_template()` calls
2. **Python:** No `import` statements from other active files
3. **Static Assets:** No references in templates/CSS/JS

### Verification Process

```bash
# Check if template is referenced
grep -r "template_name.html" app/ templates/ --include="*.py" --include="*.html"

# Check if Python module is imported
grep -r "from.*module_name import" app/ --include="*.py"
```

### Grace Period

Before deletion:
1. Move to `_deprecated/` directory
2. Wait 14 days
3. Monitor logs for 404s or import errors
4. If clean, permanently delete

---

## 7. Rollback Strategy

### Every refactoring MUST have:

1. **Backup:** Git commit before changes (`git tag refactor-backup-YYYYMMDD`)
2. **Feature Flag:** For UI changes
3. **Database Migration:** Reversible (with `downgrade()`)
4. **Rollback Script:** One-command revert

### Rollback Trigger Conditions

Rollback if:
- Critical path broken (500 errors, blank pages)
- >5 user-reported bugs within 24h
- Performance degradation >20%
- Data integrity issues

---

## 8. Communication & Ownership

### File Ownership

| Component | Owner | Backup |
|-----------|-------|--------|
| Admin UI | DevTeam | - |
| Analysis Features | DevTeam | - |
| Backend Services | DevTeam | - |
| Database Schema | DevTeam | - |

### Change Notifications

**Internal:**
- Slack/Discord: `#dev-changes` channel
- Weekly summary email

**External (if public API):**
- Changelog.md update
- Release notes
- Migration guide

---

## 9. Success Metrics (KPIs)

| Metric | Baseline (2025-10-04) | Target (2025-11-01) | Status |
|--------|----------------------|---------------------|--------|
| Templates > 300 LOC | 8 | 0 | 🔴 |
| Python > 500 LOC | 6 | 2 | 🔴 |
| Unreferenced files | 10 | 0 | 🟡 |
| Avg template size | 95 LOC | 80 LOC | 🟢 |
| Code duplication % | ? | <5% | - |
| Test coverage | ? | >70% | - |

**Review Frequency:** Weekly during cleanup phase

---

## 10. Enforcement

### Manual Review Gates

All PRs with refactoring **MUST** include:

1. **Checklist:** Pre/Post refactor items checked
2. **Size Report:** Before/after LOC counts
3. **Test Evidence:** Screenshot or test run output
4. **Migration Notes:** How to adapt dependent code (if any)

### Automated Checks (Future)

- Pre-commit hook: File size warnings
- CI pipeline: Test coverage enforcement
- PR bot: Auto-comment on size violations

---

**Approval:** Required for policy changes
**Next Review:** 2025-11-01
