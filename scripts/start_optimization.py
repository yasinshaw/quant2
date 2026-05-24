#!/usr/bin/env python3
"""Start Bayesian optimization and poll for completion"""
import requests
import time
import json

API_URL = "http://localhost:8000/api/v1/backtest/optimize"
STATUS_URL = "http://localhost:8000/api/v1/backtest/jobs/{}"

# Optimize only key parameters (7 total)
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
        "ema_fast": {"min": 8, "max": 16},
        "ema_slow": {"min": 22, "max": 32},
        "pullback_threshold": {"min": 35, "max": 42},
        "atr_stop_mult": {"min": 1.2, "max": 2.2},
        "adx_threshold": {"min": 15.0, "max": 22.0},
        "risk_pct": {"min": 1.0, "max": 2.0}
    },
    "fixed_parameters": {
        "rsi_period": 14,
        "rsi_exit_long": 70,
        "rsi_exit_short": 30,
        "atr_period": 14,
        "vol_scale_threshold": 1.5,
        "cb_max_losses": 3
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
try:
    response = requests.post(API_URL, json=payload, timeout=30)
    elapsed = time.time() - start

    if response.status_code == 200:
        result = response.json()
        job_id = result.get('job_id') or result.get('id')

        print(f"\n✓ Optimization job started!")
        print(f"  Job ID: {job_id}")
        print(f"  Setup time: {elapsed:.1f}s")
        print(f"\nThe optimization is now running in the background.")
        print(f"This may take 20-60 minutes depending on your CPU.")
        print(f"\nMonitor progress:")
        print(f"  Frontend: http://localhost:3002")
        print(f"  Status API:")
        print(f"    curl -s {STATUS_URL.format(job_id)} | python3 -m json.tool")
        print(f"\nBest results will be saved to the database.")
        print(f"Check back in ~30 minutes.")

        # Save job ID to file for later reference
        with open('/tmp/optimization_job_id.txt', 'w') as f:
            f.write(str(job_id))
        print(f"\nJob ID saved to /tmp/optimization_job_id.txt")

    else:
        print(f"\n✗ Failed to start optimization!")
        print(f"  Status Code: {response.status_code}")
        print(f"  Response: {response.text}")

except requests.exceptions.Timeout:
    print(f"\n⚠ Request timed out after {elapsed:.1f}s")
    print(f"The optimization may still be running on the server.")
    print(f"Check the backend logs: ./start.sh logs backend")

except Exception as e:
    print(f"\n✗ Error: {e}")
