# News MCP API Examples

## Authentication

Currently, the API does not require authentication for most endpoints. In production, implement proper authentication.

## Base URL

```
http://localhost:8000
```

## Feed Management

### List All Feeds

```bash
curl -X GET http://localhost:8000/api/feeds
```

**Response:**
```json
[
  {
    "id": 1,
    "title": "BBC News",
    "url": "https://feeds.bbci.co.uk/news/rss.xml",
    "status": "active",
    "fetch_interval_minutes": 30,
    "last_fetched": "2025-09-23T10:30:00Z",
    "items_count": 245
  }
]
```

### Create New Feed

```bash
curl -X POST http://localhost:8000/api/feeds \
  -H "Content-Type: application/json" \
  -d '{
    "title": "TechCrunch",
    "url": "https://techcrunch.com/feed/",
    "fetch_interval_minutes": 60,
    "category_id": 2
  }'
```

### Update Feed

```bash
curl -X PUT http://localhost:8000/api/feeds/1 \
  -H "Content-Type: application/json" \
  -d '{
    "fetch_interval_minutes": 45,
    "status": "active"
  }'
```

### Delete Feed

```bash
curl -X DELETE http://localhost:8000/api/feeds/1
```

## Item Management

### Get Latest Items

```bash
# Get latest 50 items
curl -X GET "http://localhost:8000/api/items/latest?limit=50"

# Get items from specific feed
curl -X GET "http://localhost:8000/api/items?feed_id=1&limit=20"

# Get unanalyzed items
curl -X GET "http://localhost:8000/api/items?analyzed=false&limit=100"
```

### Search Items

```bash
curl -X GET "http://localhost:8000/api/items/search?q=technology&limit=20"
```

## Analysis Operations

### Start Analysis Run

```bash
curl -X POST http://localhost:8000/api/analysis/start \
  -H "Content-Type: application/json" \
  -d '{
    "scope": {
      "type": "global",
      "unanalyzed_only": true
    },
    "params": {
      "model_tag": "gpt-4.1-nano",
      "rate_per_second": 1.0,
      "limit": 100
    }
  }'
```

### Preview Analysis

```bash
curl -X POST http://localhost:8000/api/analysis/preview \
  -H "Content-Type: application/json" \
  -d '{
    "scope": {
      "type": "timerange",
      "start_time": "2025-09-22T00:00:00Z",
      "end_time": "2025-09-23T00:00:00Z"
    },
    "params": {
      "model_tag": "gpt-4.1-nano",
      "limit": 50
    }
  }'
```

**Response:**
```json
{
  "item_count": 45,
  "already_analyzed": 30,
  "to_analyze": 15,
  "estimated_cost_usd": 0.0045,
  "estimated_duration_minutes": 15
}
```

### Get Analysis Status

```bash
curl -X GET http://localhost:8000/api/analysis/status/123
```

### Cancel Analysis Run

```bash
curl -X POST http://localhost:8000/api/analysis/cancel/123
```

## Statistics

### System Statistics

```bash
curl -X GET http://localhost:8000/api/statistics/system
```

**Response:**
```json
{
  "total_feeds": 37,
  "active_feeds": 37,
  "total_items": 12450,
  "analyzed_items": 8932,
  "analysis_coverage": 71.7,
  "avg_fetch_time_ms": 245,
  "success_rate": 100
}
```

### Feed Performance

```bash
curl -X GET http://localhost:8000/api/statistics/feeds/performance
```

## Template Management

### List Templates

```bash
curl -X GET http://localhost:8000/api/templates
```

### Assign Template to Feed

```bash
curl -X POST http://localhost:8000/api/templates/assign \
  -H "Content-Type: application/json" \
  -d '{
    "feed_id": 1,
    "template_id": 2
  }'
```

## Health Monitoring

### Health Check

```bash
curl -X GET http://localhost:8000/api/health
```

**Response:**
```json
{
  "status": "healthy",
  "database": "connected",
  "worker": "running",
  "scheduler": "active",
  "uptime_seconds": 3600
}
```

