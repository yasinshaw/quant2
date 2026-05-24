# 回测和参数调优历史记录功能实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development

**Goal:** 为量化交易平台添加回测和参数调优历史记录查看功能，支持分页、筛选、排序和删除操作

**Architecture:** 采用经典的三层架构 - 前端(Next.js + React Query) → 后端(FastAPI) → 数据库(SQLite)，复用现有详情页面，最小化实现

**Tech Stack:**
- Backend: FastAPI, SQLAlchemy, SQLite
- Frontend: Next.js 14, TypeScript, Tailwind CSS, React Query, Axios
- Testing: pytest (backend), Playwright (E2E)

---

## 任务列表

### Task 1: 实现数据库层历史查询方法

**Files:**
- Modify: `backend/database.py`
- Test: `tests/test_database.py`

**Steps:**
- [ ] 在 `backend/database.py` 中添加 `get_backtest_history()` 方法
  - 参数：strategy_name, symbol, status, sort_by, sort_order, page, page_size
  - 使用 SQLAlchemy join 查询 BacktestJob 和 BacktestResult
  - 实现筛选条件（if 参数存在则 filter）
  - 实现排序逻辑（支持 created_at, total_return, sharpe_ratio）
  - 使用 offset() 和 limit() 实现分页
  - 返回格式：{total, page, page_size, total_pages, items}
  - items 中每条记录包含：id, strategy_name, symbol, interval, start_time, end_time, status, total_return, sharpe_ratio, max_drawdown, total_trades, created_at, completed_at

- [ ] 在 `backend/database.py` 中添加 `get_optimization_history()` 方法
  - 参数同上
  - 查询 OptimizationJob 和 OptimizationResult
  - items 中每条记录包含：id, strategy_name, symbol, interval, start_time, end_time, status, best_score, best_parameters, total_combinations, created_at, completed_at

- [ ] 在 `backend/database.py` 中添加 `delete_backtest_job()` 方法
  - 参数：job_id
  - 检查作业状态，如果为 running 则抛出 ValueError
  - 使用 session.delete() 删除作业（级联删除会自动删除 result 和 trades）
  - 返回 True 表示成功

- [ ] 在 `backend/database.py` 中添加 `delete_optimization_job()` 方法
  - 参数：job_id
  - 检查作业状态，如果为 running 则抛出 ValueError
  - 删除作业（级联删除 results）
  - 返回 True 表示成功

**Test:**
```python
# 在 tests/test_database.py 中添加测试

def test_get_backtest_history(db):
    """测试获取回测历史列表"""
    # 创建测试数据：3个回测作业（不同策略、交易对、状态）
    # 测试无筛选条件时返回所有记录
    # 测试按策略筛选
    # 测试按交易对筛选
    # 测试按状态筛选
    # 测试分页
    # 测试排序（时间、收益率）
    pass

def test_get_optimization_history(db):
    """测试获取调优历史列表"""
    # 类似回测历史测试
    pass

def test_delete_backtest_job(db):
    """测试删除回测作业"""
    # 测试删除已完成作业成功
    # 测试删除运行中作业失败（抛出 ValueError）
    # 测试删除不存在的作业失败
    pass

def test_delete_optimization_job(db):
    """测试删除调优作业"""
    # 类似回测删除测试
    pass
```

**Verify:**
```bash
cd ~/code/quant2
pytest tests/test_database.py -v
```

**Commit:** `feat(db): add history query and delete methods`

---

### Task 2: 实现后端历史查询API端点

**Files:**
- Modify: `backend/api/backtest.py`
- Test: `tests/test_backtest_api.py`

**Steps:**
- [ ] 在 `backend/api/backtest.py` 中添加 `GET /api/v1/backtest/history` 端点
  - 使用 Query 参数定义筛选和分页参数
  - 参数验证：page >= 1, page_size 1-100
  - 调用 `_db.get_backtest_history()`
  - 返回分页响应
  - 异常处理：500 数据库错误

