# News MCP - Enterprise RSS Aggregation with AI Analysis

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15+-blue.svg)](https://www.postgresql.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

News MCP ist ein enterprise-grade RSS-Aggregationssystem mit integrierter KI-Analyse. Das System sammelt, verarbeitet und analysiert Nachrichtenartikel aus verschiedenen RSS-Feeds und bietet ein modernes Web-Interface für das Management und die Analyse.

## 🚀 Features

### Core Funktionalitäten
- **RSS Feed Management**: Automatische Erfassung und Verarbeitung von RSS-Feeds
- **Auto-Analysis System**: Automatische KI-Analyse neuer Feed-Items (Phase 2)
- **KI-Powered Analysis**: Sentiment-Analyse und Kategorisierung mit OpenAI GPT
- **Real-time Dashboard**: Live-Monitoring von Feed-Status und Analyse-Runs
- **Advanced Analytics**: Detaillierte Statistiken und Performance-Metriken
- **Template System**: Dynamische Feed-Templates für flexible Konfiguration

### Technical Features
- **Async Processing**: Hochperformante asynchrone Verarbeitung
- **Queue Management**: Intelligente Job-Queue mit Rate-Limiting
- **Centralized Caching**: In-Memory Selection Cache für optimierte Performance
- **Modular Architecture**: Saubere Trennung von API, Services und Views
- **Dark Mode UI**: Moderne, responsive Web-Oberfläche

## 📋 Inhaltsverzeichnis

- [Installation](#installation)
- [Konfiguration](#konfiguration)
- [API Dokumentation](#api-dokumentation)
- [Datenbank Schema](#datenbank-schema)
- [Deployment](#deployment)
- [Entwicklung](#entwicklung)
- [Architektur](#architektur)

## 🛠 Installation

### Voraussetzungen

```bash
# System-Requirements
- Python 3.9+
- PostgreSQL 15+
- Redis (optional, für erweiterte Caching-Features)
- Git

# Ubuntu/Debian
sudo apt update
sudo apt install python3 python3-pip postgresql postgresql-contrib git

# macOS
brew install python postgresql git
```

### Setup

1. **Repository klonen**
```bash
git clone https://github.com/your-org/news-mcp.git
cd news-mcp
```

2. **Virtual Environment erstellen**
```bash
python3 -m venv venv
source venv/bin/activate  # Linux/macOS
# oder: venv\Scripts\activate  # Windows
```

3. **Dependencies installieren**
```bash
pip install -r requirements.txt
```

4. **Datenbank Setup**
```bash
# PostgreSQL User und Database erstellen
sudo -u postgres psql
CREATE USER news_user WITH PASSWORD 'news_password';
CREATE DATABASE news_db OWNER news_user;
GRANT ALL PRIVILEGES ON DATABASE news_db TO news_user;
\q

# Environment Variables setzen
export PGPASSWORD=news_password
export DATABASE_URL="postgresql://news_user:news_password@localhost/news_db"
```

5. **Datenbank initialisieren**
```bash
# Alembic Migrations
alembic upgrade head

# Oder direkte Schema-Erstellung
python -c "from app.database import create_tables; create_tables()"
```

6. **Server starten**
```bash
# Development Server
./scripts/start-web-server.sh

# Oder manuell
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## ⚙️ Konfiguration

### Environment Variables

```bash
# .env Datei erstellen
cp .env.example .env

# Wichtige Konfigurationen
DATABASE_URL=postgresql://news_user:news_password@localhost/news_db
OPENAI_API_KEY=your_openai_api_key_here
ENVIRONMENT=development
LOG_LEVEL=INFO
REDIS_URL=redis://localhost:6379/0  # Optional
```

### Konfigurationsdateien

- `app/core/config.py` - Hauptkonfiguration
- `alembic.ini` - Datenbank-Migrations-Konfiguration
- `scripts/` - Deployment und Management-Scripts

## 📊 Verwendung

### Web Interface

```bash
# Haupt-Dashboard
http://localhost:8000/

# Analysis Cockpit
http://localhost:8000/admin/analysis

# Feed Management
http://localhost:8000/admin/feeds

# Auto-Analysis Dashboard
http://localhost:8000/admin/auto-analysis
```

### CLI Tools

```bash
# Service Management
./scripts/start-all-background.sh    # Alle Services starten
./scripts/stop-all.sh               # Alle Services stoppen
./scripts/status.sh                 # Status aller Services

# Workers
./scripts/start-worker.sh           # Analysis Worker starten
./scripts/start-scheduler.sh        # Feed Scheduler starten
```

## 📡 API Dokumentation

### Core Endpoints

#### Feed Management
```http
GET    /api/feeds              # Liste aller Feeds
POST   /api/feeds              # Neuen Feed erstellen
PUT    /api/feeds/{id}         # Feed aktualisieren
DELETE /api/feeds/{id}         # Feed löschen
```

#### Article Management
```http
GET    /api/items              # Artikel auflisten
GET    /api/items/{id}         # Einzelnen Artikel abrufen
POST   /api/items/search       # Artikel suchen
```

#### Analysis API
```http
POST   /api/analysis/selection    # Artikel-Auswahl erstellen
GET    /api/analysis/runs         # Analysis Runs auflisten
POST   /api/analysis/runs         # Neue Analyse starten
GET    /api/analysis/runs/{id}    # Run Status abrufen
POST   /api/analysis/runs/{id}/cancel  # Run abbrechen
```

#### Auto-Analysis API (Phase 2)
```http
POST   /api/feeds/{id}/toggle-auto-analysis  # Auto-Analysis aktivieren/deaktivieren
GET    /api/feeds/{id}/auto-analysis-status  # Auto-Analysis Status
GET    /api/auto-analysis/queue              # Queue Status
GET    /api/auto-analysis/history            # Auto-Analysis Historie
```

#### System Management
```http
GET    /api/analysis/manager/status     # System Status
POST   /api/analysis/manager/emergency-stop  # Notfall-Stop
POST   /api/analysis/manager/resume     # Betrieb fortsetzen
GET    /api/analysis/health            # Health Check
```

### HTMX Endpoints

```http
GET    /htmx/analysis/stats-horizontal    # Dashboard Statistiken
GET    /htmx/analysis/runs/active         # Aktive Runs
GET    /htmx/analysis/runs/history        # Run Historie
GET    /htmx/analysis/articles-live       # Live Artikel-Feed
GET    /htmx/auto-analysis/dashboard      # Auto-Analysis Dashboard
GET    /htmx/auto-analysis/queue          # Queue Status
GET    /htmx/auto-analysis/history        # Auto-Analysis Historie
```

### API Response Formats

```json
// Standard Success Response
{
  "success": true,
  "data": { ... },
  "message": "Optional message"
}

// Error Response
{
  "success": false,
  "error": "Error description",
  "detail": "Detailed error information"
}

// Analysis Run Response
{
  "id": 123,
  "status": "completed",
  "total_items": 50,
  "processed_count": 50,
  "error_count": 0,
  "created_at": "2025-09-28T12:00:00Z",
  "completed_at": "2025-09-28T12:05:00Z"
}
```

## 🗄️ Datenbank Schema

### Core Tables

#### feeds
```sql
CREATE TABLE feeds (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    url TEXT NOT NULL UNIQUE,
    status VARCHAR(20) DEFAULT 'ACTIVE',
    fetch_interval_minutes INTEGER DEFAULT 60,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

#### items
```sql
CREATE TABLE items (
    id SERIAL PRIMARY KEY,
    feed_id INTEGER REFERENCES feeds(id),
    title TEXT,
    link TEXT,
    description TEXT,
    author VARCHAR(255),
    published TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);
```

#### analysis_runs
```sql
CREATE TABLE analysis_runs (
    id SERIAL PRIMARY KEY,
    status VARCHAR(20) DEFAULT 'pending',
    scope_json JSONB,
    params_json JSONB,
    queued_count INTEGER DEFAULT 0,
    processed_count INTEGER DEFAULT 0,
    failed_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    started_at TIMESTAMP,
    completed_at TIMESTAMP
);
```

#### item_analysis
```sql
CREATE TABLE item_analysis (
    id SERIAL PRIMARY KEY,
    item_id INTEGER REFERENCES items(id),
    sentiment_json JSONB,
    urgency_json JSONB,
    impact_json JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);
```

#### pending_auto_analysis (Phase 2)
```sql
CREATE TABLE pending_auto_analysis (
    id SERIAL PRIMARY KEY,
    item_id INTEGER REFERENCES items(id),
    feed_id INTEGER REFERENCES feeds(id),
    priority INTEGER DEFAULT 5,
    status VARCHAR(20) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT NOW(),
    processed_at TIMESTAMP
);
```

### Indizes und Performance

```sql
-- Performance Indizes
CREATE INDEX idx_items_feed_id ON items(feed_id);
CREATE INDEX idx_items_published ON items(published);
CREATE INDEX idx_analysis_runs_status ON analysis_runs(status);
CREATE INDEX idx_item_analysis_item_id ON item_analysis(item_id);
CREATE INDEX idx_pending_auto_analysis_status ON pending_auto_analysis(status);
CREATE INDEX idx_pending_auto_analysis_feed_id ON pending_auto_analysis(feed_id);

-- Composite Indizes
CREATE INDEX idx_items_feed_published ON items(feed_id, published DESC);
CREATE INDEX idx_runs_status_created ON analysis_runs(status, created_at DESC);
CREATE INDEX idx_pending_auto_analysis_status_priority ON pending_auto_analysis(status, priority DESC);
```

### Migrations

```bash
# Neue Migration erstellen
alembic revision --autogenerate -m "Description"

# Migrations anwenden
alembic upgrade head

# Migration rückgängig machen
alembic downgrade -1

# History anzeigen
alembic history
```

## 🚀 Deployment

### Docker Deployment

```dockerfile
# Dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

```yaml
# docker-compose.yml
version: '3.8'
services:
  web:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://news_user:news_password@db:5432/news_db
    depends_on:
      - db

  db:
    image: postgres:15
    environment:
      POSTGRES_DB: news_db
      POSTGRES_USER: news_user
      POSTGRES_PASSWORD: news_password
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

### Production Setup

```bash
# Systemd Service
sudo cp deployment/news-mcp.service /etc/systemd/system/
sudo systemctl enable news-mcp
sudo systemctl start news-mcp

# Nginx Konfiguration
sudo cp deployment/nginx.conf /etc/nginx/sites-available/news-mcp
sudo ln -s /etc/nginx/sites-available/news-mcp /etc/nginx/sites-enabled/
sudo systemctl reload nginx
```

### Environment-spezifische Konfiguration

```bash
# Production
export ENVIRONMENT=production
export LOG_LEVEL=WARNING
export DATABASE_URL=postgresql://user:pass@prod-db:5432/news_db

# Development
export ENVIRONMENT=development
export LOG_LEVEL=DEBUG
export DATABASE_URL=postgresql://news_user:news_password@localhost/news_db
```

## 👨‍💻 Entwicklung

### Development Setup

```bash
# Development Dependencies
pip install -r requirements-dev.txt

# Pre-commit Hooks
pre-commit install

# Tests ausführen
pytest

# Code Formatting
black app/
isort app/

# Type Checking
mypy app/
```

### Projekt Struktur

```
news-mcp/
├── app/
│   ├── api/                    # API Routes
│   │   ├── analysis_management.py
│   │   ├── analysis_selection.py
│   │   ├── feeds.py            # Feed Management + Auto-Analysis
│   │   └── htmx.py
│   ├── core/                   # Core Konfiguration
│   │   ├── config.py
│   │   └── logging_config.py
│   ├── models/                 # SQLModel Definitionen
│   │   └── __init__.py
│   ├── services/               # Business Logic
│   │   ├── analysis_run_manager.py
│   │   ├── auto_analysis_service.py      # Auto-Analysis (Phase 2)
│   │   ├── pending_analysis_processor.py # Queue Processor
│   │   └── selection_cache.py
│   ├── web/                    # Web Views
│   │   ├── components/         # HTMX Komponenten
│   │   └── views/              # Page Views + Auto-Analysis Views
│   ├── worker/                 # Background Workers
│   │   └── analysis_worker.py
│   ├── database.py            # DB Connection
│   └── main.py                # FastAPI App
├── templates/                  # Jinja2 Templates
├── static/                     # Static Assets
├── scripts/                    # Management Scripts
├── alembic/                    # DB Migrations
├── tests/                      # Test Suite
└── docs/                       # Dokumentation
```

### Testing

```bash
# Unit Tests
pytest tests/unit/

# Integration Tests
pytest tests/integration/

# Test Coverage
pytest --cov=app

# Load Tests
locust -f tests/load/locustfile.py
```

### Git Workflow

```bash
# Feature Branch
git checkout -b feature/new-feature
git commit -m "feat: add new feature"
git push origin feature/new-feature

# Pull Request Review
# Nach Merge:
git checkout main
git pull origin main
git branch -d feature/new-feature
```

## 🏗️ Architektur

### System Übersicht

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Web Client    │    │   API Client    │    │   Admin UI      │
└─────────┬───────┘    └─────────┬───────┘    └─────────┬───────┘
          │                      │                      │
          └──────────────────────┼──────────────────────┘
                                 │
                    ┌─────────────▼─────────────┐
                    │      FastAPI Server      │
                    │   (app/main.py)         │
                    └─────────────┬─────────────┘
                                 │
                ┌────────────────┼────────────────┐
                │                │                │
       ┌────────▼────────┐ ┌─────▼─────┐ ┌───────▼───────┐
       │   API Routes    │ │ Services  │ │  Web Views    │
       │  (app/api/)     │ │(app/services/)│ (app/web/)   │
       └─────────────────┘ └───────────┘ └───────────────┘
                                 │
                    ┌─────────────▼─────────────┐
                    │     PostgreSQL DB        │
                    │   (feeds, items, etc.)   │
                    └───────────────────────────┘
```

### Service Architecture

```
Analysis Manager
├── Run Manager (Queue Management)
├── Selection Cache (In-Memory)
├── Worker Processes (Async)
└── Rate Limiting (API Protection)

Feed System
├── Feed Fetcher (RSS Parser)
├── Content Processor (Article Extraction)
├── Scheduler (Cron-like)
└── Health Monitor (Status Tracking)
```

### Data Flow

```
RSS Feeds → Feed Fetcher → Content Processor → Database
                                                    ↓
Selection Cache ← API Endpoints ← Analysis Manager ← Database
                     ↓
Web Interface ← HTMX Components ← Alpine.js State
```

## 📝 Contributing

### Code Standards

- **Python**: PEP 8, Type Hints, Docstrings
- **JavaScript**: ES6+, Alpine.js patterns
- **SQL**: Standardized naming conventions
- **Git**: Conventional Commits

### Pull Request Process

1. Fork das Repository
2. Erstelle Feature Branch
3. Implementiere Changes mit Tests
4. Führe Code Quality Checks aus
5. Erstelle Pull Request mit ausführlicher Beschreibung

### Issue Reporting

```markdown
**Bug Report Template:**
- Environment: Development/Production
- Python Version: 3.x
- Error Message: Full traceback
- Steps to Reproduce: 1, 2, 3...
- Expected vs Actual Behavior
```

## 📞 Support

- **Documentation**: [docs/](docs/)
- **Issues**: [GitHub Issues](https://github.com/your-org/news-mcp/issues)
- **Discussions**: [GitHub Discussions](https://github.com/your-org/news-mcp/discussions)

## 📄 License

Dieses Projekt ist unter der MIT License lizenziert - siehe [LICENSE](LICENSE) für Details.

## 🙏 Acknowledgments

- FastAPI Framework
- SQLModel ORM
- Alpine.js für reaktive UI
- Bootstrap für UI-Komponenten
- OpenAI für KI-Analyse

---

**News MCP** - Enterprise RSS Aggregation with AI Analysis