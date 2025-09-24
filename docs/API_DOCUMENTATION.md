# News MCP API Documentation

**Enterprise RSS Management & AI Analysis Platform**

Generated: 2025-09-24
Version: v3.0.0-repository-migration

## 🔗 Quick Links

- **Base URL**: `http://localhost:8000`
- **Interactive Docs**: `/docs` (Swagger UI)
- **Alternative Docs**: `/redoc` (ReDoc)
- **OpenAPI Schema**: `/openapi.json`
- **Health Check**: `/health/`

## 📊 API Overview

| Category | Endpoints | Description |
|----------|-----------|-------------|
| **Core RSS** | 35+ | Feed management, items, health monitoring |
| **Analysis** | 40+ | AI-powered content analysis and job management |
| **HTMX UI** | 60+ | Dynamic web interface components |
| **Admin** | 25+ | System administration, feature flags |
| **Templates** | 15+ | Dynamic content extraction templates |

## 🚀 Getting Started

### Authentication
Currently uses session-based authentication for web interface.
API endpoints are public for development.

### Rate Limits
- Analysis API: 30 requests/minute per IP
- General API: 100 requests/minute per IP
- File operations: 10 requests/minute per IP

### Response Format
All API responses follow this structure:
```json
{
  "success": true,
  "data": { /* response data */ },
  "message": "Optional message",
  "timestamp": "2025-09-24T10:30:00Z"
}
```

---

## 🏠 Application Routes

### Main Interface

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | **Main Dashboard** - System overview with feed status |
| `/admin` | GET | **Admin Dashboard** - Central administration panel |

### Admin Panels

| Endpoint | Method | Description | Features |
|----------|--------|-------------|----------|
| `/admin/analysis` | GET | **Analysis Control Center** | Live article selection, AI analysis management |
| `/admin/feeds` | GET | **Feed Management** | RSS feed configuration, health monitoring |
| `/admin/items` | GET | **Article Browser** | Search, filter, and manage news items |
| `/admin/health` | GET | **System Health** | Service monitoring, performance metrics |
| `/admin/database` | GET | **Database Admin** | Query interface, schema management |
| `/admin/processors` | GET | **Content Processors** | Template management, processing stats |
| `/admin/statistics` | GET | **Analytics Dashboard** | Usage statistics, performance reports |
| `/admin/metrics` | GET | **System Metrics** | Detailed performance monitoring |
| `/admin/templates` | GET | **Template Manager** | Dynamic content extraction templates |

---

## 📰 Feed Management API

### Overview
Comprehensive RSS feed management with health monitoring, dynamic templates, and real-time status updates.

### Core Feed Operations

#### GET /api/feeds/
**List All Feeds** - Get paginated list of RSS feeds with filtering

**Query Parameters:**
| Name | Type | Default | Description |
|------|------|---------|-------------|
| `skip` | integer | 0 | Number of records to skip (pagination) |
| `limit` | integer | 50 | Maximum records to return (1-100) |
| `category_id` | integer | null | Filter by category ID |
| `status` | string | null | Filter by status: `active`, `inactive`, `error` |

**Example Request:**
```bash
GET /api/feeds/?limit=20&status=active&category_id=1
```

**Response Structure:**
```json
{
  "feeds": [
    {
      "id": 1,
      "title": "TechCrunch RSS",
      "url": "https://techcrunch.com/feed/",
      "status": "active",
      "last_fetched": "2025-09-24T10:15:30Z",
      "item_count": 1250,
      "error_count": 0,
      "category_id": 1,
      "fetch_interval_minutes": 30
    }
  ],
  "total": 37,
  "page": 1,
  "pages": 2
}
```

#### POST /api/feeds/
**Create New Feed** - Add a new RSS feed to the system

**Request Body:**
```json
{
  "title": "Feed Name",
  "url": "https://example.com/feed.xml",
  "category_id": 1,
  "fetch_interval_minutes": 60,
  "is_active": true
}
```

#### GET /api/feeds/{feed_id}
**Get Feed Details** - Retrieve specific feed information

**Path Parameters:**
- `feed_id` (integer): Unique feed identifier

