"""Simple feeds endpoint for UI components"""
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.database import get_session
from app.models.core import Feed
from app.core.logging_config import get_logger

router = APIRouter(prefix="/api/feeds-simple", tags=["feeds-simple"])
logger = get_logger(__name__)

@router.get("/list")
async def get_feeds_list(db: Session = Depends(get_session)):
    """Get simple list of active feeds for UI dropdowns"""
    try:
        # Direct database query to get active feeds
        stmt = select(Feed).where(Feed.status == "ACTIVE").order_by(Feed.title)
        result = db.execute(stmt)
        feeds = result.scalars().all()

        # Return simple JSON array
        return [
            {
                "id": feed.id,
                "title": feed.title,
                "status": feed.status
            }
            for feed in feeds
        ]
    except Exception as e:
        logger.error(f"Error loading feeds: {e}")
        # Return empty array on error
        return []