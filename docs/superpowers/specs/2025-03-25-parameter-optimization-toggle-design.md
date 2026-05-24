# Parameter Optimization Toggle Design

## Overview

Add a toggle mechanism to the parameter optimization interface that allows users to selectively optimize specific parameters while keeping others at fixed values. By default, all parameters should use their strategy default values without optimization.

## Problem Statement

Currently, when users run parameter optimization:
- All numeric strategy parameters are automatically included in the optimization grid
- Users must manually set ranges for parameters they don't want to optimize
- This leads to unnecessarily large parameter spaces and long optimization times
- Users cannot easily run "partial optimizations" (optimizing only some parameters while keeping others fixed)

## Goals

1. **Default behavior**: All parameters should use strategy default values by default
2. **Selective optimization**: Users explicitly opt-in parameters for optimization via toggle switches
3. **Flexible fixed values**: Users can customize fixed parameter values (not participating in optimization)
4. **Clear UI**: Visual distinction between fixed and optimized parameters
5. **Efficient computation**: Only optimize parameters that users have explicitly enabled

## Non-Goals

- Changing the underlying grid search optimization algorithm
- Adding new optimization methods (e.g., Bayesian, genetic)
- Modifying the strategy parameter definition system

## Design

### Architecture

The solution involves changes across three layers:

1. **Frontend UI**: Add toggle switches and conditional input fields
2. **API Contract**: Extend request structure to include fixed parameters
3. **Backend Logic**: Merge fixed parameters with each optimization combination

### Data Model Changes

#### Frontend State

```typescript
interface ParameterConfig {
  optimize: boolean;           // Toggle switch state
  fixedValue?: number;         // User-specified fixed value (when optimize=false)
  range?: {                    // Optimization range (when optimize=true)
    min: number;
    max: number;
    step: number;
  };
  strategyDefaultValue: number; // Strategy's default value for display
}

type ParameterConfigs = Record<string, ParameterConfig>;
```

#### API Request Structure

```typescript
interface OptimizationRequest {
  strategy_name: string;
  symbol: string;
  interval: string;
  start_time: string;
  end_time: string;
  parameter_ranges: Record<string, any[]>;  // Only optimized parameters
  fixed_parameters?: Record<string, any>;   // New field: fixed parameter values
  initial_cash?: number;
}
```

**Example:**
```json
{
  "strategy_name": "DualMovingAverage",
  "symbol": "BTCUSDT",
  "interval": "1h",
  "start_time": "2024-01-01T00:00:00",
  "end_time": "2024-01-31T23:59:59",
  "parameter_ranges": {
    "fast_period": [10, 15, 20]  // Only this parameter is optimized
  },
  "fixed_parameters": {
    "slow_period": 30,           // Fixed at user-specified value
    "stop_loss": 0.05            // Fixed at user-specified value
  }
}
```

### UI Design

#### Component Structure

The `OptimizationForm` component manages the new parameter configuration state:

```typescript
const [parameterConfigs, setParameterConfigs] = useState<ParameterConfigs>({});
```

#### Parameter Item Layout (Compact)

Each parameter renders as a single row:

```
┌──────────────────────────────────────────────────────────────────┐
│ period        [🔘 Optimize]  20  (Strategy default: 20)        │
│               [Fixed value input: _______]                        │
└──────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│ threshold     [🟢 Optimize]                                     │
│               Min: [0.5]  Max: [2.0]  Step: [0.1]               │
└──────────────────────────────────────────────────────────────────┘
```

**Visual States:**

1. **Toggle OFF (Fixed Parameter)**:
   - Gray toggle switch
   - Single input field labeled with parameter name
   - Gray hint text: "(Strategy default: X)"
   - Input shows current value (default or user-modified)

2. **Toggle ON (Optimized Parameter)**:
   - Green/blue toggle switch
   - Three input fields: Min, Max, Step
   - No hint text needed

#### Initialization Logic

When a strategy is selected:

```typescript
useEffect(() => {
  if (selectedStrategyDetails.data?.parameters) {
    const configs: ParameterConfigs = {};

    Object.entries(selectedStrategyDetails.data.parameters).forEach(([key, param]) => {
      if (param.type === 'int' || param.type === 'float') {
        // All parameters default to NOT optimized
        configs[key] = {
          optimize: false,
          fixedValue: param.default,  // Use strategy default
          strategyDefaultValue: param.default,
        };
      }
    });

    setParameterConfigs(configs);
  }
}, [selectedStrategyDetails.data]);
```

#### Combination Count Calculation

Only optimized parameters contribute to the combination count:

```typescript
const totalCombinations = useMemo(() => {
  return Object.values(parameterConfigs)
    .filter(config => config.optimize)  // Only count optimized parameters
    .reduce((total, config) => {
      const count = generateParameterCount(config.range!);
      return total * (count || 1);
    }, 1);
}, [parameterConfigs]);
```

#### Form Submission

Split parameters into two categories:

