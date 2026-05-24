"""
Unit tests for GridSearchOptimizer class

Tests verify:
1. Parameter combination generation (single, multiple, different types)
2. Optimization flow (all combinations tested, results saved)
3. Optimal parameter selection (based on score/pnl_pct)
4. Progress updates (status updates)
5. Edge cases (single combination, many combinations, errors)
"""
import pytest
import tempfile
import os
from datetime import datetime, timedelta
from typing import Dict, Any

import backtrader as bt

from backend.core.optimizer import GridSearchOptimizer
from backend.core.backtest_engine import BacktestEngine
from backend.core.strategy_base import StrategyBase
from backend.database import Database, CandleData
from backend.models.optimization_job import OptimizationJob
from backend.models.optimization_result import OptimizationResult


# ========================================
# Test Strategies
# ========================================

class SimpleMAStrategy(StrategyBase):
    """Simple moving average strategy for testing parameter optimization"""

    strategy_name = "Simple MA for Optimization"
    strategy_version = "1.0"
    strategy_description = "MA crossover strategy with configurable period"

    params = (
        ('ma_period', 10),
        ('threshold', 0.0),
    )

    def __init__(self):
        super().__init__()
        self.ma = bt.indicators.SimpleMovingAverage(
            self.data.close, period=self.params.ma_period
        )

    def next(self):
        if not self.position:
            # Buy when price above MA by threshold
            if self.data.close[0] > self.ma[0] * (1 + self.params.threshold):
                self.buy()
        else:
            # Sell when price below MA by threshold
            if self.data.close[0] < self.ma[0] * (1 - self.params.threshold):
                self.sell()

    @staticmethod
    def get_parameters() -> Dict[str, Any]:
        return {
            'ma_period': {
                'type': 'int',
                'default': 10,
                'min': 5,
                'max': 50,
                'description': 'Moving Average period'
            },
            'threshold': {
                'type': 'float',
                'default': 0.0,
                'min': 0.0,
                'max': 0.1,
                'description': 'Buy/sell threshold'
            }
        }


class NoTradeStrategy(StrategyBase):
    """Strategy that never trades - for testing edge cases"""

    strategy_name = "No Trade"
    strategy_version = "1.0"
    strategy_description = "Strategy that makes no trades"

    params = (
        ('dummy_param', 1),
    )

    def next(self):
        pass

    @staticmethod
    def get_parameters() -> Dict[str, Any]:
        return {
            'dummy_param': {
                'type': 'int',
                'default': 1,
                'min': 1,
                'max': 10,
                'description': 'Dummy parameter'
            }
        }


# ========================================
# Test Fixtures
# ========================================

@pytest.fixture
def temp_db():
    """Create a temporary database for testing"""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test_quant.db")
        db_url = f"sqlite:///{db_path}"
        db = Database(db_url)
        db.create_tables()
        yield db


@pytest.fixture
def sample_candles():
    """Create sample candle data (100 hourly candles with upward trend)"""
    base_time = datetime(2024, 1, 1, 0, 0, 0)
    candles = []

    # Generate 100 candles with a slight upward trend
    for i in range(100):
        open_time = base_time + timedelta(hours=i)
        close_time = open_time + timedelta(hours=1)

        # Price pattern: slight upward trend with some volatility
        base_price = 100.0 + i * 0.5  # Upward trend
        volatility = (i % 10 - 5) * 0.5  # Add some volatility

        open_price = base_price + volatility
        close_price = base_price + volatility + 0.3
        high_price = max(open_price, close_price) + 0.2
        low_price = min(open_price, close_price) - 0.2
        volume = 1000.0 + i * 10

        candles.append(CandleData(
            symbol='BTCUSDT',
            interval='1h',
            open_time=open_time,
            close_time=close_time,
            open_price=open_price,
            high_price=high_price,
            low_price=low_price,
            close_price=close_price,
            volume=volume
        ))

    return candles


@pytest.fixture
def backtest_engine(temp_db, sample_candles):
    """Create backtest engine with sample data loaded"""
    temp_db.save_candles(sample_candles)
    return BacktestEngine(temp_db)


