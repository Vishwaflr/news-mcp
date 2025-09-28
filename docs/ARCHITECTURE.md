# News MCP System Architecture

## Übersicht

Das News MCP System ist eine modulare, skalierbare Plattform für RSS-Feed-Aggregation mit integrierter KI-Analyse. Die Architektur folgt modernen Microservice-Prinzipien mit klarer Trennung von Verantwortlichkeiten.

## High-Level Architektur

```mermaid
graph TB
    subgraph "External"
        RSS[RSS Feeds]
        OpenAI[OpenAI API]
        User[Web Browser]
    end

    subgraph "Load Balancer"
        LB[Nginx/Traefik]
    end

    subgraph "Application Layer"
        Web[FastAPI Web Server]
        Worker[Analysis Worker]
        Scheduler[Feed Scheduler]
        AutoAnalysis[Auto-Analysis System]
        MCP[MCP Server]
    end

    subgraph "Data Layer"
        DB[(PostgreSQL)]
        Cache[Redis Cache]
        FS[File System]
    end

    User --> LB
    LB --> Web
    RSS --> Scheduler
    Scheduler --> DB
    Scheduler --> AutoAnalysis
    AutoAnalysis --> Worker
    Worker --> OpenAI
    Worker --> DB
    Web --> DB
    Web --> Cache
    MCP --> DB

    style Web fill:#e1f5fe
    style Worker fill:#f3e5f5
    style Scheduler fill:#e8f5e8
    style AutoAnalysis fill:#fce4ec
    style DB fill:#fff3e0
```

## Systemkomponenten

### 1. Web Server (FastAPI)

**Verantwortlichkeiten:**
- HTTP API Endpoints
- Web Interface (HTMX)
- Request/Response Handling
- Authentication & Authorization
- Rate Limiting

**Technische Details:**
```python
# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

app = FastAPI(
    title="News MCP API",
    version="3.1.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Middleware Stack
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(CORSMiddleware, allow_origins=["*"])
```

**Performance Characteristics:**
- **Concurrency**: Async/await für I/O-bound Operations
- **Throughput**: 1000+ requests/second (single instance)
- **Latency**: <100ms für Standard API Calls
- **Memory**: ~200MB baseline + request overhead

### 2. Analysis Worker

**Verantwortlichkeiten:**
- AI-basierte Artikel-Analyse
- Queue-Processing
- Rate Limiting für externe APIs
- Batch Processing

**Architecture Pattern:**
```python
# Worker Processing Flow
class AnalysisWorker:
    async def process_queue(self):
        while True:
            # 1. Fetch next item from queue
            item = await self.queue.get_next()

            # 2. Rate limiting check
            await self.rate_limiter.wait_if_needed()

            # 3. AI Analysis
            result = await self.ai_service.analyze(item)

            # 4. Store results
            await self.db.save_analysis(result)

            # 5. Update metrics
            self.metrics.record_processing(item, result)
```

**Scaling Strategy:**
- **Horizontal**: Multiple worker instances
- **Vertical**: Configurable concurrency per worker
- **Queue**: PostgreSQL-based job queue
- **Backpressure**: Automatic rate limiting

### 3. Feed Scheduler

**Verantwortlichkeiten:**
- RSS Feed Fetching
- Schedule Management
- Health Monitoring
- Content Deduplication

**Scheduling Algorithm:**
```python
class FeedScheduler:
    def calculate_next_fetch(self, feed: Feed) -> datetime:
        """Dynamic scheduling based on feed activity"""

        # Base interval from feed configuration
        base_interval = feed.fetch_interval_minutes

        # Adjust based on update frequency
        recent_items = self.get_recent_items(feed, hours=24)
        if recent_items > 10:
            # High activity - fetch more frequently
            base_interval = max(base_interval * 0.5, 15)
        elif recent_items == 0:
            # No activity - fetch less frequently
            base_interval = min(base_interval * 2, 240)

        # Apply jitter to distribute load
        jitter = random.uniform(0.9, 1.1)

        return datetime.utcnow() + timedelta(
            minutes=base_interval * jitter
        )
```

