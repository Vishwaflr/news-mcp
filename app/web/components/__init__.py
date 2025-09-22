"""HTMX Components package for the News MCP application."""

from .base_component import BaseComponent
from .feed_components import router as feed_router
from .item_components import router as item_router
from .processor_components import router as processor_router
from .system_components import router as system_router

__all__ = [
    "BaseComponent",
    "feed_router",
    "item_router",
    "processor_router",
    "system_router"
]