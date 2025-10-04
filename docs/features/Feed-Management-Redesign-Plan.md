# Feed Management Redesign - Implementation Plan

## Overview
Complete redesign of the Feed Management UI with 2-column layout (list + detail panel), health scoring, advanced analytics, and comprehensive search/filter functionality.

---

## Phase 1: Foundation & Data Layer (2-3 hours)

### 1.1 Database Schema Extensions
**Goal:** Add missing columns for health scoring and analytics

**Tasks:**
- [ ] Add `health_score` (INTEGER 0-100) to `feeds` table
- [ ] Add `last_error_message` (TEXT) to `feeds` table
- [ ] Add `last_error_at` (TIMESTAMP) to `feeds` table
- [ ] Add `total_articles` (INTEGER) to `feeds` table
- [ ] Add `articles_24h` (INTEGER) to `feeds` table
- [ ] Add `analyzed_count` (INTEGER) to `feeds` table
- [ ] Add `analyzed_percentage` (FLOAT) to `feeds` table
- [ ] Create migration script: `migrations/add_feed_analytics_columns.sql`

**Files:**
- `app/models/core.py` (update Feed model)
- `migrations/add_feed_analytics_columns.sql`

**Verification:**
```sql
-- Check new columns exist
\d feeds
SELECT health_score, last_error_message, total_articles FROM feeds LIMIT 1;
```

---

### 1.2 Health Score Service
**Goal:** Implement health score calculation logic

**Algorithm:**
```
Health Score (0-100) =
  Reachability (30%) +
  Volume (25%) +
  Duplicate Rate (15%) +
  Content Quality (15%) +
  Stability (15%)
```

**Tasks:**
- [ ] Create `app/services/feed_health_service.py`
- [ ] Implement `calculate_health_score(feed_id)` function
- [ ] Implement `update_all_health_scores()` background job
- [ ] Add health score to Feed API response schema

**Files:**
- `app/services/feed_health_service.py` (NEW)
- `app/api/feeds.py` (update response schema)

**Verification:**
```bash
curl http://192.168.178.72:8000/api/feeds/1 | jq '.health_score'
```

---

### 1.3 Analytics Aggregation Service
**Goal:** Calculate analyzed %, sentiment breakdown, article counts

**Tasks:**
- [ ] Create `app/services/feed_analytics_service.py`
- [ ] Implement `get_feed_analytics(feed_id)` returning:
  - total_articles
  - articles_24h
  - analyzed_count
  - analyzed_percentage
  - sentiment_breakdown (positive/negative/neutral counts)
- [ ] Add caching (15 min TTL)
- [ ] Create background job to update analytics hourly

**Files:**
- `app/services/feed_analytics_service.py` (NEW)
- `app/api/feeds.py` (add `/feeds/{id}/analytics` endpoint)

**Verification:**
```bash
curl http://192.168.178.72:8000/api/feeds/1/analytics | jq
```

---

## Phase 2: Backend API Extensions (2-3 hours)

### 2.1 Enhanced Feed List Endpoint
**Goal:** Support search, filter, sort with analytics data

**Tasks:**
- [ ] Update `GET /api/feeds/` to accept query params:
  - `search` (name/url/source_label)
  - `status` (active/inactive/error)
  - `category_id` (filter by category)
  - `sort_by` (health_score/last_fetch/total_articles/name)
  - `sort_order` (asc/desc)
- [ ] Include analytics in list response (health_score, total_articles, analyzed_%)
- [ ] Add pagination (limit/offset)

**Files:**
- `app/api/feeds.py` (update GET /api/feeds/)
- `app/services/domain/feed_service.py` (add filter logic)

**Verification:**
```bash
# Test search
curl "http://192.168.178.72:8000/api/feeds/?search=heise"

# Test filter
curl "http://192.168.178.72:8000/api/feeds/?status=active&sort_by=health_score"

# Test category filter
curl "http://192.168.178.72:8000/api/feeds/?category_id=2"
```

---

### 2.2 Feed Detail Endpoint
**Goal:** Comprehensive feed details for right panel

**Tasks:**
- [ ] Create `GET /api/feeds/{id}/details` returning:
  - Basic info (name, url, status, interval, categories)
  - Health score + breakdown
  - Analytics (articles, analyzed %, sentiment)
  - Last 5 fetches (from fetch_log)
  - Last error details
  - Last 3 articles preview
  - Configuration (auto-deactivate policy, retry strategy)