### 4. Auto-Analysis System (Phase 2)

**Verantwortlichkeiten:**
- Automatische Analyse neuer Feed-Items
- Queue-Management für pending items
- Feed-spezifische Konfiguration
- Rate Limiting & Error Handling

**Architecture Pattern:**
```python
class AutoAnalysisService:
    async def process_new_items(self, feed_id: int, items: List[Item]):
        """Process new items from feed for auto-analysis"""

        # Check if feed has auto-analysis enabled
        feed_config = await self.get_feed_config(feed_id)
        if not feed_config.auto_analysis_enabled:
            return

        # Queue items for processing
        for item in items:
            await self.queue_item_for_analysis(item, priority=5)

    async def queue_item_for_analysis(self, item: Item, priority: int = 5):
        """Add item to pending_auto_analysis queue"""

        pending_analysis = PendingAutoAnalysis(
            item_id=item.id,
            feed_id=item.feed_id,
            priority=priority,
            status="pending"
        )

        self.session.add(pending_analysis)
        await self.session.commit()

class PendingAnalysisProcessor:
    async def process_queue(self):
        """Process pending auto-analysis queue with rate limiting"""

        while True:
            # Get next batch (respect rate limits)
            batch = await self.get_next_batch(size=10)
            if not batch:
                await asyncio.sleep(30)  # No work, wait
                continue

            # Process batch
            for pending_item in batch:
                try:
                    await self.analyze_item(pending_item)
                    await self.mark_completed(pending_item)
                except Exception as e:
                    await self.handle_error(pending_item, e)
```

**Integration Points:**
- **Feed Fetcher**: Triggers auto-analysis for new items
- **Analysis Worker**: Processes queued items
- **Rate Limiter**: Respects OpenAI API limits
- **Web UI**: Management interface via HTMX views

### 5. Database Layer

**Schema Design Principles:**
- **Normalization**: 3NF für Datenintegrität
- **Denormalization**: Selective für Performance
- **Indexing**: Query-optimierte Indizes
- **Partitioning**: Zeit-basiert für große Tabellen

**Key Tables:**
```sql
-- Core Content
feeds (40 rows, 37 aktiv) → RSS Feed Konfiguration
items (11,254 rows) → Nachrichtenartikel
sources (41 rows) → Nachrichtenquellen

-- Analysis System
analysis_runs (75 rows) → AI Analysis Jobs
analysis_run_items (2,981 rows) → Individual Tasks
item_analysis (2,866 rows) → Analysis Results

-- Monitoring
fetch_log (35,040 rows) → Feed Fetch Historie
feed_health (37 rows) → Health Monitoring
```

**Performance Optimizations:**
```sql
-- Composite Indizes für häufige Queries
CREATE INDEX idx_items_feed_published
ON items(feed_id, published DESC);

-- Partial Indizes für filtered queries
CREATE INDEX idx_analysis_runs_active
ON analysis_runs(status, created_at DESC)
WHERE status IN ('pending', 'running');

-- Zeit-basierte Partitionierung
CREATE TABLE fetch_log_y2024 PARTITION OF fetch_log
FOR VALUES FROM ('2024-01-01') TO ('2025-01-01');
```

## Service Communication

### 1. Synchronous Communication

**Web API ↔ Database:**
```python
# Repository Pattern für Data Access
class FeedRepository:
    def __init__(self, session: Session):
        self.session = session

    async def get_active_feeds(self) -> List[Feed]:
        statement = select(Feed).where(
            Feed.status == FeedStatus.ACTIVE
        )
        result = await self.session.execute(statement)
        return result.scalars().all()
```

**Benefits:**
- Einfache Fehlerbehandlung
- Konsistente Transaktionen
- Direct Response Handling

### 2. Asynchronous Communication

