import asyncio
import logging
from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlmodel import Session, select
from app.database import engine
from app.models import FeedStatus, Feed
from app.config import settings
from jobs.fetcher import FeedFetcher

logger = logging.getLogger(__name__)

class FeedScheduler:
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.fetcher = FeedFetcher()
        self.running_jobs = set()

    async def start(self):
        logger.info("Starting feed scheduler")
        self.scheduler.start()

        self.scheduler.add_job(
            self._schedule_feeds,
            IntervalTrigger(minutes=1),
            id="schedule_feeds",
            replace_existing=True
        )

        self.scheduler.add_job(
            self._cleanup_old_logs,
            IntervalTrigger(hours=6),
            id="cleanup_logs",
            replace_existing=True
        )

    async def stop(self):
        logger.info("Stopping feed scheduler")
        self.scheduler.shutdown()
        await self.fetcher.close()

    async def _schedule_feeds(self):
        with Session(engine) as session:
            now = datetime.utcnow()

            feeds = session.exec(
                select(Feed).where(
                    Feed.status == FeedStatus.ACTIVE
                )
            ).all()

            for feed in feeds:
                should_fetch = False

                if not feed.last_fetched:
                    should_fetch = True
                else:
                    next_fetch = feed.last_fetched + timedelta(minutes=feed.fetch_interval_minutes)
                    if now >= next_fetch:
                        should_fetch = True

                if should_fetch and feed.id not in self.running_jobs:
                    job_id = f"fetch_feed_{feed.id}"

                    self.scheduler.add_job(
                        self._fetch_feed_with_cleanup,
                        args=[feed],
                        id=job_id,
                        replace_existing=True
                    )

                    self.running_jobs.add(feed.id)
                    logger.debug(f"Scheduled fetch for feed {feed.id}")

    async def _fetch_feed_with_cleanup(self, feed: Feed):
        try:
            await self.fetcher.fetch_feed(feed)
        except Exception as e:
            logger.error(f"Error in scheduled fetch for feed {feed.id}: {e}")
        finally:
            self.running_jobs.discard(feed.id)

    async def _cleanup_old_logs(self):
        logger.info("Cleaning up old fetch logs")
        with Session(engine) as session:
            cutoff_date = datetime.utcnow() - timedelta(days=30)

            from app.models import FetchLog
            old_logs = session.exec(
                select(FetchLog).where(FetchLog.started_at < cutoff_date)
            ).all()

            for log in old_logs:
                session.delete(log)

            session.commit()
            logger.info(f"Cleaned up {len(old_logs)} old fetch logs")

    async def fetch_feed_now(self, feed_id: int):
        with Session(engine) as session:
            feed = session.get(Feed, feed_id)
            if not feed:
                raise ValueError(f"Feed {feed_id} not found")

            return await self.fetcher.fetch_feed(feed)

if __name__ == "__main__":
    async def main():
        logging.basicConfig(level=settings.log_level)
        scheduler = FeedScheduler()

        try:
            await scheduler.start()
            logger.info("Feed scheduler running. Press Ctrl+C to stop.")

            while True:
                await asyncio.sleep(1)

        except KeyboardInterrupt:
            logger.info("Shutting down...")
        finally:
            await scheduler.stop()

    asyncio.run(main())