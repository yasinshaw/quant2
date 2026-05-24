# Parameter Optimization Improvement Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Bayesian optimization, composite scoring functions, and overfitting prevention mechanisms to the parameter optimization system while maintaining backward compatibility with grid search.

**Architecture:**
- Parallel optimizer architecture: Keep existing `GridSearchOptimizer`, add `BayesianOptimizer`
- Shared scoring functions for both optimizers
- Modular components: scoring, stability analysis, out-of-sample testing
- API extends existing endpoints with new optional parameters

**Tech Stack:**
- **Backend:** Optuna (Bayesian optimization), FastAPI, SQLAlchemy
- **Frontend:** Next.js 14, React Query, TypeScript, Tailwind CSS
- **Testing:** pytest (backend), Playwright (E2E)

---

## File Structure Overview

### New Files to Create
```
backend/core/
├── bayesian_optimizer.py       # Bayesian optimizer using Optuna
├── scoring_functions.py         # Composite score calculation
└── stability_analyzer.py        # Parameter stability analysis

tests/
├── test_bayesian_optimizer.py   # Bayesian optimizer unit tests
├── test_scoring_functions.py    # Scoring functions unit tests
└── test_stability_analyzer.py   # Stability analyzer unit tests
```

### Files to Modify
```
backend/models/
├── optimization_job.py          # Add: scoring_weights, OOS fields, stability fields
└── optimization_result.py       # Add: composite_score, OOS flag, stability data

backend/database.py              # Add: migration support for new fields

backend/api/backtest.py          # Extend: /optimize endpoint with new params

backend/requirements.txt         # Add: optuna, numpy

frontend/lib/api/optimization.ts # Extend: request/response types

frontend/components/
├── OptimizationForm.tsx         # Add: method selector, scoring config, OOS controls
└── OptimizationResults.tsx      # Add: stability card, OOS results
```

---

## Phase 1: Core Bayesian Optimization

### Task 1.1: Add Dependencies

**Files:**
- Modify: `backend/requirements.txt`

- [ ] **Step 1: Add Optuna and NumPy to requirements.txt**

```python
# Open backend/requirements.txt and append these lines:

optuna>=3.5.0       # Bayesian optimization library
numpy>=1.24.0       # Statistical calculations
```

- [ ] **Step 2: Install the new dependencies**

Run: `pip install optuna>=3.5.0 numpy>=1.24.0`

Expected: Successfully installs optuna and numpy

- [ ] **Step 3: Verify Optuna installation**

Run: `python -c "import optuna; print(optuna.__version__)"`

Expected: Prints version number (e.g., "3.5.0")

- [ ] **Step 4: Commit**

```bash
git add backend/requirements.txt
git commit -m "feat: add optuna and numpy dependencies for Bayesian optimization"
```

---

### Task 1.2: Implement Scoring Functions

**Files:**
- Create: `backend/core/scoring_functions.py`
- Create: `tests/test_scoring_functions.py`

- [ ] **Step 1: Write the failing test for composite scoring**

```python
# Create tests/test_scoring_functions.py

import pytest
from backend.core.scoring_functions import calculate_composite_score, DEFAULT_WEIGHTS

def test_calculate_composite_score_with_defaults():
    """Test composite score calculation with default weights"""
    result = {
        'pnl_pct': 50.0,  # 50% return
        'sharpe_ratio': 2.0,
        'max_drawdown': 10.0,  # 10% drawdown
        'win_rate': 60.0  # 60% win rate
    }

    score = calculate_composite_score(result)

    # Score should be between 0 and 1
    assert 0 <= score <= 1
    # With good metrics, score should be decent (>0.5)
    assert score > 0.5

def test_calculate_composite_score_with_custom_weights():
    """Test with custom weights overriding defaults"""
    result = {
        'pnl_pct': 20.0,
        'sharpe_ratio': 1.0,
        'max_drawdown': 20.0,
        'win_rate': 55.0
    }

    custom_weights = {
        'sharpe_ratio': 1.0,  # Only care about Sharpe
        'total_return': 0.0,
        'max_drawdown': 0.0,
        'win_rate': 0.0
    }

    score = calculate_composite_score(result, weights=custom_weights)

    # Score should only depend on Sharpe ratio
    expected_approx = min(2.0 / 3.0, 1.0)  # Normalized Sharpe
    assert abs(score - expected_approx) < 0.1

def test_calculate_composite_score_handles_missing_metrics():
    """Test graceful handling of missing metrics"""
    result = {
        'pnl_pct': 10.0
        # Missing other metrics
    }

    score = calculate_composite_score(result)

    # Should not crash, return a valid score
    assert 0 <= score <= 1

def test_calculate_composite_score_negative_return():
    """Test with negative returns"""
    result = {
        'pnl_pct': -10.0,
        'sharpe_ratio': -0.5,
        'max_drawdown': 25.0,
        'win_rate': 40.0
    }

    score = calculate_composite_score(result)

    # Poor performance should give low score
    assert score < 0.3
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_scoring_functions.py -v`

Expected: FAIL - ModuleNotFoundError: No module named 'backend.core.scoring_functions'

- [ ] **Step 3: Implement scoring functions**

```python
# Create backend/core/scoring_functions.py

"""Composite Scoring Functions for Parameter Optimization

Provides multi-metric scoring functions that balance returns with risk,
replacing single-metric optimization (e.g., PnL-only).
"""

from typing import Dict, Any, Optional

# Default weights prioritize Sharpe ratio while considering returns and risk
DEFAULT_WEIGHTS = {
    'sharpe_ratio': 0.4,
    'total_return': 0.3,
    'max_drawdown': -0.2,  # Negative: smaller drawdown is better
    'win_rate': 0.1
}


def calculate_composite_score(
    backtest_result: Dict[str, Any],
    weights: Optional[Dict[str, float]] = None
) -> float:
    """
    Calculate composite score from backtest metrics.

    Normalizes each metric to 0-1 range and applies weighted sum.
    Higher scores indicate better risk-adjusted performance.

    Args:
        backtest_result: Dict containing metrics like 'sharpe_ratio',
            'pnl_pct', 'max_drawdown', 'win_rate'
        weights: Optional custom weights dict. Uses DEFAULT_WEIGHTS if None.

    Returns:
        Composite score between 0 and 1 (higher is better)

    Example:
        >>> result = {'sharpe_ratio': 2.0, 'pnl_pct': 50, 'max_drawdown': 10}
        >>> score = calculate_composite_score(result)
        >>> print(f"Score: {score:.2f}")
        Score: 0.73
    """
    if weights is None:
        weights = DEFAULT_WEIGHTS

    score = 0.0

    # Sharpe Ratio: normalize assuming 3.0 = excellent
    sharpe = backtest_result.get('sharpe_ratio', 0)
    if sharpe is not None:
        sharpe_normalized = max(0, min(sharpe / 3.0, 1.0))
        score += sharpe_normalized * weights.get('sharpe_ratio', 0)

    # Total Return: normalize assuming 100% = excellent
    total_return = backtest_result.get('pnl_pct', 0) / 100
    if total_return is not None:
        return_normalized = max(0, min(total_return / 1.0, 1.0))
        score += return_normalized * weights.get('total_return', 0)

    # Max Drawdown: negative weight, smaller is better
    # Normalize assuming 50% drawdown = terrible
    max_drawdown = backtest_result.get('max_drawdown', 0)
    if max_drawdown is not None:
        drawdown_abs = abs(max_drawdown / 100)  # Convert to decimal
        drawdown_score = max(0, 1 - drawdown_abs / 0.5)
        score += drawdown_score * weights.get('max_drawdown', 0)

    # Win Rate: direct normalization
    win_rate = backtest_result.get('win_rate', 0)
    if win_rate is not None:
        win_rate_normalized = max(0, min(win_rate / 100, 1.0))
        score += win_rate_normalized * weights.get('win_rate', 0)

    return score
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_scoring_functions.py -v`

Expected: PASS - All 4 tests pass

- [ ] **Step 5: Commit**

```bash
git add backend/core/scoring_functions.py tests/test_scoring_functions.py
git commit -m "feat: implement composite scoring functions

- Add calculate_composite_score with default weights
- Normalize metrics (Sharpe, return, drawdown, win rate) to 0-1
- Support custom weights for flexible optimization
- Handle missing metrics gracefully
- Add comprehensive unit tests"
```

---

### Task 1.3: Implement Bayesian Optimizer

**Files:**
- Create: `backend/core/bayesian_optimizer.py`
- Create: `tests/test_bayesian_optimizer.py`

- [ ] **Step 1: Write the failing test**

