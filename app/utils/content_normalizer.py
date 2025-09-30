"""
Content Normalization Utilities

Handles HTML entities, encoding issues, URL normalization, and text cleaning
for RSS feed content processing.
"""
import re
import html
import urllib.parse
from typing import Optional, Dict, Any
from urllib.parse import urljoin, urlparse
import unicodedata
from app.core.logging_config import get_logger

logger = get_logger(__name__)

class ContentNormalizer:
    """Comprehensive content normalization for RSS feeds."""

    # Common HTML entities that may not be handled by html.unescape
    EXTENDED_ENTITIES = {
        '&nbsp;': ' ',
        '&mdash;': '—',
        '&ndash;': '–',
        '&hellip;': '…',
        '&lsquo;': ''',
        '&rsquo;': ''',
        '&ldquo;': '"',
        '&rdquo;': '"',
        '&bull;': '•',
        '&middot;': '·',
        '&copy;': '©',
        '&reg;': '®',
        '&trade;': '™',
        '&amp;': '&',  # Handle double-encoded ampersands
    }

    # Tracking parameters to remove from URLs
    TRACKING_PARAMS = [
        'utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content',
        'fbclid', 'gclid', 'igshid', 'ref', 'ref_src', 'source',
        'campaign', 'medium', 'content'
    ]

    @classmethod
    def normalize_text(cls, text: str, options: Dict[str, Any] = None) -> str:
        """
        Normalize text content with configurable options.

        Args:
            text: Raw text content
            options: Normalization options

        Returns:
            Normalized text
        """
        if not text:
            return ""

        options = options or {}
        normalized = text

        # Decode HTML entities
        if options.get('decode_html_entities', True):
            normalized = cls.decode_html_entities(normalized)

        # Fix encoding issues
        if options.get('fix_encoding', True):
            normalized = cls.fix_encoding_issues(normalized)

        # Normalize whitespace
        if options.get('normalize_whitespace', True):
            normalized = cls.normalize_whitespace(normalized)

        # Remove HTML tags
        if options.get('strip_html', False):
            normalized = cls.strip_html_tags(normalized)

        # Fix quotes and dashes
        if options.get('fix_typography', True):
            normalized = cls.fix_typography(normalized)

        # Normalize unicode
        if options.get('normalize_unicode', True):
            normalized = cls.normalize_unicode(normalized)

        return normalized.strip()

    @classmethod
    def decode_html_entities(cls, text: str) -> str:
        """Decode HTML entities in text."""
        # Standard HTML entity decoding
        text = html.unescape(text)

        # Extended entities
        for entity, replacement in cls.EXTENDED_ENTITIES.items():
            text = text.replace(entity, replacement)

        # Numeric entities that might be missed
        text = re.sub(r'&#(\d+);', lambda m: chr(int(m.group(1))), text)
        text = re.sub(r'&#x([0-9a-fA-F]+);', lambda m: chr(int(m.group(1), 16)), text)

        return text

    @classmethod
    def fix_encoding_issues(cls, text: str) -> str:
        """Fix common encoding issues."""
        # Handle Windows-1252 characters that appear in UTF-8
        replacements = {
            '\u0080': '€',  # Euro sign
            '\u0082': '‚',  # Single low-9 quotation mark
            '\u0083': 'ƒ',  # Latin small letter f with hook
            '\u0084': '„',  # Double low-9 quotation mark
            '\u0085': '…',  # Horizontal ellipsis
            '\u0086': '†',  # Dagger
            '\u0087': '‡',  # Double dagger
            '\u0088': 'ˆ',  # Modifier letter circumflex accent
            '\u0089': '‰',  # Per mille sign
            '\u008A': 'Š',  # Latin capital letter S with caron
            '\u008B': '‹',  # Single left-pointing angle quotation mark
            '\u008C': 'Œ',  # Latin capital ligature OE
            '\u008E': 'Ž',  # Latin capital letter Z with caron
            '\u0091': ''',  # Left single quotation mark
            '\u0092': ''',  # Right single quotation mark
            '\u0093': '"',  # Left double quotation mark
            '\u0094': '"',  # Right double quotation mark
            '\u0095': '•',  # Bullet
            '\u0096': '–',  # En dash
            '\u0097': '—',  # Em dash
            '\u0098': '˜',  # Small tilde
            '\u0099': '™',  # Trade mark sign
            '\u009A': 'š',  # Latin small letter s with caron
            '\u009B': '›',  # Single right-pointing angle quotation mark
            '\u009C': 'œ',  # Latin small ligature oe
            '\u009E': 'ž',  # Latin small letter z with caron
            '\u009F': 'Ÿ',  # Latin capital letter Y with diaeresis
        }

        for old, new in replacements.items():
            text = text.replace(old, new)

        return text

    @classmethod
    def normalize_whitespace(cls, text: str) -> str:
        """Normalize whitespace in text."""
        # Replace multiple whitespace with single space
        text = re.sub(r'\s+', ' ', text)
        # Remove leading/trailing whitespace
        text = text.strip()
        # Fix common whitespace around punctuation
        text = re.sub(r'\s+([,.!?;:])', r'\1', text)
        text = re.sub(r'([,.!?;:])\s+', r'\1 ', text)
        return text

    @classmethod
    def strip_html_tags(cls, text: str) -> str:
        """Remove HTML tags from text."""
        # Remove script and style elements completely
        text = re.sub(r'<(script|style)[^>]*>.*?</\1>', '', text, flags=re.DOTALL | re.IGNORECASE)
        # Remove HTML comments
        text = re.sub(r'<!--.*?-->', '', text, flags=re.DOTALL)
        # Remove HTML tags but keep content
        text = re.sub(r'<[^>]+>', '', text)
        return text

    @classmethod
    def fix_typography(cls, text: str) -> str:
        """Fix typography issues."""
        # Fix straight quotes to curly quotes
        text = re.sub(r'"([^"]*)"', r'"\1"', text)
        text = re.sub(r"'([^']*)'", r"'\1'", text)

        # Fix double/triple dashes
        text = text.replace('---', '—')
        text = text.replace('--', '—')

        # Fix ellipsis
        text = text.replace('...', '…')

        # Fix spacing around em/en dashes
        text = re.sub(r'\s*—\s*', ' — ', text)
        text = re.sub(r'\s*–\s*', ' – ', text)

        return text

    @classmethod
    def normalize_unicode(cls, text: str) -> str:
        """Normalize unicode characters."""
        # Normalize to NFC (Canonical Decomposition, followed by Canonical Composition)
        text = unicodedata.normalize('NFC', text)
        return text

    @classmethod
    def normalize_url(cls, url: str, base_url: str = None) -> str:
        """
        Normalize URLs by removing tracking parameters and resolving relative URLs.

        Args:
            url: URL to normalize
            base_url: Base URL for resolving relative URLs

        Returns:
            Normalized absolute URL
        """
        if not url:
            return ""

        try:
            # Resolve relative URLs
            if base_url and not urllib.parse.urlparse(url).netloc:
                url = urljoin(base_url, url)

            # Parse URL
            parsed = urllib.parse.urlparse(url)
            query_params = urllib.parse.parse_qs(parsed.query)

            # Remove tracking parameters
            filtered_params = {
                key: value for key, value in query_params.items()
                if key.lower() not in [p.lower() for p in cls.TRACKING_PARAMS]
            }

            # Rebuild query string
            new_query = urllib.parse.urlencode(filtered_params, doseq=True)

            # Reconstruct URL
            normalized_url = urllib.parse.urlunparse((
                parsed.scheme,
                parsed.netloc,
                parsed.path,
                parsed.params,
                new_query,
                ''  # Remove fragment
            ))

            return normalized_url

        except Exception as e:
            logger.warning(f"Error normalizing URL {url}: {e}")
            return url

    @classmethod
    def extract_text_from_html(cls, html_content: str, max_length: int = None) -> str:
        """
        Extract clean text from HTML content.

        Args:
            html_content: HTML string
            max_length: Maximum length of extracted text

        Returns:
            Clean text content
        """
        if not html_content:
            return ""

        # Remove script and style content
        text = re.sub(r'<(script|style)[^>]*>.*?</\1>', '', html_content, flags=re.DOTALL | re.IGNORECASE)

        # Replace block elements with newlines
        text = re.sub(r'</(div|p|br|h[1-6]|li|td|tr)[^>]*>', '\n', text, flags=re.IGNORECASE)

        # Remove all HTML tags
        text = cls.strip_html_tags(text)

        # Normalize the text
        text = cls.normalize_text(text)

        # Truncate if needed
        if max_length and len(text) > max_length:
            text = text[:max_length].rsplit(' ', 1)[0] + '…'

        return text

    @classmethod
    def normalize_feed_entry(cls, entry: Dict[str, Any], base_url: str = None) -> Dict[str, Any]:
        """
        Normalize all text fields in a feed entry.

        Args:
            entry: Feed entry dictionary
            base_url: Base URL for resolving relative URLs

        Returns:
            Normalized feed entry
        """
        normalized = entry.copy()

        # Text fields to normalize
        text_fields = ['title', 'description', 'content', 'author', 'summary']
        for field in text_fields:
            if field in normalized and normalized[field]:
                if field == 'content':
                    # For content, extract text from HTML
                    normalized[field] = cls.extract_text_from_html(normalized[field], max_length=5000)
                else:
                    # For other fields, just normalize
                    normalized[field] = cls.normalize_text(normalized[field])

        # Normalize URLs
        if 'link' in normalized:
            normalized['link'] = cls.normalize_url(normalized['link'], base_url)

        return normalized

    @classmethod
    def detect_language(cls, text: str) -> Optional[str]:
        """
        Simple language detection based on character patterns.

        Args:
            text: Text to analyze

        Returns:
            ISO language code or None
        """
        if not text or len(text) < 20:
            return None

        # Simple heuristics
        if re.search(r'[äöüßÄÖÜ]', text):
            return 'de'  # German
        elif re.search(r'[àáâãèéêìíîòóôõùúûç]', text):
            return 'fr'  # French
        elif re.search(r'[ñáéíóúü¿¡]', text):
            return 'es'  # Spanish
        elif re.search(r'[àáâãèéêìíîòóôõùúûç]', text):
            return 'pt'  # Portuguese
        else:
            return 'en'  # Default to English

# Test function
# Test code removed - use unit tests in tests/ directory instead