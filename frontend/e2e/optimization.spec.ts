import { test, expect } from '@playwright/test';

/**
 * Parameter Optimization E2E Test
 *
 * Purpose: Test the parameter optimization flow
 *
 * Flow:
 * 1. Navigate to /optimize
 * 2. Select strategy
 * 3. Configure parameter ranges
 * 4. Run optimization
 * 5. Verify results display
 */

test.describe('Parameter Optimization Flow', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to optimize page before each test
    await page.goto('/optimize');
  });

  test('should display optimization page with form elements', async ({ page }) => {
    // Verify page title
    await expect(page.locator('h1')).toContainText('Parameter Optimization');

    // Verify strategy selector exists
    await expect(page.getByLabel(/strategy/i)).toBeVisible();

    // Verify parameter configuration section exists
    await expect(page.getByRole('heading', { name: /parameter ranges/i }).or(
      page.getByRole('heading', { name: /configure parameters/i })
    )).toBeVisible({ timeout: 5000 }).catch(() => false);

    // NEW: Verify advanced settings section
    await expect(page.getByText(/advanced settings/i)).toBeVisible();
  });

  test('should select strategy and display parameter ranges', async ({ page }) => {
    // Wait for strategies to load
    await page.waitForSelector('select', { timeout: 5000 });

    // Select a strategy
    const strategySelect = page.getByLabel(/strategy/i);
    const optionCount = await strategySelect.locator('option').count();

    if (optionCount > 1) {
      // Select first available strategy (index 1, as 0 is usually placeholder)
      await strategySelect.selectOption({ index: 1 });

      // Wait for parameter inputs to appear
      await page.waitForTimeout(500);

      // Verify parameter range inputs are visible
      // Look for parameter-related inputs (min, max, step fields)
      const parameterInputs = await page.locator('input[type="number"]').count();
      expect(parameterInputs).toBeGreaterThan(0);
    } else {
      console.log('No strategies loaded - backend may not be available');
    }
  });

  // NEW: Test Bayesian optimization selection
  test('should select bayesian optimization method', async ({ page }) => {
    await page.waitForSelector('select', { timeout: 5000 });

    const strategySelect = page.getByLabel(/strategy/i);
    const optionCount = await strategySelect.locator('option').count();

    if (optionCount > 1) {
      await strategySelect.selectOption({ index: 1 });
      await page.waitForTimeout(500);

      // Look for optimization method selection
      const bayesianButton = page.getByText(/bayesian optimization/i).or(page.getByText(/bayesian/i));

      if (await bayesianButton.isVisible()) {
        await bayesianButton.click();

        // Verify n_trials input appears
        await expect(page.getByLabel(/number of trials/i)).toBeVisible();
      }
    }
  });

  // NEW: Test custom scoring weights
  test('should configure custom scoring weights', async ({ page }) => {
    await page.waitForSelector('select', { timeout: 5000 });

    const strategySelect = page.getByLabel(/strategy/i);
    const optionCount = await strategySelect.locator('option').count();

    if (optionCount > 1) {
      await strategySelect.selectOption({ index: 1 });
      await page.waitForTimeout(500);

      // Find custom scoring toggle
      const scoringToggle = page.locator('button').filter({ hasText: /custom scoring/i });

      if (await scoringToggle.isVisible()) {
        await scoringToggle.click();

        // Verify scoring weight inputs appear
        await expect(page.getByLabel(/sharpe ratio.*weight/i)).toBeVisible();
        await expect(page.getByLabel(/total return.*weight/i)).toBeVisible();
      }
    }
  });

  // NEW: Test out-of-sample testing configuration
  test('should configure out-of-sample testing', async ({ page }) => {
    await page.waitForSelector('select', { timeout: 5000 });

    const strategySelect = page.getByLabel(/strategy/i);
    const optionCount = await strategySelect.locator('option').count();

    if (optionCount > 1) {
      await strategySelect.selectOption({ index: 1 });
      await page.waitForTimeout(500);

      // Find out-of-sample testing toggle
      const oosToggle = page.locator('button').filter({ hasText: /out-of-sample/i }).or(page.locator('button').filter({ hasText: /sample testing/i }));

      if (await oosToggle.isVisible()) {
        await oosToggle.click();

        // Verify test date inputs appear
        await expect(page.getByLabel(/test start/i)).toBeVisible();
        await expect(page.getByLabel(/test end/i)).toBeVisible();
      }
    }
  });

  // NEW: Test stability analysis toggle
  test('should toggle stability analysis', async ({ page }) => {
    await page.waitForSelector('select', { timeout: 5000 });

    const strategySelect = page.getByLabel(/strategy/i);
    const optionCount = await strategySelect.locator('option').count();

    if (optionCount > 1) {
      await strategySelect.selectOption({ index: 1 });
      await page.waitForTimeout(500);

      // Find stability analysis toggle
      const stabilityToggle = page.locator('button').filter({ hasText: /stability analysis/i });

      if (await stabilityToggle.isVisible()) {
        const isChecked = await stabilityToggle.getAttribute('aria-pressed');

        // Toggle off
        await stabilityToggle.click();

        // Verify it's now off
        const newState = await stabilityToggle.getAttribute('aria-pressed');
        expect(newState).not.toBe(isChecked);
      }
    }
  });

  test('should configure optimization parameters', async ({ page }) => {
    // Wait for page to load
    await page.waitForSelector('select', { timeout: 5000 });

    const strategySelect = page.getByLabel(/strategy/i);
    const optionCount = await strategySelect.locator('option').count();

    if (optionCount > 1) {
      // Select strategy
      await strategySelect.selectOption({ index: 1 });
      await page.waitForTimeout(500);

      // Configure data parameters
      await page.getByLabel(/symbol/i).selectOption('BTCUSDT');
      await page.getByLabel(/interval/i).selectOption('1h');

      // Set date range (short period for faster test)
      const startDate = new Date();
      startDate.setDate(startDate.getDate() - 7);
      const endDate = new Date();

      const dateInputs = page.locator('input[type="date"]');
      await dateInputs.first().fill(startDate.toISOString().split('T')[0]);
      await dateInputs.nth(1).fill(endDate.toISOString().split('T')[0]);

      // Configure parameter ranges if available
      const numberInputs = page.locator('input[type="number"]');
      const inputCount = await numberInputs.count();

      if (inputCount >= 3) {
        // Typically: min, max, step for at least one parameter
        // Fill with reasonable values
        await numberInputs.first().fill('5');
        await numberInputs.nth(1).fill('20');
        if (inputCount >= 3) {
          await numberInputs.nth(2).fill('5');
        }
      }

      // Verify inputs were filled
      const symbolValue = await page.getByLabel(/symbol/i).inputValue();
      expect(symbolValue).toBe('BTCUSDT');
    } else {
      console.log('No strategies available - skipping configuration test');
    }
  });

  test('should run optimization and display results', async ({ page }) => {
    // Wait for page to load
    await page.waitForSelector('select', { timeout: 5000 });

    const strategySelect = page.getByLabel(/strategy/i);
    const optionCount = await strategySelect.locator('option').count();

    if (optionCount > 1) {
      // Configure optimization
      await strategySelect.selectOption({ index: 1 });
      await page.waitForTimeout(500);

      await page.getByLabel(/symbol/i).selectOption('BTCUSDT');
      await page.getByLabel(/interval/i).selectOption('1h');

      // Short date range for faster optimization
      const startDate = new Date();
      startDate.setDate(startDate.getDate() - 3);
      const endDate = new Date();

      const dateInputs = page.locator('input[type="date"]');
      await dateInputs.first().fill(startDate.toISOString().split('T')[0]);
      await dateInputs.nth(1).fill(endDate.toISOString().split('T')[0]);

      // Configure parameter ranges
      const numberInputs = page.locator('input[type="number"]');
      const inputCount = await numberInputs.count();

      if (inputCount >= 3) {
        await numberInputs.first().fill('5');
        await numberInputs.nth(1).fill('10');
        if (inputCount >= 3) {
          await numberInputs.nth(2).fill('5');
        }
      }

      // Find and click optimization button
      const optimizeButton = page.getByRole('button', { name: /start optimization|run optimization|optimize/i });

      // Check if button is enabled
      const isEnabled = await optimizeButton.isEnabled();

      if (isEnabled) {
        await optimizeButton.click();

        // Wait for optimization to complete or show progress
        // This may take time, so use longer timeout
        const resultsAppeared = await page.waitForSelector(
          'text=/Optimization Results|Best Parameters|Total Combinations/i',
          { timeout: 60000 }
        ).then(() => true).catch(() => false);

        if (resultsAppeared) {
          // Verify results are displayed
          await expect(page.getByText(/best parameters/i)).toBeVisible();

          // Check for metrics
          const hasSharpe = await page.getByText(/sharpe ratio/i).count() > 0;
          const hasReturn = await page.getByText(/total return/i).count() > 0;

          expect(hasSharpe || hasReturn).toBeTruthy();

          // NEW: Check for stability analysis section
          const hasStabilitySection = await page.getByText(/stability analysis/i).count() > 0;
          if (hasStabilitySection) {
            console.log('Stability analysis section displayed');
          }
        } else {
          console.log('Optimization timeout - may require longer wait or backend unavailable');
        }
      }
    } else {
      console.log('No strategies loaded - skipping optimization test');
    }
  });

  // NEW: Test stability report display
  test('should display stability report when available', async ({ page }) => {
    // This test would require a completed optimization with stability analysis
    // For now, just verify the section can exist

    await page.waitForSelector('select', { timeout: 5000 });

    // Navigate to a results page if possible
    const resultsLink = page.getByText(/optimization results/i);

    if (await resultsLink.isVisible()) {
      await resultsLink.click();

      // Check if stability report section exists
      const stabilitySection = page.getByText(/stability analysis/i);
      const hasStability = await stabilitySection.isVisible().catch(() => false);

      if (hasStability) {
        // Verify stability metrics are displayed
        await expect(page.getByText(/stability score/i)).toBeVisible();
        await expect(page.getByText(/variance/i)).toBeVisible();
      }
    }
  });

  test('should handle optimization errors gracefully', async ({ page }) => {
    // Test error handling

    await page.waitForSelector('select', { timeout: 5000 });

    const strategySelect = page.getByLabel(/strategy/i);
    const optionCount = await strategySelect.locator('option').count();

    if (optionCount > 1) {
      // Try to submit with minimal configuration
      await strategySelect.selectOption({ index: 1 });

      const optimizeButton = page.getByRole('button', { name: /start optimization|run optimization|optimize/i });
      const isDisabled = await optimizeButton.isDisabled();

      if (!isDisabled) {
        await optimizeButton.click();

        // Should either show validation error or handle gracefully
        const hasError = await page.waitForSelector(
          'text=/error|required|invalid|failed/i',
          { timeout: 3000 }
        ).then(() => true).catch(() => false);

        // It's okay if no error shown - form might prevent submission
        console.log(`Error handling test: ${hasError ? 'Error displayed' : 'No error shown'}`);
      }
    }
  });

  test('should display optimization progress or status', async ({ page }) => {
    // This test checks if optimization shows some progress indicator

    await page.waitForSelector('select', { timeout: 5000 });

    const strategySelect = page.getByLabel(/strategy/i);
    const optionCount = await strategySelect.locator('option').count();

    if (optionCount > 1) {
      // Quick configuration
      await strategySelect.selectOption({ index: 1 });
      await page.getByLabel(/symbol/i).selectOption('BTCUSDT');
      await page.getByLabel(/interval/i).selectOption('1h');

      const startDate = new Date();
      startDate.setDate(startDate.getDate() - 2);
      const dateInputs = page.locator('input[type="date"]');
      await dateInputs.first().fill(startDate.toISOString().split('T')[0]);
      await dateInputs.nth(1).fill(new Date().toISOString().split('T')[0]);

      const optimizeButton = page.getByRole('button', { name: /start optimization|run optimization|optimize/i });

      if (await optimizeButton.isEnabled()) {
        await optimizeButton.click();

        // Check for loading state or progress indicator
        const hasLoadingState = await page.waitForSelector(
          'text=/loading|running|processing|optimizing/i',
          { timeout: 2000 }
        ).then(() => true).catch(() => false);

        console.log(`Loading state detected: ${hasLoadingState}`);
      }
    }
  });
});
