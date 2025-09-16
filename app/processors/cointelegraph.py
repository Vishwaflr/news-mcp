import re
from typing import Optional, List
from .universal import UniversalContentProcessor
from .base import ContentItem, ProcessedContent

class CointelegraphProcessor(UniversalContentProcessor):
    """Specialized processor for Cointelegraph feeds"""

    def __init__(self, config=None):
        super().__init__(config)

    def _process_title(self, title: Optional[str], transformations: List[str]) -> Optional[str]:
        """Clean up Cointelegraph-specific title formatting"""
        if not title:
            return None

        # First apply universal cleanup
        processed = super()._process_title(title, transformations)

        if not processed:
            return None

        # Cointelegraph sometimes truncates titles with HTML artifacts
        # Fix common truncation issues where title ends abruptly
        is_truncated = False

        # Check for short titles (likely truncated)
        if len(processed) < 20 and not processed.endswith(('.', '!', '?', ':')):
            is_truncated = True

        # Check for titles that end with incomplete words (common truncation pattern)
        # Look for titles ending with single letters or very short word fragments
        words = processed.split()
        if words and len(words[-1]) <= 2 and not processed.endswith(('.', '!', '?', ':', ')')):
            is_truncated = True

        # Check for specific patterns that indicate truncation
        truncation_patterns = [
            r' \w{1,2}$',  # ends with 1-2 characters
            r' \w+ \w{1,2}$',  # ends with word + 1-2 characters
        ]

        for pattern in truncation_patterns:
            if re.search(pattern, processed):
                is_truncated = True
                break

        if is_truncated:
            self._log_transformation(transformations, "possible_truncated_title")

        return processed

    def _process_description(self, description: Optional[str], transformations: List[str]) -> Optional[str]:
        """Clean up Cointelegraph-specific description formatting"""
        if not description:
            return None

        # Apply universal cleanup first
        processed = super()._process_description(description, transformations)

        if not processed:
            return None

        # Cointelegraph has specific HTML patterns that need cleaning
        # Remove image references and style attributes
        img_pattern_removed = re.sub(r'<p[^>]*style="[^"]*"[^>]*>.*?</p>', '', processed, flags=re.DOTALL)
        if img_pattern_removed != processed:
            self._log_transformation(transformations, "remove_image_paragraphs")
            processed = img_pattern_removed

        # Remove float style attributes that indicate image blocks
        float_removed = re.sub(r'<p[^>]*float:[^>]*>.*?</p>', '', processed, flags=re.DOTALL)
        if float_removed != processed:
            self._log_transformation(transformations, "remove_float_elements")
            processed = float_removed

        # Clean up remaining HTML attributes
        attr_cleaned = re.sub(r'<(\w+)[^>]*>', r'<\1>', processed)
        if attr_cleaned != processed:
            self._log_transformation(transformations, "clean_html_attributes")
            processed = attr_cleaned

        # Remove empty paragraphs
        empty_p_removed = re.sub(r'<p>\s*</p>', '', processed)
        if empty_p_removed != processed:
            self._log_transformation(transformations, "remove_empty_paragraphs")
            processed = empty_p_removed

        return processed.strip() if processed else None

    def _process_author(self, author: Optional[str], transformations: List[str]) -> Optional[str]:
        """Clean up Cointelegraph author formatting"""
        if not author:
            return None

        # Apply universal cleanup first
        processed = super()._process_author(author, transformations)

        if not processed:
            return None

        # Cointelegraph format: "Cointelegraph by [Author Name]"
        if processed.lower().startswith('cointelegraph by '):
            processed = processed[17:]  # Remove "Cointelegraph by "
            self._log_transformation(transformations, "remove_cointelegraph_prefix")

        # Sometimes has extra "by" prefix
        if processed.lower().startswith('by '):
            processed = processed[3:]
            self._log_transformation(transformations, "remove_by_prefix")

        return processed.strip() if processed else None

    def _calculate_quality_score(self, content: ProcessedContent) -> float:
        """Calculate quality score with Cointelegraph-specific adjustments"""
        base_score = super()._calculate_quality_score(content)

        # Check for truncation indicators
        if content.transformations and "possible_truncated_title" in content.transformations:
            # Significantly penalize truncated titles
            base_score *= 0.5

        # Penalize very short titles (likely truncated)
        if content.title and len(content.title) < 20:
            base_score *= 0.7

        # Additional penalty for titles ending with incomplete words
        if content.title:
            words = content.title.split()
            if words and len(words[-1]) <= 2 and not content.title.endswith(('.', '!', '?', ':', ')')):
                base_score *= 0.6

        # Bonus for complete author information
        if content.author and 'cointelegraph' not in content.author.lower():
            base_score += 0.1

        return min(base_score, 1.0)