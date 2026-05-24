#!/usr/bin/env python3
"""V8 Iteration 2: Stricter entry conditions"""
import requests
import time

API_URL = "http://localhost:8000/api/v1/backtest/run"

# Optimized parameters: more selective entries
payload = {
    "strategy_name": "Trend Following V8",
    "dataset_id": 18,
    "start_time": "2022-01-01T00:00:00",
    "end_time": "2024-12-28T23:59:59",
    "parameters": {
        "trend_ema_period": 200,
        "fast_ema": 20,
        "slow_ema": 50,
        "rsi_long_entry": 30,    # Lower = more oversold (higher quality)
        "rsi_short_entry": 70,   # Higher = more overbought
        "rsi_long_exit": 70,
        "rsi_short_exit": 30,
        "atr_period": 14,
        "atr_stop_mult": 1.8,    # Tighter stop
        "atr_trailing_mult": 3.0, # Wider trailing (let profits run)
        "risk_pct": 1.0,
        "max_leverage": 1.0,
        "use_adx_filter": True,
        "adx_period": 14,
        "adx_threshold": 22      # Higher ADX requirement
    }
}

print("=" * 70)
print("V8 ITERATION #2: 更严格的入场条件")
print("=" * 70)
print("优化点:")
print("  - RSI入场阈值更严格 (30/70 vs 35/65)")
print("  - ADX阈值提高 (22 vs 20)")
print("  - 止损收紧 (1.8x vs 2.0x)")
print("  - 移动止损放宽 (3.0x vs 2.5x)")
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
else:
    print(f"✗ 失败: {response.text}")
