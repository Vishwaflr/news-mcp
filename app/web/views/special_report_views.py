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
                    <a href="/admin/content-special_reports/{special_report.id}" class="btn btn-sm btn-primary">
                        <i class="fas fa-eye"></i> View
                    </a>
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
