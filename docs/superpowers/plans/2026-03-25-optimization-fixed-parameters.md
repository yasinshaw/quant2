# Parameter Optimization with Fixed Values Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enable users to fix specific strategy parameters during optimization while optimizing others.

**Architecture:**
- Frontend adds checkbox/fixed-value UI per parameter in OptimizationForm
- Backend API accepts optional `fixed_parameters` field
- Optimizer merges fixed parameters with each combination before backtesting
- Backward compatible: fixed_parameters optional, defaults to current behavior

**Tech Stack:**
- Frontend: React, TypeScript, Tailwind CSS
- Backend: FastAPI, Python, asyncio
- Testing: pytest (backend), Playwright (E2E)

---

## File Structure

### Files to Modify
- `frontend/components/OptimizationForm.tsx` - Add parameter enable/disable UI
- `backend/api/backtest.py` - Add `fixed_parameters` field support
- `backend/core/optimizer.py` - Update optimization algorithm

### Files to Create
- `tests/test_optimizer_fixed_params.py` - Unit tests for optimizer with fixed params
- `tests/test_optimize_api_fixed_params.py` - API integration tests
- `frontend/e2e/optimization-fixed-params.spec.ts` - E2E tests

---

## Task 1: Backend Optimizer - Add Fixed Parameters Support

**Files:**
- Modify: `backend/core/optimizer.py:190-402`
- Test: `tests/test_optimizer_fixed_params.py` (create)

- [ ] **Step 1: Write failing test for fixed parameters**

```python
# tests/test_optimizer_fixed_params.py
import pytest
from backend.core.optimizer import GridSearchOptimizer
from backend.core.backtest_engine import BacktestEngine
from backend.database import Database

@pytest.fixture
def optimizer(db_session):
    db = Database("sqlite:///:memory:")
    engine = BacktestEngine(db)
    return GridSearchOptimizer(engine)

def test_optimize_with_fixed_parameters(optimizer, sample_strategy):
    """Test optimizer merges fixed parameters with combinations"""
    # parameter_ranges: only 'period' varies
    # fixed_parameters: 'threshold' fixed at 0.5
    pass

def test_optimize_all_parameters_fixed(optimizer, sample_strategy):
    """Test edge case: all parameters fixed = single backtest"""
    pass

def test_optimize_no_fixed_parameters(optimizer, sample_strategy):
    """Test backward compatibility: no fixed parameters = current behavior"""
    pass
```

Run: `pytest tests/test_optimizer_fixed_params.py -v`
Expected: FAIL - tests not implemented

- [ ] **Step 2: Implement test helpers**

```python
# tests/test_optimizer_fixed_params.py
from backend.strategies.dummy_strategy import DummyStrategy

@pytest.fixture
def sample_strategy():
    return DummyStrategy

@pytest.fixture
def db_session():
    # Setup in-memory DB with test data
    pass
```

Run: `pytest tests/test_optimizer_fixed_params.py -v`
Expected: FAIL - still missing implementations

- [ ] **Step 3: Implement fixed parameter support in optimizer**

```python
# backend/core/optimizer.py

async def optimize(
    self,
    strategy_class: Type[StrategyBase],
    symbol: str,
    interval: str,
    start_time: str,
    end_time: str,
    parameter_ranges: Dict[str, List[Any]],
    fixed_parameters: Dict[str, Any],  # NEW parameter
    optimization_job_id: int
) -> Dict[str, Any]:
    # Log fixed parameters
    logger.info(
        f"Optimizing {len(parameter_ranges)} parameters "
        f"with {len(fixed_parameters)} fixed values"
    )

    # Generate combinations from optimized parameters only
    combinations = self._generate_combinations(parameter_ranges)

    # Handle edge case: all parameters fixed
    if not combinations:
        logger.info("All parameters fixed, running single backtest")
        combinations = [{}]  # Single empty combination

    # For each combination, merge with fixed parameters
    async def run_with_semaphore(params: Dict[str, Any], index: int):
        async with semaphore:
            # Merge fixed parameters with combination
            final_params = {**fixed_parameters, **params}
            # ... rest of existing logic
```

