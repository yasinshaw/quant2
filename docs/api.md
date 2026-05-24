# Quantitative Trading Platform API Documentation

## Overview

### Base URL
```
http://localhost:8000
```

### Version
- API Version: v1
- Application Version: 1.0.0

### General Format
- All requests and responses use JSON format
- Content-Type: `application/json`
- Character encoding: UTF-8

### Authentication
- **None** - Currently no authentication required
- This is a personal/local trading platform

### Rate Limiting
- **None** - No rate limiting implemented
- Use responsibly when running backtests

### CORS Configuration
Allowed origins:
- `http://localhost:3000` (Next.js development server)
- `http://localhost:8000` (FastAPI server)
- `http://127.0.0.1:3000`
- `http://127.0.0.1:8000`

---

## Health Check

### GET /health

Check API health status and version.

**Request Example:**
```bash
curl http://localhost:8000/health
```

**Response Schema:**
| Field | Type | Description |
|-------|------|-------------|
| status | string | Health status ("healthy") |
| version | string | API version |

**Response Example:**
```json
{
  "status": "healthy",
  "version": "1.0.0"
}
```

---

## Strategies API

Base path: `/api/v1/strategies`

### GET /api/v1/strategies/

List all available trading strategies.

**Request Example:**
```bash
curl http://localhost:8000/api/v1/strategies/
```

**Response Schema:**
| Field | Type | Description |
|-------|------|-------------|
| strategies | array | List of strategy metadata |
| strategies[].name | string | Strategy name |
| strategies[].version | string | Strategy version |
| strategies[].description | string | Strategy description |

**Response Example:**
```json
{
  "strategies": [
    {
      "name": "DoubleMA",
      "version": "1.0.0",
      "description": "Double Moving Average crossover strategy"
    },
    {
      "name": "RSI",
      "version": "1.0.0",
      "description": "RSI overbought/oversold strategy"
    },
    {
      "name": "MACD",
      "version": "1.0.0",
      "description": "MACD signal crossover strategy"
    }
  ]
}
```

---

### POST /api/v1/strategies/refresh

Refresh strategy list from folder. Use this when new strategy files are added or modified.

**Request Example:**
```bash
curl -X POST http://localhost:8000/api/v1/strategies/refresh
```

**Response Schema:**
| Field | Type | Description |
|-------|------|-------------|
| message | string | Status message |
| count | integer | Number of strategies loaded |

**Response Example:**
```json
{
  "message": "Strategies refreshed",
  "count": 3
}
```

---

### GET /api/v1/strategies/{strategy_name}

Get detailed information about a specific strategy, including parameter definitions.

**Path Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| strategy_name | string | Name of the strategy |

**Request Example:**
```bash
curl http://localhost:8000/api/v1/strategies/DoubleMA
```

**Response Schema:**
| Field | Type | Description |
|-------|------|-------------|
| name | string | Strategy name |
| version | string | Strategy version |
| description | string | Strategy description |
| parameters | object | Parameter definitions |
| parameters.{name}.type | string | Parameter type (int, float, etc.) |
| parameters.{name}.default | any | Default value |
| parameters.{name}.min | number | Minimum value (optional) |
| parameters.{name}.max | number | Maximum value (optional) |
| parameters.{name}.description | string | Parameter description |

**Response Example:**
```json
{
  "name": "DoubleMA",
  "version": "1.0.0",
  "description": "Double Moving Average crossover strategy",
  "parameters": {
    "fast_period": {
      "type": "int",
      "default": 10,
      "min": 5,
      "max": 50,
      "description": "Fast moving average period"
    },
    "slow_period": {
      "type": "int",
      "default": 20,
      "min": 10,
      "max": 100,
      "description": "Slow moving average period"
    }
  }
}
```

**Error Codes:**
- `404 Not Found` - Strategy not found

**Error Response Example:**
```json
{
  "detail": "Strategy 'InvalidStrategy' not found"
}
```

---

## Data Management API

Base path: `/api/v1/data`

### GET /api/v1/data/symbols

List all trading symbols that have data in the database.

