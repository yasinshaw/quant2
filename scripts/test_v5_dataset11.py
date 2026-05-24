#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""V5 Test on Dataset 11 (2022-12-31 → 2026-01-01) - Verify Success"""
import requests
import time

API_URL = "http://localhost:8000/api/v1/backtest/run"

# V5原始成功参数
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
print("V5 TEST - Dataset 11 (2022-12-31 → 2026-01-01)")
print("=" * 80)
print("Using same dataset and time range as successful job 158")
print("")

# 测试完整时间段
payload = {
    "strategy_name": "Trend Pullback V5",
    "dataset_id": 11,
    "start_time": "2022-12-31T16:00:00",
    "end_time": "2026-01-01T00:00:00",
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

    # Calculate Calmar (3年数据)
    annual_return = return_pct / 3.0
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
    print("COMPARISON WITH JOB 158")
    print("=" * 80)
    print("Job 158 (Expected): Return +52.8%, Calmar ~3.61, Sharpe 0.87, DD 14.6%")
    print(f"Current Test:       Return {return_pct:.2f}%, Calmar {calmar:.2f}, Sharpe {sharpe:.2f}, DD {max_dd:.2f}%")
    print("")

    if abs(return_pct - 52.8) < 5 and abs(calmar - 3.61) < 0.5:
        print("✓ Results match job 158!")
        print("  → V5 is validated on dataset 11")
        print("  → Should use 70/30 split on dataset 11 for optimization")
    else:
        print("⚠ Results differ from job 158")
        print("  → May need to investigate further")

else:
    print(f"✗ Failed: {response.text}")
