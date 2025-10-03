"""
HTMX views for Content Templates UI.
"""

from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select
from typing import List
import httpx

from app.database import get_session
from app.models.content_distribution import SpecialReport, GeneratedContent
from app.config import settings

router = APIRouter(tags=["special-report-views"])
templates = Jinja2Templates(directory="templates")


@router.get("/admin/special-reports", response_class=HTMLResponse)
async def special_reports_page(request: Request):
    """Main special reports overview page."""
    return templates.TemplateResponse(
        "admin/special_reports.html",
        {"request": request}
    )


@router.get("/admin/special-reports/{special_report_id}/edit", response_class=HTMLResponse)
async def special_report_edit_page(
    request: Request,
    special_report_id: int,
    session: Session = Depends(get_session)
):
    """Dedicated edit page with live test functionality."""
    from sqlmodel import select
    from app.models.core import Feed

    special_report = session.get(SpecialReport, special_report_id)
    if not special_report:
        raise HTTPException(status_code=404, detail="Special Report not found")

    # Get all feeds
    feeds = session.exec(select(Feed).order_by(Feed.title)).all()

    # Extract selection criteria
    sc = special_report.selection_criteria or {}
    selected_feed_ids = sc.get('feed_ids') or []

    # Safely extract keywords
    keywords_raw = sc.get('keywords') or []
    keywords_str = ','.join(keywords_raw) if isinstance(keywords_raw, list) else (keywords_raw if isinstance(keywords_raw, str) else '')

    exclude_keywords_raw = sc.get('exclude_keywords') or []
    exclude_keywords_str = ','.join(exclude_keywords_raw) if isinstance(exclude_keywords_raw, list) else (exclude_keywords_raw if isinstance(exclude_keywords_raw, str) else '')

    return templates.TemplateResponse(
        "admin/special_report_edit.html",
        {
            "request": request,
            "special_report": special_report,
            "feeds": feeds,
            "selected_feed_ids": selected_feed_ids,
            "selection_criteria": sc,
            "keywords_str": keywords_str,
            "exclude_keywords_str": exclude_keywords_str
        }
    )


@router.get("/admin/special-reports/{special_report_id}", response_class=HTMLResponse)
async def special_report_detail_page(
    request: Request,
    special_report_id: int,
    session: Session = Depends(get_session)
):
    """Special report detail page with generated content."""
    special_report = session.get(SpecialReport, special_report_id)

    if not special_report:
        raise HTTPException(status_code=404, detail="Template not found")

    return templates.TemplateResponse(
        "admin/special_report_detail.html",
        {
            "request": request,
            "special_report": special_report
        }
    )


@router.get("/htmx/special_reports/list", response_class=HTMLResponse)
async def htmx_special_reports_list(session: Session = Depends(get_session)):
    """HTMX: Templates list."""
    query = select(SpecialReport).order_by(SpecialReport.created_at.desc())
    all_special_reports = session.exec(query).all()

    if not all_special_reports:
        return """
        <div class="alert alert-info bg-dark border-info text-light">
            <i class="fas fa-info-circle"></i>
            No special_reports found. Create your first special_report via the API.
        </div>
        """

    html_parts = []
    html_parts.append('<div class="table-responsive">')
    html_parts.append('<table class="table table-dark table-hover border-secondary">')
    html_parts.append('''
        <thead>
            <tr>
                <th>Name</th>
                <th>Audience</th>
                <th>Model</th>
                <th>Schedule</th>
                <th>Status</th>
                <th>Actions</th>
            </tr>
        </thead>
        <tbody>
    ''')

    for special_report in all_special_reports:
        status_badge = 'bg-success' if special_report.is_active else 'bg-secondary'
        status_text = 'Active' if special_report.is_active else 'Inactive'

        html_parts.append(f'''
            <tr>
                <td>
                    <strong>{special_report.name}</strong>
                    <br>
                    <small class="text-muted">{special_report.description or 'No description'}</small>
                </td>
                <td>{special_report.target_audience or '-'}</td>
                <td><code>{special_report.llm_model}</code></td>
                <td>{special_report.generation_schedule or 'On-demand'}</td>
                <td><span class="badge {status_badge}">{status_text}</span></td>
                <td>
                    <div class="btn-group btn-group-sm" role="group">
                        <a href="/admin/special-reports/{special_report.id}" class="btn btn-sm btn-outline-primary" title="View">
                            <i class="fas fa-eye"></i>
                        </a>
                        <a href="/admin/special-reports/{special_report.id}/edit" class="btn btn-sm btn-outline-warning" title="Edit">
                            <i class="fas fa-edit"></i>
                        </a>
                        <button class="btn btn-sm btn-outline-danger"
                                hx-delete="/htmx/special_reports/{special_report.id}/delete"
                                hx-target="#special-reports-list"
                                hx-confirm="Are you sure you want to delete '{special_report.name}'?"
                                title="Delete">
                            <i class="fas fa-trash"></i>
                        </button>
                    </div>
                </td>
            </tr>
        ''')

    html_parts.append('</tbody></table></div>')

    return ''.join(html_parts)


