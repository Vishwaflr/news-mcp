# Claude CLI Playwright Configuration

## Problem
The "playwright-remote" MCP server is showing as failed in Claude CLI.

## Solution
We've installed Playwright MCP locally in the news-mcp project. To fix the error, you need to update your Claude CLI configuration.

## Steps to Fix

### 1. Remove Old playwright-remote Configuration

In your Claude CLI configuration, remove the "playwright-remote" server entry that is failing.

### 2. Add Local Playwright Configuration

Replace it with this local configuration:

```json
{
  "mcpServers": {
    "playwright-local": {
      "command": "/home/cytrex/news-mcp/scripts/start-playwright-mcp-local.sh",
      "args": []
    }
  }
}
```

Or if you prefer using npx directly:

```json
{
  "mcpServers": {
    "playwright-local": {
      "command": "npx",
      "args": ["@playwright/mcp"],
      "cwd": "/home/cytrex/news-mcp",
      "env": {
        "NODE_PATH": "/home/cytrex/news-mcp/node_modules"
      }
    }
  }
}
```

### 3. Restart Claude CLI

After updating the configuration:
1. Stop Claude CLI completely
2. Start it again
3. Run `/mcp` to verify "playwright-local" shows as connected

## Available Playwright Tools

Once connected, you'll have access to these MCP tools:

- `mcp__playwright-local__launch_browser` - Launch browser
- `mcp__playwright-local__navigate_to` - Navigate to URL
- `mcp__playwright-local__click_element` - Click elements
- `mcp__playwright-local__screenshot` - Take screenshots
- `mcp__playwright-local__get_text` - Extract text
- `mcp__playwright-local__close_browser` - Close browser

## Testing

Test with:
```
"Open http://192.168.178.72:8000/admin/analysis and take a screenshot"
```

## Troubleshooting

If still failing:

1. **Check Node/NPM**:
   ```bash
   node --version  # Should be 18+
   npm --version
   ```

2. **Reinstall packages**:
   ```bash
   cd /home/cytrex/news-mcp
   npm install
   npx playwright install chromium
   ```

3. **Test manually**:
   ```bash
   /home/cytrex/news-mcp/scripts/start-playwright-mcp-local.sh
   # Should wait for input (Ctrl+C to exit)
   ```

4. **Check logs**:
   Look for error messages in Claude CLI logs when starting up.

## Benefits of Local Setup

- No external dependencies
- Faster response times
- Direct access to local test environment
- Can test localhost URLs directly
- Integrated with news-mcp project