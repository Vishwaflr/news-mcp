#!/usr/bin/env python
from app.database import get_session
from app.models import Feed, Item
from sqlmodel import select

try:
    session = next(get_session())
    # Different approach - select only Item then join
    query = select(Item).join(Feed)
    query = query.order_by(Item.published.desc()).offset(0).limit(20)
    results = session.exec(query).all()
    print(f"Found {len(results)} items")

    # Now get with Feed data
    query2 = session.query(Item, Feed).join(Feed)
    results2 = query2.limit(20).all()
    print(f"Found {len(results2)} items with feed data")

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()