@pytest.fixture
def optimizer(backtest_engine):
    """Create optimizer instance"""
    return GridSearchOptimizer(backtest_engine)


# ========================================
# Test Parameter Combination Generation
# ========================================

class TestParameterCombinationGeneration:
    """Test _generate_combinations method"""

    def test_single_parameter(self, optimizer):
        """Test generation with single parameter"""
        param_ranges = {
            'period': [10, 20, 30]
        }

        combinations = optimizer._generate_combinations(param_ranges)

        # Should generate 3 combinations
        assert len(combinations) == 3

        # Verify each combination
        assert {'period': 10} in combinations
        assert {'period': 20} in combinations
        assert {'period': 30} in combinations

    def test_multiple_parameters(self, optimizer):
        """Test generation with multiple parameters"""
        param_ranges = {
            'period': [10, 20],
            'threshold': [0.5, 1.0]
        }

        combinations = optimizer._generate_combinations(param_ranges)

        # Should generate 2 * 2 = 4 combinations
        assert len(combinations) == 4

        # Verify all combinations exist
        expected = [
            {'period': 10, 'threshold': 0.5},
            {'period': 10, 'threshold': 1.0},
            {'period': 20, 'threshold': 0.5},
            {'period': 20, 'threshold': 1.0}
        ]

        for exp in expected:
            assert exp in combinations

    def test_three_parameters(self, optimizer):
        """Test generation with three parameters"""
        param_ranges = {
            'p1': [1, 2],
            'p2': [3, 4],
            'p3': [5, 6]
        }

        combinations = optimizer._generate_combinations(param_ranges)

        # Should generate 2 * 2 * 2 = 8 combinations
        assert len(combinations) == 8

    def test_different_value_types(self, optimizer):
        """Test generation with different value types"""
        param_ranges = {
            'int_param': [1, 2],
            'float_param': [0.5, 1.5],
            'str_param': ['a', 'b'],
            'bool_param': [True, False]
        }

        combinations = optimizer._generate_combinations(param_ranges)

        # Should generate 2 * 2 * 2 * 2 = 16 combinations
        assert len(combinations) == 16

        # Verify types are preserved
        for combo in combinations:
            assert isinstance(combo['int_param'], int)
            assert isinstance(combo['float_param'], float)
            assert isinstance(combo['str_param'], str)
            assert isinstance(combo['bool_param'], bool)

    def test_single_value_parameter(self, optimizer):
        """Test generation with single value in parameter range"""
        param_ranges = {
            'period': [10],
            'threshold': [0.5, 1.0]
        }

        combinations = optimizer._generate_combinations(param_ranges)

        # Should generate 1 * 2 = 2 combinations
        assert len(combinations) == 2

    def test_empty_parameter_ranges(self, optimizer):
        """Test generation with empty parameter ranges"""
        param_ranges = {}

        combinations = optimizer._generate_combinations(param_ranges)

        # Should generate 1 empty combination
        assert len(combinations) == 1
        assert combinations[0] == {}


# ========================================
# Test Optimization Flow
# ========================================

