# Parameter Optimization Improvement Design

**Date:** 2026-03-25
**Status:** Draft
**Author:** Claude (with user input)

## Overview

Comprehensive improvement of the parameter optimization system, introducing Bayesian optimization, composite scoring functions, and overfitting prevention mechanisms to address the limitations of the current grid search approach.

## Background and Motivation

### Current Limitations

The current `GridSearchOptimizer` has several limitations:

1. **Computational Inefficiency** - Exhaustive search explodes with parameter dimensionality
2. **Single Metric Optimization** - Only optimizes `pnl_pct`, ignoring risk-adjusted returns
3. **No Overfitting Detection** - Cannot validate parameter robustness on unseen data
4. **No Stability Analysis** - Cannot detect isolated peaks vs parameter plateaus

### User Requirements

The user explicitly requested three key improvements:

A. **Efficient Optimization Algorithms** - Bayesian optimization using Optuna
B. **Composite Scoring Function** - Multi-metric weighted combination (Sharpe, return, drawdown, win rate)
C. **Overfitting Prevention** - Out-of-sample testing + parameter stability analysis

## Design Goals

1. **Efficiency** - Reduce backtest count while finding better parameters
2. **Robustness** - Detect and warn about overfitting
3. **Flexibility** - Support both grid and Bayesian optimization
4. **Compatibility** - Maintain backward compatibility with existing code
5. **Usability** - Simple API with sensible defaults

## Architecture

### Component Structure

```
backend/core/
├── optimizer.py                   # Existing: GridSearchOptimizer (preserved)
├── bayesian_optimizer.py          # New: BayesianOptimizer using Optuna
├── scoring_functions.py           # New: Composite score calculation
├── stability_analyzer.py          # New: Parameter stability analysis
└── backtest_engine.py             # Existing: Reused for backtest execution
```

### Data Flow

```
User Request
    ↓
API selects optimizer based on optimization_method
    ├─ 'grid' → GridSearchOptimizer
    └─ 'bayesian' → BayesianOptimizer (NEW)
    ↓
Optimizer runs backtests with composite scoring (NEW)
    ↓
Out-of-sample validation (if enabled, NEW)
    ↓
Parameter stability analysis (if enabled, NEW)
    ↓
Return: best_params + stability_report + oos_results
```

### Design Decision: Parallel Architecture

**Decision:** Keep GridSearchOptimizer, add BayesianOptimizer as an alternative

**Rationale:**
- Backward compatibility - existing code continues to work
- User choice - can compare methods side-by-side
- Minimal refactoring - add instead of replace
- Progressive enhancement - users adopt new features gradually

## Core Components

### 1. BayesianOptimizer

**Purpose:** Efficient optimization using Bayesian methods with Optuna

**Key Features:**
- Suggests next parameters based on previous results
- Balances exploration (unknown regions) vs exploitation (promising regions)
- Handles both continuous and discrete parameters
- Supports parallel execution

**Interface:**
```python
class BayesianOptimizer:
    async def optimize(
        strategy_class,
        symbol,
        interval,
        start_time,
        end_time,
        parameter_ranges: Dict[str, Any],  # [min, max] or [v1, v2, ...]
        n_trials: int = 100,
        scoring_weights: Dict[str, float],
        optimization_job_id: int
    ) -> Dict[str, Any]
```

**Implementation Notes:**
- Reuses existing data caching mechanism from GridSearchOptimizer
- Parallel trial execution with semaphore (similar to current implementation)
- Returns best params + complete trial history for visualization

### 2. Scoring Functions

**Purpose:** Calculate composite score from multiple metrics

**Default Weights:**
```python
DEFAULT_WEIGHTS = {
    'sharpe_ratio': 0.4,
    'total_return': 0.3,
    'max_drawdown': -0.2,  # Negative: smaller is better
    'win_rate': 0.1
}
```

**Score Calculation:**
```python
score = Σ(normalized_metric × weight)

# Normalization examples:
- Sharpe: min(0, max(sharpe / 3.0, 1.0))  # 3.0 = excellent
- Return: min(0, max(return / 1.0, 1.0))  # 100% = excellent
- Drawdown: max(0, 1 - drawdown / 0.5)    # 50% = severe
- Win Rate: min(0, max(win_rate, 1.0))    # Direct
```

**User Customization:**
- Optional via API parameter `scoring_weights`
- Falls back to defaults if not provided

### 3. Stability Analyzer

**Purpose:** Detect "parameter plateaus" vs isolated peaks

**Method:**
1. Sample parameters in ±10% neighborhood of best params
2. Run backtests for perturbed parameters
3. Calculate variance of scores
4. Stability score = `max(0, 1 - variance)`

**Stability Threshold:**
- `variance < 0.1` → Stable (parameter plateau)
- `variance >= 0.1` → Unstable (isolated peak, warning)

**Output:**
```python
{
    'stability_score': 0.85,      # 0-1, higher = more stable
    'variance': 0.05,
    'std': 0.22,
    'mean_score': 0.72,
    'is_stable': True,
    'neighbor_results': [...]      # Sample of neighbor results
}
```

