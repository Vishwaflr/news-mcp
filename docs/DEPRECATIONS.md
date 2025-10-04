# News-MCP Deprecation Tracker

**Last Updated:** 2025-10-04
**Policy:** See CLEANUP_POLICY.md Section 3

## Active Deprecations

| Item | Type | Deprecated | Sunset | Replacement | Status | Notes |
|------|------|------------|--------|-------------|--------|-------|
| `templates/partials/analysis_additional_filters.html` | Template | 2025-10-04 | 2025-10-18 | analysis/components/ | 🟡 Grace Period | Moved to _deprecated/ |
| `templates/partials/analysis_settings.html` | Template | 2025-10-04 | 2025-10-18 | analysis/components/ | 🟡 Grace Period | Moved to _deprecated/ |
| `templates/partials/analysis_preview_start.html` | Template | 2025-10-04 | 2025-10-18 | analysis/components/ | 🟡 Grace Period | Moved to _deprecated/ |
| `templates/partials/analysis_active_runs.html` | Template | 2025-10-04 | 2025-10-18 | analysis/components/ | 🟡 Grace Period | Moved to _deprecated/ |
| `templates/partials/analysis_model_params.html` | Template | 2025-10-04 | 2025-10-18 | analysis/components/ | 🟡 Grace Period | Moved to _deprecated/ |
| `templates/partials/analysis_additional_settings.html` | Template | 2025-10-04 | 2025-10-18 | analysis/components/ | 🟡 Grace Period | Moved to _deprecated/ |
| `templates/partials/analysis_target_selection.html` | Template | 2025-10-04 | 2025-10-18 | analysis/components/target_selection.html | 🟡 Grace Period | Replaced in v4 refactor |
| `templates/components/job_status_panel.html` | Template | 2025-10-04 | 2025-10-18 | None | 🟡 Grace Period | No longer used |
| `templates/components/job_confirmation_modal.html` | Template | 2025-10-04 | 2025-10-18 | None | 🟡 Grace Period | No longer used |
| `templates/admin/special_reports_old.html` | Template | 2025-10-04 | 2025-10-18 | admin/special_reports.html | 🟡 Grace Period | Old version with "_old" suffix |

## Status Legend

| Icon | Status | Meaning |
|------|--------|---------|
| 🟢 | Announced | Deprecation notice added, still functional |
| 🟡 | Grace Period | Moved to _deprecated/, monitoring for errors |
| 🔴 | Sunset Due | Ready for permanent deletion |
| ✅ | Deleted | Permanently removed from codebase |

## Migration Guides

### Analysis Partials → Components

**Old Pattern:**
```jinja2
{% include "partials/analysis_target_selection.html" %}
```

**New Pattern:**
```jinja2
{% include "analysis/components/target_selection.html" %}
```

**Changes:**
- All analysis partials moved to `templates/analysis/components/`
- Cleaner separation of concerns
- Consistent naming (no more `analysis_` prefix redundancy)

### Special Reports (Old → New)

**Old:**
```jinja2
{% include "admin/special_reports_old.html" %}
```

**New:**
```jinja2
{% include "admin/special_reports.html" %}
```

**Changes:**
- Improved form validation
- Better HTMX integration
- Cleaner UI layout

---

## Historical Deprecations (Completed)

| Item | Deprecated | Deleted | Reason |
|------|------------|---------|--------|
| _(none yet)_ | - | - | - |

---

## Planned Deprecations (Future)

### Phase 2: Template Refactoring

After refactoring large templates, the following **main templates** will be deprecated:

| Item | Planned Deprecation | Sunset | Replacement |
|------|-------------------|--------|-------------|
| `templates/admin/analysis_manager.html` (720 LOC) | Phase 2 | TBD | Refactored version with components |
| `templates/admin/processors.html` (594 LOC) | Phase 2 | TBD | Refactored version with components |
| `templates/admin/database.html` (555 LOC) | Phase 2 | TBD | Refactored version with components |
| `templates/admin/statistics.html` (492 LOC) | Phase 2 | TBD | Refactored version with components |

**Note:** These won't be "deprecated" in the traditional sense - they'll be refactored in-place. But the old versions will be backed up before refactoring.

### Phase 3: Python Backend

After splitting large Python files, the following **monolithic files** will maintain compatibility layers:

| Item | Planned Split | Compatibility Layer Until |
|------|--------------|---------------------------|
| `app/web/views/feed_views.py` (1,150 LOC) | Phase 3 | 2025-12-01 (re-exports) |
| `app/api/v1/analysis.py` (811 LOC) | Phase 3 | 2025-12-01 (re-exports) |
| `app/web/components/feed_components.py` (790 LOC) | Phase 3 | 2025-12-01 (re-exports) |
| `app/web/views/special_report_views.py` (756 LOC) | Phase 3 | 2025-12-01 (re-exports) |

---

## Monitoring

### Grace Period Checks

During the 14-day grace period for each deprecated file:

**Daily:**
```bash
# Check server logs for 404s
grep "404\|FileNotFoundError" /var/log/news-mcp/app.log | grep "analysis_"

# Check for unexpected errors
grep "ERROR" /var/log/news-mcp/app.log | tail -20
```

**Weekly:**
```bash
# Confirm no references in new code
for file in templates/_deprecated/2025-10-04/*; do
  name=$(basename "$file" .html)
  grep -r "$name" app/ templates/ --include="*.py" --include="*.html" && echo "⚠️  Found reference!" || echo "✓ Clean"
done
```

---

## Deletion Checklist

Before permanently deleting a deprecated item:

- [ ] Grace period completed (14+ days for templates, 30+ days for code)
- [ ] Zero 404 errors in logs
- [ ] Zero import errors
- [ ] No references in codebase (`grep` check)
- [ ] Backup exists (git history + tarball)
- [ ] Team notified (if applicable)

**Permanent Deletion Command:**
```bash
# After all checks pass:
rm -rf templates/_deprecated/YYYY-MM-DD/
git add templates/_deprecated/
git commit -m "Permanently delete deprecated templates from YYYY-MM-DD (grace period clean)"
```

---

## Communication

### Internal Notifications

**Slack/Discord:**
- Post in `#dev-changes` when deprecation announced
- Reminder 7 days before sunset
- Confirmation when deleted

**Email:**
- Weekly summary of active deprecations
- Sunset reminders

---

## Metrics

### Current Status (2025-10-04)

| Metric | Count |
|--------|-------|
| Active Deprecations | 10 |
| In Grace Period | 10 |
| Sunset Due | 0 |
| Deleted (Lifetime) | 0 |

### Target (2025-10-18)

| Metric | Count |
|--------|-------|
| Active Deprecations | 0 |
| Deleted (Lifetime) | 10 |

---

**Next Review:** 2025-10-11 (weekly)
**Owner:** Development Team
