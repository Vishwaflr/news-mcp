#!/usr/bin/env python3
"""
Quick LLM Model Test - Testet nur die wichtigsten Modelle
"""

import json
import time
import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# Test mit dem neuen Standard-Modell
QUICK_TEST_MODELS = [
    "gpt-4.1-nano",    # ✅ Neuer Standard
]

# Ein Test-Artikel
TEST_ARTICLE = {
    "title": "Tesla Stock Surges 15% After Strong Q4 Delivery Numbers Beat Expectations",
    "summary": "Tesla delivered 484,507 vehicles in Q4 2024, exceeding analyst expectations of 470,000. The strong delivery numbers pushed Tesla stock up 15% in after-hours trading."
}

def build_prompt(title: str, summary: str) -> str:
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

def test_model(client, model: str) -> dict:
    prompt = build_prompt(TEST_ARTICLE["title"], TEST_ARTICLE["summary"])

    try:
        params = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "timeout": 10,
            "response_format": {"type": "json_object"}
        }

        if model.startswith(('gpt-5', 'o3', 'o4')):
            params["max_completion_tokens"] = 500
        else:
            params["max_tokens"] = 500
            params["temperature"] = 0.1

        start_time = time.time()
        response = client.chat.completions.create(**params)
        end_time = time.time()

        raw_response = response.choices[0].message.content

        try:
            parsed_json = json.loads(raw_response)
            json_valid = True
            json_error = None
        except json.JSONDecodeError as e:
            parsed_json = None
            json_valid = False
            json_error = str(e)

        return {
            "success": True,
            "response_time": round(end_time - start_time, 2),
            "raw_response": raw_response,
            "json_valid": json_valid,
            "json_error": json_error,
            "parsed_json": parsed_json,
            "tokens": response.usage.total_tokens if response.usage else 0
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        }

def main():
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("❌ OPENAI_API_KEY not found")
        return

    client = OpenAI(api_key=api_key)

    print("🧪 Quick LLM Model Test")
    print("=" * 50)
    print(f"📰 Test Article: {TEST_ARTICLE['title'][:50]}...")
    print("=" * 50)

    for model in QUICK_TEST_MODELS:
        print(f"\n🔍 Testing {model}...")

        result = test_model(client, model)

        if result["success"]:
            if result["json_valid"]:
                print(f"   ✅ SUCCESS: Valid JSON ({result['response_time']}s, {result['tokens']} tokens)")

                # Zeige ein paar Key-Werte
                data = result["parsed_json"]
                if "overall" in data and "label" in data["overall"]:
                    label = data["overall"]["label"]
                    score = data["overall"].get("score", 0)
                    print(f"   📊 Analysis: {label} (score: {score})")

                # Prüfe ob alle required keys da sind
                required = ["overall", "market", "urgency", "impact", "themes"]
                missing = [k for k in required if k not in data]
                if missing:
                    print(f"   ⚠️  Missing keys: {missing}")
                else:
                    print(f"   ✅ All required keys present")

            else:
                print(f"   ❌ JSON PARSE ERROR: {result['json_error']}")
                print(f"   📝 Raw response: {result['raw_response'][:100]}...")
        else:
            print(f"   ❌ API ERROR: {result['error']}")

    print("\n" + "=" * 50)

if __name__ == "__main__":
    main()