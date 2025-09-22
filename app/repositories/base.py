"""Base repository classes and interfaces."""

from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any, TypeVar, Generic
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.db.session import DatabaseSession

# Type variables for generic repository
T = TypeVar('T', bound=BaseModel)
CreateT = TypeVar('CreateT', bound=BaseModel)
UpdateT = TypeVar('UpdateT', bound=BaseModel)
FilterT = TypeVar('FilterT', bound=BaseModel)


class RepositoryError(Exception):
    """Base repository exception"""
    pass


class NotFoundError(RepositoryError):
    """Record not found (404)"""
    pass


class ConflictError(RepositoryError):
    """Unique constraint violation (409)"""
    pass


class InvalidFilterError(RepositoryError):
    """Invalid filter parameters (400)"""
    pass


class TimeoutError(RepositoryError):
    """Query timeout (504)"""
    pass


class BaseRepository(ABC, Generic[T, CreateT, UpdateT, FilterT]):
    """
    Abstract base repository with standard CRUD operations.

    Type parameters:
    - T: Response/Entity model
    - CreateT: Creation input model
    - UpdateT: Update input model
    - FilterT: Filter/Query model
    """

    def __init__(self, db_session: DatabaseSession):
        self.db = db_session

    # Abstract methods - must be implemented by subclasses
    @abstractmethod
    async def get_by_id(self, id: int) -> Optional[T]:
        """Get single record by ID"""
        pass

    @abstractmethod
    async def list(self, limit: int = 100, offset: int = 0) -> List[T]:
        """List all records with pagination"""
        pass

    @abstractmethod
    async def query(self, filter_obj: FilterT, limit: int = 100, offset: int = 0) -> List[T]:
        """Query with filters"""
        pass

    @abstractmethod
    async def count(self, filter_obj: Optional[FilterT] = None) -> int:
        """Count records matching filter"""
        pass

    @abstractmethod
    async def insert(self, data: CreateT) -> T:
        """Insert new record"""
        pass

    @abstractmethod
    async def update(self, id: int, data: UpdateT) -> Optional[T]:
        """Update existing record"""
        pass

    @abstractmethod
    async def delete(self, id: int) -> bool:
        """Delete record by ID"""
        pass

    # Optional methods with default implementations
    async def upsert(self, data: CreateT, key_fields: List[str]) -> T:
        """Insert or update based on key fields"""
        # Default implementation - can be overridden for better performance
        raise NotImplementedError("Upsert not implemented for this repository")

    async def exists(self, id: int) -> bool:
        """Check if record exists"""
        return await self.get_by_id(id) is not None

    # Helper methods for SQL execution
    def _execute_query(self, query: str, params: Optional[dict] = None) -> list:
        """Execute read-only query with proper session handling"""
        try:
            return self.db.execute_query(query, params)
        except Exception as e:
            self._handle_db_error(e)

    def _execute_insert(self, query: str, params: Optional[dict] = None):
        """Execute insert/update query with transaction"""
        try:
            return self.db.execute_insert(query, params)
        except Exception as e:
            self._handle_db_error(e)

    def _execute_with_session(self, session: Session, query: str, params: Optional[dict] = None):
        """Execute query within provided session"""
        try:
            return session.execute(text(query), params or {})
        except Exception as e:
            self._handle_db_error(e)

    def _handle_db_error(self, error: Exception):
        """Convert SQLAlchemy errors to repository errors"""
        error_msg = str(error)

        if "timeout" in error_msg.lower():
            raise TimeoutError(f"Query timeout: {error_msg}")
        elif "unique" in error_msg.lower() or "duplicate" in error_msg.lower():
            raise ConflictError(f"Unique constraint violation: {error_msg}")
        elif "not found" in error_msg.lower():
            raise NotFoundError(f"Record not found: {error_msg}")
        else:
            raise RepositoryError(f"Database error: {error_msg}")

    def _build_where_clause(self, filters: dict, params: dict) -> str:
        """Build WHERE clause from filter dictionary"""
        conditions = []

        for field, value in filters.items():
            if value is not None:
                if isinstance(value, list):
                    if value:  # Non-empty list
                        placeholders = [f":_{field}_{i}" for i in range(len(value))]
                        conditions.append(f"{field} IN ({','.join(placeholders)})")
                        for i, v in enumerate(value):
                            params[f"_{field}_{i}"] = v
                elif isinstance(value, str) and field.endswith('_search'):
                    # Full-text search
                    field_name = field.replace('_search', '')
                    conditions.append(f"{field_name} ILIKE :{field}")
                    params[field] = f"%{value}%"
                else:
                    conditions.append(f"{field} = :{field}")
                    params[field] = value

        return " AND ".join(conditions) if conditions else "1=1"

    def _build_order_clause(self, sort_by: str, sort_desc: bool = False) -> str:
        """Build ORDER BY clause"""
        direction = "DESC" if sort_desc else "ASC"
        return f"ORDER BY {sort_by} {direction}"

    def _build_limit_clause(self, limit: int, offset: int = 0) -> str:
        """Build LIMIT/OFFSET clause"""
        return f"LIMIT {limit} OFFSET {offset}"


class PaginatedResponse(BaseModel):
    """Standard paginated response"""
    items: List[Any]
    total_count: Optional[int] = None
    limit: int
    offset: int
    has_more: bool = False


class PaginationParams(BaseModel):
    """Standard pagination parameters"""
    limit: int = 50
    offset: int = 0
    include_total: bool = False

    class Config:
        # Validate limits
        @classmethod
        def __init_subclass__(cls, **kwargs):
            super().__init_subclass__(**kwargs)

        def __post_init__(self):
            if self.limit > 1000:
                self.limit = 1000
            if self.limit < 1:
                self.limit = 1
            if self.offset < 0:
                self.offset = 0