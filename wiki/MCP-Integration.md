# MCP Integration - Claude Desktop Setup

Complete guide for integrating News MCP with **Claude Desktop** using the Model Context Protocol.

---

## 🔌 What is MCP?

**Model Context Protocol (MCP)** allows Claude Desktop to directly interact with your News MCP system through **48 native tools**, enabling natural language control of feeds, analysis, and monitoring.

### What You Can Do

**Instead of:**
```
User → Web Dashboard → Click buttons → Manually configure
```

**You can now:**
```
User: "Show me all my RSS feeds"
Claude: *uses list_feeds tool* → Returns formatted feed list

User: "Add TechCrunch feed and enable auto-analysis"
Claude: *uses add_feed + update_feed tools* → Done!

User: "What are the trending topics today?"
Claude: *uses trending_topics tool* → Analyzes and returns insights
```

---

## 🚀 Quick Setup (3 Steps)

### Step 1: Start MCP Server

```bash
cd /home/cytrex/news-mcp
source venv/bin/activate
python3 http_mcp_server.py &
```

**Verify server is running:**
```bash
curl http://localhost:8001/health
# Expected: {"status":"healthy"}
```

### Step 2: Configure Claude Desktop

**Find config file:**
- **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`
- **Linux:** `~/.config/Claude/claude_desktop_config.json`

**Add configuration:**
```json
{
  "mcpServers": {
    "news-mcp": {
      "command": "node",
      "args": ["/home/cytrex/news-mcp/mcp-http-bridge.js"],
      "env": {
        "NEWS_MCP_SERVER_URL": "http://localhost:8001"
      }
    }
  }
}
```

**Replace `/home/cytrex/news-mcp` with your actual path!**

### Step 3: Restart Claude Desktop

1. Quit Claude Desktop completely
2. Relaunch Claude Desktop
3. Look for 🔌 icon (MCP tools connected)
4. Try: "List all my RSS feeds"

---

## 🛠️ Available MCP Tools (48 Total)

### 📡 Feed Management (6 tools)

| Tool | Purpose | Example Usage |
|------|---------|---------------|
| `list_feeds` | List all feeds with health metrics | "Show me all my RSS feeds" |
| `add_feed` | Add new RSS feed | "Add https://techcrunch.com/feed/" |
| `update_feed` | Update feed configuration | "Pause feed #5" |
| `delete_feed` | Delete feed (requires confirmation) | "Delete feed #10 with confirmation" |
| `test_feed` | Test feed URL before adding | "Test this RSS feed: https://example.com/rss" |
| `refresh_feed` | Manually trigger feed update | "Refresh feed #3 immediately" |

**Example Interaction:**
```
You: "Add TechCrunch RSS feed"
Claude: *uses add_feed with url="https://techcrunch.com/feed/"*
       "✅ Added TechCrunch feed (ID: 15) with 50 articles fetched"

You: "What's the status of my feeds?"
Claude: *uses list_feeds*
       "You have 15 active feeds. Top feeds by activity:
        1. TechCrunch - 50 items, healthy ✅
        2. The Verge - 42 items, healthy ✅
        3. Wired - 35 items, warning ⚠️ (2 fetch failures)"
```

---

### 📊 Analytics & Insights (6 tools)

| Tool | Purpose | Example Usage |
|------|---------|---------------|
| `get_dashboard` | System overview statistics | "Show me dashboard stats" |
| `feed_performance` | Feed efficiency metrics | "How is feed #5 performing?" |
| `latest_articles` | Recent articles with filters | "Show latest 10 articles from TechCrunch" |
| `search_articles` | Full-text article search | "Find articles about AI from last week" |
| `trending_topics` | Keyword analysis | "What are the trending topics today?" |
| `export_data` | Export articles (JSON/CSV) | "Export all tech articles as JSON" |

**Example Interaction:**
```
You: "What are the trending topics in my feeds today?"
Claude: *uses trending_topics with timeframe="1d"*
       "📊 Top trending topics (last 24 hours):
        1. 'AI' - 45 mentions (↑ 120%)
        2. 'OpenAI' - 32 mentions (↑ 85%)
        3. 'GPT-4' - 28 mentions (↑ 90%)
        4. 'Apple' - 21 mentions (↓ 15%)"

