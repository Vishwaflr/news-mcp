# Contributing to News MCP

**Enterprise RSS Management & AI Analysis Platform**

Thank you for your interest in contributing to News MCP! This document provides comprehensive guidelines and information for contributors.

## 🚀 Quick Start for Contributors

### Prerequisites
- **Python 3.11+** with virtual environment support
- **PostgreSQL 14+** with development headers
- **Git** with commit signing configured (recommended)
- **Docker** (optional, for containerized development)

### Development Setup

1. **Fork and Clone**
   ```bash
   git clone https://github.com/your-username/news-mcp.git
   cd news-mcp
   ```

2. **Environment Setup**
   ```bash
   # Create virtual environment
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate

   # Install dependencies
   pip install -r requirements.txt
   pip install -r requirements-dev.txt
   ```

3. **Database Setup**
   ```bash
   # Copy environment template
   cp .env.example .env
   # Edit .env with your database credentials

   # Run migrations
   alembic upgrade head
   ```

4. **Verify Installation**
   ```bash
   # Run tests
   python -m pytest tests/ -v

   # Start development server
   ./scripts/start-web-server.sh
   ```

---

## 📋 Development Guidelines

### Code Standards

#### Python Code Style
- **PEP 8 Compliance**: All code must follow PEP 8 guidelines
- **Type Hints**: Required for all function signatures
- **Docstrings**: Google-style docstrings for all public functions
- **Line Length**: Maximum 88 characters (Black formatter)

**Example:**
```python
def analyze_articles(
    items: List[Item],
    model: str = "gpt-4.1-nano",
    batch_size: int = 10
) -> AnalysisResult:
    """Analyze a batch of articles using AI.

    Args:
        items: List of articles to analyze
        model: AI model to use for analysis
        batch_size: Number of articles to process in each batch

    Returns:
        Analysis results with sentiment and impact scores

    Raises:
        AnalysisError: If analysis fails for any item
    """
    pass
```

#### Code Quality Tools
```bash
# Format code (required before commit)
black app/ tests/
isort app/ tests/

# Type checking
mypy app/

# Linting
flake8 app/ tests/

# Security scanning
bandit -r app/
```

### Git Workflow

#### Branch Naming Convention
- `feature/description` - New features
- `bugfix/description` - Bug fixes
- `hotfix/description` - Critical production fixes
- `refactor/description` - Code refactoring
- `docs/description` - Documentation updates

#### Commit Message Format
```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types:**
- `feat` - New feature
- `fix` - Bug fix
- `docs` - Documentation changes
- `style` - Code formatting changes
- `refactor` - Code refactoring
- `test` - Adding or updating tests
- `chore` - Maintenance tasks

**Example:**
```
feat(analysis): add batch processing for AI analysis

- Implement queue-based batch processing
- Add cost estimation and monitoring
- Include progress tracking with ETA
- Support for multiple AI models

Closes #123
```

### Testing Requirements

#### Test Coverage
- **Minimum Coverage**: 80% overall
- **New Features**: 90% coverage required
- **Critical Paths**: 95% coverage (analysis, feed processing)

#### Test Categories
1. **Unit Tests** - Individual component testing
   ```bash
   pytest tests/unit/ -v
   ```

2. **Integration Tests** - Component interaction testing
   ```bash
   pytest tests/integration/ -v
   ```

3. **API Tests** - Endpoint testing
   ```bash
   pytest tests/api/ -v
   ```

4. **Performance Tests** - Load and performance testing
   ```bash
   pytest tests/performance/ -v --benchmark-only
   ```

#### Writing Tests
```python
import pytest
from unittest.mock import Mock, patch
from app.services.analysis import AnalysisService

class TestAnalysisService:
    """Test suite for AnalysisService."""

    @pytest.fixture
    def analysis_service(self):
        """Create AnalysisService instance for testing."""
        return AnalysisService(model="test-model")

    def test_analyze_single_article(self, analysis_service):
        """Test analysis of a single article."""
        # Given
        article = Mock(title="Test Article", content="Test content")

        # When
        result = analysis_service.analyze(article)

        # Then
        assert result.sentiment is not None
        assert result.impact_score >= 0.0
        assert result.impact_score <= 1.0
