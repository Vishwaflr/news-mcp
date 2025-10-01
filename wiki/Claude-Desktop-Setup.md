# Claude Desktop Setup - MCP Integration

Connect News MCP to Claude Desktop via Model Context Protocol.

---

## 🎯 Quick Setup

### Step 1: Start MCP Server

```bash
cd /path/to/news-mcp
./scripts/start_mcp_server.sh

# MCP Server runs on http://localhost:8001
```

### Step 2: Configure Claude Desktop

**Location:** `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS)

```json
{
  "mcpServers": {
    "news-mcp": {
      "command": "node",
      "args": ["/path/to/news-mcp/mcp-http-bridge.js"],
      "env": {
        "NEWS_MCP_SERVER_URL": "http://localhost:8001"
      }
    }
  }
}
```

### Step 3: Restart Claude Desktop

Close and reopen Claude Desktop. You should see "news-mcp" in the MCP tools list.

---

## 🔌 Using MCP Tools in Claude

Once configured, you can use commands like:

> "Show me all active RSS feeds"

> "Search for articles about AI published in the last 7 days"

> "Run an analysis on the latest 50 technology articles"

---

## 🔗 Related Documentation

- **[MCP Integration](MCP-Integration)** - Complete MCP guide
- **[MCP Tools Reference](MCP-Tools-Reference)** - All 48 tools
- **[MCP Remote Access](MCP-Remote-Access)** - Remote/LAN setup

---

**Last Updated:** 2025-10-01