**Files:**
- `app/api/feeds.py` (add GET /api/feeds/{id}/details)

**Verification:**
```bash
curl http://192.168.178.72:8000/api/feeds/1/details | jq
```

---

### 2.3 Bulk Actions Endpoints
**Goal:** Support Refresh All, Health Check, Bulk Import

**Tasks:**
- [ ] Create `POST /api/feeds/bulk/refresh` (queues fetch for all active feeds)
- [ ] Create `POST /api/feeds/bulk/health-check` (runs health check without fetch)
- [ ] Create `POST /api/feeds/bulk/import` (CSV/JSON import)
- [ ] Add response: `{success: [], failed: [], skipped: []}`

**Files:**
- `app/api/feeds.py` (add bulk endpoints)
- `app/services/domain/feed_service.py` (add bulk methods)

**Verification:**
```bash
# Refresh all
curl -X POST http://192.168.178.72:8000/api/feeds/bulk/refresh

# Health check
curl -X POST http://192.168.178.72:8000/api/feeds/bulk/health-check

# Bulk import
curl -X POST http://192.168.178.72:8000/api/feeds/bulk/import \
  -H "Content-Type: application/json" \
  -d '{"feeds": [{"url": "...", "name": "..."}]}'
```

---

## Phase 3: Frontend - Layout & Structure (3-4 hours)

### 3.1 New Base Template
**Goal:** 2-column layout with responsive design

**Layout:**
```
┌─────────────────────────────────────────────┐
│ Header: Title + Global Search + Stats      │
├──────────────────┬──────────────────────────┤
│                  │                          │
│  Feed List       │  Detail Panel            │
│  (60% width)     │  (40% width)             │
│                  │                          │
│  - Filter Chips  │  - Overview              │
│  - Feed Cards    │  - Activity              │
│  - Pagination    │  - Quality               │
│                  │  - Configuration         │
│                  │  - Diagnostics           │
│                  │  - Preview               │
│                  │                          │
├──────────────────┴──────────────────────────┤
│ Quick Actions: Add | Refresh All | Health  │
└─────────────────────────────────────────────┘
```

**Tasks:**
- [ ] Create `templates/admin/feeds_v2.html` (new template)
- [ ] Add 2-column flexbox/grid layout
- [ ] Add global stats header (Total/Active/Inactive/Error counts)
- [ ] Add global search input (debounced)
- [ ] Add filter chips container (status/category tabs)
- [ ] Add quick actions footer (sticky)

**Files:**
- `templates/admin/feeds_v2.html` (NEW)
- `static/css/feeds-v2.css` (NEW)
- `app/web/views/feed_views.py` (add route for /admin/feeds-v2)

**Verification:**
- Navigate to `http://192.168.178.72:8000/admin/feeds-v2`
- Check layout renders correctly (2 columns, responsive)

---

### 3.2 Feed List Component
**Goal:** Card-based feed list with status badges and analytics

**Card Structure:**
```
┌────────────────────────────────────────┐
│ ● ACTIVE  [Security] [Auto]            │
│ Heise Security News                    │
│ https://heise.de/security/rss          │
│ Source: Heise · Interval: 15 min       │
│                                        │
│ 📊 202 Articles · 183 Analyzed (90%)   │
│ 😊 150  😐 20  😞 13                   │
│ Health: ████████░░ 85/100              │
│                                        │
│ Last Fetch: 2 min ago                  │
│ Last Article: 5 min ago                │
│                                        │
│ [🔍] [✏️] [▶️] [💾] [🔌] [🗑️]        │
└────────────────────────────────────────┘
```

**Tasks:**
- [ ] Create `templates/components/feed_card_v2.html` (Jinja partial)
- [ ] Add status badge (ACTIVE=green, INACTIVE=gray, ERROR=red)
- [ ] Add category badges (colored chips)
- [ ] Add auto/manual badge
- [ ] Add analytics chips (articles, analyzed %, sentiment)
- [ ] Add health bar (colored 0-49=red, 50-79=yellow, 80-100=green)
- [ ] Add action buttons (6 icons)
- [ ] Add click handler to select feed

**Files:**
- `templates/components/feed_card_v2.html` (NEW)
- `app/web/components/feed_components_v2.py` (NEW - render logic)

**HTMX Endpoints:**
- `GET /htmx/feeds-list-v2?search=&status=&category_id=&sort_by=` (returns list of cards)

**Verification:**
```bash
curl "http://192.168.178.72:8000/htmx/feeds-list-v2" | grep "feed-card"
```

