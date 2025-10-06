# Playwright E2E Testing Guide

**Last Updated:** 2025-10-05
**Purpose:** Local end-to-end testing of the News-MCP frontend
**Status:** ✅ Active (10 test files)

---

## Overview

Playwright is installed locally in this project for automated browser testing. It is used exclusively for testing frontend features, NOT for web scraping or MCP integration.

---

## Installation Status

### Installed Packages
```json
{
  "@playwright/test": "^1.55.1",
  "playwright": "^1.55.1"
}
```

### Browsers Installed
- ✅ Chromium (via `npx playwright install chromium`)
- ✅ System dependencies installed

---

## Running Tests

### Run All E2E Tests
```bash
cd /home/cytrex/news-mcp
npx playwright test tests/e2e/
```

### Run Specific Test File
```bash
npx playwright test tests/e2e/feed-buttons.spec.js
```

### Run in UI Mode (Interactive)
```bash
npx playwright test --ui
```

### Run with Debug Mode
```bash
npx playwright test --debug
```

### Generate HTML Report
```bash
npx playwright test
npx playwright show-report
```

---

## Available Test Files

Located in `/home/cytrex/news-mcp/tests/e2e/`:

1. **smoke-test.spec.js** - Basic page load verification
2. **feed-buttons.spec.js** - Feed management UI tests
3. **feed-fixes.spec.js** - Feed configuration tests
4. **items-sidebar.spec.js** - Article sidebar tests
5. **analysis-config.spec.js** - Analysis configuration UI
6. **auto-analysis.spec.js** - Auto-analysis toggle tests
7. **processors.spec.js** - Content processor tests
8. **special-reports-edit.spec.js** - Special Reports editor tests

---

## Test Structure Example

```javascript
const { test, expect } = require('@playwright/test');

test('verify feeds page loads', async ({ page }) => {
  await page.goto('http://192.168.178.72:8000/admin/feeds');

  // Check page title
  await expect(page).toHaveTitle(/Feeds/);

  // Verify navigation
  const nav = page.locator('nav.navbar');
  await expect(nav).toBeVisible();

  // Take screenshot
  await page.screenshot({ path: '/tmp/feeds-page.png' });
});
```

---

## Configuration

Playwright config is in `playwright.config.js` (if exists) or uses defaults.

Default settings:
- **Base URL:** `http://192.168.178.72:8000`
- **Timeout:** 30 seconds
- **Browser:** Chromium (headless)
- **Retries:** 2 (on CI), 0 (locally)

---

## Common Tasks

### Test Frontend Feature
```bash
# Example: Test Special Reports edit page
npx playwright test tests/e2e/special-reports-edit.spec.js --reporter=line
```

### Take Screenshot for Documentation
```javascript
await page.screenshot({
  path: '/tmp/feature-screenshot.png',
  fullPage: true
});
```

### Verify HTMX Updates
```javascript
// Click button that triggers HTMX
await page.click('#toggle-feed-1');

// Wait for HTMX swap
await page.waitForSelector('#feed-status-1');

// Verify updated content
const status = await page.locator('#feed-status-1').textContent();
expect(status).toBe('Active');
```

### Test Console Errors
```javascript
const consoleErrors = [];
page.on('console', msg => {
  if (msg.type() === 'error') {
    consoleErrors.push(msg.text());
  }
});

await page.goto('http://192.168.178.72:8000/admin/feeds');

// Verify no console errors
expect(consoleErrors).toHaveLength(0);
```

---

## Troubleshooting

### Browser not launching
```bash
# Reinstall Chromium
npx playwright install chromium

# Install system dependencies
npx playwright install-deps chromium
```

### Test timeout
```javascript
// Increase timeout for slow operations
test('slow operation', async ({ page }) => {
  test.setTimeout(60000); // 60 seconds

  await page.goto('http://192.168.178.72:8000/admin/analysis');
});
```

### Debugging Failed Tests
```bash
# Run in headed mode (see browser)
npx playwright test --headed

# Run with slow motion
npx playwright test --headed --slow-mo=1000

# Run specific test in debug mode
npx playwright test tests/e2e/feed-buttons.spec.js --debug
```

---

## Best Practices

### 1. Use Locators
```javascript
// ❌ Bad - fragile selector
await page.click('div > button:nth-child(3)');

// ✅ Good - semantic selector
await page.click('button[data-testid="add-feed"]');
```

### 2. Wait for Elements
```javascript
// ❌ Bad - arbitrary timeout
await page.waitForTimeout(2000);

// ✅ Good - wait for specific condition
await page.waitForSelector('#feed-list');
await page.waitForLoadState('networkidle');
```

### 3. Isolate Tests
```javascript
test.beforeEach(async ({ page }) => {
  // Reset state before each test
  await page.goto('http://192.168.178.72:8000/admin/feeds');
});

test.afterEach(async ({ page }) => {
  // Clean up after test
  await page.close();
});
```

### 4. Test User Journeys, Not Implementation
```javascript
// ❌ Bad - testing implementation details
test('verify HTMX swap happens', async ({ page }) => {
  await page.click('#button');
  await expect(page.locator('[hx-swap-oob]')).toBeVisible();
});

// ✅ Good - testing user-visible behavior
test('adding feed shows success message', async ({ page }) => {
  await page.fill('#feed-url', 'https://example.com/feed');
  await page.click('#add-feed-btn');
  await expect(page.locator('.alert-success')).toContainText('Feed added');
});
```

---

## NOT for MCP or Web Scraping

**Important:** This Playwright installation is for **E2E testing only**.

For web scraping or MCP integration:
- Use Python libraries (httpx, BeautifulSoup, readability)
- Consider Playwright Python bindings if JavaScript rendering is needed
- See separate documentation for scraper architecture

---

## Related Documentation

- [E2E Test Files](/home/cytrex/news-mcp/tests/e2e/)
- [Playwright Official Docs](https://playwright.dev/)
- [Frontend Testing Best Practices](https://playwright.dev/docs/best-practices)

---

## Maintenance

### Update Playwright
```bash
npm update @playwright/test playwright
npx playwright install chromium
```

### Check Version
```bash
npx playwright --version
```

### Clean Test Artifacts
```bash
rm -rf test-results/
rm -rf playwright-report/
```
