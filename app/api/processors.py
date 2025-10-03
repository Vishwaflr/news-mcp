from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

from app.database import get_session
from app.models import (
    ProcessorType, ProcessingStatus
)
from app.models.content import ContentProcessingLog
from app.services.domain.processor_service import ProcessorService
from app.dependencies import get_processor_service
from app.processors.manager import ContentProcessingManager
from app.processors.validator import ProcessorConfigValidator

router = APIRouter(prefix="/processors", tags=["processors"])

@router.get("/types")
def get_processor_types(processor_service: ProcessorService = Depends(get_processor_service)):
    """Get all available processor types"""
    result = processor_service.get_available_processor_types()

    if not result.success:
        raise HTTPException(status_code=500, detail=result.error)

    return result.data

@router.get("/config/{feed_id}")
def get_feed_processor_config(
    feed_id: int,
    processor_service: ProcessorService = Depends(get_processor_service)
):
    """Get processor configuration for a specific feed"""
    result = processor_service.get_feed_processor_config(feed_id)

    if not result.success:
        if "not found" in result.error:
            raise HTTPException(status_code=404, detail=result.error)
        raise HTTPException(status_code=500, detail=result.error)

    return result.data

@router.post("/config/{feed_id}")
def create_or_update_feed_processor_config(
    feed_id: int,
    processor_type: ProcessorType,
    config: Dict[str, Any] = {},
    is_active: bool = True,
    session: Session = Depends(get_session)
):
    """Create or update processor configuration for a feed"""

    # Validate processor configuration first
    validation_result = ProcessorConfigValidator.validate_config(
        processor_type.value, config
    )

    if not validation_result["is_valid"]:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Invalid processor configuration",
                "errors": validation_result["errors"]
            }
        )

    processor_service = ProcessorService(session)
    result = processor_service.create_or_update_processor_config(
        feed_id=feed_id,
        processor_type=processor_type,
        config=config,
        is_active=is_active
    )

    if not result.success:
        if "not found" in result.error:
            raise HTTPException(status_code=404, detail=result.error)
        raise HTTPException(status_code=400, detail=result.error)

    return {
        "message": "Processor configuration updated successfully",
        "feed_id": feed_id,
        "processor_type": processor_type.value,
        "warnings": validation_result.get("warnings", [])
    }

@router.delete("/config/{feed_id}")
def delete_feed_processor_config(feed_id: int, session: Session = Depends(get_session)):
    """Delete processor configuration for a feed (revert to default)"""

    processor_service = ProcessorService(session)
    result = processor_service.delete_processor_config(feed_id)

    if not result.success:
        if "not found" in result.error:
            raise HTTPException(status_code=404, detail=result.error)
        raise HTTPException(status_code=500, detail=result.error)

    return {
        "message": "Processor configuration deleted successfully",
        "feed_id": feed_id,
        "note": "Feed will now use default processor (Universal)"
    }

@router.get("/templates")
def get_processor_templates(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    is_active: Optional[bool] = None,
    processor_service: ProcessorService = Depends(get_processor_service)
):
    """Get all processor templates"""

    result = processor_service.get_processor_templates(active_only=is_active)

    if not result.success:
        raise HTTPException(status_code=500, detail=result.error)

    templates = result.data
    return {
        "templates": [
            {
                "id": template.id,
                "name": template.name,
                "processor_type": template.processor_type.value,
                "config": template.config,
                "description": template.description,
                "is_active": template.is_active,
                "created_at": template.created_at
            }
            for template in templates[skip:skip+limit]
        ],
        "total": len(templates)
    }

@router.post("/templates")
def create_processor_template(
    name: str,
    processor_type: ProcessorType,
    config: Dict[str, Any] = {},
    description: Optional[str] = None,
    is_active: bool = True,
    session: Session = Depends(get_session)
):
    """Create a new processor template"""

    # Validate processor configuration
    validation_result = ProcessorConfigValidator.validate_config(
        processor_type.value, config
    )

    if not validation_result["is_valid"]:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Invalid processor configuration",
                "errors": validation_result["errors"]
            }
        )

    processor_service = ProcessorService(session)
    result = processor_service.create_processor_template(
        name=name,
        processor_type=processor_type,
        config=config,
        description=description,
        is_active=is_active
    )

    if not result.success:
        if "already exists" in result.error:
            raise HTTPException(status_code=400, detail=result.error)
        raise HTTPException(status_code=500, detail=result.error)

    return {
        "message": "Processor template created successfully",
        "template_id": result.data.id,
        "warnings": validation_result.get("warnings", [])
    }

