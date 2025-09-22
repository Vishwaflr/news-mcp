#!/usr/bin/env python3
"""Test system status function directly."""

import os
import sys
sys.path.append('/home/cytrex/news-mcp')

try:
    from app.web.components.system_components import get_system_status
    from app.database import get_session

    print("=== Direct System Status Test ===")

    session = next(get_session())
    result = get_system_status(session)
    print("✅ API call successful")
    print(f"Result (first 200 chars): {result[:200]}...")

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()