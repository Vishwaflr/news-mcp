#!/usr/bin/env python3
"""
Manual test of LLM Client
"""
import os
import sys
sys.path.insert(0, 'app')

from dotenv import load_dotenv
load_dotenv()

from app.services.llm_client import LLMClient

def test_llm_parsing():
    print("Testing LLM Client...")

    client = LLMClient(model="gpt-4o-mini", rate_per_sec=2.0)

    # Test normal response
    print("\n1. Testing normal classification...")
    result = client.classify(
        "Bitcoin surges to new all-time high",
        "Bitcoin has reached a new all-time high of $95,000 amid institutional adoption"
    )

    print(f"Result: {result}")
    print(f"Sentiment: {result['overall']['label']}")
    print(f"Impact: {result['impact']['overall']}")

    # Test fallback mechanism
    print("\n2. Testing fallback...")
    fallback = client._get_fallback_result()
    print(f"Fallback: {fallback}")

    # Test validation
    print("\n3. Testing validation...")
    test_data = {
        "overall": {"label": "positive", "score": 1.5},  # Invalid score
        "impact": {"overall": 0.8}
    }
    normalized = client._validate_and_normalize_result(test_data)
    print(f"Normalized score: {normalized['overall']['score']}")  # Should be clamped to 1.0

    print("\n✅ LLM Client tests completed successfully!")

if __name__ == "__main__":
    test_llm_parsing()