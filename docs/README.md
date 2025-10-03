# Documentation Index

This directory contains comprehensive documentation for the News MCP system.

## 📚 Core Documentation

### Getting Started
- **[Main README](../README.md)** - Project overview and quick start
- **[Developer Setup](../DEVELOPER_SETUP.md)** - Complete development environment setup
- **[Testing Guide](../TESTING.md)** - Testing strategies and procedures

### Architecture & Monitoring
- **[Monitoring & Feature Flags](../MONITORING.md)** - Feature flag system and performance monitoring
- **[Database ERD](../ERD_DIAGRAM.md)** - Entity relationship diagram
- **[Data Architecture](../DATA_ARCHITECTURE.md)** - Complete database architecture

### Technical Configuration
- **[pyproject.toml](../pyproject.toml)** - Project configuration and dependencies
- **[Pre-commit Config](../.pre-commit-config.yaml)** - Code quality automation
- **[Ruff Config](../.ruff.toml)** - Linting and formatting rules

## 🔄 Repository Migration Documentation

The system is currently migrating from Raw SQL to Repository Pattern. Key documents:

### Migration Architecture
- **Feature Flags**: Safe gradual rollout (5% → 100%)
- **Shadow Comparison**: A/B testing between implementations
- **Performance Monitoring**: P50/P95/P99 metrics with automatic fallback
- **Circuit Breaker**: Auto-disable on >5% error rate or >30% latency increase

### Migration Monitoring
```bash
# Real-time dashboard
python monitoring_dashboard.py

# API endpoints
curl "http://localhost:8000/api/admin/feature-flags/"
curl "http://localhost:8000/api/admin/feature-flags/metrics/dashboard"
```

## 🛠️ Auto-Generated Documentation

The following files are automatically maintained:

- **[API Documentation](./API_DOCUMENTATION.md)** - Complete REST API reference (Sep 2025)
- **[Database Schema](./DATABASE_SCHEMA.md)** - Full database structure with 28 tables (Sep 2025)
- **[API Examples](./API_EXAMPLES.md)** - Practical examples for all endpoints (Sep 2025)
- **[Feature Flags Reference](./FEATURE_FLAGS.md)** - Feature flag system documentation (Sep 2025)
- **[ERD Diagram](./ERD_MERMAID.md)** - Entity Relationship Diagram in Mermaid format (Sep 2025)

## 📁 Specialized Documentation

### Component-Specific
- **[Sentiment Analysis Guide](./SENTIMENT_GUIDE.md)** - ✨ NEW: Understanding sentiment scores, impact, and urgency
- **[Analysis Control Interface](./ANALYSIS_CONTROL_INTERFACE.md)** - ✨ NEW: Complete interface redesign documentation
- **[UI Components Guide](./UI_COMPONENTS_GUIDE.md)** - ✨ NEW: Bootstrap 5 + Alpine.js + HTMX patterns
- **[Schema Import Workaround](./SCHEMA_IMPORT_WORKAROUND.md)** - ✨ NEW: Current technical debt documentation
- **[MCP Server](../MCP_SERVER_README.md)** - Model Context Protocol server setup
- **[Worker System](./WORKER_README.md)** - Analysis worker documentation
- **[Repository Policy](./REPOSITORY_POLICY.md)** - Data access patterns

### Platform-Specific
- **[Windows Bridge Setup](../windows-bridge/)** - Windows integration guides
- **[Deployment Guide](../DEPLOYMENT.md)** - Production deployment

## 📦 Historical Documentation

Archived documentation is available in **[docs/archive/](./archive/)** including:
- Historical system fixes and recovery procedures
- Legacy SQLModel problem analysis
- Migration decision documentation

## 🔧 Development Workflow

### Documentation Maintenance

Documentation is automatically updated via GitHub Actions:

1. **API docs** regenerated on code changes
2. **Schema docs** updated on new migrations
3. **Dependencies** refreshed on package changes
4. **Validation** ensures no broken links

### Manual Updates

For major changes, update these core files:
- Main README.md architecture section
- DEVELOPER_SETUP.md for new tools/requirements
- MONITORING.md for new feature flags or metrics
- TESTING.md for new testing procedures

### Quality Standards

All documentation follows:
- **Markdown standards** with proper headers and formatting
- **Link validation** to prevent broken internal references
- **Example validation** to ensure code samples work
- **Currency checks** to identify outdated content

## 🎯 Documentation Goals

### Completeness
- ✅ Setup instructions for new developers
- ✅ Architecture overview for system understanding
- ✅ Testing procedures for quality assurance
- ✅ Monitoring guides for operations

### Accuracy
- ✅ Auto-generated content stays current
- ✅ Manual validation of examples
- ✅ Regular review of outdated content
- ✅ Version control for all changes

### Usability
- ✅ Clear navigation and indexing
- ✅ Progressive disclosure (basic → advanced)
- ✅ Task-oriented organization
- ✅ Searchable content structure

## 🚀 Quick Actions

```bash
# Setup development environment
./scripts/setup-dev.sh

# Run all tests including migration tests
python -m pytest -m migration

# Monitor repository migration
python monitoring_dashboard.py

# Validate documentation
pre-commit run --all-files

# Generate fresh API docs
python -c "from app.main import app; import json; print(json.dumps(app.openapi(), indent=2))" > docs/openapi.json
```

---

📖 **Tip**: Use GitHub's search functionality to find specific topics across all documentation files.