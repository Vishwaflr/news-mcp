# Troubleshooting Guide - Common Issues & Solutions

Quick solutions for common News MCP problems.

---

## 🚨 Quick Diagnostic Commands

```bash
# Check all services status
./scripts/status.sh

# Check web server
curl http://localhost:8000/api/health/status

# Check MCP server
curl http://localhost:8001/health

# Check database connection
PGPASSWORD=news_password psql -h localhost -U news_user -d news_db -c "SELECT 1"

# View logs
tail -f logs/analysis-worker.log
tail -f logs/scheduler.log
```

---

## 🔧 Service Issues

### Web Server Won't Start

**Symptoms:**
- `curl http://localhost:8000` fails
- "Address already in use" error
- Port 8000 blocked

**Solutions:**

```bash
# 1. Check if port is in use
lsof -i :8000

# 2. Kill existing process
kill -9 <PID>

# 3. Or use different port
uvicorn app.main:app --host 0.0.0.0 --port 8001

# 4. Check for errors
cat logs/webserver.log
```

### Analysis Worker Not Processing

**Symptoms:**
- Analysis runs stuck at "Queued"
- No progress updates
- Worker PID file exists but process dead

**Solutions:**

```bash
# 1. Check worker status
ps aux | grep analysis_worker

# 2. View worker logs
tail -f logs/analysis-worker.log

# 3. Restart worker
./scripts/stop-all.sh
./scripts/start-worker.sh

# 4. Check queue manually
curl http://localhost:8000/api/analysis/manager/queue
```

### Feed Scheduler Not Running

**Symptoms:**
- Feeds not updating
- No fetch logs
- Scheduler PID missing

**Solutions:**

```bash
# 1. Check scheduler status
ps aux | grep feed_scheduler

# 2. View scheduler logs
tail -f logs/scheduler.log

# 3. Restart scheduler
./scripts/start-scheduler.sh

# 4. Verify database connection
PGPASSWORD=news_password psql -h localhost -U news_user -d news_db -c "SELECT * FROM feeds LIMIT 1"
```

---

## 🗄️ Database Issues

### Connection Failed

**Error:** `psycopg2.OperationalError: could not connect to server`

**Solutions:**

```bash
# 1. Check PostgreSQL is running
sudo systemctl status postgresql

# 2. Start if stopped
sudo systemctl start postgresql

# 3. Verify credentials
psql -h localhost -U news_user -d news_db
# Password: news_password

# 4. Check DATABASE_URL in .env
cat .env | grep DATABASE_URL

# 5. Test connection manually
python3 -c "from app.database import engine; print(engine.connect())"
```

### Migration Errors

**Error:** `alembic.util.exc.CommandError`

**Solutions:**

```bash
# 1. Check current version
alembic current

# 2. View migration history
alembic history

# 3. Downgrade one version
alembic downgrade -1

# 4. Upgrade to head
alembic upgrade head

# 5. If migrations are broken, reset
# WARNING: This deletes all data!
rm -rf alembic/versions/*
psql -h localhost -U news_user -d news_db -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
alembic revision --autogenerate -m "initial"
alembic upgrade head
```

### Table Does Not Exist

**Error:** `relation "feeds" does not exist`

**Solution:**

```bash
# Create tables directly
python3 -c "from app.database import create_tables; create_tables()"

# Or via alembic
alembic upgrade head
```

---

## 📡 Feed Issues

### Feed Fetch Failures

**Symptoms:**
- Feed shows "ERROR" status
- No new items
- Consecutive failures counter increasing

**Diagnostics:**

```sql
-- Check feed health
SELECT f.id, f.title, fh.consecutive_failures, fh.last_error_message
FROM feeds f
LEFT JOIN feed_health fh ON f.id = fh.feed_id
WHERE fh.consecutive_failures > 3;

-- Check fetch logs
SELECT * FROM fetch_log
WHERE feed_id = <FEED_ID>
ORDER BY started_at DESC
LIMIT 10;
```

**Solutions:**

```bash
# 1. Test feed URL manually
curl -I "https://example.com/feed/"

# 2. Verify URL format
# Should be RSS/Atom XML, not HTML

# 3. Check for authentication requirements
# Some feeds require API keys

# 4. Verify feed parsing
curl http://localhost:8000/api/feeds/<FEED_ID>/test

# 5. Reset feed health
UPDATE feed_health SET consecutive_failures = 0 WHERE feed_id = <FEED_ID>;
```

### Feed Returns No Items