**Queue-based Processing:**
```python
# Analysis Job Queue
class AnalysisQueue:
    async def enqueue_run(self, run_config: RunConfig) -> int:
        """Enqueue analysis run for processing"""

        run = AnalysisRun(
            scope_json=run_config.scope,
            params_json=run_config.params,
            status="queued"
        )

        self.session.add(run)
        await self.session.commit()

        # Notify workers
        await self.notify_workers()

        return run.id
```

**Event-driven Updates:**
```python
# Real-time Status Updates via WebSocket/SSE
class RunStatusBroadcast:
    async def notify_run_status_change(self, run_id: int):
        """Broadcast status changes to connected clients"""

        run = await self.get_run(run_id)

        # HTMX Partial Update
        await self.broadcast_htmx_update(
            target="#run-status",
            content=self.render_run_status(run)
        )
```

## Data Flow Architecture

### 1. Content Ingestion Flow

```mermaid
sequenceDiagram
    participant S as Scheduler
    participant RSS as RSS Feed
    participant DB as Database
    participant W as Worker
    participant AI as OpenAI API

    S->>RSS: Fetch Feed
    RSS-->>S: RSS XML
    S->>S: Parse & Extract Items
    S->>DB: Store New Items
    DB-->>S: Stored Item IDs
    S->>W: Trigger Analysis (async)
    W->>AI: Analyze Content
    AI-->>W: Analysis Results
    W->>DB: Store Analysis
```

### 2. Analysis Processing Flow

```mermaid
stateDiagram-v2
    [*] --> Queued
    Queued --> Running: Worker picks up
    Running --> Completed: Success
    Running --> Failed: Error
    Running --> Cancelled: User cancellation
    Failed --> Queued: Retry
    Completed --> [*]
    Cancelled --> [*]

    note right of Running
        Rate limited processing
        Progress tracking
        Error handling
    end note
```

### 3. Web Request Flow

```mermaid
graph LR
    A[Client Request] --> B[Nginx]
    B --> C[FastAPI Router]
    C --> D[Route Handler]
    D --> E[Service Layer]
    E --> F[Repository]
    F --> G[Database]
    G --> F
    F --> E
    E --> D
    D --> H[Response Serialization]
    H --> C
    C --> B
    B --> A
```

## Scalability Patterns

### 1. Horizontal Scaling

**Stateless Services:**
```yaml
# Docker Compose Scaling
version: '3.8'
services:
  web:
    image: news-mcp:latest
    deploy:
      replicas: 3
      resources:
        limits:
          memory: 512M
        reservations:
          memory: 256M

  worker:
    image: news-mcp:latest
    command: python -m app.workers.analysis_worker
    deploy:
      replicas: 2
      resources:
        limits:
          memory: 1G
```

**Load Balancing:**
```nginx
# Nginx Upstream Configuration
upstream news_mcp_backend {
    least_conn;
    server web1:8000 max_fails=3 fail_timeout=30s;
    server web2:8000 max_fails=3 fail_timeout=30s;
    server web3:8000 max_fails=3 fail_timeout=30s;
}

server {
    location / {
        proxy_pass http://news_mcp_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### 2. Vertical Scaling

**Resource Optimization:**
```python
# Database Connection Pooling
from sqlalchemy.pool import QueuePool