```

---

## 🔧 Database Development

### Schema Changes

#### Migration Process
1. **Create Migration**
   ```bash
   alembic revision --autogenerate -m "Add user preferences table"
   ```

2. **Review Generated Migration**
   - Check for data loss operations
   - Verify index creation strategies
   - Test migration on sample data

3. **Test Migration**
   ```bash
   # Test upgrade
   alembic upgrade head

   # Test downgrade
   alembic downgrade -1
   alembic upgrade head
   ```

#### Migration Best Practices
- **Backwards Compatibility**: Ensure migrations don't break existing code
- **Performance**: Add indexes concurrently for large tables
- **Data Safety**: Use transactions and rollback strategies
- **Documentation**: Include clear migration descriptions

**Example Migration:**
```python
"""Add analysis caching table

Revision ID: abc123def456
Revises: prev_revision
Create Date: 2025-09-24 10:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

def upgrade():
    """Add caching table for analysis results."""
    op.create_table('analysis_cache',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('content_hash', sa.String(64), nullable=False),
        sa.Column('model_version', sa.String(50), nullable=False),
        sa.Column('analysis_result', postgresql.JSONB(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes concurrently in production
    op.create_index('idx_analysis_cache_hash_model', 'analysis_cache',
                   ['content_hash', 'model_version'], unique=True)
    op.create_index('idx_analysis_cache_expires', 'analysis_cache', ['expires_at'])

def downgrade():
    """Remove analysis caching table."""
    op.drop_table('analysis_cache')
```

---

## 🎯 Feature Development

### AI Analysis Features

#### Development Guidelines
- **Model Abstraction**: Support multiple AI providers
- **Cost Tracking**: Accurate token and cost accounting
- **Error Handling**: Robust retry and fallback mechanisms
- **Rate Limiting**: Respect API limits and implement backoff

**Example Implementation:**
```python
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

class AIProvider(ABC):
    """Abstract base class for AI providers."""

    @abstractmethod
    async def analyze(self, content: str, **kwargs) -> Dict[str, Any]:
        """Analyze content and return structured results."""
        pass

    @abstractmethod
    def calculate_cost(self, tokens_used: int) -> float:
        """Calculate analysis cost in USD."""
        pass

class OpenAIProvider(AIProvider):
    """OpenAI GPT integration."""

    def __init__(self, api_key: str, model: str = "gpt-4.1-nano"):
        self.api_key = api_key
        self.model = model
        self.cost_per_token = 0.0015 / 1000  # $0.0015 per 1k tokens

    async def analyze(self, content: str, **kwargs) -> Dict[str, Any]:
        """Analyze content using OpenAI API."""
        try:
            response = await self._make_api_call(content, **kwargs)
            return {
                "sentiment": response["sentiment"],
                "impact": response["impact"],
                "tokens_used": response["usage"]["total_tokens"],
                "model": self.model
            }
        except Exception as e:
            logger.error(f"Analysis failed: {e}")
            raise AnalysisError(f"AI analysis failed: {e}")

    def calculate_cost(self, tokens_used: int) -> float:
        """Calculate cost based on token usage."""
        return tokens_used * self.cost_per_token
```

### RSS Feed Processing

#### Feed Handler Development
```python
from typing import List, Optional
from dataclasses import dataclass
from app.models.feed import Feed
from app.models.item import Item

@dataclass
class FeedProcessingResult:
    """Result of feed processing operation."""
    items_found: int
    items_new: int
    items_updated: int
    processing_time_ms: int
    errors: List[str]

class FeedProcessor:
    """Process RSS feeds and extract articles."""

    def __init__(self, template_engine: TemplateEngine):
        self.template_engine = template_engine

    async def process_feed(self, feed: Feed) -> FeedProcessingResult:
        """Process a single RSS feed."""
        start_time = time.time()

        try:
            # Fetch feed content
            content = await self._fetch_feed_content(feed.url)

            # Parse using appropriate template
            template = await self.template_engine.get_template(feed)
            items = await template.parse(content)

            # Store new items
            result = await self._store_items(feed, items)

            processing_time = int((time.time() - start_time) * 1000)
            return FeedProcessingResult(
                items_found=len(items),
                items_new=result.new_count,
                items_updated=result.updated_count,
                processing_time_ms=processing_time,
                errors=[]
            )

        except Exception as e:
            logger.error(f"Feed processing failed for {feed.url}: {e}")
            return FeedProcessingResult(
                items_found=0, items_new=0, items_updated=0,
                processing_time_ms=int((time.time() - start_time) * 1000),
                errors=[str(e)]
            )
```

---

## 🔍 Code Review Process

### Pull Request Requirements

#### PR Checklist
- [ ] **Code Quality**
  - [ ] Follows style guidelines
  - [ ] Includes type hints
  - [ ] Has comprehensive docstrings
  - [ ] Passes all linting checks

- [ ] **Testing**
  - [ ] Includes unit tests
  - [ ] Maintains 80%+ coverage
  - [ ] All tests pass
  - [ ] Includes integration tests for new features

- [ ] **Documentation**
  - [ ] Updates relevant documentation
  - [ ] Includes API documentation updates
  - [ ] Updates CHANGELOG.md
  - [ ] Includes migration notes if needed

- [ ] **Database Changes**
  - [ ] Includes migration scripts
  - [ ] Migration tested up/down
  - [ ] Performance impact assessed
  - [ ] Backwards compatibility verified

#### PR Template
```markdown
## Description
Brief description of changes and motivation.

## Type of Change
- [ ] Bug fix (non-breaking change that fixes an issue)
- [ ] New feature (non-breaking change that adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Documentation update

## Testing
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] Manual testing completed
- [ ] Performance impact tested

## Database Changes
- [ ] No database changes
- [ ] Includes migration script
- [ ] Migration tested
- [ ] Data loss risk: None/Low/Medium/High

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] Tests added/updated
- [ ] No merge conflicts
```

### Review Guidelines

#### For Reviewers
1. **Code Quality**
   - Check for proper error handling
   - Verify security best practices
   - Ensure performance considerations
   - Review test coverage

2. **Architecture**
   - Verify separation of concerns
   - Check dependency management
   - Ensure scalability considerations
   - Review API design

3. **Database**
   - Check migration safety
   - Verify index usage
   - Review query performance
   - Ensure data integrity

#### For Authors
1. **Pre-Submit**
   - Run full test suite
   - Check code formatting
   - Update documentation
   - Test migration scripts

2. **Addressing Feedback**
   - Respond to all comments
   - Make requested changes
   - Add tests for edge cases
   - Update documentation

---

## 🚀 Deployment & Release

### Release Process

#### Version Numbering
We follow [Semantic Versioning](https://semver.org/):
- **MAJOR** (X.0.0): Breaking changes
- **MINOR** (x.Y.0): New features (backwards compatible)
- **PATCH** (x.y.Z): Bug fixes (backwards compatible)

#### Release Checklist
1. **Pre-Release**
   - [ ] All tests passing
   - [ ] Documentation updated
   - [ ] Migration scripts tested
   - [ ] Performance benchmarks verified
   - [ ] Security audit completed

2. **Release**
   - [ ] Version number updated
   - [ ] CHANGELOG.md updated
   - [ ] Git tag created
   - [ ] Release notes written
   - [ ] Docker images built

3. **Post-Release**
   - [ ] Deployment verified
   - [ ] Monitoring dashboards checked
   - [ ] Performance metrics reviewed
   - [ ] Error rates monitored

### Hotfix Process
```bash
# Create hotfix branch from main
git checkout main
git pull origin main
git checkout -b hotfix/critical-security-fix

# Make minimal fix
# ... code changes ...

# Test thoroughly
pytest tests/ -v
./scripts/run-security-tests.sh

# Create PR for immediate review
gh pr create --title "HOTFIX: Critical security vulnerability" \
             --body "Fixes critical security issue..." \
             --label "hotfix" \
             --reviewer team-leads

# After approval and merge
git tag v2.1.1
git push origin v2.1.1
```

---

## 📊 Performance Guidelines

### Performance Standards
- **API Response Times**: 95th percentile < 200ms
- **Database Queries**: 99th percentile < 100ms
- **Feed Processing**: < 5 seconds per feed
- **Analysis Processing**: < 10 seconds per article

### Optimization Guidelines
```python
# Good: Efficient database query
def get_recent_articles(limit: int = 50) -> List[Item]:
    """Get recent articles with proper indexing."""
    return session.query(Item)\
        .options(joinedload(Item.feed))\
        .filter(Item.published > datetime.now() - timedelta(hours=24))\
        .order_by(Item.published.desc())\
        .limit(limit)\
        .all()

# Bad: N+1 query problem
def get_articles_with_feeds_bad(article_ids: List[int]) -> List[Item]:
    """BAD: Creates N+1 queries."""
    articles = session.query(Item).filter(Item.id.in_(article_ids)).all()
    for article in articles:
        article.feed_title = article.feed.title  # Causes extra query per article
    return articles

# Good: Single query with join
def get_articles_with_feeds_good(article_ids: List[int]) -> List[Item]:
    """GOOD: Single query with join."""
    return session.query(Item)\
        .options(joinedload(Item.feed))\
        .filter(Item.id.in_(article_ids))\
        .all()
```

### Caching Strategy
```python
from functools import lru_cache
from typing import Optional
import redis

class CacheService:
    """Redis-based caching service."""

    def __init__(self, redis_url: str):
        self.redis = redis.from_url(redis_url)

    def get_analysis_result(self, content_hash: str, model: str) -> Optional[Dict]:
        """Get cached analysis result."""
        cache_key = f"analysis:{content_hash}:{model}"
        cached = self.redis.get(cache_key)
        return json.loads(cached) if cached else None

    def set_analysis_result(self, content_hash: str, model: str,
                           result: Dict, ttl: int = 86400):
        """Cache analysis result for 24 hours."""
        cache_key = f"analysis:{content_hash}:{model}"
        self.redis.setex(cache_key, ttl, json.dumps(result))
```

---

## 🔒 Security Guidelines

### Security Standards
- **Input Validation**: All user inputs validated and sanitized
- **SQL Injection**: Use parameterized queries only
- **XSS Protection**: All outputs properly escaped
- **Authentication**: Strong session management
- **Secrets**: Environment variables only, never in code

### Security Checklist
- [ ] No secrets in code or logs
- [ ] SQL queries use parameters
- [ ] User inputs validated
- [ ] Error messages don't leak information
- [ ] Dependencies regularly updated
- [ ] Security headers configured

```python
# Good: Parameterized query
def get_articles_by_feed(feed_id: int, limit: int = 50) -> List[Item]:
    """Safely query articles by feed ID."""
    return session.query(Item)\
        .filter(Item.feed_id == feed_id)\
        .limit(limit)\
        .all()

# Bad: SQL injection risk
def get_articles_by_feed_bad(feed_id: str) -> List[Item]:
    """DANGEROUS: SQL injection vulnerability."""
    query = f"SELECT * FROM items WHERE feed_id = {feed_id}"
    return session.execute(text(query)).fetchall()
```

---

## 🐛 Bug Reporting

### Bug Report Template
```markdown
**Bug Description**
A clear and concise description of what the bug is.

**To Reproduce**
Steps to reproduce the behavior:
1. Go to '...'
2. Click on '....'
3. Scroll down to '....'
4. See error

**Expected Behavior**
A clear and concise description of what you expected to happen.

**Screenshots**
If applicable, add screenshots to help explain your problem.

**Environment:**
 - OS: [e.g. Ubuntu 20.04]
 - Python Version: [e.g. 3.11.5]
 - Database Version: [e.g. PostgreSQL 14.9]
 - News MCP Version: [e.g. v2.1.0]

**Additional Context**
Add any other context about the problem here.

**Logs**
```
Paste relevant log output here
```
```

---

## 🛠️ Development Tools

### Recommended IDE Setup

#### Visual Studio Code
Install these extensions:
- **Python** - Microsoft Python support
- **Python Type Hint** - Type hint support
- **SQLAlchemy** - Database model support
- **GitLens** - Enhanced Git integration
- **Docker** - Container support

**settings.json:**
```json
{
    "python.defaultInterpreterPath": "./venv/bin/python",
    "python.formatting.provider": "black",
    "python.linting.enabled": true,
    "python.linting.flake8Enabled": true,
    "python.linting.mypyEnabled": true,
    "python.testing.pytestEnabled": true,
    "python.testing.pytestArgs": ["tests/"],
    "files.exclude": {
        "**/__pycache__": true,
        "**/*.pyc": true
    }
}
```

### Development Commands
```bash
# Pre-commit setup (recommended)
pip install pre-commit
pre-commit install

# Code formatting
make format  # or: black app/ tests/ && isort app/ tests/

# Type checking
make typecheck  # or: mypy app/

# Linting
make lint  # or: flake8 app/ tests/

# Security scanning
make security  # or: bandit -r app/

# Test suite
make test  # or: pytest tests/ -v --cov=app

# Database operations
make db-upgrade  # or: alembic upgrade head
make db-downgrade  # or: alembic downgrade -1

# Start services
make dev  # Start all development services
make start-web  # Web server only
make start-worker  # Background worker only
```

---

## 🤝 Community Guidelines

### Code of Conduct

We are committed to providing a welcoming and inspiring community for all. Our Code of Conduct applies to all interactions:

#### Our Standards
- **Be respectful**: Treat everyone with respect and kindness
- **Be inclusive**: Welcome people of all backgrounds and experience levels
- **Be constructive**: Provide helpful feedback and suggestions
- **Be professional**: Maintain professional conduct in all interactions

#### Unacceptable Behavior
- Harassment or discrimination of any kind
- Offensive or inappropriate language
- Personal attacks or insults
- Spam or promotional content
- Sharing private information without consent

### Getting Help

#### Resources
1. **Documentation**
   - [README.md](./README.md) - Project overview
   - [API Documentation](./docs/API_DOCUMENTATION.md) - API reference
   - [Database Schema](./docs/DATABASE_SCHEMA.md) - Database documentation

2. **Community**
   - GitHub Issues - Bug reports and feature requests
   - GitHub Discussions - Questions and community chat
   - Pull Requests - Code contributions and reviews

3. **Support Channels**
   - Create an issue for bugs or feature requests
   - Use discussions for questions and help
   - Tag maintainers for urgent issues (@maintainer-username)

### Recognition

Contributors are recognized through:
- **Contributors Page**: Listed in CONTRIBUTORS.md
- **Release Notes**: Significant contributions highlighted
- **GitHub Profile**: Contribution graphs and achievement badges
- **Community Mentions**: Shout-outs in project communications

---

## 📚 Learning Resources

### Technology Stack
- **FastAPI**: [Official Documentation](https://fastapi.tiangolo.com/)
- **SQLAlchemy**: [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- **PostgreSQL**: [PostgreSQL Manual](https://www.postgresql.org/docs/)
- **Alembic**: [Alembic Documentation](https://alembic.sqlalchemy.org/)
- **HTMX**: [HTMX Documentation](https://htmx.org/docs/)

### Python Development
- **Type Hints**: [PEP 484](https://www.python.org/dev/peps/pep-0484/)
- **Async Programming**: [Python Async Guide](https://realpython.com/async-io-python/)
- **Testing**: [pytest Documentation](https://docs.pytest.org/)
- **Code Style**: [PEP 8](https://www.python.org/dev/peps/pep-0008/)

### RSS and Web Feeds
- **RSS Specification**: [RSS 2.0](https://cyber.harvard.edu/rss/rss.html)
- **Atom Specification**: [RFC 4287](https://tools.ietf.org/html/rfc4287)
- **Feed Processing**: [feedparser Documentation](https://feedparser.readthedocs.io/)

---

## 🎯 Project Roadmap

### Current Focus (v3.0.x)
- **Repository Pattern Migration**: Modernize data access layer
- **Performance Optimization**: Improve query performance and caching
- **Analysis Enhancement**: Advanced AI analysis features
- **UI/UX Improvements**: Better user interface and experience

### Upcoming Features (v3.1.x)
- **Multi-user Support**: User authentication and permissions
- **Advanced Analytics**: Detailed metrics and reporting
- **API Expansion**: Additional REST and GraphQL endpoints
- **Cloud Deployment**: Kubernetes and container orchestration

### Long-term Goals (v4.0+)
- **Machine Learning**: Content classification and recommendation
- **Real-time Processing**: WebSocket and streaming support
- **Plugin System**: Extensible architecture for custom processors
- **Enterprise Features**: SSO, audit logging, compliance tools

---

**Thank you for contributing to News MCP!**

Your contributions help make enterprise RSS management and AI analysis accessible to everyone. Together, we're building the future of intelligent content processing.

---

**Last Updated**: 2025-09-24
**Version**: v4.0.0
**Contributors**: See [CONTRIBUTORS.md](./CONTRIBUTORS.md)