---

### 3.3 Detail Panel Component
**Goal:** 6-section accordion/tabs with comprehensive feed info

**Sections:**
1. **Overview** - Name, URL, Status, Health Score, Last Error
2. **Activity** - Sparklines, Last 5 Fetches table
3. **Quality** - Analyzed %, Sentiment chart, Top Topics
4. **Configuration** - Edit form (inline or modal)
5. **Diagnostics** - robots.txt, Redirects, Encoding, Last Error
6. **Preview** - Last 3 articles (title, date, link)

**Tasks:**
- [ ] Create `templates/components/feed_detail_panel.html` (NEW)
- [ ] Implement 6 accordion sections
- [ ] Add loading skeleton for async data
- [ ] Add "No feed selected" empty state

**Files:**
- `templates/components/feed_detail_panel.html` (NEW)
- `app/web/components/feed_components_v2.py` (add render_detail_panel)

**HTMX Endpoints:**
- `GET /htmx/feed-detail/{id}` (returns full detail panel HTML)
- `GET /htmx/feed-detail/{id}/section/{section_name}` (lazy load sections)

**Verification:**
```bash
curl http://192.168.178.72:8000/htmx/feed-detail/1 | grep "Overview"
```

---

## Phase 4: Search & Filter (1-2 hours)

### 4.1 Global Search Implementation
**Goal:** Real-time search with debouncing

**Tasks:**
- [ ] Add search input with Alpine.js debounce (300ms)
- [ ] HTMX trigger on input change
- [ ] Highlight search terms in results
- [ ] Show "No results" state

**Files:**
- `templates/admin/feeds_v2.html` (search input)
- Update `GET /htmx/feeds-list-v2` to use search param

**JavaScript:**
```html
<input
  type="text"
  x-data="{ search: '' }"
  x-model="search"
  @input.debounce.300ms="htmx.trigger('#feed-list', 'refresh')"
  hx-get="/htmx/feeds-list-v2"
  hx-target="#feed-list"
  hx-include="[name='search']"
>
```

**Verification:**
- Type "heise" in search → see filtered results
- Clear search → see all feeds

---

### 4.2 Filter Chips (Status/Category)
**Goal:** Clickable filter tabs

**Design:**
```
[All (45)] [Active (30)] [Inactive (10)] [Error (5)]
[Security] [Finance] [Tech] [+2 more]
```

**Tasks:**
- [ ] Create filter chip component
- [ ] Add active state styling
- [ ] HTMX trigger on click
- [ ] Show counts in badges

**Files:**
- `templates/components/filter_chips.html` (NEW)

**HTMX:**
```html
<button
  class="filter-chip"
  hx-get="/htmx/feeds-list-v2?status=active"
  hx-target="#feed-list"
>
  Active (30)
</button>
```

**Verification:**
- Click "Active" → see only active feeds
- Click "Error" → see only error feeds

---

### 4.3 Sort Dropdown
**Goal:** Sort by health_score, last_fetch, total_articles, name

**Tasks:**
- [ ] Add sort dropdown
- [ ] HTMX trigger on change
- [ ] Add asc/desc toggle

**Files:**
- `templates/admin/feeds_v2.html` (sort dropdown)

**Verification:**
- Sort by "Health Score" → lowest first
- Toggle to "Health Score ↓" → highest first

---

## Phase 5: Modals & Forms (2-3 hours)

### 5.1 Add Feed Modal
**Goal:** Clean form to add new feed

**Fields:**
- URL (required, validated)
- Name (optional, auto-filled from feed)
- Source Label (optional)
- Categories (multi-select)
- Interval (dropdown: 15/30/60 min)
- Active (toggle, default ON)

**Tasks:**
- [ ] Create `templates/modals/add_feed_modal.html`
- [ ] Add form validation (URL format, duplicate check)
- [ ] Add "Test Fetch" button (preview feed before save)
- [ ] HTMX POST to `/api/feeds/`

**Files:**
- `templates/modals/add_feed_modal.html` (NEW)

**Verification:**
- Click "Add Feed" → modal opens
- Enter URL → "Test Fetch" → shows preview
- Click "Save" → feed added to list

---

### 5.2 Edit Feed Modal
**Goal:** Edit existing feed

**Tasks:**
- [ ] Create `templates/modals/edit_feed_modal.html`
- [ ] Pre-fill form with current values
- [ ] Add "Save & Test" button
- [ ] HTMX PUT to `/api/feeds/{id}`

