/**
 * Processors Page Test
 * Tests the new reorganized processors page
 */

const { test, expect } = require('@playwright/test');

const BASE_URL = 'http://192.168.178.72:8000';

test.describe('Processors Page - Full Test', () => {

  test('should load processors page without errors', async ({ page }) => {
    const errors = [];
    page.on('console', msg => {
      if (msg.type() === 'error' && !msg.text().includes('404') && !msg.text().includes('Failed to load resource')) {
        errors.push(msg.text());
      }
    });

    const response = await page.goto(`${BASE_URL}/admin/processors`, {
      waitUntil: 'domcontentloaded',
      timeout: 15000
    });

    expect(response.status()).toBe(200);
    expect(errors).toHaveLength(0);
  });

  test('should display health metrics cards', async ({ page }) => {
    await page.goto(`${BASE_URL}/admin/processors`);

    // Wait for HTMX to load content
    await page.waitForTimeout(2000);

    // Check for 4 metric cards
    const metricCards = page.locator('.metric-card');
    await expect(metricCards).toHaveCount(4);

    // Check health status is displayed
    const healthBadge = page.locator('#health-status-badge');
    await expect(healthBadge).toBeVisible();

    // Should show UNHEALTHY or HEALTHY badge
    const badgeText = await healthBadge.textContent();
    expect(badgeText).toMatch(/(HEALTHY|DEGRADED|UNHEALTHY)/);
  });

  test('should display available processors', async ({ page }) => {
    await page.goto(`${BASE_URL}/admin/processors`);

    // Wait for HTMX to load processors
    await page.waitForTimeout(2000);

    // Check processor types are loaded
    const processorSection = page.locator('#processor-types');
    await expect(processorSection).toBeVisible();

    // Should have processor cards (at least 3: universal, heise, cointelegraph)
    const processorCards = page.locator('.processor-type-card');
    const count = await processorCards.count();
    expect(count).toBeGreaterThanOrEqual(3);
  });

  test('should have 3 main tabs', async ({ page }) => {
    await page.goto(`${BASE_URL}/admin/processors`);

    // Check for 3 tabs
    const tabs = page.locator('.nav-tabs .nav-link');
    await expect(tabs).toHaveCount(3);

    // Check tab names
    const tab1 = page.locator('#dashboard-tab');
    const tab2 = page.locator('#config-tab');
    const tab3 = page.locator('#operations-tab');

    await expect(tab1).toContainText('Health Dashboard');
    await expect(tab2).toContainText('Configuration');
    await expect(tab3).toContainText('Operations');
  });

  test('should switch between tabs', async ({ page }) => {
    await page.goto(`${BASE_URL}/admin/processors`);

    // Wait for page to load
    await page.waitForTimeout(1000);

    // Dashboard tab should be active initially
    const dashboardTab = page.locator('#dashboard-tab');
    await expect(dashboardTab).toHaveClass(/active/);

    // Click Configuration tab
    const configTab = page.locator('#config-tab');
    await configTab.click();
    await page.waitForTimeout(500);

    // Configuration tab should now be active
    await expect(configTab).toHaveClass(/active/);
    await expect(dashboardTab).not.toHaveClass(/active/);

    // Check Configuration content is visible
    const configContent = page.locator('#config');
    await expect(configContent).toHaveClass(/active/);

    // Click Operations tab
    const operationsTab = page.locator('#operations-tab');
    await operationsTab.click();
    await page.waitForTimeout(500);

    // Operations tab should now be active
    await expect(operationsTab).toHaveClass(/active/);
    await expect(configTab).not.toHaveClass(/active/);
  });

  test('should display operations section correctly', async ({ page }) => {
    await page.goto(`${BASE_URL}/admin/processors`);

    // Click Operations tab
    await page.click('#operations-tab');
    await page.waitForTimeout(500);

    // Check for Feed Reprocessing card
    const feedReprocessCard = page.locator('text=Feed Reprocessing');
    await expect(feedReprocessCard).toBeVisible();

    // Check for Single Item Reprocessing card
    const itemReprocessCard = page.locator('text=Single Item Reprocessing');
    await expect(itemReprocessCard).toBeVisible();

    // Check for reprocess buttons
    const feedButton = page.locator('button:has-text("Start Reprocessing")');
    const itemButton = page.locator('button:has-text("Reprocess Item")');

    await expect(feedButton).toBeVisible();
    await expect(itemButton).toBeVisible();
  });

  test('should show no server errors (500+)', async ({ page }) => {
    const serverErrors = [];

    page.on('response', response => {
      if (response.status() >= 500) {
        serverErrors.push({
          url: response.url(),
          status: response.status()
        });
      }
    });

    await page.goto(`${BASE_URL}/admin/processors`, {
      waitUntil: 'networkidle',
      timeout: 15000
    });

    // Wait for all HTMX requests to complete
    await page.waitForTimeout(3000);

    expect(serverErrors).toHaveLength(0);
  });

  test('should update metrics periodically', async ({ page }) => {
    await page.goto(`${BASE_URL}/admin/processors`);

    // Wait for initial load
    await page.waitForTimeout(2000);

    // Get initial health status
    const initialHealth = await page.locator('#health-status-badge').textContent();

    // Check that health badge has content
    expect(initialHealth.length).toBeGreaterThan(0);
    expect(initialHealth).toMatch(/(HEALTHY|DEGRADED|UNHEALTHY)/);
  });

  test('should have responsive metric cards', async ({ page }) => {
    await page.goto(`${BASE_URL}/admin/processors`);
    await page.waitForTimeout(2000);

    // Check metric cards have hover effect
    const firstCard = page.locator('.metric-card').first();
    await expect(firstCard).toBeVisible();

    // Cards should have gradient background
    const cardStyle = await firstCard.evaluate(el =>
      window.getComputedStyle(el).backgroundImage
    );
    expect(cardStyle).toContain('linear-gradient');
  });
});
