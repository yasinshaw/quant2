# Parameter Optimization Toggle Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-step. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add toggle switches to optimization form so users can selectively optimize specific parameters while keeping others at fixed values (default: no optimization).

**Architecture:** Frontend UI layer adds toggle switches and conditional input fields; API layer extends request with `fixed_parameters` field; backend optimizer merges fixed parameters into each combination before running backtests.

**Tech Stack:** Next.js 14 (frontend), FastAPI (backend), TypeScript, React Query, pytest

---

## File Structure

**Frontend Changes:**
- `frontend/lib/api/optimization.ts` - Update TypeScript interfaces for `fixed_parameters`
- `frontend/components/OptimizationForm.tsx` - Add toggle UI and parameter config state

**Backend Changes:**
- `backend/api/backtest.py` - Update optimize endpoint to accept `fixed_parameters`
- `backend/core/optimizer.py` - Merge fixed parameters into each combination

**Tests:**
- `tests/test_optimizer.py` - Test fixed parameter merging logic
- `tests/test_backtest_api.py` - Test API accepts fixed_parameters

---

## Task 1: Backend - Add fixed_parameters Support to Optimizer

**Files:**
- Modify: `backend/core/optimizer.py:190-199` (optimize method signature)
- Test: `tests/test_optimizer.py`

- [ ] **Step 1: Write failing test for fixed parameter merging**

```python
# tests/test_optimizer.py
def test_optimizer_merges_fixed_parameters(db, optimizer):
    """Test that fixed parameters are merged into each combination"""
    from backend.strategies.dual_moving_average import DualMovingAverage

    # Create parameter ranges (only fast_period varies)
    parameter_ranges = {
        'fast_period': [10, 20]
    }

    # Fixed parameters (slow_period stays at 30)
    fixed_parameters = {
        'slow_period': 30,
        'stop_loss': 0.05
    }

    # Mock the single backtest to capture parameters
    captured_params = []
    async def mock_backtest(*args, params, **kwargs):
        captured_params.append(params)
        return {
            'final_value': 100000,
            'pnl': 0,
            'pnl_pct': 0,
            'total_trades': 0,
            'win_rate': 0,
            'sharpe_ratio': 0,
            'max_drawdown': 0,
            'trades': []
        }

    optimizer._run_single_backtest = mock_backtest

    # Run optimization
    import asyncio
    asyncio.run(optimizer.optimize(
        strategy_class=DualMovingAverage,
        symbol='BTCUSDT',
        interval='1h',
        start_time='2024-01-01T00:00:00',
        end_time='2024-01-31T23:59:59',
        parameter_ranges=parameter_ranges,
        optimization_job_id=1,
        fixed_parameters=fixed_parameters
    ))

    # Verify fixed parameters are in each combination
    assert len(captured_params) == 2  # fast_period: 10, 20
    for params in captured_params:
        assert params['slow_period'] == 30, "slow_period should be fixed at 30"
        assert params['stop_loss'] == 0.05, "stop_loss should be fixed at 0.05"
        assert params['fast_period'] in [10, 20], "fast_period should vary"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd ~/code/quant2
pytest tests/test_optimizer.py::test_optimizer_merges_fixed_parameters -v
```

