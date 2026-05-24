# 回测和参数调优历史记录功能设计

**日期：** 2026-03-25
**状态：** 设计阶段
**方案：** 方案一 - 最小化实现

## 一、概述

### 背景
当前系统已经在数据库中保存了所有回测和参数调优的结果，但前端缺少历史记录查看功能。用户无法方便地查看过往的回测和调优记录。

### 目标
为回测和参数调优功能添加历史记录查看页面，支持：
- 分页查看历史记录
- 按策略、交易对、状态筛选
- 按时间、收益率等指标排序
- 删除不需要的历史记录
- 点击查看详细信息

### 范围
- 后端：新增历史查询和删除API
- 前端：新增历史页面，包含回测和参数调优两个标签页
- 不包括：编辑历史记录、批量删除、导出功能

## 二、架构设计

### 整体架构
```
┌─────────────┐
│   Frontend  │
│  (Next.js)  │
└──────┬──────┘
       │ HTTP/REST
       ▼
┌─────────────┐
│   Backend   │
│  (FastAPI)  │
└──────┬──────┘
       │ SQLAlchemy
       ▼
┌─────────────┐
│   SQLite    │
│  Database   │
└─────────────┘
```

### 数据流
1. 用户访问 `/history` 页面
2. 前端调用历史API获取分页数据
3. 后端查询数据库，返回历史记录列表
4. 前端展示列表，支持筛选和排序
5. 用户点击记录查看详情或删除

## 三、后端设计

### 3.1 API端点设计

#### 回测历史API

**获取回测历史列表**
```
GET /api/v1/backtest/history
```

**查询参数：**
- `strategy_name` (string, optional): 策略名称筛选
- `symbol` (string, optional): 交易对筛选
- `status` (string, optional): 状态筛选 (pending/running/completed/failed)
- `sort_by` (string, optional): 排序字段，默认 `created_at`
- `sort_order` (string, optional): `asc` 或 `desc`，默认 `desc`
- `page` (integer, optional): 页码，默认 1
- `page_size` (integer, optional): 每页数量，默认 20，最大 100

**响应示例：**
```json
{
  "total": 45,
  "page": 1,
  "page_size": 20,
  "total_pages": 3,
  "items": [
    {
      "id": 12,
      "strategy_name": "DoubleMAStrategy",
      "symbol": "BTCUSDT",
      "interval": "1h",
      "start_time": "2024-01-01T00:00:00",
      "end_time": "2024-03-01T00:00:00",
      "status": "completed",
      "total_return": 15.6,
      "sharpe_ratio": 1.8,
      "max_drawdown": -8.2,
      "total_trades": 42,
      "created_at": "2024-03-15T10:30:00",
      "completed_at": "2024-03-15T10:31:45"
    }
  ]
}
```

**删除回测记录**
```
DELETE /api/v1/backtest/jobs/{job_id}
```

**响应示例：**
```json
{
  "success": true,
  "message": "Backtest job deleted successfully"
}
```

**错误响应：**
- 404: Job not found
- 400: Cannot delete running job

---

#### 参数调优历史API

**获取调优历史列表**
```
GET /api/v1/optimization/history
```

**查询参数：** 同回测历史API

**响应示例：**
```json
{
  "total": 15,
  "page": 1,
  "page_size": 20,
  "total_pages": 1,
  "items": [
    {
      "id": 8,
      "strategy_name": "RSIStrategy",
      "symbol": "ETHUSDT",
      "interval": "4h",
      "start_time": "2024-01-01T00:00:00",
      "end_time": "2024-03-01T00:00:00",
      "status": "completed",
      "best_score": 2.1,
      "best_parameters": {
        "rsi_period": 14,
        "oversold": 30,
        "overbought": 70
      },
      "total_combinations": 27,
      "created_at": "2024-03-14T15:20:00",
      "completed_at": "2024-03-14T15:35:20"
    }
  ]
}
```

**删除调优记录**
```
DELETE /api/v1/optimization/jobs/{job_id}
```

**响应示例：**
```json
{
  "success": true,
  "message": "Optimization job deleted successfully"
}
```

---

### 3.2 数据库层实现

在 `backend/database.py` 中添加以下方法：

