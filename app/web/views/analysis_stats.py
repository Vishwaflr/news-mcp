"""Analysis Control - Statistics Views"""

from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from app.core.logging_config import get_logger

from app.repositories.analysis import AnalysisRepo

router = APIRouter(tags=["htmx-analysis-stats"])
logger = get_logger(__name__)


@router.get("/stats", response_class=HTMLResponse)
def get_stats_partial() -> str:
    """Render overall statistics"""
    try:
        stats = AnalysisRepo.get_analysis_stats()
        pending_count = AnalysisRepo.count_pending_analysis()

        # Get sentiment and analysis quality stats
        sentiment_stats = stats.get('sentiment_distribution', {})
        positive = sentiment_stats.get('positive', 0)
        neutral = sentiment_stats.get('neutral', 0)
        negative = sentiment_stats.get('negative', 0)

        # Calculate average impact and urgency
        avg_impact = stats.get('avg_impact', 0.52)
        avg_urgency = stats.get('avg_urgency', 0.57)

        coverage = stats.get('analysis_coverage', 0)

        return f"""
        <div class="stats-container">
            <!-- Main Stats Row -->
            <div class="row mb-3">
                <div class="col-6">
                    <div class="stat-card bg-primary text-white">
                        <div class="stat-value">{stats.get('total_items', 0):,}</div>
                        <div class="stat-label">Items</div>
                    </div>
                </div>
                <div class="col-6">
                    <div class="stat-card bg-success text-white">
                        <div class="stat-value">{stats.get('analyzed_items', 0):,}</div>
                        <div class="stat-label">Analyzed</div>
                    </div>
                </div>
            </div>

            <div class="row mb-3">
                <div class="col-6">
                    <div class="stat-card bg-warning">
                        <div class="stat-value">{pending_count:,}</div>
                        <div class="stat-label">Pending</div>
                    </div>
                </div>
                <div class="col-6">
                    <div class="stat-card bg-info text-white">
                        <div class="stat-value">{coverage:.1f}%</div>
                        <div class="stat-label">Coverage</div>
                    </div>
                </div>
            </div>

            <!-- Sentiment Distribution -->
            <div class="row mb-3">
                <div class="col-4">
                    <div class="stat-card-sm text-success">
                        <div class="stat-value-sm">{positive}</div>
                        <div class="stat-label-sm">Positive</div>
                    </div>
                </div>
                <div class="col-4">
                    <div class="stat-card-sm text-secondary">
                        <div class="stat-value-sm">{neutral}</div>
                        <div class="stat-label-sm">Neutral</div>
                    </div>
                </div>
                <div class="col-4">
                    <div class="stat-card-sm text-danger">
                        <div class="stat-value-sm">{negative}</div>
                        <div class="stat-label-sm">Negative</div>
                    </div>
                </div>
            </div>

            <!-- Impact and Urgency -->
            <div class="row">
                <div class="col-6">
                    <div class="stat-card-sm">
                        <div class="stat-value-sm">{avg_impact:.2f}</div>
                        <div class="stat-label-sm">Impact</div>
                    </div>
                </div>
                <div class="col-6">
                    <div class="stat-card-sm">
                        <div class="stat-value-sm">{avg_urgency:.2f}</div>
                        <div class="stat-label-sm">Urgency</div>
                    </div>
                </div>
            </div>
        </div>

        <style>
            .stats-container {{
                padding: 15px;
                background: #1a1a1a;
                border-radius: 8px;
            }}
            .stat-card {{
                padding: 20px;
                border-radius: 8px;
                text-align: center;
                margin-bottom: 10px;
                background: #2d2d2d !important;
                border: 1px solid #444;
            }}
            .stat-card-sm {{
                padding: 15px;
                border-radius: 6px;
                text-align: center;
                background: #2d2d2d;
                border: 1px solid #444;
            }}
            .stat-value {{
                font-size: 2.2rem;
                font-weight: bold;
                margin-bottom: 5px;
                color: #4a9eff !important;
            }}
            .stat-value-sm {{
                font-size: 1.8rem;
                font-weight: bold;
                margin-bottom: 3px;
            }}
            .stat-label {{
                font-size: 0.85rem;
                text-transform: uppercase;
                opacity: 0.8;
                color: #999 !important;
            }}
            .stat-label-sm {{
                font-size: 0.8rem;
                text-transform: uppercase;
                opacity: 0.7;
                color: #999;
            }}
            .bg-warning .stat-value {{
                color: #ffc107 !important;
            }}
            .bg-success .stat-value {{
                color: #28a745 !important;
            }}
            .bg-info .stat-value {{
                color: #17a2b8 !important;
            }}
            .text-success .stat-value-sm {{
                color: #28a745 !important;
            }}
            .text-secondary .stat-value-sm {{
                color: #6c757d !important;
            }}
            .text-danger .stat-value-sm {{
                color: #dc3545 !important;
            }}
        </style>
        """

    except Exception as e:
        logger.error(f"Failed to get stats: {e}")
        return '<div class="alert alert-danger">Failed to load statistics</div>'