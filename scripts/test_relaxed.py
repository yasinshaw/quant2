#!/usr/bin/env python3
"""Test with relaxed parameters"""
import requests

API_URL = "http://localhost:8000/api/v1/backtest/run"

# Test with very relaxed parameters
payload = {
    "strategy_name": "Trend Pullback V6",
    "dataset_id": 18,
    "start_time": "2022-01-01T00:00:00",
    "end_time": "2022-12-31T23:59:59",
    "parameters": {
        "adx_threshold": 15.0,  # Lower ADX threshold
        "pullback_threshold": 30,  # More aggressive entry
        "use_momentum_filter": False,  # Disable momentum filter
        "pullback_pct": 0.0,  # Disable enhanced pullback
    }
}

print("Testing with RELAXED parameters...")
print(f"Period: 2022 (1 year)")

response = requests.post(API_URL, json=payload, timeout=180)

if response.status_code == 200:
    result = response.json()
    print(f"\n✓ Backtest completed!")
    print(f"  Total Trades: {result.get('total_trades', 0)}")
    print(f"  Return: {result.get('pnl_pct', 0):.2f}%")
else:
    print(f"\n✗ Failed: {response.status_code}")
    print(response.text[:500])
