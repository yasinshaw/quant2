#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""V10 Iteration 15: Fine-tune for Sharpe and Win Rate"""
import requests
import time

API_URL = "http://localhost:8000/api/v1/backtest/run"

# Based on iter14, slightly more conservative entries
payload = {
    "strategy_name": "Trend Following V10",
    "dataset_id": 18,
    "start_time": "2022-01-01T00:00:00",
    "end_time": "2024-12-28T23:59:59",
    "parameters": {
        "trend_ema_period": 200,
        "fast_ema1": 14,
        "slow_ema1": 40,
        "fast_ema2": 20,
        "slow_ema2": 50,
        "rsi_long_entry_strict": 31,   # Slightly stricter
        "rsi_long_entry_relaxed": 39,   # Slightly stricter
        "rsi_short_entry_strict": 69,   # Slightly stricter
        "rsi_short_entry_relaxed": 61,   # Slightly stricter
        "rsi_long_exit": 63,
        "rsi_short_exit": 37,
        "atr_period": 14,
        "atr_stop_mult": 1.7,
        "atr_trailing_mult": 3.0,
        "risk_pct": 1.0,
        "max_leverage": 1.0,
        "use_adx_filter": True,
        "adx_period": 14,
        "adx_threshold": 23,            # Slightly higher
        "use_dynamic_stop": True,
        "dynamic_stop_threshold": 2.0,
    }
}

print("=" * 70)
print("V10 ITERATION #15: Fine-tune for Sharpe and Win Rate")
print("=" * 70)
print("Changes from iteration 14:")
print("  - Stricter RSI entry: 31/39 vs 30/38 (long)")
print("  - Stricter RSI entry: 69/61 vs 70/62 (short)")
print("  - Higher ADX: 23 vs 22")
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

    print(f"\nCompared to iteration 14:")
    print(f"  Return:  {return_pct:.2f}% vs 26.24% ({return_pct-26.24:+.2f}%)")
    print(f"  Sharpe:  {sharpe:.2f} vs 0.85 ({sharpe-0.85:+.2f})")
    print(f"  Max DD:  {max_dd:.2f}% vs 5.64% ({max_dd-5.64:+.2f}%)")
    print(f"  Win Rate: {win_rate:.2f}% vs 48.48% ({win_rate-48.48:+.2f}%)")
    print(f"  Trades:  {trades} vs 66 ({trades-66:+d})")

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
        if sharpe < 1.0:
            print(f"  - Sharpe gap: {1.0-sharpe:.2f}")
        if win_rate < 50:
            print(f"  - Win Rate gap: {50-win_rate:.2f}%")
    print(f"{'='*70}")
else:
    print(f"✗ Failed: {response.text}")
