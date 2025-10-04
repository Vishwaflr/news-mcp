# Documentation Archive

**Last Updated:** 2025-10-04
**Purpose:** Historical documentation and superseded files

This directory contains documentation that is no longer actively used but is preserved for historical reference and context.

---

## 📦 Recently Archived (2025-10-04)

### **Old API Documentation** (Superseded by ENDPOINTS.md)
- **`API_DOCUMENTATION.md`** - Auto-generated API docs (replaced by ENDPOINTS.md v4.1.0)
- **`API_EXAMPLES.md`** - API usage examples (integrated into ENDPOINTS.md)

### **Old Schema Documentation** (Integrated into Database-Schema.md)
- **`DATABASE_SCHEMA_2025-09-27.md`** - Auto-generated schema (943 lines, 29 tables)
  - Superseded by: `docs/core/Database-Schema.md` (764 lines, 35 tables, manually curated)
- **`ERD_MERMAID.md`** - Entity Relationship Diagram in Mermaid format
  - Now integrated into `docs/core/Database-Schema.md`

### **Progress & Status Logs** (Completed work)
- **`SPRINT1_PROGRESS.md`** - Sprint 1 progress tracking (completed 2025-10-03)
- **`DOCUMENTATION_UPDATE_SUMMARY.md`** - Documentation update log (2025-10-03)
- **`WIKI_UPDATE_SUMMARY.md`** - Wiki synchronization log (2025-10-03)

---

## 📦 Legacy Archive (Pre-2025-10-04)

### **System Recovery Documentation**
- **`FIXES_DOCUMENTATION.md`** - Historical bug fixes and emergency recovery procedures
  - System restoration from 4.4% to 95% health
  - PostgreSQL schema synchronization
  - Circular import resolution
  - Feed system recovery

### **Technical Debt Analysis**
- **`sqlproblem.md`** - SQLModel compatibility problem analysis (resolved via Repository Pattern)
  - BaseTableModel vs. Database schema discrepancies
  - Model definition inconsistencies
  - Raw SQL workaround documentation

### **Implementation Plans** (Completed)
- **`IMPLEMENTATION_PLAN_SKIP_LOGIC.md`** - Skip logic implementation plan (feature implemented)
- **`PROGRESS.md`** - Old progress tracking format (replaced by NAVIGATOR.md)

---

## 🗂️ Why Documents Are Archived

### **Superseded**
- Newer, better versions exist in active documentation
- Content consolidated into comprehensive guides
- Auto-generated docs replaced by manually curated versions

### **Completed**
- Implementation plans fully executed
- Progress logs for finished sprints
- One-time migration/update logs

### **Obsolete**
- Technical issues resolved
- Workarounds no longer needed
- Emergency procedures superseded by stable architecture

---

## 📍 Active Documentation Location

All current documentation is organized in:

- **`/docs/core/`** - Architecture, Database Schema, Setup, Deployment
- **`/docs/features/`** - Auto-Analysis, Sentiment, Special Reports, Feature Flags
- **`/docs/guides/`** - UI Components, Workers, Testing, Playwright, Integrations
- **`/docs/operations/`** - Backups, Recovery Procedures, Baseline Metrics

See **[docs/README.md](../README.md)** for the complete documentation index.

---

## 📋 Full Archive Index

| File | Date Archived | Reason | Superseded By |
|------|---------------|--------|---------------|
| **2025-10-04 Cleanup** | | | |
| `API_DOCUMENTATION.md` | 2025-10-04 | Redundant with ENDPOINTS.md | `../ENDPOINTS.md` |
| `API_EXAMPLES.md` | 2025-10-04 | Integrated into ENDPOINTS.md | `../ENDPOINTS.md` |
| `DATABASE_SCHEMA_2025-09-27.md` | 2025-10-04 | Auto-generated, older version | `../core/Database-Schema.md` |
| `ERD_MERMAID.md` | 2025-10-04 | Integrated into schema docs | `../core/Database-Schema.md` |
| `SPRINT1_PROGRESS.md` | 2025-10-04 | Sprint completed | `../NAVIGATOR.md` (Phase 2 ✅) |
| `DOCUMENTATION_UPDATE_SUMMARY.md` | 2025-10-04 | One-time update log | N/A (completed task) |
| `WIKI_UPDATE_SUMMARY.md` | 2025-10-04 | One-time sync log | N/A (completed task) |
| **Legacy** | | | |
| `FIXES_DOCUMENTATION.md` | Pre-2025 | Historical recovery | `../NAVIGATOR.md` (stable system) |
| `sqlproblem.md` | Pre-2025 | Resolved technical issue | Repository Pattern |
| `PROGRESS.md` | Pre-2025 | Old progress format | `../NAVIGATOR.md` |
| `IMPLEMENTATION_PLAN_SKIP_LOGIC.md` | Pre-2025 | Implementation complete | N/A (feature live) |

---

## 🔍 When to Consult Archived Docs

### **Historical Context**
- Understanding how a problem was solved in the past
- Reviewing the evolution of system architecture
- Learning from past implementation decisions

### **Recovery Scenarios**
- Need to restore old functionality
- Investigating regression issues
- Comparing current vs. historical approaches

### **Research & Audit**
- Studying system evolution
- Understanding design decision rationale
- Audit trails for major changes

---

## 🎓 Key Historical Lessons

### **From System Recovery** (`FIXES_DOCUMENTATION.md`, `sqlproblem.md`)
1. **Hybrid SQL architectures are fragile** → Migrated to Repository Pattern
2. **Emergency fixes create technical debt** → Systematic refactoring needed
3. **Schema sync is critical** → Automated validation now in place

### **From Documentation Cleanup** (2025-10-04)
1. **Consolidate auto-generated docs** → Single source of truth (ENDPOINTS.md, Database-Schema.md)
2. **Organize by topic, not chronology** → `core/`, `features/`, `guides/`, `operations/`
3. **Archive completed work** → Keep history, but separate from active docs

### **From Migration to Repository Pattern**
- Feature flags enable safe gradual rollout
- Shadow comparison provides A/B testing
- Performance monitoring with automatic fallback
- Clean separation of concerns

---

## ⚠️ Important Notes

1. **Do NOT reference archived docs in new code** - Use active documentation
2. **Archived docs may contain outdated information** - Verify against current system
3. **Links in archived docs may be broken** - Referenced files may have moved
4. **Archived docs are read-only** - No updates needed

---

## 📊 Archive Statistics

- **Total Archived Files:** 11
- **Last Archive Date:** 2025-10-04
- **Archive Size:** ~200 KB
- **Oldest Document:** Pre-2025 legacy fixes
- **Newest Archive:** Documentation cleanup (2025-10-04)

---

## 🔗 See Also

- **[docs/README.md](../README.md)** - Current documentation index
- **[../NAVIGATOR.md](../../NAVIGATOR.md)** - System overview (v4.5.0)
- **[../ENDPOINTS.md](../../ENDPOINTS.md)** - API reference (v4.1.0)
- **[../core/Database-Schema.md](../core/Database-Schema.md)** - Current schema

---

**For current documentation, see [docs/README.md](../README.md)**