class TestOptimizationFlow:
    """Test complete optimization flow"""

    @pytest.mark.asyncio
    async def test_optimization_runs_all_combinations(self, optimizer, temp_db):
        """Test that all parameter combinations are tested"""
        # Create optimization job
        job = OptimizationJob(
            strategy_name='SimpleMAStrategy',
            symbol='BTCUSDT',
            interval='1h',
            start_time=datetime.fromisoformat('2024-01-01T00:00:00'),
            end_time=datetime.fromisoformat('2024-01-05T00:00:00'),
            parameter_ranges={'ma_period': [5, 10], 'threshold': [0.0, 0.01]},
            optimization_method='grid',
            status='running'
        )
        job_id = temp_db.create_optimization_job(job)

        # Run optimization
        param_ranges = {
            'ma_period': [5, 10],
            'threshold': [0.0, 0.01]
        }

        best_result = await optimizer.optimize(
            strategy_class=SimpleMAStrategy,
            symbol='BTCUSDT',
            interval='1h',
            start_time='2024-01-01T00:00:00',
            end_time='2024-01-05T00:00:00',
            parameter_ranges=param_ranges,
            optimization_job_id=job_id
        )

        # Verify all combinations were tested (2 * 2 = 4)
        results = temp_db.get_optimization_results(job_id)
        assert len(results) == 4

    @pytest.mark.asyncio
    async def test_optimization_saves_results_to_database(self, optimizer, temp_db):
        """Test that optimization results are saved to database"""
        # Create optimization job
        job = OptimizationJob(
            strategy_name='SimpleMAStrategy',
            symbol='BTCUSDT',
            interval='1h',
            start_time=datetime.fromisoformat('2024-01-01T00:00:00'),
            end_time=datetime.fromisoformat('2024-01-05T00:00:00'),
            parameter_ranges={'ma_period': [5, 10]},
            optimization_method='grid',
            status='running'
        )
        job_id = temp_db.create_optimization_job(job)

        # Run optimization with 2 combinations
        param_ranges = {'ma_period': [5, 10]}

        await optimizer.optimize(
            strategy_class=SimpleMAStrategy,
            symbol='BTCUSDT',
            interval='1h',
            start_time='2024-01-01T00:00:00',
            end_time='2024-01-05T00:00:00',
            parameter_ranges=param_ranges,
            optimization_job_id=job_id
        )

        # Verify results saved
        results = temp_db.get_optimization_results(job_id)
        assert len(results) == 2

        # Verify result structure
        for result in results:
            assert result.optimization_job_id == job_id
            assert isinstance(result.parameters, dict)
            assert isinstance(result.score, float)
            assert 'ma_period' in result.parameters

    @pytest.mark.asyncio
    async def test_optimization_updates_job_status(self, optimizer, temp_db):
        """Test that optimization updates job status"""
        # Create optimization job
        job = OptimizationJob(
            strategy_name='SimpleMAStrategy',
            symbol='BTCUSDT',
            interval='1h',
            start_time=datetime.fromisoformat('2024-01-01T00:00:00'),
            end_time=datetime.fromisoformat('2024-01-05T00:00:00'),
            parameter_ranges={'ma_period': [5, 10]},
            optimization_method='grid',
            status='running'
        )
        job_id = temp_db.create_optimization_job(job)

        # Run optimization
        param_ranges = {'ma_period': [5, 10]}

        await optimizer.optimize(
            strategy_class=SimpleMAStrategy,
            symbol='BTCUSDT',
            interval='1h',
            start_time='2024-01-01T00:00:00',
            end_time='2024-01-05T00:00:00',
            parameter_ranges=param_ranges,
            optimization_job_id=job_id
        )

        # Verify job status updated to completed
        with temp_db.get_session() as session:
            updated_job = session.query(OptimizationJob).filter(
                OptimizationJob.id == job_id
            ).first()
            assert updated_job.status == 'completed'
            assert updated_job.completed_at is not None


# ========================================
# Test Optimal Parameter Selection
# ========================================

