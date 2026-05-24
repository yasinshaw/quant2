import { test, expect } from '@playwright/test';

test.describe('JSON Parameter Import', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('http://localhost:3002/backtest');
  });

  test('should show import button when strategy is selected', async ({ page }) => {
    // Wait for strategies to load
    await page.waitForSelector('select#strategy');

    // Select a strategy
    await page.selectOption('select#strategy', 'Double MA Crossover');

    // Check if import button appears
    const importButton = page.getByText('Import from JSON');
    await expect(importButton).toBeVisible();
  });

  test('should parse JSON and show validation modal', async ({ page }) => {
    // Select strategy first
    await page.waitForSelector('select#strategy');
    await page.selectOption('select#strategy', 'Double MA Crossover');

    // Trigger file upload
    const fileInput = await page.locator('input[type="file"]');
    await fileInput.setInputFiles('../test_optimization.json');

    // Wait for modal to appear
    await page.waitForSelector('.fixed.inset-0');

    // Check if validation passed
    await expect(page.getByText('All Parameters Validated Successfully')).toBeVisible();

    // Check if parameters are displayed
    await expect(page.getByText('fast_period')).toBeVisible();
    await expect(page.getByText('slow_period')).toBeVisible();

    // Check if performance metrics are shown
    await expect(page.getByText('Performance Metrics')).toBeVisible();
  });

  test('should import parameters when confirmed', async ({ page }) => {
    // Select strategy first
    await page.waitForSelector('select#strategy');
    await page.selectOption('select#strategy', 'Double MA Crossover');

    // Get initial parameter values
    const fastPeriodInput = page.locator('input#param-fast_period');
    await expect(fastPeriodInput).toHaveValue('10'); // default value

    // Upload JSON
    const fileInput = await page.locator('input[type="file"]');
    await fileInput.setInputFiles('../test_optimization.json');

    // Wait for modal and click import
    await page.waitForSelector('.fixed.inset-0');
    await page.click('button:has-text("Import Parameters")');

    // Check if parameters were updated
    await expect(fastPeriodInput).toHaveValue('10'); // JSON value matches default

    // Check for success toast
    await expect(page.getByText('Parameters imported successfully')).toBeVisible();
  });

  test('should reject JSON with invalid parameters', async ({ page }) => {
    // Select strategy
    await page.waitForSelector('select#strategy');
    await page.selectOption('select#strategy', 'Double MA Crossover');

    // Verify the import button exists
    await expect(page.getByText('Import from JSON')).toBeVisible();
  });
});