**Files:**
- `templates/modals/edit_feed_modal.html` (NEW)

**Verification:**
- Click edit icon on feed → modal opens with data
- Change interval → Save → see update in list

---

### 5.3 Bulk Import Modal
**Goal:** CSV/JSON import with validation

**Format:**
```csv
url,name,source_label,category,interval,active
https://...,Feed 1,Source 1,Security,15,true
```

**Tasks:**
- [ ] Create `templates/modals/bulk_import_modal.html`
- [ ] Add file upload or textarea input
- [ ] Parse CSV/JSON
- [ ] Show preview table (what will be imported)
- [ ] HTMX POST to `/api/feeds/bulk/import`
- [ ] Show results: Imported/Skipped/Failed

**Files:**
- `templates/modals/bulk_import_modal.html` (NEW)

**Verification:**
- Click "Bulk Import" → upload CSV → see preview
- Click "Import" → see success/error counts

---

### 5.4 Health Report Modal
**Goal:** Summary of all feeds with health issues

**Design:**
```
Feed Health Report
──────────────────
Overall Health: 78/100

Issues Found (5):
────────────────
🔴 Heise News (45/100)
   - Last fetch failed: 403 Forbidden
   - No articles in 24h

🟡 TechCrunch (62/100)
   - Duplicate rate high (40%)

[Export Report] [Close]
```

**Tasks:**
- [ ] Create `templates/modals/health_report_modal.html`
- [ ] Calculate overall health average
- [ ] Group by severity (critical/warning/ok)
- [ ] Add "Export Report" (CSV)

**Files:**
- `templates/modals/health_report_modal.html` (NEW)

**Verification:**
- Click "Health Check" → see report modal
- Export report → download CSV

---

### 5.5 Delete Confirm Modal
**Goal:** Safe deletion with type-to-confirm

**Tasks:**
- [ ] Create `templates/modals/delete_feed_modal.html`
- [ ] Require user to type feed name
- [ ] Show warning about articles/analyses
- [ ] HTMX DELETE to `/api/feeds/{id}`

**Files:**
- `templates/modals/delete_feed_modal.html` (NEW)

**Verification:**
- Click delete → type feed name → confirm → feed deleted

---

## Phase 6: Quick Actions & Polish (1-2 hours)

### 6.1 Quick Actions Bar
**Goal:** Sticky footer with 3 main actions

**Buttons:**
- [ ] **Add New Feed** → Opens add modal
- [ ] **Refresh All** → Queues fetch for all active feeds
- [ ] **Health Check** → Opens health report modal

**Tasks:**
- [ ] Create sticky footer component
- [ ] Add loading states for bulk actions
- [ ] Add success/error toasts

**Files:**
- `templates/admin/feeds_v2.html` (add footer)

**Verification:**
- Click "Refresh All" → see toast "45 feeds queued"
- Click "Health Check" → see health report modal

---

### 6.2 Empty States
**Goal:** Helpful messages when no data

**States:**
- [ ] No feeds exist → "Add your first feed"
- [ ] No search results → "No feeds match 'xyz'"
- [ ] No feed selected → "Select a feed to view details"

**Files:**
- `templates/components/empty_states.html` (NEW)

---

### 6.3 Loading States
**Goal:** Skeleton loaders and spinners

**Tasks:**
- [ ] Add skeleton cards for feed list loading
- [ ] Add spinner for detail panel loading
- [ ] Add progress bar for bulk actions

**Files:**
- `static/css/feeds-v2.css` (skeleton styles)

---

### 6.4 Error Handling
**Goal:** User-friendly error messages

**Tasks:**
- [ ] Add error toasts for failed actions
- [ ] Add retry buttons for failed fetches
- [ ] Add "Report Bug" link in error states

---

## Phase 7: Testing & Migration (1-2 hours)

### 7.1 E2E Tests
**Goal:** Playwright tests for critical paths

**Tests:**
- [ ] Search feeds
- [ ] Filter by status
- [ ] Select feed → view details
- [ ] Add new feed
- [ ] Edit feed
- [ ] Delete feed
- [ ] Bulk refresh
- [ ] Health check

**Files:**
- `tests/e2e/feed-management-v2.spec.js` (NEW)

**Run:**
```bash
npx playwright test tests/e2e/feed-management-v2.spec.js --reporter=line
```

---

### 7.2 Migration Path
**Goal:** Smooth transition from old to new UI

