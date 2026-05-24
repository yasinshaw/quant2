# 已下载数据列表侧边栏设计文档

**日期：** 2026-03-24
**功能：** 在数据管理页面添加左侧侧边栏，展示已下载的历史数据列表及时间范围

## 1. 功能概述

### 1.1 目标
为用户提供一个清晰、便捷的视图来查看所有已下载的历史数据，包括：
- 每个 symbol 下的所有 interval
- 每个数据集的时间范围（开始时间 - 结束时间）
- K线数量统计
- 快速切换到已下载数据集的能力

### 1.2 用户体验
- 左侧固定侧边栏，宽度 300px
- 按 symbol 分组，默认折叠
- 点击 symbol 展开显示所有 interval
- 点击数据项自动填充右侧表单
- 清晰的视觉反馈和交互效果

## 2. 系统架构

### 2.1 技术栈
- **后端：** FastAPI + SQLAlchemy + SQLite
- **前端：** Next.js 14 + TypeScript + Tailwind CSS + React Query
- **API：** RESTful API，JSON 响应格式

### 2.2 数据流
```
用户点击侧边栏
  ↓
React Query 发起请求
  ↓
GET /api/v1/data/downloaded
  ↓
Database.get_downloaded_data_summary()
  ↓
SQL 查询（GROUP BY symbol, interval）
  ↓
返回聚合数据
  ↓
前端渲染列表
```

## 3. 后端设计

### 3.1 数据库层

**文件：** `backend/database.py`

**新增方法：** `get_downloaded_data_summary()`

```python
def get_downloaded_data_summary(self) -> List[Dict[str, Any]]:
    """
    获取所有已下载数据的摘要信息

    使用 GROUP BY 聚合查询，按 symbol 和 interval 分组，
    计算每个组的统计数据：
    - K线数量 (COUNT)
    - 最早时间 (MIN open_time)
    - 最晚时间 (MAX open_time)

    Returns:
        List[Dict]: 按 symbol 分组的数据摘要列表
    """
    with self.get_session() as session:
        # 查询所有启用的 symbol
        symbols = session.query(Symbol).filter(
            Symbol.enabled == True
        ).order_by(Symbol.name).all()

        result = []
        for symbol in symbols:
            # 聚合查询该 symbol 的所有 interval 数据
            intervals_data = session.query(
                Candle.interval,
                func.count(Candle.id).label('count'),
                func.min(Candle.open_time).label('start_time'),
                func.max(Candle.open_time).label('end_time')
            ).filter(
                Candle.symbol_id == symbol.id
            ).group_by(Candle.interval).all()

            # 只包含有数据的 symbol
            if intervals_data:
                result.append({
                    "symbol": symbol.name,
                    "intervals": [
                        {
                            "interval": interval,
                            "count": count,
                            "start_time": start_time,
                            "end_time": end_time
                        }
                        for interval, count, start_time, end_time in intervals_data
                    ]
                })

        return result
```

**查询性能考虑：**
- 利用现有的索引 `idx_candles_lookup`
- GROUP BY 聚合在数据库层完成，减少数据传输
- 按 symbol 排序，提供一致的展示顺序

### 3.2 API 层

**文件：** `backend/api/data.py`

**新增端点：** `GET /api/v1/data/downloaded`

**请求：**
```
GET /api/v1/data/downloaded
```

**响应：**
```json
{
  "data": [
    {
      "symbol": "BTCUSDT",
      "intervals": [
        {
          "interval": "1h",
          "count": 8760,
          "start_time": "2024-01-01T00:00:00",
          "end_time": "2024-12-31T23:00:00"
        },
        {
          "interval": "1d",
          "count": 365,
          "start_time": "2024-01-01T00:00:00",
          "end_time": "2024-12-31T00:00:00"
        }
      ]
    },
    {
      "symbol": "ETHUSDT",
      "intervals": [
        {
          "interval": "1h",
          "count": 4380,
          "start_time": "2024-07-01T00:00:00",
          "end_time": "2024-12-31T23:00:00"
        }
      ]
    }
  ]
}
```

**实现：**
```python
@router.get("/downloaded")
async def get_downloaded_data() -> Dict[str, Any]:
    """
    获取所有已下载数据的摘要列表

    返回所有已下载的历史数据，按 symbol 分组，包含每个 interval 的
    时间范围和 K 线数量信息。

    Returns:
        Dict with "data" key containing list of symbol summaries

    Raises:
        HTTPException: 500 if database error occurs
    """
    try:
        summary = _db.get_downloaded_data_summary()

        # 转换 datetime 为 ISO 字符串
        for symbol_data in summary:
            for interval_data in symbol_data["intervals"]:
                interval_data["start_time"] = interval_data["start_time"].isoformat()
                interval_data["end_time"] = interval_data["end_time"].isoformat()

        return {"data": summary}
    except Exception as e:
        logger.error(f"Failed to get downloaded data summary: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve downloaded data"
        )
```

**错误处理：**
- 捕获所有异常，返回 500 错误
- 记录详细错误日志（包括堆栈跟踪）
- 返回用户友好的错误消息

