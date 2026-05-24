#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""V10 Iteration 10: Balanced approach for all criteria"""
import requests
import time

API_URL = "http://localhost:8000/api/v1/backtest/run"

# Balance all metrics
payload = {
    "strategy_name": "Trend Following V10",
    "dataset_id": 18,
    "start_time": "2022-01-01T00:00:00",
    "end_time": "2024-12-28T23:59:59",
    "parameters": {
        "trend_ema_period": 190,       # Slightly shorter (190 vs 200)
        "fast_ema1": 14,               # Faster for more signals
        "slow_ema1": 38,               # Faster
        "fast_ema2": 19,
        "slow_ema2": 48,
        "rsi_long_entry_strict": 29,
        "rsi_long_entry_relaxed": 36,
        "rsi_short_entry_strict": 71,
        "rsi_short_entry_relaxed": 64,
        "rsi_long_exit": 64,           # Earlier exit
        "rsi_short_exit": 36,
        "atr_period": 14,
        "atr_stop_mult": 1.7,
        "atr_trailing_mult": 3.0,
        "risk_pct": 1.1,               # Slightly more risk
        "max_leverage": 1.0,
        "use_adx_filter": True,
        "adx_period": 14,
        "adx_threshold": 21,           # Slightly lower
        "use_dynamic_stop": True,
        "dynamic_stop_threshold": 2.0,
    }
}

print("=" * 70)
print("V10 ITERATION #10: Balanced for all criteria")
print("=" * 70)

start = time.time()
response = requests.post(API_URL, json=payload, timeout=300)
elapsed = time.time() - start

if response.status_code == 200:
    result = response.json()
    print(f"✓ Backtest completed ({elapsed:.1f}s)\n")

    job_id = result.get('backtest_job_id')
    return_pct = result.get('pnl_pct', 0)
    sharpe = result.get('sharpe_ratio', 0)
    max_dd = result.get('max_drawdown', 100)
    win_rate = result.get('win_rate', 0)
    trades = result.get('total_trades', 0)

    print(f"  Job ID: {job_id}")
    print(f"  Return: {return_pct:.2f}%")
    print(f"  Sharpe: {sharpe:.2f}")
    print(f"  Max DD: {max_dd:.2f}%")
    print(f"  Win Rate: {win_rate:.2f}%")
    print(f"  Trades: {trades}")

    print(f"\n{'='*70}")
    print("Live Trading Criteria Check:")
    print(f"{'='*70}")

    checks = [
        ("Sharpe > 1.0", sharpe > 1.0, f"{sharpe:.2f}"),
        ("Return > 0%", return_pct > 0, f"{return_pct:.2f}%"),
        ("Max DD < 15%", max_dd < 15, f"{max_dd:.2f}%"),
        ("Win Rate > 50%", win_rate > 50, f"{win_rate:.2f}%"),
        ("Trades > 50", trades > 50, str(trades))
    ]

    all_pass = all(check[1] for check in checks)

    for name, passed, value in checks:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"  {status:12s} {name:20s} ({value})")

    print(f"{'='*70}")
    if all_pass:
        print("\n✓✓✓✓✓✓✓✓✓✓✓✓✓✓✓✓✓✓✓✓✓✓✓✓✓✓✓✓✓✓✓✓✓✓✓✓✓✓✓✓✓✓✓")
        print("        Strategy meets live trading standards!")
        print("✓✓✓✓✓✓✓✓✓✓✓✓✓✓✓✓✓✓✓✓✓✓✓✓✓✓✓✓✓✓✓✓✓✓✓✓✓✓✓✓✓✓✓")
        print(f"\nNext step: Run validation period backtest")
        print(f"Validation period: 2024-12-29 → 2026-04-10")
        print(f"Training Job ID: {job_id}")
    else:
        print("✗✗✗ Strategy does not meet all criteria")
        failed = [name for name, passed, _ in checks if not passed]
        print(f"\nFailed criteria: {', '.join(failed)}")
    print(f"{'='*70}")
else:
    print(f"✗ Failed: {response.text}")
