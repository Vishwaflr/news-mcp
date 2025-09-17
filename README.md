# News MCP - Dynamic RSS Management & Content Processing System

Ein vollständiger MCP-kompatibler Newsreader mit dynamischem Template-Management, intelligenter Inhaltsverarbeitung und Hot-Reload-Fähigkeit für Enterprise-Ready RSS-Feed-Aggregation.

## 🚀 Hauptfunktionen

### 🔥 Dynamic Template Management (Phase 2 - NEU!)
- **Database-driven Templates**: Alle Templates in der Datenbank, keine statischen YAML-Dateien
- **Hot-Reload Capability**: Konfigurationsänderungen ohne Service-Neustart
- **Web UI Management**: Vollständige Template-Verwaltung über moderne Web-Oberfläche
- **Auto-Assignment**: Automatische Template-Zuweisung basierend auf URL-Patterns
- **Built-in Templates**: Vorkonfigurierte Templates für Heise, Cointelegraph, Wall Street Journal
- **Configuration Change Tracking**: Vollständige Audit-Historie aller Template-Änderungen

### Core RSS Management
- **RSS Feed Management**: Feeds hinzufügen, kategorisieren und verwalten
- **Dynamic Scheduler**: Separater Scheduler-Service mit automatischer Konfigurationserkennung
- **Health Monitoring**: Überwachung der Feed-Gesundheit mit Metriken
- **Deduplizierung**: Automatische Erkennung doppelter Artikel
- **MCP Integration**: Vollständige MCP-Server-Implementation mit Tools

### Advanced Content Processing
- **Template-based Processing**: Flexible Feldmappings und Content-Regeln
- **Content Rules**: HTML-Extraktion, Text-Normalisierung, Tracking-Entfernung
- **Quality Filters**: Titel-Längen-Validierung und Content-Qualitätsprüfung
- **Multi-Source Support**: Universelle Template-Engine für verschiedene RSS-Formate
- **Real-time Configuration**: Sofortige Anwendung von Template-Änderungen

### 🎛️ Enterprise Management Interface
- **Template Management**: HTMX-basierte Template-Erstellung und -Bearbeitung
- **Feed Assignment**: Drag-and-Drop Template-Zuweisung zu Feeds
- **Configuration Dashboard**: Real-time Status aller Templates und Zuweisungen
- **Statistics & Analytics**: Detaillierte Auswertungen der Template-Performance
- **Health Monitoring**: Real-time Status aller Feeds und Scheduler-Instanzen

### 🏗️ Robuste Architektur
- **Microservices**: Separate Services für Web-UI und Scheduler
- **Configuration Drift Detection**: Automatische Erkennung von Konfigurationsänderungen
- **Concurrent Processing**: Batch-limitierte parallele Feed-Verarbeitung
- **Error Recovery**: Automatische Wiederherstellung bei Service-Fehlern
- **Production-Ready**: PostgreSQL-Unterstützung und Skalierbarkeit

## 🏛️ Architektur

```
├── data/                    # 🗄️ Lokale Datenbank-Speicherung
│   └── postgres/            # PostgreSQL Datenverzeichnis (automatisch erstellt)
├── app/                     # FastAPI Web-API und Admin-Interface
│   ├── api/                # REST API Endpunkte
│   │   ├── feeds.py           # Feed Management API
│   │   ├── items.py           # Artikel API
│   │   ├── health.py          # Health Monitoring API
│   │   ├── categories.py      # Kategorien API
│   │   ├── sources.py         # Quellen API
│   │   └── htmx.py           # HTMX Interface Endpunkte
│   ├── routes/             # 🔥 Template Management Routes
│   │   └── templates.py       # Template CRUD Operations
│   ├── services/           # 🔥 Core Services (NEU!)
│   │   ├── dynamic_template_manager.py    # Template Management
│   │   ├── configuration_watcher.py       # Config Change Detection
│   │   ├── feed_change_tracker.py         # Change Audit System
│   │   └── content_processing/            # Content Processing Pipeline
│   ├── models.py           # SQLModel Datenmodelle (erweitert)
│   ├── database.py         # Datenbank-Setup
│   └── main.py             # FastAPI App
├── jobs/                   # 🔥 Dynamic Background Services
│   ├── fetcher.py             # RSS Feed Fetcher (mit Dynamic Templates)
│   ├── dynamic_scheduler.py   # Hot-Reload Scheduler Service
│   └── scheduler_manager.py   # Scheduler CLI Management
├── mcp_server/             # MCP Server Implementation
│   └── server.py              # MCP Tools und Server
├── templates/              # Jinja2 Templates
│   ├── admin/              # Enterprise Admin Interface
│   │   ├── templates.html     # 🔥 Template Management UI
│   │   ├── feeds.html         # Feed Management
│   │   ├── items.html         # Artikel Stream
│   │   └── health.html        # Health Dashboard
│   └── htmx/               # 🔥 HTMX Partial Templates
│       └── templates_list.html # Dynamic Template Lists
└── systemd/                # Systemd Service Units
```