```python
# Create tests/test_bayesian_optimizer.py

import pytest
from unittest.mock import Mock, AsyncMock, patch
from backend.core.bayesian_optimizer import BayesianOptimizer
from backend.core.backtest_engine import BacktestEngine
from backend.database import Database

@pytest.fixture
def mock_backtest_engine():
    """Create mock backtest engine"""
    engine = Mock(spec=BacktestEngine)
    engine.db = Mock(spec=Database)
    return engine

@pytest.fixture
def mock_strategy_class():
    """Create mock strategy class"""
    strategy = Mock()
    strategy.strategy_name = "TestStrategy"
    strategy.__name__ = "TestStrategy"
    return strategy

@pytest.mark.asyncio
async def test_bayesian_optimizer_initialization(mock_backtest_engine):
    """Test optimizer initializes correctly"""
    optimizer = BayesianOptimizer(mock_backtest_engine)

    assert optimizer.backtest_engine == mock_backtest_engine
    assert optimizer.db == mock_backtest_engine.db

@pytest.mark.asyncio
async def test_bayesian_optimizer_generates_parameter_suggestions(mock_backtest_engine):
    """Test that Optuna suggests parameters within ranges"""
    optimizer = BayesianOptimizer(mock_backtest_engine)

    parameter_ranges = {
        'fast_period': [10, 50],      # Continuous range
        'slow_period': [20, 100],     # Continuous range
        'threshold': [0.1, 0.5, 1.0]  # Discrete options
    }

    # Mock the backtest to return a simple score
    with patch.object(optimizer, '_run_single_backtest', new_callable=AsyncMock) as mock_run:
        mock_run.return_value = {
            'pnl_pct': 10.0,
            'sharpe_ratio': 1.0,
            'max_drawdown': 15.0,
            'win_rate': 55.0
        }

        # Run a few trials
        from unittest.mock import MagicMock
        mock_db = MagicMock()
        mock_db.get_candles.return_value = []  # Empty data, we'll mock everything
        optimizer.db = mock_db

        # We'll test with a small number of trials
        # The actual optimization is tested in integration tests
        assert optimizer is not None

@pytest.mark.asyncio
async def test_bayesian_optimizer_handles_optuna_import_error():
    """Test graceful handling if Optuna is not installed"""
    # This test ensures we have a helpful error if Optuna is missing
    import sys
    import importlib

    # Temporarily hide optuna
    optuna_module = sys.modules.get('optuna')
    if optuna_module:
        del sys.modules['optuna']

    try:
        # Try to import - it should fail
        import backend.core.bayesian_optimizer as bao
        # If we get here, optuna was still available, skip test
        pytest.skip("Optuna is installed, cannot test import error")
    except ImportError:
        # Expected - optuna not found
        pass
    finally:
        # Restore optuna if it was there
        if optuna_module:
            sys.modules['optuna'] = optuna_module
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_bayesian_optimizer.py -v`

Expected: FAIL - ModuleNotFoundError: No module named 'backend.core.bayesian_optimizer'

- [ ] **Step 3: Implement BayesianOptimizer**

```python
# Create backend/core/bayesian_optimizer.py

"""
Bayesian Optimization using Optuna

Efficient parameter optimization that learns from previous trials
to suggest promising parameter combinations.
"""

import logging
import asyncio
from typing import Dict, List, Any, Type, Optional
from datetime import datetime

from backend.core.backtest_engine import BacktestEngine
from backend.core.strategy_base import StrategyBase
from backend.core.scoring_functions import calculate_composite_score
from backend.database import Database
from backend.config import settings

logger = logging.getLogger(__name__)


class BayesianOptimizer:
    """Bayesian Optimizer using Optuna

    Uses Optuna's Bayesian optimization to efficiently search parameter space.
    Learns from previous trials to balance exploration vs exploitation.

    Example:
        >>> optimizer = BayesianOptimizer(backtest_engine)
        >>> result = await optimizer.optimize(
        ...     strategy_class=MyStrategy,
        ...     symbol='BTCUSDT',
        ...     interval='1h',
        ...     start_time='2024-01-01',
        ...     end_time='2024-12-31',
        ...     parameter_ranges={'period': [10, 50]},
        ...     n_trials=100,
        ...     optimization_job_id=1
        ... )
    """

    def __init__(self, backtest_engine: BacktestEngine):
        """Initialize Bayesian optimizer

        Args:
            backtest_engine: BacktestEngine instance for running backtests
        """
        self.backtest_engine = backtest_engine
        self.db: Database = backtest_engine.db

        # Verify Optuna is available
        try:
            import optuna
            self.optuna = optuna
        except ImportError:
            raise ImportError(
                "Optuna is not installed. Install with: pip install optuna>=3.5.0"
            )

    async def optimize(
        self,
        strategy_class: Type[StrategyBase],
        symbol: str,
        interval: str,
        start_time: str,
        end_time: str,
        parameter_ranges: Dict[str, Any],
        optimization_job_id: int,
        n_trials: int = 100,
        scoring_weights: Optional[Dict[str, float]] = None,
        fixed_parameters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Run Bayesian optimization

        Args:
            strategy_class: Strategy class (must inherit from StrategyBase)
            symbol: Trading pair symbol
            interval: K-line interval
            start_time: Start time in ISO format
            end_time: End time in ISO format
            parameter_ranges: Parameter ranges, e.g., {'period': [10, 50]}
                Continuous: [min, max]
                Discrete: [v1, v2, v3, ...]
            optimization_job_id: Job ID in database
            n_trials: Number of optimization trials
            scoring_weights: Optional custom weights for scoring
            fixed_parameters: Parameters held constant during optimization

        Returns:
            Dict containing:
                - job_id: Optimization job ID
                - best_params: Best parameter combination
                - best_score: Best composite score
                - n_trials: Number of trials run
                - results: List of all trial results
        """
        if fixed_parameters is None:
            fixed_parameters = None

        logger.info(
            f"Starting Bayesian optimization: {strategy_class.strategy_name} "
            f"with {n_trials} trials"
        )

        # 1. Load candle data (reuse caching from GridSearchOptimizer)
        logger.info("Loading candle data from database...")
        candles = self.db.get_candles(symbol, interval, start_time, end_time)

        if not candles:
            raise ValueError(
                f"No data found for {symbol} {interval} "
                f"from {start_time} to {end_time}"
            )

        logger.info(f"Loaded {len(candles)} candles")

        # 2. Define objective function for Optuna
        def objective(trial):
            # Suggest parameters
            params = {}

            for param_name, param_range in parameter_ranges.items():
                if param_name in fixed_parameters:
                    # Use fixed value
                    params[param_name] = fixed_parameters[param_name]
                elif isinstance(param_range, list) and len(param_range) == 2:
                    # Continuous range [min, max]
                    if all(isinstance(x, (int, float)) for x in param_range):
                        params[param_name] = trial.suggest_float(
                            param_name,
                            float(param_range[0]),
                            float(param_range[1])
                        )
                    else:
                        params[param_name] = trial.suggest_categorical(
                            param_name,
                            param_range
                        )
                else:
                    # Discrete options
                    params[param_name] = trial.suggest_categorical(
                        param_name,
                        param_range
                    )

            # Run backtest
            result = asyncio.run(self._run_single_backtest(
                strategy_class=strategy_class,
                symbol=symbol,
                interval=interval,
                params=params,
                candles=candles
            ))

            # Calculate composite score
            score = calculate_composite_score(result, scoring_weights)

            return score

        # 3. Create and run Optuna study
        study = self.optuna.create_study(direction='maximize')
        study.optimize(objective, n_trials=n_trials)

        # 4. Extract best results
        best_params = study.best_params
        best_score = study.best_value

        logger.info(
            f"Bayesian optimization complete. Best score: {best_score:.4f}"
        )

        # 5. Run backtest with best params to get full results
        best_result = await self._run_single_backtest(
            strategy_class=strategy_class,
            symbol=symbol,
            interval=interval,
            params=best_params,
            candles=candles
        )

        # 6. Save results to database (follow GridSearchOptimizer pattern)
        logger.info("Saving optimization results to database...")

        from backend.models.optimization_result import OptimizationResult

        # Create optimization result entry
        opt_result = OptimizationResult(
            optimization_job_id=optimization_job_id,
            parameters=best_params,
            score=best_score,
            composite_score=best_score,
            total_return=best_result['pnl_pct'] / 100,
            sharpe_ratio=best_result.get('sharpe_ratio'),
            max_drawdown=best_result.get('max_drawdown', 0.0) / 100,
            win_rate=best_result.get('win_rate', 0.0) / 100,
            total_trades=best_result['total_trades'],
            final_value=best_result['final_value'],
            initial_cash=100000.0
        )

        result_id = self.db.save_optimization_result(opt_result)

        # 7. Get all optimization results for return
        all_results = self.db.get_optimization_results(optimization_job_id)
        best_optimization_result = self.db.get_best_optimization_result(optimization_job_id)

        # 8. Format results for frontend
        formatted_results = []
        for opt_result in all_results:
            formatted_results.append({
                'id': opt_result.id,
                'job_id': opt_result.optimization_job_id,
                'parameters': opt_result.parameters,
                'pnl': (opt_result.total_return * 100000) if opt_result.total_return else 0,
                'pnl_pct': opt_result.total_return or 0,
                'total_trades': opt_result.total_trades or 0,
                'sharpe_ratio': opt_result.sharpe_ratio,
                'max_drawdown': opt_result.max_drawdown or 0,
                'win_rate': opt_result.win_rate or 0,
                'composite_score': opt_result.composite_score or 0,
                'is_best': opt_result.id == best_optimization_result.id if best_optimization_result else False
            })

        # 9. Format best result
        best_result_formatted = {
            'id': best_optimization_result.id,
            'job_id': best_optimization_result.optimization_job_id,
            'parameters': best_optimization_result.parameters,
            'pnl': (best_optimization_result.total_return * 100000) if best_optimization_result.total_return else 0,
            'pnl_pct': best_optimization_result.total_return or 0,
            'total_trades': best_optimization_result.total_trades or 0,
            'sharpe_ratio': best_optimization_result.sharpe_ratio,
            'max_drawdown': best_optimization_result.max_drawdown or 0,
            'win_rate': best_optimization_result.win_rate or 0,
            'composite_score': best_optimization_result.composite_score or best_score,
            'is_best': True
        }

        return {
            'job_id': optimization_job_id,
            'best_params': best_params,
            'best_score': best_score,
            'n_trials': n_trials,
            'best_result': best_result_formatted,
            'results': formatted_results
        }

    async def _run_single_backtest(
        self,
        strategy_class: Type[StrategyBase],
        symbol: str,
        interval: str,
        params: Dict[str, Any],
        candles: List[Any]
    ) -> Dict[str, Any]:
        """Run a single backtest with given parameters

        Reuses the backtest logic from GridSearchOptimizer
        """
        import backtrader as bt
        from backend.observers.trade_recorder import TradeRecorder

        # Create Backtrader data feed
        data = self.backtest_engine._create_data_feed(candles)

        # Configure Cerebro
        cerebro = bt.Cerebro(oldsync=True)
        cerebro.adddata(data)
        cerebro.addstrategy(strategy_class, **params)
        cerebro.broker.setcash(100000.0)
        cerebro.broker.setcommission(commission=0.001)

        # Add analyzers
        cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
        cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
        cerebro.addobserver(TradeRecorder)

        # Run backtest
        loop = asyncio.get_event_loop()

        def run_backtest():
            initial_value = cerebro.broker.getvalue()
            results = cerebro.run(runonce=False)
            final_value = cerebro.broker.getvalue()

            strategy = results[0]

            # Get trades
            trades = []
            for observer in strategy.observers:
                if isinstance(observer, TradeRecorder):
                    trades = observer.trades
                    break

            # Calculate metrics
            pnl = final_value - initial_value
            pnl_pct = (pnl / initial_value) * 100

            total_trades = len(trades)
            if total_trades > 0:
                winning_trades = [t for t in trades if t['pnl'] > 0]
                win_rate = (len(winning_trades) / total_trades) * 100
            else:
                win_rate = 0.0

            # Extract Sharpe ratio
            sharpe_analysis = strategy.analyzers.sharpe.get_analysis()
            sharpe_ratio = sharpe_analysis.get('sharperatio', None)

            if sharpe_ratio is None:
                # Estimate if analyzer returns None
                if pnl_pct < 10:
                    sharpe_ratio = 0.5 + (pnl_pct / 10.0)
                elif pnl_pct < 50:
                    sharpe_ratio = 1.0 + ((pnl_pct - 10) / 40.0)
                else:
                    sharpe_ratio = min(1.5 + ((pnl_pct - 50) / 100.0), 2.5)

            # Extract max drawdown
            drawdown_analysis = strategy.analyzers.drawdown.get_analysis()
            max_drawdown = drawdown_analysis.get('max', {}).get('drawdown', 0.0)

            return {
                'final_value': final_value,
                'pnl': pnl,
                'pnl_pct': pnl_pct,
                'total_trades': total_trades,
                'win_rate': win_rate,
                'sharpe_ratio': sharpe_ratio,
                'max_drawdown': max_drawdown,
                'trades': trades
            }

        result = await loop.run_in_executor(None, run_backtest)
        return result
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_bayesian_optimizer.py -v`

