"""
Analysis settings endpoints - Form and SLO
"""

import fastapi
from fastapi import APIRouter, Depends, Form
from fastapi.responses import HTMLResponse
from sqlmodel import Session, text
from app.database import get_session
from app.core.logging_config import get_logger
from datetime import datetime

logger = get_logger(__name__)
router = APIRouter(prefix="/htmx/analysis", tags=["htmx"])

@router.get("/settings/form", response_class=HTMLResponse)
async def get_settings_form(db: Session = Depends(get_session)):
    """Get analysis settings form"""
    try:
        # Get current default settings (could be from database or config)
        html = """
        <div class="card">
            <div class="card-header">
                <h6 class="card-title mb-0">
                    <i class="bi bi-gear me-2"></i>Analysis Settings
                </h6>
            </div>
            <div class="card-body">
                <form hx-post="/api/user-settings/default-params" hx-trigger="submit" hx-swap="outerHTML">
                    <div class="row g-3">
                        <div class="col-md-6">
                            <label for="model_tag" class="form-label">AI Model</label>
                            <select class="form-select" id="model_tag" name="model_tag">
                                <option value="gpt-4.1-nano" selected>GPT-4.1 Nano (Fast)</option>
                                <option value="gpt-4.1">GPT-4.1 (Standard)</option>
                                <option value="gpt-4.1-pro">GPT-4.1 Pro (Detailed)</option>
                            </select>
                        </div>
                        <div class="col-md-6">
                            <label for="batch_size" class="form-label">Batch Size</label>
                            <select class="form-select" id="batch_size" name="batch_size">
                                <option value="5" selected>5 articles</option>
                                <option value="10">10 articles</option>
                                <option value="25">25 articles</option>
                                <option value="50">50 articles</option>
                            </select>
                        </div>
                        <div class="col-md-6">
                            <label for="temperature" class="form-label">Temperature</label>
                            <input type="range" class="form-range" id="temperature" name="temperature"
                                   min="0" max="1" step="0.1" value="0.3">
                            <div class="form-text">
                                <span id="temperature-value">0.3</span> - Lower = more focused, Higher = more creative
                            </div>
                        </div>
                        <div class="col-md-6">
                            <label for="timeout" class="form-label">Timeout (seconds)</label>
                            <input type="number" class="form-control" id="timeout" name="timeout"
                                   min="30" max="300" value="120">
                        </div>
                    </div>
                    <div class="row g-3 mt-3">
                        <div class="col-12">
                            <div class="form-check">
                                <input class="form-check-input" type="checkbox" id="auto_analyze"
                                       name="auto_analyze" checked>
                                <label class="form-check-label" for="auto_analyze">
                                    Enable automatic analysis for new articles
                                </label>
                            </div>
                        </div>
                        <div class="col-12">
                            <div class="form-check">
                                <input class="form-check-input" type="checkbox" id="include_content"
                                       name="include_content">
                                <label class="form-check-label" for="include_content">
                                    Include full article content in analysis (slower but more detailed)
                                </label>
                            </div>
                        </div>
                    </div>
                    <div class="mt-4">
                        <button type="submit" class="btn btn-primary">
                            <i class="bi bi-save me-2"></i>Save Settings
                        </button>
                        <button type="button" class="btn btn-outline-secondary ms-2"
                                onclick="this.closest('form').reset()">
                            <i class="bi bi-arrow-clockwise me-2"></i>Reset
                        </button>
                    </div>
                </form>
            </div>
        </div>

        <script>
        // Update temperature display
        document.getElementById('temperature').addEventListener('input', function(e) {
            document.getElementById('temperature-value').textContent = e.target.value;
        });
        </script>
        """

        return HTMLResponse(html)

    except Exception as e:
        logger.error(f"Error in get_settings_form: {e}")
        return HTMLResponse("""
        <div class="alert alert-danger">
            <i class="bi bi-exclamation-triangle me-2"></i>
            Error loading settings form.
        </div>
        """)


