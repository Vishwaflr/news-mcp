# Architecture - News MCP System Design

Comprehensive overview of the News MCP system architecture, design patterns, and technical implementation.

---

## 🏗️ High-Level Architecture

The News MCP System is a modular, scalable platform for RSS feed aggregation with integrated AI analysis:

```
┌─────────────────────────────────────────────────────────┐
│  External Services                                       │
│  • RSS Feeds  • OpenAI API  • Web Browser               │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│  Load Balancer (Nginx/Traefik)                         │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│  Application Layer                                       │
│  ┌──────────┬──────────┬──────────┬──────────┐        │
│  │ FastAPI  │ Analysis │ Feed     │ Auto-    │        │
│  │ Web      │ Worker   │ Scheduler│ Analysis │        │
│  │ Server   │          │          │ System   │        │
│  └──────────┴──────────┴──────────┴──────────┘        │
│  ┌──────────┐                                          │
│  │ MCP      │ (Model Context Protocol Server)         │
│  │ Server   │                                          │
│  └──────────┘                                          │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│  Data Layer                                             │
│  ┌────────────┬────────────┬────────────┐             │
│  │ PostgreSQL │ Redis      │ File       │             │
│  │ Database   │ Cache      │ System     │             │
│  └────────────┴────────────┴────────────┘             │
└─────────────────────────────────────────────────────────┘
```

---

## 📦 System Components

### 1. FastAPI Web Server

**Port:** 8000 (configurable)

**Responsibilities:**
- 172+ REST API endpoints
- 11 web dashboards (HTMX)
- Request/response handling
- Authentication & authorization
- Rate limiting
- Static file serving

**Technical Stack:**
- FastAPI 0.104+
- Uvicorn ASGI server
- Pydantic validation
- SQLModel ORM
- HTMX + Alpine.js (frontend)

**Performance:**
- **Throughput:** 1000+ requests/second (single instance)
- **Latency:** <100ms for standard API calls
- **Memory:** ~200MB baseline
- **Concurrency:** Async/await for I/O operations

---

### 2. MCP Server

**Port:** 8001 (HTTP bridge mode)

**Responsibilities:**
- Model Context Protocol implementation
- 48 native tools for LLM integration
- Claude Desktop integration
- Remote/LAN access support

**Tool Categories:**
- Feed management (10 tools)
- Article search & retrieval (8 tools)
- Analysis operations (12 tools)
- Statistics & metrics (8 tools)
- System health (6 tools)
- Database queries (4 tools)

**Architecture:**
- HTTP REST endpoint bridge
- JSON-RPC protocol
- Stateless operation
- Direct database access

**[Complete MCP Documentation →](MCP-Integration)**

---

### 3. Analysis Worker

**Responsibilities:**
- AI-powered article analysis
- Queue processing
- Rate limiting for OpenAI API
- Batch processing
- Error handling & retry logic

**Processing Flow:**
```
1. Fetch next item from queue
2. Rate limiting check (OpenAI limits)
3. AI analysis (GPT-3.5/GPT-4)
4. Store results to database
5. Update metrics & progress
```

**Scaling:**
- **Horizontal:** Multiple worker instances
- **Vertical:** Configurable concurrency per worker
- **Queue:** PostgreSQL-based job queue
- **Throughput:** 30 items/minute (single worker)

---

### 4. Feed Scheduler

**Responsibilities:**
- Automatic RSS feed fetching
- Schedule management
- Health monitoring
- Content deduplication
- Error tracking

**Scheduling Algorithm:**
- **Base interval:** Configured per feed (default: 60 minutes)
- **Dynamic adjustment:** Based on feed activity
  - High activity → More frequent checks
  - No updates → Less frequent checks
- **Jitter:** Random variance to distribute load

**Current Scale:**
- 37 active feeds
- 35,040+ fetch operations logged
- ~450 new articles per day

---

### 5. Auto-Analysis System (Phase 2 ✅)

**Responsibilities:**
- Automatic AI analysis of new feed items
- Queue management for pending analysis
- Feed-specific configuration
- Rate limiting & backpressure handling