```python
def get_backtest_history(
    self,
    strategy_name: Optional[str] = None,
    symbol: Optional[str] = None,
    status: Optional[str] = None,
    sort_by: str = 'created_at',
    sort_order: str = 'desc',
    page: int = 1,
    page_size: int = 20
) -> Dict[str, Any]:
    """
    Get paginated backtest history with filters and sorting.

    Returns:
        Dict with keys: total, page, page_size, total_pages, items
    """

def delete_backtest_job(self, job_id: int) -> bool:
    """
    Delete backtest job and all related records (result, trades).
    Prevents deletion of running jobs.

    Raises:
        ValueError: If job is running or not found
    """

def get_optimization_history(
    self,
    strategy_name: Optional[str] = None,
    symbol: Optional[str] = None,
    status: Optional[str] = None,
    sort_by: str = 'created_at',
    sort_order: str = 'desc',
    page: int = 1,
    page_size: int = 20
) -> Dict[str, Any]:
    """
    Get paginated optimization history with filters and sorting.

    Returns:
        Dict with keys: total, page, page_size, total_pages, items
    """

def delete_optimization_job(self, job_id: int) -> bool:
    """
    Delete optimization job and all related results.
    Prevents deletion of running jobs.

    Raises:
        ValueError: If job is running or not found
    """
```

**实现细节：**
- 使用 SQLAlchemy 的 `join` 查询 BacktestJob 和 BacktestResult
- 使用 `func.count()` 获取总数
- 使用 `offset()` 和 `limit()` 实现分页
- 排序支持字段：`created_at`, `total_return`, `sharpe_ratio`
- 删除时检查状态，防止删除正在运行的作业
- 利用现有的级联删除（cascade="all, delete-orphan"）自动删除关联记录

---

### 3.3 API层实现

在 `backend/api/backtest.py` 中添加端点：

```python
@router.get("/history")
async def get_backtest_history(
    strategy_name: Optional[str] = Query(None),
    symbol: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    sort_by: str = Query("created_at"),
    sort_order: str = Query("desc"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100)
) -> Dict[str, Any]:
    """Get paginated backtest history with filters"""

@router.delete("/jobs/{job_id}", status_code=status.HTTP_200_OK)
async def delete_backtest_job(job_id: int) -> Dict[str, Any]:
    """Delete a backtest job and its related records"""

@router.get("/optimization/history")
async def get_optimization_history(
    strategy_name: Optional[str] = Query(None),
    symbol: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    sort_by: str = Query("created_at"),
    sort_order: str = Query("desc"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100)
) -> Dict[str, Any]:
    """Get paginated optimization history with filters"""

@router.delete("/optimization/jobs/{job_id}", status_code=status.HTTP_200_OK)
async def delete_optimization_job(job_id: int) -> Dict[str, Any]:
    """Delete an optimization job and its related records"""
```

**错误处理：**
- 404: 记录不存在
- 400: 尝试删除正在运行的作业
- 500: 数据库错误

## 四、前端设计

### 4.1 页面结构

**路由：** `/history`

**布局：**
```
┌─────────────────────────────────────────────────┐
│  History - 历史记录                              │
│  ┌──────────────────────────────────────────┐  │
│  │  [Backtests]  [Optimizations]            │  │
│  └──────────────────────────────────────────┘  │
│                                                 │
│  ┌──────────────────────────────────────────┐  │
│  │  Filters:                                │  │
│  │  [Strategy ▼] [Symbol ▼] [Status ▼]     │  │
│  │  [Clear Filters]                         │  │
│  └──────────────────────────────────────────┘  │
│                                                 │
│  ┌──────────────────────────────────────────┐  │
│  │  Table Header                            │  │
│  │  ──────────────────────────────────────  │  │
│  │  Row 1  [View] [Delete]                  │  │
│  │  Row 2  [View] [Delete]                  │  │
│  │  Row 3  [View] [Delete]                  │  │
│  │  ...                                     │  │
│  └──────────────────────────────────────────┘  │
│                                                 │
│  ┌──────────────────────────────────────────┐  │
│  │  [Previous]  Page 1 of 3  [Next]         │  │
│  └──────────────────────────────────────────┘  │
└─────────────────────────────────────────────────┘
```

---

### 4.2 组件设计

#### 主要组件

**1. HistoryPage (`frontend/app/history/page.tsx`)**
- 主页面容器
- 管理标签页状态（回测/调优）
- 管理筛选器和分页状态
- 使用 React Query 获取数据

**2. HistoryTabs (`frontend/components/HistoryTabs.tsx`)**
- 标签页切换组件
- Props: `activeTab`, `onTabChange`
- 两个标签：Backtests, Optimizations

