#!/usr/bin/env python3
"""
Scheduler Management Script

Main entry point for running and managing the dynamic scheduler.
Provides commands for starting, stopping, and monitoring the scheduler.
"""
import asyncio
import argparse
import logging
import sys
import json
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from jobs.dynamic_scheduler import DynamicScheduler
from app.services.configuration_watcher import get_configuration_status

def setup_logging(level: str = "INFO"):
    """Setup logging configuration"""
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('/tmp/news-mcp-scheduler.log')
        ]
    )

async def start_scheduler(args):
    """Start the dynamic scheduler"""
    print("🚀 Starting News MCP Dynamic Scheduler...")

    scheduler = DynamicScheduler(
        instance_id=args.instance_id,
        config_check_interval=args.config_interval
    )

    try:
        await scheduler.start()
    except KeyboardInterrupt:
        print("\n⏹️  Scheduler stopped by user")
    except Exception as e:
        print(f"❌ Scheduler failed: {e}")
        sys.exit(1)

async def status_command(args):
    """Show scheduler status"""
    print("📊 News MCP Scheduler Status")
    print("=" * 40)

    try:
        # Get configuration status
        config_status = get_configuration_status(args.instance_id)

        print(f"Instance ID: {config_status['scheduler_instance']}")
        print(f"Active: {config_status['scheduler_active']}")
        print(f"Feeds: {config_status['feeds']}")
        print(f"Templates: {config_status['templates']}")
        print(f"Active Assignments: {config_status['active_assignments']}")
        print(f"Unprocessed Changes: {config_status['unprocessed_changes']}")

        if config_status['last_heartbeat']:
            print(f"Last Heartbeat: {config_status['last_heartbeat']}")
        else:
            print("Last Heartbeat: Never")

        if config_status['last_config_check']:
            print(f"Last Config Check: {config_status['last_config_check']}")
        else:
            print("Last Config Check: Never")

        # Configuration drift
        drift = config_status.get('configuration_drift', {})
        if drift.get('feed_config_changed') or drift.get('template_config_changed'):
            print("\n⚠️  Configuration Drift Detected:")
            if drift.get('feed_config_changed'):
                print("  - Feed configuration has changed")
            if drift.get('template_config_changed'):
                print("  - Template configuration has changed")
        else:
            print("\n✅ Configuration is up to date")

    except Exception as e:
        print(f"❌ Error getting status: {e}")
        sys.exit(1)

async def config_command(args):
    """Show detailed configuration"""
    try:
        config_status = get_configuration_status(args.instance_id)

        if args.format == 'json':
            print(json.dumps(config_status, indent=2, default=str))
        else:
            print("📋 Detailed Configuration Status")
            print("=" * 50)

            for key, value in config_status.items():
                if isinstance(value, dict):
                    print(f"\n{key.upper()}:")
                    for subkey, subvalue in value.items():
                        print(f"  {subkey}: {subvalue}")
                else:
                    print(f"{key}: {value}")

    except Exception as e:
        print(f"❌ Error getting configuration: {e}")
        sys.exit(1)

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="News MCP Dynamic Scheduler Management",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python jobs/scheduler_manager.py start                 # Start scheduler
  python jobs/scheduler_manager.py start --debug        # Start with debug logging
  python jobs/scheduler_manager.py status               # Show status
  python jobs/scheduler_manager.py config               # Show configuration
  python jobs/scheduler_manager.py config --json        # Show configuration as JSON
        """
    )

    parser.add_argument(
        '--instance-id',
        default='dynamic_scheduler',
        help='Scheduler instance ID (default: dynamic_scheduler)'
    )

    parser.add_argument(
        '--log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default='INFO',
        help='Logging level (default: INFO)'
    )

    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # Start command
    start_parser = subparsers.add_parser('start', help='Start the scheduler')
    start_parser.add_argument(
        '--config-interval',
        type=int,
        default=30,
        help='Configuration check interval in seconds (default: 30)'
    )
    start_parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug logging'
    )

    # Status command
    status_parser = subparsers.add_parser('status', help='Show scheduler status')

    # Config command
    config_parser = subparsers.add_parser('config', help='Show configuration')
    config_parser.add_argument(
        '--format',
        choices=['text', 'json'],
        default='text',
        help='Output format (default: text)'
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Setup logging
    log_level = 'DEBUG' if getattr(args, 'debug', False) else args.log_level
    setup_logging(log_level)

    # Execute command
    if args.command == 'start':
        asyncio.run(start_scheduler(args))
    elif args.command == 'status':
        asyncio.run(status_command(args))
    elif args.command == 'config':
        asyncio.run(config_command(args))


if __name__ == "__main__":
    main()