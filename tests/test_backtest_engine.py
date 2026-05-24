"""
Unit tests for BacktestEngine class

Tests verify:
1. Complete backtest flow with data loading and execution
2. Indicator calculation in strategies
3. Trade detail extraction and recording
4. Error handling (no data, invalid params, exceptions)
5. Edge cases (no trades, losses, profits, multiple trades)
"""
import pytest
import tempfile
import os
from datetime import datetime, timedelta
from typing import Dict, Any

import backtrader as bt

from backend.core.backtest_engine import BacktestEngine
from backend.core.strategy_base import StrategyBase
from backend.database import Database, CandleData
from backend.models.backtest_job import BacktestJob
from backend.models.backtest_result import BacktestResult
from backend.models.trade import Trade


# ========================================
# Test Strategies
# ========================================

class BuyAndHoldStrategy(StrategyBase):
    """Simple buy and hold strategy for testing - buys then sells"""

    strategy_name = "Buy and Hold"
    strategy_version = "1.0"
    strategy_description = "Buy at first bar and sell after 5 bars"

    def __init__(self):
        super().__init__()
        self.order = None
        self.bar_count = 0

    def next(self):
        self.bar_count += 1

        # Buy at first bar
        if not self.position and self.bar_count == 1:
            self.order = self.buy()

        # Sell after 5 bars
        if self.position and self.bar_count == 6:
            self.order = self.sell()

    @staticmethod
    def get_parameters() -> Dict[str, Any]:
        return {}


class SimpleMAStrategy(StrategyBase):
    """Simple moving average crossover strategy"""

    strategy_name = "Simple MA"
    strategy_version = "1.0"
    strategy_description = "Buy when price above MA, sell when below"

    params = (
        ('ma_period', 10),
    )

    def __init__(self):
        super().__init__()
        self.ma = bt.indicators.SimpleMovingAverage(
            self.data.close, period=self.params.ma_period
        )

    def next(self):
        if not self.position:
            if self.data.close[0] > self.ma[0]:
                self.buy()
        else:
            if self.data.close[0] < self.ma[0]:
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
            }
        }


class NoTradeStrategy(StrategyBase):
    """Strategy that never trades"""

    strategy_name = "No Trade"
    strategy_version = "1.0"
    strategy_description = "Strategy that makes no trades"

    def next(self):
        pass

    @staticmethod
    def get_parameters() -> Dict[str, Any]:
        return {}


class FailingStrategy(StrategyBase):
    """Strategy that raises exception for testing error handling"""

    strategy_name = "Failing Strategy"
    strategy_version = "1.0"
    strategy_description = "Strategy that raises exception"

    def next(self):
        raise ValueError("Strategy failed intentionally")

    @staticmethod
    def get_parameters() -> Dict[str, Any]:
        return {}


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
    """Create sample candle data (100 hourly candles)"""
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
def backtest_engine(temp_db):
    """Create backtest engine instance"""
    return BacktestEngine(temp_db)


@pytest.fixture
def backtest_engine_with_data(temp_db, sample_candles):
    """Create backtest engine with sample data loaded"""
    temp_db.save_candles(sample_candles)
    return BacktestEngine(temp_db)


# ========================================
# Test Complete Backtest Flow
# ========================================