@router.put("/templates/{template_id}")
def update_processor_template(
    template_id: int,
    name: Optional[str] = None,
    processor_type: Optional[ProcessorType] = None,
    patterns: Optional[List[str]] = None,
    config: Optional[Dict[str, Any]] = None,
    is_active: Optional[bool] = None,
    session: Session = Depends(get_session)
):
    """Update a processor template"""

    template = session.get(ProcessorTemplate, template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    # Update fields if provided
    if name is not None:
        # Check for duplicate name (exclude current template)
        existing = session.exec(
            select(ProcessorTemplate).where(
                ProcessorTemplate.name == name,
                ProcessorTemplate.id != template_id
            )
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="Template name already exists")
        template.name = name

    if processor_type is not None:
        template.processor_type = processor_type

    if patterns is not None:
        template.patterns = patterns

    if config is not None:
        # Validate new configuration
        type_to_validate = processor_type.value if processor_type else template.processor_type.value
        validation_result = ProcessorConfigValidator.validate_config(type_to_validate, config)

        if not validation_result["is_valid"]:
            raise HTTPException(
                status_code=400,
                detail={
                    "message": "Invalid processor configuration",
                    "errors": validation_result["errors"]
                }
            )

        template.config = config

    if is_active is not None:
        template.is_active = is_active

    template.updated_at = datetime.utcnow()
    session.add(template)
    session.commit()

    return {
        "message": "Template updated successfully",
        "template_id": template_id
    }

@router.delete("/templates/{template_id}")
def delete_processor_template(template_id: int, session: Session = Depends(get_session)):
    """Delete a processor template"""

    template = session.get(ProcessorTemplate, template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    session.delete(template)
    session.commit()

    return {"message": "Template deleted successfully"}

@router.get("/stats")
def get_processing_statistics(
    feed_id: Optional[int] = None,
    days: int = Query(7, ge=1, le=365),
    processor_service: ProcessorService = Depends(get_processor_service)
):
    """Get processing statistics"""

    result = processor_service.get_processing_statistics(days=days)

    if not result.success:
        raise HTTPException(status_code=500, detail=result.error)

    return result.data

@router.post("/reprocess/feed/{feed_id}")
def reprocess_feed_items(
    feed_id: int,
    limit: Optional[int] = Query(None, ge=1, le=1000),
    force_all: bool = Query(False, description="Reprocess all items, not just failed ones"),
    session: Session = Depends(get_session)
):
    """Reprocess items from a specific feed"""

    processor_service = ProcessorService(session)
    feed_ids = [feed_id] if feed_id else None
    failed_only = not force_all

    result = processor_service.trigger_reprocessing(
        feed_ids=feed_ids,
        failed_only=failed_only
    )

    if not result.success:
        if "not found" in result.error:
            raise HTTPException(status_code=404, detail=result.error)
        raise HTTPException(status_code=500, detail=result.error)

    return result.data

@router.post("/reprocess/item/{item_id}")
def reprocess_single_item(item_id: int, session: Session = Depends(get_session)):
    """Reprocess a single item"""

    from app.models import Item

    item = session.get(Item, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    # Initialize content manager
    content_manager = ContentProcessingManager(session)

    try:
        success = content_manager.reprocess_item(item)
        session.commit()

        if success:
            return {
                "message": "Item reprocessed successfully",
                "item_id": item_id
            }
        else:
            return {
                "message": "Item reprocessing failed",
                "item_id": item_id
            }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error reprocessing item: {str(e)}"
        )

@router.get("/health")
def get_processor_health(session: Session = Depends(get_session)):
    """Get overall processor health metrics"""

    from app.processors.factory import ProcessorFactory

    # Get recent processing activity
    recent_logs = session.exec(
        select(ContentProcessingLog).where(
            ContentProcessingLog.processed_at >= datetime.utcnow() - timedelta(hours=24)
        )
    ).all()

    # Calculate health metrics
    total_processed = len(recent_logs)
    successful = len([log for log in recent_logs if log.processing_status == ProcessingStatus.SUCCESS])
    failed = len([log for log in recent_logs if log.processing_status == ProcessingStatus.FAILED])

    success_rate = (successful / total_processed) if total_processed > 0 else 0

    # Get processor type breakdown
    processor_breakdown = {}
    for log in recent_logs:
        proc_type = log.processor_type.value
        if proc_type not in processor_breakdown:
            processor_breakdown[proc_type] = {"total": 0, "success": 0, "failed": 0}

        processor_breakdown[proc_type]["total"] += 1
        if log.processing_status == ProcessingStatus.SUCCESS:
            processor_breakdown[proc_type]["success"] += 1
        else:
            processor_breakdown[proc_type]["failed"] += 1

    # Calculate success rates for each processor
    for proc_type, stats in processor_breakdown.items():
        stats["success_rate"] = (stats["success"] / stats["total"]) if stats["total"] > 0 else 0

    # Get available processors
    available_processors = ProcessorFactory.get_available_processors()

    return {
        "overall_health": "healthy" if success_rate > 0.9 else "degraded" if success_rate > 0.7 else "unhealthy",
        "success_rate": success_rate,
        "24h_activity": {
            "total_processed": total_processed,
            "successful": successful,
            "failed": failed
        },
        "processor_breakdown": processor_breakdown,
        "available_processors": list(available_processors.keys()),
        "last_updated": datetime.utcnow()
    }

@router.post("/validate-config")
def validate_processor_config(
    processor_type: ProcessorType,
    config: Dict[str, Any]
):
    """Validate a processor configuration without saving it"""

    validation_result = ProcessorConfigValidator.validate_config(
        processor_type.value, config
    )

    return {
        "is_valid": validation_result["is_valid"],
        "errors": validation_result.get("errors", []),
        "warnings": validation_result.get("warnings", []),
        "processor_type": processor_type.value
    }