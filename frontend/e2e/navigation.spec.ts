import { test, expect } from '@playwright/test';

/**
 * Navigation E2E Test
 *
 * Purpose: Test basic navigation across all main pages of the application
 *
 * Flow:
 * 1. Visit home page
 * 2. Click each navigation link
 * 3. Verify correct page loads
 */

test.describe('Navigation', () => {
  test.beforeEach(async ({ page }) => {
    // Start from the home page before each test
    await page.goto('/');
  });

  test('should display home page with navigation', async ({ page }) => {
    // Verify home page loads
    await expect(page).toHaveTitle(/Quantitative Trading Platform/);

    // Verify main heading is visible
    await expect(page.locator('h1')).toContainText('Quantitative Trading Platform');

    // Verify quick action cards are visible
    await expect(page.getByText('Manage Strategies')).toBeVisible();
    await expect(page.getByText('Download Data')).toBeVisible();
    await expect(page.getByText('Run Backtest')).toBeVisible();
    await expect(page.getByText('Optimize Parameters')).toBeVisible();
  });

  test('should navigate to Strategies page', async ({ page }) => {
    // Click on Strategies nav link
    await page.getByRole('link', { name: /strategies/i }).click();

    // Verify URL
    await expect(page).toHaveURL('/strategies');

    // Verify page content
    await expect(page.locator('h1')).toContainText('Trading Strategies');
  });

  test('should navigate to Data page', async ({ page }) => {
    // Click on Data nav link
    await page.getByRole('link', { name: /data/i }).click();

    // Verify URL
    await expect(page).toHaveURL('/data');

    // Verify page content
    await expect(page.locator('h1')).toContainText('Data Management');
  });

  test('should navigate to Backtest page', async ({ page }) => {
    // Click on Backtest nav link
    await page.getByRole('link', { name: /backtest/i }).click();

    // Verify URL
    await expect(page).toHaveURL('/backtest');

    // Verify page content
    await expect(page.locator('h1')).toContainText('Run Backtest');
  });

  test('should navigate to Optimize page', async ({ page }) => {
    // Click on Optimize nav link
    await page.getByRole('link', { name: /optimize/i }).click();

    // Verify URL
    await expect(page).toHaveURL('/optimize');

    // Verify page content
    await expect(page.locator('h1')).toContainText('Parameter Optimization');
  });

  test('should navigate using quick action cards from home', async ({ page }) => {
    // Test Strategies quick action
    await page.getByText('Manage Strategies').click();
    await expect(page).toHaveURL('/strategies');
    await page.goBack();

    // Test Data quick action
    await page.getByText('Download Data').click();
    await expect(page).toHaveURL('/data');
    await page.goBack();

    // Test Backtest quick action
    await page.getByText('Run Backtest').click();
    await expect(page).toHaveURL('/backtest');
    await page.goBack();

    // Test Optimize quick action
    await page.getByText('Optimize Parameters').click();
    await expect(page).toHaveURL('/optimize');
  });

  test('should highlight active navigation link', async ({ page }) => {
    // Navigate to Data page
    await page.getByRole('link', { name: /data/i }).click();
    await expect(page).toHaveURL('/data');

    // Verify Data link has active styling
    const dataLink = page.getByRole('link', { name: /data/i });
    await expect(dataLink).toHaveAttribute('aria-current', 'page');
  });
});
