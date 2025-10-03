/**
 * E2E Test - Items Page with Sticky Sidebar
 *
 * Tests the Finance/Geopolitical analysis sidebar:
 * - Sidebar is visible on the right
 * - Sidebar updates when hovering over articles
 * - Finance and Geopolitical blocks display correctly
 * - No console errors
 */

const { test, expect } = require('@playwright/test');

const BASE_URL = 'http://192.168.178.72:8000';
const ITEMS_PAGE = `${BASE_URL}/admin/items`;

test.describe('Items Page - Sticky Analysis Sidebar', () => {
  test('should render sidebar and two-column layout', async ({ page }) => {
    const errors = [];
    page.on('console', msg => {
      if (msg.type() === 'error') errors.push(msg.text());
    });

    await page.goto(ITEMS_PAGE);
    await page.waitForLoadState('networkidle');

    // Wait for items to load
    await page.waitForSelector('.article-card, .alert', { timeout: 5000 });

    // Check sidebar exists
    const sidebar = page.locator('#analysis-sidebar');
    await expect(sidebar).toBeVisible();

    // Check for Finance block (should appear after initial load)
    await page.waitForTimeout(1000);
    const financeBlock = sidebar.locator('.finance-block');
    await expect(financeBlock).toBeVisible({ timeout: 3000 });

    // Verify Finance block content
    await expect(financeBlock).toContainText('Finance');
    await expect(financeBlock).toContainText('Market:');
    await expect(financeBlock).toContainText('Impact:');
    await expect(financeBlock).toContainText('Volatility:');

    // Check for console errors
    expect(errors).toEqual([]);
  });

  test('should update sidebar on article hover', async ({ page }) => {
    await page.goto(ITEMS_PAGE);
    await page.waitForLoadState('networkidle');
    await page.waitForSelector('.article-card', { timeout: 5000 });

    const sidebar = page.locator('#analysis-sidebar');

    // Get first article card
    const firstCard = page.locator('.article-card').first();
    await firstCard.hover();
    await page.waitForTimeout(200);

    // Sidebar should show Finance block
    const financeBlock = sidebar.locator('.finance-block');
    await expect(financeBlock).toBeVisible();

    // If there's a second card, hover over it
    const secondCard = page.locator('.article-card').nth(1);
    const secondExists = await secondCard.count() > 0;

    if (secondExists) {
      await secondCard.hover();
      await page.waitForTimeout(200);

      // Sidebar should still show Finance block (might update content)
      await expect(financeBlock).toBeVisible();
    }
  });

  test('should display Geopolitical block when available', async ({ page }) => {
    await page.goto(ITEMS_PAGE);
    await page.waitForLoadState('networkidle');
    await page.waitForSelector('.article-card', { timeout: 5000 });

    const sidebar = page.locator('#analysis-sidebar');

    // Hover over first article
    await page.locator('.article-card').first().hover();
    await page.waitForTimeout(500);

    // Check if Geopolitical block exists (not all articles have it)
    const geoBlock = sidebar.locator('.geopolitical-block');
    const geoExists = await geoBlock.count() > 0;

    if (geoExists) {
      await expect(geoBlock).toBeVisible();
      await expect(geoBlock).toContainText('Geopolitical');
      await expect(geoBlock).toContainText('Type:');
      await expect(geoBlock).toContainText('Security:');
    }
  });

  test('should have sticky positioning', async ({ page }) => {
    await page.goto(ITEMS_PAGE);
    await page.waitForLoadState('networkidle');
    await page.waitForSelector('.article-card', { timeout: 5000 });

    const sidebar = page.locator('#analysis-sidebar');

    // Check sticky positioning
    const styles = await sidebar.evaluate(el => window.getComputedStyle(el));
    expect(styles.position).toBe('sticky');
  });

  test('should not have JavaScript errors', async ({ page }) => {
    const errors = [];
    page.on('console', msg => {
      if (msg.type() === 'error') errors.push(msg.text());
    });

    page.on('pageerror', error => {
      errors.push(error.message);
    });

    await page.goto(ITEMS_PAGE);
    await page.waitForLoadState('networkidle');
    await page.waitForSelector('.article-card', { timeout: 5000 });

    // Interact with articles
    const cards = page.locator('.article-card');
    const cardCount = await cards.count();

    if (cardCount > 0) {
      await cards.first().hover();
      await page.waitForTimeout(300);
    }

    if (cardCount > 1) {
      await cards.nth(1).hover();
      await page.waitForTimeout(300);
    }

    // Check for errors
    expect(errors).toEqual([]);
  });
});
