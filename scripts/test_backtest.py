#!/usr/bin/env python3
"""Test single backtest to see trade count"""
import requests
import json

API_URL = "http://localhost:8000/api/v1/backtest/run"

# Use default parameters
payload = {
    "strategy_name": "Trend Pullback V6",
    "dataset_id": 18,
    "start_time": "2022-01-01T00:00:00",
    "end_time": "2022-12-31T23:59:59",
    "parameters": {}
}

print("Testing backtest with default parameters...")
print(f"Strategy: {payload['strategy_name']}")
print(f"Period: {payload['start_time']} → {payload['end_time']}")

response = requests.post(API_URL, json=payload, timeout=120)

if response.status_code == 200:
    result = response.json()
    print(f"\n✓ Backtest completed!")
    print(f"  Job ID: {result.get('backtest_job_id')}")
    print(f"  Total Trades: {result.get('total_trades', 0)}")
    print(f"  Return: {result.get('pnl_pct', 0):.2f}%")
    print(f"  Sharpe: {result.get('sharpe_ratio', 0):.2f}")
    print(f"  Max DD: {result.get('max_drawdown', 0):.2f}%")
else:
    print(f"\n✗ Backtest failed!")
    print(f"  Status Code: {response.status_code}")
    print(f"  Response: {response.text}")
