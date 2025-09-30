# API Documentation - News-MCP v1

## Base URL
```
http://localhost:8000/api/v1
```

## Authentication
Currently no authentication required (internal use only).

## Analysis Endpoints

### Start Analysis Run
```http
POST /api/v1/analysis/runs
```

#### Request Body
```json
{
  "scope": {
    "type": "feeds|items|categories|global",
    "feed_ids": [1, 2, 3],        // if type=feeds
    "item_ids": [100, 101],        // if type=items
    "category_ids": [5, 6],        // if type=categories
    "hours": 24,                   // optional time filter
    "limit": 100,                  // max items to analyze
    "unanalyzed_only": true        // skip already analyzed
  },
  "params": {
    "model_tag": "gpt-4.1-nano",
    "rate_per_second": 1.0,
    "dry_run": false,
    "limit": 100                   // overrides scope.limit if set
  }
}
```

#### Response
```json
{
  "id": 353,
  "status": "running",
  "created_at": "2025-09-30T16:23:26Z",
  "metrics": {
    "queued_count": 100,
    "processed_count": 0,
    "estimated_cost_usd": 0.05
  }
}
```

### Get Run Status
```http
GET /api/v1/analysis/runs/{run_id}
```

#### Response
```json
{
  "id": 353,
  "status": "completed",
  "metrics": {
    "queued_count": 100,
    "processed_count": 100,
    "failed_count": 0,
    "actual_cost_usd": 0.048,
    "items_per_minute": 120.5,
    "error_rate": 0.0
  }
}
```

### Cancel Run
```http
DELETE /api/v1/analysis/runs/{run_id}
```

### List Recent Runs
```http
GET /api/v1/analysis/runs?limit=20
```

#### Query Parameters
- `limit` (int): Number of runs to return (default: 20)
- `status` (string): Filter by status (pending|running|completed|failed)

### Preview Analysis
```http
POST /api/v1/analysis/preview
```

#### Request Body
Same as Start Analysis Run

#### Response
```json
{
  "item_count": 50,
  "already_analyzed": 30,
  "new_items_count": 20,
  "estimated_cost_usd": 0.02,
  "estimated_duration_minutes": 2
}
```

## Feed Endpoints

### List Feeds
```http
GET /api/feeds
```

#### Response
```json
{
  "feeds": [
    {
      "id": 1,
      "title": "TechCrunch",
      "url": "https://techcrunch.com/feed/",
      "status": "active",
      "item_count": 245,
      "auto_analysis_enabled": true
    }
  ]
}
```

### Toggle Auto-Analysis
```http
POST /api/feeds/{feed_id}/toggle-auto-analysis
```

#### Request Body
```json
{
  "enabled": true
}
```

## Item Endpoints

### List Recent Items
```http
GET /api/items/recent?limit=50
```

### Get Item Analysis
```http
GET /api/items/{item_id}/analysis
```

#### Response
```json
{
  "item_id": 12345,
  "sentiment": {
    "overall": {
      "label": "positive",
      "confidence": 0.85
    },
    "market": {
      "trend": "bullish",
      "confidence": 0.72
    }
  },
  "impact": {
    "overall": 7.5,
    "sectors": ["technology", "finance"]
  },
  "analyzed_at": "2025-09-30T16:00:00Z"
}
```

## Statistics Endpoints

### System Statistics
```http
GET /api/statistics/system
```

#### Response
```json
{
  "total_feeds": 41,
  "active_feeds": 35,
  "total_items": 14750,
  "analyzed_items": 8432,
  "analysis_coverage": 57.2,
  "today_items": 450,
  "today_analyzed": 320
}
```

### Cost Statistics
```http
GET /api/statistics/cost?days=30
```

#### Response
```json
{
  "period_days": 30,
  "total_cost_usd": 45.23,
  "total_runs": 234,
  "avg_cost_per_run": 0.19,
  "by_model": {
    "gpt-4.1-nano": 35.00,
    "gpt-4o-mini": 10.23
  }
}
```

## Health Endpoints

### Health Check
```http
GET /api/health/status
```

#### Response
```json
{
  "status": "healthy",
  "database": "connected",
  "worker": "running",
  "queue_depth": 45
}
```

### Circuit Breaker Status (NEW)
```http
GET /api/v1/health/circuit-breakers
```

#### Response
```json
{
  "timestamp": "2025-09-30T17:00:00Z",
  "summary": {
    "total_breakers": 5,
    "open": 0,
    "half_open": 1,
    "closed": 4,
    "total_errors": 23,
    "total_recoveries": 5,
    "health_percentage": 80.0
  },
  "breakers": {
    "openai": {
      "name": "openai",
      "state": "closed",
      "failure_count": 0,
      "success_count": 0,
      "stats": {
        "total_errors": 5,
        "consecutive_errors": 0,
        "errors_by_type": {
          "rate_limit": 3,
          "timeout": 2
        },
        "recovery_attempts": 2,
        "successful_recoveries": 2,
        "last_error": "2025-09-30T16:45:00Z"
      }
    }
  }
}
```

### Circuit Breaker Details (NEW)
```http
GET /api/v1/health/circuit-breakers/{breaker_name}
```

### Reset Circuit Breaker (NEW)
```http
POST /api/v1/health/circuit-breakers/{breaker_name}/reset
```

#### Response
```json
{
  "status": "success",
  "message": "Circuit breaker 'openai' has been reset to closed state"
}
```

### Error Statistics (NEW)
```http
GET /api/v1/health/error-stats
```

#### Response
```json
{
  "timestamp": "2025-09-30T17:00:00Z",
  "errors_by_type": {
    "rate_limit": 15,
    "timeout": 8,
    "server_error": 5
  },
  "errors_by_service": {
    "openai": 20,
    "feed_fetch": 8
  },
  "top_problematic_services": {
    "openai": 20,
    "feed_fetch": 8
  },
  "total_errors": 28
}
```

## WebSocket Endpoint

### Real-time Updates
```websocket
ws://localhost:8000/ws/analysis
```

#### Message Format
```json
{
  "type": "run_update",
  "data": {
    "run_id": 353,
    "status": "running",
    "progress": 45
  }
}
```

## Error Responses

All endpoints use standard HTTP status codes and return errors in this format:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid scope type",
    "details": {
      "field": "scope.type",
      "value": "invalid",
      "allowed": ["feeds", "items", "categories", "global"]
    }
  }
}
```

### Common Status Codes
- `200` - Success
- `201` - Created
- `400` - Bad Request
- `404` - Not Found
- `422` - Validation Error
- `500` - Internal Server Error

## Rate Limiting

API endpoints have the following rate limits:
- Analysis runs: 10 per minute
- Preview: 30 per minute
- Statistics: 60 per minute
- General endpoints: 100 per minute

## Pagination

List endpoints support pagination:
```http
GET /api/items?page=2&page_size=50
```

- `page` (int): Page number (default: 1)
- `page_size` (int): Items per page (default: 20, max: 100)

## Filtering

Most list endpoints support filtering:
```http
GET /api/items?feed_id=1&published_after=2025-09-01
```

Common filters:
- `feed_id` - Filter by feed
- `category_id` - Filter by category
- `status` - Filter by status
- `published_after` - Items after date
- `published_before` - Items before date
- `analyzed` - true/false

---

*Last Updated: 2025-09-30*
*API Version: 1.1.0*
*New: Error Recovery & Circuit Breaker Monitoring*