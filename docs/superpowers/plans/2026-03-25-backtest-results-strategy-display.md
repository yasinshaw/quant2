# Backtest Results Strategy and Parameters Display Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Display strategy name and parameters on backtest results detail page

**Architecture:** Extend existing `/api/v1/backtest/results/{result_id}/report` API endpoint to include `strategy_name` and `parameters` from the associated `BacktestJob`. Create a new `ConfigurationSection` React component to display this information in a clean, responsive card layout.

**Tech Stack:** FastAPI (backend), React/Next.js (frontend), pytest (backend testing), Playwright (E2E testing)

---

## File Structure

**Backend (3 files):**
- Modify: `backend/api/backtest.py` - Add strategy info to report response
- Modify: `tests/test_backtest_api.py` - Add tests for enhanced report endpoint
- No changes to models or database (fields already exist)

**Frontend (4 files):**
- Create: `frontend/components/ConfigurationSection.tsx` - New component for displaying configuration
- Modify: `frontend/lib/api/backtest.ts` - Extend BacktestReport interface
- Modify: `frontend/app/results/[id]/page.tsx` - Integrate ConfigurationSection component
- Create: `frontend/e2e/results-configuration.spec.ts` - E2E test for configuration display

---

## Task 1: Backend - Extend Report API with Strategy Information

**Files:**
- Modify: `backend/api/backtest.py`
- Test: `tests/test_backtest_api.py`

### Context

The `get_report()` endpoint currently returns only performance metrics. We need to:
1. Fetch the associated `BacktestJob` using the `backtest_job_id` from the result
2. Extract `strategy_name` and `parameters` fields
3. Add them to the report response
4. Handle edge cases where the job might be missing

### Steps

- [ ] **Step 1: Write failing test for report with strategy info**

Create test file: `tests/test_backtest_api.py` (or add to existing)

```python
import pytest
from datetime import datetime
from backend.models.backtest_job import BacktestJob
from backend.models.backtest_result import BacktestResult
from backend.models.trade import Trade
from backend.database import Database
from backend.config import settings

# Import fixtures and dependencies
_db = Database(settings.database_url)


def test_get_report_includes_strategy_info(client, db_session):
    """Test that report endpoint includes strategy_name and parameters."""
    # Create a backtest job with strategy info
    job = BacktestJob(
        strategy_name="TestStrategy",
        symbol="BTCUSDT",
        interval="1h",
        start_time=datetime(2024, 1, 1),
        end_time=datetime(2024, 1, 31),
        parameters={"fast_period": 10, "slow_period": 20},
        status="completed"
    )
    db_session.add(job)
    db_session.flush()

    # Create backtest result
    result = BacktestResult(
        backtest_job_id=job.id,
        total_return=0.15,
        sharpe_ratio=1.5,
        max_drawdown=0.08,
        win_rate=0.6,
        profit_factor=1.8,
        total_trades=50,
        initial_cash=100000,
        final_value=115000
    )
    db_session.add(result)
    db_session.commit()

    # Call the report endpoint
    response = client.get(f"/api/v1/backtest/results/{result.id}/report")

    # Verify response includes strategy info
    assert response.status_code == 200
    data = response.json()
    assert "strategy_name" in data
    assert data["strategy_name"] == "TestStrategy"
    assert "parameters" in data
    assert data["parameters"] == {"fast_period": 10, "slow_period": 20}


def test_get_report_with_missing_job(client, db_session):
    """Test that report handles missing BacktestJob gracefully."""
    # Create result without associated job (edge case)
    result = BacktestResult(
        backtest_job_id=99999,  # Non-existent job ID
        total_return=0.15,
        sharpe_ratio=1.5,
        max_drawdown=0.08,
        win_rate=0.6,
        profit_factor=1.8,
        total_trades=50,
        initial_cash=100000,
        final_value=115000
    )
    db_session.add(result)
    db_session.commit()

    # Call the report endpoint - should not fail
    response = client.get(f"/api/v1/backtest/results/{result.id}/report")

    # Verify response includes default values
    assert response.status_code == 200
    data = response.json()
    assert "strategy_name" in data
    assert data["strategy_name"] == "Unknown"
    assert "parameters" in data
    assert data["parameters"] == {}
```

Run: `pytest tests/test_backtest_api.py::test_get_report_includes_strategy_info -v`

