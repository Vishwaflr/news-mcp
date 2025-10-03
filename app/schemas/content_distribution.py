"""
Pydantic schemas for Content Distribution (Special Reports).
Temporary compatibility layer - full migration in progress.
"""

from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime
from decimal import Decimal

# For now, use aliases pointing to the model classes
# Full Pydantic schema definitions will be added in next phase

class SpecialReportCreate(BaseModel):
    name: str
    description: Optional[str] = None
    target_audience: Optional[str] = None
    selection_criteria: Dict[str, Any]
    content_structure: Dict[str, Any]
    llm_prompt_template: str
    llm_model: str = "gpt-4o-mini"
    llm_temperature: Decimal = Decimal("0.7")
    system_instruction: Optional[str] = None
    output_format: str = "markdown"
    output_constraints: Optional[Dict[str, Any]] = None
    generation_schedule: Optional[str] = None
    is_active: bool = True
    tags: Optional[Dict[str, Any]] = None

class SpecialReportUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
    # Add other fields as needed

class SpecialReportPreview(BaseModel):
    special_report_id: int
    matching_articles_count: int
    sample_article_ids: List[int]
    estimated_cost_usd: float
    estimated_time_seconds: int
    articles_summary: List[Dict[str, Any]]

class ContentGenerationRequest(BaseModel):
    async_mode: bool = True

class ContentGenerationResponse(BaseModel):
    success: bool
    job_id: Optional[str] = None
    status: str
    message: str

# Backward compatibility aliases
ContentTemplateCreate = SpecialReportCreate
ContentTemplateUpdate = SpecialReportUpdate
ContentTemplatePreview = SpecialReportPreview

# Import model for schema
from app.models.content_distribution import SpecialReport
ContentTemplate = SpecialReport
