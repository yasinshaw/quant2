# Monte Carlo Simulation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Monte Carlo trade-shuffle simulation to backtest results page for strategy robustness analysis.

**Architecture:** Backend numpy-based simulator shuffles trade PnL order N times, computes equity curves and drawdowns. New POST endpoint returns distribution statistics. Frontend component with fan chart and histogram, triggered by button on results page.

**Tech Stack:** Python/numpy (backend), Recharts (frontend charts), React Query (data fetching), Pydantic (request validation)

**Spec:** `docs/superpowers/specs/2026-04-12-monte-carlo-simulation-design.md`

---

## File Map

| Action | File | Responsibility |
|--------|------|---------------|
| Create | `backend/core/monte_carlo.py` | MonteCarloSimulator class with numpy vectorization |
| Create | `tests/test_monte_carlo.py` | Unit tests for simulator |
| Modify | `backend/api/backtest.py` | Add POST `/jobs/{job_id}/monte-carlo` endpoint |
| Modify | `frontend/lib/api/backtest.ts` | Add MonteCarloResult interface + API method |
| Create | `frontend/components/MonteCarloSimulation.tsx` | Collapsible panel with stats + charts |
| Modify | `frontend/app/results/[id]/page.tsx` | Insert component between CandlestickChart and TradeTable |

---

### Task 1: Backend Simulator Core

**Files:**
- Create: `backend/core/monte_carlo.py`
- Create: `tests/test_monte_carlo.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_monte_carlo.py
import pytest
import numpy as np
from backend.core.monte_carlo import MonteCarloSimulator, MonteCarloResult


class TestMonteCarloSimulator:
    def test_simulate_returns_result_with_correct_fields(self):
        pnl = [100, -50, 200, -30, 80, -20, 150, -60, 90, -10]
        result = MonteCarloSimulator.simulate(
            trades_pnl=pnl,
            initial_cash=100000,
            original_return=0.45,
            original_max_drawdown=0.05,
            num_simulations=100,
        )
        assert isinstance(result, MonteCarloResult)
        assert result.num_simulations == 100
        assert len(result.final_returns) == 100
        assert len(result.max_drawdowns) == 100
        assert len(result.equity_curves) == 100
        assert result.original_return == 0.45
        assert result.original_max_drawdown == 0.05

    def test_simulate_preserves_total_pnl(self):
        """Each simulation should have the same total PnL as original."""
        pnl = [100, -50, 200, -30, 80]
        total_pnl = sum(pnl)
        initial_cash = 100000
        result = MonteCarloSimulator.simulate(
            trades_pnl=pnl,
            initial_cash=initial_cash,
            original_return=0.3,
            original_max_drawdown=0.05,
            num_simulations=50,
        )
        # All final returns should equal the same total PnL / initial_cash
        expected_return = total_pnl / initial_cash
        for ret in result.final_returns:
            assert abs(ret - expected_return) < 1e-10

    def test_simulate_max_drawdowns_are_positive(self):
        pnl = [100, -200, 300, -50, 80, -30, 200, -100, 50, -20]
        result = MonteCarloSimulator.simulate(
            trades_pnl=pnl,
            initial_cash=100000,
            original_return=0.33,
            original_max_drawdown=0.2,
            num_simulations=100,
        )
        for dd in result.max_drawdowns:
            assert dd >= 0

    def test_simulate_statistics_in_range(self):
        pnl = [100, -50, 200, -30, 80, -20, 150, -60, 90, -10]
        result = MonteCarloSimulator.simulate(
            trades_pnl=pnl,
            initial_cash=100000,
            original_return=0.45,
            original_max_drawdown=0.05,
            num_simulations=1000,
        )
        assert 0 <= result.ruin_probability <= 1
        assert result.p5_return <= result.median_return <= result.p95_return
        assert result.median_max_drawdown <= result.p95_max_drawdown

    def test_simulate_equity_curves_sampled_length(self):
        pnl = [100, -50, 200, -30, 80, -20, 150, -60, 90, -10]
        result = MonteCarloSimulator.simulate(
            trades_pnl=pnl,
            initial_cash=100000,
            original_return=0.45,
            original_max_drawdown=0.05,
            num_simulations=10,
        )
        expected_len = min(len(pnl), 100)
        for curve in result.equity_curves:
            assert len(curve) == expected_len

    def test_simulate_ruin_probability_with_large_losses(self):
        """When a single loss can wipe 50%+, some shuffles should cause ruin."""
        pnl = [-60000, 100, 100, 100, 100]  # One massive loss
        result = MonteCarloSimulator.simulate(
            trades_pnl=pnl,
            initial_cash=100000,
            original_return=-0.596,
            original_max_drawdown=0.6,
            num_simulations=1000,
        )
        assert result.ruin_probability > 0  # Some shuffles hit -60000 early

    def test_simulate_requires_minimum_trades(self):
        with pytest.raises(ValueError, match="at least 2 trades"):
            MonteCarloSimulator.simulate(
                trades_pnl=[100],
                initial_cash=100000,
                original_return=0.001,
                original_max_drawdown=0.0,
                num_simulations=100,
            )
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/yasin/code/quant2 && python -m pytest tests/test_monte_carlo.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'backend.core.monte_carlo'`

