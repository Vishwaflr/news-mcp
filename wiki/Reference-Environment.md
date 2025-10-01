# Environment Variables Reference - Complete Configuration

Complete reference for all News MCP environment variables.

---

## 📋 Core Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | *(required)* | PostgreSQL connection string |
| `ENVIRONMENT` | `development` | Environment: development\|production\|staging |
| `LOG_LEVEL` | `INFO` | Logging level: DEBUG\|INFO\|WARNING\|ERROR |
| `HOST` | `0.0.0.0` | Server bind address |
| `PORT` | `8000` | Web server port |

---

## 🤖 AI Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_API_KEY` | *(required)* | OpenAI API key |
| `OPENAI_MODEL` | `gpt-3.5-turbo` | Default OpenAI model |
| `OPENAI_TEMPERATURE` | `0.3` | Response temperature (0.0-1.0) |

---

## 🔄 Auto-Analysis

| Variable | Default | Description |
|----------|---------|-------------|
| `MAX_CONCURRENT_RUNS` | `5` | Max concurrent analysis runs |
| `MAX_DAILY_RUNS` | `100` | Max manual runs per day |
| `MAX_DAILY_AUTO_RUNS` | `500` | Max auto-analysis runs per day |
| `AUTO_ANALYSIS_RATE_PER_SECOND` | `3.0` | OpenAI API rate limit |
| `AUTO_ANALYSIS_BATCH_SIZE` | `10` | Items per processing batch |

---

## 📡 Feed Scheduler

| Variable | Default | Description |
|----------|---------|-------------|
| `DEFAULT_FETCH_INTERVAL` | `60` | Default fetch interval (minutes) |
| `MIN_FETCH_INTERVAL` | `15` | Minimum fetch interval (minutes) |
| `MAX_FETCH_INTERVAL` | `240` | Maximum fetch interval (minutes) |
| `SCHEDULER_CHECK_INTERVAL` | `300` | Scheduler loop interval (seconds) |

---

## 🗄️ Database

| Variable | Default | Description |
|----------|---------|-------------|
| `DB_POOL_SIZE` | `20` | Base connection pool size |
| `DB_MAX_OVERFLOW` | `30` | Additional overflow connections |
| `DB_POOL_RECYCLE` | `3600` | Connection recycle time (seconds) |
| `DB_ECHO` | `False` | Log all SQL queries (debug) |

---

## 🔌 MCP Server

| Variable | Default | Description |
|----------|---------|-------------|
| `MCP_SERVER_PORT` | `8001` | MCP server port |
| `NEWS_MCP_SERVER_URL` | `http://localhost:8001` | MCP server URL |

---

## 🔐 Security (Production)

| Variable | Default | Description |
|----------|---------|-------------|
| `SECRET_KEY` | *(generate)* | Application secret key (32+ chars) |
| `CORS_ORIGINS` | `*` | Allowed CORS origins (comma-separated) |
| `API_KEY_HEADER` | `X-API-Key` | API key header name |

---

## 📊 Monitoring

| Variable | Default | Description |
|----------|---------|-------------|
| `HEALTH_CHECK_INTERVAL` | `60` | Health check frequency (seconds) |
| `LOG_FORMAT` | `text` | Log format: text\|json |
| `LOG_FILE` | *(optional)* | Log file path |

---

## 🔗 Related Documentation

- **[Configuration](Configuration)** - Configuration guide
- **[Installation](Installation)** - Setup guide
- **[Deployment](Deployment-Production)** - Production setup

---

**Last Updated:** 2025-10-01