- [ ] 在 `backend/api/backtest.py` 中添加 `DELETE /api/v1/backtest/jobs/{job_id}` 端点
  - 路径参数：job_id
  - 调用 `_db.delete_backtest_job()`
  - 捕获 ValueError 返回 400（运行中）
  - 捕获 NotFound 返回 404
  - 返回 {success: true, message: "..."}

- [ ] 在 `backend/api/backtest.py` 中添加 `GET /api/v1/optimization/history` 端点
  - 类似回测历史端点
  - 调用 `_db.get_optimization_history()`

- [ ] 在 `backend/api/backtest.py` 中添加 `DELETE /api/v1/optimization/jobs/{job_id}` 端点
  - 类似回测删除端点
  - 调用 `_db.delete_optimization_job()`

**Test:**
```python
# 在 tests/test_backtest_api.py 中添加测试

def test_get_backtest_history(client):
    """测试获取回测历史API"""
    # 创建测试数据
    # 测试 GET /api/v1/backtest/history 返回正确格式
    # 测试筛选参数
    # 测试分页参数
    # 测试排序参数
    pass

def test_delete_backtest_job(client):
    """测试删除回测作业API"""
    # 测试删除成功返回 200
    # 测试删除运行中作业返回 400
    # 测试删除不存在的作业返回 404
    pass

def test_get_optimization_history(client):
    """测试获取调优历史API"""
    # 类似回测历史测试
    pass

def test_delete_optimization_job(client):
    """测试删除调优作业API"""
    # 类似回测删除测试
    pass
```

**Verify:**
```bash
pytest tests/test_backtest_api.py -v
```

**Commit:** `feat(api): add history query and delete endpoints`

---

### Task 3: 创建前端API客户端

**Files:**
- Create: `frontend/lib/api/history.ts`

**Steps:**
- [ ] 定义 TypeScript 接口
  - HistoryQueryParams
  - PaginatedResponse<T>
  - BacktestHistoryItem
  - OptimizationHistoryItem

- [ ] 实现 historyApi 对象
  - getBacktestHistory(params): 调用 GET /api/v1/backtest/history
  - deleteBacktestJob(jobId): 调用 DELETE /api/v1/backtest/jobs/{id}
  - getOptimizationHistory(params): 调用 GET /api/v1/optimization/history
  - deleteOptimizationJob(jobId): 调用 DELETE /api/v1/optimization/jobs/{id}

- [ ] 使用 axios 发送请求
  - 导入 API_BASE_URL（应该是 http://localhost:8000）
  - 正确处理响应和错误

**Test:**
```bash
# 手动测试：在浏览器控制台导入并调用
# 或者通过后续的集成测试验证
```

**Commit:** `feat(frontend): add history API client`

---

### Task 4: 创建分页组件

**Files:**
- Create: `frontend/components/Pagination.tsx`

**Steps:**
- [ ] 创建 Pagination 组件
  - Props: currentPage (number), totalPages (number), onPageChange (function)
  - 显示：上一页按钮、当前页/总页数、下一页按钮
  - 第一页时禁用上一页按钮
  - 最后一页时禁用下一页按钮
  - 使用 Tailwind CSS 样式

- [ ] 实现页码切换逻辑
  - 点击上一页调用 onPageChange(currentPage - 1)
  - 点击下一页调用 onPageChange(currentPage + 1)

**Test:**
```bash
# 通过视觉测试和后续集成测试验证
```

**Commit:** `feat(frontend): add Pagination component`

---

### Task 5: 创建历史筛选器组件

**Files:**
- Create: `frontend/components/HistoryFilters.tsx`

**Steps:**
- [ ] 创建 HistoryFilters 组件
  - Props: filters, onFilterChange, onClear, strategies, symbols
  - 三个下拉菜单：Strategy、Symbol、Status
  - 清除筛选按钮

- [ ] 实现筛选逻辑
  - 选择策略时调用 onFilterChange({ ...filters, strategy_name: value })
  - 选择交易对时调用 onFilterChange({ ...filters, symbol: value })
  - 选择状态时调用 onFilterChange({ ...filters, status: value })
  - 点击清除按钮调用 onClear()

