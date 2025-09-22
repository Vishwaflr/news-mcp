# QMAgent - Quality Management Agent

QMAgent ist die automatische Dokumentations-Überwachung für News MCP.

## 🎯 **Wie es funktioniert**

### 1. **QMAgent (Python)** - Erkennung
- Überwacht Code-Änderungen
- Identifiziert was dokumentiert werden muss
- Erstellt Tasks für Claude Code Agent

### 2. **Claude Code Agent** - Ausführung
- Liest QMAgent Tasks
- Führt Dokumentations-Updates aus
- Markiert Tasks als completed

## 🔧 **Verwendung**

### Manuelle Prüfung
```bash
# Check für neue Änderungen
python scripts/qmagent.py check

# Status anzeigen
python scripts/qmagent.py status

# Tasks anzeigen
python scripts/qmagent.py tasks

# Tasks löschen (nach completion)
python scripts/qmagent.py clear
```

### Mit Claude Code
```bash
# 1. Prüfe QMAgent
python scripts/qmagent.py check

# 2. Wenn Tasks gefunden, führe sie mit Claude Code aus
# (Die Tasks werden in .qmagent_tasks.json gespeichert)

# 3. Nach Completion
python scripts/qmagent.py clear
```

## 🎛️ **Was QMAgent überwacht**

| **Trigger** | **Priorität** | **Dokumentation** |
|-------------|---------------|-------------------|
| `app/repositories/` | HIGH | README.md, DEVELOPER_SETUP.md, TESTING.md |
| `app/utils/feature_flags.py` | CRITICAL | MONITORING.md, DEVELOPER_SETUP.md |
| `app/utils/shadow_compare.py` | HIGH | MONITORING.md, TESTING.md |
| `app/utils/monitoring.py` | MEDIUM | MONITORING.md |
| `app/api/` | MEDIUM | README.md |
| `alembic/versions/` | MEDIUM | README.md, DEVELOPER_SETUP.md |
| `pyproject.toml` | LOW | DEVELOPER_SETUP.md |

## 🤖 **CLAUDE.md Integration**

QMAgent ist in CLAUDE.md integriert - Claude Code führt automatisch bei jeder Session aus:

1. `python scripts/qmagent.py check` (erkennt Änderungen)
2. `python scripts/qmagent.py tasks` (zeigt was zu tun ist)
3. Führt Dokumentations-Updates aus
4. `python scripts/qmagent.py clear` (löscht erledigte Tasks)

## 📋 **Beispiel-Workflow**

```bash
# Entwickler ändert app/repositories/items_repo.py
# QMAgent erkennt dies:

$ python scripts/qmagent.py check
📋 QMAgent: Found 1 changes requiring documentation updates
Priority breakdown: High: 1

$ python scripts/qmagent.py tasks
## ⚡ HIGH PRIORITY
- **Repository Pattern changes detected** in `app/repositories/items_repo.py`
  📝 Update: README.md, DEVELOPER_SETUP.md, TESTING.md

# Claude Code Agent führt die Updates aus
# Danach:

$ python scripts/qmagent.py clear
✅ Tasks cleared
```

## 🎯 **Besondere Features**

### Repository Pattern Focus
QMAgent ist speziell für die Repository Pattern Migration optimiert:
- Erkennt Repository-Änderungen sofort
- Priorisiert Feature Flag Updates (CRITICAL)
- Überwacht Shadow Comparison System

### Intelligent Prioritization
- **CRITICAL**: Feature Flags (sofortige Dokumentation nötig)
- **HIGH**: Repository Pattern (wichtig für Migration)
- **MEDIUM**: API Changes (wichtig aber weniger dringend)
- **LOW**: Dependencies (kann warten)

### Zero-Maintenance
- Kein Daemon nötig
- Läuft on-demand
- Integriert in normale Claude Code Workflows

## 🚀 **Installation**

QMAgent ist bereits installiert. Nur prüfen ob es funktioniert:

```bash
$ python scripts/qmagent.py check
✅ QMAgent: No documentation updates needed
```

Das war's! QMAgent funktioniert sofort und überwacht automatisch alle kritischen Änderungen.

---

🎯 **Ziel**: Dokumentation bleibt automatisch aktuell ohne manuelle Überwachung.