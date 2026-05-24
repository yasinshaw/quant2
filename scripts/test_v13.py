#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""V13 Testing - Based on V10 Iter 14 Success"""
import requests
import time

API_URL = "http://localhost:8000/api/v1/backtest/run"

# V13测试配置（基于V10 Iter 14最佳参数）
test_configs = [
    {
        "name": "V13 Config 1 (V10 iter14 base)",
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
            "atr_stop_mult": 1.7,
            "adx_threshold": 22,
        }
    },
    {
        "name": "V13 Config 2 (V10 iter9 best)",
        "params": {
            "trend_ema_period": 200,
            "fast_ema1": 15,
            "slow_ema1": 42,
            "fast_ema2": 21,
            "slow_ema2": 52,
            "rsi_long_entry_strict": 29,
            "rsi_long_entry_relaxed": 37,
            "rsi_short_entry_strict": 71,
            "rsi_short_entry_relaxed": 63,
            "atr_stop_mult": 1.65,
            "adx_threshold": 22,
        }
    },
    {
        "name": "V13 Config 3 (Optimized for Calmar)",
        "params": {
            "trend_ema_period": 200,
            "fast_ema1": 14,
            "slow_ema1": 38,   # 稍快
            "fast_ema2": 19,
            "slow_ema2": 48,   # 稍快
            "rsi_long_entry_strict": 28,   # 稍松
            "rsi_long_entry_relaxed": 36,
            "rsi_short_entry_strict": 72,   # 稍松
            "rsi_short_entry_relaxed": 64,
            "atr_stop_mult": 1.6,    # 稍紧止损
            "adx_threshold": 21,     # 降低ADX增加机会
        }
    },
]

print("=" * 80)
print("V13 TESTING - Balanced Complexity (11 parameters)")
print("=" * 80)
print(f"Testing {len(test_configs)} configurations...")
print("")

results = []

for i, config in enumerate(test_configs, 1):
    print(f"{'='*80}")
    print(f"Test {i}/{len(test_configs)}: {config['name']}")
    print(f"{'='*80}")

    payload = {
        "strategy_name": "Trend Following V13",
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
        print(f"  **Calmar: {calmar:.2f}** (PRIMARY METRIC)")
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

print(f"{'Rank':<6} {'Config':<30} {'Calmar':<10} {'Return':<10} {'Max DD':<10} {'Trades':<8}")
print("-" * 80)

for rank, r in enumerate(results, 1):
    print(f"{rank:<6} {r['name']:<30} {r['calmar']:<10.2f} {r['return']:<10.2f}% {r['max_dd']:<10.2f}% {r['trades']:<8}")

if results:
    best = results[0]
    print(f"\n🏆 BEST: {best['name']}")
    print(f"   Calmar Ratio: {best['calmar']:.2f}")
    print(f"   Target: >2.0 excellent, 1.5-2.0 good, 1.0-1.5 acceptable")
    print(f"   Job ID: {best['job_id']}")
    print(f"   URL: http://localhost:3002/results/{best['job_id']}")

    # Compare with previous strategies
    print(f"\n{'='*80}")
    print("STRATEGY COMPARISON:")
    print(f"{'='*80}")
    print(f"V10 Iter 14 (15 params, overfit):")
    print(f"  Calmar: 1.55, Return: 26.24%, Max DD: 5.64%, Trades: 66")
    print(f"  Validation: Calmar -0.57, FAILED")
    print(f"")
    print(f"V12 (9 params, too simple):")
    print(f"  Calmar: 0.15, Return: 4.44%, Max DD: 9.90%, Trades: 27")
    print(f"")
    print(f"V13 Best (11 params, balanced):")
    print(f"  Calmar: {best['calmar']:.2f}, Return: {best['return']:.2f}%, Max DD: {best['max_dd']:.2f}%, Trades: {best['trades']}")

    if best['calmar'] >= 1.0:
        print(f"\n✓ V13 meets minimum Calmar threshold (1.0)")
        if best['calmar'] >= 1.5:
            print("  Good! Ready for validation period backtest.")
        else:
            print("  Acceptable. Can proceed to validation.")
