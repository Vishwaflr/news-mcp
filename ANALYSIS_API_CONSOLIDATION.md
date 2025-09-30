# Analysis API Consolidation Plan

**Created:** 2025-09-30
**Status:** In Progress

## 📊 Current State: 4 Separate Analysis APIs

### 1. `analysis_control.py` (765 lines) - Legacy/Main
**Purpose:** Original analysis control system
**Endpoints:** 21 endpoints
```
POST /analysis/preview          - Preview what would be analyzed
POST /analysis/start            - Start new analysis run
POST /analysis/runs             - Create new run (duplicate of /start?)
GET  /analysis/runs             - List all runs
POST /analysis/pause/{run_id}   - Pause a run
POST /analysis/start/{run_id}   - Resume a paused run
POST /analysis/cancel/{run_id}  - Cancel a run
GET  /analysis/status/{run_id}  - Get single run status
GET  /analysis/status           - Get all runs status
GET  /analysis/history          - Get run history (duplicate?)
POST /analysis/presets          - Create preset
GET  /analysis/presets          - List presets
DELETE /analysis/presets/{id}   - Delete preset
GET  /analysis/quick-actions    - Get quick actions
GET  /analysis/articles         - Get articles for analysis
GET  /analysis/feeds            - Get feeds for analysis
GET  /analysis/stats            - Get analysis statistics
GET  /analysis/history          - Get history (duplicate endpoint!)
GET  /analysis/cost/{model}     - Get model cost
GET  /analysis/models/compare   - Compare models
GET  /analysis/budget           - Get budget info
```

### 2. `analysis_management.py` (408 lines) - Central Management
**Purpose:** Run management and control
**Endpoints:** 11 endpoints
```
GET  /api/analysis/runs/{run_id}           - Get run details (DUPLICATE)
POST /api/analysis/runs/{run_id}/cancel    - Cancel run (DUPLICATE)
GET  /api/analysis/runs/{run_id}/items     - Get analyzed items
GET  /api/analysis/manager/status          - Manager status
POST /api/analysis/manager/emergency-stop  - Emergency stop all
POST /api/analysis/manager/resume          - Resume after emergency
GET  /api/analysis/manager/limits          - Get rate limits
GET  /api/analysis/manager/queue           - Get queued runs
POST /api/analysis/manager/queue/process   - Process queue
DELETE /api/analysis/manager/queue/{id}    - Remove from queue
GET  /api/analysis/health                  - Health check
```

### 3. `analysis_jobs.py` - Preview Jobs
**Purpose:** Job-based preview system
**Endpoints:** 7 endpoints
```
POST /analysis/jobs/preview           - Create preview job
GET  /analysis/jobs/{job_id}          - Get job details
POST /analysis/jobs/{job_id}/refresh  - Refresh preview
GET  /analysis/jobs/                  - List all jobs
POST /analysis/jobs/{job_id}/confirm  - Confirm and start
POST /analysis/jobs/{job_id}/cancel   - Cancel job
POST /analysis/jobs/preview/legacy    - Legacy preview support
```

### 4. `analysis_worker_api.py` - Worker Control
**Purpose:** Worker process management
**Endpoints:** 4 endpoints
```
GET  /api/analysis/worker/status   - Worker status
POST /api/analysis/worker/control  - Start/stop/restart worker
GET  /api/analysis/stats           - Worker statistics (DUPLICATE)
POST /api/analysis/test-deferred   - Test deferred task
```

## 🔴 Major Issues Found

### 1. Duplicate Endpoints
- **Run Status:** 3 different endpoints
  - `/analysis/status/{run_id}`
  - `/api/analysis/runs/{run_id}`
  - `/analysis/runs` (GET)

- **Cancel Run:** 3 different endpoints
  - `/analysis/cancel/{run_id}`
  - `/api/analysis/runs/{run_id}/cancel`
  - `/analysis/jobs/{job_id}/cancel`

- **Statistics:** 2 different endpoints
  - `/analysis/stats`
  - `/api/analysis/stats`

