#!/usr/bin/env python3
"""Test simple statistics query without SQLModel."""

import os
import sys
sys.path.append('/home/cytrex/news-mcp')

from app.database import get_session
from sqlmodel import text

def test_simple_stats():
    """Test if basic stats queries work."""
    session = next(get_session())

    print("=== Simple Stats Test ===")

    try:
        # Test 1: Count feeds
        print("Testing feed count...")
        count = session.exec(text("SELECT COUNT(*) FROM feeds")).one()
        print(f"✅ Found {count} feeds")

        # Test 2: Count items
        print("Testing item count...")
        count = session.exec(text("SELECT COUNT(*) FROM items")).one()
        print(f"✅ Found {count} items")

        # Test 3: Simple join
        print("Testing simple join...")
        results = session.exec(text("""
            SELECT f.id, f.title, COUNT(i.id) as item_count
            FROM feeds f
            LEFT JOIN items i ON f.id = i.feed_id
            GROUP BY f.id, f.title
            LIMIT 5
        """)).fetchall()
        print(f"✅ Found {len(results)} feed results")
        for row in results:
            print(f"  Feed {row[0]}: {row[1]} ({row[2]} items)")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        session.close()

if __name__ == "__main__":
    test_simple_stats()