#!/usr/bin/env python3
"""V8 Iteration 3: Balance quality and quantity"""
import requests
import time

API_URL = "http://localhost:8000/api/v1/backtest/run"

# Balance: slightly relaxed to get more trades
payload = {
    "strategy_name": "Trend Following V8",
    "dataset_id": 18,
    "start_time": "2022-01-01T00:00:00",
    "end_time": "2024-12-28T23:59:59",
    "parameters": {
        "trend_ema_period": 200,
        "fast_ema": 18,              # Faster signal
        "slow_ema": 45,              # Faster signal
        "rsi_long_entry": 32,        # Slightly relaxed
        "rsi_short_entry": 68,       # Slightly relaxed
        "rsi_long_exit": 68,         # Earlier exit
        "rsi_short_exit": 32,        # Earlier exit
        "atr_period": 14,
        "atr_stop_mult": 1.7,
        "atr_trailing_mult": 2.8,
        "risk_pct": 1.2,             # Slightly more risk
        "max_leverage": 1.0,
        "use_adx_filter": True,
        "adx_period": 14,
        "adx_threshold": 20          # Slightly lower
    }
}

print("=" * 70)
print("V8 ITERATION #3: 平衡质量和数量")
print("=" * 70)
print("调整:")
print("  - 更快的EMA (18/45 vs 20/50)")
print("  - RSI略微放宽 (32/68 vs 30/70)")
print("  - ADX降低 (20 vs 22)")
print("  - 更早退出 (68/32 vs 70/30)")
print("")

start = time.time()
response = requests.post(API_URL, json=payload, timeout=300)
elapsed = time.time() - start

if response.status_code == 200:
    result = response.json()
    print(f"✓ 回测完成 ({elapsed:.1f}s)")
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

    print(f"\n实盘标准:")
    print(f"  Sharpe > 1.0: {'✓' if sharpe > 1.0 else '✗'} ({sharpe:.2f})")
    print(f"  Return > 0%: {'✓' if return_pct > 0 else '✗'} ({return_pct:.2f}%)")
    print(f"  Max DD < 15%: {'✓' if max_dd < 15 else '✗'} ({max_dd:.2f}%)")
    print(f"  Win Rate > 50%: {'✓' if win_rate > 50 else '✗'} ({win_rate:.2f}%)")
    print(f"  Trades > 50: {'✓' if trades > 50 else '✗'} ({trades})")

    all_pass = (sharpe > 1.0 and return_pct > 0 and max_dd < 15 and win_rate > 50 and trades > 50)
    print(f"\n{'✓✓✓ 达标！' if all_pass else '✗✗✗ 未达标'}")

    if not all_pass:
        print("\n下一步调整:")
        if trades <= 50:
            print("  - 需要增加交易次数（放宽条件）")
        if sharpe < 1.0:
            print("  - 需要提高Sharpe（优化盈亏比）")
        if win_rate < 50:
            print("  - 需要提高胜率（更严格入场）")
else:
    print(f"✗ 失败: {response.text}")
