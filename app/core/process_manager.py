"""
Process Manager for News MCP Services
Handles lifecycle management, health monitoring, and orchestration
"""

import asyncio
import os
import signal
import subprocess
import time
import psutil
import httpx
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path
import logging

from .service_registry import (
    ServiceRegistry, ServiceConfig, ServiceStatus, ServiceType,
    get_service_registry, HEALTH_CHECK_INTERVAL, MAX_STARTUP_TIME, MAX_SHUTDOWN_TIME
)

logger = logging.getLogger(__name__)


@dataclass
class ProcessInfo:
    """Information about a running process"""
    pid: int
    started_at: float
    restart_count: int = 0
    last_restart: Optional[float] = None
    status: ServiceStatus = ServiceStatus.RUNNING


class ServiceProcessManager:
    """Manages all News MCP service processes"""

    def __init__(self, project_root: str = None):
        self.registry = get_service_registry(project_root)
        self.processes: Dict[str, ProcessInfo] = {}
        self.process_group_id: Optional[int] = None
        self.shutdown_requested = False

    async def start_all_services(self, services: Optional[List[str]] = None) -> bool:
        """Start all services in dependency order"""
        if services is None:
            services = self.registry.get_startup_order()

        logger.info(f"Starting services: {services}")

        # Validate dependencies first
        issues = self.registry.validate_dependencies()
        if issues:
            logger.error(f"Dependency validation failed: {issues}")
            return False

        # Create new process group for all services
        self.process_group_id = os.getpgrp()
        logger.info(f"Created process group: {self.process_group_id}")

        success = True
        started_services = []

        try:
            for service_id in services:
                service = self.registry.get_service(service_id)
                if not service:
                    logger.error(f"Unknown service: {service_id}")
                    success = False
                    break

                # Skip external services like database
                if service.service_type == ServiceType.DATABASE:
                    logger.info(f"Skipping external service: {service_id}")
                    continue

                logger.info(f"Starting service: {service.name}")
                if await self._start_service(service_id, service):
                    started_services.append(service_id)
                    logger.info(f"✅ Service started: {service.name}")
                else:
                    logger.error(f"❌ Failed to start service: {service.name}")
                    if service.critical:
                        success = False
                        break

        except Exception as e:
            logger.error(f"Error starting services: {e}")
            success = False

        if not success:
            logger.warning("Stopping previously started services due to failure")
            for service_id in reversed(started_services):
                await self._stop_service(service_id)

        return success

    async def stop_all_services(self, timeout: int = MAX_SHUTDOWN_TIME) -> bool:
        """Stop all services in reverse dependency order"""
        self.shutdown_requested = True
        services = self.registry.get_shutdown_order()

        logger.info(f"Stopping services: {services}")

        success = True
        for service_id in services:
            if service_id in self.processes:
                if not await self._stop_service(service_id, timeout // len(services)):
                    success = False

        # Clean up process group
        if self.process_group_id:
            try:
                os.killpg(self.process_group_id, signal.SIGTERM)
                logger.info(f"Terminated process group: {self.process_group_id}")
            except ProcessLookupError:
                pass

        self.process_group_id = None
        self.shutdown_requested = False
        return success

    async def restart_service(self, service_id: str) -> bool:
        """Restart a specific service"""
        logger.info(f"Restarting service: {service_id}")

        service = self.registry.get_service(service_id)
        if not service:
            logger.error(f"Unknown service: {service_id}")
            return False

        # Stop service first
        await self._stop_service(service_id)

        # Wait a moment before restart
        await asyncio.sleep(service.restart_delay)

        # Start service
        return await self._start_service(service_id, service)

    async def get_service_status(self, service_id: str) -> ServiceStatus:
        """Get current status of a service"""
        service = self.registry.get_service(service_id)
        if not service:
            return ServiceStatus.UNKNOWN

        # For external services, check health endpoint
        if service.service_type == ServiceType.DATABASE:
            return await self._check_service_health(service)

        # Check process status
        if service_id not in self.processes:
            return ServiceStatus.STOPPED

        process_info = self.processes[service_id]
        try:
            process = psutil.Process(process_info.pid)
            if process.is_running():
                return ServiceStatus.RUNNING
            else:
                return ServiceStatus.STOPPED
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return ServiceStatus.STOPPED

    async def get_all_status(self) -> Dict[str, Dict]:
        """Get status of all services"""
        status = {}

        for service_id, service in self.registry.get_all_services().items():
            service_status = await self.get_service_status(service_id)

            status[service_id] = {
                "name": service.name,
                "status": service_status.value,
                "type": service.service_type.value,
                "critical": service.critical,
                "port": service.port,
                "health_endpoint": service.health_endpoint
            }

            # Add process info if available
            if service_id in self.processes:
                process_info = self.processes[service_id]
                status[service_id].update({
                    "pid": process_info.pid,
                    "started_at": process_info.started_at,
                    "restart_count": process_info.restart_count,
                    "last_restart": process_info.last_restart
                })

        return status

    async def health_check_all(self) -> Dict[str, bool]:
        """Run health checks on all services"""
        health_status = {}

        for service_id, service in self.registry.get_all_services().items():
            if service.health_endpoint:
                service_status = await self._check_service_health(service)
                health_status[service_id] = service_status == ServiceStatus.RUNNING
            else:
                # Basic process check
                process_status = await self.get_service_status(service_id)
                health_status[service_id] = process_status == ServiceStatus.RUNNING

        return health_status

    async def _start_service(self, service_id: str, service: ServiceConfig) -> bool:
        """Start a single service"""
        try:
            # Check if already running
            if service_id in self.processes:
                current_status = await self.get_service_status(service_id)
                if current_status == ServiceStatus.RUNNING:
                    logger.warning(f"Service {service_id} is already running")
                    return True

            # Create environment
            env = os.environ.copy()
            env["PYTHONPATH"] = self.registry.project_root

            # Prepare command
            cmd = service.command
            if service.service_type in [ServiceType.SCHEDULER, ServiceType.WORKER]:
                # Python services need venv activation
                venv_python = os.path.join(self.registry.project_root, "venv", "bin", "python")
                if os.path.exists(venv_python):
                    cmd = cmd.replace("python", venv_python, 1)

            # Start process
            if service.log_file:
                log_path = Path(service.log_file)
                log_path.parent.mkdir(exist_ok=True)
                with open(service.log_file, "a") as log_file:
                    process = await asyncio.create_subprocess_shell(
                        cmd,
                        stdout=log_file,
                        stderr=subprocess.STDOUT,
                        cwd=self.registry.project_root,
                        env=env,
                        preexec_fn=os.setpgrp if self.process_group_id else None
                    )
            else:
                process = await asyncio.create_subprocess_shell(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    cwd=self.registry.project_root,
                    env=env,
                    preexec_fn=os.setpgrp if self.process_group_id else None
                )

            # Store process info
            self.processes[service_id] = ProcessInfo(
                pid=process.pid,
                started_at=time.time()
            )

            # Write PID file if configured
            if service.pid_file:
                with open(service.pid_file, "w") as f:
                    f.write(str(process.pid))

            # Wait for service to be ready
            if service.port or service.health_endpoint:
                ready = await self._wait_for_service_ready(service, service.timeout_seconds)
                if not ready:
                    logger.error(f"Service {service_id} failed to become ready")
                    await self._stop_service(service_id)
                    return False

            return True

        except Exception as e:
            logger.error(f"Failed to start service {service_id}: {e}")
            return False

    async def _stop_service(self, service_id: str, timeout: int = 10) -> bool:
        """Stop a single service"""
        if service_id not in self.processes:
            logger.warning(f"Service {service_id} is not tracked")
            return True

        process_info = self.processes[service_id]
        service = self.registry.get_service(service_id)

        try:
            # Try graceful shutdown first
            process = psutil.Process(process_info.pid)
            process.terminate()

            # Wait for graceful shutdown
            try:
                process.wait(timeout=timeout // 2)
                logger.info(f"Service {service_id} stopped gracefully")
            except psutil.TimeoutExpired:
                # Force kill if graceful shutdown failed
                logger.warning(f"Force killing service {service_id}")
                process.kill()
                process.wait(timeout=timeout // 2)

        except (psutil.NoSuchProcess, psutil.AccessDenied):
            logger.info(f"Service {service_id} was already stopped")

        # Clean up
        del self.processes[service_id]

        # Remove PID file
        if service and service.pid_file and os.path.exists(service.pid_file):
            os.unlink(service.pid_file)

        return True

    async def _wait_for_service_ready(self, service: ServiceConfig, timeout: int) -> bool:
        """Wait for service to be ready (port listening or health check passing)"""
        start_time = time.time()

        while time.time() - start_time < timeout:
            if service.port:
                # Check if port is listening
                try:
                    reader, writer = await asyncio.open_connection("127.0.0.1", service.port)
                    writer.close()
                    await writer.wait_closed()
                    return True
                except (ConnectionRefusedError, OSError):
                    pass

            if service.health_endpoint:
                # Try health check
                health_status = await self._check_service_health(service)
                if health_status == ServiceStatus.RUNNING:
                    return True

            await asyncio.sleep(1)

        return False

    async def _check_service_health(self, service: ServiceConfig) -> ServiceStatus:
        """Check service health via HTTP endpoint"""
        if not service.health_endpoint:
            return ServiceStatus.UNKNOWN

        try:
            base_url = f"http://localhost:{service.port or 8000}"
            url = f"{base_url}{service.health_endpoint}"

            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(url)
                if response.status_code == 200:
                    return ServiceStatus.RUNNING
                else:
                    return ServiceStatus.ERROR

        except Exception as e:
            logger.debug(f"Health check failed for {service.name}: {e}")
            return ServiceStatus.ERROR