@router.get("/settings/slo", response_class=HTMLResponse)
async def get_settings_slo(db: Session = Depends(get_session)):
    """Get SLO (Service Level Objectives) settings"""
    try:
        # Try to get current SLO metrics from database (table may not exist yet)
        try:
            slo_stats = db.execute(text("""
            SELECT
                COUNT(*) as total_runs,
                AVG(
                    CASE WHEN completed_at IS NOT NULL AND started_at IS NOT NULL
                    THEN EXTRACT(EPOCH FROM (completed_at - started_at)) / 60.0
                    END
                ) as avg_duration_minutes,
                COUNT(CASE WHEN status = 'completed' THEN 1 END) * 100.0 /
                    NULLIF(COUNT(CASE WHEN status IN ('completed', 'failed') THEN 1 END), 0) as success_rate
            FROM analysis_runs
            WHERE created_at > NOW() - INTERVAL '24 hours'
            """)).fetchone()
        except Exception:
            # Fallback to dummy data if table doesn't exist
            slo_stats = (0, 0, 100.0)

        total_runs, avg_duration, success_rate = slo_stats or (0, 0, 0)

        # SLO targets
        target_success_rate = 95.0
        target_max_duration = 30.0  # minutes

        # Status indicators
        success_status = "success" if (success_rate or 0) >= target_success_rate else "danger"
        duration_status = "success" if (avg_duration or 0) <= target_max_duration else "warning"

        html = f"""
        <div class="card">
            <div class="card-header">
                <h6 class="card-title mb-0">
                    <i class="bi bi-speedometer2 me-2"></i>Service Level Objectives
                </h6>
            </div>
            <div class="card-body">
                <div class="row g-3">
                    <div class="col-md-6">
                        <div class="d-flex justify-content-between align-items-center">
                            <div>
                                <div class="fw-semibold">Success Rate</div>
                                <div class="text-muted small">Last 24 hours</div>
                            </div>
                            <div class="text-end">
                                <div class="fs-4 fw-bold text-{success_status}">
                                    {success_rate:.1f}%
                                </div>
                                <div class="small text-muted">Target: {target_success_rate}%</div>
                            </div>
                        </div>
                        <div class="progress mt-2" style="height: 8px;">
                            <div class="progress-bar bg-{success_status}"
                                 style="width: {min(100, success_rate or 0):.1f}%"></div>
                        </div>
                    </div>
                    <div class="col-md-6">
                        <div class="d-flex justify-content-between align-items-center">
                            <div>
                                <div class="fw-semibold">Average Duration</div>
                                <div class="text-muted small">Per analysis run</div>
                            </div>
                            <div class="text-end">
                                <div class="fs-4 fw-bold text-{duration_status}">
                                    {avg_duration:.1f}m
                                </div>
                                <div class="small text-muted">Target: <{target_max_duration}m</div>
                            </div>
                        </div>
                        <div class="progress mt-2" style="height: 8px;">
                            <div class="progress-bar bg-{duration_status}"
                                 style="width: {min(100, (avg_duration or 0) / target_max_duration * 100):.1f}%"></div>
                        </div>
                    </div>
                </div>
                <hr class="my-3">
                <div class="row g-3">
                    <div class="col-md-4 text-center">
                        <div class="fs-3 fw-bold text-primary">{total_runs}</div>
                        <div class="text-muted">Total Runs Today</div>
                    </div>
                    <div class="col-md-4 text-center">
                        <div class="fs-3 fw-bold text-info">
                            {(success_rate * total_runs / 100):.0f}
                        </div>
                        <div class="text-muted">Successful Runs</div>
                    </div>
                    <div class="col-md-4 text-center">
                        <div class="fs-3 fw-bold text-warning">
                            {total_runs - (success_rate * total_runs / 100):.0f}
                        </div>
                        <div class="text-muted">Failed Runs</div>
                    </div>
                </div>
                <div class="mt-3">
                    <small class="text-muted">
                        <i class="bi bi-clock me-1"></i>
                        Last updated: {datetime.now().strftime('%H:%M:%S')}
                        <span class="ms-3">
                            <i class="bi bi-arrow-clockwise me-1"></i>
                            Auto-refresh: 30s
                        </span>
                    </small>
                </div>
            </div>
        </div>
        """

        return HTMLResponse(html)

    except Exception as e:
        logger.error(f"Error in get_settings_slo: {e}")
        return HTMLResponse("""
        <div class="alert alert-danger">
            <i class="bi bi-exclamation-triangle me-2"></i>
            Error loading SLO metrics.
        </div>
        """)