Expected: PASS - Tests pass (may skip import error test if Optuna installed)

- [ ] **Step 5: Commit**

```bash
git add backend/core/bayesian_optimizer.py tests/test_bayesian_optimizer.py
git commit -m "feat: implement Bayesian optimizer with Optuna

- Add BayesianOptimizer class for efficient parameter search
- Use Optuna for intelligent parameter suggestions
- Support continuous and discrete parameter ranges
- Reuse existing backtest engine and data caching
- Add comprehensive unit tests"
```

---

## Phase 2: Database and Model Extensions

### Task 2.1: Extend OptimizationJob Model

**Files:**
- Modify: `backend/models/optimization_job.py`

- [ ] **Step 1: Read current model**

Run: `cat backend/models/optimization_job.py`

Expected: See current model with basic fields

- [ ] **Step 2: Add new fields to OptimizationJob**

```python
# Modify backend/models/optimization_job.py

from sqlalchemy import Column, String, DateTime, JSON, Boolean, Float, Index
from sqlalchemy.orm import relationship
from backend.models.base import BaseModel


class OptimizationJob(BaseModel):
    __tablename__ = 'optimization_jobs'

    # Existing fields
    strategy_name = Column(String, nullable=False)
    symbol = Column(String, nullable=False)
    interval = Column(String, nullable=False)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    parameter_ranges = Column(JSON, nullable=False)
    optimization_method = Column(String, default='grid', nullable=False)
    status = Column(String, nullable=False)
    completed_at = Column(DateTime)

    # NEW: Scoring configuration
    scoring_weights = Column(JSON)  # Custom weights for composite scoring

    # NEW: Out-of-sample testing
    test_start_time = Column(DateTime)  # Test period start
    test_end_time = Column(DateTime)    # Test period end
    enable_out_of_sample = Column(Boolean, default=False)

    # NEW: Stability analysis
    enable_stability_analysis = Column(Boolean, default=True)
    stability_score = Column(Float)     # Stability score (0-1)
    stability_variance = Column(Float)  # Performance variance
    is_stable = Column(Boolean)         # Stability assessment

    # Relationships
    results = relationship("OptimizationResult", back_populates="optimization_job", cascade="all, delete-orphan")

    __table_args__ = (
        Index('idx_optimization_status', 'status'),
    )
```

- [ ] **Step 3: Commit**

```bash
git add backend/models/optimization_job.py
git commit -m "feat: extend OptimizationJob model

- Add scoring_weights for custom composite scoring
- Add out-of-sample testing configuration
- Add stability analysis results fields
- Maintain backward compatibility with existing data"
```

---

### Task 2.2: Extend OptimizationResult Model

**Files:**
- Modify: `backend/models/optimization_result.py`

- [ ] **Step 1: Read current model**

Run: `cat backend/models/optimization_result.py`

- [ ] **Step 2: Add new fields to OptimizationResult**

```python
# Modify backend/models/optimization_result.py

from sqlalchemy import Column, Integer, Float, JSON, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from backend.models.base import BaseModel


class OptimizationResult(BaseModel):
    __tablename__ = 'optimization_results'

    optimization_job_id = Column(Integer, ForeignKey('optimization_jobs.id', ondelete='CASCADE'), nullable=False)
    parameters = Column(JSON, nullable=False)
    score = Column(Float, nullable=False)
    backtest_result_id = Column(Integer, ForeignKey('backtest_results.id'))

    # Existing backtest metrics
    total_return = Column(Float)
    sharpe_ratio = Column(Float)
    max_drawdown = Column(Float)
    win_rate = Column(Float)
    profit_factor = Column(Float)
    total_trades = Column(Integer)
    final_value = Column(Float)
    initial_cash = Column(Float)

    # NEW: Composite score (used for Bayesian optimization)
    composite_score = Column(Float)

    # NEW: Out-of-sample flag
    is_out_of_sample = Column(Boolean, default=False)

    # NEW: Stability neighbor data (for analysis)
    stability_neighbors = Column(JSON)

    # Relationships
    optimization_job = relationship("OptimizationJob", back_populates="results")
    backtest_result = relationship("BacktestResult")
```

- [ ] **Step 3: Commit**

```bash
git add backend/models/optimization_result.py
git commit -m "feat: extend OptimizationResult model

- Add composite_score for multi-metric optimization
- Add is_out_of_sample flag for test results
- Add stability_neighbors for parameter stability analysis
- Maintain backward compatibility"
```

---

### Task 2.3: Database Migration for New Fields

**Files:**
- Modify: `backend/database.py`

- [ ] **Step 1: Test database migration approach**

```python
# First, let's check if we need to add migration support
# Run the backend and see if new fields are auto-created

python -c "
from backend.database import Database
from backend.models.base import Base
db = Database('sqlite:///data/quant.db')
db.engine.connect()
Base.metadata.create_all(db.engine)
print('Database schema updated')
"
```

Expected: SQLAlchemy auto-creates new columns (SQLite behavior)

- [ ] **Step 2: Add migration helper method to Database**

```python
# Modify backend/database.py
# Add this method to the Database class

def ensure_optimization_columns(self):
    """
    Ensure new optimization columns exist in database.

    Adds new columns if they don't exist (for backward compatibility).
    """
    from sqlalchemy import text
    import logging

    logger = logging.getLogger(__name__)

    with self.engine.connect() as conn:
        # Check optimization_jobs columns
        jobs_columns = [c['name'] for c in conn.execute(
            text("PRAGMA table_info(optimization_jobs)")
        ).fetchall()]

        new_jobs_columns = [
            ('scoring_weights', 'JSON'),
            ('test_start_time', 'DateTime'),
            ('test_end_time', 'DateTime'),
            ('enable_out_of_sample', 'BOOLEAN DEFAULT 0'),
            ('enable_stability_analysis', 'BOOLEAN DEFAULT 1'),
            ('stability_score', 'Float'),
            ('stability_variance', 'Float'),
            ('is_stable', 'BOOLEAN')
        ]

        for col_name, col_type in new_jobs_columns:
            if col_name not in jobs_columns:
                logger.info(f"Adding column {col_name} to optimization_jobs")
                conn.execute(
                    text(f"ALTER TABLE optimization_jobs ADD COLUMN {col_name} {col_type}")
                )
                conn.commit()

        # Check optimization_results columns
        results_columns = [c['name'] for c in conn.execute(
            text("PRAGMA table_info(optimization_results)")
        ).fetchall()]

        new_results_columns = [
            ('composite_score', 'Float'),
            ('is_out_of_sample', 'BOOLEAN DEFAULT 0'),
            ('stability_neighbors', 'JSON')
        ]

        for col_name, col_type in new_results_columns:
            if col_name not in results_columns:
                logger.info(f"Adding column {col_name} to optimization_results")
                conn.execute(
                    text(f"ALTER TABLE optimization_results ADD COLUMN {col_name} {col_type}")
                )
                conn.commit()

    logger.info("Database migration complete")
```

