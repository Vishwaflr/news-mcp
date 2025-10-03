"""
API endpoints for Content Template management.

Provides CRUD operations for special-reports and preview functionality.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select
from typing import List, Optional
from datetime import datetime

from app.database import get_session
from app.models.content_distribution import SpecialReport, PendingContentGeneration
from app.schemas.content_distribution import (
    SpecialReportCreate,
    SpecialReportUpdate,
    SpecialReport as SpecialReportSchema,
    SpecialReportPreview,
    ContentGenerationRequest,
    ContentGenerationResponse,
)

router = APIRouter(prefix="/special-reports", tags=["special-reports"])


@router.post("/", response_model=SpecialReportSchema, status_code=201)
async def create_special_report(
    special_report_data: SpecialReportCreate,
    session: Session = Depends(get_session)
):
    """
    Create a new content special_report.

    Args:
        special_report_data: Template configuration
        session: Database session

    Returns:
        Created special_report

    Raises:
        HTTPException: If special_report with same name exists
    """
    # Check for duplicate name
    existing = session.exec(
        select(SpecialReport).where(SpecialReport.name == special_report_data.name)
    ).first()

    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Template with name '{special_report_data.name}' already exists"
        )

    # Create special_report
    db_special_report = SpecialReport(**special_report_data.model_dump())
    session.add(db_special_report)
    session.commit()
    session.refresh(db_special_report)

    return db_special_report


@router.get("/", response_model=List[SpecialReportSchema])
async def list_special_reports(
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    session: Session = Depends(get_session)
):
    """
    List all content special-reports.

    Args:
        is_active: Filter by active status (optional)
        skip: Number of records to skip
        limit: Maximum records to return
        session: Database session

    Returns:
        List of special-reports
    """
    query = select(SpecialReport)

    if is_active is not None:
        query = query.where(SpecialReport.is_active == is_active)

    query = query.offset(skip).limit(limit)
    special_reports = session.exec(query).all()

    return special_reports


@router.get("/{special_report_id}", response_model=SpecialReportSchema)
async def get_special_report(
    special_report_id: int,
    session: Session = Depends(get_session)
):
    """
    Get a specific special_report by ID.

    Args:
        special_report_id: Template ID
        session: Database session

    Returns:
        Template details

    Raises:
        HTTPException: If special_report not found
    """
    special_report = session.get(SpecialReport, special_report_id)

    if not special_report:
        raise HTTPException(status_code=404, detail="Template not found")

    return special_report


@router.put("/{special_report_id}", response_model=SpecialReportSchema)
async def update_special_report(
    special_report_id: int,
    special_report_data: SpecialReportUpdate,
    session: Session = Depends(get_session)
):
    """
    Update a special_report.

    Args:
        special_report_id: Template ID
        special_report_data: Updated special_report data
        session: Database session

    Returns:
        Updated special_report

    Raises:
        HTTPException: If special_report not found or name conflict
    """
    special_report = session.get(SpecialReport, special_report_id)

    if not special_report:
        raise HTTPException(status_code=404, detail="Template not found")

    # Check for name conflict if name is being updated
    if special_report_data.name and special_report_data.name != special_report.name:
        existing = session.exec(
            select(SpecialReport).where(SpecialReport.name == special_report_data.name)
        ).first()

        if existing:
            raise HTTPException(
                status_code=400,
                detail=f"Template with name '{special_report_data.name}' already exists"
            )

    # Update fields
    update_dict = special_report_data.model_dump(exclude_unset=True)
    for key, value in update_dict.items():
        setattr(special_report, key, value)

    special_report.updated_at = datetime.utcnow()
    special_report.version += 1

    session.add(special_report)
    session.commit()
    session.refresh(special_report)

    return special_report


@router.delete("/{special_report_id}", status_code=204)
async def delete_special_report(
    special_report_id: int,
    session: Session = Depends(get_session)
):
    """
    Delete a special_report.

    Args:
        special_report_id: Template ID
        session: Database session

    Raises:
        HTTPException: If special_report not found
    """
    special_report = session.get(SpecialReport, special_report_id)

    if not special_report:
        raise HTTPException(status_code=404, detail="Template not found")

    session.delete(special_report)
    session.commit()

    return None


@router.post("/{special_report_id}/test", response_model=SpecialReportPreview)
async def test_special_report(
    special_report_id: int,
    session: Session = Depends(get_session)
):
    """
    Test special_report by previewing article selection (dry-run).

    Does NOT generate content, only shows what would be selected.

    Args:
        special_report_id: Template ID
        session: Database session

    Returns:
        Preview of matching articles and cost estimate

    Raises:
        HTTPException: If special_report not found
    """
    from app.services.content_query_builder import build_article_query, estimate_generation_cost

    special_report = session.get(SpecialReport, special_report_id)

    if not special_report:
        raise HTTPException(status_code=404, detail="Template not found")

    # Build query from special_report criteria
    articles = build_article_query(special_report.selection_criteria, session)

    # Get sample of results
    article_count = len(articles)
    sample_articles = articles[:5] if article_count > 0 else []

    # Estimate cost
    estimated_cost = estimate_generation_cost(
        special_report=special_report,
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

    return SpecialReportPreview(
        special_report_id=special_report.id,
        matching_articles_count=article_count,
        sample_article_ids=[a.id for a in sample_articles],
        estimated_cost_usd=estimated_cost,
        estimated_time_seconds=max(5, article_count // 10),  # Rough estimate
        articles_summary=articles_summary
    )


@router.post("/{special_report_id}/generate", response_model=ContentGenerationResponse)
async def generate_content(
    special_report_id: int,
    request: Optional[ContentGenerationRequest] = None,
    session: Session = Depends(get_session)
):
    """
    Trigger content generation for a special_report.

    Args:
        special_report_id: Template ID
        request: Generation request options
        session: Database session

    Returns:
        Generation job details or generated content (sync mode)

    Raises:
        HTTPException: If special_report not found or inactive
    """
    special_report = session.get(SpecialReport, special_report_id)

    if not special_report:
        raise HTTPException(status_code=404, detail="Template not found")

    if not special_report.is_active:
        raise HTTPException(status_code=400, detail="Template is inactive")

    # Default to async mode
    async_mode = request.async_mode if request else True

    # Queue generation job
    import uuid
    job_id = str(uuid.uuid4())

    pending_job = PendingContentGeneration(
        special_report_id=special_report.id,
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
            message=f"Content generation queued successfully for special_report '{special_report.name}'"
        )
    else:
        # TODO: Implement synchronous generation (wait for worker)
        raise HTTPException(
            status_code=501,
            detail="Synchronous generation not yet implemented. Use async_mode=true"
        )