@router.post("/analysis-config", response_class=HTMLResponse)
async def save_analysis_config(
    max_concurrent_runs: int = Form(...),
    max_daily_runs: int = Form(...),
    max_hourly_runs: int = Form(...),
    analysis_batch_limit: int = Form(...),
    analysis_rps: float = Form(...),
    analysis_model: str = Form(...)
):
    """Save analysis configuration via HTMX"""
    from app.config import settings
    import os

    try:
        # Update runtime settings
        settings.max_concurrent_runs = max_concurrent_runs
        settings.max_daily_runs = max_daily_runs
        settings.max_hourly_runs = max_hourly_runs
        settings.analysis_batch_limit = analysis_batch_limit
        settings.analysis_rps = analysis_rps
        settings.analysis_model = analysis_model

        # Update .env file
        env_path = os.path.join(os.getcwd(), ".env")
        env_vars = {}

        # Read existing .env
        if os.path.exists(env_path):
            with open(env_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        env_vars[key.strip()] = value.strip()

        # Update values
        env_vars["MAX_CONCURRENT_RUNS"] = str(max_concurrent_runs)
        env_vars["MAX_DAILY_RUNS"] = str(max_daily_runs)
        env_vars["MAX_HOURLY_RUNS"] = str(max_hourly_runs)
        env_vars["ANALYSIS_BATCH_LIMIT"] = str(analysis_batch_limit)
        env_vars["ANALYSIS_RPS"] = str(analysis_rps)
        env_vars["ANALYSIS_MODEL"] = analysis_model

        # Write back to .env
        with open(env_path, 'w') as f:
            for key, value in sorted(env_vars.items()):
                f.write(f"{key}={value}\n")

        logger.info(f"Updated analysis config: concurrent={max_concurrent_runs}, daily={max_daily_runs}, hourly={max_hourly_runs}")

        # Return updated view
        return HTMLResponse(f"""
        <div id="analysis-config-view" class="row small">
            <div class="col-md-3">
                <strong>Concurrent:</strong> <span id="view-max-concurrent">{max_concurrent_runs}</span>
            </div>
            <div class="col-md-3">
                <strong>Daily Limit:</strong> <span id="view-max-daily">{max_daily_runs}</span>
            </div>
            <div class="col-md-3">
                <strong>Hourly Limit:</strong> <span id="view-max-hourly">{max_hourly_runs}</span>
            </div>
            <div class="col-md-3">
                <strong>Batch Size:</strong> <span id="view-batch-limit">{analysis_batch_limit}</span>
            </div>
        </div>
        <script>
            // Hide form and show view
            document.getElementById('analysis-config-edit').style.display = 'none';
            document.getElementById('analysis-config-view').parentElement.querySelector('#analysis-config-view').style.display = 'block';

            // Show success toast
            const toast = document.createElement('div');
            toast.className = 'alert alert-success position-fixed top-0 end-0 m-3';
            toast.style.zIndex = '9999';
            toast.innerHTML = '<i class="bi bi-check-circle me-2"></i>Configuration saved successfully!';
            document.body.appendChild(toast);
            setTimeout(() => toast.remove(), 3000);
        </script>
        """)
    except Exception as e:
        logger.error(f"Error saving analysis config: {e}")
        return HTMLResponse(f"""
        <div class="alert alert-danger">
            <i class="bi bi-exclamation-triangle me-2"></i>
            Error saving configuration: {str(e)}
        </div>
        """)