**Response:**
```json
{
  "id": 1,
  "title": "TechCrunch RSS",
  "url": "https://techcrunch.com/feed/",
  "status": "active",
  "created_at": "2025-01-15T09:30:00Z",
  "last_fetched": "2025-09-24T10:15:30Z",
  "fetch_interval_minutes": 30,
  "item_count": 1250,
  "success_rate_7d": 98.5,
  "template_id": 1,
  "category": {
    "id": 1,
    "name": "Technology"
  }
}
```

#### PUT /api/feeds/{feed_id}
**Update Feed** - Modify feed configuration

**Request Body:**
```json
{
  "title": "Updated Feed Name",
  "fetch_interval_minutes": 45,
  "is_active": false
}
```

#### DELETE /api/feeds/{feed_id}
**Delete Feed** - Remove feed from system (soft delete)

#### POST /api/feeds/{feed_id}/fetch
**Manual Fetch** - Trigger immediate feed fetch

**Response:**
```json
{
  "status": "success",
  "items_found": 12,
  "items_new": 8,
  "fetch_time_ms": 1250,
  "message": "Feed fetched successfully"
}
```

---

## 📄 Articles & Content API

### Overview
Access and manage news articles with advanced filtering, search capabilities, and AI analysis integration.

### Content Access

#### GET /api/items/
**List Articles** - Get articles with advanced filtering and search

**Query Parameters:**
| Name | Type | Default | Description |
|------|------|---------|-------------|
| `skip` | integer | 0 | Pagination offset |
| `limit` | integer | 50 | Results per page (1-200) |
| `category_id` | integer | null | Filter by category |
| `feed_id` | integer | null | Filter by specific feed |
| `since_hours` | integer | null | Articles from last N hours |
| `search` | string | null | Full-text search in title/content |
| `analyzed_only` | boolean | false | Only articles with AI analysis |
| `sort` | string | "published" | Sort by: `published`, `title`, `analysis_score` |
| `order` | string | "desc" | Sort order: `asc`, `desc` |

**Advanced Search Examples:**
```bash
# Recent tech articles
GET /api/items/?search=artificial+intelligence&since_hours=24&category_id=1

# High-impact analyzed articles
GET /api/items/?analyzed_only=true&sort=analysis_score&order=desc

# Articles from specific feed in last week
GET /api/items/?feed_id=5&since_hours=168
```

**Response Structure:**
```json
{
  "items": [
    {
      "id": 12345,
      "title": "AI Breakthrough in Natural Language Processing",
      "summary": "Researchers announce major advancement...",
      "url": "https://example.com/article/12345",
      "published": "2025-09-24T08:30:00Z",
      "feed_id": 1,
      "feed_title": "TechCrunch",
      "analysis_result": {
        "sentiment": "positive",
        "impact_score": 0.85,
        "key_topics": ["AI", "NLP", "Machine Learning"]
      }
    }
  ],
  "total": 1250,
  "analyzed_count": 890,
  "page_info": {
    "current_page": 1,
    "total_pages": 25,
    "has_next": true
  }
}
```

#### GET /api/items/{item_id}
**Get Article Details** - Retrieve specific article with full content

**Response:**
```json
{
  "id": 12345,
  "title": "AI Breakthrough in Natural Language Processing",
  "content": "Full article content...",
  "summary": "Auto-generated or manual summary",
  "url": "https://example.com/article/12345",
  "published": "2025-09-24T08:30:00Z",
  "author": "Jane Doe",
  "feed": {
    "id": 1,
    "title": "TechCrunch",
    "category": "Technology"
  },
  "analysis_result": {
    "sentiment": "positive",
    "impact_score": 0.85,
    "urgency_score": 0.7,
    "key_topics": ["AI", "NLP", "Machine Learning"],
    "summary_ai": "AI researchers have developed...",
    "analyzed_at": "2025-09-24T09:15:00Z",
    "model_used": "gpt-4.1-nano",
    "cost_usd": 0.023
  }
}
```

#### GET /api/items/analyzed
**List Analyzed Articles** - Get articles with AI analysis data

**Query Parameters:**
| Name | Type | Description |
|------|------|-------------|
| `impact_min` | float | Minimum impact score (0-1) |
| `sentiment` | string | Filter by sentiment: `positive`, `neutral`, `negative` |
| `urgency_min` | float | Minimum urgency score (0-1) |
| `limit` | integer | Maximum items to return |