- **History:** 2 identical endpoints in same file!
  - `/analysis/history` (line 197)
  - `/analysis/history` (line 362)

### 2. Inconsistent Prefixes
- Some use `/analysis/`
- Some use `/api/analysis/`
- Jobs use `/analysis/jobs/`

### 3. Overlapping Functionality
- Preview: Both `analysis_control` and `analysis_jobs` handle previews
- Run Management: Split between `analysis_control` and `analysis_management`
- Status: Scattered across all 4 APIs

## ✅ Proposed Consolidated Structure

### `/api/v1/analysis/` - Single Unified API

#### Core Operations
```
# Preview & Start
POST   /api/v1/analysis/preview      - Preview analysis scope
POST   /api/v1/analysis/runs         - Start new run
GET    /api/v1/analysis/runs         - List all runs
GET    /api/v1/analysis/runs/{id}    - Get run details
DELETE /api/v1/analysis/runs/{id}    - Cancel run
POST   /api/v1/analysis/runs/{id}/pause   - Pause run
POST   /api/v1/analysis/runs/{id}/resume  - Resume run
GET    /api/v1/analysis/runs/{id}/items   - Get analyzed items

# Presets
GET    /api/v1/analysis/presets      - List presets
POST   /api/v1/analysis/presets      - Create preset
DELETE /api/v1/analysis/presets/{id} - Delete preset

# Statistics & Monitoring
GET    /api/v1/analysis/stats        - Overall statistics
GET    /api/v1/analysis/health       - Health check
GET    /api/v1/analysis/history      - Historical runs

# Cost & Budget
GET    /api/v1/analysis/cost/{model}    - Model costs
GET    /api/v1/analysis/models/compare  - Compare models
GET    /api/v1/analysis/budget          - Budget info

# Manager Control (Admin)
GET    /api/v1/analysis/manager/status       - Manager status
GET    /api/v1/analysis/manager/queue        - Queue status
POST   /api/v1/analysis/manager/queue/process - Process queue
POST   /api/v1/analysis/manager/emergency-stop - Emergency stop
GET    /api/v1/analysis/manager/limits       - Rate limits

# Worker Control (Admin)
GET    /api/v1/analysis/worker/status   - Worker status
POST   /api/v1/analysis/worker/control  - Control worker
```

## 🛠️ Implementation Status

### ✅ Phase 1: Create New Consolidated API (COMPLETED - 2025-09-30)
1. ✅ Created `/app/api/v1/analysis.py` with all endpoints
2. ✅ Using existing services/repositories
3. ✅ Added proper OpenAPI documentation
4. ✅ Health endpoint working: `/api/v1/analysis/health`
5. ⚠️ Some model imports need fixing (AnalysisResult)

### Phase 2: Redirect Old Endpoints
1. Add redirects from old endpoints to new ones
2. Log deprecation warnings
3. Update frontend to use new endpoints

### Phase 3: Remove Old Code
1. After 2 weeks, remove old API files
2. Clean up unused imports
3. Update tests

## 📈 Benefits

1. **Reduced Complexity:** 4 files → 1 file
2. **No Duplicates:** 50+ endpoints → ~25 endpoints
3. **Consistent Naming:** All under `/api/v1/analysis/`
4. **Better Documentation:** Single OpenAPI spec
5. **Easier Maintenance:** One place for all analysis logic

## 🔄 Migration Strategy

### Week 1
- [ ] Create new consolidated API
- [ ] Add comprehensive tests
- [ ] Update documentation

### Week 2
- [ ] Update frontend to use new endpoints
- [ ] Add redirects with deprecation warnings
- [ ] Monitor for issues

### Week 3
- [ ] Remove old endpoints
- [ ] Clean up codebase
- [ ] Final testing

## 📊 Metrics

- **Before:** 43 endpoints across 4 files (1,800+ lines)
- **After:** ~25 endpoints in 1 file (~500 lines)
- **Reduction:** 42% fewer endpoints, 72% less code