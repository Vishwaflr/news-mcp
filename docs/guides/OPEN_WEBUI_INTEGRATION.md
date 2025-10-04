# News MCP - Open WebUI Integration Guide

Complete guide for integrating News MCP with Open WebUI for seamless news aggregation and analysis capabilities.

## Overview

News MCP provides a comprehensive HTTP-based MCP server that integrates seamlessly with Open WebUI, offering 14 specialized tools for RSS feed management, article analysis, and content processing.

## Quick Start

### 1. Start the HTTP MCP Server

```bash
# Navigate to News MCP directory
cd /path/to/news-mcp

# Start HTTP MCP server (recommended)
./scripts/start_mcp_server.sh http

# OR direct command
uvicorn http_mcp_server:app --host 0.0.0.0 --port 8001
```

### 2. Verify Server Status

```bash
# Health check
curl http://localhost:8001/health

# OpenAPI documentation
curl http://localhost:8001/openapi.json

# Test system ping
curl -X POST http://localhost:8001/mcp/tools/system.ping \
  -H "Content-Type: application/json" -d '{}'
```

## Open WebUI Configuration

### Method 1: External Tool Configuration

In Open WebUI settings, configure News MCP as an external tool:

```yaml
external_tools:
  news_mcp:
    name: "News MCP"
    description: "RSS feed management and news analysis"
    base_url: "http://192.168.178.72:8001"
    auth_type: "none"
    endpoints:
      system_ping:
        path: "/mcp/tools/system.ping"
        method: "POST"
        description: "System health check"
      feeds_list:
        path: "/mcp/tools/feeds.list"
        method: "POST"
        description: "List all RSS feeds"
      articles_latest:
        path: "/mcp/tools/articles.latest"
        method: "POST"
        description: "Get latest articles"
      articles_search:
        path: "/mcp/tools/articles.search"
        method: "POST"
        description: "Search articles"
```

### Method 2: OpenAPI Import

1. Access Open WebUI Settings → External Tools
2. Import from OpenAPI URL: `http://192.168.178.72:8001/openapi.json`
3. Configure base URL and authentication (none required)

## Available Tools

### System Management
- **`system.ping`** - Health check and connectivity test
- **`system.health`** - Comprehensive system status

### Feed Management
- **`feeds.list`** - List all RSS feeds with metadata
- **`feeds.add`** - Add new RSS feeds
- **`feeds.update`** - Update feed configuration
- **`feeds.delete`** - Remove feeds
- **`feeds.test`** - Test feed connectivity
- **`feeds.refresh`** - Force feed refresh
- **`feeds.performance`** - Get performance metrics
- **`feeds.diagnostics`** - Detailed diagnostics

### Content & Articles
- **`articles.latest`** - Get recent articles with filtering
- **`articles.search`** - Full-text search across articles

### Template Management
- **`templates.assign`** - Manage feed-specific templates

### Data Export
- **`data.export`** - Export data in various formats

## Usage Examples

### Basic Health Check

```bash
curl -X POST http://192.168.178.72:8001/mcp/tools/system.ping \
  -H "Content-Type: application/json" \
  -d '{}'
```

**Response:**
```json
{
  "ok": true,
  "data": {
    "content": ["{\"ok\": true, \"data\": {\"pong\": true}}"]
  },
  "meta": {"tool": "system.ping"},
  "errors": []
}
```

### Get System Status

```bash
curl -X POST http://192.168.178.72:8001/mcp/tools/system.health \
  -H "Content-Type: application/json" \
  -d '{}'
```

### List All Feeds

```bash
curl -X POST http://192.168.178.72:8001/mcp/tools/feeds.list \
  -H "Content-Type: application/json" \
  -d '{}'
```

### Get Latest Articles

```bash
curl -X POST http://192.168.178.72:8001/mcp/tools/articles.latest \
  -H "Content-Type: application/json" \
  -d '{"limit": 10}'
```

### Search Articles

```bash
curl -X POST http://192.168.178.72:8001/mcp/tools/articles.search \
  -H "Content-Type: application/json" \
  -d '{"query": "artificial intelligence", "limit": 5}'
```

## API Response Format

All News MCP tools return responses in this standardized format:

```json
{
  "ok": boolean,
  "data": {
    "content": ["JSON string or array of results"]
  },
  "meta": {
    "tool": "tool_name",
    "execution_time": "duration"
  },
  "errors": []
}
```

## Error Handling

### Common HTTP Status Codes
- **200 OK** - Successful tool execution
- **404 Not Found** - Tool or endpoint not available
- **405 Method Not Allowed** - Wrong HTTP method
- **500 Internal Server Error** - Tool execution error

### Error Response Format
```json
{
  "ok": false,
  "data": null,
  "meta": {"tool": "tool_name"},
  "errors": ["Error description"]
}
```

## CORS Configuration

The HTTP MCP server includes CORS middleware for cross-origin requests:

```python
# Allowed origins for Open WebUI
allowed_origins = [
    "http://localhost:3000",
    "http://localhost:8080",
    "http://192.168.178.78:*",
    "*"  # Development only
]
```

## Troubleshooting

### Connection Issues

1. **Verify server is running:**
   ```bash
   curl http://192.168.178.72:8001/health
   ```

2. **Check Open WebUI logs for errors**

3. **Verify network connectivity between Open WebUI and News MCP server**

### Tool Execution Failures

1. **Check tool syntax and parameters**
2. **Verify database connection:** `curl -X POST .../system.health`
3. **Review News MCP server logs**

### Performance Optimization

- **Database indexing:** Run `python scripts/index_check.py`
- **Feed refresh intervals:** Adjust in database or via `feeds.update`
- **Article retention:** Configure cleanup policies

## Advanced Configuration

### Custom Tool Parameters

Most tools accept optional parameters for filtering and customization:

```json
{
  "limit": 10,
  "offset": 0,
  "filter": {
    "category": "technology",
    "published_after": "2024-01-01"
  }
}
```

### Performance Monitoring

Monitor News MCP performance through:
- **System health endpoint:** `/mcp/tools/system.health`
- **Feed diagnostics:** `/mcp/tools/feeds.diagnostics`
- **Database metrics:** Built into health checks

## Integration Best Practices

1. **Use health checks** before heavy operations
2. **Implement retry logic** for network operations
3. **Cache results** when appropriate
4. **Monitor API rate limits** and response times
5. **Handle errors gracefully** with fallback options

## Security Considerations

- News MCP currently operates without authentication
- Ensure network-level security between Open WebUI and News MCP
- Consider VPN or firewall rules for production deployments
- Monitor access logs for suspicious activity

## Support and Documentation

- **Main README:** `README.md`
- **API Documentation:** `http://192.168.178.72:8001/openapi.json`
- **Health Monitoring:** `http://192.168.178.72:8001/health`
- **Test Script:** `./test_endpoints.sh`

For technical support and feature requests, consult the main documentation or system logs.