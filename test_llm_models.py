#!/usr/bin/env python3
"""
LLM Model Testing Script

Tests verschiedene OpenAI-Modelle mit unserem News-Analyse-Prompt
um zu überprüfen, welche Modelle geeignete JSON-Ausgaben liefern.
"""

import json
import time
import os
from openai import OpenAI
from typing import Dict, List
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Verfügbare Modelle zum Testen
TEST_MODELS = [
    "gpt-4o-mini",
    "gpt-4.1-nano",
    "gpt-5-mini",
    "gpt-4.1-mini",
    "o4-mini",
    "gpt-5",
    "o3",
    "gpt-4.1",
    "gpt-4o",
    "gpt-4o-2024-05-13"
]

# Test-Artikel für konsistente Tests
TEST_ARTICLES = [
    {
        "title": "Tesla Stock Surges 15% After Strong Q4 Delivery Numbers Beat Expectations",
        "summary": "Tesla delivered 484,507 vehicles in Q4 2024, exceeding analyst expectations of 470,000. The strong delivery numbers pushed Tesla stock up 15% in after-hours trading as investors showed renewed confidence in the electric vehicle maker's growth trajectory."
    },
    {
        "title": "Federal Reserve Holds Interest Rates Steady, Signals Potential Cut Next Quarter",
        "summary": "The Federal Reserve kept interest rates unchanged at 5.25-5.50% following their two-day meeting. Fed Chair Powell indicated that economic data supports a potential rate cut in the next quarter if inflation continues its downward trend."
    },
    {
        "title": "Microsoft Announces $50 Billion Share Buyback Program",
        "summary": "Microsoft unveiled a massive $50 billion share buyback program and raised its quarterly dividend by 10%. The tech giant reported strong cloud revenue growth of 28% year-over-year, driving optimism about its AI and cloud computing strategy."
    }
]

