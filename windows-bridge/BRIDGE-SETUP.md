# News MCP Bridge Setup for Claude Desktop (Windows)

## 📋 Architecture

```
Claude Desktop (Windows) ↔ Bridge Process ↔ Linux HTTP Server (192.168.178.72:3001) ✅ Running

Windows Bridge Process ✅ Ready for setup
```

## 🎯 Step-by-Step Setup

### 1. Download Bridge Files

Download these files from the repository:
- `test-bridge.js`
- `mcp-news-bridge.js`

### 2. Place Files

Place both files in a folder like:
```
C:\MCP\news-bridge\
```

### 3. Install Dependencies

Open Command Prompt and run:
```bash
npm install axios
```

### 4. Test Connection

Test the bridge connection:
```bash
node C:\MCP\news-bridge\test-bridge.js
```

### 5. Update Claude Configuration

Add this to your Claude configuration:
```json
{
  "mcpServers": {
    "news-mcp-bridge": {
      "command": "node",
      "args": [
        "C:\\MCP\\news-bridge\\mcp-news-bridge.js"
      ]
    }
  }
}
```

### 6. Restart Claude Desktop

Close and restart Claude Desktop completely.

## 🔧 Available Tools

After successful setup, these tools are available:

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
3. **Bridge process fails:** Check Node.js installation

### Verification Checklist

- [ ] Linux HTTP Server running (Port 3001)
- [ ] Bridge files in correct location
- [ ] Node.js and npm installed
- [ ] Dependencies installed (axios)
- [ ] Claude configuration updated

## ⚠️ Important Notes

This bridge solution is more complex than the direct client. Consider using the [Direct Client Setup](./DIRECT-CLIENT-SETUP.md) instead for simpler configuration.

The bridge setup is recommended only for advanced users who need custom bridge functionality.