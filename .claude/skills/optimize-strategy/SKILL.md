---
name: optimize-strategy
description: Strategy optimization workflow using Bayesian parameter tuning, cross-validation backtesting, and iterative strategy refinement. Use when the user wants to optimize a trading strategy, tune strategy parameters, find optimal parameters via Bayesian optimization, or run a complete optimize-then-validate workflow. Triggers include "optimize strategy", "tune parameters", "find best parameters", "策略优化", "参数调优", "贝叶斯优化".
---

# Strategy Optimization Workflow

Complete end-to-end workflow: Bayesian parameter optimization → result analysis → cross-validation backtest → result analysis → strategy refinement.

## Prerequisites Check

Before starting, verify the backend is running:
```bash
curl -s http://localhost:8000/api/v1/strategies/ | head -c 200
```

If not running, start it:
```bash
cd /Users/yasin/code/quant2 && ./start.sh start
```

## Workflow Steps

### Step 1: Gather Context

1. **List available strategies** — `GET /api/v1/strategies/`
2. **Get strategy details** — `GET /api/v1/strategies/{strategy_name}` to see parameters
3. **List available datasets** — `GET /api/v1/data/datasets`
4. **Read strategy source code** — Read the `.py` file in `backend/strategies/`

If no datasets available, ask user to download data first.

### Step 2: Select Dataset & Split Time Range

1. From available datasets, select the one with the **longest time range** and **appropriate timeframe** (prefer 1h or 4h for optimization)
2. Calculate time split:
   - **Training period (70%)**: First 70% of the dataset time range — used for Bayesian optimization
   - **Validation period (30%)**: Last 30% of the dataset time range — used for cross-validation backtest
3. Display the selected dataset, time ranges, and split to user for confirmation

Example split calculation:
```
Dataset: BTCUSDT 4h (2023-01-01 to 2024-12-31)
Training:   2023-01-01 → 2024-05-10  (optimization)
Validation: 2024-05-11 → 2024-12-31  (cross-validation)
```

### Step 3: Run Bayesian Optimization

Call `POST /api/v1/backtest/optimize` with:
```json
{
  "strategy_name": "<strategy_name>",
  "dataset_id": "<dataset_id>",
  "start_time": "<training_start>",
  "end_time": "<training_end>",
  "optimization_method": "bayesian",
  "n_trials": 100,
  "parameter_ranges": { ... },
  "enable_stability_analysis": true,
  "scoring_weights": {}
}
```

**CRITICAL: Use Calmar-focused scoring weights!** The primary optimization target is **Calmar Ratio** (Annual Return / Max Drawdown). Use `"scoring_weights": {"sharpe": 0.20, "calmar": 0.40, "max_drawdown": -0.25, "profit_factor": 0.10, "win_rate": 0.00, "trade_frequency": 0.05}` to prioritize Calmar. NEVER pass `"scoring_weights": {}` (empty dict makes all scores = 0).

Set `n_trials` to 100 by default. Increase to 200 if parameter space is large (>6 parameters).

**Parameter count guideline:** With 15+ parameters, the Bayesian optimizer struggles (vast search space). Prefer:
- Optimize 3-6 key parameters
- Fix less impactful parameters to their defaults via `fixed_parameters`

**Narrow parameter ranges:** Start with ranges close to the defaults. Wide ranges (e.g., fast_period 5-50) make the optimizer waste trials on unproductive regions.

Poll job status via `GET /api/v1/backtest/jobs/{job_id}` until status is `completed`.

### Step 4: Analyze Optimization Results

1. **Get optimization results** — `GET /api/v1/backtest/optimization/jobs/{job_id}/results`
2. **Get stability analysis** — `GET /api/v1/backtest/optimization/jobs/{job_id}/stability`

Analyze and report:

#### Score Analysis
- Best composite score and its components
- If score < 0.3: strategy likely not viable → suggest user reconsider
- If score > 0.7: good optimization result

#### Stability Analysis
- `stability_score` ≥ 0.7: parameters are robust
- `stability_score` < 0.5: likely overfitting → consider widening parameter ranges or adjusting strategy
- Check `is_stable` flag

#### Key Metrics
- Total return, Sharpe ratio, max drawdown, win rate, profit factor
- Trade count (must be ≥ 20 for meaningful results)

#### Parameter Sensitivity
- Which parameters have the most impact (check neighbor variations in stability analysis)

### Step 5: Strategy Refinement (if needed)

If optimization results are poor (score < 0.4 or unstable):

1. **Backup strategy file**:
   ```bash
   cp backend/strategies/{strategy_file}.py backend/strategies/{strategy_file}.py.bak.{timestamp}
   ```

