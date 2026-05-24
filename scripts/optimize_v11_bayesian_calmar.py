#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""V11 Bayesian Optimization - Calmar Ratio Priority"""
import requests
import time
import json

API_URL = "http://localhost:8000/api/v1/backtest/optimize"

# Calmar-focused scoring weights
# Calmar Ratio = Annual Return / |Max Drawdown|
# Target: Maximize Calmar while keeping drawdown low
scoring_weights = {
    "sharpe": 0.20,
    "calmar": 0.40,        # HIGHEST PRIORITY
    "max_drawdown": -0.25, # HEAVILY PENALIZE DRAWDOWN
    "profit_factor": 0.10,
    "win_rate": 0.00,      # IGNORE WIN RATE
    "trade_frequency": 0.05
}

# Narrow parameter ranges around V10 Iteration 14's best values
payload = {
    "strategy_name": "Trend Following V11",
    "symbol": "ETHUSDT",
    "interval": "1h",
    "start_time": "2022-01-01T00:00:00",
    "end_time": "2024-12-28T23:59:59",
    "optimization_method": "bayesian",
    "n_trials": 150,  # 更多trial以找到更好的Calmar
    "parameter_ranges": {
        "trend_ema_period": [180, 220],
        "fast_ema": [12, 18],
        "slow_ema": [35, 45],
        "rsi_long_entry": [25, 35],
        "rsi_short_entry": [65, 75],
        "atr_stop_mult": [1.5, 2.2],
        "adx_threshold": [20, 24],
    },
    "enable_stability_analysis": True,
    "scoring_weights": scoring_weights,
}

print("=" * 80)
print("V11 BAYESIAN OPTIMIZATION - CALMAR RATIO PRIORITY")
print("=" * 80)
print("Objective: Maximize Calmar Ratio (Annual Return / |Max Drawdown|)")
print("")
print("Scoring Weights (Calmar-focused):")
print("  - Calmar Ratio:     40% (PRIMARY)")
print("  - Max Drawdown:    -25% (HEAVY PENALTY)")
print("  - Sharpe Ratio:     20%")
print("  - Profit Factor:    10%")
print("  - Trade Frequency:  5%")
print("  - Win Rate:         0% (IGNORED)")
print("")
print("Parameter Ranges (Narrow for stability):")
print("  - trend_ema_period: 180-220")
print("  - fast_ema:         12-18")
print("  - slow_ema:         35-45")
print("  - rsi_long_entry:   25-35")
print("  - rsi_short_entry:  65-75")
print("  - atr_stop_mult:    1.5-2.2")
print("  - adx_threshold:    20-24")
print("")
print("=" * 80)
print("Starting optimization (this may take 10-30 minutes)...")
print("=" * 80)
print("")

start = time.time()
response = requests.post(API_URL, json=payload, timeout=3600)
elapsed = time.time() - start

if response.status_code == 200:
    result = response.json()
    job_id = result.get('job_id')
    print(f"✓ Optimization job started: {job_id}")
    print(f"  Response time: {elapsed:.1f}s")
    print("")
    print("Optimization is running in the background.")
    print("Use this job ID to check progress and retrieve results.")
    print("")
    print("To check status:")
    print(f"  curl http://localhost:8000/api/v1/backtest/jobs/{job_id}")
    print("")
    print("To get results:")
    print(f"  curl http://localhost:8000/api/v1/backtest/optimization/jobs/{job_id}/results")
else:
    print(f"✗ Failed to start optimization:")
    print(f"  Status: {response.status_code}")
    print(f"  Response: {response.text}")
