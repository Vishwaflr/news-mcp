"""
HTMX Views for Analysis Manager UI
"""

import os
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse
from app.api.analysis_management import get_manager_status, get_queue_status

router = APIRouter()

@router.get("/htmx/manager-status", response_class=HTMLResponse)
async def get_manager_status_view(request: Request):
    """Get current manager status as HTML component."""
    try:
        status = await get_manager_status()
        data = status["data"]

        emergency_class = "text-danger" if data["emergency_stop"] else "text-success"
        emergency_text = "STOPPED" if data["emergency_stop"] else "RUNNING"

        html = f"""
        <div class="card-body">
            <h5 class="card-title">System Status</h5>
            <ul class="list-unstyled mb-0">
                <li class="d-flex justify-content-between mb-2">
                    <span class="text-muted">Status:</span>
                    <span class="{emergency_class} fw-bold">{emergency_text}</span>
                </li>
                <li class="d-flex justify-content-between mb-2">
                    <span class="text-muted">Active Runs:</span>
                    <span class="fw-semibold">{data['active_runs']} / {data['max_concurrent']}</span>
                </li>
                <li class="d-flex justify-content-between mb-2">
                    <span class="text-muted">Max Concurrent:</span>
                    <span class="fw-semibold">{data['max_concurrent']}</span>
                </li>
            </ul>
            <div class="mt-3 pt-3 border-top">
                <small class="text-muted">
                    Limits: {"🔴" if any(data['limits'].values()) else "🟢"} All OK
                </small>
            </div>
        </div>
        """
        return html
    except Exception as e:
        return f'<div class="text-red-500">Error: {str(e)}</div>'


@router.get("/htmx/manager-queue", response_class=HTMLResponse)
async def get_manager_queue_view(request: Request):
    """Get queue status as HTML component."""
    try:
        status = await get_manager_status()
        data = status["data"]
        queue = data["queue_breakdown"]

        total_queued = data["queued_runs"]
        queue_color = "text-success" if total_queued == 0 else "text-warning" if total_queued < 5 else "text-danger"

        html = f"""
        <div class="card-body">
            <h5 class="card-title">Queue Status</h5>
            <ul class="list-unstyled mb-0">
                <li class="d-flex justify-content-between mb-2">
                    <span class="text-muted">Total Queued:</span>
                    <span class="{queue_color} fw-bold">{total_queued}</span>
                </li>
                <li class="d-flex justify-content-between mb-2">
                    <span class="text-muted">High Priority:</span>
                    <span class="fw-semibold">{queue['high']}</span>
                </li>
                <li class="d-flex justify-content-between mb-2">
                    <span class="text-muted">Medium Priority:</span>
                    <span class="fw-semibold">{queue['medium']}</span>
                </li>
                <li class="d-flex justify-content-between mb-2">
                    <span class="text-muted">Low Priority:</span>
                    <span class="fw-semibold">{queue['low']}</span>
                </li>
            </ul>
        </div>
        """
        return html
    except Exception as e:
        return f'<div class="text-danger">Error: {str(e)}</div>'


@router.get("/htmx/manager-daily-stats", response_class=HTMLResponse)
async def get_manager_daily_stats_view(request: Request):
    """Get daily statistics as HTML component."""
    try:
        status = await get_manager_status()
        data = status["data"]
        daily = data["daily_stats"]
        hourly = data["hourly_stats"]

        daily_percent = (daily['total_runs'] / daily['limit_total']) * 100 if daily['limit_total'] > 0 else 0
        hourly_percent = (hourly['runs_last_hour'] / hourly['limit']) * 100 if hourly['limit'] > 0 else 0

        html = f"""
        <div class="card-body">
            <h5 class="card-title">Usage Statistics</h5>
            <div class="mb-3">
                <div class="d-flex justify-content-between mb-1">
                    <small class="text-muted">Daily Manual:</small>
                    <small>{daily['total_runs']} / {daily['limit_total']}</small>
                </div>
                <div class="progress" style="height: 8px;">
                    <div class="progress-bar bg-primary" role="progressbar" style="width: {min(daily_percent, 100):.1f}%" aria-valuenow="{daily_percent:.1f}" aria-valuemin="0" aria-valuemax="100"></div>
                </div>
            </div>
            <div class="mb-3">
                <div class="d-flex justify-content-between mb-1">
                    <small class="text-muted">Daily Auto:</small>
                    <small>{daily['auto_runs']} / {daily['limit_auto']}</small>
                </div>
                <div class="progress" style="height: 8px;">
                    <div class="progress-bar bg-success" role="progressbar" style="width: {min((daily['auto_runs'] / daily['limit_auto']) * 100, 100):.1f}%" aria-valuenow="{(daily['auto_runs'] / daily['limit_auto']) * 100:.1f}" aria-valuemin="0" aria-valuemax="100"></div>
                </div>
            </div>
            <div class="mb-0">
                <div class="d-flex justify-content-between mb-1">
                    <small class="text-muted">Last Hour:</small>
                    <small>{hourly['runs_last_hour']} / {hourly['limit']}</small>
                </div>
                <div class="progress" style="height: 8px;">
                    <div class="progress-bar bg-warning" role="progressbar" style="width: {min(hourly_percent, 100):.1f}%" aria-valuenow="{hourly_percent:.1f}" aria-valuemin="0" aria-valuemax="100"></div>
                </div>
            </div>
        </div>
        """
        return html
    except Exception as e:
        return f'<div class="text-danger">Error: {str(e)}</div>'


