# 已下载数据侧边栏实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在数据管理页面添加左侧侧边栏，展示已下载的历史数据列表及时间范围，支持快速切换数据集

**Architecture:** 后端添加聚合查询 API，前端使用 React Query 管理状态，侧边栏组件按 symbol 分组展示数据，点击数据项自动填充表单

**Tech Stack:** FastAPI + SQLAlchemy + SQLite (backend), Next.js 14 + TypeScript + Tailwind CSS + React Query (frontend)

---

## Task 1: 后端数据库层 - 添加聚合查询方法

**Files:**
- Modify: `backend/database.py:270` (after get_candles_count method)

- [ ] **Step 1: 添加 func 导入**

在文件顶部的导入部分添加：
```python
from sqlalchemy import create_engine, event, func
```

- [ ] **Step 2: 编写失败的测试**

在 `tests/test_database.py` 添加测试：

```python
def test_get_downloaded_data_summary_empty(db):
    """测试空数据库返回空列表"""
    result = db.get_downloaded_data_summary()
    assert result == []


def test_get_downloaded_data_summary_single_symbol(db):
    """测试单个 symbol 的数据摘要"""
    # 创建测试数据
    from datetime import datetime
    from backend.database import CandleData

    symbol = db.get_or_create_symbol("BTCUSDT")

    # 插入测试 K 线数据
    candles = [
        CandleData(
            symbol="BTCUSDT",
            interval="1h",
            open_time=datetime(2024, 1, 1, i),
            close_time=datetime(2024, 1, 1, i, 59, 59),
            open_price=42000.0,
            high_price=42500.0,
            low_price=41800.0,
            close_price=42300.0,
            volume=100.0
        )
        for i in range(10)
    ]
    db.save_candles(candles)

    # 查询摘要
    result = db.get_downloaded_data_summary()

    # 验证
    assert len(result) == 1
    assert result[0]["symbol"] == "BTCUSDT"
    assert len(result[0]["intervals"]) == 1
    assert result[0]["intervals"][0]["interval"] == "1h"
    assert result[0]["intervals"][0]["count"] == 10
    assert result[0]["intervals"][0]["start_time"] == datetime(2024, 1, 1, 0)
    assert result[0]["intervals"][0]["end_time"] == datetime(2024, 1, 1, 9)


def test_get_downloaded_data_summary_multiple_intervals(db):
    """测试多个 interval 的数据摘要"""
    from datetime import datetime
    from backend.database import CandleData

    symbol = db.get_or_create_symbol("ETHUSDT")

    # 插入 1h 数据
    candles_1h = [
        CandleData(
            symbol="ETHUSDT",
            interval="1h",
            open_time=datetime(2024, 1, 1, i),
            close_time=datetime(2024, 1, 1, i, 59, 59),
            open_price=2200.0,
            high_price=2250.0,
            low_price=2180.0,
            close_price=2230.0,
            volume=50.0
        )
        for i in range(5)
    ]

    # 插入 1d 数据
    candles_1d = [
        CandleData(
            symbol="ETHUSDT",
            interval="1d",
            open_time=datetime(2024, 1, i),
            close_time=datetime(2024, 1, i, 23, 59, 59),
            open_price=2200.0,
            high_price=2300.0,
            low_price=2100.0,
            close_price=2250.0,
            volume=500.0
        )
        for i in range(1, 4)
    ]

    db.save_candles(candles_1h + candles_1d)

    # 查询摘要
    result = db.get_downloaded_data_summary()

    # 验证
    assert len(result) == 1
    assert result[0]["symbol"] == "ETHUSDT"
    assert len(result[0]["intervals"]) == 2

    # 验证 interval 数据
    intervals = {item["interval"]: item for item in result[0]["intervals"]}
    assert "1h" in intervals
    assert "1d" in intervals
    assert intervals["1h"]["count"] == 5
    assert intervals["1d"]["count"] == 3
```

- [ ] **Step 3: 运行测试验证失败**