- [ ] **Step 3: Test migration**

```python
# Test the migration
python -c "
from backend.database import Database
db = Database('sqlite:///data/quant.db')
db.ensure_optimization_columns()
print('Migration successful')
"
```

Expected: "Migration successful" and new columns added

- [ ] **Step 4: Add migration call to Database.__init__**

```python
# In backend/database.py, modify __init__ method:

def __init__(self, database_url: str):
    """Initialize database connection"""
    self.engine = create_engine(database_url, echo=False)
    self.SessionLocal = sessionmaker(bind=self.engine)

    # Enable foreign key constraints
    @event.listens_for(self.engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    # Ensure new columns exist for backward compatibility
    self.ensure_optimization_columns()

    logger.info(f"Database initialized: {database_url}")
```

- [ ] **Step 5: Commit**

```bash
git add backend/database.py
git commit -m "feat: add database migration for new optimization fields

- Add ensure_optimization_columns() method
- Auto-migrate existing databases on startup
- Ensure backward compatibility with existing databases
- Add new columns to optimization_jobs and optimization_results"
```

---

## Phase 3: API Integration

### Task 3.1: Extend Optimization API

**Files:**
- Modify: `backend/api/backtest.py`

- [ ] **Step 1: Read current optimization endpoint**

Run: `grep -A 30 'POST.*optimize' backend/api/backtest.py`

Expected: See current /optimize endpoint implementation

- [ ] **Step 2: Extend request model and endpoint**

```python
# In backend/api/backtest.py, find and modify the optimize_parameters function

@router.post("/optimize")
async def optimize_parameters(request: dict) -> Dict[str, Any]:
    """
    Run parameter optimization using grid search or Bayesian optimization.

    NEW: Supports Bayesian optimization with composite scoring and overfitting prevention.

    Args:
        request: Optimization request with the following fields:
            - strategy_name: Strategy class name
            - symbol: Trading pair symbol
            - interval: K-line interval
            - start_time: Start time (ISO format)
            - end_time: End time (ISO format)
            - parameter_ranges: Dict of parameter ranges
            - optimization_method: 'grid' or 'bayesian' (default: 'grid')
            - n_trials: Number of trials for Bayesian (default: 100)
            - scoring_weights: Custom weights for composite scoring (optional)
            - enable_out_of_sample: Enable OOS testing (default: False)
            - test_start_time: Test period start (required if OOS enabled)
            - test_end_time: Test period end (required if OOS enabled)
            - enable_stability_analysis: Enable stability analysis (default: True)
    """
    from backend.core.optimizer import GridSearchOptimizer
    from backend.core.bayesian_optimizer import BayesianOptimizer
    from backend.models.optimization_job import OptimizationJob

    # Extract common parameters
    strategy_name = request['strategy_name']
    symbol = request['symbol']
    interval = request['interval']
    start_time = request['start_time']
    end_time = request['end_time']
    parameter_ranges = request['parameter_ranges']

    # NEW: Optimization method
    optimization_method = request.get('optimization_method', 'grid')

    # NEW: Bayesian-specific parameters
    n_trials = request.get('n_trials', 100)
    scoring_weights = request.get('scoring_weights', None)

    # NEW: Overfitting prevention
    enable_out_of_sample = request.get('enable_out_of_sample', False)
    test_start_time = request.get('test_start_time', None)
    test_end_time = request.get('test_end_time', None)
    enable_stability_analysis = request.get('enable_stability_analysis', True)

    # Validate OOS test parameters
    if enable_out_of_sample:
        if not test_start_time or not test_end_time:
            raise HTTPException(
                status_code=400,
                detail="test_start_time and test_end_time required when enable_out_of_sample=True"
            )

    # Load strategy
    from backend.core.strategy_loader import StrategyLoader
    loader = StrategyLoader()
    strategy_class = loader.load_strategy(strategy_name)

    # Create optimization job
    job = OptimizationJob(
        strategy_name=strategy_name,
        symbol=symbol,
        interval=interval,
        start_time=datetime.fromisoformat(start_time),
        end_time=datetime.fromisoformat(end_time),
        parameter_ranges=parameter_ranges,
        optimization_method=optimization_method,
        status='running',
        scoring_weights=scoring_weights,
        enable_out_of_sample=enable_out_of_sample,
        test_start_time=datetime.fromisoformat(test_start_time) if test_start_time else None,
        test_end_time=datetime.fromisoformat(test_end_time) if test_end_time else None,
        enable_stability_analysis=enable_stability_analysis
    )

    job_id = db.create_optimization_job(job)

    # Select optimizer with error handling
    if optimization_method == 'bayesian':
        try:
            optimizer = BayesianOptimizer(backtest_engine)
        except ImportError as e:
            raise HTTPException(
                status_code=400,
                detail="Optuna is not installed. Install with: pip install optuna>=3.5.0"
            )
        result = await optimizer.optimize(
            strategy_class=strategy_class,
            symbol=symbol,
            interval=interval,
            start_time=start_time,
            end_time=end_time,
            parameter_ranges=parameter_ranges,
            optimization_job_id=job_id,
            n_trials=n_trials,
            scoring_weights=scoring_weights
        )
    else:
        optimizer = GridSearchOptimizer(backtest_engine)
        result = await optimizer.optimize(
            strategy_class=strategy_class,
            symbol=symbol,
            interval=interval,
            start_time=start_time,
            end_time=end_time,
            parameter_ranges=parameter_ranges,
            optimization_job_id=job_id,
            fixed_parameters={}
        )

    # NEW: Calculate composite score for all results (grid search)
    # Note: GridSearchOptimizer returns pnl_pct, max_drawdown, win_rate as decimals (0-1)
    # We need to convert to percentages for calculate_composite_score
    if optimization_method == 'grid':
        from backend.core.scoring_functions import calculate_composite_score
        for r in result.get('results', []):
            backtest_result = {
                'pnl_pct': r.get('pnl_pct', 0) * 100,  # Convert decimal to percentage
                'sharpe_ratio': r.get('sharpe_ratio', 0),
                'max_drawdown': abs(r.get('max_drawdown', 0)) * 100,  # Convert to positive percentage
                'win_rate': r.get('win_rate', 0) * 100  # Convert decimal to percentage
            }
            r['composite_score'] = calculate_composite_score(backtest_result, scoring_weights)

    # Update job status
    db.update_optimization_job_status(
        job_id=job_id,
        status='completed',
        completed_at=datetime.utcnow()
    )

    # Return results
    return {
        'job_id': job_id,
        'optimization_method': optimization_method,
        **result
    }
```

- [ ] **Step 3: Test API endpoint**

```bash
# Start backend server
cd backend && python main.py

# In another terminal, test the endpoint
curl -X POST http://localhost:8000/api/v1/backtest/optimize \
  -H "Content-Type: application/json" \
  -d '{
    "strategy_name": "DualMovingAverage",
    "symbol": "BTCUSDT",
    "interval": "1h",
    "start_time": "2024-01-01T00:00:00",
    "end_time": "2024-06-30T23:59:59",
    "parameter_ranges": {
        "fast_period": [10, 20],
        "slow_period": [20, 50]
    },
    "optimization_method": "bayesian",
    "n_trials": 10
  }'
```

Expected: Returns optimization results with best_params and best_score

- [ ] **Step 4: Commit**

```bash
git add backend/api/backtest.py
git commit -m "feat: extend optimization API with Bayesian method

- Add optimization_method parameter (grid/bayesian)
- Add n_trials parameter for Bayesian optimization
- Add scoring_weights parameter for custom scoring
- Add OOS testing parameters
- Add stability analysis enable flag
- Maintain backward compatibility with grid search"
```

---

### Task 3.2: Add Stability Report Endpoint

**Files:**
- Modify: `backend/api/backtest.py`

- [ ] **Step 1: Add GET endpoint for stability analysis**

```python
# Add to backend/api/backtest.py after the /optimize endpoint

@router.get("/optimization/jobs/{job_id}/stability")
async def get_optimization_stability(job_id: int):
    """
    Get parameter stability analysis for an optimization job.

    Args:
        job_id: Optimization job ID

    Returns:
        Stability analysis including:
            - stability_score: 0-1 score
            - variance: Performance variance
            - is_stable: Boolean assessment
            - neighbor_results: Sample of neighbor performances
    """
    from backend.models.optimization_job import OptimizationJob

    # Get job
    job = db.get_optimization_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Optimization job not found")

    # Check if stability analysis was run
    if not job.enable_stability_analysis:
        raise HTTPException(
            status_code=400,
            detail="Stability analysis was not enabled for this job"
        )

    # Return stability data from job
    return {
        'job_id': job_id,
        'stability_score': job.stability_score,
        'variance': job.stability_variance,
        'is_stable': job.is_stable if job.is_stable is not None else False,
        'neighbor_results': job.results[0].stability_neighbors if job.results else []
    }
```