You: "Find all articles about OpenAI from this week"
Claude: *uses search_articles with query="OpenAI" days=7*
       "Found 18 articles about OpenAI:
        1. 'OpenAI releases GPT-4 Turbo' - TechCrunch - 2 days ago
        2. 'OpenAI CEO discusses AI safety' - The Verge - 3 days ago
        ..."
```

---

### 🎯 Analysis Tools (3 tools)

| Tool | Purpose | Example Usage |
|------|---------|---------------|
| `analysis_preview` | Preview analysis selection | "Preview analysis for feed #5" |
| `analysis_run` | Start AI analysis run | "Analyze latest 50 items from TechCrunch" |
| `analysis_history` | View past analysis results | "Show my recent analysis runs" |

**Example Interaction:**
```
You: "Analyze the latest 50 articles from TechCrunch"
Claude: *uses analysis_preview to check scope*
       "Preview: 50 articles will be analyzed
        Estimated cost: $0.25
        Estimated time: 17 seconds"

       *uses analysis_run to start*
       "✅ Analysis started (Run #123)
        Progress: 50/50 items processed
        Results: 32 positive, 12 neutral, 6 negative sentiment"
```

---

### 🏷️ Templates (5 tools)

| Tool | Purpose | Example Usage |
|------|---------|---------------|
| `list_templates` | List feed templates | "Show all available templates" |
| `template_performance` | Template usage stats | "How are templates performing?" |
| `templates_create` | Create new template | "Create template for Hacker News" |
| `templates_test` | Test template matching | "Test template against feed URL" |
| `templates_assign` | Assign template to feed | "Assign template #3 to feed #5" |

---

### 🗄️ Database Access (3 tools)

| Tool | Purpose | Example Usage |
|------|---------|---------------|
| `execute_query` | Run safe read-only SQL | "Query: SELECT COUNT(*) FROM items" |
| `table_info` | Get schema information | "Show me the feeds table schema" |
| `quick_queries` | Predefined useful queries | "Run feed health diagnostic query" |

**Example Interaction:**
```
You: "How many articles do I have in total?"
Claude: *uses execute_query with SQL*
       "You have 11,254 articles across all feeds"

You: "Which feeds have the most articles?"
Claude: *uses quick_queries → "top feeds by item count"*
       "Top 5 feeds by articles:
        1. TechCrunch - 1,250 articles
        2. The Verge - 987 articles
        3. Wired - 845 articles
        4. Ars Technica - 712 articles
        5. Engadget - 598 articles"
```

---

### ❤️ Health & Monitoring (6 tools)

| Tool | Purpose | Example Usage |
|------|---------|---------------|
| `system_health` | Overall system status | "Check system health" |
| `feed_diagnostics` | Detailed feed health check | "Diagnose feed #12" |
| `error_analysis` | System error patterns | "Show me recent errors" |
| `scheduler_status` | Feed scheduler status | "Is the scheduler running?" |
| `log_analysis` | Analyze system logs | "Show errors from last hour" |
| `usage_stats` | System usage statistics | "Show API usage stats" |

**Example Interaction:**
```
You: "Is my system healthy?"
Claude: *uses system_health*
       "✅ System Status: Healthy
        • Web Server: Running
        • Database: Connected
        • Worker: Active (processing 2 runs)
        • Scheduler: Running (last fetch 2 min ago)
        • Queue: 15 items pending
        • No critical issues detected"

You: "Why is feed #12 failing?"
Claude: *uses feed_diagnostics with feed_id=12*
       "🔴 Feed #12 Issues:
        • 5 consecutive fetch failures
        • Last error: 'HTTP 403 Forbidden'
        • Last successful fetch: 2 days ago
        • Recommendation: Check feed URL or contact publisher"
