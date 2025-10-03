import time
from app.core.logging_config import get_logger
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

from app.repositories.analysis_queue import AnalysisQueueRepo
from app.repositories.analysis import AnalysisRepo
from app.services.llm_client import LLMClient
from app.services.error_recovery import get_error_recovery_service, CircuitBreakerConfig
from app.domain.analysis.schema import AnalysisResult, Overall, Market, SentimentPayload, ImpactPayload
from app.domain.analysis.control import MODEL_PRICING, AVG_TOKENS_PER_ITEM
from app.services.prometheus_metrics import get_metrics

logger = get_logger(__name__)

class AnalysisOrchestrator:
    """Orchestrates analysis runs and manages item processing"""

    def __init__(self, chunk_size: int = 10, min_request_interval: float = 1.0):
        self.chunk_size = chunk_size
        self.min_request_interval = min_request_interval
        self.last_request_time = 0.0
        self.queue_repo = AnalysisQueueRepo()
        self.error_recovery = get_error_recovery_service()

        # Configure circuit breakers for critical services
        self.openai_breaker_config = CircuitBreakerConfig(
            failure_threshold=3,  # Open after 3 failures
            success_threshold=2,   # Close after 2 successes
            timeout_seconds=60,    # Try recovery after 60s
        )

        # SPRINT 1 DAY 3: Prometheus metrics
        self.metrics = get_metrics()

    def get_available_runs(self) -> List[Dict[str, Any]]:
        """Get runs that can be processed (pending or running, not paused/cancelled)"""
        runs = self.queue_repo.get_pending_runs()
        available_runs = []

        for run in runs:
            if run["status"] in ["pending", "running"]:
                available_runs.append(run)

        return available_runs

    def start_run(self, run: Dict[str, Any]) -> bool:
        """Start a pending run"""
        if run["status"] != "pending":
            return False

        logger.info(f"Starting run {run['id']}")
        return self.queue_repo.update_run_status(run["id"], "running")

    def process_run_items(self, run: Dict[str, Any]) -> int:
        """Process a batch of items for a run"""
        run_id = run["id"]
        params = run["params"]

        # Mark run as started if this is the first processing
        self._mark_run_started(run_id)

        # Apply rate limiting
        self._throttle_requests(params.get("rate_per_second", 1.0))

        # Claim items for processing
        claimed_items = self.queue_repo.claim_items_for_processing(run_id, self.chunk_size)

        if not claimed_items:
            logger.debug(f"No items to process for run {run_id}")
            return 0

        logger.info(f"Processing {len(claimed_items)} items for run {run_id}")

        # Initialize LLM client
        model_tag = params.get("model_tag", "gpt-4.1-nano")
        llm_client = LLMClient(
            model=model_tag,
            rate_per_sec=params.get("rate_per_second", 1.0),
            timeout=8
        )

        processed_count = 0
        skipped_count = 0

        for item_info in claimed_items:
            queue_id = item_info["queue_id"]
            item_id = item_info["item_id"]

            try:
                # NEW: Check if item was already analyzed
                is_analyzed, previous_run = self.check_already_analyzed(item_id, days=7)

                if is_analyzed:
                    # Mark as skipped
                    self._mark_item_skipped(queue_id, f"already_analyzed_in_{previous_run}")
                    skipped_count += 1
                    logger.info(f"Skipped item {item_id} - already analyzed in {previous_run}")
                    continue

                # Get item content
                item_content = self.queue_repo.get_item_content(item_id)
                if not item_content:
                    self._mark_item_failed(queue_id, "ENODATA", "Item content not found")
                    continue

                # Process the item
                if params.get("dry_run", False):
                    self._process_item_dry_run(queue_id, item_content, model_tag)
                else:
                    self._process_item_analysis(queue_id, item_content, llm_client, model_tag)

                processed_count += 1

            except Exception as e:
                logger.error(f"Failed to process item {item_id}: {e}")
                self._mark_item_failed(queue_id, "EUNKNOWN", str(e))

        # Update run statistics
        if skipped_count > 0:
            self._update_run_skip_stats(run_id, skipped_count)

        # Update processed count in analysis_runs table
        self._update_run_processed_count(run_id)

        # Update run heartbeat
        self.queue_repo.heartbeat_run(run_id)

        logger.info(f"Run {run_id}: Processed {processed_count}, Skipped {skipped_count}")
        return processed_count

    async def _process_item_analysis_with_recovery(self, queue_id: int, item_content: Dict[str, Any],
                                                llm_client: LLMClient, model_tag: str) -> None:
        """Process analysis with error recovery"""
        item_id = item_content["id"]

        async def analyze():
            return llm_client.classify(
                item_content["title"] or "",
                item_content["content"][:1200] if item_content.get("content") else ""
            )

        # Use circuit breaker and retry for OpenAI calls
        circuit_breaker = self.error_recovery.get_circuit_breaker(
            f"openai_{model_tag}",
            self.openai_breaker_config
        )

        try:
            llm_data = await self.error_recovery.execute_with_recovery(
                analyze,
                service_name=f"openai_{model_tag}",
                max_retries=3,
                circuit_breaker=True
            )

            # Process successful result
            self._save_analysis_result(queue_id, item_id, llm_data, model_tag)

        except Exception as e:
            error_code = self._classify_error(e)
            self._mark_item_failed(queue_id, error_code, str(e))
            logger.error(f"Failed to analyze item {item_id} after recovery attempts: {e}")

    def _process_item_analysis(self, queue_id: int, item_content: Dict[str, Any],
                              llm_client: LLMClient, model_tag: str) -> None:
        """Process actual analysis for an item"""
        # SPRINT 1 DAY 3: Track analysis duration
        start_time = time.time()

        try:
            item_id = item_content["id"]
            title = item_content["title"] or ""
            content = item_content["content"] or item_content["description"] or ""

            if not title.strip():
                self._mark_item_failed(queue_id, "EEMPTY", "Empty title")
                self.metrics.record_item_processed("failed", "manual")
                self.metrics.record_error("empty_title", "orchestrator")
                return

            # Prepare content for analysis (limit to 1200 chars)
            summary_text = content[:1200] if content else ""

            logger.debug(f"Analyzing item {item_id}: {title[:50]}...")

            # Call LLM for classification with retry
            # SPRINT 1 DAY 3: Track API call duration
            api_start = time.time()
            llm_data = self._call_llm_with_retry(llm_client, title, summary_text, model_tag)
            api_duration = time.time() - api_start
            self.metrics.api_request_duration.labels(model=model_tag).observe(api_duration)
            self.metrics.record_api_call(model_tag, "success")

            # Build analysis result
            sentiment = SentimentPayload(
                overall=Overall(**llm_data["overall"]),
                market=Market(**llm_data["market"]),
                urgency=float(llm_data["urgency"]),
                themes=llm_data.get("themes", [])[:6]
            )

            impact = ImpactPayload(**llm_data["impact"])

            # Parse geopolitical data (always present, may have zero values)
            geopolitical = None
            if "geopolitical" in llm_data:
                from app.domain.analysis.schema import GeopoliticalPayload
                try:
                    geopolitical = GeopoliticalPayload(**llm_data["geopolitical"])
                except Exception as e:
                    logger.warning(f"Failed to parse geopolitical data for item {item_id}: {e}")

            result = AnalysisResult(
                sentiment=sentiment,
                impact=impact,
                geopolitical=geopolitical,
                model_tag=model_tag
            )

            # Save analysis result
            AnalysisRepo.upsert(item_id, result)

            # Calculate cost
            tokens_used = AVG_TOKENS_PER_ITEM  # Estimate for now
            model_pricing = MODEL_PRICING.get(model_tag, MODEL_PRICING["gpt-4.1-nano"])
            cost_usd = (tokens_used * model_pricing["input"]) / 1_000_000

            # Mark item as completed
            self.queue_repo.update_item_state(
                queue_id, "completed",
                tokens_used=tokens_used,
                cost_usd=cost_usd
            )

            logger.info(f"✓ Analyzed item {item_id}: {sentiment.overall.label} sentiment, {impact.overall:.2f} impact")

            # SPRINT 1 DAY 3: Record successful completion
            analysis_duration = time.time() - start_time
            self.metrics.analysis_duration.observe(analysis_duration)
            self.metrics.record_item_processed("completed", "manual")

        except Exception as e:
            error_code = self._classify_error(e)
            self._mark_item_failed(queue_id, error_code, str(e))

            # SPRINT 1 DAY 3: Record failure
            self.metrics.record_item_processed("failed", "manual")
            self.metrics.record_error(error_code, "orchestrator")
            self.metrics.record_api_call(model_tag, "failure")

    def _process_item_dry_run(self, queue_id: int, item_content: Dict[str, Any], model_tag: str) -> None:
        """Process dry run for an item"""
        try:
            item_id = item_content["id"]
            title = item_content["title"] or ""

            if not title.strip():
                self._mark_item_failed(queue_id, "EEMPTY", "Empty title")
                return

            # Simulate processing
            time.sleep(0.1)  # Small delay to simulate processing

            # Mark as completed with simulated cost
            tokens_used = AVG_TOKENS_PER_ITEM
            model_pricing = MODEL_PRICING.get(model_tag, MODEL_PRICING["gpt-4.1-nano"])
            cost_usd = (tokens_used * model_pricing["input"]) / 1_000_000

            self.queue_repo.update_item_state(
                queue_id, "completed",
                tokens_used=tokens_used,
                cost_usd=cost_usd
            )

            logger.info(f"[DRY RUN] Would analyze item {item_id}: {title[:50]}...")

        except Exception as e:
            self._mark_item_failed(queue_id, "EUNKNOWN", str(e))

    def _mark_item_failed(self, queue_id: int, error_code: str, error_message: str) -> None:
        """Mark an item as failed with error classification"""
        self.queue_repo.update_item_state(queue_id, "failed", f"{error_code}: {error_message}")
        logger.error(f"Item failed with {error_code}: {error_message}")

    def _mark_item_skipped(self, queue_id: int, skip_reason: str) -> None:
        """Mark an item as skipped"""
        # SPRINT 1 DAY 3: Record skip metrics
        self.metrics.record_item_processed("skipped", "manual")

        from sqlmodel import Session, text
        from app.database import engine
        from datetime import datetime

        query = text("""
            UPDATE analysis_run_items
            SET state = 'skipped',
                skip_reason = :reason,
                skipped_at = :now,
                completed_at = :now
            WHERE id = :queue_id
        """)

        with Session(engine) as session:
            session.execute(query, {
                "queue_id": queue_id,
                "reason": skip_reason[:50],  # Truncate to field limit
                "now": datetime.utcnow()
            })
            session.commit()
            logger.info(f"Item {queue_id} marked as skipped: {skip_reason}")

    def _update_run_skip_stats(self, run_id: int, skipped_count: int) -> None:
        """Update run skip statistics"""
        from sqlmodel import Session, text
        from app.database import engine

        query = text("""
            UPDATE analysis_runs
            SET skipped_count = skipped_count + :count,
                updated_at = NOW()
            WHERE id = :run_id
        """)

        with Session(engine) as session:
            session.execute(query, {"run_id": run_id, "count": skipped_count})
            session.commit()
            logger.debug(f"Updated run {run_id} skip stats: +{skipped_count}")

    def _mark_run_started(self, run_id: int) -> None:
        """Mark run as started and set started_at if not already set"""
        from sqlmodel import Session, text
        from app.database import engine

        query = text("""
            UPDATE analysis_runs
            SET started_at = COALESCE(started_at, NOW()),
                status = CASE WHEN status = 'pending' THEN 'running' ELSE status END,
                updated_at = NOW()
            WHERE id = :run_id
        """)

        with Session(engine) as session:
            session.execute(query, {"run_id": run_id})
            session.commit()
            logger.debug(f"Marked run {run_id} as started")

    def _update_run_processed_count(self, run_id: int) -> None:
        """Update processed count based on completed items"""
        from sqlmodel import Session, text
        from app.database import engine

        query = text("""
            UPDATE analysis_runs ar
            SET processed_count = (
                    SELECT COUNT(*)
                    FROM analysis_run_items
                    WHERE run_id = ar.id AND state = 'completed'
                ),
                failed_count = (
                    SELECT COUNT(*)
                    FROM analysis_run_items
                    WHERE run_id = ar.id AND state = 'failed'
                ),
                updated_at = NOW()
            WHERE ar.id = :run_id
        """)

        with Session(engine) as session:
            session.execute(query, {"run_id": run_id})
            session.commit()
            logger.debug(f"Updated processed count for run {run_id}")

    def _call_llm_with_retry(self, llm_client: LLMClient, title: str, summary_text: str, model_tag: str) -> Dict:
        """Call LLM with retry logic and circuit breaker"""
        max_retries = 3
        retry_delay = 1.0

        for attempt in range(max_retries):
            try:
                # Get circuit breaker for this model
                circuit_breaker = self.error_recovery.get_circuit_breaker(
                    f"openai_{model_tag}",
                    self.openai_breaker_config
                )

                # Execute with circuit breaker
                return circuit_breaker.call(llm_client.classify, title, summary_text)

            except Exception as e:
                error_type = self._classify_error(e)

                # Handle specific error types
                if error_type == "E429":  # Rate limit
                    # Exponential backoff for rate limits
                    wait_time = retry_delay * (2 ** attempt)
                    logger.warning(f"Rate limited, waiting {wait_time}s before retry {attempt + 1}/{max_retries}")
                    time.sleep(wait_time)

                elif error_type == "E5xx":  # Server errors
                    # Longer wait for server recovery
                    wait_time = 10 * (attempt + 1)
                    logger.warning(f"Server error, waiting {wait_time}s before retry {attempt + 1}/{max_retries}")
                    time.sleep(wait_time)

                elif error_type == "ETIMEOUT":  # Timeout
                    # Quick retry for timeouts
                    wait_time = 2
                    logger.warning(f"Timeout, retrying in {wait_time}s (attempt {attempt + 1}/{max_retries})")
                    time.sleep(wait_time)

                elif attempt < max_retries - 1:
                    # Generic retry with backoff
                    wait_time = retry_delay * (attempt + 1)
                    logger.warning(f"Error {error_type}, retrying in {wait_time}s (attempt {attempt + 1}/{max_retries})")
                    time.sleep(wait_time)
                else:
                    # Final attempt failed
                    logger.error(f"All {max_retries} attempts failed for LLM call")
                    raise

        raise Exception(f"Failed after {max_retries} attempts")

    def _save_analysis_result(self, queue_id: int, item_id: int, llm_data: Dict, model_tag: str) -> None:
        """Save successful analysis result"""
        try:
            # Build analysis result
            sentiment = SentimentPayload(
                overall=Overall(**llm_data["overall"]),
                market=Market(**llm_data["market"]),
                urgency=float(llm_data["urgency"]),
                themes=llm_data.get("themes", [])[:6]
            )

            impact = ImpactPayload(**llm_data["impact"])

            # Parse geopolitical data (always present, may have zero values)
            geopolitical = None
            if "geopolitical" in llm_data:
                from app.domain.analysis.schema import GeopoliticalPayload
                try:
                    geopolitical = GeopoliticalPayload(**llm_data["geopolitical"])
                except Exception as e:
                    logger.warning(f"Failed to parse geopolitical data for item {item_id}: {e}")

            result = AnalysisResult(
                sentiment=sentiment,
                impact=impact,
                geopolitical=geopolitical,
                model_tag=model_tag
            )

            # Save analysis result
            AnalysisRepo.upsert(item_id, result)

            # Calculate cost
            tokens_used = AVG_TOKENS_PER_ITEM  # Estimate for now
            model_pricing = MODEL_PRICING.get(model_tag, MODEL_PRICING["gpt-4.1-nano"])
            cost_usd = (tokens_used * model_pricing["input"]) / 1_000_000

            # Mark item as completed
            self.queue_repo.update_item_state(
                queue_id, "completed",
                tokens_used=tokens_used,
                cost_usd=cost_usd
            )

            logger.info(f"✓ Analyzed item {item_id}: {sentiment.overall.label} sentiment, {impact.overall:.2f} impact")

        except Exception as e:
            logger.error(f"Failed to save analysis result for item {item_id}: {e}")
            raise

    def _classify_error(self, error: Exception) -> str:
        """Classify error into standard error codes"""
        error_str = str(error).lower()

        if "429" in error_str or "rate limit" in error_str:
            return "E429"
        elif "500" in error_str or "502" in error_str or "503" in error_str or "504" in error_str:
            return "E5xx"
        elif "parse" in error_str or "json" in error_str or "format" in error_str:
            return "EPARSE"
        elif "timeout" in error_str or "connection" in error_str:
            return "ETIMEOUT"
        elif "auth" in error_str or "api" in error_str:
            return "EAUTH"
        else:
            return "EUNKNOWN"

    def _throttle_requests(self, rate_per_second: float) -> None:
        """Apply rate limiting between requests"""
        if rate_per_second <= 0:
            return

        min_interval = 1.0 / rate_per_second
        current_time = time.time()
        time_since_last = current_time - self.last_request_time

        if time_since_last < min_interval:
            sleep_time = min_interval - time_since_last
            time.sleep(sleep_time)

        self.last_request_time = time.time()

    def check_already_analyzed(self, item_id: int, days: int = 7) -> tuple[bool, Optional[str]]:
        """
        Check if item was already analyzed (has results in item_analysis table).
        This is the source of truth for analysis completion.

        Returns: (is_analyzed, previous_run_id or 'existing')
        """
        from sqlmodel import Session, text
        from app.database import engine

        # IMPROVED: Check item_analysis table directly (source of truth)
        query = text("""
            SELECT
                ia.item_id,
                ia.updated_at
            FROM item_analysis ia
            WHERE ia.item_id = :item_id
            LIMIT 1
        """)

        with Session(engine) as session:
            result = session.execute(query, {"item_id": item_id}).first()
            if result:
                # Item has analysis results - skip it
                return True, "existing"
            return False, None

    def check_run_completion(self, run: Dict[str, Any]) -> bool:
        """Check if a run is completed and update status accordingly"""
        run_id = run["id"]
        metrics = self.queue_repo.get_run_metrics(run_id)

        if not metrics:
            return False

        # Check if all items are processed
        if metrics["queued_count"] == 0 and metrics["processing_count"] == 0:
            if metrics["total_count"] > 0:
                # Run is completed - update counts before status
                self._sync_run_counts(run_id)
                self.queue_repo.update_run_status(run_id, "completed")
                logger.info(f"Run {run_id} completed: {metrics['completed_count']}/{metrics['total_count']} items processed")
                return True
            else:
                # No items were queued, mark as completed anyway
                self.queue_repo.update_run_status(run_id, "completed")
                logger.info(f"Run {run_id} completed with no items")
                return True

        return False

    def _sync_run_counts(self, run_id: int) -> None:
        """Synchronize run counts from analysis_run_items to analysis_runs"""
        from sqlmodel import Session, text
        from app.database import engine

        with Session(engine) as session:
            query = text("""
                UPDATE analysis_runs
                SET
                    processed_count = (
                        SELECT COUNT(*)
                        FROM analysis_run_items
                        WHERE run_id = :run_id AND state = 'completed'
                    ),
                    failed_count = (
                        SELECT COUNT(*)
                        FROM analysis_run_items
                        WHERE run_id = :run_id AND state = 'failed'
                    )
                WHERE id = :run_id
            """)
            session.execute(query, {"run_id": run_id})
            session.commit()

    def reset_stale_items(self, stale_seconds: int = 300) -> int:
        """Reset stale processing items back to queued"""
        return self.queue_repo.reset_stale_processing_items(stale_seconds)

    def get_run_metrics(self, run_id: int) -> Dict[str, Any]:
        """Get current metrics for a run"""
        return self.queue_repo.get_run_metrics(run_id)