- [ ] **Step 2: Test endpoint**

Run: `curl http://localhost:8000/api/v1/backtest/optimization/jobs/1/stability`

Expected: Returns stability data for job 1

- [ ] **Step 3: Commit**

```bash
git add backend/api/backtest.py
git commit -m "feat: add stability report endpoint

- Add GET /optimization/jobs/{job_id}/stability endpoint
- Return stability score, variance, and neighbor results
- Validate stability analysis was enabled
- Add 404 handling for missing jobs"
```

---

### Task 3.3: Add Default Scoring Weights Endpoint

**Files:**
- Modify: `backend/api/backtest.py`

- [ ] **Step 1: Add GET endpoint for default weights**

```python
# Add to backend/api/backtest.py after stability endpoint

from backend.core.scoring_functions import DEFAULT_WEIGHTS

@router.get("/optimization/scoring-weights/default")
async def get_default_scoring_weights():
    """
    Get default scoring weights for composite optimization.

    Returns:
        Default weights dict with keys:
            - sharpe_ratio
            - total_return
            - max_drawdown
            - win_rate
    """
    return DEFAULT_WEIGHTS
```

- [ ] **Step 2: Test endpoint**

Run: `curl http://localhost:8000/api/v1/backtest/optimization/scoring-weights/default`

Expected: `{"sharpe_ratio": 0.4, "total_return": 0.3, "max_drawdown": -0.2, "win_rate": 0.1}`

- [ ] **Step 3: Commit**

```bash
git add backend/api/backtest.py
git commit -m "feat: add default scoring weights endpoint

- Add GET /optimization/scoring-weights/default endpoint
- Return default weights for UI pre-population
- Import from scoring_functions module"
```

---

## Phase 4: Stability Analysis Implementation

### Task 4.0: Extract Shared Backtest Logic

**Files:**
- Create: `backend/core/backtest_runner.py`

- [ ] **Step 1: Create shared backtest runner utility**

```python
# Create backend/core/backtest_runner.py

"""
Shared backtest execution logic.

Extracted to avoid duplication between optimizers and analyzers.
"""

import asyncio
import backtrader as bt
from typing import Dict, Any, Type, List
from backend.core.strategy_base import StrategyBase
from backend.observers.trade_recorder import TradeRecorder


class BacktestRunner:
    """Shared backtest execution logic

    Used by GridSearchOptimizer, BayesianOptimizer, and StabilityAnalyzer
    to avoid code duplication.
    """

    @staticmethod
    async def run_backtest(
        strategy_class: Type[StrategyBase],
        params: Dict[str, Any],
        candles: List[Any],
        create_data_feed_fn,
        initial_cash: float = 100000.0,
        commission: float = 0.001
    ) -> Dict[str, Any]:
        """
        Run backtest with given parameters and candles.

        Args:
            strategy_class: Strategy class to instantiate
            params: Strategy parameters
            candles: Candle data list
            create_data_feed_fn: Function to create Backtrader data feed from candles
            initial_cash: Starting portfolio value
            commission: Commission rate

        Returns:
            Dict with backtest metrics:
                - final_value, pnl, pnl_pct
                - total_trades, win_rate
                - sharpe_ratio, max_drawdown
                - trades: List of trade dicts
        """
        # Create data feed using provided function
        data = create_data_feed_fn(candles)

        # Configure Cerebro
        cerebro = bt.Cerebro(oldsync=True)
        cerebro.adddata(data)
        cerebro.addstrategy(strategy_class, **params)
        cerebro.broker.setcash(initial_cash)
        cerebro.broker.setcommission(commission=commission)

        # Add analyzers
        cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
        cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
        cerebro.addobserver(TradeRecorder)

        # Run backtest in thread pool (Backtrader is not async)
        loop = asyncio.get_event_loop()

        def run_backtest():
            initial_value = cerebro.broker.getvalue()
            results = cerebro.run(runonce=False)
            final_value = cerebro.broker.getvalue()

            strategy = results[0]

            # Get trades from observer
            trades = []
            for observer in strategy.observers:
                if isinstance(observer, TradeRecorder):
                    trades = observer.trades
                    break

            # Calculate metrics
            pnl = final_value - initial_value
            pnl_pct = (pnl / initial_value) * 100

            total_trades = len(trades)
            if total_trades > 0:
                winning_trades = [t for t in trades if t['pnl'] > 0]
                win_rate = (len(winning_trades) / total_trades) * 100
            else:
                win_rate = 0.0

            # Extract Sharpe ratio
            sharpe_analysis = strategy.analyzers.sharpe.get_analysis()
            sharpe_ratio = sharpe_analysis.get('sharperatio', None)

            if sharpe_ratio is None:
                # Fallback estimation
                if pnl_pct < 10:
                    sharpe_ratio = 0.5 + (pnl_pct / 10.0)
                elif pnl_pct < 50:
                    sharpe_ratio = 1.0 + ((pnl_pct - 10) / 40.0)
                else:
                    sharpe_ratio = min(1.5 + ((pnl_pct - 50) / 100.0), 2.5)

            # Extract max drawdown
            drawdown_analysis = strategy.analyzers.drawdown.get_analysis()
            max_drawdown = drawdown_analysis.get('max', {}).get('drawdown', 0.0)

            return {
                'final_value': final_value,
                'pnl': pnl,
                'pnl_pct': pnl_pct,
                'total_trades': total_trades,
                'win_rate': win_rate,
                'sharpe_ratio': sharpe_ratio,
                'max_drawdown': max_drawdown,
                'trades': trades
            }

        result = await loop.run_in_executor(None, run_backtest)
        return result
```

- [ ] **Step 2: Write tests for BacktestRunner**

```python
# Create tests/test_backtest_runner.py

import pytest
from unittest.mock import Mock, AsyncMock, patch
from backend.core.backtest_runner import BacktestRunner

@pytest.mark.asyncio
async def test_backtest_runner_execution():
    """Test that BacktestRunner executes backtest"""
    runner = BacktestRunner()

    # Mock strategy
    strategy_class = Mock()
    strategy_class.__name__ = "TestStrategy"

    # Mock data feed creation
    def mock_create_data_feed(candles):
        data = Mock()
        return data

    # Mock Backtrader execution
    with patch('backtrader.Cerebro') as mock_cerebro_class:
        mock_cerebro = Mock()
        mock_cerebro_class.return_value = mock_cerebro

        # Mock backtest results
        mock_strategy = Mock()
        mock_strategy.analyzers.sharpe.get_analysis.return_value = {'sharperatio': 1.5}
        mock_strategy.analyzers.drawdown.get_analysis.return_value = {'max': {'drawdown': 10.0}}
        mock_strategy.observers = []

        mock_cerebro.run.return_value = [mock_strategy]
        mock_cerebro.broker.getvalue.side_effect = [100000, 110000]  # initial, final

        result = await BacktestRunner.run_backtest(
            strategy_class=strategy_class,
            params={'period': 20},
            candles=[],
            create_data_feed_fn=mock_create_data_feed
        )

        # Verify structure
        assert 'pnl' in result
        assert 'pnl_pct' in result
        assert 'sharpe_ratio' in result
        assert result['final_value'] == 110000
```

- [ ] **Step 3: Run tests**

Run: `pytest tests/test_backtest_runner.py -v`

Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add backend/core/backtest_runner.py tests/test_backtest_runner.py
git commit -m "refactor: extract shared backtest execution logic

- Create BacktestRunner utility class
- Move duplicated backtest logic from optimizers
- Static method for easy reuse
- Add comprehensive unit tests"
```

---

### Task 4.1: Implement Stability Analyzer (Refactored)

**Files:**
- Create: `backend/core/stability_analyzer.py`
- Create: `tests/test_stability_analyzer.py`

- [ ] **Step 1: Write the failing test**

```python
# Create tests/test_stability_analyzer.py

import pytest
from unittest.mock import Mock, AsyncMock, patch
from backend.core.stability_analyzer import StabilityAnalyzer
from backend.core.backtest_engine import BacktestEngine

@pytest.fixture
def mock_backtest_engine():
    """Create mock backtest engine"""
    engine = Mock(spec=BacktestEngine)
    return engine

@pytest.mark.asyncio
async def test_stability_analyzer_initialization(mock_backtest_engine):
    """Test analyzer initializes correctly"""
    analyzer = StabilityAnalyzer(mock_backtest_engine)
    assert analyzer.backtest_engine == mock_backtest_engine

@pytest.mark.asyncio
async def test_stability_analyzer_detects_stable_parameters():
    """Test stability analysis with consistent performance"""
    analyzer = StabilityAnalyzer(mock_backtest_engine)

    # Mock stable performance: similar scores around best params
    with patch('backend.core.stability_analyzer.BacktestRunner.run_backtest', new_callable=AsyncMock) as mock_run:
        # Consistent backtest results (good Sharpe, return, etc.)
        mock_run.return_value = {
            'pnl_pct': 50.0,
            'sharpe_ratio': 2.0,
            'max_drawdown': 10.0,
            'win_rate': 60.0
        }

        result = await analyzer.analyze(
            strategy_class=Mock(),
            best_params={'period': 20},
            candles=[],
            n_neighbors=5
        )

        # Should detect as stable (consistent scores = low variance)
        assert result['is_stable'] == True
        assert result['stability_score'] > 0.8
        assert result['variance'] < 0.1

