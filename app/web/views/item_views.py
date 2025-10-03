from fastapi import APIRouter, Depends, Query
from fastapi.responses import HTMLResponse
from sqlmodel import Session, select
from typing import Optional
from app.core.logging_config import get_logger

from app.database import get_session
from app.models import Item, Feed, FeedCategory
from app.repositories.analysis import AnalysisRepo

router = APIRouter(tags=["htmx-items"])
logger = get_logger(__name__)

@router.get("/items-list", response_class=HTMLResponse)
def get_items_list(
    session: Session = Depends(get_session),
    category_id: Optional[str] = None,
    feed_id: Optional[str] = None,
    search: Optional[str] = None,
    since_hours: Optional[str] = None,
    skip: int = 0,
    limit: int = 20
):
    from datetime import datetime, timedelta
    from sqlmodel import or_

    query = select(Item, Feed).join(Feed)

    # Convert string parameters to int, handle empty strings
    try:
        category_id_int = int(category_id) if category_id and category_id.strip() else None
    except ValueError:
        category_id_int = None

    try:
        feed_id_int = int(feed_id) if feed_id and feed_id.strip() else None
    except ValueError:
        feed_id_int = None

    try:
        since_hours_int = int(since_hours) if since_hours and since_hours.strip() else None
    except ValueError:
        since_hours_int = None

    if category_id_int:
        query = query.join(FeedCategory).where(FeedCategory.category_id == category_id_int)

    if feed_id_int:
        query = query.where(Item.feed_id == feed_id_int)

    if since_hours_int:
        since_time = datetime.utcnow() - timedelta(hours=since_hours_int)
        query = query.where(Item.created_at >= since_time)

    if search:
        search_term = f"%{search}%"
        query = query.where(
            or_(
                Item.title.contains(search_term),
                Item.description.contains(search_term)
            )
        )

    # Order by published date first (actual article date), then by created_at (when added to our system)
    # This ensures articles are sorted by their real publication date, not when we fetched them
    from sqlalchemy import desc, case
    query = query.order_by(
        desc(case(
            (Item.published.is_(None), Item.created_at),
            else_=Item.published
        ))
    ).offset(skip).limit(limit)
    results = session.exec(query).all()

    html = ""
    for item, feed in results:
        published_date = item.published.strftime("%d.%m.%Y %H:%M") if item.published else item.created_at.strftime("%d.%m.%Y %H:%M")
        description = item.description[:200] + "..." if item.description and len(item.description) > 200 else item.description or ""

        # Clean and escape content
        clean_title = item.title.replace('"', '&quot;') if item.title else 'Untitled'
        clean_description = description.replace('"', '&quot;') if description else ''
        feed_name = (feed.title or feed.url[:30] + "...") if feed else 'Unknown Feed'

        # Get analysis data
        analysis = AnalysisRepo.get_by_item_id(item.id)
        analysis_display = generate_sentiment_display(analysis)

        html += f"""
        <div class="card mb-3 shadow-sm">
            <div class="card-body">
                <div class="d-flex justify-content-between align-items-start mb-2">
                    <h5 class="card-title mb-0 flex-grow-1">
                        <a href="{item.link}" target="_blank" class="text-decoration-none text-primary">
                            {clean_title}
                        </a>
                    </h5>
                    {analysis_display}
                </div>
                <div class="d-flex flex-wrap gap-3 text-muted small mb-2">
                    <span><i class="bi bi-calendar me-1"></i>{published_date}</span>
                    <span><i class="bi bi-rss me-1"></i>{feed_name}</span>
                    {f'<span><i class="bi bi-person me-1"></i>{item.author}</span>' if item.author else ''}
                </div>
                {f'<p class="card-text text-body-secondary">{clean_description}</p>' if clean_description else ''}
            </div>
        </div>
        """

    if not html:
        html = '<div class="alert alert-info">No articles found.</div>'

    return html


