#!/usr/bin/env python
from app.database import get_session
from app.models import Item, Feed
from sqlmodel import select

try:
    session = next(get_session())
    query = select(Item, Feed).join(Feed, Item.feed_id == Feed.id)
    query = query.order_by(Item.published.desc()).offset(0).limit(20)
    results = session.exec(query).all()
    print(f"Found {len(results)} items")
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()