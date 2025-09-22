# Repository Layer Policy

## Übersicht

Diese Policy definiert einheitliche Konventionen für den Data Access Layer. Ziel ist die schrittweise Ablösung von Raw-SQL durch typisierte, testbare Repository-Interfaces.

## Grundprinzipien

### 1. Single Responsibility
- **Ein Repository pro Aggregat** (Items, Feeds, Analysis, Templates)
- **Nur Datenzugriff** - keine Business Logic
- **SQLAlchemy Core** statt ORM für Stabilität bei JSONB/Joins

### 2. Klare Schnittstellen
- **Pydantic DTOs** an allen API-Grenzen (kein ORM-Leak)
- **Typisierte Filter-Objekte** (QueryObjects)
- **Explizite Limits/Pagination** in allen Read-APIs

### 3. Session Management
- **Zentrale Session Factory** (`app/db/session.py`)
- **Kleine Transaktionen** (max. ein Use-Case)
- **Einheitliche Retry-Policy**

## Standard Repository Interface

Jedes Repository implementiert folgende Methoden:

```python
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from pydantic import BaseModel

class BaseRepository(ABC):
    """Standard Repository Interface"""

    # Read Operations
    @abstractmethod
    async def get_by_id(self, id: int) -> Optional[BaseModel]:
        """Get single record by ID"""

    @abstractmethod
    async def list(self, limit: int = 100, offset: int = 0) -> List[BaseModel]:
        """List all records with pagination"""

    @abstractmethod
    async def query(self, filter_obj: BaseModel, limit: int = 100, offset: int = 0) -> List[BaseModel]:
        """Query with filters"""

    @abstractmethod
    async def count(self, filter_obj: Optional[BaseModel] = None) -> int:
        """Count records matching filter"""

    # Write Operations
    @abstractmethod
    async def insert(self, data: BaseModel) -> BaseModel:
        """Insert new record"""

    @abstractmethod
    async def update(self, id: int, data: BaseModel) -> Optional[BaseModel]:
        """Update existing record"""

    @abstractmethod
    async def upsert(self, data: BaseModel, key_fields: List[str]) -> BaseModel:
        """Insert or update based on key fields"""

    @abstractmethod
    async def delete(self, id: int) -> bool:
        """Delete record by ID"""
```

## Query Objects (Filter-DTOs)

### Namenskonvention
- `{Entity}Query` für Filter (z.B. `ItemQuery`, `FeedQuery`)
- `{Entity}Create` für Insert-DTOs
- `{Entity}Update` für Update-DTOs
- `{Entity}Response` für Output-DTOs

### Beispiel: ItemQuery
```python
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel

class ItemQuery(BaseModel):
    """Filter object for item queries"""
    feed_ids: Optional[List[int]] = None
    from_date: Optional[datetime] = None
    to_date: Optional[datetime] = None
    search: Optional[str] = None  # Full-text search

    # Analysis filters
    sentiment: Optional[str] = None  # "positive", "negative", "neutral"
    impact_min: Optional[float] = None
    urgency_min: Optional[int] = None

    # Sorting
    sort_by: str = "created_at"  # "created_at", "published", "impact_score"
    sort_desc: bool = True
```

## Session & Transaction Handling

### Session Factory
```python
# app/db/session.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from contextlib import contextmanager

class DatabaseSession:
    def __init__(self, database_url: str):
        self.engine = create_engine(database_url)
        self.SessionLocal = sessionmaker(bind=self.engine)

    @contextmanager
    def session(self):
        """Context manager for database sessions"""
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    @contextmanager
    def read_session(self):
        """Read-only session (no commit)"""
        session = self.SessionLocal()
        try:
            yield session
        finally:
            session.close()
```

### Repository Base Class
```python
# app/repositories/base.py
from abc import ABC
from sqlalchemy.orm import Session
from app.db.session import DatabaseSession

class BaseRepository(ABC):
    def __init__(self, db_session: DatabaseSession):
        self.db = db_session

    def _execute_query(self, query, params=None):
        """Execute raw SQL with proper session handling"""
        with self.db.read_session() as session:
            return session.execute(query, params or {}).fetchall()

    def _execute_insert(self, query, params=None):
        """Execute insert/update with transaction"""
        with self.db.session() as session:
            result = session.execute(query, params or {})
            return result.fetchone()
```

## Error Handling