@router.get("/htmx/special_reports/{special_report_id}/content", response_class=HTMLResponse)
async def htmx_special_report_content(
    special_report_id: int,
    session: Session = Depends(get_session)
):
    """HTMX: Generated content list for special_report."""
    query = select(GeneratedContent).where(
        GeneratedContent.special_report_id == special_report_id
    ).order_by(GeneratedContent.generated_at.desc())

    content_list = session.exec(query).all()

    if not content_list:
        return """
        <div class="alert alert-warning bg-dark border-warning text-light">
            <i class="fas fa-exclamation-triangle"></i>
            No content generated yet for this special_report.
        </div>
        """

    html_parts = []
    html_parts.append('<div class="list-group">')

    for content in content_list:
        status_color = {
            'generated': 'success',
            'published': 'primary',
            'archived': 'secondary',
            'failed': 'danger'
        }.get(content.status, 'secondary')

        # Format date
        date_str = content.generated_at.strftime('%Y-%m-%d %H:%M')

        html_parts.append(f'''
            <div class="list-group-item list-group-item-action bg-dark border-secondary">
                <div class="d-flex w-100 justify-content-between align-items-start">
                    <div class="flex-grow-1">
                        <h6 class="mb-1">{content.title or f'Content #{content.id}'}</h6>
                        <div class="d-flex gap-3 mb-2">
                            <small class="text-muted">
                                <i class="far fa-calendar"></i> {date_str}
                            </small>
                            <small class="text-muted">
                                <i class="far fa-file-alt"></i> {content.articles_count} articles
                            </small>
                            {f'<small class="text-muted"><i class="far fa-file-word"></i> {content.word_count} words</small>' if content.word_count else ''}
                            {f'<small class="text-muted"><i class="fas fa-dollar-sign"></i> ${content.generation_cost_usd:.4f}</small>' if content.generation_cost_usd else ''}
                        </div>
                        <span class="badge bg-{status_color}">{content.status}</span>
                    </div>
                    <div class="d-flex gap-2">
                        <button class="btn btn-sm btn-outline-primary"
                                hx-get="/htmx/content/{content.id}/preview"
                                hx-target="#preview-content"
                                data-bs-toggle="modal"
                                data-bs-target="#contentPreviewModal">
                            <i class="fas fa-eye"></i> Preview
                        </button>
                    </div>
                </div>
            </div>
        ''')

    html_parts.append('</div>')

    return ''.join(html_parts)


