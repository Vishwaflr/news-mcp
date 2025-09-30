"""
Analysis Control Repository - Facade

This module now acts as a facade/compatibility layer that delegates to the
split repositories. Maintains backward compatibility while improving maintainability.

Refactored from 765 lines into 3 modules:
- analysis_run_repo.py (Run operations)
- analysis_preview_repo.py (Preview/scope operations)
- analysis_preset_repo.py (Preset management)
"""

from typing import List, Optional
from datetime import datetime
from app.domain.analysis.control import RunScope, RunParams, RunPreview, AnalysisRun, AnalysisPreset, RunStatus
from app.repositories.analysis_run_repo import AnalysisRunRepo
from app.repositories.analysis_preview_repo import AnalysisPreviewRepo
from app.repositories.analysis_preset_repo import AnalysisPresetRepo
from app.core.logging_config import get_logger

logger = get_logger(__name__)


class AnalysisControlRepo:
    """
    Facade repository that delegates to specialized repositories.
    Maintains backward compatibility for existing code.
    """

    # ========== Preview Operations (Delegated to AnalysisPreviewRepo) ==========

    @staticmethod
    def preview_run(scope: RunScope, params: RunParams) -> RunPreview:
        """Preview what a run would analyze without actually starting it"""
        return AnalysisPreviewRepo.preview_run(scope, params)

    @staticmethod
    def _build_scope_query(scope: RunScope, include_analysis_join: bool = True) -> str:
        """Build SQL query based on scope configuration"""
        return AnalysisRunRepo._build_scope_query(scope, include_analysis_join)

    # ========== Run Operations (Delegated to AnalysisRunRepo) ==========

    @staticmethod
    def create_run(scope: RunScope, params: RunParams, triggered_by: str = "manual") -> AnalysisRun:
        """Create a new analysis run"""
        return AnalysisRunRepo.create_run(scope, params, triggered_by)

    @staticmethod
    def _queue_items_for_run(session, run_id: int, scope: RunScope, params: RunParams) -> int:
        """Queue items for analysis run"""
        return AnalysisRunRepo._queue_items_for_run(session, run_id, scope, params)

    @staticmethod
    def get_run_by_id(run_id: int) -> Optional[AnalysisRun]:
        """Get a specific analysis run by ID"""
        return AnalysisRunRepo.get_run_by_id(run_id)

    @staticmethod
    def list_runs(limit: int = 20, since: Optional[datetime] = None) -> List[AnalysisRun]:
        """List analysis runs with optional date filter"""
        return AnalysisRunRepo.list_runs(limit, since)

    @staticmethod
    def get_recent_runs(limit: int = 20, offset: int = 0) -> List[AnalysisRun]:
        """Get recent analysis runs with pagination"""
        return AnalysisRunRepo.get_recent_runs(limit, offset)

    @staticmethod
    def update_run_status(run_id: int, status: RunStatus, error: Optional[str] = None) -> bool:
        """Update the status of an analysis run"""
        return AnalysisRunRepo.update_run_status(run_id, status, error)

    @staticmethod
    def get_active_runs() -> List[AnalysisRun]:
        """Get all active (non-completed) analysis runs"""
        return AnalysisRunRepo.get_active_runs()

    @staticmethod
    def get_run(run_id: int) -> Optional[AnalysisRun]:
        """Get a specific run with detailed information"""
        return AnalysisRunRepo.get_run(run_id)

    # ========== Preset Operations (Delegated to AnalysisPresetRepo) ==========

    @staticmethod
    def save_preset(preset: AnalysisPreset) -> AnalysisPreset:
        """Save or update an analysis preset"""
        return AnalysisPresetRepo.save_preset(preset)

    @staticmethod
    def get_presets() -> List[AnalysisPreset]:
        """Get all analysis presets"""
        return AnalysisPresetRepo.get_presets()

    @staticmethod
    def delete_preset(preset_id: int) -> bool:
        """Delete an analysis preset"""
        return AnalysisPresetRepo.delete_preset(preset_id)