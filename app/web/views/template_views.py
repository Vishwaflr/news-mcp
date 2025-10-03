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
from app.models.content_distribution import ContentTemplate, GeneratedContent
from app.config import settings

router = APIRouter(tags=["template-views"])
templates = Jinja2Templates(directory="templates")


@router.get("/admin/content-templates", response_class=HTMLResponse)
async def content_templates_page(request: Request):
    """Main content templates overview page."""
    return templates.TemplateResponse(
        "admin/content_templates.html",
        {"request": request}
    )


@router.get("/admin/content-templates/{template_id}", response_class=HTMLResponse)
async def content_template_detail_page(
    request: Request,
    template_id: int,
    session: Session = Depends(get_session)
):
    """Content template detail page with generated content."""
    template = session.get(ContentTemplate, template_id)

    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    return templates.TemplateResponse(
        "admin/template_detail.html",
        {
            "request": request,
            "template": template
        }
    )


@router.get("/htmx/templates/list", response_class=HTMLResponse)
async def htmx_templates_list(session: Session = Depends(get_session)):
    """HTMX: Templates list."""
    query = select(ContentTemplate).order_by(ContentTemplate.created_at.desc())
    all_templates = session.exec(query).all()

    if not all_templates:
        return """
        <div class="alert alert-info bg-dark border-info text-light">
            <i class="fas fa-info-circle"></i>
            No templates found. Create your first template via the API.
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

    for template in all_templates:
        status_badge = 'bg-success' if template.is_active else 'bg-secondary'
        status_text = 'Active' if template.is_active else 'Inactive'

        html_parts.append(f'''
            <tr>
                <td>
                    <strong>{template.name}</strong>
                    <br>
                    <small class="text-muted">{template.description or 'No description'}</small>
                </td>
                <td>{template.target_audience or '-'}</td>
                <td><code>{template.llm_model}</code></td>
                <td>{template.generation_schedule or 'On-demand'}</td>
                <td><span class="badge {status_badge}">{status_text}</span></td>
                <td>
                    <a href="/admin/content-templates/{template.id}" class="btn btn-sm btn-primary">
                        <i class="fas fa-eye"></i> View
                    </a>
                </td>
            </tr>
        ''')

    html_parts.append('</tbody></table></div>')

    return ''.join(html_parts)


@router.get("/htmx/templates/{template_id}/content", response_class=HTMLResponse)
async def htmx_template_content(
    template_id: int,
    session: Session = Depends(get_session)
):
    """HTMX: Generated content list for template."""
    query = select(GeneratedContent).where(
        GeneratedContent.template_id == template_id
    ).order_by(GeneratedContent.generated_at.desc())

    content_list = session.exec(query).all()

    if not content_list:
        return """
        <div class="alert alert-warning bg-dark border-warning text-light">
            <i class="fas fa-exclamation-triangle"></i>
            No content generated yet for this template.
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
