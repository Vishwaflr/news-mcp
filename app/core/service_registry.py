"""
Service Registry for News MCP
Centralized configuration and management of all services
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set
from enum import Enum
import os


class ServiceType(Enum):
    WEB_SERVER = "web-server"
    SCHEDULER = "scheduler"
    WORKER = "worker"
    DATABASE = "database"
    MCP_SERVER = "mcp-server"


class ServiceStatus(Enum):
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    ERROR = "error"
    UNKNOWN = "unknown"


@dataclass
class ServiceConfig:
    """Configuration for a service"""
    name: str
    service_type: ServiceType
    command: str
    port: Optional[int] = None
    depends_on: List[str] = field(default_factory=list)
    health_endpoint: Optional[str] = None
    max_restart_count: int = 3
    restart_delay: int = 5
    timeout_seconds: int = 30
    critical: bool = True  # If True, failure stops entire system
    log_file: Optional[str] = None
    pid_file: Optional[str] = None


class ServiceRegistry:
    """Registry for all News MCP services"""

    def __init__(self, project_root: str):
        self.project_root = project_root
        self.logs_dir = os.path.join(project_root, "logs")
        self._services = self._initialize_services()

    def _initialize_services(self) -> Dict[str, ServiceConfig]:
        """Initialize all service configurations"""

        # Ensure logs directory exists
        os.makedirs(self.logs_dir, exist_ok=True)

        services = {
            "database": ServiceConfig(
                name="PostgreSQL Database",
                service_type=ServiceType.DATABASE,
                command="",  # External service
                health_endpoint="/health/detailed",
                critical=True,
                depends_on=[],
                timeout_seconds=10
            ),

            "web-server": ServiceConfig(
                name="Web Server",
                service_type=ServiceType.WEB_SERVER,
                command="uvicorn app.main:app --host 0.0.0.0 --port 8000",
                port=8000,
                depends_on=["database"],
                health_endpoint="/health",
                log_file=os.path.join(self.logs_dir, "web-server.log"),
                pid_file=os.path.join(self.project_root, ".web-server.pid"),
                critical=True
            ),

            "scheduler": ServiceConfig(
                name="Feed Scheduler",
                service_type=ServiceType.SCHEDULER,
                command="python -c 'import asyncio; from app.services.feed_scheduler import start_scheduler; asyncio.run(start_scheduler())'",
                depends_on=["database"],
                health_endpoint="/api/scheduler/heartbeat",
                log_file=os.path.join(self.logs_dir, "scheduler.log"),
                pid_file=os.path.join(self.project_root, ".feed-scheduler.pid"),
                critical=True,
                max_restart_count=5  # Scheduler can be more resilient
            ),

            "worker": ServiceConfig(
                name="Analysis Worker",
                service_type=ServiceType.WORKER,
                command="python app/worker/analysis_worker.py --verbose",
                depends_on=["database", "web-server"],
                health_endpoint="/api/worker/status",
                log_file=os.path.join(self.logs_dir, "analysis-worker.log"),
                pid_file=os.path.join(self.project_root, ".analysis-worker.pid"),
                critical=False,  # Worker can fail without stopping system
                max_restart_count=10
            ),

            "mcp-server": ServiceConfig(
                name="MCP HTTP Server",
                service_type=ServiceType.MCP_SERVER,
                command="uvicorn http_mcp_server:app --host 0.0.0.0 --port 8001",
                port=8001,
                depends_on=["database", "web-server"],
                health_endpoint="/health",
                log_file=os.path.join(self.logs_dir, "mcp-http.log"),
                pid_file=os.path.join(self.project_root, ".mcp-server-http.pid"),
                critical=False,  # Optional service
                timeout_seconds=15
            )
        }

        return services

    def get_service(self, service_id: str) -> Optional[ServiceConfig]:
        """Get service configuration by ID"""
        return self._services.get(service_id)

    def get_all_services(self) -> Dict[str, ServiceConfig]:
        """Get all service configurations"""
        return self._services.copy()

    def get_critical_services(self) -> Dict[str, ServiceConfig]:
        """Get only critical services"""
        return {k: v for k, v in self._services.items() if v.critical}

    def get_startup_order(self) -> List[str]:
        """Get services in dependency-resolved startup order"""
        ordered = []
        remaining = set(self._services.keys())

        # Simple dependency resolution (assumes no circular dependencies)
        while remaining:
            # Find services with no unmet dependencies
            ready = []
            for service_id in remaining:
                service = self._services[service_id]
                if all(dep in ordered or dep not in self._services for dep in service.depends_on):
                    ready.append(service_id)

            if not ready:
                # Circular dependency or missing dependency
                remaining_list = list(remaining)
                remaining_list.sort()  # For deterministic behavior
                ready = [remaining_list[0]]  # Force progress

            # Add ready services to order
            for service_id in ready:
                ordered.append(service_id)
                remaining.remove(service_id)

        return ordered

    def get_shutdown_order(self) -> List[str]:
        """Get services in reverse dependency order for shutdown"""
        return list(reversed(self.get_startup_order()))

    def get_dependents(self, service_id: str) -> List[str]:
        """Get services that depend on the given service"""
        dependents = []
        for sid, service in self._services.items():
            if service_id in service.depends_on:
                dependents.append(sid)
        return dependents

    def validate_dependencies(self) -> List[str]:
        """Validate all service dependencies and return any issues"""
        issues = []

        for service_id, service in self._services.items():
            for dep in service.depends_on:
                if dep not in self._services:
                    issues.append(f"Service '{service_id}' depends on unknown service '{dep}'")

        # Check for circular dependencies
        for service_id in self._services:
            visited = set()
            stack = [service_id]

            while stack:
                current = stack.pop()
                if current in visited:
                    issues.append(f"Circular dependency detected involving service '{current}'")
                    break
                visited.add(current)

                current_service = self._services.get(current)
                if current_service:
                    stack.extend(current_service.depends_on)

        return issues


# Global registry instance
_registry = None

def get_service_registry(project_root: str = None) -> ServiceRegistry:
    """Get the global service registry instance"""
    global _registry

    if _registry is None:
        if project_root is None:
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        _registry = ServiceRegistry(project_root)

    return _registry


# Service management constants
DEFAULT_PROJECT_ROOT = "/home/cytrex/news-mcp"
HEALTH_CHECK_INTERVAL = 10  # seconds
MAX_STARTUP_TIME = 60  # seconds
MAX_SHUTDOWN_TIME = 30  # seconds