#!/usr/bin/env python3
"""Test simple SQLModel without BaseTableModel."""

import os
import sys
sys.path.append('/home/cytrex/news-mcp')

from sqlmodel import SQLModel, Field, Session, select, create_engine
from typing import Optional

# Test with direct SQLModel inheritance
class TestFeed(SQLModel, table=True):
    __tablename__ = "feeds"

    id: Optional[int] = Field(default=None, primary_key=True)
    url: str = Field(unique=True, index=True)
    title: Optional[str] = None

def test_simple_model():
    """Test if basic SQLModel works."""
    from app.database import get_session

    session = next(get_session())

    print("=== Simple SQLModel Test ===")

    try:
        # Test simple select
        print("Testing simple TestFeed select...")
        feeds = session.exec(select(TestFeed)).all()
        print(f"✅ Found {len(feeds)} test feeds")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        session.close()

if __name__ == "__main__":
    test_simple_model()