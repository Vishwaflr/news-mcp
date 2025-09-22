"""Global exception handlers for FastAPI application."""

import logging
import traceback
from typing import Union, Dict, Any
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError, ResponseValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from pydantic import ValidationError

from .exceptions import (
    NewsMCPException, ValidationException, BusinessLogicException,
    ExternalServiceException, DatabaseException, ResourceNotFoundException,
    ResourceConflictException, AuthenticationException, AuthorizationException,
    RateLimitException, ConfigurationException, ErrorSeverity
)

logger = logging.getLogger(__name__)


class ErrorHandler:
    """Centralized error handling and response generation."""

    @staticmethod
    def create_error_response(
        status_code: int,
        error_code: str,
        message: str,
        user_message: str = None,
        details: Dict[str, Any] = None,
        retry_after: int = None
    ) -> JSONResponse:
        """Create standardized error response."""
        content = {
            "error": {
                "code": error_code,
                "message": message,
                "user_message": user_message or message,
                "details": details or {}
            }
        }

        headers = {}
        if retry_after:
            headers["Retry-After"] = str(retry_after)

        return JSONResponse(
            status_code=status_code,
            content=content,
            headers=headers
        )

    @staticmethod
    def log_error(
        exception: Exception,
        request: Request,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM
    ) -> None:
        """Log error with context information."""
        request_info = {
            "method": request.method,
            "url": str(request.url),
            "client_ip": request.client.host if request.client else "unknown",
            "user_agent": request.headers.get("user-agent", "unknown"),
            "request_id": getattr(request.state, "request_id", None)
        }

        error_info = {
            "exception_type": type(exception).__name__,
            "exception_message": str(exception),
            "traceback": traceback.format_exc(),
            "request": request_info
        }

        if severity == ErrorSeverity.CRITICAL:
            logger.critical("Critical error occurred", extra=error_info)
        elif severity == ErrorSeverity.HIGH:
            logger.error("High severity error occurred", extra=error_info)
        elif severity == ErrorSeverity.MEDIUM:
            logger.warning("Medium severity error occurred", extra=error_info)
        else:
            logger.info("Low severity error occurred", extra=error_info)