---

## 🧠 AI Analysis API

### Overview
Powerful AI-driven content analysis system with GPT-4.1-nano integration, cost estimation, and job management.

**Key Features:**
- Sentiment analysis and impact scoring
- Batch processing with rate limiting (~30 articles/minute)
- Real-time cost estimation
- Job queue management
- Analysis presets and templates

### Analysis Control

#### POST /api/analysis/preview
**Preview Analysis Run** - Estimate scope, cost, and duration before starting

**Request Body:**
```json
{
  "scope": {
    "type": "timerange",  // "latest", "feed", "timerange", "specific"
    "params": {
      "start_date": "2025-09-23T00:00:00Z",
      "end_date": "2025-09-24T00:00:00Z"
      // or "feed_ids": [1, 2, 3] for feed scope
      // or "item_count": 100 for latest scope
      // or "item_ids": [123, 456] for specific scope
    }
  },
  "model": "gpt-4.1-nano",
  "analysis_type": "comprehensive"  // "basic", "comprehensive", "sentiment_only"
}
```

**Response:**
```json
{
  "preview": {
    "total_items": 150,
    "new_items": 89,
    "already_analyzed": 61,
    "estimated_cost_usd": 2.45,
    "estimated_duration_minutes": 3,
    "feeds_affected": [
      {"id": 1, "title": "TechCrunch", "item_count": 45},
      {"id": 2, "title": "Hacker News", "item_count": 44}
    ]
  },
  "model_info": {
    "name": "gpt-4.1-nano",
    "cost_per_1k_tokens": 0.0015,
    "avg_tokens_per_article": 800
  }
}
```

#### POST /api/analysis/start
**Start Analysis Run** - Begin AI analysis of selected articles

**Request Body:**
```json
{
  "scope": {
    "type": "feed",
    "params": {"feed_ids": [1, 2, 3]}
  },
  "model": "gpt-4.1-nano",
  "analysis_type": "comprehensive",
  "priority": "normal",  // "low", "normal", "high"
  "max_cost_usd": 5.00,
  "description": "Weekly tech news analysis"
}
```

**Response:**
```json
{
  "run_id": 42,
  "status": "pending",
  "queued_at": "2025-09-24T10:30:00Z",
  "estimated_start": "2025-09-24T10:32:00Z",
  "queue_position": 2,
  "items_to_process": 89
}
```

#### GET /api/analysis/status/{run_id}
**Get Analysis Run Status** - Monitor progress of active or completed runs

**Path Parameters:**
- `run_id` (integer): Unique run identifier

**Response Examples:**

**Active Run:**
```json
{
  "run_id": 42,
  "status": "running",
  "started_at": "2025-09-24T10:32:15Z",
  "progress": {
    "total_items": 89,
    "processed": 34,
    "failed": 2,
    "remaining": 53,
    "percentage": 38.2
  },
  "performance": {
    "items_per_minute": 28.5,
    "estimated_completion": "2025-09-24T10:35:30Z",
    "total_cost_usd": 1.23
  },
  "current_item": {
    "id": 12389,
    "title": "Latest AI Development...",
    "processing_since": "2025-09-24T10:34:02Z"
  }
}
```

**Completed Run:**
```json
{
  "run_id": 41,
  "status": "completed",
  "started_at": "2025-09-24T09:15:30Z",
  "completed_at": "2025-09-24T09:18:45Z",
  "duration_seconds": 195,
  "results": {
    "total_processed": 67,
    "successful": 65,
    "failed": 2,
    "total_cost_usd": 1.89
  },
  "analysis_summary": {
    "sentiment_distribution": {
      "positive": 42,
      "neutral": 18,
      "negative": 5
    },
    "avg_impact_score": 0.67,
    "top_topics": ["AI", "Technology", "Business"]
  }
}
```

#### GET /api/analysis/runs
**List Analysis Runs** - Get all analysis runs with filtering

**Query Parameters:**
| Name | Type | Description |
|------|------|-------------|
| `active_only` | boolean | Show only active runs |
| `status` | string | Filter by status |
| `limit` | integer | Maximum results |
| `since_date` | string | Runs since date |