**3. HistoryFilters (`frontend/components/HistoryFilters.tsx`)**
- 筛选器组件
- Props: `filters`, `onFilterChange`, `onClear`
- 下拉菜单：策略、交易对、状态
- 清除筛选按钮

**4. BacktestHistoryTable (`frontend/components/BacktestHistoryTable.tsx`)**
- 回测历史表格
- Props: `data`, `onDelete`, `onView`
- 列：策略、交易对/周期、时间范围、状态、收益率、夏普比率、最大回撤、交易数、创建时间、操作
- 状态颜色：completed=绿色, failed=红色, running=蓝色, pending=灰色

**5. OptimizationHistoryTable (`frontend/components/OptimizationHistoryTable.tsx`)**
- 调优历史表格
- Props: `data`, `onDelete`, `onView`
- 列：策略、交易对/周期、时间范围、状态、最佳得分、参数组合数、创建时间、操作

**6. Pagination (`frontend/components/Pagination.tsx`)**
- 分页组件
- Props: `currentPage`, `totalPages`, `onPageChange`
- 显示：上一页、页码、下一页

---

#### 表格列详细设计

**回测历史表格列：**

| 列名 | 字段 | 格式 | 对齐 |
|------|------|------|------|
| Strategy | strategy_name | 文本 | 左对齐 |
| Symbol / Interval | symbol + interval | BTCUSDT / 1h | 左对齐 |
| Time Range | start_time ~ end_time | 2024-01-01 ~ 2024-03-01 | 左对齐 |
| Status | status | Badge (带颜色) | 居中 |
| Total Return | total_return | +15.6% (颜色: 正/负) | 右对齐 |
| Sharpe Ratio | sharpe_ratio | 1.80 | 右对齐 |
| Max Drawdown | max_drawdown | -8.2% (红色) | 右对齐 |
| Trades | total_trades | 42 | 右对齐 |
| Created At | created_at | 2024-03-15 10:30 | 左对齐 |
| Actions | - | [View] [Delete] | 居中 |

**调优历史表格列：**

| 列名 | 字段 | 格式 | 对齐 |
|------|------|------|------|
| Strategy | strategy_name | 文本 | 左对齐 |
| Symbol / Interval | symbol + interval | ETHUSDT / 4h | 左对齐 |
| Time Range | start_time ~ end_time | 2024-01-01 ~ 2024-03-01 | 左对齐 |
| Status | status | Badge (带颜色) | 居中 |
| Best Score | best_score | 2.10 | 右对齐 |
| Combinations | total_combinations | 27 | 右对齐 |
| Created At | created_at | 2024-03-14 15:20 | 左对齐 |
| Actions | - | [View] [Delete] | 居中 |

---

### 4.3 API客户端

**文件：** `frontend/lib/api/history.ts`

```typescript
export interface HistoryQueryParams {
  strategy_name?: string;
  symbol?: string;
  status?: string;
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
  page?: number;
  page_size?: number;
}

export interface PaginatedResponse<T> {
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
  items: T[];
}

export interface BacktestHistoryItem {
  id: number;
  strategy_name: string;
  symbol: string;
  interval: string;
  start_time: string;
  end_time: string;
  status: string;
  total_return: number;
  sharpe_ratio: number;
  max_drawdown: number;
  total_trades: number;
  created_at: string;
  completed_at?: string;
}

export interface OptimizationHistoryItem {
  id: number;
  strategy_name: string;
  symbol: string;
  interval: string;
  start_time: string;
  end_time: string;
  status: string;
  best_score: number;
  best_parameters: Record<string, any>;
  total_combinations: number;
  created_at: string;
  completed_at?: string;
}

export const historyApi = {
  getBacktestHistory: async (params: HistoryQueryParams): Promise<PaginatedResponse<BacktestHistoryItem>> => {
    const response = await axios.get(`${API_BASE_URL}/api/v1/backtest/history`, { params });
    return response.data;
  },

  deleteBacktestJob: async (jobId: number): Promise<void> => {
    await axios.delete(`${API_BASE_URL}/api/v1/backtest/jobs/${jobId}`);
  },

  getOptimizationHistory: async (params: HistoryQueryParams): Promise<PaginatedResponse<OptimizationHistoryItem>> => {
    const response = await axios.get(`${API_BASE_URL}/api/v1/optimization/history`, { params });
    return response.data;
  },

  deleteOptimizationJob: async (jobId: number): Promise<void> => {
    await axios.delete(`${API_BASE_URL}/api/v1/optimization/jobs/${jobId}`);
  }
};
```

