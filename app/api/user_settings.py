from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session, select
from typing import Dict, Any
from app.core.logging_config import get_logger

from app.database import get_session
from app.models import UserSettings
from app.domain.analysis.control import RunParams

router = APIRouter(prefix="/user-settings", tags=["user-settings"])
logger = get_logger(__name__)

@router.get("/default-params")
async def get_default_params(session: Session = Depends(get_session)) -> Dict[str, Any]:
    """Get default analysis parameters from database"""
    try:
        # Get or create default settings
        settings = session.exec(
            select(UserSettings).where(UserSettings.user_id == "default")
        ).first()

        if not settings:
            # Create default settings if none exist
            settings = UserSettings(
                user_id="default",
                default_limit=200,
                default_rate_per_second=1.0,
                default_model_tag="gpt-4.1-nano",
                default_dry_run=False,
                default_override_existing=False
            )
            session.add(settings)
            session.commit()
            session.refresh(settings)

        return {
            "limit": settings.default_limit,
            "rate_per_second": settings.default_rate_per_second,
            "model_tag": settings.default_model_tag,
            "dry_run": settings.default_dry_run,
            "override_existing": settings.default_override_existing
        }

    except Exception as e:
        logger.error(f"Failed to get default params: {e}")
        # Return hardcoded defaults as fallback
        return {
            "limit": 200,
            "rate_per_second": 1.0,
            "model_tag": "gpt-4.1-nano",
            "dry_run": False,
            "override_existing": False
        }

@router.post("/default-params")
async def save_default_params(
    params: RunParams,
    session: Session = Depends(get_session)
) -> Dict[str, str]:
    """Save default analysis parameters to database"""
    try:
        # Get existing settings or create new
        settings = session.exec(
            select(UserSettings).where(UserSettings.user_id == "default")
        ).first()

        if settings:
            # Update existing
            settings.default_limit = params.limit
            settings.default_rate_per_second = params.rate_per_second
            settings.default_model_tag = params.model_tag
            settings.default_dry_run = params.dry_run
            settings.default_override_existing = params.override_existing
        else:
            # Create new
            settings = UserSettings(
                user_id="default",
                default_limit=params.limit,
                default_rate_per_second=params.rate_per_second,
                default_model_tag=params.model_tag,
                default_dry_run=params.dry_run,
                default_override_existing=params.override_existing
            )
            session.add(settings)

        session.commit()
        session.refresh(settings)

        logger.info(f"Saved default params: limit={params.limit}, rate={params.rate_per_second}, model={params.model_tag}")

        return {"status": "success", "message": "Default parameters saved"}

    except Exception as e:
        logger.error(f"Failed to save default params: {e}")
        session.rollback()
        raise HTTPException(status_code=500, detail=str(e))