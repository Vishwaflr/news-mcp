# News MCP Deployment Guide

## Übersicht

Dieser Guide beschreibt verschiedene Deployment-Strategien für das News MCP System - von Development bis Production.

## Voraussetzungen

### System Requirements
- **OS**: Linux (Ubuntu 20.04+, CentOS 8+) oder macOS
- **RAM**: 4GB+ (8GB+ für Production)
- **Storage**: 20GB+ freier Speicherplatz
- **Network**: Stabile Internetverbindung für RSS-Feeds

### Software Dependencies
- **Python**: 3.9+ (empfohlen: 3.11)
- **PostgreSQL**: 15+
- **Git**: Für Code-Deployment
- **Nginx**: Für Production Reverse Proxy (optional)
- **Systemd**: Für Service Management (Linux)

## Development Deployment

### Quick Start
```bash
# Repository klonen
git clone https://github.com/your-org/news-mcp.git
cd news-mcp

# Environment Setup
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Database Setup
sudo -u postgres createdb news_db
sudo -u postgres createuser news_user
alembic upgrade head

# Services starten
./scripts/start-web-server.sh
./scripts/start-worker.sh
./scripts/start-scheduler.sh
```

### Environment Configuration
```bash
# .env für Development
DATABASE_URL=postgresql://news_user:news_password@localhost/news_db
OPENAI_API_KEY=your_api_key_here
ENVIRONMENT=development
LOG_LEVEL=DEBUG
WEB_HOST=0.0.0.0
WEB_PORT=8001
```

## Production Deployment

### 1. Server Vorbereitung

#### Ubuntu/Debian
```bash
# System Updates
sudo apt update && sudo apt upgrade -y

# Dependencies installieren
sudo apt install -y python3 python3-venv python3-pip \
    postgresql postgresql-contrib nginx git supervisor

# News MCP User erstellen
sudo useradd -m -s /bin/bash news-mcp
sudo usermod -aG sudo news-mcp
```

#### CentOS/RHEL
```bash
# System Updates
sudo dnf update -y

# Dependencies installieren
sudo dnf install -y python3 python3-pip postgresql-server \
    postgresql-contrib nginx git supervisor

# PostgreSQL initialisieren
sudo postgresql-setup --initdb
sudo systemctl enable postgresql
sudo systemctl start postgresql
```

### 2. Database Setup

```bash
# PostgreSQL konfigurieren
sudo -u postgres psql
CREATE DATABASE news_db;
CREATE USER news_user WITH PASSWORD 'secure_production_password';
GRANT ALL PRIVILEGES ON DATABASE news_db TO news_user;
ALTER USER news_user CREATEDB;  -- Für Tests
\q

# PostgreSQL Tuning für Production
sudo nano /etc/postgresql/15/main/postgresql.conf
```

**PostgreSQL Tuning:**
```conf
# postgresql.conf für 8GB RAM Server
shared_buffers = 2GB
effective_cache_size = 6GB
maintenance_work_mem = 512MB
checkpoint_completion_target = 0.9
wal_buffers = 16MB
default_statistics_target = 100
random_page_cost = 1.1
effective_io_concurrency = 200
```

### 3. Application Deployment

```bash
# Als news-mcp User
sudo su - news-mcp
cd /home/news-mcp

# Code deployment
git clone https://github.com/your-org/news-mcp.git
cd news-mcp

# Python Environment
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Production Environment
cp .env.example .env
nano .env  # Production Konfiguration
```

**Production .env:**
```bash
# Production Environment
DATABASE_URL=postgresql://news_user:secure_production_password@localhost/news_db
OPENAI_API_KEY=your_production_api_key
ENVIRONMENT=production
LOG_LEVEL=WARNING
WEB_HOST=127.0.0.1
WEB_PORT=8001

# Security
SECRET_KEY=generate_secure_random_secret_key
ALLOWED_HOSTS=your-domain.com,www.your-domain.com

# Performance
WORKERS=4
MAX_CONCURRENT_ANALYSIS=3
FEED_FETCH_TIMEOUT=30
```

### 4. Database Migrations

```bash
# Migrations anwenden
source venv/bin/activate
alembic upgrade head

# Initial Data laden (optional)
python scripts/setup_initial_data.py
```

