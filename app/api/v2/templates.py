"""
API endpoints for Content Template management.

Provides CRUD operations for templates and preview functionality.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select
from typing import List, Optional
from datetime import datetime

from app.database import get_session
from app.models.content_distribution import ContentTemplate, PendingContentGeneration
from app.schemas.content_distribution import (
    ContentTemplateCreate,
    ContentTemplateUpdate,
    ContentTemplate as ContentTemplateSchema,
    ContentTemplatePreview,
    ContentGenerationRequest,
    ContentGenerationResponse,
)

router = APIRouter(prefix="/templates", tags=["templates"])


@router.post("/", response_model=ContentTemplateSchema, status_code=201)
async def create_template(
    template_data: ContentTemplateCreate,
    session: Session = Depends(get_session)
):
    """
    Create a new content template.

    Args:
        template_data: Template configuration
        session: Database session

    Returns:
        Created template

    Raises:
        HTTPException: If template with same name exists
    """
    # Check for duplicate name
    existing = session.exec(
        select(ContentTemplate).where(ContentTemplate.name == template_data.name)
    ).first()

    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Template with name '{template_data.name}' already exists"
        )

    # Create template
    db_template = ContentTemplate(**template_data.model_dump())
    session.add(db_template)
    session.commit()
    session.refresh(db_template)

    return db_template


@router.get("/", response_model=List[ContentTemplateSchema])
async def list_templates(
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    session: Session = Depends(get_session)
):
    """
    List all content templates.

    Args:
        is_active: Filter by active status (optional)
        skip: Number of records to skip
        limit: Maximum records to return
        session: Database session

    Returns:
        List of templates
    """
    query = select(ContentTemplate)

    if is_active is not None:
        query = query.where(ContentTemplate.is_active == is_active)

    query = query.offset(skip).limit(limit)
    templates = session.exec(query).all()

    return templates


@router.get("/{template_id}", response_model=ContentTemplateSchema)
async def get_template(
    template_id: int,
    session: Session = Depends(get_session)
):
    """
    Get a specific template by ID.

    Args:
        template_id: Template ID
        session: Database session

    Returns:
        Template details

    Raises:
        HTTPException: If template not found
    """
    template = session.get(ContentTemplate, template_id)

    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    return template


@router.put("/{template_id}", response_model=ContentTemplateSchema)
async def update_template(
    template_id: int,
    template_data: ContentTemplateUpdate,
    session: Session = Depends(get_session)
):
    """
    Update a template.

    Args:
        template_id: Template ID
        template_data: Updated template data
        session: Database session

    Returns:
        Updated template

    Raises:
        HTTPException: If template not found or name conflict
    """
    template = session.get(ContentTemplate, template_id)

    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    # Check for name conflict if name is being updated
    if template_data.name and template_data.name != template.name:
        existing = session.exec(
            select(ContentTemplate).where(ContentTemplate.name == template_data.name)
        ).first()

        if existing:
            raise HTTPException(
                status_code=400,
                detail=f"Template with name '{template_data.name}' already exists"
            )

    # Update fields
    update_dict = template_data.model_dump(exclude_unset=True)
    for key, value in update_dict.items():
        setattr(template, key, value)

    template.updated_at = datetime.utcnow()
    template.version += 1

    session.add(template)
    session.commit()
    session.refresh(template)

    return template


@router.delete("/{template_id}", status_code=204)
async def delete_template(
    template_id: int,
    session: Session = Depends(get_session)
):
    """
    Delete a template.

    Args:
        template_id: Template ID
        session: Database session

    Raises:
        HTTPException: If template not found
    """
    template = session.get(ContentTemplate, template_id)

    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    session.delete(template)
    session.commit()

    return None


@router.post("/{template_id}/test", response_model=ContentTemplatePreview)
async def test_template(
    template_id: int,
    session: Session = Depends(get_session)
):
    """
    Test template by previewing article selection (dry-run).

    Does NOT generate content, only shows what would be selected.

    Args:
        template_id: Template ID
        session: Database session

    Returns:
        Preview of matching articles and cost estimate

    Raises:
        HTTPException: If template not found
    """
    from app.services.content_query_builder import build_article_query, estimate_generation_cost

    template = session.get(ContentTemplate, template_id)

    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    # Build query from template criteria
    articles = build_article_query(template.selection_criteria, session)

    # Get sample of results
    article_count = len(articles)
    sample_articles = articles[:5] if article_count > 0 else []

    # Estimate cost
    estimated_cost = estimate_generation_cost(
        template=template,
        article_count=article_count
    )

    # Build articles summary (fetch analysis separately)
    from app.models.analysis import ItemAnalysis
    articles_summary = []
    for a in sample_articles:
        # Fetch analysis separately
        analysis = session.exec(
            select(ItemAnalysis).where(ItemAnalysis.item_id == a.id)
        ).first()

        impact_score = None
        if analysis and analysis.impact_json:
            impact_score = analysis.impact_json.get('overall')

        articles_summary.append({
            "id": a.id,
            "title": a.title,
            "impact_score": impact_score,
            "published_at": a.published.isoformat() if a.published else None
        })

    return ContentTemplatePreview(
        template_id=template.id,
        matching_articles_count=article_count,
        sample_article_ids=[a.id for a in sample_articles],
        estimated_cost_usd=estimated_cost,
        estimated_time_seconds=max(5, article_count // 10),  # Rough estimate
        articles_summary=articles_summary
    )


@router.post("/{template_id}/generate", response_model=ContentGenerationResponse)
async def generate_content(
    template_id: int,
    request: Optional[ContentGenerationRequest] = None,
    session: Session = Depends(get_session)
):
    """
    Trigger content generation for a template.

    Args:
        template_id: Template ID
        request: Generation request options
        session: Database session

    Returns:
        Generation job details or generated content (sync mode)

    Raises:
        HTTPException: If template not found or inactive
    """
    template = session.get(ContentTemplate, template_id)

    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    if not template.is_active:
        raise HTTPException(status_code=400, detail="Template is inactive")

    # Default to async mode
    async_mode = request.async_mode if request else True

    # Queue generation job
    import uuid
    job_id = str(uuid.uuid4())

    pending_job = PendingContentGeneration(
        template_id=template.id,
        status="pending",
        triggered_by="manual"
    )
    session.add(pending_job)
    session.commit()

    if async_mode:
        return ContentGenerationResponse(
            success=True,
            job_id=job_id,
            status="queued",
            message=f"Content generation queued successfully for template '{template.name}'"
        )
    else:
        # TODO: Implement synchronous generation (wait for worker)
        raise HTTPException(
            status_code=501,
            detail="Synchronous generation not yet implemented. Use async_mode=true"
        )
