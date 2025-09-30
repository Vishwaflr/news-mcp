#!/bin/bash
# Start local Playwright MCP Server
# This replaces the external playwright-remote server

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

echo "Starting Playwright MCP Server locally..."
echo "=================================="
echo "Project Root: $PROJECT_ROOT"
echo "Node Modules: $PROJECT_ROOT/node_modules"
echo ""
echo "MCP Server Details:"
echo "- Package: @playwright/mcp v0.0.40"
echo "- Browsers: Chromium installed"
echo "- Mode: Local execution"
echo ""

# Export NODE_PATH for module resolution
export NODE_PATH="$PROJECT_ROOT/node_modules"

# Start the MCP server
echo "Starting server on stdio..."
npx @playwright/mcp