"""
Auto-Scraping Service with Error Tracking and Auto-Disable
Integrates into sentiment analysis workflow for controlled scraping
"""
from datetime import datetime
from sqlmodel import Session, select, func
from app.core.logging_config import get_logger
from app.models.core import Feed, Item
from app.services.scraper_service import ScraperService

logger = get_logger(__name__)

# Configuration
MAX_SCRAPE_ERRORS_BEFORE_DISABLE = 10  # Auto-disable after 10 consecutive errors
ERROR_RESET_SUCCESS_COUNT = 3  # Reset error count after 3 successful scrapes


class AutoScraperService:
    """
    Controlled auto-scraping with error tracking and safety mechanisms

    Features:
    - Only scrapes items that haven't been scraped yet (scrape_status IS NULL)
    - Tracks errors per feed
    - Auto-disables scraping after MAX_SCRAPE_ERRORS_BEFORE_DISABLE consecutive errors
    - Resets error count after ERROR_RESET_SUCCESS_COUNT successful scrapes
    - Integrates seamlessly into sentiment analysis workflow
    """

    def __init__(self, session: Session):
        self.session = session
        self.scraper = ScraperService()

    async def scrape_for_analysis(self, item: Item, feed: Feed) -> bool:
        """
        Scrape article content for an item during analysis workflow

        Args:
            item: Item to scrape
            feed: Feed configuration (checked for scrape_full_content)

        Returns:
            True if scraping succeeded or wasn't needed, False if failed
        """
        # Check if feed has scraping enabled
        if not feed.scrape_full_content:
            return True  # Not an error, just not enabled

        # Check if feed was auto-disabled
        if feed.scrape_auto_disabled_at:
            logger.warning(
                f"Scraping disabled for feed {feed.id} ({feed.title}) "
                f"since {feed.scrape_auto_disabled_at}"
            )
            return True  # Don't fail analysis because of disabled scraping

        # Check if item was already scraped
        if item.scrape_status is not None:
            logger.debug(f"Item {item.id} already scraped (status: {item.scrape_status})")
            return True

        # Scrape the article
        try:
            result = await self.scraper.scrape_article(
                url=item.link,
                extract_images=False,  # Don't extract images in auto-mode
                extract_metadata=True
            )

            # Update item with scrape results
            item.scraped_at = result["scraped_at"]
            item.scrape_status = result["scrape_status"]
            item.scrape_word_count = result.get("word_count", 0)

            if result["success"]:
                # Update item content with scraped text
                item.content = result["content"]

                # Reset or decrement error count on success
                await self._handle_scrape_success(feed)

                logger.info(
                    f"Scraped article {item.id} for feed {feed.id}: "
                    f"{result['word_count']} words"
                )
                return True
            else:
                # Handle scrape error
                await self._handle_scrape_error(
                    feed,
                    f"{result['scrape_status']}: {result.get('error', 'Unknown error')}"
                )

                logger.warning(
                    f"Scrape failed for article {item.id} (feed {feed.id}): "
                    f"{result.get('error', 'Unknown error')}"
                )
                return False

        except Exception as e:
            # Handle unexpected errors
            await self._handle_scrape_error(feed, str(e))

            # Update item with error status
            item.scraped_at = datetime.now()
            item.scrape_status = "error"

            logger.error(f"Scrape exception for article {item.id} (feed {feed.id}): {e}")
            return False

    async def _handle_scrape_success(self, feed: Feed):
        """Handle successful scrape - reset or decrement error count"""
        if feed.scrape_error_count > 0:
            # Decrement error count
            feed.scrape_error_count = max(0, feed.scrape_error_count - 1)

            # If error count reaches 0, clear error info
            if feed.scrape_error_count == 0:
                feed.scrape_last_error = None
                feed.scrape_last_error_at = None
                logger.info(
                    f"Feed {feed.id} scrape errors reset after successful scrape"
                )

        self.session.commit()

    async def _handle_scrape_error(self, feed: Feed, error_message: str):
        """Handle scrape error - increment count and check for auto-disable"""
        feed.scrape_error_count += 1
        feed.scrape_last_error = error_message[:500]  # Limit error message length
        feed.scrape_last_error_at = datetime.now()

        # Check if we should auto-disable
        if feed.scrape_error_count >= MAX_SCRAPE_ERRORS_BEFORE_DISABLE:
            feed.scrape_auto_disabled_at = datetime.now()
            logger.error(
                f"Auto-disabled scraping for feed {feed.id} ({feed.title}) "
                f"after {feed.scrape_error_count} consecutive errors. "
                f"Last error: {error_message}"
            )
        else:
            logger.warning(
                f"Scrape error {feed.scrape_error_count}/{MAX_SCRAPE_ERRORS_BEFORE_DISABLE} "
                f"for feed {feed.id}: {error_message}"
            )

        self.session.commit()

    def get_scraping_stats(self, feed_id: int) -> dict:
        """Get scraping statistics for a feed"""
        feed = self.session.get(Feed, feed_id)
        if not feed:
            return {}

        # Count items by scrape status
        stmt = (
            select(Item.scrape_status, func.count(Item.id))
            .where(Item.feed_id == feed_id)
            .group_by(Item.scrape_status)
        )
        status_counts = dict(self.session.exec(stmt).all())

        return {
            "enabled": feed.scrape_full_content,
            "auto_disabled": feed.scrape_auto_disabled_at is not None,
            "auto_disabled_at": feed.scrape_auto_disabled_at,
            "error_count": feed.scrape_error_count,
            "last_error": feed.scrape_last_error,
            "last_error_at": feed.scrape_last_error_at,
            "items_scraped_success": status_counts.get("success", 0),
            "items_scraped_paywall": status_counts.get("paywall", 0),
            "items_scraped_error": status_counts.get("error", 0),
            "items_scraped_timeout": status_counts.get("timeout", 0),
            "items_not_scraped": status_counts.get(None, 0)
        }

    def re_enable_scraping(self, feed_id: int) -> bool:
        """Manually re-enable scraping for a feed (resets error tracking)"""
        feed = self.session.get(Feed, feed_id)
        if not feed:
            return False

        feed.scrape_error_count = 0
        feed.scrape_last_error = None
        feed.scrape_last_error_at = None
        feed.scrape_auto_disabled_at = None

        self.session.commit()

        logger.info(f"Manually re-enabled scraping for feed {feed.id} ({feed.title})")
        return True
