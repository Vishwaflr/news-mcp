import re
from typing import Optional, Dict, Any, List
from datetime import datetime
from .base import ProcessedContent, ContentItem

class ContentValidator:
    """Validates processed content before database insertion"""

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.min_title_length = self.config.get("min_title_length", 5)
        self.max_title_length = self.config.get("max_title_length", 300)
        self.min_description_length = self.config.get("min_description_length", 10)
        self.max_description_length = self.config.get("max_description_length", 1000)
        self.required_fields = self.config.get("required_fields", ["title"])
        self.allowed_html_tags = self.config.get("allowed_html_tags", ["p", "br", "strong", "em", "a"])

    def validate(self, content: ProcessedContent) -> Dict[str, Any]:
        """Validate processed content and return validation result"""
        result = {
            "is_valid": True,
            "errors": [],
            "warnings": [],
            "quality_adjustments": {}
        }

        # Check required fields
        self._validate_required_fields(content, result)

        # Validate title
        self._validate_title(content, result)

        # Validate description
        self._validate_description(content, result)

        # Validate author
        self._validate_author(content, result)

        # Validate link
        self._validate_link(content, result)

        # Check for suspicious patterns
        self._check_suspicious_patterns(content, result)

        return result

    def _validate_required_fields(self, content: ProcessedContent, result: Dict[str, Any]):
        """Check that all required fields are present"""
        for field in self.required_fields:
            value = getattr(content, field, None)
            if not value or (isinstance(value, str) and not value.strip()):
                result["errors"].append(f"Required field '{field}' is missing or empty")
                result["is_valid"] = False

    def _validate_title(self, content: ProcessedContent, result: Dict[str, Any]):
        """Validate title field"""
        if not content.title:
            return

        title = content.title.strip()

        # Length validation
        if len(title) < self.min_title_length:
            result["errors"].append(f"Title too short: {len(title)} chars (min: {self.min_title_length})")
            result["is_valid"] = False
        elif len(title) > self.max_title_length:
            result["warnings"].append(f"Title very long: {len(title)} chars (max: {self.max_title_length})")
            result["quality_adjustments"]["long_title"] = -0.1

        # Check for HTML remnants
        if re.search(r'<[^>]+>', title):
            result["warnings"].append("Title contains HTML tags")
            result["quality_adjustments"]["html_in_title"] = -0.2

        # Check for suspicious patterns
        if re.search(r'(click here|read more|continue reading)$', title, re.IGNORECASE):
            result["warnings"].append("Title ends with clickbait phrase")
            result["quality_adjustments"]["clickbait"] = -0.15

        # Check for encoding issues
        if '�' in title or re.search(r'&[a-z]+;', title):
            result["warnings"].append("Title may have encoding issues")
            result["quality_adjustments"]["encoding_issues"] = -0.1

    def _validate_description(self, content: ProcessedContent, result: Dict[str, Any]):
        """Validate description field"""
        if not content.description:
            result["warnings"].append("Description is missing")
            result["quality_adjustments"]["no_description"] = -0.2
            return

        desc = content.description.strip()

        # Length validation
        if len(desc) < self.min_description_length:
            result["warnings"].append(f"Description very short: {len(desc)} chars")
            result["quality_adjustments"]["short_description"] = -0.1
        elif len(desc) > self.max_description_length:
            result["warnings"].append(f"Description very long: {len(desc)} chars")
            result["quality_adjustments"]["long_description"] = -0.05

        # Check HTML content
        html_tags = re.findall(r'<([^/>]+)>', desc)
        if html_tags:
            disallowed_tags = [tag for tag in html_tags if tag.split()[0].lower() not in self.allowed_html_tags]
            if disallowed_tags:
                result["warnings"].append(f"Description contains disallowed HTML tags: {disallowed_tags}")
                result["quality_adjustments"]["disallowed_html"] = -0.1

        # Check for duplicate content
        if content.title and content.title.strip().lower() == desc.lower():
            result["warnings"].append("Description is identical to title")
            result["quality_adjustments"]["duplicate_content"] = -0.2

    def _validate_author(self, content: ProcessedContent, result: Dict[str, Any]):
        """Validate author field"""
        if not content.author:
            return

        author = content.author.strip()

        # Check for suspicious author patterns
        if re.search(r'(admin|anonymous|unknown|no author)$', author, re.IGNORECASE):
            result["warnings"].append("Author appears to be placeholder text")
            result["quality_adjustments"]["placeholder_author"] = -0.05

        # Check for email addresses (might be leftover from processing)
        if '@' in author and re.search(r'\S+@\S+\.\S+', author):
            result["warnings"].append("Author field contains email address")
            result["quality_adjustments"]["email_in_author"] = -0.05

    def _validate_link(self, content: ProcessedContent, result: Dict[str, Any]):
        """Validate link field"""
        if not content.link:
            result["warnings"].append("Link is missing")
            result["quality_adjustments"]["no_link"] = -0.1
            return

        link = content.link.strip()

        # Basic URL validation
        if not re.match(r'https?://\S+', link):
            result["errors"].append("Link is not a valid HTTP(S) URL")
            result["is_valid"] = False

        # Check for suspicious domains
        suspicious_domains = ['bit.ly', 'tinyurl.com', 'goo.gl', 't.co']
        for domain in suspicious_domains:
            if domain in link:
                result["warnings"].append(f"Link uses URL shortener: {domain}")
                result["quality_adjustments"]["url_shortener"] = -0.05
                break

    def _check_suspicious_patterns(self, content: ProcessedContent, result: Dict[str, Any]):
        """Check for suspicious content patterns"""

        # Check if content looks like spam
        spam_indicators = ['buy now', 'click here', 'limited time', 'act now', 'free money']
        text_to_check = f"{content.title or ''} {content.description or ''}".lower()

        spam_count = sum(1 for indicator in spam_indicators if indicator in text_to_check)
        if spam_count >= 2:
            result["warnings"].append(f"Content contains {spam_count} spam indicators")
            result["quality_adjustments"]["spam_indicators"] = -0.3

        # Check for very short or incomplete content
        total_text = len(f"{content.title or ''} {content.description or ''}")
        if total_text < 50:
            result["warnings"].append("Total content is very short")
            result["quality_adjustments"]["minimal_content"] = -0.2

    def adjust_quality_score(self, original_score: float, validation_result: Dict[str, Any]) -> float:
        """Adjust quality score based on validation results"""
        adjusted_score = original_score

        for adjustment_type, adjustment in validation_result.get("quality_adjustments", {}).items():
            adjusted_score += adjustment

        # Ensure score stays within bounds
        return max(0.0, min(1.0, adjusted_score))

