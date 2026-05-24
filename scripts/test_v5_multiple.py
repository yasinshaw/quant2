#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""V5 Multiple Parameter Configurations Test"""
import requests
import time

API_URL = "http://localhost:8000/api/v1/backtest/run"

# 多个测试配置
test_configs = [
    {
        "name": "V5 Config 1 (Baseline)",
        "params": {
            "ema_fast": 24, "ema_slow": 85,
            "rsi_period": 21, "pullback_threshold": 40,
            "rsi_exit_long": 71, "rsi_exit_short": 27,
            "atr_stop_mult": 1.5, "risk_pct": 1.5,
            "adx_threshold": 10,
        }
    },
    {
        "name": "V5 Config 2 (Faster EMAs)",
        "params": {
            "ema_fast": 18, "ema_slow": 70,
            "rsi_period": 19, "pullback_threshold": 38,
            "rsi_exit_long": 68, "rsi_exit_short": 32,
            "atr_stop_mult": 1.6, "risk_pct": 1.8,
            "adx_threshold": 15,
        }
    },
    {
        "name": "V5 Config 3 (Tighter stops)",
        "params": {
            "ema_fast": 22, "ema_slow": 80,
            "rsi_period": 20, "pullback_threshold": 42,
            "rsi_exit_long": 65, "rsi_exit_short": 35,
            "atr_stop_mult": 1.3, "risk_pct": 2.0,
            "adx_threshold": 18,
        }
    },
    {
        "name": "V5 Config 4 (Lower ADX)",
        "params": {
            "ema_fast": 26, "ema_slow": 90,
            "rsi_period": 21, "pullback_threshold": 38,
            "rsi_exit_long": 70, "rsi_exit_short": 30,
            "atr_stop_mult": 1.4, "risk_pct": 1.5,
            "adx_threshold": 12,  # Lower ADX
        }
    },
    {
        "name": "V5 Config 5 (Higher risk)",
        "params": {
            "ema_fast": 20, "ema_slow": 75,
            "rsi_period": 18, "pullback_threshold": 35,
            "rsi_exit_long": 72, "rsi_exit_short": 28,
            "atr_stop_mult": 1.7, "risk_pct": 2.5,
            "adx_threshold": 16,
        }
    },
]

print("=" * 80)
print("V5 MULTIPLE CONFIGURATIONS TEST (Training Period)")
print("=" * 80)
print(f"Testing {len(test_configs)} configurations...")
print("")

results = []

for i, config in enumerate(test_configs, 1):
    print(f"{'='*80}")
    print(f"Test {i}/{len(test_configs)}: {config['name']}")
    print(f"{'='*80}")

    payload = {
        "strategy_name": "Trend Pullback V5",
        "dataset_id": 16,
        "start_time": "2020-01-01T00:00:00",
        "end_time": "2024-05-20T23:59:59",
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

        annual_return = return_pct / 4.4
        calmar = annual_return / abs(max_dd) if max_dd != 0 else 0

        print(f"✓ Completed ({elapsed:.1f}s)")
        print(f"  Calmar: {calmar:.2f}, Return: {return_pct:.2f}%, DD: {max_dd:.2f}%, Trades: {trades}")

        results.append({
            "name": config['name'],
            "job_id": job_id,
            "calmar": calmar,
            "return": return_pct,
            "max_dd": max_dd,
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
    print(f"   Calmar: {best['calmar']:.2f}")
    print(f"   Job ID: {best['job_id']}")
    print(f"   URL: http://localhost:3002/results/{best['job_id']}")

    if best['calmar'] >= 1.0:
        print(f"\n✓ Meets threshold (Calmar {best['calmar']:.2f} ≥ 1.0)")
        print(f"  Next: Run validation period backtest")
    else:
        print(f"\n✗ Below threshold (Calmar {best['calmar']:.2f} < 1.0)")
        print(f"  May need further optimization")
