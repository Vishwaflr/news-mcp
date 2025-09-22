from fastapi import APIRouter, Depends, HTTPException, Body
from sqlmodel import Session, select, text
from typing import Optional, Dict, Any
import logging
from datetime import datetime, timedelta

from app.database import get_session
from app.models import Feed, FetchLog

router = APIRouter(prefix="/scheduler", tags=["scheduler"])
logger = logging.getLogger(__name__)

# Standard response format for MCP v2
def create_response(data: Any = None, error: str = None, meta: Dict[str, Any] = None) -> Dict[str, Any]:
    """Create standardized API response for MCP v2"""
    return {
        "ok": error is None,
        "data": data,
        "meta": meta or {},
        "errors": [{"code": "api_error", "message": error}] if error else []
    }

@router.get("/status")
def get_scheduler_status(session: Session = Depends(get_session)):
    """Get current scheduler status and configuration"""
    try:
        # Get basic feed statistics
        total_feeds = session.exec(select(Feed)).all()
        active_feeds = [f for f in total_feeds if f.status == "active"]

        # Calculate average fetch interval
        if active_feeds:
            avg_interval = sum(f.fetch_interval_minutes for f in active_feeds) / len(active_feeds)
        else:
            avg_interval = 0

        # Get recent fetch activity (last hour)
        one_hour_ago = datetime.utcnow() - timedelta(hours=1)
        recent_fetches = session.exec(
            select(FetchLog).where(FetchLog.started_at > one_hour_ago)
        ).all()

        # Get queue depth approximation (feeds due for update)
        now = datetime.utcnow()
        feeds_due = 0
        for feed in active_feeds:
            if feed.last_fetch:
                next_fetch = feed.last_fetch + timedelta(minutes=feed.fetch_interval_minutes)
                if next_fetch <= now:
                    feeds_due += 1
            else:
                feeds_due += 1  # Never fetched feeds are due

        # Check for stuck/stale operations
        stale_cutoff = datetime.utcnow() - timedelta(minutes=30)
        stale_operations = session.exec(
            select(FetchLog).where(
                FetchLog.status == "running",
                FetchLog.started_at < stale_cutoff
            )
        ).all()

        status_data = {
            "status": "active" if len(stale_operations) == 0 else "degraded",
            "configuration": {
                "total_feeds": len(total_feeds),
                "active_feeds": len(active_feeds),
                "avg_interval_minutes": round(avg_interval, 1)
            },
            "activity": {
                "feeds_due_for_update": feeds_due,
                "recent_fetches_1h": len(recent_fetches),
                "stale_operations": len(stale_operations)
            },
            "last_checked": datetime.utcnow().isoformat(),
            "uptime_status": "operational"
        }

        return create_response(data=status_data)

    except Exception as e:
        logger.error(f"Error getting scheduler status: {e}")
        return create_response(error=f"Failed to get scheduler status: {str(e)}")

@router.post("/interval")
def set_global_interval(
    minutes: int = Body(...),
    session: Session = Depends(get_session)
):
    """Set global fetch interval for all active feeds"""
    try:
        if minutes < 1 or minutes > 1440:  # 1 minute to 24 hours
            return create_response(error="Interval must be between 1 and 1440 minutes")

        # Update all active feeds
        active_feeds = session.exec(select(Feed).where(Feed.status == "active")).all()
        updated_count = 0

        for feed in active_feeds:
            feed.fetch_interval_minutes = minutes
            session.add(feed)
            updated_count += 1

        session.commit()

        logger.info(f"Updated fetch interval to {minutes} minutes for {updated_count} feeds")

        return create_response(data={
            "interval_minutes": minutes,
            "updated_feeds": updated_count,
            "effective_at": datetime.utcnow().isoformat()
        })

    except Exception as e:
        logger.error(f"Error setting scheduler interval: {e}")
        session.rollback()
        return create_response(error=f"Failed to set interval: {str(e)}")

@router.post("/interval/{feed_id}")
def set_feed_interval(
    feed_id: int,
    minutes: int = Body(...),
    session: Session = Depends(get_session)
):
    """Set fetch interval for a specific feed"""
    try:
        if minutes < 1 or minutes > 1440:
            return create_response(error="Interval must be between 1 and 1440 minutes")

        feed = session.get(Feed, feed_id)
        if not feed:
            return create_response(error="Feed not found")

        old_interval = feed.fetch_interval_minutes
        feed.fetch_interval_minutes = minutes
        session.add(feed)
        session.commit()

        logger.info(f"Updated feed {feed_id} interval from {old_interval} to {minutes} minutes")

        return create_response(data={
            "feed_id": feed_id,
            "old_interval_minutes": old_interval,
            "new_interval_minutes": minutes,
            "effective_at": datetime.utcnow().isoformat()
        })

    except Exception as e:
        logger.error(f"Error setting feed {feed_id} interval: {e}")
        session.rollback()
        return create_response(error=f"Failed to set feed interval: {str(e)}")

