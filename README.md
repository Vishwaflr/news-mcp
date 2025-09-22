# News MCP - Dynamic RSS Management & Content Processing System

A comprehensive MCP-compatible news reader with dynamic template management, intelligent content processing, and hot-reload capabilities for enterprise-ready RSS feed aggregation.

## 🏗️ **Architecture Overview**

**NEW (v3.0)**: Modern Repository Pattern with Feature Flag-controlled Rollout

| Layer | Technology | Status | Description |
|-------|-----------|--------|-------------|
| **Data Layer** | Repository Pattern + SQLAlchemy Core | 🟢 Production Ready | Type-safe, tested, feature-flag controlled |
| **Legacy Layer** | Raw SQL + SQLModel | 🟡 Being Phased Out | Shadow-compared for safe migration |
| **API Layer** | FastAPI + Pydantic DTOs | 🟢 Active | Clean interfaces, no ORM leakage |
| **Frontend** | HTMX + Bootstrap | 🟢 Enhanced | Progressive enhancement with new features |
| **Database** | PostgreSQL + Alembic | 🟢 Schema-First | Versioned migrations, automated docs |

### 🎛️ **Feature Flags & Safe Deployment**

🆕 **Latest Enhancements (2025-09-22)**:
- **Circuit Breaker Protection**: Auto-disable on error rate >5% or latency >50% increase
- **Repository-Specific Monitoring**: Dedicated shadow comparison for each repository
- **Worker Integration**: AnalysisRepo with OpenAI GPT-4.1-nano integration
- **Emergency Auto-Disable**: Automatic rollback on performance degradation

**Core Features**:
- **Canary Rollout**: New repository layer with gradual percentage rollout (5-100%)
- **Shadow Comparison**: Automatic A/B testing between old and new implementations
- **Emergency Fallback**: Auto-disable on >5% error rate or >30% latency increase
- **Live Monitoring**: Real-time metrics dashboard with P50/P95/P99 percentiles
- **Circuit Breaker**: Automatic fallback to legacy implementation on failures
- **Risk-Free Migration**: Zero-downtime cutover with instant rollback capability

### 🏭 **Repository Architecture**

```python
# Repository layer hierarchy
app/repositories/
├── base.py                 # CRUD operations base class
├── items_repo.py          # ✅ Items timeline & search (OFF)
├── analysis_repo.py       # ✅ Analysis worker integration (OFF)
├── analysis_control.py    # ✅ Analysis run management (OFF)
├── analysis_queue.py      # ✅ Worker queue processing (OFF)
└── feeds_shadow_compare.py # ✅ Feeds-specific A/B testing

# Feature flags control rollout
items_repo: OFF      → 10% → 25% → 75% → 100%
feeds_repo: OFF      → 5%  → 25% → 75% → 100%
analysis_repo: OFF   → 15% → 25% → 75% → 100%
shadow_compare: CANARY (10% sampling active)
```

## 📚 Database Documentation

