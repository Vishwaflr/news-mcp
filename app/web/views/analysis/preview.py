"""
Analysis preview & start endpoint
"""

from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi.responses import HTMLResponse
from sqlmodel import Session
from app.database import get_session
from app.core.logging_config import get_logger
from app.services.selection_cache import get_selection_cache

logger = get_logger(__name__)
router = APIRouter(prefix="/htmx/analysis", tags=["htmx"])

@router.get("/preview-start", response_class=HTMLResponse)
async def get_preview_start(
    selection_id: str = Query(..., description="Selection ID from cache"),
    db: Session = Depends(get_session)
):
    """Get preview and start information for cached selection"""
    try:
        cache = get_selection_cache()
        cached_selection = cache.get(selection_id)

        if not cached_selection:
            return HTMLResponse("""
            <div class="alert alert-warning">
                <i class="bi bi-exclamation-triangle me-2"></i>
                Selection not found or expired. Please create a new selection.
            </div>
            """)

        metadata = cached_selection['metadata']
        articles = cached_selection['articles']

        total_count = len(articles)
        analyzed_count = sum(1 for a in articles if a.get('has_analysis'))
        new_items = total_count - analyzed_count

        cost_per_item = 0.0001
        estimated_cost = new_items * cost_per_item

        estimated_minutes = max(1, new_items // 60)

        html = f"""
        <div class="preview-panel p-3 bg-dark rounded">
            <h5 class="mb-3">📊 Preview & Start</h5>

            <div class="row text-center mb-3">
                <div class="col-4">
                    <div class="preview-stat">
                        <div class="stat-value text-info">{total_count}</div>
                        <div class="stat-label text-white">Total Selected</div>
                    </div>
                </div>
                <div class="col-4">
                    <div class="preview-stat">
                        <div class="stat-value text-muted">{analyzed_count}</div>
                        <div class="stat-label text-white">Already Analyzed</div>
                    </div>
                </div>
                <div class="col-4">
                    <div class="preview-stat">
                        <div class="stat-value text-primary">{new_items}</div>
                        <div class="stat-label text-white">To Analyze</div>
                    </div>
                </div>
            </div>

            <div class="row text-center mb-3">
                <div class="col-6">
                    <div class="preview-stat">
                        <div class="stat-value text-success">${estimated_cost:.3f}</div>
                        <div class="stat-label text-white">Estimated Cost</div>
                    </div>
                </div>
                <div class="col-6">
                    <div class="preview-stat">
                        <div class="stat-value text-warning">{estimated_minutes}</div>
                        <div class="stat-label text-white">Est. Minutes</div>
                    </div>
                </div>
            </div>

            <div class="alert alert-info">
                <small>
                    <i class="bi bi-info-circle me-2"></i>
                    {"Ready to analyze " + str(new_items) + " new articles" if new_items > 0 else "No new articles to analyze with current selection"}
                </small>
            </div>
        </div>
        """

        return HTMLResponse(html)

    except Exception as e:
        logger.error(f"Error in get_preview_start: {e}")
        return HTMLResponse(f"""
        <div class="alert alert-danger">
            <i class="bi bi-exclamation-triangle me-2"></i>
            Error loading preview: {str(e)}
        </div>
        """)

