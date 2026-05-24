#!/usr/bin/env python3
"""
诊断多进程并行问题

测试Optuna的n_jobs参数在当前环境下的效果
"""
import sys
import time
import multiprocessing
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

def test_objective_with_sleep(trial):
    """测试目标函数 - 模拟CPU密集任务"""
    import time
    # 模拟0.2秒的计算（类似回测）
    time.sleep(0.2)
    return trial.suggest_float('x', 0, 10)

def test_objective_real_work(trial):
    """测试目标函数 - 真实计算"""
    # 简单的CPU密集计算
    x = trial.suggest_float('x', -10, 10)
    result = sum(i * x for i in range(100000))
    return -abs(result)  # 最小化绝对值

def run_benchmark(n_trials=20, n_jobs=1, use_real_work=False):
    """运行基准测试"""
    import optuna

    objective = test_objective_real_work if use_real_work else test_objective_with_sleep

    start = time.time()
    study = optuna.create_study(direction='minimize')
    study.optimize(objective, n_trials=n_trials, n_jobs=n_jobs, show_progress_bar=False)
    duration = time.time() - start

    return duration, len(study.trials)

if __name__ == '__main__':
    print("="*60)
    print("多进程诊断测试")
    print("="*60)
    print(f"CPU核心数: {multiprocessing.cpu_count()}")
    print(f"平台: {sys.platform}")
    print()

    # 测试配置
    n_trials = 20

    results = []

    for n_jobs in [1, 2, 4, 8]:
        print(f"测试 n_jobs={n_jobs}...")

        # 使用sleep模拟
        duration, trials = run_benchmark(n_trials=n_trials, n_jobs=n_jobs, use_real_work=False)
        trials_per_sec = trials / duration
        speedup = results[0][1] / trials_per_sec if results else 1.0

        print(f"  耗时: {duration:.2f}s")
        print(f"  吞吐量: {trials_per_sec:.2f} trials/s")
        print(f"  加速比: {speedup:.2f}x")

        results.append((n_jobs, trials_per_sec, duration))
        print()

    # 分析结果
    print("="*60)
    print("结果分析")
    print("="*60)
    baseline = results[0][1]

    for n_jobs, tps, duration in results:
        if n_jobs == 1:
            continue
        speedup = tps / baseline
        efficiency = speedup / n_jobs * 100
        print(f"n_jobs={n_jobs}: {speedup:.2f}x 加速, 效率: {efficiency:.1f}%")

    # 建议
    print()
    print("="*60)
    print("建议")
    print("="*60)

    best_speedup = max(results, key=lambda x: x[1])[1] / baseline
    if best_speedup > 1.5:
        print("✅ 多进程有效，建议启用")
        optimal_workers = max(results, key=lambda x: x[1])[0]
        print(f"   推荐使用 {optimal_workers} 个workers")
    else:
        print("❌ 多进程效果不佳，可能原因：")
        print("   - macOS 的 fork() 限制")
        print("   - 数据序列化开销过大")
        print("   - GIL (全局解释器锁) 限制")
        print()
        print("建议：")
        print("   1. 使用 start_method='spawn' 替代 'fork'")
        print("   2. 优化数据传输，减少序列化")
        print("   "   "3. 接受当前性能，使用单进程")