**Architecture:**
```
Feed Fetch → New Items Detected
     ↓
Check Auto-Analysis Config (per feed)
     ↓
Queue Items → Pending Analysis Table
     ↓
Worker Pickup → Process with Rate Limits
     ↓
Store Results → Update Statistics
```

**Configuration:**
- Per-feed enable/disable toggle
- Priority levels (1-10)
- Queue size limits
- Retry policies

**Current Status:**
- 9 feeds with auto-analysis enabled
- 100% rollout phase completed
- 20+ items/minute throughput

**[Auto-Analysis Guide →](Feature-Auto-Analysis)**

---

### 6. Database Layer (PostgreSQL)

**Schema Design:**
- **30 tables** in 3NF normalization
- **54,000+ total rows** across all tables
- **Indexes:** Query-optimized composite indexes
- **Partitioning:** Time-based for large tables

**Key Tables:**

| Table | Rows | Purpose |
|-------|------|---------|
| `feeds` | 37 | RSS feed configuration |
| `items` | 10,285 | News articles |
| `item_analysis` | 2,866 | AI analysis results |
| `analysis_runs` | 49 | Analysis job tracking |
| `fetch_log` | 35,040 | Feed fetch history |
| `feed_health` | 37 | Health monitoring |
| `sources` | 38 | News sources |
| `categories` | 8 | Content categories |

**Performance Optimizations:**
- Composite indexes for common queries
- Partial indexes for filtered queries
- Connection pooling (20 base + 30 overflow)
- Query result caching

**[Database Schema Details →](Database-Schema)**

---

## 🔄 Data Flow Patterns

### 1. Content Ingestion Flow

```
RSS Feed
  ↓
Scheduler Fetch (scheduled interval)
  ↓
Parse RSS XML → Extract Items
  ↓
Deduplication Check (by URL/GUID)
  ↓
Store New Items → Database
  ↓
Trigger Auto-Analysis (if enabled)
  ↓
Queue Item → Pending Analysis
  ↓
Worker Processes → OpenAI API
  ↓
Store Analysis Results → Database
  ↓
Update Statistics & Metrics
```

**Typical Timeline:**
- Feed fetch: 0.5-2 seconds
- Item parsing: <100ms per item
- Database insert: <50ms per item
- Analysis queuing: <10ms per item
- AI analysis: 2-5 seconds per item

---

### 2. Analysis Processing Flow

**State Machine:**
```
[Queued] → Worker picks up → [Running]
   ↓
[Running] → Success → [Completed]
   ↓
[Running] → Error → [Failed] → Retry → [Queued]
   ↓
[Running] → User cancels → [Cancelled]
```

**Error Handling:**
- Automatic retry with exponential backoff
- Maximum 3 retry attempts
- Dead letter queue for persistent failures
- Detailed error logging with stack traces

---

### 3. Web Request Flow

```
Client Request
  ↓
Nginx Load Balancer (SSL termination)
  ↓
FastAPI Router (path matching)
  ↓
Route Handler (validation)
  ↓
Service Layer (business logic)
  ↓
Repository (data access)
  ↓
Database (PostgreSQL)
  ↓
Response Serialization (Pydantic)
  ↓
Return to Client
```

**Middleware Stack:**
1. CORS middleware (cross-origin support)
2. GZip compression (>1KB responses)
3. Request logging (structured logs)
4. Error handling (exception mapping)
5. Metrics collection (Prometheus-compatible)

---

## 🎯 Design Patterns

### 1. Repository Pattern

**Purpose:** Clean separation between data access and business logic

```python
# Repository Layer
class FeedRepository:
    async def get_active_feeds(self) -> List[Feed]:
        statement = select(Feed).where(Feed.status == "active")
        result = await self.session.execute(statement)
        return result.scalars().all()

# Service Layer
class FeedService:
    def __init__(self, repo: FeedRepository):
        self.repo = repo

    async def get_feeds_needing_fetch(self) -> List[Feed]:
        feeds = await self.repo.get_active_feeds()
        return [f for f in feeds if self.should_fetch(f)]
```

