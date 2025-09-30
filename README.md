# News MCP - Enterprise RSS Aggregation with AI Analysis

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15+-blue.svg)](https://www.postgresql.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Enterprise-grade RSS aggregation system with integrated AI analysis. The system collects, processes, and analyzes news articles from various RSS feeds and provides a modern web interface for management and analysis.

## 🚀 Features

### Core Functionality
- **RSS Feed Management**: Automatic collection and processing of RSS feeds
- **Auto-Analysis System**: Automatic AI analysis of new feed items (Phase 2)
- **AI-Powered Analysis**: Sentiment analysis and categorization with OpenAI GPT
- **Real-time Dashboard**: Live monitoring of feed status and analysis runs
- **Advanced Analytics**: Detailed statistics and performance metrics
- **Template System**: Dynamic feed templates for flexible configuration

### Technical Features
- **Async Processing**: High-performance asynchronous processing
- **Queue Management**: Intelligent job queue with rate limiting
- **Centralized Caching**: In-memory selection cache for optimized performance
- **Modular Architecture**: Clean separation of API, services, and views
- **Dark Mode UI**: Modern, responsive web interface

## 📋 Table of Contents

- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [API Documentation](#api-documentation)
- [Database Schema](#database-schema)
- [Deployment](#deployment)
- [Development](#development)
- [Architecture](#architecture)

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

6. **Start Server**
```bash
# Development server
./scripts/start-web-server.sh

# Or manually
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

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

# Auto-Analysis Configuration
MAX_CONCURRENT_RUNS=5
MAX_DAILY_RUNS=100
MAX_DAILY_AUTO_RUNS=500
AUTO_ANALYSIS_RATE_PER_SECOND=3.0
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
# Service management
./scripts/start-all-background.sh    # Start all services
./scripts/stop-all.sh                # Stop all services
./scripts/status.sh                  # Status of all services

# Workers
./scripts/start-worker.sh            # Start analysis worker
./scripts/start-scheduler.sh         # Start feed scheduler
```

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

- **Feeds**: 37 active feeds
- **Articles**: 11,000+ items
- **Analysis Runs**: 75+ completed
- **Concurrent Processing**: 5 simultaneous runs
- **OpenAI Rate**: 3.0 requests/second
- **Auto-Analysis**: 9 feeds with automatic analysis

### Limits

```bash
MAX_CONCURRENT_RUNS=5       # Simultaneous analysis runs
MAX_DAILY_RUNS=100          # Manual analysis runs per day
MAX_DAILY_AUTO_RUNS=500     # Auto-analysis runs per day
MAX_HOURLY_RUNS=10          # Runs per hour (all types)
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

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- FastAPI for the excellent web framework
- OpenAI for GPT API integration
- PostgreSQL for robust data storage
- The open-source community

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/CytrexSGR/news-mcp/issues)
- **Discussions**: [GitHub Discussions](https://github.com/CytrexSGR/news-mcp/discussions)

---

**Current Version**: v3.2.0 - Phase 2 Complete (Auto-Analysis Production)

**Status**: ✅ Production Ready - 100% Auto-Analysis Rollout