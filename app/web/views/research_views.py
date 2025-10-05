"""
HTMX views for Research Templates UI
"""
from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session
from typing import Optional

from app.database import get_session
from app.repositories.research_template_repo import ResearchTemplateRepo
from app.repositories.research_run_repo import ResearchRunRepo
from app.services.perplexity.research_executor import ResearchExecutor

router = APIRouter(tags=["research-views"])
templates = Jinja2Templates(directory="templates")


@router.get("/admin/research", response_class=HTMLResponse)
async def research_templates_page(request: Request):
    """Main research templates overview page"""
    return templates.TemplateResponse(
        "admin/research.html",
        {"request": request}
    )


@router.get("/admin/research/templates/new", response_class=HTMLResponse)
async def new_template_page(request: Request):
    """Create new research template page"""
    executor = ResearchExecutor()
    available_functions = executor.list_available_functions()

    return templates.TemplateResponse(
        "admin/research_template_edit.html",
        {
            "request": request,
            "template": None,
            "available_functions": available_functions,
            "mode": "create"
        }
    )


@router.get("/admin/research/templates/{template_id}/edit", response_class=HTMLResponse)
async def edit_template_page(
    request: Request,
    template_id: int,
    session: Session = Depends(get_session)
):
    """Edit research template page"""
    template = ResearchTemplateRepo.get_by_id(template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    executor = ResearchExecutor()
    available_functions = executor.list_available_functions()

    return templates.TemplateResponse(
        "admin/research_template_edit.html",
        {
            "request": request,
            "template": template,
            "available_functions": available_functions,
            "mode": "edit"
        }
    )


@router.get("/admin/research/runs", response_class=HTMLResponse)
async def research_runs_page(request: Request):
    """Research runs history page"""
    return templates.TemplateResponse(
        "admin/research_runs.html",
        {"request": request}
    )


@router.get("/admin/research/runs/{run_id}", response_class=HTMLResponse)
async def research_run_detail_page(
    request: Request,
    run_id: int
):
    """Research run detail page"""
    run = ResearchRunRepo.get_by_id(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    template = None
    if run.template_id:
        template = ResearchTemplateRepo.get_by_id(run.template_id)

    return templates.TemplateResponse(
        "admin/research_run_detail.html",
        {
            "request": request,
            "run": run,
            "template": template
        }
    )


# HTMX Endpoints
@router.get("/htmx/research/templates/list", response_class=HTMLResponse)
async def htmx_templates_list(
    active_only: bool = False,
    session: Session = Depends(get_session)
):
    """HTMX: Research templates list"""
    templates_list = ResearchTemplateRepo.list_all(active_only=active_only, limit=100)

    if not templates_list:
        return """
        <div class="alert alert-info">
            <i class="bi bi-info-circle me-2"></i>
            No research templates found. Create your first template to get started!
        </div>
        """

    html = ""
    for template in templates_list:
        status_badge = '<span class="badge bg-success">Active</span>' if template.is_active else '<span class="badge bg-secondary">Inactive</span>'
        schedule_badge = f'<span class="badge bg-primary"><i class="bi bi-clock"></i> {template.cron_expression}</span>' if template.schedule_enabled else '<span class="badge bg-light text-dark">Manual</span>'

        html += f"""
        <tr>
            <td>
                <strong>{template.name}</strong>
                <br><small class="text-muted">{template.description or ''}</small>
            </td>
            <td><code>{template.perplexity_function}</code></td>
            <td><code>{template.llm_model}</code></td>
            <td>{schedule_badge}</td>
            <td>{status_badge}</td>
            <td>
                <div class="btn-group btn-group-sm">
                    <button class="btn btn-success" onclick="openQueryModal({template.id})">
                        <i class="bi bi-play-fill"></i> Execute
                    </button>
                    <a href="/admin/research/templates/{template.id}/edit" class="btn btn-primary">
                        <i class="bi bi-pencil"></i> Edit
                    </a>
                    <button class="btn btn-danger" hx-delete="/htmx/research/templates/{template.id}" hx-confirm="Delete template '{template.name}'?" hx-target="closest tr" hx-swap="outerHTML">
                        <i class="bi bi-trash"></i>
                    </button>
                </div>
            </td>
        </tr>
        """

    return html


@router.get("/htmx/research/runs/list", response_class=HTMLResponse)
async def htmx_runs_list(
    template_id: Optional[int] = None,
    limit: int = 50,
    session: Session = Depends(get_session)
):
    """HTMX: Research runs list"""
    runs = ResearchRunRepo.list_all(template_id=template_id, limit=limit)

    if not runs:
        return """
        <div class="alert alert-info">
            <i class="bi bi-info-circle me-2"></i>
            No runs found. Execute a template to see results here!
        </div>
        """

    html = ""
    for run in runs:
        # Status badge
        status_colors = {
            "pending": "secondary",
            "running": "primary",
            "completed": "success",
            "failed": "danger"
        }
        status_badge = f'<span class="badge bg-{status_colors.get(run.status, "secondary")}">{run.status.upper()}</span>'

        # Template name
        template_name = "Unknown"
        if run.template_id:
            template = ResearchTemplateRepo.get_by_id(run.template_id)
            template_name = template.name if template else f"Template #{run.template_id}"

        # Duration
        duration = f"{run.duration_seconds}s" if run.duration_seconds else "N/A"

        # Cost
        cost_display = f"${run.cost_usd:.4f}" if run.cost_usd else "N/A"

        html += f"""
        <tr>
            <td><small class="text-muted">#{run.id}</small></td>
            <td>{run.created_at.strftime('%Y-%m-%d %H:%M:%S')}</td>
            <td>{template_name}</td>
            <td>{status_badge}</td>
            <td>{run.tokens_used or 'N/A'}</td>
            <td>{cost_display}</td>
            <td>{duration}</td>
            <td>
                <div class="btn-group btn-group-sm">
                    <a href="/admin/research/runs/{run.id}" class="btn btn-sm btn-primary">
                        <i class="bi bi-eye"></i> View
                    </a>
                    <button class="btn btn-sm btn-danger" hx-delete="/htmx/research/runs/{run.id}" hx-confirm="Delete run #{run.id}?" hx-target="closest tr" hx-swap="outerHTML">
                        <i class="bi bi-trash"></i>
                    </button>
                </div>
            </td>
        </tr>
        """

    return html


@router.post("/htmx/research/templates/{template_id}/execute", response_class=HTMLResponse)
async def htmx_execute_template(
    template_id: int,
    request: Request,
    session: Session = Depends(get_session)
):
    """HTMX: Execute a research template"""
    try:
        # Get query from form data
        form = await request.form()
        query = form.get("query", "").strip()

        if not query:
            return """
            <div class="alert alert-danger alert-dismissible fade show">
                <i class="bi bi-exclamation-triangle me-2"></i>
                <strong>Error:</strong> Query is required
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            </div>
            """

        executor = ResearchExecutor()
        run = await executor.execute_template(
            template_id=template_id,
            query=query,
            trigger_type="manual",
            triggered_by="web_ui"
        )

        return f"""
        <div class="alert alert-success alert-dismissible fade show">
            <i class="bi bi-check-circle me-2"></i>
            <strong>Execution started!</strong> Run #{run.id} is {run.status}.
            <a href="/admin/research/runs/{run.id}" class="alert-link">View details</a>
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
        """
    except Exception as e:
        return f"""
        <div class="alert alert-danger alert-dismissible fade show">
            <i class="bi bi-exclamation-triangle me-2"></i>
            <strong>Execution failed:</strong> {str(e)}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
        """


@router.delete("/htmx/research/templates/{template_id}", response_class=HTMLResponse)
async def htmx_delete_template(template_id: int):
    """HTMX: Delete a research template"""
    success = ResearchTemplateRepo.delete(template_id)
    if success:
        return ""  # Row will be removed by hx-swap="outerHTML"
    else:
        return f'<td colspan="6" class="text-danger">Failed to delete template</td>'


@router.delete("/htmx/research/runs/{run_id}", response_class=HTMLResponse)
async def htmx_delete_run(run_id: int):
    """HTMX: Delete a research run"""
    success = ResearchRunRepo.delete(run_id)
    if success:
        return ""  # Row will be removed
    else:
        return f'<td colspan="8" class="text-danger">Failed to delete run</td>'


@router.get("/htmx/research/analytics/cost-summary", response_class=HTMLResponse)
async def htmx_cost_summary(hours: int = 24):
    """HTMX: Cost summary widget"""
    summary = ResearchRunRepo.get_cost_summary(hours=hours)

    return f"""
    <div class="row g-3">
        <div class="col-md-3">
            <div class="card bg-dark border-primary">
                <div class="card-body text-center">
                    <h6 class="text-muted">Total Runs</h6>
                    <h3 class="text-primary">{summary['total_runs']}</h3>
                    <small class="text-muted">Last {hours}h</small>
                </div>
            </div>
        </div>
        <div class="col-md-3">
            <div class="card bg-dark border-success">
                <div class="card-body text-center">
                    <h6 class="text-muted">Completed</h6>
                    <h3 class="text-success">{summary['completed_runs']}</h3>
                </div>
            </div>
        </div>
        <div class="col-md-3">
            <div class="card bg-dark border-warning">
                <div class="card-body text-center">
                    <h6 class="text-muted">Total Tokens</h6>
                    <h3 class="text-warning">{summary['total_tokens']:,}</h3>
                </div>
            </div>
        </div>
        <div class="col-md-3">
            <div class="card bg-dark border-info">
                <div class="card-body text-center">
                    <h6 class="text-muted">Total Cost</h6>
                    <h3 class="text-info">${summary['total_cost_usd']:.4f}</h3>
                    <small class="text-muted">Perplexity: ${summary['perplexity_cost_usd']:.4f}</small>
                </div>
            </div>
        </div>
    </div>
    """