Expected: FAIL - `optimize()` doesn't accept `fixed_parameters` argument yet

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
    optimization_job_id: int,
    fixed_parameters: Optional[Dict[str, Any]] = None  # NEW
) -> Dict[str, Any]:
    """
    Execute grid search optimization

    Args:
        strategy_class: Strategy class (must inherit from StrategyBase)
        symbol: Trading pair symbol (e.g., 'BTCUSDT')
        interval: K-line interval (e.g., '1h', '1d')
        start_time: Start time in ISO format
        end_time: End time in ISO format
        parameter_ranges: Parameter ranges dict, e.g., {'period': [10, 20], 'threshold': [0.5, 1.0]}
        optimization_job_id: OptimizationJob ID in database
        fixed_parameters: Parameters to hold at fixed values (not optimized)
    """
    if fixed_parameters is None:
        fixed_parameters = {}

    # ... existing code up to async def run_with_semaphore ...

    async def run_with_semaphore(params: Dict[str, Any], index: int):
        """Run backtest with semaphore to limit concurrency"""
        nonlocal completed_count, last_progress_log

        # Merge fixed parameters with current combination
        merged_params = {**fixed_parameters, **params}

        async with semaphore:
            try:
                backtest_result = await self._run_single_backtest(
                    strategy_class=strategy_class,
                    symbol=symbol,
                    interval=interval,
                    start_time=start_time,
                    end_time=end_time,
                    params=merged_params,  # Use merged parameters
                    candles_cache=candles
                )

                completed_count += 1

                if completed_count - last_progress_log >= progress_log_interval or completed_count == total_combinations:
                    logger.info(
                        f"Progress: {completed_count}/{total_combinations} "
                        f"({completed_count/total_combinations*100:.1f}%) completed"
                    )
                    last_progress_log = completed_count

                return {
                    'params': merged_params,  # Store merged params
                    'backtest_result': backtest_result,
                    'score': backtest_result['pnl_pct']
                }

            except Exception as e:
                logger.error(
                    f"Backtest failed for parameters {params}: {e}",
                    exc_info=True
                )
                return None

    # ... rest of existing code unchanged ...
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/test_optimizer.py::test_optimizer_merges_fixed_parameters -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/core/optimizer.py tests/test_optimizer.py
git commit -m "feat(backend): add fixed_parameters support to optimizer"
```

---

## Task 2: Backend - Update API Endpoint to Accept fixed_parameters

**Files:**
- Modify: `backend/api/backtest.py:193-295` (optimize_parameters function)

- [ ] **Step 1: Write failing test for API endpoint**

```python
# tests/test_backtest_api.py
def test_optimize_endpoint_accepts_fixed_parameters(client, mocker):
    """Test that /api/v1/backtest/optimize accepts fixed_parameters field"""
    # Mock the optimizer
    mock_optimize = mocker.patch('backend.api.backtest._optimizer.optimize')
    mock_optimize.return_value = {
        'job_id': 1,
        'total_combinations': 2,
        'results': [],
        'best_result': {
            'id': 1,
            'job_id': 1,
            'parameters': {'fast_period': 10, 'slow_period': 30},
            'pnl': 1000,
            'pnl_pct': 0.01,
            'total_trades': 5,
            'sharpe_ratio': 1.5,
            'max_drawdown': 0.02,
            'win_rate': 0.6,
            'is_best': True
        }
    }

    response = client.post("/api/v1/backtest/optimize", json={
        "strategy_name": "DualMovingAverage",
        "symbol": "BTCUSDT",
        "interval": "1h",
        "start_time": "2024-01-01T00:00:00",
        "end_time": "2024-01-31T23:59:59",
        "parameter_ranges": {
            "fast_period": [10, 20]
        },
        "fixed_parameters": {
            "slow_period": 30,
            "stop_loss": 0.05
        }
    })

    assert response.status_code == 200

    # Verify optimizer was called with fixed_parameters
    mock_optimize.assert_called_once()
    call_kwargs = mock_optimize.call_args[1]
    assert 'fixed_parameters' in call_kwargs
    assert call_kwargs['fixed_parameters']['slow_period'] == 30
    assert call_kwargs['fixed_parameters']['stop_loss'] == 0.05
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_backtest_api.py::test_optimize_endpoint_accepts_fixed_parameters -v
```

Expected: FAIL - API doesn't extract `fixed_parameters` from request yet

- [ ] **Step 3: Update API endpoint**

```python
# backend/api/backtest.py

