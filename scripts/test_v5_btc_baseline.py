#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""V5 Baseline Test on BTCUSDT 4h - Verify Original Success"""
import requests
import time

API_URL = "http://localhost:8000/api/v1/backtest/run"

# V5原始成功参数（从memory）
baseline_params = {
    "ema_fast": 24,
    "ema_slow": 85,
    "rsi_period": 21,
    "pullback_threshold": 40,
    "rsi_exit_long": 71,
    "rsi_exit_short": 27,
    "atr_stop_mult": 1.5,
    "risk_pct": 1.5,
    "adx_threshold": 10,
    "vol_scale_threshold": 1.5,
    "vol_scale_factor": 0.5,
    "cb_max_losses": 3,
    "cb_cooldown": 6,
    "macro_ema_period": 200,
    "dd_throttle_start": 10.0,
    "dd_throttle_max": 20.0,
}

print("=" * 80)
print("V5 BASELINE TEST - BTCUSDT 4h (Training Period)")
print("=" * 80)
print("Verifying if V5 actually works on BTC 4h data")
print("")

payload = {
    "strategy_name": "Trend Pullback V5",
    "dataset_id": 19,  # BTCUSDT 4h
    "start_time": "2020-01-01T00:00:00",
    "end_time": "2024-05-20T23:59:59",  # Same 70% training period
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
    print(f"  Trades: {trades}")
    print(f"\n📊 http://localhost:3002/results/{job_id}")

    print("\n" + "=" * 80)
    print("COMPARISON")
    print("=" * 80)
    print(f"BTC 4h: Calmar {calmar:.2f}")
    print(f"ETH 4h: Calmar 0.04 (from earlier test)")
    print(f"Difference: {calmar - 0.04:.2f}")
    print("")

    if calmar >= 1.0:
        print("✓ V5 works on BTC 4h!")
        print("  → V5 strategy is valid, but ETH requires different approach")
    else:
        print("✗ V5 also fails on BTC 4h!")
        print("  → Memory may be outdated, or parameters need re-tuning")

else:
    print(f"✗ Failed: {response.text}")
