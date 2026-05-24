#!/usr/bin/env python3
"""V10 Iteration 9: Final push for >50% win rate"""
import requests
import time

API_URL = "http://localhost:8000/api/v1/backtest/run"

# Focus on win rate only
payload = {
    "strategy_name": "Trend Following V10",
    "dataset_id": 18,
    "start_time": "2022-01-01T00:00:00",
    "end_time": "2024-12-28T23:59:59",
    "parameters": {
        "trend_ema_period": 200,
        "fast_ema1": 16,
        "slow_ema1": 42,
        "fast_ema2": 21,
        "slow_ema2": 52,
        "rsi_long_entry_strict": 29,    # Slightly relaxed (29 vs 30)
        "rsi_long_entry_relaxed": 37,   # Slightly relaxed (37 vs 38)
        "rsi_short_entry_strict": 71,   # Slightly relaxed (71 vs 70)
        "rsi_short_entry_relaxed": 63,   # Slightly relaxed (63 vs 62)
        "rsi_long_exit": 65,             # Earlier exit (65 vs 66)
        "rsi_short_exit": 35,            # Earlier exit (35 vs 34)
        "atr_period": 14,
        "atr_stop_mult": 1.65,           # Slightly tighter
        "atr_trailing_mult": 3.1,
        "risk_pct": 1.0,
        "max_leverage": 1.0,
        "use_adx_filter": True,
        "adx_period": 14,
        "adx_threshold": 22,            # Back to iter 6 level
        "use_dynamic_stop": True,
        "dynamic_stop_threshold": 2.0,
    }
}

print("=" * 70)
print("V10 ITERATION #9: 最终冲刺（胜率>50%）")
print("=" * 70)
print("策略:")
print("  - 稍微放宽RSI入场（增加高质量机会）")
print("  - 更早退出（锁定利润）")
print("  - 收紧止损（减少大亏）")
print("")

start = time.time()
response = requests.post(API_URL, json=payload, timeout=300)
elapsed = time.time() - start

if response.status_code == 200:
    result = response.json()
    print(f"✓ 回测完成 ({elapsed:.1f}s)\n")

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

    print(f"\n{'='*70}")
    print("实盘标准检查:")
    print(f"{'='*70}")

    checks = {
        "Sharpe > 1.0": (sharpe > 1.0, f"{sharpe:.2f}"),
        "Return > 0%": (return_pct > 0, f"{return_pct:.2f}%"),
        "Max DD < 15%": (max_dd < 15, f"{max_dd:.2f}%"),
        "Win Rate > 50%": (win_rate > 50, f"{win_rate:.2f}%"),
        "Trades > 50": (trades > 50, str(trades))
    }

    all_pass = True
    for name, (passed, value) in checks.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"  {name:20s} {status:12s} ({value})")
        if not passed:
            all_pass = False

    print(f"{'='*70}")
    if all_pass:
        print("✓✓✓✓✓ 达到实盘标准！准备验证测试 ✓✓✓✓✓")
        print(f"{'='*70}")
        print("\n接下来进行验证期回测...")
        print(f"验证期: 2024-12-29 → 2026-04-10")
        print(f"训练期Job ID: {job_id}")
        # job_id: {job_id}
    else:
        print("✗✗✗ 未达标")
        failed = [name for name, (passed, _) in checks.items() if not passed]
        print(f"\n未达标指标: {', '.join(failed)}")
    print(f"{'='*70}")
else:
    print(f"✗ 失败: {response.text}")