#### POST /api/analysis/cancel/{run_id}
**Cancel Analysis Run** - Stop active analysis

#### GET /api/analysis/cost/{model}
**Get Cost Estimate** - Calculate analysis costs

**Path Parameters:**
- `model` (string): AI model name

**Query Parameters:**
| Name | Type | Description |
|------|------|-------------|
| `article_count` | integer | Number of articles to analyze |
| `avg_article_length` | integer | Average article length in tokens |

---

## ⚡ HTMX Dynamic Interface API

### Overview
HTMX-powered endpoints for dynamic web interface updates without full page reloads. These endpoints return HTML fragments for seamless integration.

**Key Features:**
- Real-time UI updates
- Progressive enhancement
- Optimistic UI patterns
- Live search and filtering

### Analysis Interface

#### GET /htmx/analysis/active-runs
**Live Active Analysis Runs** - Real-time display of running analysis jobs

**Response:** HTML fragment showing active runs with progress bars

```html
<div class="list-group" id="active-runs">
  <div class="list-group-item" data-run-id="42">
    <div class="d-flex justify-content-between align-items-center">
      <div>
        <h6 class="mb-1">Analysis Run #42</h6>
        <p class="mb-1 text-muted">Started: 2025-09-24 10:32:15</p>
      </div>
      <span class="badge bg-primary">RUNNING</span>
    </div>
    <div class="progress mt-2" style="height: 20px;">
      <div class="progress-bar" role="progressbar" style="width: 38.2%">38%</div>
    </div>
    <small class="text-muted">34/89 items processed • ~2 min remaining</small>
  </div>
</div>
```

**Auto-refresh:** Updates every 2 seconds via `hx-trigger="every 2s"`

#### GET /htmx/analysis/runs/history
**Analysis Run History** - Paginated history of completed runs

**Query Parameters:**
| Name | Type | Default | Description |
|------|------|---------|-------------|
| `page` | integer | 1 | Page number |
| `limit` | integer | 10 | Results per page |
| `status` | string | null | Filter by status |

#### GET /htmx/analysis/stats-horizontal
**Live System Statistics** - Real-time dashboard metrics cards

**Response:** Bootstrap card layout with key metrics

```html
<div class="row g-3">
  <div class="col-md-3">
    <div class="stat-card">
      <div class="stat-value">12,450</div>
      <div class="stat-label">Total Articles</div>
    </div>
  </div>
  <div class="col-md-3">
    <div class="stat-card">
      <div class="stat-value">8,920</div>
      <div class="stat-label">Analyzed</div>
    </div>
  </div>
  <div class="col-md-3">
    <div class="stat-card">
      <div class="stat-value">71.6%</div>
      <div class="stat-label">Coverage</div>
      <div class="stat-trend">↑ 2.3%</div>
    </div>
  </div>
  <div class="col-md-3">
    <div class="stat-card">
      <div class="stat-value">2</div>
      <div class="stat-label">Active Runs</div>
      <div class="stat-status">🟢 Healthy</div>
    </div>
  </div>
</div>
```

**Features:**
- Real-time updates every 30 seconds
- Trend indicators (↑↓)
- Status icons for system health
- Responsive layout

---

## 🏥 Health Monitoring API

### Overview
Comprehensive system health monitoring with detailed diagnostics for all components.

### System Health Checks

#### GET /health/
**Basic Health Check** - Simple liveness probe

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-09-24T10:30:00Z",
  "version": "v3.0.0-repository-migration"
}
```

#### GET /health/detailed
**Comprehensive Health Check** - Full system diagnostics

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-09-24T10:30:00Z",
  "checks": {
    "database": {
      "status": "healthy",
      "response_time_ms": 45,
      "connection_pool": "8/20 active"
    },
    "feeds": {
      "status": "healthy",
      "active_feeds": 37,
      "error_rate": "0%",
      "last_fetch_success": "2025-09-24T10:28:30Z"
    },
    "analysis_worker": {
      "status": "healthy",
      "queue_size": 3,
      "processing_rate": "28.5 items/min",
      "error_rate": "1.2%"
    },
    "storage": {
      "status": "healthy",
      "disk_usage": "45%",
      "available_gb": 15.2
    }
  },
  "performance": {
    "avg_response_time_ms": 89,
    "requests_per_minute": 145,
    "memory_usage_mb": 256,
    "cpu_usage_percent": 23
  }
}
```

