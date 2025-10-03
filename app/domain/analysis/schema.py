from pydantic import BaseModel, Field, validator
from typing import Literal, List, Optional

Label = Literal["positive", "neutral", "negative"]
Horizon = Literal["short", "medium", "long"]

# Geopolitical analysis types
ConflictType = Literal["diplomatic", "economic", "hybrid", "interstate_war", "nuclear_threat"]
GeoTimeHorizon = Literal["immediate", "short_term", "long_term"]

class Overall(BaseModel):
    label: Label
    score: float = Field(..., ge=-1.0, le=1.0)
    confidence: float = Field(..., ge=0.0, le=1.0)

class Market(BaseModel):
    bullish: float = Field(..., ge=0.0, le=1.0)
    bearish: float = Field(..., ge=0.0, le=1.0)
    uncertainty: float = Field(..., ge=0.0, le=1.0)
    time_horizon: Horizon

class SentimentPayload(BaseModel):
    overall: Overall
    market: Market
    urgency: float = Field(..., ge=0.0, le=1.0)
    themes: List[str] = Field(default_factory=list, max_items=6)

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
    sentiment: SentimentPayload
    impact: ImpactPayload
    geopolitical: Optional[GeopoliticalPayload] = None  # Optional for backward compatibility
    model_tag: str

    @validator('sentiment')
    def validate_sentiment_themes(cls, v):
        if len(v.themes) > 6:
            v.themes = v.themes[:6]
        return v

class AnalysisRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    summary: str = Field(..., max_length=1200)

class AnalysisResponse(BaseModel):
    item_id: int
    analysis: AnalysisResult
    created_at: str
    updated_at: str