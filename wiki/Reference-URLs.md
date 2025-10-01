# URL Reference - Quick Access Guide

Quick reference for all News MCP URLs and endpoints.

---

## 🌐 Web Dashboards

| Dashboard | URL | Description |
|-----------|-----|-------------|
| **Main Dashboard** | http://localhost:8000/ | System overview |
| **Analysis Cockpit** | http://localhost:8000/admin/analysis | Manual analysis interface |
| **Auto-Analysis** | http://localhost:8000/admin/auto-analysis | Auto-analysis monitoring |
| **Manager Control** | http://localhost:8000/admin/manager | Emergency controls |
| **Feed Management** | http://localhost:8000/admin/feeds | RSS feed CRUD |
| **Database Browser** | http://localhost:8000/admin/database | Query interface |

---

## 📖 API Documentation

| Documentation | URL | Description |
|---------------|-----|-------------|
| **Swagger UI** | http://localhost:8000/docs | Interactive API docs |
| **ReDoc** | http://localhost:8000/redoc | Alternative API docs |
| **OpenAPI Schema** | http://localhost:8000/openapi.json | OpenAPI specification |

---

## 🔌 MCP Server

| Service | URL | Description |
|---------|-----|-------------|
| **MCP Server** | http://localhost:8001/ | Model Context Protocol server |
| **MCP Health** | http://localhost:8001/health | MCP server health check |

---

## 🔍 API Endpoints (Quick Reference)

### Feed Management
```
GET    /api/feeds/              # List feeds
POST   /api/feeds/              # Create feed
GET    /api/feeds/{id}          # Get feed
PUT    /api/feeds/{id}          # Update feed
DELETE /api/feeds/{id}          # Delete feed
POST   /api/feeds/{id}/fetch    # Manual fetch
```

### Articles
```
GET    /api/items/              # List articles
GET    /api/items/{id}          # Get article
GET    /api/items/analyzed      # Analyzed articles
```

### Analysis
```
POST   /api/analysis/runs       # Start analysis
GET    /api/analysis/runs       # List runs
GET    /api/analysis/runs/{id}  # Get run details
DELETE /api/analysis/runs/{id}  # Cancel run
```

### Health & Monitoring
```
GET    /api/health/             # System health
GET    /api/health/feeds        # Feed health
GET    /api/health/logs/{id}    # Fetch logs
```

---

## 🔗 Related Documentation

- **[API Overview](API-Overview)** - Complete API reference
- **[Dashboard Overview](Dashboard-Overview)** - Dashboard details
- **[MCP Integration](MCP-Integration)** - MCP setup

---

**Last Updated:** 2025-10-01
