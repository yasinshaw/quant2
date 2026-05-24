# Backtest Results Strategy and Parameters Display Design

**Date:** 2026-03-25
**Author:** Claude Code
**Status:** Draft

## Overview

Display the strategy name and parameters used in backtest runs on the backtest results detail page (`/results/[id]`), enabling users to understand the exact configuration that produced each result.

## Problem Statement

Currently, the backtest results detail page only shows performance metrics and trade data. Users cannot see which strategy and parameters were used to generate these results, making it difficult to:
- Reproduce successful backtests
- Compare different parameter configurations
- Understand the context of historical results

## Goals

1. Show the strategy name used for each backtest result
2. Display all parameters with their values
3. Maintain clean UI consistent with existing design
4. Handle edge cases gracefully (missing data, legacy results)

## Design

### Backend Changes

#### API Modification

**Endpoint:** `GET /api/v1/backtest/results/{result_id}/report`

**Current Response:**
```json
{
  "summary": {...},
  "monthly_returns": {...},
  "trade_analysis": {...},
  "equity_curve": [...]
}
```

**Enhanced Response:**
```json
{
  "summary": {...},
  "monthly_returns": {...},
  "trade_analysis": {...},
  "equity_curve": [...],
  "strategy_name": "DualMovingAverage",
  "parameters": {
    "fast_period": 10,
    "slow_period": 20
  }
}
```

#### Implementation

**File:** `backend/api/backtest.py`

In the `get_report()` function:
```python
# After getting result and trades
result = _db.get_backtest_result(result_id)
trades = _db.get_trades(result.backtest_job_id)

# Get job information
job = _db.get_backtest_job(result.backtest_job_id)

# Generate report
report = _report_generator.generate_report(result, trades)

# Add strategy information
report['strategy_name'] = job.strategy_name
report['parameters'] = job.parameters

return report
```

### Frontend Changes

#### Type Definitions

**File:** `frontend/lib/api/backtest.ts`

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
  strategy_name: string;        // NEW
  parameters: Record<string, any>;  // NEW
}
```

#### New Component

**File:** `frontend/components/ConfigurationSection.tsx`

```typescript
'use client';

import React from 'react';

interface ConfigurationSectionProps {
  strategyName: string;
  parameters: Record<string, any>;
}

export default function ConfigurationSection({
  strategyName,
  parameters
}: ConfigurationSectionProps) {
  return (
    <div className="bg-white rounded-lg shadow-md p-6 mb-8">
      <h2 className="text-xl font-bold text-gray-900 mb-4">
        Configuration
      </h2>

      {/* Strategy Name */}
      <div className="mb-4">
        <p className="text-sm text-gray-600 mb-1">Strategy</p>
        <p className="text-lg font-semibold text-blue-600">
          {strategyName}
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

function formatValue(value: any): string {
  if (typeof value === 'object') {
    return JSON.stringify(value);
  }
  return String(value);
}
```

#### Page Integration

**File:** `frontend/app/results/[id]/page.tsx`

Insert the new component after Trade Analysis Summary and before Charts:

```typescript
import ConfigurationSection from '@/components/ConfigurationSection';

// ... inside the component return JSX

{/* Trade Analysis Summary */}
<div className="bg-white rounded-lg shadow-md p-6 mb-8">
  <h2 className="text-xl font-bold text-gray-900 mb-4">Trade Analysis Summary</h2>
  {/* ... existing content ... */}
</div>

{/* NEW: Configuration Section */}
<ConfigurationSection
  strategyName={report.strategy_name}
  parameters={report.parameters}
/>

{/* Charts */}
<div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
  <EquityCurve data={equity_curve} />
  <MonthlyReturns data={monthly_returns} />
</div>
```

### Data Flow

```
User visits /results/[id]
    ↓
Frontend calls: GET /api/v1/backtest/results/{result_id}/report
    ↓
Backend get_report():
  1. Fetch BacktestResult from DB
  2. Fetch BacktestJob via backtest_job_id
  3. Extract strategy_name and parameters from Job
  4. Generate performance report
  5. Merge all data and return
    ↓
Frontend receives BacktestReport (with strategy_name and parameters)
    ↓
ConfigurationSection renders configuration info
```

## Error Handling & Edge Cases

### Backend
- **BacktestJob missing**: Log warning, set `strategy_name` to "Unknown", `parameters` to `{}`
- **Parameters field NULL**: Use empty object `{}`
- Do not fail entire request if strategy data is missing

### Frontend
- **Missing strategy_name**: Display "N/A"
- **Missing parameters**: Display "Default parameters"
- **Complex parameter values** (objects/arrays): Format with `JSON.stringify()`
- Render gracefully even with incomplete data

## Testing Strategy

### Backend Tests
- Unit test: `test_get_report_includes_strategy_info()`
  - Verify response includes `strategy_name` and `parameters`
  - Test with valid BacktestJob
  - Test with missing BacktestJob

### Frontend Tests
- Component test: Verify ConfigurationSection renders correctly
  - With strategy name and parameters
  - With empty parameters
  - With complex parameter values
- E2E test: Verify configuration section appears on results page

## UI/UX Considerations

### Visual Design
- **Strategy Name**: Blue color (`text-blue-600`), font-semibold for emphasis
- **Parameter Cards**: Light gray background (`bg-gray-50`), rounded corners
- **Layout**: Responsive grid - 2 columns on mobile, 3 on desktop
- **Spacing**: Consistent with existing page sections

### Accessibility
- Semantic HTML structure
- Clear labels for strategy and parameters
- Sufficient color contrast

## Success Criteria

- [ ] Strategy name displayed on all backtest result pages
- [ ] All parameters shown with correct values
- [ ] UI consistent with existing design system
- [ ] Handles edge cases gracefully (missing data, legacy results)
- [ ] No performance degradation (same single API call)
- [ ] Tests pass for new functionality

## Implementation Notes

1. **No database migration required** - BacktestJob already has these fields
2. **Breaking changes**: None - API response is extended, not modified
3. **Performance impact**: Minimal - one additional JOIN query
4. **Backward compatibility**: Old reports without job data handled gracefully

## Future Enhancements (Out of Scope)

- Link strategy name to strategy documentation page
- Allow copying parameters to clipboard
- Compare multiple backtests side-by-side
- Export configuration as JSON
