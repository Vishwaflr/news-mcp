#!/usr/bin/env python3
"""
Analysis Worker - Processes analysis runs and items from the queue
"""

import os
import sys

# Add project root to Python path FIRST
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

import time
import signal
import asyncio
import logging
import argparse
import requests
from typing import Optional
from datetime import datetime
from app.core.logging_config import get_logger, setup_logging

from app.services.analysis_orchestrator import AnalysisOrchestrator
from app.services.queue_processor import get_queue_processor
from app.services.pending_analysis_processor import PendingAnalysisProcessor
from app.domain.analysis.control import MODEL_PRICING
from app.utils.feature_flags import feature_flags
from app.services.error_recovery import get_error_recovery_service, CircuitBreakerConfig
from app.worker.metrics_server import MetricsServer

# Configure structured logging
setup_logging(log_level="INFO")
logger = get_logger(__name__)

class AnalysisWorker:
    """Main analysis worker class"""

    def __init__(self):
        self.running = True
        self.orchestrator = None
        self.queue_processor = None
        self.pending_processor = None
        self.use_repository = False
        self.last_feature_flag_check = 0
        self.error_recovery = get_error_recovery_service()

        # SPRINT 1 DAY 4: Metrics server for Prometheus scraping
        self.metrics_server = None

        # Configure circuit breakers for different operations
        self.db_breaker = self.error_recovery.get_circuit_breaker(
            "worker_db",
            CircuitBreakerConfig(
                failure_threshold=10,
                success_threshold=3,
                timeout_seconds=30
            )
        )

        self._setup_signal_handlers()
        self._load_config()

    def _setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown"""
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, shutting down gracefully...")
            self.running = False

        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)

    def _load_config(self):
        """Load configuration from environment variables"""
        self.config = {
            'chunk_size': int(os.getenv('WORKER_CHUNK_SIZE', '10')),
            'sleep_interval': float(os.getenv('WORKER_SLEEP_INTERVAL', '5.0')),
            'heartbeat_interval': float(os.getenv('WORKER_HEARTBEAT_INTERVAL', '10.0')),
            'stale_processing_seconds': int(os.getenv('WORKER_STALE_PROCESSING_SEC', '300')),
            'min_request_interval': float(os.getenv('WORKER_MIN_REQUEST_INTERVAL', '0.5')),
            'max_runs_per_cycle': int(os.getenv('WORKER_MAX_RUNS_PER_CYCLE', '5')),
            'reset_stale_on_start': os.getenv('WORKER_RESET_STALE_ON_START', 'true').lower() == 'true',
            'use_repository': os.getenv('WORKER_USE_REPOSITORY', 'false').lower() == 'true',
            'feature_flag_check_interval': float(os.getenv('WORKER_FEATURE_FLAG_CHECK_INTERVAL', '30.0'))
        }

        logger.info(f"Worker config loaded: {self.config}")

    def start(self):
        """Start the worker main loop"""
        logger.info("Starting Analysis Worker")

        try:
            # SPRINT 1 DAY 4: Start metrics server for Prometheus
            metrics_port = int(os.getenv('WORKER_METRICS_PORT', '9090'))
            self.metrics_server = MetricsServer(port=metrics_port)
            self.metrics_server.start()

            # Initialize orchestrator
            self.orchestrator = AnalysisOrchestrator(
                chunk_size=self.config['chunk_size'],
                min_request_interval=self.config['min_request_interval']
            )

            # Initialize queue processor
            self.queue_processor = get_queue_processor()

            # Initialize pending analysis processor
            self.pending_processor = PendingAnalysisProcessor()

            # Reset stale items on startup if configured
            if self.config['reset_stale_on_start']:
                stale_count = self.orchestrator.reset_stale_items(self.config['stale_processing_seconds'])
                if stale_count > 0:
                    logger.info(f"Reset {stale_count} stale processing items on startup")

            last_heartbeat = 0
            last_stale_reset = 0

            logger.info("Worker main loop started")

            while self.running:
                cycle_start = time.time()

                try:
                    # Process analysis runs
                    work_done = self._process_work_cycle()

                    # Periodic maintenance
                    current_time = time.time()

                    # Heartbeat and stale reset
                    if current_time - last_heartbeat > self.config['heartbeat_interval']:
                        self._periodic_maintenance()
                        last_heartbeat = current_time

                    if current_time - last_stale_reset > self.config['stale_processing_seconds']:
                        self.orchestrator.reset_stale_items(self.config['stale_processing_seconds'])
                        last_stale_reset = current_time

                    # Sleep if no work was done
                    if not work_done:
                        logger.debug("No work to do, sleeping...")
                        time.sleep(self.config['sleep_interval'])

                except Exception as e:
                    logger.error(f"Error in work cycle: {e}", exc_info=True)
                    time.sleep(self.config['sleep_interval'])

        except KeyboardInterrupt:
            logger.info("Worker interrupted by user")
        except Exception as e:
            logger.error(f"Worker failed: {e}", exc_info=True)
            raise
        finally:
            # SPRINT 1 DAY 4: Stop metrics server
            if self.metrics_server:
                self.metrics_server.stop()
            logger.info("Analysis Worker stopped")

    def _process_work_cycle(self) -> bool:
        """Process one work cycle, returns True if work was done"""
        work_done = False

        try:
            # First, process pending auto-analysis jobs
            if self.pending_processor:
                try:
                    pending_processed = asyncio.run(self.pending_processor.process_pending_queue())
                    if pending_processed > 0:
                        logger.info(f"Processed {pending_processed} pending auto-analysis jobs")
                        work_done = True
                except Exception as e:
                    logger.error(f"Error processing pending auto-analysis: {e}")

            # Second, try to process queued runs (start new runs from queue)
            if self.queue_processor:
                try:
                    # Use asyncio.run for cleaner async execution in sync context
                    queue_result = asyncio.run(self.queue_processor.process_queue())
                    if queue_result:
                        logger.info(f"Started new run from queue: analysis_run_id={queue_result.get('analysis_run_id')}")
                        work_done = True
                except Exception as e:
                    logger.error(f"Error processing queue: {e}")

            # Then, get available runs (existing running runs that need item processing)
            runs = self.orchestrator.get_available_runs()

            if not runs:
                logger.debug("No runs available for processing")
                return work_done

            # Limit number of runs processed per cycle
            runs = runs[:self.config['max_runs_per_cycle']]

            for run in runs:
                if not self.running:
                    break

                try:
                    work_done |= self._process_single_run(run)
                except Exception as e:
                    logger.error(f"Error processing run {run['id']}: {e}")

        except Exception as e:
            logger.error(f"Error in work cycle: {e}")

        return work_done

    def _process_single_run(self, run: dict) -> bool:
        """Process a single run, returns True if work was done"""
        run_id = run["id"]
        status = run["status"]

        logger.debug(f"Processing run {run_id} with status {status}")

        try:
            # Start pending runs with error recovery
            if status == "pending":
                try:
                    # Use circuit breaker for database operations
                    started = self.db_breaker.call(self.orchestrator.start_run, run)
                    if started:
                        logger.info(f"Started run {run_id}")
                        run["status"] = "running"  # Update local status
                    else:
                        logger.warning(f"Failed to start run {run_id}")
                        return False
                except Exception as e:
                    logger.error(f"Circuit breaker blocked or failed starting run {run_id}: {e}")
                    return False

            # Process items for running runs
            if run["status"] == "running":
                processed_count = self.orchestrator.process_run_items(run)

                if processed_count > 0:
                    logger.info(f"Processed {processed_count} items for run {run_id}")

                # Check if run is completed
                if self.orchestrator.check_run_completion(run):
                    logger.info(f"Run {run_id} completed")

                return processed_count > 0

        except Exception as e:
            logger.error(f"Error processing run {run_id}: {e}")

        return False

    def _check_feature_flags(self):
        """Check if repository usage should be enabled via feature flags"""
        current_time = time.time()

        if current_time - self.last_feature_flag_check < self.config['feature_flag_check_interval']:
            return

        try:
            # Check analysis_repo feature flag
            flag_status = feature_flags.get_flag_status('analysis_repo')

            if flag_status:
                status = flag_status.get('status')
                rollout_percentage = flag_status.get('rollout_percentage', 0)

                # Check if we should use repository based on flag status
                should_use_repo = False

                if status == 'on':
                    should_use_repo = True
                elif status == 'canary' and rollout_percentage > 0:
                    # Simple hash-based rollout (could be more sophisticated)
                    worker_hash = hash(os.getpid()) % 100
                    should_use_repo = worker_hash < rollout_percentage
                elif status == 'emergency_off':
                    should_use_repo = False

                if should_use_repo != self.use_repository:
                    logger.info(f"Repository usage changing: {self.use_repository} -> {should_use_repo}")
                    self.use_repository = should_use_repo

                    # Reinitialize orchestrator with new mode
                    if self.orchestrator:
                        self.orchestrator.set_repository_mode(should_use_repo)

            self.last_feature_flag_check = current_time

        except Exception as e:
            logger.error(f"Error checking feature flags: {e}")

    def _periodic_maintenance(self):
        """Perform periodic maintenance tasks"""
        try:
            logger.debug("Performing periodic maintenance")

            # Check feature flags for repository usage
            self._check_feature_flags()

            # Check emergency stop status and pause/resume queue processing
            if self.queue_processor:
                try:
                    from app.services.analysis_run_manager import get_run_manager
                    run_manager = get_run_manager()
                    status = run_manager.get_status()

                    emergency_stop = status.get("emergency_stop", False)

                    if emergency_stop and self.queue_processor.is_processing_active():
                        logger.warning("Emergency stop detected, pausing queue processing")
                        self.queue_processor.pause_processing()
                    elif not emergency_stop and not self.queue_processor.is_processing_active():
                        logger.info("Emergency stop cleared, resuming queue processing")
                        self.queue_processor.resume_processing()

                except Exception as e:
                    logger.error(f"Error checking emergency stop status: {e}")

            # Additional maintenance tasks can be added here

        except Exception as e:
            logger.error(f"Error in periodic maintenance: {e}")

    def stop(self):
        """Stop the worker"""
        self.running = False
        logger.info("Worker stop requested")


def main():
    """CLI entry point"""
    parser = argparse.ArgumentParser(description='News Analysis Worker')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose logging')
    parser.add_argument('--dry-run', action='store_true',
                       help='Run in dry-run mode without processing')

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Load environment variables
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        logger.warning("python-dotenv not available, skipping .env file loading")

    # Validate required environment variables
    required_env_vars = ['DATABASE_URL', 'OPENAI_API_KEY']
    missing_vars = [var for var in required_env_vars if not os.getenv(var)]
    if missing_vars:
        logger.error(f"Missing required environment variables: {missing_vars}")
        sys.exit(1)

    if args.dry_run:
        logger.info("Running in dry-run mode")
        # Could add dry-run specific logic here
        return

    try:
        worker = AnalysisWorker()
        worker.start()
    except KeyboardInterrupt:
        logger.info("Worker interrupted by user")
    except Exception as e:
        logger.error(f"Worker failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()