```typescript
const handleSubmit = async (e: React.FormEvent) => {
  const parameter_ranges: Record<string, any[]> = {};
  const fixed_parameters: Record<string, any> = {};

  Object.entries(parameterConfigs).forEach(([name, config]) => {
    if (config.optimize) {
      // Generate parameter values from range
      parameter_ranges[name] = generateParameterValues(config.range!);
    } else {
      // Use fixed value
      fixed_parameters[name] = config.fixedValue;
    }
  });

  onSubmit({
    strategy_name: strategy,
    symbol,
    interval,
    start_time: start.toISOString(),
    end_time: end.toISOString(),
    parameter_ranges,
    fixed_parameters,  // New field
    initial_cash: initialCash,
  });
};
```

### Backend Changes

#### API Endpoint Update

**File**: `backend/api/backtest.py`

Modify the `optimize_parameters` endpoint to accept `fixed_parameters`:

```python
@router.post("/optimize")
async def optimize_parameters(request: dict) -> Dict[str, Any]:
    # ... existing validation ...

    # Get parameters
    initial_cash = request.get("initial_cash", settings.default_initial_cash)
    parameter_ranges = request["parameter_ranges"]
    fixed_parameters = request.get("fixed_parameters", {})  # NEW

    # ... rest of implementation ...
```

#### Optimizer Logic Update

**File**: `backend/core/optimizer.py`

Update the `optimize()` method to merge fixed parameters:

```python
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
        ...
        fixed_parameters: Parameters to hold at fixed values (not optimized)
    """
    if fixed_parameters is None:
        fixed_parameters = {}

    # ... existing data loading and combination generation ...

    # Update async task to merge fixed parameters
    async def run_with_semaphore(params: Dict[str, Any], index: int):
        # Merge fixed parameters with current combination
        merged_params = {**fixed_parameters, **params}

        backtest_result = await self._run_single_backtest(
            strategy_class=strategy_class,
            symbol=symbol,
            interval=interval,
            start_time=start_time,
            end_time=end_time,
            params=merged_params,  # Use merged parameters
            candles_cache=candles
        )

        return {
            'params': merged_params,  # Store merged params
            'backtest_result': backtest_result,
            'score': backtest_result['pnl_pct']
        }
```

### Database Schema Changes

**No changes required.** The existing schema stores full parameter combinations in `OptimizationResult.parameters`, which will now include both optimized and fixed values.

### Error Handling

#### Frontend Validation

1. **No optimized parameters**: Show error if all toggles are off
   ```typescript
   const hasOptimizedParams = Object.values(parameterConfigs)
     .some(config => config.optimize);

   if (!hasOptimizedParams) {
     setError('Please enable at least one parameter for optimization');
     return;
   }
   ```

2. **Invalid ranges**: Validate min < max, step > 0
3. **Empty parameter ranges**: Show error if optimized parameters result in 0 combinations

#### Backend Validation

1. **Empty parameter_ranges**: Return 400 if no parameters to optimize
2. **Parameter conflicts**: Validate no overlap between `parameter_ranges` and `fixed_parameters`

### Testing Strategy

#### Unit Tests

**Frontend**:
- Test parameter config initialization (all defaults to optimize=false)
- Test toggle state changes
- Test fixed value updates
- Test combination count calculation (only optimized parameters)
- Test form submission splits parameters correctly

**Backend**:
- Test optimizer merges fixed parameters correctly
- Test empty `fixed_parameters` (backward compatibility)
- Test parameter validation

#### Integration Tests

- Test full optimization flow with mixed fixed/optimized parameters
- Test API accepts new `fixed_parameters` field
- Test backward compatibility (old API calls without `fixed_parameters`)

#### E2E Tests

1. User selects strategy → all parameters show as "not optimized" with default values
2. User enables toggle for one parameter → range inputs appear
3. User modifies fixed value for another parameter → value persists
4. User runs optimization → only optimized parameter varies
5. Results show correct parameter combinations

## Migration Plan

### Phase 1: Backend API (Breaking Change Prevention)

1. Add `fixed_parameters` as optional field to `OptimizationRequest`
2. Update `optimizer.optimize()` signature with default `None`
3. Maintain backward compatibility (old API calls work unchanged)

### Phase 2: Frontend Implementation

1. Update `OptimizationForm` component with toggle UI
2. Update TypeScript interfaces
3. Add parameter config state management
4. Update form submission logic

### Phase 3: Testing

1. Add unit tests for new logic
2. Add integration tests for API
3. Add E2E tests for user flows
4. Manual testing with various strategies

## Success Criteria

- [ ] All parameters default to "not optimized" state
- [ ] Users can selectively enable optimization per parameter
- [ ] Users can customize fixed parameter values
- [ ] Combination count only includes optimized parameters
- [ ] Backend correctly merges fixed and optimized parameters
- [ ] Backward compatible with existing API clients
- [ ] No performance regression
- [ ] All tests pass (unit, integration, E2E)

## Alternatives Considered

### Alternative 1: Checkbox-based Selection
Use checkboxes instead of toggle switches.

**Rejected**: Toggle switches better represent binary on/off state for individual parameters.

### Alternative 2: Drag-and-drop Interface
Drag parameters between "Fixed" and "Optimized" columns.

**Rejected**: More complex to implement, harder to make responsive. Toggles are simpler and faster.

### Alternative 3: All Parameters Optimize by Default
Keep current behavior but add ability to disable optimization.

**Rejected**: Goes against user requirement "默认都不需要调优" (default: no optimization needed).

## Open Questions

None.
