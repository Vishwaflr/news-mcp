# 🧭 News MCP Navigator

> **System Overview & Development Hotspots** | Version: Job-based Analysis System | Updated: 2025-09-24

## 📊 **3-Column System Overview**

| **Core System** | **Domain Logic** | **Infrastructure** |
|---|---|---|
| **API Layer** | **Analysis Engine** | **Database** |
| • FastAPI Routes | • Job Management | • PostgreSQL |
| • HTMX Endpoints | • Preview Calculations | • SQLAlchemy Core |
| • Error Handling | • Execution Control | • Repository Pattern |
| | | |
| **Web Interface** | **Feed Management** | **Monitoring** |
| • Alpine.js Components | • RSS Processing | • Health Checks |
| • Template System | • Content Analysis | • Feature Flags |
| • Real-time Updates | • Template Matching | • Performance Metrics |
| | | |
| **Job System** | **AI Integration** | **Deployment** |
| • Preview Jobs | • OpenAI API | • Docker Setup |
| • Execution Queue | • Sentiment Analysis | • Process Management |
| • Status Tracking | • Impact Scoring | • Background Workers |

## 🔥 **Top-5 Development Hotspots**

### **H1: Job-based Analysis System** 📊
**Current Status:** Phase 1 Complete | **Priority:** Critical | **Workset Size:** 6 files
```
📁 Workset H1:
├── app/domain/analysis/jobs.py              # Domain Models (PreviewJob, SelectionConfig)
├── app/services/domain/job_service.py       # Job Management Service
├── app/api/analysis_jobs.py                 # REST API Endpoints
├── static/js/analysis-controller.js         # Frontend Controller
├── templates/analysis_control_refactored.html # UI Template
└── app/main.py                              # Router Registration
```

### **H2: Repository Pattern Migration** 🔄
**Current Status:** In Progress | **Priority:** High | **Workset Size:** 8 files
```
📁 Workset H2:
├── app/repositories/                        # New Repository Layer
├── app/utils/feature_flags.py              # Migration Control
├── app/core/shadow_comparison.py           # A/B Testing
├── app/domain/analysis/control.py          # Domain Objects
├── app/services/domain/base.py             # Service Base Classes
├── app/repositories/analysis_control.py    # Analysis Repository
├── app/core/logging_config.py              # Logging Infrastructure
└── alembic/versions/                       # Database Migrations
```

### **H3: Feed Processing Pipeline** 📡
**Current Status:** Stable | **Priority:** Medium | **Workset Size:** 7 files
```
📁 Workset H3:
├── app/api/feeds.py                        # Feed CRUD Operations
├── app/domain/feeds/                       # Feed Domain Models
├── app/services/feed_processor.py          # Processing Logic
├── app/processors/                         # Content Processors
├── app/api/processors.py                   # Processor Management
├── app/core/scheduler.py                   # Background Tasks
└── templates/admin/feeds.html              # Management UI
```

### **H4: HTMX Web Interface** 🌐
**Current Status:** Refactoring | **Priority:** Medium | **Workset Size:** 8 files
```
📁 Workset H4:
├── app/api/htmx.py                         # HTMX Endpoints
├── app/web/views/analysis_control.py       # View Controllers
├── templates/components/                   # UI Components
├── static/css/admin.css                    # Styling
├── static/js/                              # JavaScript Controllers
├── templates/analysis_control_refactored.html # Main Interface
├── templates/components/analysis/          # Analysis Components
└── app/routes/templates.py                 # Template Routes
```

### **H5: Monitoring & Observability** 📈
**Current Status:** Basic Setup | **Priority:** Low | **Workset Size:** 6 files
```
📁 Workset H5:
├── app/core/health.py                      # Health Checks
├── app/core/metrics.py                     # Metrics Collection
├── app/api/metrics.py                      # Metrics API
├── app/core/feature_flags.py               # Feature Flag System
├── app/core/error_handlers.py              # Error Handling
└── templates/admin/metrics.html            # Metrics Dashboard
```

## 🧪 **Contract Test Specifications**

### **T1: Job System Integrity**
```python
# Contract: PreviewJob → RunScope → Execution
def test_job_preview_execution_contract():
    # Given: Valid PreviewJob configuration
    # When: Converting to RunScope and RunParams
    # Then: Estimates match actual execution parameters
    pass
```

### **T2: Repository Pattern Consistency**
```python
# Contract: Legacy → Repository → Shadow Comparison
def test_repository_shadow_comparison_contract():
    # Given: Same query parameters
    # When: Calling legacy vs repository methods
    # Then: Results must be identical (shadow mode)
    pass
```

### **T3: HTMX Component Communication**
```python
# Contract: Alpine.js ↔ HTMX State Sync
def test_htmx_alpine_state_contract():
    # Given: UI state change in Alpine.js
    # When: HTMX updates component
    # Then: Alpine.js state remains consistent
    pass
```

### **T4: Feed Processing Pipeline**
```python
# Contract: RSS Fetch → Process → Store → Analyze
def test_feed_processing_pipeline_contract():
    # Given: RSS feed URL
    # When: Complete processing cycle
    # Then: Items stored with correct metadata
    pass
```

### **T5: API Response Format Consistency**
```python
# Contract: All API endpoints follow ServiceResult<T> pattern
def test_api_response_format_contract():
    # Given: Any API endpoint call
    # When: Success or error response
    # Then: Consistent ServiceResult structure
    pass
```

## 🚀 **Phase 2 Development Roadmap**

### **Week 1: Frontend Job Integration**
- [ ] Replace direct analysis calls with job-based flow
- [ ] Implement job status polling in UI
- [ ] Add job confirmation dialogs
- [ ] Update Alpine.js controllers for job management

### **Week 2: Backend Job Execution**
- [ ] Connect jobs to analysis manager
- [ ] Implement job queue processing
- [ ] Add job persistence (move from memory to database)
- [ ] Create job history and tracking

### **Week 3: Repository Migration Completion**
- [ ] Complete shadow comparison validation
- [ ] Switch feature flags to repository-first
- [ ] Remove legacy code paths
- [ ] Update all tests for repository pattern

### **Week 4: Performance & Polish**
- [ ] Optimize job processing performance
- [ ] Add comprehensive error handling
- [ ] Implement job cancellation
- [ ] Performance benchmarking and SLO validation

---

**🎯 Current Focus:** Job-based Analysis System (Phase 1 → Phase 2)
**📍 Next Milestone:** Frontend job integration and status polling
**⚡ Critical Path:** HTMX/Alpine.js state synchronization in job workflows