# Sharpe Ratio 计算说明

## 概述

本系统使用 Backtrader 框架的 SharpeRatio 分析器来计算夏普比率。当分析器无法计算时（通常由于数据不足），系统会使用估算方法。

## Sharpe Ratio 计算方法

### 1. 主要方法：Backtrader SharpeRatio 分析器

Backtrader 内置的 `SharpeRatio` 分析器基于以下公式：

```
Sharpe Ratio = (平均收益率 - 无风险利率) / 收益率标准差 × √252
```

**参数：**
- 时间周期：默认使用每日收益率
- 无风险利率：默认 1% (0.01)
- 年化因子：252 个交易日

**返回 None 的情况：**
1. 数据不足（通常需要至少 30 根 K 线）
2. 没有收益率波动（所有收益率相同）
3. 回测期间没有持仓变化
4. 计算窗口内没有足够的价格变动

### 2. 后备方法：基于总回报的估算

当 Backtrader 分析器返回 None 时，系统使用以下估算方法：

```python
# 基于总回报率的估算
if total_return > 0:
    if total_return < 10%:
        sharpe_ratio = 0.5 + (total_return / 10.0)  # 范围: 0.5 - 1.5
    elif total_return < 50%:
        sharpe_ratio = 1.0 + ((total_return - 10) / 40.0)  # 范围: 1.0 - 2.0
    else:
        sharpe_ratio = min(1.5 + ((total_return - 50) / 100.0), 2.5)  # 上限: 2.5
elif total_return < 0:
    sharpe_ratio = max(total_return / 10.0, -2.0)  # 下限: -2.0
else:
    sharpe_ratio = 0.0
```

## 为什么 Sharpe Ratio 可能显示 0.00 或估算值？

### 常见原因

1. **数据不足**
   - 需要至少 20-30 根 K 线
   - 建议：下载更多历史数据

2. **策略没有交易**
   - 策略参数不适合当前市场
   - 建议：调整策略参数或使用不同的时间范围

3. **收益率波动率为零**
   - 策略收益过于稳定（不太可能）
   - 建议：检查数据质量

4. **回测期间太短**
   - Backtrader 需要足够的时间来计算每日收益率
   - 建议：使用至少 1 个月的数据

## 如何获得准确的 Sharpe Ratio

### ✅ 推荐做法

1. **使用足够的历史数据**
   ```
   时间范围：至少 3-6 个月
   K线数量：至少 100-200 根
   ```

2. **确保策略会产生交易**
   ```
   - 检查策略参数是否适合市场
   - 使用不同的参数组合进行优化
   - 尝试不同的时间周期（1h, 4h, 1d）
   ```

3. **检查数据质量**
   ```
   - 确保数据连续无缺失
   - 验证价格数据合理（无异常值）
   ```

### ❌ 避免

1. 使用过短的时间范围（< 1个月）
2. 使用不适合市场的策略参数
3. 在数据不足时过度解读 Sharpe Ratio

## 估算值的含义

当看到估算的 Sharpe Ratio 时，请理解：

- **这是基于总回报的近似值**
- **不是基于每日收益率波动率的精确计算**
- **仅供参考，不应作为唯一的风险评估指标**

### 估算 Sharpe Ratio 的解读

| Sharpe Ratio | 解释 |
|--------------|------|
| < 0 | 策略表现差于无风险利率 |
| 0 - 0.5 | 低于平均 |
| 0.5 - 1.0 | 还可以 |
| 1.0 - 1.5 | 良好 |
| 1.5 - 2.0 | 很好 |
| > 2.0 | 优秀（但需谨慎验证） |

## 示例

### 示例 1：有足够数据的情况
```
数据：6个月，1000+ 根K线
交易：50+ 笔
Sharpe Ratio: 1.85 (来自 Backtrader 分析器)
状态：✅ 精确计算
```

### 示例 2：数据不足的情况
```
数据：1个月，30 根K线
交易：5 笔
总回报：+15%
Sharpe Ratio: 1.125 (估算)
状态：⚠️ 基于总回报估算
```

### 示例 3：没有交易的情况
```
数据：1周，10 根K线
交易：0 笔
Sharpe Ratio: 0.0
状态：ℹ️ 无交易，无法计算
```

## 技术实现

代码位置：`backend/core/backtest_engine.py`

```python
# 添加 SharpeRatio 分析器
cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')

# 提取结果
sharpe_analysis = strategy.analyzers.sharpe.get_analysis()
sharpe_ratio = sharpe_analysis.get('sharperatio', None)

# 如果为 None，使用估算方法
if sharpe_ratio is None:
    # 基于总回报估算
    sharpe_ratio = estimate_sharpe_from_return(total_return)
```

## 常见问题

**Q: 为什么我的 Sharpe Ratio 一直是 0.00？**
A: 可能原因：
1. 数据不足 - 下载更多历史数据
2. 策略没有产生交易 - 调整参数或时间范围
3. 回测期间太短 - 使用更长的时间范围

**Q: 估算的 Sharpe Ratio 可靠吗？**
A: 估算值仅供参考。真正的 Sharpe Ratio 应基于每日收益率的统计特性。当看到估算值时，建议：
1. 下载更多数据
2. 重新运行回测
3. 使用精确计算的 Sharpe Ratio

**Q: 如何提高 Sharpe Ratio 的准确性？**
A:
1. 使用至少 3-6 个月的历史数据
2. 确保策略会产生足够的交易（>10 笔）
3. 使用合适的时间周期（1h, 4h, 1d）
4. 检查数据质量，确保无缺失值

## 相关资源

- [Backtrader SharpeRatio 文档](https://www.backtrader.com/docu/analyzers-reference/#sharperatio)
- [Sharpe Ratio 维基百科](https://en.wikipedia.org/wiki/Sharpe_ratio)
- 项目文档：`docs/sharpe_drawdown_fix_summary.md`
