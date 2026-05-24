#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""V5 ETH-Tuned Parameter Test - Aggressive Adjustments for ETH Characteristics"""
import requests
import time

API_URL = "http://localhost:8000/api/v1/backtest/run"

# ETH特性调优参数（基于ETH高波动、深回撤的特性）
eth_tuned_configs = [
    {
        "name": "ETH Tuned 1 (Low ADX + Deep Pullback)",
        "params": {
            "ema_fast": 24, "ema_slow": 85,
            "rsi_period": 21, "pullback_threshold": 50,  # 更深的回撤
            "rsi_exit_long": 71, "rsi_exit_short": 27,
            "atr_stop_mult": 1.5, "risk_pct": 1.5,
            "adx_threshold": 5,  # 更低的ADX阈值（ETH趋势较弱）
        }
    },
    {
        "name": "ETH Tuned 2 (Very Low ADX)",
        "params": {
            "ema_fast": 24, "ema_slow": 85,
            "rsi_period": 21, "pullback_threshold": 45,
            "rsi_exit_long": 71, "rsi_exit_short": 27,
            "atr_stop_mult": 1.5, "risk_pct": 1.5,
            "adx_threshold": 3,  # 非常低的ADX
        }
    },
    {
        "name": "ETH Tuned 3 (Faster EMAs + Deep Pullback)",
        "params": {
            "ema_fast": 20, "ema_slow": 70,  # 更快的EMA（ETH趋势变化快）
            "rsi_period": 18, "pullback_threshold": 50,
            "rsi_exit_long": 68, "rsi_exit_short": 32,
            "atr_stop_mult": 1.6, "risk_pct": 1.8,
            "adx_threshold": 5,
        }
    },
    {
        "name": "ETH Tuned 4 (No ADX Filter)",
        "params": {
            "ema_fast": 24, "ema_slow": 85,
            "rsi_period": 21, "pullback_threshold": 45,
            "rsi_exit_long": 71, "rsi_exit_short": 27,
            "atr_stop_mult": 1.5, "risk_pct": 1.5,
            "adx_threshold": 0,  # 完全关闭ADX filter
        }
    },
    {
        "name": "ETH Tuned 5 (Conservative - High ADX + Tight Pullback)",
        "params": {
            "ema_fast": 30, "ema_slow": 100,  # 更慢的EMA
            "rsi_period": 25, "pullback_threshold": 35,  # 更浅的回撤
            "rsi_exit_long": 65, "rsi_exit_short": 35,
            "atr_stop_mult": 1.3, "risk_pct": 1.2,
            "adx_threshold": 15,
        }
    },
]

print("=" * 80)
print("V5 ETH-TUNED PARAMETER TEST (Training Period)")
print("=" * 80)
print(f"Testing {len(eth_tuned_configs)} ETH-specific configurations...")
print("Target: Find Calmar ≥ 1.0 on ETH 4h data")
print("")

results = []

for i, config in enumerate(eth_tuned_configs, 1):
    print(f"{'='*80}")
    print(f"Test {i}/{len(eth_tuned_configs)}: {config['name']}")
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

print(f"{'Rank':<6} {'Config':<35} {'Calmar':<10} {'Return':<10} {'Max DD':<10} {'Trades':<8}")
print("-" * 80)

for rank, r in enumerate(results, 1):
    print(f"{rank:<6} {r['name']:<35} {r['calmar']:<10.2f} {r['return']:<10.2f}% {r['max_dd']:<10.2f}% {r['trades']:<8}")

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
        print(f"  May need to consider different strategy type or accept lower performance")
