"""
Analysis Preset Repository

Handles preset management for analysis configurations.
Split from analysis_control.py for better maintainability.
"""

from typing import List, Optional
from datetime import datetime
from sqlmodel import Session, select
from app.database import engine
from app.models.analysis import AnalysisPreset
from app.core.logging_config import get_logger

logger = get_logger(__name__)


class AnalysisPresetRepo:
    """Repository for analysis preset operations"""

    @staticmethod
    def save_preset(preset: AnalysisPreset) -> AnalysisPreset:
        """Save or update an analysis preset"""
        with Session(engine) as session:
            # If it's a default preset, unset other defaults
            if preset.is_default:
                existing_defaults = session.exec(
                    select(AnalysisPreset).where(AnalysisPreset.is_default == True)
                ).all()

                for existing in existing_defaults:
                    existing.is_default = False
                    session.add(existing)

            # Save the preset
            if preset.id:
                # Update existing
                existing = session.get(AnalysisPreset, preset.id)
                if existing:
                    existing.name = preset.name
                    existing.description = preset.description
                    existing.scope_config = preset.scope_config
                    existing.params_config = preset.params_config
                    existing.is_default = preset.is_default
                    existing.updated_at = datetime.utcnow()
                    session.add(existing)
                    session.commit()
                    session.refresh(existing)
                    return existing

            # Create new
            preset.created_at = datetime.utcnow()
            preset.updated_at = datetime.utcnow()
            session.add(preset)
            session.commit()
            session.refresh(preset)

            logger.info(f"Saved preset {preset.id}: {preset.name}")
            return preset

    @staticmethod
    def get_presets() -> List[AnalysisPreset]:
        """Get all analysis presets"""
        with Session(engine) as session:
            query = select(AnalysisPreset).order_by(
                AnalysisPreset.is_default.desc(),
                AnalysisPreset.created_at.desc()
            )
            return session.exec(query).all()

    @staticmethod
    def get_preset_by_id(preset_id: int) -> Optional[AnalysisPreset]:
        """Get a specific preset by ID"""
        with Session(engine) as session:
            return session.get(AnalysisPreset, preset_id)

    @staticmethod
    def get_default_preset() -> Optional[AnalysisPreset]:
        """Get the default preset if one exists"""
        with Session(engine) as session:
            query = select(AnalysisPreset).where(AnalysisPreset.is_default == True)
            return session.exec(query).first()

    @staticmethod
    def delete_preset(preset_id: int) -> bool:
        """Delete an analysis preset"""
        with Session(engine) as session:
            preset = session.get(AnalysisPreset, preset_id)
            if not preset:
                return False

            session.delete(preset)
            session.commit()
            logger.info(f"Deleted preset {preset_id}")
            return True

    @staticmethod
    def update_preset_usage(preset_id: int) -> bool:
        """Update the last used timestamp for a preset"""
        with Session(engine) as session:
            preset = session.get(AnalysisPreset, preset_id)
            if not preset:
                return False

            preset.updated_at = datetime.utcnow()
            session.commit()
            return True