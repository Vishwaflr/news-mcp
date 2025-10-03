"""
Template Management Routes

Web interface for managing dynamic feed templates.
"""
from fastapi import APIRouter, Request, Form, HTTPException, Depends
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from typing import Optional, List
from sqlmodel import Session, select, text
import json

from ..database import get_session
from ..models import DynamicFeedTemplate, Feed, FeedTemplateAssignment
from ..services.dynamic_template_manager import get_dynamic_template_manager
from ..services.feed_change_tracker import FeedChangeTracker

router = APIRouter()
templates = Jinja2Templates(directory="templates")

@router.get("/admin/templates", response_class=HTMLResponse)
async def templates_page(request: Request):
    """Template management page"""
    return templates.TemplateResponse("admin/templates.html", {"request": request})

@router.get("/htmx/templates-list", response_class=HTMLResponse)
async def templates_list(request: Request, session: Session = Depends(get_session)):
    """Get list of all templates with their assignments"""

    # Get all templates using raw SQL to avoid SQLModel issues
    templates_result = session.execute(
        text("""
        SELECT id, name, description, version, url_patterns, field_mappings,
               content_processing_rules, quality_filters, categorization_rules,
               fetch_settings, is_active, is_builtin, created_by, created_at, updated_at
        FROM dynamic_feed_templates
        ORDER BY created_at DESC
        """)
    ).fetchall()

    # Get all feeds for assignment dropdown
    feeds_result = session.execute(
        text("SELECT id, title, url FROM feeds ORDER BY title")
    ).fetchall()

    all_feeds = [{"id": f[0], "title": f[1], "url": f[2]} for f in feeds_result]

    # Enrich templates with assignment info
    enriched_templates = []
    for template_row in templates_result:
        # Get assignments for this template
        assignments_result = session.execute(
            text("""
            SELECT fta.id, fta.feed_id, fta.template_id, fta.is_active,
                   fta.assigned_by, fta.created_at as assigned_at, fta.priority,
                   f.title, f.url
            FROM feed_template_assignments fta
            JOIN feeds f ON f.id = fta.feed_id
            WHERE fta.template_id = :template_id AND fta.is_active = true
            """),
            {"template_id": template_row[0]}
        ).fetchall()

        # Parse JSON fields
        try:
            url_patterns = json.loads(template_row[4]) if template_row[4] else []
        except (json.JSONDecodeError, TypeError) as e:
            logger.debug(f"Error parsing url_patterns for template {template_row[0]}: {e}")
            url_patterns = []

        # Create a dict with template data plus assignment info
        template_dict = {
            'id': template_row[0],
            'name': template_row[1],
            'description': template_row[2],
            'url_patterns': url_patterns,
            'is_active': template_row[10],
            'is_builtin': template_row[11],
            'created_at': template_row[13],
            'assignments': [],
            'assigned_feed_ids': []
        }

        for assignment in assignments_result:
            assignment_dict = {
                'id': assignment[0],
                'feed_id': assignment[1],
                'template_id': assignment[2],
                'is_active': assignment[3],
                'assigned_by': assignment[4],
                'assigned_at': assignment[5],
                'priority': assignment[6],
                'feed': {
                    'id': assignment[1],
                    'title': assignment[7],
                    'url': assignment[8]
                }
            }
            template_dict['assignments'].append(assignment_dict)
            template_dict['assigned_feed_ids'].append(assignment[1])

        enriched_templates.append(template_dict)

    return templates.TemplateResponse("htmx/templates_list.html", {
        "request": request,
        "templates": enriched_templates,
        "all_feeds": all_feeds
    })