**Request Example:**
```bash
curl http://localhost:8000/api/v1/data/symbols
```

**Response Schema:**
| Field | Type | Description |
|-------|------|-------------|
| symbols | array | List of symbol names |

**Response Example:**
```json
{
  "symbols": ["BTCUSDT", "ETHUSDT", "BNBUSDT"]
}
```

**Error Codes:**
- `500 Internal Server Error` - Database error

---

### GET /api/v1/data/candles

Get historical candle data for a specific symbol, interval, and time range.

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| symbol | string | Yes | Trading pair (e.g., BTCUSDT) |
| interval | string | Yes | K-line interval (e.g., 1m, 5m, 1h, 1d) |
| start_time | string | Yes | Start time in ISO format (e.g., 2024-01-01T00:00:00) |
| end_time | string | Yes | End time in ISO format (e.g., 2024-01-31T23:59:59) |

**Request Example:**
```bash
curl "http://localhost:8000/api/v1/data/candles?symbol=BTCUSDT&interval=1h&start_time=2024-01-01T00:00:00&end_time=2024-01-31T23:59:59"
```

**Response Schema:**
| Field | Type | Description |
|-------|------|-------------|
| candles | array | List of candle data |
| candles[].open_time | string | Candle open time (ISO format) |
| candles[].close_time | string | Candle close time (ISO format) |
| candles[].open | number | Open price |
| candles[].high | number | High price |
| candles[].low | number | Low price |
| candles[].close | number | Close price |
| candles[].volume | number | Trading volume |

**Response Example:**
```json
{
  "candles": [
    {
      "open_time": "2024-01-01T00:00:00",
      "close_time": "2024-01-01T01:00:00",
      "open": 42000.0,
      "high": 42500.0,
      "low": 41800.0,
      "close": 42300.0,
      "volume": 100.5
    },
    {
      "open_time": "2024-01-01T01:00:00",
      "close_time": "2024-01-01T02:00:00",
      "open": 42300.0,
      "high": 42800.0,
      "low": 42200.0,
      "close": 42600.0,
      "volume": 95.3
    }
  ]
}
```

**Error Codes:**
- `400 Bad Request` - Invalid datetime format or start_time >= end_time
- `500 Internal Server Error` - Database error

**Error Response Example:**
```json
{
  "detail": "Invalid datetime format: Invalid isoformat string"
}
```

---

### POST /api/v1/data/download

Download historical data from Binance and save to database.

**Request Body:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| symbol | string | Yes | Trading pair (e.g., BTCUSDT) |
| interval | string | Yes | K-line interval (e.g., 1h) |
| start_time | string | Yes | Start time in ISO format |
| end_time | string | Yes | End time in ISO format |

**Request Example:**
```bash
curl -X POST http://localhost:8000/api/v1/data/download \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "BTCUSDT",
    "interval": "1h",
    "start_time": "2024-01-01T00:00:00",
    "end_time": "2024-01-31T23:59:59"
  }'
```

**Response Schema:**
| Field | Type | Description |
|-------|------|-------------|
| symbol | string | Trading pair |
| interval | string | K-line interval |
| count | integer | Number of candles downloaded or existing |
| status | string | Status: "downloaded", "already_exists", or "error" |
| message | string | Success message (only on success) |
| error | string | Error message (only on error) |

**Response Examples:**

Success (downloaded):
```json
{
  "symbol": "BTCUSDT",
  "interval": "1h",
  "count": 720,
  "status": "downloaded",
  "message": "Data downloaded successfully"
}
```

Success (already exists):
```json
{
  "symbol": "BTCUSDT",
  "interval": "1h",
  "count": 720,
  "status": "already_exists",
  "message": "Data already exists"
}
```

Error:
```json
{
  "symbol": "BTCUSDT",
  "interval": "1h",
  "count": 0,
  "status": "error",
  "error": "Failed to fetch data from Binance"
}
```

**Error Codes:**
- `400 Bad Request` - Missing required fields or invalid datetime format

---

### GET /api/v1/data/status/{symbol}/{interval}

