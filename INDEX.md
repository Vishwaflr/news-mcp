# 📚 News MCP Repository Index

> **Complete Directory Structure & Navigation Guide** | Updated: 2025-09-24

## 🏗️ **Core Architecture Directories**

### **`app/` - Main Application**
| Directory | Description | Hotspot |
|-----------|-------------|---------|
| `app/api/` | FastAPI route handlers and REST endpoints | H1, H3 |
| `app/core/` | Core infrastructure (logging, config, health) | H2, H5 |
| `app/domain/` | Domain models and business logic | H1, H2 |
| `app/services/` | Application services and business workflows | H1, H2 |
| `app/repositories/` | Data access layer (Repository Pattern) | H2 |
| `app/web/views/` | HTMX view controllers | H4 |
| `app/processors/` | Content processing pipeline | H3 |
| `app/routes/` | Template routing | H4 |
| `app/utils/` | Utility functions and helpers | H2 |

### **`static/` - Frontend Assets**
| Directory | Description | Hotspot |
|-----------|-------------|---------|
| `static/js/` | JavaScript controllers and Alpine.js components | H1, H4 |
| `static/css/` | Styling and responsive design | H4 |
| `static/images/` | Icons and static images | - |

### **`templates/` - HTML Templates**
| Directory | Description | Hotspot |
|-----------|-------------|---------|
| `templates/admin/` | Administrative interface templates | H3, H4, H5 |
| `templates/components/` | Reusable UI components | H4 |
| `templates/analysis_control_refactored.html` | Main analysis interface | H1, H4 |

## 🔍 **Key Domain Areas**

### **Analysis System** (Hotspot H1)
```
app/domain/analysis/
├── jobs.py              # Job-based analysis models
├── control.py           # Analysis control domain
└── models.py            # Core analysis entities

app/services/domain/
├── job_service.py       # Job management service
└── base.py              # Service base classes

app/api/
├── analysis_jobs.py     # Job-based API endpoints
└── analysis_control.py  # Legacy analysis API
```

### **Feed Management** (Hotspot H3)
```
app/api/
├── feeds.py             # Feed CRUD operations
├── processors.py        # Processor management
└── feed_limits.py       # Feed rate limiting

app/domain/feeds/
└── models.py            # Feed domain models

app/processors/
├── base.py              # Base processor classes
├── content/             # Content processors
└── templates/           # Processing templates
```

### **Repository Layer** (Hotspot H2)
```
app/repositories/
├── base.py              # Base repository classes
├── analysis_control.py  # Analysis data access
├── feeds.py             # Feed data access
└── items.py             # Item data access

app/utils/
├── feature_flags.py     # Feature flag management
└── shadow_comparison.py # A/B testing utilities
```

### **Web Interface** (Hotspot H4)
```
app/api/htmx.py          # HTMX endpoint handlers
app/web/views/           # View controllers
├── analysis_control.py  # Analysis UI logic
└── base.py              # Base view classes

templates/
├── analysis_control_refactored.html  # Main interface
├── components/analysis/              # Analysis UI components
└── admin/                            # Admin interfaces
```

### **Infrastructure** (Hotspot H5)
```
app/core/
├── health.py            # Health check system
├── metrics.py           # Metrics collection
├── logging_config.py    # Structured logging
├── error_handlers.py    # Global error handling
└── feature_flags.py     # Feature flag infrastructure
```

## 📂 **Supporting Directories**

### **Database & Migrations**
```
alembic/
├── versions/            # Database migrations
└── env.py              # Alembic configuration

migrations/              # Legacy migrations
└── *.sql               # Manual SQL migrations
```

### **Scripts & Tools**
```
scripts/
├── start-web-server.sh  # Development server
├── start-worker.sh      # Background worker
├── start_mcp_server.sh  # MCP server (STDIO/HTTP)
├── qmagent.py          # Documentation automation
└── update_all_docs.sh   # Documentation updates
```

### **Configuration & Documentation**
```
├── pyproject.toml       # Python dependencies
├── docker-compose.yml   # Container orchestration
├── ENDPOINTS.md         # API documentation
├── NAVIGATOR.md         # Development guide (this file)
├── README.md            # Project overview
├── DEVELOPER_SETUP.md   # Setup instructions
├── TESTING.md           # Test procedures
└── MONITORING.md        # Observability guide
```

## 🎯 **Navigation Shortcuts**

### **Starting Points by Task**
| Task | Primary Files | Hotspot |
|------|---------------|---------|
| **Add Analysis Feature** | `app/domain/analysis/jobs.py` → `app/api/analysis_jobs.py` | H1 |
| **Fix Feed Processing** | `app/api/feeds.py` → `app/processors/` | H3 |
| **Repository Migration** | `app/repositories/` → `app/utils/feature_flags.py` | H2 |
| **UI Component Issue** | `templates/components/` → `static/js/` | H4 |
| **Add Monitoring** | `app/core/health.py` → `app/api/metrics.py` | H5 |

### **Common File Patterns**
- **Domain Models**: `app/domain/{area}/models.py` or `{area}.py`
- **API Endpoints**: `app/api/{feature}.py`
- **Services**: `app/services/domain/{feature}_service.py`
- **Repositories**: `app/repositories/{feature}.py`
- **UI Components**: `templates/components/{feature}/`
- **JavaScript**: `static/js/{feature}-controller.js`

### **Configuration Files by Environment**
- **Development**: `pyproject.toml`, `docker-compose.yml`
- **Database**: `alembic/versions/`, `app/database.py`
- **API**: `app/config.py`, `app/main.py`
- **Frontend**: `static/`, `templates/`
- **Process Management**: `scripts/start-*.sh`

---

**🔧 Quick Start Navigation:**
1. **New Feature**: Start with `app/domain/{area}/` for models
2. **Bug Fix**: Check `app/api/{area}.py` for endpoint logic
3. **UI Issue**: Look in `templates/` and `static/js/`
4. **Database**: Check `alembic/versions/` for migrations
5. **Process**: Use `scripts/` for server management

**📍 Current Development Focus:** Job-based Analysis System (Hotspot H1)