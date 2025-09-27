"""
Analysis HTMX endpoints - modular structure
Combines all analysis-related HTMX routers
"""

from fastapi import APIRouter
from .runs import router as runs_router
from .stats import router as stats_router
from .articles import router as articles_router
from .preview import router as preview_router
from .settings import router as settings_router
from .target_selection import router as target_selection_router

router = APIRouter()

router.include_router(runs_router)
router.include_router(stats_router)
router.include_router(articles_router)
router.include_router(preview_router)
router.include_router(settings_router)
router.include_router(target_selection_router)

__all__ = ["router"]