2. **Analyze issues** and adjust strategy logic. Common improvements:
   - Add trend filter (only trade in direction of higher timeframe trend)
   - Add volatility filter (skip low-volatility periods)
   - Adjust entry/exit conditions
   - Add partial position sizing
   - Add stop-loss / take-profit

3. **Re-run optimization** (Step 3) with refined strategy

### Step 6: Cross-Validation Backtest

Once optimization results are satisfactory:

1. **Run backtest** with best parameters on **validation period** (the remaining 30%):
   ```
   POST /api/v1/backtest/run
   {
     "strategy_name": "<strategy_name>",
     "dataset_id": "<dataset_id>",
     "start_time": "<validation_start>",
     "end_time": "<validation_end>",
     "parameters": { <best_parameters_from_optimization> }
   }
   ```

2. **Get backtest results** — `GET /api/v1/backtest/jobs/{job_id}`

### Step 7: Analyze Backtest Results

Compare validation backtest metrics against optimization metrics:

**Primary Metric - Calmar Ratio:**
- Calmar Ratio = Annual Return / |Max Drawdown|
- Target: **Calmar > 2.0** (excellent), 1.5-2.0 (good), 1.0-1.5 (acceptable), < 1.0 (poor)
- **This is the most important metric**

**Secondary Metrics:**
| Metric | Good | Warning | Bad |
|--------|------|---------|-----|
| Max Drawdown | < 15% | 15-30% | > 30% |
| Profit Factor | > 1.5 | 1.0-1.5 | < 1.0 |
| Trade Count | > 30 | 10-30 | < 10 |

**Note:** Sharpe Ratio and Win Rate are **NOT important** for this strategy.

**Overfitting Detection:**
- If validation Calmar drops > 50% from training Calmar → likely overfit
- If validation max drawdown is > 2x training max drawdown → likely overfit
- If trade count in validation is < 10 → insufficient data

**Assessment:**
- If validation Calmar Ratio is consistent with training (within 50%) → strategy is robust
- If significant degradation → strategy may be overfit, consider Step 5 refinement

### Step 8: Strategy Code Optimization (if needed)

If validation results show issues but are fixable:

1. **Backup strategy file** (if not already backed up):
   ```bash
   cp backend/strategies/{strategy_file}.py backend/strategies/{strategy_file}.py.bak.{timestamp}
   ```

2. **Optimize strategy code** addressing specific issues found in validation
3. **Re-run the full workflow** from Step 3

### Step 9: Final Output

1. Report final backtest job ID
2. Open the results page in browser:
   ```bash
   open "http://localhost:3002/results/{backtest_job_id}"
   ```

## Summary Report Template

After completing the workflow, output a summary like:

```
## Strategy Optimization Summary

**Strategy**: {name} v{version}
**Dataset**: {symbol} {interval} ({dataset_name})
**Optimization**: {n_trials} Bayesian trials

### Best Parameters
{formatted parameter list}

### Training Results (70%)
- **Calmar Ratio: {calmar}** (PRIMARY METRIC)
- Total Return: {return}
- Max Drawdown: {drawdown}
- Profit Factor: {pf}
- Trades: {count}
- Stability: {stability_score} ({is_stable})

### Validation Results (30%)
- **Calmar Ratio: {calmar}** (PRIMARY METRIC)
- Total Return: {return}
- Max Drawdown: {drawdown}
- Profit Factor: {pf}
- Trades: {count}

### Assessment
{overall assessment of strategy quality and robustness}

**Backtest Job ID**: {id}
**URL**: http://localhost:3002/results/{id}
```

## Important Notes

- **Always backup** strategy files before modifying them
- **Use dataset_id** (not symbol/interval) for all API calls — the system uses dataset-based data management
- **Training/validation split** is always 70/30 by time range
- **Never skip stability analysis** — it's critical for detecting overfitting
- **Backend must be running** before starting the workflow
- **Percentage values** in API are stored as decimals (15% = 0.15) but displayed as percentages
- When reading/writing strategy Python files, use the Read/Edit tools directly
- **NEVER pass `"scoring_weights": {}`** — omit the field entirely to use default weights
- **After modifying strategy code**, restart the backend (`./start.sh restart`) to clear Python module cache
- **If optimizer returns score 0.0 for all trials**, check: (1) scoring_weights not `{}`, (2) parameter ranges not too wide, (3) backend restarted after code changes
- **Diagnose 0-trade results**: manually test the optimizer's params via `POST /api/v1/backtest/run` to compare with optimizer's internal backtest

## Known Bugs

- **Stability analysis fails** with `database_url` missing error — non-critical, does not affect optimization
- **Bayesian optimizer uses `get_candles()`** instead of `get_candles_by_dataset()` — may include candles from overlapping datasets
- **`POST /strategies/refresh`** may not fully reload modified strategies due to Python module caching — restart backend instead
