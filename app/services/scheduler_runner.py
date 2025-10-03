#!/usr/bin/env python3
"""
Feed Scheduler Runner - Standalone scheduler service
"""

import os
import sys
import signal
import asyncio
import logging

# Add project root to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app.core.logging_config import get_logger, setup_logging
from app.services.feed_scheduler import get_scheduler

# Configure logging
setup_logging(log_level="INFO")
logger = get_logger(__name__)

# Global scheduler reference for signal handlers
scheduler = None
shutdown_event = asyncio.Event()


def signal_handler(signum, frame):
    """Handle shutdown signals"""
    logger.info(f"Received signal {signum}, shutting down...")
    shutdown_event.set()


async def main():
    """Main scheduler loop"""
    global scheduler

    # Setup signal handlers
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    logger.info("Starting Feed Scheduler Service")

    try:
        # Load environment variables
        try:
            from dotenv import load_dotenv
            load_dotenv()
        except ImportError:
            logger.warning("python-dotenv not available, skipping .env file loading")

        # Validate required environment variables
        required_env_vars = ['DATABASE_URL']
        missing_vars = [var for var in required_env_vars if not os.getenv(var)]
        if missing_vars:
            logger.error(f"Missing required environment variables: {missing_vars}")
            sys.exit(1)

        # Get scheduler instance
        scheduler = get_scheduler()

        # Start scheduler in background task
        scheduler_task = asyncio.create_task(scheduler.start())

        # Wait for shutdown signal
        await shutdown_event.wait()

        # Stop scheduler
        logger.info("Stopping scheduler...")
        await scheduler.stop()

        # Wait for scheduler task to complete
        await scheduler_task

        logger.info("Feed Scheduler Service stopped cleanly")

    except KeyboardInterrupt:
        logger.info("Scheduler interrupted by user")
    except Exception as e:
        logger.error(f"Scheduler failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
