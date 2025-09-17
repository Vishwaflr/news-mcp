# 🚀 News MCP Deployment Guide

Komplettes Deployment-Guide für das News MCP Dynamic Template System in verschiedenen Umgebungen.

## 📋 Inhaltsverzeichnis

- [🔧 Systemanforderungen](#-systemanforderungen)
- [⚡ Schnellstart (Development)](#-schnellstart-development)
- [🏢 Production Deployment](#-production-deployment)
- [🐳 Docker Deployment](#-docker-deployment)
- [☁️ Cloud Deployment](#️-cloud-deployment)
- [📊 Monitoring & Logging](#-monitoring--logging)
- [🔄 Updates & Wartung](#-updates--wartung)
- [🛠️ Troubleshooting](#️-troubleshooting)

## 🔧 Systemanforderungen

### Minimum Requirements
- **OS**: Linux, macOS, oder Windows
- **Python**: 3.11+ (empfohlen: 3.12)
- **RAM**: 2 GB (4 GB empfohlen)
- **Storage**: 5 GB (10 GB empfohlen)
- **CPU**: 2 Cores (4 Cores empfohlen)

### Production Requirements
- **OS**: Linux (Ubuntu 22.04+ oder RHEL 8+)
- **Python**: 3.12
- **RAM**: 8 GB (16 GB für >500 Feeds)
- **Storage**: 50 GB SSD
- **CPU**: 4 Cores (8 Cores für >500 Feeds)
- **Database**: PostgreSQL 15+

## ⚡ Schnellstart (Development)

### 1. Repository Setup

```bash
# Repository klonen
git clone https://github.com/your-org/news-mcp.git
cd news-mcp

# Virtual Environment erstellen
python3.12 -m venv venv
source venv/bin/activate  # Linux/macOS
# venv\\Scripts\\activate  # Windows

# Dependencies installieren
pip install --upgrade pip
pip install -r requirements.txt
```

### 2. Database Setup

```bash
# PostgreSQL mit Docker Compose starten
docker compose up -d

# Warten bis PostgreSQL bereit ist
sleep 5
```

### 3. Konfiguration

```bash
# Konfigurationsdatei erstellen
cp .env.example .env

# .env anpassen (optional für Development)
nano .env
```

### 4. Services starten

```bash
# Terminal 1: Web-API Server
export PYTHONPATH=$(pwd)
python app/main.py

# Terminal 2: Dynamic Scheduler
python jobs/scheduler_manager.py start --debug

# Terminal 3: MCP Server (optional)
python mcp_server/server.py
```

### 5. Zugriff testen

```bash
# Web Interface
open http://localhost:8000/admin/templates

# API Health Check
curl http://localhost:8000/api/health

# Template Management
curl http://localhost:8000/htmx/templates-list
```

## 🏢 Production Deployment

### 1. Server Setup

```bash
# Ubuntu 22.04 Setup
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3.12 python3.12-venv python3-pip nginx postgresql-15 systemd supervisor

# User erstellen
sudo useradd -m -s /bin/bash newsmcp
sudo usermod -aG sudo newsmcp
```

### 2. Database Setup

#### Option A: Local PostgreSQL (Projekt-Datenbank)
```bash
# Docker Compose für lokale Entwicklung nutzen
cd /opt/news-mcp
docker compose up -d

# Daten werden automatisch in ./data/postgres/ gespeichert
```

#### Option B: System PostgreSQL (Production)
```bash
# PostgreSQL konfigurieren
sudo -u postgres createuser newsmcp
sudo -u postgres createdb newsdb -O newsmcp
sudo -u postgres psql -c "ALTER USER newsmcp PASSWORD 'secure_password_here';"

# PostgreSQL Tuning
sudo nano /etc/postgresql/15/main/postgresql.conf
```

PostgreSQL Tuning Einstellungen:
```conf
# /etc/postgresql/15/main/postgresql.conf
shared_buffers = 256MB
effective_cache_size = 1GB
maintenance_work_mem = 64MB
checkpoint_completion_target = 0.9
wal_buffers = 16MB
default_statistics_target = 100
random_page_cost = 1.1
effective_io_concurrency = 200
work_mem = 4MB
min_wal_size = 1GB
max_wal_size = 4GB
max_connections = 100
```

### 3. Application Setup

```bash
# Application deployen
sudo mkdir -p /opt/news-mcp
sudo chown newsmcp:newsmcp /opt/news-mcp
sudo -u newsmcp git clone https://github.com/your-org/news-mcp.git /opt/news-mcp

# Dependencies installieren
cd /opt/news-mcp
sudo -u newsmcp python3.12 -m venv venv
sudo -u newsmcp venv/bin/pip install --upgrade pip
sudo -u newsmcp venv/bin/pip install -r requirements.txt
```

### 4. Konfiguration

```bash
# Production Konfiguration
sudo -u newsmcp cp .env.example .env
sudo -u newsmcp nano .env
```

Production `.env`:
```bash
# Database (Option A: Projekt-lokale Datenbank)
DATABASE_URL=postgresql://news_user:news_password@localhost:5432/news_db

# Database (Option B: System PostgreSQL)
# DATABASE_URL=postgresql://newsmcp:secure_password_here@localhost/newsdb

# Security
API_HOST=127.0.0.1
CORS_ORIGINS=["https://yourdomain.com"]
CORS_ALLOW_CREDENTIALS=false
DEBUG=false

# Performance
MAX_CONCURRENT_FETCHES=10
CONFIG_CHECK_INTERVAL_SECONDS=60
SQLALCHEMY_POOL_SIZE=20
SQLALCHEMY_MAX_OVERFLOW=30

# Logging
LOG_LEVEL=WARNING
LOG_FILE_PATH=/var/log/news-mcp/app.log
```

### 5. Systemd Services

```bash
# Service-Dateien kopieren
sudo cp systemd/*.service /etc/systemd/system/

# Services konfigurieren
sudo systemctl daemon-reload
sudo systemctl enable news-api news-scheduler
sudo systemctl start news-api news-scheduler

# Status prüfen
sudo systemctl status news-api news-scheduler
```

### 6. Nginx Reverse Proxy

```bash
# Nginx konfigurieren
sudo nano /etc/nginx/sites-available/news-mcp
```

Nginx Konfiguration:
```nginx
server {
    listen 80;
    server_name yourdomain.com;

    # SSL Redirect
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;

    # Security Headers
    add_header X-Content-Type-Options nosniff;
    add_header X-Frame-Options DENY;
    add_header X-XSS-Protection "1; mode=block";
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # WebSocket Support
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    # Static Files
    location /static {
        alias /opt/news-mcp/static;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # Rate Limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    location /api {
        limit_req zone=api burst=20 nodelay;
        proxy_pass http://127.0.0.1:8000;
    }
}
```

```bash
# Nginx aktivieren
sudo ln -s /etc/nginx/sites-available/news-mcp /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 7. SSL Certificate (Let's Encrypt)

```bash
# Certbot installieren
sudo apt install -y certbot python3-certbot-nginx

# SSL Certificate generieren
sudo certbot --nginx -d yourdomain.com

# Auto-Renewal testen
sudo certbot renew --dry-run
```

## 🐳 Docker Deployment

### 1. Dockerfile

```dockerfile
# Dockerfile
FROM python:3.12-slim

# System Dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Working Directory
WORKDIR /app

# Python Dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Application Code
COPY . .

# Non-root User
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Health Check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

# Default Command
CMD ["python", "app/main.py"]
```

### 2. Docker Compose

```yaml
# docker-compose.yml
version: '3.8'

services:
  # Database (local project storage)
  db:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: news_db
      POSTGRES_USER: news_user
      POSTGRES_PASSWORD: news_password
    ports:
      - "5432:5432"
    volumes:
      - ./data/postgres:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U news_user -d news_db"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped

  # Redis (optional für Caching)
  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 3
    restart: unless-stopped

  # Web API
  web:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://news_user:news_password@db/news_db
      - REDIS_URL=redis://redis:6379
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
    volumes:
      - ./logs:/app/logs
    restart: unless-stopped

  # Dynamic Scheduler
  scheduler:
    build: .
    command: python jobs/scheduler_manager.py start
    environment:
      - DATABASE_URL=postgresql://news_user:news_password@db/news_db
      - SCHEDULER_INSTANCE_ID=docker_scheduler
    depends_on:
      db:
        condition: service_healthy
    volumes:
      - ./logs:/app/logs
    restart: unless-stopped

  # Nginx Reverse Proxy
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./certs:/etc/nginx/certs:ro
    depends_on:
      - web
    restart: unless-stopped

volumes:
  redis_data:
```

### 3. Docker Deployment

```bash
# Production Build
docker-compose -f docker-compose.yml build --no-cache

# Services starten
docker-compose up -d

# Logs überwachen
docker-compose logs -f

# Services skalieren
docker-compose up -d --scale scheduler=2
```

## ☁️ Cloud Deployment

### AWS Deployment

```bash
# ECS Task Definition
{
  "family": "news-mcp",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "1024",
  "memory": "2048",
  "executionRoleArn": "arn:aws:iam::account:role/ecsTaskExecutionRole",
  "taskRoleArn": "arn:aws:iam::account:role/ecsTaskRole",
  "containerDefinitions": [
    {
      "name": "web",
      "image": "your-account.dkr.ecr.region.amazonaws.com/news-mcp:latest",
      "portMappings": [{"containerPort": 8000}],
      "environment": [
        {"name": "DATABASE_URL", "value": "postgresql://..."}
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/news-mcp",
          "awslogs-region": "us-east-1"
        }
      }
    }
  ]
}
```

### Google Cloud Run

```bash
# Cloud Run Deployment
gcloud run deploy news-mcp \
  --image gcr.io/your-project/news-mcp:latest \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars DATABASE_URL=postgresql://... \
  --memory 2Gi \
  --cpu 2 \
  --concurrency 80 \
  --max-instances 10
```

### DigitalOcean App Platform

```yaml
# .do/app.yaml
name: news-mcp
services:
- name: web
  source_dir: /
  github:
    repo: your-org/news-mcp
    branch: main
  run_command: python app/main.py
  environment_slug: python
  instance_count: 1
  instance_size_slug: basic-xxs
  envs:
  - key: DATABASE_URL
    value: ${db.DATABASE_URL}
  http_port: 8000

- name: scheduler
  source_dir: /
  github:
    repo: your-org/news-mcp
    branch: main
  run_command: python jobs/scheduler_manager.py start
  environment_slug: python
  instance_count: 1
  instance_size_slug: basic-xxs
  envs:
  - key: DATABASE_URL
    value: ${db.DATABASE_URL}

databases:
- name: db
  engine: PG
  version: "15"
  size: basic-xs
```

## 📊 Monitoring & Logging

### 1. Application Monitoring

```python
# app/monitoring.py
import logging
import time
from functools import wraps
from prometheus_client import Counter, Histogram, start_http_server

# Metrics
REQUEST_COUNT = Counter('http_requests_total', 'Total HTTP requests', ['method', 'endpoint'])
REQUEST_LATENCY = Histogram('http_request_duration_seconds', 'HTTP request latency')

def monitor_endpoint(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = await func(*args, **kwargs)
            REQUEST_COUNT.labels(method='GET', endpoint=func.__name__).inc()
            return result
        finally:
            REQUEST_LATENCY.observe(time.time() - start_time)
    return wrapper

# Start Prometheus metrics server
start_http_server(8090)
```

### 2. Log Configuration

```python
# app/logging_config.py
import logging.config

LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'detailed': {
            'format': '%(asctime)s - %(name)s - %(levelname)s - %(module)s:%(lineno)d - %(message)s'
        },
        'json': {
            'format': '{"timestamp": "%(asctime)s", "level": "%(levelname)s", "module": "%(module)s", "message": "%(message)s"}'
        }
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'level': 'INFO',
            'formatter': 'detailed'
        },
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': '/var/log/news-mcp/app.log',
            'maxBytes': 10485760,  # 10MB
            'backupCount': 5,
            'formatter': 'json'
        }
    },
    'loggers': {
        'news_mcp': {
            'level': 'INFO',
            'handlers': ['console', 'file']
        }
    }
}

logging.config.dictConfig(LOGGING_CONFIG)
```

### 3. Health Checks

```bash
# Health Check Script
#!/bin/bash
# healthcheck.sh

# API Health
curl -f http://localhost:8000/api/health || exit 1

# Database Connection
python -c "
from app.database import engine
from sqlmodel import text
with engine.connect() as conn:
    conn.execute(text('SELECT 1'))
" || exit 2

# Scheduler Health
python jobs/scheduler_manager.py status | grep -q "Active: True" || exit 3

echo "All services healthy"
```

## 🔄 Updates & Wartung

### 1. Zero-Downtime Updates

```bash
# Blue-Green Deployment Script
#!/bin/bash
# deploy.sh

set -e

VERSION=$1
ENVIRONMENT=${2:-production}

echo "Deploying version $VERSION to $ENVIRONMENT"

# Build new version
docker build -t news-mcp:$VERSION .

# Update scheduler first (can handle downtime)
docker-compose stop scheduler
docker-compose up -d scheduler

# Rolling update for web services
for i in {1..3}; do
    echo "Updating web instance $i"
    docker-compose stop web_$i
    docker-compose up -d web_$i
    sleep 30  # Wait for health check
done

echo "Deployment completed successfully"
```

### 2. Database Migrations

```bash
# Migration Script
#!/bin/bash
# migrate.sh

# Backup Database
pg_dump $DATABASE_URL > backup_$(date +%Y%m%d_%H%M%S).sql

# Run Migrations
python -c "
from app.database import create_db_and_tables
create_db_and_tables()
"

# Verify Migration
python jobs/scheduler_manager.py config --json | jq '.feeds_count'
```

### 3. Maintenance Tasks

```bash
# maintenance.sh - Daily maintenance
#!/bin/bash

# Cleanup old logs
find /var/log/news-mcp -name "*.log.*" -mtime +7 -delete

# Database maintenance
psql $DATABASE_URL -c "VACUUM ANALYZE;"
psql $DATABASE_URL -c "REINDEX DATABASE newsdb;"

# Template cache cleanup
python -c "
from app.services.dynamic_template_manager import cleanup_cache
cleanup_cache()
"

# Feed health check
python jobs/scheduler_manager.py status
```

## 🛠️ Troubleshooting

### Häufige Probleme

#### 1. Scheduler startet nicht
```bash
# Debug Scheduler
python jobs/scheduler_manager.py start --debug

# Check Logs
tail -f /tmp/news-mcp-scheduler.log

# Check Database Connection
python -c "
from app.database import engine
print(engine.connect())
"
```

#### 2. Template Assignment funktioniert nicht
```bash
# Check Template Status
curl http://localhost:8000/htmx/templates-list

# Manual Template Assignment
python -c "
from app.services.dynamic_template_manager import get_dynamic_template_manager
from app.database import engine
from sqlmodel import Session

with Session(engine) as session:
    with get_dynamic_template_manager(session) as manager:
        assignments = manager.auto_assign_templates_to_feeds()
        print(f'Made {assignments} assignments')
"
```

#### 3. Performance Probleme
```bash
# Database Performance
psql $DATABASE_URL -c "
SELECT query, mean_time, calls
FROM pg_stat_statements
ORDER BY mean_time DESC
LIMIT 10;
"

# Memory Usage
python -c "
import psutil
print(f'Memory: {psutil.virtual_memory().percent}%')
print(f'CPU: {psutil.cpu_percent()}%')
"
```

#### 4. Network/Connectivity Probleme
```bash
# Test External Connectivity
curl -I https://www.heise.de/rss/heise-atom.xml

# Test Database Connection
psql $DATABASE_URL -c "SELECT version();"

# Test Redis Connection (if using)
redis-cli ping
```

### Log Analysis

```bash
# Error Analysis
grep -E "(ERROR|CRITICAL)" /var/log/news-mcp/app.log | tail -20

# Performance Analysis
grep "Request took" /var/log/news-mcp/app.log | awk '{print $NF}' | sort -n

# Template Activity
grep "template_" /var/log/news-mcp/app.log | tail -10
```

### Emergency Procedures

#### Service Recovery
```bash
# Complete Service Restart
sudo systemctl stop news-api news-scheduler
sudo systemctl start news-scheduler
sleep 10
sudo systemctl start news-api

# Database Recovery
sudo -u postgres pg_resetwal /var/lib/postgresql/15/main
sudo systemctl restart postgresql
```

#### Data Recovery
```bash
# Restore from Backup
psql $DATABASE_URL < backup_YYYYMMDD_HHMMSS.sql

# Rebuild Template Cache
python -c "
from app.services.dynamic_template_manager import rebuild_cache
rebuild_cache()
"
```

## 🎯 Production Checklist

- [ ] SSL Certificate konfiguriert und Auto-Renewal aktiviert
- [ ] Database Backups automatisiert (täglich)
- [ ] Monitoring und Alerting konfiguriert
- [ ] Log Rotation konfiguriert
- [ ] Firewall Rules konfiguriert
- [ ] Security Updates automatisiert
- [ ] Health Checks implementiert
- [ ] Performance Monitoring aktiv
- [ ] Error Tracking konfiguriert
- [ ] Documentation aktuell
- [ ] Disaster Recovery Plan dokumentiert
- [ ] Team Zugriffe konfiguriert

---

**⚡ Für weitere Hilfe:**
- Issues: [GitHub Issues](https://github.com/your-org/news-mcp/issues)
- Documentation: [Wiki](https://github.com/your-org/news-mcp/wiki)
- Community: [Discussions](https://github.com/your-org/news-mcp/discussions)