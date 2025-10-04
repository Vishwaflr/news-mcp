# Documentation Index

**Last Updated:** 2025-10-04
**Structure Version:** 2.0 (Reorganized for clarity)

This directory contains comprehensive documentation for the News-MCP system.

---

## 📚 Quick Navigation

### **Getting Started**
- **[Main README](../README.md)** - Project overview and quick start
- **[Developer Setup](core/DEVELOPER_SETUP.md)** - Complete development environment setup
- **[Deployment Guide](core/DEPLOYMENT.md)** - Production deployment instructions

### **Core Documentation**
Located in `/docs/core/`
- **[Architecture](core/ARCHITECTURE.md)** - System architecture and design
- **[Database Schema](core/Database-Schema.md)** - Complete database structure (35 tables)
- **[Deployment](core/DEPLOYMENT.md)** - Deployment strategies
- **[Developer Setup](core/DEVELOPER_SETUP.md)** - Development environment

### **Features Documentation**
Located in `/docs/features/`
- **[Auto-Analysis Guide](features/AUTO_ANALYSIS_GUIDE.md)** - Automatic article analysis system
- **[Sentiment Guide](features/SENTIMENT_GUIDE.md)** - Sentiment analysis scoring
- **[Special Reports Flow](features/Special-Reports-Flow.md)** - LLM-based report generation
- **[Feature Flags](features/FEATURE_FLAGS.md)** - Feature flag system
- **[Feed Management Redesign](features/Feed-Management-Redesign-Plan.md)** - Feed UI V2 lessons learned

### **Guides & Tutorials**
Located in `/docs/guides/`
- **[UI Components Guide](guides/UI_COMPONENTS_GUIDE.md)** - Bootstrap 5 + Alpine.js + HTMX patterns
- **[Worker System](guides/WORKER_README.md)** - Background worker documentation
- **[Playwright MCP Setup](guides/PLAYWRIGHT_MCP_SETUP.md)** - End-to-end testing setup
- **[Claude CLI Config](guides/CLAUDE_CLI_PLAYWRIGHT_CONFIG.md)** - Claude Code integration
- **[Open WebUI Integration](guides/OPEN_WEBUI_INTEGRATION.md)** - WebUI integration guide

### **Operations**
Located in `/docs/operations/`
- **[Backup Strategy](operations/Backup-Strategy.md)** - Database backup procedures
- **[Database Rebuild 2025-10-04](operations/Database-Rebuild-2025-10-04.md)** - Recovery documentation
- **[Baseline Metrics](operations/BASELINE_METRICS.md)** - Performance baseline

---

## 📋 Top-Level Documents

### **Navigation & Reference**
- **[CLAUDE.md](../CLAUDE.md)** - Working rules for Claude Code (internal)
- **[NAVIGATOR.md](../NAVIGATOR.md)** - System overview and roadmap (v4.5.0)
- **[ENDPOINTS.md](../ENDPOINTS.md)** - Complete API reference (v4.1.0, 260+ endpoints)
- **[INDEX.md](../INDEX.md)** - File map (optional)

### **Project Docs**
- **[README.md](../README.md)** - Main project documentation
- **[CONTRIBUTING.md](../CONTRIBUTING.md)** - Contributing guidelines
- **[SECURITY.md](../SECURITY.md)** - Security policy

### **Roadmap**
- **[ROADMAP_OVERVIEW.md](../ROADMAP_OVERVIEW.md)** - High-level roadmap
- **[ROADMAP_SPRINT1.md](../ROADMAP_SPRINT1.md)** - Sprint 1 details

---

## 🗂️ Planning & Analysis Docs

These documents guide ongoing refactoring and feature development:

