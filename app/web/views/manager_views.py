"""
HTMX Views for Analysis Manager UI
"""

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
        queue_color = "text-green-600" if total_queued == 0 else "text-yellow-600" if total_queued < 5 else "text-red-600"

        html = f"""
        <div>
            <h3 class="text-lg font-semibold text-gray-200 mb-3">Queue Status</h3>
            <div class="space-y-2">
                <div class="flex justify-between">
                    <span class="text-gray-400">Total Queued:</span>
                    <span class="{queue_color} font-bold">{total_queued}</span>
                </div>
                <div class="flex justify-between">
                    <span class="text-gray-400">High Priority:</span>
                    <span class="font-semibold text-gray-100">{queue['high']}</span>
                </div>
                <div class="flex justify-between">
                    <span class="text-gray-400">Medium Priority:</span>
                    <span class="font-semibold text-gray-100">{queue['medium']}</span>
                </div>
                <div class="flex justify-between">
                    <span class="text-gray-400">Low Priority:</span>
                    <span class="font-semibold text-gray-100">{queue['low']}</span>
                </div>
            </div>
        </div>
        """
        return html
    except Exception as e:
        return f'<div class="text-red-500">Error: {str(e)}</div>'


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
        <div>
            <h3 class="text-lg font-semibold text-gray-200 mb-3">Usage Statistics</h3>
            <div class="space-y-3">
                <div>
                    <div class="flex justify-between mb-1">
                        <span class="text-gray-400 text-sm">Daily Manual:</span>
                        <span class="text-sm">{daily['total_runs']} / {daily['limit_total']}</span>
                    </div>
                    <div class="w-full bg-gray-600 rounded-full h-2">
                        <div class="bg-blue-600 h-2 rounded-full" style="width: {min(daily_percent, 100):.1f}%"></div>
                    </div>
                </div>
                <div>
                    <div class="flex justify-between mb-1">
                        <span class="text-gray-400 text-sm">Daily Auto:</span>
                        <span class="text-sm">{daily['auto_runs']} / {daily['limit_auto']}</span>
                    </div>
                    <div class="w-full bg-gray-600 rounded-full h-2">
                        <div class="bg-green-600 h-2 rounded-full" style="width: {min((daily['auto_runs'] / daily['limit_auto']) * 100, 100):.1f}%"></div>
                    </div>
                </div>
                <div>
                    <div class="flex justify-between mb-1">
                        <span class="text-gray-400 text-sm">Last Hour:</span>
                        <span class="text-sm">{hourly['runs_last_hour']} / {hourly['limit']}</span>
                    </div>
                    <div class="w-full bg-gray-600 rounded-full h-2">
                        <div class="bg-yellow-600 h-2 rounded-full" style="width: {min(hourly_percent, 100):.1f}%"></div>
                    </div>
                </div>
            </div>
        </div>
        """
        return html
    except Exception as e:
        return f'<div class="text-red-500">Error: {str(e)}</div>'


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