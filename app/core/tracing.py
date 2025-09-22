"""Request tracing and monitoring middleware."""

import time
import uuid
from typing import Dict, Any, Optional, Callable, List
from datetime import datetime
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.logging_config import ContextManager, get_logger
from app.core.metrics import metrics

logger = get_logger(__name__)


class RequestTracer:
    """Request tracing and context management."""

    def __init__(self):
        self.active_requests: Dict[str, Dict[str, Any]] = {}

    def start_request(self, request: Request) -> str:
        """Start tracing a request."""
        request_id = str(uuid.uuid4())
        start_time = time.time()

        # Extract request information
        request_info = {
            "request_id": request_id,
            "method": request.method,
            "url": str(request.url),
            "path": request.url.path,
            "query_params": dict(request.query_params),
            "headers": dict(request.headers),
            "client_ip": self._get_client_ip(request),
            "user_agent": request.headers.get("user-agent", "unknown"),
            "start_time": start_time,
            "start_timestamp": datetime.utcnow()
        }

        # Set logging context
        ContextManager.set_context(
            request_id=request_id,
            operation=f"{request.method} {request.url.path}",
            client_ip=request_info["client_ip"],
            user_agent=request_info["user_agent"],
            method=request.method,
            url=str(request.url)
        )

        # Store request info
        self.active_requests[request_id] = request_info

        # Log request start
        logger.info(f"Request started: {request.method} {request.url.path}")

        return request_id

    def end_request(self, request_id: str, response: Response) -> None:
        """End tracing a request."""
        if request_id not in self.active_requests:
            logger.warning(f"Request {request_id} not found in active requests")
            return

        request_info = self.active_requests[request_id]
        end_time = time.time()
        duration_ms = (end_time - request_info["start_time"]) * 1000

        # Update context with response information
        ContextManager.set_context(
            status_code=response.status_code,
            duration_ms=duration_ms
        )

        # Log request completion
        logger.info(
            f"Request completed: {request_info['method']} {request_info['path']}",
            status_code=response.status_code,
            duration_ms=duration_ms
        )

        # Record metrics
        metrics.record_timer(
            "request_duration_ms",
            duration_ms,
            tags={
                "method": request_info["method"],
                "path": request_info["path"],
                "status_code": str(response.status_code)
            }
        )

        # Clean up
        del self.active_requests[request_id]

    def get_active_request_count(self) -> int:
        """Get number of currently active requests."""
        return len(self.active_requests)

    def get_request_info(self, request_id: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific request."""
        return self.active_requests.get(request_id)

    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP from request."""
        # Check for forwarded headers first
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip

        # Fall back to direct client IP
        if request.client:
            return request.client.host

        return "unknown"


# Global request tracer
tracer = RequestTracer()


class TracingMiddleware(BaseHTTPMiddleware):
    """Middleware for request tracing and monitoring."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with tracing."""
        # Skip tracing for health checks, metrics endpoints and static files
        if request.url.path.startswith(("/health", "/metrics", "/static")):
            return await call_next(request)

        # Start tracing
        request_id = tracer.start_request(request)

        # Add request ID to request state
        request.state.request_id = request_id

        try:
            # Process request
            response = await call_next(request)

            # Smart header handling: Only add headers for API responses (JSON)
            # Skip header modification for HTML template responses to avoid conflicts
            if request.url.path.startswith("/api") or self._is_json_response(response):
                response.headers["X-Request-ID"] = request_id

            # End tracing
            tracer.end_request(request_id, response)

            return response

        except Exception as e:
            # Log error with context
            logger.error(
                f"Request failed: {request.method} {request.url.path}",
                error_type=type(e).__name__,
                error_message=str(e)
            )

            # Record error metrics
            metrics.increment_counter(
                "request_errors_total",
                tags={
                    "method": request.method,
                    "path": request.url.path,
                    "error_type": type(e).__name__
                }
            )

            # Clean up tracing
            if request_id in tracer.active_requests:
                del tracer.active_requests[request_id]

            # Re-raise exception
            raise

    def _is_json_response(self, response: Response) -> bool:
        """Check if response is JSON-based."""
        content_type = response.headers.get("content-type", "")
        return "application/json" in content_type


class OperationTracer:
    """Tracer for individual operations within requests."""

    def __init__(self, operation_name: str, tags: Optional[Dict[str, str]] = None):
        self.operation_name = operation_name
        self.tags = tags or {}
        self.start_time = None

    def __enter__(self):
        self.start_time = time.time()
        logger.operation_start(self.operation_name, **self.tags)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time is None:
            return

        duration_ms = (time.time() - self.start_time) * 1000

        if exc_type:
            # Operation failed
            logger.operation_error(self.operation_name, exc_val, **self.tags)

            # Record error metrics
            error_tags = self.tags.copy()
            error_tags.update({
                "operation": self.operation_name,
                "error_type": exc_type.__name__
            })
            metrics.increment_counter("operation_errors_total", tags=error_tags)

        else:
            # Operation succeeded
            logger.operation_end(self.operation_name, duration_ms, **self.tags)

        # Record timing metrics
        timing_tags = self.tags.copy()
        timing_tags.update({
            "operation": self.operation_name,
            "success": str(exc_type is None).lower()
        })
        metrics.record_timer("operation_duration_ms", duration_ms, tags=timing_tags)


def trace_operation(operation_name: str, tags: Optional[Dict[str, str]] = None):
    """Decorator for tracing operations."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            with OperationTracer(operation_name, tags):
                return func(*args, **kwargs)

        async def async_wrapper(*args, **kwargs):
            with OperationTracer(operation_name, tags):
                return await func(*args, **kwargs)

        # Preserve function metadata
        if hasattr(func, '__name__'):
            wrapper.__name__ = func.__name__
            async_wrapper.__name__ = func.__name__

        return async_wrapper if callable(getattr(func, '__call__', None)) else wrapper
    return decorator


class PerformanceMonitor:
    """Monitor application performance and detect issues."""

    def __init__(self):
        self.slow_request_threshold_ms = 5000  # 5 seconds
        self.error_rate_threshold = 0.1  # 10%
        self.monitoring_window_minutes = 5

    def check_slow_requests(self) -> List[Dict[str, Any]]:
        """Check for slow requests."""
        slow_requests = []
        current_time = time.time()

        for request_id, request_info in tracer.active_requests.items():
            request_duration = (current_time - request_info["start_time"]) * 1000

            if request_duration > self.slow_request_threshold_ms:
                slow_requests.append({
                    "request_id": request_id,
                    "method": request_info["method"],
                    "path": request_info["path"],
                    "duration_ms": request_duration,
                    "client_ip": request_info["client_ip"]
                })

        return slow_requests

    def get_error_rate(self) -> float:
        """Calculate current error rate."""
        # This would typically use metrics data
        # For now, return a placeholder
        return 0.0

    def get_performance_summary(self) -> Dict[str, Any]:
        """Get overall performance summary."""
        slow_requests = self.check_slow_requests()
        error_rate = self.get_error_rate()

        return {
            "active_requests": tracer.get_active_request_count(),
            "slow_requests": len(slow_requests),
            "error_rate": error_rate,
            "health_status": self._get_health_status(slow_requests, error_rate)
        }

    def _get_health_status(self, slow_requests: List, error_rate: float) -> str:
        """Determine health status based on performance metrics."""
        if error_rate > self.error_rate_threshold:
            return "unhealthy"
        elif len(slow_requests) > 5:
            return "degraded"
        else:
            return "healthy"


# Global performance monitor
performance_monitor = PerformanceMonitor()


# API endpoints for tracing and monitoring
from fastapi import APIRouter

def create_tracing_router() -> APIRouter:
    """Create tracing and monitoring API router."""
    router = APIRouter(prefix="/monitoring", tags=["monitoring"])

    @router.get("/requests/active")
    async def get_active_requests():
        """Get currently active requests."""
        active_requests = []
        current_time = time.time()

        for request_id, request_info in tracer.active_requests.items():
            duration_ms = (current_time - request_info["start_time"]) * 1000
            active_requests.append({
                "request_id": request_id,
                "method": request_info["method"],
                "path": request_info["path"],
                "duration_ms": round(duration_ms, 2),
                "client_ip": request_info["client_ip"],
                "start_time": request_info["start_timestamp"].isoformat()
            })

        return {
            "count": len(active_requests),
            "requests": active_requests
        }

    @router.get("/requests/{request_id}")
    async def get_request_details(request_id: str):
        """Get details about a specific request."""
        request_info = tracer.get_request_info(request_id)
        if not request_info:
            return {"error": f"Request {request_id} not found"}, 404

        current_time = time.time()
        duration_ms = (current_time - request_info["start_time"]) * 1000

        return {
            "request_id": request_id,
            "method": request_info["method"],
            "url": request_info["url"],
            "path": request_info["path"],
            "query_params": request_info["query_params"],
            "client_ip": request_info["client_ip"],
            "user_agent": request_info["user_agent"],
            "start_time": request_info["start_timestamp"].isoformat(),
            "duration_ms": round(duration_ms, 2)
        }

    @router.get("/performance")
    async def get_performance_summary():
        """Get performance summary."""
        return performance_monitor.get_performance_summary()

    @router.get("/slow-requests")
    async def get_slow_requests():
        """Get currently slow requests."""
        slow_requests = performance_monitor.check_slow_requests()
        return {
            "count": len(slow_requests),
            "threshold_ms": performance_monitor.slow_request_threshold_ms,
            "requests": slow_requests
        }

    return router