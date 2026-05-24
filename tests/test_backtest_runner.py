"""
Tests for BacktestRunner shared execution logic.
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from backend.core.backtest_runner import BacktestRunner
from backend.observers.trade_recorder import TradeRecorder


@pytest.mark.asyncio
async def test_backtest_runner_execution():
    """Test that BacktestRunner executes backtest and returns metrics"""
    # Mock strategy class
    mock_strategy_class = Mock()

    # Mock parameters
    params = {'param1': 10, 'param2': 20}

    # Mock candles
    candles = [
        {'timestamp': '2024-01-01T00:00:00', 'open': 100, 'high': 110, 'low': 90, 'close': 105, 'volume': 1000},
        {'timestamp': '2024-01-01T01:00:00', 'open': 105, 'high': 115, 'low': 100, 'close': 110, 'volume': 1200}
    ]

    # Mock data feed creation function
    def mock_create_data_feed(candles):
        return Mock()

    # Mock Backtrader execution
    with patch('backend.core.backtest_runner.bt.Cerebro') as mock_cerebro_class:
        # Configure mock cerebro instance
        mock_cerebro = Mock()
        mock_cerebro_class.return_value = mock_cerebro

        # Mock broker
        mock_broker = Mock()
        mock_broker.getvalue.side_effect = [100000, 110000]  # initial, final
        mock_cerebro.broker = mock_broker

        # Mock strategy result
        mock_strategy = Mock()

        # Mock TradeRecorder observer with trades
        mock_observer = Mock(spec=TradeRecorder)
        mock_observer.trades = [
            {'pnl': 100, 'entry_time': '2024-01-01T00:00:00', 'exit_time': '2024-01-01T01:00:00'}
        ]
        mock_strategy.observers = [mock_observer]

        # Mock analyzers
        mock_sharpe_analyzer = Mock()
        mock_sharpe_analyzer.get_analysis.return_value = {'sharperatio': 1.5}

        mock_drawdown_analyzer = Mock()
        mock_drawdown_analyzer.get_analysis.return_value = {'max': {'drawdown': 5.0}}

        mock_strategy.analyzers.sharpe = mock_sharpe_analyzer
        mock_strategy.analyzers.drawdown = mock_drawdown_analyzer

        # Mock cerebro.run to return strategy
        mock_cerebro.run.return_value = [mock_strategy]

        # Execute backtest
        result = await BacktestRunner.run_backtest(
            strategy_class=mock_strategy_class,
            params=params,
            candles=candles,
            create_data_feed_fn=mock_create_data_feed,
            initial_cash=100000.0,
            commission=0.001
        )

        # Verify cerebro was configured correctly
        mock_cerebro_class.assert_called_once_with(oldsync=True)
        mock_cerebro.adddata.assert_called_once()
        mock_cerebro.addstrategy.assert_called_once_with(mock_strategy_class, **params)
        mock_cerebro.broker.setcash.assert_called_once_with(100000.0)
        mock_cerebro.broker.setcommission.assert_called_once_with(commission=0.001)
        mock_cerebro.addanalyzer.assert_called()
        mock_cerebro.addobserver.assert_called_once()

        # Verify result structure
        assert 'final_value' in result
        assert 'pnl' in result
        assert 'pnl_pct' in result
        assert 'total_trades' in result
        assert 'win_rate' in result
        assert 'sharpe_ratio' in result
        assert 'max_drawdown' in result
        assert 'trades' in result

        # Verify calculated values
        assert result['final_value'] == 110000
        assert result['pnl'] == 10000
        assert result['pnl_pct'] == 10.0
        assert result['total_trades'] == 1
        assert result['win_rate'] == 100.0
        assert result['sharpe_ratio'] == 1.5
        assert result['max_drawdown'] == 5.0
        assert len(result['trades']) == 1
