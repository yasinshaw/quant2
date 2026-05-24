#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""V10 Iteration 11: Focus on Sharpe and Trades"""
import requests
import time

API_URL = "http://localhost:8000/api/v1/backtest/run"

# Based on iteration 9, make minimal changes
payload = {
    "strategy_name": "Trend Following V10",
    "dataset_id": 18,
    "start_time": "2022-01-01T00:00:00",
    "end_time": "2024-12-28T23:59:59",
    "parameters": {
        "trend_ema_period": 200,       # Keep same
        "fast_ema1": 15,               # Keep same
        "slow_ema1": 42,               # Keep same
        "fast_ema2": 21,               # Keep same
        "slow_ema2": 52,               # Keep same
        "rsi_long_entry_strict": 28,   # Slightly relaxed (28 vs 29)
        "rsi_long_entry_relaxed": 36,  # Slightly relaxed (36 vs 37)
        "rsi_short_entry_strict": 72,  # Slightly relaxed (72 vs 71)
        "rsi_short_entry_relaxed": 64,  # Keep same
        "rsi_long_exit": 65,            # Slightly later (65 vs 64)
        "rsi_short_exit": 35,           # Slightly later (35 vs 36)
        "atr_period": 14,
        "atr_stop_mult": 1.6,           # Tighter stops (1.6 vs 1.65)
        "atr_trailing_mult": 3.1,
        "risk_pct": 1.0,                # Keep same
        "max_leverage": 1.0,
        "use_adx_filter": True,
        "adx_period": 14,
        "adx_threshold": 21,            # Slightly lower (21 vs 22)
        "use_dynamic_stop": True,
        "dynamic_stop_threshold": 2.0,
    }
}

print("=" * 70)
print("V10 ITERATION #11: Focus on Sharpe and Trades (based on iter9)")
print("=" * 70)
print("Changes from iteration 9:")
print("  - Relax RSI entry: 28/36 vs 29/37 (long)")
print("  - Relax RSI entry: 72/64 vs 71/63 (short)")
print("  - Later RSI exit: 65/35 vs 64/36")
print("  - Tighter stop: 1.6x vs 1.65x")
print("  - Lower ADX: 21 vs 22")
print("")

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

    print(f"\nCompared to iteration 9:")
    print(f"  Return:  {return_pct:.2f}% vs 29.09% ({return_pct-29.09:+.2f}%)")
    print(f"  Sharpe:  {sharpe:.2f} vs 0.95 ({sharpe-0.95:+.2f})")
    print(f"  Max DD:  {max_dd:.2f}% vs 9.30% ({max_dd-9.30:+.2f}%)")
    print(f"  Win Rate: {win_rate:.2f}% vs 50.00% ({win_rate-50.00:+.2f}%)")
    print(f"  Trades:  {trades} vs 48 ({trades-48:+d})")

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
        gaps = []
        if sharpe <= 1.0:
            gaps.append(f"Sharpe: need +{1.0-sharpe:.2f}")
        if win_rate <= 50:
            gaps.append(f"Win Rate: need +{50-win_rate:.2f}%")
        if trades <= 50:
            gaps.append(f"Trades: need +{50-trades}")
        if gaps:
            print(f"Gaps: {', '.join(gaps)}")
    print(f"{'='*70}")
else:
    print(f"✗ Failed: {response.text}")
