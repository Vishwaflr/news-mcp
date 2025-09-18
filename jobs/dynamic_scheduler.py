"""
Dynamic Feed Scheduler

A separate service that runs parallel to the web application and manages
feed fetching with dynamic configuration reloading. Reacts to configuration
changes in real-time without requiring restarts.

This scheduler replaces static configuration with database-driven configuration
that can be updated through the web interface.
"""
import asyncio
import logging
import signal
import sys
from typing import Dict, List, Optional, Set
from datetime import datetime, timedelta
from dataclasses import dataclass
from sqlmodel import Session, select

from app.database import engine
from app.models import Feed, FeedStatus
from app.services.configuration_watcher import (
    get_configuration_watcher, ConfigurationChange
)
from app.services.dynamic_template_manager import get_dynamic_template_manager
from jobs.fetcher import FeedFetcher

logger = logging.getLogger(__name__)

@dataclass
class ScheduledFeed:
    """Represents a scheduled feed with its configuration"""
    feed_id: int
    url: str
    title: str
    interval_minutes: int
    next_fetch: datetime
    status: FeedStatus
    consecutive_failures: int = 0
    is_running: bool = False

class DynamicScheduler:
    """Dynamic feed scheduler that reacts to configuration changes"""

    def __init__(self, instance_id: str = "dynamic_scheduler",
                 config_check_interval: int = 30):
        self.instance_id = instance_id
        self.config_check_interval = config_check_interval
        self.running = False
        self.scheduled_feeds: Dict[int, ScheduledFeed] = {}
        self.fetcher = None
        self.shutdown_event = asyncio.Event()

    async def start(self):
        """Start the dynamic scheduler"""
        logger.info(f"Starting Dynamic Scheduler (ID: {self.instance_id})")

        self.running = True
        self.fetcher = FeedFetcher()

        # Set up signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        try:
            # Initial configuration load
            await self._load_initial_configuration()

            # Start main scheduler loop
            await self._scheduler_loop()

        except Exception as e:
            logger.error(f"Scheduler error: {e}")
            raise
        finally:
            await self._cleanup()

    async def stop(self):
        """Stop the scheduler gracefully"""
        logger.info("Stopping Dynamic Scheduler...")
        self.running = False
        self.shutdown_event.set()

        if self.fetcher:
            await self.fetcher.close()

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"Received signal {signum}, shutting down...")
        asyncio.create_task(self.stop())

    async def _scheduler_loop(self):
        """Main scheduler loop"""
        logger.info("Dynamic Scheduler loop started")

        last_config_check = datetime.min

        while self.running:
            try:
                current_time = datetime.utcnow()

                # Check for configuration changes periodically
                if (current_time - last_config_check).total_seconds() >= self.config_check_interval:
                    await self._check_configuration_changes()
                    last_config_check = current_time

                # Process scheduled feeds
                await self._process_scheduled_feeds()

                # Update scheduler heartbeat
                await self._update_heartbeat()

                # Sleep for a short interval before next iteration
                try:
                    await asyncio.wait_for(self.shutdown_event.wait(), timeout=5.0)
                    break  # Shutdown requested
                except asyncio.TimeoutError:
                    continue  # Continue normal operation

            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}")
                await asyncio.sleep(5)  # Wait before retrying

        logger.info("Dynamic Scheduler loop ended")

    async def _load_initial_configuration(self):
        """Load initial feed configuration from database"""
        logger.info("Loading initial feed configuration...")

        with Session(engine) as session:
            feeds = session.exec(
                select(Feed).where(Feed.status == FeedStatus.ACTIVE)
            ).all()

            for feed in feeds:
                scheduled_feed = ScheduledFeed(
                    feed_id=feed.id,
                    url=feed.url,
                    title=feed.title or f"Feed {feed.id}",
                    interval_minutes=feed.fetch_interval_minutes,
                    next_fetch=self._calculate_next_fetch(
                        feed.last_fetched, feed.fetch_interval_minutes
                    ),
                    status=feed.status
                )

                self.scheduled_feeds[feed.id] = scheduled_feed
                logger.debug(f"Scheduled feed {feed.id}: {feed.title}")

        logger.info(f"Loaded {len(self.scheduled_feeds)} active feeds")

    async def _check_configuration_changes(self):
        """Check for and apply configuration changes"""
        try:
            with get_configuration_watcher(scheduler_instance=self.instance_id) as watcher:
                changes = watcher.detect_changes_since_last_check()

                if changes:
                    logger.info(f"Detected {len(changes)} configuration changes")
                    await self._apply_configuration_changes(changes)

                    # Mark changes as applied
                    change_ids = [change.timestamp.timestamp() for change in changes]  # Use timestamps as IDs
                    watcher.mark_changes_as_applied()

        except Exception as e:
            logger.error(f"Error checking configuration changes: {e}")

    async def _apply_configuration_changes(self, changes: List[ConfigurationChange]):
        """Apply configuration changes to the scheduler"""
        feeds_to_reload: Set[int] = set()

        for change in changes:
            logger.info(f"Applying change: {change.change_type}")

            if change.change_type == 'feed_created':
                await self._handle_feed_created(change)

            elif change.change_type == 'feed_updated':
                await self._handle_feed_updated(change)
                if change.feed_id:
                    feeds_to_reload.add(change.feed_id)

            elif change.change_type == 'feed_deleted':
                await self._handle_feed_deleted(change)

            elif change.change_type in ['template_updated', 'feed_template_assigned', 'feed_template_unassigned']:
                await self._handle_template_changes(change)
                # Template changes might affect multiple feeds
                with get_configuration_watcher() as watcher:
                    affected_feeds = watcher.get_template_changes_affecting_feeds()
                    feeds_to_reload.update(affected_feeds.keys())

        # Reload affected feeds
        if feeds_to_reload:
            await self._reload_feeds(feeds_to_reload)

    async def _handle_feed_created(self, change: ConfigurationChange):
        """Handle new feed creation"""
        if not change.feed_id:
            return

        with Session(engine) as session:
            feed = session.get(Feed, change.feed_id)
            if feed and feed.status == FeedStatus.ACTIVE:
                scheduled_feed = ScheduledFeed(
                    feed_id=feed.id,
                    url=feed.url,
                    title=feed.title or f"Feed {feed.id}",
                    interval_minutes=feed.fetch_interval_minutes,
                    next_fetch=datetime.utcnow(),  # Schedule immediate fetch for new feeds
                    status=feed.status
                )

                self.scheduled_feeds[feed.id] = scheduled_feed
                logger.info(f"Added new feed to schedule: {feed.title} (ID: {feed.id})")

    async def _handle_feed_updated(self, change: ConfigurationChange):
        """Handle feed configuration updates"""
        if not change.feed_id:
            return

        with Session(engine) as session:
            feed = session.get(Feed, change.feed_id)
            if not feed:
                # Feed was deleted
                if change.feed_id in self.scheduled_feeds:
                    del self.scheduled_feeds[change.feed_id]
                    logger.info(f"Removed deleted feed from schedule: {change.feed_id}")
                return

            if feed.id in self.scheduled_feeds:
                scheduled_feed = self.scheduled_feeds[feed.id]

                # Update configuration
                old_interval = scheduled_feed.interval_minutes
                scheduled_feed.url = feed.url
                scheduled_feed.title = feed.title or f"Feed {feed.id}"
                scheduled_feed.interval_minutes = feed.fetch_interval_minutes
                scheduled_feed.status = feed.status

                # Reschedule if interval changed
                if old_interval != feed.fetch_interval_minutes:
                    scheduled_feed.next_fetch = self._calculate_next_fetch(
                        feed.last_fetched, feed.fetch_interval_minutes
                    )
                    logger.info(f"Updated feed schedule: {feed.title} "
                               f"(interval: {old_interval} -> {feed.fetch_interval_minutes} minutes)")

                # Remove from schedule if deactivated
                if feed.status != FeedStatus.ACTIVE:
                    del self.scheduled_feeds[feed.id]
                    logger.info(f"Removed inactive feed from schedule: {feed.title}")

            elif feed.status == FeedStatus.ACTIVE:
                # Feed was reactivated, add back to schedule
                await self._handle_feed_created(change)

    async def _handle_feed_deleted(self, change: ConfigurationChange):
        """Handle feed deletion"""
        if change.feed_id and change.feed_id in self.scheduled_feeds:
            feed_title = self.scheduled_feeds[change.feed_id].title
            del self.scheduled_feeds[change.feed_id]
            logger.info(f"Removed deleted feed from schedule: {feed_title} (ID: {change.feed_id})")

    async def _handle_template_changes(self, change: ConfigurationChange):
        """Handle template-related changes"""
        # Template changes are handled by reloading affected feeds
        # The actual reloading happens in _apply_configuration_changes
        logger.debug(f"Template change detected: {change.change_type}")

    async def _reload_feeds(self, feed_ids: Set[int]):
        """Reload specific feeds from database"""
        with Session(engine) as session:
            for feed_id in feed_ids:
                feed = session.get(Feed, feed_id)
                if feed and feed_id in self.scheduled_feeds:
                    scheduled_feed = self.scheduled_feeds[feed_id]
                    scheduled_feed.url = feed.url
                    scheduled_feed.title = feed.title or f"Feed {feed.id}"
                    scheduled_feed.interval_minutes = feed.fetch_interval_minutes
                    scheduled_feed.status = feed.status

                    logger.debug(f"Reloaded feed configuration: {feed.title}")

    async def _process_scheduled_feeds(self):
        """Process feeds that are due for fetching"""
        current_time = datetime.utcnow()
        feeds_to_fetch = []

        # Find feeds due for fetching
        for feed_id, scheduled_feed in self.scheduled_feeds.items():
            if (not scheduled_feed.is_running and
                scheduled_feed.status == FeedStatus.ACTIVE and
                current_time >= scheduled_feed.next_fetch):
                feeds_to_fetch.append(scheduled_feed)

        # Process feeds concurrently (but limit concurrency)
        if feeds_to_fetch:
            logger.debug(f"Processing {len(feeds_to_fetch)} feeds due for fetching")

            # Process in batches to avoid overwhelming the system
            batch_size = 5
            for i in range(0, len(feeds_to_fetch), batch_size):
                batch = feeds_to_fetch[i:i + batch_size]
                tasks = [self._fetch_feed(scheduled_feed) for scheduled_feed in batch]
                await asyncio.gather(*tasks, return_exceptions=True)

    async def _fetch_feed(self, scheduled_feed: ScheduledFeed):
        """Fetch a single feed"""
        scheduled_feed.is_running = True
        current_time = datetime.utcnow()  # Define current_time

        try:
            # Load feed from database to get latest configuration
            with Session(engine) as session:
                feed = session.get(Feed, scheduled_feed.feed_id)
                if not feed:
                    logger.warning(f"Feed {scheduled_feed.feed_id} not found in database")
                    return

                logger.info(f"Fetching feed: {scheduled_feed.title}")

                # Perform the fetch
                fetch_log = await self.fetcher.fetch_feed(feed)

                # Extract status before session closes
                fetch_status = fetch_log.status if fetch_log else "error"
                fetch_success = fetch_status == "success"

            # Update scheduling based on result (outside session)
            if fetch_success:
                scheduled_feed.consecutive_failures = 0
                # Schedule next fetch based on configured interval
                scheduled_feed.next_fetch = current_time + timedelta(
                    minutes=scheduled_feed.interval_minutes
                )
                logger.debug(f"Scheduled next fetch for {scheduled_feed.title} "
                            f"at {scheduled_feed.next_fetch}")
            else:
                # Handle failures with exponential backoff
                scheduled_feed.consecutive_failures += 1
                backoff_minutes = min(
                    scheduled_feed.interval_minutes * (2 ** scheduled_feed.consecutive_failures),
                    240  # Max 4 hours
                )
                scheduled_feed.next_fetch = current_time + timedelta(minutes=backoff_minutes)
                logger.warning(f"Feed fetch failed: {scheduled_feed.title} "
                              f"(failures: {scheduled_feed.consecutive_failures}, "
                              f"next try in {backoff_minutes} minutes)")

        except Exception as e:
            logger.error(f"Error fetching feed {scheduled_feed.title}: {e}")
            scheduled_feed.consecutive_failures += 1
            # Schedule retry with backoff
            backoff_minutes = min(
                scheduled_feed.interval_minutes * (2 ** scheduled_feed.consecutive_failures),
                240  # Max 4 hours
            )
            scheduled_feed.next_fetch = current_time + timedelta(minutes=backoff_minutes)

        finally:
            scheduled_feed.is_running = False

    async def _update_heartbeat(self):
        """Update scheduler heartbeat in database"""
        try:
            with get_configuration_watcher(scheduler_instance=self.instance_id) as watcher:
                # This updates the heartbeat automatically
                pass
        except Exception as e:
            logger.debug(f"Error updating heartbeat: {e}")

    def _calculate_next_fetch(self, last_fetched: Optional[datetime],
                            interval_minutes: int) -> datetime:
        """Calculate next fetch time for a feed"""
        if last_fetched:
            return last_fetched + timedelta(minutes=interval_minutes)
        else:
            # For feeds never fetched, schedule immediately
            return datetime.utcnow()

    async def _cleanup(self):
        """Cleanup resources"""
        logger.info("Cleaning up scheduler resources...")

        if self.fetcher:
            await self.fetcher.close()

    def get_status(self) -> Dict[str, any]:
        """Get scheduler status for monitoring"""
        current_time = datetime.utcnow()

        active_feeds = len([f for f in self.scheduled_feeds.values()
                           if f.status == FeedStatus.ACTIVE])
        running_feeds = len([f for f in self.scheduled_feeds.values()
                            if f.is_running])
        overdue_feeds = len([f for f in self.scheduled_feeds.values()
                            if current_time > f.next_fetch and not f.is_running])

        next_fetch_times = [f.next_fetch for f in self.scheduled_feeds.values()
                           if not f.is_running and f.status == FeedStatus.ACTIVE]
        next_fetch = min(next_fetch_times) if next_fetch_times else None

        return {
            'instance_id': self.instance_id,
            'running': self.running,
            'total_feeds': len(self.scheduled_feeds),
            'active_feeds': active_feeds,
            'currently_fetching': running_feeds,
            'overdue_feeds': overdue_feeds,
            'next_fetch': next_fetch.isoformat() if next_fetch else None,
            'config_check_interval': self.config_check_interval
        }


async def main():
    """Main entry point for the dynamic scheduler"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    scheduler = DynamicScheduler()

    try:
        await scheduler.start()
    except KeyboardInterrupt:
        logger.info("Scheduler interrupted by user")
    except Exception as e:
        logger.error(f"Scheduler failed: {e}")
        sys.exit(1)
    finally:
        await scheduler.stop()


if __name__ == "__main__":
    asyncio.run(main())