@router.get("/htmx/content/{content_id}/preview", response_class=HTMLResponse)
async def htmx_content_preview(
    content_id: int,
    session: Session = Depends(get_session)
):
    """HTMX: Content preview (markdown or HTML)."""
    content = session.get(GeneratedContent, content_id)

    if not content:
        return '<div class="alert alert-danger bg-dark border-danger text-light">Content not found</div>'

    # Show metadata
    html_parts = []
    html_parts.append(f'''
        <div class="mb-3">
            <h4 class="text-light">{content.title or f'Content #{content.id}'}</h4>
            <div class="d-flex gap-3 mb-2 text-muted">
                <small><i class="far fa-calendar"></i> {content.generated_at.strftime('%Y-%m-%d %H:%M')}</small>
                <small><i class="far fa-file-alt"></i> {content.articles_count} articles</small>
                {f'<small><i class="far fa-file-word"></i> {content.word_count} words</small>' if content.word_count else ''}
                {f'<small><i class="fas fa-dollar-sign"></i> ${content.generation_cost_usd:.4f}</small>' if content.generation_cost_usd else ''}
                <small><i class="fas fa-brain"></i> {content.llm_model_used or 'Unknown'}</small>
            </div>
        </div>
        <hr>
    ''')

    # Show content (prefer HTML, fallback to Markdown)
    if content.content_html:
        html_parts.append(f'<div class="content-preview">{content.content_html}</div>')
    elif content.content_markdown:
        # Simple markdown to HTML conversion (basic)
        md_html = content.content_markdown.replace('\n', '<br>')
        html_parts.append(f'<div class="content-preview"><pre class="text-light">{md_html}</pre></div>')
    else:
        html_parts.append('<div class="alert alert-warning bg-dark border-warning text-light">No content available</div>')

    # Show source articles
    if content.source_article_ids:
        html_parts.append(f'''
            <hr>
            <details>
                <summary class="text-muted">Source Articles ({len(content.source_article_ids)})</summary>
                <ul class="mt-2">
                    {''.join(f'<li>Article ID: {aid}</li>' for aid in content.source_article_ids[:10])}
                    {f'<li>... and {len(content.source_article_ids) - 10} more</li>' if len(content.source_article_ids) > 10 else ''}
                </ul>
            </details>
        ''')

    return ''.join(html_parts)