- [ ] **Step 3: Implement MonteCarloSimulator**

```python
# backend/core/monte_carlo.py
"""Monte Carlo simulation for strategy robustness analysis.

Shuffles trade PnL order N times to assess the distribution of outcomes
when trade execution order is randomized.
"""
import numpy as np
from dataclasses import dataclass
from typing import List
import logging

logger = logging.getLogger(__name__)


@dataclass
class MonteCarloResult:
    """Result of Monte Carlo simulation."""
    num_simulations: int
    equity_curves: List[List[float]]     # Downsampled curves
    final_returns: List[float]           # Per-simulation final return (decimal ratio)
    max_drawdowns: List[float]           # Per-simulation max drawdown (decimal ratio)
    median_return: float                 # P50 of returns
    p5_return: float                     # 5th percentile return
    p95_return: float                    # 95th percentile return
    median_max_drawdown: float           # P50 of max drawdowns
    p95_max_drawdown: float              # P95 of max drawdowns (worst case)
    ruin_probability: float              # Fraction of sims where equity < 50% of initial
    original_return: float               # Original backtest return
    original_max_drawdown: float         # Original backtest max drawdown


class MonteCarloSimulator:
    """Runs Monte Carlo simulation by shuffling trade order."""

    RUIN_THRESHOLD = 0.5  # Equity drops below 50% of initial

    @staticmethod
    def simulate(
        trades_pnl: List[float],
        initial_cash: float,
        original_return: float,
        original_max_drawdown: float,
        num_simulations: int = 1000,
    ) -> MonteCarloResult:
        """Run Monte Carlo trade-shuffle simulation.

        Args:
            trades_pnl: List of trade PnL values (absolute).
            initial_cash: Starting portfolio value.
            original_return: Original backtest return (decimal ratio, e.g. 0.22 = 22%).
            original_max_drawdown: Original backtest max drawdown (decimal ratio).
            num_simulations: Number of random permutations to run.

        Returns:
            MonteCarloResult with distribution statistics.

        Raises:
            ValueError: If fewer than 2 trades provided.
        """
        if len(trades_pnl) < 2:
            raise ValueError("Monte Carlo simulation requires at least 2 trades")

        pnl_array = np.array(trades_pnl, dtype=np.float64)
        n_trades = len(pnl_array)

        # Pre-allocate results
        all_curves = np.zeros((num_simulations, n_trades + 1))
        all_curves[:, 0] = initial_cash

        for i in range(num_simulations):
            shuffled = pnl_array.copy()
            np.random.shuffle(shuffled)
            cumulative_pnl = np.cumsum(shuffled)
            all_curves[i, 1:] = initial_cash + cumulative_pnl

        # Compute final returns (decimal ratio)
        final_values = all_curves[:, -1]
        final_returns = (final_values - initial_cash) / initial_cash

        # Compute max drawdown per simulation (vectorized)
        max_drawdowns = np.zeros(num_simulations)
        for i in range(num_simulations):
            curve = all_curves[i]
            peak = np.maximum.accumulate(curve)
            drawdowns = (peak - curve) / peak
            max_drawdowns[i] = np.max(drawdowns)

        # Ruin probability: equity drops below threshold
        min_equity = np.min(all_curves, axis=1)
        ruin_mask = min_equity < (initial_cash * MonteCarloSimulator.RUIN_THRESHOLD)
        ruin_probability = float(np.mean(ruin_mask))

        # Downsample equity curves to min(n_trades, 100) points
        sample_count = min(n_trades, 100)
        sample_indices = np.linspace(0, n_trades, sample_count, dtype=int)
        # Ensure index 0 is included
        if sample_indices[0] != 0:
            sample_indices[0] = 0

        equity_curves = []
        for i in range(num_simulations):
            equity_curves.append(all_curves[i, sample_indices].tolist())

        return MonteCarloResult(
            num_simulations=num_simulations,
            equity_curves=equity_curves,
            final_returns=final_returns.tolist(),
            max_drawdowns=max_drawdowns.tolist(),
            median_return=float(np.median(final_returns)),
            p5_return=float(np.percentile(final_returns, 5)),
            p95_return=float(np.percentile(final_returns, 95)),
            median_max_drawdown=float(np.median(max_drawdowns)),
            p95_max_drawdown=float(np.percentile(max_drawdowns, 95)),
            ruin_probability=ruin_probability,
            original_return=original_return,
            original_max_drawdown=original_max_drawdown,
        )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/yasin/code/quant2 && python -m pytest tests/test_monte_carlo.py -v`
