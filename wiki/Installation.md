# Installation Guide - News MCP Setup

Complete installation guide for News MCP on Linux, macOS, and Docker environments.

---

## 📋 Prerequisites

Before installing News MCP, ensure you have:

### Required Software

| Software | Minimum Version | Purpose |
|----------|----------------|---------|
| **Python** | 3.9+ | Application runtime |
| **PostgreSQL** | 15+ | Database server |
| **Git** | 2.x+ | Version control |

### Optional Software

| Software | Purpose |
|----------|---------|
| **Redis** | Extended caching (future use) |
| **Docker** | Containerized deployment |
| **Nginx** | Reverse proxy (production) |

---

## 🐧 Installation on Linux (Ubuntu/Debian)

### Step 1: System Dependencies

```bash
# Update package lists
sudo apt update

# Install required packages
sudo apt install -y \
    python3 \
    python3-pip \
    python3-venv \
    postgresql \
    postgresql-contrib \
    git

# Verify installations
python3 --version    # Should be 3.9+
psql --version       # Should be 15+
git --version
```

### Step 2: Clone Repository

```bash
# Clone from GitHub
git clone https://github.com/CytrexSGR/news-mcp.git
cd news-mcp

# Verify repository
ls -la
# Should see: app/, docs/, scripts/, requirements.txt, etc.
```

### Step 3: Create Virtual Environment

```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip
```

### Step 4: Install Python Dependencies

```bash
# Install all dependencies
pip install -r requirements.txt

# Verify installation
pip list | grep fastapi
pip list | grep sqlmodel
pip list | grep openai
```

### Step 5: Database Setup

```bash
# Switch to postgres user
sudo -u postgres psql

# In PostgreSQL shell, run:
CREATE USER news_user WITH PASSWORD 'news_password';
CREATE DATABASE news_db OWNER news_user;
GRANT ALL PRIVILEGES ON DATABASE news_db TO news_user;
\q

# Verify database connection
psql -h localhost -U news_user -d news_db -c "SELECT version();"
```

### Step 6: Configure Environment

```bash
# Create .env file from template
cp .env.example .env

# Edit .env file
nano .env
```

**Minimum .env configuration:**
```bash
DATABASE_URL=postgresql://news_user:news_password@localhost/news_db
OPENAI_API_KEY=your_openai_api_key_here
ENVIRONMENT=development
LOG_LEVEL=INFO
```

### Step 7: Initialize Database

```bash
# Export database password
export PGPASSWORD=news_password

# Run Alembic migrations
alembic upgrade head

# Verify tables created
psql -h localhost -U news_user -d news_db -c "\dt"
# Should show 30 tables
```

### Step 8: Start Services

```bash
# Start web server (foreground)
./scripts/start-web-server.sh

# Or start in background
./scripts/start-all-background.sh

# Verify server is running
curl http://localhost:8000/api/health/
```

**Expected output:**
```json
{
  "status": "healthy",
  "database": "connected",
  "timestamp": "2025-10-01T12:00:00Z"
}
```

### Step 9: Access Web Interface

Open your browser to:
- **Main Dashboard:** http://localhost:8000/
- **API Docs:** http://localhost:8000/docs
- **Feed Management:** http://localhost:8000/admin/feeds

---

## 🍎 Installation on macOS

### Step 1: Install Homebrew (if not installed)

```bash
# Install Homebrew
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

### Step 2: System Dependencies

```bash
# Install required packages
brew install python@3.9 postgresql git

# Start PostgreSQL service
brew services start postgresql

# Verify installations
python3 --version
psql --version
git --version
```

### Step 3: Follow Linux Steps

Continue with **Steps 2-9** from the Linux installation guide above.

**macOS-specific notes:**
- PostgreSQL user: Use your macOS username instead of `postgres`
- Database creation: No `sudo -u postgres` needed, just run `psql`

---

## 🐳 Docker Installation

### Prerequisites

```bash
# Install Docker and Docker Compose
# Visit: https://docs.docker.com/get-docker/

# Verify installation
docker --version
docker-compose --version
```

### Step 1: Clone Repository

```bash
git clone https://github.com/CytrexSGR/news-mcp.git
cd news-mcp
```

### Step 2: Configure Environment

```bash
# Create .env file
cp .env.example .env

# Edit database URL for Docker
nano .env
```

**Docker .env configuration:**
```bash
DATABASE_URL=postgresql://news_user:news_password@db:5432/news_db
OPENAI_API_KEY=your_openai_api_key_here
ENVIRONMENT=production
```

### Step 3: Build and Run

```bash
# Build Docker images
docker-compose build

# Start all services
docker-compose up -d

# View logs
docker-compose logs -f web

# Check service status
docker-compose ps
```

### Step 4: Initialize Database

```bash
# Run migrations
docker-compose exec web alembic upgrade head

