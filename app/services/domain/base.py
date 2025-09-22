"""Base service interfaces and abstractions for the News MCP application."""

from abc import ABC, abstractmethod
from typing import TypeVar, Generic, List, Optional, Dict, Any
from sqlmodel import Session
from pydantic import BaseModel

T = TypeVar('T')
CreateT = TypeVar('CreateT', bound=BaseModel)
UpdateT = TypeVar('UpdateT', bound=BaseModel)


class ServiceResult(Generic[T]):
    """Standard service result wrapper with success/error handling."""

    def __init__(self, success: bool, data: Optional[T] = None, error: Optional[str] = None):
        self.success = success
        self.data = data
        self.error = error

    @classmethod
    def ok(cls, data: T) -> 'ServiceResult[T]':
        return cls(success=True, data=data)

    @classmethod
    def error(cls, error: str) -> 'ServiceResult[T]':
        return cls(success=False, error=error)

    def unwrap(self) -> T:
        """Get data or raise exception if error."""
        if not self.success:
            raise ValueError(self.error)
        return self.data


class BaseService(ABC, Generic[T, CreateT, UpdateT]):
    """Base service class with common CRUD operations."""

    def __init__(self, session: Session):
        self.session = session

    @abstractmethod
    def get_by_id(self, entity_id: int) -> ServiceResult[T]:
        """Get entity by ID."""
        pass

    @abstractmethod
    def list(self, skip: int = 0, limit: int = 100, filters: Optional[Dict[str, Any]] = None) -> ServiceResult[List[T]]:
        """List entities with pagination and filters."""
        pass

    @abstractmethod
    def create(self, create_data: CreateT) -> ServiceResult[T]:
        """Create new entity."""
        pass

    @abstractmethod
    def update(self, entity_id: int, update_data: UpdateT) -> ServiceResult[T]:
        """Update existing entity."""
        pass

    @abstractmethod
    def delete(self, entity_id: int) -> ServiceResult[bool]:
        """Delete entity."""
        pass


class ServiceError(Exception):
    """Base exception for service layer errors."""

    def __init__(self, message: str, code: str = "GENERIC_ERROR"):
        self.message = message
        self.code = code
        super().__init__(message)


class NotFoundError(ServiceError):
    """Entity not found error."""

    def __init__(self, entity_type: str, entity_id: int):
        super().__init__(f"{entity_type} with id {entity_id} not found", "NOT_FOUND")


class ValidationError(ServiceError):
    """Data validation error."""

    def __init__(self, message: str):
        super().__init__(message, "VALIDATION_ERROR")


class BusinessLogicError(ServiceError):
    """Business logic constraint violation."""

    def __init__(self, message: str):
        super().__init__(message, "BUSINESS_LOGIC_ERROR")