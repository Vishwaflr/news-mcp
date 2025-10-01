# Configuration Guide - News MCP Settings

Complete configuration reference for News MCP environment variables and settings.

---

## 📋 Environment Variables

### Core Configuration

```bash
# .env file location: /path/to/news-mcp/.env

# Database
DATABASE_URL=postgresql://news_user:news_password@localhost/news_db

# Application
ENVIRONMENT=development          # development | production | staging
LOG_LEVEL=INFO                   # DEBUG | INFO | WARNING | ERROR
HOST=0.0.0.0                     # Server bind address
PORT=8000                        # Server port

# AI Integration
OPENAI_API_KEY=sk-...           # OpenAI API key (required for analysis)
OPENAI_MODEL=gpt-3.5-turbo      # Default: gpt-3.5-turbo | gpt-4

# MCP Server
MCP_SERVER_PORT=8001            # MCP server port
NEWS_MCP_SERVER_URL=http://localhost:8001  # MCP server URL
```

---

## 🤖 Auto-Analysis Configuration

```bash
# Auto-Analysis Limits
MAX_CONCURRENT_RUNS=5           # Max concurrent analysis runs
MAX_DAILY_RUNS=100              # Max manual runs per day
MAX_DAILY_AUTO_RUNS=500         # Max auto-analysis runs per day
AUTO_ANALYSIS_RATE_PER_SECOND=3.0  # OpenAI API rate limit

# Queue Settings
AUTO_ANALYSIS_BATCH_SIZE=10     # Items per batch
AUTO_ANALYSIS_RETRY_ATTEMPTS=3  # Max retries on failure
```

---

## 📡 Feed Scheduler Configuration

```bash
# Default Settings
DEFAULT_FETCH_INTERVAL=60       # Minutes between fetches
SCHEDULER_CHECK_INTERVAL=300    # Scheduler loop interval (seconds)

# Rate Limiting
MIN_FETCH_INTERVAL=15           # Minimum interval (minutes)
MAX_FETCH_INTERVAL=240          # Maximum interval (minutes)
```

---

## 🗄️ Database Configuration

```bash
# Connection Pool
DB_POOL_SIZE=20                 # Base connections
DB_MAX_OVERFLOW=30              # Additional connections
DB_POOL_RECYCLE=3600            # Connection recycle time (seconds)

# Performance
DB_ECHO=False                   # Log all SQL queries (debug only)
```

---

## 🔐 Security Configuration (Production)

```bash
# Secret Keys
SECRET_KEY=<generate_random_32_chars>  # Application secret

# CORS
CORS_ORIGINS=http://localhost:3000,https://yourdomain.com  # Allowed origins

# API Keys (future)
API_KEY_HEADER=X-API-Key        # API key header name
```

---

## 📊 Monitoring Configuration

```bash
# Health Checks
HEALTH_CHECK_INTERVAL=60        # Health check frequency (seconds)

# Logging
LOG_FORMAT=json                 # json | text
LOG_FILE=/var/log/news-mcp/app.log  # Log file path (optional)
```

---

## 🔗 Related Documentation

- **[Installation](Installation)** - Setup guide
- **[Deployment](Deployment-Production)** - Production setup
- **[Reference](Reference-Environment)** - Complete variable reference

---

**Last Updated:** 2025-10-01
