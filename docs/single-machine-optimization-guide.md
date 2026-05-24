# 单机多进程贝叶斯优化指南

## 硬件配置
- Mac mini (4核)
- 本地单机环境

## 优化策略

### 方案对比

| 方案 | 适用场景 | 预期提升 | 复杂度 |
|------|---------|---------|--------|
| ✅ **多进程并行** | 单机多核 | 2-3倍 | 中等 |
| ❌ 分布式优化 | 多台机器 | 线性扩展 | 高 |
| ✅ **已实施的优化** | 所有场景 | 内存-54% | 低 |

### 推荐方案：多进程并行 + 已有优化

结合已实施的内存优化，添加多进程并行执行。

## 实现方式

### 选项1：Optuna内置并行（最简单）

修改 `bayesian_optimizer.py` 中的 `study.optimize()` 调用：

```python
# 当前（单进程）
study.optimize(objective, n_trials=n_trials)

# 优化后（多进程）
from multiprocessing import cpu_count
n_jobs = min(cpu_count(), 4)  # Mac mini 4核
study.optimize(objective, n_trials=n_trials, n_jobs=n_jobs)
```

**优点**：
- 最简单，只需修改一行代码
- Optuna自动管理进程池
- 稳定性好

**缺点**：
- 每个进程需要独立加载数据
- 进程间通信有开销

**预期提升**：2-2.5倍

### 选项2：手动多进程Batch执行（更灵活）

```python
from concurrent.futures import ProcessPoolExecutor
import multiprocessing as mp

# 将试验分成批次，每批由一个进程处理
batch_size = n_trials // mp.cpu_count()

with ProcessPoolExecutor(max_workers=mp.cpu_count()) as executor:
    futures = []
    for i in range(mp.cpu_count()):
        start = i * batch_size
        end = start + batch_size if i < mp.cpu_count() - 1 else n_trials
        future = executor.submit(
            run_batch,
            objective,
            study,
            start,
            end
        )
        futures.append(future)

    results = [f.result() for f in futures]
```

**优点**：
- 更细粒度的控制
- 可以实现自定义负载均衡
- 更好的错误处理

**缺点**：
- 实现复杂
- 需要手动处理进程间通信

**预期提升**：2.5-3倍

## 性能预测

### Mac mini 4核配置

| 优化方案 | 当前速度 | 优化后速度 | 提升倍数 |
|---------|---------|-----------|---------|
| 基线 | 3.23 trials/s | - | 1x |
| 已优化（内存） | 3.18 trials/s | - | 1x |
| + 多进程 | 3.18 trials/s | **~8 trials/s** | **2.5x** |
| + 多进程Batch | 3.18 trials/s | **~9.5 trials/s** | **3x** |

### 实际场景

对于100次试验的优化：
- **当前**：~31秒
- **多进程**：~12秒（节省19秒）
- **多进程Batch**：~10秒（节省21秒）

对于1000次试验的优化：
- **当前**：~315秒 (5.25分钟)
- **多进程**：~125秒 (2.08分钟)
- **多进程Batch**：~105秒 (1.75分钟)

## 实施建议

### 阶段1：快速验证（5分钟）
使用Optuna内置并行，快速验证效果：

```python
# backend/core/bayesian_optimizer.py 第281行
study.optimize(
    objective,
    n_trials=n_trials,
    n_jobs=4,  # 添加这行
    show_progress_bar=True
)
```

### 阶段2：优化调优（可选）
如果效果满意，可以进一步优化：
- 调整worker数量（2-4之间测试）
- 添加内存监控
- 优化进程间数据传输

## 注意事项

### 内存使用
- 已有优化将内存降至5.48MB/进程
- 4进程并行：~22MB总内存
- Mac mini内存应该足够

### CPU利用率
```bash
# 监控CPU使用
top -pid $(pgrep -f "python.*bayesian")

# 或使用Activity Monitor观察CPU核心
```

### 最佳实践
1. **worker数量**：建议设置为CPU核心数（4）或核心数-1（3）
2. **试验数量**：至少是worker数量的2-3倍
3. **数据大小**：小数据集多进程优势更明显

## 下一步

我建议先实施**选项1（Optuna内置并行）**，因为：
1. 最简单（修改1行代码）
2. 效果明显（2-2.5倍提升）
3. 风险最低（Optuna官方支持）

需要我立即实施吗？