Run: `pytest tests/test_optimizer_fixed_params.py -v`
Expected: PASS

- [ ] **Step 4: Run all optimizer tests to ensure no regression**

Run: `pytest tests/test_optimizer.py -v`
Expected: All existing tests still PASS

- [ ] **Step 5: Commit backend optimizer changes**

```bash
git add backend/core/optimizer.py tests/test_optimizer_fixed_params.py
git commit -m "feat(optimizer): add fixed parameters support

- Add fixed_parameters parameter to optimize() method
- Merge fixed params with each combination before backtest
- Handle edge case: all params fixed = single backtest
- Add unit tests for fixed parameter behavior

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Task 2: Backend API - Add Fixed Parameters Field

**Files:**
- Modify: `backend/api/backtest.py:191-293`
- Test: `tests/test_optimize_api_fixed_params.py` (create)

- [ ] **Step 1: Write failing API tests**

```python
# tests/test_optimize_api_fixed_params.py
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def test_optimize_with_fixed_parameters():
    """Test API accepts fixed_parameters field"""
    response = client.post("/api/v1/backtest/optimize", json={
        "strategy_name": "DummyStrategy",
        "symbol": "BTCUSDT",
        "interval": "1h",
        "start_time": "2024-01-01T00:00:00",
        "end_time": "2024-01-31T23:59:59",
        "parameter_ranges": {"period": [10, 20]},
        "fixed_parameters": {"threshold": 0.5}
    })
    assert response.status_code == 200

def test_optimize_fixed_parameters_optional():
    """Test backward compatibility: fixed_parameters is optional"""
    response = client.post("/api/v1/backtest/optimize", json={
        "strategy_name": "DummyStrategy",
        "symbol": "BTCUSDT",
        "interval": "1h",
        "start_time": "2024-01-01T00:00:00",
        "end_time": "2024-01-31T23:59:59",
        "parameter_ranges": {"period": [10, 20]}
        # No fixed_parameters
    })
    assert response.status_code == 200

def test_optimize_validate_at_least_one_param():
    """Test validation: need either ranges or fixed params"""
    response = client.post("/api/v1/backtest/optimize", json={
        "strategy_name": "DummyStrategy",
        "symbol": "BTCUSDT",
        "interval": "1h",
        "start_time": "2024-01-01T00:00:00",
        "end_time": "2024-01-31T23:59:59",
        "parameter_ranges": {},
        "fixed_parameters": {}
    })
    assert response.status_code == 400
```

Run: `pytest tests/test_optimize_api_fixed_params.py -v`
Expected: FAIL - API doesn't accept fixed_parameters yet

- [ ] **Step 2: Update API endpoint to accept fixed_parameters**

```python
# backend/api/backtest.py

@router.post("/optimize")
async def optimize_parameters(request: dict) -> Dict[str, Any]:
    # ... existing validation ...

    # Extract fixed_parameters (optional)
    fixed_parameters = request.get("fixed_parameters", {})

    # Validation: at least one parameter (optimized or fixed)
    if not parameter_ranges and not fixed_parameters:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Must specify either parameter_ranges or fixed_parameters"
        )

    # ... existing job creation logic ...

    # Pass fixed_parameters to optimizer
    result = await _optimizer.optimize(
        strategy_class=strategy_class,
        symbol=request["symbol"],
        interval=request["interval"],
        start_time=start_dt.isoformat(),
        end_time=end_dt.isoformat(),
        parameter_ranges=parameter_ranges,
        fixed_parameters=fixed_parameters,  # NEW
        optimization_job_id=job_id
    )
```

Run: `pytest tests/test_optimize_api_fixed_params.py -v`
Expected: PASS

- [ ] **Step 3: Run all API tests for regression**

Run: `pytest tests/test_backtest_api.py -v`
Expected: All existing tests PASS

- [ ] **Step 4: Commit API changes**

```bash
git add backend/api/backtest.py tests/test_optimize_api_fixed_params.py
git commit -m "feat(api): add fixed_parameters to optimization endpoint

