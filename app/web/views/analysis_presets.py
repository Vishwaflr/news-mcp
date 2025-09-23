"""Analysis Control - Preset Management Views"""

from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from app.core.logging_config import get_logger

from app.repositories.analysis_control import AnalysisControlRepo

router = APIRouter(tags=["htmx-analysis-presets"])
logger = get_logger(__name__)


@router.get("/presets", response_class=HTMLResponse)
def get_presets_partial() -> str:
    """Render analysis presets"""
    try:
        control_repo = AnalysisControlRepo()
        presets = control_repo.get_presets()

        if not presets:
            return """
            <div class="text-center text-muted py-4">
                <i class="fas fa-bookmark fa-3x mb-3"></i>
                <p>No saved presets</p>
                <small>Create presets to save common analysis configurations</small>
            </div>
            """

        html = '<div class="row">'

        for preset in presets:
            scope_items = []
            if preset.config.get('feed_ids'):
                scope_items.append(f"{len(preset.config['feed_ids'])} feeds")
            if preset.config.get('category_id'):
                scope_items.append("Category filter")
            if preset.config.get('days_back'):
                scope_items.append(f"Last {preset.config['days_back']} days")

            scope_desc = ", ".join(scope_items) if scope_items else "All items"

            html += f"""
            <div class="col-md-6 mb-3">
                <div class="card">
                    <div class="card-body">
                        <div class="d-flex justify-content-between align-items-start">
                            <div>
                                <h6 class="card-title">{preset.name}</h6>
                                <p class="card-text text-muted small">{preset.description or 'No description'}</p>
                                <p class="card-text">
                                    <small class="text-muted">
                                        <i class="fas fa-filter"></i> {scope_desc}
                                    </small>
                                </p>
                            </div>
                            <div class="btn-group">
                                <button class="btn btn-sm btn-outline-primary"
                                        onclick="loadPreset({preset.id})"
                                        title="Load preset">
                                    <i class="fas fa-play"></i>
                                </button>
                                <button class="btn btn-sm btn-outline-danger"
                                        onclick="deletePreset({preset.id})"
                                        title="Delete preset">
                                    <i class="fas fa-trash"></i>
                                </button>
                            </div>
                        </div>
                        <div class="mt-2">
                            <small class="text-muted">
                                Created: {preset.created_at.strftime('%Y-%m-%d %H:%M')}
                            </small>
                        </div>
                    </div>
                </div>
            </div>
            """

        html += '</div>'
        return html

    except Exception as e:
        logger.error(f"Failed to get presets: {e}")
        return '<div class="alert alert-danger">Failed to load presets</div>'