**Benefits:**
- Testable business logic (mock repository)
- Centralized data access
- Type-safe queries

---

### 2. Service Layer Pattern

**Purpose:** Orchestrate business operations across repositories

```python
class AnalysisService:
    def __init__(
        self,
        run_repo: AnalysisRunRepository,
        item_repo: ItemRepository,
        ai_client: OpenAIClient
    ):
        self.run_repo = run_repo
        self.item_repo = item_repo
        self.ai_client = ai_client

    async def start_analysis_run(self, config: RunConfig) -> int:
        # 1. Validate configuration
        # 2. Select target items
        # 3. Create analysis run
        # 4. Queue items for processing
        # 5. Notify workers
        pass
```

---

### 3. Queue Pattern

**Purpose:** Decouple producers and consumers for async processing

```python
# Producer (API)
async def trigger_analysis(run_config: RunConfig):
    run_id = await analysis_service.create_run(run_config)
    await queue.enqueue(run_id)
    return {"run_id": run_id, "status": "queued"}

# Consumer (Worker)
async def process_queue():
    while True:
        run_id = await queue.dequeue()
        await process_analysis_run(run_id)
```

---

### 4. Feature Flag Pattern

**Purpose:** Gradual rollout and A/B testing

```python
class FeatureFlags:
    async def is_enabled(self, feature: str, feed_id: int) -> bool:
        flag = await self.get_flag(feature)

        if flag.rollout_percentage == 100:
            return True

        # Consistent hashing for stable behavior
        hash_value = hash(f"{feature}:{feed_id}") % 100
        return hash_value < flag.rollout_percentage
```

**[Feature Flags Guide →](Feature-Flags)**

---

## 📈 Scalability Strategy

### Horizontal Scaling

**Web Server:**
- Stateless design (no local state)
- Load balancer distribution (Nginx)
- Docker/Kubernetes deployment
- Target: 3-5 instances

**Analysis Worker:**
- Independent worker instances
- Database-backed queue coordination
- Auto-scaling based on queue size
- Target: 2-4 instances

**Database:**
- Read replicas for analytics
- Primary for writes
- Connection pooling per instance
- Target: 1 primary + 2 replicas

---

### Vertical Scaling

**Resource Optimization:**
- Database connection pooling (20 base + 30 overflow)
- Async I/O for external APIs
- Streaming responses for large datasets
- Memory-efficient batch processing

**Database Optimization:**
- Query optimization (composite indexes)
- Materialized views for analytics
- Partitioning for large tables (fetch_log)
- Regular VACUUM operations

---

### Caching Strategy

**Multi-Level Caching:**

**L1: In-Memory (Python LRU)**
- Feed configurations
- Category/source lookups
- Template definitions
- TTL: Application lifetime

**L2: Redis (Optional)**
- Dashboard statistics
- API response caching
- Session data
- TTL: 5-15 minutes

**L3: Database Query Optimization**
- Optimized queries
- Materialized views
- Index-only scans

---

## 🔒 Security Architecture

### Network Security

```
Internet
  ↓
WAF (Web Application Firewall)
  ↓
Load Balancer (SSL Termination)
  ↓
Web Servers (Application Network)
  ↓
Database (Data Network - Isolated)
```

