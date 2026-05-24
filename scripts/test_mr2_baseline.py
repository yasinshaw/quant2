#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Mean Reversion V2 Baseline Test on ETHUSDT 4h"""
import requests
import time

API_URL = "http://localhost:8000/api/v1/backtest/run"

# V2默认参数
baseline_params = {
    "bb_period": 20,
    "bb_dev": 2.0,
    "rsi_period": 14,
    "rsi_oversold": 30,
    "rsi_overbought": 70,
    "atr_period": 14,
    "atr_stop_mult": 2.0,
    "risk_pct": 1.0,
    "max_leverage": 1.5,
    "exit_at_middle_band": True,
    "exit_at_opposite_band": False,
}

print("=" * 80)
print("MEAN REVERSION V2 BASELINE TEST - ETHUSDT 4h (Training Period)")
print("=" * 80)
print("Testing if mean reversion works better than trend following on ETH")
print("")

payload = {
    "strategy_name": "Mean Reversion V2",
    "dataset_id": 16,
    "start_time": "2020-01-01T00:00:00",
    "end_time": "2024-05-20T23:59:59",
    "parameters": baseline_params
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
    profit_factor = result.get('profit_factor', 0)

    # Calculate Calmar (训练期约4.4年)
    annual_return = return_pct / 4.4
    calmar = annual_return / abs(max_dd) if max_dd != 0 else 0

    print(f"✓ Completed ({elapsed:.1f}s)\n")
    print(f"  Job ID: {job_id}")
    print(f"  Return: {return_pct:.2f}%")
    print(f"  **Calmar: {calmar:.2f}** (PRIMARY)")
    print(f"  Max DD: {max_dd:.2f}%")
    print(f"  Sharpe: {sharpe:.2f}")
    print(f"  Win Rate: {win_rate:.2f}%")
    print(f"  Profit Factor: {profit_factor:.2f}")
    print(f"  Trades: {trades}")
    print(f"\n📊 http://localhost:3002/results/{job_id}")

    print("\n" + "=" * 80)
    print("ASSESSMENT")
    print("=" * 80)
    if calmar >= 1.0:
        print("✓ Mean reversion shows promise!")
        print(f"  Calmar {calmar:.2f} meets threshold")
        print("  → Proceed with optimization")
    elif calmar >= 0.5:
        print(f"⚠ Calmar {calmar:.2f} is below threshold but better than trend strategies")
        print("  → May work with optimization")
    else:
        print(f"✗ Calmar {calmar:.2f} - Mean reversion also struggles on ETH 4h")
        print("  → ETH 4h (2020-2024) may be unsuitable for mechanical strategies")
        print("  → Consider: different time range, different asset, or accept limitations")

else:
    print(f"✗ Failed: {response.text}")
