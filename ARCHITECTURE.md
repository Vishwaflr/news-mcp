# News-MCP Architecture Documentation

## Overview

News-MCP is an enterprise-ready RSS management and content processing system with AI-powered sentiment analysis. The system follows a modern, modular architecture with clear separation of concerns.

## Architecture Layers

### 1. API Layer (`/app/api/`)

#### Core APIs
- **v1/analysis.py** - Main analysis API (refactored 2025-09-30)
  - Run management endpoints
  - Preview and cost estimation
  - Status tracking and metrics

#### Supporting APIs
- **feeds.py** - Feed CRUD operations
- **items.py** - Article/item management
- **categories.py** - Feed categorization
- **sources.py** - Source management
- **htmx.py** - Server-side rendering for dynamic UI

### 2. Repository Layer (`/app/repositories/`)

The repository layer was refactored from a monolithic 765-line file into focused modules:

#### Analysis Repositories (Refactored 2025-09-30)
- **analysis_run_repo.py** (254 lines)
  - Run lifecycle management
  - Item queueing based on scopes
  - Status and metrics tracking
  - Skip tracking for efficiency

- **analysis_preview_repo.py** (171 lines)
  - Preview generation
  - Cost estimation
  - Scope statistics

- **analysis_preset_repo.py** (98 lines)
  - Preset management
  - Configuration templates

- **analysis_control.py** (98 lines)
  - Facade for backward compatibility
  - Delegates to specialized repositories

### 3. Service Layer (`/app/services/`)

#### Domain Services (`/app/services/domain/`)
- **analysis_service.py** - Business logic for analysis
- **feed_service.py** - Feed management logic
- **job_service.py** - Job queue management

#### Infrastructure Services
- **analysis_orchestrator.py** - Orchestrates analysis runs (with error recovery)
- **analysis_run_manager.py** - Run state management
- **auto_analysis_service.py** - Automatic analysis triggers
- **pending_analysis_processor.py** - Queue processing
- **llm_client.py** - OpenAI integration
- **cost_estimator.py** - Cost calculation
- **error_recovery.py** - Circuit breaker and retry logic (NEW)

### 4. Worker Layer (`/app/worker/`)

- **analysis_worker.py** - Background processing
  - Processes analysis queue
  - Rate limiting
  - Enhanced error recovery with circuit breakers
  - Metrics collection

### 5. Web UI Layer (`/templates/`)

- **analysis_cockpit_v4.html** - Main analysis UI (Alpine.js v3)
- **admin/analysis_manager.html** - Admin dashboard
- HTMX components for progressive enhancement

## Data Flow

### Analysis Run Creation Flow

```
1. User Request → API (v1/analysis)
2. API → AnalysisService (validation)
3. Service → AnalysisRunRepo (create run)
4. Repository → Database (persist)
5. Repository → Queue items
6. Worker → Process queue
7. Worker → LLM Client → OpenAI
8. Worker → Save results
9. UI → Poll status → Update display
```

### Auto-Analysis Flow

```
1. Feed Fetcher → New items
2. Auto-Analysis Service → Detect new items
3. Service → Create pending analysis
4. Processor → Batch items
5. Processor → Create run
6. → (continues as manual flow)
```

## Key Design Decisions

### 1. Repository Pattern
- Type-safe data access
- Clear separation from business logic
- Easy testing and mocking
- Database abstraction

### 2. Static Methods in Repositories
- No instance state needed
- Thread-safe by design
- Simpler dependency management
- Clear transaction boundaries

### 3. Domain Model Separation
- Database models (`/app/models/`)
- Domain models (`/app/domain/`)
- Clean conversion layer
- API response models (Pydantic)

### 4. Scope-Based Filtering
- Flexible item selection
- Support for multiple criteria:
  - By items (specific IDs)
  - By feeds (feed IDs)
  - By categories (category IDs)
  - By time (hours back)
  - Global (all items)

### 5. Progressive Enhancement UI
- Server-side rendering with HTMX
- Client-side interactivity with Alpine.js
- WebSocket for real-time updates
- Dark mode support

## Performance Optimizations

### Database
- Proper indexing on frequently queried columns
- DISTINCT queries to avoid duplicates
- Batch processing for queue items
- Skip tracking to avoid re-analysis

### Processing
- Configurable rate limiting
- Concurrent run limits (5 max)
- Chunk-based processing (10 items default)
- Stale item recovery

### Caching
- Selection cache for preview
- Cost estimation cache
- Feature flag caching

## Configuration

### Environment Variables
- `DATABASE_URL` - PostgreSQL connection
- `OPENAI_API_KEY` - AI integration
- `MAX_CONCURRENT_RUNS` - Processing limit
- `WORKER_CHUNK_SIZE` - Batch size
- `RATE_LIMIT_PER_SECOND` - API throttling

### Feature Flags
- Progressive rollout support
- A/B testing capability
- Automatic fallback on errors
- Shadow comparison mode

## Monitoring & Health

### Health Checks
- Database connectivity
- Worker status
- Queue depth
- Error rates
- Circuit breaker status (NEW)

### Metrics
- Processing rates (items/minute)
- Cost tracking (per run, per model)
- Error rates and types
- Coverage metrics (10m, 60m windows)
- Circuit breaker metrics (NEW)
  - Open/closed/half-open states
  - Failure counts by service
  - Recovery success rates

### Error Recovery (NEW)
- **Circuit Breaker Pattern**
  - Automatic failure detection
  - Service isolation on failures
  - Gradual recovery testing
  - Manual reset capability
- **Retry Strategies**
  - Exponential backoff with jitter
  - Configurable retry attempts
  - Error-type specific recovery
- **Monitoring Endpoints**
  - `/api/v1/health/circuit-breakers` - Status overview
  - `/api/v1/health/error-stats` - Error statistics

## Security

### API Security
- Input validation (Pydantic models)
- SQL injection prevention (SQLModel)
- Rate limiting per endpoint
- Error message sanitization

### Data Protection
- Sensitive data in .env files
- No credentials in code
- Secure database connections
- Audit logging

## Deployment

### Services
1. **Web Server** - FastAPI application
2. **Worker** - Background processor
3. **Scheduler** - Feed fetching
4. **Database** - PostgreSQL

### Scripts
- `./scripts/start-all.sh` - Start all services
- `./scripts/start-worker.sh` - Start worker only
- `./scripts/start-web-server.sh` - Start web only
- `./scripts/status.sh` - Check service status

## Future Roadmap

### Phase 3: Enhanced Features ✅ COMPLETED
- Advanced error recovery ✅
  - Circuit breaker pattern implemented
  - Exponential backoff retry strategies
  - Error classification and targeted recovery
  - Comprehensive monitoring endpoints
- Performance optimizations (In Progress)
- Enhanced monitoring (Partial - circuit breakers done)
- Multi-model support (Planned)

### Phase 4: Scale & Reliability
- Horizontal scaling
- Redis queue backend
- Kubernetes deployment
- Multi-region support

---

*Last Updated: 2025-09-30*
*Architecture Version: 3.1.0-error-recovery*