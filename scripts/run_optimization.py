#!/usr/bin/env python3
"""Run Bayesian optimization for Trend Pullback V6"""
import requests
import time
import json

API_URL = "http://localhost:8000/api/v1/backtest/optimize"

# Optimize only key parameters (7 total)
# Fix less impactful parameters to defaults
payload = {
    "strategy_name": "Trend Pullback V6",
    "symbol": "ETHUSDT",
    "interval": "1h",
    "start_time": "2022-01-01T00:00:00",
    "end_time": "2024-12-28T23:59:59",
    "optimization_method": "bayesian",
    "n_trials": 100,
    "enable_stability_analysis": True,
    "parameter_ranges": {
        "ema_fast": {"min": 8, "max": 18},
        "ema_slow": {"min": 20, "max": 35},
        "pullback_threshold": {"min": 30, "max": 45},
        "atr_stop_mult": {"min": 0.8, "max": 2.0},
        "adx_threshold": {"min": 18.0, "max": 30.0},
        "vol_scale_threshold": {"min": 1.2, "max": 1.8},
        "cb_max_losses": {"min": 2, "max": 4}
    },
    "fixed_parameters": {
        "rsi_period": 14,
        "rsi_exit_long": 70,
        "rsi_exit_short": 30,
        "atr_period": 14,
        "risk_pct": 1.2,
        "pullback_pct": 0.8,
        "momentum_period": 10
    }
    # NOTE: NOT passing scoring_weights - let API use defaults
}

print("=" * 60)
print("BAYESIAN OPTIMIZATION: Trend Pullback V6 on ETH 1h")
print("=" * 60)
print(f"Symbol: {payload['symbol']}")
print(f"Interval: {payload['interval']}")
print(f"Training Period: {payload['start_time']} → {payload['end_time']}")
print(f"Method: {payload['optimization_method']}")
print(f"Trials: {payload['n_trials']}")
print(f"Optimizing {len(payload['parameter_ranges'])} parameters")
print(f"Fixed {len(payload['fixed_parameters'])} parameters")
print("\nStarting optimization...")

start = time.time()
response = requests.post(API_URL, json=payload, timeout=60)

if response.status_code == 200:
    result = response.json()
    job_id = result.get('job_id')
    elapsed = time.time() - start

    print(f"\n✓ Optimization job created!")
    print(f"  Job ID: {job_id}")
    print(f"  Status: {result.get('status')}")
    print(f"  Message: {result.get('message')}")
    print(f"  Response time: {elapsed:.1f}s")
    print(f"\nMonitor job: http://localhost:3002")
    print(f"\nTo check status:")
    print(f"  curl -s http://localhost:8000/api/v1/backtest/jobs/{job_id} | python3 -m json.tool")
else:
    print(f"\n✗ Failed to create optimization job!")
    print(f"  Status Code: {response.status_code}")
    print(f"  Response: {response.text}")
