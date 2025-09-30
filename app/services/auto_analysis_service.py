"""
Auto-Analysis Service

Handles automatic analysis triggering for feeds with auto_analyze_enabled.
"""

from app.core.logging_config import get_logger
from typing import List, Optional
from datetime import datetime, timedelta
from sqlmodel import Session, select

from app.database import engine
from app.models.core import Feed, Item
from app.domain.analysis.control import RunScope, RunParams
from app.services.domain.analysis_service import AnalysisService
from app.dependencies import get_analysis_service
from app.utils.feature_flags import feature_flags, FeatureFlagStatus
from app.services.auto_analysis_config import auto_analysis_config

logger = get_logger(__name__)

class AutoAnalysisService:
    """Service for handling automatic analysis triggering"""

    def __init__(self):
        # Load from centralized config
        self.max_items_per_run = auto_analysis_config.max_items_per_run
        self.max_daily_auto_runs_per_feed = auto_analysis_config.max_daily_runs

    async def trigger_feed_auto_analysis(self, feed_id: int, new_item_ids: List[int]) -> Optional[dict]:
        """
        Trigger auto-analysis for new items in a feed if enabled.

        Args:
            feed_id: The feed ID that has new items
            new_item_ids: List of newly fetched item IDs

        Returns:
            dict with run info if analysis was triggered, None otherwise
        """
        if not new_item_ids:
            return None

        # Check global feature flag first
        if not self._is_auto_analysis_enabled_for_feed(feed_id):
            logger.debug(f"Auto-analysis not enabled globally or for feed {feed_id}")
            return None

        with Session(engine) as session:
            # Check if feed has auto-analysis enabled
            feed = session.get(Feed, feed_id)
            if not feed or not feed.auto_analyze_enabled:
                logger.debug(f"Feed {feed_id} does not have auto-analysis enabled")
                return None

            # Check daily limits
            if not self._check_daily_limits(session, feed_id):
                logger.warning(f"Feed {feed_id} has exceeded daily auto-analysis limit")
                return None

            # Limit number of items to analyze
            items_to_analyze = new_item_ids[:self.max_items_per_run]

            if len(new_item_ids) > self.max_items_per_run:
                logger.info(f"Limiting auto-analysis for feed {feed_id} to {self.max_items_per_run} items (had {len(new_item_ids)})")

            # Check if we're in shadow mode
            is_shadow = feature_flags.is_enabled("auto_analysis_shadow", str(feed_id))

            try:
                # Create analysis run
                scope = RunScope(type="items", item_ids=items_to_analyze)
                params = RunParams(
                    limit=len(items_to_analyze),
                    rate_per_second=auto_analysis_config.rate_per_second,  # From config
                    model_tag=auto_analysis_config.ai_model,  # From config
                    triggered_by="auto"  # Mark this as auto-triggered
                )

                if is_shadow:
                    # Shadow mode: log but don't actually execute
                    logger.info(f"[SHADOW MODE] Would start auto-analysis for feed {feed_id} with {len(items_to_analyze)} items")
                    feature_flags.record_success("auto_analysis_shadow")

                    return {
                        "run_id": "shadow_run",
                        "feed_id": feed_id,
                        "items_count": len(items_to_analyze),
                        "run_type": "auto_analysis_shadow",
                        "shadow_mode": True
                    }

                # Get analysis service and start run
                analysis_service = get_analysis_service()
                result = await analysis_service.start_analysis_run(scope, params, "auto")

                if result.success:
                    run_data = result.data
                    logger.info(f"Started auto-analysis run {run_data.id} for feed {feed_id} with {len(items_to_analyze)} items")

                    # Record success for feature flag metrics
                    feature_flags.record_success("auto_analysis_global")

                    return {
                        "run_id": run_data.id,
                        "feed_id": feed_id,
                        "items_count": len(items_to_analyze),
                        "run_type": "auto_analysis"
                    }
                else:
                    logger.error(f"Failed to start auto-analysis for feed {feed_id}: {result.error}")
                    feature_flags.record_error("auto_analysis_global")
                    return None

            except Exception as e:
                logger.error(f"Error triggering auto-analysis for feed {feed_id}: {e}")
                feature_flags.record_error("auto_analysis_global")
                return None

    def _check_daily_limits(self, session: Session, feed_id: int) -> bool:
        """
        Check if feed is within daily auto-analysis limits.

        Args:
            session: Database session
            feed_id: Feed ID to check

        Returns:
            True if within limits, False otherwise
        """
        try:
            # Query for auto-analysis runs in the last 24 hours using triggered_by field
            from app.models.analysis import AnalysisRun

            yesterday = datetime.utcnow() - timedelta(days=1)

            # Count auto-triggered runs for this specific feed
            auto_runs_today = session.exec(
                select(AnalysisRun).where(
                    AnalysisRun.created_at >= yesterday,
                    AnalysisRun.triggered_by == "auto",
                    AnalysisRun.scope_json.contains(f'"item_ids"')  # Basic check that it's item-based
                )
            ).all()

            # Filter to only runs for this specific feed by checking scope_json for feed items
            feed = session.get(Feed, feed_id)
            if not feed:
                return False

            # Get feed's item IDs to match against runs
            feed_items = session.exec(
                select(Item.id).where(Item.feed_id == feed_id)
            ).all()
            feed_item_ids = set(item for item in feed_items)

            feed_auto_runs = []
            for run in auto_runs_today:
                # Check if any items in the run belong to this feed
                import json
                try:
                    scope_data = json.loads(run.scope_json) if isinstance(run.scope_json, str) else run.scope_json
                    run_item_ids = set(scope_data.get('item_ids', []))
                    if run_item_ids.intersection(feed_item_ids):
                        feed_auto_runs.append(run)
                except (json.JSONDecodeError, KeyError, TypeError) as e:
                    logger.debug(f"Error parsing run scope for run {run.id}: {e}")
                    continue

            runs_count = len(feed_auto_runs)
            logger.debug(f"Feed {feed_id} has {runs_count} auto-analysis runs in last 24h (limit: {self.max_daily_auto_runs_per_feed})")

            return runs_count < self.max_daily_auto_runs_per_feed

        except Exception as e:
            logger.error(f"Error checking daily limits for feed {feed_id}: {e}")
            # Err on the side of caution - don't allow if we can't check
            return False

    def _is_auto_analysis_enabled_for_feed(self, feed_id: int) -> bool:
        """
        Check if auto-analysis is enabled for this feed via feature flag.
        Implements gradual rollout based on feed ID.

        Args:
            feed_id: Feed ID to check

        Returns:
            True if auto-analysis is enabled for this feed
        """
        # Check global feature flag status
        flag_status = feature_flags.get_flag_status("auto_analysis_global")
        if not flag_status:
            return False

        status = FeatureFlagStatus(flag_status["status"])

        # Emergency off or completely off
        if status in [FeatureFlagStatus.EMERGENCY_OFF, FeatureFlagStatus.OFF]:
            return False

        # Fully on
        if status == FeatureFlagStatus.ON:
            return True

        # Canary/gradual rollout
        if status == FeatureFlagStatus.CANARY:
            # Use feed ID for consistent rollout
            return feature_flags.is_enabled("auto_analysis_global", str(feed_id))

        return False

    def get_auto_analysis_stats(self, feed_id: int) -> dict:
        """
        Get auto-analysis statistics for a feed.

        Args:
            feed_id: Feed ID

        Returns:
            dict with statistics
        """
        with Session(engine) as session:
            try:
                from app.models.analysis import AnalysisRun

                # Get auto-triggered runs from last 7 days
                week_ago = datetime.utcnow() - timedelta(days=7)

                auto_runs = session.exec(
                    select(AnalysisRun).where(
                        AnalysisRun.created_at >= week_ago,
                        AnalysisRun.triggered_by == "auto"
                    )
                ).all()

                # Filter for this feed
                feed = session.get(Feed, feed_id)
                if not feed:
                    return {"error": "Feed not found"}

                # Get feed's item IDs to match against runs
                feed_items = session.exec(
                    select(Item.id).where(Item.feed_id == feed_id)
                ).all()
                feed_item_ids = set(item for item in feed_items)

                feed_runs = []
                for run in auto_runs:
                    # Check if any items in the run belong to this feed
                    import json
                    try:
                        scope_data = json.loads(run.scope_json) if isinstance(run.scope_json, str) else run.scope_json
                        run_item_ids = set(scope_data.get('item_ids', []))
                        if run_item_ids.intersection(feed_item_ids):
                            feed_runs.append(run)
                    except (json.JSONDecodeError, KeyError, TypeError) as e:
                        logger.debug(f"Error parsing run scope for stats: {e}")
                        continue

                return {
                    "auto_runs_last_7_days": len(feed_runs),
                    "auto_analysis_enabled": feed.auto_analyze_enabled,
                    "last_auto_run": max([run.created_at for run in feed_runs]) if feed_runs else None
                }

            except Exception as e:
                logger.error(f"Error getting auto-analysis stats for feed {feed_id}: {e}")
                return {"error": str(e)}