- Accept optional fixed_parameters field in /optimize
- Validate at least one parameter (optimized or fixed)
- Pass fixed_parameters through to optimizer
- Add integration tests

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Task 3: Frontend - Add Parameter Enable/Disable UI

**Files:**
- Modify: `frontend/components/OptimizationForm.tsx:1-343`

- [ ] **Step 1: Add state for parameter enablement and fixed values**

```typescript
// frontend/components/OptimizationForm.tsx

// After line 42, add new state:
const [paramEnabled, setParamEnabled] = useState<Record<string, boolean>>({});
const [fixedValues, setFixedValues] = useState<Record<string, number>>({});

// Update useEffect to initialize enabled state
useEffect(() => {
  if (selectedStrategyDetails.data?.parameters) {
    const defaultRanges: Record<string, ParameterRange> = {};
    const defaultEnabled: Record<string, boolean> = {};
    const defaultFixed: Record<string, number> = {};

    Object.entries(selectedStrategyDetails.data.parameters).forEach(([key, param]) => {
      if (param.type === 'int' || param.type === 'float') {
        defaultRanges[key] = {
          min: param.min ?? (param.type === 'int' ? 1 : 0.1),
          max: param.max ?? (param.type === 'int' ? 100 : 10),
          step: param.type === 'int' ? 1 : 0.1,
        };
        defaultEnabled[key] = true;  // All enabled by default
        defaultFixed[key] = param.default ?? 0;  // Store default values
      }
    });

    setParamRanges(defaultRanges);
    setParamEnabled(defaultEnabled);
    setFixedValues(defaultFixed);
  }
}, [selectedStrategyDetails.data]);
```

- [ ] **Step 2: Add toggle and fixed value handlers**

```typescript
// Add after line 85:
const handleToggleParameter = (name: string, enabled: boolean) => {
  setParamEnabled((prev) => ({
    ...prev,
    [name]: enabled,
  }));
};

const handleFixedValueChange = (name: string, value: number) => {
  setFixedValues((prev) => ({
    ...prev,
    [name]: value,
  }));
};
```

- [ ] **Step 3: Update combinations calculation**

```typescript
// Modify calculateTotalCombinations function (line 95):
const calculateTotalCombinations = (): number => {
  return Object.entries(paramRanges)
    .filter(([name]) => paramEnabled[name])  // Only count enabled params
    .reduce((total, [name, range]) => {
      const count = generateParameterValues(range).length;
      return total * (count || 1);
    }, 1);
};

// Add helper for display:
const getOptimizationSummary = () => {
  const totalParams = Object.keys(paramRanges).length;
  const fixedParams = Object.entries(paramEnabled).filter(([_, enabled]) => !enabled).length;
  const optimizedParams = totalParams - fixedParams;
  return `${optimizedParams} parameters total (${fixedParams} fixed)`;
};
```

- [ ] **Step 4: Update parameter card JSX (around line 278)**