engine = create_async_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=20,           # Base connections
    max_overflow=30,        # Additional connections
    pool_recycle=3600,      # Recycle after 1 hour
    pool_pre_ping=True      # Validate connections
)
```

**Memory Management:**
```python
# Streaming Response für große Datasets
@router.get("/api/items/export")
async def export_items():
    def generate_csv():
        yield "id,title,published\n"

        for batch in get_items_batched(batch_size=1000):
            for item in batch:
                yield f"{item.id},{item.title},{item.published}\n"

    return StreamingResponse(
        generate_csv(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=items.csv"}
    )
```

### 3. Caching Strategy

**Multi-Level Caching:**
```python
# L1: In-Memory Cache (FastAPI)
from functools import lru_cache

@lru_cache(maxsize=1000)
def get_feed_config(feed_id: int) -> FeedConfig:
    return load_feed_config(feed_id)

# L2: Redis Cache
class CacheService:
    async def get_or_set(self, key: str, factory, ttl: int = 300):
        # Try Redis first
        cached = await self.redis.get(key)
        if cached:
            return json.loads(cached)

        # Generate value
        value = await factory()

        # Cache for future requests
        await self.redis.setex(
            key, ttl, json.dumps(value, default=str)
        )

        return value

# L3: Database with Optimized Queries
class OptimizedQueries:
    async def get_dashboard_stats(self):
        """Single query for dashboard metrics"""
        query = text("""
            SELECT
                COUNT(DISTINCT f.id) as total_feeds,
                COUNT(DISTINCT i.id) as total_items,
                COUNT(DISTINCT ia.item_id) as analyzed_items,
                COUNT(DISTINCT CASE WHEN ar.status = 'running' THEN ar.id END) as active_runs
            FROM feeds f
            LEFT JOIN items i ON f.id = i.feed_id
            LEFT JOIN item_analysis ia ON i.id = ia.item_id
            LEFT JOIN analysis_runs ar ON ar.status = 'running'
        """)

        result = await self.session.execute(query)
        return result.fetchone()
```

## Security Architecture

### 1. Network Security

```mermaid
graph TB
    Internet[Internet]
    WAF[Web Application Firewall]
    LB[Load Balancer/SSL Termination]
    Web[Web Servers]
    DB[Database]

    Internet --> WAF
    WAF --> LB
    LB --> Web
    Web --> DB

    subgraph "DMZ"
        WAF
        LB
    end

    subgraph "Application Network"
        Web
    end

    subgraph "Data Network"
        DB
    end
```

### 2. Application Security

**Input Validation:**
```python
from pydantic import BaseModel, validator, HttpUrl
from typing import Optional

class FeedCreateRequest(BaseModel):
    title: str
    url: HttpUrl
    description: Optional[str] = None

    @validator('title')
    def validate_title(cls, v):
        if len(v) < 3:
            raise ValueError('Title must be at least 3 characters')
        if len(v) > 255:
            raise ValueError('Title too long')
        return v.strip()

    @validator('url')
    def validate_url(cls, v):
        # Only allow HTTP/HTTPS
        if v.scheme not in ['http', 'https']:
            raise ValueError('Only HTTP/HTTPS URLs allowed')
        return v
```

**SQL Injection Prevention:**
```python
# SQLModel/SQLAlchemy ORM verhindert SQL Injection
from sqlmodel import select

# Sicher - Parametrisierte Queries
async def get_items_by_feed(feed_id: int):
    statement = select(Item).where(Item.feed_id == feed_id)
    return await session.execute(statement)

# Auch bei Raw SQL - Parametrisiert
async def custom_query(feed_id: int):
    query = text("""
        SELECT title, published
        FROM items
        WHERE feed_id = :feed_id
        ORDER BY published DESC
    """)
    return await session.execute(query, {"feed_id": feed_id})
```

### 3. Data Protection

**Environment Variables:**
```bash
# Sichere Konfiguration
DATABASE_URL=postgresql://user:pass@localhost/db
OPENAI_API_KEY=sk-...
SECRET_KEY=...  # 32+ zufällige Zeichen

# Niemals in Code:
# API_KEY = "sk-hardcoded"  # SCHLECHT!
```

**Data Encryption:**
```python
# Sensitive Data Encryption
from cryptography.fernet import Fernet

class SecureConfig:
    def __init__(self):
        self.cipher = Fernet(os.environ['ENCRYPTION_KEY'])

    def encrypt_api_key(self, key: str) -> str:
        return self.cipher.encrypt(key.encode()).decode()

    def decrypt_api_key(self, encrypted_key: str) -> str:
        return self.cipher.decrypt(encrypted_key.encode()).decode()
```

## Monitoring & Observability

### 1. Health Checks

```python
# Multi-level Health Checks
class HealthCheckService:
    async def check_database(self) -> HealthStatus:
        try:
            await self.session.execute(text("SELECT 1"))
            return HealthStatus.HEALTHY
        except Exception as e:
            return HealthStatus.UNHEALTHY

    async def check_external_apis(self) -> HealthStatus:
        try:
            # Test OpenAI API
            response = await openai.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": "test"}],
                max_tokens=1
            )
            return HealthStatus.HEALTHY
        except Exception:
            return HealthStatus.DEGRADED

    async def comprehensive_health_check(self):
        checks = {
            "database": await self.check_database(),
            "openai_api": await self.check_external_apis(),
            "worker_queue": await self.check_worker_queue(),
            "disk_space": await self.check_disk_space()
        }

        overall = HealthStatus.HEALTHY
        if any(status == HealthStatus.UNHEALTHY for status in checks.values()):
            overall = HealthStatus.UNHEALTHY
        elif any(status == HealthStatus.DEGRADED for status in checks.values()):
            overall = HealthStatus.DEGRADED

        return {
            "status": overall,
            "checks": checks,
            "timestamp": datetime.utcnow()
        }
