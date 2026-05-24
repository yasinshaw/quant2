# Quantitative Trading Platform

A comprehensive quantitative trading platform for strategy development, backtesting, and parameter optimization.

## Tech Stack

- **Backend**: FastAPI + Backtrader + SQLite + Optuna (optional)
- **Frontend**: Next.js 14 + TypeScript + Tailwind CSS
- **Data Source**: Binance public API

## Features

### Core Features
- Historical data management
- Strategy development and testing
- Backtesting engine with comprehensive metrics
- Parameter optimization

### Advanced Optimization Features (New)
- **Bayesian Optimization**: Efficient parameter search using Optuna
- **Composite Scoring**: Multi-metric optimization with custom weights
- **Stability Analysis**: Detect overfitting through parameter variance analysis
- **Out-of-Sample Testing**: Validate parameter generalization on unseen data

## Project Structure

```
backend/
├── core/                    # Core business logic
│   ├── backtest_runner.py  # Shared backtest execution
│   ├── bayesian_optimizer.py  # Bayesian optimization (Optuna)
│   ├── stability_analyzer.py  # Parameter stability analysis
│   ├── scoring_functions.py  # Composite scoring
│   └── optimizer.py         # Grid search optimizer
├── models/                  # Data models
│   ├── optimization_job.py  # Extended with new fields
│   └── optimization_result.py  # Extended with composite score
├── api/                     # FastAPI endpoints
│   └── backtest.py          # Extended optimization endpoints
├── utils/                   # Utility functions
├── observers/               # Backtrader observers
└── strategies/              # Trading strategies

frontend/                  # Next.js frontend
├── components/
│   ├── OptimizationForm.tsx  # Extended with new options
│   └── OptimizationResults.tsx  # Extended with stability display
└── lib/api/
    └── optimization.ts      # Extended API types

data/                      # SQLite database storage

tests/                     # Test files
├── test_scoring_functions.py
├── test_bayesian_optimizer.py
├── test_stability_analyzer.py
├── test_optimization_api.py
└── test_optimization_integration.py

logs/                      # Application logs
```

## Getting Started

### Backend Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Optional: Install Optuna for Bayesian optimization
pip install optuna>=3.5.0
```

### Frontend Setup

```bash
cd frontend
pnpm install
pnpm dev
```

## Development

- Backend runs on `http://localhost:8000`
- Frontend runs on `http://localhost:3000`

## Usage

### Parameter Optimization Methods

#### 1. Grid Search (Default)
Traditional exhaustive search over parameter combinations:

```json
{
  "strategy_name": "MovingAverageCrossover",
  "symbol": "BTCUSDT",
  "interval": "1h",
  "start_time": "2024-01-01T00:00:00",
  "end_time": "2024-01-31T23:59:59",
  "parameter_ranges": {
    "fast_period": [10, 20, 30],
    "slow_period": [30, 40, 50]
  }
}
```

#### 2. Bayesian Optimization (Recommended)
Intelligent parameter search using Optuna:

```json
{
  "strategy_name": "MovingAverageCrossover",
  "symbol": "BTCUSDT",
  "interval": "1h",
  "start_time": "2024-01-01T00:00:00",
  "end_time": "2024-01-31T23:59:59",
  "optimization_method": "bayesian",
  "n_trials": 100,
  "parameter_ranges": {
    "fast_period": {"type": "int", "min": 5, "max": 50},
    "slow_period": {"type": "int", "min": 20, "max": 100}
  }
}
```

**Benefits**:
- More efficient than grid search
- Automatically learns from previous trials
- Better for high-dimensional parameter spaces

### Composite Scoring

Optimize using multiple metrics simultaneously:

```json
{
  "scoring_weights": {
    "sharpe_ratio": 0.4,
    "total_return": 0.3,
    "max_drawdown": -0.2,
    "win_rate": 0.1
  }
}
```

**Default weights**:
- Sharpe Ratio: 40%
- Total Return: 30%
- Max Drawdown: -20% (lower is better)
- Win Rate: 10%

### Stability Analysis

Automatically detect overfitting by testing parameter robustness:

```json
{
  "enable_stability_analysis": true
}
```

**What it does**:
- Tests parameter variations around optimal values
- Calculates stability score (0-1, higher is more stable)
- Identifies "parameter plateaus" vs isolated peaks
- Helps distinguish robust parameters from overfitted ones

**Stability Report**:
```json
{
  "stability_score": 0.85,
  "variance": 0.02,
  "is_stable": true,
  "neighbors": [
    {"parameters": {"fast_period": 19}, "score": 0.82},
    {"parameters": {"fast_period": 21}, "score": 0.83}
  ]
}
```

### Out-of-Sample Testing

Validate parameters on unseen data to detect overfitting:

```json
{
  "enable_out_of_sample": true,
  "test_start_time": "2024-02-01T00:00:00",
  "test_end_time": "2024-02-28T23:59:59"
}
```

**Benefits**:
- Detects overfitting to training period
- Validates parameter generalization
- Provides realistic performance expectations

## API Endpoints

### Optimization
- `POST /api/v1/backtest/optimize` - Run parameter optimization
- `GET /api/v1/backtest/optimization/jobs/{id}/results` - Get optimization results
- `GET /api/v1/backtest/optimization/jobs/{id}/stability` - Get stability report (NEW)
- `GET /api/v1/backtest/optimization/scoring-weights` - Get default scoring weights (NEW)

## Best Practices

1. **Use Bayesian optimization** for complex parameter spaces
2. **Enable stability analysis** to detect overfitting
3. **Use custom scoring weights** to match your investment objectives
4. **Always use out-of-sample testing** for validation
5. **Monitor stability scores** - aim for > 0.7

## Preventing Overfitting

Overfitting in parameter optimization occurs when parameters are tuned too closely to historical data. Use these techniques:

1. **Stability Analysis**: Check if small parameter changes cause large performance drops
2. **Out-of-Sample Testing**: Validate on data not used in optimization
3. **Walk-Forward Analysis**: Use rolling windows for time series
4. **Parameter Constraints**: Limit parameter ranges to sensible values
5. **Composite Scoring**: Don't optimize a single metric in isolation

## Testing

```bash
# Backend tests
pytest tests/ -v

# With coverage
pytest --cov=backend tests/

# Frontend tests
cd frontend && pnpm test:e2e
```

## License

MIT
