#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Mean Reversion V1 Testing"""
import requests
import time

API_URL = "http://localhost:8000/api/v1/backtest/run"

# 测试配置
test_configs = [
    {
        "name": "MR Config 1 (Default)",
        "params": {
            "bb_period": 20,
            "bb_dev": 2.0,
            "rsi_period": 14,
            "rsi_oversold": 30,
            "rsi_overbought": 70,
            "rsi_exit": 50,
            "atr_stop_mult": 2.0,
        }
    },
    {
        "name": "MR Config 2 (Wider BB)",
        "params": {
            "bb_period": 20,
            "bb_dev": 2.5,       # 更宽的布林带
            "rsi_period": 14,
            "rsi_oversold": 25,   # 更严格的阈值
            "rsi_overbought": 75,
            "rsi_exit": 50,
            "atr_stop_mult": 2.0,
        }
    },
    {
        "name": "MR Config 3 (Faster signals)",
        "params": {
            "bb_period": 15,       # 更快
            "bb_dev": 2.0,
            "rsi_period": 10,       # 更快
            "rsi_oversold": 30,
            "rsi_overbought": 70,
            "rsi_exit": 50,
            "atr_stop_mult": 1.8,   # 更紧的止损
        }
    },
]

print("=" * 80)
print("MEAN REVERSION V1 TESTING - Non-Trend Strategy")
print("=" * 80)
print("Strategy: Buy dips, sell rallies (opposite of trend following)")
print(f"Testing {len(test_configs)} configurations...")
print("")

results = []

for i, config in enumerate(test_configs, 1):
    print(f"{'='*80}")
    print(f"Test {i}/{len(test_configs)}: {config['name']}")
    print(f"{'='*80}")

    payload = {
        "strategy_name": "Mean Reversion V1",
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
        print(f"  **Calmar: {calmar:.2f}**")
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

if results:
    best = results[0]
    print(f"\n🏆 BEST: {best['name']}")
    print(f"   Calmar Ratio: {best['calmar']:.2f}")
    print(f"   Target: >2.0 excellent, 1.5-2.0 good, 1.0-1.5 acceptable, <1.0 poor")
    print(f"   Job ID: {best['job_id']}")
    print(f"   URL: http://localhost:3002/results/{best['job_id']}")

    # Compare with trend strategies
    print(f"\n{'='*80}")
    print("STRATEGY TYPE COMPARISON:")
    print(f"{'='*80}")
    print(f"Trend Following (V10/V13b):")
    print(f"  Training: High Calmar (1.29-1.55)")
    print(f"  Validation: FAILED (Calmar -0.57)")
    print(f"  Reason: Market regime changed, trends stopped working")
    print(f"")
    print(f"Mean Reversion V1:")
    print(f"  Training: Calmar {best['calmar']:.2f}")
    print(f"  Better for: Ranging markets, reversals")

    if best['calmar'] >= 1.0:
        print(f"\n✓ Mean Reversion meets threshold (1.0)")
        print(f"  Next: Run validation period backtest")
        print(f"  Expectation: Should work better in validation period")
        print(f"               (market may be ranging vs trending)")
    else:
        print(f"\n⚠️  Mean Reversion below threshold (1.0)")
        print(f"  May need parameter optimization")