@router.get("/htmx/special_reports/{special_report_id}/edit-form", response_class=HTMLResponse)
async def htmx_edit_form(
    special_report_id: int,
    session: Session = Depends(get_session)
):
    """HTMX: Get comprehensive edit form for special report."""
    from sqlmodel import select
    from app.models.core import Feed

    special_report = session.get(SpecialReport, special_report_id)
    if not special_report:
        return '<div class="alert alert-danger">Special Report not found</div>'

    # Get all feeds for dropdown
    feeds = session.exec(select(Feed).order_by(Feed.title)).all()

    # Extract selection criteria
    sc = special_report.selection_criteria or {}
    selected_feed_ids = sc.get('feed_ids') or []

    # Safely extract keywords (could be string or list)
    keywords_raw = sc.get('keywords') or []
    keywords_str = ','.join(keywords_raw) if isinstance(keywords_raw, list) else (keywords_raw if isinstance(keywords_raw, str) else '')

    exclude_keywords_raw = sc.get('exclude_keywords') or []
    exclude_keywords_str = ','.join(exclude_keywords_raw) if isinstance(exclude_keywords_raw, list) else (exclude_keywords_raw if isinstance(exclude_keywords_raw, str) else '')

    # Build feed selection checkboxes
    feed_options = []
    for feed in feeds[:20]:  # Limit to first 20 feeds for UI
        checked = 'checked' if feed.id in selected_feed_ids else ''
        feed_options.append(f'''
            <div class="form-check">
                <input class="form-check-input" type="checkbox" name="feed_ids" value="{feed.id}" {checked} id="feed_{feed.id}">
                <label class="form-check-label" for="feed_{feed.id}">{feed.title or feed.url[:50]}</label>
            </div>
        ''')

    return f'''
        <form hx-put="/htmx/special_reports/{special_report.id}/update"
              hx-target="#special-reports-list"
              hx-swap="innerHTML">

            <!-- Basic Info -->
            <h6 class="text-light mb-3">Basic Configuration</h6>
            <div class="mb-3">
                <label class="form-label">Name</label>
                <input type="text" name="name" class="form-control" value="{special_report.name}" required>
            </div>
            <div class="mb-3">
                <label class="form-label">Description</label>
                <textarea name="description" class="form-control" rows="2">{special_report.description or ''}</textarea>
            </div>
            <div class="mb-3">
                <label class="form-label">Target Audience</label>
                <input type="text" name="target_audience" class="form-control" value="{special_report.target_audience or ''}" placeholder="e.g., IT Management, Security Teams">
            </div>

            <hr class="my-4">

            <!-- LLM Configuration -->
            <h6 class="text-light mb-3">LLM Configuration</h6>
            <div class="mb-3">
                <label class="form-label">LLM Model</label>
                <select name="llm_model" class="form-select">
                    <option value="gpt-4o" {'selected' if special_report.llm_model == 'gpt-4o' else ''}>GPT-4o (Best Quality)</option>
                    <option value="gpt-4o-mini" {'selected' if special_report.llm_model == 'gpt-4o-mini' else ''}>GPT-4o-mini (Balanced)</option>
                    <option value="gpt-3.5-turbo" {'selected' if special_report.llm_model == 'gpt-3.5-turbo' else ''}>GPT-3.5-turbo (Fast)</option>
                </select>
            </div>
            <div class="mb-3">
                <label class="form-label">Prompt Template</label>
                <textarea name="llm_prompt_template" class="form-control" rows="4" required>{special_report.llm_prompt_template}</textarea>
                <small class="text-muted">Use {{{{articles}}}} as placeholder for article content</small>
            </div>

            <hr class="my-4">

            <!-- Article Selection Criteria -->
            <h6 class="text-light mb-3">Article Selection Criteria</h6>

            <div class="mb-3">
                <label class="form-label">Feeds (select sources)</label>
                <div style="max-height: 200px; overflow-y: auto; border: 1px solid #495057; border-radius: 4px; padding: 10px;">
                    {''.join(feed_options)}
                </div>
                <small class="text-muted">Leave empty to use all feeds</small>
            </div>

            <div class="row mb-3">
                <div class="col-md-6">
                    <label class="form-label">Timeframe (hours)</label>
                    <input type="number" name="timeframe_hours" class="form-control" value="{sc.get('timeframe_hours', 24)}" min="1" max="168">
                </div>
                <div class="col-md-6">
                    <label class="form-label">Max Articles</label>
                    <input type="number" name="max_articles" class="form-control" value="{sc.get('max_articles', 30)}" min="1" max="500">
                </div>
            </div>

            <div class="row mb-3">
                <div class="col-md-6">
                    <label class="form-label">Min Impact Score (0.0-1.0)</label>
                    <input type="number" name="min_impact_score" class="form-control" step="0.1" value="{sc.get('min_impact_score', 0.0)}" min="0" max="1">
                    <small class="text-muted">0 = all, 0.6+ = high impact only</small>
                </div>
                <div class="col-md-6">
                    <label class="form-label">Min Sentiment Score (-1.0 to 1.0)</label>
                    <input type="number" name="min_sentiment_score" class="form-control" step="0.1" value="{sc.get('min_sentiment_score') or ''}" min="-1" max="1" placeholder="optional">
                    <small class="text-muted">-1 = negative, 0 = neutral, 1 = positive</small>
                </div>
            </div>

            <div class="mb-3">
                <label class="form-label">Keywords (comma-separated, optional)</label>
                <input type="text" name="keywords" class="form-control" value="{keywords_str}" placeholder="security, breach, vulnerability">
            </div>

            <div class="mb-3">
                <label class="form-label">Exclude Keywords (comma-separated, optional)</label>
                <input type="text" name="exclude_keywords" class="form-control" value="{exclude_keywords_str}" placeholder="spam, advertisement">
            </div>

            <hr class="my-4">

            <!-- Status -->
            <div class="mb-3 form-check">
                <input type="checkbox" name="is_active" class="form-check-input" {'checked' if special_report.is_active else ''}>
                <label class="form-check-label">Active</label>
            </div>

            <div class="d-flex gap-2">
                <button type="submit" class="btn btn-primary">Save Changes</button>
                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
            </div>
        </form>
    '''


