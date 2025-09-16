import re
from typing import Dict, Any, Optional
from sqlmodel import Session
from ..models import ProcessorType, Feed, FeedProcessorConfig, ProcessorTemplate
from .base import BaseProcessor
from .universal import UniversalContentProcessor
from .heise import HeiseProcessor
from .cointelegraph import CointelegraphProcessor

class ProcessorFactory:
    """Factory for creating content processors"""

    _processors = {
        ProcessorType.UNIVERSAL: UniversalContentProcessor,
        ProcessorType.HEISE: HeiseProcessor,
        ProcessorType.COINTELEGRAPH: CointelegraphProcessor,
    }

    @classmethod
    def create_processor(cls, processor_type: ProcessorType, config: Dict[str, Any] = None) -> BaseProcessor:
        """Create a processor instance"""
        if processor_type not in cls._processors:
            # Fallback to universal processor for unknown types
            processor_type = ProcessorType.UNIVERSAL

        processor_class = cls._processors[processor_type]
        return processor_class(config)

    @classmethod
    def get_processor_for_feed(cls, feed: Feed, session: Session) -> BaseProcessor:
        """Get the appropriate processor for a feed"""

        # Check if feed has specific processor config
        if feed.processor_config and feed.processor_config.is_active:
            return cls.create_processor(
                feed.processor_config.processor_type,
                feed.processor_config.config
            )

        # Try to match against processor templates
        processor_type, config = cls._match_feed_to_template(feed, session)
        if processor_type:
            return cls.create_processor(processor_type, config)

        # Fallback to universal processor
        return cls.create_processor(ProcessorType.UNIVERSAL)

    @classmethod
    def _match_feed_to_template(cls, feed: Feed, session: Session) -> tuple[Optional[ProcessorType], Optional[Dict[str, Any]]]:
        """Match a feed URL against processor templates"""

        # Get all active templates
        templates = session.query(ProcessorTemplate).filter(
            ProcessorTemplate.is_active == True
        ).all()

        for template in templates:
            for pattern in template.patterns:
                try:
                    if re.search(pattern, feed.url, re.IGNORECASE):
                        return template.processor_type, template.config
                except re.error:
                    # Skip invalid regex patterns
                    continue

        return None, None

    @classmethod
    def auto_detect_processor_type(cls, feed_url: str) -> ProcessorType:
        """Auto-detect processor type based on feed URL"""
        url_lower = feed_url.lower()

        if 'heise.de' in url_lower:
            return ProcessorType.HEISE
        elif 'cointelegraph.com' in url_lower:
            return ProcessorType.COINTELEGRAPH
        else:
            return ProcessorType.UNIVERSAL

    @classmethod
    def register_processor(cls, processor_type: ProcessorType, processor_class: type):
        """Register a new processor type"""
        cls._processors[processor_type] = processor_class

    @classmethod
    def get_available_processors(cls) -> Dict[ProcessorType, type]:
        """Get all available processor types"""
        return cls._processors.copy()