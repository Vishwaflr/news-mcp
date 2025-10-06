# Playwright MCP Setup Guide

## Overview

Playwright MCP integration allows Claude Code to autonomously test the frontend by controlling a browser through the Model Context Protocol.

## Installation

The Playwright MCP server has been installed locally in this project.

### Packages Installed
```json
{
  "@playwright/mcp": "^0.0.40",
  "@playwright/test": "^1.55.1",
  "playwright": "^1.55.1"
}
```

### Browser Installation
- Chromium browser installed via: `npx playwright install chromium`
- System dependencies installed via: `npx playwright install-deps chromium`

## Configuration for Claude Desktop

To enable Playwright tools in Claude Desktop (where this session runs), add the following to your Claude Desktop configuration:

**File**: `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS)
or `~/.config/Claude/claude_desktop_config.json` (Linux)

```json
{
  "mcpServers": {
    "playwright": {
      "command": "node",
      "args": [
        "/home/cytrex/news-mcp/node_modules/@playwright/mcp/dist/index.js"
      ]
    },
    "news-mcp": {
      "command": "node",
      "args": ["/home/cytrex/news-mcp/mcp-http-bridge.js"],
      "env": {
        "NEWS_MCP_SERVER_URL": "http://localhost:8001"
      }
    }
  }
}
```

## Available Playwright Tools

After configuration, the following MCP tools will be available:

### Browser Control
- `playwright_launch_browser` - Launch browser instance
- `playwright_navigate` - Navigate to URL
- `playwright_close_browser` - Close browser

### Page Interaction
- `playwright_click` - Click on elements
- `playwright_fill` - Fill form inputs
- `playwright_screenshot` - Take page screenshots
- `playwright_get_text` - Extract text from page

### Testing Capabilities
- Navigate to http://192.168.178.72:8000/admin/analysis
- Verify navigation elements are present
- Test form interactions
- Capture screenshots for documentation
- Verify HTMX updates and Alpine.js functionality

## Usage Example

Once configured in Claude Desktop and restarted, you can ask:

```
"Open the Analysis Cockpit page and verify the navigation is working"
"Take a screenshot of the Manager Dashboard"
"Click the Latest tab in Analysis Cockpit and verify it loads articles"
"Test the Auto-Analysis toggle on the feeds page"
```

## Troubleshooting

### Browser not launching
```bash
# Verify Chromium is installed
npx playwright --version

# Reinstall if needed
npx playwright install chromium
```

### Permission errors
```bash
# Fix permissions
chmod +x scripts/start-playwright-mcp.sh
```

### System dependencies missing
```bash
# Install on Ubuntu/Debian
sudo npx playwright install-deps chromium
```

## Testing Frontend Features

With Playwright MCP, Claude can autonomously:

1. **Navigation Testing**
   - Verify all nav links work
   - Check active states on pages
   - Test responsive navigation

2. **Form Testing**
   - Fill and submit analysis forms
   - Toggle feed settings
   - Test validation

3. **Visual Regression**
   - Take screenshots before/after changes
   - Verify UI consistency
   - Document features

4. **Interactive Testing**
   - Test HTMX live updates
   - Verify Alpine.js state management
   - Check WebSocket connections

5. **Cross-Page Workflows**
   - Navigate from dashboard to analysis
   - Create feed → Start analysis → View results
   - Test complete user journeys

## Next Steps

1. Add Playwright configuration to Claude Desktop
2. Restart Claude Desktop
3. Ask Claude to test specific frontend features
4. Use screenshots for documentation and bug reports