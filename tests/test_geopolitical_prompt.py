#!/usr/bin/env python3
"""
Test geopolitical analysis prompt with sample articles
"""

import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services.llm_client import LLMClient

# Sample test articles
TEST_ARTICLES = [
    {
        "title": "Ukraine receives new military aid package from NATO allies",
        "summary": "NATO countries announced a $2 billion military aid package to Ukraine, including advanced air defense systems and ammunition. The move comes as tensions with Russia remain high in Eastern Europe.",
        "expected_geopolitical": True,
        "expected_stability": "negative",
        "expected_conflict_type": "interstate_war"
    },
    {
        "title": "Apple announces new iPhone 15 with improved camera features",
        "summary": "Apple unveiled the iPhone 15 at their annual event, featuring a 48MP camera, USB-C port, and improved battery life. The phone will be available starting next month at $799.",
        "expected_geopolitical": False,
        "expected_stability": "neutral"
    },
    {
        "title": "EU imposes new sanctions on Russian energy exports",
        "summary": "The European Union agreed on new sanctions targeting Russian oil and gas exports, aiming to reduce energy dependence. The measures could affect global energy markets and increase prices.",
        "expected_geopolitical": True,
        "expected_stability": "negative",
        "expected_conflict_type": "economic",
        "expected_affected": ["RU", "EU"]
    },
    {
        "title": "OpenAI releases GPT-4.5 with improved reasoning capabilities",
        "summary": "OpenAI announced GPT-4.5, a new language model with enhanced reasoning and coding abilities. The model shows 20% improvement on benchmark tests and is available via API.",
        "expected_geopolitical": False,
        "expected_stability": "neutral"
    },
    {
        "title": "China conducts military exercises near Taiwan",
        "summary": "The People's Liberation Army launched large-scale military drills around Taiwan, prompting concerns from the US and regional allies. Taiwan's defense ministry reported increased air and naval activity.",
        "expected_geopolitical": True,
        "expected_stability": "negative",
        "expected_conflict_type": "hybrid",
        "expected_affected": ["CN", "Taiwan"]
    }
]

def test_prompt_with_articles():
    """Test the extended prompt with sample articles"""

    # Check if OpenAI API key is set
    if not os.getenv('OPENAI_API_KEY'):
        print("⚠️  OPENAI_API_KEY not set - skipping live API tests")
        print("   Set OPENAI_API_KEY to test with real OpenAI API\n")

        # Test prompt structure only
        llm = LLMClient.__new__(LLMClient)  # Create without calling __init__
        prompt = llm._build_prompt("Test title", "Test summary")

        print("✓ Prompt structure test:")
        print(f"  Contains 'geopolitical': {'geopolitical' in prompt}")
        print(f"  Contains 'stability_score': {'stability_score' in prompt}")
        print(f"  Contains 'diplomatic_impact': {'diplomatic_impact' in prompt}")
        print(f"  Contains 'Entity Standards': {'Entity Standards' in prompt}")
        print(f"  Prompt length: ~{len(prompt)} characters")

        return

    # Test with real OpenAI API
    print("🧪 Testing geopolitical analysis prompt with OpenAI API\n")
    llm = LLMClient(model="gpt-4.1-nano")

    results = []

    for i, article in enumerate(TEST_ARTICLES, 1):
        print(f"Test {i}/{len(TEST_ARTICLES)}: {article['title'][:60]}...")

        try:
            result = llm.classify(article['title'], article['summary'])

            # Extract geopolitical data
            geo = result.get('geopolitical', {})

            # Check if geopolitical analysis was provided
            is_geopolitical = (
                abs(geo.get('stability_score', 0.0)) > 0.1 or
                abs(geo.get('economic_impact', 0.0)) > 0.1 or
                geo.get('security_relevance', 0.0) > 0.1 or
                len(geo.get('impact_affected', [])) > 0
            )

            # Validate against expectations
            expected_geo = article.get('expected_geopolitical', False)
            geo_match = "✓" if is_geopolitical == expected_geo else "✗"

            print(f"  {geo_match} Geopolitical: {is_geopolitical} (expected: {expected_geo})")
            print(f"  Stability: {geo.get('stability_score', 0.0):.2f}")
            print(f"  Economic Impact: {geo.get('economic_impact', 0.0):.2f}")
            print(f"  Security: {geo.get('security_relevance', 0.0):.2f}")
            print(f"  Conflict Type: {geo.get('conflict_type', 'N/A')}")
            print(f"  Affected: {geo.get('impact_affected', [])}")
            print(f"  Beneficiaries: {geo.get('impact_beneficiaries', [])}")
            print(f"  Regions: {geo.get('regions_affected', [])}")
            print(f"  Confidence: {geo.get('confidence', 0.0):.2f}")
            print()

            results.append({
                'title': article['title'],
                'is_geopolitical': is_geopolitical,
                'expected_geopolitical': expected_geo,
                'match': is_geopolitical == expected_geo,
                'stability_score': geo.get('stability_score', 0.0),
                'conflict_type': geo.get('conflict_type'),
                'affected': geo.get('impact_affected', []),
                'beneficiaries': geo.get('impact_beneficiaries', [])
            })

        except Exception as e:
            print(f"  ✗ Error: {e}\n")
            results.append({
                'title': article['title'],
                'error': str(e),
                'match': False
            })

    # Print summary
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)

    total = len(results)
    matched = sum(1 for r in results if r.get('match', False))
    errors = sum(1 for r in results if 'error' in r)

    print(f"Total tests: {total}")
    print(f"Matched expectations: {matched}/{total} ({matched/total*100:.1f}%)")
    print(f"Errors: {errors}")

    if matched == total and errors == 0:
        print("\n✅ All tests passed!")
    else:
        print("\n⚠️  Some tests failed - review results above")

    return results

if __name__ == "__main__":
    test_prompt_with_articles()
