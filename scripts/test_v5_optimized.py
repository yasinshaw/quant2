#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""V5 Manual Test with Optimized Parameters"""
import requests
import time

API_URL = "http://localhost:8000/api/v1/backtest/run"

# 贝叶斯优化最佳参数（取整）
optimized_params = {
    "ema_fast": 22,
    "ema_slow": 99,
    "rsi_period": 19,
    "pullback_threshold": 41,
    "rsi_exit_long": 67,
    "rsi_exit_short": 25,
    "atr_stop_mult": 1.25,
    "risk_pct": 1.9,
    "adx_threshold": 21,
    "vol_scale_threshold": 1.6,
    "cb_max_losses": 4,
    "cb_cooldown": 6,
    "macro_ema_period": 188,
    "dd_throttle_start": 9,
    "dd_throttle_max": 20,
}

print("=" * 80)
print("V5 TEST - Optimized Parameters (Training Period)")
print("=" * 80)
print("")

payload = {
    "strategy_name": "Trend Pullback V5",
    "dataset_id": 16,  # ETH 4h
    "start_time": "2020-01-01T00:00:00",
    "end_time": "2024-05-20T23:59:59",
    "parameters": optimized_params
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

else:
    print(f"✗ Failed: {response.text}")
