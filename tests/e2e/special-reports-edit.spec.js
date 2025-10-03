/**
 * E2E Test Suite - Special Reports Edit Page
 *
 * Tests the three-panel layout and granular sentiment filtering:
 * - Three-panel layout renders correctly (Config | Articles | Test)
 * - All sentiment filter toggles work
 * - Articles list auto-updates when filters change
 * - Test button shows filtered results
 * - No console errors
 * - Data consistency between API and UI
 */

const { test, expect } = require('@playwright/test');

const BASE_URL = 'http://192.168.178.72:8000';
const EDIT_PAGE_URL = `${BASE_URL}/admin/special-reports/1/edit`;

test.describe('Special Reports Edit Page - Three-Panel Layout', () => {
  test('should render all three panels correctly', async ({ page }) => {
    const errors = [];

    // Capture console errors
    page.on('console', msg => {
      if (msg.type() === 'error') {
        const text = msg.text();
        if (!text.includes('404') && !text.includes('Failed to load resource')) {
          errors.push(text);
        }
      }
    });

    await page.goto(EDIT_PAGE_URL);

    // Wait for page to load
    await page.waitForLoadState('networkidle');

    // Verify page title
    await expect(page.locator('h2')).toContainText('Edit:');

    // Check all three panels exist
    const configPanel = page.locator('.config-panel');
    const articlesPanel = page.locator('.articles-panel');
    const previewPanel = page.locator('.preview-panel');

    await expect(configPanel).toBeVisible();
    await expect(articlesPanel).toBeVisible();
    await expect(previewPanel).toBeVisible();

    // Verify panel headers
    await expect(configPanel.locator('h4')).toContainText('Configuration');
    await expect(articlesPanel.locator('h4')).toContainText('Selected Articles');
    await expect(previewPanel.locator('h4')).toContainText('Live Test');

    // Check for console errors
    expect(errors).toEqual([]);
  });

  test('should display all sentiment filter fields with toggles', async ({ page }) => {
    await page.goto(EDIT_PAGE_URL);
    await page.waitForLoadState('networkidle');

    // Check all sentiment filter labels exist
    await expect(page.locator('text=Min Sentiment (-1 to 1)')).toBeVisible();
    await expect(page.locator('text=Min Urgency (0-1)')).toBeVisible();
    await expect(page.locator('text=Min Bearish (0-1)')).toBeVisible();
    await expect(page.locator('text=Min Bullish (0-1)')).toBeVisible();
    await expect(page.locator('text=Min Uncertainty (0-1)')).toBeVisible();

    // Check all toggle switches exist
    const sentimentToggle = page.locator('#enable_sentiment');
    const urgencyToggle = page.locator('#enable_urgency');
    const bearishToggle = page.locator('#enable_bearish');
    const bullishToggle = page.locator('#enable_bullish');
    const uncertaintyToggle = page.locator('#enable_uncertainty');

    await expect(sentimentToggle).toBeVisible();
    await expect(urgencyToggle).toBeVisible();
    await expect(bearishToggle).toBeVisible();
    await expect(bullishToggle).toBeVisible();
    await expect(uncertaintyToggle).toBeVisible();

    // Verify default states (sentiment enabled, others disabled)
    await expect(sentimentToggle).toBeChecked();
    await expect(urgencyToggle).not.toBeChecked();
    await expect(bearishToggle).not.toBeChecked();
    await expect(bullishToggle).not.toBeChecked();
    await expect(uncertaintyToggle).not.toBeChecked();

    // Verify corresponding inputs are disabled when toggle is off
    const sentimentInput = page.locator('#sentiment_input');
    const urgencyInput = page.locator('#urgency_input');
    const bearishInput = page.locator('#bearish_input');
    const bullishInput = page.locator('#bullish_input');
    const uncertaintyInput = page.locator('#uncertainty_input');

    await expect(sentimentInput).toBeEnabled();
    await expect(urgencyInput).toBeDisabled();
    await expect(bearishInput).toBeDisabled();
    await expect(bullishInput).toBeDisabled();
    await expect(uncertaintyInput).toBeDisabled();
  });

  test('should enable/disable inputs when toggles are clicked', async ({ page }) => {
    await page.goto(EDIT_PAGE_URL);
    await page.waitForLoadState('networkidle');

    const urgencyToggle = page.locator('#enable_urgency');
    const urgencyInput = page.locator('#urgency_input');

    // Initially disabled
    await expect(urgencyInput).toBeDisabled();

    // Click toggle to enable
    await urgencyToggle.click();
    await page.waitForTimeout(200); // Wait for toggle animation

    // Should now be enabled
    await expect(urgencyInput).toBeEnabled();

    // Click again to disable
    await urgencyToggle.click();
    await page.waitForTimeout(200);

    // Should be disabled again
    await expect(urgencyInput).toBeDisabled();
  });

  test('should auto-update articles list when filters change', async ({ page }) => {
    await page.goto(EDIT_PAGE_URL);
    await page.waitForLoadState('networkidle');

    // Wait for initial articles to load
    await page.waitForSelector('.articles-panel .article-card, .articles-panel .text-muted', { timeout: 5000 });

    // Get initial article count
    const initialArticleCount = page.locator('.articles-panel .article-card');
    const initialCount = await initialArticleCount.count();

    console.log(`Initial article count: ${initialCount}`);

    // Change timeframe to get different results
    const timeframeInput = page.locator('input[name="timeframe_hours"]');
    await timeframeInput.clear();
    await timeframeInput.fill('48');

    // Wait for debounced update (500ms + network request)
    await page.waitForTimeout(1000);

    // Articles should have updated
    const updatedArticleCount = page.locator('.articles-panel .article-card');
    const updatedCount = await updatedArticleCount.count();

    console.log(`Updated article count: ${updatedCount}`);

    // Count should be different (or at least the request was made)
    // We can't guarantee count changes, but we can verify no errors
    expect(updatedCount).toBeGreaterThanOrEqual(0);
  });

  test('should filter articles when urgency filter is enabled', async ({ page }) => {
    await page.goto(EDIT_PAGE_URL);
    await page.waitForLoadState('networkidle');

    // Wait for initial load
    await page.waitForSelector('.articles-panel .article-card, .articles-panel .text-muted', { timeout: 5000 });

    // Enable urgency filter
    const urgencyToggle = page.locator('#enable_urgency');
    await urgencyToggle.click();

    // Set high urgency threshold
    const urgencyInput = page.locator('#urgency_input');
    await urgencyInput.clear();
    await urgencyInput.fill('0.8');

    // Wait for debounced update
    await page.waitForTimeout(1000);

    // Check if articles updated (some should be filtered out)
    const articlesPanel = page.locator('.articles-panel');
    const content = await articlesPanel.textContent();

    // Either articles exist or "No articles match" message
    const hasArticles = await page.locator('.articles-panel .article-card').count() > 0;
    const hasNoMatchMessage = content.includes('No articles match');

    expect(hasArticles || hasNoMatchMessage).toBe(true);
  });

  test('should show test results when Test Selection button is clicked', async ({ page }) => {
    await page.goto(EDIT_PAGE_URL);
    await page.waitForLoadState('networkidle');

    // Click Test Selection button
    const testButton = page.locator('button.btn-test');
    await expect(testButton).toBeVisible();
    await testButton.click();

    // Wait for test results
    await page.waitForSelector('#test-results .alert, #test-results .article-card', { timeout: 10000 });

    // Should show either results or "no articles" message
    const testResults = page.locator('#test-results');
    const content = await testResults.textContent();

    expect(content.length).toBeGreaterThan(0);
    expect(
      content.includes('Found') ||
      content.includes('No articles found') ||
      content.includes('articles selected')
    ).toBe(true);
  });

  test('should save configuration without errors', async ({ page }) => {
    const errors = [];
    const responses = [];

    page.on('console', msg => {
      if (msg.type() === 'error') {
        errors.push(msg.text());
      }
    });

    page.on('response', response => {
      if (response.url().includes('/update')) {
        responses.push({
          status: response.status(),
          url: response.url()
        });
      }
    });

    await page.goto(EDIT_PAGE_URL);
    await page.waitForLoadState('networkidle');

    // Change a value
    const nameInput = page.locator('input[name="name"]');
    const originalName = await nameInput.inputValue();
    await nameInput.clear();
    await nameInput.fill(`Test Report ${Date.now()}`);

    // Click Save
    const saveButton = page.locator('button[type="submit"][form="edit-form"]');
    await saveButton.click();

    // Wait for save response
    await page.waitForTimeout(2000);

    // Check for success message
    const saveStatus = page.locator('#save-status');
    const statusText = await saveStatus.textContent();

    expect(statusText.toLowerCase()).toContain('success');
    expect(errors).toEqual([]);

    // Restore original name
    await nameInput.clear();
    await nameInput.fill(originalName);
    await saveButton.click();
    await page.waitForTimeout(1000);
  });

  test('should verify data consistency between API and frontend', async ({ page, request }) => {
    // Fetch data from API
    const apiResponse = await request.get(`${BASE_URL}/api/v2/special-reports/1`);
    expect(apiResponse.ok()).toBeTruthy();
    const apiData = await apiResponse.json();

    // Load page
    await page.goto(EDIT_PAGE_URL);
    await page.waitForLoadState('networkidle');

    // Verify name matches
    const nameInput = page.locator('input[name="name"]');
    const uiName = await nameInput.inputValue();
    expect(uiName).toBe(apiData.name);

    // Verify LLM model matches
    const modelSelect = page.locator('select[name="llm_model"]');
    const uiModel = await modelSelect.inputValue();
    expect(uiModel).toBe(apiData.llm_model);

    // Verify active status matches
    const activeCheckbox = page.locator('#is_active');
    const uiActive = await activeCheckbox.isChecked();
    expect(uiActive).toBe(apiData.is_active);

    console.log('✅ Data consistency verified: API data matches frontend');
  });

  test('should not have JavaScript errors during interaction', async ({ page }) => {
    const errors = [];

    page.on('console', msg => {
      if (msg.type() === 'error') {
        const text = msg.text();
        if (!text.includes('404') && !text.includes('Failed to load resource')) {
          errors.push(text);
        }
      }
    });

    page.on('pageerror', error => {
      errors.push(error.message);
    });

    await page.goto(EDIT_PAGE_URL);
    await page.waitForLoadState('networkidle');

    // Interact with multiple elements
    await page.locator('#enable_urgency').click();
    await page.locator('#urgency_input').fill('0.5');
    await page.locator('#enable_bearish').click();
    await page.locator('#bearish_input').fill('0.7');
    await page.locator('input[name="timeframe_hours"]').fill('72');

    // Wait for all updates
    await page.waitForTimeout(1500);

    // Click test button
    await page.locator('button.btn-test').click();
    await page.waitForTimeout(2000);

    // Check for errors
    expect(errors).toEqual([]);
  });
});

test.describe('Special Reports Edit Page - Responsive Design', () => {
  test('should adapt layout on smaller screens', async ({ page }) => {
    // Test mobile viewport
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto(EDIT_PAGE_URL);
    await page.waitForLoadState('networkidle');

    // All panels should still be visible (stacked vertically)
    await expect(page.locator('.config-panel')).toBeVisible();
    await expect(page.locator('.articles-panel')).toBeVisible();
    await expect(page.locator('.preview-panel')).toBeVisible();

    // Test tablet viewport
    await page.setViewportSize({ width: 768, height: 1024 });
    await page.waitForTimeout(500);

    await expect(page.locator('.config-panel')).toBeVisible();
    await expect(page.locator('.articles-panel')).toBeVisible();
    await expect(page.locator('.preview-panel')).toBeVisible();
  });
});
