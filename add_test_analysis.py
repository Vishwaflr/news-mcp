#!/usr/bin/env python3
import os
import psycopg2
import json

conn = psycopg2.connect(os.getenv('DATABASE_URL'))
cur = conn.cursor()

# Get first item
cur.execute("SELECT id FROM items LIMIT 1")
test_item_id = cur.fetchone()[0]

sentiment_data = {
    "overall": {"label": "positive", "score": 0.8, "confidence": 0.9},
    "market": {"bullish": 0.7, "bearish": 0.2, "uncertainty": 0.1, "time_horizon": "short"},
    "urgency": 0.6,
    "themes": ["test", "analysis"]
}
impact_data = {"overall": 0.8, "volatility": 0.4}

cur.execute("""
    SELECT upsert_item_analysis(%s, %s::jsonb, %s::jsonb, %s)
""", (test_item_id, json.dumps(sentiment_data), json.dumps(impact_data), "gpt-4o-mini-test"))

conn.commit()
print(f"Added test analysis for item {test_item_id}")
cur.close()
conn.close()