@router.post("/optimize")
async def optimize_parameters(request: dict) -> Dict[str, Any]:
    """Run parameter optimization using grid search.

    Args:
        request: Optimization request with:
            - strategy_name: Name of strategy to optimize
            - symbol: Trading pair
            - interval: K-line interval
            - start_time: Start time in ISO format
            - end_time: End time in ISO format
            - parameter_ranges: Dict of parameter names to value lists
            - fixed_parameters: (optional) Dict of parameter names to fixed values
            - initial_cash: Initial cash (optional)
            - optimization_method: Optimization method (optional, default: 'grid')
    """
    # ... existing validation ...

    # Get parameters
    initial_cash = request.get("initial_cash", settings.default_initial_cash)
    parameter_ranges = request["parameter_ranges"]
    fixed_parameters = request.get("fixed_parameters", {})  # NEW

    # ... existing job creation ...

    # Run optimization
    try:
        result = await _optimizer.optimize(
            strategy_class=strategy_class,
            symbol=request["symbol"],
            interval=request["interval"],
            start_time=start_dt.isoformat(),
            end_time=end_dt.isoformat(),
            parameter_ranges=parameter_ranges,
            optimization_job_id=job_id,
            fixed_parameters=fixed_parameters  # NEW
        )
        # ... rest unchanged ...
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/test_backtest_api.py::test_optimize_endpoint_accepts_fixed_parameters -v
```

Expected: PASS

- [ ] **Step 5: Test backward compatibility (old API calls still work)**

```python
# tests/test_backtest_api.py
def test_optimize_endpoint_backward_compatible(client, mocker):
    """Test that API calls without fixed_parameters still work"""
    mock_optimize = mocker.patch('backend.api.backtest._optimizer.optimize')
    mock_optimize.return_value = {'job_id': 1, 'total_combinations': 1, 'results': [], 'best_result': {}}

    # Request WITHOUT fixed_parameters (old format)
    response = client.post("/api/v1/backtest/optimize", json={
        "strategy_name": "DualMovingAverage",
        "symbol": "BTCUSDT",
        "interval": "1h",
        "start_time": "2024-01-01T00:00:00",
        "end_time": "2024-01-31T23:59:59",
        "parameter_ranges": {"fast_period": [10, 20]}
    })

    assert response.status_code == 200
    mock_optimize.assert_called_once()
    call_kwargs = mock_optimize.call_args[1]
    assert call_kwargs['fixed_parameters'] == {}  # Should default to empty dict
```

```bash
pytest tests/test_backtest_api.py::test_optimize_endpoint_backward_compatible -v
```

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add backend/api/backtest.py tests/test_backtest_api.py
git commit -m "feat(api): add fixed_parameters to optimize endpoint"
```

---

## Task 3: Frontend - Update TypeScript Interfaces

**Files:**
- Modify: `frontend/lib/api/optimization.ts`

- [ ] **Step 1: Update TypeScript interface**

```typescript
// frontend/lib/api/optimization.ts

export interface OptimizationRequest {
  strategy_name: string;
  symbol: string;
  interval: string;
  start_time: string;
  end_time: string;
  parameter_ranges: Record<string, any[]>;
  fixed_parameters?: Record<string, any>;  // NEW
  initial_cash?: number;
}
```

- [ ] **Step 2: Run TypeScript type check**

```bash
cd ~/code/quant2/frontend
pnpm tsc --noEmit
```

Expected: No type errors

- [ ] **Step 3: Commit**

```bash
git add frontend/lib/api/optimization.ts
git commit -m "feat(frontend): add fixed_parameters to OptimizationRequest interface"
```

---

## Task 4: Frontend - Add Parameter Config State Type

**Files:**
- Modify: `frontend/components/OptimizationForm.tsx`

- [ ] **Step 1: Add ParameterConfig interface and state**

```typescript
// frontend/components/OptimizationForm.tsx

// Add after line 13
interface ParameterConfig {
  optimize: boolean;
  fixedValue?: number;
  range?: {
    min: number;
    max: number;
    step: number;
  };
  strategyDefaultValue: number;
}

// Replace useState for paramRanges with parameterConfigs
// Remove old interface and state (lines 9-13, 42)
const [parameterConfigs, setParameterConfigs] = useState<Record<string, ParameterConfig>>({});
```

- [ ] **Step 2: Update useEffect to initialize with optimize=false**

