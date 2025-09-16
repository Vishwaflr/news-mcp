import re
import html
from typing import Optional, List
from .base import BaseProcessor, ContentItem, ProcessedContent

class UniversalContentProcessor(BaseProcessor):
    """Universal content processor for basic cleanup operations"""

    def __init__(self, config=None):
        super().__init__(config)
        self.enable_html_decode = self.config.get("enable_html_decode", True)
        self.enable_whitespace_cleanup = self.config.get("enable_whitespace_cleanup", True)
        self.enable_title_cleanup = self.config.get("enable_title_cleanup", True)
        self.enable_description_cleanup = self.config.get("enable_description_cleanup", True)
        self.max_description_length = self.config.get("max_description_length", 500)

    def process(self, item: ContentItem) -> ProcessedContent:
        """Process content with universal cleanup rules"""
        result = ProcessedContent()
        transformations = []

        # Copy basic fields
        result.link = item.link
        result.published = item.published
        result.guid = item.guid
        result.content = item.content

        # Process title
        result.title = self._process_title(item.title, transformations)

        # Process description
        result.description = self._process_description(item.description, transformations)

        # Process author
        result.author = self._process_author(item.author, transformations)

        result.transformations = transformations
        result.quality_score = self._calculate_quality_score(result)

        return result

    def _process_title(self, title: Optional[str], transformations: List[str]) -> Optional[str]:
        """Clean up title field"""
        if not title:
            return None

        processed = title

        if self.enable_html_decode:
            decoded = html.unescape(processed)
            if decoded != processed:
                self._log_transformation(transformations, "html_decode_title")
                processed = decoded

        if self.enable_title_cleanup:
            # Remove extra quotes
            if processed.startswith('"') and processed.endswith('"'):
                processed = processed[1:-1]
                self._log_transformation(transformations, "remove_quotes_title")

            # Clean up whitespace
            if self.enable_whitespace_cleanup:
                cleaned = re.sub(r'\s+', ' ', processed.strip())
                if cleaned != processed:
                    self._log_transformation(transformations, "whitespace_cleanup_title")
                    processed = cleaned

        return processed if processed else None

    def _process_description(self, description: Optional[str], transformations: List[str]) -> Optional[str]:
        """Clean up description field"""
        if not description:
            return None

        processed = description

        if self.enable_html_decode:
            decoded = html.unescape(processed)
            if decoded != processed:
                self._log_transformation(transformations, "html_decode_description")
                processed = decoded

        if self.enable_description_cleanup:
            # Remove HTML tags (basic cleanup)
            html_removed = re.sub(r'<[^>]+>', ' ', processed)
            if html_removed != processed:
                self._log_transformation(transformations, "html_tags_removed_description")
                processed = html_removed

            # Clean up whitespace
            if self.enable_whitespace_cleanup:
                cleaned = re.sub(r'\s+', ' ', processed.strip())
                if cleaned != processed:
                    self._log_transformation(transformations, "whitespace_cleanup_description")
                    processed = cleaned

            # Truncate if too long
            if len(processed) > self.max_description_length:
                processed = processed[:self.max_description_length].rsplit(' ', 1)[0] + '...'
                self._log_transformation(transformations, "truncate_description")

        return processed if processed else None

    def _process_author(self, author: Optional[str], transformations: List[str]) -> Optional[str]:
        """Clean up author field"""
        if not author:
            return None

        processed = author

        if self.enable_html_decode:
            decoded = html.unescape(processed)
            if decoded != processed:
                self._log_transformation(transformations, "html_decode_author")
                processed = decoded

        # Clean up whitespace
        if self.enable_whitespace_cleanup:
            cleaned = re.sub(r'\s+', ' ', processed.strip())
            if cleaned != processed:
                self._log_transformation(transformations, "whitespace_cleanup_author")
                processed = cleaned

        return processed if processed else None

    def _calculate_quality_score(self, content: ProcessedContent) -> float:
        """Calculate a simple quality score based on content completeness"""
        score = 0.0

        if content.title and len(content.title.strip()) > 0:
            score += 0.4

        if content.description and len(content.description.strip()) > 10:
            score += 0.3

        if content.author and len(content.author.strip()) > 0:
            score += 0.1

        if content.link and content.link.startswith(('http://', 'https://')):
            score += 0.2

        return min(score, 1.0)