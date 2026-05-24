# Bayesian Optimizer Performance Benchmark Guide

## Overview

This guide explains how to use the performance benchmark tools to measure and validate optimizations for the Bayesian optimizer.

## Setup

### Prerequisites

1. **Download test data** (if not already available):

```bash
# Download 1 month of BTCUSDT 1h data
curl -X POST http://localhost:8000/api/v1/data/download \
  -H 'Content-Type: application/json' \
  -d '{
    "symbol": "BTCUSDT",
    "interval": "1h",
    "start_time": "2024-01-01T00:00:00",
    "end_time": "2024-01-31T23:59:59"
  }'
```

2. **Ensure backend services are running**:

```bash
# Start backend
cd backend
source venv/bin/activate
python main.py
```

## Usage

### Step 1: Run Baseline Benchmark

Before making any optimizations, establish a performance baseline:

```bash
# Full benchmark (takes ~5-10 minutes)
python scripts/benchmark_bayesian_optimizer.py --output baseline.json

# Quick benchmark for faster iteration (~2-3 minutes)
python scripts/benchmark_bayesian_optimizer.py --quick --output baseline.json
```

**Output:**
```
============================================================
Bayesian Optimizer Performance Benchmark
============================================================
Strategy: Double MA Crossover
Data: BTCUSDT 1h
Period: 2024-01-01T00:00:00 to 2024-01-31T23:59:59
Quick Mode: True

✓ Found 744 candles in database

============================================================
Benchmark: Small (2 params, 10 trials)
============================================================
  Trials: 10
  Parameters: {'fast_period': {...}, 'slow_period': {...}}

✓ Benchmark completed
  Total time: 15.23s
  Average time per trial: 1.523s
  Trials per second: 0.66
  Peak memory: 125.45 MB
  Best score: 0.8234
  Best params: {'fast_period': 8, 'slow_period': 22}

============================================================
Benchmark Summary
============================================================

Scenario                        Time     Trials/s     Memory
--------------------------------------------------------------
Small (2 params, 10 trials)        15.23        0.66     125.45
Medium (2 params, 20 trials)       32.18        0.62     138.92
Large (2 params, 30 trials)        48.76        0.61     142.31
--------------------------------------------------------------
Average                           32.06        0.63     135.56

✓ Results saved to baseline.json
```

### Step 2: Apply Optimizations

Make your performance improvements to the code (see below for optimization ideas).

### Step 3: Run Optimized Benchmark

```bash
# Use same quick mode option for fair comparison
python scripts/benchmark_bayesian_optimizer.py --quick --output optimized.json
```

### Step 4: Compare Results

```bash
python scripts/compare_benchmark_results.py baseline.json optimized.json
```

**Output:**
```
======================================================================
Performance Comparison Report
======================================================================

Before: 2026-03-27T10:30:15.123456
After:  2026-03-27T11:45:30.789012
Strategy: Double MA Crossover

Scenario                        Before        After        Change
----------------------------------------------------------------------

Large (2 params, 30 trials)
  Time (s)                       48.76        12.45      +74.5%  ← Green
  Trials/s                        0.61         2.41     +295.1%  ← Green
  Memory (MB)                    142.31       145.23       -2.0%  ← Green

======================================================================
Overall Improvement
======================================================================

Average Time:        +74.5%
Average Throughput:  +295.1%
Average Memory:      -2.0%

🚀 Overall Speedup: 3.92x
✅ Optimization successful!
```

## Benchmark Scenarios

The benchmark runs three scenarios with increasing complexity:

| Scenario | Parameters | Trials | Purpose |
|----------|-----------|--------|---------|
| Small | 2 params, narrow range | 10 | Quick sanity check |
| Medium | 2 params, medium range | 50/20* | Normal workload |
| Large | 2 params, wide range | 100/30* | Stress test |

*Quick mode uses fewer trials

## Key Metrics

