# Monte Carlo Simulation for Strategy Robustness

## Summary

Add a Monte Carlo trade-shuffle simulation to the backtest results page, allowing users to assess strategy robustness by analyzing the distribution of outcomes when trade order is randomized.

## Problem

A backtest produces a single equity curve based on the actual trade sequence. This single path may be lucky or unlucky. Users need to understand: "If I got the same trades but in a different order, would the strategy still survive?"

## Solution

Implement a Monte Carlo simulation that shuffles trade PnL order N times (default 1000) and recomputes equity curves, returns, and drawdowns for each permutation. Present the distribution of outcomes with confidence intervals.

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Computation | Backend API | Supports 10K+ simulations, results can be cached later |
| Trigger | Button on results page | On-demand, no wasted computation |
| Method | Trade order shuffle (not bootstrap) | Preserves trade count, most common approach |
| Default simulations | 1000 | Good balance of speed and accuracy |
| Persistence | Not stored | Computed on-demand each time |

## Backend

### Core Module: `backend/core/monte_carlo.py`

```python
@dataclass
class MonteCarloResult:
    equity_curves: list[list[float]]   # Sampled curves (50 points each)
    final_returns: list[float]         # Per-simulation return
    max_drawdowns: list[float]         # Per-simulation max drawdown
    median_return: float
    p5_return: float
    p95_return: float
    median_max_drawdown: float
    p95_max_drawdown: float
    ruin_probability: float            # Equity drops below 50% of initial
    original_return: float
    original_max_drawdown: float

class MonteCarloSimulator:
    def simulate(
        trades_pnl: list[float],
        initial_cash: float,
        original_return: float,
        original_max_drawdown: float,
        num_simulations: int = 1000,
    ) -> MonteCarloResult
```

Implementation notes:
- Use `numpy.random.shuffle(pnl.copy())` for each permutation
- Vectorized cumulative sum via numpy
- Max drawdown computed per curve using vectorized approach
- Equity curves downsampled to `min(num_trades, 100)` points using `numpy.linspace` for evenly-spaced index sampling; each curve independently downsampled
- 1000 simulations should complete in < 1 second

Data units (all values are decimal ratios, matching existing `BacktestResult` convention):
- Returns: 0.18 = 18%
- Drawdowns: 0.12 = 12%
- Ruin probability: 0.02 = 2%

### API Endpoint

`POST /api/v1/backtest/jobs/{job_id}/monte-carlo`

**Request** (Pydantic model with automatic validation):
```python
class MonteCarloRequest(BaseModel):
    num_simulations: int = Field(default=1000, ge=100, le=10000)
```

**Handler data flow:**
1. Fetch job via `_db.get_backtest_job(job_id)`, validate `status == 'completed'`
2. Fetch result via `_db.get_backtest_result_by_job_id(job_id)` — provides `initial_cash`, `total_return`, `max_drawdown`
3. Fetch trades via `_db.get_trades(job_id)` — extract `pnl` list
4. Filter out trades where `pnl is None` (incomplete trade data), log warning if any filtered
5. Validate remaining trade count >= 10
6. Call `MonteCarloSimulator.simulate()`
7. Return result (not persisted)

**Response** (all monetary values are decimal ratios: 0.18 = 18%):
```json
{
  "num_simulations": 1000,
  "equity_curves": [[...], ...],
  "final_returns": [...],
  "max_drawdowns": [...],
  "median_return": 0.18,
  "p5_return": -0.05,
  "p95_return": 0.42,
  "median_max_drawdown": 0.12,
  "p95_max_drawdown": 0.25,
  "ruin_probability": 0.02,
  "original_return": 0.22,
  "original_max_drawdown": 0.086
}
```

Validation:
- `num_simulations` must be in [100, 10000] (Pydantic enforced)
- Job must exist and have completed results
- Trade count (after filtering None pnl) must be >= 10
- Returns 400 with descriptive error if validation fails

## Frontend

### API Layer: `frontend/lib/api/backtest.ts`

New interfaces and API method (snake_case, matching existing project convention):
```typescript
interface MonteCarloResult {
  num_simulations: number
  equity_curves: number[][]
  final_returns: number[]
  max_drawdowns: number[]
  median_return: number
  p5_return: number
  p95_return: number
  median_max_drawdown: number
  p95_max_drawdown: number
  ruin_probability: number
  original_return: number
  original_max_drawdown: number
}

// New API method
monteCarloApi.run(jobId: string, numSimulations: number): Promise<MonteCarloResult>
```

### Component: `frontend/components/MonteCarloSimulation.tsx`

Collapsible panel with:

1. **Controls** — Simulation count slider (100–10000, step 100, default 1000) + Run button
2. **Stats row** — 4 metric cards:
   - Median Return (P50)
   - 95th Percentile Drawdown (worst case)
   - Ruin Probability (equity < 50%)
   - Original vs Median comparison
3. **Chart row** — 2 charts side by side:
   - **Equity curve fan chart** (Recharts LineChart): P5/P25/P50/P75/P95 percentile lines + original curve highlighted
   - **Return distribution histogram** (Recharts BarChart): return bins with original position marker and P5/P95 boundaries

Uses React Query for data fetching with loading/error states. Run button disabled during request (via `isLoading`).

### Page Integration: `frontend/app/results/[id]/page.tsx`

Insert MonteCarloSimulation component between CandlestickChart and TradeTable. Panel starts collapsed; user clicks button to expand and run.

## Scope

**In scope:**
- Backend simulator with numpy vectorization
- Single API endpoint
- Frontend component with fan chart and histogram
- Integration into existing results page

**Out of scope (future extensions):**
- Bootstrap resampling mode
- Saving/persisting simulation results
- Monte Carlo for optimization results
- Confidence level configuration
- Export simulation data
