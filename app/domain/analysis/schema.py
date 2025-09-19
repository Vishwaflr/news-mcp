from pydantic import BaseModel, Field, validator
from typing import Literal, List, Optional

Label = Literal["positive", "neutral", "negative"]
Horizon = Literal["short", "medium", "long"]

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

class AnalysisResult(BaseModel):
    sentiment: SentimentPayload
    impact: ImpactPayload
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