- **Total Duration**: Wall-clock time for all trials
- **Trials per Second**: Throughput metric (higher is better)
- **Peak Memory**: Maximum memory usage
- **Average Trial Time**: Latency per trial

## Optimization Opportunities

Based on code analysis, here are the main optimization targets:

### 1. **Optuna Parallelization** (Highest Impact) ⭐⭐⭐

**Current:** Sequential execution
```python
study.optimize(objective, n_trials=n_trials)
```

**Optimized:** Parallel execution
```python
study.optimize(objective, n_trials=n_trials, n_jobs=4)
```

**Expected:** 3-4x speedup

### 2. **Optuna Sampler Configuration** (Medium Impact) ⭐⭐

**Current:** Default sampler
```python
study = optuna.create_study(direction='maximize')
```

**Optimized:** TPE sampler with pruning
```python
from optuna.samplers import TPESampler
from optuna.pruners import MedianPruner

sampler = TPESampler(seed=42)
pruner = MedianPruner()
study = optuna.create_study(
    direction='maximize',
    sampler=sampler,
    pruner=pruner
)
```

**Expected:** 30-50% fewer trials needed for same quality

### 3. **Data Feed Caching** (Low-Medium Impact) ⭐

**Current:** Recreated every trial
```python
def objective(trial):
    data = self.backtest_engine._create_data_feed(candles)  # Every trial
```

**Optimized:** Pre-created data feed
```python
# Create once before optimization
data_feed = self.backtest_engine._create_data_feed(candles)

def objective(trial):
    # Reuse cached data feed
    cerebro = bt.Cerebro()
    cerebro.adddata(data_feed)  # No creation overhead
```

**Expected:** 20-30% faster

### 4. **Avoid Redundant Final Backtest** (Low Impact)

**Current:** Runs best params again after optimization
```python
# Line 274-280 in bayesian_optimizer.py
best_result = await self._run_single_backtest(...)
```

**Optimized:** Store full results during optimization

**Expected:** 10-15% time savings

## Performance Targets

Based on the analysis, realistic targets are:

| Optimization | Target | Status |
|--------------|--------|--------|
| Parallelization | 3-4x speedup | Not implemented |
| Sampler + Pruner | 30-50% improvement | Not implemented |
| Data caching | 20-30% faster | Not implemented |
| Remove redundant | 10-15% faster | Not implemented |
| **Overall** | **4-6x speedup** | Baseline established |

## Troubleshooting

### No test data found

```bash
# Download required data
curl -X POST http://localhost:8000/api/v1/data/download \
  -H 'Content-Type: application/json' \
  -d '{
    "symbol": "BTCUSDT",
    "interval": "1h",
    "start_time": "2024-01-01T00:00:00",
    "end_time": "2024-01-31T23:59:59"
  }'
```

### Benchmark hangs or takes too long

Use `--quick` flag for faster iteration:
```bash
python scripts/benchmark_bayesian_optimizer.py --quick
```

### Comparison shows negative improvement

Verify you're comparing same scenarios:
1. Both benchmarks should use same `--quick` flag
2. Test data should be the same
3. System load should be similar

## Continuous Performance Monitoring

Add to CI/CD pipeline:

```yaml
# .github/workflows/performance.yml
name: Performance Tests

on: [pull_request]

jobs:
  benchmark:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Run benchmark
        run: |
          python scripts/benchmark_bayesian_optimizer.py --quick
      - name: Check regression
        run: |
          python scripts/compare_benchmark_results.py \
            baseline.json \
            current.json
```

## Next Steps

1. ✅ Run baseline benchmark: `python scripts/benchmark_bayesian_optimizer.py --quick --output baseline.json`
2. 📝 Review optimization opportunities above
3. 🔧 Implement optimizations (start with parallelization)
4. 📊 Run optimized benchmark: `python scripts/benchmark_bayesian_optimizer.py --quick --output optimized.json`
5. 📈 Compare results: `python scripts/compare_benchmark_results.py baseline.json optimized.json`
6. 🎯 Target: 4-6x overall speedup