```typescript
// In the parameters mapping section:
{Object.entries(paramRanges).map(([name, range]) => (
  <div key={name} className="bg-gray-50 rounded-lg p-4">
    <div className="flex justify-between items-center mb-3">
      <h4 className="text-sm font-semibold text-gray-800">{name}</h4>
      <label className="flex items-center space-x-2 text-sm">
        <input
          type="checkbox"
          checked={paramEnabled[name] ?? true}
          onChange={(e) => handleToggleParameter(name, e.target.checked)}
          className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
        />
        <span className="text-gray-600">Enable</span>
      </label>
    </div>

    {paramEnabled[name] ? (
      // Show range inputs (existing behavior)
      <div className="grid grid-cols-3 gap-4">
        <div>
          <label className="block text-xs text-gray-600 mb-1">Min</label>
          <input
            type="number"
            value={range.min}
            onChange={(e) => handleRangeChange(name, 'min', parseFloat(e.target.value))}
            className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
        <div>
          <label className="block text-xs text-gray-600 mb-1">Max</label>
          <input
            type="number"
            value={range.max}
            onChange={(e) => handleRangeChange(name, 'max', parseFloat(e.target.value))}
            className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
        <div>
          <label className="block text-xs text-gray-600 mb-1">Step</label>
          <input
            type="number"
            step="0.01"
            value={range.step}
            onChange={(e) => handleRangeChange(name, 'step', parseFloat(e.target.value))}
            className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
      </div>
    ) : (
      // Show fixed value input
      <div>
        <label className="block text-xs text-gray-600 mb-1">
          Fixed Value (default: {selectedStrategyDetails.data?.parameters[name]?.default})
        </label>
        <input
          type="number"
          step="0.01"
          value={fixedValues[name] ?? 0}
          onChange={(e) => handleFixedValueChange(name, parseFloat(e.target.value))}
          className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
      </div>
    )}
  </div>
))}
```

- [ ] **Step 5: Update combinations display**

```typescript
// Modify around line 274:
<div className="text-sm text-gray-600">
  Optimized: <span className="font-bold text-blue-600">{totalCombinations}</span> combinations, {getOptimizationSummary()}
</div>
```

- [ ] **Step 6: Update submit payload**

```typescript
// Modify handleSubmit (around line 124):
const parameter_ranges: Record<string, any[]> = {};
const fixed_parameters: Record<string, number> = {};

Object.entries(paramRanges).forEach(([name, range]) => {
  if (paramEnabled[name]) {
    // Include in parameter_ranges if enabled
    parameter_ranges[name] = generateParameterValues(range);
  } else {
    // Include in fixed_parameters if disabled
    fixed_parameters[name] = fixedValues[name];
  }
});

// Update validation: at least one optimized param
if (Object.keys(parameter_ranges).length === 0 && Object.keys(fixed_parameters).length === 0) {
  setError('No parameters available');
  return;
}

// Update onSubmit call
onSubmit({
  strategy_name: strategy,
  symbol,
  interval,
  start_time: start.toISOString(),
  end_time: end.toISOString(),
  parameter_ranges,
  fixed_parameters,  // NEW
  initial_cash: initialCash,
});
```

- [ ] **Step 7: Update TypeScript types**

```typescript
// frontend/lib/api/optimization.ts

export interface OptimizationRequest {
  strategy_name: string;
  symbol: string;
  interval: string;
  start_time: string;
  end_time: string;
  parameter_ranges: Record<string, any[]>;
  fixed_parameters?: Record<string, number>;  // NEW optional field
  initial_cash: number;
}
```

- [ ] **Step 8: Test frontend manually**

```bash
cd frontend
pnpm dev
```

Manual test:
1. Navigate to /optimize
2. Select a strategy with multiple parameters
3. Toggle "Enable" checkbox on/off
4. Verify range inputs hide/fixed value shows
5. Check combinations count updates
6. Submit and verify request payload

- [ ] **Step 9: Commit frontend changes**

```bash
git add frontend/components/OptimizationForm.tsx frontend/lib/api/optimization.ts
git commit -m "feat(frontend): add parameter enable/disable UI

- Add checkbox per parameter to enable/disable optimization
- Show range inputs when enabled, fixed value input when disabled
- Fixed values default to strategy defaults, user can override
- Update combinations display to show fixed parameter count
- Submit separate parameter_ranges and fixed_parameters to API

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Task 4: E2E Tests

**Files:**
- Create: `frontend/e2e/optimization-fixed-params.spec.ts`

- [ ] **Step 1: Write E2E test for parameter toggle**

```typescript
// frontend/e2e/optimization-fixed-params.spec.ts
import { test, expect } from '@playwright/test';