def generate_sentiment_display(analysis):
    """Generate HTML for sentiment analysis display with expandable details"""
    if not analysis or not analysis.get('sentiment_json'):
        return '<div class="sentiment-analysis mb-2"><span class="badge bg-secondary">No Analysis</span></div>'

    sentiment_json = analysis.get('sentiment_json', {})
    impact_json = analysis.get('impact_json', {})
    model = analysis.get('model_tag', 'unknown')

    # Extract key values
    overall = sentiment_json.get('overall', {})
    market = sentiment_json.get('market', {})
    geopolitical = sentiment_json.get('geopolitical', {})
    label = overall.get('label', 'neutral')
    score = overall.get('score', 0.0)
    confidence = overall.get('confidence', 0.0)
    urgency = sentiment_json.get('urgency', 0.0)
    impact_overall = impact_json.get('overall', 0.0)
    impact_volatility = impact_json.get('volatility', 0.0)
    themes = sentiment_json.get('themes', [])

    # Sentiment icon and color
    if label == 'positive':
        icon = '🟢'
        color = 'success'
    elif label == 'negative':
        icon = '🔴'
        color = 'danger'
    else:
        icon = '⚪'
        color = 'secondary'

    # Compact display (always visible)
    compact_html = f"""
    <div class="sentiment-analysis mb-2">
        <div class="d-flex align-items-center gap-2 sentiment-compact" style="cursor: pointer;" onclick="toggleSentimentDetails(this)">
            <span class="sentiment-icon">{icon}</span>
            <span class="badge bg-{color}">{score:.1f}</span>
            <span class="badge bg-warning">⚡ {urgency:.1f}</span>
            <span class="badge bg-info">📊 {impact_overall:.1f}</span>
            <small class="text-muted">Details ⌄</small>
        </div>
"""

    # Detailed display (initially hidden)
    market_display = f"📉 Bearish ({market.get('bearish', 0):.1f})" if market.get('bearish', 0) > 0.6 else f"📈 Bullish ({market.get('bullish', 0):.1f})" if market.get('bullish', 0) > 0.6 else "➡️ Neutral"
    time_horizon = market.get('time_horizon', 'medium').title()
    themes_display = ' • '.join([f"🏷️ {theme}" for theme in themes[:4]])  # Show max 4 themes

    # Geopolitical display
    geo_display = ""
    if geopolitical and geopolitical.get("conflict_type"):
        conflict_type = geopolitical.get("conflict_type", "N/A").replace("_", " ").title()
        security = geopolitical.get("security_relevance", 0)
        escalation = geopolitical.get("escalation_potential", 0)
        geo_display = f'<div class="mb-2"><strong>🌍 Geopolitical:</strong> {conflict_type} • Security: {security:.1f} • Escalation: {escalation:.1f}</div>'

    detailed_html = f"""
        <div class="sentiment-details mt-2" style="display: none;">
            <div class="card border-light bg-light">
                <div class="card-header bg-transparent border-bottom-0 py-2">
                    <h6 class="mb-0 text-muted">📊 Sentiment Analysis ({model})</h6>
                </div>
                <div class="card-body py-2">
                    <div class="row g-2">
                        <div class="col-md-6">
                            <div class="mb-2">
                                <strong>Overall:</strong>
                                <span class="badge bg-{color}">{label.title()} ({score:.1f})</span>
                                <small class="text-muted">• {int(confidence*100)}% confident</small>
                            </div>
                            <div class="mb-2">
                                <strong>Market:</strong> {market_display} • {time_horizon}-term
                            </div>
                            {geo_display}
                        </div>
                        <div class="col-md-6">
                            <div class="mb-2">
                                <strong>Impact:</strong> ⚡ {impact_overall:.1f} • Volatility: 📈 {impact_volatility:.1f}
                            </div>
                            <div class="mb-2">
                                <strong>Urgency:</strong> ⏰ {urgency:.1f}
                            </div>
                        </div>
                    </div>
                    {f'<div class="mt-2"><strong>Themes:</strong> {themes_display}</div>' if themes else ''}
                </div>
            </div>
        </div>
    </div>
    """

    return compact_html + detailed_html