"""Centralized exception handling system for the News MCP application."""

from typing import Optional, Dict, Any
from enum import Enum
import traceback
from datetime import datetime


class ErrorSeverity(str, Enum):
    """Error severity levels for monitoring and alerting."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(str, Enum):
    """Error categories for classification and handling."""
    VALIDATION = "validation"
    BUSINESS_LOGIC = "business_logic"
    EXTERNAL_SERVICE = "external_service"
    DATABASE = "database"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    RATE_LIMIT = "rate_limit"
    CONFIGURATION = "configuration"
    SYSTEM = "system"


class NewsMCPException(Exception):
    """Base exception class for all News MCP application errors."""

    def __init__(
        self,
        message: str,
        error_code: str,
        category: ErrorCategory = ErrorCategory.SYSTEM,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        details: Optional[Dict[str, Any]] = None,
        user_message: Optional[str] = None,
        retry_after: Optional[int] = None
    ):
        self.message = message
        self.error_code = error_code
        self.category = category
        self.severity = severity
        self.details = details or {}
        self.user_message = user_message or message
        self.retry_after = retry_after
        self.timestamp = datetime.utcnow()
        self.traceback = traceback.format_exc()

        super().__init__(self.message)

    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for JSON serialization."""
        return {
            "error_code": self.error_code,
            "message": self.message,
            "user_message": self.user_message,
            "category": self.category.value,
            "severity": self.severity.value,
            "details": self.details,
            "retry_after": self.retry_after,
            "timestamp": self.timestamp.isoformat()
        }


# Validation Exceptions
class ValidationException(NewsMCPException):
    """Raised when input validation fails."""

    def __init__(self, message: str, field: Optional[str] = None, value: Any = None, **kwargs):
        details = kwargs.get('details', {})
        if field:
            details['field'] = field
        if value is not None:
            details['value'] = str(value)

        super().__init__(
            message=message,
            error_code="VALIDATION_ERROR",
            category=ErrorCategory.VALIDATION,
            severity=ErrorSeverity.LOW,
            details=details,
            user_message=f"Invalid input: {message}",
            **kwargs
        )


class SchemaValidationException(ValidationException):
    """Raised when data doesn't match expected schema."""

    def __init__(self, message: str, schema_errors: Optional[list] = None, **kwargs):
        details = kwargs.get('details', {})
        if schema_errors:
            details['schema_errors'] = schema_errors

        super().__init__(
            message=message,
            details=details,
            user_message="The provided data format is invalid.",
            **kwargs
        )


# Business Logic Exceptions
class BusinessLogicException(NewsMCPException):
    """Raised when business rules are violated."""

    def __init__(self, message: str, rule: Optional[str] = None, **kwargs):
        details = kwargs.get('details', {})
        if rule:
            details['violated_rule'] = rule

        super().__init__(
            message=message,
            error_code="BUSINESS_LOGIC_ERROR",
            category=ErrorCategory.BUSINESS_LOGIC,
            severity=ErrorSeverity.MEDIUM,
            details=details,
            **kwargs
        )


class ResourceLimitException(BusinessLogicException):
    """Raised when resource limits are exceeded."""

    def __init__(self, resource: str, limit: int, current: int, **kwargs):
        message = f"{resource} limit exceeded: {current}/{limit}"
        details = {
            "resource": resource,
            "limit": limit,
            "current": current
        }

        super().__init__(
            message=message,
            rule=f"{resource}_limit",
            details=details,
            user_message=f"You have exceeded the {resource} limit ({limit}). Please try again later.",
            **kwargs
        )


class ConcurrencyLimitException(ResourceLimitException):
    """Raised when concurrent operation limits are exceeded."""

    def __init__(self, operation: str, limit: int, **kwargs):
        super().__init__(
            resource=f"concurrent_{operation}",
            limit=limit,
            current=limit + 1,  # Assuming we're over the limit
            retry_after=60,  # Suggest retry after 1 minute
            **kwargs
        )


# External Service Exceptions
class ExternalServiceException(NewsMCPException):
    """Raised when external service calls fail."""

    def __init__(self, service: str, message: str, status_code: Optional[int] = None, **kwargs):
        details = kwargs.get('details', {})
        details.update({
            "service": service,
            "status_code": status_code
        })

        super().__init__(
            message=message,
            error_code="EXTERNAL_SERVICE_ERROR",
            category=ErrorCategory.EXTERNAL_SERVICE,
            severity=ErrorSeverity.MEDIUM,
            details=details,
            user_message="A temporary service issue occurred. Please try again later.",
            **kwargs
        )


class FeedFetchException(ExternalServiceException):
    """Raised when RSS feed fetching fails."""

    def __init__(self, feed_url: str, message: str, **kwargs):
        super().__init__(
            service="rss_feed",
            message=f"Failed to fetch feed {feed_url}: {message}",
            details={"feed_url": feed_url},
            **kwargs
        )


