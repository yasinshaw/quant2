# 显示问题修复完成总结

## 已修复的问题

### 1. ✅ Total Return 显示错误（2485% → 24.85%）

**根本原因**：后端存储百分比（24.85），前端期望小数（0.2485）并乘以 100

**修复**：后端在存储前除以 100，与优化器保持一致

**影响范围**：
- `backend/core/backtest_engine.py` - 2 处
- `backend/api/backtest.py` - 1 处

### 2. ✅ Max Drawdown 缺少负号前缀

**根本原因**：Max Drawdown 是回撤（损失），应该显示为负数，但多个页面没有负号

**修复**：在所有显示 Max Drawdown 的地方添加负号前缀

**影响范围**：
- `BacktestHistoryTable.tsx` - 添加 formatDrawdown 函数
- `results/[id]/page.tsx` - 添加负号前缀
- `optimization-results/[id]/page.tsx` - 添加负号前缀
- `OptimizationResults.tsx` - 添加负号前缀

## 数据格式规范

### 后端存储（小数形式）
- `total_return`: 0.2485（表示 24.85%）
- `max_drawdown`: 0.055（表示 5.5%）
- `win_rate`: 0.60（表示 60%）

### 前端显示（百分比形式）
- Total Return: `formatPercent(0.2485)` → "+24.85%"
- Max Drawdown: `formatDrawdown(0.055)` → "-5.50%"
- Win Rate: `(0.60 * 100).toFixed(1)` → "60.0%"

## 测试验证

### Total Return 测试
```bash
$ pytest tests/test_e2e_total_return.py -v -s
✓ Total Return: Database stores 0.2485, Frontend shows 24.85%
✓ Max Drawdown: Database stores 0.055, Frontend shows 5.50%
✓ Win Rate: Database stores 0.60, Frontend shows 60.0%
```

### Max Drawdown 测试
```bash
$ pytest tests/test_max_drawdown_display.py -v -s
✓ Max Drawdown: Database stores 0.055, Frontend shows -5.50%
✓ Max Drawdown: Database stores 0.1525, Frontend shows -15.25%
✓ Max Drawdown: Database stores 0.0, Frontend shows -0.00%
```

## 修改的文件

### 后端（3 个文件）
- `backend/core/backtest_engine.py`
- `backend/api/backtest.py`

### 前端（4 个文件）
- `frontend/components/BacktestHistoryTable.tsx`
- `frontend/app/results/[id]/page.tsx`
- `frontend/app/optimization-results/[id]/page.tsx`
- `frontend/components/OptimizationResults.tsx`

### 测试（3 个文件）
- `tests/test_e2e_total_return.py`
- `tests/test_total_return_fix.py`
- `tests/test_max_drawdown_display.py`

### 文档（2 个文件）
- `docs/total_return_fix_summary.md`
- `docs/display_fixes_complete.md`

## 注意事项

⚠️ **数据库迁移**：如果生产数据库中已有以百分比形式存储的数据，需要迁移脚本：

```sql
-- 将百分比转换为小数
UPDATE backtest_results
SET total_return = total_return / 100,
    max_drawdown = max_drawdown / 100,
    win_rate = win_rate / 100
WHERE total_return > 1;  -- 只转换大于 1 的值（百分比）
```

## 验证清单

- [x] Total Return 显示正确（如 +24.85%）
- [x] Max Drawdown 显示负号（如 -5.50%）
- [x] Win Rate 显示正确（如 60.0%）
- [x] Sharpe Ratio 显示正确（如 1.50）
- [x] 所有测试通过
- [x] 代码与优化器保持一致