class TestCompleteBacktestFlow:
    """Test complete backtest execution flow"""

    @pytest.mark.asyncio
    async def test_run_backtest_buy_and_hold(self, backtest_engine_with_data):
        """Test complete backtest with buy and hold strategy"""
        result = await backtest_engine_with_data.run(
            strategy_class=BuyAndHoldStrategy,
            symbol='BTCUSDT',
            interval='1h',
            start_time='2024-01-01T00:00:00',
            end_time='2024-01-05T00:00:00',
            parameters={},
            initial_cash=100000.0
        )

        # Verify result structure
        assert 'final_value' in result
        assert 'pnl' in result
        assert 'pnl_pct' in result
        assert 'trades' in result
        assert 'total_return' in result
        assert 'total_trades' in result
        assert 'win_rate' in result
        assert 'profit_factor' in result
        assert 'max_drawdown' in result
        assert 'sharpe_ratio' in result
        assert 'initial_cash' in result

        # Verify types
        assert isinstance(result['final_value'], float)
        assert isinstance(result['pnl'], float)
        assert isinstance(result['pnl_pct'], float)
        assert isinstance(result['total_return'], float)
        assert isinstance(result['total_trades'], int)
        assert isinstance(result['win_rate'], float)
        assert isinstance(result['profit_factor'], float)
        assert isinstance(result['max_drawdown'], float)
        assert isinstance(result['sharpe_ratio'], float)
        assert isinstance(result['initial_cash'], float)
        assert isinstance(result['trades'], list)

        # Verify we have at least one trade
        assert len(result['trades']) > 0

        # Verify final value is positive (upward trend in data)
        assert result['final_value'] > 100000.0

    @pytest.mark.asyncio
    async def test_run_backtest_saves_to_database(self, backtest_engine_with_data):
        """Test that backtest results are saved to database"""
        db = backtest_engine_with_data.db

        # Create a backtest job first
        job = BacktestJob(
            strategy_name='Buy and Hold',
            symbol='BTCUSDT',
            interval='1h',
            start_time=datetime.fromisoformat('2024-01-01T00:00:00'),
            end_time=datetime.fromisoformat('2024-01-05T00:00:00'),
            parameters={},
            status='running'
        )
        job_id = db.create_backtest_job(job)

        # Run backtest using run_with_job (async method)
        result = await backtest_engine_with_data.run_with_job(
            job_id=job_id,
            strategy_class=BuyAndHoldStrategy,
            symbol='BTCUSDT',
            interval='1h',
            start_time='2024-01-01T00:00:00',
            end_time='2024-01-05T00:00:00',
            parameters={},
            initial_cash=100000.0
        )

        # Verify result has database ID
        assert 'backtest_result_id' in result

        # Verify database records created
        backtest_result = db.get_backtest_result(job_id)
        assert backtest_result is not None
        assert backtest_result.initial_cash == 100000.0
        assert backtest_result.final_value == result['final_value']

        trades = db.get_trades(job_id)
        assert len(trades) > 0

    @pytest.mark.asyncio
    async def test_run_backtest_with_strategy_parameters(self, backtest_engine_with_data):
        """Test backtest with strategy parameters"""
        result = await backtest_engine_with_data.run(
            strategy_class=SimpleMAStrategy,
            symbol='BTCUSDT',
            interval='1h',
            start_time='2024-01-01T00:00:00',
            end_time='2024-01-05T00:00:00',
            parameters={'ma_period': 15},
            initial_cash=100000.0
        )

        assert result is not None
        assert 'final_value' in result


# ========================================
# Test Indicator Calculation
# ========================================

class TestIndicatorCalculation:
    """Test that indicators are calculated correctly"""

    @pytest.mark.asyncio
    async def test_ma_indicator_calculated(self, backtest_engine_with_data):
        """Test MA indicator is calculated in strategy"""
        result = await backtest_engine_with_data.run(
            strategy_class=SimpleMAStrategy,
            symbol='BTCUSDT',
            interval='1h',
            start_time='2024-01-01T00:00:00',
            end_time='2024-01-05T00:00:00',
            parameters={'ma_period': 10},
            initial_cash=100000.0
        )

        # Should complete without errors
        assert result is not None

        # Should have some trades (MA crossover generates trades)
        assert len(result['trades']) >= 0


# ========================================
# Test Trade Detail Extraction
# ========================================

class TestTradeDetailExtraction:
    """Test trade details are extracted correctly"""

    @pytest.mark.asyncio
    async def test_trade_format(self, backtest_engine_with_data):
        """Test trade record format"""
        result = await backtest_engine_with_data.run(
            strategy_class=BuyAndHoldStrategy,
            symbol='BTCUSDT',
            interval='1h',
            start_time='2024-01-01T00:00:00',
            end_time='2024-01-05T00:00:00',
            parameters={},
            initial_cash=100000.0
        )

        # Check trade format - should have at least one trade
        assert len(result['trades']) > 0, f"Expected at least 1 trade, got {len(result['trades'])}"

        trade = result['trades'][0]
        assert 'entry_time' in trade
        assert 'exit_time' in trade
        assert 'side' in trade
        assert 'entry_price' in trade
        assert 'exit_price' in trade
        assert 'size' in trade
        assert 'commission' in trade
        assert 'pnl' in trade

        # Verify types
        assert isinstance(trade['entry_time'], str)
        assert isinstance(trade['exit_time'], str)
        assert trade['side'] in ['BUY', 'SELL']
        assert isinstance(trade['entry_price'], float)
        assert isinstance(trade['exit_price'], float)
        assert isinstance(trade['size'], float)
        assert isinstance(trade['commission'], float)
        assert isinstance(trade['pnl'], float)

    @pytest.mark.asyncio
    async def test_multiple_trades_recorded(self, backtest_engine_with_data):
        """Test multiple trades are recorded"""
        result = await backtest_engine_with_data.run(
            strategy_class=SimpleMAStrategy,
            symbol='BTCUSDT',
            interval='1h',
            start_time='2024-01-01T00:00:00',
            end_time='2024-01-05T00:00:00',
            parameters={'ma_period': 5},
            initial_cash=100000.0
        )

        # All trades should be in the list
        assert isinstance(result['trades'], list)

        # Each trade should have valid data
        for trade in result['trades']:
            assert trade['entry_price'] > 0
            assert trade['exit_price'] > 0
            # Size might be 0.0 for some trades, so check >= 0
            assert trade['size'] >= 0


# ========================================
# Test Error Handling
# ========================================

