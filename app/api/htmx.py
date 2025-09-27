"""
HTMX Router Aggregator

This module aggregates all HTMX routes from specialized component modules.
The monolithic htmx_legacy.py (1,368 lines) has been refactored into:
- feed_components.py (Feed management HTMX)
- item_components.py (Article/Item HTMX)
- processor_components.py (Processor management HTMX)
- system_components.py (System/Health HTMX)
"""

from fastapi import APIRouter

# Import all specialized HTMX routers from components
from app.web.components.feed_components import router as feed_router
from app.web.components.item_components import router as item_router
from app.web.components.processor_components import router as processor_router
from app.web.components.system_components import router as system_router

# Create main router that includes all specialized routers
router = APIRouter(tags=["htmx"])

# Include all specialized routers
router.include_router(feed_router, prefix="")
router.include_router(item_router, prefix="")
router.include_router(processor_router, prefix="")
router.include_router(system_router, prefix="")