class TestOptimalParameterSelection:
    """Test that optimizer selects the best parameters"""

    @pytest.mark.asyncio
    async def test_selects_best_parameters_by_score(self, optimizer, temp_db):
        """Test that optimizer selects parameters with highest score (pnl_pct)"""
        # Create optimization job
        job = OptimizationJob(
            strategy_name='SimpleMAStrategy',
            symbol='BTCUSDT',
            interval='1h',
            start_time=datetime.fromisoformat('2024-01-01T00:00:00'),
            end_time=datetime.fromisoformat('2024-01-05T00:00:00'),
            parameter_ranges={'ma_period': [5, 10, 15]},
            optimization_method='grid',
            status='running'
        )
        job_id = temp_db.create_optimization_job(job)

        # Run optimization
        param_ranges = {'ma_period': [5, 10, 15]}

        best_result = await optimizer.optimize(
            strategy_class=SimpleMAStrategy,
            symbol='BTCUSDT',
            interval='1h',
            start_time='2024-01-01T00:00:00',
            end_time='2024-01-05T00:00:00',
            parameter_ranges=param_ranges,
            optimization_job_id=job_id
        )

        # Verify best result has highest score
        all_results = temp_db.get_optimization_results(job_id)
        best_score = max(r.score for r in all_results)

        assert best_result['optimization_result'].score == best_score

        # Verify best result is returned
        assert 'parameters' in best_result
        assert 'optimization_result' in best_result
        assert 'backtest_result' in best_result

    @pytest.mark.asyncio
    async def test_best_result_matches_database(self, optimizer, temp_db):
        """Test that returned best result matches database best result"""
        # Create optimization job
        job = OptimizationJob(
            strategy_name='SimpleMAStrategy',
            symbol='BTCUSDT',
            interval='1h',
            start_time=datetime.fromisoformat('2024-01-01T00:00:00'),
            end_time=datetime.fromisoformat('2024-01-05T00:00:00'),
            parameter_ranges={'ma_period': [5, 10]},
            optimization_method='grid',
            status='running'
        )
        job_id = temp_db.create_optimization_job(job)

        # Run optimization
        param_ranges = {'ma_period': [5, 10]}

        best_result = await optimizer.optimize(
            strategy_class=SimpleMAStrategy,
            symbol='BTCUSDT',
            interval='1h',
            start_time='2024-01-01T00:00:00',
            end_time='2024-01-05T00:00:00',
            parameter_ranges=param_ranges,
            optimization_job_id=job_id
        )

        # Get best result from database
        db_best = temp_db.get_best_optimization_result(job_id)

        # Verify they match
        assert best_result['optimization_result'].id == db_best.id
        assert best_result['optimization_result'].score == db_best.score


# ========================================
# Test Progress Updates
# ========================================

class TestProgressUpdates:
    """Test progress tracking during optimization"""

    @pytest.mark.asyncio
    async def test_all_combinations_processed(self, optimizer, temp_db):
        """Test that all combinations are processed"""
        # Create optimization job
        job = OptimizationJob(
            strategy_name='SimpleMAStrategy',
            symbol='BTCUSDT',
            interval='1h',
            start_time=datetime.fromisoformat('2024-01-01T00:00:00'),
            end_time=datetime.fromisoformat('2024-01-05T00:00:00'),
            parameter_ranges={'ma_period': [5, 10, 15]},
            optimization_method='grid',
            status='running'
        )
        job_id = temp_db.create_optimization_job(job)

        # Run optimization with 3 combinations
        param_ranges = {'ma_period': [5, 10, 15]}

        await optimizer.optimize(
            strategy_class=SimpleMAStrategy,
            symbol='BTCUSDT',
            interval='1h',
            start_time='2024-01-01T00:00:00',
            end_time='2024-01-05T00:00:00',
            parameter_ranges=param_ranges,
            optimization_job_id=job_id
        )

        # Verify all 3 results saved
        results = temp_db.get_optimization_results(job_id)
        assert len(results) == 3


# ========================================
# Test Edge Cases
# ========================================

