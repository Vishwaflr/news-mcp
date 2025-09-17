# News MCP Server - LAN Access

This document describes how to set up and use the News MCP Server for LAN access.

## Overview

The News MCP Server provides comprehensive access to the News-MCP system via the Model Context Protocol (MCP). It offers 20+ tools for managing feeds, analyzing data, monitoring health, and administering the system.

## Features

### Feed Management
- **list_feeds**: List all RSS feeds with status and health info
- **add_feed**: Add new RSS feeds with automatic template detection
- **update_feed**: Update feed configuration (interval, status, title)
- **delete_feed**: Remove feeds and all associated articles
- **test_feed**: Test feed URLs without adding them
- **refresh_feed**: Manually trigger feed refresh

### Analytics & Statistics
- **get_dashboard**: Comprehensive dashboard statistics
- **feed_performance**: Analyze feed performance over time
- **latest_articles**: Get recent articles with filtering
- **search_articles**: Search articles by keywords
- **trending_topics**: Analyze trending keywords and topics
- **export_data**: Export data in JSON/CSV formats

### Template Management
- **list_templates**: List dynamic feed templates
- **template_performance**: Analyze template usage and performance
- **assign_template**: Assign templates to feeds (manual or auto)

### Database Operations
- **execute_query**: Execute safe read-only SQL queries
- **table_info**: Get database table structure and info
- **quick_queries**: Predefined useful queries (summary, stats, errors)

### Health Monitoring
- **system_health**: Overall system health status
- **feed_diagnostics**: Detailed feed health analysis
- **error_analysis**: Analyze system errors and failures
- **scheduler_status**: Check feed scheduler status

### Administration
- **maintenance_tasks**: System maintenance (cleanup, vacuum, etc.)
- **log_analysis**: Analyze system logs for patterns
- **usage_stats**: System usage statistics and metrics

## Setup for LAN Access

### 1. Prerequisites

Ensure the News-MCP system is running:
```bash
cd /home/cytrex/news-mcp
source venv/bin/activate
python3 app/main.py  # Web interface should be running
```

### 2. Start MCP Server

```bash
cd /home/cytrex/news-mcp
source venv/bin/activate
python3 start_mcp_server.py
```

### 3. Client Configuration

For Claude Desktop or other MCP clients, add this configuration:

```json
{
  "mcpServers": {
    "news-mcp": {
      "command": "ssh",
      "args": [
        "user@YOUR_SERVER_IP",
        "cd /home/cytrex/news-mcp && source venv/bin/activate && python3 start_mcp_server.py"
      ],
      "env": {
        "PYTHONPATH": "/home/cytrex/news-mcp"
      }
    }
  }
}
```

Replace `YOUR_SERVER_IP` with the actual IP address of the server running News-MCP.

### 4. Alternative: Direct Network Access

If you want to expose the MCP server directly on the network, you can modify the server to use TCP instead of stdio. However, the current implementation uses stdio for security.

## Usage Examples

### 1. List All Feeds
```
Tool: list_feeds
Parameters: {"include_health": true, "include_stats": true}
```

### 2. Add New Feed
```
Tool: add_feed
Parameters: {
  "url": "https://example.com/rss.xml",
  "title": "Example News",
  "fetch_interval_minutes": 15
}
```

### 3. Get Dashboard Statistics
```
Tool: get_dashboard
Parameters: {}
```

### 4. Search Articles
```
Tool: search_articles
Parameters: {
  "query": "technology",
  "limit": 20,
  "hours": 24
}
```

### 5. Execute Database Query
```
Tool: execute_query
Parameters: {
  "query": "SELECT COUNT(*) as total_items FROM items WHERE created_at > NOW() - INTERVAL '24 hours'"
}
```

### 6. Analyze Feed Performance
```
Tool: feed_performance
Parameters: {
  "days": 7,
  "limit": 10
}
```

### 7. System Health Check
```
Tool: system_health
Parameters: {}
```

## Security Features

- **Read-only database queries**: SQL injection protection with query validation
- **Safe operations**: Only safe maintenance operations are allowed
- **Input validation**: All parameters are validated before execution
- **Error handling**: Comprehensive error handling and logging

## Network Requirements

- **Protocol**: stdio (no direct network ports)
- **Access**: SSH-based for LAN clients
- **Firewall**: No additional ports needed (uses SSH)
- **Authentication**: Uses existing SSH authentication

## Troubleshooting

### Server won't start
1. Check that the News-MCP database is accessible
2. Verify Python path and virtual environment
3. Check log output for specific errors

### Client can't connect
1. Verify SSH access to the server
2. Check that the News-MCP system is running
3. Verify the correct paths in client configuration

### Database errors
1. Ensure PostgreSQL is running and accessible
2. Check database connection in News-MCP config
3. Verify database permissions

## Monitoring

The server logs all operations and errors. Monitor the console output or system logs for:
- Tool execution times
- Database query performance
- Error patterns
- Client connections

## Support

For issues specific to the MCP server:
1. Check the server logs for error messages
2. Verify News-MCP web interface is working
3. Test database connectivity separately
4. Check SSH access and permissions