### 4. Out-of-Sample Testing

**Purpose:** Validate parameter generalization on unseen data

**Configuration:**
```python
{
    'enable_out_of_sample': True,
    'test_start_time': '2024-06-01',
    'test_end_time': '2024-12-31'
}
```

**Process:**
1. Optimize on training data (start_time → end_time)
2. Run single backtest on test data with best params
3. Compare in-sample vs out-of-sample performance

**Overfitting Detection:**
```python
is_overfitted = (oos_return < in_sample_return * 0.5)
```

**Output:**
```python
{
    'test_period': {'start': ..., 'end': ...},
    'result': {...},  # Backtest result
    'is_overfitted': False,
    'performance_degradation': 5.2  # Percentage points
}
```

## Data Model Changes

### OptimizationJob Extensions

```python
class OptimizationJob(BaseModel):
    # Existing fields...
    strategy_name = Column(String, nullable=False)
    # ... (other existing fields)

    # NEW: Scoring configuration
    scoring_weights = Column(JSON)

    # NEW: Overfitting prevention
    test_start_time = Column(DateTime)
    test_end_time = Column(DateTime)
    enable_out_of_sample = Column(Boolean, default=False)
    enable_stability_analysis = Column(Boolean, default=True)

    # NEW: Stability analysis results
    stability_score = Column(Float)
    stability_variance = Column(Float)
    is_stable = Column(Boolean)
```

### OptimizationResult Extensions

```python
class OptimizationResult(BaseModel):
    # Existing fields...

    # NEW: Composite score
    composite_score = Column(Float)

    # NEW: Out-of-sample flag
    is_out_of_sample = Column(Boolean, default=False)

    # NEW: Stability neighbor data
    stability_neighbors = Column(JSON)
```

## API Interface

### POST /api/v1/backtest/optimize

**Request Extensions:**
```python
{
    # Existing fields
    "strategy_name": "DualMovingAverage",
    "symbol": "BTCUSDT",
    "interval": "1h",
    "start_time": "2024-01-01T00:00:00",
    "end_time": "2024-06-30T23:59:59",
    "parameter_ranges": {...},

    # NEW: Optimization method
    "optimization_method": "bayesian",  # 'grid' | 'bayesian'
    "n_trials": 100,  # For Bayesian only

    # NEW: Scoring configuration
    "scoring_weights": {  # Optional, uses defaults if null
        "sharpe_ratio": 0.4,
        "total_return": 0.3,
        "max_drawdown": -0.2,
        "win_rate": 0.1
    },

    # NEW: Overfitting prevention
    "enable_out_of_sample": False,
    "test_start_time": "2024-07-01T00:00:00",  # Required if oos enabled
    "test_end_time": "2024-12-31T23:59:59",
    "enable_stability_analysis": True
}
```

**Response Extensions:**
```python
{
    # Existing fields
    "job_id": 123,
    "total_combinations": 100,
    "best_result": {...},
    "results": [...],

    # NEW: Composite score in results
    "best_result": {
        "composite_score": 0.75,  # NEW
        # ... other metrics
    },

    # NEW: Stability analysis (if enabled)
    "stability": {
        "stability_score": 0.85,
        "is_stable": True,
        "variance": 0.05,
        "neighbor_results": [...]
    },

    # NEW: Out-of-sample test (if enabled)
    "out_of_sample": {
        "result": {...},
        "is_overfitted": False,
        "performance_degradation": 5.2
    }
}
```

### GET /api/v1/backtest/optimization/jobs/{job_id}/stability

**Purpose:** Retrieve stability analysis report separately

**Response:**
```python
{
    "stability_score": 0.85,
    "variance": 0.05,
    "is_stable": True,
    "neighbor_results": [...]
}
```

### GET /api/v1/backtest/optimization/scoring-weights/default

**Purpose:** Get default scoring weights for UI pre-population

**Response:** `DEFAULT_WEIGHTS` dict

## Frontend Changes

### OptimizationForm Component

**New Fields:**
1. Optimization method selector (radio: Grid / Bayesian)
2. Trial count input (shown only for Bayesian)
3. Scoring weights config (collapsible "Advanced Options")
4. Out-of-sample test toggle + date pickers
5. Stability analysis toggle (default: enabled)

**UI Layout:**
```
Basic Configuration
├─ Strategy, Symbol, Interval
├─ Time Range (Start / End)
└─ Parameter Ranges

Optimization Method
├─ ◉ Grid Search (exhaustive)
└─ ○ Bayesian Optimization (efficient)
    └─ Trials: [100] (input)

Scoring (Advanced ▼)
├─ Sharpe Ratio:     [0.4]  slider/input
├─ Total Return:     [0.3]  slider/input
├─ Max Drawdown:    [-0.2]  slider/input
└─ Win Rate:         [0.1]  slider/input
    └─ [Reset to Defaults] button

Overfitting Prevention
├─ ☐ Enable Out-of-Sample Test
│   ├─ Test Start: [date picker]
│   └─ Test End:   [date picker]
└─ ☑ Enable Stability Analysis

[Run Optimization] button
```

