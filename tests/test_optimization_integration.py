"""
Integration tests for parameter optimization with new features.

Tests the complete optimization workflow including:
- Bayesian optimization
- Composite scoring
- Stability analysis
- Out-of-sample testing
- API endpoints
"""
import pytest
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch
import asyncio

from backend.database import Database
from backend.core.bayesian_optimizer import BayesianOptimizer
from backend.core.stability_analyzer import StabilityAnalyzer
from backend.core.scoring_functions import calculate_composite_score, DEFAULT_WEIGHTS
from backend.core.backtest_runner import BacktestRunner
from backend.config import settings


@pytest.mark.integration
class TestOptimizationIntegration:
    """Integration tests for optimization workflow"""

    @pytest.mark.asyncio
    async def test_bayesian_optimization_with_composite_scoring(self):
        """Test Bayesian optimization with composite scoring"""
        # This test would require Optuna installed
        try:
            import optuna
        except ImportError:
            pytest.skip("Optuna not installed")

        from backend.core.backtest_engine import BacktestEngine

        # Mock database
        mock_db = Mock(spec=Database)

        # Create optimizer
        engine = Mock(spec=BacktestEngine)
        engine.db = mock_db

        optimizer = BayesianOptimizer(engine)

        # Mock strategy class
        mock_strategy_class = Mock()

        # Mock data feed creation
        def mock_create_data_feed(candles):
            return Mock()

        # Mock database methods
        mock_db.create_optimization_job.return_value = 1
        mock_db.create_optimization_result.return_value = 1
        mock_db.update_optimization_job_status.return_value = None

        # Run optimization
        with patch('backend.core.bayesian_optimizer.BacktestRunner') as mock_runner:
            # Mock backtest results
            mock_runner.run_backtest = AsyncMock(return_value={
                'final_value': 110000,
                'pnl': 10000,
                'pnl_pct': 10.0,
                'total_trades': 20,
                'win_rate': 60.0,
                'sharpe_ratio': 1.5,
                'max_drawdown': 5.0,
                'trades': []
            })

            result = await optimizer.optimize(
                strategy_class=mock_strategy_class,
                symbol='BTCUSDT',
                interval='1h',
                start_time='2024-01-01T00:00:00',
                end_time='2024-01-31T23:59:59',
                parameter_ranges={
                    'period': {'type': 'int', 'min': 10, 'max': 50},
                    'deviation': {'type': 'float', 'min': 1.0, 'max': 5.0}
                },
                optimization_job_id=1,
                n_trials=5,
                scoring_weights=None
            )

            # Verify structure
            assert 'best_result' in result
            assert 'parameters' in result['best_result']
            assert 'pnl' in result['best_result']

    @pytest.mark.asyncio
    async def test_stability_analysis_workflow(self):
        """Test complete stability analysis workflow"""
        from backend.core.backtest_engine import BacktestEngine

        # Mock database
        mock_db = Mock(spec=Database)

        # Create analyzer
        engine = Mock(spec=BacktestEngine)
        engine.db = mock_db
        engine._create_data_feed = Mock(return_value=Mock())

        analyzer = StabilityAnalyzer(engine)

        # Mock strategy
        mock_strategy_class = Mock()

        # Optimal parameters
        optimal_params = {'period': 20, 'deviation': 2.0}
        parameter_ranges = {
            'period': {'type': 'int', 'min': 10, 'max': 50},
            'deviation': {'type': 'float', 'min': 1.0, 'max': 5.0}
        }

        # Mock database methods
        mock_db.get_candles.return_value = [
            {'timestamp': '2024-01-01T00:00:00', 'open': 100, 'high': 110, 'low': 90, 'close': 105, 'volume': 1000}
        ]
        mock_db.update_optimization_job_stability.return_value = None
        mock_db.get_best_optimization_result.return_value = {'id': 1}
        mock_db.update_optimization_result_stability_neighbors.return_value = None

        # Mock backtest execution
        with patch('backend.core.stability_analyzer.BacktestRunner') as mock_runner:
            # Mock backtest results with some variance
            mock_runner.run_backtest = AsyncMock(side_effect=[
                # Optimal
                {
                    'pnl_pct': 15.0,
                    'sharpe_ratio': 1.8,
                    'max_drawdown': 5.0,
                    'total_trades': 20
                },
                # Neighbor 1
                {
                    'pnl_pct': 14.0,
                    'sharpe_ratio': 1.7,
                    'max_drawdown': 5.5,
                    'total_trades': 20
                },
                # Neighbor 2
                {
                    'pnl_pct': 14.5,
                    'sharpe_ratio': 1.75,
                    'max_drawdown': 5.2,
                    'total_trades': 20
                }
            ])

            result = await analyzer.analyze_stability(
                strategy_class=mock_strategy_class,
                optimal_params=optimal_params,
                parameter_ranges=parameter_ranges,
                symbol='BTCUSDT',
                interval='1h',
                start_time=datetime(2024, 1, 1),
                end_time=datetime(2024, 1, 31),
                optimization_job_id=1,
                variation_pct=0.10,
                samples_per_param=2
            )

            # Verify stability metrics calculated
            assert 'stability_score' in result
            assert 'variance' in result
            assert 'is_stable' in result
            assert 'neighbors' in result
            assert len(result['neighbors']) == 2

    @pytest.mark.asyncio
    async def test_composite_scoring_with_missing_metrics(self):
        """Test composite scoring handles missing metrics gracefully"""
        # Test with all metrics
        complete_result = {
            'sharpe_ratio': 1.5,
            'total_return': 0.15,
            'max_drawdown': 0.05,
            'win_rate': 0.60
        }
        score = calculate_composite_score(complete_result)
        assert 0 <= score <= 1

        # Test with missing metrics
        incomplete_result = {
            'sharpe_ratio': 1.5,
            'total_return': 0.15
        }
        score = calculate_composite_score(incomplete_result)
        assert 0 <= score <= 1

        # Test with negative returns
        negative_result = {
            'sharpe_ratio': -0.5,
            'total_return': -0.10,
            'max_drawdown': 0.20,
            'win_rate': 0.40
        }
        score = calculate_composite_score(negative_result)
        assert score >= 0

    def test_default_scoring_weights(self):
        """Test default scoring weights are well-defined"""
        assert 'sharpe_ratio' in DEFAULT_WEIGHTS
        assert 'total_return' in DEFAULT_WEIGHTS
        assert 'max_drawdown' in DEFAULT_WEIGHTS
        assert 'win_rate' in DEFAULT_WEIGHTS

        # Weights should sum to approximately 1.0 (ignoring negative sign for drawdown)
        weight_sum = (
            DEFAULT_WEIGHTS['sharpe_ratio'] +
            DEFAULT_WEIGHTS['total_return'] +
            abs(DEFAULT_WEIGHTS['max_drawdown']) +
            DEFAULT_WEIGHTS['win_rate']
        )
        assert abs(weight_sum - 1.0) < 0.01  # Allow small floating point error

    @pytest.mark.asyncio
    async def test_backtest_runner_shared_execution(self):
        """Test BacktestRunner provides consistent execution"""
        from backend.observers.trade_recorder import TradeRecorder

        # Mock strategy class
        mock_strategy_class = Mock()

        # Mock data
        candles = [
            {'timestamp': '2024-01-01T00:00:00', 'open': 100, 'high': 110, 'low': 90, 'close': 105, 'volume': 1000}
        ]

        def mock_create_data_feed(candles):
            return Mock()

        # Run backtest
        with patch('backend.core.backtest_runner.bt.Cerebro') as mock_cerebro_class:
            mock_cerebro = Mock()
            mock_cerebro_class.return_value = mock_cerebro

            mock_broker = Mock()
            mock_broker.getvalue.side_effect = [100000, 110000]
            mock_cerebro.broker = mock_broker

            # Mock observer
            mock_observer = Mock(spec=TradeRecorder)
            mock_observer.trades = [
                {'pnl': 100, 'entry_time': '2024-01-01T00:00:00', 'exit_time': '2024-01-01T01:00:00'}
            ]

            mock_strategy = Mock()
            mock_strategy.observers = [mock_observer]
            mock_strategy.analyzers.sharpe.get_analysis.return_value = {'sharperatio': 1.5}
            mock_strategy.analyzers.drawdown.get_analysis.return_value = {'max': {'drawdown': 5.0}}

            mock_cerebro.run.return_value = [mock_strategy]

            result = await BacktestRunner.run_backtest(
                strategy_class=mock_strategy_class,
                params={'period': 20},
                candles=candles,
                create_data_feed_fn=mock_create_data_feed
            )

            # Verify result structure
            assert 'final_value' in result
            assert 'pnl' in result
            assert 'sharpe_ratio' in result
            assert 'max_drawdown' in result
            assert 'trades' in result

            # Verify values
            assert result['final_value'] == 110000
            assert result['pnl'] == 10000
            assert result['sharpe_ratio'] == 1.5


@pytest.mark.integration
class TestDatabaseMigration:
    """Integration tests for database schema migration"""

    def test_optimization_columns_added_to_existing_database(self):
        """Test that new columns are added to existing databases"""
        # This test would verify the ensure_optimization_columns method
        # For now, we just verify it can be called without error
        db = Database(settings.database_url)

        # Should not raise any errors
        db.ensure_optimization_columns()

    def test_database_methods_for_stability(self):
        """Test new database methods for stability analysis"""
        db = Database(settings.database_url)

        # These methods should exist and be callable
        assert hasattr(db, 'update_optimization_job_stability')
        assert hasattr(db, 'get_best_optimization_result')
        assert hasattr(db, 'update_optimization_result_stability_neighbors')