- **[CODEBASE_MAP.md](CODEBASE_MAP.md)** - Code structure analysis
- **[CLEANUP_POLICY.md](CLEANUP_POLICY.md)** - Code quality policies
- **[REFACTOR_PLAN.md](REFACTOR_PLAN.md)** - Step-by-step refactoring plan
- **[DEPRECATIONS.md](DEPRECATIONS.md)** - Deprecated features tracker
- **[GEOPOLITICAL_ANALYSIS_PLAN.md](GEOPOLITICAL_ANALYSIS_PLAN.md)** - Geopolitical feature plan
- **[GEOPOLITICAL_IMPLEMENTATION_SUMMARY.md](GEOPOLITICAL_IMPLEMENTATION_SUMMARY.md)** - Implementation summary

---

## 📦 Archive

Historical documentation and outdated files are in `/docs/archive/`:

- **Old API Docs:** `API_DOCUMENTATION.md`, `API_EXAMPLES.md` (superseded by ENDPOINTS.md)
- **Old Schema Docs:** `DATABASE_SCHEMA_2025-09-27.md`, `ERD_MERMAID.md` (integrated into Database-Schema.md)
- **Progress Logs:** `SPRINT1_PROGRESS.md`, `DOCUMENTATION_UPDATE_SUMMARY.md`, `WIKI_UPDATE_SUMMARY.md`
- **Legacy Fixes:** `FIXES_DOCUMENTATION.md`, `sqlproblem.md`, `PROGRESS.md`

See **[archive/README.md](archive/README.md)** for full archive index.

---

## 🔍 Technical Debt & Workarounds

Documents tracking known issues and temporary solutions:

- **[SCHEMA_IMPORT_WORKAROUND.md](SCHEMA_IMPORT_WORKAROUND.md)** - SQLModel circular import workaround
- **[SCHEMA_REFLECTION_ARCHITECTURE.md](SCHEMA_REFLECTION_ARCHITECTURE.md)** - Schema reflection patterns
- **[ANALYSIS_CONTROL_INTERFACE.md](ANALYSIS_CONTROL_INTERFACE.md)** - Analysis UI interface docs

---

## 📊 Current System Status

**Version:** 4.5.0 (2025-10-04)
**Total Tables:** 35
**Total Endpoints:** 260+
**Services Running:**
- ✅ API Server (FastAPI, Port 8000)
- ✅ Analysis Worker (Background)
- ✅ Feed Scheduler (RSS Fetching)
- ✅ Content Generator Worker (LLM Reports)

**Active Features:**
- ✅ Auto-Analysis (12 feeds)
- ✅ Special Reports (Phase 3 complete)
- ✅ Feed Management V2
- ✅ Sentiment & Impact Analysis
- ✅ Geopolitical Analysis (17.67% coverage)

---

## 🎯 Documentation Goals

### Completeness
- ✅ Setup instructions for new developers
- ✅ Architecture overview for system understanding
- ✅ Testing procedures for quality assurance
- ✅ Operations guides for production

### Accuracy
- ✅ Auto-generated content stays current
- ✅ Manual validation of examples
- ✅ Regular review cycles
- ✅ Version control for all changes

### Usability
- ✅ Clear navigation and indexing (NEW: organized by topic)
- ✅ Progressive disclosure (basic → advanced)
- ✅ Task-oriented organization
- ✅ Searchable content structure

---

## 🚀 Quick Actions

```bash
# Setup development environment
./scripts/setup-dev.sh

# Start all services
./scripts/start-api.sh
./scripts/start-worker.sh
./scripts/start-scheduler.sh

# Run tests
pytest tests/ -v
npx playwright test tests/e2e/ --reporter=line

# Check database schema
psql -h localhost -U cytrex -d news_db -c "\dt"

# View API documentation
# Open: http://localhost:8000/docs
```

---

## 📞 Need Help?

- **API Questions:** See [ENDPOINTS.md](../ENDPOINTS.md)
- **Architecture Questions:** See [core/ARCHITECTURE.md](core/ARCHITECTURE.md)
- **Setup Issues:** See [core/DEVELOPER_SETUP.md](core/DEVELOPER_SETUP.md)
- **Feature Documentation:** Browse `/docs/features/`
- **Operational Issues:** See `/docs/operations/`

---

**📖 Tip:** Use GitHub's search functionality (Ctrl/Cmd+K) to find specific topics across all documentation files.