```typescript
// Replace existing useEffect (lines 61-75)
useEffect(() => {
  if (selectedStrategyDetails.data?.parameters) {
    const configs: Record<string, ParameterConfig> = {};
    Object.entries(selectedStrategyDetails.data.parameters).forEach(([key, param]) => {
      if (param.type === 'int' || param.type === 'float') {
        // Default: ALL parameters are NOT optimized
        configs[key] = {
          optimize: false,
          fixedValue: param.default ?? (param.type === 'int' ? 1 : 0.1),
          strategyDefaultValue: param.default ?? (param.type === 'int' ? 1 : 0.1),
        };
      }
    });
    setParameterConfigs(configs);
  }
}, [selectedStrategyDetails.data]);
```

- [ ] **Step 3: Run TypeScript type check**

```bash
cd frontend && pnpm tsc --noEmit
```

Expected: Type errors (existing code still uses old paramRanges)

- [ ] **Step 4: Commit (incomplete, will finish in next task)**

No commit yet - state changed but UI not updated

---

## Task 5: Frontend - Add Toggle UI Components

**Files:**
- Modify: `frontend/components/OptimizationForm.tsx` (ParameterRanges section, lines 281-327)

- [ ] **Step 1: Create Toggle Switch component**

```typescript
// Add at top of file after imports
function ToggleSwitch({ checked, onChange, label }: { checked: boolean; onChange: (checked: boolean) => void; label: string }) {
  return (
    <button
      type="button"
      onClick={() => onChange(!checked)}
      className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 ${
        checked ? 'bg-blue-600' : 'bg-gray-200'
      }`}
      aria-pressed={checked}
      aria-label={label}
    >
      <span
        className={`inline-block h-4 w-4 transform rounded-full bg-white transition duration-200 ease-in-out ${
          checked ? 'translate-x-6' : 'translate-x-1'
        }`}
      />
    </button>
  );
}
```

- [ ] **Step 2: Update parameter rendering with toggle UI**

Replace the parameter ranges section (lines 281-327):

```typescript
{Object.keys(parameterConfigs).length > 0 && (
  <div className="border-t pt-6">
    <div className="flex justify-between items-center mb-4">
      <h3 className="text-lg font-semibold text-gray-900">Parameters</h3>
      <div className="text-sm text-gray-600">
        Combinations: <span className="font-bold text-blue-600">{totalCombinations}</span>
      </div>
    </div>
    <div className="space-y-4">
      {Object.entries(parameterConfigs).map(([name, config]) => (
        <div key={name} className="bg-gray-50 rounded-lg p-4">
          <div className="flex items-center justify-between mb-3">
            <h4 className="text-sm font-semibold text-gray-800">{name}</h4>
            <ToggleSwitch
              checked={config.optimize}
              onChange={(checked) => {
                setParameterConfigs((prev) => ({
                  ...prev,
                  [name]: {
                    ...prev[name],
                    optimize: checked,
                    // Initialize range if enabling optimization
                    range: checked ? {
                      min: prev[name].strategyDefaultValue * 0.5,
                      max: prev[name].strategyDefaultValue * 2,
                      step: typeof prev[name].strategyDefaultValue === 'number' &&
                            Number.isInteger(prev[name].strategyDefaultValue) ? 1 : 0.1
                    } : undefined
                  }
                }));
              }}
              label={`Toggle optimization for ${name}`}
            />
          </div>

          {config.optimize ? (
            // Optimized: Show Min/Max/Step inputs
            <div className="grid grid-cols-3 gap-4">
              <div>
                <label className="block text-xs text-gray-600 mb-1">Min</label>
                <input
                  type="number"
                  value={config.range?.min ?? ''}
                  onChange={(e) => {
                    const value = parseFloat(e.target.value);
                    if (!isNaN(value)) {
                      setParameterConfigs((prev) => ({
                        ...prev,
                        [name]: {
                          ...prev[name],
                          range: { ...prev[name].range!, min: value }
                        }
                      }));
                    }
                  }}
                  className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div>
                <label className="block text-xs text-gray-600 mb-1">Max</label>
                <input
                  type="number"
                  value={config.range?.max ?? ''}
                  onChange={(e) => {
                    const value = parseFloat(e.target.value);
                    if (!isNaN(value)) {
                      setParameterConfigs((prev) => ({
                        ...prev,
                        [name]: {
                          ...prev[name],
                          range: { ...prev[name].range!, max: value }
                        }
                      }));
                    }
                  }}
                  className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div>
                <label className="block text-xs text-gray-600 mb-1">Step</label>
                <input
                  type="number"
                  step="0.01"
                  value={config.range?.step ?? ''}
                  onChange={(e) => {
                    const value = parseFloat(e.target.value);
                    if (!isNaN(value)) {
                      setParameterConfigs((prev) => ({
                        ...prev,
                        [name]: {
                          ...prev[name],
                          range: { ...prev[name].range!, step: value }
                        }
                      }));
                    }
                  }}
                  className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>
          ) : (
            // Fixed: Show single value input with hint
            <div>
              <input
                type="number"
                value={config.fixedValue ?? ''}
                onChange={(e) => {
                  const value = parseFloat(e.target.value);
                  if (!isNaN(value)) {
                    setParameterConfigs((prev) => ({
                      ...prev,
                      [name]: {
                        ...prev[name],
                        fixedValue: value
                      }
                    }));
                  }
                }}
                className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              <p className="text-xs text-gray-500 mt-1">
                Strategy default: {config.strategyDefaultValue}
              </p>
            </div>
          )}
        </div>
      ))}
    </div>
  </div>
)}
```

- [ ] **Step 3: Run TypeScript check**

```bash
cd frontend && pnpm tsc --noEmit
```

Expected: No errors

- [ ] **Step 4: Commit**

```bash
git add frontend/components/OptimizationForm.tsx
git commit -m "feat(frontend): add toggle switches to parameter optimization form"
```

---

## Task 6: Frontend - Update Combination Count Logic

**Files:**
- Modify: `frontend/components/OptimizationForm.tsx` (totalCombinations calculation, lines 105-110)

- [ ] **Step 1: Update totalCombinations to only count optimized parameters**

Replace the useMemo (lines 105-110):

```typescript
const totalCombinations = useMemo(() => {
  return Object.values(parameterConfigs)
    .filter(config => config.optimize)  // Only count optimized parameters
    .reduce((total, config) => {
      if (!config.range) return total;
      const count = generateParameterCount(config.range);
      return total * (count || 1);
    }, 1);
}, [parameterConfigs]);
```

- [ ] **Step 2: Run TypeScript check**

```bash
cd frontend && pnpm tsc --noEmit
```

Expected: No errors

- [ ] **Step 3: Commit**

```bash
git add frontend/components/OptimizationForm.tsx
git commit -m "fix(frontend): calculate combinations only for optimized parameters"
```

---

## Task 7: Frontend - Update Form Submission

**Files:**
- Modify: `frontend/components/OptimizationForm.tsx` (handleSubmit function, lines 112-153)

- [ ] **Step 1: Update handleSubmit to split parameters**

Replace the handleSubmit function (lines 112-153):

```typescript
const handleSubmit = async (e: React.FormEvent) => {
  e.preventDefault();
  setError('');

  if (!startTime || !endTime) {
    setError('Please select both start and end dates');
    return;
  }

  const start = new Date(startTime);
  const end = new Date(endTime);

  if (start >= end) {
    setError('Start date must be before end date');
    return;
  }

  // Check if at least one parameter is optimized
  const hasOptimizedParams = Object.values(parameterConfigs).some(config => config.optimize);
  if (!hasOptimizedParams) {
    setError('Please enable at least one parameter for optimization');
    return;
  }

  // Split into parameter_ranges and fixed_parameters
  const parameter_ranges: Record<string, any[]> = {};
  const fixed_parameters: Record<string, any> = {};

  Object.entries(parameterConfigs).forEach(([name, config]) => {
    if (config.optimize) {
      // Generate parameter values from range
      if (!config.range) return;
      const values: number[] = [];
      for (let v = config.range.min; v <= config.range.max; v += config.range.step) {
        values.push(Number(v.toFixed(2)));
      }
      parameter_ranges[name] = values;
    } else {
      // Use fixed value
      if (config.fixedValue !== undefined) {
        fixed_parameters[name] = config.fixedValue;
      }
    }
  });

  if (totalCombinations > 1000) {
    setError(`Too many combinations (${totalCombinations}). Please reduce parameter ranges.`);
    return;
  }

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
};
```

- [ ] **Step 2: Run TypeScript check**

```bash
cd frontend && pnpm tsc --noEmit
```

Expected: No errors

- [ ] **Step 3: Commit**

```bash
git add frontend/components/OptimizationForm.tsx
git commit -m "feat(frontend): split parameters into optimized and fixed in form submission"
```

---

## Task 8: Frontend - Remove Unused Functions

**Files:**
- Modify: `frontend/components/OptimizationForm.tsx`

- [ ] **Step 1: Remove handleRangeChange function (lines 77-87)**

This function is no longer needed with the new parameter config structure.

- [ ] **Step 2: Remove generateParameterValues function (lines 89-95)**

Replace with inline logic in handleSubmit.

- [ ] **Step 3: Remove generateParameterCount function (lines 98-102)**

Move this logic directly into the useMemo for totalCombinations.

- [ ] **Step 4: Update totalCombinations useMemo with inline count logic**

```typescript
const totalCombinations = useMemo(() => {
  return Object.values(parameterConfigs)
    .filter(config => config.optimize)
    .reduce((total, config) => {
      if (!config.range || config.range.step <= 0) return total;
      const count = Math.floor((config.range.max - config.range.min) / config.range.step) + 1;
      return total * Math.max(0, count);
    }, 1);
}, [parameterConfigs]);
```

- [ ] **Step 5: Run TypeScript check**

```bash
cd frontend && pnpm tsc --noEmit
```

Expected: No errors

- [ ] **Step 6: Commit**

```bash
git add frontend/components/OptimizationForm.tsx
git commit -m "refactor(frontend): remove unused helper functions"
```

---

## Task 9: E2E Test - Verify Toggle Functionality

**Files:**
- Create: `frontend/e2e/optimize-toggle.spec.ts`

- [ ] **Step 1: Write E2E test**

```typescript
// frontend/e2e/optimize-toggle.spec.ts
import { test, expect } from '@playwright/test';

