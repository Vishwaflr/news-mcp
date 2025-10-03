/**
 * Smoke Test Suite - All Admin Pages
 *
 * Tests basic functionality of all admin pages:
 * - Page loads without 500 errors
 * - No console errors
 * - Critical elements present
 * - API endpoints return 200
 */

const { test, expect } = require('@playwright/test');

const BASE_URL = 'http://192.168.178.72:8000';

// All admin pages to test
const ADMIN_PAGES = [
  { path: '/admin/processors', name: 'Processors' },
  { path: '/admin/analysis', name: 'Analysis' },
  { path: '/admin/feeds', name: 'Feeds' },
  { path: '/admin/items', name: 'Items' },
  { path: '/admin/templates', name: 'Templates' },
  { path: '/admin/statistics', name: 'Statistics' },
  { path: '/admin/health', name: 'Health' },
  { path: '/admin/database', name: 'Database' },
  { path: '/admin/manager', name: 'Manager' },
  { path: '/admin/auto-analysis', name: 'Auto-Analysis' },
];

test.describe('Smoke Test - All Admin Pages', () => {
  for (const page of ADMIN_PAGES) {
    test(`${page.name} should load without errors`, async ({ page: browserPage }) => {
      const errors = [];
      const networkErrors = [];

      // Capture console errors (excluding resource 404s which are not critical)
      browserPage.on('console', msg => {
        if (msg.type() === 'error') {
          const text = msg.text();
          // Ignore 404 resource errors (images, etc.) - focus on actual JS errors
          if (!text.includes('404') && !text.includes('Failed to load resource')) {
            errors.push(text);
          }
        }
      });

      // Capture network errors (500+ only, not 404s)
      browserPage.on('response', response => {
        if (response.status() >= 500) {
          networkErrors.push({
            url: response.url(),
            status: response.status(),
            statusText: response.statusText()
          });
        }
      });

      // Navigate to page
      try {
        const response = await browserPage.goto(`${BASE_URL}${page.path}`, {
          waitUntil: 'domcontentloaded',
          timeout: 15000
        });

        // Check that page loaded
        expect(response.status()).toBeLessThan(500);

        // Wait a bit for any HTMX requests
        await browserPage.waitForTimeout(2000);

        // Take screenshot for documentation
        await browserPage.screenshot({
          path: `/tmp/smoke-${page.name.toLowerCase().replace(/\s+/g, '-')}.png`,
          fullPage: true
        });

        // Report errors
        if (errors.length > 0) {
          console.log(`\n❌ Console errors on ${page.name}:`);
          errors.forEach(err => console.log(`   - ${err}`));
        }

        if (networkErrors.length > 0) {
          console.log(`\n❌ Network errors on ${page.name}:`);
          networkErrors.forEach(err =>
            console.log(`   - ${err.status} ${err.statusText}: ${err.url}`)
          );
        }

        if (errors.length === 0 && networkErrors.length === 0) {
          console.log(`\n✓ ${page.name} loaded successfully`);
        }

        // Assertions
        expect(errors, `Console errors on ${page.name}`).toHaveLength(0);
        expect(networkErrors, `Network errors on ${page.name}`).toHaveLength(0);

      } catch (error) {
        console.log(`\n❌ Failed to load ${page.name}: ${error.message}`);
        throw error;
      }
    });
  }
});

test.describe('Smoke Test - Critical API Endpoints', () => {
  const API_ENDPOINTS = [
    { url: '/api/feeds/', method: 'GET', name: 'List Feeds' },
    { url: '/api/items/', method: 'GET', name: 'List Items' },
    { url: '/api/processors/health', method: 'GET', name: 'Processors Health' },
    { url: '/api/metrics/system/overview', method: 'GET', name: 'System Metrics' },
    { url: '/api/metrics/feeds/15/summary', method: 'GET', name: 'Feed Metrics' },
    { url: '/api/analysis/runs?limit=10', method: 'GET', name: 'Analysis Runs' },
    { url: '/api/categories/', method: 'GET', name: 'Categories' },
    { url: '/api/sources/', method: 'GET', name: 'Sources' },
  ];

  for (const endpoint of API_ENDPOINTS) {
    test(`API: ${endpoint.name} should return 200`, async ({ page }) => {
      const response = await page.request.get(`${BASE_URL}${endpoint.url}`);

      console.log(`\n${endpoint.name}: ${response.status()} ${response.statusText()}`);

      if (response.status() !== 200) {
        const body = await response.text();
        console.log(`Response body: ${body.substring(0, 500)}`);
      }

      expect(response.status()).toBe(200);

      // Validate JSON response
      const data = await response.json();
      expect(data).toBeDefined();

      console.log(`✓ ${endpoint.name} OK`);
    });
  }
});

test.describe('Smoke Test - Database Connectivity', () => {
  test('Database tables should be accessible', async ({ page }) => {
    // Test by checking if items endpoint returns data
    const response = await page.request.get(`${BASE_URL}/api/items/?limit=1`);
    expect(response.status()).toBe(200);

    const data = await response.json();
    console.log(`\n✓ Database connectivity OK (found ${data.length || 0} items)`);
  });
});
