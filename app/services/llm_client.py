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
        return f"""You are a precise financial news classifier. Return STRICT JSON only.

Title: {title}
Summary: {summary}

Return this exact JSON structure:
{{
  "overall": {{"label": "positive|neutral|negative", "score": -1.0 to 1.0, "confidence": 0.0 to 1.0}},
  "market": {{"bullish": 0.0 to 1.0, "bearish": 0.0 to 1.0, "uncertainty": 0.0 to 1.0, "time_horizon": "short|medium|long"}},
  "urgency": 0.0 to 1.0,
  "impact": {{"overall": 0.0 to 1.0, "volatility": 0.0 to 1.0}},
  "themes": ["max", "6", "strings"]
}}"""

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

            return {
                "overall": overall,
                "market": market,
                "urgency": urgency,
                "impact": impact,
                "themes": themes
            }

        except Exception as e:
            logger.error(f"Result validation error: {e}")
            return self._get_fallback_result()

    def _get_fallback_result(self) -> Dict:
        return {
            "overall": {"label": "neutral", "score": 0.0, "confidence": 0.0},
            "market": {"bullish": 0.5, "bearish": 0.5, "uncertainty": 0.5, "time_horizon": "medium"},
            "urgency": 0.0,
            "impact": {"overall": 0.0, "volatility": 0.0},
            "themes": []
        }