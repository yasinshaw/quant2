# 量化交易平台设计文档

**创建日期**: 2026-03-22
**项目名称**: 个人量化交易平台
**版本**: 1.0

## 项目概述

### 目标

构建一个个人使用的量化交易平台，支持：
1. 下载和管理加密货币历史数据
2. 编写、回测和优化交易策略
3. 输出详细的回测报告和交易明细
4. 第二阶段对接OKX交易所，实现模拟和实盘交易
5. 提供Web界面和RESTful API供AI调用

### 核心原则

- **本地运行**：仅在本地使用，不考虑公网部署和安全问题
- **快速迭代**：采用单体应用架构，优先功能实现
- **开发者友好**：使用本地IDE编写策略，Git管理代码
- **扩展性强**：预留OKX实盘接口，支持未来扩展

## 技术架构

### 整体架构

**单体应用架构**：
```
quant2/
├── backend/                    # Python后端（FastAPI + Backtrader）
├── frontend/                   # Next.js前端
├── data/                       # SQLite数据库
└── docs/                       # 文档
```

**优势**：
- 开发速度快，易于维护
- 部署简单（一个后端进程 + 一个前端进程）
- 调试方便，所有代码在一起
- 足够灵活，后续可以拆分

### 技术栈

**后端**：
- **Web框架**: FastAPI 0.104+ - 高性能，自动生成API文档
- **回测引擎**: Backtrader 1.9+ - 成熟的量化回测框架
- **数据库**: SQLite3 - 轻量级，单文件存储
- **ORM**: SQLAlchemy 2.0+ - 数据库操作
- **数据处理**: pandas、numpy
- **HTTP客户端**: httpx - 用于Binance/OKX API调用
- **配置管理**: python-dotenv、pydantic-settings

**前端**：
- **框架**: Next.js 14+ (App Router)
- **语言**: TypeScript 5+
- **样式**: TailwindCSS
- **数据获取**: TanStack Query
- **图表库**: Recharts 或 Plotly
- **图标**: Lucide React

**数据源**：
- **初期**: Binance公开API（无需API key）
- **第二阶段**: OKX API（需要API key，用于实盘交易）

## 项目结构

```
quant2/
├── backend/                    # Python后端
│   ├── core/                  # 核心引擎
│   │   ├── strategy_base.py   # 策略基类
│   │   ├── backtest_engine.py # 回测引擎
│   │   ├── data_manager.py    # 数据管理器
│   │   ├── data_source.py     # 数据源抽象接口
│   │   ├── optimizer.py       # 参数优化器
│   │   └── strategy_loader.py # 策略动态加载器
│   ├── strategies/            # 用户策略文件夹
│   │   ├── __init__.py
│   │   └── example_strategy.py
│   ├── models/                # SQLAlchemy数据库模型
│   │   ├── candle.py         # K线数据
│   │   ├── trade.py          # 交易记录
│   │   ├── backtest_job.py   # 回测任务
│   │   ├── backtest_result.py # 回测结果
│   │   ├── optimization_job.py # 优化任务
│   │   └── optimization_result.py # 优化结果
│   ├── api/                   # FastAPI路由
│   │   ├── strategies.py     # 策略相关API
│   │   ├── data.py          # 数据管理API
│   │   ├── backtest.py      # 回测API
│   │   └── live.py          # 实盘交易API（第二阶段）
│   ├── utils/                # 工具函数
│   │   ├── binance_client.py # Binance API客户端
│   │   ├── okx_client.py    # OKX API客户端（第二阶段）
│   │   └── report_generator.py # 回测报告生成器
│   ├── config.py             # 配置管理
│   ├── main.py               # FastAPI入口
│   ├── requirements.txt      # Python依赖
│   └── .env                  # 环境变量
├── frontend/                  # Next.js前端
│   ├── src/
│   │   ├── app/             # Next.js 14 App Router
│   │   │   ├── page.tsx     # 首页Dashboard
│   │   │   ├── data/        # 数据管理页
│   │   │   ├── strategies/  # 策略列表页
│   │   │   ├── backtest/    # 回测配置和结果页
│   │   │   └── optimize/    # 参数优化页
│   │   ├── components/      # React组件
│   │   ├── lib/            # API客户端
│   │   │   └── api.ts      # API调用封装
│   │   └── types/          # TypeScript类型定义
│   │       └── index.ts
│   ├── package.json
│   └── tailwind.config.js
├── data/                     # SQLite数据库文件
│   └── quant.db
└── docs/                     # 文档
    └── superpowers/
        └── specs/           # 设计文档
```

## 数据库设计

### SQLite表结构

#### 1. 交易对配置表 (symbols)
```sql
CREATE TABLE symbols (
    id INTEGER PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,        -- 'BTCUSDT'
    base_currency TEXT NOT NULL,      -- 'BTC'
    quote_currency TEXT NOT NULL,     -- 'USDT'
    enabled BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### 2. K线数据表 (candles)
```sql
CREATE TABLE candles (
    id INTEGER PRIMARY KEY,
    symbol_id INTEGER NOT NULL,
    interval TEXT NOT NULL,           -- '1m', '5m', '1h', '1d'
    open_time TIMESTAMP NOT NULL,
    close_time TIMESTAMP NOT NULL,
    open_price REAL NOT NULL,
    high_price REAL NOT NULL,
    low_price REAL NOT NULL,
    close_price REAL NOT NULL,
    volume REAL NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (symbol_id) REFERENCES symbols(id),
    UNIQUE(symbol_id, interval, open_time)  -- 防止重复
);

-- 索引优化查询性能
CREATE INDEX idx_candles_lookup ON candles(symbol_id, interval, open_time);
```

**数据量估算**：
- 10个交易对 × 6个时间周期 × 1年1分钟数据
- 总计：约3150万条记录
- SQLite完全可以处理（支持TB级数据）

#### 3. 回测任务表 (backtest_jobs)
```sql
CREATE TABLE backtest_jobs (
    id INTEGER PRIMARY KEY,
    strategy_name TEXT NOT NULL,
    symbol TEXT NOT NULL,
    interval TEXT NOT NULL,
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP NOT NULL,
    parameters JSON NOT NULL,         -- 策略参数
    status TEXT NOT NULL,             -- 'pending', 'running', 'completed', 'failed'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);

CREATE INDEX idx_backtest_status ON backtest_jobs(status);
```

#### 4. 交易记录表 (trades)
```sql
CREATE TABLE trades (
    id INTEGER PRIMARY KEY,
    backtest_job_id INTEGER NOT NULL,
    order_id TEXT,                    -- Backtrader的订单ID
    symbol TEXT NOT NULL,
    side TEXT NOT NULL,               -- 'BUY', 'SELL'
    price REAL NOT NULL,
    size REAL NOT NULL,
    commission REAL DEFAULT 0,
    timestamp TIMESTAMP NOT NULL,
    FOREIGN KEY (backtest_job_id) REFERENCES backtest_jobs(id)
);

