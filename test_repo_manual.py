#!/usr/bin/env python3
"""
Manual test of Analysis Repository
"""
import os
import sys
sys.path.insert(0, 'app')

from dotenv import load_dotenv
load_dotenv()

from app.repositories.analysis import AnalysisRepo
from app.domain.analysis.schema import (
    AnalysisResult, Overall, Market, SentimentPayload, ImpactPayload
)

def test_repository():
    print("Testing Analysis Repository...")

    # Test getting items without analysis
    print("\n1. Testing get_items_without_analysis...")
    items = AnalysisRepo.get_items_without_analysis(limit=5)
    print(f"Found {len(items)} items without analysis")
    for item in items[:2]:
        print(f"  - Item {item['id']}: {item['title'][:50]}...")

    # Test counting pending
    print("\n2. Testing count_pending_analysis...")
    count = AnalysisRepo.count_pending_analysis()
    print(f"Pending analysis: {count} items")

    # Test stats
    print("\n3. Testing get_analysis_stats...")
    stats = AnalysisRepo.get_analysis_stats()
    print(f"Stats: {stats}")

    # Test upsert if we have items
    if items:
        test_item = items[0]
        test_item_id = test_item['id']

        print(f"\n4. Testing upsert with item {test_item_id}...")

        # Create test analysis
        analysis = AnalysisResult(
            sentiment=SentimentPayload(
                overall=Overall(label="positive", score=0.8, confidence=0.9),
                market=Market(bullish=0.7, bearish=0.2, uncertainty=0.1, time_horizon="short"),
                urgency=0.6,
                themes=["test", "analysis"]
            ),
            impact=ImpactPayload(overall=0.8, volatility=0.4),
            model_tag="test-model"
        )

        # Insert analysis
        AnalysisRepo.upsert(test_item_id, analysis)
        print("✅ Analysis inserted successfully")

        # Retrieve analysis
        retrieved = AnalysisRepo.get_by_item_id(test_item_id)
        if retrieved:
            print(f"✅ Retrieved analysis: sentiment={retrieved['sentiment_json']['overall']['label']}")
        else:
            print("❌ Failed to retrieve analysis")

        # Update analysis
        analysis.sentiment.overall.label = "negative"
        analysis.sentiment.overall.score = -0.5
        AnalysisRepo.upsert(test_item_id, analysis)
        print("✅ Analysis updated successfully")

        # Verify update
        updated = AnalysisRepo.get_by_item_id(test_item_id)
        if updated and updated['sentiment_json']['overall']['label'] == 'negative':
            print("✅ Update verified")
        else:
            print("❌ Update verification failed")

    print("\n✅ Repository tests completed successfully!")

if __name__ == "__main__":
    test_repository()