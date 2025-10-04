"""Item management HTMX components."""

from fastapi import APIRouter, Depends, Query
from fastapi.responses import HTMLResponse
from sqlmodel import Session, text
from typing import Optional
from datetime import datetime, timedelta
from app.core.logging_config import get_logger

from app.database import get_session
from app.repositories.analysis import AnalysisRepo
from .base_component import BaseComponent

router = APIRouter(tags=["htmx-items"])
logger = get_logger(__name__)


class ItemComponent(BaseComponent):
    """Component for item-related HTMX endpoints."""

    @staticmethod
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

        # Prepare market and geopolitical data
        market_display = f"📉 Bearish ({market.get('bearish', 0):.1f})" if market.get('bearish', 0) > 0.6 else f"📈 Bullish ({market.get('bullish', 0):.1f})" if market.get('bullish', 0) > 0.6 else "➡️ Neutral"
        time_horizon = market.get('time_horizon', 'medium').title()
        themes_display = ' • '.join([f"🏷️ {theme}" for theme in themes[:4]])  # Show max 4 themes

        # Finance Block
        finance_html = f"""
    <div class="finance-block p-3 mb-2" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 8px; color: white;">
        <h6 class="mb-2">💰 Finance</h6>
        <div class="mb-1"><strong>Market:</strong> {market_display}</div>
        <div class="mb-1"><strong>Horizon:</strong> {time_horizon}</div>
        <div class="mb-1"><strong>Impact:</strong> ⚡ {impact_overall:.1f}</div>
        <div><strong>Volatility:</strong> 📈 {impact_volatility:.1f}</div>
    </div>
"""

        # Geopolitical Block
        geo_html = ""
        if geopolitical and geopolitical.get("conflict_type"):
            conflict_type = geopolitical.get("conflict_type", "N/A").replace("_", " ").title()
            security = geopolitical.get("security_relevance", 0)
            escalation = geopolitical.get("escalation_potential", 0)
            stability = geopolitical.get("stability_score", 0)
            regions = geopolitical.get("regions_affected", [])
            regions_str = ", ".join(regions[:3]) if regions else "N/A"

            geo_html = f"""
    <div class="geopolitical-block p-3 mb-2" style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); border-radius: 8px; color: white;">
        <h6 class="mb-2">🌍 Geopolitical</h6>
        <div class="mb-1"><strong>Type:</strong> {conflict_type}</div>
        <div class="mb-1"><strong>Security:</strong> {security:.1f}</div>
        <div class="mb-1"><strong>Escalation:</strong> {escalation:.1f}</div>
        <div class="mb-1"><strong>Stability:</strong> {stability:.1f}</div>
        <div><strong>Regions:</strong> {regions_str}</div>
    </div>
"""

        # Compact display (always visible)
        compact_html = f"""
        <div class="sentiment-analysis">
            {finance_html}
            {geo_html}
    """

        # Detailed display (initially hidden)
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

    @staticmethod
    def build_item_card(item_data: dict) -> str:
        """Build HTML for a single item card."""
        published_date = ItemComponent.format_date(item_data.get('published')) if item_data.get('published') else ItemComponent.format_date(item_data.get('created_at'))
        description = ItemComponent.truncate_text(item_data.get('description', ''), 200)

        # Clean and escape content
        clean_title = ItemComponent.clean_html_attr(item_data.get('title', 'Untitled'))
        clean_description = ItemComponent.clean_html_attr(description)
        feed_name = item_data.get('feed_title', item_data.get('feed_url', 'Unknown Feed')[:30] + "...")

        author_info = f'<span><i class="bi bi-person me-1"></i>{item_data.get("author")}</span>' if item_data.get('author') else ''

        # Get analysis data
        analysis = AnalysisRepo.get_by_item_id(item_data.get('id'))

        # Separate Finance and Geopolitical blocks
        finance_col = ''
        geo_col = ''

        if analysis and analysis.get('sentiment_json'):
            sentiment = analysis.get('sentiment_json', {})
            impact = analysis.get('impact_json', {})
            market = sentiment.get('market', {})

            bearish = market.get('bearish', 0)
            bullish = market.get('bullish', 0)
            market_display = f'📉 Bearish ({bearish:.1f})' if bearish > 0.6 else f'📈 Bullish ({bullish:.1f})' if bullish > 0.6 else '➡️ Neutral'
            time_horizon = (market.get('time_horizon', 'medium') or 'medium').capitalize()

            finance_col = f'''
            <div class="card shadow-sm h-100">
                <div class="card-body p-2" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 8px; color: white; font-size: 0.85rem;">
                    <h6 class="mb-1" style="font-size: 0.9rem;">💰 Finance</h6>
                    <div style="font-size: 0.75rem;"><strong>Market:</strong> {market_display}</div>
                    <div style="font-size: 0.75rem;"><strong>Horizon:</strong> {time_horizon}</div>
                    <div style="font-size: 0.75rem;"><strong>Impact:</strong> ⚡ {impact.get('overall', 0):.1f}</div>
                    <div style="font-size: 0.75rem;"><strong>Volatility:</strong> 📈 {impact.get('volatility', 0):.1f}</div>
                </div>
            </div>
            '''

            geo = sentiment.get('geopolitical', {})
            if geo and geo.get('conflict_type'):
                conflict_type = (geo.get('conflict_type', 'N/A') or 'N/A').replace('_', ' ').title()
                regions = ', '.join((geo.get('regions_affected', []) or [])[:3]) or 'N/A'

                geo_col = f'''
                <div class="card shadow-sm h-100">
                    <div class="card-body p-2" style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); border-radius: 8px; color: white; font-size: 0.85rem;">
                        <h6 class="mb-1" style="font-size: 0.9rem;">🌍 Geopolitical</h6>
                        <div style="font-size: 0.75rem;"><strong>Type:</strong> {conflict_type}</div>
                        <div style="font-size: 0.75rem;"><strong>Security:</strong> {geo.get('security_relevance', 0):.1f}</div>
                        <div style="font-size: 0.75rem;"><strong>Escalation:</strong> {geo.get('escalation_potential', 0):.1f}</div>
                        <div style="font-size: 0.75rem;"><strong>Stability:</strong> {geo.get('stability_score', 0):.1f}</div>
                        <div style="font-size: 0.75rem;"><strong>Regions:</strong> {regions}</div>
                    </div>
                </div>
                '''

        # Ensure we always have placeholders for grid
        finance_placeholder = '''
        <div class="card shadow-sm h-100">
            <div class="card-body p-2" style="background: #6c757d; border-radius: 8px; color: white; font-size: 0.85rem; opacity: 0.5;">
                <h6 class="mb-1" style="font-size: 0.9rem;">💰 Finance</h6>
                <div style="font-size: 0.75rem;">No analysis</div>
            </div>
        </div>
        '''
        geo_placeholder = '''
        <div class="card shadow-sm h-100">
            <div class="card-body p-2" style="background: #6c757d; border-radius: 8px; color: white; font-size: 0.85rem; opacity: 0.5;">
                <h6 class="mb-1" style="font-size: 0.9rem;">🌍 Geopolitical</h6>
                <div style="font-size: 0.75rem;">No analysis</div>
            </div>
        </div>
        '''
        finance_display = finance_col if finance_col.strip() else finance_placeholder
        geo_display = geo_col if geo_col.strip() else geo_placeholder

        return f'''
        <div class="mb-3" style="display: grid; grid-template-columns: 70% 15% 15%; gap: 0.5rem;">
            <div class="card shadow-sm article-card" data-item-id="{item_data.get('id')}">
                <div class="card-body">
                    <h5 class="card-title mb-2">
                        <a href="{item_data.get('link', '#')}" target="_blank" class="text-decoration-none text-primary">
                            {clean_title}
                        </a>
                    </h5>
                    <div class="d-flex flex-wrap gap-3 text-muted small mb-2">
                        <span><i class="bi bi-calendar me-1"></i>{published_date}</span>
                        <span><i class="bi bi-rss me-1"></i>{feed_name}</span>
                        {author_info}
                    </div>
                    {f'<p class="card-text text-body-secondary">{clean_description}</p>' if clean_description else ''}
                </div>
            </div>
            {finance_display}
            {geo_display}
        </div>
        '''