# Verify tables
docker-compose exec db psql -U news_user -d news_db -c "\dt"
```

### Step 5: Access Services

- **Web Interface:** http://localhost:8000/
- **MCP Server:** http://localhost:8001/
- **Database:** localhost:5432

---

## 🚀 Post-Installation Setup

### 1. Add Your First Feed

**Via Web Interface:**
1. Navigate to http://localhost:8000/admin/feeds
2. Click "Add Feed"
3. Enter feed details:
   - **Title:** BBC News
   - **URL:** http://feeds.bbci.co.uk/news/rss.xml
   - **Interval:** 60 minutes
4. Click "Create"

**Via API:**
```bash
curl -X POST http://localhost:8000/api/feeds/ \
  -H "Content-Type: application/json" \
  -d '{
    "title": "BBC News",
    "url": "http://feeds.bbci.co.uk/news/rss.xml",
    "fetch_interval_minutes": 60
  }'
```

### 2. Fetch Feed Content

```bash
# Trigger manual fetch
curl -X POST http://localhost:8000/api/feeds/1/fetch

# View fetched items
curl http://localhost:8000/api/items/?feed_id=1
```

### 3. Start Background Workers

```bash
# Analysis worker (for AI analysis)
./scripts/start-worker.sh

# Feed scheduler (automatic feed fetching)
./scripts/start-scheduler.sh

# Verify workers are running
./scripts/status.sh
```

### 4. Configure MCP Server (Optional)

```bash
# Start MCP server
./scripts/start_mcp_server.sh

# Verify MCP server
curl http://localhost:8001/health
```

**[Complete MCP Setup Guide →](MCP-Integration)**

---

## 🔍 Verification Checklist

After installation, verify everything works:

### ✅ Web Server
```bash
curl http://localhost:8000/api/health/
# Expected: {"status": "healthy"}
```

### ✅ Database Connection
```bash
psql -h localhost -U news_user -d news_db -c "SELECT COUNT(*) FROM feeds;"
# Expected: Row count (initially 0)
```

### ✅ API Endpoints
```bash
curl http://localhost:8000/api/feeds/
# Expected: {"feeds": [], "total": 0}
```

### ✅ Web Dashboard
- Visit: http://localhost:8000/
- Should see dashboard with statistics

### ✅ API Documentation
- Visit: http://localhost:8000/docs
- Should see interactive Swagger UI

---

## 🛠️ Troubleshooting

### Database Connection Failed

**Error:** `psql: connection refused`

**Solution:**
```bash
# Check PostgreSQL is running
sudo systemctl status postgresql

# Start PostgreSQL
sudo systemctl start postgresql

# Enable auto-start
sudo systemctl enable postgresql
```

---

### Module Import Errors

**Error:** `ModuleNotFoundError: No module named 'fastapi'`

**Solution:**
```bash
# Ensure virtual environment is activated
source venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt
```

---

### Port Already in Use

**Error:** `Address already in use: 0.0.0.0:8000`

**Solution:**
```bash
# Find process using port 8000
lsof -i :8000

# Kill process
kill -9 <PID>

# Or use different port
uvicorn app.main:app --port 8001
```

---

### Alembic Migration Errors

**Error:** `Target database is not up to date`

**Solution:**
```bash
# Check current migration version
alembic current

# View migration history
alembic history

# Upgrade to latest
alembic upgrade head

# If stuck, stamp current version
alembic stamp head
```

---

### OpenAI API Key Invalid

**Error:** `AuthenticationError: Invalid API key`

**Solution:**
1. Verify your API key at https://platform.openai.com/api-keys
2. Update `.env` file with correct key
3. Restart web server
4. Test with a simple analysis run

---

## 📚 Next Steps

After successful installation:

1. **[Configuration Guide](Configuration)** - Fine-tune your setup
2. **[Quick Start](Quick-Start)** - Get running in 5 minutes
3. **[MCP Integration](MCP-Integration)** - Connect to Claude Desktop
4. **[Dashboard Overview](Dashboard-Overview)** - Explore web interfaces
5. **[API Reference](API-Overview)** - Learn the REST API

---

## 🔗 Related Documentation

- **[Quick Start Guide](Quick-Start)** - Fast setup
- **[Configuration](Configuration)** - Environment variables
- **[Deployment](Deployment-Production)** - Production setup
- **[Troubleshooting](Troubleshooting-Common)** - Common issues

---

## 📞 Support

**Installation Issues:**
- [GitHub Issues](https://github.com/CytrexSGR/news-mcp/issues)
- [Troubleshooting Guide](Troubleshooting-Common)
- [GitHub Discussions](https://github.com/CytrexSGR/news-mcp/discussions)

---

**Last Updated:** 2025-10-01
**Tested Versions:**
- Ubuntu 22.04 LTS ✅
- Debian 12 ✅
- macOS 14 (Sonoma) ✅
- Docker 24+ ✅
