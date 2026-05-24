#!/usr/bin/env python3
"""Test V7 strategy on full dataset"""
import requests
import time

API_URL = "http://localhost:8000/api/v1/backtest/run"

# Test on training period first
payload = {
    "strategy_name": "Trend Breakthrough V7",
    "dataset_id": 18,
    "start_time": "2022-01-01T00:00:00",
    "end_time": "2024-12-28T23:59:59",
    "parameters": {}
}

print("=" * 70)
print("TESTING V7 STRATEGY: Training Period (2022-2024)")
print("=" * 70)

start = time.time()
response = requests.post(API_URL, json=payload, timeout=300)
elapsed = time.time() - start

if response.status_code == 200:
    result = response.json()
    print(f"\n✓ V7 Training backtest completed ({elapsed:.1f}s)")
    print(f"  Job ID: {result.get('backtest_job_id')}")
    print(f"  Total Return: {result.get('pnl_pct', 0):.2f}%")
    print(f"  Sharpe Ratio: {result.get('sharpe_ratio', 0):.2f}")
    print(f"  Max Drawdown: {result.get('max_drawdown', 0):.2f}%")
    print(f"  Win Rate: {result.get('win_rate', 0):.2f}%")
    print(f"  Total Trades: {result.get('total_trades', 0)}")

    # Check if it meets minimum criteria
    sharpe = result.get('sharpe_ratio', 0)
    return_pct = result.get('pnl_pct', 0)
    max_dd = result.get('max_drawdown', 100)
    win_rate = result.get('win_rate', 0)
    trades = result.get('total_trades', 0)

    print(f"\n实盘标准检查:")
    print(f"  ✓ Sharpe > 1.0: {'PASS' if sharpe > 1.0 else f'FAIL ({sharpe:.2f})'}")
    print(f"  ✓ Return > 0%: {'PASS' if return_pct > 0 else f'FAIL ({return_pct:.2f}%)'}")
    print(f"  ✓ Max DD < 15%: {'PASS' if max_dd < 15 else f'FAIL ({max_dd:.2f}%)'}")
    print(f"  ✓ Win Rate > 50%: {'PASS' if win_rate > 50 else f'FAIL ({win_rate:.2f}%)'}")
    print(f"  ✓ Trades > 50: {'PASS' if trades > 50 else f'FAIL ({trades})'}")

    all_pass = (sharpe > 1.0 and return_pct > 0 and max_dd < 15 and win_rate > 50 and trades > 50)
    print(f"\n总体评估: {'✓ 达到实盘基本标准' if all_pass else '✗ 未达到实盘标准，需要优化'}")
else:
    print(f"\n✗ Backtest failed: {response.text}")
