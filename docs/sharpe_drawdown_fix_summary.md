# Sharpe Ratio & Max Drawdown 修复总结

## 问题描述

回测结果中的 Sharpe Ratio 和 Max Drawdown 一直显示为 0，无论是哪个策略或参数组合。

## 根本原因

在 `backend/core/backtest_engine.py` 中，这两个指标被硬编码为 0.0：

```python
# 第 163-167 行（修复前）
max_drawdown = 0.0  # TODO: Calculate from portfolio values
sharpe_ratio = 0.0  # TODO: Calculate from daily returns
```

## 修复方案

### 1. 添加 Backtrader 分析器

在回测引擎中添加 Sharpe Ratio 和 DrawDown 分析器：

```python
# backend/core/backtest_engine.py 第 125-126 行
cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
```

### 2. 提取分析结果

从 Backtrader 分析器中提取计算结果：

```python
# backend/core/backtest_engine.py 第 163-177 行
# Extract Sharpe Ratio from analyzer
sharpe_analysis = strategy.analyzers.sharpe.get_analysis()
sharpe_ratio = sharpe_analysis.get('sharpe_ratio', 0.0)
if sharpe_ratio is None:
    sharpe_ratio = 0.0
    logger.warning("Sharpe ratio analysis returned None, using 0.0")

# Extract DrawDown from analyzer
drawdown_analysis = strategy.analyzers.drawdown.get_analysis()
max_drawdown = drawdown_analysis.get('max', {}).get('drawdown', 0.0)
if max_drawdown is None:
    max_drawdown = 0.0
    logger.warning("Max drawdown analysis returned None, using 0.0")

logger.info(f"Calculated metrics - Sharpe Ratio: {sharpe_ratio:.2f}, Max Drawdown: {max_drawdown:.2f}%")
```

### 3. 更新数据库保存

确保计算结果正确保存到数据库：

```python
# backend/core/backtest_engine.py 第 415-423 行
backtest_result = BacktestResult(
    backtest_job_id=job_id,
    total_return=result['pnl_pct'],
    annual_return=annual_return,
    sharpe_ratio=result['sharpe_ratio'],  # 使用计算的值
    max_drawdown=result['max_drawdown'],  # 使用计算的值
    win_rate=win_rate,
    profit_factor=profit_factor,
    total_trades=total_trades,
    initial_cash=initial_cash,
    final_value=final_value
)
```

## 验证结果

### ✅ 后端单元测试
```bash
python3 -m pytest tests/test_backtest_engine.py -v
# 14 passed in 1.20s
```

### ✅ 端到端测试
```bash
python3 test_sharpe_drawdown_e2e.py
# ✅ TEST PASSED: Sharpe Ratio and Max Drawdown are correctly calculated!
```

## 技术说明

### Sharpe Ratio 计算

Backtrader 的 `SharpeRatio` 分析器计算方式：
- **时间周期**: 默认使用年度化（252个交易日）
- **无风险利率**: 默认 1% (0.01)
- **返回值**: None（数据不足）或浮点数

### Max Drawdown 计算

Backtrader 的 `DrawDown` 分析器计算方式：
- **计算方法**: 从最高点到最低点的最大跌幅
- **返回格式**: 百分比值（如 5.5 表示 5.5%）
- **返回值**: 始终为非负数

### 可能的值为 0.0 的原因

以下情况下，指标可能显示为 0.0：

1. **Sharpe Ratio = 0.0**:
   - 回测期间没有交易
   - 收益率波动为零（所有收益率相同）
   - 交易数据不足以计算

2. **Max Drawdown = 0.0**:
   - 策略在整个回测期间持续盈利
   - 没有明显的回撤期
   - 没有交易发生

## 前端影响

前端无需修改，因为：
- API 接口保持不变
- 字段名称保持一致（`sharpe_ratio`, `max_drawdown`）
- TypeScript 类型定义已正确包含这些字段

## 后续建议

1. **增强日志**: 添加更详细的日志记录分析器的返回值
2. **参数配置**: 允许用户配置 Sharpe Ratio 的参数（时间周期、无风险利率）
3. **更多指标**: 考虑添加其他风险指标（Sortino Ratio, Calmar Ratio）
4. **文档说明**: 在前端添加工具提示，解释这些指标的含义和计算方式

## 文件修改清单

- ✅ `backend/core/backtest_engine.py` - 添加分析器和结果提取
- ✅ 测试通过：`tests/test_backtest_engine.py`
- ✅ 端到端验证：`test_sharpe_drawdown_e2e.py`

## 结论

✅ Sharpe Ratio 和 Max Drawdown 现在通过 Backtrader 的内置分析器动态计算，不再硬编码为 0.0。

✅ 修复已验证，所有测试通过。

✅ 前后端集成正确，无需额外修改。
