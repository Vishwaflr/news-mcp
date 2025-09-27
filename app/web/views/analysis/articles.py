"""
Articles live list endpoint with inline CSS
"""

from fastapi import APIRouter, Depends, Query
from fastapi.responses import HTMLResponse
from sqlmodel import Session, text
from app.database import get_session
from app.core.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/htmx/analysis", tags=["htmx"])
@router.get("/articles-live", response_class=HTMLResponse)
async def get_articles_live(
    selection_id: str = Query(..., description="Selection ID from cache"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_session)
):
    """Get paginated articles from cached selection"""
    try:
        from app.services.selection_cache import get_selection_cache

        cache = get_selection_cache()
        cached_selection = cache.get(selection_id)

        if not cached_selection:
            return HTMLResponse("""
            <div class="alert alert-warning">
                <i class="bi bi-info-circle me-2"></i>
                Selection not found or expired. Please create a new selection.
            </div>
            """)

        articles = cached_selection['articles']
        total_count = len(articles)

        offset = (page - 1) * page_size
        paginated_articles = articles[offset:offset + page_size]

        current_page = page
        total_pages = min(((total_count + page_size - 1) // page_size if total_count > 0 else 1), 100)
        has_more = offset + page_size < total_count and current_page < 100

        if not paginated_articles:
            return HTMLResponse(f"""
            <div class="alert alert-info mb-0">
                <div class="d-flex align-items-center">
                    <i class="bi bi-info-circle me-2"></i>
                    <span>No articles found on this page.</span>
                </div>
            </div>
            <div class="mt-2 text-center" style="color: #6b7280; font-size: 0.85rem;">
                Total: {total_count} articles
            </div>
            <div class="pagination-data d-none"
                 data-page="{current_page}"
                 data-total-pages="{total_pages}"
                 data-has-more="false"
                 data-total-count="{total_count}"></div>
            """)

        html = ""

        for idx, article in enumerate(paginated_articles, 1):
            try:
                item_id = article['id']
                title = article['title']
                link = article['link']
                published = article['published']
                feed_title = article['feed_title']
                sentiment_label = article['sentiment_label']
                has_analysis = article['has_analysis']
                description = article.get('description', '')

                from datetime import datetime
                if published:
                    if isinstance(published, str):
                        published_dt = datetime.fromisoformat(published.replace('Z', '+00:00'))
                        published_str = published_dt.strftime('%d.%m.%Y %H:%M')
                    else:
                        published_str = published.strftime('%d.%m.%Y %H:%M')
                else:
                    published_str = 'No date'

                display_title = (title[:120] + "...") if title and len(title) > 120 else (title or "Untitled")
                display_desc = (description[:180] + "...") if description and len(description) > 180 else (description or "")

                if has_analysis and sentiment_label:
                    if sentiment_label.lower() == 'positive':
                        analysis_badge = '<span class="badge bg-success"><small>✓ Analyzed: Positive</small></span>'
                    elif sentiment_label.lower() == 'negative':
                        analysis_badge = '<span class="badge bg-danger"><small>✓ Analyzed: Negative</small></span>'
                    else:
                        analysis_badge = '<span class="badge bg-secondary"><small>✓ Analyzed: Neutral</small></span>'
                else:
                    analysis_badge = '<span class="badge" style="background: #f59e0b;"><small>○ Not Analyzed</small></span>'

                desc_html = f'<div class="article-description">{display_desc}</div>' if display_desc else ''
                link_html = f'<a href="{link}" target="_blank" class="btn-link">Read Article →</a>' if link else ''

                html += f"""
                <div class="article-item">
                    <div class="article-number">{offset + idx}</div>
                    <div class="article-content">
                        <div class="article-title-row">
                            <h6 class="article-title">{display_title}</h6>
                        </div>
                        <div class="article-meta-row">
                            <span class="article-feed">{feed_title or 'Unknown Feed'}</span>
                            <span class="article-date">{published_str}</span>
                        </div>
                        {desc_html}
                        <div class="article-footer-row">
                            {analysis_badge}
                            <div class="article-actions">
                                {link_html}
                                <span class="article-id">#{item_id}</span>
                            </div>
                        </div>
                    </div>
                </div>
                """
            except Exception as e:
                logger.error(f"Error rendering article {idx}: {e}", exc_info=True)
                html += f'<div class="alert alert-warning">Error rendering article {idx}: {str(e)}</div>'

        html += f"""
        <div class="articles-footer">
            <div class="pagination-info">
                <span>Showing {offset + 1}-{min(offset + page_size, total_count)} of {total_count} articles</span>
                <span class="separator">•</span>
                <span>Page {current_page} of {total_pages}</span>
            </div>
        </div>
        <div class="pagination-data d-none"
             data-page="{current_page}"
             data-total-pages="{total_pages}"
             data-has-more="{str(has_more).lower()}"
             data-total-count="{total_count}"></div>
        """

        return HTMLResponse(html)

    except Exception as e:
        logger.error(f"Error in get_articles_live: {e}")
        return HTMLResponse("""
        <div class="alert alert-danger">
            <i class="bi bi-exclamation-triangle me-2"></i>
            Error loading articles: """ + str(e) + """
        </div>
        """)