---

### 4.4 状态管理

使用 React Query 管理服务器状态：

```typescript
// 查询回测历史
const {
  data: backtestHistory,
  isLoading,
  error,
  refetch
} = useQuery({
  queryKey: ['backtest-history', filters, page],
  queryFn: () => historyApi.getBacktestHistory({ ...filters, page }),
  keepPreviousData: true
});

// 删除回测记录
const deleteMutation = useMutation({
  mutationFn: historyApi.deleteBacktestJob,
  onSuccess: () => {
    queryClient.invalidateQueries(['backtest-history']);
  }
});
```

---

### 4.5 用户交互流程

#### 查看历史列表
1. 用户点击导航栏 "History" 链接
2. 路由到 `/history` 页面
3. 默认显示回测历史标签页
4. 加载第一页数据（20条记录）
5. 按创建时间倒序显示

#### 筛选记录
1. 用户选择筛选条件（策略/交易对/状态）
2. 触发 `onFilterChange` 回调
3. 更新 `filters` 状态
4. React Query 自动重新获取数据
5. 显示筛选后的结果

#### 查看详情
1. 用户点击表格行的 "View" 按钮
2. 回测：路由到 `/results/[id]`（已存在）
3. 调优：路由到 `/optimization-results/[id]`（需新建或复用回测详情页）

#### 删除记录
1. 用户点击 "Delete" 按钮
2. 弹出确认对话框："确定要删除这条记录吗？此操作不可撤销。"
3. 用户确认
4. 调用删除 API
5. 成功后刷新列表
6. 显示成功提示："记录已删除"

#### 分页浏览
1. 用户点击 "Next" 或 "Previous" 按钮
2. 更新 `page` 状态
3. React Query 自动获取新页面数据
4. 显示加载状态
5. 显示新页面内容

---

### 4.6 错误处理

**加载错误：**
- 显示错误消息："加载失败，请重试"
- 提供 "Retry" 按钮

**删除错误：**
- 显示错误消息："删除失败：{错误原因}"
- 记录正在运行时："无法删除正在运行的任务"

**空状态：**
- 无记录时显示："暂无历史记录"
- 无筛选结果时："未找到符合条件的记录"

---

### 4.7 样式设计

**表格样式：**
- 斑马纹背景（奇偶行不同颜色）
- Hover 时高亮行
- 响应式设计：小屏幕时水平滚动

**状态徽章：**
- Completed: 绿色背景
- Failed: 红色背景
- Running: 蓝色背景，带动画
- Pending: 灰色背景

**数值颜色：**
- 正收益：绿色
- 负收益：红色
- 零/中性：灰色

---

## 五、文件清单

### 后端文件

**新增：** 无

**修改：**
1. `backend/api/backtest.py` - 添加历史查询和删除端点
2. `backend/database.py` - 添加历史查询和删除方法

### 前端文件

**新增：**
1. `frontend/app/history/page.tsx` - 历史页面主组件
2. `frontend/components/HistoryTabs.tsx` - 标签页组件
3. `frontend/components/HistoryFilters.tsx` - 筛选器组件
4. `frontend/components/BacktestHistoryTable.tsx` - 回测历史表格
5. `frontend/components/OptimizationHistoryTable.tsx` - 调优历史表格
6. `frontend/components/Pagination.tsx` - 分页组件
7. `frontend/lib/api/history.ts` - 历史API客户端

**修改：**
1. `frontend/components/Navigation.tsx` - 添加 "History" 导航链接
2. `frontend/app/page.tsx` - 更新首页统计数据（可选）

---

## 六、测试计划

### 后端测试

**单元测试：**
- `test_get_backtest_history` - 测试历史查询功能
- `test_get_backtest_history_with_filters` - 测试筛选功能
- `test_get_backtest_history_pagination` - 测试分页功能
- `test_delete_backtest_job` - 测试删除功能
- `test_delete_running_job_fails` - 测试删除运行中作业失败
- `test_get_optimization_history` - 测试调优历史查询
- `test_delete_optimization_job` - 测试调优删除

**集成测试：**
- 使用 FastAPI TestClient 测试完整API流程
- 测试数据库级联删除
- 测试并发请求

### 前端测试

**E2E测试（Playwright）：**
1. `test_view_backtest_history` - 查看回测历史
2. `test_filter_backtest_history` - 筛选回测历史
3. `test_delete_backtest_record` - 删除回测记录
4. `test_view_optimization_history` - 查看调优历史
5. `test_pagination` - 分页功能
6. `test_tab_switching` - 标签页切换

