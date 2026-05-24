#!/usr/bin/env python3
"""
测试多线程是否能加速Backtrader

关键测试：Backtrader的C扩展是否释放GIL
"""
import sys
import time
import threading
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import asyncio

sys.path.insert(0, str(Path(__file__).parent.parent))

def run_single_backtest(config):
    """运行单个回测（模拟真实场景）"""
    import backtrader as bt
    import pandas as pd

    # 创建简单数据
    dates = pd.date_range('2024-01-01', periods=100, freq='D')
    df = pd.DataFrame({
        'open': [100 + i for i in range(100)],
        'high': [102 + i for i in range(100)],
        'low': [99 + i for i in range(100)],
        'close': [101 + i for i in range(100)],
        'volume': [1000] * 100
    }, index=dates)

    # 创建Cerebro
    cerebro = bt.Cerebro()
    cerebro.adddata(bt.feeds.PandasData(dataname=df))

    # 添加简单策略
    class TestStrategy(bt.Strategy):
        params = (('period', config['period']),)

        def __init__(self):
            self.sma = bt.indicators.SMA(self.data.close, period=self.params.period)

        def next(self):
            if len(self.data) > self.params.period:
                if self.data.close[0] > self.sma[0]:
                    self.buy()

    cerebro.addstrategy(TestStrategy, period=config['period'])
    cerebro.run()

    return config['period']

def test_baseline(n=20):
    """测试基线：顺序执行"""
    start = time.time()
    for i in range(n):
        run_single_backtest({'period': 10 + i})
    return time.time() - start

def test_multithreading(n=20, workers=8):
    """测试多线程"""
    start = time.time()
    params_list = [{'period': 10 + i} for i in range(n)]

    with ThreadPoolExecutor(max_workers=workers) as executor:
        results = list(executor.map(run_single_backtest, params_list))

    return time.time() - start

def test_multiprocessing(n=20, workers=8):
    """测试多进程"""
    start = time.time()
    params_list = [{'period': 10 + i} for i in range(n)]

    with ProcessPoolExecutor(max_workers=workers) as executor:
        results = list(executor.map(run_single_backtest, params_list))

    return time.time() - start

if __name__ == '__main__':
    print("="*60)
    print("Backtrader多线程 vs 多进程测试")
    print("="*60)
    print(f"测试次数: 20次回测")
    print(f"Worker数量: 8")
    print()

    # 基线测试
    print("1. 基线测试（顺序执行）...")
    baseline_time = test_baseline()
    print(f"   耗时: {baseline_time:.2f}s")
    print(f"   吞吐量: {20/baseline_time:.2f} trials/s")
    print()

    # 多线程测试
    print("2. 多线程测试...")
    threading_time = test_multithreading()
    print(f"   耗时: {threading_time:.2f}s")
    print(f"   吞吐量: {20/threading_time:.2f} trials/s")
    speedup = baseline_time / threading_time
    print(f"   加速比: {speedup:.2f}x")
    print()

    # 多进程测试
    print("3. 多进程测试...")
    process_time = test_multiprocessing()
    print(f"   耗时: {process_time:.2f}s")
    print(f"   吞吐量: {20/process_time:.2f} trials/s")
    speedup = baseline_time / process_time
    print(f"   加速比: {speedup:.2f}x")
    print()

    # 结论
    print("="*60)
    print("结论")
    print("="*60)

    threading_speedup = baseline_time / threading_time
    process_speedup = baseline_time / process_time

    if threading_speedup > 2:
        print("✅ 多线程有效！Backtrader释放GIL")
        print(f"   推荐: 使用多线程 ({threading_speedup:.2f}x加速)")
    elif process_speedup > 2:
        print("✅ 多进程有效")
        print(f"   推荐: 使用多进程 ({process_speedup:.2f}x加速)")
    else:
        print("❌ 多线程和多进程都无效")
        print("   原因: Backtrader可能不释放GIL，或者开销太大")
