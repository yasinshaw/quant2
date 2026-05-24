#!/usr/bin/env python3
"""V10 Iteration 8: Subtle optimization for Sharpe"""
import requests
import time

API_URL = "http://localhost:8000/api/v1/backtest/run"

# Back to iteration 6 base, with only subtle changes
payload = {
    "strategy_name": "Trend Following V10",
    "dataset_id": 18,
    "start_time": "2022-01-01T00:00:00",
    "end_time": "2024-12-28T23:59:59",
    "parameters": {
        "trend_ema_period": 200,
        "fast_ema1": 16,               # Slightly slower (16 vs 15)
        "slow_ema1": 42,               # Slightly slower (42 vs 40)
        "fast_ema2": 21,               # Slightly slower
        "slow_ema2": 52,               # Slightly slower
        "rsi_long_entry_strict": 30,   # Back to iter 6
        "rsi_long_entry_relaxed": 38,
        "rsi_short_entry_strict": 70,
        "rsi_short_entry_relaxed": 62,
        "rsi_long_exit": 66,           # Slightly earlier (66 vs 68)
        "rsi_short_exit": 34,          # Slightly earlier (34 vs 32)
        "atr_period": 14,
        "atr_stop_mult": 1.7,          # Slightly tighter (1.7 vs 1.8)
        "atr_trailing_mult": 3.0,
        "risk_pct": 1.0,
        "max_leverage": 1.0,
        "use_adx_filter": True,
        "adx_period": 14,
        "adx_threshold": 23,          # Slightly higher (23 vs 22)
        "use_dynamic_stop": True,
        "dynamic_stop_threshold": 2.0,
    }
}

print("=" * 70)
print("V10 ITERATION #8: 微调优化（基于迭代6）")
print("=" * 70)
print("微调:")
print("  - EMA稍慢: (16/42, 21/52) vs (15/40, 20/50)")
print("  - 更早止盈: (66/34) vs (68/32)")
print("  - 止损稍紧: 1.7x vs 1.8x")
print("  - ADX稍高: 23 vs 22")
print("")

start = time.time()
response = requests.post(API_URL, json=payload, timeout=300)
elapsed = time.time() - start

if response.status_code == 200:
    result = response.json()
    print(f"✓ 回测完成 ({elapsed:.1f}s)\n")
    print(f"  Job ID: {result.get('backtest_job_id')}")
    print(f"  Return: {result.get('pnl_pct', 0):.2f}%")
    print(f"  Sharpe: {result.get('sharpe_ratio', 0):.2f}")
    print(f"  Max DD: {result.get('max_drawdown', 0):.2f}%")
    print(f"  Win Rate: {result.get('win_rate', 0):.2f}%")
    print(f"  Trades: {result.get('total_trades', 0)}")

    sharpe = result.get('sharpe_ratio', 0)
    return_pct = result.get('pnl_pct', 0)
    max_dd = result.get('max_drawdown', 100)
    win_rate = result.get('win_rate', 0)
    trades = result.get('total_trades', 0)

    print(f"\n与迭代6对比:")
    print(f"  Return:  {return_pct:.2f}% vs 26.93% ({return_pct-26.93:+.2f}%)")
    print(f"  Sharpe:  {sharpe:.2f} vs 0.79 ({sharpe-0.79:+.2f})")
    print(f"  Max DD:  {max_dd:.2f}% vs 7.33% ({max_dd-7.33:+.2f}%)")
    print(f"  Win Rate: {win_rate:.2f}% vs 47.69% ({win_rate-47.69:+.2f}%)")
    print(f"  Trades:  {trades} vs 65 ({trades-65:+d})")

    print(f"\n{'='*70}")
    all_pass = all([sharpe > 1.0, return_pct > 0, max_dd < 15, win_rate > 50, trades > 50])
    if all_pass:
        print("✓✓✓ 达到实盘标准！准备验证测试 ✓✓✓")
        print(f"{'='*70}")
        print("\n下一步:")
        print("  1. 运行验证期回测（2024-12-28 → 2026-04-10）")
        print("  2. 如果验证期也达标，策略可用于实盘！")
    else:
        print("✗✗✗ 未达标")
        if sharpe <= 1.0:
            print(f"  - Sharpe: {sharpe:.2f} (差距: {1.0-sharpe:.2f})")
        if win_rate <= 50:
            print(f"  - Win Rate: {win_rate:.2f}% (差距: {50-win_rate:.2f}%)")
    print(f"{'='*70}")
else:
    print(f"✗ 失败: {response.text}")
