#!/usr/bin/env python3
"""Run backtests on training and validation periods"""
import requests
import json
import time

API_URL = "http://localhost:8000/api/v1/backtest/run"

# Test parameters (V6 defaults)
parameters = {
    "ema_fast": 12,
    "ema_slow": 26,
    "rsi_period": 14,
    "pullback_threshold": 38,
    "rsi_exit_long": 70,
    "rsi_exit_short": 30,
    "atr_period": 14,
    "atr_stop_mult": 1.5,
    "risk_pct": 1.5,
    "adx_threshold": 18.0,
    "vol_scale_threshold": 1.5,
    "cb_max_losses": 3,
    "max_leverage": 1.5
}

print("=" * 70)
print("STRATEGY VALIDATION: Trend Pullback V6 on ETH 1h")
print("=" * 70)
print("\nParameters:")
for k, v in parameters.items():
    print(f"  {k}: {v}")

# Training period (70%)
print("\n" + "=" * 70)
print("TRAINING PERIOD (70%): 2022-01-01 → 2024-12-28")
print("=" * 70)

training_payload = {
    "strategy_name": "Trend Pullback V6",
    "dataset_id": 18,
    "start_time": "2022-01-01T00:00:00",
    "end_time": "2024-12-28T23:59:59",
    "parameters": parameters
}

start = time.time()
response = requests.post(API_URL, json=training_payload, timeout=300)
elapsed = time.time() - start

if response.status_code == 200:
    result = response.json()
    print(f"\n✓ Training backtest completed ({elapsed:.1f}s)")
    print(f"  Job ID: {result.get('backtest_job_id')}")
    print(f"  Total Return: {result.get('pnl_pct', 0):.2f}%")
    print(f"  Sharpe Ratio: {result.get('sharpe_ratio', 0):.2f}")
    print(f"  Max Drawdown: {result.get('max_drawdown', 0):.2f}%")
    print(f"  Win Rate: {result.get('win_rate', 0):.2f}%")
    print(f"  Total Trades: {result.get('total_trades', 0)}")

    training_job_id = result.get('backtest_job_id')
else:
    print(f"\n✗ Training backtest failed!")
    print(f"  {response.text}")
    training_job_id = None

# Validation period (30%)
print("\n" + "=" * 70)
print("VALIDATION PERIOD (30%): 2024-12-28 → 2026-04-10")
print("=" * 70)

validation_payload = {
    "strategy_name": "Trend Pullback V6",
    "dataset_id": 18,
    "start_time": "2024-12-29T00:00:00",
    "end_time": "2026-04-10T23:59:59",
    "parameters": parameters
}

start = time.time()
response = requests.post(API_URL, json=validation_payload, timeout=300)
elapsed = time.time() - start

if response.status_code == 200:
    result = response.json()
    print(f"\n✓ Validation backtest completed ({elapsed:.1f}s)")
    print(f"  Job ID: {result.get('backtest_job_id')}")
    print(f"  Total Return: {result.get('pnl_pct', 0):.2f}%")
    print(f"  Sharpe Ratio: {result.get('sharpe_ratio', 0):.2f}")
    print(f"  Max Drawdown: {result.get('max_drawdown', 0):.2f}%")
    print(f"  Win Rate: {result.get('win_rate', 0):.2f}%")
    print(f"  Total Trades: {result.get('total_trades', 0)}")

    validation_job_id = result.get('backtest_job_id')
else:
    print(f"\n✗ Validation backtest failed!")
    print(f"  {response.text}")
    validation_job_id = None

# Summary
print("\n" + "=" * 70)
print("SUMMARY")
print("=" * 70)
print(f"Training Job ID: {training_job_id}")
print(f"Validation Job ID: {validation_job_id}")
print(f"\nView results: http://localhost:3002/results/{training_job_id}")
print(f"               http://localhost:3002/results/{validation_job_id}")

# Save job IDs
with open('/tmp/backtest_job_ids.txt', 'w') as f:
    f.write(f"Training: {training_job_id}\n")
    f.write(f"Validation: {validation_job_id}\n")
