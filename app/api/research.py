"""
Research API Endpoints
REST API for Perplexity-based research templates and runs
"""
from typing import List, Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from app.models.research import ResearchTemplate, ResearchRun
from app.repositories.research_template_repo import ResearchTemplateRepo
from app.repositories.research_run_repo import ResearchRunRepo
from app.services.perplexity.research_executor import ResearchExecutor
from app.core.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/api/research", tags=["research"])


# Request/Response Models
class TemplateCreate(BaseModel):
    name: str
    description: Optional[str] = None
    perplexity_function: str
    function_parameters: dict = {}
    llm_model: str
    llm_prompt: str
    llm_temperature: float = 0.7
    system_instruction: Optional[str] = None
    output_format: str = "markdown"
    output_schema: Optional[dict] = None
    schedule_enabled: bool = False
    cron_expression: Optional[str] = None
    is_active: bool = True
    created_by: Optional[str] = None
    tags: Optional[dict] = []


class TemplateUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    perplexity_function: Optional[str] = None
    function_parameters: Optional[dict] = None
    llm_model: Optional[str] = None
    llm_prompt: Optional[str] = None
    llm_temperature: Optional[float] = None
    system_instruction: Optional[str] = None
    output_format: Optional[str] = None
    output_schema: Optional[dict] = None
    schedule_enabled: Optional[bool] = None
    cron_expression: Optional[str] = None
    is_active: Optional[bool] = None


class ExecuteRequest(BaseModel):
    query: Optional[str] = None
    trigger_type: str = "manual"
    triggered_by: Optional[str] = None


# Template Endpoints
@router.get("/templates", response_model=List[ResearchTemplate])
async def list_templates(
    active_only: bool = False,
    scheduled_only: bool = False,
    limit: int = 100,
    offset: int = 0
):
    """List all research templates"""
    return ResearchTemplateRepo.list_all(
        active_only=active_only,
        scheduled_only=scheduled_only,
        limit=limit,
        offset=offset
    )


@router.get("/templates/{template_id}", response_model=ResearchTemplate)
async def get_template(template_id: int):
    """Get a specific template"""
    template = ResearchTemplateRepo.get_by_id(template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return template


@router.post("/templates", response_model=ResearchTemplate)
async def create_template(data: TemplateCreate):
    """Create a new research template"""
    # Check if name already exists
    existing = ResearchTemplateRepo.get_by_name(data.name)
    if existing:
        raise HTTPException(status_code=400, detail="Template name already exists")

    template = ResearchTemplate(**data.model_dump())
    return ResearchTemplateRepo.create(template)


@router.put("/templates/{template_id}", response_model=ResearchTemplate)
async def update_template(template_id: int, data: TemplateUpdate):
    """Update a template"""
    updates = {k: v for k, v in data.model_dump().items() if v is not None}

    template = ResearchTemplateRepo.update(template_id, **updates)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    return template


@router.delete("/templates/{template_id}")
async def delete_template(template_id: int):
    """Delete a template"""
    success = ResearchTemplateRepo.delete(template_id)
    if not success:
        raise HTTPException(status_code=404, detail="Template not found")

    return {"success": True, "message": f"Template {template_id} deleted"}


# Execution Endpoints
@router.post("/templates/{template_id}/execute", response_model=ResearchRun)
async def execute_template(
    template_id: int,
    data: ExecuteRequest,
    background_tasks: BackgroundTasks
):
    """Execute a research template"""
    executor = ResearchExecutor()

    try:
        run = await executor.execute_template(
            template_id=template_id,
            query=data.query,
            trigger_type=data.trigger_type,
            triggered_by=data.triggered_by
        )
        return run

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Template execution failed: {e}")
        raise HTTPException(status_code=500, detail=f"Execution failed: {str(e)}")


# Run Endpoints
@router.get("/runs", response_model=List[ResearchRun])
async def list_runs(
    template_id: Optional[int] = None,
    status: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
):
    """List research runs"""
    return ResearchRunRepo.list_all(
        template_id=template_id,
        status=status,
        limit=limit,
        offset=offset
    )


@router.get("/runs/{run_id}", response_model=ResearchRun)
async def get_run(run_id: int):
    """Get a specific run"""
    run = ResearchRunRepo.get_by_id(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return run


@router.get("/runs/pending", response_model=List[ResearchRun])
async def get_pending_runs(limit: int = 10):
    """Get pending runs ready for execution"""
    return ResearchRunRepo.get_pending_runs(limit=limit)


@router.get("/runs/active", response_model=List[ResearchRun])
async def get_active_runs():
    """Get currently running executions"""
    return ResearchRunRepo.get_active_runs()


@router.delete("/runs/{run_id}")
async def delete_run(run_id: int):
    """Delete a run"""
    success = ResearchRunRepo.delete(run_id)
    if not success:
        raise HTTPException(status_code=404, detail="Run not found")

    return {"success": True, "message": f"Run {run_id} deleted"}


# Analytics Endpoints
@router.get("/analytics/cost-summary")
async def get_cost_summary(hours: int = 24):
    """Get cost summary for recent runs"""
    return ResearchRunRepo.get_cost_summary(hours=hours)


@router.get("/analytics/functions")
async def list_available_functions():
    """List all available Perplexity functions"""
    executor = ResearchExecutor()
    functions = executor.list_available_functions()

    return {
        "functions": functions,
        "count": len(functions)
    }