**Symptoms:**
- Fetch succeeds but 0 items found
- Feed worked before, stopped working
- `items_found = 0` in fetch_log

**Solutions:**

```bash
# 1. Check if feed still publishes
curl "https://example.com/feed/" | head -100

# 2. Verify feed format hasn't changed
# RSS/Atom structure might have been updated

# 3. Check for date filtering
# Feed might only show today's items

# 4. Manual test with feedparser
python3 << EOF
import feedparser
d = feedparser.parse("https://example.com/feed/")
print(f"Entries: {len(d.entries)}")
EOF
```

### Duplicate Items

**Symptoms:**
- Same article appearing multiple times
- Item count increasing too fast
- Duplicate detection not working

**Solutions:**

```sql
-- Find duplicates by URL
SELECT url, COUNT(*) as count
FROM items
GROUP BY url
HAVING COUNT(*) > 1;

-- Find duplicates by GUID
SELECT guid, COUNT(*) as count
FROM items
GROUP BY guid
HAVING COUNT(*) > 1;

-- Remove duplicates (keep oldest)
DELETE FROM items
WHERE id NOT IN (
    SELECT MIN(id)
    FROM items
    GROUP BY guid
);
```

---

## 🤖 Analysis Issues

### Analysis Run Stuck

**Symptoms:**
- Run shows "Running" but no progress
- Progress frozen at 0% or partial
- No items being processed

**Solutions:**

```bash
# 1. Check worker is alive
ps aux | grep analysis_worker

# 2. View worker logs for errors
tail -f logs/analysis-worker.log

# 3. Check run status in database
SELECT * FROM analysis_runs WHERE status = 'running' ORDER BY created_at DESC;

# 4. Cancel stuck run
curl -X POST http://localhost:8000/api/analysis/runs/<RUN_ID>/cancel

# 5. Emergency stop all runs
curl -X POST http://localhost:8000/api/analysis/manager/emergency-stop
```

### OpenAI API Errors

**Error:** `openai.error.RateLimitError`

**Solutions:**

```bash
# 1. Verify API key
echo $OPENAI_API_KEY

# 2. Check API key validity
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"

# 3. Reduce rate limit
# In .env:
AUTO_ANALYSIS_RATE_PER_SECOND=1.0  # Lower from 3.0

# 4. Check API usage/billing
# Visit: https://platform.openai.com/usage

# 5. Wait for rate limit reset
# OpenAI has per-minute and per-day limits
```

### Auto-Analysis Queue Growing

**Symptoms:**
- `pending_auto_analysis` table growing
- Items not being processed
- Queue depth > 200

**Solutions:**

```sql
-- Check queue size
SELECT feed_id, COUNT(*) as pending
FROM pending_auto_analysis
GROUP BY feed_id
ORDER BY pending DESC;

-- Check for blocked items
SELECT * FROM pending_auto_analysis
WHERE created_at < NOW() - INTERVAL '1 hour';
```

```bash
# 1. Manually process queue
curl -X POST http://localhost:8000/api/analysis/manager/process-queue

# 2. Increase concurrent runs
# In .env:
MAX_CONCURRENT_RUNS=10  # Increase from 5

# 3. Increase rate limit (if OpenAI allows)
AUTO_ANALYSIS_RATE_PER_SECOND=5.0

# 4. Disable auto-analysis for low-priority feeds
# Via dashboard or API

# 5. Clear old pending items
DELETE FROM pending_auto_analysis
WHERE created_at < NOW() - INTERVAL '24 hours';
```

---

## 🔌 MCP Integration Issues

### Claude Desktop Not Connecting

**Symptoms:**
- No 🔌 icon in Claude Desktop
- "MCP server not connected" error
- Tools not appearing

**Solutions:**

```bash
# 1. Check MCP server is running
curl http://localhost:8001/health

# 2. Start if not running
cd /home/cytrex/news-mcp
source venv/bin/activate
python3 http_mcp_server.py &

# 3. Verify config file location (macOS)
ls -la ~/Library/Application\ Support/Claude/claude_desktop_config.json

# 4. Validate JSON syntax
cat ~/Library/Application\ Support/Claude/claude_desktop_config.json | jq .

# 5. Check Node.js installed
node --version

# 6. Verify bridge file exists
ls -la /home/cytrex/news-mcp/mcp-http-bridge.js

# 7. Check Claude Desktop logs
# macOS: ~/Library/Logs/Claude/
# Windows: %APPDATA%\Claude\logs\
```

### MCP Tools Fail When Called