```bash
pytest tests/test_database.py::test_get_downloaded_data_summary_empty -v
pytest tests/test_database.py::test_get_downloaded_data_summary_single_symbol -v
pytest tests/test_database.py::test_get_downloaded_data_summary_multiple_intervals -v
```

Expected: FAIL with "AttributeError: 'Database' object has no attribute 'get_downloaded_data_summary'"

- [ ] **Step 4: 实现方法**

在 `backend/database.py` 的第 270 行后添加：

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

- [ ] **Step 5: 运行测试验证通过**

```bash
pytest tests/test_database.py::test_get_downloaded_data_summary_empty -v
pytest tests/test_database.py::test_get_downloaded_data_summary_single_symbol -v
pytest tests/test_database.py::test_get_downloaded_data_summary_multiple_intervals -v
```

Expected: All PASS

- [ ] **Step 6: 提交代码**

```bash
git add backend/database.py tests/test_database.py
git commit -m "feat(database): add get_downloaded_data_summary method

- Add method to query downloaded data summary grouped by symbol and interval
- Return count, start_time, and end_time for each interval
- Use GROUP BY aggregation for better performance"
```

---

## Task 2: 后端 API 层 - 添加下载列表端点

**Files:**
- Modify: `backend/api/data.py:275` (after get_data_status endpoint)

- [ ] **Step 1: 编写失败的测试**

在 `tests/test_data_api.py` 添加测试：

```python
def test_get_downloaded_data_empty(client):
    """测试空数据库返回空列表"""
    response = client.get("/api/v1/data/downloaded")
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert data["data"] == []


def test_get_downloaded_data_single_symbol(client, sample_candles):
    """测试单个 symbol 的数据"""
    # 先下载一些数据
    client.post("/api/v1/data/download", json={
        "symbol": "BTCUSDT",
        "interval": "1h",
        "start_time": "2024-01-01T00:00:00",
        "end_time": "2024-01-01T09:00:00"
    })

    response = client.get("/api/v1/data/downloaded")
    assert response.status_code == 200
    data = response.json()

    assert len(data["data"]) == 1
    assert data["data"][0]["symbol"] == "BTCUSDT"
    assert len(data["data"][0]["intervals"]) == 1

    interval = data["data"][0]["intervals"][0]
    assert interval["interval"] == "1h"
    assert interval["count"] == 10
    assert "start_time" in interval
    assert "end_time" in interval
    assert "T" in interval["start_time"]  # ISO format check


def test_get_downloaded_data_multiple_symbols(client):
    """测试多个 symbol 的数据"""
    # 下载 BTCUSDT 数据
    client.post("/api/v1/data/download", json={
        "symbol": "BTCUSDT",
        "interval": "1h",
        "start_time": "2024-01-01T00:00:00",
        "end_time": "2024-01-01T05:00:00"
    })

    # 下载 ETHUSDT 数据
    client.post("/api/v1/data/download", json={
        "symbol": "ETHUSDT",
        "interval": "1d",
        "start_time": "2024-01-01T00:00:00",
        "end_time": "2024-01-03T00:00:00"
    })

    response = client.get("/api/v1/data/downloaded")
    assert response.status_code == 200
    data = response.json()

    assert len(data["data"]) == 2

    # 验证按字母顺序排序
    symbols = [item["symbol"] for item in data["data"]]
    assert symbols == ["BTCUSDT", "ETHUSDT"]


def test_get_downloaded_data_response_format(client):
    """验证响应格式正确"""
    # 下载数据
    client.post("/api/v1/data/download", json={
        "symbol": "BTCUSDT",
        "interval": "1h",
        "start_time": "2024-01-01T00:00:00",
        "end_time": "2024-01-01T02:00:00"
    })

    response = client.get("/api/v1/data/downloaded")

    # 验证响应结构
    assert response.status_code == 200
    data = response.json()

    # 检查顶层结构
    assert isinstance(data, dict)
    assert "data" in data
    assert isinstance(data["data"], list)

    # 检查 symbol 结构
    symbol_data = data["data"][0]
    assert "symbol" in symbol_data
    assert "intervals" in symbol_data
    assert isinstance(symbol_data["intervals"], list)

    # 检查 interval 结构
    interval_data = symbol_data["intervals"][0]
    assert "interval" in interval_data
    assert "count" in interval_data
    assert "start_time" in interval_data
    assert "end_time" in interval_data

    # 验证类型
    assert isinstance(interval_data["interval"], str)
    assert isinstance(interval_data["count"], int)
    assert isinstance(interval_data["start_time"], str)
    assert isinstance(interval_data["end_time"], str)
```