class TestEdgeCases:
    """Test edge cases in optimization"""

    @pytest.mark.asyncio
    async def test_single_parameter_combination(self, optimizer, temp_db):
        """Test optimization with single parameter combination"""
        # Create optimization job
        job = OptimizationJob(
            strategy_name='SimpleMAStrategy',
            symbol='BTCUSDT',
            interval='1h',
            start_time=datetime.fromisoformat('2024-01-01T00:00:00'),
            end_time=datetime.fromisoformat('2024-01-05T00:00:00'),
            parameter_ranges={'ma_period': [10]},
            optimization_method='grid',
            status='running'
        )
        job_id = temp_db.create_optimization_job(job)

        # Run optimization with single combination
        param_ranges = {'ma_period': [10]}

        best_result = await optimizer.optimize(
            strategy_class=SimpleMAStrategy,
            symbol='BTCUSDT',
            interval='1h',
            start_time='2024-01-01T00:00:00',
            end_time='2024-01-05T00:00:00',
            parameter_ranges=param_ranges,
            optimization_job_id=job_id
        )

        # Should complete successfully
        assert best_result is not None
        assert best_result['parameters'] == {'ma_period': 10}

        # Should have 1 result
        results = temp_db.get_optimization_results(job_id)
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_no_parameters(self, optimizer, temp_db):
        """Test optimization with no parameters (empty parameter ranges)"""
        # Create optimization job
        job = OptimizationJob(
            strategy_name='NoTradeStrategy',
            symbol='BTCUSDT',
            interval='1h',
            start_time=datetime.fromisoformat('2024-01-01T00:00:00'),
            end_time=datetime.fromisoformat('2024-01-05T00:00:00'),
            parameter_ranges={},
            optimization_method='grid',
            status='running'
        )
        job_id = temp_db.create_optimization_job(job)

        # Run optimization with no parameters
        param_ranges = {}

        best_result = await optimizer.optimize(
            strategy_class=NoTradeStrategy,
            symbol='BTCUSDT',
            interval='1h',
            start_time='2024-01-01T00:00:00',
            end_time='2024-01-05T00:00:00',
            parameter_ranges=param_ranges,
            optimization_job_id=job_id
        )

        # Should complete successfully
        assert best_result is not None

        # Should have 1 result (empty params)
        results = temp_db.get_optimization_results(job_id)
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_strategy_makes_no_trades(self, optimizer, temp_db):
        """Test optimization when strategy makes no trades"""
        # Create optimization job
        job = OptimizationJob(
            strategy_name='NoTradeStrategy',
            symbol='BTCUSDT',
            interval='1h',
            start_time=datetime.fromisoformat('2024-01-01T00:00:00'),
            end_time=datetime.fromisoformat('2024-01-05T00:00:00'),
            parameter_ranges={'dummy_param': [1, 2]},
            optimization_method='grid',
            status='running'
        )
        job_id = temp_db.create_optimization_job(job)

        # Run optimization
        param_ranges = {'dummy_param': [1, 2]}

        best_result = await optimizer.optimize(
            strategy_class=NoTradeStrategy,
            symbol='BTCUSDT',
            interval='1h',
            start_time='2024-01-01T00:00:00',
            end_time='2024-01-05T00:00:00',
            parameter_ranges=param_ranges,
            optimization_job_id=job_id
        )

        # Should complete successfully
        assert best_result is not None

        # All results should have 0 score (no trades = no pnl)
        results = temp_db.get_optimization_results(job_id)
        for result in results:
            assert result.score == 0.0

    @pytest.mark.asyncio
    async def test_many_combinations(self, optimizer, temp_db):
        """Test optimization with many parameter combinations"""
        # Create optimization job
        job = OptimizationJob(
            strategy_name='SimpleMAStrategy',
            symbol='BTCUSDT',
            interval='1h',
            start_time=datetime.fromisoformat('2024-01-01T00:00:00'),
            end_time=datetime.fromisoformat('2024-01-05T00:00:00'),
            parameter_ranges={'ma_period': [5, 10, 15, 20], 'threshold': [0.0, 0.01, 0.02]},
            optimization_method='grid',
            status='running'
        )
        job_id = temp_db.create_optimization_job(job)

        # Run optimization with 4 * 3 = 12 combinations
        param_ranges = {
            'ma_period': [5, 10, 15, 20],
            'threshold': [0.0, 0.01, 0.02]
        }

        best_result = await optimizer.optimize(
            strategy_class=SimpleMAStrategy,
            symbol='BTCUSDT',
            interval='1h',
            start_time='2024-01-01T00:00:00',
            end_time='2024-01-05T00:00:00',
            parameter_ranges=param_ranges,
            optimization_job_id=job_id
        )

        # Should complete successfully
        assert best_result is not None

        # Should have 12 results
        results = temp_db.get_optimization_results(job_id)
        assert len(results) == 12

        # Best result should have highest score
        best_score = max(r.score for r in results)
        assert best_result['optimization_result'].score == best_score


# ========================================
# Test Error Handling
# ========================================

