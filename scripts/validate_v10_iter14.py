#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""V10 Iteration 14 - Validation Period Backtest"""
import requests
import time

API_URL = "http://localhost:8000/api/v1/backtest/run"

# Iteration 14 parameters (best Calmar ratio: 1.55)
payload = {
    "strategy_name": "Trend Following V10",
    "dataset_id": 18,
    "start_time": "2024-12-29T00:00:00",  # Validation period start
    "end_time": "2026-04-10T23:59:59",    # Current date
    "parameters": {
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
        "atr_period": 14,
        "atr_stop_mult": 1.7,
        "atr_trailing_mult": 3.0,
        "risk_pct": 1.0,
        "max_leverage": 1.0,
        "use_adx_filter": True,
        "adx_period": 14,
        "adx_threshold": 22,
        "use_dynamic_stop": True,
        "dynamic_stop_threshold": 2.0,
    }
}

print("=" * 80)
print("V10 ITERATION 14 - VALIDATION PERIOD BACKTEST")
print("=" * 80)
print("Training Period: 2022-01-01 → 2024-12-28")
print("Validation Period: 2024-12-29 → 2026-04-10")
print("")
print("Training Results:")
print("  Return: 26.24% (3 years)")
print("  Calmar Ratio: 1.55 ✓✓✓ (GOOD)")
print("  Max DD: 5.64%")
print("  Trades: 66")
print("")
print("=" * 80)
print("Running validation backtest...")
print("=" * 80)
print("")

start = time.time()
response = requests.post(API_URL, json=payload, timeout=300)
elapsed = time.time() - start

if response.status_code == 200:
    result = response.json()
    print(f"✓ Validation backtest completed ({elapsed:.1f}s)\n")

    job_id = result.get('backtest_job_id')
    return_pct = result.get('pnl_pct', 0)
    sharpe = result.get('sharpe_ratio', 0)
    max_dd = result.get('max_drawdown', 100)
    win_rate = result.get('win_rate', 0)
    trades = result.get('total_trades', 0)

    # Calculate Calmar (validation period is ~1.3 years)
    from datetime import datetime
    start_date = datetime(2024, 12, 29)
    end_date = datetime(2026, 4, 10)
    validation_days = (end_date - start_date).days
    validation_years = validation_days / 365.25
    annual_return = return_pct / validation_years
    calmar = annual_return / abs(max_dd) if max_dd != 0 else 0

    print(f"  Job ID: {job_id}")
    print(f"  Return: {return_pct:.2f}%")
    print(f"  Sharpe: {sharpe:.2f}")
    print(f"  Max DD: {max_dd:.2f}%")
    print(f"  Win Rate: {win_rate:.2f}%")
    print(f"  Trades: {trades}")
    print(f"  **Calmar Ratio: {calmar:.2f}** (PRIMARY METRIC)")

    print(f"\n{'='*80}")
    print("TRAINING vs VALIDATION COMPARISON:")
    print(f"{'='*80}")
    print(f"{'Metric':<25} {'Training':<20} {'Validation':<20} {'Change':<15}")
    print("-" * 80)
    print(f"{'Calmar Ratio':<25} {'1.55':<20} {f'{calmar:.2f}':<20} {f'{(calmar-1.55)/1.55*100:+.1f}%':<15}")
    print(f"{'Return':<25} {'26.24%':<20} {f'{return_pct:.2f}%':<20} {f'({return_pct-26.24:+.2f}%)':<15}")
    print(f"{'Max DD':<25} {'5.64%':<20} {f'{max_dd:.2f}%':<20} {f'({max_dd-5.64:+.2f}%)':<15}")
    print(f"{'Trades':<25} {'66':<20} {f'{trades}':<20} {f'({trades-66:+d})':<15}")

    print(f"\n{'='*80}")
    print("OVERFITTING CHECK:")
    print(f"{'='*80}")

    # Check for overfitting
    calmar_drop = (1.55 - calmar) / 1.55 if calmar < 1.55 else 0
    dd_increase = (max_dd - 5.64) / 5.64 if max_dd > 5.64 else 0

    checks = []
    if calmar_drop > 0.5:
        checks.append(("✗ FAIL", f"Calmar dropped {calmar_drop*100:.1f}% (>50% threshold)"))
    else:
        checks.append(("✓ PASS", f"Calmar stable (dropped {calmar_drop*100:.1f}%)"))

    if dd_increase > 1.0:
        checks.append(("✗ FAIL", f"Max DD increased {dd_increase*100:.1f}% (>100% threshold)"))
    else:
        checks.append(("✓ PASS", f"Max DD controlled (increased {dd_increase*100:.1f}%)"))

    if trades < 10:
        checks.append(("✗ FAIL", f"Insufficient trades ({trades} < 10)"))
    else:
        checks.append(("✓ PASS", f"Sufficient trades ({trades})"))

    for status, msg in checks:
        print(f"  {status}: {msg}")

    print(f"\n{'='*80}")
    if all("PASS" in check[0] for check in checks):
        print("✓✓✓✓✓✓✓✓✓✓✓✓✓✓✓✓✓✓✓✓✓✓✓✓✓✓✓✓✓✓✓✓✓✓✓✓✓✓✓✓✓✓")
        print("           STRATEGY IS ROBUST - READY FOR LIVE TRADING!")
        print("✓✓✓✓✓✓✓✓✓✓✓✓✓✓✓✓✓✓✓✓✓✓✓✓✓✓✓✓✓✓✓✓✓✓✓✓✓✓✓✓✓✓✓")
    else:
        print("⚠️  STRATEGY MAY BE OVERFIT - CAUTION ADVISED")
    print(f"{'='*80}")

    print(f"\n📊 View Results:")
    print(f"   http://localhost:3002/results/{job_id}")

else:
    print(f"✗ Failed: {response.text}")