Expected: All 7 tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/core/monte_carlo.py tests/test_monte_carlo.py
git commit -m "feat: add Monte Carlo trade-shuffle simulator with tests"
```

---

### Task 2: API Endpoint

**Files:**
- Modify: `backend/api/backtest.py` — add import at line ~16 and new endpoint after `get_report_by_job` (~line 628)

- [ ] **Step 1: Add import**

Add after line 17 (`from backend.core.stability_analyzer import StabilityAnalyzer`):
```python
from backend.core.monte_carlo import MonteCarloSimulator
```

- [ ] **Step 2: Add endpoint after `get_report_by_job` (after line 628)**

```python
@router.post("/jobs/{job_id}/monte-carlo")
async def run_monte_carlo(job_id: int, request: dict) -> Dict[str, Any]:
    """
    Run Monte Carlo simulation for a backtest job.

    Shuffles trade order N times to assess strategy robustness.

    Args:
        job_id: BacktestJob ID
        request: { num_simulations: int (100-10000, default 1000) }

    Returns:
        MonteCarloResult with distribution statistics.
    """
    num_simulations = request.get("num_simulations", 1000)
    if not isinstance(num_simulations, int) or num_simulations < 100 or num_simulations > 10000:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="num_simulations must be an integer between 100 and 10000"
        )

    # Fetch job
    job = _db.get_backtest_job(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found"
        )

    if job.status != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Job {job_id} is not completed (status: {job.status})"
        )

    # Fetch result
    result = _db.get_backtest_result_by_job_id(job_id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No result found for job {job_id}"
        )

    # Fetch trades and extract PnL
    trades = _db.get_trades(job_id)
    pnl_list = [t.pnl for t in trades if hasattr(t, 'pnl') and t.pnl is not None]

    if len(pnl_list) < 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Insufficient trades for Monte Carlo simulation: {len(pnl_list)} (minimum 10)"
        )

    if len(pnl_list) < len(trades):
        logger.warning(
            f"Filtered {len(trades) - len(pnl_list)} trades with None pnl for job {job_id}"
        )

    # Run simulation
    mc_result = MonteCarloSimulator.simulate(
        trades_pnl=pnl_list,
        initial_cash=float(result.initial_cash),
        original_return=float(result.total_return),
        original_max_drawdown=float(result.max_drawdown),
        num_simulations=num_simulations,
    )

    logger.info(
        f"Monte Carlo simulation completed for job {job_id}: "
        f"{num_simulations} simulations, median_return={mc_result.median_return:.4f}, "
        f"p95_dd={mc_result.p95_max_drawdown:.4f}, ruin_prob={mc_result.ruin_probability:.4f}"
    )

    return {
        "num_simulations": mc_result.num_simulations,
        "equity_curves": mc_result.equity_curves,
        "final_returns": mc_result.final_returns,
        "max_drawdowns": mc_result.max_drawdowns,
        "median_return": mc_result.median_return,
        "p5_return": mc_result.p5_return,
        "p95_return": mc_result.p95_return,
        "median_max_drawdown": mc_result.median_max_drawdown,
        "p95_max_drawdown": mc_result.p95_max_drawdown,
        "ruin_probability": mc_result.ruin_probability,
        "original_return": mc_result.original_return,
        "original_max_drawdown": mc_result.original_max_drawdown,
    }
