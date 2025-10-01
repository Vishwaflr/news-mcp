# API Overview - News MCP REST API

Complete reference for the News MCP REST API with 172+ endpoints across 15 categories.

---

## 🎯 API Architecture

The News MCP API follows RESTful principles with a modular, category-based organization:

- **172+ Endpoints** organized into 15 logical categories
- **FastAPI Framework** with automatic OpenAPI documentation
- **Type-Safe** with Pydantic models and SQLModel integration
- **HTMX Support** for progressive enhancement
- **WebSocket** for real-time updates

---

## 📋 API Categories

| Category | Endpoints | Prefix | Description |
|----------|-----------|--------|-------------|
| **[Feed Management](#feed-management)** | 15 | `/api/feeds` | RSS feed CRUD operations |
| **[Items/Articles](#itemsarticles)** | 12 | `/api/items` | Article retrieval and search |
| **[Analysis System](#analysis-system)** | 35 | `/api/analysis` | AI analysis runs and results |
| **[Templates](#templates)** | 8 | `/api/templates` | Dynamic feed templates |
| **[Categories & Sources](#categories--sources)** | 8 | `/api/categories`, `/api/sources` | Content organization |
| **[Processors](#processors)** | 6 | `/api/processors` | Content processing pipeline |
| **[Statistics & Metrics](#statistics--metrics)** | 12 | `/api/statistics`, `/api/metrics` | System metrics |
| **[Health & System](#health--system)** | 10 | `/api/health`, `/api/system` | System monitoring |
| **[HTMX Views](#htmx-views)** | 30 | `/htmx/*` | Server-side rendered components |
| **[WebSocket](#websocket)** | 1 | `/ws/*` | Real-time updates |
| **[Database Admin](#database-admin)** | 4 | `/api/database` | Database utilities |
| **[Feature Flags](#feature-flags)** | 12 | `/admin/feature-flags` | Feature toggles |
| **[User Settings](#user-settings)** | 4 | `/api/user-settings` | User preferences |
| **[Scheduler](#scheduler)** | 6 | `/api/scheduler` | Feed scheduling |
| **[Feed Limits](#feed-limits)** | 9 | `/api/feed-limits` | Rate limiting |

**Total:** 172 endpoints

---

## 🔑 API Conventions

### Request/Response Format

All API endpoints follow consistent patterns:

**JSON Requests:**
```json
{
  "field": "value",
  "nested": {
    "key": "value"
  }
}
```

**Standard Response:**
```json
{
  "success": true,
  "data": { },
  "message": "Operation successful"
}
```

**Error Response:**
```json
{
  "detail": "Error description",
  "status_code": 400
}
```

### HTTP Status Codes

| Code | Meaning | Usage |
|------|---------|-------|
| `200` | OK | Successful GET/PUT/DELETE |
| `201` | Created | Successful POST |
| `400` | Bad Request | Invalid input |
| `404` | Not Found | Resource doesn't exist |
| `422` | Unprocessable Entity | Validation error |
| `500` | Internal Server Error | Server error |

### Pagination

Endpoints returning lists support pagination:

```http
GET /api/items?page=1&limit=50
```

**Response:**
```json
{
  "items": [...],
  "total": 1000,
  "page": 1,
  "limit": 50,
  "pages": 20
}
```

---

## 📚 Quick Reference

### Feed Management

Manage RSS feeds with full CRUD operations:

```http
GET    /api/feeds/                    # List all feeds
GET    /api/feeds/{id}                # Get feed details
POST   /api/feeds/                    # Create feed (form)
POST   /api/feeds/json                # Create feed (JSON)
PUT    /api/feeds/{id}                # Update feed
DELETE /api/feeds/{id}                # Delete feed
POST   /api/feeds/{id}/fetch          # Manual fetch
POST   /api/feeds/{id}/toggle-auto-analysis  # Toggle auto-analysis
```

**[Complete Feed API →](API-Feed-Management)**

---

### Items/Articles

Retrieve and search articles:

```http
GET    /api/items/                    # List articles (paginated)
GET    /api/items/{id}                # Article details
GET    /api/items/analyzed            # Analyzed articles only
GET    /api/items/{id}/analysis       # Article analysis results
GET    /api/items/analysis/stats      # Analysis statistics
```

**[Complete Items API →](API-Items)**

---

### Analysis System

Run and monitor AI analysis:

```http
POST   /api/analysis/runs             # Start analysis run
GET    /api/analysis/runs             # List runs
GET    /api/analysis/runs/{id}        # Run details
GET    /api/analysis/runs/{id}/results  # Analysis results
DELETE /api/analysis/runs/{id}        # Cancel run
GET    /api/analysis/stats            # System statistics
```

**[Complete Analysis API →](API-Analysis)**

---

### Auto-Analysis

Automatic analysis system (Phase 2):

```http
GET    /api/analysis/auto/status      # Auto-analysis status
POST   /api/analysis/auto/enable      # Enable auto-analysis
POST   /api/analysis/auto/disable     # Disable auto-analysis
GET    /api/analysis/auto/queue       # View queue
GET    /api/analysis/auto/metrics     # Performance metrics
```

**[Complete Auto-Analysis API →](API-Auto-Analysis)**

---

### Templates

Dynamic feed template management:

```http
GET    /api/templates/                # List templates
GET    /api/templates/{id}            # Template details
POST   /api/templates/                # Create template
PUT    /api/templates/{id}            # Update template
DELETE /api/templates/{id}            # Delete template
POST   /api/templates/{id}/assign     # Assign to feed
GET    /api/templates/performance     # Template statistics
```

**[Complete Templates API →](API-Templates)**

---

### Health & Monitoring

System health and diagnostics:

```http
GET    /api/health/                   # System health overview
GET    /api/health/feeds              # Feed health status
GET    /api/health/feeds/{id}         # Individual feed health
GET    /api/health/logs/{id}          # Feed fetch logs
GET    /api/health/scheduler          # Scheduler status
GET    /api/health/database           # Database health
```

**[Complete Health API →](API-Health)**

---

### Statistics & Metrics

Performance metrics and analytics:

```http
GET    /api/statistics/dashboard      # Dashboard stats
GET    /api/statistics/feeds          # Feed statistics
GET    /api/statistics/analysis       # Analysis metrics
GET    /api/metrics/system            # System metrics
GET    /api/metrics/performance       # Performance data
```

**[Complete Statistics API →](API-Statistics)**

---

## 🌐 HTMX Endpoints

Server-side rendered components for progressive enhancement:

### Analysis HTMX
```http
GET    /htmx/analysis/target-selection       # Target selection UI
GET    /htmx/analysis/preview-start          # Preview interface
GET    /htmx/analysis/runs/history           # Run history table
GET    /htmx/analysis/runs/active            # Active runs
GET    /htmx/analysis/settings/form          # Settings form
```

### Dashboard HTMX
```http
GET    /htmx/dashboard/stats                 # Dashboard statistics
GET    /htmx/dashboard/articles-live         # Live article stream
GET    /htmx/dashboard/feed-status           # Feed status cards
```

**[Complete HTMX API →](API-HTMX)**

---

## 🔌 WebSocket API

Real-time updates via WebSocket:

```javascript
// Connect to WebSocket
const ws = new WebSocket('ws://localhost:8000/ws/updates');

// Receive updates
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Update:', data);
};
```

**Event Types:**
- `analysis_progress` - Analysis run progress updates
- `feed_fetch` - Feed fetch status
- `system_alert` - System notifications
- `item_new` - New articles added

**[Complete WebSocket API →](API-WebSocket)**

---

## 📖 Interactive Documentation

The API provides auto-generated interactive documentation:

- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc
- **OpenAPI Schema:** http://localhost:8000/openapi.json

Use these interfaces to:
- Browse all endpoints
- Test API calls directly
- View request/response schemas
- Generate client code

---

## 🔐 Authentication

Currently, the API operates without authentication (development mode).

**Production Recommendations:**
- Implement JWT-based authentication
- Use API keys for MCP clients
- Enable CORS restrictions
- Add rate limiting per client

---

## 🚀 Rate Limiting

Feed operations respect rate limits:

- **Default:** 1 request per 5 minutes per feed
- **Configurable:** Per-feed interval settings
- **Manual Override:** Admin can bypass limits

---

## 📊 Performance

**Typical Response Times:**
- Feed list: < 50ms
- Article search: < 100ms
- Analysis run start: < 200ms
- Statistics: < 150ms

**Concurrency:**
- Async processing with FastAPI
- Database connection pooling
- Background worker queue

---

## 🔗 Related Documentation

- **[MCP Integration](MCP-Integration)** - Model Context Protocol tools
- **[Architecture](Architecture)** - System design
- **[Database Schema](Database-Schema)** - Data models
- **[Deployment](Deployment-Production)** - Production setup

---

## 📞 API Support

- **Issues:** [GitHub Issues](https://github.com/CytrexSGR/news-mcp/issues)
- **OpenAPI Spec:** `/openapi.json`
- **Status Page:** `/api/health/`

---

**Last Updated:** 2025-10-01
**API Version:** 4.0.0
**Total Endpoints:** 172
