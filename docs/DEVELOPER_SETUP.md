# Developer Setup Guide

## Overview

This guide describes how to set up a local development environment for the News MCP System.

## System Requirements

### Hardware
- **RAM**: 8GB+ recommended
- **Storage**: 10GB+ free disk space
- **CPU**: 2+ Cores

### Software
- **Python**: 3.9+ (recommended: 3.11)
- **Git**: For version control
- **PostgreSQL**: 15+ (or Docker)
- **Editor**: VS Code, PyCharm, or similar

## 1. Environment Setup

### Python Installation

#### macOS (with Homebrew)
```bash
# Install Homebrew (if not already installed)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install Python
brew install python@3.11
brew install postgresql@15
```

#### Ubuntu/Debian
```bash
sudo apt update
sudo apt install -y python3.11 python3.11-venv python3.11-dev \
    postgresql postgresql-contrib libpq-dev git curl
```

#### Windows (with Chocolatey)
```powershell
# Install Chocolatey
Set-ExecutionPolicy Bypass -Scope Process -Force; iex ((New-Object System.Net.WebClient).DownloadString('https://chocolatey.org/install.ps1'))

# Install Dependencies
choco install python311 postgresql git
```

### Git Configuration
```bash
# Git Configuration
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"
git config --global init.defaultBranch main

# SSH Key for GitHub (optional)
ssh-keygen -t ed25519 -C "your.email@example.com"
eval "$(ssh-agent -s)"
ssh-add ~/.ssh/id_ed25519
```

## 2. Repository Setup

### Code Checkout
```bash
# Clone Repository
git clone https://github.com/your-org/news-mcp.git
cd news-mcp

# Development Branch (if available)
git checkout develop
```

### Python Virtual Environment
```bash
# Create Virtual Environment
python3.11 -m venv venv

# Activate
source venv/bin/activate  # Linux/macOS
# or: venv\Scripts\activate  # Windows

# Upgrade Pip
pip install --upgrade pip

# Install Dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt  # Development Dependencies
```

## 3. Database Setup

### PostgreSQL Installation & Configuration

#### Option 1: Local Installation
```bash
# Start PostgreSQL
sudo systemctl start postgresql  # Linux
brew services start postgresql@15  # macOS

# Create Database and User
sudo -u postgres psql
```

```sql
CREATE DATABASE news_db;
CREATE USER news_user WITH PASSWORD 'news_password';
GRANT ALL PRIVILEGES ON DATABASE news_db TO news_user;
ALTER USER news_user CREATEDB;  -- For Tests
\q
```

#### Option 2: Docker
```bash
# Start PostgreSQL Container
docker run --name news-postgres \
    -e POSTGRES_DB=news_db \
    -e POSTGRES_USER=news_user \
    -e POSTGRES_PASSWORD=news_password \
    -p 5432:5432 \
    -d postgres:15

# Check Container Status
docker ps
```

### Database Migrations
```bash
# Set Environment Variables
export DATABASE_URL="postgresql://news_user:news_password@localhost/news_db"
export PGPASSWORD=news_password

# Run Alembic Migrations
alembic upgrade head

# Check Migrations Status
alembic current
alembic history
```

## 4. Environment Configuration

### Create .env File
```bash
cp .env.example .env
```

### Development .env
```bash
# Database
DATABASE_URL=postgresql://news_user:news_password@localhost/news_db

# OpenAI (for AI Analysis)
OPENAI_API_KEY=your_openai_api_key_here

# Environment
ENVIRONMENT=development
LOG_LEVEL=DEBUG

# Web Server
WEB_HOST=0.0.0.0
WEB_PORT=8001

# Development Features
DEBUG=true
RELOAD=true

# Analysis Settings
MAX_CONCURRENT_ANALYSIS=1
DEFAULT_MODEL=gpt-4.1-nano
DEFAULT_RATE_LIMIT=1.0

# Cache Settings
CACHE_TTL_SECONDS=60
SELECTION_CACHE_SIZE=100
```

## 5. Development Tools

### Pre-commit Hooks
```bash
# Install Pre-commit
pip install pre-commit

# Setup Hooks
pre-commit install

# Run Hooks Manually
pre-commit run --all-files
```

### Code Quality Tools

#### .pre-commit-config.yaml
```yaml
repos:
  - repo: https://github.com/psf/black
    rev: 23.7.0
    hooks:
      - id: black
        language_version: python3.11

  - repo: https://github.com/pycqa/isort
    rev: 5.12.0
    hooks:
      - id: isort
        args: ["--profile", "black"]

  - repo: https://github.com/pycqa/flake8
    rev: 6.0.0
    hooks:
      - id: flake8
        args: ["--max-line-length=88", "--extend-ignore=E203,W503"]

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.5.1
    hooks:
      - id: mypy
        additional_dependencies: [types-requests]
```

