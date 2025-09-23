from fastapi import APIRouter, Depends, HTTPException, Body
from sqlmodel import Session, select
from typing import List, Optional, Dict, Any
from app.core.logging_config import get_logger
import requests
from urllib.parse import urlparse

from app.database import get_session
from app.models import DynamicFeedTemplate, Feed, FeedTemplateAssignment
from app.services.dynamic_template_manager import get_dynamic_template_manager
from app.services.feed_change_tracker import track_template_changes

router = APIRouter(prefix="/templates", tags=["templates"])
logger = get_logger(__name__)

# Standard response format for MCP v2
def create_response(data: Any = None, error: str = None, meta: Dict[str, Any] = None) -> Dict[str, Any]:
    """Create standardized API response for MCP v2"""
    return {
        "ok": error is None,
        "data": data,
        "meta": meta or {},
        "errors": [{"code": "api_error", "message": error}] if error else []
    }

@router.get("/")
def list_templates(
    assigned_to_feed_id: Optional[int] = None,
    active_only: bool = True,
    session: Session = Depends(get_session)
):
    """List dynamic feed templates with optional filtering"""
    try:
        query = select(DynamicFeedTemplate)

        if active_only:
            query = query.where(DynamicFeedTemplate.is_active == True)

        if assigned_to_feed_id:
            # Get templates assigned to specific feed
            assignments = session.exec(
                select(FeedTemplateAssignment.template_id)
                .where(FeedTemplateAssignment.feed_id == assigned_to_feed_id)
            ).all()
            template_ids = [a for a in assignments]
            if template_ids:
                query = query.where(DynamicFeedTemplate.id.in_(template_ids))
            else:
                # No templates assigned to this feed
                return create_response(data=[])

        templates = session.exec(query.order_by(DynamicFeedTemplate.created_at.desc())).all()

        # Convert to dict format for JSON serialization
        templates_data = []
        for template in templates:
            template_dict = {
                "id": template.id,
                "name": template.name,
                "description": template.description,
                "match_rules": template.match_rules,
                "extraction_config": template.extraction_config,
                "processing_rules": template.processing_rules,
                "is_active": template.is_active,
                "is_builtin": template.is_builtin,
                "created_at": template.created_at.isoformat() if template.created_at else None,
                "updated_at": template.updated_at.isoformat() if template.updated_at else None
            }
            templates_data.append(template_dict)

        return create_response(
            data=templates_data,
            meta={"total": len(templates_data)}
        )

    except Exception as e:
        logger.error(f"Error listing templates: {e}")
        return create_response(error=f"Failed to list templates: {str(e)}")

@router.post("/create")
def create_template(
    name: str = Body(...),
    description: Optional[str] = Body(None),
    match_rules: List[Dict[str, Any]] = Body(...),
    extraction_config: Dict[str, Any] = Body(...),
    processing_rules: Optional[Dict[str, Any]] = Body(None),
    session: Session = Depends(get_session)
):
    """Create a new dynamic feed template"""
    try:
        manager = get_dynamic_template_manager(session)

        template = manager.create_template(
            name=name,
            description=description,
            match_rules=match_rules,
            extraction_config=extraction_config,
            processing_rules=processing_rules or {},
            created_by="api_user"
        )

        if not template:
            return create_response(error="Failed to create template")

        return create_response(data={
            "id": template.id,
            "name": template.name,
            "description": template.description,
            "created_at": template.created_at.isoformat() if template.created_at else None
        })

    except Exception as e:
        logger.error(f"Error creating template: {e}")
        return create_response(error=f"Failed to create template: {str(e)}")

@router.put("/{template_id}")
def update_template(
    template_id: int,
    name: Optional[str] = Body(None),
    description: Optional[str] = Body(None),
    match_rules: Optional[List[Dict[str, Any]]] = Body(None),
    extraction_config: Optional[Dict[str, Any]] = Body(None),
    processing_rules: Optional[Dict[str, Any]] = Body(None),
    is_active: Optional[bool] = Body(None),
    session: Session = Depends(get_session)
):
    """Update an existing template"""
    try:
        manager = get_dynamic_template_manager(session)

        # Build update kwargs
        update_kwargs = {}
        if name is not None:
            update_kwargs["name"] = name
        if description is not None:
            update_kwargs["description"] = description
        if match_rules is not None:
            update_kwargs["match_rules"] = match_rules
        if extraction_config is not None:
            update_kwargs["extraction_config"] = extraction_config
        if processing_rules is not None:
            update_kwargs["processing_rules"] = processing_rules
        if is_active is not None:
            update_kwargs["is_active"] = is_active

        template = manager.update_template(
            template_id=template_id,
            updated_by="api_user",
            **update_kwargs
        )

        if not template:
            return create_response(error="Template not found or update failed")

        return create_response(data={
            "id": template.id,
            "name": template.name,
            "description": template.description,
            "is_active": template.is_active,
            "updated_at": template.updated_at.isoformat() if template.updated_at else None
        })

    except Exception as e:
        logger.error(f"Error updating template {template_id}: {e}")
        return create_response(error=f"Failed to update template: {str(e)}")

