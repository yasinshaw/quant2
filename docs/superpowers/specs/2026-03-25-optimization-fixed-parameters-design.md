# Parameter Optimization with Fixed Values - Design Document

**Date**: 2026-03-25
**Status**: Approved
**Author**: Claude Code

## Overview

Enable users to fix (disable optimization) specific strategy parameters while optimizing others. Users can select which parameters to optimize and which to keep at fixed values during parameter optimization.

## Requirements

### Functional Requirements
1. Users can enable/disable optimization for each strategy parameter individually
2. Fixed parameters use strategy default values by default
3. Users can override fixed values with custom values
4. System displays clear information about optimization scope (total combinations, fixed parameters count)
5. Edge case: All parameters fixed = run single backtest

### Non-Functional Requirements
- Backward compatible with existing optimization API
- No breaking changes to strategy interface
- Clear UI feedback for parameter states

## Architecture

### Frontend Changes

#### Component: `OptimizationForm.tsx`

**State Management**:
```typescript
// New states
const [paramEnabled, setParamEnabled] = useState<Record<string, boolean>>({});
const [fixedValues, setFixedValues] = useState<Record<string, number>>({});
```

**UI Structure**:
- Each parameter has an "Enable Optimization" checkbox
- When enabled: Show min/max/step inputs (existing behavior)
- When disabled: Show single "Fixed Value" input with default value

**Parameter Card Layout**:
```
┌─────────────────────────────────────────┐
│ period              [✓] Enable          │
│                                           │
│ Min: [10]  Max: [30]  Step: [5]          │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│ threshold          [  ] Enable          │
│                                           │
│ Fixed Value: [0.5]  (default: 0.5)      │
└─────────────────────────────────────────┘
```

**Combinations Display**:
```
Optimized: 50 combinations, 3 parameters total (1 fixed)
```

**Submit Payload**:
```typescript
{
  strategy_name: "...",
  symbol: "BTCUSDT",
  interval: "1h",
  start_time: "...",
  end_time: "...",
  parameter_ranges: {
    "period": [10, 20, 30]
  },
  fixed_parameters: {
    "threshold": 0.5
  },
  initial_cash: 100000
}
```

### Backend Changes

#### API Layer: `backend/api/backtest.py`

**Endpoint**: `POST /api/v1/backtest/optimize`

**Request Schema Updates**:
```python
{
    "strategy_name": str,
    "symbol": str,
    "interval": str,
    "start_time": str,  # ISO format
    "end_time": str,    # ISO format
    "parameter_ranges": Dict[str, List[Any]],  # Only enabled params
    "fixed_parameters": Dict[str, Any],        # NEW: Optional, disabled params
    "initial_cash": float  # optional
}
```

**Validation**:
- `fixed_parameters` is optional (defaults to `{}`)
- At least one of `parameter_ranges` or `fixed_parameters` must be non-empty
- Fixed parameter values must match parameter type (int/float)

#### Optimizer: `backend/core/optimizer.py`

**Method Signature**:
```python
async def optimize(
    self,
    strategy_class: Type[StrategyBase],
    symbol: str,
    interval: str,
    start_time: str,
    end_time: str,
    parameter_ranges: Dict[str, List[Any]],
    fixed_parameters: Dict[str, Any],  # NEW
    optimization_job_id: int
) -> Dict[str, Any]
```

**Algorithm Updates**:
```python
# Generate combinations from optimized parameters only
combinations = self._generate_combinations(parameter_ranges)

# Handle edge case: all parameters fixed
if not combinations:
    combinations = [{}]  # Single empty combination

# Merge with fixed parameters for each backtest
for combo in combinations:
    final_params = {**fixed_parameters, **combo}
    # Run backtest with final_params
```

**Logging**:
```python
logger.info(
    f"Optimizing {len(parameter_ranges)} parameters "
    f"with {len(fixed_parameters)} fixed values"
)
```

## Data Flow

```
User selects parameters to optimize
  ↓
Frontend builds two dicts:
  - parameter_ranges: {enabled_param: [values]}
  - fixed_parameters: {disabled_param: value}
  ↓
API receives and validates
  ↓
Optimizer generates combinations from parameter_ranges
  ↓
For each combination:
  - Merge with fixed_parameters
  - Run backtest
  - Save result
  ↓
Return results with all parameters (optimized + fixed)
```

## Edge Cases

| Scenario | Behavior |
|----------|----------|
| All parameters fixed | Generate single empty combination, run one backtest |
| All parameters optimized | Maintain current behavior (backward compatible) |
| Mixed fixed/optimized | Normal execution, log both counts |
| No parameters (empty strategy) | Validation error |

## Backward Compatibility

- `fixed_parameters` field is optional
- If omitted, all parameters in `parameter_ranges` are optimized (current behavior)
- Empty `parameter_ranges` with `fixed_parameters` = single backtest mode
- No changes to strategy `get_parameters()` interface

## Testing Strategy

### Unit Tests
- Test combinations calculation with fixed parameters
- Test parameter merging logic
- Test edge cases (all fixed, all optimized)

### Integration Tests
- Test API endpoint with `fixed_parameters`
- Test database saves with mixed parameters
- Test optimizer execution

### E2E Tests
- Test user toggling parameters on/off
- Test fixed value input and validation
- Test combinations display accuracy

## Implementation Plan

See separate implementation plan document.

## References

- Current optimization implementation: `backend/core/optimizer.py`
- Frontend form: `frontend/components/OptimizationForm.tsx`
- API endpoint: `backend/api/backtest.py::optimize_parameters`
