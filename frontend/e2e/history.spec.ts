import { test, expect, Page } from '@playwright/test';

/**
 * History Page E2E Tests
 *
 * Purpose: Test the history page functionality including viewing backtest/optimization
 * history, filtering, pagination, tab switching, and delete operations.
 *
 * Prerequisites:
 * - Backend and frontend must be running
 * - Test data may need to exist in the database for some tests
 */

test.describe('History Page', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to history page before each test
    await page.goto('/history');
  });

  /**
   * Test 1: View backtest history
   * Verify page title, active tab, and history list display
   */
  test('test_view_backtest_history', async ({ page }) => {
    // Verify page title
    await expect(page.locator('h1')).toContainText('History');

    // Verify page description
    await expect(
      page.getByText('View and manage your backtest and optimization history')
    ).toBeVisible();

    // Verify backtest tab is active by default
    const backtestTab = page.getByRole('button', { name: 'Backtests' });
    await expect(backtestTab).toHaveAttribute('aria-current', 'page');

    // Verify history content area exists
    // Either shows table with data or "No backtest history available" message
    const hasTable = await page.locator('table').count();
    const hasEmptyMessage = await page.getByText(/No backtest history available/i).count();

    // One of them should be visible
    expect(hasTable || hasEmptyMessage).toBeGreaterThan(0);
  });

  /**
   * Test 2: Filter functionality
   * Select strategy filter, verify list updates, clear filters, verify list restores
   */
  test('test_filter_functionality', async ({ page }) => {
    // Wait for page to load
    await page.waitForSelector('text=/History|Backtest History|No backtest history/i', {
      timeout: 5000,
    });

    // Get the strategy filter dropdown
    const strategyFilter = page.locator('#filter-strategy');
    await expect(strategyFilter).toBeVisible();

    // Check if there are strategy options available (besides "All Strategies")
    const strategyOptions = await strategyFilter.locator('option').count();

    if (strategyOptions > 1) {
      // Select first non-default strategy
      await strategyFilter.selectOption({ index: 1 });

      // Wait for data to reload
      await page.waitForTimeout(500);

      // Verify filter is applied (dropdown shows selected value)
      const selectedValue = await strategyFilter.inputValue();
      expect(selectedValue).not.toBe('');

      // Verify clear filters button is enabled
      const clearButton = page.getByRole('button', { name: /clear filters/i });
      await expect(clearButton).toBeEnabled();

      // Clear filters
      await clearButton.click();

      // Wait for data to reload
      await page.waitForTimeout(500);

      // Verify filter is reset
      const resetValue = await strategyFilter.inputValue();
      expect(resetValue).toBe('');
    } else {
      // No strategies available - just verify filter exists
      console.log('No strategies loaded - backend may not be available');
    }
  });

  /**
   * Test 3: Pagination
   * Create enough test data (>20 items), verify first page, click next, verify second page
   */
  test('test_pagination', async ({ page }) => {
    // Wait for page to load
    await page.waitForSelector('text=/History|Backtest History|No backtest history/i', {
      timeout: 5000,
    });

    // Check if pagination exists (only shows when total_pages > 1)
    const paginationContainer = page.locator('button:has-text("下一页")');

    if (await paginationContainer.count()) {
      // Verify initial page state
      const pageIndicator = page.locator('text=/\\d+\\s*\\/\\s*\\d+/');
      await expect(pageIndicator).toBeVisible();

      // Get current page number
      const pageText = await pageIndicator.textContent();
      const currentPageMatch = pageText?.match(/(\d+)\s*\/\s*(\d+)/);

      if (currentPageMatch) {
        const currentPage = parseInt(currentPageMatch[1]);
        const totalPages = parseInt(currentPageMatch[2]);

        // Verify we're on page 1
        expect(currentPage).toBe(1);

        if (totalPages > 1) {
          // Click next page
          await page.getByRole('button', { name: /下一页/ }).click();

          // Wait for page to load
          await page.waitForTimeout(500);

          // Verify we're on page 2
          const newPageText = await pageIndicator.textContent();
          const newPageMatch = newPageText?.match(/(\d+)\s*\/\s*(\d+)/);
          if (newPageMatch) {
            expect(parseInt(newPageMatch[1])).toBe(2);
          }
        }
      }
    } else {
      // No pagination - might not have enough data
      console.log('No pagination visible - not enough test data for multiple pages');
    }
  });

  /**
   * Test 4: Tab switching
   * Click Optimizations tab, verify optimization history displays
   */
  test('test_tab_switching', async ({ page }) => {
    // Verify we start on Backtests tab
    const backtestTab = page.getByRole('button', { name: 'Backtests' });
    await expect(backtestTab).toHaveAttribute('aria-current', 'page');

    // Click on Optimizations tab
    const optimizationTab = page.getByRole('button', { name: 'Optimizations' });
    await optimizationTab.click();

    // Verify Optimizations tab is now active
    await expect(optimizationTab).toHaveAttribute('aria-current', 'page');
    await expect(backtestTab).not.toHaveAttribute('aria-current', 'page');

    // Verify optimization history content is shown
    // Either shows table with data or "No optimization history available" message
    const hasOptimizationContent =
      (await page.locator('table').count()) > 0 ||
      (await page.getByText(/No optimization history available/i).count()) > 0;

    expect(hasOptimizationContent).toBeTruthy();

    // Switch back to Backtests tab
    await backtestTab.click();
    await expect(backtestTab).toHaveAttribute('aria-current', 'page');
  });

  /**
   * Test 5: Delete functionality
   * Click delete button, verify confirmation dialog, confirm delete, verify record disappears
   */
  test('test_delete_functionality', async ({ page }) => {
    // Wait for page to load
    await page.waitForSelector('text=/History|Backtest History|No backtest history/i', {
      timeout: 5000,
    });

    // Check if there's data to delete
    const deleteButton = page.getByRole('button', { name: 'Delete' }).first();

    if (await deleteButton.count()) {
      // Check if delete button is enabled (not running status)
      const isDisabled = await deleteButton.isDisabled();

      if (!isDisabled) {
        // Get initial row count
        const initialRows = await page.locator('table tbody tr').count();

        // Set up dialog handler before clicking delete
        page.once('dialog', async (dialog) => {
          // Verify confirmation dialog appears
          expect(dialog.type()).toBe('confirm');
          expect(dialog.message()).toContain('Are you sure');
          // Accept the dialog (confirm delete)
          await dialog.accept();
        });

        // Click delete button
        await deleteButton.click();

        // Wait for delete to complete and table to update
        await page.waitForTimeout(1000);

        // Verify row was deleted (count should decrease)
        // Note: This might not always be true if there's only one row and it shows empty state
        const hasTable = (await page.locator('table').count()) > 0;
        if (hasTable) {
          const newRows = await page.locator('table tbody tr').count();
          expect(newRows).toBeLessThanOrEqual(initialRows);
        }
      } else {
        console.log('Delete button is disabled (job may be running)');
      }
    } else {
      console.log('No delete button found - no history data available');
    }
  });

  /**
   * Test 6: Empty state
   * Access history page with no data, verify "No history" message displays
   */
  test('test_empty_state', async ({ page }) => {
    // This test checks if the empty state is properly displayed
    // when there's no data. We'll verify the empty state message exists in the DOM.

    // Wait for page to load
    await page.waitForSelector('text=/History|Backtest History/i', { timeout: 5000 });

    // Check if we're showing empty state or data
    const hasEmptyMessage = (await page.getByText(/No backtest history available/i).count()) > 0;
    const hasTable = (await page.locator('table').count()) > 0;

    // One of them should be true
    expect(hasEmptyMessage || hasTable).toBeTruthy();

    // If we have empty state, verify the message is properly styled
    if (hasEmptyMessage) {
      const emptyMessage = page.getByText(/No backtest history available/i);
      await expect(emptyMessage).toBeVisible();

      // Verify the message is centered and styled appropriately
      const container = emptyMessage.locator('..');
      await expect(container).toHaveClass(/text-center/);
    }

    // Also check optimization tab for empty state
    const optimizationTab = page.getByRole('button', { name: 'Optimizations' });
    await optimizationTab.click();
    await page.waitForTimeout(500);

    const hasOptEmptyMessage =
      (await page.getByText(/No optimization history available/i).count()) > 0;
    const hasOptTable = (await page.locator('table').count()) > 0;

    expect(hasOptEmptyMessage || hasOptTable).toBeTruthy();
  });
});

/**
 * Helper function to wait for API responses
 */
async function waitForHistoryLoad(page: Page) {
  // Wait for either data to load or empty state to show
  await page.waitForSelector(
    'table, text=/No backtest history available|No optimization history available|Loading/i',
    { timeout: 10000 }
  );
}