**Symptoms:**
- Tools appear in Claude Desktop
- Calling tools returns errors
- "Connection refused" or "500 Internal Server Error"

**Solutions:**

```bash
# 1. Verify core web server running
curl http://localhost:8000/api/health/status

# 2. Check MCP server logs
tail -f logs/mcp-server.log

# 3. Test tool directly
curl -X POST http://localhost:8001/tools/list_feeds \
  -H "Content-Type: application/json" \
  -d '{}'

# 4. Check database connection
python3 -c "from app.database import engine; engine.connect()"

# 5. Restart all services
./scripts/stop-all.sh
./scripts/start-all-background.sh
```

### Remote MCP Access Not Working

**Symptoms:**
- Works locally but not from remote machine
- Connection timeout
- "Connection refused"

**Solutions:**

```bash
# 1. Verify server binds to 0.0.0.0 (not 127.0.0.1)
netstat -tuln | grep 8001
# Should show: 0.0.0.0:8001

# 2. Test from remote machine
curl http://<SERVER_IP>:8001/health

# 3. Check firewall
sudo ufw status
sudo ufw allow 8001/tcp

# 4. Verify IP address in config
# In claude_desktop_config.json:
# "NEWS_MCP_SERVER_URL": "http://192.168.1.100:8001"

# 5. Ping server from remote
ping <SERVER_IP>
```

---

## 🌐 Web Dashboard Issues

### Dashboard Not Loading

**Symptoms:**
- Blank page or 404
- "Failed to load resource" errors
- CSS/JS not loading

**Solutions:**

```bash
# 1. Check web server running
curl -I http://localhost:8000

# 2. Check static files exist
ls -la static/

# 3. Verify templates exist
ls -la templates/

# 4. Check browser console for errors
# Open DevTools (F12) → Console tab

# 5. Clear browser cache
# Ctrl+Shift+Delete (Chrome/Firefox)
```

### HTMX Components Not Updating

**Symptoms:**
- Static data, no live updates
- "Loading..." never completes
- Polling not working

**Solutions:**

```bash
# 1. Check HTMX is loaded
# In browser DevTools → Network tab
# Look for: htmx.org/1.9.10/

# 2. Verify HTMX endpoints work
curl http://localhost:8000/htmx/analysis/active-runs

# 3. Check WebSocket connection (if used)
# In DevTools → Network → WS tab

# 4. Disable browser extensions
# Ad blockers can block WebSocket/polling

# 5. Check server logs for errors
tail -f logs/webserver.log
```

### WebSocket Connection Failed

**Symptoms:**
- "WebSocket connection to 'ws://localhost:8000/ws' failed"
- No real-time updates
- Progress bars frozen

**Solutions:**

```bash
# 1. Verify WebSocket endpoint exists
curl -I http://localhost:8000/ws/analysis

# 2. Check web server supports WebSocket
# FastAPI/Uvicorn should support by default

# 3. Test WebSocket manually
# Use browser extension or wscat:
npm install -g wscat
wscat -c ws://localhost:8000/ws/analysis

# 4. Check firewall/proxy settings
# Some proxies block WebSocket

# 5. Fall back to polling
# System auto-falls back to HTMX polling if WS fails
```

---

## ⚡ Performance Issues

### Slow Dashboard Load Times

**Symptoms:**
- Dashboard takes >5 seconds to load
- High CPU usage
- Browser freezes

**Solutions:**

```sql
-- Check database query performance
EXPLAIN ANALYZE SELECT * FROM items LIMIT 100;

-- Add missing indexes
CREATE INDEX IF NOT EXISTS idx_items_published ON items(published DESC);
CREATE INDEX IF NOT EXISTS idx_items_feed_id ON items(feed_id);

-- Analyze tables
ANALYZE items;
ANALYZE feeds;
```

```bash
# Check database connections
SELECT count(*) FROM pg_stat_activity;

# Tune PostgreSQL (in postgresql.conf)
shared_buffers = 256MB
effective_cache_size = 1GB
max_connections = 100
```

### High Memory Usage

**Symptoms:**
- RAM usage > 2GB
- System slowdown
- OOM killer triggering

**Solutions:**

```bash
# 1. Check process memory
ps aux --sort=-%mem | head -10

# 2. Reduce concurrent runs
# In .env:
MAX_CONCURRENT_RUNS=2  # Lower from 5

# 3. Clear old data
DELETE FROM items WHERE published < NOW() - INTERVAL '90 days';
VACUUM FULL;

# 4. Restart services periodically
# Add to cron:
0 3 * * * /path/to/scripts/stop-all.sh && /path/to/scripts/start-all-background.sh
```

