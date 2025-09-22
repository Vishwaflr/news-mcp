import feedparser
import httpx
import hashlib
import logging
from datetime import datetime, timedelta
from typing import Optional, List
from sqlmodel import Session, select
from app.database import engine
from app.models import FeedStatus, FeedHealth, Feed, Item, FetchLog
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
        # Create initial log entry using raw SQL
        log_id = None
        with Session(engine) as session:
            from sqlmodel import text
            result = session.execute(
                text("""
                    INSERT INTO fetch_log (feed_id, started_at, status, items_found, items_new)
                    VALUES (:feed_id, :started_at, :status, 0, 0)
                    RETURNING id
                """),
                {
                    "feed_id": feed.id,
                    "started_at": datetime.utcnow(),
                    "status": "running"
                }
            )
            log_id = result.fetchone()[0]
            session.commit()

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
                with Session(engine) as session:
                    from sqlmodel import text
                    session.execute(
                        text("""
                            UPDATE fetch_log
                            SET completed_at = :completed_at, status = :status, response_time_ms = :response_time
                            WHERE id = :log_id
                        """),
                        {
                            "completed_at": datetime.utcnow(),
                            "status": "not_modified",
                            "response_time": response_time,
                            "log_id": log_id
                        }
                    )
                    session.commit()

                await self._update_health(feed.id, True, response_time)
                # Return a log object for compatibility
                log = FetchLog(
                    id=log_id,
                    feed_id=feed.id,
                    started_at=datetime.utcnow(),
                    completed_at=datetime.utcnow(),
                    status="not_modified",
                    items_found=0,
                    items_new=0,
                    response_time_ms=response_time
                )
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

                # Get dynamic template for this feed (temporarily disabled due to SQLModel issues)
                # with get_dynamic_template_manager(session) as template_manager:
                #     template = template_manager.get_template_for_feed(feed_db.id)
                template = None

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

                # Update feed metadata
                feed_db.status = FeedStatus.ACTIVE
                session.add(feed_db)
                session.commit()

            # Update log in separate session to avoid detached instance issues
            with Session(engine) as log_session:
                from sqlmodel import text
                log_session.execute(
                    text("""
                        UPDATE fetch_log
                        SET completed_at = :completed_at, status = :status,
                            items_found = :items_found, items_new = :items_new,
                            response_time_ms = :response_time
                        WHERE id = :log_id
                    """),
                    {
                        "completed_at": datetime.utcnow(),
                        "status": "success",
                        "items_found": items_found,
                        "items_new": items_new,
                        "response_time": response_time,
                        "log_id": log_id
                    }
                )
                log_session.commit()

            await self._update_health(feed.id, True, response_time)
            logger.info(f"Feed {feed.id} fetched successfully: {items_new}/{items_found} new items")

        except Exception as e:
            error_msg = str(e)

            # Don't treat SQLAlchemy session errors as feed failures if items were processed
            if "DetachedInstanceError" in error_msg and items_new > 0:
                logger.warning(f"Session error after successful processing of {items_new} items in feed {feed.id}: {error_msg}")

                # Mark as successful since items were processed
                with Session(engine) as session:
                    feed_db = session.get(Feed, feed.id)
                    feed_db.status = FeedStatus.ACTIVE
                    feed_db.last_fetched = datetime.utcnow()
                    session.add(feed_db)
                    session.commit()

                with Session(engine) as log_session:
                    from sqlmodel import text
                    log_session.execute(
                        text("""
                            UPDATE fetch_log
                            SET completed_at = :completed_at, status = :status,
                                items_found = :items_found, items_new = :items_new
                            WHERE id = :log_id
                        """),
                        {
                            "completed_at": datetime.utcnow(),
                            "status": "success",
                            "items_found": items_found,
                            "items_new": items_new,
                            "log_id": log_id
                        }
                    )
                    log_session.commit()

                await self._update_health(feed.id, True, response_time if 'response_time' in locals() else None)
                logger.info(f"Feed {feed.id} completed successfully despite session error: {items_new}/{items_found} new items")
            else:
                # Real errors
                logger.error(f"Error fetching feed {feed.id}: {error_msg}")

                with Session(engine) as session:
                    feed_db = session.get(Feed, feed.id)
                    feed_db.status = FeedStatus.ERROR
                    feed_db.last_fetched = datetime.utcnow()
                    session.add(feed_db)
                    session.commit()

                with Session(engine) as log_session:
                    from sqlmodel import text
                    log_session.execute(
                        text("""
                            UPDATE fetch_log
                            SET completed_at = :completed_at, status = :status,
                                error_message = :error_message,
                                items_found = :items_found, items_new = :items_new
                            WHERE id = :log_id
                        """),
                        {
                            "completed_at": datetime.utcnow(),
                            "status": "error",
                            "error_message": error_msg,
                            "items_found": items_found if 'items_found' in locals() else 0,
                            "items_new": items_new if 'items_new' in locals() else 0,
                            "log_id": log_id
                        }
                    )
                    log_session.commit()

                await self._update_health(feed.id, False, response_time if 'response_time' in locals() else None)

        # Return final log state using raw SQL to avoid session issues
        with Session(engine) as session:
            from sqlmodel import text
            result = session.execute(
                text("SELECT * FROM fetch_log WHERE id = :log_id"),
                {"log_id": log_id}
            ).fetchone()

            if result:
                log_copy = FetchLog(
                    id=result[0],
                    feed_id=result[1],
                    started_at=result[2],
                    completed_at=result[3],
                    status=result[4],
                    items_found=result[5],
                    items_new=result[6],
                    error_message=result[7],
                    response_time_ms=result[8]
                )
                return log_copy
            return None

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
            from sqlmodel import text

            # Check if health record exists
            health_result = session.execute(
                text("SELECT * FROM feed_health WHERE feed_id = :feed_id"),
                {"feed_id": feed_id}
            ).fetchone()

            if not health_result:
                # Create new health record
                session.execute(
                    text("""
                        INSERT INTO feed_health
                        (feed_id, ok_ratio, consecutive_failures, avg_response_time_ms,
                         last_success, last_failure, uptime_24h, uptime_7d, updated_at)
                        VALUES (:feed_id, :ok_ratio, :consecutive_failures, :avg_response_time_ms,
                                :last_success, :last_failure, 0.0, 0.0, :updated_at)
                    """),
                    {
                        "feed_id": feed_id,
                        "ok_ratio": 1.0 if success else 0.0,
                        "consecutive_failures": 0 if success else 1,
                        "avg_response_time_ms": response_time_ms,
                        "last_success": datetime.utcnow() if success else None,
                        "last_failure": None if success else datetime.utcnow(),
                        "updated_at": datetime.utcnow()
                    }
                )
            else:
                # Update existing health record
                updates = {
                    "feed_id": feed_id,
                    "updated_at": datetime.utcnow()
                }

                if success:
                    updates["consecutive_failures"] = 0
                    updates["last_success"] = datetime.utcnow()

                    if response_time_ms and health_result[4]:  # avg_response_time_ms column
                        updates["avg_response_time_ms"] = (health_result[4] + response_time_ms) / 2
                    elif response_time_ms:
                        updates["avg_response_time_ms"] = response_time_ms
                else:
                    updates["consecutive_failures"] = health_result[3] + 1  # consecutive_failures column
                    updates["last_failure"] = datetime.utcnow()

                # Calculate recent success rates
                recent_logs = session.execute(
                    text("""
                        SELECT status FROM fetch_log
                        WHERE feed_id = :feed_id AND started_at >= :cutoff_24h
                        ORDER BY started_at DESC LIMIT 100
                    """),
                    {
                        "feed_id": feed_id,
                        "cutoff_24h": datetime.utcnow() - timedelta(hours=24)
                    }
                ).fetchall()

                if recent_logs:
                    successful = len([log for log in recent_logs if log[0] == "success"])
                    updates["uptime_24h"] = successful / len(recent_logs)

                week_logs = session.execute(
                    text("""
                        SELECT status FROM fetch_log
                        WHERE feed_id = :feed_id AND started_at >= :cutoff_7d
                        ORDER BY started_at DESC
                    """),
                    {
                        "feed_id": feed_id,
                        "cutoff_7d": datetime.utcnow() - timedelta(days=7)
                    }
                ).fetchall()

                if week_logs:
                    successful = len([log for log in week_logs if log[0] == "success"])
                    updates["uptime_7d"] = successful / len(week_logs)

                # Build dynamic update query
                set_clauses = []
                for key in updates:
                    if key != "feed_id":
                        set_clauses.append(f"{key} = :{key}")

                update_query = f"UPDATE feed_health SET {', '.join(set_clauses)} WHERE feed_id = :feed_id"
                session.execute(text(update_query), updates)

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
                from sqlmodel import text

                # Check for duplicates first using raw SQL
                existing = session.execute(
                    text("SELECT id FROM items WHERE content_hash = :content_hash"),
                    {"content_hash": item_data.get('content_hash')}
                ).fetchone()

                if existing:
                    logger.debug(f"Skipping existing item: {item_data.get('title', 'Unknown')[:50]}...")
                    return False

                # Insert item using raw SQL to avoid SQLModel issues
                from sqlmodel import text
                insert_result = session.execute(
                    text("""
                        INSERT INTO items (title, link, description, content, author, published,
                                         guid, content_hash, feed_id, created_at)
                        VALUES (:title, :link, :description, :content, :author, :published,
                                :guid, :content_hash, :feed_id, :created_at)
                        RETURNING id
                    """),
                    {
                        "title": item_data.get('title'),
                        "link": item_data.get('link'),
                        "description": item_data.get('description'),
                        "content": item_data.get('content'),
                        "author": item_data.get('author'),
                        "published": item_data.get('published'),
                        "guid": item_data.get('guid'),
                        "content_hash": item_data.get('content_hash'),
                        "feed_id": item_data.get('feed_id'),
                        "created_at": datetime.utcnow()
                    }
                )
                new_item_id = insert_result.fetchone()[0]

                # Create processing log if metadata is available (temporarily disabled due to SQLModel issues)
                # if processing_metadata:
                #     try:
                #         # Processing log creation disabled
                #         pass
                #     except Exception as log_error:
                #         # Don't fail item saving due to logging issues
                #         logger.warning(f"Failed to create processing log: {log_error}")
                pass  # Processing log disabled

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