### IDE Configuration

#### VS Code
```json
// .vscode/settings.json
{
    "python.defaultInterpreterPath": "./venv/bin/python",
    "python.linting.enabled": true,
    "python.linting.pylintEnabled": false,
    "python.linting.flake8Enabled": true,
    "python.formatting.provider": "black",
    "python.sortImports.args": ["--profile", "black"],
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
        "source.organizeImports": true
    },
    "python.testing.pytestEnabled": true,
    "python.testing.pytestArgs": ["tests/"],
    "files.exclude": {
        "**/__pycache__": true,
        "**/*.pyc": true,
        ".pytest_cache": true,
        ".coverage": true,
        "htmlcov": true
    }
}
```

#### VS Code Extensions
```bash
# Recommended Extensions
code --install-extension ms-python.python
code --install-extension ms-python.black-formatter
code --install-extension ms-python.isort
code --install-extension ms-python.flake8
code --install-extension ms-python.mypy-type-checker
code --install-extension bradlc.vscode-tailwindcss
code --install-extension formulahendry.auto-rename-tag
```

## 6. Start Services

### Development Server
```bash
# All Services Together (recommended)
./scripts/start-all-background.sh

# Or individually:
./scripts/start-web-server.sh      # Port 8001
./scripts/start-worker.sh          # Background Analysis Worker
./scripts/start-scheduler.sh       # Feed Scheduler
```

### Service Management
```bash
# Check Status
./scripts/status.sh

# Stop Services
./scripts/stop-all.sh

# Follow Logs
tail -f logs/web.log
tail -f logs/worker.log
tail -f logs/scheduler.log
```

## 7. Testing

### Test Setup
```bash
# Create Test Database
export TEST_DATABASE_URL="postgresql://news_user:news_password@localhost/news_db_test"
createdb news_db_test
alembic -x data=test upgrade head
```

### Run Tests
```bash
# All Tests
pytest

# With Coverage
pytest --cov=app --cov-report=html

# Specific Tests
pytest tests/test_analysis.py
pytest tests/test_feeds.py -v

# Tests with Marks
pytest -m "not slow"  # Fast Tests
pytest -m "integration"  # Integration Tests
```

### Test Configuration

#### pytest.ini
```ini
[tool:pytest]
testpaths = tests
python_files = test_*.py
python_functions = test_*
python_classes = Test*
addopts =
    --strict-markers
    --strict-config
    -ra
    --cov-branch
    --cov-report=term-missing:skip-covered
    --cov-fail-under=80

markers =
    slow: marks tests as slow (deselect with '-m "not slow"')
    integration: marks tests as integration tests
    unit: marks tests as unit tests
    api: marks tests as API tests
```

## 8. Development Workflow

### Branch Strategy
```bash
# Feature Development
git checkout develop
git pull origin develop
git checkout -b feature/analysis-improvements

# Development...
git add .
git commit -m "feat: improve analysis speed"

# Push and Pull Request
git push origin feature/analysis-improvements
```

### Code Style Guidelines

#### Python Code Standards
```python
# Example: Good Python Code Style
from typing import List, Optional
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from app.database import get_session
from app.models import Feed, FeedCreate
from app.services.feed_service import FeedService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/feeds", tags=["feeds"])


@router.post("/", response_model=Feed)
async def create_feed(
    feed_data: FeedCreate,
    db: Session = Depends(get_session)
) -> Feed:
    """Create a new RSS feed.

    Args:
        feed_data: Feed creation data
        db: Database session

    Returns:
        Created feed object

    Raises:
        HTTPException: If feed creation fails
    """
    try:
        feed_service = FeedService(db)
        feed = await feed_service.create_feed(feed_data)
        logger.info(f"Created feed: {feed.id}")
        return feed
    except Exception as e:
        logger.error(f"Feed creation failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))
```

### Debugging

#### VS Code Debug Configuration
```json
// .vscode/launch.json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "FastAPI Server",
            "type": "python",
            "request": "launch",
            "program": "${workspaceFolder}/venv/bin/uvicorn",
            "args": [
                "app.main:app",
                "--host", "0.0.0.0",
                "--port", "8001",
                "--reload"
            ],
            "env": {
                "PYTHONPATH": "${workspaceFolder}",
                "DATABASE_URL": "postgresql://news_user:news_password@localhost/news_db"
            },
            "console": "integratedTerminal",
            "cwd": "${workspaceFolder}"
        },
        {
            "name": "Analysis Worker",
            "type": "python",
            "request": "launch",
            "program": "${workspaceFolder}/scripts/start-worker.sh",
            "console": "integratedTerminal",
            "cwd": "${workspaceFolder}"
        }
    ]
}
```