@router.get("/htmx/manager-config", response_class=HTMLResponse)
async def get_manager_config_view(request: Request):
    """Get configuration settings as HTML component."""
    try:
        status = await get_manager_status()
        data = status["data"]

        html = f"""
        <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div class="bg-gray-700 p-3 rounded">
                <div class="text-xs text-gray-500 mb-1">Max Concurrent</div>
                <div class="text-2xl font-bold text-blue-600">{data['max_concurrent']}</div>
            </div>
            <div class="bg-gray-700 p-3 rounded">
                <div class="text-xs text-gray-500 mb-1">Daily Manual Limit</div>
                <div class="text-2xl font-bold text-gray-200">{data['daily_stats']['limit_total']}</div>
            </div>
            <div class="bg-gray-700 p-3 rounded">
                <div class="text-xs text-gray-500 mb-1">Daily Auto Limit</div>
                <div class="text-2xl font-bold text-gray-200">{data['daily_stats']['limit_auto']}</div>
            </div>
            <div class="bg-gray-700 p-3 rounded">
                <div class="text-xs text-gray-500 mb-1">Hourly Limit</div>
                <div class="text-2xl font-bold text-gray-200">{data['hourly_stats']['limit']}</div>
            </div>
        </div>
        <div class="mt-4 p-3 bg-blue-900/30 rounded text-sm text-blue-400 border border-blue-800">
            💡 To change these values, edit the .env file or environment variables and restart the services.
        </div>
        """
        return html
    except Exception as e:
        return f'<div class="text-red-500">Error: {str(e)}</div>'


@router.get("/htmx/manager-active-runs", response_class=HTMLResponse)
async def get_manager_active_runs_view(request: Request):
    """Get active runs table as HTML component."""
    try:
        # This would need actual run data from the database
        # For now, showing a placeholder
        html = """
        <div class="overflow-x-auto">
            <table class="w-full text-sm">
                <thead>
                    <tr class="border-b">
                        <th class="text-left py-2">Run ID</th>
                        <th class="text-left py-2">Type</th>
                        <th class="text-left py-2">Status</th>
                        <th class="text-left py-2">Items</th>
                        <th class="text-left py-2">Started</th>
                        <th class="text-left py-2">Actions</th>
                    </tr>
                </thead>
                <tbody id="runs-tbody">
                    <tr>
                        <td colspan="6" class="py-4 text-center text-gray-500">
                            No active runs at the moment
                        </td>
                    </tr>
                </tbody>
            </table>
        </div>
        """
        return html
    except Exception as e:
        return f'<div class="text-red-500">Error: {str(e)}</div>'