Expected: FAIL (test fails because endpoint doesn't return strategy info yet)

- [ ] **Step 2: Implement strategy info in get_report()**

Modify file: `backend/api/backtest.py`

Find the `get_report()` function (around line 381) and modify it:

```python
@router.get("/results/{result_id}/report")
async def get_report(result_id: int) -> Dict[str, Any]:
    """
    Get detailed backtest report.

    Args:
        result_id: BacktestResult ID to generate report for

    Returns:
        Dict containing:
            - summary: Performance metrics summary
            - monthly_returns: Monthly returns breakdown
            - trade_analysis: Per-trade analysis with statistics
            - equity_curve: Equity curve data
            - strategy_name: Strategy used for backtest
            - parameters: Strategy parameters used

    Raises:
        HTTPException: 404 if result not found
    """
    result = _db.get_backtest_result(result_id)

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Result {result_id} not found"
        )

    # Get trades
    trades = _db.get_trades(result.backtest_job_id)

    # Generate report
    report = _report_generator.generate_report(result, trades)

    # Get job information for strategy details
    job = _db.get_backtest_job(result.backtest_job_id)

    # Add strategy information to report
    if job:
        report['strategy_name'] = job.strategy_name
        report['parameters'] = job.parameters if job.parameters else {}
    else:
        # Handle edge case: job might be missing for old results
        logger.warning(f"BacktestJob {result.backtest_job_id} not found for result {result_id}")
        report['strategy_name'] = "Unknown"
        report['parameters'] = {}

    logger.info(f"Generated report for result {result_id} with {len(trades)} trades")

    return report
```

- [ ] **Step 3: Run tests to verify implementation**

Run: `pytest tests/test_backtest_api.py::test_get_report_includes_strategy_info -v`

Expected: PASS (test now passes)

Run: `pytest tests/test_backtest_api.py::test_get_report_with_missing_job -v`

Expected: PASS (edge case test passes)

- [ ] **Step 4: Run all backend tests to ensure no regression**

Run: `pytest tests/ -v --tb=short`

Expected: All existing tests still pass

- [ ] **Step 5: Commit backend changes**

```bash
git add backend/api/backtest.py tests/test_backtest_api.py
git commit -m "feat(backtest): add strategy info to report API

- Extend /report endpoint to return strategy_name and parameters
- Fetch BacktestJob to extract configuration details
- Handle missing job gracefully with default values
- Add tests for new functionality and edge cases

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Task 2: Frontend - Extend Type Definitions

**Files:**
- Modify: `frontend/lib/api/backtest.ts`

### Steps

- [ ] **Step 1: Update BacktestReport interface**

Modify file: `frontend/lib/api/backtest.ts`

Find the `BacktestReport` interface (around line 59) and add the new fields:

```typescript
export interface BacktestReport {
  summary: {
    total_return: number;
    final_value: number;
    total_trades: number;
    win_rate: number;
    sharpe_ratio: number;
    max_drawdown: number;
    profit_factor: number;
    avg_trade: number;
    avg_winning_trade: number;
    avg_losing_trade: number;
  };
  monthly_returns: Record<string, number>;
  trade_analysis: {
    trades: Trade[];
    long_trades: number;
    short_trades: number;
    avg_hold_time: number;
    best_trade: number;
    worst_trade: number;
  };
  equity_curve: Array<{ time: string; value: number }>;
  strategy_name: string;        // NEW: Strategy name used for backtest
  parameters: Record<string, any>;  // NEW: Strategy parameters
}
```

- [ ] **Step 2: Verify TypeScript compilation**

Run: `cd frontend && pnpm tsc --noEmit`

Expected: No TypeScript errors

- [ ] **Step 3: Commit type definition changes**

```bash
git add frontend/lib/api/backtest.ts
git commit -m "feat(frontend): extend BacktestReport type with strategy info

- Add strategy_name field to BacktestReport interface
- Add parameters field to BacktestReport interface
- Enables displaying configuration in results page

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Task 3: Frontend - Create ConfigurationSection Component

**Files:**
- Create: `frontend/components/ConfigurationSection.tsx`

### Steps

- [ ] **Step 1: Create ConfigurationSection component**

Create file: `frontend/components/ConfigurationSection.tsx`

```typescript
'use client';

import React from 'react';

interface ConfigurationSectionProps {
  strategyName: string;
  parameters: Record<string, any>;
}

/**
 * Displays the strategy configuration used for a backtest.
 * Shows the strategy name and all parameters with their values.
 */
export default function ConfigurationSection({
  strategyName,
  parameters
}: ConfigurationSectionProps) {
  // Handle edge case: missing strategy name
  const displayName = strategyName || 'N/A';

  // Format parameter values for display
  const formatValue = (value: any): string => {
    if (value === null || value === undefined) {
      return 'N/A';
    }
    if (typeof value === 'object') {
      return JSON.stringify(value);
    }
    return String(value);
  };

  return (
    <div className="bg-white rounded-lg shadow-md p-6 mb-8">
      <h2 className="text-xl font-bold text-gray-900 mb-4">
        Configuration
      </h2>

      {/* Strategy Name */}
      <div className="mb-4">
        <p className="text-sm text-gray-600 mb-1">Strategy</p>
        <p className="text-lg font-semibold text-blue-600">
          {displayName}
        </p>
      </div>

      {/* Parameters */}
      <div>
        <p className="text-sm text-gray-600 mb-2">Parameters</p>
        {Object.keys(parameters).length > 0 ? (
          <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
            {Object.entries(parameters).map(([key, value]) => (
              <div key={key} className="bg-gray-50 rounded p-3">
                <p className="text-xs text-gray-500">{key}</p>
                <p className="text-sm font-medium text-gray-900">
                  {formatValue(value)}
                </p>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-sm text-gray-500">Default parameters</p>
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Verify TypeScript compilation**

Run: `cd frontend && pnpm tsc --noEmit`

Expected: No TypeScript errors

- [ ] **Step 3: Commit component creation**

```bash
git add frontend/components/ConfigurationSection.tsx
git commit -m "feat(frontend): add ConfigurationSection component

- Create new component to display strategy configuration
- Shows strategy name and parameters in card layout
- Handles edge cases: missing name, empty params, complex values
- Responsive grid layout (2 cols mobile, 3 cols desktop)

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Task 4: Frontend - Integrate ConfigurationSection into Results Page

**Files:**
- Modify: `frontend/app/results/[id]/page.tsx`

### Steps

- [ ] **Step 1: Add import for ConfigurationSection**

Modify file: `frontend/app/results/[id]/page.tsx`

Add import at the top (around line 7):

```typescript
import ConfigurationSection from '@/components/ConfigurationSection';
```

- [ ] **Step 2: Destructure new fields from report**

Find the destructuring assignment (around line 66) and add the new fields:

```typescript
const {
  summary,
  monthly_returns,
  trade_analysis,
  equity_curve,
  strategy_name,  // NEW
  parameters,     // NEW
} = report;
```

- [ ] **Step 3: Add ConfigurationSection to JSX**

Find the Trade Analysis Summary section (around line 170) and insert the new component after it:

```typescript
{/* Trade Analysis Summary */}
<div className="bg-white rounded-lg shadow-md p-6 mb-8">
  <h2 className="text-xl font-bold text-gray-900 mb-4">Trade Analysis Summary</h2>
  <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-4">
    {analysisMetrics.map((metric, index) => (
      <div key={index}>
        <p className="text-xs text-gray-600 mb-1">{metric.label}</p>
        <p className={`text-lg font-semibold ${metric.color}`}>{metric.value}</p>
      </div>
    ))}
  </div>
</div>

{/* NEW: Configuration Section */}
<ConfigurationSection
  strategyName={strategy_name}
  parameters={parameters}
/>

{/* Charts */}
<div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
  <EquityCurve data={equity_curve} />
  <MonthlyReturns data={monthly_returns} />
</div>
```

- [ ] **Step 4: Verify TypeScript compilation**

Run: `cd frontend && pnpm tsc --noEmit`

Expected: No TypeScript errors

- [ ] **Step 5: Run frontend dev server to test visually**

Run: `cd frontend && pnpm dev`

Expected: Dev server starts without errors

Visit: `http://localhost:3000/results/[any-result-id]`

Expected: Configuration section appears between Trade Analysis Summary and Charts

- [ ] **Step 6: Commit page integration**

```bash
git add frontend/app/results/[id]/page.tsx
git commit -m "feat(frontend): integrate ConfigurationSection into results page

- Import and render ConfigurationSection component
- Display strategy name and parameters from report data
- Positioned after Trade Analysis Summary, before Charts
- Maintains consistent page layout and spacing

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Task 5: Frontend - Create E2E Test

**Files:**
- Create: `frontend/e2e/results-configuration.spec.ts`

### Steps

- [ ] **Step 1: Write E2E test for configuration display**

Create file: `frontend/e2e/results-configuration.spec.ts`

```typescript
import { test, expect } from '@playwright/test';

test.describe('Backtest Results - Configuration Display', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to a backtest results page
    // Note: This assumes you have a backtest result with ID 1
    // Adjust the ID as needed for your test data
    await page.goto('/results/1');
  });

  test('should display configuration section', async ({ page }) => {
    // Wait for the page to load
    await page.waitForLoadState('networkidle');

    // Check that Configuration section is present
    const configSection = page.getByText('Configuration').first();
    await expect(configSection).toBeVisible();
  });

  test('should display strategy name', async ({ page }) => {
    await page.waitForLoadState('networkidle');

    // Check for Strategy label
    await expect(page.getByText('Strategy')).toBeVisible();

    // Check that strategy name is displayed (blue color indicates it's the strategy)
    const strategyName = page.locator('.text-blue-600');
    await expect(strategyName).toBeVisible();
    await expect(strategyName).not.toHaveText('N/A', { useInnerText: true });
  });

  test('should display parameters', async ({ page }) => {
    await page.waitForLoadState('networkidle');

    // Check for Parameters label
    await expect(page.getByText('Parameters')).toBeVisible();

    // Check that parameter cards are rendered
    const parameterCards = page.locator('.bg-gray-50');
    const count = await parameterCards.count();

    // Should have at least some parameters (or show "Default parameters")
    if (count > 0) {
      await expect(parameterCards.first()).toBeVisible();
    } else {
      await expect(page.getByText('Default parameters')).toBeVisible();
    }
  });

  test('should handle missing data gracefully', async ({ page }) => {
    // Test with a result ID that might not have strategy data
    await page.goto('/results/99999');

    await page.waitForLoadState('networkidle');

    // Should still show configuration section with N/A values
    await expect(page.getByText('Configuration')).toBeVisible();
    await expect(page.getByText('N/A')).toBeVisible();
  });
});
```

- [ ] **Step 2: Run E2E test**

Run: `cd frontend && pnpm test:e2e results-configuration.spec.ts`

Expected: Tests pass (may need to adjust result IDs based on your test data)

- [ ] **Step 3: Commit E2E test**

```bash
git add frontend/e2e/results-configuration.spec.ts
git commit -m "test(frontend): add E2E test for configuration display

