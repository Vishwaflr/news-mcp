"""Bootstrap service for processor system initialization."""

from typing import Dict, Any, List
from sqlmodel import Session, select
from datetime import datetime
from app.core.logging_config import get_logger

from app.models import (
    Feed, FeedProcessorConfig, ProcessorTemplate,
    ProcessorType
)
from app.processors.factory import ProcessorFactory

logger = get_logger(__name__)


class ProcessorBootstrap:
    """Initialize and configure the processor system with sensible defaults."""

    def __init__(self, session: Session):
        self.session = session

    def get_bootstrap_status(self) -> Dict[str, Any]:
        """Check if system needs bootstrapping."""
        try:
            # Count total feeds
            total_feeds = self.session.exec(select(Feed)).all()
            total_count = len(total_feeds)

            # Count feeds with processor configs
            configured_feeds = self.session.exec(
                select(FeedProcessorConfig).where(FeedProcessorConfig.is_active == True)
            ).all()
            configured_count = len(configured_feeds)

            # Count templates
            templates = self.session.exec(select(ProcessorTemplate)).all()
            template_count = len(templates)

            # Determine if bootstrap needed
            needs_bootstrap = (
                configured_count < total_count or
                template_count == 0
            )

            return {
                "needs_bootstrap": needs_bootstrap,
                "total_feeds": total_count,
                "configured_feeds": configured_count,
                "unconfigured_feeds": total_count - configured_count,
                "template_count": template_count,
                "missing_templates": template_count == 0,
                "configuration_percentage": round((configured_count / total_count * 100), 1) if total_count > 0 else 0
            }

        except Exception as e:
            logger.error(f"Error checking bootstrap status: {e}")
            return {
                "needs_bootstrap": True,
                "error": str(e)
            }

    def create_default_templates(self) -> Dict[str, Any]:
        """Create built-in processor templates."""
        try:
            templates_created = []

            # Template 1: Universal Processor
            universal_template = self.session.exec(
                select(ProcessorTemplate).where(ProcessorTemplate.name == "Universal Content Processor")
            ).first()

            if not universal_template:
                universal_template = ProcessorTemplate(
                    name="Universal Content Processor",
                    processor_type=ProcessorType.UNIVERSAL,
                    description="Basic content cleaning and normalization for all feeds",
                    config_json='{"remove_html": true, "normalize_whitespace": true}',
                    url_patterns='[".*"]',  # Matches all URLs as fallback
                    is_builtin=True,
                    is_active=True,
                    created_at=datetime.utcnow()
                )
                self.session.add(universal_template)
                templates_created.append("Universal")
                logger.info("Created Universal processor template")

            # Template 2: Heise Processor
            heise_template = self.session.exec(
                select(ProcessorTemplate).where(ProcessorTemplate.name == "Heise.de Processor")
            ).first()

            if not heise_template:
                heise_template = ProcessorTemplate(
                    name="Heise.de Processor",
                    processor_type=ProcessorType.HEISE,
                    description="Specialized processor for Heise Online feeds (removes German prefixes, handles specific formatting)",
                    config_json='{"strip_prefixes": ["heise+:", "heise online:", "ct:"], "content_selectors": [".article-content", ".meldung"]}',
                    url_patterns='[".*heise\\\\.de.*", ".*heise\\\\.online.*"]',
                    is_builtin=True,
                    is_active=True,
                    created_at=datetime.utcnow()
                )
                self.session.add(heise_template)
                templates_created.append("Heise")
                logger.info("Created Heise processor template")

            # Template 3: Cointelegraph Processor
            cointelegraph_template = self.session.exec(
                select(ProcessorTemplate).where(ProcessorTemplate.name == "Cointelegraph Processor")
            ).first()

            if not cointelegraph_template:
                cointelegraph_template = ProcessorTemplate(
                    name="Cointelegraph Processor",
                    processor_type=ProcessorType.COINTELEGRAPH,
                    description="Handles Cointelegraph truncation and formatting issues",
                    config_json='{"min_content_length": 100, "fix_truncation": true}',
                    url_patterns='[".*cointelegraph\\\\.com.*"]',
                    is_builtin=True,
                    is_active=True,
                    created_at=datetime.utcnow()
                )
                self.session.add(cointelegraph_template)
                templates_created.append("Cointelegraph")
                logger.info("Created Cointelegraph processor template")

            # Commit all templates
            self.session.commit()

            return {
                "success": True,
                "templates_created": templates_created,
                "total_templates": len(templates_created),
                "message": f"Created {len(templates_created)} default templates"
            }

        except Exception as e:
            self.session.rollback()
            logger.error(f"Error creating default templates: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def auto_configure_all_feeds(self) -> Dict[str, Any]:
        """Auto-detect and assign processors to all feeds."""
        try:
            # Ensure templates exist first
            template_result = self.create_default_templates()
            if not template_result["success"]:
                return {
                    "success": False,
                    "error": "Failed to create templates",
                    "details": template_result
                }

            # Get all feeds
            feeds = self.session.exec(select(Feed)).all()

            configured_count = 0
            skipped_count = 0
            errors = []

            for feed in feeds:
                try:
                    # Check if feed already has a config
                    existing_config = self.session.exec(
                        select(FeedProcessorConfig).where(FeedProcessorConfig.feed_id == feed.id)
                    ).first()

                    if existing_config and existing_config.is_active:
                        skipped_count += 1
                        logger.debug(f"Skipping feed {feed.id} - already configured")
                        continue

                    # Auto-detect processor type based on feed URL
                    processor_type = ProcessorFactory.auto_detect_processor_type(feed.url)

                    # Create or update config
                    if existing_config:
                        existing_config.processor_type = processor_type
                        existing_config.is_active = True
                        existing_config.updated_at = datetime.utcnow()
                    else:
                        new_config = FeedProcessorConfig(
                            feed_id=feed.id,
                            processor_type=processor_type,
                            config_json='{}',
                            is_active=True,
                            created_at=datetime.utcnow()
                        )
                        self.session.add(new_config)

                    configured_count += 1
                    logger.info(f"Configured feed {feed.id} ({feed.title}) with {processor_type.value} processor")

                except Exception as e:
                    error_msg = f"Error configuring feed {feed.id}: {str(e)}"
                    errors.append(error_msg)
                    logger.error(error_msg)
                    continue

            # Commit all changes
            self.session.commit()

            return {
                "success": True,
                "total_feeds": len(feeds),
                "configured": configured_count,
                "skipped": skipped_count,
                "errors": errors,
                "message": f"Configured {configured_count} feeds, skipped {skipped_count} already configured"
            }

        except Exception as e:
            self.session.rollback()
            logger.error(f"Error in auto-configure: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def get_feed_assignments(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get all feed-to-processor assignments."""
        try:
            feeds = self.session.exec(select(Feed)).all()

            assignments = []
            for feed in feeds:
                config = self.session.exec(
                    select(FeedProcessorConfig).where(FeedProcessorConfig.feed_id == feed.id)
                ).first()

                assignments.append({
                    "feed_id": feed.id,
                    "feed_title": feed.title,
                    "feed_url": feed.url,
                    "processor_type": config.processor_type.value if config else None,
                    "is_active": config.is_active if config else False,
                    "has_config": config is not None,
                    "auto_detected_type": ProcessorFactory.auto_detect_processor_type(feed.url).value
                })

            # Group by processor type
            by_processor = {}
            for assignment in assignments:
                proc_type = assignment["processor_type"] or "unassigned"
                if proc_type not in by_processor:
                    by_processor[proc_type] = []
                by_processor[proc_type].append(assignment)

            return {
                "success": True,
                "assignments": assignments,
                "by_processor": by_processor,
                "summary": {
                    "total": len(assignments),
                    "configured": len([a for a in assignments if a["has_config"]]),
                    "unassigned": len([a for a in assignments if not a["has_config"]])
                }
            }

        except Exception as e:
            logger.error(f"Error getting feed assignments: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def assign_processor_to_feed(
        self,
        feed_id: int,
        processor_type: ProcessorType,
        config: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Assign a specific processor to a feed."""
        try:
            # Verify feed exists
            feed = self.session.get(Feed, feed_id)
            if not feed:
                return {
                    "success": False,
                    "error": f"Feed {feed_id} not found"
                }

            # Check for existing config
            existing_config = self.session.exec(
                select(FeedProcessorConfig).where(FeedProcessorConfig.feed_id == feed_id)
            ).first()

            if existing_config:
                # Update existing
                existing_config.processor_type = processor_type
                existing_config.is_active = True
                existing_config.updated_at = datetime.utcnow()
                if config:
                    existing_config.config = config
            else:
                # Create new
                new_config = FeedProcessorConfig(
                    feed_id=feed_id,
                    processor_type=processor_type,
                    config_json='{}' if not config else str(config),
                    is_active=True,
                    created_at=datetime.utcnow()
                )
                self.session.add(new_config)

            self.session.commit()

            logger.info(f"Assigned {processor_type.value} processor to feed {feed_id} ({feed.title})")

            return {
                "success": True,
                "feed_id": feed_id,
                "processor_type": processor_type.value,
                "message": f"Assigned {processor_type.value} to {feed.title}"
            }

        except Exception as e:
            self.session.rollback()
            logger.error(f"Error assigning processor to feed {feed_id}: {e}")
            return {
                "success": False,
                "error": str(e)
            }
