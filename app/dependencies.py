"""Dependency injection container for services."""

from functools import lru_cache
from fastapi import Depends
from sqlmodel import Session

from app.database import get_session
from app.services.domain.feed_service import FeedService
from app.services.domain.item_service import ItemService
from app.services.domain.processor_service import ProcessorService
from app.services.domain.analysis_service import AnalysisService


# Service factory functions with dependency injection
def get_feed_service(session: Session = Depends(get_session)) -> FeedService:
    """Get FeedService instance with database session."""
    return FeedService(session)


def get_item_service(session: Session = Depends(get_session)) -> ItemService:
    """Get ItemService instance with database session."""
    return ItemService(session)


def get_processor_service(session: Session = Depends(get_session)) -> ProcessorService:
    """Get ProcessorService instance with database session."""
    return ProcessorService(session)


@lru_cache(maxsize=1)
def get_analysis_service() -> AnalysisService:
    """Get AnalysisService instance (stateless, can be cached)."""
    return AnalysisService()


# Alternative: Service container class for more complex scenarios
class ServiceContainer:
    """Service container for complex dependency management."""

    def __init__(self):
        self._services = {}

    def register_service(self, service_type: type, factory_func):
        """Register a service factory function."""
        self._services[service_type] = factory_func

    def get_service(self, service_type: type, **kwargs):
        """Get service instance."""
        if service_type not in self._services:
            raise ValueError(f"Service {service_type} not registered")
        return self._services[service_type](**kwargs)


# Global service container instance (for advanced use cases)
service_container = ServiceContainer()

# Register services
service_container.register_service(FeedService, lambda session: FeedService(session))
service_container.register_service(ItemService, lambda session: ItemService(session))
service_container.register_service(ProcessorService, lambda session: ProcessorService(session))
service_container.register_service(AnalysisService, lambda: AnalysisService())