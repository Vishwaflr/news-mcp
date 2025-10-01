"""
Configuration API

API endpoints for reading and updating system configuration.
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any
from app.core.logging_config import get_logger
from app.config import settings
import os

router = APIRouter(prefix="/api/config", tags=["config"])
logger = get_logger(__name__)


@router.get("/analysis")
async def get_analysis_config() -> Dict[str, Any]:
    """Get current analysis configuration"""
    try:
        return {
            "success": True,
            "data": {
                "max_concurrent_runs": settings.max_concurrent_runs,
                "max_daily_runs": settings.max_daily_runs,
                "max_hourly_runs": settings.max_hourly_runs,
                "analysis_batch_limit": settings.analysis_batch_limit,
                "analysis_rps": settings.analysis_rps,
                "analysis_model": settings.analysis_model,
            }
        }
    except Exception as e:
        logger.error(f"Error getting analysis config: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get config: {str(e)}")


@router.post("/analysis")
async def update_analysis_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Update analysis configuration.

    This updates the runtime settings and writes them to .env file.
    """
    try:
        # Update runtime settings
        if "max_concurrent_runs" in config:
            settings.max_concurrent_runs = int(config["max_concurrent_runs"])
        if "max_daily_runs" in config:
            settings.max_daily_runs = int(config["max_daily_runs"])
        if "max_hourly_runs" in config:
            settings.max_hourly_runs = int(config["max_hourly_runs"])
        if "analysis_batch_limit" in config:
            settings.analysis_batch_limit = int(config["analysis_batch_limit"])
        if "analysis_rps" in config:
            settings.analysis_rps = float(config["analysis_rps"])
        if "analysis_model" in config:
            settings.analysis_model = str(config["analysis_model"])

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
        if "max_concurrent_runs" in config:
            env_vars["MAX_CONCURRENT_RUNS"] = str(config["max_concurrent_runs"])
        if "max_daily_runs" in config:
            env_vars["MAX_DAILY_RUNS"] = str(config["max_daily_runs"])
        if "max_hourly_runs" in config:
            env_vars["MAX_HOURLY_RUNS"] = str(config["max_hourly_runs"])
        if "analysis_batch_limit" in config:
            env_vars["ANALYSIS_BATCH_LIMIT"] = str(config["analysis_batch_limit"])
        if "analysis_rps" in config:
            env_vars["ANALYSIS_RPS"] = str(config["analysis_rps"])
        if "analysis_model" in config:
            env_vars["ANALYSIS_MODEL"] = str(config["analysis_model"])

        # Write back to .env
        with open(env_path, 'w') as f:
            for key, value in sorted(env_vars.items()):
                f.write(f"{key}={value}\n")

        logger.info(f"Updated analysis config: {config}")

        return {
            "success": True,
            "message": "Configuration updated successfully",
            "data": {
                "max_concurrent_runs": settings.max_concurrent_runs,
                "max_daily_runs": settings.max_daily_runs,
                "max_hourly_runs": settings.max_hourly_runs,
                "analysis_batch_limit": settings.analysis_batch_limit,
                "analysis_rps": settings.analysis_rps,
                "analysis_model": settings.analysis_model,
            }
        }
    except Exception as e:
        logger.error(f"Error updating analysis config: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update config: {str(e)}")
