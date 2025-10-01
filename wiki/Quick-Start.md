# Quick Start Guide - Get News MCP Running in 5 Minutes

Get News MCP up and running quickly with this streamlined installation guide.

---

## ⚡ Prerequisites

Before starting, ensure you have:

- ✅ **Python 3.9+** - Check with `python3 --version`
- ✅ **PostgreSQL 15+** - Database server
- ✅ **Git** - Version control
- ✅ **OpenAI API Key** (optional, for AI analysis)

---

## 🚀 Installation (5 Steps)

### Step 1: Clone Repository

```bash
git clone https://github.com/CytrexSGR/news-mcp.git
cd news-mcp
```

### Step 2: Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate  # Linux/macOS
# or: venv\Scripts\activate  # Windows
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Setup Database

```bash
# Create PostgreSQL user and database
sudo -u postgres psql

# In PostgreSQL shell:
CREATE USER news_user WITH PASSWORD 'news_password';
CREATE DATABASE news_db OWNER news_user;
GRANT ALL PRIVILEGES ON DATABASE news_db TO news_user;
\q
```

### Step 5: Configure Environment

```bash
# Copy example config
cp .env.example .env

# Edit .env with your settings
nano .env
```

**Minimal `.env` configuration:**
```bash
DATABASE_URL=postgresql://news_user:news_password@localhost/news_db
OPENAI_API_KEY=sk-your_api_key_here  # Optional, for AI analysis
ENVIRONMENT=development
```

---

## 🎯 Initialize Database

```bash
# Run migrations
alembic upgrade head

# Or direct table creation
python -c "from app.database import create_tables; create_tables()"
```

---

## ▶️ Start Services

### Option 1: All Services (Recommended)

```bash
./scripts/start-all-background.sh
```

This starts:
- Web Server (port 8000)
- Analysis Worker
- Feed Scheduler

### Option 2: Individual Services

```bash
# Web server only
./scripts/start-web-server.sh

# Add worker (in new terminal)
./scripts/start-worker.sh

# Add scheduler (in new terminal)
./scripts/start-scheduler.sh
```

---

## ✅ Verify Installation

### Check Services Status

```bash
./scripts/status.sh
```

**Expected Output:**
```
✅ Web Server: Running (PID 12345)
✅ Analysis Worker: Running (PID 12346)
✅ Feed Scheduler: Running (PID 12347)
```

### Test Web Interface

Open browser: **http://localhost:8000**

You should see the main dashboard.

### Test API

```bash
curl http://localhost:8000/api/health/status
```

**Expected Response:**
```json
{
  "status": "healthy",
  "services": {
    "web": "up",
    "database": "up",
    "worker": "up"
  }
}
```

---

## 📝 First Steps

### 1. Add Your First Feed

**Via Web UI:**
1. Navigate to http://localhost:8000/admin/feeds
2. Click **"Add Feed"**
3. Enter URL: `https://techcrunch.com/feed/`
4. Click **"Save"**

**Via API:**
```bash
curl -X POST http://localhost:8000/api/feeds/ \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://techcrunch.com/feed/",
    "title": "TechCrunch",
    "status": "active"
  }'
```

### 2. Fetch Feed Items

**Manual Fetch:**
```bash
curl -X POST http://localhost:8000/api/feeds/1/fetch
```

**Wait 30 seconds**, then check items:
```bash
curl http://localhost:8000/api/items/ | head -20
```

### 3. Run Your First Analysis

**Via Analysis Cockpit:**
1. Navigate to http://localhost:8000/admin/analysis
2. Select your feed
3. Set scope limit: 10
4. Click **"Preview Selection"**
5. Click **"Start Analysis"**
6. Watch progress in real-time!

---

## 🔌 Optional: MCP Server Setup

Enable Claude Desktop integration:

### Start MCP Server

```bash
# In news-mcp directory
source venv/bin/activate
python3 http_mcp_server.py &
```

Server runs on **port 8001**.

### Configure Claude Desktop

Edit config file:
- **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

Add:
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

Restart Claude Desktop.

**[Full MCP Setup Guide →](MCP-Integration)**

---

## 🎉 You're Ready!

### Quick Access Links

| Dashboard | URL | Description |
|-----------|-----|-------------|
| Main Dashboard | http://localhost:8000 | System overview |
| Analysis Cockpit | http://localhost:8000/admin/analysis | Manual analysis |
| Auto-Analysis | http://localhost:8000/admin/auto-analysis | Automatic analysis |
| Feeds | http://localhost:8000/admin/feeds | Feed management |
| Health Monitor | http://localhost:8000/admin/health | System health |
| API Docs | http://localhost:8000/docs | Swagger UI |

---

## 🔧 Common Issues

### Issue: Database connection failed

**Error:** `psycopg2.OperationalError: could not connect to server`

**Solution:**
```bash
# Check PostgreSQL is running
sudo systemctl status postgresql

# Start if not running
sudo systemctl start postgresql

# Verify connection
psql -h localhost -U news_user -d news_db
```

### Issue: Port 8000 already in use

**Error:** `Address already in use`

**Solution:**
```bash
# Find process using port 8000
lsof -i :8000

# Kill process
kill -9 <PID>

# Or use different port
uvicorn app.main:app --host 0.0.0.0 --port 8001
```

### Issue: Module not found errors

**Error:** `ModuleNotFoundError: No module named 'fastapi'`

**Solution:**
```bash
# Ensure virtual environment is activated
source venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt
```

### Issue: Alembic migrations fail

**Error:** `alembic.util.exc.CommandError`

**Solution:**
```bash
# Reset alembic
rm -rf alembic/versions/*

# Regenerate migration
alembic revision --autogenerate -m "initial"
alembic upgrade head

# Or use direct table creation instead
python -c "from app.database import create_tables; create_tables()"
```

---

## 📚 Next Steps

### Learn the System

- **[Dashboard Overview](Dashboard-Overview)** - Explore all 11 dashboards
- **[Analysis Cockpit](Analysis-Cockpit)** - Master manual analysis
- **[Auto-Analysis](Auto-Analysis-Dashboard)** - Setup automatic analysis
- **[MCP Integration](MCP-Integration)** - Connect Claude Desktop

### Configure Features

- **[Feed Management](Feature-Feed-Health)** - Advanced feed configuration
- **[Dynamic Templates](Feature-Templates)** - Feed template system
- **[Feature Flags](Feature-Flags)** - Gradual rollout controls

### Development

- **[Architecture](Architecture)** - System design
- **[API Reference](API-Overview)** - Complete API docs
- **[Contributing](https://github.com/CytrexSGR/news-mcp/blob/main/CONTRIBUTING.md)** - Contribution guide

---

## 🆘 Need Help?

- **Issues:** [GitHub Issues](https://github.com/CytrexSGR/news-mcp/issues)
- **Discussions:** [GitHub Discussions](https://github.com/CytrexSGR/news-mcp/discussions)
- **Wiki:** [Full Documentation](Home)
- **Troubleshooting:** [Common Issues](Troubleshooting-Common)

---

**Installation Time:** ~5 minutes
**Difficulty:** Beginner-friendly
**Last Updated:** 2025-10-01
