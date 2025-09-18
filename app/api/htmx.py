"""
HTMX Router Aggregator

This module aggregates all HTMX routes from specialized view modules.
Previously this was a single 1279 LOC monster file - now cleanly split into:
- feed_views.py (Feed management HTMX)
- item_views.py (Article/Item HTMX)
- system_views.py (System/Health/Processor HTMX)
"""

from fastapi import APIRouter

# Import all specialized HTMX routers
from app.web.views.feed_views import router as feed_router
from app.web.views.item_views import router as item_router
from app.web.views.system_views import router as system_router

# Create main router that includes all specialized routers
router = APIRouter(prefix="/htmx", tags=["htmx"])

# Include all specialized routers (they already have /htmx prefix)
router.include_router(feed_router, prefix="")
router.include_router(item_router, prefix="")
router.include_router(system_router, prefix="")