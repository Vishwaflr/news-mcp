# News MCP - MCP-Native RSS Intelligence Platform

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15+-blue.svg)](https://www.postgresql.org/)
[![MCP](https://img.shields.io/badge/MCP-Enabled-orange.svg)](https://modelcontextprotocol.io/)
[![License: GPL-3.0](https://img.shields.io/badge/License-GPL%203.0-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)

**Model Context Protocol (MCP) server for intelligent RSS aggregation and AI-powered news analysis.** Control your news feeds directly from Claude Desktop or any MCP-enabled LLM client with 20+ native tools. Enterprise-grade system with automatic feed management, sentiment analysis, and real-time monitoring.

## 🚀 Features

### Core Functionality
- **RSS Feed Management**: Automatic collection and processing of RSS feeds
- **Auto-Analysis System**: Automatic AI analysis of new feed items (Phase 2 ✅)
- **AI-Powered Analysis**: Multi-dimensional sentiment analysis with OpenAI GPT
  - **Sentiment Scoring**: Overall, market, and thematic sentiment (-1.0 to +1.0)
  - **Geopolitical Analysis**: 13-field assessment including stability, security, diplomatic impact
  - **Impact & Urgency**: Quantified metrics for prioritization (0.0 to 1.0)
  - **Market Indicators**: Bullish/bearish/neutral sentiment, volatility assessment
- **Real-time Dashboard**: Live monitoring of feed status and analysis runs
- **Advanced Analytics**: Detailed statistics and performance metrics
- **Template System**: Dynamic feed templates for flexible configuration

### MCP Integration (Model Context Protocol)
- **🔌 20+ MCP Tools**: Complete system control via LLM-native interface
- **Feed Management**: List, add, update, delete feeds via Claude Desktop/LLM clients
- **Analytics Tools**: Dashboard stats, trending topics, article search
- **Database Access**: Safe read-only SQL queries with predefined templates
- **Health Monitoring**: System diagnostics, error analysis, scheduler status
- **LAN Access Ready**: HTTP bridge for remote Claude Desktop integration
- **See [MCP Documentation](MCP_SERVER_README.md) for full details**

### Technical Features
- **Async Processing**: High-performance asynchronous processing
- **Queue Management**: Intelligent job queue with rate limiting
- **Centralized Caching**: In-memory selection cache for optimized performance
- **Modular Architecture**: Clean separation of API, services, and views
- **Dark Mode UI**: Modern, responsive web interface
- **Feature Flags**: Gradual rollout with circuit breaker and A/B testing

## 📸 Screenshots

Get a visual overview of the system's capabilities:

- [Feed Management](docs/screenshots) - RSS feed monitoring with health status
- [Articles Stream](docs/screenshots) - Real-time article feed with AI analysis
- [Analysis Cockpit](docs/screenshots) - Manual analysis interface
- [Auto-Analysis System](docs/screenshots) - Automated AI processing
- [Statistics Dashboard](docs/screenshots) - Performance metrics and charts
- [Database Browser](docs/screenshots) - Query interface with templates

**[View all screenshots →](docs/screenshots/README.md)**

## 📋 Table of Contents

- [Screenshots](#screenshots)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [MCP Integration](#mcp-integration-model-context-protocol)
- [Sentiment Analysis Guide](docs/SENTIMENT_GUIDE.md) - **Understanding sentiment scores and analysis**
- [API Documentation](#api-documentation)
- [Database Schema](#database-schema)
- [Deployment](#deployment)
- [Development](#development)
- [Architecture](#architecture)

## 🏗️ Architecture

The system follows a modern, modular architecture with clear separation of concerns:

- **Repository Pattern**: Type-safe data access with SQLModel
- **Service Layer**: Business logic and orchestration
- **API Layer**: RESTful endpoints with FastAPI
- **Worker System**: Background processing with rate limiting
- **UI Layer**: HTMX + Alpine.js for progressive enhancement

See [ARCHITECTURE.md](ARCHITECTURE.md) for detailed documentation.

### Recent Refactoring (v4.0.0)
- Modularized 765-line monolithic repository into focused modules
- Improved error handling and recovery mechanisms
- Enhanced performance with skip tracking
- Fixed scope limit handling for proper item selection

## 🛠 Installation

### Prerequisites

```bash
# System Requirements
- Python 3.9+
- PostgreSQL 15+
- Redis (optional, for extended caching features)
- Git

# Ubuntu/Debian
sudo apt update
sudo apt install python3 python3-pip postgresql postgresql-contrib git

# macOS
brew install python postgresql git
```

### Setup

1. **Clone Repository**
```bash
git clone https://github.com/CytrexSGR/news-mcp.git
cd news-mcp
```

2. **Create Virtual Environment**
```bash
python3 -m venv venv
source venv/bin/activate  # Linux/macOS
# or: venv\Scripts\activate  # Windows
```

3. **Install Dependencies**
```bash
pip install -r requirements.txt
```

4. **Database Setup**
```bash
# Create PostgreSQL user and database
sudo -u postgres psql
CREATE USER news_user WITH PASSWORD 'news_password';
CREATE DATABASE news_db OWNER news_user;
GRANT ALL PRIVILEGES ON DATABASE news_db TO news_user;
\q

# Set environment variables
export PGPASSWORD=news_password
export DATABASE_URL="postgresql://news_user:news_password@localhost/news_db"
```

5. **Initialize Database**
```bash
# Alembic migrations
alembic upgrade head

# Or direct schema creation
python -c "from app.database import create_tables; create_tables()"
```

6. **Configure Environment**
```bash
# Create .env file (if not exists)
cp .env.example .env

# Edit .env and set required values:
# - DATABASE_URL (PostgreSQL connection)
# - OPENAI_API_KEY (for AI analysis)
# - API_HOST (default: 0.0.0.0)
# - API_PORT (default: 8000)
```

7. **Start Server**
```bash
# Start all services (API + Worker + Scheduler)
./scripts/start-all.sh

# Or start individual services
./scripts/start-api.sh       # Web server (Port 8000)
./scripts/start-worker.sh    # Analysis worker
./scripts/start-scheduler.sh # Feed scheduler

# Check service status
./scripts/status.sh

# Stop all services
./scripts/stop-all.sh
```

**Service Architecture:**
- **API Server**: Web UI + REST API (Port 8000)
- **Analysis Worker**: Background AI processing (Port 9090 metrics)
- **Feed Scheduler**: Automatic RSS fetching

Access the application at: `http://localhost:8000` (or your configured API_HOST:API_PORT)

## ⚙️ Configuration

### Environment Variables

```bash
# Create .env file
cp .env.example .env

# Important configurations
DATABASE_URL=postgresql://news_user:news_password@localhost/news_db
OPENAI_API_KEY=your_openai_api_key_here
ENVIRONMENT=development
LOG_LEVEL=INFO

# Auto-Analysis Configuration (Production Values)
MAX_CONCURRENT_RUNS=6
MAX_DAILY_RUNS=300
MAX_DAILY_AUTO_RUNS=1000
MAX_HOURLY_RUNS=50
AUTO_ANALYSIS_RATE_PER_SECOND=3.0
ANALYSIS_BATCH_LIMIT=200
ANALYSIS_RPS=1.5
```

### Configuration Files

- `app/core/config.py` - Main configuration
- `alembic.ini` - Database migration configuration
- `scripts/` - Deployment and management scripts

## 📊 Usage

### Web Interface

```bash
# Main dashboard
http://localhost:8000/

# Analysis cockpit
http://localhost:8000/admin/analysis

# Feed management
http://localhost:8000/admin/feeds

# Auto-analysis dashboard
http://localhost:8000/admin/auto-analysis

# Manager control center
http://localhost:8000/admin/manager
```

### CLI Tools

```bash
# Service Management
./scripts/start-all.sh               # Start all services (API + Worker + Scheduler)
./scripts/start-api.sh               # Start API server only (Port 8000)
./scripts/start-worker.sh            # Start analysis worker only
./scripts/start-scheduler.sh         # Start feed scheduler only
./scripts/stop-all.sh                # Stop all services (graceful shutdown with timeout)
./scripts/status.sh                  # Check service status and PIDs

# Service Architecture
# - API Server: Web UI + REST API (logs/api.log)
# - Analysis Worker: Background AI processing (logs/worker.log)
# - Feed Scheduler: Automatic RSS fetching (logs/scheduler.log)
# - All services use PID files in /tmp/news-mcp-*.pid
```

## 🔌 MCP Integration (Model Context Protocol)

News MCP provides a complete **Model Context Protocol** implementation, allowing LLMs like Claude to directly interact with your RSS system.

### Quick Start with Claude Desktop

**Note**: MCP Server integration is available but requires separate setup. The main application (API + Web UI) works standalone without MCP.

1. **Configure Claude Desktop**

Add to your Claude Desktop config (`~/Library/Application Support/Claude/claude_desktop_config.json` on macOS):

```json
{
  "mcpServers": {
    "news-mcp": {
      "command": "node",
      "args": ["/path/to/news-mcp/mcp-http-bridge.js"],
      "env": {
        "NEWS_MCP_SERVER_URL": "http://localhost:8001"
      }
    }
  }
}
```

3. **Restart Claude Desktop** - The MCP tools will appear automatically

### Available MCP Tools (20+)

#### Feed Management
```
- list_feeds          # View all RSS feeds with status
- add_feed            # Add new RSS feed
- update_feed         # Update feed configuration
- delete_feed         # Remove feed
- test_feed           # Test feed URL
- refresh_feed        # Manually trigger feed refresh
```

#### Analytics & Insights
```
- get_dashboard       # System overview with statistics
- latest_articles     # Get recent articles with filters
- search_articles     # Full-text article search
- trending_topics     # Analyze trending keywords
- feed_performance    # Performance metrics per feed
- export_data         # Export articles as JSON/CSV
```

#### Health & Monitoring
```
- system_health       # Overall system status
- feed_diagnostics    # Detailed feed health check
- error_analysis      # System error patterns
- scheduler_status    # Feed scheduler status
```

#### Database Access
```
- execute_query       # Safe read-only SQL queries
- table_info          # Database schema information
- quick_queries       # Predefined useful queries
```

#### Template Management
```
- list_templates      # View dynamic feed templates
- template_performance # Template usage statistics
- assign_template     # Assign template to feed
```

### Example Claude Interactions

```
You: "Show me all my RSS feeds"
Claude: *uses list_feeds tool*
        "You have 37 active feeds. Here are the details..."

You: "What are the trending topics today?"
Claude: *uses trending_topics tool*
        "Based on 450 articles today, the top topics are..."

You: "Add feed https://techcrunch.com/feed/"
Claude: *uses add_feed tool*
        "Added TechCrunch feed successfully..."

You: "Which feeds are having problems?"
Claude: *uses feed_diagnostics tool*
        "2 feeds have issues: Feed #12 has 5 consecutive failures..."
```

### LAN Access (Remote Claude Desktop)

For using Claude Desktop on a different machine:

1. **Configure Bridge for LAN**
```bash
export NEWS_MCP_SERVER_URL=http://192.168.1.100:8001
node mcp-http-bridge.js
```

2. **Update Claude Desktop Config**
```json
{
  "mcpServers": {
    "news-mcp": {
      "command": "node",
      "args": ["/path/to/mcp-http-bridge.js"],
      "env": {
        "NEWS_MCP_SERVER_URL": "http://192.168.1.100:8001"
      }
    }
  }
}
```

### MCP Architecture

```
Claude Desktop
    │
    ├─> mcp-http-bridge.js (stdio → HTTP)
    │
    └─> HTTP MCP Server (Port 8001)
            │
            └─> News MCP API (Port 8000)
                    │
                    └─> PostgreSQL Database
```

**Full MCP Documentation**: See [MCP_SERVER_README.md](MCP_SERVER_README.md) for complete setup guide, tool reference, and advanced configuration.

## 📡 API Documentation

### Core Endpoints

#### Feed Management
```http
GET    /api/feeds              # List all feeds
POST   /api/feeds              # Create new feed
PUT    /api/feeds/{id}         # Update feed
DELETE /api/feeds/{id}         # Delete feed
```

#### Article Management
```http
GET    /api/items              # List articles
GET    /api/items/{id}         # Get single article
POST   /api/items/search       # Search articles
```

#### Analysis API
```http
POST   /api/analysis/selection        # Create article selection
GET    /api/analysis/runs             # List analysis runs
POST   /api/analysis/runs             # Start new analysis
GET    /api/analysis/runs/{id}        # Get run status
POST   /api/analysis/runs/{id}/cancel # Cancel run
```

#### Auto-Analysis API (Phase 2)
```http
POST   /api/feeds/{id}/toggle-auto-analysis  # Enable/disable auto-analysis
GET    /api/feeds/{id}/auto-analysis-status  # Auto-analysis status
GET    /api/auto-analysis/queue              # Queue status
GET    /api/auto-analysis/history            # Auto-analysis history
```

#### System Management
```http
GET    /api/analysis/manager/status          # System status
POST   /api/analysis/manager/emergency-stop  # Emergency stop
POST   /api/analysis/manager/resume          # Resume operations
GET    /api/analysis/manager/queue           # Queue status
```

### Interactive API Documentation

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 🗄 Database Schema

### Core Tables

- `feeds` - RSS feed configurations
- `items` - News articles/items
- `sources` - News sources
- `categories` - Content categories
- `analysis_runs` - Analysis execution records
- `item_analysis` - Analysis results per item
- `pending_auto_analysis` - Auto-analysis queue

### Relationships

```
feeds (1) ─────< (N) items
feeds (N) ─────> (M) categories
items (1) ─────< (1) item_analysis
feeds (1) ─────< (N) pending_auto_analysis
```

## 🚀 Deployment

### Production Setup

1. **Environment Configuration**
```bash
# Production .env
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO
DATABASE_URL=postgresql://user:pass@prod-host:5432/news_db
OPENAI_API_KEY=prod_api_key
```

2. **Start Services**
```bash
# All services in background
./scripts/start-all-background.sh

# Individual services
./scripts/start-web-server.sh
./scripts/start-worker.sh
./scripts/start-scheduler.sh
```

3. **Service Management**
```bash
# Check status
./scripts/status.sh

# Stop all
./scripts/stop-all.sh
```

### Systemd Services

```bash
# Copy service files
sudo cp systemd/*.service /etc/systemd/system/

# Enable and start
sudo systemctl enable news-mcp-web news-mcp-worker news-mcp-scheduler
sudo systemctl start news-mcp-web news-mcp-worker news-mcp-scheduler

# Check status
sudo systemctl status news-mcp-*
```

## 🧪 Development

### Running Tests

```bash
# All tests
pytest

# Specific test file
pytest tests/test_feeds.py

# With coverage
pytest --cov=app tests/

# Integration tests
pytest tests/integration/
```

### Code Quality

```bash
# Linting
ruff check app/

# Type checking
mypy app/

# Format code
ruff format app/
```

### Database Migrations

```bash
# Create new migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1

# Show current version
alembic current
```

## 🏗 Architecture

### System Components

```
┌─────────────────────────────────────────────────┐
│                  Web Interface                   │
│         (FastAPI + HTMX + Bootstrap)            │
└─────────────────────────────────────────────────┘
                       │
┌─────────────────────────────────────────────────┐
│                  API Layer                       │
│  /api/feeds  /api/items  /api/analysis          │
└─────────────────────────────────────────────────┘
                       │
┌─────────────────────────────────────────────────┐
│                 Service Layer                    │
│  Feed Service  │  Analysis Service  │  Auto-    │
│                │  Run Manager       │  Analysis │
└─────────────────────────────────────────────────┘
                       │
┌─────────────────────────────────────────────────┐
│              Background Workers                  │
│  Analysis Worker  │  Feed Scheduler             │
└─────────────────────────────────────────────────┘
                       │
┌─────────────────────────────────────────────────┐
│               Database Layer                     │
│            PostgreSQL + SQLModel                 │
└─────────────────────────────────────────────────┘
```

### Key Patterns

- **Repository Pattern**: Data access abstraction
- **Service Layer**: Business logic encapsulation
- **Feature Flags**: Gradual rollout with circuit breaker
- **Queue Management**: Rate-limited processing with priorities
- **HTMX Components**: Progressive enhancement for UI

## 📈 Performance

### Current Metrics

- **Feeds**: 41 active feeds
- **Articles**: 16,843 items
- **Analysis Runs**: 813 completed
- **Analyzed Items**: 6,137 items processed
- **Concurrent Processing**: 6 simultaneous runs
- **OpenAI Rate**: 3.0 requests/second
- **Auto-Analysis**: 13 feeds with automatic analysis enabled
- **Success Rate**: >95% (production-tested)

### Limits

```bash
MAX_CONCURRENT_RUNS=6       # Simultaneous analysis runs
MAX_DAILY_RUNS=300          # Manual analysis runs per day
MAX_DAILY_AUTO_RUNS=1000    # Auto-analysis runs per day
MAX_HOURLY_RUNS=50          # Runs per hour (all types)
ANALYSIS_BATCH_LIMIT=200    # Articles per batch
ANALYSIS_RPS=1.5            # OpenAI requests per second per run
```

## 🔧 Troubleshooting

### Common Issues

**Database connection errors:**
```bash
# Check PostgreSQL status
sudo systemctl status postgresql

# Test connection
psql -h localhost -U news_user -d news_db
```

**Worker not processing:**
```bash
# Check worker logs
tail -f logs/analysis-worker.log

# Restart worker
./scripts/stop-all.sh
./scripts/start-worker.sh
```

**Feed fetch failures:**
```bash
# Check scheduler logs
tail -f logs/scheduler.log

# Manual feed fetch
curl -X POST http://localhost:8000/api/feeds/{feed_id}/fetch
```

## 📚 Documentation

- [Architecture Documentation](docs/ARCHITECTURE.md)
- [API Examples](docs/API_EXAMPLES.md)
- [Database Schema](docs/DATABASE_SCHEMA.md)
- [MCP Server Integration](MCP_SERVER_README.md)
- [Testing Guide](TESTING.md)
- [Monitoring Guide](MONITORING.md)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines.

## 📄 License

This project is licensed under the GNU General Public License v3.0 - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- FastAPI for the excellent web framework
- OpenAI for GPT API integration
- PostgreSQL for robust data storage
- The open-source community

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/CytrexSGR/news-mcp/issues)
- **Discussions**: [GitHub Discussions](https://github.com/CytrexSGR/news-mcp/discussions)

---

**Current Version**: v4.0.0 - Complete Documentation Suite & Production-Ready MCP Server

**Status**: ✅ Production Ready - 100% Auto-Analysis Rollout