| Documentation | Description | Link |
|--------------|-------------|------|
| **Live Schema Docs** | Auto-generated database documentation | [Latest](https://YOUR_GITHUB_USER.github.io/news-mcp/db-docs/latest) |
| **ERD Diagram** | Interactive entity relationship diagram | [dbdiagram.io](https://dbdiagram.io/d/news-mcp) |
| **Data Architecture** | Complete system architecture | [DATA_ARCHITECTURE.md](./DATA_ARCHITECTURE.md) |
| **Schema Migrations** | Alembic migration history | [/alembic/versions](./alembic/versions) |
| **DBeaver Project** | Database IDE configuration | [/.dbeaver](/.dbeaver) |

## 🟢 Current System Status

**Last Updated: September 22, 2025**

| Component | Status | Health | Notes |
|-----------|--------|--------|-------|
| **Overall System** | 🟢 Production Ready | **95%+** | Recovered from 4.4% critical state |
| **Feed Management** | 🟢 Fully Operational | **100%** | 45/45 feeds ACTIVE and processing |
| **Database** | 🟢 Synchronized | **100%** | PostgreSQL schema fully updated |
| **Web Interface** | 🟢 Accessible | **100%** | Available at http://192.168.178.72:8000 |
| **Analysis Worker** | 🟢 Processing | **100%** | OpenAI GPT-4.1-nano integration active |
| **Analysis Control Center** | 🟢 Functional | **100%** | Preview, runs, and progress tracking working |
| **Repository Migration** | 🟡 In Progress | **25%** | Feature flags ready, shadow comparison active |
| **Feed Scheduler** | 🟢 Running | **100%** | Automatic fetching every 60 seconds |

### 🎯 Key Metrics
- **Feed Success Rate**: 100% (recovered from 4.4%)
- **Articles in Database**: 5,400+ and growing
- **Analysis Throughput**: ~30 items/minute
- **Analysis Cost**: ~$0.0003 per item
- **Database Response Time**: <100ms
- **Worker Error Rate**: 0%

### 🔧 Recent Critical Fixes (v2.2.0)
- ✅ **Database Schema Synchronization**: Fixed missing columns
- ✅ **Circular Import Resolution**: Restructured model architecture
- ✅ **SQLAlchemy Conflicts**: Removed duplicate table definitions
- ✅ **Analysis System**: Fixed progress tracking and worker integration
- ✅ **Frontend Accessibility**: Restored server binding and UI components

For detailed system changes, see `CHANGELOG.md`.

## 🚀 Key Features

### 🔥 Dynamic Template Management (Phase 2 - NEW!)
- **Database-driven Templates**: All templates stored in database, no static YAML files
- **Hot-Reload Capability**: Configuration changes without service restart
- **Web UI Management**: Complete template management via modern web interface
- **Auto-Assignment**: Automatic template assignment based on URL patterns
- **Built-in Templates**: Pre-configured templates for Heise, Cointelegraph, Wall Street Journal
- **Configuration Change Tracking**: Complete audit history of all template changes

### Core RSS Management
- **RSS Feed Management**: Add, categorize and manage feeds
- **Dynamic Scheduler**: Separate scheduler service with automatic configuration detection
- **Health Monitoring**: Feed health monitoring with metrics
- **Deduplication**: Automatic detection of duplicate articles
- **MCP Integration**: Complete MCP server implementation with tools

### Advanced Content Processing
- **Template-based Processing**: Flexible field mappings and content rules
- **Content Rules**: HTML extraction, text normalization, tracking removal
- **Quality Filters**: Title length validation and content quality checks
- **Multi-Source Support**: Universal template engine for various RSS formats
- **Real-time Configuration**: Immediate application of template changes

### 🎛️ Enterprise Management Interface
- **Template Management**: HTMX-based template creation and editing
- **Feed Assignment**: Drag-and-drop template assignment to feeds
- **Configuration Dashboard**: Real-time status of all templates and assignments
- **Statistics & Analytics**: Detailed analysis of template performance
- **Health Monitoring**: Real-time status of all feeds and scheduler instances
- **Analysis Control Center**: Advanced sentiment and impact analysis with AI models
  - Bulk analysis runs with flexible target selection (latest articles, feeds, time ranges)
  - Real-time preview with cost estimation and duplicate detection
  - Multiple AI model support (GPT-4.1-nano, GPT-4o-mini, etc.)
  - Analysis history tracking with detailed run metrics
  - 🆕 **Worker-based processing**: Background analysis with OpenAI GPT-4.1-nano integration
  - 🆕 **Repository integration**: AnalysisRepo for queue management and result tracking

### 🏗️ Robust Architecture
- **Microservices**: Separate services for web UI and scheduler
- **Configuration Drift Detection**: Automatic detection of configuration changes
- **Concurrent Processing**: Batch-limited parallel feed processing
- **Error Recovery**: Automatic recovery from service errors
- **Production-Ready**: PostgreSQL support and scalability

## 🏛️ Architecture

### 🗄️ **Data Layer (Repository Pattern)**
```
app/
├── repositories/           # 🔄 Type-safe Repository Pattern
│   ├── base.py            # BaseRepository with CRUD operations
│   ├── items_repo.py      # ✅ Items timeline & search (OFF)
│   ├── analysis_repo.py   # ✅ Analysis worker integration (OFF)
│   ├── analysis_control.py # ✅ Analysis run management (OFF)
│   ├── analysis_queue.py  # ✅ Worker queue processing (OFF)
│   └── feeds_shadow_compare.py # ✅ Feeds-specific A/B testing
├── schemas/               # 📝 Pydantic DTOs (no ORM leakage)
│   ├── items.py          # ItemQuery, ItemResponse, ItemCreate
│   └── __init__.py       # Schema exports
├── core/                 # 🔧 Core Infrastructure
│   └── ...               # Core application logic
└── utils/                # 🛡️ Safety & Monitoring
    ├── feature_flags.py  # 🆕 Circuit breaker & emergency auto-disable
    ├── shadow_compare.py # 🆕 General A/B testing framework
    ├── feeds_shadow_compare.py # 🆕 Feeds-specific comparison
    └── monitoring.py     # 🆕 Performance metrics & alerting
```

### 🏢 **Application Structure**
```
├── data/                    # 🗄️ Local database storage
│   └── postgres/            # PostgreSQL data directory (automatically created)
├── app/                     # FastAPI Web API and Admin Interface
│   ├── api/                # REST API endpoints
│   │   ├── feeds.py        # Feed Management API
│   │   ├── items.py        # Article/Item API (Repository-based)
│   │   ├── categories.py   # Category Management
│   │   ├── sources.py      # Source Management
│   │   ├── processors.py   # Content Processor API
│   │   ├── statistics.py   # Analytics & Metrics
│   │   ├── health.py       # Health Check Endpoints
│   │   ├── htmx.py         # HTMX Templates Management
│   │   ├── htmx_legacy.py  # Legacy HTMX Support
│   │   ├── analysis_control.py # 🆕 Analysis Control Center API
│   │   ├── feature_flags_admin.py # 🆕 Feature Flag Management API
│   │   ├── database.py     # Database Management API
│   │   └── user_settings.py # User Settings API
│   ├── web/                # 🎨 HTMX Web Interface
│   │   ├── items_htmx.py   # Items list with feature flag toggle
│   │   └── ...             # Progressive enhancement
│   ├── models/             # 📊 SQLModel Database Models
│   │   ├── base.py         # BaseCreatedOnly, BaseCreatedUpdated
│   │   ├── items.py        # Item model with analysis relations
│   │   └── ...             # Clean model separation
│   ├── repositories/       # 🔄 Repository Pattern Implementation
│   ├── schemas/            # 📝 Pydantic DTOs & Query Objects
│   ├── database.py         # Database Configuration
│   ├── config.py           # Application Configuration
│   ├── processors/         # Content Processing Engine
│   │   ├── base.py         # Base Processor Classes
│   │   ├── factory.py      # Processor Factory
│   │   ├── manager.py      # Processing Manager
│   │   ├── validator.py    # Content Validation
│   │   ├── universal.py    # Universal Template Processor
│   │   ├── heise.py        # Heise-specific Processor
│   │   └── cointelegraph.py # Cointelegraph Processor
│   ├── services/           # Business Logic Services
│   │   ├── dynamic_template_manager.py  # Template Management
│   │   ├── feed_change_tracker.py       # Change Detection
│   │   └── configuration_watcher.py     # Config Monitoring
│   └── utils/              # Utility Functions & Safety Tools
│       ├── content_normalizer.py        # Content Normalization
│       ├── feed_detector.py             # Feed Type Detection
│       ├── feature_flags.py             # Feature flag system
│       ├── shadow_compare.py            # A/B testing framework
│       └── monitoring.py                # Performance monitoring
├── jobs/                   # 🔄 Background Processing
│   ├── scheduler.py        # Basic AsyncIO Scheduler
│   ├── scheduler_manager.py # Production Scheduler Manager
│   ├── dynamic_scheduler.py # Advanced Dynamic Scheduler
│   └── fetcher.py          # RSS Feed Fetcher
├── mcp_server/             # 🔌 MCP Protocol Implementation
│   ├── server.py           # Basic MCP Server
│   └── comprehensive_server.py # Full-featured MCP Server
├── windows-bridge/         # 🪟 Windows Integration
│   ├── direct-http-mcp-client.js    # Direct HTTP-MCP Client
│   ├── mcp-news-bridge.js           # MCP Bridge Server
│   └── *.md                         # Setup Documentation
├── templates/              # 🎨 HTMX/Jinja2 Templates
│   ├── base.html          # Base Layout
│   ├── dashboard.html     # Main Dashboard
│   ├── feeds/             # Feed Management Templates
│   ├── templates/         # Template Management UI
│   └── components/        # Reusable Components
├── static/                 # 📦 Static Assets (CSS, JS)
├── systemd/                # 🔧 System Service Configuration
├── scripts/                # 🛠️ Deployment & Utility Scripts
│   ├── setup_cutover.sh   # Repository migration setup
│   ├── index_check.py     # Database performance validation
│   ├── check_migrations.py # Migration validation
│   ├── qmagent.py         # QMAgent automation
│   ├── github_deploy.sh   # GitHub deployment
│   └── start-worker.sh    # Worker startup script
├── alembic/                # 🗄️ Database Migrations
│   ├── env.py             # Drop protection for critical tables
│   └── versions/          # Versioned schema changes
└── test_mcp_server.py     # 🧪 MCP Server Testing
```

## 🚀 Quick Start

### Prerequisites
- Python 3.11+ (recommended for async performance)
- PostgreSQL 14+ (with JSON support)
- Virtual environment required
- Git (for development)

### Installation

1. **Clone and setup virtual environment:**
```bash
git clone <repository-url>
cd news-mcp
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate     # Windows
```

2. **Install dependencies:**
```bash
pip install -r requirements.txt
```

3. **Configure environment:**
```bash
cp .env.example .env
# Edit .env with your database settings
```

4. **Initialize database:**
```bash
# Run migrations and create initial schema
alembic upgrade head

# Verify database setup and indexes
python scripts/index_check.py

# Optional: Create missing indexes if needed
python scripts/index_check.py --create-missing
```

### Running the System

#### Development Mode
```bash
# Terminal 1: Start Web UI with hot reload
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Terminal 2: Start Scheduler
python jobs/scheduler_manager.py start --debug

# Terminal 3: Monitor feature flags and performance
python monitoring_dashboard.py

# Terminal 4: Start MCP Server (optional)
python start_mcp_server.py
```

#### Production Mode
```bash
# Install systemd services
sudo cp systemd/*.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable news-mcp-web news-mcp-scheduler
sudo systemctl start news-mcp-web news-mcp-scheduler
```

## 🎯 Usage

### Web Interface
- Access dashboard: `http://localhost:8000`
- Manage feeds: `http://localhost:8000/feeds`
- Template management: `http://localhost:8000/templates`
- Health monitoring: `http://localhost:8000/health`

### MCP Integration
```json
// Claude Desktop configuration
{
  "mcpServers": {
    "news-mcp": {
      "command": "python",
      "args": ["/path/to/news-mcp/start_mcp_server.py"]
    }
  }
}
```

### API Usage
```bash
# Add a new feed
curl -X POST "http://localhost:8000/api/feeds" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com/rss", "title": "Example Feed"}'

# Get recent articles (Repository-based with feature flag)
curl "http://localhost:8000/api/items?limit=10" \
  -H "X-User-ID: user123"

# Check feature flag status
curl "http://localhost:8000/api/admin/feature-flags/"

# Update feature flag (increase rollout)
curl -X POST "http://localhost:8000/api/admin/feature-flags/items_repo" \
  -H "Content-Type: application/json" \
  -d '{"status": "canary", "rollout_percentage": 25}'

# View performance metrics
curl "http://localhost:8000/api/admin/feature-flags/metrics/dashboard"

# Health check
curl "http://localhost:8000/api/health"
```

## 🔧 Configuration

### Environment Variables (.env)
```env
# Database
DATABASE_URL=postgresql://news_user:news_password@localhost:5432/news_db
# Repository Feature Flags (JSON format)
FEATURE_FLAGS_JSON={"items_repo":{"status":"canary","rollout_percentage":5}}

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
LOG_LEVEL=INFO

# Performance & Monitoring
MAX_QUERY_TIME_MS=1000
SHADOW_COMPARE_SAMPLE_RATE=0.1  # 10% sampling
METRICS_RETENTION_HOURS=24

# MCP Server
MCP_SERVER_HOST=localhost
MCP_SERVER_PORT=3001

# Scheduler
SCHEDULER_INTERVAL_MINUTES=5
MAX_CONCURRENT_FEEDS=3

# Analysis & AI
OPENAI_API_KEY=your_openai_api_key_here
ANALYSIS_MODEL=gpt-4o-mini
```

### Adding Custom Feed Templates
1. Access template management: `http://localhost:8000/templates`
2. Create new template with field mappings
3. Assign to feeds via URL patterns
4. Templates take effect immediately (hot-reload)

## 📊 Monitoring & Analytics

### Feature Flag Management
- `/api/admin/feature-flags/` - View all feature flags and status
- `/api/admin/feature-flags/{flag_name}` - Get/update specific flag
- `/api/admin/feature-flags/metrics/dashboard` - Comprehensive metrics
- `/api/admin/feature-flags/metrics/shadow-comparison` - A/B test results
- `/api/admin/feature-flags/metrics/performance` - Performance comparison

### Health Endpoints
- `/api/health` - Overall system health
- `/api/health/feeds` - Feed-specific health metrics
- `/api/health/scheduler` - Scheduler status
- `/api/admin/feature-flags/health` - Feature flag system health

### Repository Migration Monitoring
- **Shadow Comparison**: Automatic A/B testing between old/new implementations
- **Performance Metrics**: P50, P95, P99 latency tracking with alerting
- **Error Rate Monitoring**: Automatic fallback on >5% error rate
- **Circuit Breaker**: Emergency disable on performance regression
- **Live Dashboard**: Real-time monitoring via `python monitoring_dashboard.py`

### Database Performance
- **Index Reality Check**: `python scripts/index_check.py`
- **Query Performance SLOs**: <100ms for timeline, <50ms for feed queries
- **Automated Optimization**: Missing index detection and creation

## 🐳 Docker Deployment

```bash
# Start with Docker Compose
docker-compose up -d

# Check logs
docker-compose logs -f
```

## 🔌 MCP Tools Available

When running as MCP server, the following tools are available:
- `search_feeds` - Search and filter RSS feeds
- `get_recent_articles` - Get recent articles with filtering
- `add_feed` - Add new RSS feeds
- `get_feed_health` - Check feed health status
- `search_articles` - Full-text search in articles
- `get_categories` - List available categories
- `manage_templates` - Template management operations

## 🧪 Testing

```bash
# Test MCP server functionality
python test_mcp_server.py

# Test individual components
python -m pytest tests/  # (if test suite exists)
```

## 🔐 Security

- All external requests use proper user-agent headers
- Input validation on all API endpoints
- SQL injection protection via SQLModel/SQLAlchemy
- Environment-based configuration (no hardcoded secrets)
- Optional SSL/TLS support for production

## 📝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

- 📖 Documentation: See `/docs` directory
- 🐛 Issues: Create issue on GitHub
- 💬 Discussions: GitHub Discussions tab

## 🚀 Roadmap

### Phase 3 (Upcoming)
- [ ] Advanced analytics dashboard
- [ ] Machine learning content classification
- [ ] Multi-tenant support
- [ ] Advanced caching strategies
- [ ] Real-time WebSocket feeds
- [ ] Mobile-responsive design improvements

### Current Status: Phase 2 Complete ✅
- ✅ Dynamic template management
- ✅ Hot-reload configuration
- ✅ Web-based template editor
- ✅ Production-ready scheduler
- ✅ Comprehensive monitoring