class LLMModelTester:
    def __init__(self):
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")

        self.client = OpenAI(api_key=api_key)
        self.results = {}

    def build_prompt(self, title: str, summary: str) -> str:
        """Unser Standard-Analyse-Prompt"""
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

    def test_model(self, model: str, article: Dict, timeout: int = 10) -> Dict:
        """Teste ein einzelnes Modell mit einem Artikel"""
        prompt = self.build_prompt(article["title"], article["summary"])

        try:
            # Model-spezifische Parameter
            params = {
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "timeout": timeout,
                "response_format": {"type": "json_object"}
            }

            # Parameter je nach Modell anpassen
            if model.startswith(('gpt-5', 'o3', 'o4')):
                params["max_completion_tokens"] = 500
                # Kein temperature für moderne Modelle
            else:
                params["max_tokens"] = 500
                params["temperature"] = 0.1

            start_time = time.time()
            response = self.client.chat.completions.create(**params)
            end_time = time.time()

            raw_response = response.choices[0].message.content

            # JSON parsen
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
                "tokens_used": response.usage.total_tokens if response.usage else None
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__
            }

    def validate_json_structure(self, parsed_json: Dict) -> Dict:
        """Validiere die JSON-Struktur gegen unser erwartetes Schema"""
        if not parsed_json:
            return {"valid": False, "errors": ["No JSON data"]}

        errors = []

        # Prüfe required keys
        required_keys = ["overall", "market", "urgency", "impact", "themes"]
        for key in required_keys:
            if key not in parsed_json:
                errors.append(f"Missing key: {key}")

        # Prüfe overall structure
        if "overall" in parsed_json:
            overall = parsed_json["overall"]
            if not isinstance(overall, dict):
                errors.append("overall must be object")
            else:
                for subkey in ["label", "score", "confidence"]:
                    if subkey not in overall:
                        errors.append(f"Missing overall.{subkey}")

        # Prüfe market structure
        if "market" in parsed_json:
            market = parsed_json["market"]
            if not isinstance(market, dict):
                errors.append("market must be object")
            else:
                for subkey in ["bullish", "bearish", "uncertainty", "time_horizon"]:
                    if subkey not in market:
                        errors.append(f"Missing market.{subkey}")

        # Prüfe themes
        if "themes" in parsed_json:
            themes = parsed_json["themes"]
            if not isinstance(themes, list):
                errors.append("themes must be array")
            elif len(themes) > 6:
                errors.append("themes array too long (max 6)")

        return {
            "valid": len(errors) == 0,
            "errors": errors
        }

    def run_comprehensive_test(self):
        """Führe umfassende Tests für alle Modelle durch"""
        print("🧪 LLM Model Testing Started")
        print("=" * 60)

        for model in TEST_MODELS:
            print(f"\n📋 Testing Model: {model}")
            print("-" * 40)

            model_results = {
                "model": model,
                "articles": {},
                "summary": {
                    "total_tests": 0,
                    "successful_calls": 0,
                    "valid_json": 0,
                    "valid_structure": 0,
                    "avg_response_time": 0,
                    "total_tokens": 0
                }
            }

            total_time = 0
            total_tokens = 0

            for i, article in enumerate(TEST_ARTICLES):
                article_key = f"article_{i+1}"
                print(f"  📰 Testing with article {i+1}: {article['title'][:50]}...")

                result = self.test_model(model, article)
                model_results["articles"][article_key] = result
                model_results["summary"]["total_tests"] += 1

                if result["success"]:
                    model_results["summary"]["successful_calls"] += 1
                    total_time += result["response_time"]

                    if result["tokens_used"]:
                        total_tokens += result["tokens_used"]

                    if result["json_valid"]:
                        model_results["summary"]["valid_json"] += 1

                        # Struktur-Validierung
                        validation = self.validate_json_structure(result["parsed_json"])
                        if validation["valid"]:
                            model_results["summary"]["valid_structure"] += 1
                            print(f"    ✅ Success: Valid JSON & Structure ({result['response_time']}s)")
                        else:
                            print(f"    ⚠️  JSON valid but structure issues: {validation['errors']}")
                    else:
                        print(f"    ❌ JSON Parse Error: {result['json_error']}")
                else:
                    print(f"    ❌ API Error: {result['error']}")

                # Kurze Pause zwischen Requests
                time.sleep(0.5)

            # Durchschnittswerte berechnen
            if model_results["summary"]["successful_calls"] > 0:
                model_results["summary"]["avg_response_time"] = round(
                    total_time / model_results["summary"]["successful_calls"], 2
                )
            model_results["summary"]["total_tokens"] = total_tokens

            self.results[model] = model_results

            # Model Summary ausgeben
            summary = model_results["summary"]
            print(f"  📊 Summary: {summary['successful_calls']}/{summary['total_tests']} calls successful, "
                  f"{summary['valid_json']}/{summary['total_tests']} valid JSON, "
                  f"{summary['valid_structure']}/{summary['total_tests']} valid structure")

        self.print_final_summary()

    def print_final_summary(self):
        """Drucke finale Zusammenfassung aller Modelle"""
        print("\n" + "=" * 60)
        print("🏆 FINAL RESULTS SUMMARY")
        print("=" * 60)

        # Tabelle Header
        print(f"{'Model':<20} {'Success':<8} {'JSON':<6} {'Struct':<7} {'Avg Time':<9} {'Tokens':<8}")
        print("-" * 60)

        # Beste Modelle tracken
        best_models = []

        for model, results in self.results.items():
            s = results["summary"]
            success_rate = f"{s['successful_calls']}/{s['total_tests']}"
            json_rate = f"{s['valid_json']}/{s['total_tests']}"
            struct_rate = f"{s['valid_structure']}/{s['total_tests']}"
            avg_time = f"{s['avg_response_time']}s"
            tokens = s['total_tokens']

            print(f"{model:<20} {success_rate:<8} {json_rate:<6} {struct_rate:<7} {avg_time:<9} {tokens:<8}")

            # Modell als "gut" bewerten wenn alle Tests erfolgreich
            if s['valid_structure'] == s['total_tests']:
                best_models.append((model, s['avg_response_time']))

        print("\n🎯 RECOMMENDED MODELS:")
        if best_models:
            best_models.sort(key=lambda x: x[1])  # Nach Response Time sortieren
            for model, time in best_models[:3]:  # Top 3
                print(f"   ✅ {model} (avg: {time}s)")
        else:
            print("   ❌ No models passed all tests")

        # Detaillierte Fehler für fehlgeschlagene Modelle
        print("\n🔍 DETAILED ERROR ANALYSIS:")
        for model, results in self.results.items():
            if results["summary"]["valid_structure"] < results["summary"]["total_tests"]:
                print(f"  ⚠️  {model}:")
                for article_key, article_result in results["articles"].items():
                    if not article_result.get("success", False):
                        print(f"    - {article_key}: {article_result.get('error', 'Unknown error')}")
                    elif not article_result.get("json_valid", False):
                        print(f"    - {article_key}: JSON Error - {article_result.get('json_error', 'Unknown')}")

    def save_results(self, filename: str = "llm_test_results.json"):
        """Speichere Ergebnisse in JSON-Datei"""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)
        print(f"\n💾 Results saved to {filename}")

def main():
    """Hauptfunktion"""
    tester = LLMModelTester()

    try:
        tester.run_comprehensive_test()
        tester.save_results()

    except KeyboardInterrupt:
        print("\n\n⏹️  Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")

if __name__ == "__main__":
    main()