**Security Layers:**
- SSL/TLS encryption (Let's Encrypt)
- Network segmentation (VPC/private networks)
- Firewall rules (iptables/security groups)
- Rate limiting (per-IP limits)

---

### Application Security

**Input Validation:**
- Pydantic models for all requests
- Type checking & coercion
- Length limits & regex patterns
- SQL injection prevention (ORM)

**Data Protection:**
- Environment variables for secrets
- No hardcoded credentials
- API key encryption at rest
- Secure password hashing (bcrypt)

**CORS Configuration:**
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Restrict in production
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)
```

---

## 📊 Monitoring & Observability

### Health Checks

**Multi-Level Health:**
```http
GET /api/health/
```

**Response:**
```json
{
  "status": "healthy",
  "checks": {
    "database": "healthy",
    "openai_api": "healthy",
    "worker_queue": "healthy",
    "disk_space": "healthy"
  },
  "timestamp": "2025-10-01T12:00:00Z"
}
```

**Health States:**
- `healthy` - All systems operational
- `degraded` - Partial functionality
- `unhealthy` - Critical failure

---

### Structured Logging

**Log Format (JSON):**
```json
{
  "timestamp": "2025-10-01T12:34:56.789Z",
  "level": "INFO",
  "logger": "app.services.analysis",
  "message": "Analysis run completed",
  "run_id": 123,
  "items_processed": 45,
  "duration_seconds": 127.5,
  "cost_usd": 0.12
}
```

**Log Levels:**
- `DEBUG` - Development details
- `INFO` - Normal operations
- `WARNING` - Potential issues
- `ERROR` - Errors with recovery
- `CRITICAL` - System failures

---

### Metrics Collection

**Prometheus-Compatible Metrics:**
- `http_requests_total` - Total HTTP requests
- `http_request_duration_seconds` - Request latency
- `analysis_runs_total` - Analysis job counter
- `active_feeds_count` - Current active feeds
- `queue_size` - Pending analysis items

**Dashboard Integration:**
- Grafana dashboards
- Real-time alerting
- Historical trending
- SLA monitoring

---

## 🚀 Performance Characteristics

### Current Metrics (v4.0.0)

| Component | Throughput | Latency | Memory | Storage |
|-----------|------------|---------|---------|----------|
| Web Server | 1000+ req/s | <100ms | 200MB | - |
| Analysis Worker | 30 items/min | 2-5s/item | 500MB | - |
| Feed Scheduler | 37 feeds/hr | <1s/fetch | 100MB | - |
| Database | 10k queries/s | <10ms | 2GB | 50GB+ |
| MCP Server | 100 req/s | <50ms | 150MB | - |

---

### Scaling Targets

**Q1 2026 Targets:**
- 200 active feeds (5.4x growth)
- 2000 articles/day (4.4x growth)
- 100 items/min analysis (3.3x growth)
- <50ms API response time (2x improvement)

**Q4 2026 Targets:**
- 1000 active feeds (27x growth)
- 10,000 articles/day (22x growth)
- 500 items/min analysis (16x growth)
- <30ms API response time (3.3x improvement)

---

## 🗺️ Architecture Evolution

### Current (v4.0.0) - Monolithic with Modular Design
- Single application with clean module separation
- Repository pattern for data access
- Background workers in same codebase
- Suitable for current scale (37 feeds, 11K articles)

### Phase 1 (Q1-Q2 2026) - Database Optimization
- Read replicas for analytics queries
- Connection pool tuning
- Query optimization
- Materialized views

### Phase 2 (Q3-Q4 2026) - Microservices Preparation
- Redis cluster for distributed caching
- Event-driven architecture patterns
- Service interface definitions
- API gateway implementation

### Phase 3 (2027+) - Full Microservices
- Analysis service separation
- Independent scaling per service
- Service mesh (Istio/Linkerd)
- Event streaming (Kafka/RabbitMQ)

---

## 🔗 Related Documentation

- **[API Overview](API-Overview)** - REST API reference
- **[Database Schema](Database-Schema)** - Data model details
- **[MCP Integration](MCP-Integration)** - Model Context Protocol
- **[Deployment](Deployment-Production)** - Production setup
- **[Worker System](Worker-System)** - Background processing

---

## 📚 Technical Stack Summary

**Backend:**
- Python 3.9+
- FastAPI 0.104+
- SQLModel (ORM)
- Pydantic (validation)
- Uvicorn (ASGI)

**Database:**
- PostgreSQL 15+
- Redis (optional cache)

**Frontend:**
- HTMX (progressive enhancement)
- Alpine.js (interactivity)
- Tailwind CSS (styling)

**AI Integration:**
- OpenAI API (GPT-3.5/GPT-4)
- Anthropic Claude (via MCP)

**DevOps:**
- Docker & Docker Compose
- Systemd services
- Nginx (reverse proxy)
- Git version control

---

**Last Updated:** 2025-10-01
**Architecture Version:** 4.0.0
**System Status:** Production Ready
