from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from typing import List
from app.database import get_session
from app.models import FeedHealth, FetchLog, Feed
from app.models.base import FeedStatus
# from app.schemas import FeedHealthResponse, FetchLogResponse
from typing import Any
FeedHealthResponse = Any
FetchLogResponse = Any

router = APIRouter(prefix="/health", tags=["health"])

@router.get("/feeds", response_model=List[FeedHealthResponse])
def get_all_feed_health(session: Session = Depends(get_session)):
    health_records = session.exec(select(FeedHealth)).all()
    return health_records

@router.get("/feeds/{feed_id}", response_model=FeedHealthResponse)
def get_feed_health(feed_id: int, session: Session = Depends(get_session)):
    health = session.exec(select(FeedHealth).where(FeedHealth.feed_id == feed_id)).first()
    if not health:
        raise HTTPException(status_code=404, detail="Feed health record not found")
    return health

@router.get("/logs/{feed_id}", response_model=List[FetchLogResponse])
def get_feed_logs(
    feed_id: int,
    limit: int = 50,
    session: Session = Depends(get_session)
):
    logs = session.exec(
        select(FetchLog)
        .where(FetchLog.feed_id == feed_id)
        .order_by(FetchLog.started_at.desc())
        .limit(limit)
    ).all()
    return logs

@router.get("/status")
def get_system_status(session: Session = Depends(get_session)):
    total_feeds = len(session.exec(select(Feed)).all())
    active_feeds = len(session.exec(select(Feed).where(Feed.status == FeedStatus.ACTIVE)).all())
    error_feeds = len(session.exec(select(Feed).where(Feed.status == FeedStatus.ERROR)).all())

    return {
        "total_feeds": total_feeds,
        "active_feeds": active_feeds,
        "error_feeds": error_feeds,
        "health_percentage": (active_feeds / total_feeds * 100) if total_feeds > 0 else 100
    }