```

- [ ] **Step 3: Restart backend and test endpoint manually**

Run: `curl -X POST http://localhost:8000/api/v1/backtest/jobs/220/monte-carlo -H "Content-Type: application/json" -d '{"num_simulations": 100}'`

Expected: JSON response with `median_return`, `equity_curves`, etc.

- [ ] **Step 4: Commit**

```bash
git add backend/api/backtest.py
git commit -m "feat: add POST /jobs/{job_id}/monte-carlo API endpoint"
```

---

### Task 3: Frontend API Layer

**Files:**
- Modify: `frontend/lib/api/backtest.ts` — add interface and API method

- [ ] **Step 1: Add interface after `BacktestReport` (after line 97)**

```typescript
export interface MonteCarloResult {
  num_simulations: number;
  equity_curves: number[][];
  final_returns: number[];
  max_drawdowns: number[];
  median_return: number;
  p5_return: number;
  p95_return: number;
  median_max_drawdown: number;
  p95_max_drawdown: number;
  ruin_probability: number;
  original_return: number;
  original_max_drawdown: number;
}
```

- [ ] **Step 2: Add API method inside `backtestApi` object (before closing `}`)**

```typescript
  runMonteCarlo: async (jobId: number, numSimulations: number = 1000): Promise<MonteCarloResult> => {
    const response = await api.post<MonteCarloResult>(
      `/api/v1/backtest/jobs/${jobId}/monte-carlo`,
      { num_simulations: numSimulations }
    );
    return response.data;
  },
```

- [ ] **Step 3: Verify TypeScript compiles**

Run: `cd /Users/yasin/code/quant2/frontend && npx tsc --noEmit`
Expected: No errors related to new types

- [ ] **Step 4: Commit**

```bash
git add frontend/lib/api/backtest.ts
git commit -m "feat: add MonteCarloResult interface and API method"
```

---

### Task 4: Frontend Monte Carlo Component

**Files:**
- Create: `frontend/components/MonteCarloSimulation.tsx`

- [ ] **Step 1: Create component**

