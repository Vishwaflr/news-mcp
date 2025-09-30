"""
Health and Monitoring API endpoints for v1

Provides health checks, circuit breaker status, and system diagnostics.
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any, List
from app.services.error_recovery import get_error_recovery_service
from app.core.health import health_monitor
from datetime import datetime

router = APIRouter(prefix="/api/v1/health", tags=["health"])


@router.get("/status")
async def health_status() -> Dict[str, Any]:
    """
    Get overall system health status.

    Returns:
        System health information including database, worker, and services status
    """
    try:
        results = await health_monitor.check_all()
        overall_status = health_monitor.get_overall_status(results)

        return {
            "status": overall_status.value,
            "timestamp": datetime.utcnow().isoformat(),
            "components": {
                name: {
                    "status": result.status.value,
                    "message": result.message,
                    "details": result.details
                }
                for name, result in results.items()
            }
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Health check failed: {str(e)}")


@router.get("/circuit-breakers")
async def get_circuit_breaker_status() -> Dict[str, Any]:
    """
    Get status of all circuit breakers in the system.

    Returns:
        Status information for each circuit breaker including state, failure counts, and statistics
    """
    try:
        error_recovery = get_error_recovery_service()
        breaker_status = error_recovery.get_status()

        # Calculate summary statistics
        total_breakers = len(breaker_status)
        open_breakers = sum(1 for cb in breaker_status.values() if cb["state"] == "open")
        half_open_breakers = sum(1 for cb in breaker_status.values() if cb["state"] == "half_open")
        closed_breakers = sum(1 for cb in breaker_status.values() if cb["state"] == "closed")

        total_errors = sum(cb["stats"]["total_errors"] for cb in breaker_status.values())
        total_recoveries = sum(cb["stats"]["successful_recoveries"] for cb in breaker_status.values())

        return {
            "timestamp": datetime.utcnow().isoformat(),
            "summary": {
                "total_breakers": total_breakers,
                "open": open_breakers,
                "half_open": half_open_breakers,
                "closed": closed_breakers,
                "total_errors": total_errors,
                "total_recoveries": total_recoveries,
                "health_percentage": (closed_breakers / total_breakers * 100) if total_breakers > 0 else 100
            },
            "breakers": breaker_status
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get circuit breaker status: {str(e)}")


@router.post("/circuit-breakers/{breaker_name}/reset")
async def reset_circuit_breaker(breaker_name: str) -> Dict[str, str]:
    """
    Manually reset a circuit breaker to closed state.

    Args:
        breaker_name: Name of the circuit breaker to reset

    Returns:
        Success message
    """
    try:
        error_recovery = get_error_recovery_service()
        error_recovery.reset_circuit_breaker(breaker_name)

        return {
            "status": "success",
            "message": f"Circuit breaker '{breaker_name}' has been reset to closed state"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to reset circuit breaker: {str(e)}")


@router.get("/circuit-breakers/{breaker_name}")
async def get_specific_circuit_breaker(breaker_name: str) -> Dict[str, Any]:
    """
    Get detailed status for a specific circuit breaker.

    Args:
        breaker_name: Name of the circuit breaker

    Returns:
        Detailed status information for the specified circuit breaker
    """
    try:
        error_recovery = get_error_recovery_service()
        all_breakers = error_recovery.get_status()

        if breaker_name not in all_breakers:
            raise HTTPException(status_code=404, detail=f"Circuit breaker '{breaker_name}' not found")

        breaker_info = all_breakers[breaker_name]
        breaker_info["timestamp"] = datetime.utcnow().isoformat()

        return breaker_info
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get circuit breaker details: {str(e)}")


@router.get("/error-stats")
async def get_error_statistics() -> Dict[str, Any]:
    """
    Get aggregated error statistics from all circuit breakers.

    Returns:
        Error statistics by type and service
    """
    try:
        error_recovery = get_error_recovery_service()
        breaker_status = error_recovery.get_status()

        # Aggregate errors by type
        errors_by_type: Dict[str, int] = {}
        errors_by_service: Dict[str, int] = {}

        for service_name, breaker in breaker_status.items():
            stats = breaker["stats"]
            errors_by_service[service_name] = stats["total_errors"]

            for error_type, count in stats["errors_by_type"].items():
                errors_by_type[error_type] = errors_by_type.get(error_type, 0) + count

        # Find most problematic services
        problematic_services = sorted(
            errors_by_service.items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]  # Top 5 problematic services

        return {
            "timestamp": datetime.utcnow().isoformat(),
            "errors_by_type": errors_by_type,
            "errors_by_service": errors_by_service,
            "top_problematic_services": dict(problematic_services),
            "total_errors": sum(errors_by_service.values())
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get error statistics: {str(e)}")


@router.get("/liveness")
async def liveness() -> Dict[str, str]:
    """
    Kubernetes liveness probe endpoint.

    Returns:
        Simple status indicating the service is alive
    """
    return {"status": "alive"}


@router.get("/readiness")
async def readiness() -> Dict[str, Any]:
    """
    Kubernetes readiness probe endpoint.

    Returns:
        Readiness status including critical component checks
    """
    try:
        # Check critical components
        results = await health_monitor.check_all()
        overall_status = health_monitor.get_overall_status(results)
        is_ready = overall_status.value == "healthy"

        # Check if any circuit breakers are open
        error_recovery = get_error_recovery_service()
        breaker_status = error_recovery.get_status()
        critical_breakers_open = any(
            cb["state"] == "open"
            for name, cb in breaker_status.items()
            if name in ["openai", "database", "worker_db"]  # Critical services
        )

        if critical_breakers_open:
            is_ready = False

        return {
            "ready": is_ready,
            "timestamp": datetime.utcnow().isoformat(),
            "checks": {
                "database": "database" in results and results["database"].status.value == "healthy",
                "critical_breakers_closed": not critical_breakers_open
            }
        }
    except Exception as e:
        return {
            "ready": False,
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e)
        }