CREATE INDEX idx_trades_backtest ON trades(backtest_job_id);
```

#### 5. 回测结果汇总表 (backtest_results)
```sql
CREATE TABLE backtest_results (
    id INTEGER PRIMARY KEY,
    backtest_job_id INTEGER NOT NULL UNIQUE,
    total_return REAL NOT NULL,       -- 总收益率
    annual_return REAL,               -- 年化收益率
    sharpe_ratio REAL,                -- 夏普比率
    max_drawdown REAL NOT NULL,       -- 最大回撤
    win_rate REAL,                    -- 胜率
    profit_factor REAL,               -- 盈亏比
    total_trades INTEGER,             -- 总交易次数
    initial_cash REAL NOT NULL,
    final_value REAL NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (backtest_job_id) REFERENCES backtest_jobs(id)
);
```

#### 6. 参数优化任务表 (optimization_jobs)
```sql
CREATE TABLE optimization_jobs (
    id INTEGER PRIMARY KEY,
    strategy_name TEXT NOT NULL,
    symbol TEXT NOT NULL,
    interval TEXT NOT NULL,
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP NOT NULL,
    parameter_ranges JSON NOT NULL,   -- 参数范围定义
    optimization_method TEXT DEFAULT 'grid', -- 'grid', 'genetic'
    status TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);
```

#### 7. 参数优化结果表 (optimization_results)
```sql
CREATE TABLE optimization_results (
    id INTEGER PRIMARY KEY,
    optimization_job_id INTEGER NOT NULL,
    parameters JSON NOT NULL,         -- 最优参数
    score REAL NOT NULL,              -- 评分（如夏普比率）
    backtest_result_id INTEGER,       -- 关联到具体的回测结果
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (optimization_job_id) REFERENCES optimization_jobs(id),
    FOREIGN KEY (backtest_result_id) REFERENCES backtest_results(id)
);
```

## 核心模块设计

### 1. 策略系统

#### 策略基类 (StrategyBase)

```python
# backend/core/strategy_base.py
import backtrader as bt
from abc import ABC, abstractmethod
from typing import Dict, Any

class StrategyBase(bt.Strategy, ABC):
    """
    策略基类 - 所有用户策略必须继承此类

    用户需要实现:
    1. __init__(): 初始化指标
    2. next(): 每根K线调用一次，实现交易逻辑
    3. get_parameters(): 返回策略可调参数定义
    """

    # 策略元信息（子类应该覆盖）
    strategy_name: str = "Base Strategy"
    strategy_version: str = "1.0"
    strategy_description: str = "Base strategy class"

    def __init__(self):
        """初始化策略 - 子类应该调用 super().__init__()"""
        super().__init__()
        self.order = None
        self.buy_price = None
        self.buy_comm = None

    @abstractmethod
    def next(self):
        """
        交易逻辑 - 每根K线调用一次

        可用属性:
        - self.data.close: 收盘价
        - self.data.open: 开盘价
        - self.data.high: 最高价
        - self.data.low: 最低价
        - self.data.volume: 成交量
        - self.position: 当前持仓
        - self.orders: 待执行订单

        可用方法:
        - self.buy(size=...): 买入
        - self.sell(size=...): 卖出
        - self.close(): 平仓
        """
        pass

    def notify_order(self, order):
        """订单状态通知"""
        if order.status in [order.Submitted, order.Accepted]:
            return

        if order.status in [order.Completed]:
            if order.isbuy():
                self.buy_price = order.executed.price
                self.buy_comm = order.executed.comm
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log('Order Canceled/Margin/Rejected')

        self.order = None

    def notify_trade(self, trade):
        """交易完成通知"""
        if not trade.isclosed:
            return

        self.log(f'TRADE PROFIT, Gross: {trade.pnl}, Net: {trade.pnlcomm}')

    def log(self, txt, dt=None):
        """日志输出"""
        dt = dt or self.datas[0].datetime.date(0)
        print(f'[{dt.isoformat()}] {txt}')

    @classmethod
    @abstractmethod
    def get_parameters(cls) -> Dict[str, Any]:
        """
        返回策略可调参数定义

        格式:
        {
            'param_name': {
                'type': 'int' | 'float' | 'str' | 'bool',
                'default': default_value,
                'min': min_value,  # 仅数值类型
                'max': max_value,  # 仅数值类型
                'description': '参数说明'
            }
        }
        """
        pass

    @classmethod
    def get_metadata(cls) -> Dict[str, str]:
        """返回策略元信息"""
        return {
            'name': cls.strategy_name,
            'version': cls.strategy_version,
            'description': cls.strategy_description
        }
```

#### 策略加载器 (StrategyLoader)

```python
# backend/core/strategy_loader.py
import importlib.util
import inspect
from pathlib import Path
from typing import Dict, Type
from backend.core.strategy_base import StrategyBase

