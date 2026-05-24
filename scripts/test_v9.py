#!/usr/bin/env python3
"""Test V9 strategy - Iteration 5"""
import requests
import time

API_URL = "http://localhost:8000/api/v1/backtest/run"

payload = {
    "strategy_name": "Trend Following V9",
    "dataset_id": 18,
    "start_time": "2022-01-01T00:00:00",
    "end_time": "2024-12-28T23:59:59",
    "parameters": {}
}

print("=" * 70)
print("V9 STRATEGY TEST: MACD + BB + RSI (更灵活的趋势判断)")
print("=" * 70)

start = time.time()
response = requests.post(API_URL, json=payload, timeout=300)
elapsed = time.time() - start

if response.status_code == 200:
    result = response.json()
    print(f"\n✓ 回测完成 ({elapsed:.1f}s)")
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

    print(f"\n实盘标准检查:")
    print(f"  Sharpe > 1.0: {'✓ PASS' if sharpe > 1.0 else f'✗ FAIL ({sharpe:.2f})'}")
    print(f"  Return > 0%: {'✓ PASS' if return_pct > 0 else f'✗ FAIL ({return_pct:.2f}%)'}")
    print(f"  Max DD < 15%: {'✓ PASS' if max_dd < 15 else f'✗ FAIL ({max_dd:.2f}%)'}")
    print(f"  Win Rate > 50%: {'✓ PASS' if win_rate > 50 else f'✗ FAIL ({win_rate:.2f}%)'}")
    print(f"  Trades > 50: {'✓ PASS' if trades > 50 else f'✗ FAIL ({trades})'}")

    all_pass = (sharpe > 1.0 and return_pct > 0 and max_dd < 15 and win_rate > 50 and trades > 50)
    print(f"\n{'='*70}")
    if all_pass:
        print("✓✓✓ V9策略达到实盘标准！可以进入验证阶段 ✓✓✓")
    else:
        print("✗✗✗ V9策略未达到实盘标准，继续优化 ✗✗✗")
    print(f"{'='*70}")
else:
    print(f"\n✗ 失败: {response.text}")
