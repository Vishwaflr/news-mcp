from pydantic import BaseModel, Field, validator
from typing import Literal, List, Optional

Label = Literal["positive", "neutral", "negative"]
Horizon = Literal["short", "medium", "long"]

# Geopolitical analysis types
ConflictType = Literal["diplomatic", "economic", "hybrid", "interstate_war", "nuclear_threat"]
GeoTimeHorizon = Literal["immediate", "short_term", "long_term"]

# NEW: Category types
CategoryType = Literal[
    "geopolitics_security",
    "economy_markets",
    "technology_science",
    "politics_society",
    "climate_environment_health",
    "panorama"
]

class Overall(BaseModel):
    label: Label
    score: float = Field(..., ge=-1.0, le=1.0)
    confidence: float = Field(..., ge=0.0, le=1.0)

class Market(BaseModel):
    bullish: float = Field(..., ge=0.0, le=1.0)
    bearish: float = Field(..., ge=0.0, le=1.0)
    uncertainty: float = Field(..., ge=0.0, le=1.0)
    time_horizon: Horizon

# NEW: Semantic Tags for network
class SemanticTags(BaseModel):
    """Semantic tags for building article network"""
    actor: str = Field(..., min_length=1, max_length=250, description="Up to 4 comma-separated actors (persons, organizations, countries)")
    theme: str = Field(..., min_length=1, max_length=100, description="Topic cluster")
    region: str = Field(..., min_length=1, max_length=100, description="Geographic or political space")

    @validator('actor')
    def validate_max_actors(cls, v):
        """Ensure maximum 4 actors"""
        if ',' in v:
            actors = [a.strip() for a in v.split(',')]
            if len(actors) > 4:
                # Keep only first 4
                return ', '.join(actors[:4])
        return v

class SentimentPayload(BaseModel):
    overall: Overall
    market: Market
    urgency: float = Field(..., ge=0.0, le=1.0)

class ImpactPayload(BaseModel):
    overall: float = Field(..., ge=0.0, le=1.0)
    volatility: float = Field(..., ge=0.0, le=1.0)

class DiplomaticImpact(BaseModel):
    """Diplomatic impact from different perspectives"""
    global_impact: float = Field(..., ge=-1.0, le=1.0, alias="global")
    western: float = Field(..., ge=-1.0, le=1.0)
    regional: float = Field(..., ge=-1.0, le=1.0)

    class Config:
        populate_by_name = True  # Allow both 'global' and 'global_impact'

class GeopoliticalPayload(BaseModel):
    """Geopolitical analysis dimensions"""
    stability_score: float = Field(..., ge=-1.0, le=1.0)
    economic_impact: float = Field(..., ge=-1.0, le=1.0)
    security_relevance: float = Field(..., ge=0.0, le=1.0)

    diplomatic_impact: DiplomaticImpact

    impact_beneficiaries: List[str] = Field(default_factory=list, max_items=3)
    impact_affected: List[str] = Field(default_factory=list, max_items=3)

    regions_affected: List[str] = Field(default_factory=list)
    time_horizon: GeoTimeHorizon
    confidence: float = Field(..., ge=0.0, le=1.0)
    escalation_potential: float = Field(..., ge=0.0, le=1.0)
    alliance_activation: List[str] = Field(default_factory=list)
    conflict_type: ConflictType

    @validator('impact_beneficiaries', 'impact_affected')
    def validate_max_three_entities(cls, v):
        """Ensure maximum 3 entities"""
        if len(v) > 3:
            return v[:3]
        return v

class AnalysisResult(BaseModel):
    category: CategoryType  # NEW
    semantic_tags: SemanticTags  # NEW
    sentiment: SentimentPayload
    impact: ImpactPayload
    geopolitical: Optional[GeopoliticalPayload] = None  # Optional for backward compatibility
    model_tag: str

class AnalysisRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    summary: str = Field(..., max_length=1200)

class AnalysisResponse(BaseModel):
    item_id: int
    analysis: AnalysisResult
    created_at: str
    updated_at: str