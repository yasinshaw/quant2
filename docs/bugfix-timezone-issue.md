# 时区转换Bug修复文档

## 问题描述

用户在前端界面选择日期下载K线数据时，实际下载的数据时间范围与用户选择的不一致。

### 复现场景
1. 用户在界面选择：2026-01-01 到 2026-04-07
2. 期望下载：2026-01-01 00:00:00 到 2026-04-07 23:59:59
3. 实际下载：2025-12-31 16:00:00 到 2026-04-07 15:59:59

### 根本原因

前端代码使用了 `Date.toISOString()` 方法，该方法会将本地时间转换为UTC时间，导致时区偏移。

**原始代码（有问题）：**
```javascript
const startISO = new Date(startDate + 'T00:00:00').toISOString();
// 用户选择: 2026-01-01
// 本地时间(CST +08:00): 2026-01-01 00:00:00
// toISOString(): 2025-12-31T16:00:00.000Z (UTC)
// 后端解析为: 2025-12-31 16:00:00 (丢失时区信息)
```

## 受影响的文件

1. ✅ **frontend/components/DownloadForm.tsx** - 数据下载表单
2. ✅ **frontend/components/BacktestForm.tsx** - 回测表单
3. ✅ **frontend/components/OptimizationForm.tsx** - 优化表单

## 修复方案

### 方案：避免时区转换

直接格式化本地时间字符串，不进行时区转换。

**修复后的代码：**
```javascript
// DownloadForm.tsx
const startISO = startDate + 'T00:00:00';
const endISO = endDate + 'T23:59:59';

// BacktestForm.tsx 和 OptimizationForm.tsx
const formatDateTime = (date: Date) => {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  const hours = String(date.getHours()).padStart(2, '0');
  const minutes = String(date.getMinutes()).padStart(2, '0');
  const seconds = String(date.getSeconds()).padStart(2, '0');
  return `${year}-${month}-${day}T${hours}:${minutes}:${seconds}`;
};

const startISO = formatDateTime(start);
```

### 后端处理

后端的 `parse_iso_datetime()` 函数（backend/api/data.py:23-52）已经能够正确处理不带时区的ISO格式字符串：
- 接收：`"2026-01-01T00:00:00"` (无时区信息)
- 解析为：`datetime(2026, 1, 1, 0, 0, 0)` (本地时间)

## 验证

### 测试步骤
1. 启动前端和后端服务
2. 进入数据管理页面
3. 选择 ETHUSDT, 4h, 2026-01-01 到 2026-04-07
4. 点击下载
5. 检查数据库中实际保存的时间范围

### 预期结果
```sql
SELECT COUNT(*), MIN(open_time), MAX(open_time)
FROM candles
WHERE symbol_id=2 AND interval='4h' AND open_time >= '2026-01-01';

-- 结果应该是：
-- count: ~450
-- min: 2026-01-01 00:00:00
-- max: 2026-04-07 08:00:00
```

## 相关问题

### 为什么之前下载的数据只到 2025-12-31 12:00:00？

1. 之前下载的时间范围实际是：2024-12-31 到 2026-01-01（不包含）
2. 由于时区bug，实际下载的是：2024-12-31 16:00:00 到 2025-12-31 16:00:00
3. 所以数据库中最新数据只到 2025-12-31 12:00:00（Binance数据延迟）

### 如何修复已存在的错误数据？

使用 `force_download=true` 重新下载数据，会覆盖已有的数据。

```bash
curl -X POST http://localhost:8000/api/v1/data/download \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "ETHUSDT",
    "interval": "4h",
    "start_time": "2026-01-01T00:00:00",
    "end_time": "2026-04-07T23:59:59",
    "force_download": true
  }'
```

## 影响范围

此修复影响所有使用日期选择器的功能：
- ✅ 数据下载
- ✅ 回测运行
- ✅ 参数优化
- ✅ 样本外测试

## 部署注意事项

1. 前端需要重新构建和部署
2. 后端无需修改
3. 已下载的数据不受影响（但可能时间范围不准确）
4. 建议用户重新下载关键数据集

## 日期：2026-04-07
## 修复人：Claude Code
