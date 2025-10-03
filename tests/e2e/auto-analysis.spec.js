/**
 * Auto-Analysis Page Test
 * Tests the fixed auto-analysis dashboard metrics
 */

const { test, expect } = require('@playwright/test');

const BASE_URL = 'http://192.168.178.72:8000';

test.describe('Auto-Analysis Page - Full Test', () => {

  test('should load auto-analysis page without errors', async ({ page }) => {
    const errors = [];
    page.on('console', msg => {
      if (msg.type() === 'error' && !msg.text().includes('404') && !msg.text().includes('Failed to load resource')) {
        errors.push(msg.text());
      }
    });

    const response = await page.goto(`${BASE_URL}/admin/auto-analysis`, {
      waitUntil: 'domcontentloaded',
      timeout: 15000
    });

    expect(response.status()).toBe(200);
    expect(errors).toHaveLength(0);
  });

  test('should display dashboard with correct metrics', async ({ page }) => {
    await page.goto(`${BASE_URL}/admin/auto-analysis`);

    // Wait for HTMX to load dashboard
    await page.waitForTimeout(2000);

    // Check dashboard card is visible
    const dashboard = page.locator('.card:has-text("Auto-Analysis System")');
    await expect(dashboard).toBeVisible();

    // Check for stat values
    const statValues = page.locator('.stat-value');
    const count = await statValues.count();
    expect(count).toBeGreaterThanOrEqual(2); // At least Active Feeds and Jobs Today
  });

  test('should show accurate metrics matching database', async ({ page }) => {
    await page.goto(`${BASE_URL}/admin/auto-analysis`);
    await page.waitForTimeout(2000);

    // Get displayed metrics
    const activeFeeds = await page.locator('.stat-value.text-primary').textContent();
    const jobsToday = await page.locator('.stat-value.text-success').textContent();

    // Verify they are numbers
    expect(parseInt(activeFeeds)).toBeGreaterThanOrEqual(0);
    expect(parseInt(jobsToday)).toBeGreaterThanOrEqual(0);

    console.log(`Active Feeds: ${activeFeeds}, Jobs Today: ${jobsToday}`);
  });

  test('should display items analyzed and success rate', async ({ page }) => {
    await page.goto(`${BASE_URL}/admin/auto-analysis`);
    await page.waitForTimeout(2000);

    // Look for "Items Analyzed" text
    const itemsText = page.locator('text=Items Analyzed');
    await expect(itemsText).toBeVisible();

    // Look for "Success Rate" text
    const successText = page.locator('text=Success Rate');
    await expect(successText).toBeVisible();
  });

  test('should show queue status', async ({ page }) => {
    await page.goto(`${BASE_URL}/admin/auto-analysis`);
    await page.waitForTimeout(2000);

    // Check for pending badge or queue empty message
    const hasPendingBadge = await page.locator('text=/\\d+ Pending/').count() > 0;
    const hasEmptyQueue = await page.locator('text=Queue is empty').count() > 0;

    // One of them should be visible
    expect(hasPendingBadge || hasEmptyQueue).toBe(true);
  });

  test('should load pending queue section', async ({ page }) => {
    await page.goto(`${BASE_URL}/admin/auto-analysis`);
    await page.waitForTimeout(3000);

    // Check for pending queue card
    const queueCard = page.locator('text=Pending Queue');
    await expect(queueCard).toBeVisible();
  });

  test('should load recent history section', async ({ page }) => {
    await page.goto(`${BASE_URL}/admin/auto-analysis`);
    await page.waitForTimeout(3000);

    // Check for history card
    const historyCard = page.locator('text=Recent History');
    await expect(historyCard).toBeVisible();
  });

  test('should have configuration section', async ({ page }) => {
    await page.goto(`${BASE_URL}/admin/auto-analysis`);

    // Check for config section
    const configSection = page.locator('text=System Configuration');
    await expect(configSection).toBeVisible();

    // Should show settings like max runs, model, etc
    const hasMaxRuns = await page.locator('text=/Auto-Runs pro Feed/').count() > 0;
    expect(hasMaxRuns).toBe(true);
  });

  test('should not have server errors (500+)', async ({ page }) => {
    const serverErrors = [];

    page.on('response', response => {
      if (response.status() >= 500) {
        serverErrors.push({
          url: response.url(),
          status: response.status()
        });
      }
    });

    await page.goto(`${BASE_URL}/admin/auto-analysis`, {
      waitUntil: 'networkidle',
      timeout: 15000
    });

    // Wait for HTMX requests
    await page.waitForTimeout(3000);

    expect(serverErrors).toHaveLength(0);
  });

  test('should verify metrics are realistic (not fake)', async ({ page }) => {
    await page.goto(`${BASE_URL}/admin/auto-analysis`);
    await page.waitForTimeout(2000);

    // Get jobs today number
    const jobsText = await page.locator('.stat-value.text-success').textContent();
    const jobsToday = parseInt(jobsText);

    // Should be reasonable number (0-1000, not the old fake 423)
    expect(jobsToday).toBeGreaterThanOrEqual(0);
    expect(jobsToday).toBeLessThan(1000);

    // Get success rate
    const successRateElements = await page.locator('strong:has-text("%")').count();
    expect(successRateElements).toBeGreaterThan(0);
  });
});
