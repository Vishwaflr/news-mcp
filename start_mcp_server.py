#!/usr/bin/env python3
"""
Startup script for News MCP Server
Configures the server for LAN accessibility
"""

import asyncio
import logging
import sys
import os
from pathlib import Path

# Add the project root to the path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from mcp_server.comprehensive_server import ComprehensiveNewsServer

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def main():
    """Main startup function"""
    print("Starting News MCP Server for LAN access...", file=sys.stderr)
    logger.info("Starting News MCP Server for LAN access...")

    # Set environment variables for database access
    os.environ["PYTHONPATH"] = str(project_root)

    try:
        # Create and start the server
        print("Creating server instance...", file=sys.stderr)
        server = ComprehensiveNewsServer()
        print("Server instance created, starting...", file=sys.stderr)

        # For LAN access, the server runs over stdio/transport
        # The actual LAN connectivity is handled by the MCP client configuration
        await server.run()
    except Exception as e:
        print(f"Error in main: {e}", file=sys.stderr)
        raise

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Server shutdown requested")
    except Exception as e:
        logger.error(f"Server error: {e}")
        sys.exit(1)