**测试场景：**
- 空列表显示
- 加载错误处理
- 删除确认对话框
- 筛选器清除
- 页码跳转

---

## 七、实现步骤

### 阶段一：后端实现（1-2小时）
1. 在 `database.py` 中实现历史查询方法
2. 在 `database.py` 中实现删除方法
3. 在 `backtest.py` 中添加API端点
4. 编写后端单元测试
5. 使用 pytest 验证功能

### 阶段二：前端基础组件（1小时）
1. 创建 `lib/api/history.ts` API客户端
2. 创建 `Pagination.tsx` 分页组件
3. 创建 `HistoryFilters.tsx` 筛选器组件
4. 创建 `HistoryTabs.tsx` 标签页组件

### 阶段三：前端页面实现（1-2小时）
1. 创建 `BacktestHistoryTable.tsx` 表格组件
2. 创建 `OptimizationHistoryTable.tsx` 表格组件
3. 创建 `history/page.tsx` 主页面
4. 更新导航栏添加 "History" 链接

### 阶段四：测试和调试（1小时）
1. 编写E2E测试
2. 手动测试所有功能
3. 修复发现的问题
4. 优化性能和用户体验

**预计总时间：** 4-6小时

---

## 八、未来扩展

虽然当前采用最小化实现，但设计考虑了未来扩展的可能性：

### 可能的扩展功能
1. **批量操作** - 批量删除、批量导出
2. **高级筛选** - 时间范围、收益率范围、多条件组合
3. **导出功能** - 导出为CSV、JSON、PDF
4. **结果对比** - 并排对比两次回测/调优结果
5. **快速重跑** - 从历史记录快速重新运行回测
6. **收藏功能** - 标记重要的回测结果
7. **标签系统** - 为记录添加自定义标签
8. **统计面板** - 显示总体统计信息（平均收益率、成功率等）

### 性能优化
- 虚拟滚动（处理大量记录）
- 后端缓存热门查询
- 延迟加载详细数据

---

## 九、风险和缓解

### 风险1：删除操作误删重要数据
**缓解措施：**
- 删除前显示确认对话框
- 显示记录的详细信息（策略、时间范围、收益率）
- 考虑添加"软删除"功能（标记为已删除而非物理删除）

### 风险2：大量历史记录导致性能问题
**缓解措施：**
- 强制分页，每页最多100条
- 数据库索引优化（已有status索引）
- 限制单次查询返回的数据量

### 风险3：删除运行中的作业
**缓解措施：**
- 后端检查作业状态
- 禁止删除状态为 `running` 的作业
- 前端禁用运行中作业的删除按钮

---

## 十、验收标准

### 功能验收
- [ ] 可以查看回测历史列表（分页）
- [ ] 可以查看参数调优历史列表（分页）
- [ ] 可以按策略、交易对、状态筛选
- [ ] 可以按创建时间、收益率、夏普比率排序
- [ ] 可以删除历史记录（带确认）
- [ ] 可以点击记录查看详细信息
- [ ] 可以在两个标签页间切换

### 性能验收
- [ ] 首次加载时间 < 1秒（100条记录）
- [ ] 筛选响应时间 < 500ms
- [ ] 删除操作响应时间 < 300ms

### 用户体验验收
- [ ] 加载时显示骨架屏或加载指示器
- [ ] 错误时显示友好的错误消息
- [ ] 空状态时显示明确的提示
- [ ] 响应式设计，支持移动端访问

### 代码质量验收
- [ ] 后端测试覆盖率 > 80%
- [ ] 前端E2E测试覆盖主要流程
- [ ] 代码通过 lint 检查
- [ ] 无 TypeScript 类型错误

---

## 十一、总结

本设计文档详细描述了回测和参数调优历史记录功能的实现方案。采用最小化实现策略，复用现有的详情页面，专注于核心功能：查看、筛选、排序、删除。

**关键设计决策：**
1. 使用标签页分离回测和调优历史
2. 服务端分页，每页20条记录
3. 支持多维度筛选和排序
4. 删除前确认，防止误操作
5. 复用现有详情页，减少开发工作量

**实现优先级：**
1. 后端API（核心功能）
2. 前端基础组件（可复用）
3. 前端页面（整合组件）
4. 测试（保证质量）

这个方案在满足用户需求的同时，保持了代码的简洁性和可维护性，为未来的功能扩展预留了空间。