```tsx
'use client';

import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import {
  LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer,
  CartesianGrid, BarChart, Bar, Cell, ReferenceLine,
} from 'recharts';
import { backtestApi, MonteCarloResult } from '@/lib/api/backtest';

interface Props {
  jobId: number;
  initialCash: number;
}

function computePercentileCurves(equityCurves: number[][], percentiles: number[]) {
  if (!equityCurves.length) return {};
  const numPoints = equityCurves[0].length;
  const result: Record<string, number[]> = {};

  for (const p of percentiles) {
    const key = `p${p}`;
    result[key] = [];
    for (let i = 0; i < numPoints; i++) {
      const values = equityCurves.map(c => c[i]).sort((a, b) => a - b);
      const idx = Math.floor(values.length * p / 100);
      result[key].push(values[Math.min(idx, values.length - 1)]);
    }
  }

  return result;
}

function buildHistogramData(returns: number[], originalReturn: number) {
  if (!returns.length) return [];
  const min = Math.min(...returns);
  const max = Math.max(...returns);
  const binCount = 30;
  const binWidth = (max - min) / binCount || 1;

  const bins = Array.from({ length: binCount }, (_, i) => ({
    range: (min + i * binWidth + binWidth / 2),
    count: 0,
    isOriginal: false,
  }));

  for (const r of returns) {
    const idx = Math.min(Math.floor((r - min) / binWidth), binCount - 1);
    bins[idx].count++;
  }

  // Mark the bin closest to original return
  let closestIdx = 0;
  let closestDist = Infinity;
  bins.forEach((b, i) => {
    const dist = Math.abs(b.range - originalReturn);
    if (dist < closestDist) {
      closestDist = dist;
      closestIdx = i;
    }
  });
  bins[closestIdx].isOriginal = true;

  return bins;
}

export default function MonteCarloSimulation({ jobId, initialCash }: Props) {
  const [numSimulations, setNumSimulations] = useState(1000);
  const [result, setResult] = useState<MonteCarloResult | null>(null);

  const mutation = useMutation({
    mutationFn: () => backtestApi.runMonteCarlo(jobId, numSimulations),
    onSuccess: (data) => setResult(data),
  });

  const handleRun = () => {
    setResult(null);
    mutation.mutate();
  };

  const pctFormat = (v: number) => `${(v * 100).toFixed(1)}%`;
  const moneyFormat = (v: number) => `$${(v / 1000).toFixed(0)}K`;

  return (
    <div className="bg-white dark:bg-slate-800 rounded-xl shadow-md border border-slate-200 dark:border-slate-700">
      {/* Header + Controls */}
      <div className="p-6 border-b border-slate-200 dark:border-slate-700">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-heading font-bold text-slate-900 dark:text-slate-100">
            Monte Carlo Simulation
          </h3>
          <div className="flex items-center gap-4">
            <label className="flex items-center gap-2 text-sm text-slate-600 dark:text-slate-400">
              <span>Simulations:</span>
              <input
                type="range"
                min={100}
                max={10000}
                step={100}
                value={numSimulations}
                onChange={(e) => setNumSimulations(Number(e.target.value))}
                className="w-32"
              />
              <span className="font-mono text-slate-900 dark:text-slate-100 w-16 text-right">
                {numSimulations.toLocaleString()}
              </span>
            </label>
            <button
              onClick={handleRun}
              disabled={mutation.isPending}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-slate-400 text-white text-sm font-semibold rounded-lg transition-colors"
            >
              {mutation.isPending ? 'Running...' : 'Run Simulation'}
            </button>
          </div>
        </div>
      </div>

      {/* Error */}
      {mutation.isError && (
        <div className="p-4 mx-6 mt-4 bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-400 rounded-lg text-sm">
          Failed to run simulation. Please try again.
        </div>
      )}

      {/* Loading */}
      {mutation.isPending && (
        <div className="p-12 text-center text-slate-500 dark:text-slate-400">
          Running {numSimulations.toLocaleString()} simulations...
        </div>
      )}

      {/* Results */}
      {result && (
        <div className="p-6 space-y-6">
          {/* Stats Cards */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            <StatCard
              label="Median Return"
              value={pctFormat(result.median_return)}
              sub={`P5: ${pctFormat(result.p5_return)} / P95: ${pctFormat(result.p95_return)}`}
            />
            <StatCard
              label="95th Pctl Drawdown"
              value={pctFormat(result.p95_max_drawdown)}
              sub={`Median: ${pctFormat(result.median_max_drawdown)}`}
              valueColor={result.p95_max_drawdown > 0.25 ? 'text-red-600 dark:text-red-400' : undefined}
            />
            <StatCard
              label="Ruin Probability"
              value={pctFormat(result.ruin_probability)}
              sub={`Equity < ${moneyFormat(initialCash * 0.5)}`}
              valueColor={result.ruin_probability > 0.05 ? 'text-red-600 dark:text-red-400' : 'text-green-600 dark:text-green-400'}
            />
            <StatCard
              label="Original vs Median"
              value={pctFormat(result.original_return)}
              sub={`Median: ${pctFormat(result.median_return)}`}
              valueColor={result.original_return >= result.median_return ? 'text-green-600 dark:text-green-400' : 'text-amber-600 dark:text-amber-400'}
            />
          </div>

          {/* Charts */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Fan Chart */}
            <div>
              <h4 className="text-sm font-semibold text-slate-700 dark:text-slate-300 mb-2">
                Equity Curve Distribution
              </h4>
              <FanChart result={result} initialCash={initialCash} />
            </div>

            {/* Histogram */}
            <div>
              <h4 className="text-sm font-semibold text-slate-700 dark:text-slate-300 mb-2">
                Return Distribution
              </h4>
              <ReturnHistogram result={result} />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function StatCard({ label, value, sub, valueColor }: {
  label: string; value: string; sub: string; valueColor?: string;
}) {
  return (
    <div className="bg-slate-50 dark:bg-slate-700/50 rounded-lg p-4">
      <p className="text-xs text-slate-500 dark:text-slate-400 uppercase tracking-wider">{label}</p>
      <p className={`text-xl font-bold mt-1 ${valueColor ?? 'text-slate-900 dark:text-slate-100'}`}>{value}</p>
      <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">{sub}</p>
    </div>
  );
}

function FanChart({ result, initialCash }: { result: MonteCarloResult; initialCash: number }) {
  const percentiles = computePercentileCurves(result.equity_curves, [5, 25, 50, 75, 95]);
  const numPoints = result.equity_curves[0]?.length ?? 0;
  const data = Array.from({ length: numPoints }, (_, i) => ({
    index: i + 1,
    p5: percentiles.p5?.[i],
    p25: percentiles.p25?.[i],
    p50: percentiles.p50?.[i],
    p75: percentiles.p75?.[i],
    p95: percentiles.p95?.[i],
  }));

  const allValues = data.flatMap(d => [d.p5, d.p95].filter((v): v is number => v !== undefined));
  const minVal = Math.min(...allValues);
  const maxVal = Math.max(...allValues);
  const domain = [Math.floor(minVal * 0.95), Math.ceil(maxVal * 1.05)];

  return (
    <ResponsiveContainer width="100%" height={280}>
      <LineChart data={data}>
        <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" className="dark:stroke-slate-700" />
        <XAxis dataKey="index" tick={{ fontSize: 11, fill: '#475569' }} stroke="#94a3b8" />
        <YAxis domain={domain} tick={{ fontSize: 11, fill: '#475569' }} stroke="#94a3b8"
          tickFormatter={(v: number) => `$${(v / 1000).toFixed(0)}K`} />
        <Tooltip formatter={(v: number) => `$${v.toLocaleString(undefined, { maximumFractionDigits: 0 })}`} />
        <Line type="monotone" dataKey="p5" stroke="#93c5fd" strokeWidth={1} dot={false} name="P5" />
        <Line type="monotone" dataKey="p25" stroke="#60a5fa" strokeWidth={1} dot={false} name="P25" />
        <Line type="monotone" dataKey="p50" stroke="#3b82f6" strokeWidth={2} dot={false} name="P50 (Median)" />
        <Line type="monotone" dataKey="p75" stroke="#60a5fa" strokeWidth={1} dot={false} name="P75" />
        <Line type="monotone" dataKey="p95" stroke="#93c5fd" strokeWidth={1} dot={false} name="P95" />
      </LineChart>
    </ResponsiveContainer>
  );
}

function ReturnHistogram({ result }: { result: MonteCarloResult }) {
  const bins = buildHistogramData(result.final_returns, result.original_return);

  return (
    <ResponsiveContainer width="100%" height={280}>
      <BarChart data={bins}>
        <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" className="dark:stroke-slate-700" />
        <XAxis dataKey="range" tick={{ fontSize: 10, fill: '#475569' }} stroke="#94a3b8"
          tickFormatter={(v: number) => `${(v * 100).toFixed(0)}%`} />
        <YAxis tick={{ fontSize: 11, fill: '#475569' }} stroke="#94a3b8" />
        <Tooltip formatter={(v: number) => v} labelFormatter={(l: number) => `Return: ${(l * 100).toFixed(1)}%`} />
        <Bar dataKey="count">
          {bins.map((entry, idx) => (
            <Cell
              key={idx}
              fill={entry.isOriginal ? '#f59e0b' : entry.range >= 0 ? '#3b82f6' : '#ef4444'}
              opacity={entry.isOriginal ? 1 : 0.6}
            />
          ))}
        </Bar>
        <ReferenceLine x={result.original_return} stroke="#f59e0b" strokeWidth={2} label="Original" />
      </BarChart>
    </ResponsiveContainer>
  );
}
```

