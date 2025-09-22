"""Structured logging configuration with context management."""

import logging
import logging.config
import json
import uuid
from datetime import datetime
from typing import Dict, Any, Optional
from contextvars import ContextVar
from functools import wraps

# Context variables for request tracking
request_context: ContextVar[Dict[str, Any]] = ContextVar('request_context', default={})


class ContextFilter(logging.Filter):
    """Logging filter that adds context information to log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        """Add context information to the log record."""
        context = request_context.get({})

        # Add context fields to the record
        for key, value in context.items():
            setattr(record, key, value)

        # Ensure required fields exist
        if not hasattr(record, 'request_id'):
            record.request_id = 'unknown'
        if not hasattr(record, 'user_id'):
            record.user_id = 'anonymous'
        if not hasattr(record, 'operation'):
            record.operation = 'unknown'

        return True


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        # Base log data
        log_data = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }

        # Add context information
        context_fields = [
            'request_id', 'user_id', 'operation', 'client_ip',
            'user_agent', 'method', 'url', 'status_code', 'duration_ms'
        ]

        for field in context_fields:
            if hasattr(record, field):
                log_data[field] = getattr(record, field)

        # Add exception information if present
        if record.exc_info:
            log_data['exception'] = {
                'type': record.exc_info[0].__name__ if record.exc_info[0] else None,
                'message': str(record.exc_info[1]) if record.exc_info[1] else None,
                'traceback': self.formatException(record.exc_info)
            }

        # Add extra fields from the record
        extra_fields = {}
        for key, value in record.__dict__.items():
            if key not in ['name', 'msg', 'args', 'levelname', 'levelno', 'pathname',
                          'filename', 'module', 'exc_info', 'exc_text', 'stack_info',
                          'lineno', 'funcName', 'created', 'msecs', 'relativeCreated',
                          'thread', 'threadName', 'processName', 'process', 'message'] + context_fields:
                if not key.startswith('_'):
                    extra_fields[key] = value

        if extra_fields:
            log_data['extra'] = extra_fields

        return json.dumps(log_data, default=str)


class ContextManager:
    """Manages logging context for requests and operations."""

    @staticmethod
    def set_context(**kwargs) -> None:
        """Set context variables for the current request/operation."""
        current_context = request_context.get({})
        current_context.update(kwargs)
        request_context.set(current_context)

    @staticmethod
    def get_context() -> Dict[str, Any]:
        """Get current context."""
        return request_context.get({})

    @staticmethod
    def clear_context() -> None:
        """Clear current context."""
        request_context.set({})

    @staticmethod
    def generate_request_id() -> str:
        """Generate unique request ID."""
        return str(uuid.uuid4())


def setup_logging(
    log_level: str = "INFO",
    log_format: str = "json",
    log_file: Optional[str] = None
) -> None:
    """Setup logging configuration."""

    # Determine formatter
    if log_format.lower() == "json":
        formatter_class = JSONFormatter
        format_string = ""
    else:
        formatter_class = logging.Formatter
        format_string = (
            "%(asctime)s - %(name)s - %(levelname)s - "
            "[%(request_id)s] - %(message)s"
        )

    # Base logging configuration
    config = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'detailed': {
                '()': formatter_class,
                'format': format_string
            }
        },
        'filters': {
            'context_filter': {
                '()': ContextFilter
            }
        },
        'handlers': {
            'console': {
                'class': 'logging.StreamHandler',
                'level': log_level,
                'formatter': 'detailed',
                'filters': ['context_filter'],
                'stream': 'ext://sys.stdout'
            }
        },
        'loggers': {
            '': {  # Root logger
                'level': log_level,
                'handlers': ['console'],
                'propagate': False
            },
            'app': {
                'level': log_level,
                'handlers': ['console'],
                'propagate': False
            },
            'uvicorn': {
                'level': 'INFO',
                'handlers': ['console'],
                'propagate': False
            },
            'sqlalchemy': {
                'level': 'WARNING',
                'handlers': ['console'],
                'propagate': False
            }
        }
    }

    # Add file handler if specified
    if log_file:
        config['handlers']['file'] = {
            'class': 'logging.handlers.RotatingFileHandler',
            'level': log_level,
            'formatter': 'detailed',
            'filters': ['context_filter'],
            'filename': log_file,
            'maxBytes': 10485760,  # 10MB
            'backupCount': 5
        }

        # Add file handler to all loggers
        for logger_config in config['loggers'].values():
            logger_config['handlers'].append('file')

    logging.config.dictConfig(config)


def with_logging_context(**context_kwargs):
    """Decorator to add logging context to a function."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Set context
            ContextManager.set_context(**context_kwargs)
            try:
                return func(*args, **kwargs)
            finally:
                # Context is automatically cleaned up by contextvars
                pass

        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Set context
            ContextManager.set_context(**context_kwargs)
            try:
                return await func(*args, **kwargs)
            finally:
                # Context is automatically cleaned up by contextvars
                pass

        return async_wrapper if callable(getattr(func, '__call__', None)) and hasattr(func, '__code__') else wrapper
    return decorator


class StructuredLogger:
    """Enhanced logger with structured logging capabilities."""

    def __init__(self, name: str):
        self.logger = logging.getLogger(name)

    def _log_with_context(self, level: int, message: str, **kwargs) -> None:
        """Log message with additional context."""
        extra = kwargs.copy()

        # Add current context
        context = ContextManager.get_context()
        extra.update(context)

        self.logger.log(level, message, extra=extra)

    def debug(self, message: str, **kwargs) -> None:
        """Log debug message."""
        self._log_with_context(logging.DEBUG, message, **kwargs)

    def info(self, message: str, **kwargs) -> None:
        """Log info message."""
        self._log_with_context(logging.INFO, message, **kwargs)

    def warning(self, message: str, **kwargs) -> None:
        """Log warning message."""
        self._log_with_context(logging.WARNING, message, **kwargs)

    def error(self, message: str, **kwargs) -> None:
        """Log error message."""
        self._log_with_context(logging.ERROR, message, **kwargs)

    def critical(self, message: str, **kwargs) -> None:
        """Log critical message."""
        self._log_with_context(logging.CRITICAL, message, **kwargs)

    def operation_start(self, operation: str, **kwargs) -> None:
        """Log start of an operation."""
        ContextManager.set_context(operation=operation)
        self.info(f"Starting operation: {operation}", operation_status="started", **kwargs)

    def operation_end(self, operation: str, duration_ms: Optional[float] = None, **kwargs) -> None:
        """Log end of an operation."""
        log_kwargs = {"operation_status": "completed", **kwargs}
        if duration_ms is not None:
            log_kwargs["duration_ms"] = duration_ms
        self.info(f"Completed operation: {operation}", **log_kwargs)

    def operation_error(self, operation: str, error: Exception, **kwargs) -> None:
        """Log operation error."""
        self.error(
            f"Operation failed: {operation}",
            operation_status="failed",
            error_type=type(error).__name__,
            error_message=str(error),
            **kwargs
        )


def get_logger(name: str) -> StructuredLogger:
    """Get a structured logger instance."""
    return StructuredLogger(name)