- [ ] Status 下拉选项：pending, running, completed, failed

- [ ] 使用 Tailwind CSS 样式，响应式布局

**Test:**
```bash
# 通过视觉测试和后续集成测试验证
```

**Commit:** `feat(frontend): add HistoryFilters component`

---

### Task 6: 创建标签页组件

**Files:**
- Create: `frontend/components/HistoryTabs.tsx`

**Steps:**
- [ ] 创建 HistoryTabs 组件
  - Props: activeTab ('backtest' | 'optimization'), onTabChange (function)
  - 两个标签按钮：Backtests、Optimizations
  - 当前激活标签有高亮样式

- [ ] 实现标签切换逻辑
  - 点击 Backtests 调用 onTabChange('backtest')
  - 点击 Optimizations 调用 onTabChange('optimization')

- [ ] 使用 Tailwind CSS，标签样式参考现有导航

**Test:**
```bash
# 通过视觉测试和后续集成测试验证
```

**Commit:** `feat(frontend): add HistoryTabs component`

---

### Task 7: 创建回测历史表格组件

**Files:**
- Create: `frontend/components/BacktestHistoryTable.tsx`

**Steps:**
- [ ] 创建 BacktestHistoryTable 组件
  - Props: data (BacktestHistoryItem[]), onDelete (function), onView (function)
  - 表格列：Strategy, Symbol/Interval, Time Range, Status, Total Return, Sharpe Ratio, Max Drawdown, Trades, Created At, Actions

- [ ] 格式化显示
  - Symbol/Interval: `${symbol} / ${interval}`
  - Time Range: `${formatDate(start_time)} ~ ${formatDate(end_time)}`
  - Status: Badge 组件，不同状态不同颜色（completed=绿, failed=红, running=蓝, pending=灰）
  - Total Return: 百分比格式，正数绿色，负数红色
  - Max Drawdown: 百分比格式，红色
  - Created At: 格式化为 `YYYY-MM-DD HH:mm`

- [ ] Actions 列
  - View 按钮：调用 onView(item.id)
  - Delete 按钮：调用 onDelete(item.id)，运行中的作业禁用删除按钮

- [ ] 样式
  - 斑马纹背景（偶数行灰色）
  - Hover 高亮
  - 响应式：小屏幕水平滚动

**Test:**
```bash
# 通过视觉测试和后续集成测试验证
```

**Commit:** `feat(frontend): add BacktestHistoryTable component`

---

### Task 8: 创建调优历史表格组件

**Files:**
- Create: `frontend/components/OptimizationHistoryTable.tsx`

**Steps:**
- [ ] 创建 OptimizationHistoryTable 组件
  - Props: data (OptimizationHistoryItem[]), onDelete (function), onView (function)
  - 表格列：Strategy, Symbol/Interval, Time Range, Status, Best Score, Combinations, Created At, Actions

- [ ] 格式化显示
  - Symbol/Interval, Time Range, Status, Created At: 同回测表格
  - Best Score: 数字格式，保留2位小数
  - Combinations: 整数

- [ ] Actions 列
  - View 按钮：调用 onView(item.id)
  - Delete 按钮：调用 onDelete(item.id)，运行中的作业禁用

- [ ] 样式：同回测表格

**Test:**
```bash
# 通过视觉测试和后续集成测试验证
```

**Commit:** `feat(frontend): add OptimizationHistoryTable component`

---

### Task 9: 创建历史页面主组件

**Files:**
- Create: `frontend/app/history/page.tsx`

**Steps:**
- [ ] 创建 HistoryPage 组件（'use client'）
  - 状态管理：activeTab, filters, page
  - 使用 React Query 获取数据
  - 使用 useMutation 处理删除操作

