#!/usr/bin/env python3
import os
import psycopg2
import json

conn = psycopg2.connect(os.getenv('DATABASE_URL'))
cur = conn.cursor()

# Get most recent item ID
cur.execute("SELECT id FROM items ORDER BY created_at DESC LIMIT 1")
recent_item_id = cur.fetchone()[0]
print(f"Adding analysis for recent item ID: {recent_item_id}")

sentiment_data = {
    "overall": {"label": "positive", "score": 0.85, "confidence": 0.92},
    "market": {"bullish": 0.8, "bearish": 0.1, "uncertainty": 0.1, "time_horizon": "short"},
    "urgency": 0.75,
    "themes": ["military", "defense", "geopolitics"]
}
impact_data = {"overall": 0.9, "volatility": 0.6}

cur.execute("""
    SELECT upsert_item_analysis(%s, %s::jsonb, %s::jsonb, %s)
""", (recent_item_id, json.dumps(sentiment_data), json.dumps(impact_data), "test-ui-badge"))

conn.commit()
print(f"Added test analysis for item {recent_item_id}")
cur.close()
conn.close()