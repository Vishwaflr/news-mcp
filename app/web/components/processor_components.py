"""Processor management HTMX components - Facade."""

from fastapi import APIRouter
from .processor_config_components import router as config_router, ProcessorConfigComponent
from .processor_stats_components import router as stats_router, ProcessorStatsComponent
from .processor_status_components import router as status_router, ProcessorStatusComponent

# Main router that combines all sub-routers
router = APIRouter(tags=["htmx-processors"])

# Include all sub-routers
router.include_router(config_router)
router.include_router(stats_router)
router.include_router(status_router)

# Re-export component classes for backward compatibility
ProcessorComponent = type('ProcessorComponent', (
    ProcessorConfigComponent,
    ProcessorStatsComponent,
    ProcessorStatusComponent
), {})

__all__ = [
    'router',
    'ProcessorComponent',
    'ProcessorConfigComponent',
    'ProcessorStatsComponent',
    'ProcessorStatusComponent'
]