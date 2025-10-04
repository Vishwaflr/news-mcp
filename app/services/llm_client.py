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

TASK 1 - CATEGORY (select ONE main category):
- geopolitics_security (Wars, Conflicts, Crises, Diplomatic Relations, Military)
- economy_markets (Financial Markets, Crypto/Blockchain, Trade, Industry, Business)
- technology_science (Tech Innovation, AI/Automation, Research, Development, Space)
- politics_society (Domestic Politics, Elections, Democracy, Social Movements, Law)
- climate_environment_health (Climate Change, Natural Disasters, Medicine, Public Health, Environment)
- panorama (Entertainment, Sport, Culture, Lifestyle, Human Interest)

TASK 2 - SEMANTIC TAGS (exactly 3 for building article network):

1. ACTOR (Who?): Up to 4 comma-separated entities (persons, organizations, countries) that appear FREQUENTLY in news
   - Examples: "Trump", "EU, NATO", "Biden, Harris", "Israel, Hamas, Egypt"
   - USE: Well-known entities that connect different topics (max 4)
   - AVOID: Unknown persons, one-time mentions, very specific organizations
   - FORMAT: Comma-separated if multiple (e.g. "US, China" or "Biden")

2. THEME (What?): A topic cluster that spans MULTIPLE articles
   - Examples: Immigration, Trade-War, Climate-Policy, AI-Regulation, Electoral-Process
   - USE: Broad themes that recur across news
   - AVOID: Very specific one-off events without repeat potential

3. REGION (Where?): Geographic or political space that appears FREQUENTLY in news
   - Examples: Middle-East, EU, South-Asia, US-China-Relations, Africa, Ukraine
   - USE: Regions/relations that connect different actors and themes
   - AVOID: Small cities unless major local event

GOAL: Other articles should be linkable via these 3 tags to form a semantic network.

TASK 3 - SENTIMENT & IMPACT (existing analysis):

Return this exact JSON structure:
{{
  "category": "geopolitics_security|economy_markets|technology_science|politics_society|climate_environment_health|panorama",
  "semantic_tags": {{
    "actor": "string (max 100 chars)",
    "theme": "string (max 100 chars)",
    "region": "string (max 100 chars)"
  }},
  "overall": {{"label": "positive|neutral|negative", "score": -1.0 to 1.0, "confidence": 0.0 to 1.0}},
  "market": {{"bullish": 0.0 to 1.0, "bearish": 0.0 to 1.0, "uncertainty": 0.0 to 1.0, "time_horizon": "short|medium|long"}},
  "urgency": 0.0 to 1.0,
  "impact": {{"overall": 0.0 to 1.0, "volatility": 0.0 to 1.0}},
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

EXAMPLES:
Article: "Biden announces new sanctions on Russian oil exports"
→ category: "geopolitics_security"
→ actor: "Biden, US", theme: "Economic-Sanctions", region: "US-Russia-Relations"

Article: "Tesla stock surges on new AI chip announcement"
→ category: "economy_markets"
→ actor: "Tesla", theme: "AI-Technology", region: "US"

Article: "EU agrees on Gaza ceasefire resolution"
→ category: "geopolitics_security"
→ actor: "EU, Israel, Hamas", theme: "Peace-Process", region: "Middle-East"

Entity Standards:
- Countries: ISO 3166-1 Alpha-2 (US, DE, FR, CN, RU, UA, etc.)
- Blocs: EU, NATO, ASEAN, BRICS, G7, UN, OPEC
- Regions: Middle_East, Eastern_Europe, Asia_Pacific, Latin_America, Sub_Saharan_Africa
- Max 3 entries for impact_beneficiaries and impact_affected
- If news is not geopolitically relevant, set all geopolitical scores to 0.0 and arrays to []"""

    def _validate_and_normalize_result(self, result: Dict) -> Dict:
        try:
            # NEW: Validate category
            valid_categories = [
                "geopolitics_security", "economy_markets", "technology_science",
                "politics_society", "climate_environment_health", "panorama"
            ]
            category = result.get("category", "panorama")
            if category not in valid_categories:
                logger.warning(f"Invalid category '{category}', using 'panorama'")
                category = "panorama"

            # NEW: Validate semantic tags
            semantic_tags = result.get("semantic_tags", {})
            actor = str(semantic_tags.get("actor", "Unknown")).strip()
            theme = str(semantic_tags.get("theme", "General")).strip()[:100]
            region = str(semantic_tags.get("region", "Global")).strip()[:100]

            # Validate actor count (max 4)
            if ',' in actor:
                actors = [a.strip() for a in actor.split(',')]
                if len(actors) > 4:
                    logger.warning(f"Too many actors ({len(actors)}), limiting to 4")
                    actor = ', '.join(actors[:4])

            # Ensure max length
            if len(actor) > 250:
                actor = actor[:250]

            # Ensure not empty
            if not actor or actor == "":
                actor = "Unknown"
            if not theme or theme == "":
                theme = "General"
            if not region or region == "":
                region = "Global"

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

            # Validate geopolitical fields (optional, backward compatible)
            geopolitical = self._validate_geopolitical(result.get("geopolitical", {}))

            return {
                "category": category,  # NEW
                "semantic_tags": {  # NEW
                    "actor": actor,
                    "theme": theme,
                    "region": region
                },
                "overall": overall,
                "market": market,
                "urgency": urgency,
                "impact": impact,
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
            "category": "panorama",  # NEW
            "semantic_tags": {  # NEW
                "actor": "Unknown",
                "theme": "General",
                "region": "Global"
            },
            "overall": {"label": "neutral", "score": 0.0, "confidence": 0.0},
            "market": {"bullish": 0.5, "bearish": 0.5, "uncertainty": 0.5, "time_horizon": "medium"},
            "urgency": 0.0,
            "impact": {"overall": 0.0, "volatility": 0.0},
            "geopolitical": self._get_empty_geopolitical()
        }