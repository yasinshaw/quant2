# 多线程优化分析

## 为什么之前没考虑多线程？

我之前的假设：Python有GIL，多线程没用。

**但这个假设可能是错的！**

### 关键事实

1. **Backtrader是C扩展**
   - C扩展在执行时会释放GIL
   - 多线程可能有效！

2. **多线程 vs 多进程**
   - 多进程：需要pickle序列化数据（有开销）
   - 多线程：共享内存，无序列化开销

3. **Optuna的n_jobs**
   - 使用的是multiprocessing（多进程）
   - 没有提供threading选项

## 需要测试的方案

### 方案1：手动线程池
```python
from concurrent.futures import ThreadPoolExecutor
import threading

# 将试验分批，每批由一个线程处理
with ThreadPoolExecutor(max_workers=8) as executor:
    futures = []
    for trial_params in trial_batches:
        future = executor.submit(run_single_batch, trial_params)
        futures.append(future)
```

### 方案2：异步+线程池
```python
import asyncio
from concurrent.futures import ThreadPoolExecutor

loop = asyncio.get_event_loop()
executor = ThreadPoolExecutor(max_workers=8)

tasks = []
for trial in range(n_trials):
    task = loop.run_in_executor(executor, run_backtest, params)
    tasks.append(task)

results = await asyncio.gather(*tasks)
```

### 方案3：Optuna自定义执行器
```python
from optuna.storages import InMemoryStorage
from optuna.pruners import MedianPruner

# 创建多个study，每个线程运行一个
# 然后合并结果
```

## 其他可能的优化空间

### 1. Backtrader配置优化
```python
cerebro = bt.Cerebro(
    preload=True,      # 预加载数据到内存
    runonce=False,     # 可能更快
    oldsync=True,      # 当前已使用
    # 还有其他配置吗？
)
```

### 2. 减少分析器
当前有两个分析器：
- SharpeRatio
- DrawDown

如果DrawDown不常用，可以移除它：
```python
# 只保留必要的
cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
```

### 3. 数据加载优化
当前每个trial都创建DataFrame，可以：
- 预处理成numpy数组（更快）
- 使用Backtrader的CSV数据源
- 缓存解析后的数据

### 4. 指标计算优化
当前的scoring函数计算了多个指标：
- total_return
- sharpe_ratio
- max_drawdown
- win_rate
- total_trades

可以简化或延迟计算。

### 5. 数据库批量写入
当前每个结果都单独写入，可以批量写入。

## 下一步测试

让我先测试多线程方案，看看是否有效。