- [ ] **Step 2: 运行测试验证失败**

```bash
pytest tests/test_data_api.py::test_get_downloaded_data_empty -v
pytest tests/test_data_api.py::test_get_downloaded_data_single_symbol -v
pytest tests/test_data_api.py::test_get_downloaded_data_multiple_symbols -v
pytest tests/test_data_api.py::test_get_downloaded_data_response_format -v
```

Expected: FAIL with 404 Not Found

- [ ] **Step 3: 实现 API 端点**

在 `backend/api/data.py` 的第 275 行后添加：

```python
@router.get("/downloaded")
async def get_downloaded_data() -> Dict[str, Any]:
    """
    获取所有已下载数据的摘要列表

    返回所有已下载的历史数据，按 symbol 分组，包含每个 interval 的
    时间范围和 K 线数量信息。

    Returns:
        Dict with "data" key containing list of symbol summaries
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
                        }
                    ]
                }
            ]
        }

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
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get downloaded data summary: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve downloaded data"
        )
```

- [ ] **Step 4: 运行测试验证通过**

```bash
pytest tests/test_data_api.py::test_get_downloaded_data_empty -v
pytest tests/test_data_api.py::test_get_downloaded_data_single_symbol -v
pytest tests/test_data_api.py::test_get_downloaded_data_multiple_symbols -v
pytest tests/test_data_api.py::test_get_downloaded_data_response_format -v
```

Expected: All PASS

- [ ] **Step 5: 手动测试 API**

```bash
# 启动后端
cd backend
python main.py
```

在另一个终端：
```bash
# 测试空数据库
curl http://localhost:8000/api/v1/data/downloaded

# 下载一些数据
curl -X POST http://localhost:8000/api/v1/data/download \
  -H "Content-Type: application/json" \
  -d '{"symbol":"BTCUSDT","interval":"1h","start_time":"2024-01-01T00:00:00","end_time":"2024-01-01T05:00:00"}'

# 再次查询
curl http://localhost:8000/api/v1/data/downloaded
```

Expected: 返回正确的 JSON 格式数据

- [ ] **Step 6: 提交代码**

```bash
git add backend/api/data.py tests/test_data_api.py
git commit -m "feat(api): add GET /data/downloaded endpoint

- Add endpoint to return downloaded data summary
- Group by symbol and interval
- Return count and time range for each dataset
- Convert datetime to ISO format for JSON serialization"
```

---

## Task 3: 前端 API 客户端 - 添加类型和方法

**Files:**
- Modify: `frontend/lib/api/data.ts`

- [ ] **Step 1: 添加类型定义**

在 `frontend/lib/api/data.ts` 文件中添加类型定义：

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

- [ ] **Step 2: 添加 API 方法**

在 `dataApi` 对象中添加方法：

```typescript
export const dataApi = {
  // ... 现有方法保持不变

  getDownloadedData: async (): Promise<DownloadedDataItem[]> => {
    const response = await axios.get<{ data: DownloadedDataItem[] }>(
      `${API_BASE_URL}/api/v1/data/downloaded`
    );
    return response.data.data;
  },
};
```

- [ ] **Step 3: 验证类型正确**

```bash
cd frontend
pnpm tsc --noEmit
```

Expected: No type errors

- [ ] **Step 4: 提交代码**

