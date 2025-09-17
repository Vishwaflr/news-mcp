# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [2.1.0] - 2025-01-17 - PostgreSQL Migration & UI Fixes

### ✨ Major Features Added

#### Database Migration to PostgreSQL
- **Local Project Database**: PostgreSQL now runs locally in `./data/postgres/` directory
- **Docker Compose Integration**: Simple setup with `docker compose up -d`
- **Automatic Migration**: Seamless transition from SQLite to PostgreSQL
- **Production-Ready**: Enhanced performance and scalability with PostgreSQL

#### Bug Fixes & UI Improvements
- **Feed Interval Editing**: Fixed critical bug where interval changes via UI weren't working
- **Form-Based API Endpoints**: Added `/api/feeds/{feed_id}/form` for proper form data handling
- **HTMX Form Updates**: Updated all HTMX forms to use form data instead of JSON
- **User Experience**: Fully tested 5-minute interval changes through UI

### 🔧 Changed
- **Default Database**: PostgreSQL is now the default database (was: SQLite)
- **Configuration Files**: Updated .env.example with PostgreSQL settings
- **API Host**: Changed default host to 192.168.178.72 for local network access
- **Fetch Intervals**: Reduced default interval from 60 to 15 minutes
- **Concurrent Fetches**: Increased from 5 to 10 for better performance
- **Docker Compose**: Updated for local PostgreSQL storage in project directory

### 🐛 Fixed
- **Feed Interval Update Bug**: Fixed UI bug where interval changes weren't being saved
  - Added form-based PUT endpoint for proper form data handling
  - Updated HTMX forms to submit form data instead of JSON
  - Tested and verified 5-minute interval changes work correctly
- **Database Session Issues**: Improved session handling in feed processing
- **Content Processing Isolation**: Enhanced transaction isolation for better error handling
- **SQLite Dependencies**: Removed all SQLite-specific connection parameters

### 🗑️ Removed
- **SQLite Support**: Complete migration to PostgreSQL-only setup
- **SQLite Files**: Cleaned up all .db and .sqlite files from project
- **Legacy Configuration**: Removed SQLite-specific database parameters
- **Python Cache**: Cleaned up __pycache__ directories and temp files

### 📚 Documentation Updates
- **README.md**: Complete rewrite with PostgreSQL setup instructions
- **DEPLOYMENT.md**: Added PostgreSQL deployment options and local database setup
- **.env.example**: Updated with current PostgreSQL configuration
- **.gitignore**: Enhanced data directory handling with proper exclusions

### 🧪 Testing Completed
- ✅ Backend API health endpoints functionality
- ✅ Frontend admin interfaces with Playwright MCP automation
- ✅ Heise.de feed processing and template assignment
- ✅ Dynamic scheduler functionality and hot-reload
- ✅ Feed interval editing through UI (5-minute test)
- ✅ MCP server integration and tools
- ✅ PostgreSQL database migration and performance
- ✅ Docker Compose local development setup

### Technical Details
- **Files Modified**: 17 files updated including core config, API endpoints, and documentation
- **Database**: Moved from SQLite to PostgreSQL with local project storage
- **Session Handling**: Improved database session isolation in feed processing
- **Error Recovery**: Enhanced error handling in content processing pipeline
- **Architecture**: Maintained microservices approach with better database integration

## [2.0.0] - 2025-09-16 - Dynamic Template Management

### 🔥 Major Features Added

#### Dynamic Template System
- **Database-driven Templates**: Replaced static YAML templates with dynamic database-stored templates
- **Hot-Reload Capability**: Configuration changes apply without service restart
- **Web UI Management**: Complete template management via HTMX-powered web interface
- **Auto-Assignment**: Automatic template assignment based on URL patterns
- **Built-in Templates**: Pre-configured templates for Heise, Cointelegraph, Wall Street Journal

#### Template Management Features
- Template CRUD operations via web interface
- Field mapping configuration (RSS → Database)
- Content processing rules (HTML extraction, text normalization, tracking removal)
- Quality filters (title length validation)
- Template assignment to feeds with dropdown interface
- Configuration change tracking and audit trail

#### Architecture Improvements
- **Dynamic Scheduler Service**: Separate scheduler with configuration drift detection
- **Hot Configuration Reload**: Real-time configuration updates without downtime
- **Configuration Change Tracking**: Full audit history of all template changes
- **Microservices Architecture**: Separate services for web UI and scheduler
- **Concurrent Processing**: Batch-limited parallel feed processing

### Added

#### Core Services
- `app/services/dynamic_template_manager.py` - Template CRUD and management
- `app/services/configuration_watcher.py` - Configuration change detection
- `app/services/feed_change_tracker.py` - Change audit system
- `jobs/dynamic_scheduler.py` - Hot-reload scheduler service
- `jobs/scheduler_manager.py` - Scheduler CLI management interface

