# Total Return & Max Drawdown Display Bug Fix Summary

## Problems

### 1. Total Return 显示错误
- **预期**：24.85%
- **实际**：2485%

### 2. Max Drawdown 显示错误
- **预期**：-5.50%（带负号）
- **实际**：+5.50%（带正号）或 5.50%（无符号）

## Root Cause

数据格式不一致导致重复乘以 100：

### 问题链路

1. **后端计算** (`backtest_engine.py:146`):
   ```python
   pnl_pct = (pnl / initial_cash) * 100  # 结果: 24.85
   ```

2. **后端存储** (`backtest_engine.py:246`):
   ```python
   total_return=pnl_pct,  # 存储为 24.85（百分比形式）
   ```

3. **前端显示** (`BacktestHistoryTable.tsx:40`):
   ```typescript
   return `${(value * 100).toFixed(2)}%`;  // 24.85 * 100 = 2485%
   ```

### 不一致性对比

| 组件 | 格式 | 是否正确 |
|------|------|----------|
| 优化器 | 小数 (0.2485) | ✅ |
| 回测引擎 | 百分比 (24.85) | ❌ |
| 前端期望 | 小数 (0.2485) | ✅ |

## Solution

修改后端回测引擎，存储小数形式而非百分比形式，与优化器保持一致。

### 修改文件

#### 1. `backend/core/backtest_engine.py`

**位置 1** (第 246-254 行):
```python
# 修改前
total_return=pnl_pct,
max_drawdown=max_drawdown,
win_rate=win_rate,

# 修改后
total_return=pnl_pct / 100,  # Convert 24.85% to 0.2485
max_drawdown=max_drawdown / 100 if max_drawdown else 0.0,  # Convert to decimal
win_rate=win_rate / 100 if win_rate else 0.0,  # Convert to decimal
```

**位置 2** (第 534-538 行):
```python
# 修改前
total_return=result['pnl_pct'],
max_drawdown=max_drawdown,
win_rate=win_rate,

# 修改后
total_return=result['pnl_pct'] / 100,  # Convert to decimal
max_drawdown=max_drawdown / 100 if max_drawdown else 0.0,  # Convert to decimal
win_rate=win_rate / 100 if win_rate else 0.0,  # Convert to decimal
```

#### 2. `backend/api/backtest.py`

**位置** (第 133-137 行):
```python
# 修改前
total_return=result['pnl_pct'],
max_drawdown=result.get('max_drawdown', 0.0),
win_rate=result.get('win_rate', 0.0),

# 修改后
total_return=result['pnl_pct'] / 100,  # Convert to decimal
max_drawdown=result.get('max_drawdown', 0.0) / 100 if result.get('max_drawdown') else 0.0,  # Convert to decimal
win_rate=result.get('win_rate', 0.0) / 100 if result.get('win_rate') else 0.0,  # Convert to decimal
```

## Verification

### 测试结果

```bash
$ pytest tests/test_e2e_total_return.py -v -s

✓ Total Return: Database stores 0.2485, Frontend shows 24.85%
✓ Max Drawdown: Database stores 0.055, Frontend shows 5.50%
✓ Win Rate: Database stores 0.60, Frontend shows 60.0%
PASSED
```

### 数据流验证

1. **计算**: pnl_pct = 24.85
2. **存储**: total_return = 24.85 / 100 = 0.2485
3. **检索**: saved_result.total_return = 0.2485
4. **显示**: formatPercent(0.2485) = "24.85%" ✅

## Impact

### 受影响的字段

- ✅ `total_return` - 修复
- ✅ `max_drawdown` - 同时修复
- ✅ `win_rate` - 同时修复

### 不受影响的字段

- `sharpe_ratio` - 本身不是百分比
- `profit_factor` - 本身不是百分比
- `total_trades` - 计数，非百分比

## Notes

1. **现有数据**: 如果数据库中已有以百分比形式存储的数据，需要迁移
2. **一致性**: 现在回测引擎和优化器使用相同的数据格式
3. **前端**: 无需修改，前端逻辑本身是正确的

## Max Drawdown Display Fix

### Problem

Max Drawdown 在多个页面显示时没有负号前缀，或者显示了正号前缀：
- `BacktestHistoryTable.tsx` - 显示 "+5.50%"（使用 formatPercent）
- `results/[id]/page.tsx` - 显示 "5.50%"（无符号）
- `optimization-results/[id]/page.tsx` - 显示 "5.50%"（无符号）
- `OptimizationResults.tsx` - 显示 "5.50%"（无符号）

### Solution

Max Drawdown 是回撤，代表损失，应该始终显示为负数。

#### 修改文件

1. **`frontend/components/BacktestHistoryTable.tsx`**
   - 添加 `formatDrawdown` 函数
   - 将 `formatPercent(item.max_drawdown)` 改为 `formatDrawdown(item.max_drawdown)`

2. **`frontend/app/results/[id]/page.tsx`**
   - 将 `${summary.max_drawdown.toFixed(2)}%` 改为 `-${summary.max_drawdown.toFixed(2)}%`

3. **`frontend/app/optimization-results/[id]/page.tsx`**
   - 将 `${(result.max_drawdown * 100).toFixed(2)}%` 改为 `-${(result.max_drawdown * 100).toFixed(2)}%`

4. **`frontend/components/OptimizationResults.tsx`**
   - 将 `{r.max_drawdown?.toFixed(2) || 'N/A'}%` 改为 `-{r.max_drawdown?.toFixed(2) || 'N/A'}%`

### Verification

```bash
$ pytest tests/test_max_drawdown_display.py -v -s

✓ Max Drawdown: Database stores 0.055, Frontend shows -5.50%
✓ Max Drawdown: Database stores 0.1525, Frontend shows -15.25%
✓ Max Drawdown: Database stores 0.0, Frontend shows -0.00%
PASSED
```

## Files Changed

### Backend
- ✅ `backend/core/backtest_engine.py` - 2 处修改
- ✅ `backend/api/backtest.py` - 1 处修改

### Frontend
- ✅ `frontend/components/BacktestHistoryTable.tsx` - 添加 formatDrawdown 函数
- ✅ `frontend/app/results/[id]/page.tsx` - 添加负号前缀
- ✅ `frontend/app/optimization-results/[id]/page.tsx` - 添加负号前缀
- ✅ `frontend/components/OptimizationResults.tsx` - 添加负号前缀

### Tests
- ✅ `tests/test_e2e_total_return.py` - 新增验证测试
- ✅ `tests/test_total_return_fix.py` - 新增单元测试
- ✅ `tests/test_max_drawdown_display.py` - 新增 Max Drawdown 显示测试