```bash
git add frontend/lib/api/data.ts
git commit -m "feat(api): add types and method for downloaded data

- Add DownloadedInterval and DownloadedDataItem interfaces
- Add getDownloadedData API method
- Properly type API response with generic parameter"
```

---

## Task 4: 前端组件 - 创建侧边栏组件

**Files:**
- Create: `frontend/components/DownloadedDataSidebar.tsx`

- [ ] **Step 1: 创建组件文件**

创建 `frontend/components/DownloadedDataSidebar.tsx`：

```typescript
'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { dataApi, DownloadedDataItem } from '@/lib/api/data';

interface Props {
  onSymbolSelect: (symbol: string, interval: string) => void;
  selectedSymbol?: string;
  selectedInterval?: string;
}

export default function DownloadedDataSidebar({
  onSymbolSelect,
  selectedSymbol,
  selectedInterval,
}: Props) {
  // 数据获取
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['downloadedData'],
    queryFn: dataApi.getDownloadedData,
    staleTime: 30000, // 30秒内使用缓存
    refetchOnWindowFocus: true,
  });

  // 展开/折叠状态
  const [expandedSymbols, setExpandedSymbols] = useState<Set<string>>(new Set());

  const toggleSymbol = (symbol: string) => {
    setExpandedSymbols((prev) => {
      const next = new Set(prev);
      if (next.has(symbol)) {
        next.delete(symbol);
      } else {
        next.add(symbol);
      }
      return next;
    });
  };

  const handleIntervalClick = (symbol: string, interval: string) => {
    onSymbolSelect(symbol, interval);
  };

  // 格式化日期
  const formatDate = (isoString: string) => {
    const date = new Date(isoString);
    return date.toLocaleDateString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
    }).replace(/\//g, '-');
  };

  // 格式化数量
  const formatCount = (count: number) => {
    return count.toLocaleString('zh-CN');
  };

  // 加载状态
  if (isLoading) {
    return (
      <div className="w-[300px] h-screen sticky top-0 bg-white border-r border-gray-200 overflow-y-auto">
        <div className="p-4 border-b border-gray-200">
          <h2 className="text-lg font-semibold text-gray-900">已下载数据</h2>
        </div>
        <div className="p-4 space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="animate-pulse">
              <div className="h-4 bg-gray-200 rounded w-3/4 mb-2"></div>
              <div className="h-3 bg-gray-100 rounded w-1/2"></div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  // 错误状态
  if (error) {
    return (
      <div className="w-[300px] h-screen sticky top-0 bg-white border-r border-gray-200 overflow-y-auto">
        <div className="p-4 border-b border-gray-200">
          <h2 className="text-lg font-semibold text-gray-900">已下载数据</h2>
        </div>
        <div className="p-4">
          <div className="bg-red-50 border border-red-200 rounded-lg p-4">
            <p className="text-sm text-red-800 mb-3">加载失败</p>
            <button
              onClick={() => refetch()}
              className="text-sm text-red-600 hover:text-red-800 underline"
            >
              重试
            </button>
          </div>
        </div>
      </div>
    );
  }

  // 空状态
  if (!data || data.length === 0) {
    return (
      <div className="w-[300px] h-screen sticky top-0 bg-white border-r border-gray-200 overflow-y-auto">
        <div className="p-4 border-b border-gray-200">
          <h2 className="text-lg font-semibold text-gray-900">已下载数据</h2>
        </div>
        <div className="p-4">
          <div className="text-center py-8">
            <p className="text-gray-500 text-sm">暂无已下载数据</p>
            <p className="text-gray-400 text-xs mt-2">请先下载历史数据</p>
          </div>
        </div>
      </div>
    );
  }

  // 正常渲染
  return (
    <div className="w-[300px] h-screen sticky top-0 bg-white border-r border-gray-200 overflow-y-auto">
      <div className="p-4 border-b border-gray-200">
        <h2 className="text-lg font-semibold text-gray-900">已下载数据</h2>
      </div>

      <div className="divide-y divide-gray-100">
        {data.map((symbolData) => {
          const isExpanded = expandedSymbols.has(symbolData.symbol);

          return (
            <div key={symbolData.symbol} className="border-b border-gray-100">
              {/* Symbol 标题 */}
              <button
                onClick={() => toggleSymbol(symbolData.symbol)}
                className="w-full p-3 hover:bg-gray-50 transition-colors flex items-center justify-between"
              >
                <span className="font-medium text-gray-900">
                  {symbolData.symbol}
                </span>
                <span className="text-gray-400">
                  {isExpanded ? '▼' : '▶'}
                </span>
              </button>

              {/* Interval 列表 */}
              {isExpanded && (
                <div className="bg-gray-50">
                  {symbolData.intervals.map((intervalData) => {
                    const isSelected =
                      selectedSymbol === symbolData.symbol &&
                      selectedInterval === intervalData.interval;

                    return (
                      <button
                        key={intervalData.interval}
                        onClick={() =>
                          handleIntervalClick(
                            symbolData.symbol,
                            intervalData.interval
                          )
                        }
                        className={`w-full p-3 pl-6 text-left transition-colors ${
                          isSelected
                            ? 'bg-blue-100 border-l-4 border-blue-500'
                            : 'hover:bg-blue-50'
                        }`}
                      >
                        <div className="text-sm font-medium text-gray-900">
                          {intervalData.interval}
                        </div>
                        <div className="text-xs text-gray-500 mt-1">
                          {formatDate(intervalData.start_time)} ~{' '}
                          {formatDate(intervalData.end_time)}
                        </div>
                        <div className="text-xs text-gray-400 mt-1">
                          {formatCount(intervalData.count)} 条
                        </div>
                      </button>
                    );
                  })}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: 验证编译通过**

```bash
cd frontend
pnpm tsc --noEmit
```

Expected: No errors

- [ ] **Step 3: 提交代码**

```bash
git add frontend/components/DownloadedDataSidebar.tsx
git commit -m "feat(components): add DownloadedDataSidebar component