## 4. 前端设计

### 4.1 API 客户端

**文件：** `frontend/lib/api/data.ts`

**新增类型定义：**
```typescript
export interface DownloadedInterval {
  interval: string;
  count: number;
  start_time: string;
  end_time: string;
}

export interface DownloadedDataItem {
  symbol: string;
  intervals: DownloadedInterval[];
}
```

**新增方法：**
```typescript
export const dataApi = {
  // ... 现有方法

  getDownloadedData: async (): Promise<DownloadedDataItem[]> => {
    const response = await axios.get(`${API_BASE_URL}/api/v1/data/downloaded`);
    return response.data.data;
  },
};
```

### 4.2 侧边栏组件

**文件：** `frontend/components/DownloadedDataSidebar.tsx`

**Props 接口：**
```typescript
interface Props {
  onSymbolSelect: (symbol: string, interval: string) => void;
  selectedSymbol?: string;
  selectedInterval?: string;
}
```

**状态管理：**
```typescript
// 数据获取
const { data, isLoading, error } = useQuery({
  queryKey: ['downloadedData'],
  queryFn: dataApi.getDownloadedData,
  staleTime: 30000, // 30秒内使用缓存
  refetchOnWindowFocus: true, // 窗口聚焦时重新获取
});

// 展开/折叠状态
const [expandedSymbols, setExpandedSymbols] = useState<Set<string>>(new Set());
```

**组件功能：**

1. **加载状态：** 显示骨架屏
   - 3-5 个骨架项
   - 使用动画效果

2. **空状态：** 显示友好提示
   ```
   暂无已下载数据
   请先下载历史数据
   ```

3. **错误状态：** 显示错误信息
   - 红色警告框
   - 重试按钮

4. **列表渲染：**
   - 按 symbol 分组
   - 每个组有展开/折叠按钮（▶ / ▼）
   - 展开后显示所有 interval

5. **数据项显示：**
   ```
   BTCUSDT  ▼
     1h
     2024-01-01 ~ 2024-12-31
     8,760 条
   ```

6. **交互：**
   - 点击 symbol：切换展开/折叠
   - 点击数据项：触发 `onSymbolSelect(symbol, interval)`
   - 当前选中项高亮显示（蓝色背景）

**样式设计：**
```typescript
// 容器
className="w-[300px] h-screen sticky top-0 bg-white border-r border-gray-200 overflow-y-auto"

// 标题
className="p-4 border-b border-gray-200"
className="text-lg font-semibold text-gray-900"

// Symbol 分组
className="border-b border-gray-100"
className="p-3 hover:bg-gray-50 cursor-pointer transition-colors"

// Interval 列表
className="bg-gray-50"
className="p-3 pl-6 hover:bg-blue-50 cursor-pointer transition-colors"

// 选中状态
className="bg-blue-100 border-l-4 border-blue-500"
```

### 4.3 页面布局更新

**文件：** `frontend/app/data/page.tsx`

**布局变化：**
```typescript
// 原有：单列布局
<div className="min-h-screen bg-gray-50 p-8">
  <div className="max-w-7xl mx-auto">
    {/* 内容 */}
  </div>
</div>

// 新增：两列布局
<div className="min-h-screen bg-gray-50">
  <div className="flex">
    {/* 左侧侧边栏 */}
    <div className="w-[300px] flex-shrink-0">
      <DownloadedDataSidebar
        onSymbolSelect={handleSymbolSelect}
        selectedSymbol={selectedSymbol}
        selectedInterval={selectedInterval}
      />
    </div>

    {/* 右侧主内容 */}
    <div className="flex-1 min-w-0 p-8">
      <div className="max-w-7xl mx-auto">
        {/* 原有内容 */}
      </div>
    </div>
  </div>
</div>
```

**新增方法：**
```typescript
const handleSymbolSelect = (symbol: string, interval: string) => {
  // 更新选中的 symbol 和 interval
  setSelectedSymbol(symbol);
  setSelectedInterval(interval);

  // 清除之前的下载结果
  setDownloadResult(null);

  // 可选：滚动到顶部，方便用户看到更新的表单
  window.scrollTo({ top: 0, behavior: 'smooth' });
};
```

**响应式设计（可选扩展）：**
- 移动端（< 768px）：侧边栏可收起/展开
- 添加汉堡菜单按钮
- 使用 `useState` 管理侧边栏显示状态

## 5. 数据流与交互

### 5.1 数据加载流程
```
1. 页面加载
   ↓
2. DownloadedDataSidebar 挂载
   ↓
3. React Query 发起 GET /api/v1/data/downloaded
   ↓
4. 显示加载骨架屏
   ↓
5. 数据返回，渲染列表
   ↓
6. 用户点击 symbol 展开
   ↓
7. 用户点击 interval
   ↓
8. 触发 onSymbolSelect(symbol, interval)
   ↓
9. 父组件更新 selectedSymbol 和 selectedInterval
   ↓
10. 右侧表单自动更新，DataStatusCard 刷新
```