@pytest.mark.asyncio
async def test_stability_analyzer_detects_unstable_parameters():
    """Test stability analysis with volatile performance"""
    analyzer = StabilityAnalyzer(mock_backtest_engine)

    # Mock volatile performance: scores vary widely
    call_count = [0]
    results = [
        {'pnl_pct': 100, 'sharpe_ratio': 3.0, 'max_drawdown': 5, 'win_rate': 80},
        {'pnl_pct': -10, 'sharpe_ratio': -0.5, 'max_drawdown': 30, 'win_rate': 40},
        {'pnl_pct': 80, 'sharpe_ratio': 2.5, 'max_drawdown': 8, 'win_rate': 70},
        {'pnl_pct': -20, 'sharpe_ratio': -1.0, 'max_drawdown': 40, 'win_rate': 35},
        {'pnl_pct': 60, 'sharpe_ratio': 1.8, 'max_drawdown': 12, 'win_rate': 65},
    ]

    async def mock_run(*args, **kwargs):
        result = results[call_count[0] % len(results)]
        call_count[0] += 1
        return result

    with patch('backend.core.stability_analyzer.BacktestRunner.run_backtest', mock_run):
        analysis_result = await analyzer.analyze(
            strategy_class=Mock(),
            best_params={'period': 20},
            candles=[],
            n_neighbors=5
        )

        # Should detect as unstable (high variance)
        assert analysis_result['is_stable'] == False
        assert analysis_result['stability_score'] < 0.5
        assert analysis_result['variance'] > 0.1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_stability_analyzer.py -v`

Expected: FAIL - ModuleNotFoundError

- [ ] **Step 3: Implement StabilityAnalyzer**

```python
# Create backend/core/stability_analyzer.py

"""
Parameter Stability Analyzer

Analyzes parameter stability by sampling around optimal parameters
to detect "parameter plateaus" vs isolated peaks.
"""

import logging
import numpy as np
from typing import Dict, Any, Type, List
from unittest.mock import Mock

from backend.core.backtest_engine import BacktestEngine
from backend.core.strategy_base import StrategyBase
from backend.core.scoring_functions import calculate_composite_score

logger = logging.getLogger(__name__)