test.describe('Parameter Optimization with Fixed Values', () => {
  test('should show enable checkbox for each parameter', async ({ page }) => {
    await page.goto('/optimize');
    await page.selectOption('[id="strategy"]', 'MultiIndicatorStrategy');

    // Wait for parameters to load
    await expect(page.locator('input[type="checkbox"]').first()).toBeVisible();

    // Check that all numeric parameters have checkboxes
    const checkboxes = await page.locator('input[type="checkbox"]').count();
    expect(checkboxes).toBeGreaterThan(0);
  });

  test('should toggle between range and fixed value inputs', async ({ page }) => {
    await page.goto('/optimize');
    await page.selectOption('[id="strategy"]', 'MultiIndicatorStrategy');

    // Find first parameter checkbox
    const firstCheckbox = page.locator('input[type="checkbox"]').first();

    // Initially checked, should show range inputs
    await expect(firstCheckbox).toBeChecked();
    await expect(page.locator('input[placeholder*="Min"]').first()).toBeVisible();

    // Uncheck to show fixed value input
    await firstCheckbox.uncheck();
    await expect(page.locator('text=Fixed Value').first()).toBeVisible();
  });

  test('should update combinations count when toggling parameters', async ({ page }) => {
    await page.goto('/optimize');
    await page.selectOption('[id="strategy"]', 'MultiIndicatorStrategy');

    // Get initial combinations count
    const initialText = await page.locator('text=combinations').textContent();

    // Disable one parameter
    const firstCheckbox = page.locator('input[type="checkbox"]').first();
    await firstCheckbox.uncheck();

    // Wait for text to update
    await page.waitForTimeout(100);
    const updatedText = await page.locator('text=combinations').textContent();

    // Combinations should decrease
    expect(updatedText).not.toBe(initialText);
  });

  test('should submit with fixed parameters', async ({ page }) => {
    await page.goto('/optimize');
    await page.selectOption('[id="strategy"]', 'MultiIndicatorStrategy');

    // Disable one parameter
    const firstCheckbox = page.locator('input[type="checkbox"]').first();
    await firstCheckbox.uncheck();

    // Fill required fields
    await page.fill('[id="startTime"]', '2024-01-01T00:00');
    await page.fill('[id="endTime"]', '2024-01-31T23:59');

    // Submit (mock the API call)
    // This test requires API mocking or a test backend
  });
});
```

- [ ] **Step 2: Run E2E tests**

```bash
cd frontend
pnpm test:e2e optimization-fixed-params.spec.ts
```

Expected: All tests PASS

- [ ] **Step 3: Commit E2E tests**

```bash
git add frontend/e2e/optimization-fixed-params.spec.ts
git commit -m "test(e2e): add tests for fixed parameters UI

- Test parameter enable/disable checkboxes
- Test range/fixed value input toggle
- Test combinations count updates
- Test form submission with fixed parameters

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Task 5: Documentation and Cleanup

- [ ] **Step 1: Update CLAUDE.md if needed**

Check if project documentation needs updates for the new feature. If no major changes needed, skip this step.

- [ ] **Step 2: Verify all tests pass**

```bash
# Backend tests
pytest tests/ -v

# Frontend E2E
cd frontend && pnpm test:e2e
```

Expected: All tests PASS

- [ ] **Step 3: Final commit for any documentation**

```bash
git add docs/
git commit -m "docs: update documentation for fixed parameters feature"
```

---

## Verification Checklist

Before marking this feature complete:

- [ ] All unit tests pass (`pytest tests/`)
- [ ] All E2E tests pass (`cd frontend && pnpm test:e2e`)
- [ ] Manual testing: Toggle parameters, verify UI updates correctly
- [ ] Manual testing: Submit optimization with fixed params, verify correct behavior
- [ ] Edge case: All parameters fixed runs single backtest
- [ ] Backward compatibility: Existing optimizations still work
- [ ] No console errors in browser
- [ ] No backend errors in logs

---

## Rollback Plan

If issues arise:
1. Revert commits: `git revert HEAD~4..HEAD` (reverses all changes)
2. The revert is atomic and restores previous working state
3. Re-apply fixes in smaller increments if needed