```

### 2. Metrics Collection

```python
# Prometheus Metrics
from prometheus_client import Counter, Histogram, Gauge

# Request Metrics
request_count = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

request_duration = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration'
)

# Business Metrics
analysis_runs_total = Counter(
    'analysis_runs_total',
    'Total analysis runs',
    ['status', 'model']
)

active_feeds = Gauge(
    'active_feeds_count',
    'Number of active feeds'
)

# Middleware für automatische Metriken
@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    start_time = time.time()

    response = await call_next(request)

    # Record metrics
    request_count.labels(
        method=request.method,
        endpoint=request.url.path,
        status=response.status_code
    ).inc()

    request_duration.observe(time.time() - start_time)

    return response
```

### 3. Structured Logging

```python
import structlog

# Structured Logger Setup
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

# Usage
async def process_analysis(run_id: int):
    logger.info(
        "Starting analysis run",
        run_id=run_id,
        worker_id=worker_id,
        queue_size=current_queue_size
    )

    try:
        result = await analyze_items(run_id)

        logger.info(
            "Analysis completed successfully",
            run_id=run_id,
            items_processed=result.processed_count,
            duration_seconds=result.duration,
            cost_usd=result.total_cost
        )

    except Exception as e:
        logger.error(
            "Analysis failed",
            run_id=run_id,
            error=str(e),
            error_type=type(e).__name__
        )
        raise
```

## Performance Characteristics

### Current System Metrics

| Component | Throughput | Latency | Memory | Storage |
|-----------|------------|---------|---------|----------|
| **Web Server** | 1000+ req/s | <100ms | 200MB | - |
| **Analysis Worker** | 30 items/min | 2-5s per item | 500MB | - |
| **Feed Scheduler** | 37 feeds/hour | <1s per fetch | 100MB | - |
| **Database** | 10k queries/s | <10ms | 2GB | 50GB+ |

### Scaling Targets

| Metric | Current (Q3 2025) | Target (Q1 2026) | Target (Q4 2026) |
|--------|---------|-------------------|-----------------|
| **Feeds** | 37 | 200 | 1000 |
| **Articles/day** | 450 | 2000 | 10000 |
| **Analysis throughput** | 30/min | 100/min | 500/min |
| **Auto-Analysis throughput** | 20/min | 150/min | 750/min |
| **API Response time** | 85ms | <50ms | <30ms |
| **Uptime** | 99.9% | 99.95% | 99.99% |

### Optimization Roadmap

1. **Phase 1: Database Optimization**
   - Read Replicas für Analytics
   - Query Performance Tuning
   - Connection Pool Optimization

2. **Phase 2: Caching Layer**
   - Redis Cluster Setup
   - Intelligent Cache Invalidation
   - Edge Caching (CDN)

3. **Phase 3: Microservices Split**
   - Analysis Service separation
   - Event-driven Architecture
   - Service Mesh Implementation

---

**Letzte Aktualisierung:** September 2025
**Architecture Version:** v3.1.0