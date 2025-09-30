#!/bin/bash
# Start Playwright MCP Server for Claude Desktop integration

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

echo "Starting Playwright MCP Server..."
echo "Project Root: $PROJECT_ROOT"

# Start the Playwright MCP server using npx
npx @playwright/mcp