"""
Analysis statistics endpoint
"""

from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse
from sqlmodel import Session, text
from app.database import get_session
from app.core.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/htmx/analysis", tags=["htmx"])


@router.get("/stats-horizontal", response_class=HTMLResponse)
async def get_stats_horizontal(db: Session = Depends(get_session)):
    """Get horizontal statistics display"""
    try:
        try:
            total_items = db.execute(text("SELECT COUNT(*) FROM items")).scalar() or 0
        except:
            total_items = 0

        try:
            analyzed_items = db.execute(text("SELECT COUNT(DISTINCT item_id) FROM item_analysis WHERE item_id IS NOT NULL")).scalar() or 0
        except:
            analyzed_items = 0

        try:
            active_feeds = db.execute(text("SELECT COUNT(*) FROM feeds WHERE status = 'ACTIVE'")).scalar() or 0
        except:
            active_feeds = 0

        try:
            active_runs = db.execute(text("SELECT COUNT(*) FROM analysis_runs WHERE status = 'running'")).scalar() or 0
        except:
            active_runs = 0

        stats = (total_items, analyzed_items, active_feeds, active_runs)

        total, analyzed, feeds, runs = stats or (0, 0, 0, 0)
        coverage = (analyzed / total * 100) if total > 0 else 0

        html = f"""
        <div class="row g-3">
            <div class="col-md-3">
                <div class="stat-card">
                    <div class="stat-value">{total:,}</div>
                    <div class="stat-label">Total Articles</div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="stat-card">
                    <div class="stat-value">{analyzed:,}</div>
                    <div class="stat-label">Analyzed</div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="stat-card">
                    <div class="stat-value">{coverage:.1f}%</div>
                    <div class="stat-label">Coverage</div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="stat-card">
                    <div class="stat-value">{runs}</div>
                    <div class="stat-label">Active Runs</div>
                </div>
            </div>
        </div>
        """

        return HTMLResponse(html)

    except Exception as e:
        logger.error(f"Error in get_stats_horizontal: {e}")
        return HTMLResponse('<div class="alert alert-warning">Unable to load statistics</div>')