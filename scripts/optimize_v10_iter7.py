#!/usr/bin/env python3
"""V10 Iteration 7: Focus on Sharpe and Win Rate"""
import requests
import time

API_URL = "http://localhost:8000/api/v1/backtest/run"

# Optimized for higher Sharpe and Win Rate
payload = {
    "strategy_name": "Trend Following V10",
    "dataset_id": 18,
    "start_time": "2022-01-01T00:00:00",
    "end_time": "2024-12-28T23:59:59",
    "parameters": {
        "trend_ema_period": 200,
        "fast_ema1": 15,
        "slow_ema1": 40,
        "fast_ema2": 20,
        "slow_ema2": 50,
        "rsi_long_entry_strict": 28,    # 更严格
        "rsi_long_entry_relaxed": 35,   # 更严格
        "rsi_short_entry_strict": 72,   # 更严格
        "rsi_short_entry_relaxed": 65,   # 更严格
        "rsi_long_exit": 65,             # 更早退出
        "rsi_short_exit": 35,            # 更早退出
        "atr_period": 14,
        "atr_stop_mult": 1.6,            # 收紧止损
        "atr_trailing_mult": 3.2,
        "risk_pct": 1.0,
        "max_leverage": 1.0,
        "use_adx_filter": True,
        "adx_period": 14,
        "adx_threshold": 24,            # 更高ADX
        "use_dynamic_stop": True,
        "dynamic_stop_threshold": 2.0,
    }
}

print("=" * 70)
print("V10 ITERATION #7: 提升Sharpe和胜率")
print("=" * 70)
print("优化:")
print("  - RSI更严格: (28/35) vs (30/38) for long")
print("  - RSI更严格: (72/65) vs (70/62) for short")
print("  - 更早退出: (65/35) vs (68/32)")
print("  - 收紧止损: 1.6x vs 1.8x")
print("  - 更高ADX: 24 vs 22")
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

    # Compare with iteration 6
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
    else:
        print("✗✗✗ 未达标")
        if sharpe <= 1.0:
            print(f"  - Sharpe: {sharpe:.2f} (需要 > 1.0)")
        if win_rate <= 50:
            print(f"  - Win Rate: {win_rate:.2f}% (需要 > 50%)")
    print(f"{'='*70}")
else:
    print(f"✗ 失败: {response.text}")
