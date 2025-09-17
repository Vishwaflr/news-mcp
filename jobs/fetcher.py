import feedparser
import httpx
import hashlib
import logging
from datetime import datetime, timedelta
from typing import Optional, List
from sqlmodel import Session, select
from app.database import engine
from app.models import Feed, Item, FetchLog, FeedHealth, FeedStatus
from app.config import settings
from app.processors.manager import ContentProcessingManager
from app.services.dynamic_template_manager import get_dynamic_template_manager

logger = logging.getLogger(__name__)

class FeedFetcher:
    def __init__(self):
        self.client = httpx.AsyncClient(
            timeout=30.0,
            follow_redirects=True,
            headers={
                "User-Agent": "News-MCP/1.0 (+https://github.com/news-mcp)"
            }
        )

    async def fetch_feed(self, feed: Feed) -> FetchLog:
        log = FetchLog(
            feed_id=feed.id,
            started_at=datetime.utcnow(),
            status="running"
        )

        with Session(engine) as session:
            session.add(log)
            session.commit()
            session.refresh(log)

        try:
            start_time = datetime.utcnow()

            headers = {}
            if feed.last_modified:
                headers["If-Modified-Since"] = feed.last_modified
            if feed.etag:
                headers["If-None-Match"] = feed.etag

            response = await self.client.get(feed.url, headers=headers)
            response_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)

            if response.status_code == 304:
                log.completed_at = datetime.utcnow()
                log.status = "not_modified"
                log.response_time_ms = response_time

                with Session(engine) as session:
                    session.add(log)
                    session.commit()

                await self._update_health(feed.id, True, response_time)
                return log

            response.raise_for_status()

            parsed = feedparser.parse(response.content)

            if hasattr(parsed, 'status') and parsed.status >= 400:
                raise Exception(f"Feed parse error: {parsed.get('bozo_exception', 'Unknown error')}")

            items_found = len(parsed.entries)
            items_new = 0

            with Session(engine) as session:
                feed_db = session.get(Feed, feed.id)

                if "last-modified" in response.headers:
                    feed_db.last_modified = response.headers["last-modified"]
                if "etag" in response.headers:
                    feed_db.etag = response.headers["etag"]

                feed_db.last_fetched = datetime.utcnow()
                feed_db.title = feed_db.title or parsed.feed.get("title", "")
                feed_db.description = feed_db.description or parsed.feed.get("description", "")
                feed_db.status = FeedStatus.ACTIVE

                # Initialize content processor and get dynamic template
                content_manager = ContentProcessingManager(session)

                # Get dynamic template for this feed
                with get_dynamic_template_manager(session) as template_manager:
                    template = template_manager.get_template_for_feed(feed_db.id)

                # Process each entry individually with isolated transactions
                for entry in parsed.entries:
                    try:
                        # Use template-based field mapping instead of hardcoded extraction
                        raw_item = self._extract_fields_with_template(entry, template)

                        # Apply template content processing
                        if template:
                            raw_item = self._apply_template_processing(raw_item, template)
                            if raw_item is None:  # Item failed quality filters
                                continue

                        # Process through content processing pipeline
                        processed_item = content_manager.process_item(raw_item, feed_db)

                        if processed_item:
                            # Extract item data to decouple from session
                            item_data = processed_item.model_dump()

                            # Ensure feed_id is set correctly (not relying on ORM relationship)
                            item_data['feed_id'] = feed_db.id

                            # Extract processing metadata if available
                            processing_metadata = getattr(processed_item, '_processing_metadata', None)

                            # Process this item in an isolated transaction
                            if self._save_item_isolated(item_data, processing_metadata):
                                items_new += 1

                    except Exception as e:
                        # Log individual item processing errors but continue with other items
                        logger.warning(f"Error processing entry '{entry.get('title', 'Unknown')[:50]}...': {e}")
                        continue

                # Update feed and log after all items are processed
                log.completed_at = datetime.utcnow()
                log.status = "success"
                log.items_found = items_found
                log.items_new = items_new
                log.response_time_ms = response_time

                # Ensure feed status is set to ACTIVE on successful fetch
                feed_db.status = FeedStatus.ACTIVE

                # Final commit for feed and log updates
                try:
                    session.add(feed_db)
                    session.add(log)
                    session.commit()
                except Exception as e:
                    logger.warning(f"Error updating feed metadata: {e}")
                    session.rollback()

            await self._update_health(feed.id, True, response_time)
            logger.info(f"Feed {feed.id} fetched successfully: {items_new}/{items_found} new items")

        except Exception as e:
            error_msg = str(e)

            # Don't treat SQLAlchemy session errors as feed failures if items were processed
            if "DetachedInstanceError" in error_msg and items_new > 0:
                logger.warning(f"Session error after successful processing of {items_new} items in feed {feed.id}: {error_msg}")

                # Mark as successful since items were processed
                log.completed_at = datetime.utcnow()
                log.status = "success"
                log.items_found = items_found
                log.items_new = items_new

                with Session(engine) as session:
                    feed_db = session.get(Feed, feed.id)
                    feed_db.status = FeedStatus.ACTIVE
                    feed_db.last_fetched = datetime.utcnow()
                    session.add(feed_db)
                    session.add(log)
                    session.commit()

                await self._update_health(feed.id, True, response_time if 'response_time' in locals() else None)
                logger.info(f"Feed {feed.id} completed successfully despite session error: {items_new}/{items_found} new items")
            else:
                # Real errors
                logger.error(f"Error fetching feed {feed.id}: {error_msg}")

                log.completed_at = datetime.utcnow()
                log.status = "error"
                log.error_message = error_msg
                log.items_found = items_found if 'items_found' in locals() else 0
                log.items_new = items_new if 'items_new' in locals() else 0

                with Session(engine) as session:
                    feed_db = session.get(Feed, feed.id)
                    feed_db.status = FeedStatus.ERROR
                    feed_db.last_fetched = datetime.utcnow()
                    session.add(feed_db)
                    session.add(log)
                    session.commit()

                await self._update_health(feed.id, False, response_time if 'response_time' in locals() else None)

        return log

    def _generate_content_hash(self, entry) -> str:
        content = f"{entry.get('title', '')}{entry.get('link', '')}{entry.get('summary', '')}"
        return hashlib.sha256(content.encode()).hexdigest()

    def _extract_fields_with_template(self, entry, template) -> dict:
        """Extract fields from RSS entry using dynamic template mappings."""
        if not template:
            # Fallback to default extraction
            return {
                'title': entry.get('title'),
                'description': entry.get('summary'),
                'content': entry.get('content'),
                'author': entry.get('author'),
                'link': entry.get('link'),
                'published_parsed': entry.get('published_parsed'),
                'id': entry.get('id'),
                'guid': entry.get('guid')
            }

        # Use dynamic template field mappings
        raw_item = {}
        field_mappings = template.field_mapping_dict

        for db_field, rss_path in field_mappings.items():
            try:
                # Strip 'entry.' prefix if present since we already have the entry object
                path = rss_path.replace('entry.', '') if rss_path.startswith('entry.') else rss_path

                # Simple field extraction from RSS entry
                value = entry.get(path) if hasattr(entry, 'get') else getattr(entry, path, None)
                raw_item[db_field] = value
            except Exception as e:
                logger.warning(f"Error mapping field {db_field} with path {rss_path}: {e}")
                raw_item[db_field] = None

        return raw_item

    def _apply_template_processing(self, raw_item: dict, template) -> dict:
        """Apply dynamic template-specific content processing rules."""
        processed_item = raw_item.copy()

        # Apply content processing rules from dynamic template
        content = processed_item.get('description', '') or processed_item.get('content', '')
        if content and template.content_rules_list:
            for rule in template.content_rules_list:
                if rule.get('type') == 'html_extract':
                    # Strip HTML tags (basic implementation)
                    import re
                    content = re.sub(r'<[^>]+>', '', content)
                    max_length = rule.get('max_length', 2000)
                    content = content[:max_length] if content else ''
                elif rule.get('type') == 'text_normalize':
                    # Apply text normalization
                    if 'fix_german_umlauts' in rule.get('rules', []):
                        content = content.replace('Ã¤', 'ä').replace('Ã¶', 'ö').replace('Ã¼', 'ü')
                    if 'normalize_quotes' in rule.get('rules', []):
                        content = content.replace('"', '"').replace('"', '"').replace(''', "'").replace(''', "'")
                elif rule.get('type') == 'remove_tracking':
                    # Remove tracking parameters from URLs (basic implementation)
                    import re
                    content = re.sub(r'\?utm_[^&\s]+', '', content)
                    content = re.sub(r'&utm_[^&\s]+', '', content)

        # Update processed item with cleaned content
        if processed_item.get('description'):
            processed_item['description'] = content
        if processed_item.get('content'):
            processed_item['content'] = content

        # Apply basic quality filters from template's field mappings
        title = processed_item.get('title', '')
        quality_filters = template.field_mapping_dict.get('quality_filters', {})

        if quality_filters:
            min_title_length = quality_filters.get('min_title_length', 0)
            max_title_length = quality_filters.get('max_title_length', 1000)

            if title and (len(title) < min_title_length or len(title) > max_title_length):
                logger.debug(f"Item failed title length quality filters: {title[:50]}...")
                return None

        return processed_item

    async def _update_health(self, feed_id: int, success: bool, response_time_ms: Optional[int]):
        with Session(engine) as session:
            health = session.exec(
                select(FeedHealth).where(FeedHealth.feed_id == feed_id)
            ).first()

            if not health:
                health = FeedHealth(
                    feed_id=feed_id,
                    ok_ratio=1.0 if success else 0.0,
                    consecutive_failures=0 if success else 1,
                    avg_response_time_ms=response_time_ms,
                    last_success=datetime.utcnow() if success else None,
                    last_failure=None if success else datetime.utcnow()
                )
            else:
                if success:
                    health.consecutive_failures = 0
                    health.last_success = datetime.utcnow()
                    if response_time_ms:
                        if health.avg_response_time_ms:
                            health.avg_response_time_ms = (health.avg_response_time_ms + response_time_ms) / 2
                        else:
                            health.avg_response_time_ms = response_time_ms
                else:
                    health.consecutive_failures += 1
                    health.last_failure = datetime.utcnow()

                recent_logs = session.exec(
                    select(FetchLog)
                    .where(FetchLog.feed_id == feed_id)
                    .where(FetchLog.started_at >= datetime.utcnow() - timedelta(hours=24))
                    .order_by(FetchLog.started_at.desc())
                    .limit(100)
                ).all()

                if recent_logs:
                    successful = len([log for log in recent_logs if log.status == "success"])
                    health.uptime_24h = successful / len(recent_logs)

                week_logs = session.exec(
                    select(FetchLog)
                    .where(FetchLog.feed_id == feed_id)
                    .where(FetchLog.started_at >= datetime.utcnow() - timedelta(days=7))
                    .order_by(FetchLog.started_at.desc())
                ).all()

                if week_logs:
                    successful = len([log for log in week_logs if log.status == "success"])
                    health.uptime_7d = successful / len(week_logs)

                health.updated_at = datetime.utcnow()

            session.add(health)
            session.commit()

    def _save_item_isolated(self, item_data: dict, processing_metadata: dict = None) -> bool:
        """
        Save an item in an isolated transaction using the get_session context manager.

        Args:
            item_data: Dictionary containing item data from model_dump()
            processing_metadata: Optional processing metadata for logging

        Returns:
            bool: True if item was saved successfully, False if skipped (duplicate/error)
        """
        from app.database import get_session
        from sqlalchemy.exc import IntegrityError
        from app.models import ContentProcessingLog, ProcessorType, ProcessingStatus

        try:
            # Use get_session context manager for isolated transaction
            with next(get_session()) as session:
                # Check for duplicates first
                existing = session.exec(
                    select(Item).where(Item.content_hash == item_data.get('content_hash'))
                ).first()

                if existing:
                    logger.debug(f"Skipping existing item: {item_data.get('title', 'Unknown')[:50]}...")
                    return False

                # Create fresh Item object from data dictionary
                new_item = Item(**item_data)

                # Add and commit the item first to get an ID
                session.add(new_item)
                session.flush()  # Get the ID without committing

                # Create processing log if metadata is available
                if processing_metadata:
                    try:
                        # Determine processor type from name
                        processor_name = processing_metadata.get('processor_name', '')
                        processor_type = ProcessorType.UNIVERSAL
                        if "Heise" in processor_name:
                            processor_type = ProcessorType.HEISE
                        elif "Cointelegraph" in processor_name:
                            processor_type = ProcessorType.COINTELEGRAPH

                        # Get processing data
                        content_item = processing_metadata.get('content_item')
                        processed = processing_metadata.get('processed')
                        validation_result = processing_metadata.get('validation_result', {})

                        # Include validation information in transformations
                        transformations = processed.transformations.copy() if processed and processed.transformations else []
                        if validation_result.get("warnings"):
                            transformations.extend([f"validation_warning: {w}" for w in validation_result["warnings"][:3]])
                        if validation_result.get("quality_adjustments"):
                            adjustments = list(validation_result["quality_adjustments"].keys())[:3]
                            transformations.extend([f"quality_adjustment: {adj}" for adj in adjustments])

                        log_entry = ContentProcessingLog(
                            item_id=new_item.id,
                            feed_id=item_data.get('feed_id'),
                            processor_type=processor_type,
                            processing_status=processing_metadata.get('processing_status', ProcessingStatus.SUCCESS),
                            original_title=content_item.title if content_item else None,
                            processed_title=processed.title if processed else None,
                            original_description=content_item.description if content_item else None,
                            processed_description=processed.description if processed else None,
                            transformations=transformations,
                            error_message=processing_metadata.get('error_message'),
                            processing_time_ms=processing_metadata.get('processing_time', 0)
                        )

                        session.add(log_entry)
                    except Exception as log_error:
                        # Don't fail item saving due to logging issues
                        logger.warning(f"Failed to create processing log: {log_error}")

                # Commit everything together
                session.commit()

                logger.debug(f"Successfully saved item: {item_data.get('title', 'Unknown')[:50]}...")
                return True

        except IntegrityError as e:
            # Handle duplicate key constraints gracefully
            logger.debug(f"Skipping duplicate item (race condition): {item_data.get('title', 'Unknown')[:50]}...")
            return False

        except Exception as e:
            # Log other unexpected errors but don't break the feed processing
            logger.error(f"Unexpected error saving item '{item_data.get('title', 'Unknown')[:50]}...': {e}")
            return False

    async def close(self):
        await self.client.aclose()