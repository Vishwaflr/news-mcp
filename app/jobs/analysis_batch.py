import argparse
from app.core.logging_config import get_logger
import os
from datetime import datetime
from typing import List

from app.services.llm_client import LLMClient
from app.repositories.analysis import AnalysisRepo
from app.domain.analysis.schema import (
    AnalysisResult, Overall, Market, SentimentPayload, ImpactPayload
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = get_logger(__name__)

BATCH_LIMIT_DEFAULT = 200
MODEL_TAG = os.getenv('ANALYSIS_MODEL', 'gpt-4o-mini')
ANALYSIS_RPS = float(os.getenv('ANALYSIS_RPS', '1.0'))

def process_item_analysis(item: dict, llm_client: LLMClient, dry_run: bool = False) -> bool:
    """Process analysis for a single item"""
    try:
        item_id = item['id']
        title = item['title'] or ''
        content = item['content'] or item['description'] or ''

        if not title.strip():
            logger.warning(f"Skipping item {item_id}: empty title")
            return False

        # Prepare content for analysis (limit to 1200 chars)
        summary_text = content[:1200] if content else ''

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
            model_tag=MODEL_TAG
        )

        if not dry_run:
            AnalysisRepo.upsert(item_id, result)
            logger.info(f"✓ Analyzed item {item_id}: {sentiment.overall.label} sentiment, {impact.overall:.2f} impact")
        else:
            logger.info(f"[DRY RUN] Would analyze item {item_id}: {sentiment.overall.label} sentiment, {impact.overall:.2f} impact")

        return True

    except Exception as e:
        logger.error(f"Failed to analyze item {item.get('id', 'unknown')}: {e}")
        return False

def run_analysis_batch(limit: int = BATCH_LIMIT_DEFAULT, dry_run: bool = False) -> dict:
    """Run batch analysis on items without analysis"""
    start_time = datetime.now()

    logger.info(f"Starting analysis batch (limit={limit}, dry_run={dry_run})")

    try:
        # Get items that need analysis
        items = AnalysisRepo.get_items_without_analysis(limit=limit)
        total_items = len(items)

        if total_items == 0:
            logger.info("No items found requiring analysis")
            return {
                "status": "success",
                "total_items": 0,
                "processed": 0,
                "errors": 0,
                "duration_seconds": 0
            }

        logger.info(f"Found {total_items} items requiring analysis")

        # Initialize LLM client
        llm_client = LLMClient(
            model=MODEL_TAG,
            rate_per_sec=ANALYSIS_RPS,
            timeout=8
        )

        # Process items
        processed_count = 0
        error_count = 0

        for i, item in enumerate(items, 1):
            logger.info(f"Processing item {i}/{total_items}: {item['title'][:60]}...")

            try:
                success = process_item_analysis(item, llm_client, dry_run)
                if success:
                    processed_count += 1
                else:
                    error_count += 1

            except KeyboardInterrupt:
                logger.warning("Batch processing interrupted by user")
                break
            except Exception as e:
                logger.error(f"Unexpected error processing item {item.get('id', 'unknown')}: {e}")
                error_count += 1

        duration = (datetime.now() - start_time).total_seconds()

        result = {
            "status": "success",
            "total_items": total_items,
            "processed": processed_count,
            "errors": error_count,
            "duration_seconds": duration
        }

        logger.info(f"Batch completed: {processed_count}/{total_items} processed, {error_count} errors, {duration:.1f}s")
        return result

    except Exception as e:
        duration = (datetime.now() - start_time).total_seconds()
        logger.error(f"Batch analysis failed: {e}")
        return {
            "status": "error",
            "error": str(e),
            "duration_seconds": duration
        }

def main():
    """CLI entry point"""
    parser = argparse.ArgumentParser(description='Run news item analysis batch job')
    parser.add_argument('--limit', type=int, default=BATCH_LIMIT_DEFAULT,
                       help=f'Maximum items to process (default: {BATCH_LIMIT_DEFAULT})')
    parser.add_argument('--dry-run', action='store_true',
                       help='Run without actually saving analysis results')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose logging')

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()

    try:
        result = run_analysis_batch(limit=args.limit, dry_run=args.dry_run)

        if result["status"] == "success":
            print(f"✓ Batch completed successfully:")
            print(f"  Processed: {result['processed']}/{result['total_items']}")
            print(f"  Errors: {result['errors']}")
            print(f"  Duration: {result['duration_seconds']:.1f}s")
        else:
            print(f"✗ Batch failed: {result.get('error', 'Unknown error')}")
            exit(1)

    except KeyboardInterrupt:
        print("\n⚠ Batch interrupted by user")
        exit(1)
    except Exception as e:
        print(f"✗ Fatal error: {e}")
        exit(1)

if __name__ == "__main__":
    main()