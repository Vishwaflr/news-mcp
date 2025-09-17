#!/usr/bin/env python3
"""
TCP-enabled News MCP Server for LAN access
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
    """Main startup function for TCP server"""
    logger.info("Starting News MCP Server for TCP access...")

    # Set environment variables for database access
    os.environ["PYTHONPATH"] = str(project_root)

    # Create and start the server
    server = ComprehensiveNewsServer()

    # Start TCP server on port 8765
    from mcp.server.sse import SseServerTransport
    from mcp.server.stdio import StdioServerTransport

    logger.info("Starting MCP server on port 8765...")

    async def handle_client(reader, writer):
        transport = StdioServerTransport(reader, writer)
        await server.server.run(transport, transport)

    tcp_server = await asyncio.start_server(handle_client, '0.0.0.0', 8765)

    logger.info("MCP server listening on port 8765")

    async with tcp_server:
        await tcp_server.serve_forever()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Server shutdown requested")
    except Exception as e:
        logger.error(f"Server error: {e}")
        sys.exit(1)