- [ ] 实现数据获取
  - 根据 activeTab 调用 historyApi.getBacktestHistory 或 getOptimizationHistory
  - queryKey: ['backtest-history', filters, page] 或 ['optimization-history', filters, page]
  - keepPreviousData: true（分页时保留旧数据）

- [ ] 实现筛选功能
  - 获取所有策略列表（调用 /api/v1/strategies）
  - 获取所有交易对列表（从现有数据或硬编码）
  - 筛选器变化时重置 page 为 1

- [ ] 实现分页功能
  - 使用 Pagination 组件
  - 页码变化时更新 page 状态

- [ ] 实现删除功能
  - 点击删除时弹出确认对话框（window.confirm 或模态框）
  - 确认后调用 deleteBacktestJob 或 deleteOptimizationJob
  - 成功后刷新列表（invalidateQueries）
  - 错误时显示错误消息

- [ ] 实现查看详情功能
  - 回测：router.push(`/results/${id}`)
  - 调优：router.push(`/optimization-results/${id}`)（暂时跳转到回测详情页）

- [ ] 加载和错误状态
  - 加载时显示骨架屏或加载指示器
  - 错误时显示错误消息和重试按钮
  - 空状态时显示"暂无历史记录"

- [ ] 布局结构
  - 页面标题 "History"
  - HistoryTabs 组件
  - HistoryFilters 组件
  - BacktestHistoryTable 或 OptimizationHistoryTable 组件
  - Pagination 组件

**Test:**
```bash
# 通过E2E测试和手动测试验证
pnpm dev
# 访问 http://localhost:3000/history
```

**Commit:** `feat(frontend): add History page`

---

### Task 10: 更新导航栏添加History链接

**Files:**
- Modify: `frontend/components/Navigation.tsx` (或类似文件)

**Steps:**
- [ ] 找到导航组件（可能在 Navigation.tsx, Layout.tsx 或 Header.tsx）
- [ ] 在导航链接中添加 "History" 链接
  - 链接到 `/history`
  - 使用合适的历史图标（如 Clock 或 History 图标）
  - 样式与其他导航链接一致

**Test:**
```bash
pnpm dev
# 访问首页，确认导航栏有 History 链接
# 点击链接，确认跳转到 /history 页面
```

**Commit:** `feat(frontend): add History link to navigation`

---

### Task 11: 编写E2E测试

**Files:**
- Create: `frontend/e2e/history.spec.ts`

**Steps:**
- [ ] 测试查看回测历史
  - 访问 /history 页面
  - 确认页面标题显示
  - 确认回测标签页激活
  - 确认历史列表显示（假设有测试数据）

- [ ] 测试筛选功能
  - 选择策略筛选
  - 确认列表更新
  - 清除筛选
  - 确认列表恢复

- [ ] 测试分页功能
  - 创建足够多的测试数据（>20条）
  - 确认第一页显示
  - 点击下一页
  - 确认第二页显示

- [ ] 测试标签页切换
  - 点击 Optimizations 标签
  - 确认调优历史显示

- [ ] 测试删除功能
  - 点击删除按钮
  - 确认确认对话框出现
  - 确认删除
  - 确认记录消失

- [ ] 测试空状态
  - 清空测试数据
  - 访问历史页面
  - 确认"暂无历史记录"显示

**Test:**
```bash
cd frontend
pnpm test:e2e
```

**Commit:** `test(e2e): add history page tests`

---

### Task 12: 集成测试和优化

**Files:**
- None (测试和优化)

**Steps:**
- [ ] 运行所有后端测试
  ```bash
  pytest tests/ -v --cov=backend
  ```
  - 确认覆盖率 > 80%

- [ ] 运行所有前端测试
  ```bash
  cd frontend
  pnpm lint
  pnpm test:e2e
  ```

- [ ] 手动测试完整流程
  - 启动后端：`python backend/main.py`
  - 启动前端：`cd frontend && pnpm dev`
  - 访问 http://localhost:3000
  - 导航到 History 页面
  - 测试所有功能：筛选、分页、删除、查看详情、标签切换

