#!/usr/bin/env python3
"""Test statistics API directly."""

import os
import sys
sys.path.append('/home/cytrex/news-mcp')

try:
    from app.api.statistics import get_dashboard_stats
    from app.database import get_session

    print("=== Direct Stats API Test ===")

    session = next(get_session())
    result = get_dashboard_stats(session)
    print("✅ API call successful")
    print(f"Overview: {result['overview']}")

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()