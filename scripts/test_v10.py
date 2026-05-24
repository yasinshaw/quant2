#!/usr/bin/env python3
"""Test V10 strategy - Iteration 6"""
import requests
import time

API_URL = "http://localhost:8000/api/v1/backtest/run"

payload = {
    "strategy_name": "Trend Following V10",
    "dataset_id": 18,
    "start_time": "2022-01-01T00:00:00",
    "end_time": "2024-12-28T23:59:59",
    "parameters": {}
}

print("=" * 70)
print("V10 STRATEGY TEST: 基于V8成功配置 + 双EMA系统")
print("=" * 70)
print("目标: 保持高质量的同时增加交易次数")
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

    print(f"\n{'='*70}")
    print("实盘标准检查:")
    print(f"{'='*70}")
    print(f"  Sharpe > 1.0:      {'✓ PASS' if sharpe > 1.0 else '✗ FAIL'} ({sharpe:.2f})")
    print(f"  Return > 0%:       {'✓ PASS' if return_pct > 0 else '✗ FAIL'} ({return_pct:.2f}%)")
    print(f"  Max DD < 15%:      {'✓ PASS' if max_dd < 15 else '✗ FAIL'} ({max_dd:.2f}%)")
    print(f"  Win Rate > 50%:    {'✓ PASS' if win_rate > 50 else '✗ FAIL'} ({win_rate:.2f}%)")
    print(f"  Trades > 50:       {'✓ PASS' if trades > 50 else '✗ FAIL'} ({trades})")

    all_pass = all([
        sharpe > 1.0,
        return_pct > 0,
        max_dd < 15,
        win_rate > 50,
        trades > 50
    ])

    print(f"\n{'='*70}")
    if all_pass:
        print("✓✓✓ V10策略达到实盘标准！进行验证测试 ✓✓✓")
    else:
        print("✗✗✗ V10策略未达到实盘标准")
        print("\n需要改进的指标:")
        if sharpe <= 1.0:
            print(f"  - Sharpe: {sharpe:.2f} → 需要 > 1.0")
        if return_pct <= 0:
            print(f"  - Return: {return_pct:.2f}% → 需要 > 0%")
        if max_dd >= 15:
            print(f"  - Max DD: {max_dd:.2f}% → 需要 < 15%")
        if win_rate <= 50:
            print(f"  - Win Rate: {win_rate:.2f}% → 需要 > 50%")
        if trades <= 50:
            print(f"  - Trades: {trades} → 需要 > 50")
    print(f"{'='*70}")
else:
    print(f"✗ 失败: {response.text}")