class LLMServiceException(ExternalServiceException):
    """Raised when LLM API calls fail."""

    def __init__(self, provider: str, message: str, **kwargs):
        super().__init__(
            service=f"llm_{provider}",
            message=f"LLM service error ({provider}): {message}",
            severity=ErrorSeverity.HIGH,  # LLM failures are important
            **kwargs
        )


# Database Exceptions
class DatabaseException(NewsMCPException):
    """Raised when database operations fail."""

    def __init__(self, message: str, operation: Optional[str] = None, **kwargs):
        details = kwargs.get('details', {})
        if operation:
            details['operation'] = operation

        super().__init__(
            message=message,
            error_code="DATABASE_ERROR",
            category=ErrorCategory.DATABASE,
            severity=ErrorSeverity.HIGH,
            details=details,
            user_message="A database error occurred. Please try again later.",
            **kwargs
        )


class DatabaseConnectionException(DatabaseException):
    """Raised when database connection fails."""

    def __init__(self, message: str, **kwargs):
        super().__init__(
            message=f"Database connection failed: {message}",
            operation="connect",
            severity=ErrorSeverity.CRITICAL,
            user_message="Service temporarily unavailable. Please try again in a few minutes.",
            **kwargs
        )


# Resource Exceptions
class ResourceNotFoundException(NewsMCPException):
    """Raised when a requested resource is not found."""

    def __init__(self, resource_type: str, resource_id: Any, **kwargs):
        message = f"{resource_type} with id '{resource_id}' not found"

        super().__init__(
            message=message,
            error_code="RESOURCE_NOT_FOUND",
            category=ErrorCategory.BUSINESS_LOGIC,
            severity=ErrorSeverity.LOW,
            details={
                "resource_type": resource_type,
                "resource_id": str(resource_id)
            },
            user_message=f"The requested {resource_type.lower()} was not found.",
            **kwargs
        )


class ResourceConflictException(NewsMCPException):
    """Raised when a resource operation conflicts with existing state."""

    def __init__(self, resource_type: str, conflict_reason: str, **kwargs):
        message = f"{resource_type} conflict: {conflict_reason}"

        super().__init__(
            message=message,
            error_code="RESOURCE_CONFLICT",
            category=ErrorCategory.BUSINESS_LOGIC,
            severity=ErrorSeverity.MEDIUM,
            details={
                "resource_type": resource_type,
                "conflict_reason": conflict_reason
            },
            user_message=f"Cannot complete operation due to conflict: {conflict_reason}",
            **kwargs
        )


# Authentication & Authorization
class AuthenticationException(NewsMCPException):
    """Raised when authentication fails."""

    def __init__(self, message: str = "Authentication failed", **kwargs):
        super().__init__(
            message=message,
            error_code="AUTHENTICATION_FAILED",
            category=ErrorCategory.AUTHENTICATION,
            severity=ErrorSeverity.MEDIUM,
            user_message="Authentication failed. Please check your credentials.",
            **kwargs
        )


class AuthorizationException(NewsMCPException):
    """Raised when authorization fails."""

    def __init__(self, resource: str, action: str, **kwargs):
        message = f"Not authorized to {action} {resource}"

        super().__init__(
            message=message,
            error_code="AUTHORIZATION_FAILED",
            category=ErrorCategory.AUTHORIZATION,
            severity=ErrorSeverity.MEDIUM,
            details={
                "resource": resource,
                "action": action
            },
            user_message="You don't have permission to perform this action.",
            **kwargs
        )


# Rate Limiting
class RateLimitException(NewsMCPException):
    """Raised when rate limits are exceeded."""

    def __init__(self, limit: int, window: str, reset_time: Optional[int] = None, **kwargs):
        message = f"Rate limit exceeded: {limit} requests per {window}"

        super().__init__(
            message=message,
            error_code="RATE_LIMIT_EXCEEDED",
            category=ErrorCategory.RATE_LIMIT,
            severity=ErrorSeverity.LOW,
            details={
                "limit": limit,
                "window": window,
                "reset_time": reset_time
            },
            user_message=f"Too many requests. Please wait {window} before trying again.",
            retry_after=reset_time,
            **kwargs
        )


# Configuration Exceptions
class ConfigurationException(NewsMCPException):
    """Raised when configuration is invalid or missing."""

    def __init__(self, config_key: str, message: str, **kwargs):
        super().__init__(
            message=f"Configuration error for '{config_key}': {message}",
            error_code="CONFIGURATION_ERROR",
            category=ErrorCategory.CONFIGURATION,
            severity=ErrorSeverity.CRITICAL,
            details={"config_key": config_key},
            user_message="Service configuration error. Please contact support.",
            **kwargs
        )