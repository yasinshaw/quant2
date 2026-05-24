"""
Tests for StabilityAnalyzer parameter stability analysis.
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime
from backend.core.stability_analyzer import StabilityAnalyzer


@pytest.mark.asyncio
async def test_stability_analyzer_initialization():
    """Test that StabilityAnalyzer initializes correctly"""
    mock_backtest_engine = Mock()
    analyzer = StabilityAnalyzer(mock_backtest_engine)

    assert analyzer.backtest_engine == mock_backtest_engine


@pytest.mark.asyncio
async def test_generate_variations_int():
    """Test parameter variation generation for int type"""
    mock_backtest_engine = Mock()
    analyzer = StabilityAnalyzer(mock_backtest_engine)

    # Test int parameter variations
    param_config = {
        'type': 'int',
        'min': 5,
        'max': 50
    }

    variations = analyzer._generate_variations(
        optimal_value=20,
        param_type='int',
        param_config=param_config,
        variation_pct=0.10,
        samples=3
    )

    # Should generate variations around 20
    assert len(variations) > 0
    assert all(isinstance(v, int) for v in variations)
    assert all(5 <= v <= 50 for v in variations)


@pytest.mark.asyncio
async def test_generate_variations_float():
    """Test parameter variation generation for float type"""
    mock_backtest_engine = Mock()
    analyzer = StabilityAnalyzer(mock_backtest_engine)

    # Test float parameter variations
    param_config = {
        'type': 'float',
        'min': 0.01,
        'max': 0.1
    }

    variations = analyzer._generate_variations(
        optimal_value=0.02,
        param_type='float',
        param_config=param_config,
        variation_pct=0.10,
        samples=3
    )

    # Should generate variations around 0.02
    assert len(variations) > 0
    assert all(isinstance(v, float) for v in variations)
    assert all(0.01 <= v <= 0.1 for v in variations)


@pytest.mark.asyncio
async def test_generate_variations_choice():
    """Test parameter variation generation for choice type"""
    mock_backtest_engine = Mock()
    analyzer = StabilityAnalyzer(mock_backtest_engine)

    # Test choice parameter variations
    param_config = {
        'type': 'choice',
        'options': ['sma', 'ema', 'macd']
    }

    variations = analyzer._generate_variations(
        optimal_value='sma',
        param_type='choice',
        param_config=param_config,
        variation_pct=0.10,
        samples=3
    )

    # Should return non-optimal choices
    assert 'sma' not in variations
    assert set(variations).issubset({'ema', 'macd'})


@pytest.mark.asyncio
async def test_calculate_stability_metrics():
    """Test stability metrics calculation"""
    mock_backtest_engine = Mock()
    analyzer = StabilityAnalyzer(mock_backtest_engine)

    # Test with stable neighbors (low variance, close to optimal)
    neighbor_results = [
        {'score': 0.85, 'pnl_pct': 15, 'sharpe_ratio': 1.8, 'max_drawdown': 5},
        {'score': 0.82, 'pnl_pct': 14, 'sharpe_ratio': 1.7, 'max_drawdown': 6},
        {'score': 0.87, 'pnl_pct': 16, 'sharpe_ratio': 1.9, 'max_drawdown': 5}
    ]

    metrics = analyzer._calculate_stability_metrics(
        optimal_score=0.90,
        neighbor_results=neighbor_results
    )

    # Should have high stability score
    assert metrics['stability_score'] > 0.7
    assert metrics['is_stable'] == True
    assert metrics['variance'] < 0.1
    assert metrics['optimal_score'] == 0.90
    assert 'neighbors' in metrics

    # Test with unstable neighbors (high variance, far from optimal)
    unstable_neighbors = [
        {'score': 0.3, 'pnl_pct': 2, 'sharpe_ratio': 0.5, 'max_drawdown': 20},
        {'score': 0.4, 'pnl_pct': 3, 'sharpe_ratio': 0.6, 'max_drawdown': 18}
    ]

    unstable_metrics = analyzer._calculate_stability_metrics(
        optimal_score=0.90,
        neighbor_results=unstable_neighbors
    )

    # Should have low stability score
    assert unstable_metrics['stability_score'] < 0.5
    assert unstable_metrics['is_stable'] == False
    assert unstable_metrics['variance'] > 0


@pytest.mark.asyncio
async def test_calculate_stability_metrics_empty_neighbors():
    """Test stability metrics with no neighbor results"""
    mock_backtest_engine = Mock()
    analyzer = StabilityAnalyzer(mock_backtest_engine)

    metrics = analyzer._calculate_stability_metrics(
        optimal_score=0.90,
        neighbor_results=[]
    )

    # Should return default unstable metrics
    assert metrics['stability_score'] == 0.0
    assert metrics['variance'] == 0.0
    assert metrics['is_stable'] == False
    assert metrics['neighbors'] == []


@pytest.mark.asyncio
async def test_analyze_stability_integration():
    """Test full stability analysis flow"""
    mock_backtest_engine = Mock()

    # Mock data feed creation
    mock_backtest_engine._create_data_feed = Mock(return_value=Mock())

    analyzer = StabilityAnalyzer(mock_backtest_engine)

    # Mock strategy and parameters
    mock_strategy_class = Mock()
    optimal_params = {'period': 20, 'deviation': 2.0}
    parameter_ranges = {
        'period': {'type': 'int', 'min': 5, 'max': 50},
        'deviation': {'type': 'float', 'min': 1.0, 'max': 5.0}
    }

    # Mock database and candles
    with patch('backend.database.Database') as mock_db_class:
        mock_db = Mock()
        mock_db_class.return_value = mock_db

        mock_db.get_candles.return_value = [
            {'timestamp': '2024-01-01T00:00:00', 'open': 100, 'high': 110, 'low': 90, 'close': 105, 'volume': 1000}
        ]

        # Mock backtest execution
        with patch('backend.core.stability_analyzer.BacktestRunner') as mock_runner:
            mock_runner.run_backtest = AsyncMock(side_effect=[
                # Optimal params
                {
                    'pnl_pct': 20.0,
                    'sharpe_ratio': 2.0,
                    'max_drawdown': 5.0,
                    'total_trades': 10
                },
                # Neighbor 1
                {
                    'pnl_pct': 18.0,
                    'sharpe_ratio': 1.9,
                    'max_drawdown': 6.0,
                    'total_trades': 10
                },
                # Neighbor 2
                {
                    'pnl_pct': 19.0,
                    'sharpe_ratio': 1.95,
                    'max_drawdown': 5.5,
                    'total_trades': 10
                }
            ])

            # Mock database methods
            mock_db.update_optimization_job_stability = Mock()
            mock_db.get_best_optimization_result = Mock(return_value={'id': 123})
            mock_db.update_optimization_result_stability_neighbors = Mock()

            # Run analysis
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

            # Verify structure
            assert 'stability_score' in result
            assert 'variance' in result
            assert 'neighbors' in result
            assert 'is_stable' in result

            # Verify database was updated
            mock_db.update_optimization_job_stability.assert_called_once()
            mock_db.update_optimization_result_stability_neighbors.assert_called_once()