@router.get("/htmx/services-status", response_class=HTMLResponse)
async def get_services_status_view(request: Request):
    """Get system services status as HTML component."""
    import subprocess

    try:
        def check_process(pattern: str) -> bool:
            """Check if a process is running."""
            try:
                result = subprocess.run(
                    ["pgrep", "-f", pattern],
                    capture_output=True,
                    text=True,
                    timeout=2
                )
                return result.returncode == 0
            except:
                return False

        def check_port(port: int) -> bool:
            """Check if a port is listening."""
            try:
                # Try ss first (modern replacement for netstat)
                result = subprocess.run(
                    ["ss", "-tuln"],
                    capture_output=True,
                    text=True,
                    timeout=2
                )
                return f":{port}" in result.stdout
            except:
                return False

        # Check services
        services = [
            {
                "name": "API Server",
                "icon": "🌐",
                "status": check_port(8000),
                "description": "FastAPI (Port 8000)",
                "controllable": False
            },
            {
                "name": "MCP Server",
                "icon": "🔌",
                "status": check_process("mcp_server.py"),
                "description": "Model Context Protocol",
                "controllable": False
            },
            {
                "name": "Scheduler",
                "icon": "⏰",
                "status": check_process("scheduler_runner.py"),
                "description": "Scheduled Tasks",
                "controllable": True,
                "service_key": "scheduler"
            },
            {
                "name": "Worker",
                "icon": "⚙️",
                "status": check_process("analysis_worker.py"),
                "description": "Analysis Worker",
                "controllable": True,
                "service_key": "worker"
            }
        ]

        html = '<div class="row g-2">'

        for service in services:
            status_badge = "success" if service["status"] else "danger"
            status_text = "Running" if service["status"] else "Stopped"
            status_icon = "✓" if service["status"] else "✗"

            # Build control buttons if service is controllable
            control_buttons = ""
            if service.get("controllable"):
                service_key = service.get("service_key")
                if service["status"]:
                    control_buttons = f'''
                    <button class="btn btn-sm btn-outline-danger mt-1"
                            hx-post="/htmx/services/{service_key}/stop"
                            hx-target="#services-status"
                            hx-swap="innerHTML">
                        <i class="bi bi-stop-circle"></i> Stop
                    </button>
                    '''
                else:
                    control_buttons = f'''
                    <button class="btn btn-sm btn-outline-success mt-1"
                            hx-post="/htmx/services/{service_key}/start"
                            hx-target="#services-status"
                            hx-swap="innerHTML">
                        <i class="bi bi-play-circle"></i> Start
                    </button>
                    '''

            html += f'''
            <div class="col-md-6">
                <div class="card border-{status_badge}">
                    <div class="card-body py-2 px-3">
                        <div class="d-flex justify-content-between align-items-center">
                            <div>
                                <span class="fs-5 me-2">{service["icon"]}</span>
                                <strong>{service["name"]}</strong>
                                <br>
                                <small class="text-muted">{service["description"]}</small>
                                {control_buttons}
                            </div>
                            <div class="text-end">
                                <span class="badge bg-{status_badge}">{status_icon} {status_text}</span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            '''

        html += '</div>'
        return html

    except Exception as e:
        return f'<div class="text-danger">Error: {str(e)}</div>'


@router.post("/htmx/services/{service}/start", response_class=HTMLResponse)
async def start_service(service: str, request: Request):
    """Start a service."""
    import subprocess
    import os

    try:
        project_dir = "/home/cytrex/news-mcp"

        if service == "scheduler":
            script = os.path.join(project_dir, "scripts", "start-scheduler.sh")
        elif service == "worker":
            script = os.path.join(project_dir, "scripts", "start-worker.sh")
        else:
            raise HTTPException(status_code=400, detail=f"Unknown service: {service}")

        # Execute start script
        result = subprocess.run(
            [script],
            capture_output=True,
            text=True,
            timeout=10,
            cwd=project_dir
        )

        # Return updated status view after brief delay
        import asyncio
        await asyncio.sleep(2)
        return await get_services_status_view(request)

    except Exception as e:
        return f'<div class="alert alert-danger">Failed to start {service}: {str(e)}</div>'


@router.post("/htmx/services/{service}/stop", response_class=HTMLResponse)
async def stop_service(service: str, request: Request):
    """Stop a service."""
    import subprocess

    try:
        if service == "scheduler":
            pid_file = "/tmp/news-mcp-scheduler.pid"
            pattern = "python.*scheduler_runner"
        elif service == "worker":
            pid_file = "/tmp/news-mcp-worker.pid"
            pattern = "python.*analysis_worker"
        else:
            raise HTTPException(status_code=400, detail=f"Unknown service: {service}")

        # Try to stop using PID file first
        if os.path.exists(pid_file):
            with open(pid_file, 'r') as f:
                pid = int(f.read().strip())

            # Send SIGTERM (graceful shutdown)
            subprocess.run(["kill", str(pid)], timeout=2)

            # Wait a moment for graceful shutdown
            import asyncio
            await asyncio.sleep(1)

            # Check if still running, force kill if needed
            check = subprocess.run(["ps", "-p", str(pid)], capture_output=True, timeout=2)
            if check.returncode == 0:
                subprocess.run(["kill", "-9", str(pid)], timeout=2)

            # Remove PID file
            os.remove(pid_file)
        else:
            # Fallback: use pkill
            subprocess.run(["pkill", "-f", pattern], timeout=2)

        # Return updated status view after brief delay
        import asyncio
        await asyncio.sleep(1)
        return await get_services_status_view(request)

    except Exception as e:
        return f'<div class="alert alert-danger">Failed to stop {service}: {str(e)}</div>'