class StrategyLoader:
    """动态加载策略类"""

    def __init__(self, strategies_dir: str = "backend/strategies"):
        self.strategies_dir = Path(strategies_dir)

    def load_all(self) -> Dict[str, Type[StrategyBase]]:
        """
        扫描strategies目录，加载所有策略类

        返回: {strategy_name: strategy_class}
        """
        strategies = {}

        # 扫描所有.py文件
        for file_path in self.strategies_dir.glob("*.py"):
            if file_path.name.startswith("_"):
                continue

            # 动态导入模块
            module_name = file_path.stem
            spec = importlib.util.spec_from_file_location(module_name, file_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # 查找所有StrategyBase子类
            for name, obj in inspect.getmembers(module, inspect.isclass):
                if (issubclass(obj, StrategyBase) and
                    obj is not StrategyBase and
                    not obj.__name__.startswith('_')):
                    strategies[obj.strategy_name] = obj

        return strategies
```

#### 使用流程

1. **创建策略文件**：在 `backend/strategies/` 下创建Python文件
2. **继承基类**：实现 `next()` 和 `get_parameters()` 方法
3. **Web界面刷新**：点击"刷新策略"按钮
4. **后端加载**：StrategyLoader 扫描文件夹并加载所有策略
5. **前端显示**：策略列表显示在界面上，可选择回测

### 2. 数据管理系统

#### 数据源抽象接口

```python
# backend/core/data_source.py
from abc import ABC, abstractmethod
from typing import List
from datetime import datetime
from backend.models.candle import Candle

class DataSource(ABC):
    """数据源基类"""

    @abstractmethod
    async def fetch_candles(
        self,
        symbol: str,
        interval: str,
        start_time: datetime,
        end_time: datetime
    ) -> List[Candle]:
        """获取K线数据"""
        pass

    @abstractmethod
    async def get_supported_symbols(self) -> List[str]:
        """获取支持的交易对"""
        pass

    @abstractmethod
    async def get_supported_intervals(self) -> List[str]:
        """获取支持的K线周期"""
        pass
```

#### Binance数据源实现

```python
# backend/utils/binance_client.py
import httpx
from datetime import datetime
from typing import List
from backend.core.data_source import DataSource
from backend.models.candle import Candle

class BinanceDataSource(DataSource):
    """Binance数据源 - 公开API，无需API key"""

    def __init__(self, base_url: str = "https://api.binance.com"):
        self.base_url = base_url
        self.client = httpx.AsyncClient()

    async def fetch_candles(
        self,
        symbol: str,
        interval: str,
        start_time: datetime,
        end_time: datetime
    ) -> List[Candle]:
        """
        从Binance获取K线数据

        API文档: https://binance-docs.github.io/apidocs/spot/en/#kline-candlestick-data
        """
        candles = []

        # Binance API限制每次最多1000条数据
        current_start = start_time
        while current_start < end_time:
            params = {
                'symbol': symbol,
                'interval': interval,
                'startTime': int(current_start.timestamp() * 1000),
                'endTime': int(end_time.timestamp() * 1000),
                'limit': 1000
            }

            response = await self.client.get(
                f"{self.base_url}/api/v3/klines",
                params=params
            )
            response.raise_for_status()
            data = response.json()

            if not data:
                break

            # 转换为Candle对象
            for item in data:
                candle = Candle(
                    symbol=symbol,
                    interval=interval,
                    open_time=datetime.fromtimestamp(item[0] / 1000),
                    close_time=datetime.fromtimestamp(item[6] / 1000),
                    open_price=float(item[1]),
                    high_price=float(item[2]),
                    low_price=float(item[3]),
                    close_price=float(item[4]),
                    volume=float(item[5])
                )
                candles.append(candle)

            # 更新下一批的起始时间
            current_start = datetime.fromtimestamp(data[-1][6] / 1000)

        return candles

    async def get_supported_symbols(self) -> List[str]:
        """获取Binance支持的交易对"""
        response = await self.client.get(f"{self.base_url}/api/v3/exchangeInfo")
        response.raise_for_status()
        data = response.json()

        # 只返回USDT交易对
        symbols = [
            s['symbol'] for s in data['symbols']
            if s['quoteAsset'] == 'USDT' and s['status'] == 'TRADING'
        ]
        return sorted(symbols)

    async def get_supported_intervals(self) -> List[str]:
        """返回支持的K线周期"""
        return ['1m', '5m', '15m', '1h', '4h', '1d']
```

#### 数据管理器

```python
# backend/core/data_manager.py
from typing import List
from datetime import datetime
from backend.core.data_source import DataSource
from backend.models.candle import Candle
from backend.database import Database

class DataManager:
    """数据管理器 - 负责下载和存储历史数据"""

    def __init__(self, data_source: DataSource, db: Database):
        self.data_source = data_source
        self.db = db
        self.logger = logging.getLogger(__name__)

    async def download_and_save(
        self,
        symbol: str,
        interval: str,
        start_time: datetime,
        end_time: datetime
    ) -> dict:
        """
        下载并保存历史数据

        Returns:
        {
            'symbol': 'BTCUSDT',
            'interval': '1h',
            'count': 8760,
            'start_time': '2023-01-01',
            'end_time': '2024-01-01',
            'status': 'downloaded' | 'already_exists' | 'error'
        }
        """
        try:
            # 验证参数
            if start_time >= end_time:
                raise ValueError("start_time must be before end_time")

            if interval not in await self.data_source.get_supported_intervals():
                raise ValueError(f"Unsupported interval: {interval}")

            # 检查是否已有数据
            existing = self.db.get_candles_count(symbol, interval, start_time, end_time)
            if existing > 0:
                self.logger.info(f"Data already exists: {symbol} {interval} "
                               f"from {start_time} to {end_time} ({existing} candles)")
                return {
                    'symbol': symbol,
                    'interval': interval,
                    'count': existing,
                    'status': 'already_exists'
                }

            # 从数据源获取数据
            self.logger.info(f"Downloading data: {symbol} {interval} "
                           f"from {start_time} to {end_time}")

            candles = await self.data_source.fetch_candles(
                symbol, interval, start_time, end_time
            )

            if not candles:
                raise ValueError(f"No data received from data source")

            # 验证数据质量
            validated_candles = self._validate_candles(candles, interval)

            # 保存到数据库
            saved_count = self.db.save_candles(validated_candles)

            self.logger.info(f"Downloaded and saved {saved_count} candles for "
                           f"{symbol} {interval}")

            return {
                'symbol': symbol,
                'interval': interval,
                'count': saved_count,
                'start_time': start_time.isoformat(),
                'end_time': end_time.isoformat(),
                'status': 'downloaded'
            }

        except Exception as e:
            self.logger.error(f"Failed to download data: {e}", exc_info=True)
            return {
                'symbol': symbol,
                'interval': interval,
                'count': 0,
                'status': 'error',
                'error': str(e)
            }

    def _validate_candles(self, candles: List['Candle'], interval: str) -> List['Candle']:
        """
        验证K线数据质量

        检查:
        1. 价格合理性 (high >= low, open/close在high/low范围内)
        2. 时间连续性 (根据interval检查)
        3. 缺失值处理
        """
        validated = []
        prev_candle = None

        for candle in candles:
            # 检查价格合理性
            if candle.high_price < candle.low_price:
                self.logger.warning(f"Invalid candle: high < low at {candle.open_time}")
                continue

            if not (candle.low_price <= candle.open_price <= candle.high_price):
                self.logger.warning(f"Invalid candle: open price out of range at {candle.open_time}")
                continue

            if not (candle.low_price <= candle.close_price <= candle.high_price):
                self.logger.warning(f"Invalid candle: close price out of range at {candle.open_time}")
                continue

            # 检查价格为正数
            if candle.open_price <= 0 or candle.close_price <= 0:
                self.logger.warning(f"Invalid candle: non-positive price at {candle.open_time}")
                continue

            validated.append(candle)

        if len(validated) < len(candles):
            self.logger.warning(f"Validated {len(validated)}/{len(candles)} candles")

        return validated
```

### 2.5 数据库层

```python
# backend/database.py
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
from typing import List, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class Database:
    """数据库管理器 - 封装所有数据库操作"""

    def __init__(self, database_url: str):
        self.engine = create_engine(database_url, echo=False)
        self.SessionLocal = sessionmaker(bind=self.engine)

        # 启用外键约束（SQLite默认不启用）
        @event.listens_for(self.engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    def create_tables(self):
        """创建所有表"""
        from backend.models import candle, trade, backtest_job, backtest_result
        from backend.models import optimization_job, optimization_result, symbol
        from sqlalchemy.orm import declarative_base

        Base = declarative_base()
        # 导入所有模型以注册表结构
        Base.metadata.create_all(self.engine)
        logger.info("Database tables created")

    @contextmanager
    def get_session(self) -> Session:
        """获取数据库会话（上下文管理器）"""
        session = self.SessionLocal()
        try:
            yield session
            session.commit()  # 只在成功时commit
        except Exception as e:
            session.rollback()  # 失败时rollback
            logger.error(f"Database error: {e}")
            raise
        finally:
            session.close()

    # K线数据操作
    def get_candles(
        self,
        symbol: str,
        interval: str,
        start_time: str,
        end_time: str
    ) -> List['Candle']:
        """获取K线数据"""
        from backend.models.candle import Candle as CandleModel
        from backend.models.symbol import Symbol

        with self.get_session() as session:
            symbol_obj = session.query(Symbol).filter(
                Symbol.name == symbol
            ).first()

            if not symbol_obj:
                return []

            candles = session.query(CandleModel).filter(
                CandleModel.symbol_id == symbol_obj.id,
                CandleModel.interval == interval,
                CandleModel.open_time >= datetime.fromisoformat(start_time),
                CandleModel.open_time <= datetime.fromisoformat(end_time)
            ).order_by(CandleModel.open_time).all()

            return candles

    def save_candles(self, candles: List['Candle']) -> int:
        """批量保存K线数据"""
        from backend.models.candle import Candle as CandleModel
        from backend.models.symbol import Symbol

        with self.get_session() as session:
            saved_count = 0
            for candle in candles:
                # 获取或创建symbol
                symbol_obj = session.query(Symbol).filter(
                    Symbol.name == candle.symbol
                ).first()

                if not symbol_obj:
                    symbol_obj = Symbol(
                        name=candle.symbol,
                        base_currency=candle.symbol.replace('USDT', ''),
                        quote_currency='USDT'
                    )
                    session.add(symbol_obj)
                    session.flush()

                # 检查是否已存在
                existing = session.query(CandleModel).filter(
                    CandleModel.symbol_id == symbol_obj.id,
                    CandleModel.interval == candle.interval,
                    CandleModel.open_time == candle.open_time
                ).first()

                if not existing:
                    candle_model = CandleModel(
                        symbol_id=symbol_obj.id,
                        interval=candle.interval,
                        open_time=candle.open_time,
                        close_time=candle.close_time,
                        open_price=candle.open_price,
                        high_price=candle.high_price,
                        low_price=candle.low_price,
                        close_price=candle.close_price,
                        volume=candle.volume
                    )
                    session.add(candle_model)
                    saved_count += 1

            return saved_count

    def get_candles_count(
        self,
        symbol: str,
        interval: str,
        start_time: datetime,
        end_time: datetime
    ) -> int:
        """获取K线数量（用于检查是否已有数据）"""
        from backend.models.candle import Candle as CandleModel
        from backend.models.symbol import Symbol

        with self.get_session() as session:
            symbol_obj = session.query(Symbol).filter(
                Symbol.name == symbol
            ).first()

            if not symbol_obj:
                return 0

            return session.query(CandleModel).filter(
                CandleModel.symbol_id == symbol_obj.id,
                CandleModel.interval == interval,
                CandleModel.open_time >= start_time,
                CandleModel.open_time <= end_time
            ).count()

    # 回测结果操作
    def save_backtest_result(self, result: 'BacktestResult', trades: List['Trade']):
        """保存回测结果和交易记录"""
        with self.get_session() as session:
            session.add(result)
            session.flush()  # 获取result.id

            for trade in trades:
                trade.backtest_job_id = result.backtest_job_id
                session.add(trade)

    def get_backtest_result(self, job_id: int) -> Optional['BacktestResult']:
        """获取回测结果"""
        from backend.models.backtest_result import BacktestResult

        with self.get_session() as session:
            return session.query(BacktestResult).filter(
                BacktestResult.backtest_job_id == job_id
            ).first()

    def get_trades(self, backtest_job_id: int) -> List['Trade']:
        """获取交易记录"""
        from backend.models.trade import Trade

        with self.get_session() as session:
            return session.query(Trade).filter(
                Trade.backtest_job_id == backtest_job_id
            ).all()
```

### 3. 回测引擎

```python
# backend/core/backtest_engine.py
import backtrader as bt
from typing import Dict, Any, Type, List
from datetime import datetime
import pandas as pd
import logging
from backend.core.strategy_base import StrategyBase
from backend.database import Database
from backend.models.backtest_job import BacktestJob
from backend.models.backtest_result import BacktestResult
from backend.models.trade import Trade

logger = logging.getLogger(__name__)

class BacktestEngine:
    """回测引擎"""

    def __init__(self, db: Database):
        self.db = db

    async def run(
        self,
        strategy_class: Type[StrategyBase],
        symbol: str,
        interval: str,
        start_time: str,
        end_time: str,
        parameters: Dict[str, Any],
        initial_cash: float = 100000.0
    ) -> Dict[str, Any]:
        """
        执行回测

        返回回测结果和交易明细
        """
        # 1. 从数据库加载K线数据
        candles = self.db.get_candles(symbol, interval, start_time, end_time)

        if not candles:
            raise ValueError(f"No data found for {symbol} {interval} from {start_time} to {end_time}")

        # 2. 创建Backtrader cerebro实例
        cerebro = bt.Cerebro()

        # 3. 添加策略
        cerebro.addstrategy(strategy_class, **parameters)

        # 4. 准备数据
        data = pd.DataFrame([{
            'datetime': c.open_time,
            'open': c.open_price,
            'high': c.high_price,
            'low': c.low_price,
            'close': c.close_price,
            'volume': c.volume
        } for c in candles])

        data.set_index('datetime', inplace=True)

        # 5. 添加数据源
        data_feed = bt.feeds.PandasData(dataname=data)
        cerebro.adddata(data_feed)

        # 6. 设置初始资金
        cerebro.broker.setcash(initial_cash)
        cerebro.broker.setcommission(commission=0.001)  # 0.1%手续费

        # 7. 添加分析器
        cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
        cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
        cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
        cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')

        # 添加自定义Observer追踪交易明细
        class TradeRecorder(bt.Observer):
            """记录所有交易的Observer"""
            params = (('trades', []),)

            def next(self):
                # 记录已完成的交易
                for trade in self._owner._tradespending:
                    if trade.status == trade.Closed:
                        self.p.trades.append({
                            'entry_time': trade.dtopen.isoformat(),
                            'exit_time': trade dtclose.isoformat(),
                            'side': 'BUY' if trade.long else 'SELL',
                            'entry_price': trade.price,
                            'exit_price': trade.pnl / trade.size + trade.price if trade.size != 0 else 0,
                            'size': abs(trade.size),
                            'pnl': trade.pnl,
                            'commission': trade.commission
                        })

        cerebro.addobserver(TradeRecorder, trades=[])

        # 8. 运行回测
        results = cerebro.run()
        strategy = results[0]

        # 9. 提取交易明细
        trade_recorder = strategy.observers.traderecorder
        recorded_trades = trade_recorder.params.trades

        # 10. 提取分析结果
        sharpe = strategy.analyzers.sharpe.get_analysis()
        drawdown = strategy.analyzers.drawdown.get_analysis()
        returns = strategy.analyzers.returns.get_analysis()
        trade_analysis = strategy.analyzers.trades.get_analysis()

        # 11. 计算指标
        final_value = cerebro.broker.getvalue()
        total_return = (final_value - initial_cash) / initial_cash

        # 年化收益率（基于实际天数）
        start_dt = datetime.fromisoformat(start_time)
        end_dt = datetime.fromisoformat(end_time)
        days = (end_dt - start_dt).days
        if days > 0:
            annual_return = (1 + total_return) ** (365 / days) - 1
        else:
            annual_return = 0

        # 夏普比率
        sharpe_ratio = sharpe.get('sharperatio', 0) or 0

        # 最大回撤
        max_drawdown = drawdown.get('max', {}).get('drawdown', 0) / 100

        # 胜率
        total_trades = trade_analysis.get('total', {}).get('total', 0)
        won_trades = trade_analysis.get('won', {}).get('total', 0)
        win_rate = won_trades / total_trades if total_trades > 0 else 0

        # 盈亏比
        total_pnl = trade_analysis.get('pnl', {}).get('net', {}).get('total', 0)
        total_won = trade_analysis.get('won', {}).get('pnl', {}).get('total', 0)
        total_lost = abs(trade_analysis.get('lost', {}).get('pnl', {}).get('total', 0))
        profit_factor = total_won / total_lost if total_lost > 0 else 0

        # 12. 提取交易明细
        trades_list = []
        for trade in recorded_trades:
            trades_list.append({
                'timestamp': trade['exit_time'],  # 使用退出时间作为交易时间
                'symbol': symbol,
                'side': trade['side'],
                'price': trade['exit_price'],
                'size': trade['size'],
                'commission': trade['commission'],
                'value': trade['exit_price'] * trade['size'],
                'pnl': trade['pnl']
            })

        logger.info(f"Backtest completed: total_return={total_return:.2%}, "
                   f"sharpe={sharpe_ratio:.2f}, trades={total_trades}")

        return {
            'summary': {
                'total_return': total_return,
                'annual_return': annual_return,
                'sharpe_ratio': sharpe_ratio,
                'max_drawdown': max_drawdown,
                'win_rate': win_rate,
                'profit_factor': profit_factor,
                'total_trades': total_trades,
                'initial_cash': initial_cash,
                'final_value': final_value
            },
            'trades': trades_list
        }
```

### 4. 参数优化器

```python
# backend/core/optimizer.py
from itertools import product
from typing import Dict, List, Any, Type
from backend.core.backtest_engine import BacktestEngine
from backend.core.strategy_base import StrategyBase
from backend.models.optimization_result import OptimizationResult

class GridSearchOptimizer:
    """网格搜索参数优化器"""

    def __init__(self, backtest_engine: BacktestEngine):
        self.backtest_engine = backtest_engine

    async def optimize(
        self,
        strategy_class: Type[StrategyBase],
        symbol: str,
        interval: str,
        start_time: str,
        end_time: str,
        parameter_ranges: Dict[str, List[Any]],
        optimization_job_id: int
    ) -> OptimizationResult:
        """
        执行网格搜索优化

        Args:
            parameter_ranges: 参数范围，如:
                {
                    'fast_period': [5, 10, 15, 20],
                    'slow_period': [20, 30, 40, 50]
                }
        """
        # 生成所有参数组合
        param_names = list(parameter_ranges.keys())
        param_values = list(parameter_ranges.values())
        combinations = list(product(*param_values))

        total_combinations = len(combinations)
        print(f"Total parameter combinations: {total_combinations}")

        best_result = None
        best_params = None
        best_score = -float('inf')

        # 遍历所有参数组合
        for idx, combo in enumerate(combinations):
            params = dict(zip(param_names, combo))

            print(f"Testing combination {idx + 1}/{total_combinations}: {params}")

            # 执行回测
            backtest_result = await self.backtest_engine.run(
                strategy_class=strategy_class,
                symbol=symbol,
                interval=interval,
                start_time=start_time,
                end_time=end_time,
                parameters=params
            )

            # 计算评分（使用夏普比率）
            score = backtest_result['summary']['sharpe_ratio']

            # 更新最优结果
            if score > best_score:
                best_score = score
                best_params = params
                best_result = backtest_result

        # 保存最优结果
        optimization_result = OptimizationResult(
            optimization_job_id=optimization_job_id,
            parameters=best_params,
            score=best_score
        )

        return optimization_result
```

### 5. 报告生成器

```python
# backend/utils/report_generator.py
from typing import List, Dict
from backend.models.backtest_result import BacktestResult
from backend.models.trade import Trade
import pandas as pd

class ReportGenerator:
    """回测报告生成器"""

    def generate(
        self,
        backtest_result: BacktestResult,
        trades: List[Trade],
        equity_curve: List[Dict]
    ) -> Dict:
        """
        生成详细回测报告

        Returns:
            {
                'summary': {...},           # 核心指标
                'monthly_returns': [...],   # 月度收益
                'trade_analysis': {...},    # 交易分析
                'trades_detail': [...],     # 交易明细
                'equity_curve': [...]       # 资金曲线
            }
        """

        # 1. 核心指标
        summary = {
            'total_return': backtest_result.total_return,
            'annual_return': backtest_result.annual_return,
            'sharpe_ratio': backtest_result.sharpe_ratio,
            'max_drawdown': backtest_result.max_drawdown,
            'win_rate': backtest_result.win_rate,
            'profit_factor': backtest_result.profit_factor,
            'total_trades': backtest_result.total_trades,
            'initial_cash': backtest_result.initial_cash,
            'final_value': backtest_result.final_value
        }

        # 2. 月度收益分析
        monthly_returns = self._calculate_monthly_returns(trades)

        # 3. 交易分析
        trade_analysis = self._analyze_trades(trades)

        # 4. 交易明细
        trades_detail = [{
            'timestamp': t.timestamp.isoformat(),
            'symbol': t.symbol,
            'side': t.side,
            'price': float(t.price),
            'size': float(t.size),
            'commission': float(t.commission),
            'value': float(t.price * t.size)
        } for t in trades]

        # 5. 资金曲线
        equity_curve_data = [{
            'timestamp': point['timestamp'],
            'value': point['value']
        } for point in equity_curve]

        return {
            'summary': summary,
            'monthly_returns': monthly_returns,
            'trade_analysis': trade_analysis,
            'trades_detail': trades_detail,
            'equity_curve': equity_curve_data
        }

    def _calculate_monthly_returns(self, trades: List[Trade]) -> List[Dict]:
        """
        计算月度收益

        注意：需要成对的买卖交易才能计算盈亏
        """
        if not trades:
            return []

        trades_df = pd.DataFrame([{
            'timestamp': pd.to_datetime(t.timestamp),
            'side': t.side,
            'price': float(t.price),
            'size': float(t.size),
            'value': float(t.price * t.size)
        } for t in trades])

        trades_df['month'] = trades_df['timestamp'].dt.to_period('M')

        monthly_returns = []

        # 按月分组计算
        for month, group in trades_df.groupby('month'):
            buys = group[group['side'] == 'BUY']
            sells = group[group['side'] == 'SELL']

            # 简化计算：卖出总额 - 买入总额 = 月度盈亏
            buy_value = buys['value'].sum() if len(buys) > 0 else 0
            sell_value = sells['value'].sum() if len(sells) > 0 else 0

            # 注意：这个简化计算没有考虑持仓成本，实际应该使用FIFO或平均成本法
            pnl = sell_value - buy_value

            monthly_returns.append({
                'month': str(month),
                'pnl': float(pnl),
                'buy_trades': len(buys),
                'sell_trades': len(sells)
            })

        return monthly_returns

    def _analyze_trades(self, trades: List[Trade]) -> Dict:
        """分析交易统计"""
        if not trades:
            return {}

        buy_trades = [t for t in trades if t.side == 'BUY']
        sell_trades = [t for t in trades if t.side == 'SELL']

        import numpy as np

        return {
            'total_buy_trades': len(buy_trades),
            'total_sell_trades': len(sell_trades),
            'avg_trade_size': np.mean([t.size for t in trades]),
            'avg_trade_price': np.mean([t.price for t in trades]),
            'total_commission': sum([t.commission for t in trades])
        }
```

## API设计

### RESTful API接口

#### 1. 策略相关

```python
# backend/api/strategies.py
from fastapi import APIRouter
from typing import List, Dict
from backend.core.strategy_loader import StrategyLoader

router = APIRouter(prefix="/api/strategies", tags=["strategies"])

@router.get("/")
async def list_strategies() -> List[Dict]:
    """获取所有可用策略"""
    loader = StrategyLoader()
    strategies = loader.load_all()

    return [
        {
            'name': name,
            'version': cls.strategy_version,
            'description': cls.strategy_description,
            'parameters': cls.get_parameters()
        }
        for name, cls in strategies.items()
    ]

@router.post("/refresh")
async def refresh_strategies():
    """刷新策略列表（重新扫描strategies文件夹）"""
    loader = StrategyLoader()
    strategies = loader.load_all()

    return {
        'count': len(strategies),
        'strategies': list(strategies.keys())
    }
```

#### 2. 数据管理

```python
# backend/api/data.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from datetime import datetime

router = APIRouter(prefix="/api/data", tags=["data"])

class DownloadRequest(BaseModel):
    symbol: str
    interval: str
    start_time: str
    end_time: str

@router.post("/download")
async def download_data(request: DownloadRequest):
    """下载历史数据"""
    from backend.core.data_manager import DataManager
    from backend.utils.binance_client import BinanceDataSource
    from backend.database import db

    data_source = BinanceDataSource()
    manager = DataManager(data_source, db)

    result = await manager.download_and_save(
        symbol=request.symbol,
        interval=request.interval,
        start_time=datetime.fromisoformat(request.start_time),
        end_time=datetime.fromisoformat(request.end_time)
    )

    return result

@router.get("/symbols")
async def get_symbols():
    """获取支持的交易对列表"""
    from backend.utils.binance_client import BinanceDataSource

    data_source = BinanceDataSource()
    symbols = await data_source.get_supported_symbols()

    return {'symbols': symbols}

@router.get("/intervals")
async def get_intervals():
    """获取支持的K线周期"""
    return {
        'intervals': ['1m', '5m', '15m', '1h', '4h', '1d']
    }
```

#### 3. 回测相关

```python
# backend/api/backtest.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, List, Any

router = APIRouter(prefix="/api/backtest", tags=["backtest"])

class BacktestRequest(BaseModel):
    strategy_name: str
    symbol: str
    interval: str
    start_time: str
    end_time: str
    parameters: Dict[str, Any]
    initial_cash: float = 100000.0

class OptimizationRequest(BaseModel):
    strategy_name: str
    symbol: str
    interval: str
    start_time: str
    end_time: str
    parameter_ranges: Dict[str, List[Any]]
    initial_cash: float = 100000.0

@router.post("/run")
async def run_backtest(request: BacktestRequest):
    """执行回测"""
    from backend.core.strategy_loader import StrategyLoader
    from backend.core.backtest_engine import BacktestEngine
    from backend.database import db

    # 加载策略
    loader = StrategyLoader()
    strategies = loader.load_all()

    if request.strategy_name not in strategies:
        raise HTTPException(status_code=404, detail="Strategy not found")

    strategy_class = strategies[request.strategy_name]

    # 执行回测
    engine = BacktestEngine(db)
    result = await engine.run(
        strategy_class=strategy_class,
        symbol=request.symbol,
        interval=request.interval,
        start_time=request.start_time,
        end_time=request.end_time,
        parameters=request.parameters,
        initial_cash=request.initial_cash
    )

    return result

@router.post("/optimize")
async def optimize_parameters(request: OptimizationRequest):
    """参数优化（网格搜索）"""
    # TODO: 实现优化逻辑
    pass

@router.get("/result/{job_id}")
async def get_backtest_result(job_id: int):
    """获取回测结果"""
    # TODO: 从数据库获取结果并生成详细报告
    pass
```

### FastAPI主应用

```python
# backend/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.api import strategies, data, backtest

app = FastAPI(
    title="Quant Trading Platform",
    description="个人量化交易平台API",
    version="1.0.0"
)

# CORS配置（允许前端访问）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(strategies.router)
app.include_router(data.router)
app.include_router(backtest.router)

@app.get("/")
async def root():
    return {
        "message": "Quant Trading Platform API",
        "docs": "/docs",
        "version": "1.0.0"
    }
```

## 前端设计

### TypeScript类型定义

```typescript
// frontend/src/types/index.ts
export interface Strategy {
  name: string;
  version: string;
  description: string;
  parameters: Record<string, ParameterDefinition>;
}

export interface ParameterDefinition {
  type: 'int' | 'float' | 'str' | 'bool';
  default: any;
  min?: number;
  max?: number;
  description: string;
}

export interface BacktestResult {
  summary: {
    total_return: number;
    annual_return: number;
    sharpe_ratio: number;
    max_drawdown: number;
    win_rate: number;
    profit_factor: number;
    total_trades: number;
    initial_cash: number;
    final_value: number;
  };
  monthly_returns: Array<{
    month: string;
    pnl: number;
  }>;
  trade_analysis: {
    total_buy_trades: number;
    total_sell_trades: number;
    avg_trade_size: number;
    avg_trade_price: number;
    total_commission: number;
  };
  trades_detail: Array<{
    timestamp: string;
    symbol: string;
    side: 'BUY' | 'SELL';
    price: number;
    size: number;
    commission: number;
    value: number;
  }>;
  equity_curve: Array<{
    timestamp: string;
    value: number;
  }>;
}
```

### API客户端

```typescript
// frontend/src/lib/api.ts
const API_BASE = 'http://localhost:8000/api';

export const api = {
  // 策略相关
  async getStrategies(): Promise<Strategy[]> {
    const res = await fetch(`${API_BASE}/strategies`);
    return res.json();
  },

  async refreshStrategies(): Promise<void> {
    await fetch(`${API_BASE}/strategies/refresh`, { method: 'POST' });
  },

  // 数据相关
  async downloadData(symbol: string, interval: string, startTime: string, endTime: string) {
    const res = await fetch(`${API_BASE}/data/download`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ symbol, interval, startTime, endTime })
    });
    return res.json();
  },

  async getSymbols() {
    const res = await fetch(`${API_BASE}/data/symbols`);
    return res.json();
  },

  // 回测相关
  async runBacktest(params: any): Promise<{ job_id: number; result: BacktestResult }> {
    const res = await fetch(`${API_BASE}/backtest/run`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(params)
    });
    return res.json();
  },

  async optimizeParameters(params: any) {
    const res = await fetch(`${API_BASE}/backtest/optimize`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(params)
    });
    return res.json();
  },

  async getBacktestResult(jobId: number): Promise<BacktestResult> {
    const res = await fetch(`${API_BASE}/backtest/result/${jobId}`);
    return res.json();
  }
};
```

### 页面结构

```
frontend/src/app/
├── page.tsx                      # 首页 - Dashboard
├── data/
│   └── page.tsx                  # 数据管理页（下载历史数据）
├── strategies/
│   └── page.tsx                  # 策略列表页（查看、刷新）
├── backtest/
│   ├── page.tsx                  # 回测配置页（选择策略、参数）
│   └── result/[id]/
│       └── page.tsx              # 回测结果页（报告、图表、交易明细）
└── optimize/
    └── page.tsx                  # 参数优化页（配置范围、执行优化）