### Standard Exception Classes
```python
# app/repositories/exceptions.py
class RepositoryError(Exception):
    """Base repository exception"""

class NotFoundError(RepositoryError):
    """Record not found (404)"""

class ConflictError(RepositoryError):
    """Unique constraint violation (409)"""

class InvalidFilterError(RepositoryError):
    """Invalid filter parameters (400)"""

class TimeoutError(RepositoryError):
    """Query timeout (504)"""
```

### Error Mapping
```python
# app/api/error_handlers.py
@app.exception_handler(NotFoundError)
async def not_found_handler(request, exc):
    return JSONResponse(status_code=404, content={"error": str(exc)})

@app.exception_handler(ConflictError)
async def conflict_handler(request, exc):
    return JSONResponse(status_code=409, content={"error": str(exc)})
```

## Pagination Standards

### Cursor-Based Pagination (empfohlen)
```python
class PaginatedResponse(BaseModel):
    """Standard paginated response"""
    items: List[Any]
    next_cursor: Optional[str] = None
    has_more: bool = False
    total_count: Optional[int] = None  # Nur bei bedarf (expensive)

class PaginationParams(BaseModel):
    """Standard pagination parameters"""
    cursor: Optional[str] = None
    limit: int = Field(default=50, le=1000)  # Max 1000 items
    include_total: bool = False  # Opt-in für COUNT(*)
```

### Offset-Based Pagination (legacy)
```python
class OffsetPaginationParams(BaseModel):
    """Legacy offset pagination"""
    offset: int = Field(default=0, ge=0)
    limit: int = Field(default=50, le=1000)
```

## Testing Standards

### Repository Tests
```python
# tests/repositories/test_items_repo.py
class TestItemsRepository:
    @pytest.fixture
    def repo(self, test_db_session):
        return ItemsRepository(test_db_session)

    @pytest.fixture
    def sample_items(self, repo):
        """Create test data"""
        return [
            repo.insert(ItemCreate(title="Test 1", ...)),
            repo.insert(ItemCreate(title="Test 2", ...))
        ]

    def test_get_by_id_exists(self, repo, sample_items):
        item = repo.get_by_id(sample_items[0].id)
        assert item is not None
        assert item.title == "Test 1"

    def test_get_by_id_not_found(self, repo):
        item = repo.get_by_id(99999)
        assert item is None

    def test_query_with_filters(self, repo, sample_items):
        query = ItemQuery(search="Test")
        results = repo.query(query, limit=10)
        assert len(results) == 2
```

## Performance Guidelines

### Index Requirements
Jedes Repository dokumentiert benötigte Indizes:

```python
class ItemsRepository(BaseRepository):
    """
    Required indexes:
    - items(feed_id, created_at DESC) -- feed timeline
    - items(published DESC) -- global timeline
    - items(content_hash) -- duplicate detection
    - GIN(search_vector) -- full-text search (if implemented)
    """
```

### Query Optimization
- **Explizite SELECT** - nie `SELECT *`
- **Index Hints** bei kritischen Queries
- **Query Plans** in Tests validieren
- **Timeout-Limits** für alle Queries (30s max)

## Migration Path

### Phase 1: Repository einführen
1. Repository implementieren (parallel zu Raw-SQL)
2. Tests schreiben
3. Ein Endpoint migrieren
4. Ergebnisse vergleichen (Spot-Checks)

### Phase 2: Raw-SQL ersetzen
1. Alle Endpoints auf Repository umstellen
2. Raw-SQL Detector in CI aktivieren
3. Legacy-Code entfernen

### Phase 3: Optimierung
1. Performance-Tests
2. Index-Tuning
3. Snapshot-Tests für HTMX

## DoD Checkliste

Für jeden Repository-Ticket:

- [ ] Repository Interface implementiert
- [ ] Query Objects definiert
- [ ] Error Handling implementiert
- [ ] Unit Tests geschrieben (happy path + edge cases)
- [ ] Mindestens 1 Endpoint migriert
- [ ] Spot-Check: Ergebnisse identisch zu Raw-SQL
- [ ] Performance: Latenz ≤ vorher
- [ ] Dokumentation aktualisiert

## Qualitäts-Gates

### CI Checks
- [ ] Kein Raw-SQL in API/HTMX (außer Whitelist)
- [ ] Repository Tests grün
- [ ] Type-Checking erfolgreich
- [ ] Query-Plan Regression-Tests

### Code Review
- [ ] Session-Handling korrekt
- [ ] DTOs statt ORM-Leak
- [ ] Pagination implementiert
- [ ] Error-Cases abgedeckt

---

**Version:** 1.0
**Gültig ab:** 2025-09-22
**Nächste Review:** Bei Phase 2 Abschluss