@router.put("/htmx/special_reports/{special_report_id}/update", response_class=HTMLResponse)
async def htmx_update_special_report(
    special_report_id: int,
    request: Request,
    session: Session = Depends(get_session)
):
    """HTMX: Update special report with comprehensive configuration."""
    special_report = session.get(SpecialReport, special_report_id)
    if not special_report:
        return '<div class="alert alert-danger">Special Report not found</div>'

    # Get form data
    form_data = await request.form()

    # Update basic fields
    if 'name' in form_data:
        special_report.name = form_data['name']
    if 'description' in form_data:
        special_report.description = form_data['description'] or None
    if 'target_audience' in form_data:
        special_report.target_audience = form_data['target_audience'] or None

    # Update LLM configuration
    if 'llm_model' in form_data:
        special_report.llm_model = form_data['llm_model']
    if 'llm_prompt_template' in form_data:
        special_report.llm_prompt_template = form_data['llm_prompt_template']

    # Update selection criteria (JSONB)
    sc = special_report.selection_criteria or {}

    # Feed IDs (multi-select checkbox)
    feed_ids = form_data.getlist('feed_ids')
    if feed_ids:
        sc['feed_ids'] = [int(fid) for fid in feed_ids]
    else:
        sc['feed_ids'] = None  # Use all feeds

    # Numeric criteria
    if 'timeframe_hours' in form_data:
        sc['timeframe_hours'] = int(form_data['timeframe_hours'])
    if 'max_articles' in form_data:
        sc['max_articles'] = int(form_data['max_articles'])
    if 'min_impact_score' in form_data:
        sc['min_impact_score'] = float(form_data['min_impact_score'])
    if 'min_sentiment_score' in form_data and form_data['min_sentiment_score']:
        sc['min_sentiment_score'] = float(form_data['min_sentiment_score'])
    else:
        sc['min_sentiment_score'] = None

    # Keywords (comma-separated)
    if 'keywords' in form_data and form_data['keywords']:
        sc['keywords'] = [k.strip() for k in form_data['keywords'].split(',') if k.strip()]
    else:
        sc['keywords'] = []

    if 'exclude_keywords' in form_data and form_data['exclude_keywords']:
        sc['exclude_keywords'] = [k.strip() for k in form_data['exclude_keywords'].split(',') if k.strip()]
    else:
        sc['exclude_keywords'] = []

    special_report.selection_criteria = sc

    # Update status
    special_report.is_active = 'is_active' in form_data

    # Update timestamp
    from datetime import datetime
    special_report.updated_at = datetime.utcnow()

    session.add(special_report)
    session.commit()

    # Return updated list
    return await htmx_special_reports_list(session)


@router.delete("/htmx/special_reports/{special_report_id}/delete", response_class=HTMLResponse)
async def htmx_delete_special_report(
    special_report_id: int,
    session: Session = Depends(get_session)
):
    """HTMX: Delete special report."""
    special_report = session.get(SpecialReport, special_report_id)

    if not special_report:
        return '<div class="alert alert-danger">Special Report not found</div>'

    session.delete(special_report)
    session.commit()

    # Return updated list
    return await htmx_special_reports_list(session)