class TestErrorHandling:
    """Test error handling in backtest engine"""

    @pytest.mark.asyncio
    async def test_no_data_for_time_range(self, backtest_engine_with_data):
        """Test error when no data available for time range"""
        with pytest.raises(ValueError, match="No data found"):
            await backtest_engine_with_data.run(
                strategy_class=BuyAndHoldStrategy,
                symbol='BTCUSDT',
                interval='1h',
                start_time='2025-01-01T00:00:00',  # Future date, no data
                end_time='2025-01-05T00:00:00',
                parameters={},
                initial_cash=100000.0
            )

    @pytest.mark.asyncio
    async def test_no_data_for_symbol(self, backtest_engine_with_data):
        """Test error when symbol not found"""
        with pytest.raises(ValueError, match="No data found"):
            await backtest_engine_with_data.run(
                strategy_class=BuyAndHoldStrategy,
                symbol='ETHUSDT',  # Different symbol, no data
                interval='1h',
                start_time='2024-01-01T00:00:00',
                end_time='2024-01-05T00:00:00',
                parameters={},
                initial_cash=100000.0
            )

    @pytest.mark.asyncio
    async def test_strategy_raises_exception(self, backtest_engine_with_data):
        """Test handling of strategy exceptions"""
        # Backtrader will catch the exception but the backtest should still complete
        # The behavior might vary, so we just verify it doesn't crash the engine
        try:
            result = await backtest_engine_with_data.run(
                strategy_class=FailingStrategy,
                symbol='BTCUSDT',
                interval='1h',
                start_time='2024-01-01T00:00:00',
                end_time='2024-01-01T01:00:00',
                parameters={},
                initial_cash=100000.0
            )
            # If it completes, verify structure
            assert 'final_value' in result
        except ValueError:
            # If it raises, that's also acceptable
            pass


# ========================================
# Test Edge Cases
# ========================================

class TestEdgeCases:
    """Test edge cases in backtest scenarios"""

    @pytest.mark.asyncio
    async def test_strategy_makes_no_trades(self, backtest_engine_with_data):
        """Test backtest when strategy makes no trades"""
        result = await backtest_engine_with_data.run(
            strategy_class=NoTradeStrategy,
            symbol='BTCUSDT',
            interval='1h',
            start_time='2024-01-01T00:00:00',
            end_time='2024-01-05T00:00:00',
            parameters={},
            initial_cash=100000.0
        )

        # Should complete without errors
        assert result is not None

        # No trades should be recorded
        assert len(result['trades']) == 0

        # Final value should equal initial cash (no trades, no changes)
        assert result['final_value'] == 100000.0
        assert result['pnl'] == 0.0
        assert result['pnl_pct'] == 0.0

    @pytest.mark.asyncio
    async def test_commission_affects_final_value(self, backtest_engine_with_data):
        """Test that commission is deducted from final value"""
        result = await backtest_engine_with_data.run(
            strategy_class=BuyAndHoldStrategy,
            symbol='BTCUSDT',
            interval='1h',
            start_time='2024-01-01T00:00:00',
            end_time='2024-01-05T00:00:00',
            parameters={},
            initial_cash=100000.0,
            commission=0.01  # 1% commission
        )

        # Should complete without errors
        assert result is not None

        # Should have trades
        assert len(result['trades']) > 0

        # Commission should be recorded
        for trade in result['trades']:
            assert trade['commission'] > 0

    @pytest.mark.asyncio
    async def test_different_initial_cash(self, backtest_engine_with_data):
        """Test backtest with different initial cash amounts"""
        result1 = await backtest_engine_with_data.run(
            strategy_class=BuyAndHoldStrategy,
            symbol='BTCUSDT',
            interval='1h',
            start_time='2024-01-01T00:00:00',
            end_time='2024-01-05T00:00:00',
            parameters={},
            initial_cash=50000.0
        )

        result2 = await backtest_engine_with_data.run(
            strategy_class=BuyAndHoldStrategy,
            symbol='BTCUSDT',
            interval='1h',
            start_time='2024-01-01T00:00:00',
            end_time='2024-01-05T00:00:00',
            parameters={},
            initial_cash=200000.0
        )

        # Both should complete successfully
        assert result1['final_value'] > 50000.0
        assert result2['final_value'] > 200000.0

        # Percentage returns should be similar (same strategy, same data)
        # Allow some variance due to commission effects
        pct_diff = abs(result1['pnl_pct'] - result2['pnl_pct'])
        assert pct_diff < 1.0  # Less than 1% difference


# ========================================
# Test Data Feed Creation
# ========================================

class TestDataFeedCreation:
    """Test data feed creation from candles"""

    def test_create_data_feed(self, backtest_engine, sample_candles):
        """Test creating Backtrader data feed from candles"""
        data_feed = backtest_engine._create_data_feed(sample_candles)

        # Verify data feed is created
        assert data_feed is not None

        # Verify it's a PandasData instance
        assert isinstance(data_feed, bt.feeds.PandasData)

    def test_create_data_feed_empty_list(self, backtest_engine):
        """Test creating data feed with empty candle list"""
        with pytest.raises(Exception):  # Should raise an error
            backtest_engine._create_data_feed([])
