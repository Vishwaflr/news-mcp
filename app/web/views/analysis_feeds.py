"""Analysis Control - Feed Management Views"""

from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from sqlmodel import Session, text
from app.core.logging_config import get_logger

from app.database import engine

router = APIRouter(tags=["htmx-analysis-feeds"])
logger = get_logger(__name__)


@router.get("/feeds", response_class=HTMLResponse)
def get_feeds_partial() -> str:
    """Render feed selection checkboxes"""
    try:
        with Session(engine) as session:
            results = session.execute(text("""
                SELECT f.id, f.title, f.url, COUNT(i.id) as item_count,
                       COUNT(CASE WHEN a.item_id IS NULL THEN 1 END) as unanalyzed_count
                FROM feeds f
                LEFT JOIN items i ON i.feed_id = f.id
                LEFT JOIN item_analysis a ON a.item_id = i.id
                GROUP BY f.id, f.title, f.url
                ORDER BY f.title ASC
            """)).fetchall()

        html = '<div class="row">'
        for row in results:
            feed_id, title, url, item_count, unanalyzed_count = row
            display_title = title or url[:50] + "..."

            html += f"""
            <div class="col-md-6 mb-2">
                <div class="form-check">
                    <input class="form-check-input" type="checkbox" value="{feed_id}"
                           id="feed_{feed_id}" x-model="scope.feed_ids" @change="updatePreview()">
                    <label class="form-check-label" for="feed_{feed_id}">
                        <strong>{display_title}</strong><br>
                        <small class="text-muted">
                            {item_count} items, {unanalyzed_count} unanalyzed
                        </small>
                    </label>
                </div>
            </div>
            """

        html += '</div>'
        return html

    except Exception as e:
        logger.error(f"Failed to get feeds: {e}")
        return '<div class="alert alert-danger">Failed to load feeds</div>'


@router.get("/feeds-list-options", response_class=HTMLResponse)
def get_feeds_list_options() -> str:
    """Render feed options for select dropdown"""
    try:
        with Session(engine) as session:
            results = session.execute(text("""
                SELECT f.id, f.title, f.url, COUNT(i.id) as item_count,
                       COUNT(CASE WHEN a.item_id IS NULL THEN 1 END) as unanalyzed_count
                FROM feeds f
                LEFT JOIN items i ON i.feed_id = f.id
                LEFT JOIN item_analysis a ON a.item_id = i.id
                GROUP BY f.id, f.title, f.url
                ORDER BY f.title ASC
            """)).fetchall()

        html = '<option value="">Select Feed</option>'
        for row in results:
            feed_id, title, url, item_count, unanalyzed_count = row
            display_title = title or url[:50] + "..."
            html += f'<option value="{feed_id}">{display_title} ({unanalyzed_count} unanalyzed)</option>'

        return html

    except Exception as e:
        logger.error(f"Failed to get feed options: {e}")
        return '<option value="">Error loading feeds</option>'