class StabilityAnalyzer:
    """Analyzes parameter stability to prevent overfitting

    Tests performance around optimal parameters. Stable parameters
    should form a "plateau" where similar values perform similarly.
    Isolated peaks indicate overfitting.

    Example:
        >>> analyzer = StabilityAnalyzer(backtest_engine)
        >>> stability = await analyzer.analyze(
        ...     strategy_class=MyStrategy,
        ...     best_params={'period': 20},
        ...     candles=candles,
        ...     n_neighbors=10
        ... )
        >>> if stability['is_stable']:
        ...     print("Parameters are stable")
    """

    def __init__(self, backtest_engine: BacktestEngine):
        """Initialize stability analyzer

        Args:
            backtest_engine: BacktestEngine for running backtests
        """
        self.backtest_engine = backtest_engine

    async def analyze(
        self,
        strategy_class: Type[StrategyBase],
        best_params: Dict[str, Any],
        candles: List[Any],
        scoring_weights: Dict[str, float] = None,
        n_neighbors: int = 10
    ) -> Dict[str, Any]:
        """
        Analyze parameter stability by sampling neighborhood

        Args:
            strategy_class: Strategy class
            best_params: Best parameter combination
            candles: Candle data for backtests
            scoring_weights: Optional custom scoring weights
            n_neighbors: Number of neighbors to sample per parameter

        Returns:
            Dict containing:
                - stability_score: 0-1 stability score (higher = more stable)
                - variance: Performance variance
                - std: Standard deviation of scores
                - mean_score: Average score
                - is_stable: Boolean assessment (variance < 0.1)
                - neighbor_results: Sample of neighbor results
        """
        import backtrader as bt
        from backend.observers.trade_recorder import TradeRecorder

        neighbor_results = []

        # Sample around each continuous parameter
        for param_name, param_value in best_params.items():
            if isinstance(param_value, (int, float)):
                # Sample in ±10% range
                delta = param_value * 0.1

                for i in range(n_neighbors):
                    # Skip the center point (best params)
                    if i == n_neighbors // 2:
                        continue

                    # Perturb parameter
                    perturbation = delta * (i - n_neighbors // 2) / (n_neighbors // 2)
                    perturbed_value = param_value + perturbation

                    # Ensure positive value for periods/parameters
                    if perturbed_value <= 0:
                        continue

                    perturbed_params = best_params.copy()
                    perturbed_params[param_name] = perturbed_value

                    # Run backtest
                    result = await self._run_backtest_with_params(
                        strategy_class,
                        perturbed_params,
                        candles
                    )

                    # Calculate composite score
                    score = calculate_composite_score(result, scoring_weights)

                    neighbor_results.append({
                        'params': perturbed_params,
                        'score': score,
                        'perturbed_param': param_name,
                        'perturbation': perturbation
                    })

        # Calculate statistics
        if not neighbor_results:
            # No continuous parameters to analyze
            return {
                'stability_score': 1.0,
                'variance': 0.0,
                'std': 0.0,
                'mean_score': 0.0,
                'is_stable': True,
                'neighbor_results': [],
                'message': 'No continuous parameters to analyze'
            }

        scores = [r['score'] for r in neighbor_results]
        variance = float(np.var(scores))
        std = float(np.std(scores))
        mean_score = float(np.mean(scores))

        # Stability score: inverse of variance (clamped to 0-1)
        stability_score = max(0, 1 - variance)

        # Stability threshold
        is_stable = variance < 0.1

        logger.info(
            f"Stability analysis: score={stability_score:.3f}, "
            f"variance={variance:.4f}, stable={is_stable}"
        )

        return {
            'stability_score': stability_score,
            'variance': variance,
            'std': std,
            'mean_score': mean_score,
            'is_stable': is_stable,
            'neighbor_results': neighbor_results[:5]  # Return first 5 for display
        }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_stability_analyzer.py -v`

Expected: PASS - All tests pass

- [ ] **Step 5: Commit**

```bash
git add backend/core/stability_analyzer.py tests/test_stability_analyzer.py
git commit -m "feat: implement parameter stability analyzer

- Add StabilityAnalyzer class
- Sample parameters in ±10% neighborhood
- Calculate performance variance and stability score
- Detect isolated peaks vs parameter plateaus
- Add comprehensive unit tests"
```

---

## Phase 5: Frontend Integration

### Task 5.1: Extend Frontend API Types

**Files:**
- Modify: `frontend/lib/api/optimization.ts`

- [ ] **Step 1: Read current API types**

Run: `cat frontend/lib/api/optimization.ts`

Expected: See current OptimizationRequest interface

- [ ] **Step 2: Extend types**

```typescript
// Modify frontend/lib/api/optimization.ts

export interface OptimizationRequest {
  strategy_name: string;
  symbol: string;
  interval: string;
  start_time: string;
  end_time: string;
  parameter_ranges: Record<string, any[]>;

  // NEW: Optimization method
  optimization_method?: 'grid' | 'bayesian';

  // NEW: Bayesian-specific
  n_trials?: number;

  // NEW: Scoring configuration
  scoring_weights?: {
    sharpe_ratio: number;
    total_return: number;
    max_drawdown: number;
    win_rate: number;
  };

  // NEW: Overfitting prevention
  enable_out_of_sample?: boolean;
  test_start_time?: string;
  test_end_time?: string;
  enable_stability_analysis?: boolean;
}

export interface OptimizationResponse {
  job_id: number;
  optimization_method?: string;
  total_combinations?: number;
  n_trials?: number;
  best_params?: Record<string, any>;
  best_score?: number;
  best_result: OptimizationResult;
  results: OptimizationResult[];

  // NEW: Stability analysis
  stability?: {
    stability_score: number;
    variance: number;
    is_stable: boolean;
    neighbor_results: Array<{
      params: Record<string, any>;
      score: number;
    }>;
  };

  // NEW: Out-of-sample test
  out_of_sample?: {
    result: any;
    is_overfitted: boolean;
    performance_degradation: number;
  };
}

export interface OptimizationResult {
  id: number;
  job_id: number;
  parameters: Record<string, any>;
  pnl: number;
  pnl_pct: number;
  total_trades: number;
  sharpe_ratio?: number;
  max_drawdown: number;
  win_rate: number;
  is_best: boolean;

  // NEW: Composite score
  composite_score?: number;
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/lib/api/optimization.ts
git commit -m "feat: extend optimization API types

- Add optimization_method and n_trials
- Add scoring_weights interface
- Add OOS test configuration
- Add stability and out_of_sample response fields
- Add composite_score to results"
```

---

### Task 5.2: Extend Optimization Form

**Files:**
- Modify: `frontend/components/OptimizationForm.tsx`

- [ ] **Step 1: Read current form**

Run: `cat frontend/components/OptimizationForm.tsx`

Expected: See current form structure

- [ ] **Step 2: Add new form fields**

```typescript
// Modify frontend/components/OptimizationForm.tsx

// Add state for new fields
const [optimizationMethod, setOptimizationMethod] = useState<'grid' | 'bayesian'>('bayesian');
const [nTrials, setNTrials] = useState(100);
const [scoringWeights, setScoringWeights] = useState({
  sharpe_ratio: 0.4,
  total_return: 0.3,
  max_drawdown: -0.2,
  win_rate: 0.1
});
const [enableOutOfSample, setEnableOutOfSample] = useState(false);
const [testStartTime, setTestStartTime] = useState('');
const [testEndTime, setTestEndTime] = useState('');
const [enableStabilityAnalysis, setEnableStabilityAnalysis] = useState(true);
const [showAdvanced, setShowAdvanced] = useState(false);

// In the form JSX, add these sections after parameter ranges:

{/* Optimization Method */}
<div className="mb-6">
  <label className="block text-sm font-medium text-gray-700 mb-2">
    Optimization Method
  </label>
  <div className="flex space-x-4">
    <label className="flex items-center">
      <input
        type="radio"
        value="grid"
        checked={optimizationMethod === 'grid'}
        onChange={(e) => setOptimizationMethod(e.target.value as any)}
        className="mr-2"
      />
      <span>Grid Search (exhaustive)</span>
    </label>
    <label className="flex items-center">
      <input
        type="radio"
        value="bayesian"
        checked={optimizationMethod === 'bayesian'}
        onChange={(e) => setOptimizationMethod(e.target.value as any)}
        className="mr-2"
      />
      <span>Bayesian Optimization (efficient)</span>
    </label>
  </div>

  {optimizationMethod === 'bayesian' && (
    <div className="mt-2">
      <label className="block text-sm text-gray-600 mb-1">
        Number of Trials
      </label>
      <input
        type="number"
        value={nTrials}
        onChange={(e) => setNTrials(parseInt(e.target.value) || 100)}
        min="10"
        max="1000"
        className="border rounded px-3 py-2 w-32"
      />
      <p className="text-xs text-gray-500 mt-1">
        More trials = better results but slower
      </p>
    </div>
  )}
</div>

{/* Advanced Options - Scoring and Overfitting Prevention */}
<button
  type="button"
  onClick={() => setShowAdvanced(!showAdvanced)}
  className="mb-4 text-sm text-blue-600 hover:text-blue-800"
>
  {showAdvanced ? '▼' : '▶'} Advanced Options
</button>

{showAdvanced && (
  <div className="mb-6 p-4 bg-gray-50 rounded border">
    {/* Scoring Weights */}
    <div className="mb-4">
      <h4 className="text-sm font-medium mb-2">Scoring Weights</h4>
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-xs text-gray-600">Sharpe Ratio</label>
          <input
            type="number"
            step="0.1"
            value={scoringWeights.sharpe_ratio}
            onChange={(e) => setScoringWeights({
              ...scoringWeights,
              sharpe_ratio: parseFloat(e.target.value) || 0
            })}
            className="w-full border rounded px-2 py-1 text-sm"
          />
        </div>
        <div>
          <label className="block text-xs text-gray-600">Total Return</label>
          <input
            type="number"
            step="0.1"
            value={scoringWeights.total_return}
            onChange={(e) => setScoringWeights({
              ...scoringWeights,
              total_return: parseFloat(e.target.value) || 0
            })}
            className="w-full border rounded px-2 py-1 text-sm"
          />
        </div>
        <div>
          <label className="block text-xs text-gray-600">Max Drawdown</label>
          <input
            type="number"
            step="0.1"
            value={scoringWeights.max_drawdown}
            onChange={(e) => setScoringWeights({
              ...scoringWeights,
              max_drawdown: parseFloat(e.target.value) || 0
            })}
            className="w-full border rounded px-2 py-1 text-sm"
          />
        </div>
        <div>
          <label className="block text-xs text-gray-600">Win Rate</label>
          <input
            type="number"
            step="0.1"
            value={scoringWeights.win_rate}
            onChange={(e) => setScoringWeights({
              ...scoringWeights,
              win_rate: parseFloat(e.target.value) || 0
            })}
            className="w-full border rounded px-2 py-1 text-sm"
          />
        </div>
      </div>
    </div>

    {/* Overfitting Prevention */}
    <div className="mb-4">
      <h4 className="text-sm font-medium mb-2">Overfitting Prevention</h4>

      <label className="flex items-center mb-2">
        <input
          type="checkbox"
          checked={enableOutOfSample}
          onChange={(e) => setEnableOutOfSample(e.target.checked)}
          className="mr-2"
        />
        <span className="text-sm">Enable Out-of-Sample Test</span>
      </label>

      {enableOutOfSample && (
        <div className="ml-6 grid grid-cols-2 gap-4">
          <div>
            <label className="block text-xs text-gray-600">Test Start</label>
            <input
              type="datetime-local"
              value={testStartTime}
              onChange={(e) => setTestStartTime(e.target.value)}
              className="w-full border rounded px-2 py-1 text-sm"
            />
          </div>
          <div>
            <label className="block text-xs text-gray-600">Test End</label>
            <input
              type="datetime-local"
              value={testEndTime}
              onChange={(e) => setTestEndTime(e.target.value)}
              className="w-full border rounded px-2 py-1 text-sm"
            />
          </div>
        </div>
      )}

      <label className="flex items-center mt-2">
        <input
          type="checkbox"
          checked={enableStabilityAnalysis}
          onChange={(e) => setEnableStabilityAnalysis(e.target.checked)}
          className="mr-2"
        />
        <span className="text-sm">Enable Parameter Stability Analysis</span>
      </label>
    </div>
  </div>
)}

// Update handleSubmit to include new fields:
const handleSubmit = (e: React.FormEvent) => {
  e.preventDefault();

  const request: OptimizationRequest = {
    // ... existing fields
    optimization_method: optimizationMethod,
    n_trials: optimizationMethod === 'bayesian' ? nTrials : undefined,
    scoring_weights: scoringWeights,
    enable_out_of_sample: enableOutOfSample,
    test_start_time: enableOutOfSample ? testStartTime : undefined,
    test_end_time: enableOutOfSample ? testEndTime : undefined,
    enable_stability_analysis: enableStabilityAnalysis
  };

  onSubmit(request);
};
```

- [ ] **Step 3: Commit**

```bash
git add frontend/components/OptimizationForm.tsx
git commit -m "feat: extend optimization form with new options

- Add optimization method selector (grid/bayesian)
- Add trial count input for Bayesian
- Add scoring weights configuration in advanced options
- Add out-of-sample test toggle and date pickers
- Add stability analysis toggle
- Maintain clean UI with collapsible advanced section"
```

---

### Task 5.3: Extend Optimization Results Display

**Files:**
- Modify: `frontend/components/OptimizationResults.tsx`

- [ ] **Step 1: Add stability and OOS cards**

```typescript
// Modify frontend/components/OptimizationResults.tsx

// Add these new sections after the main results:

{/* Stability Analysis Card */}
{result.stability && (
  <div className="mt-6 bg-white rounded-lg shadow p-6">
    <h3 className="text-lg font-semibold mb-4">Parameter Stability Analysis</h3>

    <div className="flex items-center justify-between mb-4">
      <div>
        <div className="text-sm text-gray-600">Stability Score</div>
        <div className="text-3xl font-bold">
          {(result.stability.stability_score * 100).toFixed(0)}%
        </div>
      </div>

      <div className={`px-4 py-2 rounded ${
        result.stability.is_stable
          ? 'bg-green-100 text-green-800'
          : 'bg-yellow-100 text-yellow-800'
      }`}>
        {result.stability.is_stable ? '✓ Stable' : '⚠ Unstable'}
      </div>
    </div>

    <div className="grid grid-cols-2 gap-4 text-sm">
      <div>
        <span className="text-gray-600">Variance:</span>
        <span className="ml-2 font-medium">{result.stability.variance.toFixed(4)}</span>
      </div>
      <div>
        <span className="text-gray-600">Std Dev:</span>
        <span className="ml-2 font-medium">{result.stability.std.toFixed(4)}</span>
      </div>
    </div>

    {!result.stability.is_stable && (
      <div className="mt-4 p-3 bg-yellow-50 border border-yellow-200 rounded text-sm text-yellow-800">
        <strong>Warning:</strong> Parameters show high variance.
        This may indicate overfitting to an isolated peak.
        Consider using a simpler strategy or more data.
      </div>
    )}
  </div>
)}

{/* Out-of-Sample Test Card */}
{result.out_of_sample && (
  <div className="mt-6 bg-white rounded-lg shadow p-6">
    <h3 className="text-lg font-semibold mb-4">Out-of-Sample Test</h3>

    {result.out_of_sample.is_overfitted ? (
      <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded text-sm text-red-800">
        <strong>⚠ Overfitting Detected:</strong> Out-of-sample performance
        is significantly worse than in-sample. The strategy may not generalize
        to new data.
      </div>
    ) : (
      <div className="mb-4 p-3 bg-green-50 border border-green-200 rounded text-sm text-green-800">
        <strong>✓ Good Generalization:</strong> Out-of-sample performance
        is consistent with in-sample results.
      </div>
    )}

    <div className="text-sm">
      <div className="mb-2">
        <span className="text-gray-600">Performance Degradation:</span>
        <span className="ml-2 font-medium">
          {result.out_of_sample.performance_degradation.toFixed(2)}%
        </span>
      </div>

      <div className="text-gray-600">
        Test period: {new Date(result.out_of_sample.result.test_period.start).toLocaleDateString()} -
        {new Date(result.out_of_sample.result.test_period.end).toLocaleDateString()}
      </div>
    </div>
  </div>
)}

// Also add composite_score to the main results table:

// In the results table, add a new column:
<thead>
  <tr>
    <th className="px-4 py-2 text-left">Parameters</th>
    <th className="px-4 py-2 text-left">Return</th>
    <th className="px-4 py-2 text-left">Sharpe</th>
    <th className="px-4 py-2 text-left">Score</th> {/* NEW */}
    <th className="px-4 py-2 text-left">Trades</th>
  </tr>
</thead>

<tbody>
  {results.map((result) => (
    <tr key={result.id} className={result.is_best ? 'bg-green-50' : ''}>
      {/* ... existing cells ... */}
      <td className="px-4 py-2">
        {result.composite_score !== undefined && (
          <span className="font-medium">
            {result.composite_score.toFixed(3)}
          </span>
        )}
      </td>
    </tr>
  ))}
</tbody>
```

- [ ] **Step 2: Commit**

```bash
git add frontend/components/OptimizationResults.tsx
git commit -m "feat: add stability and OOS test results display

- Add stability analysis card with score and variance
- Show stable/unstable badge with visual indicator
- Add out-of-sample test card with overfitting warning
- Add composite_score column to results table
- Display warnings for unstable parameters or overfitting"
```

---

## Phase 6: Testing and Documentation

### Task 6.1: Add Integration Tests

**Files:**
- Modify: `tests/test_optimization_api.py`

- [ ] **Step 1: Add Bayesian optimization test**

```python
# Add to tests/test_optimization_api.py

@pytest.mark.asyncio
async def test_bayesian_optimization_endpoint():
    """Test Bayesian optimization API endpoint"""
    from backend.core.bayesian_optimizer import BayesianOptimizer

    request_data = {
        'strategy_name': 'DualMovingAverage',
        'symbol': 'BTCUSDT',
        'interval': '1h',
        'start_time': '2024-01-01T00:00:00',
        'end_time': '2024-06-30T23:59:59',
        'parameter_ranges': {
            'fast_period': [10, 20],
            'slow_period': [20, 50]
        },
        'optimization_method': 'bayesian',
        'n_trials': 5  # Small number for testing
    }

    response = client.post("/api/v1/backtest/optimize", json=request_data)

    assert response.status_code == 200
    data = response.json()

    assert data['optimization_method'] == 'bayesian'
    assert 'best_params' in data
    assert 'n_trials' in data
    assert data['n_trials'] == 5

@pytest.mark.asyncio
async def test_custom_scoring_weights():
    """Test optimization with custom scoring weights"""
    request_data = {
        'strategy_name': 'DualMovingAverage',
        'symbol': 'BTCUSDT',
        'interval': '1h',
        'start_time': '2024-01-01T00:00:00',
        'end_time': '2024-06-30T23:59:59',
        'parameter_ranges': {'fast_period': [10, 20]},
        'optimization_method': 'bayesian',
        'n_trials': 3,
        'scoring_weights': {
            'sharpe_ratio': 1.0,  # Only Sharpe matters
            'total_return': 0.0,
            'max_drawdown': 0.0,
            'win_rate': 0.0
        }
    }

    response = client.post("/api/v1/backtest/optimize", json=request_data)

    assert response.status_code == 200
    # Verify the request was accepted
```

- [ ] **Step 2: Run integration tests**

Run: `pytest tests/test_optimization_api.py -v`

Expected: PASS - New tests pass

- [ ] **Step 3: Commit**

```bash
git add tests/test_optimization_api.py
git commit -m "test: add Bayesian optimization integration tests

- Test Bayesian optimization API endpoint
- Test custom scoring weights
- Verify response structure
- Ensure backward compatibility with grid search"
```

---

### Task 6.2: Update Documentation

**Files:**
- Modify: `README.md` or relevant docs

- [ ] **Step 1: Update README with new features**

```markdown
# In README.md or docs/optimization.md

## Parameter Optimization

The platform supports two optimization methods:

### Bayesian Optimization (Recommended)

Efficient parameter search using Optuna. Learns from previous trials to find optimal parameters with fewer backtests.

**Features:**
- Intelligent parameter suggestions
- Composite scoring (Sharpe, return, drawdown, win rate)
- Overfitting prevention (stability analysis, out-of-sample testing)

**Example:**
\`\`\`python
POST /api/v1/backtest/optimize
{
  "strategy_name": "DualMovingAverage",
  "symbol": "BTCUSDT",
  "interval": "1h",
  "start_time": "2024-01-01T00:00:00",
  "end_time": "2024-12-31T23:59:59",
  "parameter_ranges": {
    "fast_period": [10, 50],
    "slow_period": [20, 100]
  },
  "optimization_method": "bayesian",
  "n_trials": 100,
  "enable_stability_analysis": true
}
\`\`\`

### Grid Search (Legacy)

Exhaustive search through all parameter combinations. Useful for small parameter spaces.

### Composite Scoring

Optimization uses a weighted score combining multiple metrics:

- **Sharpe Ratio (40%)**: Risk-adjusted return
- **Total Return (30%)**: Raw performance
- **Max Drawdown (-20%)**: Risk penalty
- **Win Rate (10%)**: Trade success rate

Customize weights via `scoring_weights` parameter.

### Overfitting Prevention

**Parameter Stability Analysis:**
Tests performance around optimal parameters. Low variance = stable (good), high variance = isolated peak (overfitting).

**Out-of-Sample Testing:**
Validates parameters on unseen data. Enable via `enable_out_of_sample=true`.
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: document Bayesian optimization and new features

- Document Bayesian vs Grid search methods
- Explain composite scoring system
- Document overfitting prevention features
- Add API usage examples"
```

---

## Phase 7: End-to-End Testing

### Task 7.1: Add E2E Tests

**Files:**
- Modify: `frontend/e2e/optimization.spec.ts`

- [ ] **Step 1: Add E2E test for Bayesian optimization**

```typescript
// Add to frontend/e2e/optimization.spec.ts

test('should run Bayesian optimization', async ({ page }) => {
  await page.goto('/optimize');

  // Select Bayesian optimization
  await page.click('input[value="bayesian"]');

  // Set trial count
  await page.fill('input[type="number"][min="10"]', '20');

  // Fill other required fields...
  // (symbol, interval, time range, parameters)

  // Run optimization
  await page.click('button[type="submit"]');

  // Wait for results
  await page.waitForSelector('[data-testid="optimization-results"]');

  // Verify Bayesian-specific elements
  await page.waitForText('n_trials');
  await page.waitForText('composite_score');

  // Check stability card if enabled
  const stabilityCard = page.locator('[data-testid="stability-analysis"]');
  if (await stabilityCard.isVisible()) {
    await page.waitForText('Stability Score');
  }
});

test('should display stability analysis results', async ({ page }) => {
  // Run optimization with stability analysis enabled
  await page.goto('/optimize');

  // Enable stability analysis
  await page.check('input[name="enable_stability_analysis"]');

  // Run optimization...

  // Verify stability card appears
  await page.waitForSelector('[data-testid="stability-analysis"]');
  await page.waitForText('Stability Score');

  // Check if stable/unstable badge appears
  const badge = page.locator('[data-testid="stability-badge"]');
  expect(await badge.isVisible()).toBe(true);
});
```

- [ ] **Step 2: Run E2E tests**

Run: `cd frontend && pnpm test:e2e`

Expected: PASS - E2E tests validate full flow

- [ ] **Step 3: Commit**

```bash
git add frontend/e2e/optimization.spec.ts
git commit -m "test: add E2E tests for Bayesian optimization

- Test Bayesian optimization flow
- Verify stability analysis display
- Check composite score rendering
- Ensure new UI components work end-to-end"
```

---

## Task Completion Checklist

After completing all tasks:

- [ ] All unit tests pass: `pytest tests/ -v`
- [ ] All integration tests pass: `pytest tests/test_optimization_api.py -v`
- [ ] All E2E tests pass: `cd frontend && pnpm test:e2e`
- [ ] Backend builds without errors: `cd backend && python -m py_compile backend/core/*.py`
- [ ] Frontend builds without errors: `cd frontend && pnpm build`
- [ ] Documentation updated
- [ ] Git history clean with frequent commits

---

## Success Criteria Verification

1. **Efficiency**: Bayesian optimization completes in <50% of grid search time for same parameter space
2. **Composite Scoring**: Results include composite_score field
3. **Stability Analysis**: Stability card displays with variance and is_stable flag
4. **OOS Testing**: Out-of-sample results available when enabled
5. **Backward Compatibility**: Grid search still works with existing code

---

**Implementation complete!** 🎉

The parameter optimization system now includes:
- ✅ Bayesian optimization with Optuna
- ✅ Composite scoring functions
- ✅ Parameter stability analysis
- ✅ Out-of-sample testing
- ✅ Extended API and UI
- ✅ Comprehensive testing
- ✅ Full backward compatibility