test.describe('Parameter Optimization Toggle', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('http://localhost:3000/optimize');
  });

  test('all parameters default to not optimized', async ({ page }) => {
    // Select a strategy
    await page.selectOption('select#strategy', 'DualMovingAverage');

    // Wait for parameters to load
    await page.waitForSelector('[data-testid="parameter-config"]');

    // Check all toggles are OFF (unchecked)
    const toggles = await page.locator('button[aria-pressed="false"]').count();
    expect(toggles).toBeGreaterThan(0);

    // Verify all show fixed value inputs
    const fixedInputs = await page.locator('input[type="number"]').count();
    expect(fixedInputs).toBeGreaterThan(0);
  });

  test('can enable optimization for a parameter', async ({ page }) => {
    await page.selectOption('select#strategy', 'DualMovingAverage');
    await page.waitForSelector('[data-testid="parameter-config"]');

    // Find the first parameter toggle
    const firstToggle = page.locator('button[aria-pressed="false"]').first();

    // Click to enable optimization
    await firstToggle.click();

    // Verify toggle is now ON
    await expect(firstToggle).toHaveAttribute('aria-pressed', 'true');

    // Verify Min/Max/Step inputs appear
    await expect(page.locator('input[placeholder*="Min"]')).toBeVisible();
  });

  test('combination count only includes optimized parameters', async ({ page }) => {
    await page.selectOption('select#strategy', 'DualMovingAverage');
    await page.waitForSelector('[data-testid="parameter-config"]');

    // Get initial combination count (should be 1 with no optimized params)
    const countBefore = await page.textContent('text=/Combinations:\\s*\\d+/');

    // Enable optimization for one parameter with 3 values
    await page.locator('button[aria-pressed="false"]').first().click();
    await page.fill('input[placeholder*="Min"]', '10');
    await page.fill('input[placeholder*="Max"]', '20');
    await page.fill('input[placeholder*="Step"]', '5');

    // Count should now be 3 (10, 15, 20)
    const countAfter = await page.textContent('text=/Combinations:\\s*\\d+/');
    expect(countAfter).toContain('3');
  });

  test('cannot submit without enabling at least one parameter', async ({ page }) => {
    await page.selectOption('select#strategy', 'DualMovingAverage');
    await page.waitForSelector('[data-testid="parameter-config"]');

    // Fill required form fields but don't enable any optimization
    await page.fill('input#startTime', '2024-01-01T00:00');
    await page.fill('input#endTime', '2024-01-31T23:59');

    // Try to submit
    await page.click('button[type="submit"]');

    // Should show error message
    await expect(page.locator('text=/enable at least one parameter/')).toBeVisible();
  });
});
```

- [ ] **Step 2: Run E2E test**

```bash
cd ~/code/quant2/frontend
pnpm dev &  # Start dev server in background
sleep 5
pnpm test:e2e optimize-toggle.spec.ts
```

Expected: Tests pass (UI elements present and interactive)

- [ ] **Step 3: Add data-testid attributes to OptimizationForm**

Update parameter config divs to include test IDs:

```typescript
<div key={name} className="bg-gray-50 rounded-lg p-4" data-testid="parameter-config">
```

- [ ] **Step 4: Run E2E test again**

```bash
cd frontend && pnpm test:e2e optimize-toggle.spec.ts
```

Expected: All tests pass

- [ ] **Step 5: Commit**

```bash
git add frontend/e2e/optimize-toggle.spec.ts frontend/components/OptimizationForm.tsx
git commit -m "test(e2e): add toggle functionality tests"
```

---

## Task 10: Manual Testing & Documentation

**Files:**
- Update: `README.md` or docs (if needed)

- [ ] **Step 1: Manual testing checklist**

```bash
# Start backend
cd ~/code/quant2/backend
python main.py