```

---

### 🏷️ Categories & Sources (9 tools)

| Tool | Purpose | Example Usage |
|------|---------|---------------|
| `categories_list` | List all categories | "Show me all categories" |
| `categories_add` | Create new category | "Add category: Crypto" |
| `categories_update` | Update category | "Rename category #5 to Web3" |
| `categories_delete` | Delete category | "Delete empty category #8" |
| `categories_assign` | Assign feed to category | "Put feed #10 in Tech category" |
| `sources_list` | List news sources | "Show all sources" |
| `sources_add` | Add new source | "Add source: Reuters" |
| `sources_update` | Update source info | "Update source #5 trust level to 5" |
| `sources_delete` | Delete source | "Delete source #12" |
| `sources_stats` | Source statistics | "Show stats for source #3" |

---

### 🔧 Scheduler Tools (3 tools)

| Tool | Purpose | Example Usage |
|------|---------|---------------|
| `scheduler_status` | Check scheduler health | "Is scheduler running?" |
| `scheduler_set_interval` | Update feed intervals | "Set feed #5 to fetch every 30 minutes" |
| `scheduler_heartbeat` | Scheduler heartbeat check | "Ping scheduler" |

---

### 🔍 Search & Discovery (3 tools)

| Tool | Purpose | Example Usage |
|------|---------|---------------|
| `feeds_search` | Search feeds by keyword | "Find feeds about 'technology'" |
| `feeds_health` | Health status of all feeds | "Which feeds are unhealthy?" |
| `items_recent` | Recent items with filters | "Show recent items from last hour" |
| `items_search` | Search items by criteria | "Find items tagged 'AI'" |

---

### 🛠️ Utility Tools (4 tools)

| Tool | Purpose | Example Usage |
|------|---------|---------------|
| `system_ping` | Server connectivity test | "Ping the MCP server" |
| `maintenance_tasks` | Run maintenance operations | "Run database cleanup" |
| `usage_stats` | Detailed usage metrics | "Show OpenAI API usage" |

---

## 🌐 Remote/LAN Access

Connect Claude Desktop from **another machine** on your network.

### Server Setup

**On the server machine (where News MCP runs):**

1. Find your server's IP:
```bash
hostname -I
# Example output: 192.168.1.100
```

2. Ensure MCP server binds to all interfaces:
```bash
# In http_mcp_server.py, verify:
# app.run(host="0.0.0.0", port=8001)
```

3. Allow firewall access:
```bash
# Ubuntu/Debian
sudo ufw allow 8001/tcp

# Or firewalld
sudo firewall-cmd --add-port=8001/tcp --permanent
sudo firewall-cmd --reload
```

### Client Setup

**On Claude Desktop machine:**

Edit `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "news-mcp": {
      "command": "node",
      "args": ["/path/to/mcp-http-bridge.js"],
      "env": {
        "NEWS_MCP_SERVER_URL": "http://192.168.1.100:8001"
      }
    }
  }
}
```

**Replace `192.168.1.100` with your server's actual IP!**

### Verify Connection

```bash
# From Claude Desktop machine
curl http://192.168.1.100:8001/health

# Expected:
# {"status":"healthy"}
```

---

## 📡 MCP Server Architecture

```
┌──────────────────────────────────────────────────────┐
│ Claude Desktop (MCP Client)                          │
│ ┌──────────────────────────────────────────────────┐ │
│ │ User: "Show me my RSS feeds"                     │ │
│ │ Claude: *detects intent → calls MCP tool*       │ │
│ └──────────────────────────────────────────────────┘ │
└─────────────────┬────────────────────────────────────┘
                  │ JSON-RPC over stdio
                  ↓
┌─────────────────────────────────────────────────────┐
│ mcp-http-bridge.js (Node.js Bridge)                 │
│ Converts: stdio ↔ HTTP                              │
└─────────────────┬───────────────────────────────────┘
                  │ HTTP/JSON
                  ↓
┌─────────────────────────────────────────────────────┐
│ HTTP MCP Server (Port 8001)                         │
│ • FastAPI application                               │
│ • 48 MCP tools registered                           │
│ • JSON-RPC 2.0 handler                              │
└─────────────────┬───────────────────────────────────┘
                  │ Internal API calls
                  ↓
┌─────────────────────────────────────────────────────┐
│ News MCP Core (Port 8000)                           │
│ • Database (PostgreSQL)                             │
│ • Analysis Worker                                   │
│ • Feed Scheduler                                    │
└─────────────────────────────────────────────────────┘
```

---

## 🐛 Troubleshooting

### Issue: Claude Desktop shows "MCP server not connected"

**Possible Causes:**
- MCP server not running
- Incorrect path in config
- Node.js not installed

**Solutions:**
```bash
# 1. Check MCP server is running
curl http://localhost:8001/health

# 2. If not running, start it
cd /home/cytrex/news-mcp
source venv/bin/activate
python3 http_mcp_server.py &

