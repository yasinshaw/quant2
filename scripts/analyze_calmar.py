#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Analyze Calmar Ratios from previous iterations"""

# Calmar Ratio = Annual Return / |Max Drawdown|
# Assuming ~3 years of data (2022-2024)

iterations = {
    "Iter 9 (Job 168)": {"return": 29.09, "dd": 9.30, "trades": 48},
    "Iter 10 (Job 182)": {"return": 21.38, "dd": 12.99, "trades": 45},
    "Iter 11 (Job 183)": {"return": 13.15, "dd": 13.38, "trades": 47},
    "Iter 12 (Job 184)": {"return": 20.73, "dd": 11.53, "trades": 53},
    "Iter 13 (Job 185)": {"return": 16.73, "dd": 12.29, "trades": 59},
    "Iter 14 (Job 186)": {"return": 26.24, "dd": 5.64, "trades": 66},
    "Iter 15 (Job 187)": {"return": 15.33, "dd": 8.24, "trades": 73},
}

print("=" * 80)
print("V10 Strategy - Calmar Ratio Analysis (Primary Metric)")
print("=" * 80)
print(f"{'Iteration':<20} {'Return':<10} {'Max DD':<10} {'Calmar':<10} {'Trades':<10}")
print("-" * 80)

results = []
for name, data in iterations.items():
    annual_return = data["return"] / 3  # 3 years
    calmar = annual_return / data["dd"]
    results.append((name, data["return"], data["dd"], calmar, data["trades"]))
    print(f"{name:<20} {data['return']:>6.2f}%    {data['dd']:>6.2f}%    {calmar:>6.2f}     {data['trades']:>4}")

print("-" * 80)

# Sort by Calmar
results.sort(key=lambda x: x[3], reverse=True)

print("\n🏆 TOP 3 by Calmar Ratio:")
print("=" * 80)
for i, (name, ret, dd, calmar, trades) in enumerate(results[:3], 1):
    print(f"{i}. {name}")
    print(f"   Return: {ret:.2f}%, Max DD: {dd:.2f}%, Calmar: {calmar:.2f}, Trades: {trades}")

best = results[0]
print("\n" + "=" * 80)
print(f"✓✓✓ BEST: {best[0]}")
print(f"   Calmar Ratio: {best[3]:.2f} (Target: >2.0 excellent, 1.5-2.0 good)")
print(f"   Annual Return: {best[1]/3:.2f}%")
print(f"   Max Drawdown: {best[2]:.2f}%")
print("=" * 80)

# Iteration 14 parameters
print("\n📊 Iteration 14 Parameters (Best Calmar):")
print("-" * 40)
print("trend_ema_period: 200")
print("fast_ema1: 14, slow_ema1: 40")
print("fast_ema2: 20, slow_ema2: 50")
print("rsi_long_entry_strict: 30, relaxed: 38")
print("rsi_short_entry_strict: 70, relaxed: 62")
print("rsi_long_exit: 63, short_exit: 37")
print("atr_stop_mult: 1.7, trailing_mult: 3.0")
print("risk_pct: 1.0%")
print("adx_threshold: 22")
