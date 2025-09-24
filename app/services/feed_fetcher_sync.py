"""
Synchronous feed fetcher for immediate article loading when creating new feeds.
This runs in the same process/thread to ensure it actually executes.
"""
import feedparser
import httpx
import hashlib
from app.core.logging_config import get_logger
from datetime import datetime
from sqlmodel import Session, select
from app.models import Feed, Item, FetchLog, FeedHealth, FeedStatus
from app.processors.manager import ContentProcessingManager
from app.services.dynamic_template_manager import get_dynamic_template_manager

logger = get_logger(__name__)

class SyncFeedFetcher:
    """Synchronous version of FeedFetcher for immediate fetch operations"""

    def fetch_feed_sync(self, feed_id: int) -> tuple[bool, int]:
        """
        Synchronously fetch a feed and return success status and item count.

        Args:
            feed_id: The ID of the feed to fetch

        Returns:
            Tuple of (success: bool, items_count: int)
        """
        try:
            from app.database import engine

            # Get feed from database
            with Session(engine) as session:
                feed = session.get(Feed, feed_id)
                if not feed:
                    logger.error(f"Feed {feed_id} not found")
                    return False, 0

                feed_url = feed.url

            logger.info(f"Starting synchronous fetch for feed {feed_id}: {feed_url}")

            # Create log entry
            log_id = None
            with Session(engine) as session:
                log = FetchLog(
                    feed_id=feed_id,
                    started_at=datetime.utcnow(),
                    status="running"
                )
                session.add(log)
                session.commit()
                session.refresh(log)
                log_id = log.id

            # Fetch the feed
            with httpx.Client(timeout=30.0, follow_redirects=True) as client:
                response = client.get(
                    feed_url,
                    headers={"User-Agent": "News-MCP/1.0 (+https://github.com/news-mcp)"}
                )
                response.raise_for_status()

            # Parse the feed
            parsed = feedparser.parse(response.content)

            if hasattr(parsed, 'status') and parsed.status >= 400:
                raise Exception(f"Feed parse error: {parsed.get('bozo_exception', 'Unknown error')}")

            items_found = len(parsed.entries)
            items_new = 0

            # Process entries
            with Session(engine) as session:
                feed_db = session.get(Feed, feed_id)
                if not feed_db:
                    logger.error(f"Feed {feed_id} disappeared during processing")
                    return False, 0

                # Update feed metadata
                feed_db.last_fetched = datetime.utcnow()
                feed_db.title = feed_db.title or parsed.feed.get("title", "")
                feed_db.description = feed_db.description or parsed.feed.get("description", "")
                feed_db.status = FeedStatus.ACTIVE

                # Initialize content processor
                content_manager = ContentProcessingManager(session)

                # Get template for this feed
                with get_dynamic_template_manager(session) as template_manager:
                    template = template_manager.get_template_for_feed(feed_db.id)

                # Track new item IDs for auto-analysis
                new_item_ids = []

                # Process each entry
                for entry in parsed.entries[:50]:  # Limit to first 50 items for initial fetch
                    try:
                        # Generate content hash
                        content_hash = hashlib.sha256(
                            f"{entry.get('title', '')}{entry.get('link', '')}{entry.get('summary', '')}".encode()
                        ).hexdigest()

                        # Check for duplicates
                        existing = session.exec(
                            select(Item).where(Item.content_hash == content_hash)
                        ).first()

                        if existing:
                            continue

                        # Create new item
                        item = Item(
                            feed_id=feed_db.id,
                            title=entry.get('title', 'Untitled'),
                            description=entry.get('summary', ''),
                            link=entry.get('link', ''),
                            author=entry.get('author'),
                            content_hash=content_hash
                        )

                        # Set published date
                        if hasattr(entry, 'published_parsed') and entry.published_parsed:
                            import time
                            item.published = datetime.fromtimestamp(time.mktime(entry.published_parsed))
                        else:
                            item.published = datetime.utcnow()

                        session.add(item)
                        items_new += 1

                    except Exception as e:
                        logger.warning(f"Error processing entry: {e}")
                        continue

                # Commit all changes to get item IDs
                session.commit()

                # Get IDs of newly created items for auto-analysis
                if items_new > 0:
                    # Query for items created in this session
                    recent_items = session.exec(
                        select(Item).where(
                            Item.feed_id == feed_db.id,
                            Item.created_at >= datetime.utcnow().replace(microsecond=0)  # Items from this second
                        ).order_by(Item.id.desc()).limit(items_new)
                    ).all()
                    new_item_ids = [item.id for item in recent_items]

                logger.info(f"Feed {feed_id} processed: {items_new}/{items_found} new items")

            # Trigger auto-analysis if enabled and new items exist
            if new_item_ids and items_new > 0:
                try:
                    import asyncio
                    from app.services.auto_analysis_service import AutoAnalysisService
                    auto_analysis = AutoAnalysisService()
                    # Run async function in sync context
                    result = asyncio.run(auto_analysis.trigger_feed_auto_analysis(feed_id, new_item_ids))
                    if result:
                        logger.info(f"Triggered auto-analysis run {result['run_id']} for feed {feed_id} with {result['items_count']} items")
                except Exception as e:
                    logger.error(f"Failed to trigger auto-analysis for feed {feed_id}: {e}")

            # Update log
            with Session(engine) as log_session:
                log = log_session.get(FetchLog, log_id)
                if log:
                    log.completed_at = datetime.utcnow()
                    log.status = "success"
                    log.items_found = items_found
                    log.items_new = items_new
                    log_session.commit()

            # Update health
            self._update_health_sync(feed_id, True)

            return True, items_new

        except Exception as e:
            logger.error(f"Error in synchronous fetch for feed {feed_id}: {e}")

            # Update feed status
            try:
                from app.database import engine
                with Session(engine) as session:
                    feed_db = session.get(Feed, feed_id)
                    if feed_db:
                        feed_db.status = FeedStatus.ERROR
                        feed_db.last_fetched = datetime.utcnow()
                        session.commit()

                # Update log if exists
                if 'log_id' in locals() and log_id:
                    with Session(engine) as log_session:
                        log = log_session.get(FetchLog, log_id)
                        if log:
                            log.completed_at = datetime.utcnow()
                            log.status = "error"
                            log.error_message = str(e)[:500]
                            log_session.commit()

            except Exception as update_error:
                logger.error(f"Error updating status after failure: {update_error}")

            self._update_health_sync(feed_id, False)
            return False, 0

    def _update_health_sync(self, feed_id: int, success: bool):
        """Update feed health synchronously"""
        try:
            from app.database import engine
            with Session(engine) as session:
                health = session.exec(
                    select(FeedHealth).where(FeedHealth.feed_id == feed_id)
                ).first()

                if not health:
                    health = FeedHealth(
                        feed_id=feed_id,
                        consecutive_failures=0 if success else 1,
                        last_success=datetime.utcnow() if success else None,
                        last_failure=None if success else datetime.utcnow()
                    )
                else:
                    if success:
                        health.consecutive_failures = 0
                        health.last_success = datetime.utcnow()
                    else:
                        health.consecutive_failures += 1
                        health.last_failure = datetime.utcnow()

                    health.updated_at = datetime.utcnow()

                session.add(health)
                session.commit()

        except Exception as e:
            logger.error(f"Error updating health: {e}")