#### PDB Debugging
```python
# Set breakpoint in code
import pdb; pdb.set_trace()

# Or with ipdb (better output)
import ipdb; ipdb.set_trace()
```

## 9. Database Development

### Creating Migrations
```bash
# Create new migration
alembic revision --autogenerate -m "Add feed categories table"

# Create migration manually
alembic revision -m "Add custom index"
```

### Database Tools
```bash
# pgAdmin Web Interface
pip install pgadmin4

# CLI Tools
pip install pgcli  # Better psql
pgcli postgresql://news_user:news_password@localhost/news_db
```

### Sample Data
```bash
# Load Test Data
python scripts/load_sample_data.py

# Or SQL directly
psql -h localhost -U news_user news_db < sample_data.sql
```

## 10. API Development

### FastAPI Development Server
```bash
# With Auto-Reload
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload

# With Debug Logging
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload --log-level debug
```

### API Testing
```bash
# OpenAPI Docs
open http://localhost:8001/docs

# Curl Examples
curl -X GET "http://localhost:8001/api/feeds" \
     -H "accept: application/json"

curl -X POST "http://localhost:8001/api/feeds" \
     -H "Content-Type: application/json" \
     -d '{"title": "Test Feed", "url": "https://example.com/feed.xml"}'
```

### Postman Collection
```json
{
    "info": {
        "name": "News MCP API",
        "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
    },
    "variable": [
        {
            "key": "base_url",
            "value": "http://localhost:8001"
        }
    ],
    "item": [
        {
            "name": "List Feeds",
            "request": {
                "method": "GET",
                "header": [],
                "url": {
                    "raw": "{{base_url}}/api/feeds",
                    "host": ["{{base_url}}"],
                    "path": ["api", "feeds"]
                }
            }
        }
    ]
}
```

## 11. Frontend Development

### HTMX Development
```html
<!-- Live Reload for HTMX Development -->
<script>
    if (window.location.hostname === 'localhost') {
        // Auto-refresh on changes
        setInterval(() => {
            fetch('/health')
                .catch(() => location.reload());
        }, 1000);
    }
</script>
```

### Alpine.js Development
```javascript
// Debug Alpine.js
window.Alpine.devtools = true;

// Global Alpine Data
document.addEventListener('alpine:init', () => {
    Alpine.store('debug', {
        enabled: true,
        log(message) {
            if (this.enabled) {
                console.log('[Alpine Debug]:', message);
            }
        }
    });
});
```

## 12. Performance Profiling

### Python Profiling
```bash
# cProfile
python -m cProfile -o profile.stats scripts/analyze_performance.py

# py-spy (System-wide Profiling)
pip install py-spy
py-spy record -o profile.svg -- python app/main.py
```

### Database Profiling
```sql
-- Query Performance
EXPLAIN (ANALYZE, BUFFERS)
SELECT * FROM items
WHERE feed_id = 1
ORDER BY published DESC
LIMIT 10;

-- Enable Slow Query Log
ALTER SYSTEM SET log_min_duration_statement = '1000ms';
SELECT pg_reload_conf();
```

## 13. Troubleshooting

### Common Issues

#### Import Errors
```bash
# Set PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Or in Python
import sys
sys.path.append('.')
```

#### Database Connection Issues
```bash
# Check PostgreSQL Status
brew services list | grep postgresql  # macOS
systemctl status postgresql  # Linux

# Connection Test
psql -h localhost -U news_user -d news_db -c "SELECT version();"
```

#### Port Conflicts
```bash
# Check Port Usage
lsof -i :8001
netstat -tulpn | grep :8001

# Kill Process
kill -9 <PID>
```

### Logging Configuration
```python
# app/core/logging_config.py - Development
import logging

def setup_development_logging():
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('logs/development.log')
        ]
    )
```

## 14. Contributing

### Pull Request Process
1. Create feature branch
2. Develop code + write tests
3. Run code quality tools
4. Create pull request
5. Wait for code review
6. Merge after approval

### Code Review Checklist
- [ ] Tests present and passing
- [ ] Documentation updated
- [ ] Code style followed
- [ ] Performance considered
- [ ] Security best practices followed
- [ ] Breaking changes documented

---

**Last Updated:** September 2024
**Developer Setup Version:** v2.1.0