async def news_mcp_exception_handler(request: Request, exc: NewsMCPException) -> JSONResponse:
    """Handle custom News MCP exceptions."""
    ErrorHandler.log_error(exc, request, exc.severity)

    # Map severity to HTTP status codes
    status_code_map = {
        ErrorSeverity.LOW: status.HTTP_400_BAD_REQUEST,
        ErrorSeverity.MEDIUM: status.HTTP_500_INTERNAL_SERVER_ERROR,
        ErrorSeverity.HIGH: status.HTTP_500_INTERNAL_SERVER_ERROR,
        ErrorSeverity.CRITICAL: status.HTTP_503_SERVICE_UNAVAILABLE
    }

    # Override status codes for specific exception types
    if isinstance(exc, (ValidationException, BusinessLogicException)):
        status_code = status.HTTP_400_BAD_REQUEST
    elif isinstance(exc, ResourceNotFoundException):
        status_code = status.HTTP_404_NOT_FOUND
    elif isinstance(exc, ResourceConflictException):
        status_code = status.HTTP_409_CONFLICT
    elif isinstance(exc, AuthenticationException):
        status_code = status.HTTP_401_UNAUTHORIZED
    elif isinstance(exc, AuthorizationException):
        status_code = status.HTTP_403_FORBIDDEN
    elif isinstance(exc, RateLimitException):
        status_code = status.HTTP_429_TOO_MANY_REQUESTS
    elif isinstance(exc, ExternalServiceException):
        status_code = status.HTTP_502_BAD_GATEWAY
    elif isinstance(exc, DatabaseException):
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    elif isinstance(exc, ConfigurationException):
        status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    else:
        status_code = status_code_map.get(exc.severity, status.HTTP_500_INTERNAL_SERVER_ERROR)

    return ErrorHandler.create_error_response(
        status_code=status_code,
        error_code=exc.error_code,
        message=exc.message,
        user_message=exc.user_message,
        details=exc.details,
        retry_after=exc.retry_after
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Handle Pydantic validation errors."""
    ErrorHandler.log_error(exc, request, ErrorSeverity.LOW)

    # Extract field-level validation errors
    validation_errors = []
    for error in exc.errors():
        field_path = " -> ".join(str(loc) for loc in error["loc"])
        validation_errors.append({
            "field": field_path,
            "message": error["msg"],
            "type": error["type"],
            "input": error.get("input")
        })

    return ErrorHandler.create_error_response(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        error_code="VALIDATION_ERROR",
        message="Request validation failed",
        user_message="Please check your input data and try again.",
        details={"validation_errors": validation_errors}
    )


async def response_validation_exception_handler(request: Request, exc: ResponseValidationError) -> JSONResponse:
    """Handle response validation errors (internal server errors)."""
    ErrorHandler.log_error(exc, request, ErrorSeverity.CRITICAL)

    return ErrorHandler.create_error_response(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        error_code="RESPONSE_VALIDATION_ERROR",
        message="Internal server error: response validation failed",
        user_message="An internal error occurred. Please try again later."
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Handle standard HTTP exceptions."""
    severity = ErrorSeverity.LOW if exc.status_code < 500 else ErrorSeverity.HIGH
    ErrorHandler.log_error(exc, request, severity)

    error_code_map = {
        400: "BAD_REQUEST",
        401: "UNAUTHORIZED",
        403: "FORBIDDEN",
        404: "NOT_FOUND",
        405: "METHOD_NOT_ALLOWED",
        409: "CONFLICT",
        422: "UNPROCESSABLE_ENTITY",
        429: "TOO_MANY_REQUESTS",
        500: "INTERNAL_SERVER_ERROR",
        502: "BAD_GATEWAY",
        503: "SERVICE_UNAVAILABLE",
        504: "GATEWAY_TIMEOUT"
    }

    error_code = error_code_map.get(exc.status_code, "HTTP_ERROR")

    return ErrorHandler.create_error_response(
        status_code=exc.status_code,
        error_code=error_code,
        message=exc.detail,
        user_message=exc.detail
    )


async def database_exception_handler(request: Request, exc: SQLAlchemyError) -> JSONResponse:
    """Handle SQLAlchemy database errors."""
    ErrorHandler.log_error(exc, request, ErrorSeverity.HIGH)

    # Handle specific database errors
    if isinstance(exc, IntegrityError):
        return ErrorHandler.create_error_response(
            status_code=status.HTTP_409_CONFLICT,
            error_code="DATABASE_INTEGRITY_ERROR",
            message="Database integrity constraint violation",
            user_message="The operation conflicts with existing data. Please check your input."
        )

    # Generic database error
    return ErrorHandler.create_error_response(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        error_code="DATABASE_ERROR",
        message="Database operation failed",
        user_message="A database error occurred. Please try again later."
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unexpected exceptions."""
    ErrorHandler.log_error(exc, request, ErrorSeverity.CRITICAL)

    return ErrorHandler.create_error_response(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        error_code="UNEXPECTED_ERROR",
        message=f"Unexpected error: {type(exc).__name__}",
        user_message="An unexpected error occurred. Please try again later."
    )


def register_exception_handlers(app):
    """Register all exception handlers with the FastAPI app."""

    # Custom News MCP exceptions
    app.add_exception_handler(NewsMCPException, news_mcp_exception_handler)

    # Request validation errors
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(ResponseValidationError, response_validation_exception_handler)

    # HTTP exceptions
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)

    # Database exceptions
    app.add_exception_handler(SQLAlchemyError, database_exception_handler)

    # Catch-all for unexpected exceptions
    app.add_exception_handler(Exception, generic_exception_handler)