### Slow API Responses

**Symptoms:**
- API calls take >2 seconds
- Timeout errors
- High P95 latency

**Solutions:**

```bash
# 1. Check database query performance
# Enable slow query logging in postgresql.conf:
log_min_duration_statement = 1000  # Log queries > 1s

# 2. Add database indexes
# See slow queries in logs, add indexes

# 3. Enable caching
# Redis optional, see config

# 4. Reduce data returned
# Use pagination, limit results

# 5. Monitor with metrics dashboard
# http://localhost:8000/admin/metrics
```

---

## 📝 Logging & Debugging

### Enable Debug Logging

```bash
# In .env:
LOG_LEVEL=DEBUG

# Restart services
./scripts/stop-all.sh
./scripts/start-all-background.sh

# View debug logs
tail -f logs/analysis-worker.log | grep DEBUG
```

### View All Logs

```bash
# Web server
tail -f logs/webserver.log

# Analysis worker
tail -f logs/analysis-worker.log

# Feed scheduler
tail -f logs/scheduler.log

# MCP server
tail -f logs/mcp-server.log

# PostgreSQL
sudo tail -f /var/log/postgresql/postgresql-15-main.log

# All logs together
tail -f logs/*.log
```

### Export Logs for Support

```bash
# Create debug bundle
tar -czf news-mcp-debug-$(date +%Y%m%d-%H%M%S).tar.gz \
  logs/ \
  .env.example \
  $(./scripts/status.sh) \
  $(curl -s http://localhost:8000/api/health/status)

# Send to support
# Attach to GitHub issue
```

---

## 🆘 Emergency Procedures

### Complete System Reset

**WARNING:** This deletes all data!

```bash
# 1. Stop all services
./scripts/stop-all.sh

# 2. Backup database
pg_dump -h localhost -U news_user news_db > backup-$(date +%Y%m%d).sql

# 3. Drop and recreate database
psql -h localhost -U postgres -c "DROP DATABASE news_db;"
psql -h localhost -U postgres -c "CREATE DATABASE news_db OWNER news_user;"

# 4. Recreate tables
alembic upgrade head

# 5. Restart services
./scripts/start-all-background.sh
```

### Emergency Stop All Analysis

```bash
# Stop all running analysis
curl -X POST http://localhost:8000/api/analysis/manager/emergency-stop

# Cancel all queued runs
curl -X DELETE http://localhost:8000/api/analysis/runs/pending

# Clear auto-analysis queue
PGPASSWORD=news_password psql -h localhost -U news_user -d news_db -c "DELETE FROM pending_auto_analysis;"
```

### Restore from Backup

```bash
# 1. Stop services
./scripts/stop-all.sh

# 2. Drop existing database
psql -h localhost -U postgres -c "DROP DATABASE news_db;"
psql -h localhost -U postgres -c "CREATE DATABASE news_db OWNER news_user;"

# 3. Restore from backup
psql -h localhost -U news_user -d news_db < backup-20251001.sql

# 4. Restart services
./scripts/start-all-background.sh
```

---

## 📞 Getting Help

### Before Asking for Help

1. ✅ Check this troubleshooting guide
2. ✅ Review logs for error messages
3. ✅ Try basic diagnostics (status, health check)
4. ✅ Search existing GitHub issues
5. ✅ Prepare debug information (logs, config, versions)

### Report an Issue

**GitHub Issues:** https://github.com/CytrexSGR/news-mcp/issues

**Include:**
- News MCP version (`cat README.md | grep "Current Version"`)
- Python version (`python3 --version`)
- PostgreSQL version (`psql --version`)
- Error messages (full stack trace)
- Steps to reproduce
- Logs (`tar -czf logs.tar.gz logs/`)

### Community Support

- **Discussions:** https://github.com/CytrexSGR/news-mcp/discussions
- **Wiki:** https://github.com/CytrexSGR/news-mcp/wiki

---

## 🔗 Related Pages

- **[Quick Start](Quick-Start)** - Installation guide
- **[Dashboard Overview](Dashboard-Overview)** - Web interface
- **[MCP Integration](MCP-Integration)** - MCP-specific issues
- **[Architecture](Architecture)** - System design
- **[API Reference](API-Overview)** - API documentation

---

**Last Updated:** 2025-10-01
**Covers:** Common issues, service problems, database issues, feed errors, analysis issues, MCP problems