### 5. Systemd Services

#### Web Service
```bash
sudo nano /etc/systemd/system/news-mcp-web.service
```

```ini
[Unit]
Description=News MCP Web Server
After=network.target postgresql.service
Requires=postgresql.service

[Service]
Type=exec
User=news-mcp
Group=news-mcp
WorkingDirectory=/home/news-mcp/news-mcp
Environment=PATH=/home/news-mcp/news-mcp/venv/bin
EnvironmentFile=/home/news-mcp/news-mcp/.env
ExecStart=/home/news-mcp/news-mcp/venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8001 --workers 4
ExecReload=/bin/kill -HUP $MAINPID
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

#### Worker Service
```bash
sudo nano /etc/systemd/system/news-mcp-worker.service
```

```ini
[Unit]
Description=News MCP Analysis Worker
After=network.target postgresql.service news-mcp-web.service
Requires=postgresql.service

[Service]
Type=exec
User=news-mcp
Group=news-mcp
WorkingDirectory=/home/news-mcp/news-mcp
Environment=PATH=/home/news-mcp/news-mcp/venv/bin
EnvironmentFile=/home/news-mcp/news-mcp/.env
ExecStart=/home/news-mcp/news-mcp/scripts/start-worker.sh
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

#### Scheduler Service
```bash
sudo nano /etc/systemd/system/news-mcp-scheduler.service
```

```ini
[Unit]
Description=News MCP Feed Scheduler
After=network.target postgresql.service
Requires=postgresql.service

[Service]
Type=exec
User=news-mcp
Group=news-mcp
WorkingDirectory=/home/news-mcp/news-mcp
Environment=PATH=/home/news-mcp/news-mcp/venv/bin
EnvironmentFile=/home/news-mcp/news-mcp/.env
ExecStart=/home/news-mcp/news-mcp/scripts/start-scheduler.sh
Restart=always
RestartSec=15
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

#### Services aktivieren
```bash
# Services registrieren und starten
sudo systemctl daemon-reload
sudo systemctl enable news-mcp-web news-mcp-worker news-mcp-scheduler
sudo systemctl start news-mcp-web news-mcp-worker news-mcp-scheduler