@router.post("/{template_id}/test")
def test_template(
    template_id: int,
    sample_url: Optional[str] = Body(None),
    raw_html: Optional[str] = Body(None),
    session: Session = Depends(get_session)
):
    """Test a template against sample content"""
    try:
        if not sample_url and not raw_html:
            return create_response(error="Either sample_url or raw_html must be provided")

        # Get template
        template = session.get(DynamicFeedTemplate, template_id)
        if not template:
            return create_response(error="Template not found")

        # Get content to test
        if sample_url:
            try:
                response = requests.get(sample_url, timeout=10, headers={
                    'User-Agent': 'Mozilla/5.0 (compatible; News-MCP Template Tester)'
                })
                response.raise_for_status()
                html_content = response.text
            except requests.RequestException as e:
                return create_response(error=f"Failed to fetch URL: {str(e)}")
        else:
            html_content = raw_html

        # Test extraction
        manager = get_dynamic_template_manager(session)
        config = manager._template_to_config_dict(template)

        # Simple extraction simulation (would need proper HTML parsing library)
        extracted = {
            "title": "Sample extracted title",
            "content": "Sample extracted content",
            "published_at": None,
            "author": None
        }

        # Validate against processing rules
        violations = []
        if template.processing_rules:
            min_title_len = template.processing_rules.get("min_title_len", 0)
            if len(extracted.get("title", "")) < min_title_len:
                violations.append({
                    "rule": "min_title_len",
                    "actual": len(extracted.get("title", "")),
                    "min": min_title_len
                })

        return create_response(data={
            "template_id": template_id,
            "template_name": template.name,
            "extracted": extracted,
            "violations": violations,
            "test_url": sample_url,
            "html_length": len(html_content)
        })

    except Exception as e:
        logger.error(f"Error testing template {template_id}: {e}")
        return create_response(error=f"Failed to test template: {str(e)}")

@router.post("/{template_id}/assign")
def assign_template(
    template_id: int,
    feed_id: int = Body(...),
    priority: Optional[int] = Body(100),
    custom_overrides: Optional[Dict[str, Any]] = Body(None),
    session: Session = Depends(get_session)
):
    """Assign a template to a feed"""
    try:
        # Verify template exists
        template = session.get(DynamicFeedTemplate, template_id)
        if not template:
            return create_response(error="Template not found")

        # Verify feed exists
        feed = session.get(Feed, feed_id)
        if not feed:
            return create_response(error="Feed not found")

        manager = get_dynamic_template_manager(session)
        success = manager.assign_template_to_feed(
            feed_id=feed_id,
            template_id=template_id,
            priority=priority,
            custom_overrides=custom_overrides or {},
            assigned_by="api_user"
        )

        if not success:
            return create_response(error="Failed to assign template to feed")

        return create_response(data={
            "template_id": template_id,
            "feed_id": feed_id,
            "priority": priority,
            "assigned_at": "now"  # Would be actual timestamp
        })

    except Exception as e:
        logger.error(f"Error assigning template {template_id} to feed {feed_id}: {e}")
        return create_response(error=f"Failed to assign template: {str(e)}")

@router.delete("/{template_id}/assign/{feed_id}")
def unassign_template(
    template_id: int,
    feed_id: int,
    session: Session = Depends(get_session)
):
    """Unassign a template from a feed"""
    try:
        manager = get_dynamic_template_manager(session)
        success = manager.unassign_template_from_feed(
            feed_id=feed_id,
            template_id=template_id
        )

        if not success:
            return create_response(error="Template assignment not found or already removed")

        return create_response(data={
            "template_id": template_id,
            "feed_id": feed_id,
            "unassigned_at": "now"
        })

    except Exception as e:
        logger.error(f"Error unassigning template {template_id} from feed {feed_id}: {e}")
        return create_response(error=f"Failed to unassign template: {str(e)}")

@router.delete("/{template_id}")
def delete_template(
    template_id: int,
    session: Session = Depends(get_session)
):
    """Delete a template (if not builtin)"""
    try:
        template = session.get(DynamicFeedTemplate, template_id)
        if not template:
            return create_response(error="Template not found")

        if template.is_builtin:
            return create_response(error="Cannot delete builtin template")

        manager = get_dynamic_template_manager(session)
        success = manager.delete_template(template_id)

        if not success:
            return create_response(error="Failed to delete template")

        return create_response(data={
            "template_id": template_id,
            "deleted_at": "now"
        })

    except Exception as e:
        logger.error(f"Error deleting template {template_id}: {e}")
        return create_response(error=f"Failed to delete template: {str(e)}")