#### Database Models
- `DynamicFeedTemplate` - Template storage and configuration
- `FeedTemplateAssignment` - Template-to-feed assignments
- `FeedConfigurationChange` - Configuration change log
- `FeedSchedulerState` - Scheduler state tracking

#### Web Interface
- `templates/admin/templates.html` - Template management interface
- `templates/htmx/templates_list.html` - Dynamic template list partial
- `app/routes/templates.py` - Template management routes

#### CLI Tools
- Template status monitoring (`python jobs/scheduler_manager.py status`)
- Configuration inspection (`python jobs/scheduler_manager.py config`)
- Debug mode support (`python jobs/scheduler_manager.py start --debug`)

### Changed
- **RSS Fetcher Integration**: Updated to use dynamic templates instead of static YAML
- **Field Mapping System**: Improved dot-notation field extraction with prefix handling
- **Content Processing**: Integrated template-based processing rules
- **Configuration System**: Enhanced with hot-reload and drift detection
- **Web Interface**: Updated navigation to include template management

### Removed
- `app/templates/template_engine.py` - Old static template engine
- `app/templates/*.yaml` - Static YAML template files (heise.yaml, cointelegraph.yaml, wsj.yaml)
- `/available-templates` HTMX endpoint - Replaced with dynamic template system
- `CONTENT_PROCESSING.md` - Outdated documentation (integrated into main README)

### Fixed
- **UNIQUE Constraint Handling**: Improved duplicate item detection and handling
- **Session Management**: Fixed DetachedInstanceError with FetchLog
- **Feed Status Updates**: Ensured ACTIVE status on successful fetches
- **Template Field Mapping**: Fixed RSS field extraction with entry prefix handling
- **Import Conflicts**: Resolved template router naming conflicts

### Technical Improvements
- **Database Performance**: Enhanced with configuration hash-based change detection
- **Error Handling**: Improved rollback and continuation on constraint violations
- **Logging**: Enhanced with configuration change tracking
- **Testing**: Added comprehensive template management testing with Playwright MCP
- **Documentation**: Complete rewrite of README and addition of deployment guide

## [1.0.0] - 2025-09-15 - Core RSS Management

### Added

#### Initial Features
- **RSS Feed Management**: Complete CRUD operations for RSS feeds
- **Content Processing Pipeline**: Modular content processing with specialized processors
- **MCP Integration**: Full MCP server implementation with tools
- **Web Interface**: HTMX-based admin interface for feed management
- **Health Monitoring**: Feed health tracking and metrics

#### Core Components
- `app/main.py` - FastAPI application
- `app/models.py` - SQLModel data models
- `app/database.py` - Database configuration
- `jobs/fetcher.py` - RSS feed fetcher
- `jobs/scheduler.py` - APScheduler integration
- `mcp_server/server.py` - MCP server implementation

#### Content Processors
- `app/processors/universal.py` - Universal content processor
- `app/processors/heise.py` - Heise Online specialized processor
- `app/processors/cointelegraph.py` - Cointelegraph specialized processor
- `app/processors/manager.py` - Content processing manager

#### Web Interface
- `templates/admin/feeds.html` - Feed management interface
- `templates/admin/items.html` - Article stream interface
- `templates/admin/health.html` - Health monitoring dashboard
- `app/api/htmx.py` - HTMX endpoints

#### Database Models
- `Feed` - RSS feed configuration
- `Item` - News articles
- `FetchLog` - Feed fetch history
- `FeedHealth` - Health metrics
- `Source` - Feed sources
- `Category` - Feed categorization

#### MCP Tools
- `list_feeds` - List all RSS feeds
- `add_feed` - Add new RSS feed
- `fetch_latest` - Get latest articles
- `search` - Search articles
- `feed_health` - Get feed health status
- `system_status` - System overview

### Features
- **Automatic Deduplication**: Content hash-based duplicate detection
- **Health Monitoring**: Success rates, response times, uptime tracking
- **Content Processing**: HTML entity decoding, text normalization
- **Categorization**: Feed categorization and filtering
- **Batch Processing**: Efficient bulk feed processing
- **Error Recovery**: Automatic retry and error handling

### Technical Specifications
- **Framework**: FastAPI with SQLModel ORM
- **Database**: SQLite (development) / PostgreSQL (production)
- **Frontend**: HTMX with Bootstrap 5
- **Background Jobs**: APScheduler
- **Content Processing**: Modular processor pipeline
- **MCP Compatibility**: Full MCP protocol implementation

---

## Legend

- 🔥 **Major Feature** - Significant new functionality
- ✅ **Enhancement** - Improvement to existing feature
- 🐛 **Bug Fix** - Bug fix or error correction
- 🔧 **Technical** - Technical improvement or refactoring
- 📝 **Documentation** - Documentation update
- ⚠️ **Breaking Change** - Backward incompatible change
- 🗑️ **Deprecated** - Feature marked for removal