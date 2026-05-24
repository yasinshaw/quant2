# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A quantitative trading platform for strategy development, backtesting, and parameter optimization using Backtrader framework with a FastAPI backend and Next.js frontend.

**Tech Stack:**
- Backend: FastAPI + Backtrader + SQLite + Pydantic
- Frontend: Next.js 14 + TypeScript + Tailwind CSS + React Query + Recharts
- Data Source: Binance public API (no authentication required)
- Testing: pytest (backend) + Playwright (E2E frontend)

## Development Commands

### Quick Start (Recommended)
```bash
# Start both backend and frontend servers
./start.sh start

# View service status
./start.sh status

# View logs
./start.sh logs backend   # Backend logs
./start.sh logs frontend  # Frontend logs

# Stop all services
./start.sh stop

# Restart all services
./start.sh restart
```

The startup script manages both services:
- Backend: http://localhost:8000
- Frontend: http://localhost:3002
- Logs: `logs/backend.log` and `logs/frontend.log`
- PIDs: `.pids/backend.pid` and `.pids/frontend.pid`

### Manual Start (Alternative)

#### Backend
```bash
# Run backend server
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python main.py  # Runs on http://localhost:8000

# Run backend tests
cd ~/code/quant2
pytest tests/ -v                    # All tests
pytest tests/test_backtest_engine.py -v  # Single test file
pytest tests/test_backtest_engine.py::TestBacktestEngine::test_run -v  # Single test
pytest --cov=backend tests/         # With coverage
```

#### Frontend
```bash
# Run frontend development server
cd frontend
pnpm install
pnpm dev  # Runs on http://localhost:3002

# Run frontend tests
pnpm lint               # Linting
pnpm test:e2e          # E2E tests with Playwright
pnpm test:e2e:ui       # E2E tests with UI
pnpm test:e2e:debug    # Debug E2E tests
```

## Architecture

### Backend Structure

The backend follows a layered architecture with clear separation of concerns:

**Core Layer** (`backend/core/`):
- `strategy_base.py` - Base class all strategies must inherit from. Enforces interface compliance (get_parameters, next, __init__)
- `backtest_engine.py` - Orchestrates backtests: loads data from DB, configures Backtrader, runs strategy, records trades, calculates metrics
- `data_manager.py` - Coordinates data download from Binance, validation, and storage to database
- `optimizer.py` - Parameter optimization using grid search with parallel execution
- `strategy_loader.py` - Dynamically loads strategy classes from `backend/strategies/` directory
- `report_generator.py` - Generates performance reports from backtest results

**Data Flow:**
1. User requests → FastAPI endpoints (`backend/api/`)
2. API routes delegate to core business logic
3. Core components use `Database` class for persistence
4. Strategies are loaded dynamically and executed by `BacktestEngine`
5. Results are stored in SQLite database

**Database Layer** (`backend/database.py`):
- SQLAlchemy-based ORM
- Manages candles, backtest results, optimization results, trades
- Database path configured via `backend/config.py` (default: `data/quant.db`)

**Strategy System:**
- All strategies inherit from `StrategyBase` (which extends `bt.Strategy`)
- Must implement: `__init__()`, `next()`, `get_parameters()`
- `get_parameters()` returns dict defining tunable parameters with type, default, min/max values
- Strategies are discovered automatically by scanning `backend/strategies/*.py`

**Observers** (`backend/observers/`):
- `TradeRecorder` - Backtrader observer that records all trade details during backtest execution
- Attached to Backtrader cerebro instance to capture buy/sell events

### Frontend Structure

Next.js 14 App Router application with TypeScript:

**Pages** (`frontend/app/`):
- `/` - Home page
- `/strategies` - List available strategies and view details
- `/data` - Download historical data from Binance
- `/backtest` - Configure and run backtests
- `/results/[id]` - View backtest results with equity curve, monthly returns, trade table
- `/optimize` - Parameter optimization interface

**Components** (`frontend/components/`):
- Feature-based organization (StrategyCard, BacktestForm, OptimizationForm, etc.)
- Recharts for data visualization (EquityCurve, MonthlyReturns)
- React Query for API state management via `QueryProvider`

**API Integration:**
- React Query manages server state
- Axios for HTTP requests to backend
- Backend URL: `http://localhost:8000`

### Key Architectural Patterns

**Strategy Pattern:**
- All trading strategies implement common interface (`StrategyBase`)
- Strategies are self-describing via `get_parameters()` metadata
- Enables dynamic discovery and parameter UI generation

**Observer Pattern:**
- `TradeRecorder` observes Backtrader strategy execution
- Records trades without coupling to strategy implementation

**Repository Pattern:**
- `Database` class abstracts persistence layer
- Provides clean API for candles, results, trades