### Detailed Health

```bash
curl -X GET http://localhost:8000/api/health/detailed
```

## MCP Protocol

### List Available Tools

```bash
curl -X POST http://localhost:8001/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/list",
    "id": 1
  }'
```

### Execute Tool

```bash
curl -X POST http://localhost:8001/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
      "name": "feeds.list",
      "arguments": {}
    },
    "id": 2
  }'
```

## Batch Operations

### Batch Create Feeds

```bash
curl -X POST http://localhost:8000/api/feeds/batch \
  -H "Content-Type: application/json" \
  -d '{
    "feeds": [
      {"title": "Feed 1", "url": "https://example1.com/rss"},
      {"title": "Feed 2", "url": "https://example2.com/rss"}
    ]
  }'
```

### Batch Update Status

```bash
curl -X PATCH http://localhost:8000/api/feeds/batch/status \
  -H "Content-Type: application/json" \
  -d '{
    "feed_ids": [1, 2, 3],
    "status": "paused"
  }'
```

## Pagination

Most list endpoints support pagination:

```bash
# Page 1, 20 items per page
curl -X GET "http://localhost:8000/api/items?page=1&limit=20"

# Page 2
curl -X GET "http://localhost:8000/api/items?page=2&limit=20"
```

## Filtering and Sorting

```bash
# Filter by date range
curl -X GET "http://localhost:8000/api/items?start_date=2025-09-01&end_date=2025-09-23"

# Sort by published date
curl -X GET "http://localhost:8000/api/items?sort=published&order=desc"

# Combine filters
curl -X GET "http://localhost:8000/api/items?feed_id=1&analyzed=true&sort=created_at&order=desc&limit=50"
```

## Error Handling

All endpoints return standard HTTP status codes:

- `200 OK` - Success
- `201 Created` - Resource created
- `400 Bad Request` - Invalid parameters
- `404 Not Found` - Resource not found
- `422 Unprocessable Entity` - Validation error
- `500 Internal Server Error` - Server error

**Error Response Format:**
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Request validation failed",
    "details": {
      "field": "url",
      "reason": "Invalid URL format"
    }
  }
}
```

## WebSocket Events (HTMX)

For real-time updates, connect to WebSocket:

```javascript
const ws = new WebSocket('ws://localhost:8000/ws');

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Event:', data.type, data.payload);
};

// Subscribe to feed updates
ws.send(JSON.stringify({
  type: 'subscribe',
  channel: 'feeds'
}));
```

## Rate Limiting

API endpoints have the following rate limits:

- General endpoints: 100 requests per minute
- Analysis endpoints: 10 requests per minute
- Batch operations: 5 requests per minute

Rate limit headers:
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1695470400
```

## Testing with Python

```python
import requests
import json

# Base URL
BASE_URL = 'http://localhost:8000'

# Get all feeds
response = requests.get(f'{BASE_URL}/api/feeds')
feeds = response.json()
print(f"Total feeds: {len(feeds)}")

# Create a new feed
new_feed = {
    'title': 'My Tech Blog',
    'url': 'https://myblog.com/rss',
    'fetch_interval_minutes': 60
}
response = requests.post(f'{BASE_URL}/api/feeds', json=new_feed)
if response.status_code == 201:
    created_feed = response.json()
    print(f"Created feed ID: {created_feed['id']}")

# Start analysis
analysis_config = {
    'scope': {'type': 'global', 'unanalyzed_only': True},
    'params': {'model_tag': 'gpt-4.1-nano', 'limit': 50}
}
response = requests.post(f'{BASE_URL}/api/analysis/start', json=analysis_config)
run = response.json()
print(f"Analysis run ID: {run['id']}")
```

## Related Documentation

- [API Documentation](./API_DOCUMENTATION.md) - Complete API reference
- [Database Schema](./DATABASE_SCHEMA.md) - Database structure
- [Testing Guide](./TESTING.md) - How to test the API
- [Deployment Guide](../DEPLOYMENT.md) - Production deployment