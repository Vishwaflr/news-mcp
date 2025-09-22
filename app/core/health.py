"""Health check system for monitoring application status."""

import time
import asyncio
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, field
from sqlmodel import Session, text
from fastapi import APIRouter, Depends

from app.database import get_session, engine
from app.core.logging_config import get_logger

logger = get_logger(__name__)


class HealthStatus(str, Enum):
    """Health check status levels."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class HealthCheckResult:
    """Result of a health check."""
    name: str
    status: HealthStatus
    message: str
    duration_ms: float
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)


class HealthChecker:
    """Individual health check implementation."""

    def __init__(self, name: str, check_func: Callable, timeout: float = 5.0):
        self.name = name
        self.check_func = check_func
        self.timeout = timeout

    async def check(self) -> HealthCheckResult:
        """Execute the health check."""
        start_time = time.time()
        try:
            # Run check with timeout
            if asyncio.iscoroutinefunction(self.check_func):
                result = await asyncio.wait_for(self.check_func(), timeout=self.timeout)
            else:
                result = self.check_func()

            duration_ms = (time.time() - start_time) * 1000

            if isinstance(result, HealthCheckResult):
                result.duration_ms = duration_ms
                return result
            elif isinstance(result, dict):
                return HealthCheckResult(
                    name=self.name,
                    status=result.get("status", HealthStatus.HEALTHY),
                    message=result.get("message", "OK"),
                    duration_ms=duration_ms,
                    details=result.get("details", {})
                )
            else:
                return HealthCheckResult(
                    name=self.name,
                    status=HealthStatus.HEALTHY,
                    message="OK",
                    duration_ms=duration_ms
                )

        except asyncio.TimeoutError:
            duration_ms = (time.time() - start_time) * 1000
            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.UNHEALTHY,
                message=f"Health check timed out after {self.timeout}s",
                duration_ms=duration_ms
            )
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.error(f"Health check '{self.name}' failed", error=str(e))
            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.UNHEALTHY,
                message=f"Health check failed: {str(e)}",
                duration_ms=duration_ms
            )


class HealthMonitor:
    """Centralized health monitoring system."""

    def __init__(self):
        self.checkers: Dict[str, HealthChecker] = {}
        self.last_results: Dict[str, HealthCheckResult] = {}

    def register_check(self, checker: HealthChecker) -> None:
        """Register a health check."""
        self.checkers[checker.name] = checker
        logger.info(f"Registered health check: {checker.name}")

    def register_check_func(self, name: str, check_func: Callable, timeout: float = 5.0) -> None:
        """Register a health check function."""
        checker = HealthChecker(name, check_func, timeout)
        self.register_check(checker)

    async def check_all(self) -> Dict[str, HealthCheckResult]:
        """Run all registered health checks."""
        results = {}

        # Run all checks concurrently
        tasks = [
            (name, checker.check())
            for name, checker in self.checkers.items()
        ]

        for name, task in tasks:
            try:
                result = await task
                results[name] = result
                self.last_results[name] = result
            except Exception as e:
                logger.error(f"Failed to execute health check '{name}'", error=str(e))
                result = HealthCheckResult(
                    name=name,
                    status=HealthStatus.UNHEALTHY,
                    message=f"Failed to execute check: {str(e)}",
                    duration_ms=0
                )
                results[name] = result
                self.last_results[name] = result

        return results

    async def check_single(self, name: str) -> Optional[HealthCheckResult]:
        """Run a single health check by name."""
        if name not in self.checkers:
            return None

        result = await self.checkers[name].check()
        self.last_results[name] = result
        return result

    def get_overall_status(self, results: Optional[Dict[str, HealthCheckResult]] = None) -> HealthStatus:
        """Calculate overall system health status."""
        if results is None:
            results = self.last_results

        if not results:
            return HealthStatus.UNKNOWN

        statuses = [result.status for result in results.values()]

        if any(status == HealthStatus.UNHEALTHY for status in statuses):
            return HealthStatus.UNHEALTHY
        elif any(status == HealthStatus.DEGRADED for status in statuses):
            return HealthStatus.DEGRADED
        elif all(status == HealthStatus.HEALTHY for status in statuses):
            return HealthStatus.HEALTHY
        else:
            return HealthStatus.UNKNOWN


# Global health monitor instance
health_monitor = HealthMonitor()


# Built-in health checks
async def database_health_check() -> Dict[str, Any]:
    """Check database connectivity and basic operations."""
    try:
        with Session(engine) as session:
            # Test basic connectivity
            result = session.exec(text("SELECT 1")).first()
            if result != 1:
                return {
                    "status": HealthStatus.UNHEALTHY,
                    "message": "Database query returned unexpected result"
                }

            # Test table access
            feeds_count = session.exec(text("SELECT COUNT(*) FROM feeds")).first()
            items_count = session.exec(text("SELECT COUNT(*) FROM items")).first()

            return {
                "status": HealthStatus.HEALTHY,
                "message": "Database is accessible",
                "details": {
                    "feeds_count": feeds_count,
                    "items_count": items_count
                }
            }

    except Exception as e:
        return {
            "status": HealthStatus.UNHEALTHY,
            "message": f"Database connection failed: {str(e)}"
        }


def memory_health_check() -> Dict[str, Any]:
    """Check memory usage."""
    try:
        import psutil
        process = psutil.Process()
        memory_info = process.memory_info()
        memory_percent = process.memory_percent()

        # Define thresholds
        if memory_percent > 90:
            status = HealthStatus.UNHEALTHY
            message = "Memory usage critically high"
        elif memory_percent > 80:
            status = HealthStatus.DEGRADED
            message = "Memory usage high"
        else:
            status = HealthStatus.HEALTHY
            message = "Memory usage normal"

        return {
            "status": status,
            "message": message,
            "details": {
                "memory_percent": memory_percent,
                "memory_rss_mb": memory_info.rss / 1024 / 1024,
                "memory_vms_mb": memory_info.vms / 1024 / 1024
            }
        }

    except ImportError:
        return {
            "status": HealthStatus.UNKNOWN,
            "message": "psutil not available for memory monitoring"
        }
    except Exception as e:
        return {
            "status": HealthStatus.UNHEALTHY,
            "message": f"Memory check failed: {str(e)}"
        }


def disk_health_check() -> Dict[str, Any]:
    """Check disk usage."""
    try:
        import psutil
        disk_usage = psutil.disk_usage('/')

        usage_percent = (disk_usage.used / disk_usage.total) * 100

        if usage_percent > 95:
            status = HealthStatus.UNHEALTHY
            message = "Disk usage critically high"
        elif usage_percent > 85:
            status = HealthStatus.DEGRADED
            message = "Disk usage high"
        else:
            status = HealthStatus.HEALTHY
            message = "Disk usage normal"

        return {
            "status": status,
            "message": message,
            "details": {
                "usage_percent": round(usage_percent, 2),
                "free_gb": round(disk_usage.free / 1024 / 1024 / 1024, 2),
                "total_gb": round(disk_usage.total / 1024 / 1024 / 1024, 2)
            }
        }

    except ImportError:
        return {
            "status": HealthStatus.UNKNOWN,
            "message": "psutil not available for disk monitoring"
        }
    except Exception as e:
        return {
            "status": HealthStatus.UNHEALTHY,
            "message": f"Disk check failed: {str(e)}"
        }


async def application_health_check() -> Dict[str, Any]:
    """Check application-specific health indicators."""
    try:
        with Session(engine) as session:
            # Check for recent activity
            recent_cutoff = datetime.utcnow() - timedelta(hours=24)
            recent_items = session.exec(
                text("SELECT COUNT(*) FROM items WHERE created_at >= :cutoff"),
                {"cutoff": recent_cutoff}
            ).first()

            # Check for failed analysis runs
            failed_runs = session.exec(
                text("SELECT COUNT(*) FROM analysis_runs WHERE status = 'failed' AND created_at >= :cutoff"),
                {"cutoff": recent_cutoff}
            ).first()

            details = {
                "recent_items_24h": recent_items,
                "failed_analysis_runs_24h": failed_runs
            }

            if failed_runs > 10:
                status = HealthStatus.DEGRADED
                message = "High number of failed analysis runs"
            elif recent_items == 0:
                status = HealthStatus.DEGRADED
                message = "No recent item activity"
            else:
                status = HealthStatus.HEALTHY
                message = "Application metrics healthy"

            return {
                "status": status,
                "message": message,
                "details": details
            }

    except Exception as e:
        return {
            "status": HealthStatus.UNHEALTHY,
            "message": f"Application health check failed: {str(e)}"
        }


def register_default_health_checks():
    """Register default health checks."""
    health_monitor.register_check_func("database", database_health_check, timeout=10.0)
    health_monitor.register_check_func("memory", memory_health_check, timeout=5.0)
    health_monitor.register_check_func("disk", disk_health_check, timeout=5.0)
    health_monitor.register_check_func("application", application_health_check, timeout=10.0)


# Health check API endpoints
def create_health_router() -> APIRouter:
    """Create health check router."""
    router = APIRouter(prefix="/health", tags=["health"])

    @router.get("/")
    async def health_check():
        """Basic health check endpoint."""
        return {"status": "ok", "timestamp": datetime.utcnow()}

    @router.get("/detailed")
    async def detailed_health_check():
        """Detailed health check with all registered checks."""
        start_time = time.time()
        results = await health_monitor.check_all()
        overall_status = health_monitor.get_overall_status(results)
        duration_ms = (time.time() - start_time) * 1000

        response_data = {
            "status": overall_status.value,
            "timestamp": datetime.utcnow(),
            "duration_ms": round(duration_ms, 2),
            "checks": {
                name: {
                    "status": result.status.value,
                    "message": result.message,
                    "duration_ms": round(result.duration_ms, 2),
                    "details": result.details
                }
                for name, result in results.items()
            }
        }

        # Set appropriate HTTP status code
        status_code = 200 if overall_status == HealthStatus.HEALTHY else 503
        return response_data

    @router.get("/check/{check_name}")
    async def single_health_check(check_name: str):
        """Run a single health check."""
        result = await health_monitor.check_single(check_name)
        if result is None:
            return {"error": f"Health check '{check_name}' not found"}, 404

        response_data = {
            "status": result.status.value,
            "message": result.message,
            "duration_ms": round(result.duration_ms, 2),
            "details": result.details,
            "timestamp": result.timestamp
        }

        status_code = 200 if result.status == HealthStatus.HEALTHY else 503
        return response_data

    @router.get("/ready")
    async def readiness_check():
        """Kubernetes readiness probe endpoint."""
        results = await health_monitor.check_all()
        overall_status = health_monitor.get_overall_status(results)

        if overall_status in [HealthStatus.HEALTHY, HealthStatus.DEGRADED]:
            return {"status": "ready"}
        else:
            return {"status": "not_ready"}, 503

    @router.get("/live")
    async def liveness_check():
        """Kubernetes liveness probe endpoint."""
        # Simple check - just ensure the application is responding
        return {"status": "alive"}

    return router