**Configuration:**
- `backend/config.py` uses Pydantic Settings
- Environment variables override defaults via `.env` file
- Validates configuration on startup

## API Endpoints

Backend exposes REST API under `/api/v1/`:

**Strategies** (`/api/v1/strategies`):
- `GET /` - List all available strategies
- `GET /{strategy_name}` - Get strategy details and parameter definitions

**Data** (`/api/v1/data`):
- `POST /download` - Download historical data from Binance
- `GET /status` - Check available data for symbol/interval

**Backtest** (`/api/v1/backtest`):
- `POST /run` - Execute backtest with strategy and parameters
- `GET /results/{result_id}` - Retrieve backtest results
- `GET /results/{result_id}/trades` - Get trade list for backtest

## Testing Strategy

**Backend Testing (pytest):**
- Unit tests for core components (backtest engine, data manager, optimizer)
- Integration tests for API endpoints using FastAPI TestClient
- Test database uses in-memory SQLite for isolation
- Coverage target: 80%+
- Test files mirror source structure: `tests/test_<module>.py`

**Frontend Testing (Playwright):**
- E2E tests in `frontend/e2e/`
- Tests critical user flows: data download, backtest execution, results viewing
- Base URL: `http://localhost:3000`
- Run against running dev server (start with `pnpm dev` first)

**Running Tests:**
- Backend: `pytest tests/` from project root
- Frontend: `cd frontend && pnpm test:e2e` (requires dev server running)

## Important Implementation Details

**Backtest Engine Flow:**
1. Load candles from database for specified symbol/interval/time range
2. Convert to pandas DataFrame
3. Create Backtrader data feed
4. Initialize strategy with parameters
5. Attach TradeRecorder observer
6. Run backtest with cerebro
7. Extract metrics: final value, PnL, trade list
8. Save results to database (if job_id provided)

**Data Validation:**
- DataManager validates candle timestamps and intervals
- Detects gaps in time series data
- Checks for duplicate candles
- Rejects invalid data before storage

**Parameter Optimization:**
- Grid search over parameter space defined by strategy
- Parallel execution with configurable max workers
- Each combination runs independent backtest
- Results ranked by performance metric (e.g., Sharpe ratio)

**Error Handling:**
- Backend uses FastAPI exception handlers
- Returns structured error responses with details
- Logs all errors with stack traces
- Frontend displays user-friendly error messages

**Configuration Management:**
- Environment-specific config via `.env` file
- Pydantic validates and coerces types
- Database path auto-created if missing
- Default values for all settings

**Database Schema:**
- `symbols` - Trading pair metadata
- `candles` - OHLCV data indexed by symbol/interval/timestamp
- `backtest_jobs` - Backtest execution queue
- `backtest_results` - Performance metrics and metadata
- `trades` - Individual trade records linked to backtest results
- `optimization_jobs` / `optimization_results` - Parameter optimization tracking

## Common Development Patterns

**Adding a New Strategy:**
1. Create file in `backend/strategies/my_strategy.py`
2. Inherit from `StrategyBase`
3. Implement `__init__()`, `next()`, `get_parameters()`
4. Set class attributes: `strategy_name`, `strategy_version`, `strategy_description`
5. Strategy auto-discovered by `StrategyLoader`

**Adding a New API Endpoint:**
1. Create router in `backend/api/new_feature.py`
2. Define Pydantic models for request/response in `backend/models/`
3. Implement business logic in `backend/core/`
4. Register router in `backend/main.py`: `app.include_router(router, prefix="/api/v1")`
5. Add tests in `tests/test_new_feature_api.py`

**Frontend Component Pattern:**
1. Create component in `frontend/components/`
2. Use React Query for data fetching
3. Handle loading/error states
4. Use Tailwind for styling
5. Add to appropriate page in `frontend/app/`

## Environment Variables

Backend (`.env` in project root):
```
DATABASE_URL=sqlite:///data/quant.db
BINANCE_BASE_URL=https://api.binance.com
BINANCE_TIMEOUT=30
DEFAULT_INITIAL_CASH=100000.0
MAX_WORKERS=4
```

Frontend: No environment variables required (backend URL hardcoded to localhost:8000)

## Database Management

- SQLite database stored in `data/quant.db`
- Auto-created on first run
- To reset database: delete `data/quant.db` file
- Migrations not currently implemented (schema managed by SQLAlchemy models)

## Logging

- Backend logs to console and `logs/` directory
- Structured logging with timestamps and log levels
- Request logging middleware logs all HTTP requests
- Strategy execution logs within Backtrader framework

## Performance Considerations

- Backtest engine loads full candle dataset into memory
- Large date ranges may consume significant memory
- Parameter optimization parallelized but each worker needs memory
- Frontend pagination for large trade lists
- React Query caching reduces API calls