def build_article_selection_query(form_data: dict, max_articles: int = 20, include_description: bool = False):
    """Build SQL query for article selection based on form criteria."""
    from sqlmodel import text
    from datetime import datetime, timedelta

    # Parse form data
    feed_ids = form_data.getlist('feed_ids') if hasattr(form_data, 'getlist') else form_data.get('feed_ids', [])
    # Handle both list and single value (QueryParams can return string)
    if isinstance(feed_ids, str):
        feed_ids = [feed_ids] if feed_ids else []
    feed_ids = [int(fid) for fid in feed_ids if fid]

    timeframe_hours = int(form_data.get('timeframe_hours', 24))
    max_articles = int(form_data.get('max_articles', max_articles))
    min_impact = float(form_data.get('min_impact_score', 0.0))

    # Sentiment filters with enable/disable toggles
    min_sentiment = float(form_data.get('min_sentiment_score', -1.0)) if form_data.get('min_sentiment_score') else None
    enable_sentiment = form_data.get('enable_sentiment_filter') == 'on'

    min_urgency = float(form_data.get('min_urgency', 0.0)) if form_data.get('min_urgency') else None
    enable_urgency = form_data.get('enable_urgency_filter') == 'on'

    min_bearish = float(form_data.get('min_bearish', 0.0)) if form_data.get('min_bearish') else None
    enable_bearish = form_data.get('enable_bearish_filter') == 'on'

    min_bullish = float(form_data.get('min_bullish', 0.0)) if form_data.get('min_bullish') else None
    enable_bullish = form_data.get('enable_bullish_filter') == 'on'

    min_uncertainty = float(form_data.get('min_uncertainty', 0.0)) if form_data.get('min_uncertainty') else None
    enable_uncertainty = form_data.get('enable_uncertainty_filter') == 'on'

    keywords = [k.strip() for k in form_data.get('keywords', '').split(',') if k.strip()]
    exclude_keywords = [k.strip() for k in form_data.get('exclude_keywords', '').split(',') if k.strip()]

    cutoff = datetime.now() - timedelta(hours=timeframe_hours)

    # Build WHERE clauses
    where_clauses = []
    params = {'cutoff': cutoff}

    if feed_ids:
        placeholders = ','.join([f':feed_{i}' for i in range(len(feed_ids))])
        where_clauses.append(f"i.feed_id IN ({placeholders})")
        for idx, fid in enumerate(feed_ids):
            params[f'feed_{idx}'] = fid

    where_clauses.append("i.published >= :cutoff")

    if min_impact > 0:
        where_clauses.append("COALESCE((a.impact_json->>'overall')::numeric, 0) >= :min_impact")
        params['min_impact'] = min_impact

    # Sentiment filters (only apply if enabled)
    if enable_sentiment and min_sentiment is not None:
        where_clauses.append("COALESCE((a.sentiment_json->'overall'->>'score')::numeric, 0) >= :min_sentiment")
        params['min_sentiment'] = min_sentiment

    if enable_urgency and min_urgency is not None and min_urgency > 0:
        where_clauses.append("COALESCE((a.sentiment_json->>'urgency')::numeric, 0) >= :min_urgency")
        params['min_urgency'] = min_urgency

    if enable_bearish and min_bearish is not None and min_bearish > 0:
        where_clauses.append("COALESCE((a.sentiment_json->'market'->>'bearish')::numeric, 0) >= :min_bearish")
        params['min_bearish'] = min_bearish

    if enable_bullish and min_bullish is not None and min_bullish > 0:
        where_clauses.append("COALESCE((a.sentiment_json->'market'->>'bullish')::numeric, 0) >= :min_bullish")
        params['min_bullish'] = min_bullish

    if enable_uncertainty and min_uncertainty is not None and min_uncertainty > 0:
        where_clauses.append("COALESCE((a.sentiment_json->'market'->>'uncertainty')::numeric, 0) >= :min_uncertainty")
        params['min_uncertainty'] = min_uncertainty

    if keywords:
        kw_clauses = []
        for idx, kw in enumerate(keywords):
            kw_clauses.append(f"(i.title ILIKE :kw_{idx} OR i.description ILIKE :kw_{idx})")
            params[f'kw_{idx}'] = f'%{kw}%'
        where_clauses.append(f"({' OR '.join(kw_clauses)})")

    for idx, kw in enumerate(exclude_keywords):
        where_clauses.append(f"NOT (i.title ILIKE :ex_kw_{idx} OR i.description ILIKE :ex_kw_{idx})")
        params[f'ex_kw_{idx}'] = f'%{kw}%'

    where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

    # Build SELECT fields
    select_fields = [
        "i.id",
        "i.title",
        "i.link",
        "i.published",
        "COALESCE((a.impact_json->>'overall')::numeric, 0) as impact_score",
        "COALESCE((a.sentiment_json->'overall'->>'score')::numeric, 0) as sentiment_score"
    ]

    if include_description:
        select_fields.insert(3, "i.description")

    sql = f"""
        SELECT
            {', '.join(select_fields)}
        FROM items i
        LEFT JOIN item_analysis a ON i.id = a.item_id
        WHERE {where_sql}
        ORDER BY impact_score DESC, i.published DESC
        LIMIT :limit
    """
    params['limit'] = max_articles

    return text(sql), params


