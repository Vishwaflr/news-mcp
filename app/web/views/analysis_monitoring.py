"""Analysis Monitoring Dashboard Views"""

from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from app.core.logging_config import get_logger
from app.services.analysis_run_manager import get_run_manager

router = APIRouter(tags=["htmx-analysis-monitoring"])
logger = get_logger(__name__)

@router.get("/monitoring", response_class=HTMLResponse)
def get_monitoring_dashboard() -> str:
    """Render monitoring dashboard with system limits and health"""
    try:
        run_manager = get_run_manager()
        status = run_manager.get_status()

        # Determine health indicators
        concurrent_status = "success" if not status["limits"]["at_concurrent_limit"] else "warning"
        daily_status = "success" if not status["limits"]["at_daily_limit"] else "danger"
        hourly_status = "success" if not status["limits"]["at_hourly_limit"] else "warning"
        emergency_status = "danger" if status["emergency_stop"] else "success"

        # Calculate percentages for progress bars
        concurrent_pct = (status["active_runs"] / status["max_concurrent"] * 100) if status["max_concurrent"] > 0 else 0
        daily_pct = (status["daily_stats"]["total_runs"] / status["daily_stats"]["limit_total"] * 100) if status["daily_stats"]["limit_total"] > 0 else 0
        hourly_pct = (status["hourly_stats"]["runs_last_hour"] / status["hourly_stats"]["limit"] * 100) if status["hourly_stats"]["limit"] > 0 else 0

        html = f"""
        <div class="row">
            <!-- System Status Card -->
            <div class="col-md-6 mb-3">
                <div class="card">
                    <div class="card-header d-flex justify-content-between align-items-center">
                        <h6 class="mb-0">System Status</h6>
                        <span class="badge bg-{emergency_status}">
                            {'Emergency Stop' if status['emergency_stop'] else 'Operational'}
                        </span>
                    </div>
                    <div class="card-body">
                        <div class="row text-center">
                            <div class="col-4">
                                <div class="h4 text-{concurrent_status}">{status['active_runs']}</div>
                                <small class="text-muted">Active Runs</small>
                            </div>
                            <div class="col-4">
                                <div class="h4 text-{daily_status}">{status['daily_stats']['total_runs']}</div>
                                <small class="text-muted">Today's Runs</small>
                            </div>
                            <div class="col-4">
                                <div class="h4 text-{hourly_status}">{status['hourly_stats']['runs_last_hour']}</div>
                                <small class="text-muted">Last Hour</small>
                            </div>
                        </div>

                        {'<div class="alert alert-danger mt-3"><i class="fas fa-exclamation-triangle"></i> Emergency stop is active!</div>' if status['emergency_stop'] else ''}
                    </div>
                </div>
            </div>

            <!-- Resource Limits Card -->
            <div class="col-md-6 mb-3">
                <div class="card">
                    <div class="card-header">
                        <h6 class="mb-0">Resource Limits</h6>
                    </div>
                    <div class="card-body">
                        <!-- Concurrent Runs -->
                        <div class="mb-3">
                            <div class="d-flex justify-content-between">
                                <small>Concurrent Runs</small>
                                <small>{status['active_runs']}/{status['max_concurrent']}</small>
                            </div>
                            <div class="progress" style="height: 8px;">
                                <div class="progress-bar bg-{concurrent_status}" style="width: {concurrent_pct:.1f}%"></div>
                            </div>
                        </div>

                        <!-- Daily Runs -->
                        <div class="mb-3">
                            <div class="d-flex justify-content-between">
                                <small>Daily Runs</small>
                                <small>{status['daily_stats']['total_runs']}/{status['daily_stats']['limit_total']}</small>
                            </div>
                            <div class="progress" style="height: 8px;">
                                <div class="progress-bar bg-{daily_status}" style="width: {daily_pct:.1f}%"></div>
                            </div>
                        </div>

                        <!-- Hourly Runs -->
                        <div class="mb-0">
                            <div class="d-flex justify-content-between">
                                <small>Hourly Runs</small>
                                <small>{status['hourly_stats']['runs_last_hour']}/{status['hourly_stats']['limit']}</small>
                            </div>
                            <div class="progress" style="height: 8px;">
                                <div class="progress-bar bg-{hourly_status}" style="width: {hourly_pct:.1f}%"></div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <div class="row">
            <!-- Auto-Analysis Stats -->
            <div class="col-md-6 mb-3">
                <div class="card">
                    <div class="card-header">
                        <h6 class="mb-0">Auto-Analysis</h6>
                    </div>
                    <div class="card-body">
                        <div class="row text-center">
                            <div class="col-6">
                                <div class="h5 text-info">{status['daily_stats']['auto_runs']}</div>
                                <small class="text-muted">Auto Runs Today</small>
                            </div>
                            <div class="col-6">
                                <div class="h5 text-secondary">{status['daily_stats']['limit_auto']}</div>
                                <small class="text-muted">Daily Limit</small>
                            </div>
                        </div>

                        <div class="mt-3">
                            <div class="d-flex justify-content-between">
                                <small>Auto Runs Usage</small>
                                <small>{status['daily_stats']['auto_runs']}/{status['daily_stats']['limit_auto']}</small>
                            </div>
                            <div class="progress" style="height: 8px;">
                                <div class="progress-bar bg-info" style="width: {(status['daily_stats']['auto_runs'] / status['daily_stats']['limit_auto'] * 100) if status['daily_stats']['limit_auto'] > 0 else 0:.1f}%"></div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Emergency Controls -->
            <div class="col-md-6 mb-3">
                <div class="card">
                    <div class="card-header">
                        <h6 class="mb-0">Emergency Controls</h6>
                    </div>
                    <div class="card-body">
                        <div class="d-grid gap-2">
                            {'<button class="btn btn-success" onclick="resumeOperations()"><i class="fas fa-play"></i> Resume Operations</button>' if status['emergency_stop'] else '<button class="btn btn-danger" onclick="emergencyStop()"><i class="fas fa-stop"></i> Emergency Stop</button>'}
                        </div>

                        <div class="mt-3">
                            <div class="d-flex justify-content-between align-items-center">
                                <small>Queued Runs:</small>
                                <span class="badge bg-secondary">{status['queued_runs']}</span>
                            </div>
                            <div class="mt-2">
                                <div class="d-flex justify-content-between">
                                    <small class="text-success">High Priority:</small>
                                    <small>{status.get('queue_breakdown', {}).get('high', 0)}</small>
                                </div>
                                <div class="d-flex justify-content-between">
                                    <small class="text-warning">Medium Priority:</small>
                                    <small>{status.get('queue_breakdown', {}).get('medium', 0)}</small>
                                </div>
                                <div class="d-flex justify-content-between">
                                    <small class="text-info">Low Priority:</small>
                                    <small>{status.get('queue_breakdown', {}).get('low', 0)}</small>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <script>
        async function emergencyStop() {{
            if (confirm('Are you sure you want to activate emergency stop? This will halt all analysis processing.')) {{
                try {{
                    const response = await fetch('/api/analysis/manager/emergency-stop', {{
                        method: 'POST',
                        headers: {{'Content-Type': 'application/json'}},
                        body: JSON.stringify({{'reason': 'Manual emergency stop from monitoring dashboard'}})
                    }});
                    const result = await response.json();
                    if (result.success) {{
                        htmx.trigger('#monitoring-dashboard', 'refresh');
                        alert('Emergency stop activated successfully.');
                    }} else {{
                        alert('Failed to activate emergency stop.');
                    }}
                }} catch (error) {{
                    alert('Error activating emergency stop: ' + error.message);
                }}
            }}
        }}

        async function resumeOperations() {{
            if (confirm('Resume normal operations?')) {{
                try {{
                    const response = await fetch('/api/analysis/manager/resume', {{
                        method: 'POST'
                    }});
                    const result = await response.json();
                    if (result.success) {{
                        htmx.trigger('#monitoring-dashboard', 'refresh');
                        alert('Operations resumed successfully.');
                    }} else {{
                        alert('Failed to resume operations.');
                    }}
                }} catch (error) {{
                    alert('Error resuming operations: ' + error.message);
                }}
            }}
        }}
        </script>
        """

        return html

    except Exception as e:
        logger.error(f"Failed to get monitoring dashboard: {e}")
        return f'<div class="alert alert-danger">Failed to load monitoring dashboard: {str(e)}</div>'