## Schnellstart

### 1. Installation

```bash
# Repository klonen
git clone <repository-url>
cd news-mcp

# Python Virtual Environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Datenbank starten

```bash
# PostgreSQL mit Docker Compose starten
docker compose up -d

# Warten bis PostgreSQL bereit ist
sleep 5
```

### 3. Konfiguration

```bash
cp .env.example .env
# .env bearbeiten nach Bedarf (PostgreSQL ist bereits konfiguriert)
```

### 4. Services starten

```bash
# Python Virtual Environment aktivieren
source venv/bin/activate

# Web-API Server (Terminal 1)
PYTHONPATH=/home/cytrex/news-mcp python3 app/main.py

# Dynamic Scheduler (Terminal 2)
python3 jobs/scheduler_manager.py start

# Optional: MCP Server (Terminal 3)
python3 mcp_server/server.py
```

### 5. Web Interface öffnen

```bash
# Template Management
http://localhost:8000/admin/templates

# Feed Management
http://localhost:8000/admin/feeds

# Dashboard
http://localhost:8000/
```

## 🔥 Dynamic Template System

### Template Erstellung über Web UI

1. **Web Interface öffnen**: http://localhost:8000/admin/templates
2. **Template erstellen**:
   - **Name**: Eindeutiger Template-Name
   - **Description**: Optionale Beschreibung
   - **URL Patterns**: Regex-Patterns für Auto-Assignment (z.B. `.*heise\.de.*`)
   - **Field Mappings**: RSS-zu-DB Feldmappings (z.B. `entry.title` → `title`)
   - **Content Rules**: HTML-Extraktion, Text-Normalisierung, Tracking-Entfernung
   - **Quality Filters**: Min/Max Titel-Länge

3. **Template zuweisen**:
   - Automatisch via URL-Patterns
   - Manuell über Assign-Dropdown

### CLI Template Management

```bash
# Scheduler Status anzeigen
python jobs/scheduler_manager.py status

# Detaillierte Konfiguration
python jobs/scheduler_manager.py config