# 3. Verify Node.js installed
node --version

# 4. Check config path
cat ~/Library/Application\ Support/Claude/claude_desktop_config.json

# 5. Check bridge file exists
ls -la /home/cytrex/news-mcp/mcp-http-bridge.js
```

### Issue: Tools appear but fail when called

**Possible Causes:**
- Core web server not running (port 8000)
- Database connection issues
- Authentication errors

**Solutions:**
```bash
# 1. Check web server status
curl http://localhost:8000/api/health/status

# 2. If not running, start services
./scripts/start-all-background.sh

# 3. Check logs
tail -f logs/mcp-server.log

# 4. Verify database connection
PGPASSWORD=news_password psql -h localhost -U news_user -d news_db -c "\dt"
```

### Issue: "Permission denied" errors

**Cause:** Bridge script not executable

**Solution:**
```bash
chmod +x /home/cytrex/news-mcp/mcp-http-bridge.js
```

### Issue: Remote access not working

**Possible Causes:**
- Firewall blocking port 8001
- Server binding to localhost only
- Wrong IP address in config

**Solutions:**
```bash
# 1. Verify server listens on all interfaces
netstat -tuln | grep 8001
# Should show: 0.0.0.0:8001 (not 127.0.0.1:8001)

# 2. Test from remote machine
curl http://192.168.1.100:8001/health

# 3. Check firewall
sudo ufw status
sudo ufw allow 8001/tcp

# 4. Verify IP address
hostname -I
```

---

## 🎯 Example Workflows

### Workflow 1: Daily News Monitoring

```
You: "What's new in my feeds today?"
Claude: *uses latest_articles + trending_topics*
       "Today's highlights:
        • 127 new articles across 15 feeds
        • Top topic: 'GPT-4 Turbo' (32 mentions)
        • TechCrunch posted 18 new articles
        • 2 feeds have warnings (The Verge, Wired)"

You: "Show me articles about GPT-4"
Claude: *uses search_articles*
       "Found 28 articles about GPT-4:
        [Lists top 10 with sentiment analysis]"
```

### Workflow 2: Feed Management

```
You: "Add these RSS feeds: TechCrunch, The Verge, Wired"
Claude: *uses add_feed 3 times*
       "✅ Added 3 feeds:
        • TechCrunch (ID: 15) - 50 articles fetched
        • The Verge (ID: 16) - 42 articles fetched
        • Wired (ID: 17) - 35 articles fetched"

You: "Enable auto-analysis for all 3 feeds"
Claude: *uses update_feed 3 times*
       "✅ Auto-analysis enabled for all 3 feeds
        Items will be analyzed automatically as they arrive"
```

### Workflow 3: System Health Check

```
You: "Run a full system health check"
Claude: *uses system_health + feed_diagnostics + error_analysis*
       "🔍 System Health Report:

        Overall: ✅ Healthy

        Services:
        • Web Server: ✅ Running
        • Database: ✅ Connected (11,254 items)
        • Worker: ✅ Active (2 runs in progress)
        • Scheduler: ✅ Running (last fetch 1 min ago)

        Feeds:
        • 15 active, 2 paused
        • 3 feeds with warnings:
          - Feed #12: 403 Forbidden (check URL)
          - Feed #8: Slow response (>5s)
          - Feed #19: No new items (48h)

        Recommendations:
        1. Check Feed #12 URL permissions
        2. Consider increasing Feed #8 timeout
        3. Verify Feed #19 is still publishing"
```

---

## 📚 Related Documentation

- **[Quick Start](Quick-Start)** - Initial setup
- **[Dashboard Overview](Dashboard-Overview)** - Web interface alternative
- **[API Reference](API-Overview)** - Direct API access
- **[Architecture](Architecture)** - System design
- **[Troubleshooting](Troubleshooting-MCP)** - MCP-specific issues

---

## 🔗 Official MCP Resources

- **MCP Specification:** https://modelcontextprotocol.io/
- **MCP SDK:** https://github.com/anthropics/mcp
- **Claude Desktop:** https://claude.ai/download

---

**Server File:** `http_mcp_server.py`
**Bridge File:** `mcp-http-bridge.js`
**Tools Defined:** `mcp_server/comprehensive_server.py`
**Total Tools:** 48
**Last Updated:** 2025-10-01