- Display downloaded data grouped by symbol
- Support expand/collapse for each symbol
- Show interval details: time range and count
- Handle loading, error, and empty states
- Highlight selected item
- Use React Query for data fetching with 30s cache"
```

---

## Task 5: 前端页面 - 集成侧边栏到数据页面

**Files:**
- Modify: `frontend/app/data/page.tsx`

- [ ] **Step 1: 导入组件**

在文件顶部添加导入：

```typescript
import DownloadedDataSidebar from '@/components/DownloadedDataSidebar';
```

- [ ] **Step 2: 添加选择处理函数**

在组件内部，在其他 state 定义之后添加：

```typescript
const handleSymbolSelect = (symbol: string, interval: string) => {
  setSelectedSymbol(symbol);
  setSelectedInterval(interval);
  setDownloadResult(null);
  // 滚动到顶部
  window.scrollTo({ top: 0, behavior: 'smooth' });
};
```

- [ ] **Step 3: 更新页面布局**

将整个 return 部分从：

```typescript
return (
  <div className="min-h-screen bg-gray-50 p-8">
    <div className="max-w-7xl mx-auto">
      {/* 现有内容 */}
    </div>
  </div>
);
```

替换为：

```typescript
return (
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
          {/* 原有内容保持不变 */}
          <div className="mb-8">
            <h1 className="text-3xl font-bold text-gray-900 mb-2">
              Data Management
            </h1>
            <p className="text-gray-600">
              Download and manage historical market data for backtesting
            </p>
          </div>

          {/* ... 其他内容保持不变 ... */}
        </div>
      </div>
    </div>
  </div>
);
```

- [ ] **Step 4: 添加缓存失效逻辑**

在 `downloadMutation` 的 `onSuccess` 回调中添加：

```typescript
const downloadMutation = useMutation({
  mutationFn: (request: DownloadRequest) => dataApi.download(request),
  onSuccess: (data) => {
    setDownloadResult(data);
    // 使缓存失效，刷新侧边栏
    queryClient.invalidateQueries({
      queryKey: ['downloadedData'],
    });
    queryClient.invalidateQueries({
      queryKey: ['dataStatus', data.symbol, data.interval],
    });
  },
  onError: (error) => {
    setDownloadResult({
      symbol: selectedSymbol,
      interval: selectedInterval,
      count: 0,
      status: 'error',
      message: error instanceof Error ? error.message : 'Download failed',
    });
  },
});
```

- [ ] **Step 5: 验证编译通过**

```bash
cd frontend
pnpm tsc --noEmit
```

Expected: No errors

- [ ] **Step 6: 提交代码**

```bash
git add frontend/app/data/page.tsx
git commit -m "feat(page): integrate sidebar into data management page