```

### 关键页面示例

#### 回测配置页

```tsx
// frontend/src/app/backtest/page.tsx
'use client';

import { useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { api } from '@/lib/api';

export default function BacktestPage() {
  const [selectedStrategy, setSelectedStrategy] = useState('');
  const [symbol, setSymbol] = useState('BTCUSDT');
  const [interval, setInterval] = useState('1h');
  const [parameters, setParameters] = useState<Record<string, any>>({});

  const { data: strategies } = useQuery({
    queryKey: ['strategies'],
    queryFn: api.getStrategies
  });

  const backtestMutation = useMutation({
    mutationFn: api.runBacktest,
    onSuccess: (data) => {
      window.location.href = `/backtest/result/${data.job_id}`;
    }
  });

  return (
    <div className="container mx-auto p-6">
      <h1 className="text-3xl font-bold mb-6">回测配置</h1>

      {/* 策略选择 */}
      <div className="mb-4">
        <label className="block mb-2">选择策略</label>
        <select
          value={selectedStrategy}
          onChange={(e) => setSelectedStrategy(e.target.value)}
          className="w-full p-2 border rounded"
        >
          <option value="">请选择策略</option>
          {strategies?.map((s) => (
            <option key={s.name} value={s.name}>{s.name}</option>
          ))}
        </select>
      </div>

      {/* 参数配置 */}
      {selectedStrategy && strategies && (
        <div className="mb-4">
          <h3 className="text-xl font-semibold mb-2">策略参数</h3>
          {Object.entries(
            strategies.find(s => s.name === selectedStrategy)?.parameters || {}
          ).map(([key, def]) => (
            <div key={key} className="mb-2">
              <label className="block mb-1">{def.description}</label>
              <input
                type={def.type === 'int' || def.type === 'float' ? 'number' : 'text'}
                value={parameters[key] ?? def.default}
                onChange={(e) => setParameters({
                  ...parameters,
                  [key]: def.type === 'int' ? parseInt(e.target.value) :
                         def.type === 'float' ? parseFloat(e.target.value) :
                         e.target.value
                })}
                min={def.min}
                max={def.max}
                className="w-full p-2 border rounded"
              />
            </div>
          ))}
        </div>
      )}

      <button
        onClick={() => backtestMutation.mutate({
          strategy_name: selectedStrategy,
          symbol,
          interval,
          start_time: '2023-01-01',
          end_time: '2024-01-01',
          parameters,
          initial_cash: 100000
        })}
        disabled={backtestMutation.isPending}
        className="bg-blue-500 text-white px-4 py-2 rounded"
      >
        {backtestMutation.isPending ? '回测中...' : '开始回测'}
      </button>
    </div>
  );
}
```

#### 回测结果页

```tsx
// frontend/src/app/backtest/result/[id]/page.tsx
'use client';

import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { LineChart, Line, XAxis, YAxis, Tooltip, Legend } from 'recharts';
import { useParams } from 'next/navigation';

export default function BacktestResultPage() {
  const params = useParams();
  const jobId = parseInt(params.id as string);

  const { data: result, isLoading } = useQuery({
    queryKey: ['backtest-result', jobId],
    queryFn: () => api.getBacktestResult(jobId)
  });

  if (isLoading) return <div>加载中...</div>;
  if (!result) return <div>未找到结果</div>;

  return (
    <div className="container mx-auto p-6">
      <h1 className="text-3xl font-bold mb-6">回测结果</h1>

      {/* 核心指标 */}
      <div className="grid grid-cols-3 gap-4 mb-6">
        <div className="p-4 bg-white rounded shadow">
          <div className="text-gray-600">总收益率</div>
          <div className="text-2xl font-bold">
            {(result.summary.total_return * 100).toFixed(2)}%
          </div>
        </div>
        <div className="p-4 bg-white rounded shadow">
          <div className="text-gray-600">夏普比率</div>
          <div className="text-2xl font-bold">
            {result.summary.sharpe_ratio.toFixed(2)}
          </div>
        </div>
        <div className="p-4 bg-white rounded shadow">
          <div className="text-gray-600">最大回撤</div>
          <div className="text-2xl font-bold text-red-600">
            {(result.summary.max_drawdown * 100).toFixed(2)}%
          </div>
        </div>
      </div>

      {/* 资金曲线图 */}
      <div className="bg-white p-4 rounded shadow mb-6">
        <h2 className="text-xl font-semibold mb-4">资金曲线</h2>
        <LineChart width={800} height={400} data={result.equity_curve}>
          <XAxis dataKey="timestamp" />
          <YAxis />
          <Tooltip />
          <Legend />
          <Line type="monotone" dataKey="value" stroke="#8884d8" />
        </LineChart>
      </div>

      {/* 交易明细表格 */}
      <div className="bg-white p-4 rounded shadow">
        <h2 className="text-xl font-semibold mb-4">交易明细</h2>
        <table className="w-full">
          <thead>
            <tr>
              <th className="text-left p-2">时间</th>
              <th className="text-left p-2">方向</th>
              <th className="text-right p-2">价格</th>
              <th className="text-right p-2">数量</th>
              <th className="text-right p-2">金额</th>
            </tr>
          </thead>
          <tbody>
            {result.trades_detail.map((trade, idx) => (
              <tr key={idx} className="border-t">
                <td className="p-2">{trade.timestamp}</td>
                <td className={trade.side === 'BUY' ? 'text-green-600' : 'text-red-600'}>
                  {trade.side}
                </td>
                <td className="text-right p-2">{trade.price.toFixed(2)}</td>
                <td className="text-right p-2">{trade.size.toFixed(4)}</td>
                <td className="text-right p-2">{trade.value.toFixed(2)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
```

## 配置与部署

### 环境配置

```python
# backend/config.py
from pydantic import validator
from pydantic_settings import BaseSettings
import os
from pathlib import Path

class Settings(BaseSettings):
    # 数据库
    database_url: str = "sqlite:///data/quant.db"

    # Binance API
    binance_base_url: str = "https://api.binance.com"
    binance_timeout: int = 30  # 秒

    # OKX API（第二阶段）
    okx_api_key: str = ""
    okx_secret_key: str = ""
    okx_passphrase: str = ""

    # 回测配置
    default_initial_cash: float = 100000.0
    max_workers: int = 4  # 参数优化时的并发数

    @validator('database_url')
    def validate_db_path(cls, v):
        """验证数据库路径存在"""
        if v.startswith('sqlite:///'):
            db_path = v.replace('sqlite:///', '')
            db_dir = os.path.dirname(db_path)
            if db_dir and not os.path.exists(db_dir):
                os.makedirs(db_dir, exist_ok=True)
        return v

    @validator('default_initial_cash')
    def validate_initial_cash(cls, v):
        """验证初始资金为正数"""
        if v <= 0:
            raise ValueError('Initial cash must be positive')
        return v

    class Config:
        env_file = ".env"

settings = Settings()
```

```python
# backend/logger_config.py
import logging
import sys
from pathlib import Path

def setup_logging(log_level: str = "INFO", log_file: str = None):
    """
    配置日志系统

    Args:
        log_level: 日志级别 (DEBUG, INFO, WARNING, ERROR)
        log_file: 日志文件路径（可选）
    """
    # 创建日志格式
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # 配置根日志器
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level, logging.INFO))

    # 控制台输出
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # 文件输出（如果指定）
    if log_file:
        log_dir = Path(log_file).parent
        if log_dir and not log_dir.exists():
            log_dir.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    # 降低第三方库的日志级别
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('werkzeug').setLevel(logging.WARNING)

    return root_logger
```

```env
# backend/.env
DATABASE_URL=sqlite:///data/quant.db
BINANCE_BASE_URL=https://api.binance.com

# 第二阶段使用
OKX_API_KEY=
OKX_SECRET_KEY=
OKX_PASSPHRASE=
```

### 依赖清单

```txt
# backend/requirements.txt
fastapi==0.104.1
uvicorn[standard]==0.24.0
backtrader==1.9.78.123
sqlalchemy==2.0.23
httpx==0.25.1
pandas==2.1.3
numpy==1.26.2
python-dotenv==1.0.0
pydantic==2.5.0
pydantic-settings==2.1.0
```

```json
// frontend/package.json
{
  "name": "quant-frontend",
  "version": "1.0.0",
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start"
  },
  "dependencies": {
    "next": "14.0.3",
    "react": "18.2.0",
    "react-dom": "18.2.0",
    "@tanstack/react-query": "5.8.4",
    "recharts": "2.10.1",
    "lucide-react": "0.294.0"
  },
  "devDependencies": {
    "typescript": "5.3.2",
    "tailwindcss": "3.3.5",
    "@types/node": "20.10.0",
    "@types/react": "18.2.39"
  }
}
```

### 启动脚本

```bash
#!/bin/bash
# start.sh

echo "Starting Quant Trading Platform..."

# 启动后端
cd backend
if [ ! -d "venv" ]; then
    python -m venv venv
fi
source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000 &
BACKEND_PID=$!

# 启动前端
cd ../frontend
npm install
npm run dev &
FRONTEND_PID=$!

echo ""
echo "=========================================="
echo "Quant Trading Platform Started!"
echo "=========================================="
echo "Backend:     http://localhost:8000"
echo "Frontend:    http://localhost:3000"
echo "API Docs:    http://localhost:8000/docs"
echo "=========================================="
echo ""
echo "Press Ctrl+C to stop"

# 等待中断信号
trap "kill $BACKEND_PID $FRONTEND_PID; exit" INT
wait
```

## 第二阶段扩展：OKX实盘交易

### 架构扩展点

预留OKX实盘交易接口，第二阶段实现：

```python
# backend/utils/okx_client.py
from typing import Dict, Any

class OKXClient:
    """OKX交易所客户端"""

    def __init__(self, api_key: str, secret_key: str, passphrase: str):
        self.api_key = api_key
        self.secret_key = secret_key
        self.passphrase = passphrase
        self.base_url = "https://www.okx.com"

    async def create_order(
        self,
        symbol: str,
        side: str,
        size: float,
        order_type: str = 'market'
    ) -> Dict[str, Any]:
        """创建订单"""
        # TODO: 实现OKX API调用
        pass

    async def get_balance(self) -> Dict[str, Any]:
        """获取账户余额"""
        # TODO: 实现OKX API调用
        pass

    async def subscribe_kline(
        self,
        symbol: str,
        interval: str,
        callback
    ):
        """订阅实时K线数据（WebSocket）"""
        # TODO: 实现WebSocket订阅
        pass
```

```python
# backend/core/live_trading.py
from backend.utils.okx_client import OKXClient

class LiveTradingEngine:
    """实盘交易引擎"""

    def __init__(self, okx_client: OKXClient):
        self.okx_client = okx_client
        self.running_strategies = {}

    async def start_strategy(
        self,
        strategy_name: str,
        symbol: str,
        parameters: dict,
        mode: str = 'paper'  # 'paper' 或 'live'
    ):
        """
        启动实盘策略

        流程:
        1. WebSocket订阅实时K线
        2. 每收到新K线，调用策略的next()
        3. 根据信号下单
        """
        # TODO: 实现实盘交易逻辑
        pass

    async def stop_strategy(self, strategy_id: str):
        """停止策略"""
        # TODO: 实现停止逻辑
        pass
```

### 扩展API

```python
# backend/api/live.py
from fastapi import APIRouter

router = APIRouter(prefix="/api/live", tags=["live-trading"])

@router.post("/start")
async def start_live_trading(
    strategy_name: str,
    symbol: str,
    parameters: dict,
    mode: str = 'paper'
):
    """
    启动实盘交易

    mode:
    - paper: 模拟交易（不真实下单）
    - live: 真实交易
    """
    # TODO: 第二阶段实现
    pass

@router.post("/stop/{strategy_id}")
async def stop_live_trading(strategy_id: str):
    """停止实盘交易"""
    # TODO: 第二阶段实现
    pass

@router.get("/status")
async def get_live_status():
    """获取实盘交易状态"""
    # TODO: 第二阶段实现
    pass
```

## 开发计划

### 第一阶段（核心功能）

**目标**：实现基础的回测平台

1. **后端核心**
   - [ ] 策略基类和加载器
   - [ ] 数据源（Binance）
   - [ ] 数据管理器
   - [ ] 回测引擎
   - [ ] 参数优化器（网格搜索）
   - [ ] 报告生成器

2. **数据库**
   - [ ] SQLite表结构创建
   - [ ] ORM模型实现

3. **API接口**
   - [ ] 策略管理API
   - [ ] 数据下载API
   - [ ] 回测执行API
   - [ ] 结果查询API

4. **前端界面**
   - [ ] 数据管理页
   - [ ] 策略列表页
   - [ ] 回测配置页
   - [ ] 结果展示页（图表 + 明细）
   - [ ] 参数优化页

5. **示例策略**
   - [ ] 双均线策略
   - [ ] RSI策略
   - [ ] MACD策略

### 第二阶段（实盘交易）

**目标**：对接OKX，实现模拟和实盘交易

1. **OKX集成**
   - [ ] OKX API客户端
   - [ ] WebSocket实时数据订阅
   - [ ] 订单管理

2. **实盘引擎**
   - [ ] 实时K线处理
   - [ ] 信号生成和执行
   - [ ] 仓位管理
   - [ ] 风险控制

3. **前端扩展**
   - [ ] 实盘交易页
   - [ ] 持仓管理页
   - [ ] 订单历史页
   - [ ] 实时监控页

4. **安全机制**
   - [ ] API Key加密存储
   - [ ] 交易确认
   - [ ] 止损止盈
   - [ ] 异常处理

## 总结

本设计文档详细描述了一个个人量化交易平台的技术架构、核心模块、数据库设计、API设计和前端界面。平台采用Python后端（FastAPI + Backtrader）+ TypeScript前端（Next.js）的单体应用架构，初期使用Binance公开API获取历史数据，第二阶段扩展到OKX实盘交易。

**核心优势**：
- 本地运行，无需公网部署
- 单体架构，开发维护简单
- 基于Backtrader，回测功能强大
- RESTful API，AI可直接调用
- 扩展性强，支持实盘交易

**技术亮点**：
- 策略动态加载（无需上传，本地IDE开发）
- 网格搜索参数优化
- 详细回测报告（核心指标 + 月度收益 + 交易明细）
- 数据源抽象（支持多交易所）

平台完全满足个人量化交易的需求，可以快速迭代和扩展。
