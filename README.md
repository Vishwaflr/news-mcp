# News MCP - Dynamic RSS Management & Content Processing System

**Dynamic RSS + Hot-Reload Templates + AI Analysis (Postgres, HTMX, Worker)**

Enterprise-ready RSS feed aggregation with MCP compatibility, dynamic template management, and intelligent content processing.

## Overview

Modern Repository Pattern architecture with feature flag-controlled rollout. [Architecture Details](./DATA_ARCHITECTURE.md) | [Database Schema](./ERD_DIAGRAM.md) | [Deployment Guide](./DEPLOYMENT.md)

| Metric | Value |
|--------|-------|
| **System Status** | 🟢 Production Ready (95%+) |
| **Feed Success Rate** | 100% (45/45 feeds active) |
| **Analysis Throughput** | ~30 items/minute |
| **Database Response** | <100ms |
| **Worker Error Rate** | 0% |
| **Repository Migration** | 🟡 25% complete |

## Quick Start

### Prerequisites
- Python 3.11+ and PostgreSQL 14+
- Virtual environment required

### Installation
```bash
git clone <repository-url>
cd news-mcp
python -m venv venv
source venv/bin/activate  # Linux/Mac: venv\Scripts\activate (Windows)
pip install -r requirements.txt
cp .env.example .env  # Edit with your database settings
alembic upgrade head
```

### Running
```bash
# Development Mode
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload    # Web UI
python jobs/scheduler_manager.py start --debug              # Scheduler

# Production Mode
sudo systemctl start news-mcp-web news-mcp-scheduler        # System services
```

### Access Points
- Dashboard: `http://localhost:8000` or `${WEB_HOST}:${WEB_PORT}`
- Health Check: `/admin/health`
- API Docs: `/docs`

## Key Features

### Dynamic Template Management
- Database-driven templates with hot-reload capability
- Web UI for template creation and assignment
- Pre-built templates for major news sources
- Complete audit history of configuration changes

### Content Processing & Analysis
- RSS feed management with health monitoring
- AI-powered sentiment and impact analysis (GPT-4.1-nano)
- Template-based content extraction and normalization
- Automatic deduplication and quality filtering

### Enterprise Interface
- **Modern Analysis Control Center** - Complete redesign with Bootstrap cards and Alpine.js
- **Exclusive Selection System** - Radio button-based target selection with SET confirmation
- **Real-time Statistics Dashboard** - Individual metric cards with live updates
- **Dynamic Feed Selection** - HTMX-powered dropdown with item counts
- **Smart Preview System** - Cost and duration estimation with filter logic
- **HTMX-based Management** - Server-side rendering with partial updates
- **Feature Flag System** - Safe deployment controls

### MCP Integration
- Complete MCP server implementation with tools
- Claude Desktop compatibility
- API endpoints for external integrations

## Configuration

### Environment Variables (.env)
```env
# Database
DATABASE_URL=postgresql://news_user:news_password@localhost:5432/news_db

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000

# Analysis & AI
OPENAI_API_KEY=your_openai_api_key_here
ANALYSIS_MODEL=gpt-4o-mini

# Feature Flags (JSON format)
FEATURE_FLAGS_JSON={"items_repo":{"status":"canary","rollout_percentage":5}}
```

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

## API Usage

```bash
# Add a new feed
curl -X POST "${API_HOST}:${API_PORT}/api/feeds" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com/rss", "title": "Example Feed"}'

# Get recent articles
curl "${API_HOST}:${API_PORT}/api/items?limit=10"

# Health check
curl "${API_HOST}:${API_PORT}/api/health"
```

## MCP Tools Available

- `search_feeds` - Search and filter RSS feeds
- `get_recent_articles` - Get recent articles with filtering
- `add_feed` - Add new RSS feeds
- `get_feed_health` - Check feed health status
- `search_articles` - Full-text search in articles
- `manage_templates` - Template management operations

## Monitoring

### Key Endpoints
- `/api/admin/feature-flags/` - Feature flag management
- `/api/health` - System health status
- `/admin/statistics` - Performance analytics

### Database Performance
- Index optimization: `python scripts/index_check.py`
- Query SLOs: <100ms timeline, <50ms feed queries

## Contributing

1. Fork repository
2. Create feature branch
3. Submit pull request

See [CONTRIBUTING.md](./CONTRIBUTING.md) for detailed guidelines.

## Documentation

### Core Documentation
- [Architecture Details](./DATA_ARCHITECTURE.md)
- [Deployment Guide](./DEPLOYMENT.md)
- [Testing Guide](./TESTING.md)
- [Monitoring Setup](./MONITORING.md)

### Interface & Development
- [**Analysis Control Interface**](./docs/ANALYSIS_CONTROL_INTERFACE.md) - Complete interface redesign documentation
- [UI Components Guide](./docs/UI_COMPONENTS_GUIDE.md) - Bootstrap 5 + Alpine.js + HTMX patterns
- [Schema Import Workaround](./docs/SCHEMA_IMPORT_WORKAROUND.md) - Current technical debt documentation

### Technical References
- [Documentation Index](./docs/README.md) - Complete documentation catalog
- [Worker System](./docs/WORKER_README.md) - Analysis worker documentation
- [Repository Policy](./docs/REPOSITORY_POLICY.md) - Data access patterns

## License

MIT License - see [LICENSE](LICENSE) file for details.