### 5.2 状态同步
- **Symbol/Interval 选择：** 从侧边栏点击 → 更新父组件状态 → 右侧表单自动同步
- **数据下载：** 下载成功后 → React Query invalidate → 侧边栏自动刷新
- **缓存策略：** 30 秒 staleTime，平衡性能和实时性

### 5.3 边界情况处理
1. **无数据：** 显示空状态提示
2. **网络错误：** 显示错误信息 + 重试按钮
3. **大量数据：** 虚拟滚动（如果 symbols > 50）
4. **长 symbol 名称：** 文本截断 + tooltip 显示完整名称

## 6. 性能优化

### 6.1 后端优化
- **索引利用：** 使用现有的 `idx_candles_lookup` 索引
- **聚合查询：** 在数据库层完成聚合，减少数据传输
- **惰性加载：** 只查询启用的 symbol

### 6.2 前端优化
- **React Query 缓存：** 30 秒内复用缓存数据
- **组件记忆化：** 使用 `React.memo` 优化子组件渲染
- **虚拟滚动：** 如果数据量大，考虑使用 `react-window`
- **骨架屏：** 提升感知性能

## 7. 测试策略

### 7.1 后端测试
**文件：** `tests/test_data_api.py`

**测试用例：**
1. `test_get_downloaded_data_empty` - 无数据时返回空列表
2. `test_get_downloaded_data_single_symbol` - 单个 symbol 的数据
3. `test_get_downloaded_data_multiple_symbols` - 多个 symbol 的数据
4. `test_get_downloaded_data_multiple_intervals` - 多个 interval 的数据
5. `test_get_downloaded_data_response_format` - 验证响应格式

**测试方法：**
- 使用 FastAPI TestClient
- 使用内存 SQLite 数据库
- 预先插入测试数据
- 验证响应状态码和数据结构

### 7.2 前端测试
**文件：** `frontend/e2e/data-sidebar.spec.ts`

**测试用例：**
1. 侧边栏正常显示
2. Symbol 展开/折叠功能
3. 点击数据项更新表单
4. 加载状态显示
5. 空状态显示

**测试方法：**
- Playwright E2E 测试
- 启动开发服务器
- 模拟后端 API 响应
- 验证 UI 交互

## 8. 实现计划

### 8.1 开发步骤
1. **后端实现**（约 30 分钟）
   - [ ] 在 `database.py` 添加 `get_downloaded_data_summary()` 方法
   - [ ] 在 `data.py` API 添加 `GET /downloaded` 端点
   - [ ] 编写后端单元测试
   - [ ] 手动测试 API 响应

2. **前端实现**（约 45 分钟）
   - [ ] 在 `lib/api/data.ts` 添加类型定义和 API 方法
   - [ ] 创建 `components/DownloadedDataSidebar.tsx` 组件
   - [ ] 更新 `app/data/page.tsx` 布局
   - [ ] 样式调整和交互优化
   - [ ] 编写 E2E 测试

3. **测试与验证**（约 15 分钟）
   - [ ] 运行所有测试
   - [ ] 手动测试完整流程
   - [ ] 检查边界情况
   - [ ] 性能测试（大量数据）

### 8.2 验收标准
- [ ] 侧边栏正确显示所有已下载数据
- [ ] Symbol 分组和展开/折叠功能正常
- [ ] 点击数据项自动更新右侧表单
- [ ] 加载、空状态、错误状态正确显示
- [ ] 所有测试通过（后端 + 前端）
- [ ] 响应时间 < 500ms（1000 条数据内）

## 9. 未来扩展

### 9.1 短期优化
- 添加搜索功能（搜索 symbol）
- 添加排序选项（按 symbol、数据量、时间范围）
- 添加删除数据功能
- 添加数据导出功能

### 9.2 长期规划
- 数据质量检查（缺失检测）
- 数据可视化（时间线图表）
- 多语言支持
- 主题切换（暗色模式）

## 10. 风险与缓解

### 10.1 潜在风险
1. **性能问题：** 大量数据时查询缓慢
   - **缓解：** 添加索引，考虑分页

2. **状态同步：** 下载新数据后侧边栏未更新
   - **缓解：** 使用 React Query 的 invalidate 机制

3. **响应式布局：** 小屏幕上侧边栏占用过多空间
   - **缓解：** 实现可收起的侧边栏

### 10.2 技术债务
- 当前未实现虚拟滚动，数据量大时可能卡顿
- 未实现数据删除功能，需要手动操作数据库
- 未实现数据质量检查（缺失、异常值）

## 11. 总结

本设计通过添加左侧侧边栏，为用户提供了一个清晰、高效的已下载数据视图。设计遵循以下原则：

1. **简洁性：** 显示必要信息，避免信息过载
2. **可用性：** 直观的交互，快速切换数据集
3. **性能：** 优化的查询和缓存策略
4. **可扩展性：** 易于添加新功能（搜索、删除等）

该功能将显著提升用户体验，特别是在管理多个 symbol 和 interval 的历史数据时。
