"""
Target selection panel endpoint
"""

from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse
from sqlmodel import Session
from app.database import get_session
from app.core.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/htmx/analysis", tags=["htmx"])

@router.get("/target-selection", response_class=HTMLResponse)
async def get_target_selection(db: Session = Depends(get_session)):
    """Get target selection panel with article selection options"""
    try:
        html = """
        <div class="card bg-dark border-secondary">
            <div class="card-header">
                <h6 class="card-title mb-0">🎯 Target Selection</h6>
            </div>
            <div class="card-body">
                <div class="mb-3">
                    <button type="button" class="btn btn-primary btn-sm active" onclick="selectLatestMode(this)">
                        📰 Latest Articles
                    </button>
                    <button type="button" class="btn btn-outline-primary btn-sm" onclick="selectUnanalyzedMode(this)">
                        🔍 Unanalyzed Only
                    </button>
                </div>

                <div class="mb-3">
                    <label for="article-count" class="form-label">Number of articles:</label>
                    <input type="number" class="form-control" id="article-count" value="50" min="1" max="1000">
                </div>

                <div class="active-selection mb-3">
                    <div class="alert alert-success">
                        <strong>✓ Active Selection:</strong> <span id="selection-summary">Latest 50 articles</span>
                    </div>
                </div>

                <button type="button" class="btn btn-success w-100" onclick="applySelection()">
                    ✅ Apply Selection
                </button>
            </div>
        </div>

        <script>
        let currentMode = 'latest';
        let currentCount = 50;

        function selectLatestMode(btn) {
            document.querySelectorAll('.btn').forEach(b => {
                b.classList.remove('btn-primary', 'active');
                b.classList.add('btn-outline-primary');
            });
            btn.classList.add('btn-primary', 'active');
            btn.classList.remove('btn-outline-primary');
            currentMode = 'latest';
            updateSummary();
        }

        function selectUnanalyzedMode(btn) {
            document.querySelectorAll('.btn').forEach(b => {
                b.classList.remove('btn-primary', 'active');
                b.classList.add('btn-outline-primary');
            });
            btn.classList.add('btn-primary', 'active');
            btn.classList.remove('btn-outline-primary');
            currentMode = 'unanalyzed';
            updateSummary();
        }

        function updateSummary() {
            const count = document.getElementById('article-count').value || 50;
            currentCount = count;
            let summary = '';
            if (currentMode === 'latest') {
                summary = 'Latest ' + count + ' articles';
            } else {
                summary = 'Latest ' + count + ' unanalyzed articles';
            }
            document.getElementById('selection-summary').textContent = summary;
        }

        function applySelection() {
            // Update live articles based on selection
            if (window.updateLiveArticles) {
                window.updateLiveArticles(currentMode, currentCount);
            }

            // Feedback
            const btn = event.target;
            const oldText = btn.innerHTML;
            btn.innerHTML = '✅ Applied!';
            setTimeout(() => { btn.innerHTML = oldText; }, 2000);
        }

        // Listen for count changes
        document.getElementById('article-count').addEventListener('input', updateSummary);

        // Initialize
        updateSummary();
        </script>
        """

        return HTMLResponse(html)

    except Exception as e:
        logger.error(f"Error in get_target_selection: {e}")
        return HTMLResponse("""
        <div class="alert alert-danger">
            <i class="bi bi-exclamation-triangle me-2"></i>
            Error loading target selection.
        </div>
        """)