#### GET /api/health/feeds
**All Feed Health Status** - Health overview for all RSS feeds

**Response:**
```json
{
  "summary": {
    "total_feeds": 37,
    "healthy": 35,
    "warning": 2,
    "critical": 0,
    "overall_success_rate": "97.3%"
  },
  "feeds": [
    {
      "id": 1,
      "title": "TechCrunch",
      "status": "healthy",
      "last_success": "2025-09-24T10:25:00Z",
      "success_rate_24h": 100.0,
      "avg_fetch_time_ms": 1250,
      "items_last_fetch": 12
    }
  ]
}
```

---

## 🎨 Dynamic Template API

### Overview
Manage dynamic content extraction templates for RSS feeds. Templates define how to parse and extract structured data from various feed formats.

### Template Management

#### GET /api/templates/
**List Content Templates** - Get available extraction templates

**Query Parameters:**
| Name | Type | Default | Description |
|------|------|---------|-------------|
| `assigned_to_feed_id` | integer | null | Templates assigned to specific feed |
| `active_only` | boolean | false | Only active templates |
| `template_type` | string | null | Filter by type: `rss`, `json`, `html` |

**Response:**
```json
{
  "templates": [
    {
      "id": 1,
      "name": "TechCrunch RSS",
      "description": "Optimized for TechCrunch RSS format",
      "template_type": "rss",
      "is_active": true,
      "is_builtin": true,
      "assigned_feeds": 3,
      "success_rate": 98.5,
      "selectors": {
        "title": "title",
        "content": "description",
        "author": "dc:creator",
        "published": "pubDate",
        "image": "media:content[medium='image']/@url"
      }
    }
  ],
  "total": 12,
  "active": 8
}
```

#### POST /api/templates/create
**Create New Template** - Define content extraction rules

**Request Body:**
```json
{
  "name": "Custom RSS Template",
  "description": "Template for custom RSS format",
  "template_type": "rss",
  "is_active": true,
  "selectors": {
    "title": "item/title",
    "content": "item/description",
    "published": "item/pubDate",
    "author": "item/author"
  },
  "transformations": {
    "date_format": "RFC822",
    "content_cleanup": true
  }
}
```

#### POST /api/templates/{template_id}/test
**Test Template Extraction** - Validate template against sample content

**Request Body:**
```json
{
  "sample_url": "https://example.com/feed.xml",
  "sample_content": "<optional raw content>",
  "expected_fields": ["title", "content", "published"]
}
```

**Response:**
```json
{
  "test_results": {
    "success": true,
    "items_extracted": 15,
    "extraction_rate": 93.3,
    "missing_fields": ["author"],
    "sample_items": [
      {
        "title": "AI Breakthrough Announced",
        "content": "Researchers at...",
        "published": "2025-09-24T08:30:00Z",
        "author": null,
        "confidence": 0.95
      }
    ]
  },
  "performance": {
    "extraction_time_ms": 245,
    "memory_usage_mb": 1.2
  },
  "recommendations": [
    "Consider adding fallback selector for 'author' field",
    "Date parsing could be more robust"
  ]
}
```

---

## 📊 Metrics & Analytics API

### Overview
Comprehensive system metrics including feed performance, analysis costs, processing statistics, and business intelligence.

### System Metrics

#### GET /api/metrics/system/overview
**System Overview Dashboard** - High-level system performance metrics

**Response:**
```json
{
  "system_health": {
    "status": "healthy",
    "uptime_hours": 168.5,
    "version": "v3.0.0-repository-migration"
  },
  "feed_metrics": {
    "total_feeds": 37,
    "active_feeds": 35,
    "success_rate_24h": 97.3,
    "items_fetched_today": 1250,
    "avg_fetch_time_ms": 1180
  },
  "analysis_metrics": {
    "total_analyzed_items": 8920,
    "analysis_coverage": 71.6,
    "avg_analysis_time_ms": 2100,
    "total_cost_usd_30d": 45.67,
    "active_runs": 2
  },
  "performance": {
    "api_requests_per_minute": 145,
    "avg_response_time_ms": 89,
    "error_rate": 0.5,
    "database_connections": "8/20",
    "memory_usage_mb": 256,
    "cpu_usage_percent": 23
  },
  "storage": {
    "total_articles": 12450,
    "database_size_mb": 892,
    "disk_usage_percent": 45,
    "backup_status": "completed_6h_ago"
  }
}
```

