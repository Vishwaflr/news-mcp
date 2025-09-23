"""Analysis Control - Main Router

This file has been refactored from a monolithic 752-line file into
smaller, manageable modules for better maintainability.
"""

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

# Import sub-routers
from .analysis_feeds import router as feeds_router
from .analysis_stats import router as stats_router
from .analysis_runs import router as runs_router
from .analysis_presets import router as presets_router
from .analysis_monitoring import router as monitoring_router

router = APIRouter(prefix="/htmx/analysis", tags=["htmx-analysis-control"])

# Include sub-routers
router.include_router(feeds_router)
router.include_router(stats_router)
router.include_router(runs_router)
router.include_router(presets_router)
router.include_router(monitoring_router)


@router.get("/quick-actions", response_class=HTMLResponse)
def get_quick_actions_partial() -> str:
    """Quick actions have been removed - returns empty content"""
    return ""