# Start frontend (new terminal)
cd ~/code/quant2/frontend
pnpm dev
```

Manual test steps:
1. Navigate to http://localhost:3000/optimize
2. Select "DualMovingAverage" strategy
3. Verify all parameters show toggle switches in OFF position
4. Verify each shows "Strategy default: X" hint
5. Click toggle for one parameter → Min/Max/Step inputs appear
6. Modify fixed value for another parameter
7. Verify combination count updates correctly
8. Submit optimization
9. Check backend logs show fixed parameters merged correctly

- [ ] **Step 2: Update documentation if needed**

Check if README or docs need updates for this feature.

- [ ] **Step 3: Final integration test**

```bash
cd ~/code/quant2
pytest tests/ -v
cd frontend && pnpm test:e2e
```

Expected: All tests pass

- [ ] **Step 4: Create summary commit**

```bash
git add .
git commit -m "feat: complete parameter optimization toggle feature

- Backend optimizer accepts and merges fixed_parameters
- API endpoint updated with backward compatibility
- Frontend UI with toggle switches for each parameter
- All parameters default to NOT optimized
- Users can customize fixed parameter values
- Combination count only includes optimized parameters
- E2E tests verify toggle functionality"
```

---

## Success Criteria Verification

After completing all tasks:

- [ ] All parameters default to "not optimized" state
- [ ] Users can selectively enable optimization per parameter
- [ ] Users can customize fixed parameter values
- [ ] Combination count only includes optimized parameters
- [ ] Backend correctly merges fixed and optimized parameters
- [ ] Backward compatible with existing API clients
- [ ] No performance regression
- [ ] All tests pass (unit, integration, E2E)

---

## Notes for Implementation

- **TypeScript strict mode**: All new code must pass `pnpm tsc --noEmit`
- **Testing strategy**: Unit tests first (TDD), then integration, then E2E
- **Backward compatibility**: API accepts requests without `fixed_parameters` field
- **UI consistency**: Toggle switch uses existing Tailwind classes
- **Performance**: Only optimized parameters contribute to grid search