#### GET /api/metrics/costs/breakdown
**Analysis Cost Breakdown** - Detailed cost analysis by feed and model

**Query Parameters:**
| Name | Type | Default | Description |
|------|------|---------|-------------|
| `days` | integer | 30 | Number of days to analyze |
| `group_by` | string | "feed" | Group by: `feed`, `model`, `date` |
| `currency` | string | "USD" | Currency for cost display |

**Response:**
```json
{
  "period": {
    "start_date": "2025-08-25T00:00:00Z",
    "end_date": "2025-09-24T23:59:59Z",
    "days": 30
  },
  "total_cost_usd": 45.67,
  "cost_by_feed": [
    {
      "feed_id": 1,
      "feed_title": "TechCrunch",
      "items_analyzed": 450,
      "cost_usd": 12.34,
      "avg_cost_per_item": 0.0274,
      "percentage_of_total": 27.0
    }
  ],
  "cost_by_model": [
    {
      "model": "gpt-4.1-nano",
      "items_analyzed": 2890,
      "cost_usd": 42.15,
      "avg_tokens_per_item": 850,
      "percentage_of_total": 92.3
    }
  ],
  "daily_trend": [
    {"date": "2025-09-24", "cost_usd": 2.34, "items": 89},
    {"date": "2025-09-23", "cost_usd": 1.89, "items": 67}
  ],
  "projections": {
    "monthly_estimate_usd": 48.50,
    "annual_estimate_usd": 582.00
  }
}
```

---

## 🔧 Database Administration API

### Overview
Direct database access for administrative tasks, analytics, and troubleshooting.

#### GET /api/database/tables
**List Database Tables** - Get all available tables

#### GET /api/database/schema/{table_name}
**Get Table Schema** - Detailed table structure information

#### POST /api/database/query
**Execute SQL Query** - Run read-only queries (SELECT only)

**Request Body:**
```json
{
  "query": "SELECT COUNT(*) as total_items, MAX(published) as latest_article FROM items",
  "limit": 100
}
```

---

## 🚦 Error Handling

### HTTP Status Codes

| Code | Meaning | Description |
|------|---------|-------------|
| 200 | OK | Request successful |
| 400 | Bad Request | Invalid request parameters |
| 401 | Unauthorized | Authentication required |
| 403 | Forbidden | Insufficient permissions |
| 404 | Not Found | Resource not found |
| 422 | Validation Error | Request validation failed |
| 429 | Rate Limited | Too many requests |
| 500 | Server Error | Internal server error |

### Error Response Format

```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid feed URL format",
    "details": {
      "field": "url",
      "value": "invalid-url",
      "expected": "Valid HTTP/HTTPS URL"
    }
  },
  "timestamp": "2025-09-24T10:30:00Z"
}
```

---

## 🔐 Security Considerations

### Data Protection
- All API inputs are validated and sanitized
- SQL injection protection through SQLAlchemy ORM
- XSS protection on all HTML outputs
- CSRF protection on state-changing operations

### Rate Limiting
- Analysis operations: 30 requests/minute per IP
- General API calls: 100 requests/minute per IP
- File operations: 10 requests/minute per IP

### Access Control
- Session-based authentication for web interface
- API key authentication planned for v3.1
- Role-based access control for admin functions

---

## 📚 Additional Resources

- **OpenAPI Schema**: `/openapi.json`
- **Interactive Documentation**: `/docs`
- **Health Monitoring**: `/health/detailed`
- **System Metrics**: `/api/metrics/system/overview`
- **GitHub Repository**: [News MCP Project](https://github.com/your-org/news-mcp)

---

**Last Updated**: 2025-09-24
**API Version**: v3.0.0-repository-migration
**Documentation Version**: 1.0