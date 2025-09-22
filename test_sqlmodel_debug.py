#!/usr/bin/env python3
"""Debug SQLModel compatibility issues."""

import os
import sys
sys.path.append('/home/cytrex/news-mcp')

from app.database import get_session
from sqlmodel import Session, select
# Import from new model structure
from app.models.feeds import Feed, Source, Category, FeedCategory

def test_basic_queries():
    """Test basic SQLModel queries to identify the issue."""

    session = next(get_session())

    print("=== SQLModel Debug Test ===")
    print(f"SQLModel version: {sys.modules['sqlmodel'].__version__}")

    try:
        # Test 1: Simple select
        print("\n1. Testing simple Feed select...")
        feeds = session.exec(select(Feed)).all()
        print(f"✅ Found {len(feeds)} feeds")

        # Test 2: Join with Source
        print("\n2. Testing Feed + Source join...")
        query = select(Feed, Source).join(Source)
        results = session.exec(query).all()
        print(f"✅ Found {len(results)} feed-source pairs")

        # Test 3: Complex join with FeedCategory
        print("\n3. Testing Feed + Source + FeedCategory join...")
        query = select(Feed, Source).join(Source).join(FeedCategory)
        results = session.exec(query).all()
        print(f"✅ Found {len(results)} results with categories")

        # Test 4: Category filtering
        print("\n4. Testing category filtering...")
        category_id = 1
        query = select(Feed, Source).join(Source).join(FeedCategory).where(FeedCategory.category_id == category_id)
        results = session.exec(query).all()
        print(f"✅ Found {len(results)} results for category {category_id}")

    except Exception as e:
        print(f"❌ Error: {e}")
        print(f"Error type: {type(e)}")
        import traceback
        traceback.print_exc()

        # Test what specific operation fails
        print("\n=== Detailed error analysis ===")
        try:
            print("Testing basic Feed select...")
            feeds = session.exec(select(Feed)).first()
            print(f"✅ Basic select works: {feeds}")
        except Exception as e2:
            print(f"❌ Basic select fails: {e2}")

        try:
            print("Testing join operation...")
            query = select(Feed, Source).join(Source)
            print(f"✅ Query object created: {query}")
            result = session.exec(query).first()
            print(f"✅ Join execution works: {result}")
        except Exception as e3:
            print(f"❌ Join fails: {e3}")

    finally:
        session.close()

if __name__ == "__main__":
    test_basic_queries()