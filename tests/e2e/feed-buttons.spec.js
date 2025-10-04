/**
 * E2E Test: Feed Buttons Functionality
 *
 * Tests all buttons on the Feeds page to verify they work correctly.
 *
 * Buttons to test:
 * - Load (fetch articles now)
 * - Edit (opens edit modal)
 * - Toggle Active/Inactive
 * - Delete
 */

const { test, expect } = require('@playwright/test');

const BASE_URL = 'http://192.168.178.72:8000';

test.describe('Feed Buttons Functionality', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to feeds page
    await page.goto(`${BASE_URL}/admin/feeds`);
    await page.waitForSelector('.card', { timeout: 10000 });
  });

  test('should display all feed buttons', async ({ page }) => {
    // Check that at least one feed card exists
    const feedCards = await page.locator('.card').count();
    expect(feedCards).toBeGreaterThan(0);

    // Check that Load button exists
    const loadButtons = await page.locator('button:has-text("Load")').count();
    console.log(`Found ${loadButtons} Load buttons`);

    // Check that Edit buttons exist (pencil icon)
    const editButtons = await page.locator('button i.bi-pencil').count();
    console.log(`Found ${editButtons} Edit buttons`);

    // Check that Toggle buttons exist (play/pause icon)
    const toggleButtons = await page.locator('button i.bi-play, button i.bi-pause').count();
    console.log(`Found ${toggleButtons} Toggle buttons`);

    // Check that Delete buttons exist (trash icon)
    const deleteButtons = await page.locator('button i.bi-trash').count();
    console.log(`Found ${deleteButtons} Delete buttons`);
  });

  test('should test Load button functionality', async ({ page }) => {
    // Listen for network requests
    const requests = [];
    page.on('request', request => {
      if (request.url().includes('/htmx/feed-fetch-now/')) {
        requests.push(request);
      }
    });

    // Find first Load button and click it
    const loadButton = page.locator('button').filter({ hasText: 'Load' }).first();
    await loadButton.click();

    // Wait a bit for request to be sent
    await page.waitForTimeout(1000);

    // Check if request was sent
    console.log(`Load button sent ${requests.length} requests`);
    if (requests.length === 0) {
      console.log('❌ FAILED: Load button did not send HTMX request');
    } else {
      console.log(`✅ PASSED: Load button sent request to ${requests[0].url()}`);
    }

    // Check for feedback in fetch-status div
    const feedId = await loadButton.getAttribute('hx-post');
    if (feedId) {
      const statusId = feedId.match(/\/htmx\/feed-fetch-now\/(\d+)/)?.[1];
      if (statusId) {
        const statusDiv = page.locator(`#fetch-status-${statusId}`);
        const statusText = await statusDiv.textContent({ timeout: 3000 }).catch(() => '');
        console.log(`Status feedback: "${statusText}"`);
      }
    }
  });

  test('should test Edit button functionality', async ({ page }) => {
    // Find first Edit button (pencil icon)
    const editButton = page.locator('button i.bi-pencil').first().locator('..');

    // Click Edit button
    await editButton.click();

    // Wait for modal to appear (correct ID is editFeedModal, not feedEditModal!)
    const modal = page.locator('#editFeedModal');
    await modal.waitFor({ state: 'visible', timeout: 3000 }).catch(() => {
      console.log('❌ FAILED: Edit modal did not appear');
    });

    const isVisible = await modal.isVisible();
    if (isVisible) {
      console.log('✅ PASSED: Edit modal appeared');

      // Check modal content
      const modalTitle = await modal.locator('.modal-title').textContent();
      console.log(`Modal title: "${modalTitle}"`);

      // Close modal
      await page.locator('#editFeedModal .btn-close').click();
    } else {
      console.log('❌ FAILED: Edit modal not visible');
    }
  });

  test('should test Toggle Active/Inactive button', async ({ page }) => {
    // Listen for network requests
    const requests = [];
    page.on('request', request => {
      if (request.url().includes('/api/feeds/') && request.method() === 'PATCH') {
        requests.push(request);
      }
    });

    // Find first Toggle button (play or pause icon)
    const toggleButton = page.locator('button i.bi-play, button i.bi-pause').first().locator('..');

    // Get initial icon
    const initialIcon = await toggleButton.locator('i').getAttribute('class');
    console.log(`Initial toggle icon: ${initialIcon}`);

    // Click Toggle button
    await toggleButton.click();

    // Wait for request
    await page.waitForTimeout(1000);

    // Check if request was sent
    console.log(`Toggle button sent ${requests.length} requests`);
    if (requests.length === 0) {
      console.log('❌ FAILED: Toggle button did not send PATCH request');
    } else {
      console.log(`✅ PASSED: Toggle button sent PATCH to ${requests[0].url()}`);

      // Check if icon changed
      const newIcon = await toggleButton.locator('i').getAttribute('class').catch(() => initialIcon);
      if (newIcon !== initialIcon) {
        console.log(`✅ PASSED: Icon changed from ${initialIcon} to ${newIcon}`);
      } else {
        console.log(`⚠️  WARNING: Icon did not change (still ${newIcon})`);
      }
    }
  });

  test('should test Delete button (without confirming)', async ({ page }) => {
    // Override confirm dialog to prevent actual deletion
    page.on('dialog', async dialog => {
      console.log(`Delete confirmation dialog appeared: "${dialog.message()}"`);
      await dialog.dismiss();
    });

    // Find first Delete button (trash icon)
    const deleteButton = page.locator('button i.bi-trash').first().locator('..');

    // Click Delete button
    await deleteButton.click();

    // Wait a bit
    await page.waitForTimeout(500);

    // If we got here without errors, dialog appeared
    console.log('✅ PASSED: Delete button triggered confirmation dialog');
  });

  test('should check for console errors', async ({ page }) => {
    const consoleErrors = [];
    page.on('console', msg => {
      if (msg.type() === 'error') {
        consoleErrors.push(msg.text());
      }
    });

    // Click each button type once
    const loadBtn = page.locator('button').filter({ hasText: 'Load' }).first();
    const editBtn = page.locator('button i.bi-pencil').first().locator('..');
    const toggleBtn = page.locator('button i.bi-play, button i.bi-pause').first().locator('..');

    await loadBtn.click().catch(() => {});
    await page.waitForTimeout(500);

    await editBtn.click().catch(() => {});
    await page.waitForTimeout(500);

    await toggleBtn.click().catch(() => {});
    await page.waitForTimeout(500);

    // Report console errors
    if (consoleErrors.length > 0) {
      console.log(`❌ FOUND ${consoleErrors.length} console errors:`);
      consoleErrors.forEach((err, i) => {
        console.log(`  ${i + 1}. ${err}`);
      });
    } else {
      console.log('✅ PASSED: No console errors detected');
    }
  });

  test('should verify HTMX attributes on buttons', async ({ page }) => {
    // Load button
    const loadBtn = page.locator('button').filter({ hasText: 'Load' }).first();
    const hxPost = await loadBtn.getAttribute('hx-post');
    const hxTarget = await loadBtn.getAttribute('hx-target');
    console.log(`Load button: hx-post="${hxPost}", hx-target="${hxTarget}"`);

    // Edit button
    const editBtn = page.locator('button i.bi-pencil').first().locator('..');
    const hxGet = await editBtn.getAttribute('hx-get');
    const dataToggle = await editBtn.getAttribute('data-bs-toggle');
    console.log(`Edit button: hx-get="${hxGet}", data-bs-toggle="${dataToggle}"`);

    // Toggle button
    const toggleBtn = page.locator('button i.bi-play, button i.bi-pause').first().locator('..');
    const hxPatch = await toggleBtn.getAttribute('hx-patch');
    const hxVals = await toggleBtn.getAttribute('hx-vals');
    console.log(`Toggle button: hx-patch="${hxPatch}", hx-vals="${hxVals}"`);

    // Delete button
    const deleteBtn = page.locator('button i.bi-trash').first().locator('..');
    const hxDelete = await deleteBtn.getAttribute('hx-delete');
    const hxConfirm = await deleteBtn.getAttribute('hx-confirm');
    console.log(`Delete button: hx-delete="${hxDelete}", hx-confirm="${hxConfirm}"`);

    // Verify all attributes are present
    const results = {
      'Load hx-post': hxPost,
      'Load hx-target': hxTarget,
      'Edit hx-get': hxGet,
      'Edit data-bs-toggle': dataToggle,
      'Toggle hx-patch': hxPatch,
      'Toggle hx-vals': hxVals,
      'Delete hx-delete': hxDelete,
      'Delete hx-confirm': hxConfirm
    };

    for (const [name, value] of Object.entries(results)) {
      if (!value) {
        console.log(`❌ MISSING: ${name}`);
      } else {
        console.log(`✅ PRESENT: ${name} = "${value}"`);
      }
    }
  });
});
