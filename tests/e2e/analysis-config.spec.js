// @ts-check
const { test, expect } = require('@playwright/test');

test.describe('Analysis Configuration', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to analysis page
    await page.goto('http://192.168.178.72:8000/admin/analysis');
    await page.waitForLoadState('networkidle');
  });

  test('Config section should be visible', async ({ page }) => {
    // Check if config section exists
    const configSection = page.locator('text=Manual Analysis Settings');
    await expect(configSection).toBeVisible();

    // Check if Edit button exists
    const editButton = page.locator('#toggle-analysis-config-edit');
    await expect(editButton).toBeVisible();
  });

  test('Edit button should show form', async ({ page }) => {
    // Click Edit button
    await page.click('#toggle-analysis-config-edit');

    // Wait for form to appear
    await page.waitForSelector('#analysis-config-edit', { state: 'visible' });

    // Check if form fields are visible
    await expect(page.locator('input[name="max_concurrent_runs"]')).toBeVisible();
    await expect(page.locator('input[name="max_daily_runs"]')).toBeVisible();
    await expect(page.locator('input[name="max_hourly_runs"]')).toBeVisible();
    await expect(page.locator('input[name="analysis_batch_limit"]')).toBeVisible();
    await expect(page.locator('input[name="analysis_rps"]')).toBeVisible();
    await expect(page.locator('select[name="analysis_model"]')).toBeVisible();

    // Check if Save and Cancel buttons exist
    await expect(page.locator('button:has-text("Save")')).toBeVisible();
    await expect(page.locator('#cancel-analysis-config-edit')).toBeVisible();
  });

  test('Cancel button should hide form', async ({ page }) => {
    // Click Edit button
    await page.click('#toggle-analysis-config-edit');
    await page.waitForSelector('#analysis-config-edit', { state: 'visible' });

    // Click Cancel button
    await page.click('#cancel-analysis-config-edit');

    // Wait for form to hide
    await page.waitForSelector('#analysis-config-edit', { state: 'hidden' });

    // View should be visible again
    await expect(page.locator('#analysis-config-view')).toBeVisible();
  });

  test('Save button should submit form and update config', async ({ page }) => {
    // Listen for network requests
    const requestPromise = page.waitForRequest(request =>
      request.url().includes('/htmx/analysis/analysis-config') &&
      request.method() === 'POST'
    );

    // Click Edit button
    await page.click('#toggle-analysis-config-edit');
    await page.waitForSelector('#analysis-config-edit', { state: 'visible' });

    // Change some values
    await page.fill('input[name="max_concurrent_runs"]', '7');
    await page.fill('input[name="max_daily_runs"]', '150');
    await page.fill('input[name="max_hourly_runs"]', '15');

    // Click Save button
    await page.click('button:has-text("Save")');

    // Wait for request to be sent
    const request = await requestPromise;
    expect(request).toBeTruthy();

    // Wait for response and form to hide
    await page.waitForTimeout(1000);

    // Check if success toast appears
    const toast = page.locator('.alert-success:has-text("Configuration saved successfully")');
    await expect(toast).toBeVisible({ timeout: 5000 });

    // Verify updated values are displayed in view
    await expect(page.locator('#view-max-concurrent')).toContainText('7');
    await expect(page.locator('#view-max-daily')).toContainText('150');
    await expect(page.locator('#view-max-hourly')).toContainText('15');
  });

  test('Config values should persist after reload', async ({ page }) => {
    // First, set some test values
    await page.click('#toggle-analysis-config-edit');
    await page.waitForSelector('#analysis-config-edit', { state: 'visible' });

    const testValues = {
      concurrent: '6',
      daily: '120',
      hourly: '12'
    };

    await page.fill('input[name="max_concurrent_runs"]', testValues.concurrent);
    await page.fill('input[name="max_daily_runs"]', testValues.daily);
    await page.fill('input[name="max_hourly_runs"]', testValues.hourly);

    await page.click('button:has-text("Save")');
    await page.waitForTimeout(1000);

    // Reload page
    await page.reload();
    await page.waitForLoadState('networkidle');

    // Wait for config to load
    await page.waitForTimeout(2000);

    // Verify values persisted
    await expect(page.locator('#view-max-concurrent')).toContainText(testValues.concurrent);
    await expect(page.locator('#view-max-daily')).toContainText(testValues.daily);
    await expect(page.locator('#view-max-hourly')).toContainText(testValues.hourly);
  });

  test('No console errors on page load', async ({ page }) => {
    const errors = [];
    page.on('console', msg => {
      if (msg.type() === 'error') {
        errors.push(msg.text());
      }
    });

    await page.goto('http://192.168.178.72:8000/admin/analysis');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    expect(errors).toHaveLength(0);
  });
});