**Options:**
1. **Feature Flag** - `/admin/feeds` shows v1, `/admin/feeds-v2` shows v2
2. **User Preference** - Toggle in settings
3. **Hard Cutover** - Replace `/admin/feeds` with v2

**Tasks:**
- [ ] Deploy v2 alongside v1
- [ ] Add "Try New UI" banner in v1
- [ ] Collect feedback for 1 week
- [ ] Switch default to v2

---

## Phase 8: Optimization & Advanced Features (Optional)

### 8.1 Performance
- [ ] Add Redis caching for analytics
- [ ] Lazy load detail panel sections
- [ ] Virtualize feed list (1000+ feeds)
- [ ] Add pagination (50 feeds per page)

### 8.2 Advanced Features
- [ ] Feed Groups (organize feeds)
- [ ] Bulk Edit (change category for multiple)
- [ ] Custom Health Score Weights
- [ ] Notifications (email/slack on errors)
- [ ] Feed Duplicate Detection
- [ ] Feed Recommendations (suggest similar)

---

## Timeline Summary

| Phase | Tasks | Estimated Time | Priority |
|-------|-------|----------------|----------|
| 1. Foundation & Data Layer | DB schema, Health service, Analytics | 2-3 hours | **CRITICAL** |
| 2. Backend API Extensions | Search/Filter endpoints, Bulk actions | 2-3 hours | **CRITICAL** |
| 3. Frontend Layout | 2-column layout, Cards, Detail panel | 3-4 hours | **CRITICAL** |
| 4. Search & Filter | Global search, Filter chips, Sort | 1-2 hours | **HIGH** |
| 5. Modals & Forms | Add/Edit/Import/Health/Delete modals | 2-3 hours | **HIGH** |
| 6. Quick Actions & Polish | Quick actions bar, Empty/Loading states | 1-2 hours | **MEDIUM** |
| 7. Testing & Migration | E2E tests, Feature flag, Migration | 1-2 hours | **HIGH** |
| 8. Optimization (Optional) | Caching, Lazy loading, Advanced features | 2-4 hours | **LOW** |

**Total MVP Time: 12-18 hours**
**With Advanced Features: 14-22 hours**

---

## Next Steps

**Immediate Actions:**
1. ✅ Review this plan - confirm scope and priorities
2. Start with Phase 1.1 (Database Schema Extensions)
3. Test each phase before moving to next
4. Deploy v2 as `/admin/feeds-v2` (parallel to v1)
5. Gather feedback and iterate

**Questions to Resolve:**
- Should we migrate old `/admin/feeds` or keep both?
- Do we need role-based permissions (Viewer/Editor/Admin)?
- Should health score calculation run on-demand or scheduled?
- Do we want websockets for live updates (feed fetch progress)?

---

## Success Criteria

**Phase 1-3 Complete:**
- [ ] Health scores calculated for all feeds
- [ ] Analytics data available via API
- [ ] New UI shows feed list + detail panel
- [ ] Search and filter work

**Phase 4-6 Complete:**
- [ ] All modals functional (Add/Edit/Import/Delete)
- [ ] Bulk actions work (Refresh All, Health Check)
- [ ] UI is responsive and polished

**Phase 7 Complete:**
- [ ] E2E tests pass
- [ ] v2 deployed and accessible
- [ ] Migration path decided

**Full MVP Complete:**
- [ ] All features from spec implemented
- [ ] No regressions in v1
- [ ] User feedback collected
- [ ] Performance acceptable (< 2s page load)

---

## Risk Mitigation

**Risk:** Database migrations fail
- Mitigation: Test migrations on dev DB first, backup production before apply

**Risk:** New UI breaks existing workflows
- Mitigation: Keep v1 accessible during transition, feature flag

**Risk:** Performance issues with 1000+ feeds
- Mitigation: Pagination, virtualization, caching

**Risk:** Health score calculation is slow
- Mitigation: Run async background job, cache results

---

## Rollback Plan

If critical issues found:
1. Disable v2 route (`/admin/feeds-v2`)
2. Keep v1 as default
3. Fix issues in v2
4. Re-deploy when stable

Database rollback:
```sql
-- If needed, remove new columns
ALTER TABLE feeds DROP COLUMN health_score;
ALTER TABLE feeds DROP COLUMN last_error_message;
-- etc.
```

---

**Plan Version:** 1.0
**Created:** 2025-10-03
**Status:** 🟡 Ready for Review