class TestErrorHandling:
    """Test error handling in optimizer"""

    @pytest.mark.asyncio
    async def test_invalid_job_id(self, optimizer, temp_db):
        """Test optimization with invalid job ID"""
        # Try to run with non-existent job ID - this should fail due to FK constraint
        param_ranges = {'ma_period': [10]}

        # Should raise an error (FK constraint or backtest failure)
        with pytest.raises((ValueError, Exception)):
            await optimizer.optimize(
                strategy_class=SimpleMAStrategy,
                symbol='BTCUSDT',
                interval='1h',
                start_time='2024-01-01T00:00:00',
                end_time='2024-01-05T00:00:00',
                parameter_ranges=param_ranges,
                optimization_job_id=9999  # Non-existent
            )

    @pytest.mark.asyncio
    async def test_no_data_for_time_range(self, optimizer, temp_db):
        """Test optimization when no data available"""
        # Create optimization job
        job = OptimizationJob(
            strategy_name='SimpleMAStrategy',
            symbol='BTCUSDT',
            interval='1h',
            start_time=datetime.fromisoformat('2025-01-01T00:00:00'),  # Future date
            end_time=datetime.fromisoformat('2025-01-05T00:00:00'),
            parameter_ranges={'ma_period': [10]},
            optimization_method='grid',
            status='running'
        )
        job_id = temp_db.create_optimization_job(job)

        # Run optimization with future dates (no data)
        param_ranges = {'ma_period': [10]}

        # Should raise ValueError (all backtests fail)
        with pytest.raises(ValueError, match="All backtests failed"):
            await optimizer.optimize(
                strategy_class=SimpleMAStrategy,
                symbol='BTCUSDT',
                interval='1h',
                start_time='2025-01-01T00:00:00',
                end_time='2025-01-05T00:00:00',
                parameter_ranges=param_ranges,
                optimization_job_id=job_id
            )

    @pytest.mark.asyncio
    async def test_optimizer_merges_fixed_parameters(self, optimizer, temp_db):
        """Test that fixed parameters are merged into each combination"""
        # Create optimization job
        job = OptimizationJob(
            strategy_name='SimpleMAStrategy',
            symbol='BTCUSDT',
            interval='1h',
            start_time=datetime.fromisoformat('2024-01-01T00:00:00'),
            end_time=datetime.fromisoformat('2024-01-05T00:00:00'),
            parameter_ranges={'ma_period': [5, 10]},
            optimization_method='grid',
            status='running'
        )
        job_id = temp_db.create_optimization_job(job)

        # Parameter ranges (only ma_period varies)
        parameter_ranges = {
            'ma_period': [5, 10]
        }

        # Fixed parameters (threshold stays at 0.01)
        fixed_parameters = {
            'threshold': 0.01
        }

        # Mock the single backtest to capture parameters
        captured_params = []
        original_run_single = optimizer._run_single_backtest

        async def mock_backtest(*args, params, **kwargs):
            captured_params.append(params)
            return {
                'final_value': 100000,
                'pnl': 0,
                'pnl_pct': 0,
                'total_trades': 0,
                'win_rate': 0,
                'sharpe_ratio': 0,
                'max_drawdown': 0,
                'trades': []
            }

        optimizer._run_single_backtest = mock_backtest

        # Run optimization with fixed_parameters
        await optimizer.optimize(
            strategy_class=SimpleMAStrategy,
            symbol='BTCUSDT',
            interval='1h',
            start_time='2024-01-01T00:00:00',
            end_time='2024-01-05T00:00:00',
            parameter_ranges=parameter_ranges,
            optimization_job_id=job_id,
            fixed_parameters=fixed_parameters
        )

        # Restore original method
        optimizer._run_single_backtest = original_run_single

        # Verify fixed parameters are in each combination
        assert len(captured_params) == 2  # ma_period: 5, 10
        for params in captured_params:
            assert params['threshold'] == 0.01, "threshold should be fixed at 0.01"
            assert params['ma_period'] in [5, 10], "ma_period should vary"
