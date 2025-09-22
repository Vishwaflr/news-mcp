# Developer Setup Guide

This guide will help you set up the News MCP development environment with all necessary tools and dependencies.

## 🚀 Quick Setup

### Prerequisites

- **Python 3.11+** (required for optimal async performance)
- **PostgreSQL 14+** with JSON support
- **Git** for version control
- **Node.js 18+** (for potential frontend tooling)

### Environment Setup

1. **Clone the repository:**
```bash
git clone <repository-url>
cd news-mcp
```

2. **Create and activate virtual environment:**
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate     # Windows
```

3. **Install dependencies:**
```bash
pip install -r requirements.txt
```

4. **Database Setup:**
```bash
# Create PostgreSQL database
createdb news_db
createuser news_user

# Set password
psql -c "ALTER USER news_user PASSWORD 'news_password';"
psql -c "GRANT ALL PRIVILEGES ON DATABASE news_db TO news_user;"
```

5. **Environment Configuration:**
```bash
cp .env.example .env
# Edit .env with your specific settings
```

6. **Database Migration:**
```bash
# Run migrations
alembic upgrade head

# Verify setup and create indexes
python scripts/index_check.py --create-missing
```

## 🔧 Development Environment

### Required Environment Variables

Create a `.env` file with these settings:

```env
# Database Configuration
DATABASE_URL=postgresql://news_user:news_password@localhost:5432/news_db

# Feature Flags (start with repositories in safe mode)
FEATURE_FLAGS_JSON={"items_repo":{"status":"off","rollout_percentage":10,"emergency_threshold":0.05},"feeds_repo":{"status":"off","rollout_percentage":5},"analysis_repo":{"status":"off","rollout_percentage":15},"shadow_compare":{"status":"canary","rollout_percentage":10}}

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
LOG_LEVEL=DEBUG

# Performance Monitoring
MAX_QUERY_TIME_MS=1000
SHADOW_COMPARE_SAMPLE_RATE=0.1
METRICS_RETENTION_HOURS=24

# Analysis & AI (optional)
OPENAI_API_KEY=your_openai_api_key_here
ANALYSIS_MODEL=gpt-4o-mini

# MCP Server (optional)
MCP_SERVER_HOST=localhost
MCP_SERVER_PORT=3001

# Scheduler
SCHEDULER_INTERVAL_MINUTES=1  # Fast for development
MAX_CONCURRENT_FEEDS=2
```

### Running the Development Server

Use separate terminals for each service:

#### Terminal 1: Web API
```bash
# Hot reload enabled
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

#### Terminal 2: Background Scheduler
```bash
python jobs/scheduler_manager.py start --debug
```

#### Terminal 3: Feature Flag Monitoring
```bash
# Monitor repository migration progress
python monitoring_dashboard.py

# Alternative: Simple status check
python monitoring_dashboard.py --mode check

# 🆕 Enable worker for AnalysisRepo testing
./scripts/start-worker.sh --verbose
```

#### Terminal 4: MCP Server (Optional)
```bash
python start_mcp_server.py
```

### Development URLs

- **Main Interface**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Alternative Docs**: http://localhost:8000/redoc
- **Admin Interface**: http://localhost:8000/admin/feeds
- **Feature Flags**: http://localhost:8000/api/admin/feature-flags/
- **Health Dashboard**: http://localhost:8000/api/health

## 🧪 Testing

### Running Tests

```bash
# Basic functionality test
python test_mcp_server.py

# Database performance validation
python scripts/index_check.py

# Feature flag system test
curl http://localhost:8000/api/admin/feature-flags/health
```

### Manual Testing Workflow

1. **Add Test Feed:**
```bash
curl -X POST "http://localhost:8000/api/feeds" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://feeds.bbci.co.uk/news/rss.xml", "title": "BBC News"}'
```

2. **Test Repository Feature Flag:**
```bash
# Check current status
curl "http://localhost:8000/api/admin/feature-flags/items_repo"

# Test with repository enabled (add user header)
curl "http://localhost:8000/api/items?limit=5" \
  -H "X-User-ID: dev-user-1"

# Test legacy path (no user header)
curl "http://localhost:8000/api/items?limit=5"
```

3. **Monitor Shadow Comparison:**
```bash
curl "http://localhost:8000/api/admin/feature-flags/metrics/shadow-comparison"
```

## 🛠️ Repository Migration Development

The system is currently migrating from Raw SQL to Repository Pattern. Here's how to work with it:

### Understanding Feature Flags

🆕 **Current Repository Migration Status:**
- **items_repo**: Timeline & search operations (OFF → CANARY → ON)
- **feeds_repo**: Feed management operations (OFF → CANARY → ON)
- **analysis_repo**: Worker-based analysis processing (OFF → CANARY → ON)
- **shadow_compare**: A/B testing framework (CANARY 10% sampling)

### 🔧 Advanced Feature Flag Configuration

```python
# Emergency thresholds (app/utils/feature_flags.py)
error_rate > 0.05           # 5% error rate triggers emergency_off
latency > baseline * 1.5    # 50% latency increase triggers emergency_off
consecutive_failures > 3    # Circuit breaker protection
```

### Monitoring Migration

1. **Real-time Dashboard:**
```bash
python monitoring_dashboard.py
```

2. **Performance Metrics:**
```bash
curl "http://localhost:8000/api/admin/feature-flags/metrics/performance"
```