- Add two-column layout with sidebar on left
- Update selected symbol/interval from sidebar clicks
- Invalidate cache after successful download
- Auto-scroll to top when selecting from sidebar"
```

---

## Task 6: 前端测试 - 添加 E2E 测试

**Files:**
- Create: `frontend/e2e/data-sidebar.spec.ts`

- [ ] **Step 1: 创建测试文件**

创建 `frontend/e2e/data-sidebar.spec.ts`：

```typescript
import { test, expect } from '@playwright/test';

test.describe('Downloaded Data Sidebar', () => {
  test.beforeEach(async ({ page }) => {
    // 访问数据管理页面
    await page.goto('http://localhost:3000/data');
  });

  test('should display sidebar on data page', async ({ page }) => {
    // 验证侧边栏存在
    const sidebar = page.locator('text=已下载数据');
    await expect(sidebar).toBeVisible();
  });

  test('should show empty state when no data', async ({ page }) => {
    // 验证空状态提示
    const emptyMessage = page.locator('text=暂无已下载数据');
    await expect(emptyMessage).toBeVisible();
  });

  test('should show symbol list after download', async ({ page }) => {
    // 下载一些数据
    await page.selectOption('select:first-of-type', 'BTCUSDT');
    await page.selectOption('select:nth-of-type(2)', '1h');

    // 设置时间范围
    await page.fill('input[type="date"]:first-of-type', '2024-01-01');
    await page.fill('input[type="date"]:nth-of-type(2)', '2024-01-02');

    // 点击下载按钮
    await page.click('button:has-text("下载")');

    // 等待下载完成
    await page.waitForSelector('text=下载成功', { timeout: 10000 });

    // 刷新页面以触发侧边栏数据加载
    await page.reload();

    // 验证侧边栏显示 BTCUSDT
    const symbolItem = page.locator('text=BTCUSDT');
    await expect(symbolItem).toBeVisible();
  });

  test('should expand symbol to show intervals', async ({ page }) => {
    // 假设已经有数据
    // 点击 symbol 展开
    await page.click('text=BTCUSDT');

    // 验证 interval 显示
    const intervalItem = page.locator('text=1h');
    await expect(intervalItem).toBeVisible();
  });

  test('should update form when clicking interval', async ({ page }) => {
    // 假设已经有数据
    // 点击 symbol 展开
    await page.click('text=BTCUSDT');

    // 点击 interval
    await page.click('text=1h');

    // 验证表单已更新
    const symbolSelect = page.locator('select:first-of-type');
    const intervalSelect = page.locator('select:nth-of-type(2)');

    await expect(symbolSelect).toHaveValue('BTCUSDT');
    await expect(intervalSelect).toHaveValue('1h');
  });

  test('should highlight selected item', async ({ page }) => {
    // 假设已经有数据
    // 点击 symbol 展开
    await page.click('text=BTCUSDT');

    // 点击 interval
    await page.click('text=1h');

    // 验证选中状态
    const selectedItem = page.locator('.bg-blue-100');
    await expect(selectedItem).toBeVisible();
  });
});
```

- [ ] **Step 2: 运行测试验证**

```bash
cd frontend
pnpm test:e2e e2e/data-sidebar.spec.ts
```

Expected: Tests pass (需要后端和前端都在运行)

- [ ] **Step 3: 提交代码**

```bash
git add frontend/e2e/data-sidebar.spec.ts
git commit -m "test(e2e): add sidebar component tests

