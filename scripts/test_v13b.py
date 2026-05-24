#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""V13b Testing - V10 Logic with Fixed Secondary Params"""
import requests
import time

API_URL = "http://localhost:8000/api/v1/backtest/run"

# V13b测试（使用V10 Iter 14最佳参数）
test_configs = [
    {
        "name": "V13b (V10 iter14 params)",
        "params": {
            "trend_ema_period": 200,
            "fast_ema1": 14,
            "slow_ema1": 40,
            "fast_ema2": 20,
            "slow_ema2": 50,
            "rsi_long_entry_strict": 30,
            "rsi_long_entry_relaxed": 38,
            "rsi_short_entry_strict": 70,
            "rsi_short_entry_relaxed": 62,
            "rsi_long_exit": 63,
            "rsi_short_exit": 37,
            "atr_stop_mult": 1.7,
            "adx_threshold": 22,
        }
    },
]

print("=" * 80)
print("V13b TESTING - V10 Logic with 12 Parameters")
print("=" * 80)
print("V13b = V10核心逻辑 + 固定次要参数")
print("")

config = test_configs[0]
payload = {
    "strategy_name": "Trend Following V13b",
    "dataset_id": 18,
    "start_time": "2022-01-01T00:00:00",
    "end_time": "2024-12-28T23:59:59",
    "parameters": config["params"]
}

print(f"Test: {config['name']}")
print(f"Parameters: {len(config['params'])} tunable")
print("")

start = time.time()
response = requests.post(API_URL, json=payload, timeout=300)
elapsed = time.time() - start

if response.status_code == 200:
    result = response.json()
    job_id = result.get('backtest_job_id')
    return_pct = result.get('pnl_pct', 0)
    sharpe = result.get('sharpe_ratio', 0)
    max_dd = result.get('max_drawdown', 100)
    win_rate = result.get('win_rate', 0)
    trades = result.get('total_trades', 0)

    annual_return = return_pct / 3
    calmar = annual_return / abs(max_dd) if max_dd != 0 else 0

    print(f"✓ Completed ({elapsed:.1f}s)")
    print(f"  Job ID: {job_id}")
    print(f"  Return: {return_pct:.2f}%")
    print(f"  **Calmar: {calmar:.2f}**")
    print(f"  Max DD: {max_dd:.2f}%")
    print(f"  Sharpe: {sharpe:.2f}")
    print(f"  Win Rate: {win_rate:.2f}%")
    print(f"  Trades: {trades}")

    print(f"\n{'='*80}")
    print("COMPARISON:")
    print(f"{'='*80}")
    print(f"V10 Iter 14 (15 params):")
    print(f"  Calmar: 1.55, Return: 26.24%, Max DD: 5.64%, Trades: 66")
    print(f"  Validation: FAILED (Calmar -0.57)")
    print(f"")
    print(f"V13b (12 params):")
    print(f"  Calmar: {calmar:.2f}, Return: {return_pct:.2f}%, Max DD: {max_dd:.2f}%, Trades: {trades}")

    if calmar >= 1.0:
        print(f"\n✓ V13b Calmar {calmar:.2f} meets threshold (1.0)")
        print(f"  Next: Run validation period backtest")
    else:
        print(f"\n✗ V13b Calmar {calmar:.2f} below threshold (1.0)")

else:
    print(f"✗ Failed: {response.text}")