Check data availability status for a symbol/interval combination.

**Path Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| symbol | string | Trading pair (e.g., BTCUSDT) |
| interval | string | K-line interval (e.g., 1h) |

**Request Example:**
```bash
curl http://localhost:8000/api/v1/data/status/BTCUSDT/1h
```

**Response Schema:**
| Field | Type | Description |
|-------|------|-------------|
| symbol | string | Trading pair |
| interval | string | K-line interval |
| available | boolean | Whether data is available |
| count | integer | Total number of candles |

**Response Example:**
```json
{
  "symbol": "BTCUSDT",
  "interval": "1h",
  "available": true,
  "count": 8760
}
```

---

## Backtest API

Base path: `/api/v1/backtest`

### POST /api/v1/backtest/run

Run a single backtest for a strategy.

**Request Body:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| strategy_name | string | Yes | Name of strategy to run |
| symbol | string | Yes | Trading pair (e.g., BTCUSDT) |
| interval | string | Yes | K-line interval (e.g., 1h) |
| start_time | string | Yes | Start time in ISO format |
| end_time | string | Yes | End time in ISO format |
| parameters | object | No | Strategy parameters (default: {}) |
| initial_cash | number | No | Initial cash amount (default: 100000) |

**Request Example:**
```bash
curl -X POST http://localhost:8000/api/v1/backtest/run \
  -H "Content-Type: application/json" \
  -d '{
    "strategy_name": "DoubleMA",
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

**Response Schema:**
| Field | Type | Description |
|-------|------|-------------|
| final_value | number | Final portfolio value |
| pnl | number | Absolute profit/loss |
| pnl_pct | number | Percentage profit/loss |
| trades | array | List of trades executed |

**Response Example:**
```json
{
  "final_value": 125000.50,
  "pnl": 25000.50,
  "pnl_pct": 25.0,
  "trades": [
    {
      "order_id": "order_001",
      "symbol": "BTCUSDT",
      "side": "BUY",
      "price": 42000.0,
      "size": 1.0,
      "commission": 42.0,
      "timestamp": "2024-01-15T10:30:00"
    },
    {
      "order_id": "order_002",
      "symbol": "BTCUSDT",
      "side": "SELL",
      "price": 45000.0,
      "size": 1.0,
      "commission": 45.0,
      "timestamp": "2024-02-20T14:15:00"
    }
  ]
}
```

**Error Codes:**
- `400 Bad Request` - Missing required fields or invalid datetime format
- `404 Not Found` - Strategy not found
- `500 Internal Server Error` - Backtest execution failed

**Error Response Example:**
```json
{
  "detail": "Strategy 'InvalidStrategy' not found"
}
```

---

### POST /api/v1/backtest/optimize

Run parameter optimization using grid search.

**Request Body:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| strategy_name | string | Yes | Name of strategy to optimize |
| symbol | string | Yes | Trading pair |
| interval | string | Yes | K-line interval |
| start_time | string | Yes | Start time in ISO format |
| end_time | string | Yes | End time in ISO format |
| parameter_ranges | object | Yes | Dict of parameter names to value lists |
| initial_cash | number | No | Initial cash (default: 100000) |
| optimization_method | string | No | Optimization method (default: "grid") |

**Request Example:**
```bash
curl -X POST http://localhost:8000/api/v1/backtest/optimize \
  -H "Content-Type: application/json" \
  -d '{
    "strategy_name": "DoubleMA",
    "symbol": "BTCUSDT",
    "interval": "1h",
    "start_time": "2024-01-01T00:00:00",
    "end_time": "2024-12-31T23:59:59",
    "parameter_ranges": {
      "fast_period": [5, 10, 15],
      "slow_period": [20, 30, 40]
    },
    "initial_cash": 100000,
    "optimization_method": "grid"
  }'
