# News MCP - Dynamic RSS Management & Content Processing System

A comprehensive MCP-compatible news reader with dynamic template management, intelligent content processing, and hot-reload capabilities for enterprise-ready RSS feed aggregation.

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

### 🏗️ Robust Architecture
- **Microservices**: Separate services for web UI and scheduler
- **Configuration Drift Detection**: Automatic detection of configuration changes
- **Concurrent Processing**: Batch-limited parallel feed processing
- **Error Recovery**: Automatic recovery from service errors
- **Production-Ready**: PostgreSQL support and scalability

## 🏛️ Architecture

```
├── data/                    # 🗄️ Local database storage
│   └── postgres/            # PostgreSQL data directory (automatically created)
├── app/                     # FastAPI Web API and Admin Interface
│   ├── api/                # REST API endpoints
│   │   ├── feeds.py        # Feed Management API
│   │   ├── items.py        # Article/Item API
│   │   ├── categories.py   # Category Management
│   │   ├── sources.py      # Source Management
│   │   ├── processors.py   # Content Processor API
│   │   ├── statistics.py   # Analytics & Metrics
│   │   ├── health.py       # Health Check Endpoints
│   │   ├── htmx.py         # HTMX Templates Management
│   │   ├── analysis_control.py # Analysis Control Center API
│   │   └── database.py     # Database Management API
│   ├── models.py           # SQLModel Database Models
│   ├── database.py         # Database Configuration
│   ├── config.py           # Application Configuration
│   ├── schemas.py          # Pydantic Response Schemas
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
│   └── utils/              # Utility Functions
│       ├── content_normalizer.py        # Content Normalization
│       └── feed_detector.py             # Feed Type Detection
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
└── test_mcp_server.py     # 🧪 MCP Server Testing
```

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- PostgreSQL (or SQLite for development)
- Virtual environment recommended

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
# Database will be automatically initialized on first run
python app/main.py
```

### Running the System

#### Development Mode
```bash
# Terminal 1: Start Web UI
python app/main.py

# Terminal 2: Start Scheduler
python jobs/scheduler_manager.py start --debug

# Terminal 3: Start MCP Server (optional)
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

# Get recent articles
curl "http://localhost:8000/api/items?limit=10"

# Health check
curl "http://localhost:8000/api/health"
```

## 🔧 Configuration

### Environment Variables (.env)
```env
# Database
DATABASE_URL=postgresql://user:pass@localhost/news_mcp
# or for SQLite: DATABASE_URL=sqlite:///./news.db

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
LOG_LEVEL=INFO

# MCP Server
MCP_SERVER_HOST=localhost
MCP_SERVER_PORT=3001

# Scheduler
SCHEDULER_INTERVAL_MINUTES=5
MAX_CONCURRENT_FEEDS=3
```

### Adding Custom Feed Templates
1. Access template management: `http://localhost:8000/templates`
2. Create new template with field mappings
3. Assign to feeds via URL patterns
4. Templates take effect immediately (hot-reload)

## 📊 Monitoring & Analytics

### Health Endpoints
- `/api/health` - Overall system health
- `/api/health/feeds` - Feed-specific health metrics
- `/api/health/scheduler` - Scheduler status

### Metrics Available
- Feed fetch success rates
- Article processing statistics
- Template performance metrics
- Error rates and recovery statistics

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