### OptimizationResults Component

**New Sections:**
1. Composite score display (prominent)
2. Stability analysis card
   - Stability score gauge (0-1)
   - Stable/Unstable badge
   - Variance display
   - Neighbor performance chart
3. Out-of-sample test card (if enabled)
   - OOS performance metrics
   - Overfitting warning banner
   - In-sample vs OOS comparison chart

## Dependencies

```python
# backend/requirements.txt additions
optuna>=3.5.0       # Bayesian optimization
numpy>=1.24.0       # Statistical calculations for stability
```

**Installation Check:**
- API validates Optuna availability on startup
- Returns clear error message if not installed
- Provides installation instructions in error response

## Error Handling

### Boundary Cases

1. **Insufficient Data for OOS Test**
   - Error: "No candles found for test period"
   - Action: Return 400 error before starting optimization

2. **Invalid Parameter Ranges**
   - Error: "Parameter range invalid: min >= max"
   - Action: Validate on API input, return 400

3. **Too Few Trials**
   - Warning: "n_trials < 10 may not converge"
   - Action: Allow but warn in logs

4. **Weights Don't Sum to 1**
   - Warning: "Weights sum to X, normalizing to 1.0"
   - Action: Normalize weights, log warning

## Testing Strategy

### Unit Tests

1. **test_bayesian_optimizer.py**
   - Test Optuna study creation
   - Test parameter suggestion logic
   - Test trial execution
   - Mock backtest execution

2. **test_scoring_functions.py**
   - Test composite score calculation
   - Test normalization for each metric
   - Test custom weights override
   - Test edge cases (zero division, missing metrics)

3. **test_stability_analyzer.py**
   - Test neighbor sampling
   - Test variance calculation
   - Test stability threshold logic
   - Mock backtest results

### Integration Tests

1. **test_optimization_api.py**
   - Test Bayesian optimization request
   - Test scoring weights parameter
   - Test out-of-sample test flow
   - Test stability analysis integration
   - Test error cases (invalid input, missing data)

### E2E Tests

1. **Optimization form submission**
   - Select Bayesian method
   - Configure scoring weights
   - Enable OOS test
   - Submit and wait for results

2. **Results display**
   - Verify stability card shown
   - Verify OOS results shown
   - Verify composite score displayed

## Implementation Phases

### Phase 1: Core Bayesian Optimization (Priority 1)
- [ ] Install Optuna dependency
- [ ] Implement `BayesianOptimizer` class
- [ ] Add `scoring_functions.py` module
- [ ] API: Add `optimization_method` and `n_trials` parameters
- [ ] Unit tests for Bayesian optimizer
- [ ] Integration test for API endpoint

### Phase 2: Scoring and API Integration (Priority 1)
- [ ] Implement composite score calculation
- [ ] Add `scoring_weights` parameter to API
- [ ] Update `OptimizationResult` model with `composite_score`
- [ ] Frontend: Add method selector and trial count
- [ ] Frontend: Add scoring weights config (collapsible)
- [ ] E2E test for Bayesian optimization flow

### Phase 3: Overfitting Prevention (Priority 2)
- [ ] Implement `StabilityAnalyzer` class
- [ ] Implement out-of-sample test function
- [ ] Database: Add new fields to `OptimizationJob`
- [ ] API: Add OOS test parameters
- [ ] API: Return stability and OOS results
- [ ] Frontend: Add OOS test controls
- [ ] Frontend: Display stability and OOS cards
- [ ] Unit and integration tests

### Phase 4: Polish and Validation (Priority 3)
- [ ] Add Optuna installation check
- [ ] Comprehensive error handling
- [ ] Performance optimization (caching, parallel execution)
- [ ] Documentation updates
- [ ] E2E test coverage

## Success Criteria

1. **Efficiency** - Bayesian optimization finds comparable/better parameters in <50% of grid search time
2. **Accuracy** - Composite scoring selects parameters with better risk-adjusted returns
3. **Robustness** - OOS test catches obvious overfitting cases
4. **Usability** - Frontend UI is intuitive with sensible defaults
5. **Compatibility** - Existing grid search code continues to work unchanged

## Open Questions

1. **Optuna Parallelization** - Should we use Optuna's built-in parallelization or stick with our semaphore approach?
   - **Recommendation:** Keep semaphore for consistency with existing code

2. **Stability Threshold** - Is variance < 0.1 the right threshold for "stable"?
   - **Recommendation:** Make configurable, start with 0.1 as default

3. **OOS Test Default** - Should out-of-sample testing be enabled by default?
   - **Recommendation:** No, opt-in to avoid confusion about data requirements

## References

- Optuna Documentation: https://optuna.readthedocs.io/
- Bayesian Optimization in Quant Trading: User-provided references
- Walk-Forward Analysis: User-provided methodology