- Test configuration section visibility
- Test strategy name display
- Test parameters display
- Test edge case handling for missing data

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Task 6: Verification and Integration Testing

**Files:**
- No specific files (integration testing)

### Steps

- [ ] **Step 1: Start backend server**

Run: `cd backend && python main.py`

Expected: Backend starts on http://localhost:8000

- [ ] **Step 2: Start frontend dev server**

Run: `cd frontend && pnpm dev`

Expected: Frontend starts on http://localhost:3000

- [ ] **Step 3: Run a manual backtest to generate test data**

Visit: `http://localhost:3000/backtest`

Fill out form and submit to create a new backtest result

- [ ] **Step 4: View the backtest results**

Click on the new result or visit: `http://localhost:3000/results/[new-result-id]`

Verify:
- [ ] Configuration section appears
- [ ] Strategy name is displayed correctly
- [ ] All parameters are shown with correct values
- [ ] Layout matches other sections
- [ ] Responsive on mobile view

- [ ] **Step 5: Run full test suite**

Backend: `pytest tests/ -v`

Frontend: `cd frontend && pnpm lint`

Expected: All tests pass, no linting errors

- [ ] **Step 6: Create summary commit**

```bash
git add .
git commit -m "feat: complete backtest results strategy display feature

Implementation complete:
- Backend API extended with strategy info
- Frontend ConfigurationSection component created
- Results page integration complete
- E2E tests added and passing
- All tests passing, no regressions

Success criteria met:
✓ Strategy name displayed on all result pages
✓ All parameters shown with correct values
✓ UI consistent with existing design
✓ Edge cases handled gracefully
✓ No performance degradation
✓ Tests passing

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Implementation Notes

### For Agentic Workers

1. **Follow TDD**: Each task follows write-test → implement → verify → commit cycle
2. **Run tests frequently**: Don't batch multiple steps before testing
3. **Commit often**: Each completed step gets its own commit
4. **Handle edge cases**: The code handles missing data gracefully - preserve this
5. **TypeScript safety**: Always run `pnpm tsc --noEmit` after frontend changes

### Database

No migrations needed! The `strategy_name` and `parameters` fields already exist in the `BacktestJob` model.

### API Changes

The `/api/v1/backtest/results/{result_id}/report` endpoint response is extended, not modified. This is backward compatible.

### Testing Data

For E2E tests, you may need to:
1. Create a backtest via the UI first
2. Use that result ID in your tests
3. Or seed test data in the database

### Debugging

If tests fail:
- Backend: Check `logs/` directory for detailed error logs
- Frontend: Use browser DevTools Console for errors
- API: Use `curl` or Postman to test endpoints directly

```bash
# Example: Test the report API directly
curl http://localhost:8000/api/v1/backtest/results/1/report
```

---

## Success Criteria

After completing all tasks:

- [x] Strategy name displayed on all backtest result pages
- [x] All parameters shown with correct values
- [x] UI consistent with existing design system
- [x] Handles edge cases gracefully (missing data, legacy results)
- [x] No performance degradation (same single API call)
- [x] All tests passing (backend unit tests, frontend E2E tests)
