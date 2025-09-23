"""Processor management service with business logic."""

from typing import List, Optional, Dict, Any, Tuple
from sqlmodel import Session, select, func
from datetime import datetime, timedelta
from app.core.logging_config import get_logger

from .base import BaseService, ServiceResult, NotFoundError, ValidationError, BusinessLogicError
from app.models import (
    Feed, FeedProcessorConfig, ProcessorTemplate, ContentProcessingLog,
    ProcessorType, ProcessingStatus
)

logger = get_logger(__name__)


class ProcessorService:
    """Service for processor management and configuration operations."""

    def __init__(self, session: Session):
        self.session = session

    def get_available_processor_types(self) -> ServiceResult[Dict[str, Any]]:
        """Get all available processor types with descriptions."""
        try:
            return ServiceResult.ok({
                "available_types": [ptype.value for ptype in ProcessorType],
                "descriptions": {
                    "universal": "Basic content cleaning and normalization",
                    "heise": "Specialized for Heise Online feeds with German prefixes",
                    "cointelegraph": "Handles Cointelegraph truncation and formatting issues",
                    "custom": "Custom processor configuration"
                }
            })
        except Exception as e:
            logger.error(f"Error getting processor types: {e}")
            return ServiceResult.error(f"Error: {str(e)}")

    def get_feed_processor_config(self, feed_id: int) -> ServiceResult[Dict[str, Any]]:
        """Get processor configuration for a specific feed."""
        try:
            feed = self.session.get(Feed, feed_id)
            if not feed:
                return ServiceResult.error(f"Feed with id {feed_id} not found")

            config = self.session.exec(
                select(FeedProcessorConfig).where(FeedProcessorConfig.feed_id == feed_id)
            ).first()

            if not config:
                # Return default configuration
                return ServiceResult.ok({
                    "feed_id": feed_id,
                    "processor_type": ProcessorType.UNIVERSAL.value,
                    "config": {},
                    "is_active": True,
                    "has_custom_config": False
                })

            return ServiceResult.ok({
                "feed_id": feed_id,
                "processor_type": config.processor_type.value,
                "config": config.config,
                "is_active": config.is_active,
                "has_custom_config": True,
                "created_at": config.created_at,
                "updated_at": config.updated_at
            })

        except Exception as e:
            logger.error(f"Error getting processor config for feed {feed_id}: {e}")
            return ServiceResult.error(f"Database error: {str(e)}")

    def create_or_update_processor_config(
        self,
        feed_id: int,
        processor_type: ProcessorType,
        config: Dict[str, Any],
        is_active: bool = True
    ) -> ServiceResult[FeedProcessorConfig]:
        """Create or update processor configuration for a feed."""
        try:
            # Verify feed exists
            feed = self.session.get(Feed, feed_id)
            if not feed:
                return ServiceResult.error(f"Feed with id {feed_id} not found")

            # Validate processor type
            if not isinstance(processor_type, ProcessorType):
                try:
                    processor_type = ProcessorType(processor_type)
                except ValueError:
                    return ServiceResult.error(f"Invalid processor type: {processor_type}")

            # Check for existing configuration
            existing_config = self.session.exec(
                select(FeedProcessorConfig).where(FeedProcessorConfig.feed_id == feed_id)
            ).first()

            if existing_config:
                # Update existing configuration
                existing_config.processor_type = processor_type
                existing_config.config = config
                existing_config.is_active = is_active
                existing_config.updated_at = datetime.utcnow()

                self.session.commit()
                self.session.refresh(existing_config)

                logger.info(f"Updated processor config for feed {feed_id}: {processor_type.value}")
                return ServiceResult.ok(existing_config)
            else:
                # Create new configuration
                new_config = FeedProcessorConfig(
                    feed_id=feed_id,
                    processor_type=processor_type,
                    config=config,
                    is_active=is_active,
                    created_at=datetime.utcnow()
                )

                self.session.add(new_config)
                self.session.commit()
                self.session.refresh(new_config)

                logger.info(f"Created processor config for feed {feed_id}: {processor_type.value}")
                return ServiceResult.ok(new_config)

        except Exception as e:
            self.session.rollback()
            logger.error(f"Error creating/updating processor config for feed {feed_id}: {e}")
            return ServiceResult.error(f"Failed to save configuration: {str(e)}")

    def delete_processor_config(self, feed_id: int) -> ServiceResult[bool]:
        """Delete processor configuration for a feed."""
        try:
            config = self.session.exec(
                select(FeedProcessorConfig).where(FeedProcessorConfig.feed_id == feed_id)
            ).first()

            if not config:
                return ServiceResult.error(f"No processor configuration found for feed {feed_id}")

            self.session.delete(config)
            self.session.commit()

            logger.info(f"Deleted processor config for feed {feed_id}")
            return ServiceResult.ok(True)

        except Exception as e:
            self.session.rollback()
            logger.error(f"Error deleting processor config for feed {feed_id}: {e}")
            return ServiceResult.error(f"Failed to delete configuration: {str(e)}")

    def list_processor_configs(self, active_only: bool = False) -> ServiceResult[List[Tuple[FeedProcessorConfig, Feed]]]:
        """List all processor configurations with feed information."""
        try:
            query = select(FeedProcessorConfig, Feed).join(Feed)

            if active_only:
                query = query.where(FeedProcessorConfig.is_active == True)

            results = self.session.exec(query).all()
            return ServiceResult.ok(list(results))

        except Exception as e:
            logger.error(f"Error listing processor configs: {e}")
            return ServiceResult.error(f"Database error: {str(e)}")

    def get_processor_templates(self, active_only: bool = False) -> ServiceResult[List[ProcessorTemplate]]:
        """Get processor templates."""
        try:
            query = select(ProcessorTemplate)

            if active_only:
                query = query.where(ProcessorTemplate.is_active == True)

            templates = self.session.exec(query.order_by(ProcessorTemplate.name)).all()
            return ServiceResult.ok(list(templates))

        except Exception as e:
            logger.error(f"Error getting processor templates: {e}")
            return ServiceResult.error(f"Database error: {str(e)}")

    def create_processor_template(
        self,
        name: str,
        processor_type: ProcessorType,
        config: Dict[str, Any],
        description: Optional[str] = None,
        is_active: bool = True
    ) -> ServiceResult[ProcessorTemplate]:
        """Create a new processor template."""
        try:
            # Check for duplicate names
            existing = self.session.exec(
                select(ProcessorTemplate).where(ProcessorTemplate.name == name)
            ).first()

            if existing:
                return ServiceResult.error(f"Template with name '{name}' already exists")

            template = ProcessorTemplate(
                name=name,
                processor_type=processor_type,
                config=config,
                description=description,
                is_active=is_active,
                is_builtin=False,
                created_at=datetime.utcnow()
            )

            self.session.add(template)
            self.session.commit()
            self.session.refresh(template)

            logger.info(f"Created processor template: {name}")
            return ServiceResult.ok(template)

        except Exception as e:
            self.session.rollback()
            logger.error(f"Error creating processor template: {e}")
            return ServiceResult.error(f"Failed to create template: {str(e)}")

    def apply_template_to_feeds(self, template_id: int, feed_ids: Optional[List[int]] = None) -> ServiceResult[int]:
        """Apply processor template to feeds."""
        try:
            template = self.session.get(ProcessorTemplate, template_id)
            if not template:
                return ServiceResult.error(f"Template with id {template_id} not found")

            if not template.is_active:
                return ServiceResult.error("Cannot apply inactive template")

            # If no feed_ids specified, apply to all feeds that match criteria
            if feed_ids is None:
                # Apply to all active feeds (this could be enhanced with more criteria)
                feeds = self.session.exec(
                    select(Feed).where(Feed.status == "active")
                ).all()
                feed_ids = [feed.id for feed in feeds]

            applied_count = 0
            for feed_id in feed_ids:
                result = self.create_or_update_processor_config(
                    feed_id=feed_id,
                    processor_type=template.processor_type,
                    config=template.config,
                    is_active=True
                )
                if result.success:
                    applied_count += 1

            logger.info(f"Applied template {template_id} to {applied_count}/{len(feed_ids)} feeds")
            return ServiceResult.ok(applied_count)

        except Exception as e:
            logger.error(f"Error applying template {template_id}: {e}")
            return ServiceResult.error(f"Failed to apply template: {str(e)}")

    def get_processing_statistics(self, days: int = 7) -> ServiceResult[Dict[str, Any]]:
        """Get processor performance statistics."""
        try:
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days)

            # Basic statistics
            total_query = select(func.count(ContentProcessingLog.id)).where(
                ContentProcessingLog.processed_at >= start_date
            )
            total_processed = self.session.exec(total_query).first() or 0

            success_query = select(func.count(ContentProcessingLog.id)).where(
                ContentProcessingLog.processed_at >= start_date,
                ContentProcessingLog.processing_status == ProcessingStatus.SUCCESS
            )
            success_count = self.session.exec(success_query).first() or 0

            # Processor breakdown
            breakdown_query = select(
                ContentProcessingLog.processor_type,
                func.count(ContentProcessingLog.id).label('count'),
                func.avg(ContentProcessingLog.processing_time_ms).label('avg_time')
            ).where(
                ContentProcessingLog.processed_at >= start_date
            ).group_by(ContentProcessingLog.processor_type)

            breakdown_results = self.session.exec(breakdown_query).all()

            success_rate = (success_count / total_processed * 100) if total_processed > 0 else 100

            processor_stats = []
            for result in breakdown_results:
                processor_stats.append({
                    "processor_type": result[0].value if hasattr(result[0], 'value') else str(result[0]),
                    "processed_count": result[1],
                    "avg_time_ms": float(result[2]) if result[2] else 0,
                    "usage_percentage": (result[1] / total_processed * 100) if total_processed > 0 else 0
                })

            return ServiceResult.ok({
                "period_days": days,
                "total_processed": total_processed,
                "successful_processed": success_count,
                "failed_processed": total_processed - success_count,
                "success_rate_percent": success_rate,
                "active_processors": len(breakdown_results),
                "processor_breakdown": processor_stats
            })

        except Exception as e:
            logger.error(f"Error getting processing statistics: {e}")
            return ServiceResult.error(f"Database error: {str(e)}")

    def get_recent_processing_activity(self, limit: int = 10) -> ServiceResult[List[ContentProcessingLog]]:
        """Get recent processing activity logs."""
        try:
            logs = self.session.exec(
                select(ContentProcessingLog)
                .order_by(ContentProcessingLog.processed_at.desc())
                .limit(limit)
            ).all()

            return ServiceResult.ok(list(logs))

        except Exception as e:
            logger.error(f"Error getting recent processing activity: {e}")
            return ServiceResult.error(f"Database error: {str(e)}")

    def trigger_reprocessing(
        self,
        feed_ids: Optional[List[int]] = None,
        failed_only: bool = True
    ) -> ServiceResult[Dict[str, Any]]:
        """Trigger reprocessing of items."""
        try:
            # This would typically queue items for reprocessing
            # For now, we'll just count what would be reprocessed

            query = select(ContentProcessingLog)

            if failed_only:
                query = query.where(ContentProcessingLog.processing_status == ProcessingStatus.FAILED)

            if feed_ids:
                query = query.where(ContentProcessingLog.feed_id.in_(feed_ids))

            # Get items to reprocess (last 24h of failed items)
            recent_cutoff = datetime.utcnow() - timedelta(hours=24)
            query = query.where(ContentProcessingLog.processed_at >= recent_cutoff)

            failed_logs = self.session.exec(query).all()

            # In a real implementation, you would queue these for reprocessing
            # For now, just return the count and summary
            return ServiceResult.ok({
                "items_queued": len(failed_logs),
                "reprocessing_initiated": True,
                "queue_time": datetime.utcnow(),
                "estimated_completion": datetime.utcnow() + timedelta(minutes=len(failed_logs) * 2)
            })

        except Exception as e:
            logger.error(f"Error triggering reprocessing: {e}")
            return ServiceResult.error(f"Failed to trigger reprocessing: {str(e)}")

    def validate_processor_config(self, processor_type: ProcessorType, config: Dict[str, Any]) -> ServiceResult[bool]:
        """Validate processor configuration."""
        try:
            # Basic validation - in a real implementation, this would use the ProcessorConfigValidator
            if not isinstance(config, dict):
                return ServiceResult.error("Configuration must be a dictionary")

            # Type-specific validation
            if processor_type == ProcessorType.HEISE:
                required_keys = ['strip_prefixes', 'content_selectors']
                for key in required_keys:
                    if key not in config:
                        return ServiceResult.error(f"Missing required configuration key: {key}")

            elif processor_type == ProcessorType.COINTELEGRAPH:
                if 'min_content_length' in config and not isinstance(config['min_content_length'], int):
                    return ServiceResult.error("min_content_length must be an integer")

            return ServiceResult.ok(True)

        except Exception as e:
            logger.error(f"Error validating processor config: {e}")
            return ServiceResult.error(f"Validation error: {str(e)}")