- Test sidebar visibility
- Test empty state display
- Test symbol expansion
- Test interval selection updates form
- Test selected item highlighting"
```

---

## Task 7: 集成测试和验收

**Files:**
- None (manual testing)

- [ ] **Step 1: 运行所有后端测试**

```bash
cd /Users/yasin/code/quant2
pytest tests/ -v
```

Expected: All tests PASS

- [ ] **Step 2: 运行所有前端测试**

```bash
cd frontend
pnpm lint
pnpm tsc --noEmit
pnpm test:e2e
```

Expected: All checks PASS

- [ ] **Step 3: 手动测试完整流程**

1. 启动后端：
```bash
cd backend
source venv/bin/activate
python main.py
```

2. 启动前端：
```bash
cd frontend
pnpm dev
```

3. 打开浏览器访问 http://localhost:3000/data

4. 测试步骤：
   - [ ] 侧边栏显示"暂无已下载数据"
   - [ ] 下载 BTCUSDT 1h 数据（2024-01-01 到 2024-01-02）
   - [ ] 侧边栏自动刷新显示 BTCUSDT
   - [ ] 点击 BTCUSDT 展开，显示 1h interval
   - [ ] 点击 1h，右侧表单自动更新为 BTCUSDT 和 1h
   - [ ] 选中项高亮显示
   - [ ] 下载 ETHUSDT 1d 数据
   - [ ] 侧边栏显示两个 symbol
   - [ ] 点击 ETHUSDT 1d，表单正确更新

- [ ] **Step 4: 性能测试**

使用大量数据测试性能：
```bash
# 下载多个 symbol 和 interval
curl -X POST http://localhost:8000/api/v1/data/download \
  -H "Content-Type: application/json" \
  -d '{"symbol":"BTCUSDT","interval":"1h","start_time":"2024-01-01T00:00:00","end_time":"2024-12-31T23:00:00"}'

curl -X POST http://localhost:8000/api/v1/data/download \
  -H "Content-Type: application/json" \
  -d '{"symbol":"ETHUSDT","interval":"1h","start_time":"2024-01-01T00:00:00","end_time":"2024-12-31T23:00:00"}'

# 测试 API 响应时间
time curl http://localhost:8000/api/v1/data/downloaded
```

Expected: Response time < 500ms

- [ ] **Step 5: 最终提交**

```bash
git add -A
git commit -m "test: verify all functionality works end-to-end

- All backend tests pass
- All frontend tests pass
- Manual testing complete
- Performance within acceptable limits (<500ms)"
```

---

## 验收清单

完成所有任务后，验证以下功能：

- [ ] 后端 API 返回正确的数据格式
- [ ] 数据库查询使用索引，性能良好
- [ ] 侧边栏正确显示所有已下载数据
- [ ] Symbol 分组和展开/折叠功能正常
- [ ] 点击数据项自动更新右侧表单
- [ ] 加载状态显示骨架屏
- [ ] 空状态显示友好提示
- [ ] 错误状态显示错误信息和重试按钮
- [ ] 当前选中项高亮显示
- [ ] 下载新数据后侧边栏自动刷新
- [ ] 所有测试通过（后端 + 前端）
- [ ] 响应时间 < 500ms（1000 条数据内）

---

## 注意事项

1. **数据库索引**：确保使用现有的 `idx_candles_lookup` 索引
2. **错误处理**：所有异常都要正确捕获和记录
3. **类型安全**：前端所有类型定义要完整
4. **缓存策略**：React Query 使用 30 秒 staleTime
5. **测试覆盖**：确保测试覆盖所有边界情况
6. **性能**：大量数据时注意查询性能
7. **用户体验**：清晰的视觉反馈和交互提示