3. **Increase Rollout (Gradual Migration):**
```bash
# Phase 1: Enable canary testing (5% rollout)
curl -X POST "http://localhost:8000/api/admin/feature-flags/items_repo" \
  -H "Content-Type: application/json" \
  -d '{"status": "canary", "rollout_percentage": 5}'

# Phase 2: Increase after 24h monitoring (25% rollout)
curl -X POST "http://localhost:8000/api/admin/feature-flags/items_repo" \
  -H "Content-Type: application/json" \
  -d '{"status": "canary", "rollout_percentage": 25}'

# Phase 3: Majority rollout (75% rollout)
curl -X POST "http://localhost:8000/api/admin/feature-flags/items_repo" \
  -H "Content-Type: application/json" \
  -d '{"status": "canary", "rollout_percentage": 75}'

# Phase 4: Full migration (100% rollout)
curl -X POST "http://localhost:8000/api/admin/feature-flags/items_repo" \
  -H "Content-Type: application/json" \
  -d '{"status": "on", "rollout_percentage": 100}'
```

4. **Test AnalysisRepo Worker Integration:**
```bash
# Start analysis worker
./scripts/start-worker.sh --verbose

# Check worker config
cat .env.worker

# Test analysis run
curl -X POST "http://localhost:8000/api/analysis/start/25"
```

### Adding New Repository Methods

1. **Create in `app/repositories/items_repo.py`:**
```python
async def new_method(self, params: QueryType) -> ResponseType:
    # Implementation here
    pass
```

2. **Add to schema in `app/schemas/items.py`:**
```python
class NewQuery(BaseModel):
    # Query parameters
    pass
```

3. **Add feature flag to controller:**
```python
if is_feature_enabled("new_feature", user_id):
    result = await repo.new_method(query)
else:
    result = legacy_implementation()
```

## 🔍 Debugging

### Common Development Issues

1. **Database Connection:**
```bash
# Test connection
PGPASSWORD=news_password psql -h localhost -U news_user -d news_db -c "SELECT 1;"
```

2. **Missing Indexes:**
```bash
# Check and create
python scripts/index_check.py --create-missing
```

3. **Feature Flag Issues:**
```bash
# Reset metrics
curl -X POST "http://localhost:8000/api/admin/feature-flags/items_repo/reset-metrics"

# Emergency disable
curl -X POST "http://localhost:8000/api/admin/feature-flags/items_repo" \
  -d '{"status": "emergency_off"}'
```

### Performance Debugging

1. **Slow Queries:**
```bash
# Check query performance
python scripts/index_check.py
```

2. **Shadow Comparison:**
```bash
# View A/B test results
curl "http://localhost:8000/api/admin/feature-flags/metrics/shadow-comparison"
```

3. **Live Monitoring:**
```bash
# Watch logs in real-time
tail -f logs/app.log | grep -E "(ERROR|performance|shadow)"
```

## 📁 Project Structure for Developers

### Key Development Files

```
app/
├── repositories/           # 🆕 New Repository Pattern
│   ├── base.py            # CRUD operations base class
│   ├── items_repo.py      # ✅ Items timeline & search
│   ├── analysis_repo.py   # ✅ Analysis worker integration
│   ├── analysis_control.py # ✅ Analysis run management
│   ├── analysis_queue.py  # ✅ Worker queue processing
│   └── feeds_shadow_compare.py # ✅ Feeds-specific A/B testing
├── schemas/               # 📝 Pydantic DTOs
│   ├── items.py          # Request/response models
│   └── __init__.py       # Schema exports
├── utils/                 # 🛡️ Development Tools
│   ├── feature_flags.py  # ✅ Circuit breaker & emergency auto-disable
│   ├── shadow_compare.py # ✅ General A/B testing framework
│   ├── feeds_shadow_compare.py # ✅ Feeds-specific comparison
│   └── monitoring.py     # ✅ Metrics collection
├── web/                  # 🎨 HTMX Interface
│   ├── items_htmx.py     # Feature flag integration
│   └── views/            # Web views
└── api/                  # 🔌 REST API
    ├── items.py          # Items API (being migrated)
    ├── feature_flags_admin.py # Admin interface
    └── analysis_control.py # Analysis control API
```

### Development Workflow

1. **Start with feature flags in canary mode** (5% rollout)
2. **Monitor shadow comparison** for performance/correctness
3. **Gradually increase rollout** as confidence grows
4. **Emergency rollback** if issues detected
5. **Remove legacy code** once 100% migrated

## 🚨 Emergency Procedures

### Rollback Repository Changes

```bash
# Immediate emergency disable
curl -X POST "http://localhost:8000/api/admin/feature-flags/items_repo" \
  -H "Content-Type: application/json" \
  -d '{"status": "emergency_off"}'
```

### Database Recovery

```bash
# Restore from backup
pg_restore -h localhost -U news_user -d news_db backup.sql

# Recreate indexes
python scripts/index_check.py --create-missing
```

## 📚 Next Steps

1. **Read the main README.md** for architecture overview
2. **Explore the API docs** at `/docs` when server is running
3. **Check the monitoring dashboard** to understand system health
4. **Review repository pattern** in `app/repositories/`
5. **Understand feature flags** in `app/utils/feature_flags.py`

---

🎯 **Goal**: Complete migration from Raw SQL to Repository Pattern with zero downtime and risk.