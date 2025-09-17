import logging
import time
from typing import Optional, Dict, Any
from datetime import datetime
from sqlmodel import Session

from ..models import (
    Item, Feed, ContentProcessingLog, FeedProcessorConfig,
    ProcessorType, ProcessingStatus
)
from .factory import ProcessorFactory
from .base import ContentItem, ProcessedContent
from .validator import ContentValidator, ProcessorConfigValidator

logger = logging.getLogger(__name__)

class ContentProcessingManager:
    """Manager for content processing pipeline"""

    def __init__(self, session: Session, validator_config: Dict[str, Any] = None):
        self.session = session
        self.validator = ContentValidator(validator_config)

    def process_item(self, raw_item: Dict[str, Any], feed: Feed,
                    force_reprocess: bool = False) -> Optional[Item]:
        """Process a raw RSS item and return a cleaned Item without session binding"""

        # Convert raw item to ContentItem
        content_item = self._dict_to_content_item(raw_item)

        # Get processor for this feed
        processor = ProcessorFactory.get_processor_for_feed(feed, self.session)

        # Process the content
        start_time = time.time()
        try:
            processed = processor.process_with_timing(content_item)
            processing_status = ProcessingStatus.SUCCESS
            error_message = None
        except Exception as e:
            logger.error(f"Processing failed for feed {feed.id}: {e}")
            # Fallback to minimal processing
            processed = self._fallback_processing(content_item)
            processing_status = ProcessingStatus.FAILED
            error_message = str(e)

        processing_time = int((time.time() - start_time) * 1000)

        # Validate processed content
        validation_result = self.validator.validate(processed)

        # Adjust quality score based on validation
        if processed.quality_score is not None:
            processed.quality_score = self.validator.adjust_quality_score(
                processed.quality_score, validation_result
            )

        # Log validation warnings
        if validation_result.get("warnings"):
            logger.warning(f"Content validation warnings for feed {feed.id}: {validation_result['warnings']}")

        # Skip invalid content
        if not validation_result["is_valid"]:
            logger.error(f"Content validation failed for feed {feed.id}: {validation_result['errors']}")
            return None

        # Create Item from processed content (but don't add to session)
        item = self._create_item_from_processed(processed, feed)

        # Store processing metadata for later logging if needed
        if item:
            item._processing_metadata = {
                'processor_name': processor.processor_name,
                'processing_status': processing_status,
                'content_item': content_item,
                'processed': processed,
                'error_message': error_message,
                'processing_time': processing_time,
                'validation_result': validation_result
            }

        return item

    def reprocess_item(self, item: Item) -> bool:
        """Reprocess an existing item with current processor"""
        try:
            # Get original raw content (would need to be stored)
            # For now, we'll work with what we have
            content_item = ContentItem(
                title=item.title,
                description=item.description,
                content=item.content,
                author=item.author,
                link=item.link,
                published=item.published,
                guid=item.guid
            )

            # Get processor for this feed
            from .factory import ProcessorFactory
            processor = ProcessorFactory.get_processor_for_feed(item.feed, self.session)

            # Process the content directly (don't create new item)
            import time
            start_time = time.time()
            processed = processor.process(content_item)
            processing_time = int((time.time() - start_time) * 1000)

            # Update the existing item with processed content
            item.title = processed.title or item.title
            item.description = processed.description or item.description
            item.content = processed.content or item.content
            item.author = processed.author or item.author

            # Log the reprocessing
            self._log_processing(
                item, item.feed, processor.processor_name,
                "success", content_item, processed,
                None, processing_time, {"is_valid": True}
            )

            self.session.add(item)
            return True

        except Exception as e:
            logger.error(f"Reprocessing failed for item {item.id}: {e}")

        return False

    def _dict_to_content_item(self, raw_item: Dict[str, Any]) -> ContentItem:
        """Convert raw RSS dict to ContentItem"""
        # Handle published date conversion
        published = None
        if raw_item.get('published_parsed'):
            parsed_time = raw_item['published_parsed']
            if isinstance(parsed_time, tuple) and len(parsed_time) >= 6:
                published = datetime(*parsed_time[:6])
            elif isinstance(parsed_time, datetime):
                published = parsed_time

        return ContentItem(
            title=raw_item.get('title'),
            description=raw_item.get('description') or raw_item.get('summary'),
            content=raw_item.get('content', [{}])[0].get('value') if isinstance(raw_item.get('content'), list) and raw_item.get('content') else raw_item.get('content'),
            author=raw_item.get('author'),
            link=raw_item.get('link'),
            published=published,
            guid=raw_item.get('id') or raw_item.get('guid')
        )

    def _create_item_from_processed(self, processed: ProcessedContent, feed: Feed) -> Optional[Item]:
        """Create an Item model from processed content"""
        if not processed.title and not processed.description:
            return None

        # Generate content hash for deduplication
        import hashlib
        content_for_hash = f"{processed.title or ''}{processed.link or ''}{processed.guid or ''}"
        content_hash = hashlib.sha256(content_for_hash.encode()).hexdigest()

        return Item(
            title=processed.title or "Untitled",
            link=processed.link or "",
            description=processed.description,
            content=processed.content,
            author=processed.author,
            published=processed.published,
            guid=processed.guid,
            content_hash=content_hash,
            feed_id=feed.id
        )

    def _fallback_processing(self, content_item: ContentItem) -> ProcessedContent:
        """Minimal fallback processing when main processor fails"""
        return ProcessedContent(
            title=content_item.title,
            description=content_item.description,
            content=content_item.content,
            author=content_item.author,
            link=content_item.link,
            published=content_item.published,
            guid=content_item.guid,
            transformations=["fallback_processing"],
            quality_score=0.5
        )

    def _log_processing(self, item: Item, feed: Feed, processor_name: str,
                       status: ProcessingStatus, original: ContentItem,
                       processed: ProcessedContent, error_message: Optional[str],
                       processing_time: int, validation_result: Dict[str, Any] = None):
        """Log the processing operation"""

        # Determine processor type from name
        processor_type = ProcessorType.UNIVERSAL
        if "Heise" in processor_name:
            processor_type = ProcessorType.HEISE
        elif "Cointelegraph" in processor_name:
            processor_type = ProcessorType.COINTELEGRAPH

        # Include validation information in transformations
        transformations = processed.transformations.copy() if processed.transformations else []
        if validation_result:
            if validation_result.get("warnings"):
                transformations.extend([f"validation_warning: {w}" for w in validation_result["warnings"][:3]])
            if validation_result.get("quality_adjustments"):
                adjustments = list(validation_result["quality_adjustments"].keys())[:3]
                transformations.extend([f"quality_adjustment: {adj}" for adj in adjustments])

        log_entry = ContentProcessingLog(
            item_id=item.id,
            feed_id=feed.id,
            processor_type=processor_type,
            processing_status=status,
            original_title=original.title,
            processed_title=processed.title,
            original_description=original.description,
            processed_description=processed.description,
            transformations=transformations,
            error_message=error_message,
            processing_time_ms=processing_time
        )

        self.session.add(log_entry)

    def get_processing_stats(self, feed_id: Optional[int] = None) -> Dict[str, Any]:
        """Get processing statistics"""
        query = self.session.query(ContentProcessingLog)

        if feed_id:
            query = query.filter(ContentProcessingLog.feed_id == feed_id)

        logs = query.all()

        stats = {
            "total_processed": len(logs),
            "success_count": len([l for l in logs if l.processing_status == ProcessingStatus.SUCCESS]),
            "failed_count": len([l for l in logs if l.processing_status == ProcessingStatus.FAILED]),
            "avg_processing_time": sum(l.processing_time_ms or 0 for l in logs) / len(logs) if logs else 0,
            "processor_breakdown": {}
        }

        # Processor type breakdown
        for log in logs:
            proc_type = log.processor_type.value
            if proc_type not in stats["processor_breakdown"]:
                stats["processor_breakdown"][proc_type] = 0
            stats["processor_breakdown"][proc_type] += 1

        return stats