# Scheduler mit Debug-Logging starten
python jobs/scheduler_manager.py start --debug
```

### Built-in Templates

Das System enthält vorkonfigurierte Templates für:

- **Heise Online** (`.*heise\.de.*`)
- **Cointelegraph** (`.*cointelegraph\.com.*`)
- **Wall Street Journal** (`.*feeds\.content\.dowjones\.io.*`)

## 🗄️ Datenmodell

### 🔥 Dynamic Template System (NEU!)

#### DynamicFeedTemplate
```sql
- id: Primary Key
- name: Eindeutiger Template-Name
- description: Optionale Beschreibung
- url_patterns: JSON Array von URL-Patterns
- field_mappings: JSON Object mit RSS→DB Feldmappings
- content_processing_rules: JSON Array von Processing-Regeln
- is_active: Aktivitätsstatus
- is_builtin: Built-in Template Marker
- created_at/updated_at: Zeitstempel
```

#### FeedTemplateAssignment
```sql
- id: Primary Key
- feed_id: Foreign Key zu feeds
- template_id: Foreign Key zu dynamic_feed_templates
- assigned_by: Zuweisender User/System
- is_active: Aktivitätsstatus
- created_at: Zuweisungszeitpunkt
```

#### FeedConfigurationChange
```sql
- id: Primary Key
- change_type: ENUM (feed_created, template_assigned, etc.)
- feed_id: Optional Foreign Key
- template_id: Optional Foreign Key
- change_data: JSON mit Details
- changed_by: User/System
- created_at: Änderungszeitpunkt
```

#### FeedSchedulerState
```sql
- instance_id: Scheduler-Instanz ID
- is_active: Aktivitätsstatus
- last_heartbeat: Letzter Heartbeat
- configuration_hash: Hash der aktuellen Konfiguration
- feeds_count/templates_count: Konfigurationsmetriken
```

### Bestehende Tabellen (erweitert)
- **sources**: Übergeordnete Quellen
- **feeds**: RSS-Feeds (erweitert um next_fetch_scheduled, configuration_hash)
- **categories**: Feed-Kategorien
- **items**: Nachrichtenartikel
- **fetch_log**: Feed-Abruf-Historie
- **feed_health**: Health-Metriken

## MCP Tools

### Template Management
```json
{
  "tool": "list_templates",
  "parameters": {
    "active_only": true,
    "include_assignments": true
  }
}
```

### Feed Management
```json
{
  "tool": "add_feed",
  "parameters": {
    "url": "https://example.com/rss",
    "categories": ["tech", "news"],
    "title": "Tech News",
    "fetch_interval_minutes": 60
  }
}
```

### Content Retrieval
```json
{
  "tool": "fetch_latest",
  "parameters": {
    "limit": 20,
    "categories": ["crypto"],
    "since_hours": 24
  }
}
```

## 🚀 Deployment

### Production Setup

1. **PostgreSQL Datenbank** (lokal im Projekt):
```bash
# Daten werden automatisch in ./data/postgres/ gespeichert
docker compose up -d
```

2. **Systemd Services**:
```bash
sudo cp systemd/*.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable news-api news-scheduler news-mcp
sudo systemctl start news-api news-scheduler news-mcp
```

3. **Monitoring**:
```bash
# Service Status
sudo systemctl status news-api news-scheduler news-mcp

# Logs
sudo journalctl -u news-api -f
sudo journalctl -u news-scheduler -f
```

### Docker Deployment

```dockerfile
# Dockerfile für Web-API
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "app/main.py"]
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
      - DATABASE_URL=postgresql://user:pass@db/newsdb
    depends_on:
      - db

  scheduler:
    build: .
    command: python jobs/scheduler_manager.py start
    depends_on:
      - db

  db:
    image: postgres:15
    environment:
      POSTGRES_DB: newsdb
      POSTGRES_USER: user
      POSTGRES_PASSWORD: pass
```

## 🔧 Entwicklung

### Development Setup
```bash
# Development Server mit Auto-Reload
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Scheduler Development Mode
python jobs/scheduler_manager.py start --debug

# Template Testing
python -c "
from app.services.dynamic_template_manager import get_dynamic_template_manager
from app.database import engine
from sqlmodel import Session

with Session(engine) as session:
    with get_dynamic_template_manager(session) as manager:
        templates = manager.get_all_templates()
        print(f'Found {len(templates)} templates')
"
```

### Testing
```bash
# Unit Tests (wenn implementiert)
pytest tests/

# Integration Tests
python jobs/scheduler_manager.py config --json

# Template Validation
curl -X GET http://localhost:8000/htmx/templates-list
```

## 📈 Monitoring & Analytics

### Web Dashboard
- **Template Performance**: http://localhost:8000/admin/templates
- **Feed Health**: http://localhost:8000/admin/health
- **System Status**: http://localhost:8000/admin/feeds

### CLI Monitoring
```bash
# Scheduler Status
python jobs/scheduler_manager.py status

# Configuration Details
python jobs/scheduler_manager.py config

# Real-time Logs
tail -f /tmp/news-mcp-scheduler.log
```

### API Monitoring
```bash
# Health Check
curl http://localhost:8000/api/health

# Template Status
curl http://localhost:8000/htmx/templates-list

# System Statistics
curl http://localhost:8000/htmx/system-status
```

## 🔒 Security

- **Input Validation**: Alle Template-Parameter werden validiert
- **SQL Injection Protection**: SQLModel/SQLAlchemy ORM
- **XSS Protection**: Template-Output wird escaped
- **CORS Configuration**: Konfigurierbare CORS-Einstellungen
- **Rate Limiting**: Optional für API-Endpunkte

## 📝 Changelog

### Phase 2 - Dynamic Template Management (Aktuell)
- ✅ Database-driven Template System
- ✅ Hot-Reload Scheduler Service
- ✅ Web UI für Template Management
- ✅ Configuration Change Tracking
- ✅ Automated Template Assignment
- ✅ Built-in Templates für Major Sources

### Phase 1 - Core RSS Management
- ✅ Basic RSS Feed Management
- ✅ Content Processing Pipeline
- ✅ MCP Server Implementation
- ✅ Web Interface
- ✅ Health Monitoring

## 🚧 Roadmap (Phase 3)

### Advanced Analytics & Monitoring
- Feed Performance Dashboards
- Content Analysis & Trending
- Advanced Health Monitoring
- Usage Analytics

### Content Intelligence
- AI-based Categorization
- Cross-Feed Duplicate Detection
- Content Quality Scoring
- Automatic Summarization

### Multi-User & API Extensions
- User Management & Authentication
- External API Integration
- Feed Sharing & Collaboration
- API Rate Limiting & Caching

## 📄 Lizenz

MIT License - siehe [LICENSE](LICENSE) für Details.

## 🤝 Contributing

Contributions sind willkommen! Bitte lesen Sie [CONTRIBUTING.md](CONTRIBUTING.md) für Details.

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/your-repo/issues)
- **Discussions**: [GitHub Discussions](https://github.com/your-repo/discussions)
- **Documentation**: [Wiki](https://github.com/your-repo/wiki)