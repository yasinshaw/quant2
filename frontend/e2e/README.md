# E2E Testing with Playwright

This directory contains end-to-end tests for the Quantitative Trading Platform using Playwright.

## Test Structure

### navigation.spec.ts
Tests basic navigation across all pages:
- Home page display
- Navigation to Strategies, Data, Backtest, and Optimize pages
- Quick action cards
- Active link highlighting

### data-download.spec.ts
Tests the data download flow:
- Data management page display
- Symbol and interval selection
- Date range configuration
- Data download initiation
- Data status cards display

### backtest-flow.spec.ts
Tests the backtest execution flow:
- Backtest page display
- Strategy selection
- Parameter configuration
- Backtest execution
- Results display with key metrics

### optimization.spec.ts
Tests the parameter optimization flow:
- Optimization page display
- Strategy selection
- Parameter range configuration
- Optimization execution
- Results display

## Running Tests

### Prerequisites
1. Ensure the frontend is running:
   ```bash
   cd frontend
   npm run dev
   ```

2. (Optional) Ensure the backend is running for full integration tests:
   ```bash
   cd backend
   python -m uvicorn app.main:app --reload
   ```

### Run All Tests
```bash
npm run test:e2e
```

### Run Specific Test File
```bash
npx playwright tests e2e/navigation.spec.ts
```

### Run Tests with UI
```bash
npm run test:e2e:ui
```

### Debug Tests
```bash
npm run test:e2e:debug
```

### View Test Report
```bash
npm run test:e2e:report
```

## Test Guidelines

### Best Practices
- Tests use realistic timeouts to handle async operations
- Tests are resilient to backend unavailability
- Tests focus on critical user flows, not edge cases
- Tests use semantic selectors when possible
- Tests handle loading states appropriately

### Handling Backend Unavailability
Tests are designed to work even when the backend is not running:
- Tests check for data availability before proceeding
- Tests accept both success and error states
- Tests use appropriate timeouts for async operations

### Selectors
- Prefer role-based selectors: `getByRole()`, `getByLabel()`, `getByText()`
- Use data-testid attributes for complex elements if needed
- Avoid brittle selectors like CSS classes or DOM structure

## Test Configuration

Configuration is in `playwright.config.ts`:
- Base URL: http://localhost:3000
- Browser: Chromium (can add Firefox, WebKit)
- Screenshots: On failure
- Traces: On retry
- Parallel execution: Enabled

## Troubleshooting

### Tests Fail with Timeout
- Ensure frontend is running on port 3000
- Check if backend is needed and running
- Increase timeout in specific tests if needed

### Tests Fail with Selector Not Found
- Check if page structure has changed
- Update selectors to match current UI
- Use `--debug` flag to inspect page

### No Tests Run
- Verify Playwright is installed: `npx playwright install`
- Check test file naming: `*.spec.ts`
- Verify test directory in config: `testDir: './e2e'`

## CI/CD Integration

For CI/CD pipelines, tests can be run with:
```bash
# Install dependencies
npm ci

# Install Playwright browsers
npx playwright install --with-deps chromium

# Run tests
npm run test:e2e
```

## Future Improvements

Consider adding:
- Page Object Model for complex flows
- Visual regression testing
- API mocking for consistent test results
- Performance testing
- Mobile viewport testing
