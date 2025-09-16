from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import time
from datetime import datetime

@dataclass
class ContentItem:
    """Raw content item from RSS feed"""
    title: Optional[str] = None
    description: Optional[str] = None
    content: Optional[str] = None
    author: Optional[str] = None
    link: Optional[str] = None
    published: Optional[datetime] = None
    guid: Optional[str] = None

@dataclass
class ProcessedContent:
    """Processed and cleaned content item"""
    title: Optional[str] = None
    description: Optional[str] = None
    content: Optional[str] = None
    author: Optional[str] = None
    link: Optional[str] = None
    published: Optional[datetime] = None
    guid: Optional[str] = None
    transformations: List[str] = None
    processing_time_ms: int = 0
    quality_score: float = 1.0

    def __post_init__(self):
        if self.transformations is None:
            self.transformations = []

class BaseProcessor(ABC):
    """Base class for all content processors"""

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.processor_name = self.__class__.__name__

    @abstractmethod
    def process(self, item: ContentItem) -> ProcessedContent:
        """Process a content item and return cleaned version"""
        pass

    def _log_transformation(self, transformations: List[str], name: str):
        """Log a transformation that was applied"""
        transformations.append(f"{self.processor_name}.{name}")

    def _measure_time(func):
        """Decorator to measure processing time"""
        def wrapper(self, item: ContentItem) -> ProcessedContent:
            start_time = time.time()
            result = func(self, item)
            result.processing_time_ms = int((time.time() - start_time) * 1000)
            return result
        return wrapper

    @_measure_time
    def process_with_timing(self, item: ContentItem) -> ProcessedContent:
        """Process with automatic timing"""
        return self.process(item)