- [ ] **Step 2: Verify TypeScript compiles**

Run: `cd /Users/yasin/code/quant2/frontend && npx tsc --noEmit`
Expected: No errors

- [ ] **Step 3: Commit**

```bash
git add frontend/components/MonteCarloSimulation.tsx
git commit -m "feat: add MonteCarloSimulation component with fan chart and histogram"
```

---

### Task 5: Integrate into Results Page

**Files:**
- Modify: `frontend/app/results/[id]/page.tsx` — add import and insert component

- [ ] **Step 1: Add import**

Add after the existing imports at the top of the file:
```typescript
import MonteCarloSimulation from '@/components/MonteCarloSimulation';
```

- [ ] **Step 2: Insert component**

Between the CandlestickChart (~line 207) and TradeTable (~line 210), add:
```tsx
        {/* Monte Carlo Simulation */}
        <div className="mb-8">
          <MonteCarloSimulation
            jobId={parseInt(id as string)}
            initialCash={summary.final_value / (1 + summary.total_return)}
          />
        </div>
```

- [ ] **Step 3: Verify page renders**

Open http://localhost:3002/results/220 in browser. Should see Monte Carlo panel between candlestick chart and trade table.

- [ ] **Step 4: Commit**

```bash
git add frontend/app/results/[id]/page.tsx
git commit -m "feat: integrate Monte Carlo simulation into backtest results page"
```

---

### Task 6: End-to-End Verification

- [ ] **Step 1: Restart backend**

```bash
cd /Users/yasin/code/quant2 && ./start.sh restart
```

- [ ] **Step 2: Open results page in browser**

Navigate to http://localhost:3002/results/220 (or any completed backtest with >= 10 trades)

- [ ] **Step 3: Click "Run Simulation"**

- Verify stats cards appear with reasonable values
- Verify fan chart shows P5/P25/P50/P75/P95 lines
- Verify histogram shows return distribution with original marked
- Verify slider changes simulation count
- Verify button shows "Running..." during computation

- [ ] **Step 4: Run backend tests**

```bash
cd /Users/yasin/code/quant2 && python -m pytest tests/test_monte_carlo.py -v
```
Expected: All 7 tests PASS
