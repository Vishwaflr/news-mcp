#!/usr/bin/env python3
"""Test BaseTableModel functionality."""

import os
import sys
sys.path.append('/home/cytrex/news-mcp')

from app.models.base import BaseTableModel
from sqlmodel import Session, select
from typing import Optional

# Test with BaseTableModel inheritance
class TestModelBase(BaseTableModel, table=True):
    __tablename__ = "test_model_base"

    url: str = BaseTableModel.Field(unique=True, index=True)
    title: Optional[str] = None

def test_base_model():
    """Test if BaseTableModel works."""
    from app.database import get_session

    session = next(get_session())

    print("=== BaseTableModel Test ===")

    try:
        print("Testing BaseTableModel TestFeedBase select...")
        models = session.exec(select(TestModelBase)).all()
        print(f"✅ Found {len(models)} test models")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        session.close()

if __name__ == "__main__":
    test_base_model()