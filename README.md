# News MCP - Dynamic RSS Management & Content Processing System

**Dynamic RSS + Hot-Reload Templates + AI Analysis (Postgres, HTMX, Worker)**

Enterprise-ready RSS feed aggregation with MCP compatibility, dynamic template management, and intelligent content processing.

## Overview

Modern Repository Pattern architecture with feature flag-controlled rollout. [Architecture Details](./DATA_ARCHITECTURE.md) | [Database Schema](./ERD_DIAGRAM.md) | [Deployment Guide](./DEPLOYMENT.md)

| Metric | Value |
|--------|-------|
| **System Status** | 🟢 Production Ready (98%+) |
| **Feed Success Rate** | 100% (37/37 feeds active) |
| **Analysis Throughput** | ~30 items/minute |
| **Database Response** | <100ms |
| **Worker Error Rate** | 0% |
| **Repository Migration** | 🟢 95% complete |
| **Code Quality** | 🟢 Refactored (Sep 2025) |
| **Documentation** | 🟢 Updated (Sep 2025) |
| **Security Status** | 🟢 Hardened |

## 📚 Documentation

- [API Documentation](./docs/API_DOCUMENTATION.md) - Complete REST API reference
- [Database Schema](./docs/DATABASE_SCHEMA.md) - Full database structure
- [Architecture Guide](./DATA_ARCHITECTURE.md) - System architecture details
- [ERD Diagram](./ERD_DIAGRAM.md) - Entity relationship diagram
- [Deployment Guide](./DEPLOYMENT.md) - Production deployment instructions
- [Developer Setup](./DEVELOPER_SETUP.md) - Development environment setup
- [Testing Guide](./TESTING.md) - Testing strategies and procedures
- [Monitoring Guide](./MONITORING.md) - Performance monitoring and metrics

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
# Development Mode (Process-Safe Scripts - Prevents Multiple Instances)
./scripts/start-web-server.sh                               # Web UI with auto-reload
./scripts/start-worker.sh                                   # Analysis Worker
./scripts/start-scheduler.sh                                # Feed Scheduler

# MCP Server (choose one)
./scripts/start_mcp_server.sh                               # Stdio MCP Server (default)
./scripts/start_mcp_server.sh http                          # HTTP MCP Server for Open WebUI

# Legacy Direct Commands (Not Recommended - Use Scripts Above)
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload   # Direct web server
python start_mcp_server.py                                  # Direct stdio MCP
uvicorn http_mcp_server:app --host 0.0.0.0 --port 8001     # Direct HTTP MCP

# Stop All Services
./scripts/stop-all.sh                                       # Gracefully stop all services

# Production Mode
sudo systemctl start news-mcp-web news-mcp-scheduler        # System services
```

### Access Points
- Dashboard: `http://localhost:8000` or `${WEB_HOST}:${WEB_PORT}`
- Analysis Control Center: `/admin/analysis` (integrated Articles + AI analysis)
- Health Check: `/admin/health`
- API Docs: `/docs`
- HTTP MCP Server: `http://localhost:8001` (when using HTTP mode)

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
- **Integrated Analysis Control Center** - Complete redesign combining Articles and Analysis interfaces
- **Live Article Selection System** - Real-time updates when changing analysis targets
- **Horizontal Statistics Dashboard** - System metrics displayed in compact cards above content
- **Target Selection with SET Buttons** - Instant preview and article filtering
- **Dark Mode Optimization** - Full dark theme with proper text contrast throughout
- **Model Selection with Pricing** - GPT models displayed with cost information
- **HTMX-powered Live Updates** - Server-side rendering with seamless partial updates
- **Navigation Integration** - Analysis accessible from main navbar with brain icon

### MCP Integration
- **Dual-Mode MCP Server**: Both STDIO and HTTP protocols supported
- **Claude Desktop Compatibility**: Traditional STDIO mode for seamless desktop integration
- **Open WebUI Integration**: HTTP/REST mode with OpenAPI documentation and CORS support
- **14 Comprehensive Tools**: Complete News MCP toolset with unified API
- **Real-time Testing**: Built-in endpoint testing and health monitoring

### Process Management & Development Tools
- **Process-Safe Start Scripts**: All scripts prevent multiple instances with intelligent detection
- **PID File Management**: Automatic cleanup and stale file detection
- **Port Conflict Prevention**: Port-based duplicate detection for web and MCP servers
- **User-Friendly Error Messages**: Clear instructions for stopping existing processes
- **Graceful Shutdown**: Centralized stop script for all services
- **Background Process Control**: No more runaway instances or resource conflicts

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

#### Stdio Mode (Traditional)
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

#### HTTP Mode (Open WebUI Integration)
```bash
# Start HTTP MCP Server (recommended - process-safe)
./scripts/start_mcp_server.sh http

# OR direct command (legacy - may create duplicates)
uvicorn http_mcp_server:app --host 0.0.0.0 --port 8001

# Stop all services (including MCP servers)
./scripts/stop-all.sh

# Test endpoints
curl http://localhost:8001/health                           # Health check
curl http://localhost:8001/openapi.json                     # OpenAPI docs
curl -X POST http://localhost:8001/mcp/tools/system.ping \  # Tool endpoint
  -H "Content-Type: application/json" -d '{}'
```

#### Open WebUI Configuration
```yaml
# In Open WebUI settings, add News MCP as external tool:
tool_config:
  news_mcp:
    base_url: "http://192.168.178.72:8001"
    endpoints:
      - "/mcp/tools/system.ping"      # System health check
      - "/mcp/tools/feeds.list"       # List all feeds
      - "/mcp/tools/articles.latest"  # Get recent articles
      - "/mcp/tools/articles.search"  # Search articles
      - "/mcp/tools/templates.assign" # Manage feed templates
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

### System Tools
- `system.ping` - System health check and connectivity test
- `system.health` - Comprehensive system status with metrics

### Feed Management
- `feeds.list` - List all RSS feeds with status and metadata
- `feeds.add` - Add new RSS feeds to the system
- `feeds.update` - Update existing feed configuration
- `feeds.delete` - Remove feeds from the system
- `feeds.test` - Test feed connectivity and parsing
- `feeds.refresh` - Force refresh of specific feeds
- `feeds.performance` - Get feed performance metrics and statistics
- `feeds.diagnostics` - Detailed feed health diagnostics

### Article & Content
- `articles.latest` - Get recent articles with filtering options
- `articles.search` - Full-text search across all articles

### Template Management
- `templates.assign` - Assign and manage feed-specific templates

### Data Export
- `data.export` - Export articles and feed data in various formats

**Total**: 14 comprehensive tools with both `/mcp/tools/{tool}` (Open WebUI) and `/{category}/{action}` (REST API) endpoints

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
- [**Open WebUI Integration**](./docs/OPEN_WEBUI_INTEGRATION.md) - Complete guide for Open WebUI setup and usage
- [UI Components Guide](./docs/UI_COMPONENTS_GUIDE.md) - Bootstrap 5 + Alpine.js + HTMX patterns
- [Schema Import Workaround](./docs/SCHEMA_IMPORT_WORKAROUND.md) - Current technical debt documentation

### Technical References
- [Documentation Index](./docs/README.md) - Complete documentation catalog
- [Worker System](./docs/WORKER_README.md) - Analysis worker documentation
- [Repository Policy](./docs/REPOSITORY_POLICY.md) - Data access patterns

## License

MIT License - see [LICENSE](LICENSE) file for details.