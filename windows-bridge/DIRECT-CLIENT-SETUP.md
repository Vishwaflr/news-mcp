# News MCP Direct Client Setup for Claude Desktop (Windows)

Complete setup guide for the News MCP Direct Client on Windows with Claude Desktop.

## 🎯 Current Status

Linux Server HTTP API (192.168.178.72:3001) ✅ Running

Windows Direct Client ✅ Ready for setup

## 🎯 Step-by-Step Setup

### 1. Download the Direct Client

Download the latest `direct-http-mcp-client.js` from:
```
https://github.com/your-org/news-mcp/tree/main/windows-bridge
```

### 2. Place Client File

Place the file in your Claude configuration folder:
```
%APPDATA%\Claude\mcp\
```

Create the folder if it doesn't exist.

### 3. Update Claude Configuration

Add this to your Claude configuration file:
```json
{
  "mcpServers": {
    "news-mcp-direct": {
      "command": "node",
      "args": [
        "%APPDATA%\\Claude\\mcp\\direct-http-mcp-client.js"
      ],
      "env": {
        "NEWS_MCP_SERVER_URL": "http://192.168.178.72:3001"
      }
    }
  }
}
```

### 4. Restart Claude Desktop

Close and restart Claude Desktop completely.

### 5. Test Connection

Try these commands in Claude:
```
Show me the available news feeds
Get the latest news articles
Add a new RSS feed
```

## 🔧 Available Tools

After successful setup, all 25 News MCP tools are available:

### Feed Management
- `add_feed` - Add new feed
- `update_feed` - Update feed configuration
- `delete_feed` - Delete feed
- `list_feeds` - List all feeds
- `get_feed` - Get specific feed details

### Article Management
- `get_articles` - Get articles with filters
- `search_articles` - Search articles by content
- `get_article` - Get specific article

### Template Management
- `list_templates` - List all templates
- `create_template` - Create new template
- `update_template` - Update template
- `delete_template` - Delete template
- `assign_template` - Assign template to feed

### Statistics & Health
- `get_feed_stats` - Get feed statistics
- `get_system_health` - Get system health status
- `get_feed_health` - Get specific feed health

### Categories & Sources
- `list_categories` - List all categories
- `create_category` - Create new category
- `list_sources` - List all sources

### Feed Processing
- `trigger_feed_update` - Manually update feed
- `get_feed_items` - Get items from specific feed
- `refresh_all_feeds` - Refresh all feeds

### Content Processing
- `reprocess_articles` - Reprocess articles with new templates
- `get_processing_status` - Get current processing status
- `clear_failed_items` - Clear failed processing items

## 🔍 Troubleshooting

### Common Issues

1. **Server not reachable:** Check Linux HTTP server
2. **Tools not available:** Restart Claude Desktop
3. **Connection timeout:** Check network connectivity

### Verification Checklist

- [ ] Linux HTTP Server running (Port 3001)
- [ ] Direct client file in correct location
- [ ] Claude configuration updated
- [ ] Claude Desktop restarted
- [ ] Network connectivity verified

## 🆚 Differences to Bridge Solution

### Direct Solution (Recommended)
✅ Simple setup
✅ No additional bridge process
✅ Direct HTTP communication
✅ Automatic reconnection

### Bridge Solution
❌ More complex setup
❌ Additional bridge process required
❌ More potential failure points
⚠️ For advanced users only

## ✅ After Setup Available:

All 25 MCP tools for complete news management:
- Feed management (add, update, delete feeds)
- Article search and filtering
- Template management system
- Health monitoring and statistics
- Category and source management
- Automated content processing

The update solves all connection problems! 🚀