@router.post("/pause")
def pause_scheduler(
    feed_id: Optional[int] = Body(None),
    session: Session = Depends(get_session)
):
    """Pause scheduler for all feeds or specific feed"""
    try:
        if feed_id:
            # Pause specific feed
            feed = session.get(Feed, feed_id)
            if not feed:
                return create_response(error="Feed not found")

            if feed.status == "paused":
                return create_response(error="Feed is already paused")

            feed.status = "paused"
            session.add(feed)
            session.commit()

            return create_response(data={
                "action": "pause",
                "scope": "feed",
                "feed_id": feed_id,
                "previous_status": "active",
                "paused_at": datetime.utcnow().isoformat()
            })
        else:
            # Pause all active feeds
            active_feeds = session.exec(select(Feed).where(Feed.status == "active")).all()
            paused_count = 0

            for feed in active_feeds:
                feed.status = "paused"
                session.add(feed)
                paused_count += 1

            session.commit()

            return create_response(data={
                "action": "pause",
                "scope": "global",
                "paused_feeds": paused_count,
                "paused_at": datetime.utcnow().isoformat()
            })

    except Exception as e:
        logger.error(f"Error pausing scheduler: {e}")
        session.rollback()
        return create_response(error=f"Failed to pause scheduler: {str(e)}")

@router.post("/resume")
def resume_scheduler(
    feed_id: Optional[int] = Body(None),
    session: Session = Depends(get_session)
):
    """Resume scheduler for all feeds or specific feed"""
    try:
        if feed_id:
            # Resume specific feed
            feed = session.get(Feed, feed_id)
            if not feed:
                return create_response(error="Feed not found")

            if feed.status == "active":
                return create_response(error="Feed is already active")

            feed.status = "active"
            session.add(feed)
            session.commit()

            return create_response(data={
                "action": "resume",
                "scope": "feed",
                "feed_id": feed_id,
                "previous_status": "paused",
                "resumed_at": datetime.utcnow().isoformat()
            })
        else:
            # Resume all paused feeds
            paused_feeds = session.exec(select(Feed).where(Feed.status == "paused")).all()
            resumed_count = 0

            for feed in paused_feeds:
                feed.status = "active"
                session.add(feed)
                resumed_count += 1

            session.commit()

            return create_response(data={
                "action": "resume",
                "scope": "global",
                "resumed_feeds": resumed_count,
                "resumed_at": datetime.utcnow().isoformat()
            })

    except Exception as e:
        logger.error(f"Error resuming scheduler: {e}")
        session.rollback()
        return create_response(error=f"Failed to resume scheduler: {str(e)}")

@router.get("/heartbeat")
def get_scheduler_heartbeat(session: Session = Depends(get_session)):
    """Get scheduler heartbeat and health metrics"""
    try:
        now = datetime.utcnow()

        # Get recent activity (last 5 minutes)
        recent_cutoff = now - timedelta(minutes=5)
        recent_activity = session.exec(
            select(FetchLog).where(FetchLog.started_at > recent_cutoff)
        ).all()

        # Get system resource usage approximation
        active_fetches = session.exec(
            select(FetchLog).where(FetchLog.status == "running")
        ).all()

        # Calculate health score based on recent activity
        health_score = 100
        if len(active_fetches) > 20:  # Too many concurrent fetches
            health_score -= 20

        # Check for recent errors
        recent_errors = [log for log in recent_activity if log.status == "error"]
        error_rate = len(recent_errors) / max(1, len(recent_activity))
        if error_rate > 0.1:  # More than 10% error rate
            health_score -= 30

        heartbeat_data = {
            "timestamp": now.isoformat(),
            "status": "healthy" if health_score > 70 else "degraded",
            "health_score": health_score,
            "metrics": {
                "active_operations": len(active_fetches),
                "recent_activity_5m": len(recent_activity),
                "recent_errors_5m": len(recent_errors),
                "error_rate": round(error_rate * 100, 2)
            },
            "uptime": {
                "scheduler_process": "running",
                "database_connection": "ok",
                "api_server": "ok"
            }
        }

        return create_response(data=heartbeat_data)

    except Exception as e:
        logger.error(f"Error getting scheduler heartbeat: {e}")
        return create_response(error=f"Failed to get heartbeat: {str(e)}")