class ProcessorConfigValidator:
    """Validates processor configuration before applying"""

    VALID_CONFIG_KEYS = {
        'universal': {
            'enable_html_decode', 'enable_whitespace_cleanup', 'enable_title_cleanup',
            'enable_description_cleanup', 'max_description_length'
        },
        'heise': {
            'enable_html_decode', 'enable_whitespace_cleanup', 'enable_title_cleanup',
            'enable_description_cleanup', 'max_description_length', 'remove_prefixes'
        },
        'cointelegraph': {
            'enable_html_decode', 'enable_whitespace_cleanup', 'enable_title_cleanup',
            'enable_description_cleanup', 'max_description_length'
        }
    }

    @classmethod
    def validate_config(cls, processor_type: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate processor configuration"""
        result = {
            "is_valid": True,
            "errors": [],
            "warnings": []
        }

        if processor_type not in cls.VALID_CONFIG_KEYS:
            result["errors"].append(f"Unknown processor type: {processor_type}")
            result["is_valid"] = False
            return result

        valid_keys = cls.VALID_CONFIG_KEYS[processor_type]

        # Check for unknown keys
        for key in config.keys():
            if key not in valid_keys:
                result["warnings"].append(f"Unknown config key '{key}' for processor '{processor_type}'")

        # Validate specific config values
        cls._validate_config_values(config, result)

        return result

    @classmethod
    def _validate_config_values(cls, config: Dict[str, Any], result: Dict[str, Any]):
        """Validate specific configuration values"""

        # Validate boolean flags
        bool_keys = ['enable_html_decode', 'enable_whitespace_cleanup',
                    'enable_title_cleanup', 'enable_description_cleanup']
        for key in bool_keys:
            if key in config and not isinstance(config[key], bool):
                result["errors"].append(f"Config key '{key}' must be boolean, got {type(config[key])}")
                result["is_valid"] = False

        # Validate max_description_length
        if 'max_description_length' in config:
            value = config['max_description_length']
            if not isinstance(value, int) or value <= 0:
                result["errors"].append("max_description_length must be a positive integer")
                result["is_valid"] = False
            elif value > 5000:
                result["warnings"].append("max_description_length is very large (>5000)")

        # Validate remove_prefixes for Heise processor
        if 'remove_prefixes' in config:
            prefixes = config['remove_prefixes']
            if not isinstance(prefixes, list):
                result["errors"].append("remove_prefixes must be a list")
                result["is_valid"] = False
            else:
                for prefix in prefixes:
                    if not isinstance(prefix, str):
                        result["errors"].append("All prefixes must be strings")
                        result["is_valid"] = False
                        break