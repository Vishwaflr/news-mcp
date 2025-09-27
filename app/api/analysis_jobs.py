from fastapi import APIRouter, HTTPException, Depends, Body
from typing import Dict, Optional

from app.domain.analysis.jobs import PreviewJob, JobResult, SelectionConfig, ModelParameters, AnalysisFilters
from app.services.domain.job_service import get_job_service, JobService
from app.core.logging_config import get_logger

router = APIRouter(prefix="/analysis/jobs", tags=["analysis-jobs"])
logger = get_logger(__name__)

@router.post("/preview", response_model=JobResult)
async def create_preview_job(
    selection: SelectionConfig = Body(...),
    parameters: ModelParameters = Body(...),
    filters: Optional[AnalysisFilters] = Body(None),
    job_service: JobService = Depends(get_job_service)
) -> JobResult:
    """Create a preview job for analysis estimation"""
    try:
        # Create job configuration
        job_config = PreviewJob(
            selection=selection,
            parameters=parameters,
            filters=filters or AnalysisFilters()
        )

        logger.info(f"Creating preview job for {selection.mode} selection with {parameters.model_tag}")

        # Create and calculate preview
        result = job_service.create_preview_job(job_config)

        if not result.success:
            raise HTTPException(status_code=400, detail=result.error)

        return result.data

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating preview job: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create preview job: {str(e)}")

@router.get("/{job_id}", response_model=PreviewJob)
async def get_job(
    job_id: str,
    job_service: JobService = Depends(get_job_service)
) -> PreviewJob:
    """Get a specific job by ID"""
    job = job_service.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    return job

@router.post("/{job_id}/refresh", response_model=JobResult)
async def refresh_job_estimates(
    job_id: str,
    job_service: JobService = Depends(get_job_service)
) -> JobResult:
    """Refresh estimates for an existing job"""
    result = job_service.refresh_job_estimates(job_id)

    if not result.success:
        if "not found" in result.error:
            raise HTTPException(status_code=404, detail=result.error)
        raise HTTPException(status_code=400, detail=result.error)

    return result.data

@router.get("/", response_model=Dict[str, PreviewJob])
async def list_active_jobs(
    job_service: JobService = Depends(get_job_service)
) -> Dict[str, PreviewJob]:
    """List all active preview jobs"""
    result = job_service.list_active_jobs()

    if not result.success:
        raise HTTPException(status_code=500, detail=result.error)

    return result.data

@router.post("/{job_id}/confirm")
async def confirm_job_for_execution(
    job_id: str,
    job_service: JobService = Depends(get_job_service)
):
    """Mark a job as confirmed and ready for execution"""
    result = job_service.update_job_status(job_id, "confirmed")

    if not result.success:
        if "not found" in result.error:
            raise HTTPException(status_code=404, detail=result.error)
        raise HTTPException(status_code=400, detail=result.error)

    return {"success": True, "job_id": job_id, "status": "confirmed"}

@router.post("/{job_id}/cancel")
async def cancel_job(
    job_id: str,
    job_service: JobService = Depends(get_job_service)
) -> dict:
    """Cancel a job and any associated analysis run"""
    try:
        # Update job status
        result = job_service.update_job_status(job_id, "cancelled")
        if not result.success:
            raise HTTPException(status_code=404, detail=result.error)

        # Check if job has an associated run and cancel it
        run_id = job_service.get_run_for_job(job_id)
        if run_id:
            # Cancel the analysis run
            from app.repositories.analysis_control import AnalysisControlRepo
            AnalysisControlRepo.update_run_status(run_id, "cancelled")
            return {"success": True, "job_id": job_id, "status": "cancelled", "run_id": run_id}

        return {"success": True, "job_id": job_id, "status": "cancelled"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling job {job_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to cancel job: {str(e)}")

# Alternative endpoint that mimics the existing preview API for compatibility
@router.post("/preview/legacy", response_model=JobResult)
async def create_preview_job_legacy(
    job_config: PreviewJob = Body(...),
    job_service: JobService = Depends(get_job_service)
) -> JobResult:
    """Create a preview job using full job configuration (legacy compatibility)"""
    try:
        result = job_service.create_preview_job(job_config)

        if not result.success:
            raise HTTPException(status_code=400, detail=result.error)

        return result.data

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating legacy preview job: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create preview job: {str(e)}")