# Status prüfen
sudo systemctl status news-mcp-web
sudo systemctl status news-mcp-worker
sudo systemctl status news-mcp-scheduler
```

### 6. Nginx Configuration

```bash
sudo nano /etc/nginx/sites-available/news-mcp
```

```nginx
server {
    listen 80;
    server_name your-domain.com www.your-domain.com;

    # Security Headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection \"1; mode=block\";
    add_header Strict-Transport-Security \"max-age=31536000; includeSubDomains\" always;

    # Gzip Compression
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types text/plain text/css text/xml text/javascript application/javascript application/xml+rss application/json;

    # Static Files
    location /static/ {
        alias /home/news-mcp/news-mcp/static/;
        expires 30d;
        add_header Cache-Control \"public, no-transform\";
    }

    # Health Check
    location /health {
        access_log off;
        proxy_pass http://127.0.0.1:8001/health;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Main Application
    location / {
        proxy_pass http://127.0.0.1:8001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # WebSocket Support
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection \"upgrade\";

        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # Rate Limiting
    location /api/ {
        limit_req zone=api burst=10 nodelay;
        proxy_pass http://127.0.0.1:8001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

# Rate Limiting Zones
http {
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
}
```

#### SSL mit Let's Encrypt
```bash
# Certbot installieren
sudo apt install certbot python3-certbot-nginx

# SSL Zertifikat erstellen
sudo certbot --nginx -d your-domain.com -d www.your-domain.com

# Auto-Renewal testen
sudo certbot renew --dry-run
```

### 7. Monitoring Setup

#### Log Rotation
```bash
sudo nano /etc/logrotate.d/news-mcp
```

```
/home/news-mcp/news-mcp/logs/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 news-mcp news-mcp
    postrotate
        systemctl reload news-mcp-web news-mcp-worker news-mcp-scheduler
    endscript
}
```

#### Health Check Script
```bash
nano /home/news-mcp/scripts/health-check.sh
```

```bash
#!/bin/bash
# Health Check Script für News MCP

LOG_FILE="/var/log/news-mcp-health.log"
ALERT_EMAIL="admin@your-domain.com"

check_service() {
    local service=$1
    if ! systemctl is-active --quiet $service; then
        echo "$(date): ERROR - $service is not running" | tee -a $LOG_FILE
        systemctl restart $service
        if [ $? -eq 0 ]; then
            echo "$(date): INFO - $service restarted successfully" | tee -a $LOG_FILE
        else
            echo "$(date): CRITICAL - Failed to restart $service" | tee -a $LOG_FILE
            echo "Critical: News MCP service $service failed to restart" | \
                mail -s "News MCP Alert" $ALERT_EMAIL
        fi
    fi
}

check_database() {
    if ! sudo -u news-mcp psql -d news_db -c "SELECT 1;" > /dev/null 2>&1; then
        echo "$(date): ERROR - Database connection failed" | tee -a $LOG_FILE
        echo "Database connection failed on News MCP server" | \
            mail -s "News MCP Database Alert" $ALERT_EMAIL
    fi
}

check_disk_space() {
    local usage=$(df /home/news-mcp | awk 'NR==2 {print $5}' | sed 's/%//')
    if [ $usage -gt 85 ]; then
        echo "$(date): WARNING - Disk usage at ${usage}%" | tee -a $LOG_FILE
        if [ $usage -gt 95 ]; then
            echo "Critical: Disk space at ${usage}% on News MCP server" | \
                mail -s "News MCP Disk Alert" $ALERT_EMAIL
        fi
    fi
}

# Health Checks ausführen
check_service "news-mcp-web"
check_service "news-mcp-worker"
check_service "news-mcp-scheduler"
check_database
check_disk_space

echo "$(date): Health check completed" >> $LOG_FILE
```

#### Cron Job für Health Checks
```bash
sudo crontab -e
```

```cron
# News MCP Health Checks
*/5 * * * * /home/news-mcp/scripts/health-check.sh
0 2 * * * /home/news-mcp/scripts/cleanup-logs.sh
0 1 * * 0 /home/news-mcp/scripts/weekly-maintenance.sh
```

## Docker Deployment

### Dockerfile
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# System dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Application code
COPY . .

# Non-root user
RUN useradd -m -u 1000 newsapp && chown -R newsapp:newsapp /app
USER newsapp

EXPOSE 8001

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8001/health || exit 1

CMD [\"uvicorn\", \"app.main:app\", \"--host\", \"0.0.0.0\", \"--port\", \"8001\"]
```

### docker-compose.yml
```yaml
version: '3.8'

services:
  web:
    build: .
    ports:
      - \"8001:8001\"
    environment:
      - DATABASE_URL=postgresql://news_user:news_password@db:5432/news_db
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - ENVIRONMENT=production
    depends_on:
      - db
      - redis
    volumes:
      - ./logs:/app/logs
    restart: unless-stopped

  worker:
    build: .
    command: python -m app.workers.analysis_worker
    environment:
      - DATABASE_URL=postgresql://news_user:news_password@db:5432/news_db
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    depends_on:
      - db
      - redis
    volumes:
      - ./logs:/app/logs
    restart: unless-stopped

  scheduler:
    build: .
    command: python -m app.workers.feed_scheduler
    environment:
      - DATABASE_URL=postgresql://news_user:news_password@db:5432/news_db
    depends_on:
      - db
    volumes:
      - ./logs:/app/logs
    restart: unless-stopped

  db:
    image: postgres:15
    environment:
      POSTGRES_DB: news_db
      POSTGRES_USER: news_user
      POSTGRES_PASSWORD: news_password
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./init.sql:/docker-entrypoint-initdb.d/init.sql
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    restart: unless-stopped

  nginx:
    image: nginx:alpine
    ports:
      - \"80:80\"
      - \"443:443\"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - web
    restart: unless-stopped

volumes:
  postgres_data:
```

### Docker Deployment
```bash
# Environment erstellen
cp .env.example .env
nano .env  # Konfiguration anpassen

# Services starten
docker-compose up -d

# Migrations ausführen
docker-compose exec web alembic upgrade head

# Logs verfolgen
docker-compose logs -f web worker scheduler
```

## Backup & Recovery

### Database Backup
```bash
#!/bin/bash
# /home/news-mcp/scripts/backup-db.sh

BACKUP_DIR=\"/home/news-mcp/backups\"
DATE=$(date +%Y%m%d_%H%M%S)
DB_NAME=\"news_db\"
RETENTION_DAYS=30

mkdir -p $BACKUP_DIR

# Database Backup
pg_dump -h localhost -U news_user $DB_NAME \
    --no-owner --no-privileges \
    | gzip > $BACKUP_DIR/news_db_$DATE.sql.gz

# Alte Backups löschen
find $BACKUP_DIR -name \"news_db_*.sql.gz\" -mtime +$RETENTION_DAYS -delete

echo \"Backup completed: news_db_$DATE.sql.gz\"
```

### Recovery Procedure
```bash
# Service stoppen
sudo systemctl stop news-mcp-web news-mcp-worker news-mcp-scheduler

# Database wiederherstellen
sudo -u postgres dropdb news_db
sudo -u postgres createdb news_db
sudo -u postgres psql -c \"GRANT ALL PRIVILEGES ON DATABASE news_db TO news_user;\"

# Backup einspielen
gunzip -c /home/news-mcp/backups/news_db_20240101_120000.sql.gz | \
    sudo -u news_user psql -h localhost news_db

# Services starten
sudo systemctl start news-mcp-web news-mcp-worker news-mcp-scheduler
```

## Performance Tuning

### Database Optimization
```sql
-- Performance Monitoring
SELECT schemaname, tablename,
       pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size,
       n_tup_ins, n_tup_upd, n_tup_del
FROM pg_stat_user_tables
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

-- Index Usage
SELECT schemaname, tablename, indexname, idx_tup_read, idx_tup_fetch
FROM pg_stat_user_indexes
ORDER BY idx_tup_read DESC;
```

### Application Tuning
```python
# app/core/config.py - Production Settings
class ProductionConfig:
    # Database Connection Pool
    DATABASE_POOL_SIZE = 20
    DATABASE_MAX_OVERFLOW = 30
    DATABASE_POOL_RECYCLE = 3600

    # Analysis Limits
    MAX_CONCURRENT_ANALYSIS = 3
    MAX_ITEMS_PER_ANALYSIS = 1000
    ANALYSIS_TIMEOUT_SECONDS = 300

    # Cache Settings
    CACHE_TTL_SECONDS = 300
    SELECTION_CACHE_SIZE = 1000
```

## Security

### Firewall Setup
```bash
# UFW Firewall
sudo ufw enable
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 80
sudo ufw allow 443
sudo ufw allow from 127.0.0.1 to any port 5432  # PostgreSQL local only
```

### SSL/TLS Configuration
```nginx
# Nginx SSL Best Practices
ssl_protocols TLSv1.2 TLSv1.3;
ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384;
ssl_prefer_server_ciphers off;
ssl_session_cache shared:SSL:10m;
ssl_session_timeout 10m;
```

### Environment Security
```bash
# Sichere Permissions
chmod 600 /home/news-mcp/news-mcp/.env
chown news-mcp:news-mcp /home/news-mcp/news-mcp/.env

# Log Files
chmod 640 /home/news-mcp/news-mcp/logs/*.log
chown news-mcp:adm /home/news-mcp/news-mcp/logs/*.log
```

## Troubleshooting

### Common Issues

#### Service startet nicht
```bash
# Logs prüfen
journalctl -u news-mcp-web -f
journalctl -u news-mcp-worker -f
journalctl -u news-mcp-scheduler -f

# Service Status
systemctl status news-mcp-web
systemctl status news-mcp-worker
systemctl status news-mcp-scheduler
```

#### Database Connection Issues
```bash
# PostgreSQL Status
sudo systemctl status postgresql
sudo -u postgres psql -c \"SELECT version();\"

# Connection Test
sudo -u news-mcp psql -h localhost -d news_db -c \"SELECT 1;\"
```

#### Performance Issues
```bash
# System Resources
htop
iotop
df -h
free -m

# Database Performance
sudo -u postgres psql -d news_db -c \"SELECT * FROM pg_stat_activity;\"
```

---

**Letzte Aktualisierung:** September 2024
**Deployment Version:** v2.1.0