```

**Response Schema:**
| Field | Type | Description |
|-------|------|-------------|
| parameters | object | Best parameter combination |
| backtest_result | object | Backtest result for best parameters |
| optimization_result | object | Optimization result from database |

**Response Example:**
```json
{
  "parameters": {
    "fast_period": 10,
    "slow_period": 30
  },
  "backtest_result": {
    "final_value": 135000.0,
    "pnl": 35000.0,
    "pnl_pct": 35.0
  },
  "optimization_result": {
    "id": 1,
    "score": 2.5,
    "parameters": {
      "fast_period": 10,
      "slow_period": 30
    }
  }
}
```

**Error Codes:**
- `400 Bad Request` - Missing required fields or invalid datetime format
- `404 Not Found` - Strategy not found
- `500 Internal Server Error` - Optimization failed

---

### GET /api/v1/backtest/jobs

List backtest jobs with optional status filter.

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| status | string | No | Filter by status: "pending", "running", "completed", "failed" |

**Request Example:**
```bash
curl "http://localhost:8000/api/v1/backtest/jobs?status=completed"
```

**Response Schema:**
| Field | Type | Description |
|-------|------|-------------|
| jobs | array | List of jobs |
| jobs[].id | integer | Job ID |
| jobs[].strategy_name | string | Strategy name |
| jobs[].symbol | string | Trading pair |
| jobs[].status | string | Job status |
| jobs[].created_at | string | Creation timestamp (ISO format) |

**Response Example:**
```json
{
  "jobs": [
    {
      "id": 1,
      "strategy_name": "DoubleMA",
      "symbol": "BTCUSDT",
      "status": "completed",
      "created_at": "2024-01-15T10:30:00"
    },
    {
      "id": 2,
      "strategy_name": "RSI",
      "symbol": "ETHUSDT",
      "status": "completed",
      "created_at": "2024-01-16T14:20:00"
    }
  ]
}
```

---

### GET /api/v1/backtest/jobs/{job_id}

Get job status and results for a specific backtest job.

**Path Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| job_id | integer | Job ID to retrieve |

**Request Example:**
```bash
curl http://localhost:8000/api/v1/backtest/jobs/1
```

**Response Schema:**
| Field | Type | Description |
|-------|------|-------------|
| job | object | Job details |
| job.id | integer | Job ID |
| job.strategy_name | string | Strategy name |
| job.symbol | string | Trading pair |
| job.interval | string | K-line interval |
| job.status | string | Job status |
| job.created_at | string | Creation timestamp |
| result | object | Backtest result (only if completed) |
| result.total_return | number | Total return percentage |
| result.annual_return | number | Annual return percentage |
| result.sharpe_ratio | number | Sharpe ratio |
| result.max_drawdown | number | Maximum drawdown percentage |
| result.win_rate | number | Win rate percentage |
| result.profit_factor | number | Profit factor |
| result.total_trades | integer | Total number of trades |
| result.initial_cash | number | Initial cash amount |
| result.final_value | number | Final portfolio value |

**Response Example:**
```json
{
  "job": {
    "id": 1,
    "strategy_name": "DoubleMA",
    "symbol": "BTCUSDT",
    "interval": "1h",
    "status": "completed",
    "created_at": "2024-01-15T10:30:00"
  },
  "result": {
    "total_return": 25.5,
    "annual_return": 25.5,
    "sharpe_ratio": 1.8,
    "max_drawdown": -15.2,
    "win_rate": 62.5,
    "profit_factor": 1.65,
    "total_trades": 48,
    "initial_cash": 100000,
    "final_value": 125500
  }
}
```

**Error Codes:**
- `404 Not Found` - Job not found

**Error Response Example:**
```json
{
  "detail": "Job 999 not found"
}
```

---

### GET /api/v1/backtest/results/{result_id}/report

Get detailed backtest report including monthly returns, trade analysis, and equity curve.

**Path Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| result_id | integer | Backtest result ID |

**Request Example:**
```bash
curl http://localhost:8000/api/v1/backtest/results/1/report
```

**Response Schema:**
| Field | Type | Description |
|-------|------|-------------|
| summary | object | Performance metrics summary |
| monthly_returns | object | Monthly returns breakdown |
| trade_analysis | object | Per-trade analysis with statistics |
| equity_curve | array | Equity curve data points |

**Response Example:**
```json
{
  "summary": {
    "total_return": 25.5,
    "annual_return": 25.5,
    "sharpe_ratio": 1.8,
    "max_drawdown": -15.2,
    "win_rate": 62.5,
    "profit_factor": 1.65,
    "total_trades": 48,
    "avg_trade_duration": "5.2 days"
  },
  "monthly_returns": {
    "2024-01": 5.2,
    "2024-02": 3.8,
    "2024-03": -2.1,
    "2024-04": 6.5
  },
  "trade_analysis": {
    "winning_trades": 30,
    "losing_trades": 18,
    "avg_win": 1500.0,
    "avg_loss": -800.0,
    "largest_win": 5000.0,
    "largest_loss": -2500.0
  },
  "equity_curve": [
    {"date": "2024-01-01T00:00:00", "value": 100000},
    {"date": "2024-01-02T00:00:00", "value": 101500},
    {"date": "2024-01-03T00:00:00", "value": 99800}
  ]
}
```

**Error Codes:**
- `404 Not Found` - Result not found

---

## Error Handling

### Error Response Format

All error responses follow a consistent format:

```json
{
  "detail": "Error message describing what went wrong"
}
```

For validation errors:
```json
{
  "error": "Validation error",
  "details": [
    {
      "loc": ["body", "symbol"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

### Common Error Codes

| Status Code | Description | Common Causes |
|-------------|-------------|---------------|
| 400 | Bad Request | Missing required fields, invalid datetime format, invalid parameters |
| 404 | Not Found | Strategy not found, job not found, result not found |
| 500 | Internal Server Error | Database errors, unexpected exceptions, backtest failures |

### Error Examples

**400 Bad Request - Missing Field:**
```json
{
  "detail": "Missing required field: symbol"
}
```

**400 Bad Request - Invalid Datetime:**
```json
{
  "detail": "Invalid datetime format: Invalid isoformat string"
}
```

**400 Bad Request - Invalid Time Range:**
```json
{
  "detail": "start_time must be before end_time"
}
```

**404 Not Found - Strategy:**
```json
{
  "detail": "Strategy 'InvalidStrategy' not found"
}
```

**404 Not Found - Job:**
```json
{
  "detail": "Job 999 not found"
}
```

**500 Internal Server Error:**
```json
{
  "detail": "Backtest failed: Insufficient data for specified time range"
}
```

---

## Data Models

### Candle

Historical candlestick/OHLCV data.

| Field | Type | Description |
|-------|------|-------------|
| open_time | datetime | Candle open timestamp |
| close_time | datetime | Candle close timestamp |
| open_price | float | Opening price |
| high_price | float | Highest price during candle |
| low_price | float | Lowest price during candle |
| close_price | float | Closing price |
| volume | float | Trading volume |
| symbol | string | Trading pair symbol |
| interval | string | K-line interval (1m, 5m, 1h, 1d) |

### BacktestJob

Represents a backtest execution job.

| Field | Type | Description |
|-------|------|-------------|
| id | integer | Unique job identifier |
| strategy_name | string | Strategy being tested |
| symbol | string | Trading pair |
| interval | string | K-line interval |
| start_time | datetime | Backtest start time |
| end_time | datetime | Backtest end time |
| parameters | object | Strategy parameters |
| status | string | Job status: "pending", "running", "completed", "failed" |
| created_at | datetime | Job creation timestamp |
| completed_at | datetime | Job completion timestamp (nullable) |

### BacktestResult

Performance metrics from a completed backtest.

| Field | Type | Description |
|-------|------|-------------|
| id | integer | Unique result identifier |
| backtest_job_id | integer | Associated job ID |
| total_return | float | Total return percentage |
| annual_return | float | Annual return percentage |
| sharpe_ratio | float | Sharpe ratio (risk-adjusted return) |
| max_drawdown | float | Maximum drawdown percentage (negative) |
| win_rate | float | Win rate percentage |
| profit_factor | float | Profit factor (gross profit / gross loss) |
| total_trades | integer | Total number of trades |
| initial_cash | float | Initial portfolio value |
| final_value | float | Final portfolio value |

### Trade

Individual trade execution record.

| Field | Type | Description |
|-------|------|-------------|
| id | integer | Unique trade identifier |
| backtest_job_id | integer | Associated backtest job |
| order_id | string | Backtrader order ID |
| symbol | string | Trading pair |
| side | string | Trade side: "BUY" or "SELL" |
| price | float | Execution price |
| size | float | Position size |
| commission | float | Trading commission |
| timestamp | datetime | Execution timestamp |

### OptimizationJob

Represents a parameter optimization job.

| Field | Type | Description |
|-------|------|-------------|
| id | integer | Unique job identifier |
| strategy_name | string | Strategy being optimized |
| symbol | string | Trading pair |
| interval | string | K-line interval |
| start_time | datetime | Optimization period start |
| end_time | datetime | Optimization period end |
| parameter_ranges | object | Parameter ranges to test |
| optimization_method | string | Method: "grid" or "genetic" |
| status | string | Job status |
| created_at | datetime | Job creation timestamp |
| completed_at | datetime | Job completion timestamp (nullable) |

### OptimizationResult

Best parameters found from optimization.

| Field | Type | Description |
|-------|------|-------------|
| id | integer | Unique result identifier |
| optimization_job_id | integer | Associated optimization job |
| parameters | object | Best parameter combination |
| score | float | Optimization score (e.g., Sharpe ratio) |
| backtest_result_id | integer | Associated backtest result |

---

## Usage Examples

### Running a Complete Backtest Workflow

1. **Check available strategies:**
```bash
curl http://localhost:8000/api/v1/strategies/
```

2. **Get strategy details:**
```bash
curl http://localhost:8000/api/v1/strategies/DoubleMA
```

3. **Download historical data:**
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

4. **Run backtest:**
```bash
curl -X POST http://localhost:8000/api/v1/backtest/run \
  -H "Content-Type: application/json" \
  -d '{
    "strategy_name": "DoubleMA",
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

5. **Get detailed report:**
```bash
curl http://localhost:8000/api/v1/backtest/results/1/report
```

### Running Parameter Optimization

```bash
curl -X POST http://localhost:8000/api/v1/backtest/optimize \
  -H "Content-Type: application/json" \
  -d '{
    "strategy_name": "DoubleMA",
    "symbol": "BTCUSDT",
    "interval": "1h",
    "start_time": "2024-01-01T00:00:00",
    "end_time": "2024-12-31T23:59:59",
    "parameter_ranges": {
      "fast_period": [5, 10, 15, 20],
      "slow_period": [20, 30, 40, 50]
    }
  }'
```

---

## API Summary

| Category | Endpoint | Method | Description |
|----------|----------|--------|-------------|
| Health | /health | GET | Health check |
| Strategies | /api/v1/strategies/ | GET | List all strategies |
| Strategies | /api/v1/strategies/refresh | POST | Refresh strategy list |
| Strategies | /api/v1/strategies/{name} | GET | Get strategy details |
| Data | /api/v1/data/symbols | GET | List all symbols |
| Data | /api/v1/data/candles | GET | Get candle data |
| Data | /api/v1/data/download | POST | Download historical data |
| Data | /api/v1/data/status/{symbol}/{interval} | GET | Check data status |
| Backtest | /api/v1/backtest/run | POST | Run backtest |
| Backtest | /api/v1/backtest/optimize | POST | Run optimization |
| Backtest | /api/v1/backtest/jobs | GET | List backtest jobs |
| Backtest | /api/v1/backtest/jobs/{id} | GET | Get job details |
| Backtest | /api/v1/backtest/results/{id}/report | GET | Get backtest report |

---

## Notes

- All timestamps are in ISO 8601 format (e.g., `2024-01-01T00:00:00`)
- All monetary values are floating point numbers
- All percentages are floating point numbers (e.g., 25.5 means 25.5%)
- The API runs on port 8000 by default
- No authentication is currently implemented (personal/local use only)
- No rate limiting is implemented (use responsibly)
