import re
from typing import Optional, List
from .universal import UniversalContentProcessor
from .base import ContentItem, ProcessedContent

class HeiseProcessor(UniversalContentProcessor):
    """Specialized processor for Heise Online feeds"""

    def __init__(self, config=None):
        super().__init__(config)
        self.remove_prefixes = self.config.get("remove_prefixes", [
            "heise-Angebot: ",
            "Anzeige: ",
            "Sponsored: "
        ])

    def _process_title(self, title: Optional[str], transformations: List[str]) -> Optional[str]:
        """Clean up Heise-specific title formatting"""
        if not title:
            return None

        # First apply universal cleanup
        processed = super()._process_title(title, transformations)

        if not processed:
            return None

        # Remove Heise-specific prefixes
        original = processed
        for prefix in self.remove_prefixes:
            if processed.startswith(prefix):
                processed = processed[len(prefix):]
                self._log_transformation(transformations, f"remove_prefix_{prefix.strip().replace(':', '').replace(' ', '_').lower()}")
                break

        # Clean up common Heise patterns
        # Remove "(...)" patterns at the end that are often redundant
        pattern_removed = re.sub(r'\s+\([^)]+\)$', '', processed)
        if pattern_removed != processed and pattern_removed.strip():
            self._log_transformation(transformations, "remove_end_parentheses")
            processed = pattern_removed

        return processed.strip() if processed else None

    def _process_description(self, description: Optional[str], transformations: List[str]) -> Optional[str]:
        """Clean up Heise-specific description formatting"""
        if not description:
            return None

        # Apply universal cleanup first
        processed = super()._process_description(description, transformations)

        if not processed:
            return None

        # Remove common Heise tracking/promotional text
        tracking_patterns = [
            r'\s*\(Bild:.*?\)',
            r'\s*\[.*?Anzeige.*?\]',
            r'\s*Mehr Infos.*?$',
            r'\s*Lesen Sie auch:.*?$'
        ]

        for pattern in tracking_patterns:
            cleaned = re.sub(pattern, '', processed, flags=re.IGNORECASE)
            if cleaned != processed:
                self._log_transformation(transformations, f"remove_heise_pattern")
                processed = cleaned

        return processed.strip() if processed else None

    def _process_author(self, author: Optional[str], transformations: List[str]) -> Optional[str]:
        """Clean up Heise author formatting"""
        if not author:
            return None

        # Apply universal cleanup first
        processed = super()._process_author(author, transformations)

        if not processed:
            return None

        # Heise sometimes has "Von [Author]" format
        if processed.lower().startswith('von '):
            processed = processed[4:]
            self._log_transformation(transformations, "remove_von_prefix")

        # Remove email addresses if present
        email_removed = re.sub(r'\s*\([^@]+@[^)]+\)', '', processed)
        if email_removed != processed:
            self._log_transformation(transformations, "remove_email")
            processed = email_removed

        return processed.strip() if processed else None