import time
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

from app.repositories.analysis_queue import AnalysisQueueRepo
from app.repositories.analysis import AnalysisRepo
from app.services.llm_client import LLMClient
from app.domain.analysis.schema import AnalysisResult, Overall, Market, SentimentPayload, ImpactPayload
from app.domain.analysis.control import MODEL_PRICING, AVG_TOKENS_PER_ITEM

logger = logging.getLogger(__name__)

class AnalysisOrchestrator:
    """Orchestrates analysis runs and manages item processing"""

    def __init__(self, chunk_size: int = 10, min_request_interval: float = 1.0):
        self.chunk_size = chunk_size
        self.min_request_interval = min_request_interval
        self.last_request_time = 0.0
        self.queue_repo = AnalysisQueueRepo()

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

        for item_info in claimed_items:
            queue_id = item_info["queue_id"]
            item_id = item_info["item_id"]

            try:
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

        # Update run heartbeat
        self.queue_repo.heartbeat_run(run_id)

        return processed_count

    def _process_item_analysis(self, queue_id: int, item_content: Dict[str, Any],
                              llm_client: LLMClient, model_tag: str) -> None:
        """Process actual analysis for an item"""
        try:
            item_id = item_content["id"]
            title = item_content["title"] or ""
            content = item_content["content"] or item_content["description"] or ""

            if not title.strip():
                self._mark_item_failed(queue_id, "EEMPTY", "Empty title")
                return

            # Prepare content for analysis (limit to 1200 chars)
            summary_text = content[:1200] if content else ""

            logger.debug(f"Analyzing item {item_id}: {title[:50]}...")

            # Call LLM for classification
            llm_data = llm_client.classify(title, summary_text)

            # Build analysis result
            sentiment = SentimentPayload(
                overall=Overall(**llm_data["overall"]),
                market=Market(**llm_data["market"]),
                urgency=float(llm_data["urgency"]),
                themes=llm_data.get("themes", [])[:6]
            )

            impact = ImpactPayload(**llm_data["impact"])

            result = AnalysisResult(
                sentiment=sentiment,
                impact=impact,
                model_tag=model_tag
            )

            # Save analysis result
            AnalysisRepo.upsert(item_id, result)

            # Calculate cost
            tokens_used = AVG_TOKENS_PER_ITEM  # Estimate for now
            model_pricing = MODEL_PRICING.get(model_tag, MODEL_PRICING["gpt-4.1-nano"])
            cost_usd = (tokens_used * model_pricing["input"]) / 1000

            # Mark item as completed
            self.queue_repo.update_item_state(
                queue_id, "completed",
                tokens_used=tokens_used,
                cost_usd=cost_usd
            )

            logger.info(f"✓ Analyzed item {item_id}: {sentiment.overall.label} sentiment, {impact.overall:.2f} impact")

        except Exception as e:
            error_code = self._classify_error(e)
            self._mark_item_failed(queue_id, error_code, str(e))

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
            cost_usd = (tokens_used * model_pricing["input"]) / 1000

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

    def check_run_completion(self, run: Dict[str, Any]) -> bool:
        """Check if a run is completed and update status accordingly"""
        run_id = run["id"]
        metrics = self.queue_repo.get_run_metrics(run_id)

        if not metrics:
            return False

        # Check if all items are processed
        if metrics["queued_count"] == 0 and metrics["processing_count"] == 0:
            if metrics["total_count"] > 0:
                # Run is completed
                self.queue_repo.update_run_status(run_id, "completed")
                logger.info(f"Run {run_id} completed: {metrics['completed_count']}/{metrics['total_count']} items processed")
                return True
            else:
                # No items were queued, mark as completed anyway
                self.queue_repo.update_run_status(run_id, "completed")
                logger.info(f"Run {run_id} completed with no items")
                return True

        return False

    def reset_stale_items(self, stale_seconds: int = 300) -> int:
        """Reset stale processing items back to queued"""
        return self.queue_repo.reset_stale_processing_items(stale_seconds)

    def get_run_metrics(self, run_id: int) -> Dict[str, Any]:
        """Get current metrics for a run"""
        return self.queue_repo.get_run_metrics(run_id)