@router.get("/items-list", response_class=HTMLResponse)
def get_items_list(
    session: Session = Depends(get_session),
    category_id: Optional[int] = Query(None),
    feed_id: Optional[int] = Query(None),
    search: Optional[str] = Query(None),
    since_hours: Optional[int] = Query(None),
    skip: int = 0,
    limit: int = 20
):
    """Get filtered HTML list of items."""
    try:
        # Use raw SQL to avoid SQLModel issues
        where_clauses = []
        params = {}

        if category_id and category_id > 0:
            where_clauses.append("""
                i.feed_id IN (
                    SELECT feed_id FROM feed_categories WHERE category_id = :category_id
                )
            """)
            params['category_id'] = category_id

        if feed_id and feed_id > 0:
            where_clauses.append("i.feed_id = :feed_id")
            params['feed_id'] = feed_id

        if since_hours and since_hours > 0:
            since_time = datetime.utcnow() - timedelta(hours=since_hours)
            where_clauses.append("i.created_at >= :since_time")
            params['since_time'] = since_time

        if search:
            where_clauses.append("(i.title ILIKE :search OR i.description ILIKE :search)")
            params['search'] = f'%{search}%'

        where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

        sql = f"""
            SELECT
                i.id, i.title, i.link, i.description, i.author, i.published, i.created_at,
                f.id as feed_id, f.title as feed_title, f.url as feed_url
            FROM items i
            JOIN feeds f ON i.feed_id = f.id
            {where_sql}
            ORDER BY COALESCE(i.published, i.created_at) DESC
            LIMIT :limit OFFSET :skip
        """

        params['limit'] = limit
        params['skip'] = skip

        # Execute raw SQL
        result = session.execute(text(sql), params)
        items = result.fetchall()

        # Build HTML
        html = ""
        for row in items:
            item_data = {
                'id': row[0],
                'title': row[1],
                'link': row[2],
                'description': row[3],
                'author': row[4],
                'published': row[5],
                'created_at': row[6],
                'feed_id': row[7],
                'feed_title': row[8],
                'feed_url': row[9]
            }
            html += ItemComponent.build_item_card(item_data)

        if not html:
            html = BaseComponent.alert_box('No articles found.', 'info')

        return html

    except Exception as e:
        logger.error(f"Error in items-list: {e}")
        return BaseComponent.alert_box(f'Error loading articles: {str(e)}', 'danger')