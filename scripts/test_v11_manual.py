#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""V11 Manual Testing - Based on V10 Iter 14 Best Parameters"""
import requests
import time

API_URL = "http://localhost:8000/api/v1/backtest/run"

# V10 Iteration 14 best parameters (Calmar 1.55):
# - fast_ema1: 14, slow_ema1: 40
# - fast_ema2: 20, slow_ema2: 50 (平均: fast=17, slow=45)
# - rsi_long_entry_strict: 30, relaxed: 38 (平均: 34)
# - rsi_short_entry_strict: 70, relaxed: 62 (平均: 66)
# - atr_stop_mult: 1.7
# - adx_threshold: 22

# V11 simplified parameters (based on V10 iter 14 averages):
test_configs = [
    {
        "name": "V11 Config 1 (V10 avg)",
        "params": {
            "trend_ema_period": 200,
            "fast_ema": 17,    # average of 14 and 20
            "slow_ema": 45,    # average of 40 and 50
            "rsi_long_entry": 34,
            "rsi_short_entry": 66,
            "atr_stop_mult": 1.7,
            "adx_threshold": 22,
        }
    },
    {
        "name": "V11 Config 2 (Tighter stops)",
        "params": {
            "trend_ema_period": 200,
            "fast_ema": 15,
            "slow_ema": 42,
            "rsi_long_entry": 30,
            "rsi_short_entry": 70,
            "atr_stop_mult": 1.6,   # tighter
            "adx_threshold": 22,
        }
    },
    {
        "name": "V11 Config 3 (Lower ADX)",
        "params": {
            "trend_ema_period": 200,
            "fast_ema": 15,
            "slow_ema": 42,
            "rsi_long_entry": 30,
            "rsi_short_entry": 70,
            "atr_stop_mult": 1.7,
            "adx_threshold": 20,    # lower for more trades
        }
    },
]

print("=" * 80)
print("V11 MANUAL TESTING - Simplified Strategy")
print("=" * 80)
print(f"Testing {len(test_configs)} configurations...")
print("")

results = []

for i, config in enumerate(test_configs, 1):
    print(f"{'='*80}")
    print(f"Test {i}/{len(test_configs)}: {config['name']}")
    print(f"{'='*80}")

    payload = {
        "strategy_name": "Trend Following V11",
        "dataset_id": 18,
        "start_time": "2022-01-01T00:00:00",
        "end_time": "2024-12-28T23:59:59",
        "parameters": config["params"]
    }

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

        # Calculate Calmar
        annual_return = return_pct / 3
        calmar = annual_return / abs(max_dd) if max_dd != 0 else 0

        print(f"✓ Completed ({elapsed:.1f}s)")
        print(f"  Job ID: {job_id}")
        print(f"  Return: {return_pct:.2f}%")
        print(f"  **Calmar: {calmar:.2f}** (PRIMARY)")
        print(f"  Max DD: {max_dd:.2f}%")
        print(f"  Sharpe: {sharpe:.2f}")
        print(f"  Win Rate: {win_rate:.2f}%")
        print(f"  Trades: {trades}")

        results.append({
            "name": config['name'],
            "job_id": job_id,
            "return": return_pct,
            "calmar": calmar,
            "max_dd": max_dd,
            "sharpe": sharpe,
            "trades": trades
        })
    else:
        print(f"✗ Failed: {response.text}")
    print("")

# Summary
print("=" * 80)
print("SUMMARY - RANKED BY CALMAR RATIO")
print("=" * 80)

results.sort(key=lambda x: x['calmar'], reverse=True)

print(f"{'Rank':<6} {'Config':<25} {'Calmar':<10} {'Return':<10} {'Max DD':<10} {'Trades':<8}")
print("-" * 80)

for rank, r in enumerate(results, 1):
    print(f"{rank:<6} {r['name']:<25} {r['calmar']:<10.2f} {r['return']:<10.2f}% {r['max_dd']:<10.2f}% {r['trades']:<8}")

best = results[0]
print(f"\n🏆 BEST: {best['name']}")
print(f"   Calmar Ratio: {best['calmar']:.2f} (Target: >2.0 excellent, 1.5-2.0 good)")
print(f"   Job ID: {best['job_id']}")
print(f"   URL: http://localhost:3002/results/{best['job_id']}")

if best['calmar'] >= 1.5:
    print(f"\n✓✓✓ Calmar {best['calmar']:.2f} meets threshold (1.5)")
    print("    Proceed to validation period backtest...")
