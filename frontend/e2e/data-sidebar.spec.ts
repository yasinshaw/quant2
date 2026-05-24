import { test, expect } from '@playwright/test';

/**
 * Downloaded Data Sidebar E2E Test
 *
 * Purpose: Test the sidebar component that displays downloaded data
 *
 * Flow:
 * 1. Verify sidebar visibility on data page
 * 2. Test empty state when no data available
 * 3. Test data display after download
 * 4. Test expand/collapse functionality
 * 5. Test form update when clicking items
 * 6. Test selection highlighting
 */

test.describe('Downloaded Data Sidebar', () => {
  test.beforeEach(async ({ page }) => {
    // Visit data management page before each test
    await page.goto('/data');
  });

  test('should display sidebar on data page', async ({ page }) => {
    // Verify sidebar title exists
    const sidebar = page.locator('text=已下载数据');
    await expect(sidebar).toBeVisible();
  });

  test('should show empty state when no data', async ({ page }) => {
    // Verify empty state message is displayed
    // This test assumes no data has been downloaded yet
    const emptyMessage = page.locator('text=暂无已下载数据');
    await expect(emptyMessage).toBeVisible();
  });

  test('should show symbol list after download', async ({ page }) => {
    // Select symbol
    await page.locator('select').first().selectOption('BTCUSDT');

    // Select interval
    await page.locator('select').nth(1).selectOption('1h');

    // Set time range (small range for faster test)
    const startDate = new Date();
    startDate.setDate(startDate.getDate() - 2);
    const endDate = new Date();
    endDate.setDate(endDate.getDate() - 1);

    await page.locator('input[type="date"]').first().fill(startDate.toISOString().split('T')[0]);
    await page.locator('input[type="date"]').nth(1).fill(endDate.toISOString().split('T')[0]);

    // Click download button
    await page.getByRole('button', { name: /download/i }).click();

    // Wait for download to complete
    await page.waitForSelector(
      'text=/Download (Successful|Failed|Already Exists)/i',
      { timeout: 20000 }
    );

    // Refresh page to trigger sidebar data reload
    await page.reload();

    // Verify sidebar shows BTCUSDT
    const symbolItem = page.locator('text=BTCUSDT');
    await expect(symbolItem).toBeVisible();
  });

  test('should expand symbol to show intervals', async ({ page }) => {
    // This test assumes data already exists from previous test
    // Navigate to page
    await page.goto('/data');

    // Wait for sidebar to load
    await page.waitForSelector('text=已下载数据', { timeout: 5000 });

    // Check if BTCUSDT exists (may need to download first)
    const symbolItem = page.locator('text=BTCUSDT');
    const symbolCount = await symbolItem.count();

    if (symbolCount > 0) {
      // Click symbol to expand
      await symbolItem.first().click();

      // Verify interval is displayed
      const intervalItem = page.locator('text=1h');
      await expect(intervalItem).toBeVisible();
    } else {
      // Skip test if no data available
      test.skip();
    }
  });

  test('should update form when clicking interval', async ({ page }) => {
    // This test assumes data already exists
    await page.goto('/data');

    // Wait for sidebar to load
    await page.waitForSelector('text=已下载数据', { timeout: 5000 });

    // Check if BTCUSDT exists
    const symbolItem = page.locator('text=BTCUSDT');
    const symbolCount = await symbolItem.count();

    if (symbolCount > 0) {
      // Click symbol to expand
      await symbolItem.first().click();

      // Wait for interval to appear
      await page.waitForSelector('text=1h', { timeout: 5000 });

      // Click on interval
      await page.locator('text=1h').click();

      // Verify form has been updated with selected values
      const symbolSelect = page.locator('select').first();
      const intervalSelect = page.locator('select').nth(1);

      await expect(symbolSelect).toHaveValue('BTCUSDT');
      await expect(intervalSelect).toHaveValue('1h');
    } else {
      // Skip test if no data available
      test.skip();
    }
  });

  test('should highlight selected item', async ({ page }) => {
    // This test assumes data already exists
    await page.goto('/data');

    // Wait for sidebar to load
    await page.waitForSelector('text=已下载数据', { timeout: 5000 });

    // Check if BTCUSDT exists
    const symbolItem = page.locator('text=BTCUSDT');
    const symbolCount = await symbolItem.count();

    if (symbolCount > 0) {
      // Click symbol to expand
      await symbolItem.first().click();

      // Wait for interval to appear
      await page.waitForSelector('text=1h', { timeout: 5000 });

      // Click on interval
      await page.locator('text=1h').click();

      // Verify selection highlighting (blue background)
      const selectedItem = page.locator('.bg-blue-100, [class*="bg-blue"]');
      await expect(selectedItem).toBeVisible();
    } else {
      // Skip test if no data available
      test.skip();
    }
  });
});
