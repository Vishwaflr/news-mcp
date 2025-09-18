# 🚀 News MCP Deployment Guide

Complete deployment guide for the News MCP Dynamic Template System in various environments.

## 📋 Table of Contents

- [🔧 System Requirements](#-system-requirements)
- [⚡ Quick Start (Development)](#-quick-start-development)
- [🏢 Production Deployment](#-production-deployment)
- [🐳 Docker Deployment](#-docker-deployment)
- [☁️ Cloud Deployment](#️-cloud-deployment)
- [📊 Monitoring & Logging](#-monitoring--logging)
- [🔄 Updates & Maintenance](#-updates--maintenance)
- [🛠️ Troubleshooting](#️-troubleshooting)

## 🔧 System Requirements

### Minimum Requirements
- **OS**: Linux, macOS, or Windows
- **Python**: 3.11+ (recommended: 3.12)
- **RAM**: 2 GB (4 GB recommended)
- **Storage**: 5 GB (10 GB recommended)
- **CPU**: 2 Cores (4 Cores recommended)

### Production Requirements
- **OS**: Linux (Ubuntu 22.04+ or RHEL 8+)
- **Python**: 3.12
- **RAM**: 8 GB (16 GB for >500 Feeds)
- **Storage**: 50 GB SSD
- **CPU**: 4 Cores (8 Cores for >500 Feeds)
- **Database**: PostgreSQL 15+

## ⚡ Quick Start (Development)

### 1. Repository Setup

```bash
# Clone repository
git clone https://github.com/your-org/news-mcp.git
cd news-mcp

# Create virtual environment
python3.12 -m venv venv
source venv/bin/activate  # Linux/macOS
# venv\\Scripts\\activate  # Windows

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

### 2. Database Setup

```bash
# Start PostgreSQL with Docker Compose
docker compose up -d

# Wait until PostgreSQL is ready
sleep 5
```

### 3. Configuration

```bash
# Create configuration file
cp .env.example .env

# Adjust .env (optional for development)
nano .env
```

### 4. Start Services

```bash
# Terminal 1: Web-API Server
export PYTHONPATH=$(pwd)
python app/main.py

# Terminal 2: Dynamic Scheduler
python jobs/scheduler_manager.py start --debug

# Terminal 3: MCP Server (optional)
python mcp_server/server.py
```

### 5. Test Access

```bash
# Web Interface
open http://localhost:8000/admin/templates

# API Health Check
curl http://localhost:8000/api/health

# Template Management
curl http://localhost:8000/htmx/templates-list
```

## 🏢 Production Deployment

### Server Setup

```bash
# System updates
sudo apt update && sudo apt upgrade -y

# Install Python 3.12
sudo apt install python3.12 python3.12-venv python3.12-dev -y

# Install PostgreSQL
sudo apt install postgresql postgresql-contrib -y

# Install Redis (optional for caching)
sudo apt install redis-server -y

# Install Nginx
sudo apt install nginx -y
```

### Application Setup

```bash
# Create app user
sudo useradd -r -s /bin/false newsapp
sudo mkdir -p /opt/news-mcp
sudo chown newsapp:newsapp /opt/news-mcp

# Clone and setup application
cd /opt/news-mcp
sudo -u newsapp git clone https://github.com/your-org/news-mcp.git .
sudo -u newsapp python3.12 -m venv venv
sudo -u newsapp ./venv/bin/pip install -r requirements.txt
```

### Database Configuration

```bash
# Switch to postgres user
sudo -u postgres psql

-- Create database and user
CREATE DATABASE news_mcp;
CREATE USER news_mcp_user WITH PASSWORD 'secure_password_here';
GRANT ALL PRIVILEGES ON DATABASE news_mcp TO news_mcp_user;
\\q
```

### Environment Configuration

```bash
# Create production environment file
sudo -u newsapp cp .env.example .env

# Edit with production settings
sudo -u newsapp nano .env
```

## 🐳 Docker Deployment

### Docker Compose for Local Development

```yaml
version: '3.8'

services:
  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://user:pass@db:5432/news_mcp
    depends_on:
      - db
      - redis

  db:
    image: postgres:15
    environment:
      POSTGRES_DB: news_mcp
      POSTGRES_USER: user
      POSTGRES_PASSWORD: pass
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine

volumes:
  postgres_data:
```

### Production Docker Setup

```bash
# Build production image
docker build -t news-mcp:latest .

# Run with production settings
docker run -d \
  --name news-mcp-prod \
  -p 8000:8000 \
  -e DATABASE_URL="postgresql://user:pass@localhost:5432/news_mcp" \
  news-mcp:latest
```

## ☁️ Cloud Deployment

### AWS Deployment

1. **EC2 Instance Setup**
   - Use Ubuntu 22.04 LTS
   - t3.medium or larger
   - Configure security groups for ports 80, 443, 8000

2. **RDS PostgreSQL**
   - PostgreSQL 15
   - Multi-AZ for production
   - Automated backups enabled

3. **Application Load Balancer**
   - SSL termination
   - Health checks on /api/health

### Azure Deployment

1. **App Service**
   - Python 3.12 runtime
   - B2 or higher tier

2. **Azure Database for PostgreSQL**
   - Flexible Server
   - PostgreSQL 15

## 📊 Monitoring & Logging

### System Monitoring

```bash
# Install monitoring tools
pip install psutil prometheus-client

# Monitor logs
sudo journalctl -u news-mcp -f

# Check system resources
htop
df -h
```

### Health Checks

```bash
# API health check
curl http://localhost:8000/api/health

# Database connection test
python -c "from app.database import get_db; print('DB OK')"

# Feed processing status
curl http://localhost:8000/api/statistics/feeds
```

### Log Management

```bash
# Configure logrotate
sudo nano /etc/logrotate.d/news-mcp

# Content:
/opt/news-mcp/logs/*.log {
    daily
    missingok
    rotate 52
    compress
    delaycompress
    notifempty
    create 644 newsapp newsapp
}
```

## 🔄 Updates & Maintenance

### Application Updates

```bash
# Backup database
pg_dump news_mcp > backup_$(date +%Y%m%d).sql

# Update code
git pull origin main

# Install new dependencies
pip install -r requirements.txt

# Restart services
sudo systemctl restart news-mcp
```

### Database Maintenance

```bash
# Run database migrations
python -m alembic upgrade head

# Optimize database
sudo -u postgres psql news_mcp -c "VACUUM ANALYZE;"

# Check database size
sudo -u postgres psql news_mcp -c "SELECT pg_size_pretty(pg_database_size('news_mcp'));"
```

## 🛠️ Troubleshooting

### Common Issues

1. **Database connection errors**
   ```bash
   # Check PostgreSQL status
   sudo systemctl status postgresql

   # Check connection
   pg_isready -h localhost -p 5432
   ```

2. **High memory usage**
   ```bash
   # Monitor processes
   ps aux | grep python

   # Check memory usage
   free -h
   ```

3. **Feed processing issues**
   ```bash
   # Check scheduler logs
   tail -f logs/scheduler.log

   # Restart scheduler
   python jobs/scheduler_manager.py restart
   ```

### Performance Tuning

```bash
# PostgreSQL tuning
sudo nano /etc/postgresql/15/main/postgresql.conf

# Increase shared_buffers, work_mem, maintenance_work_mem
# Restart PostgreSQL
sudo systemctl restart postgresql
```

### Backup & Recovery

```bash
# Daily backup script
#!/bin/bash
DATE=$(date +%Y%m%d)
pg_dump news_mcp | gzip > /backups/news_mcp_$DATE.sql.gz

# Keep only 30 days of backups
find /backups -name "news_mcp_*.sql.gz" -mtime +30 -delete
```

### Deployment Checklist

- [ ] Server resources adequate
- [ ] PostgreSQL configured and secured
- [ ] SSL certificates installed
- [ ] Environment variables set
- [ ] Database migrations applied
- [ ] Backup system configured
- [ ] Monitoring alerts configured
- [ ] Database backups automated (daily)
- [ ] Log rotation configured
- [ ] Firewall rules applied
- [ ] Health checks passing
- [ ] Performance monitoring active
- [ ] Error tracking enabled

## 📞 Support

**⚡ For additional help:**
- Check the [troubleshooting guide](./docs/troubleshooting.md)
- Review [system logs](#-monitoring--logging)
- Open an issue on GitHub

---
**🚀 Happy Deploying!** The News MCP system is designed for reliability and scalability.