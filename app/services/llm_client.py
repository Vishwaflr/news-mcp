import json
import time
import os
from typing import Dict, Optional
from openai import OpenAI
from app.core.logging_config import get_logger

logger = get_logger(__name__)

class LLMClient:
    def __init__(self, model: str = "gpt-4.1-nano", rate_per_sec: float = 1.0, timeout: int = 8):
        self.model = model
        self.delay = 1.0 / max(rate_per_sec, 0.1)
        self.timeout = timeout

        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")

        self.client = OpenAI(api_key=api_key)

    def classify(self, title: str, summary: str) -> Dict:
        prompt = self._build_prompt(title, summary[:800])

        try:
            time.sleep(self.delay)

            # Build parameters based on model capabilities
            params = {
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "timeout": self.timeout,
                "response_format": {"type": "json_object"}
            }

            # Modern models (gpt-5, o3, o4) have different parameter requirements
            if self.model.startswith(('gpt-5', 'o3', 'o4')):
                params["max_completion_tokens"] = 500
                # These models don't support custom temperature, only default (1.0)
            else:
                params["max_tokens"] = 500
                params["temperature"] = 0.1

            response = self.client.chat.completions.create(**params)

            raw_response = response.choices[0].message.content
            result = json.loads(raw_response)

            return self._validate_and_normalize_result(result)

        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error for '{title[:50]}...': {e}")
            return self._get_fallback_result()
        except Exception as e:
            logger.error(f"LLM classification error for '{title[:50]}...': {e}")
            return self._get_fallback_result()

    def _build_prompt(self, title: str, summary: str) -> str:
        return f"""You are a precise financial and geopolitical news classifier. Return STRICT JSON only.

Title: {title}
Summary: {summary}

Return this exact JSON structure:
{{
  "overall": {{"label": "positive|neutral|negative", "score": -1.0 to 1.0, "confidence": 0.0 to 1.0}},
  "market": {{"bullish": 0.0 to 1.0, "bearish": 0.0 to 1.0, "uncertainty": 0.0 to 1.0, "time_horizon": "short|medium|long"}},
  "urgency": 0.0 to 1.0,
  "impact": {{"overall": 0.0 to 1.0, "volatility": 0.0 to 1.0}},
  "themes": ["max", "6", "strings"],
  "geopolitical": {{
    "stability_score": -1.0 to 1.0,
    "economic_impact": -1.0 to 1.0,
    "security_relevance": 0.0 to 1.0,
    "diplomatic_impact": {{
      "global": -1.0 to 1.0,
      "western": -1.0 to 1.0,
      "regional": -1.0 to 1.0
    }},
    "impact_beneficiaries": ["max 3 ISO3166/Blocs"],
    "impact_affected": ["max 3 ISO3166/Blocs"],
    "regions_affected": ["regions"],
    "time_horizon": "immediate|short_term|long_term",
    "confidence": 0.0 to 1.0,
    "escalation_potential": 0.0 to 1.0,
    "alliance_activation": ["alliances/treaties"],
    "conflict_type": "diplomatic|economic|hybrid|interstate_war|nuclear_threat"
  }}
}}

Entity Standards:
- Countries: ISO 3166-1 Alpha-2 (US, DE, FR, CN, RU, UA, etc.)
- Blocs: EU, NATO, ASEAN, BRICS, G7, UN, OPEC
- Regions: Middle_East, Eastern_Europe, Asia_Pacific, Latin_America, Sub_Saharan_Africa
- Markets: Energy_Markets, Financial_Markets, Global_Trade, Commodity_Markets
- Max 3 entries for impact_beneficiaries and impact_affected
- If news is not geopolitically relevant, set all geopolitical scores to 0.0 and arrays to []"""

    def _validate_and_normalize_result(self, result: Dict) -> Dict:
        try:
            # Ensure required keys exist with fallbacks
            overall = result.get("overall", {})
            if "label" not in overall:
                overall["label"] = "neutral"
            if "score" not in overall:
                overall["score"] = 0.0
            if "confidence" not in overall:
                overall["confidence"] = 0.0

            market = result.get("market", {})
            if "bullish" not in market:
                market["bullish"] = 0.5
            if "bearish" not in market:
                market["bearish"] = 0.5
            if "uncertainty" not in market:
                market["uncertainty"] = 0.5
            if "time_horizon" not in market:
                market["time_horizon"] = "medium"

            impact = result.get("impact", {})
            if "overall" not in impact:
                impact["overall"] = 0.0
            if "volatility" not in impact:
                impact["volatility"] = 0.0

            # Normalize and constrain values
            overall["score"] = max(-1.0, min(1.0, float(overall["score"])))
            overall["confidence"] = max(0.0, min(1.0, float(overall["confidence"])))

            market["bullish"] = max(0.0, min(1.0, float(market["bullish"])))
            market["bearish"] = max(0.0, min(1.0, float(market["bearish"])))
            market["uncertainty"] = max(0.0, min(1.0, float(market["uncertainty"])))

            if market["time_horizon"] not in ["short", "medium", "long"]:
                market["time_horizon"] = "medium"

            impact["overall"] = max(0.0, min(1.0, float(impact["overall"])))
            impact["volatility"] = max(0.0, min(1.0, float(impact["volatility"])))

            urgency = max(0.0, min(1.0, float(result.get("urgency", 0.0))))

            themes = result.get("themes", [])
            if not isinstance(themes, list):
                themes = []
            themes = [str(theme) for theme in themes[:6]]

            # Validate geopolitical fields (optional, backward compatible)
            geopolitical = self._validate_geopolitical(result.get("geopolitical", {}))

            return {
                "overall": overall,
                "market": market,
                "urgency": urgency,
                "impact": impact,
                "themes": themes,
                "geopolitical": geopolitical
            }

        except Exception as e:
            logger.error(f"Result validation error: {e}")
            return self._get_fallback_result()

    def _validate_geopolitical(self, geo: Dict) -> Dict:
        """Validate and normalize geopolitical analysis fields"""
        try:
            # Return empty if no geopolitical data
            if not geo:
                return self._get_empty_geopolitical()

            # Validate scores
            stability_score = max(-1.0, min(1.0, float(geo.get("stability_score", 0.0))))
            economic_impact = max(-1.0, min(1.0, float(geo.get("economic_impact", 0.0))))
            security_relevance = max(0.0, min(1.0, float(geo.get("security_relevance", 0.0))))

            # Validate diplomatic impact
            diplomatic = geo.get("diplomatic_impact", {})
            diplomatic_impact = {
                "global": max(-1.0, min(1.0, float(diplomatic.get("global", 0.0)))),
                "western": max(-1.0, min(1.0, float(diplomatic.get("western", 0.0)))),
                "regional": max(-1.0, min(1.0, float(diplomatic.get("regional", 0.0))))
            }

            # Validate entity arrays (max 3 items)
            impact_beneficiaries = self._validate_entities(geo.get("impact_beneficiaries", []))
            impact_affected = self._validate_entities(geo.get("impact_affected", []))

            # Validate regions array
            regions_affected = geo.get("regions_affected", [])
            if not isinstance(regions_affected, list):
                regions_affected = []
            regions_affected = [str(r) for r in regions_affected]

            # Validate time horizon enum
            time_horizon = geo.get("time_horizon", "short_term")
            if time_horizon not in ["immediate", "short_term", "long_term"]:
                time_horizon = "short_term"

            # Validate confidence and escalation
            confidence = max(0.0, min(1.0, float(geo.get("confidence", 0.0))))
            escalation_potential = max(0.0, min(1.0, float(geo.get("escalation_potential", 0.0))))

            # Validate alliance activation array
            alliance_activation = geo.get("alliance_activation", [])
            if not isinstance(alliance_activation, list):
                alliance_activation = []
            alliance_activation = [str(a) for a in alliance_activation]

            # Validate conflict type enum
            conflict_type = geo.get("conflict_type", "diplomatic")
            valid_types = ["diplomatic", "economic", "hybrid", "interstate_war", "nuclear_threat"]
            if conflict_type not in valid_types:
                conflict_type = "diplomatic"

            return {
                "stability_score": stability_score,
                "economic_impact": economic_impact,
                "security_relevance": security_relevance,
                "diplomatic_impact": diplomatic_impact,
                "impact_beneficiaries": impact_beneficiaries,
                "impact_affected": impact_affected,
                "regions_affected": regions_affected,
                "time_horizon": time_horizon,
                "confidence": confidence,
                "escalation_potential": escalation_potential,
                "alliance_activation": alliance_activation,
                "conflict_type": conflict_type
            }

        except Exception as e:
            logger.error(f"Geopolitical validation error: {e}")
            return self._get_empty_geopolitical()

    def _validate_entities(self, entities: list) -> list:
        """Validate entity array (max 3 items, strings only)"""
        if not isinstance(entities, list):
            return []
        # Limit to 3 items and convert to strings
        return [str(e).strip() for e in entities[:3] if e]

    def _get_empty_geopolitical(self) -> Dict:
        """Return empty geopolitical structure for non-geopolitical news"""
        return {
            "stability_score": 0.0,
            "economic_impact": 0.0,
            "security_relevance": 0.0,
            "diplomatic_impact": {"global": 0.0, "western": 0.0, "regional": 0.0},
            "impact_beneficiaries": [],
            "impact_affected": [],
            "regions_affected": [],
            "time_horizon": "short_term",
            "confidence": 0.0,
            "escalation_potential": 0.0,
            "alliance_activation": [],
            "conflict_type": "diplomatic"
        }

    def _get_fallback_result(self) -> Dict:
        return {
            "overall": {"label": "neutral", "score": 0.0, "confidence": 0.0},
            "market": {"bullish": 0.5, "bearish": 0.5, "uncertainty": 0.5, "time_horizon": "medium"},
            "urgency": 0.0,
            "impact": {"overall": 0.0, "volatility": 0.0},
            "themes": [],
            "geopolitical": self._get_empty_geopolitical()
        }