- [ ] 性能测试
  - 创建 100 条测试数据
  - 测试页面加载时间（应 < 1秒）
  - 测试筛选响应时间（应 < 500ms）
  - 测试删除响应时间（应 < 300ms）

- [ ] 响应式测试
  - 测试不同屏幕尺寸（桌面、平板、手机）
  - 确认表格在小屏幕上可滚动
  - 确认筛选器在小屏幕上正确换行

- [ ] 用户体验优化
  - 添加加载指示器
  - 优化错误消息
  - 确认所有按钮有合适的 hover 效果
  - 确认颜色对比度足够

- [ ] 代码质量检查
  - 确认无 TypeScript 错误
  - 确认无 ESLint 警告
  - 确认代码格式一致

**Commit:** `test: verify all functionality and optimize UX`

---

## 实施顺序

**推荐执行顺序：**
1. Task 1 (数据库层) → Task 2 (API层) → 后端测试通过
2. Task 3 (API客户端) → Task 4-8 (前端组件) → Task 9 (页面)
3. Task 10 (导航) → Task 11 (E2E测试) → Task 12 (集成测试)

**依赖关系：**
- Task 2 依赖 Task 1
- Task 9 依赖 Task 3-8
- Task 11 依赖 Task 1-10
- Task 12 依赖所有前置任务

**并行执行建议：**
- Task 4-8 可以并行开发（独立组件）
- 后端（Task 1-2）和前端（Task 3-8）可以并行开发

---

## 验收标准

### 功能验收
- [ ] 可以查看回测历史列表（分页）
- [ ] 可以查看参数调优历史列表（分页）
- [ ] 可以按策略、交易对、状态筛选
- [ ] 可以按创建时间、收益率、夏普比率排序
- [ ] 可以删除历史记录（带确认对话框）
- [ ] 可以点击记录查看详细信息
- [ ] 可以在两个标签页间切换
- [ ] 运行中的作业不能删除（按钮禁用）

### 性能验收
- [ ] 首次加载时间 < 1秒（100条记录）
- [ ] 筛选响应时间 < 500ms
- [ ] 删除操作响应时间 < 300ms

### 代码质量验收
- [ ] 后端测试覆盖率 > 80%
- [ ] 前端E2E测试覆盖主要流程
- [ ] 代码通过 lint 检查
- [ ] 无 TypeScript 类型错误

### 用户体验验收
- [ ] 加载时显示加载指示器
- [ ] 错误时显示友好的错误消息
- [ ] 空状态时显示明确的提示
- [ ] 响应式设计，支持移动端访问
- [ ] 所有交互有合适的视觉反馈

---

## 风险和注意事项

1. **数据库查询性能**
   - 风险：大量历史记录时查询慢
   - 缓解：已创建索引（status字段），使用分页，限制单页最大100条

2. **删除操作误删**
   - 风险：用户误删重要数据
   - 缓解：确认对话框，显示记录详细信息，运行中作业不可删

3. **前后端数据格式不一致**
   - 风险：API返回格式与前端期望不符
   - 缓解：使用 TypeScript 接口严格定义，API测试覆盖

4. **React Query 缓存问题**
   - 风险：删除后列表未更新
   - 缓解：正确使用 invalidateQueries，测试删除后刷新

5. **响应式布局问题**
   - 风险：小屏幕上表格显示异常
   - 缓解：使用 Tailwind 响应式类，测试不同屏幕尺寸

---

## 开发时间估算

- Task 1-2 (后端): 2小时
- Task 3-8 (前端组件): 2小时
- Task 9-10 (页面和导航): 1小时
- Task 11-12 (测试和优化): 1.5小时

**总计: 6.5小时**

实际时间可能因开发经验和问题复杂度有所差异。

---

## 完成后的下一步

功能完成后，可以考虑：
1. 添加批量删除功能
2. 添加导出为 CSV/JSON 功能
3. 添加结果对比功能
4. 优化大量数据的加载性能（虚拟滚动）
5. 添加收藏/标签功能