@router.get("/htmx/special_reports/{special_report_id}/articles", response_class=HTMLResponse)
@router.post("/htmx/special_reports/{special_report_id}/articles", response_class=HTMLResponse)
async def htmx_articles_list(
    request: Request,
    special_report_id: int,
    session: Session = Depends(get_session)
):
    """HTMX: Show article list matching current criteria (compact view for middle panel)."""
    # Support both GET and POST (HTMX uses GET on initial load, POST on form changes)
    if request.method == "POST":
        form_data = await request.form()
    else:
        # GET request - use default values or query params
        form_data = request.query_params

    # Use shared query builder
    sql, params = build_article_selection_query(form_data)

    # Execute
    with session.connection() as conn:
        result = conn.execute(sql, params)
        articles = result.fetchall()

    # Build compact HTML for middle panel
    if not articles:
        return '''
            <div class="text-center text-muted py-4">
                <i class="fas fa-inbox fa-2x mb-2 opacity-25"></i>
                <p>No articles match current filters</p>
            </div>
        '''

    html_parts = [f'<div class="text-muted mb-2"><small>{len(articles)} articles selected</small></div>']

    for row in articles:
        pub_date = row.published.strftime('%m/%d %H:%M') if row.published else 'N/A'
        impact_score = float(row.impact_score or 0)
        sentiment_score = float(row.sentiment_score or 0)

        impact_color = 'success' if impact_score >= 0.7 else ('warning' if impact_score >= 0.4 else 'secondary')
        sentiment_color = 'success' if sentiment_score > 0.3 else ('danger' if sentiment_score < -0.3 else 'secondary')

        html_parts.append(f'''
            <div class="article-card mb-2 p-2">
                <div class="d-flex gap-2 mb-1">
                    <span class="badge bg-{impact_color}" style="font-size:0.7em">{impact_score:.1f}</span>
                    <span class="badge bg-{sentiment_color}" style="font-size:0.7em">{sentiment_score:.1f}</span>
                    <small class="text-muted">{pub_date}</small>
                </div>
                <div class="text-light" style="font-size:0.85em; line-height:1.3">{row.title}</div>
            </div>
        ''')

    return ''.join(html_parts)


@router.post("/htmx/special_reports/{special_report_id}/test", response_class=HTMLResponse)
async def htmx_test_selection(
    request: Request,
    special_report_id: int,
    session: Session = Depends(get_session)
):
    """HTMX: Test article selection with current criteria."""
    form_data = await request.form()

    # Use shared query builder (with description for detailed test view)
    sql, params = build_article_selection_query(form_data, include_description=True)

    # Execute
    with session.connection() as conn:
        result = conn.execute(sql, params)
        articles = result.fetchall()

    # Build HTML response
    if not articles:
        return '''
            <div class="alert alert-warning">
                <i class="fas fa-exclamation-triangle"></i>
                <strong>No articles found</strong> with current criteria.
                <br><small>Try relaxing the filters or extending the timeframe.</small>
            </div>
        '''

    html_parts = [f'''
        <div class="alert alert-success mb-3">
            <i class="fas fa-check-circle"></i>
            <strong>Found {len(articles)} articles</strong> matching your criteria
        </div>
    ''']

    for i, row in enumerate(articles[:10], 1):  # Show first 10
        # row is a SQLAlchemy Row object with: id, title, link, description, published, impact_score, sentiment_score
        pub_date = row.published.strftime('%Y-%m-%d %H:%M') if row.published else 'N/A'
        impact_score = float(row.impact_score or 0)
        sentiment_score = float(row.sentiment_score or 0)

        impact_color = 'success' if impact_score >= 0.7 else ('warning' if impact_score >= 0.4 else 'secondary')
        sentiment_color = 'success' if sentiment_score > 0.3 else ('danger' if sentiment_score < -0.3 else 'secondary')

        description = row.description or ''
        description_preview = description[:200] if len(description) > 200 else description

        html_parts.append(f'''
            <div class="article-card">
                <div class="d-flex justify-content-between align-items-start mb-2">
                    <span class="badge bg-secondary">#{i}</span>
                    <div>
                        <span class="badge badge-metric bg-{impact_color}">Impact: {impact_score:.2f}</span>
                        <span class="badge badge-metric bg-{sentiment_color}">Sentiment: {sentiment_score:.2f}</span>
                    </div>
                </div>
                <h6 class="text-light mb-2">{row.title}</h6>
                <p class="text-muted small mb-2">{description_preview}{'...' if len(description) > 200 else ''}</p>
                <div class="d-flex justify-content-between align-items-center">
                    <small class="text-secondary">
                        <i class="fas fa-calendar"></i> {pub_date}
                    </small>
                    <a href="{row.link}" target="_blank" class="btn btn-sm btn-outline-primary">
                        <i class="fas fa-external-link-alt"></i> View
                    </a>
                </div>
            </div>
        ''')

    if len(articles) > 10:
        html_parts.append(f'''
            <div class="alert alert-info mt-3">
                <i class="fas fa-info-circle"></i>
                Showing first 10 of {len(articles)} articles. Actual report will include all {len(articles)}.
            </div>
        ''')

    return ''.join(html_parts)