@router.post("/htmx/templates", response_class=HTMLResponse)
async def create_template(
    request: Request,
    name: str = Form(...),
    description: Optional[str] = Form(None),
    url_patterns: Optional[str] = Form(None),
    field_mapping_title: Optional[str] = Form("entry.title"),
    field_mapping_description: Optional[str] = Form("entry.summary"),
    field_mapping_link: Optional[str] = Form("entry.link"),
    field_mapping_author: Optional[str] = Form("entry.author"),
    content_rule_html_extract: Optional[bool] = Form(False),
    content_rule_normalize_text: Optional[bool] = Form(False),
    content_rule_remove_tracking: Optional[bool] = Form(False),
    min_title_length: Optional[int] = Form(5),
    max_title_length: Optional[int] = Form(200),
    session: Session = Depends(get_session)
):
    """Create a new template"""

    try:
        # Parse URL patterns
        patterns = [p.strip() for p in url_patterns.split('\n') if p.strip()] if url_patterns else []

        # Build field mappings
        field_mappings = {
            'title': field_mapping_title,
            'description': field_mapping_description,
            'link': field_mapping_link,
            'author': field_mapping_author,
            'published': 'entry.published_parsed',
            'guid': 'entry.id'
        }

        # Build content processing rules
        content_rules = []
        if content_rule_html_extract:
            content_rules.append({'type': 'html_extract', 'max_length': 2000})
        if content_rule_normalize_text:
            content_rules.append({'type': 'text_normalize', 'rules': ['fix_german_umlauts', 'normalize_quotes']})
        if content_rule_remove_tracking:
            content_rules.append({'type': 'remove_tracking'})

        # Build quality filters
        quality_filters = {
            'min_title_length': min_title_length,
            'max_title_length': max_title_length
        }

        # Create template using the manager
        with get_dynamic_template_manager(session) as manager:
            template = manager.create_template(
                name=name,
                description=description,
                url_patterns=patterns,
                field_mappings=field_mappings,
                content_processing_rules=content_rules,
                quality_filters=quality_filters,
                created_by='web_ui'
            )

        # Return updated templates list
        return await templates_list(request, session)

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.put("/htmx/templates/{template_id}", response_class=HTMLResponse)
async def update_template(
    template_id: int,
    request: Request,
    name: str = Form(...),
    description: Optional[str] = Form(None),
    url_patterns: Optional[str] = Form(None),
    field_mapping_title: Optional[str] = Form("entry.title"),
    field_mapping_description: Optional[str] = Form("entry.summary"),
    field_mapping_link: Optional[str] = Form("entry.link"),
    field_mapping_author: Optional[str] = Form("entry.author"),
    content_rule_html_extract: Optional[bool] = Form(False),
    content_rule_normalize_text: Optional[bool] = Form(False),
    content_rule_remove_tracking: Optional[bool] = Form(False),
    min_title_length: Optional[int] = Form(5),
    max_title_length: Optional[int] = Form(200),
    session: Session = Depends(get_session)
):
    """Update an existing template"""

    try:
        # Parse URL patterns
        patterns = [p.strip() for p in url_patterns.split('\n') if p.strip()] if url_patterns else []

        # Build field mappings
        field_mappings = {
            'title': field_mapping_title,
            'description': field_mapping_description,
            'link': field_mapping_link,
            'author': field_mapping_author,
            'published': 'entry.published_parsed',
            'guid': 'entry.id'
        }

        # Build content processing rules
        content_rules = []
        if content_rule_html_extract:
            content_rules.append({'type': 'html_extract', 'max_length': 2000})
        if content_rule_normalize_text:
            content_rules.append({'type': 'text_normalize', 'rules': ['fix_german_umlauts', 'normalize_quotes']})
        if content_rule_remove_tracking:
            content_rules.append({'type': 'remove_tracking'})

        # Build quality filters
        quality_filters = {
            'min_title_length': min_title_length,
            'max_title_length': max_title_length
        }

        # Update template using the manager
        with get_dynamic_template_manager(session) as manager:
            template = manager.update_template(
                template_id,
                name=name,
                description=description,
                url_patterns=patterns,
                field_mappings=field_mappings,
                content_processing_rules=content_rules,
                quality_filters=quality_filters,
                updated_by='web_ui'
            )

        if not template:
            raise HTTPException(status_code=404, detail="Template not found")

        # Return updated templates list
        return await templates_list(request, session)

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/htmx/templates/{template_id}")
async def delete_template(template_id: int, session: Session = Depends(get_session)):
    """Delete a template"""

    try:
        with get_dynamic_template_manager(session) as manager:
            success = manager.delete_template(template_id)

        if not success:
            raise HTTPException(status_code=404, detail="Template not found")

        return {"success": True, "message": "Template deleted successfully"}

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/htmx/template-details/{template_id}")
async def get_template_details(template_id: int, session: Session = Depends(get_session)):
    """Get template details for editing"""

    template = session.get(DynamicFeedTemplate, template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    return {
        "id": template.id,
        "name": template.name,
        "description": template.description,
        "url_patterns": template.url_pattern_list,
        "field_mappings": template.field_mapping_dict,
        "content_processing_rules": template.content_rules_list,
        "quality_filters": {
            "min_title_length": 5,
            "max_title_length": 200,
            **template.field_mapping_dict.get('quality_filters', {})
        }
    }

@router.post("/htmx/feeds/{feed_id}/template/{template_id}")
async def assign_template_to_feed(
    feed_id: int,
    template_id: int,
    session: Session = Depends(get_session)
):
    """Assign a template to a feed"""

    try:
        with get_dynamic_template_manager(session) as manager:
            assignment = manager.assign_template_to_feed(
                feed_id, template_id, assigned_by='web_ui'
            )

        return {"success": True, "message": "Template assigned successfully"}

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/htmx/feeds/{feed_id}/template/{template_id}")
async def unassign_template_from_feed(
    feed_id: int,
    template_id: int,
    session: Session = Depends(get_session)
):
    """Unassign a template from a feed"""

    try:
        with get_dynamic_template_manager(session) as manager:
            success = manager.unassign_template_from_feed(feed_id, template_id)

        if not success:
            raise HTTPException(status_code=404, detail="Template assignment not found")

        return {"success": True, "message": "Template unassigned successfully"}

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/htmx/templates/auto-assign")
async def auto_assign_templates(session: Session = Depends(get_session)):
    """Auto-assign templates to feeds based on URL patterns"""

    try:
        with get_dynamic_template_manager(session) as manager:
            assignments_made = manager.auto_assign_templates_to_feeds()

        return {
            "success": True,
            "message": f"Made {assignments_made} automatic template assignments"
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))