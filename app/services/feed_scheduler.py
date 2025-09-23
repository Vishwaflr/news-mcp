"""
Feed Scheduler Service

Handles automatic fetching of feeds based on their fetch_interval_minutes.
"""

from app.core.logging_config import get_logger
import asyncio
from datetime import datetime, timedelta
from typing import List, Optional
from sqlmodel import Session, select

from app.database import engine
from app.models.core import Feed, FeedStatus
from app.services.feed_fetcher_sync import SyncFeedFetcher

logger = get_logger(__name__)


class FeedScheduler:
    """Service for scheduling automatic feed fetches"""

    def __init__(self):
        self.is_running = False
        self.check_interval_seconds = 60  # Check every minute
        self.fetcher = SyncFeedFetcher()

    async def start(self):
        """Start the scheduler"""
        if self.is_running:
            logger.warning("Feed scheduler is already running")
            return

        logger.info("Starting feed scheduler")
        self.is_running = True

        try:
            while self.is_running:
                await self._check_and_fetch_feeds()
                await asyncio.sleep(self.check_interval_seconds)
        except Exception as e:
            logger.error(f"Feed scheduler error: {e}")
        finally:
            self.is_running = False
            logger.info("Feed scheduler stopped")

    async def stop(self):
        """Stop the scheduler"""
        logger.info("Stopping feed scheduler")
        self.is_running = False

    async def _check_and_fetch_feeds(self):
        """Check which feeds need fetching and fetch them"""
        try:
            with Session(engine) as session:
                # Get active feeds that might need fetching
                feeds = session.exec(
                    select(Feed).where(
                        Feed.status == FeedStatus.ACTIVE,
                        Feed.fetch_interval_minutes > 0
                    )
                ).all()

                now = datetime.utcnow()
                feeds_to_fetch = []

                for feed in feeds:
                    if self._should_fetch_feed(feed, now):
                        feeds_to_fetch.append(feed)

                if feeds_to_fetch:
                    logger.info(f"Scheduled fetch for {len(feeds_to_fetch)} feeds")
                    await self._fetch_feeds_batch(feeds_to_fetch)

        except Exception as e:
            logger.error(f"Error checking feeds for scheduled fetch: {e}")

    def _should_fetch_feed(self, feed: Feed, now: datetime) -> bool:
        """Determine if a feed should be fetched now"""
        if not feed.fetch_interval_minutes or feed.fetch_interval_minutes <= 0:
            return False

        if not feed.last_fetched:
            # Never fetched, fetch immediately
            return True

        # Calculate next fetch time
        next_fetch_time = feed.last_fetched + timedelta(minutes=feed.fetch_interval_minutes)

        # Add a small tolerance (5 minutes) to avoid timing issues
        tolerance = timedelta(minutes=5)
        return now >= (next_fetch_time - tolerance)

    async def _fetch_feeds_batch(self, feeds: List[Feed]):
        """Fetch a batch of feeds"""
        for feed in feeds:
            try:
                logger.debug(f"Scheduled fetch for feed {feed.id} ({feed.title})")

                # Use sync fetcher (will trigger auto-analysis if enabled)
                success, items_count = self.fetcher.fetch_feed_sync(feed.id)

                if success:
                    logger.info(f"Scheduled fetch for feed {feed.id} completed: {items_count} new items")
                else:
                    logger.warning(f"Scheduled fetch for feed {feed.id} failed")

            except Exception as e:
                logger.error(f"Error in scheduled fetch for feed {feed.id}: {e}")

            # Small delay between feeds to avoid overwhelming the system
            await asyncio.sleep(2)

    def get_next_fetch_times(self, limit: int = 10) -> List[dict]:
        """Get upcoming fetch times for feeds"""
        try:
            with Session(engine) as session:
                feeds = session.exec(
                    select(Feed).where(
                        Feed.status == FeedStatus.ACTIVE,
                        Feed.fetch_interval_minutes > 0
                    ).limit(limit)
                ).all()

                now = datetime.utcnow()
                next_fetches = []

                for feed in feeds:
                    if feed.last_fetched and feed.fetch_interval_minutes:
                        next_fetch = feed.last_fetched + timedelta(minutes=feed.fetch_interval_minutes)
                        is_due = now >= next_fetch

                        next_fetches.append({
                            "feed_id": feed.id,
                            "feed_title": feed.title,
                            "last_fetched": feed.last_fetched,
                            "fetch_interval_minutes": feed.fetch_interval_minutes,
                            "next_fetch": next_fetch,
                            "is_due": is_due,
                            "auto_analyze_enabled": feed.auto_analyze_enabled
                        })

                # Sort by next fetch time
                next_fetches.sort(key=lambda x: x["next_fetch"])
                return next_fetches

        except Exception as e:
            logger.error(f"Error getting next fetch times: {e}")
            return []

    def get_scheduler_status(self) -> dict:
        """Get current scheduler status"""
        return {
            "is_running": self.is_running,
            "check_interval_seconds": self.check_interval_seconds,
            "fetcher_active": self.fetcher is not None
        }


# Global scheduler instance
_scheduler_instance: Optional[FeedScheduler] = None


def get_scheduler() -> FeedScheduler:
    """Get global scheduler instance"""
    global _scheduler_instance
    if _scheduler_instance is None:
        _scheduler_instance = FeedScheduler()
    return _scheduler_instance


async def start_scheduler():
    """Start the global scheduler"""
    scheduler = get_scheduler()
    await scheduler.start()


async def stop_scheduler():
    """Stop the global scheduler"""
    scheduler = get_scheduler()
    await scheduler.stop()