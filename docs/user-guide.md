# 量化交易平台用户指南

**版本**: 1.0.0
**更新日期**: 2026-03-24

---

## 目录

1. [快速开始](#快速开始)
2. [平台概述](#平台概述)
3. [策略开发教程](#策略开发教程)
4. [使用指南](#使用指南)
5. [部署说明](#部署说明)
6. [常见问题](#常见问题)
7. [进阶主题](#进阶主题)

---

## 快速开始

### 环境要求

在开始之前，请确保您的系统满足以下要求：

- **Python**: 3.9 或更高版本
- **Node.js**: 18.0 或更高版本
- **包管理器**: pnpm（推荐）或 npm
- **操作系统**: macOS / Linux / Windows
- **内存**: 建议 4GB 以上
- **硬盘**: 至少 2GB 可用空间（用于历史数据存储）

### 安装步骤

#### 1. 克隆项目（如果使用 Git）

```bash
git clone <your-repository-url>
cd quant2
```

#### 2. 后端安装

```bash
# 进入后端目录
cd backend

# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# macOS/Linux:
source venv/bin/activate
# Windows:
# venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt
```

#### 3. 前端安装

```bash
# 打开新终端，进入前端目录
cd frontend

# 安装依赖（使用 pnpm）
pnpm install

# 如果使用 npm
# npm install
```

### 配置

#### 环境变量配置

后端配置文件位于 `backend/.env`，默认配置如下：

```env
# 数据库配置
DATABASE_URL=sqlite:///data/quant.db

# Binance API 配置
BINANCE_BASE_URL=https://api.binance.com
BINANCE_TIMEOUT=30

# 回测配置
DEFAULT_INITIAL_CASH=100000.0
MAX_WORKERS=4
```

**注意**:
- 默认使用 SQLite 数据库，数据存储在 `data/quant.db`
- 使用 Binance 公开 API，无需 API Key
- 默认初始资金为 100,000 USDT

### 运行平台

#### 方式一：分别启动后端和前端

**启动后端**:

```bash
# 在 backend 目录下
cd backend
source venv/bin/activate  # 激活虚拟环境
uvicorn main:app --reload --port 8000
```

后端启动成功后，访问：
- API 服务: http://localhost:8000
- API 文档: http://localhost:8000/docs
- 健康检查: http://localhost:8000/health

**启动前端**:

```bash
# 在 frontend 目录下（新终端）
cd frontend
pnpm dev
```

前端启动成功后，访问: http://localhost:3000

#### 方式二：使用启动脚本（推荐）

创建启动脚本 `start.sh`:

```bash
#!/bin/bash

echo "正在启动量化交易平台..."

# 启动后端
cd backend
source venv/bin/activate
uvicorn main:app --reload --port 8000 &
BACKEND_PID=$!

# 启动前端
cd ../frontend
pnpm dev &
FRONTEND_PID=$!

echo ""
echo "=========================================="
echo "量化交易平台启动成功！"
echo "=========================================="
echo "后端服务:     http://localhost:8000"
echo "前端界面:     http://localhost:3000"
echo "API 文档:     http://localhost:8000/docs"
echo "=========================================="
echo ""
echo "按 Ctrl+C 停止服务"

# 等待中断信号
trap "kill $BACKEND_PID $FRONTEND_PID; exit" INT
wait
```

运行：

```bash
chmod +x start.sh
./start.sh
```

### 第一次回测

让我们完成您的第一次回测：

#### 步骤 1: 下载历史数据

1. 打开浏览器访问 http://localhost:3000
2. 点击导航栏的 **"数据管理"**
3. 输入以下信息：
   - **交易对**: BTCUSDT
   - **时间周期**: 1h（1小时）
   - **开始时间**: 2024-01-01T00:00:00
   - **结束时间**: 2024-12-31T23:59:59
4. 点击 **"下载数据"** 按钮
5. 等待下载完成（可能需要几分钟）

**提示**: 首次下载一年的 1 小时 K 线数据约 8,760 条，大约需要 2-5 分钟。

#### 步骤 2: 运行回测

1. 点击导航栏的 **"回测配置"**
2. 选择策略：**Double MA Crossover**（双均线策略）
3. 配置参数：
   - **Fast Period** (快线周期): 10
   - **Slow Period** (慢线周期): 20
4. 选择数据：
   - **交易对**: BTCUSDT
   - **时间周期**: 1h
   - **时间范围**: 2024-01-01 至 2024-12-31
5. 初始资金: 100000（默认）
6. 点击 **"开始回测"**

#### 步骤 3: 查看结果

回测完成后，您将看到：

- **核心指标**:
  - 总收益率
  - 年化收益率
  - 夏普比率
  - 最大回撤
  - 胜率
  - 盈亏比

- **资金曲线图**: 显示账户价值随时间的变化

- **交易明细**: 每笔交易的详细信息（时间、方向、价格、数量、手续费）

恭喜！您已经完成了第一次回测！

---

## 平台概述

### 架构概览

本平台采用 **单体应用架构**，包含以下核心组件：

```
量化交易平台
│
├── 后端 (FastAPI + Backtrader)
│   ├── 策略引擎
│   ├── 回测引擎
│   ├── 数据管理器
│   ├── 参数优化器
│   └── RESTful API
│
├── 前端 (Next.js + TypeScript)
│   ├── 数据管理界面
│   ├── 策略配置界面
│   ├── 回测结果展示
│   └── 参数优化界面
│
└── 数据库 (SQLite)
    ├── K线数据
    ├── 回测任务
    ├── 交易记录
    └── 优化结果
```

### 核心特性

#### 1. 历史数据管理

- **数据源**: Binance 公开 API（无需 API Key）
- **支持交易对**: 所有 USDT 交易对（BTCUSDT, ETHUSDT 等）
- **支持时间周期**: 1m, 5m, 15m, 1h, 4h, 1d
- **数据存储**: SQLite 本地数据库
- **自动验证**: 价格合理性、时间连续性检查

#### 2. 策略开发

- **策略基类**: 继承 `StrategyBase`，简化开发
- **动态加载**: 策略文件放至 `backend/strategies/` 自动加载
- **参数定义**: 支持整数、浮点数、字符串、布尔值
- **内置指标**: Backtrader 提供丰富的技术指标

#### 3. 回测引擎

- **核心框架**: Backtrader（成熟的量化回测框架）
- **性能指标**:
  - 总收益率 / 年化收益率
  - 夏普比率（风险调整后收益）
  - 最大回撤
  - 胜率 / 盈亏比
  - 总交易次数

- **交易明细**: 每笔交易的时间、价格、数量、手续费
- **资金曲线**: 账户价值随时间的变化

#### 4. 参数优化

- **优化方法**: 网格搜索（Grid Search）
- **评分指标**: 夏普比率
- **并发执行**: 支持多进程并行优化
- **结果保存**: 保存最优参数组合

### 技术栈

#### 后端技术

| 技术 | 版本 | 用途 |
|------|------|------|
| FastAPI | 0.104+ | Web 框架，提供 RESTful API |
| Backtrader | 1.9+ | 回测引擎核心 |
| SQLite | 3.x | 轻量级数据库 |
| SQLAlchemy | 2.0+ | ORM 框架 |
| pandas | 2.1+ | 数据处理 |
| httpx | 1.25+ | HTTP 客户端（调用 Binance API） |
| Pydantic | 2.5+ | 数据验证 |

#### 前端技术

| 技术 | 版本 | 用途 |
|------|------|------|
| Next.js | 14+ | React 框架（App Router） |
| TypeScript | 5+ | 类型安全 |
| TailwindCSS | 3.3+ | 样式框架 |
| TanStack Query | 5.8+ | 数据获取和缓存 |
| Recharts | 2.10+ | 图表库 |
| Lucide React | 0.294+ | 图标库 |

### 目录结构

```
quant2/
├── backend/                    # 后端代码
│   ├── core/                  # 核心引擎
│   │   ├── strategy_base.py   # 策略基类
│   │   ├── backtest_engine.py # 回测引擎
│   │   ├── data_manager.py    # 数据管理器
│   │   ├── optimizer.py       # 参数优化器
│   │   └── strategy_loader.py # 策略加载器
│   │
│   ├── strategies/            # 用户策略文件夹
│   │   ├── double_ma_strategy.py    # 双均线策略
│   │   ├── rsi_strategy.py          # RSI 策略
│   │   └── macd_strategy.py         # MACD 策略
│   │
│   ├── models/                # 数据库模型
│   │   ├── candle.py         # K线数据
│   │   ├── trade.py          # 交易记录
│   │   ├── backtest_job.py   # 回测任务
│   │   └── backtest_result.py # 回测结果
│   │
│   ├── api/                   # API 路由
│   │   ├── strategies.py     # 策略相关 API
│   │   ├── data.py          # 数据管理 API
│   │   └── backtest.py      # 回测 API
│   │
│   ├── utils/                # 工具函数
│   │   └── binance_client.py # Binance API 客户端
│   │
│   ├── main.py               # FastAPI 入口
│   ├── config.py             # 配置管理
│   ├── requirements.txt      # Python 依赖
│   └── .env                  # 环境变量
│
├── frontend/                  # 前端代码
│   ├── src/
│   │   ├── app/             # Next.js 页面
│   │   │   ├── page.tsx     # 首页
│   │   │   ├── data/        # 数据管理页
│   │   │   ├── strategies/  # 策略列表页
│   │   │   └── backtest/    # 回测页
│   │   │
│   │   ├── components/      # React 组件
│   │   ├── lib/            # API 客户端
│   │   │   └── api.ts
│   │   │
│   │   └── types/          # TypeScript 类型
│   │       └── index.ts
│   │
│   ├── package.json
│   └── tailwind.config.js
│
├── data/                     # SQLite 数据库
│   └── quant.db
│
├── tests/                    # 测试文件
│
├── logs/                     # 日志文件
│
└── docs/                     # 文档
    ├── api.md               # API 文档
    └── user-guide.md        # 用户指南（本文档）
```

---

## 策略开发教程

### 策略结构

所有策略必须继承 `StrategyBase` 基类，并实现以下方法：

1. `__init__()`: 初始化指标
2. `next()`: 交易逻辑（每根 K 线调用一次）
3. `get_parameters()`: 返回策略参数定义（类方法）

### 创建自定义策略

让我们创建一个简单的移动平均策略：

#### 步骤 1: 创建策略文件

在 `backend/strategies/` 目录下创建新文件 `my_sma_strategy.py`:

```python
"""
Simple Moving Average Strategy
A basic trend-following strategy using a single SMA.
"""
import backtrader as bt
from backend.core.strategy_base import StrategyBase
from typing import Dict, Any


class SimpleSMAStrategy(StrategyBase):
    """
    Simple Moving Average Strategy

    Trading Logic:
    - Buy when price crosses above SMA
    - Sell when price crosses below SMA
    """

    # Strategy metadata (required)
    strategy_name = "Simple SMA"
    strategy_version = "1.0.0"
    strategy_description = "Simple moving average trend-following strategy"

    # Strategy parameters (Backtrader format)
    params = (
        ('sma_period', 20),  # SMA period
    )

    def __init__(self):
        """Initialize the strategy with SMA indicator."""
        super().__init__()

        # Create SMA indicator
        self.sma = bt.indicators.SMA(
            self.data.close,
            period=self.params.sma_period
        )

        # Crossover indicator (price vs SMA)
        self.crossover = bt.indicators.CrossOver(
            self.data.close,
            self.sma
        )

    def next(self):
        """
        Execute trading logic on each bar.

        This method is called by Backtrader for each data point.
        """
        # Check if we have enough data
        if len(self.data) < self.params.sma_period:
            return

        # Check if we have an open position
        if not self.position:
            # No position - check for buy signal
            if self.crossover > 0:  # Price crosses above SMA
                self.buy()
                self.log(f'BUY SIGNAL: Price crossed above SMA({self.params.sma_period})')

        else:
            # Have position - check for sell signal
            if self.crossover < 0:  # Price crosses below SMA
                self.sell()
                self.log(f'SELL SIGNAL: Price crossed below SMA({self.params.sma_period})')

    @staticmethod
    def get_parameters() -> Dict[str, Any]:
        """
        Return strategy parameter definitions.

        This method is used by the platform to:
        1. Generate UI forms for parameter input
        2. Validate parameter values
        3. Set default values
        """
        return {
            'sma_period': {
                'type': 'int',
                'default': 20,
                'min': 5,
                'max': 100,
                'description': 'Period for Simple Moving Average'
            }
        }
```

#### 步骤 2: 刷新策略列表

创建策略文件后，有两种方式让平台识别：

**方式 1: 通过 Web 界面**

1. 访问 http://localhost:3000
2. 点击 **"策略列表"**
3. 点击 **"刷新策略"** 按钮

**方式 2: 通过 API**

```bash
curl -X POST http://localhost:8000/api/v1/strategies/refresh
```

#### 步骤 3: 验证策略加载

访问策略列表页面，您应该能看到新创建的 "Simple SMA" 策略。

或使用 API:

```bash
curl http://localhost:8000/api/v1/strategies/
```

预期输出:

```json
{
  "strategies": [
    {
      "name": "Simple SMA",
      "version": "1.0.0",
      "description": "Simple moving average trend-following strategy"
    },
    ...
  ]
}
```

### 策略参数

#### 参数类型

支持以下参数类型：

| 类型 | 说明 | 示例 |
|------|------|------|
| `int` | 整数 | `{'type': 'int', 'default': 20, 'min': 5, 'max': 100}` |
| `float` | 浮点数 | `{'type': 'float', 'default': 0.02, 'min': 0.01, 'max': 0.1}` |
| `str` | 字符串 | `{'type': 'str', 'default': 'BTCUSDT'}` |
| `bool` | 布尔值 | `{'type': 'bool', 'default': true}` |

#### 参数定义格式

```python
@staticmethod
def get_parameters() -> Dict[str, Any]:
    return {
        'parameter_name': {
            'type': 'int' | 'float' | 'str' | 'bool',
            'default': <default_value>,
            'min': <min_value>,      # 仅数值类型
            'max': <max_value>,      # 仅数值类型
            'description': 'Parameter description'
        }
    }
```

#### 访问参数

在策略中通过 `self.params.parameter_name` 访问参数值：

```python
def next(self):
    sma_period = self.params.sma_period
    # 使用参数...
```

### Backtrader 常用 API

#### 数据访问

```python
# 价格数据
self.data.open      # 开盘价
self.data.high      # 最高价
self.data.low       # 最低价
self.data.close     # 收盘价
self.data.volume    # 成交量

# 时间数据
self.data.datetime.datetime(0)  # 当前时间
```

#### 持仓和订单

```python
# 检查持仓
if self.position:
    # 有持仓
    position_size = self.position.size
else:
    # 无持仓

# 下单
self.buy(size=1.0)    # 买入
self.sell(size=1.0)   # 卖出
self.close()          # 平仓

# 订单状态
if self.order:
    # 有待执行订单
    pass
```

#### 常用指标

```python
# Simple Moving Average
sma = bt.indicators.SMA(self.data.close, period=20)

# Exponential Moving Average
ema = bt.indicators.EMA(self.data.close, period=20)

# RSI
rsi = bt.indicators.RSI(self.data.close, period=14)

# MACD
macd = bt.indicators.MACD(
    self.data.close,
    period_me1=12,
    period_me2=26,
    period_signal=9
)

# Bollinger Bands
bb = bt.indicators.BollingerBands(
    self.data.close,
    period=20,
    devfactor=2.0
)

# Crossover
crossover = bt.indicators.CrossOver(line1, line2)
# 返回值: 1 (line1 上穿 line2), -1 (line1 下穿 line2), 0 (无交叉)
```

### 策略示例

#### 示例 1: 双均线策略（Double MA）

查看完整实现: `backend/strategies/double_ma_strategy.py`

**策略逻辑**:
- 买入: 快线（短期均线）上穿慢线（长期均线）
- 卖出: 快线下穿慢线

**参数**:
- `fast_period`: 快线周期（默认 10）
- `slow_period`: 慢线周期（默认 20）

#### 示例 2: RSI 策略

查看完整实现: `backend/strategies/rsi_strategy.py`

**策略逻辑**:
- 买入: RSI < 30（超卖区域）
- 卖出: RSI > 70（超买区域）

**参数**:
- `rsi_period`: RSI 周期（默认 14）
- `oversold`: 超卖阈值（默认 30）
- `overbought`: 超买阈值（默认 70）

#### 示例 3: MACD 策略

查看完整实现: `backend/strategies/macd_strategy.py`

**策略逻辑**:
- 买入: MACD 线上穿信号线
- 卖出: MACD 线下穿信号线

**参数**:
- `period_me1`: 短期 EMA 周期（默认 12）
- `period_me2`: 长期 EMA 周期（默认 26）
- `period_signal`: 信号线周期（默认 9）

### 测试策略

#### 单元测试

为策略编写单元测试（推荐）：

```python
# tests/test_my_strategy.py
import pytest
from backend.strategies.my_sma_strategy import SimpleSMAStrategy

def test_strategy_parameters():
    """Test strategy parameter definitions."""
    params = SimpleSMAStrategy.get_parameters()

    assert 'sma_period' in params
    assert params['sma_period']['type'] == 'int'
    assert params['sma_period']['default'] == 20
    assert params['sma_period']['min'] == 5
    assert params['sma_period']['max'] == 100

def test_strategy_metadata():
    """Test strategy metadata."""
    assert SimpleSMAStrategy.strategy_name == "Simple SMA"
    assert SimpleSMAStrategy.strategy_version == "1.0.0"
```

运行测试:

```bash
cd backend
pytest tests/test_my_strategy.py
```

#### 回测测试

使用小数据集快速测试策略：

```bash
# 1. 下载少量数据（1个月）
curl -X POST http://localhost:8000/api/v1/data/download \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "BTCUSDT",
    "interval": "1h",
    "start_time": "2024-01-01T00:00:00",
    "end_time": "2024-01-31T23:59:59"
  }'

# 2. 运行回测
curl -X POST http://localhost:8000/api/v1/backtest/run \
  -H "Content-Type: application/json" \
  -d '{
    "strategy_name": "Simple SMA",
    "symbol": "BTCUSDT",
    "interval": "1h",
    "start_time": "2024-01-01T00:00:00",
    "end_time": "2024-01-31T23:59:59",
    "parameters": {
      "sma_period": 15
    },
    "initial_cash": 10000
  }'
```

---

## 使用指南

### 数据管理

#### 下载历史数据

**通过 Web 界面**:

1. 访问 **"数据管理"** 页面
2. 填写表单：
   - **交易对**: 例如 BTCUSDT, ETHUSDT
   - **时间周期**: 1m, 5m, 15m, 1h, 4h, 1d
   - **开始时间**: ISO 格式（2024-01-01T00:00:00）
   - **结束时间**: ISO 格式（2024-12-31T23:59:59）
3. 点击 **"下载数据"**

**通过 API**:

```bash
curl -X POST http://localhost:8000/api/v1/data/download \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "BTCUSDT",
    "interval": "1h",
    "start_time": "2024-01-01T00:00:00",
    "end_time": "2024-12-31T23:59:59"
  }'
```

**响应示例**:

```json
{
  "symbol": "BTCUSDT",
  "interval": "1h",
  "count": 8760,
  "status": "downloaded",
  "message": "Data downloaded successfully"
}
```

#### 查看已有数据

**查看所有交易对**:

```bash
curl http://localhost:8000/api/v1/data/symbols
```

**查看数据状态**:

```bash
curl http://localhost:8000/api/v1/data/status/BTCUSDT/1h
```

响应:

```json
{
  "symbol": "BTCUSDT",
  "interval": "1h",
  "available": true,
  "count": 8760
}
```

#### 数据下载建议

- **时间范围**: 建议下载 1 年以上的数据进行回测
- **时间周期**:
  - 日内交易: 1m, 5m, 15m
  - 波段交易: 1h, 4h
  - 趋势跟踪: 1d

- **数据量估算**:
  - 1 年 1 小时数据: ~8,760 条
  - 1 年 5 分钟数据: ~105,120 条
  - 1 年 1 分钟数据: ~525,600 条

### 运行回测

#### 通过 Web 界面

1. 访问 **"回测配置"** 页面
2. 选择策略
3. 配置策略参数
4. 选择数据范围
5. 设置初始资金
6. 点击 **"开始回测"**

#### 通过 API

```bash
curl -X POST http://localhost:8000/api/v1/backtest/run \
  -H "Content-Type: application/json" \
  -d '{
    "strategy_name": "Double MA Crossover",
    "symbol": "BTCUSDT",
    "interval": "1h",
    "start_time": "2024-01-01T00:00:00",
    "end_time": "2024-12-31T23:59:59",
    "parameters": {
      "fast_period": 10,
      "slow_period": 20
    },
    "initial_cash": 100000
  }'
```

#### 回测结果解读

**核心指标**:

| 指标 | 说明 | 参考标准 |
|------|------|----------|
| 总收益率 | 整个回测期间的收益率 | 正值为盈利 |
| 年化收益率 | 换算为年度的收益率 | > 15% 优秀 |
| 夏普比率 | 风险调整后收益 | > 1.0 良好, > 2.0 优秀 |
| 最大回撤 | 最大亏损幅度 | < -20% 良好 |
| 胜率 | 盈利交易占比 | > 50% 良好 |
| 盈亏比 | 总盈利 / 总亏损 | > 1.5 良好 |

**示例结果**:

```json
{
  "summary": {
    "total_return": 0.255,        // 25.5% 总收益
    "annual_return": 0.255,       // 25.5% 年化收益
    "sharpe_ratio": 1.8,          // 夏普比率 1.8
    "max_drawdown": -0.152,       // -15.2% 最大回撤
    "win_rate": 0.625,            // 62.5% 胜率
    "profit_factor": 1.65,        // 盈亏比 1.65
    "total_trades": 48,           // 48 笔交易
    "initial_cash": 100000,       // 初始资金
    "final_value": 125500         // 最终价值
  }
}
```

### 分析结果

#### 资金曲线

资金曲线显示账户价值随时间的变化：

- **上升趋势**: 策略盈利
- **下降趋势**: 策略亏损
- **波动性**: 曲线平滑度反映风险

#### 月度收益

月度收益分析展示每个月的盈亏情况：

- 识别策略在不同市场环境下的表现
- 发现季节性规律
- 评估策略稳定性

#### 交易明细

每笔交易的详细信息：

- **时间**: 交易发生时间
- **方向**: BUY / SELL
- **价格**: 成交价格
- **数量**: 交易数量
- **手续费**: 交易成本
- **价值**: 交易金额

### 参数优化

#### 通过 Web 界面

1. 访问 **"参数优化"** 页面
2. 选择策略
3. 配置参数范围（例如）：
   - `fast_period`: [5, 10, 15, 20]
   - `slow_period`: [20, 30, 40, 50]
4. 选择数据范围
5. 点击 **"开始优化"**

#### 通过 API

```bash
curl -X POST http://localhost:8000/api/v1/backtest/optimize \
  -H "Content-Type: application/json" \
  -d '{
    "strategy_name": "Double MA Crossover",
    "symbol": "BTCUSDT",
    "interval": "1h",
    "start_time": "2024-01-01T00:00:00",
    "end_time": "2024-12-31T23:59:59",
    "parameter_ranges": {
      "fast_period": [5, 10, 15, 20],
      "slow_period": [20, 30, 40, 50]
    },
    "initial_cash": 100000
  }'
```

#### 优化结果

```json
{
  "parameters": {
    "fast_period": 10,
    "slow_period": 30
  },
  "backtest_result": {
    "sharpe_ratio": 2.1,
    "total_return": 0.32,
    "max_drawdown": -0.12
  }
}
```

#### 优化建议

- **参数范围**: 避免过大范围，导致计算时间过长
- **样本外测试**: 使用一部分数据优化，另一部分数据验证
- **过拟合风险**: 避免参数过度适应历史数据

---

## 部署说明

### 本地部署

#### 系统要求

- Python 3.9+
- Node.js 18+
- 4GB+ 内存
- 2GB+ 硬盘空间

#### 部署步骤

参考 [快速开始](#快速开始) 部分。

### 生产环境考虑

#### 安全性

1. **API 访问控制**:
   - 添加身份验证（JWT Token）
   - 限制 CORS 来源
   - 启用 HTTPS

2. **数据库安全**:
   - 定期备份
   - 数据库加密

3. **环境变量**:
   - 不要将 `.env` 文件提交到 Git
   - 使用环境变量管理敏感信息

#### 性能优化

1. **后端优化**:
   - 使用 Gunicorn 或 Uvicorn 多进程
   - 启用响应缓存
   - 数据库索引优化

2. **前端优化**:
   - 启用生产构建 (`pnpm build`)
   - CDN 加速
   - 代码分割和懒加载

3. **数据库优化**:
   - 定期清理旧数据
   - 建立合适的索引
   - 考虑使用 PostgreSQL 替代 SQLite

#### 监控和日志

1. **日志管理**:
   - 配置日志级别
   - 日志轮转（避免日志文件过大）
   - 错误日志告警

2. **性能监控**:
   - API 响应时间
   - 数据库查询性能
   - 系统资源使用

### 数据库管理

#### 备份策略

```bash
# 备份数据库
cp data/quant.db data/quant_backup_$(date +%Y%m%d).db

# 恢复数据库
cp data/quant_backup_20240324.db data/quant.db
```

#### 数据清理

```sql
-- 删除 1 年前的 K 线数据
DELETE FROM candles
WHERE open_time < datetime('now', '-1 year');

-- 删除失败的回测任务
DELETE FROM backtest_jobs
WHERE status = 'failed'
AND created_at < datetime('now', '-30 days');
```

#### 数据库优化

```sql
-- 重建索引（提升查询性能）
REINDEX;

-- 清理数据库碎片
VACUUM;

-- 分析查询性能
EXPLAIN QUERY PLAN
SELECT * FROM candles
WHERE symbol_id = 1 AND interval = '1h'
ORDER BY open_time;
```

---

## 常见问题

### 安装问题

#### Q1: Python 依赖安装失败

**问题**: `pip install -r requirements.txt` 报错

**解决方案**:

```bash
# 升级 pip
python -m pip install --upgrade pip

# 使用国内镜像
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

#### Q2: Node.js 依赖安装失败

**问题**: `pnpm install` 报错

**解决方案**:

```bash
# 清理缓存
pnpm store prune

# 删除 node_modules 重新安装
rm -rf node_modules pnpm-lock.yaml
pnpm install
```

#### Q3: 虚拟环境激活失败

**问题**: Windows 下 `source venv/bin/activate` 报错

**解决方案**:

Windows 使用:
```bash
venv\Scripts\activate
```

或使用 PowerShell:
```powershell
venv\Scripts\Activate.ps1
```

### 数据下载问题

#### Q4: 数据下载超时

**问题**: 下载大量数据时超时

**解决方案**:

1. 分批下载（每次下载 3-6 个月）
2. 调整超时时间（修改 `backend/.env`）:

```env
BINANCE_TIMEOUT=60
```

3. 检查网络连接

#### Q5: 数据下载失败 - 无数据

**问题**: 提示 "No data received from data source"

**解决方案**:

1. 检查交易对是否正确（例如 BTCUSDT，不是 BTC-USDT）
2. 检查时间范围是否合理
3. 访问 Binance API 文档确认支持的交易对:
   - https://binance-docs.github.io/apidocs/spot/en/

#### Q6: 数据重复下载

**问题**: 提示 "Data already exists"

**解决方案**:

这是正常的，平台会自动检测已下载的数据，避免重复下载。

如果需要重新下载，先删除数据库中的数据:

```bash
# 删除数据库文件（会删除所有数据！）
rm data/quant.db

# 重启后端，自动创建新数据库
```

### 回测错误

#### Q7: 回测失败 - "No data found"

**问题**: 提示找不到数据

**解决方案**:

1. 确认已下载数据:
```bash
curl http://localhost:8000/api/v1/data/status/BTCUSDT/1h
```

2. 检查时间范围是否在已下载数据范围内

#### Q8: 策略加载失败

**问题**: 提示 "Strategy not found"

**解决方案**:

1. 检查策略文件是否在 `backend/strategies/` 目录
2. 确认策略类继承了 `StrategyBase`
3. 刷新策略列表:
```bash
curl -X POST http://localhost:8000/api/v1/strategies/refresh
```

4. 检查策略文件是否有语法错误:
```bash
cd backend
python -m py_compile strategies/my_strategy.py
```

#### Q9: 回测结果为 0 笔交易

**问题**: 回测完成但没有交易

**解决方案**:

1. 检查策略逻辑是否正确
2. 检查参数设置是否合理
3. 查看后端日志（`logs/` 目录）了解策略执行情况
4. 尝试调整策略参数

### 性能问题

#### Q10: 回测速度慢

**问题**: 大数据量回测耗时过长

**解决方案**:

1. 减少数据量（使用较短的时间范围）
2. 优化策略代码（减少不必要的计算）
3. 使用更快的硬件

#### Q11: 参数优化时间过长

**问题**: 网格搜索参数组合太多

**解决方案**:

1. 减少参数范围
2. 分阶段优化（先粗略搜索，再精细搜索）
3. 使用更小的数据集进行初步优化

#### Q12: 数据库查询慢

**问题**: 查询大量 K 线数据缓慢

**解决方案**:

1. 重建索引:
```sql
REINDEX;
```

2. 定期清理旧数据
3. 考虑使用 PostgreSQL 替代 SQLite

### 故障排查

#### 查看日志

后端日志位于 `logs/` 目录：

```bash
# 查看最新日志
tail -f logs/app.log

# 搜索错误
grep "ERROR" logs/app.log
```

#### 检查 API 健康状态

```bash
curl http://localhost:8000/health
```

#### 检查数据库连接

```bash
# 进入数据库
sqlite3 data/quant.db

# 检查表
.tables

# 检查数据
SELECT COUNT(*) FROM candles;
```

---

## 进阶主题

### 添加新数据源

当前平台使用 Binance 作为数据源。要添加新的数据源（例如 OKX）：

#### 步骤 1: 实现数据源接口

创建 `backend/utils/okx_client.py`:

```python
from backend.core.data_source import DataSource
from typing import List
from datetime import datetime

class OKXDataSource(DataSource):
    """OKX data source implementation"""

    async def fetch_candles(
        self,
        symbol: str,
        interval: str,
        start_time: datetime,
        end_time: datetime
    ) -> List['Candle']:
        # 实现 OKX API 调用
        pass

    async def get_supported_symbols(self) -> List[str]:
        # 返回 OKX 支持的交易对
        pass

    async def get_supported_intervals(self) -> List[str]:
        return ['1m', '5m', '15m', '1h', '4h', '1d']
```

#### 步骤 2: 集成到数据管理器

修改 `backend/core/data_manager.py`，添加数据源选择逻辑。

### 自定义指标

#### 创建自定义指标

```python
import backtrader as bt

class CustomIndicator(bt.Indicator):
    """Custom indicator example"""

    lines = ('custom_line',)

    params = (
        ('period', 20),
    )

    def __init__(self):
        # 自定义指标计算逻辑
        self.lines.custom_line = bt.indicators.SMA(
            self.data.close,
            period=self.params.period
        )

# 在策略中使用
class MyStrategy(StrategyBase):
    def __init__(self):
        super().__init__()
        self.custom = CustomIndicator(self.data.close, period=20)
```

### 实盘交易（Phase 2）

**注意**: 实盘交易功能计划在第二阶段实现。

#### 计划功能

- OKX 交易所对接
- WebSocket 实时数据订阅
- 自动下单
- 仓位管理
- 风险控制

#### 架构预留

平台已预留实盘交易接口：

- `backend/utils/okx_client.py`: OKX API 客户端
- `backend/core/live_trading.py`: 实盘交易引擎
- `backend/api/live.py`: 实盘交易 API

### 性能优化

#### 后端优化

1. **异步处理**:
   - 使用 `async/await` 处理 I/O 操作
   - 并发下载多个交易对数据

2. **缓存**:
   - 缓存策略元数据
   - 缓存常用数据查询结果

3. **数据库优化**:
   - 批量插入数据
   - 使用事务
   - 建立索引

#### 前端优化

1. **代码分割**:
   - 按路由分割代码
   - 懒加载大型组件

2. **数据缓存**:
   - TanStack Query 自动缓存
   - 避免重复请求

3. **图表优化**:
   - 虚拟滚动（大数据集）
   - 降采样显示

### API 集成

#### 使用 API 进行自动化

完整的 API 文档请参考: `docs/api.md`

#### 示例: 自动化回测脚本

```python
import requests
import json

BASE_URL = "http://localhost:8000/api/v1"

def run_backtest(strategy, symbol, interval, start, end, params):
    """Run backtest and return results"""

    # 1. Download data if needed
    response = requests.post(
        f"{BASE_URL}/data/download",
        json={
            "symbol": symbol,
            "interval": interval,
            "start_time": start,
            "end_time": end
        }
    )

    # 2. Run backtest
    response = requests.post(
        f"{BASE_URL}/backtest/run",
        json={
            "strategy_name": strategy,
            "symbol": symbol,
            "interval": interval,
            "start_time": start,
            "end_time": end,
            "parameters": params,
            "initial_cash": 100000
        }
    )

    return response.json()

# 使用示例
result = run_backtest(
    strategy="Double MA Crossover",
    symbol="BTCUSDT",
    interval="1h",
    start="2024-01-01T00:00:00",
    end="2024-12-31T23:59:59",
    params={"fast_period": 10, "slow_period": 20}
)

print(f"Total Return: {result['summary']['total_return']:.2%}")
print(f"Sharpe Ratio: {result['summary']['sharpe_ratio']:.2f}")
```

---

## 附录

### 有用的链接

- **API 文档**: `docs/api.md`
- **设计文档**: `docs/superpowers/specs/2026-03-22-quant-platform-design.md`
- **Backtrader 文档**: https://www.backtrader.com/
- **FastAPI 文档**: https://fastapi.tiangolo.com/
- **Next.js 文档**: https://nextjs.org/docs

### 技术支持

如遇到问题，请按以下步骤排查：

1. 查阅本用户指南的 [常见问题](#常见问题) 部分
2. 查看日志文件（`logs/` 目录）
3. 检查 API 健康状态
4. 查阅 API 文档（`docs/api.md`）

### 更新日志

#### v1.0.0 (2026-03-24)

- 初始版本发布
- 实现核心功能：
  - 数据下载和管理
  - 策略开发和加载
  - 回测引擎
  - 参数优化
  - 结果展示

---

**感谢使用量化交易平台！祝您交易顺利！**
