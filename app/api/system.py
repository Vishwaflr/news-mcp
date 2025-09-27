"""
System Management API
Endpoints for service management, health checks, and system status
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any, List
import asyncio
import logging

from app.core.process_manager import ServiceProcessManager
from app.core.service_registry import get_service_registry, ServiceStatus

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/system", tags=["system"])


# Global process manager instance
_process_manager = None

def get_process_manager() -> ServiceProcessManager:
    """Get the global process manager instance"""
    global _process_manager
    if _process_manager is None:
        _process_manager = ServiceProcessManager()
    return _process_manager


@router.get("/services", summary="Get all service status")
async def get_services_status() -> Dict[str, Any]:
    """Get status of all News MCP services"""
    try:
        manager = get_process_manager()
        status = await manager.get_all_status()

        return {
            "success": True,
            "data": {
                "services": status,
                "timestamp": asyncio.get_event_loop().time()
            }
        }
    except Exception as e:
        logger.error(f"Error getting service status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get service status: {str(e)}")


@router.get("/services/{service_id}/status", summary="Get specific service status")
async def get_service_status(service_id: str) -> Dict[str, Any]:
    """Get status of a specific service"""
    try:
        registry = get_service_registry()
        service_config = registry.get_service(service_id)

        if not service_config:
            raise HTTPException(status_code=404, detail=f"Service '{service_id}' not found")

        manager = get_process_manager()
        status = await manager.get_service_status(service_id)

        return {
            "success": True,
            "data": {
                "service_id": service_id,
                "name": service_config.name,
                "status": status.value,
                "type": service_config.service_type.value,
                "critical": service_config.critical,
                "port": service_config.port,
                "health_endpoint": service_config.health_endpoint
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting service status for {service_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get service status: {str(e)}")


@router.post("/services/start", summary="Start all services")
async def start_services(services: List[str] = None) -> Dict[str, Any]:
    """Start all services or specific services"""
    try:
        manager = get_process_manager()
        success = await manager.start_all_services(services)

        if success:
            return {
                "success": True,
                "message": "Services started successfully",
                "data": {"started_services": services or "all"}
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to start services")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting services: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start services: {str(e)}")


@router.post("/services/stop", summary="Stop all services")
async def stop_services() -> Dict[str, Any]:
    """Stop all services"""
    try:
        manager = get_process_manager()
        success = await manager.stop_all_services()

        if success:
            return {
                "success": True,
                "message": "Services stopped successfully"
            }
        else:
            return {
                "success": False,
                "message": "Some services may not have stopped cleanly"
            }

    except Exception as e:
        logger.error(f"Error stopping services: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to stop services: {str(e)}")


@router.post("/services/{service_id}/restart", summary="Restart specific service")
async def restart_service(service_id: str) -> Dict[str, Any]:
    """Restart a specific service"""
    try:
        registry = get_service_registry()
        service_config = registry.get_service(service_id)

        if not service_config:
            raise HTTPException(status_code=404, detail=f"Service '{service_id}' not found")

        manager = get_process_manager()
        success = await manager.restart_service(service_id)

        if success:
            return {
                "success": True,
                "message": f"Service '{service_config.name}' restarted successfully",
                "data": {"service_id": service_id}
            }
        else:
            raise HTTPException(status_code=500, detail=f"Failed to restart service '{service_id}'")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error restarting service {service_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to restart service: {str(e)}")


@router.get("/health", summary="System health check")
async def system_health_check() -> Dict[str, Any]:
    """Run health checks on all services"""
    try:
        manager = get_process_manager()
        health_status = await manager.health_check_all()

        # Calculate overall health
        total_services = len(health_status)
        healthy_services = sum(1 for status in health_status.values() if status)
        health_percentage = (healthy_services / total_services * 100) if total_services > 0 else 100

        overall_status = "healthy" if health_percentage == 100 else "degraded" if health_percentage >= 50 else "unhealthy"

        return {
            "success": True,
            "data": {
                "overall_status": overall_status,
                "health_percentage": health_percentage,
                "healthy_services": healthy_services,
                "total_services": total_services,
                "services": health_status,
                "timestamp": asyncio.get_event_loop().time()
            }
        }

    except Exception as e:
        logger.error(f"Error during health check: {e}")
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")


@router.get("/registry", summary="Get service registry configuration")
async def get_service_registry_info() -> Dict[str, Any]:
    """Get service registry configuration and dependency information"""
    try:
        registry = get_service_registry()

        services_config = {}
        for service_id, config in registry.get_all_services().items():
            services_config[service_id] = {
                "name": config.name,
                "type": config.service_type.value,
                "command": config.command,
                "port": config.port,
                "depends_on": config.depends_on,
                "health_endpoint": config.health_endpoint,
                "critical": config.critical,
                "max_restart_count": config.max_restart_count,
                "timeout_seconds": config.timeout_seconds
            }

        return {
            "success": True,
            "data": {
                "services": services_config,
                "startup_order": registry.get_startup_order(),
                "shutdown_order": registry.get_shutdown_order(),
                "validation_issues": registry.validate_dependencies()
            }
        }

    except Exception as e:
        logger.error(f"Error getting service registry info: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get registry info: {str(e)}")


@router.get("/dependencies/{service_id}", summary="Get service dependencies")
async def get_service_dependencies(service_id: str) -> Dict[str, Any]:
    """Get dependency information for a specific service"""
    try:
        registry = get_service_registry()
        service_config = registry.get_service(service_id)

        if not service_config:
            raise HTTPException(status_code=404, detail=f"Service '{service_id}' not found")

        dependents = registry.get_dependents(service_id)

        return {
            "success": True,
            "data": {
                "service_id": service_id,
                "name": service_config.name,
                "depends_on": service_config.depends_on,
                "dependents": dependents
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting dependencies for {service_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get dependencies: {str(e)}")