#!/usr/bin/env python3
"""
Simple Repository test with direct DB access
"""
import os
import sys
sys.path.insert(0, 'app')

from dotenv import load_dotenv
load_dotenv()

import psycopg2
import json

def test_simple_upsert():
    print("Testing simple upsert with direct psycopg2...")

    conn = psycopg2.connect(os.getenv('DATABASE_URL'))
    cur = conn.cursor()

    try:
        # Get a real item ID first
        cur.execute("SELECT id FROM items LIMIT 1")
        test_item_id = cur.fetchone()[0]
        print(f"Using item ID: {test_item_id}")

        # Test upsert function directly
        sentiment_data = {
            "overall": {"label": "positive", "score": 0.8, "confidence": 0.9},
            "market": {"bullish": 0.7, "bearish": 0.2, "uncertainty": 0.1, "time_horizon": "short"},
            "urgency": 0.6,
            "themes": ["test", "analysis"]
        }
        impact_data = {
            "overall": 0.8,
            "volatility": 0.4
        }

        # Call upsert function
        cur.execute("""
            SELECT upsert_item_analysis(%s, %s::jsonb, %s::jsonb, %s)
        """, (test_item_id, json.dumps(sentiment_data), json.dumps(impact_data), "test-model"))

        conn.commit()
        print(f"✅ Successfully inserted analysis for item {test_item_id}")

        # Verify insert
        cur.execute("""
            SELECT sentiment_json, impact_json, model_tag
            FROM item_analysis
            WHERE item_id = %s
        """, (test_item_id,))

        result = cur.fetchone()
        if result:
            print(f"✅ Retrieved analysis: {result[2]}")
            print(f"   Sentiment: {result[0]['overall']['label']}")
            print(f"   Impact: {result[1]['overall']}")

        # Cleanup
        cur.execute("DELETE FROM item_analysis WHERE item_id = %s", (test_item_id,))
        conn.commit()
        print("✅ Cleanup completed")

    except Exception as e:
        print(f"❌ Error: {e}")
        conn.rollback()
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    test_simple_upsert()