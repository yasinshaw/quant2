"""
Unit tests for TradeRecorder observer

Tests verify:
1. Trade recording for completed trades
2. Data format correctness
3. Multiple trades handling
4. Edge cases (no trades, only buys, only sells)
"""
import pytest
import backtrader as bt
from datetime import datetime
import tempfile
import os
from backend.observers.trade_recorder import TradeRecorder


class SimpleTestStrategy(bt.Strategy):
    """Simple strategy for testing that executes predictable trades"""

    params = (('buy_bar', 5), ('sell_bar', 10))

    def __init__(self):
        self.order = None
        self.bar_count = 0

    def next(self):
        self.bar_count += 1

        if self.order:
            return

        if not self.position:
            if self.bar_count == self.params.buy_bar:
                self.order = self.buy()
        else:
            if self.bar_count == self.params.sell_bar:
                self.order = self.sell()

    def notify_order(self, order):
        """Clear order reference when order is completed"""
        if order.status in [order.Completed]:
            self.order = None


class MultipleTradesStrategy(bt.Strategy):
    """Strategy that executes multiple trades"""

    params = (
        ('trade_bars', [5, 15, 25]),  # Buy bars
        ('sell_bars', [10, 20, 30]),  # Sell bars
    )

    def __init__(self):
        self.order = None
        self.bar_count = 0
        self.trade_index = 0

    def next(self):
        self.bar_count += 1

        if self.order:
            return

        if not self.position:
            # Check if we should buy
            if (
                self.trade_index < len(self.params.trade_bars)
                and self.bar_count == self.params.trade_bars[self.trade_index]
            ):
                self.order = self.buy()
        else:
            # Check if we should sell
            if (
                self.trade_index < len(self.params.sell_bars)
                and self.bar_count == self.params.sell_bars[self.trade_index]
            ):
                self.order = self.sell()
                self.trade_index += 1

    def notify_order(self, order):
        """Clear order reference when order is completed"""
        if order.status in [order.Completed]:
            self.order = None


class NoTradeStrategy(bt.Strategy):
    """Strategy that never executes trades"""

    def next(self):
        pass


class BuyOnlyStrategy(bt.Strategy):
    """Strategy that only buys, never sells"""

    params = (('buy_bar', 5),)

    def __init__(self):
        self.order = None
        self.bar_count = 0

    def next(self):
        self.bar_count += 1

        if self.order:
            return

        if not self.position and self.bar_count == self.params.buy_bar:
            self.order = self.buy()

    def notify_order(self, order):
        """Clear order reference when order is completed"""
        if order.status in [order.Completed]:
            self.order = None


class TestTradeRecorder:
    """Test suite for TradeRecorder observer"""

    def _find_trade_recorder(self, strategy):
        """Helper to find TradeRecorder observer"""
        for obs in strategy.observers:
            if isinstance(obs, TradeRecorder):
                return obs
        return None

    @pytest.fixture
    def cerebro_with_data(self):
        """Create a Cerebro instance with sample data"""
        cerebro = bt.Cerebro()

        # Create a temporary CSV file
        import csv
        from datetime import timedelta

        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            temp_file = f.name
            writer = csv.writer(f)

            # Create 40 bars of data (spanning multiple months)
            base_date = datetime(2020, 1, 1)
            for i in range(40):
                date = base_date + timedelta(days=i)
                date_str = date.strftime('%Y-%m-%d')
                price = 100 + i  # Simple increasing price
                writer.writerow([date_str, price, price, price, price, 0])

        try:
            data = bt.feeds.GenericCSVData(
                dataname=temp_file,
                dtformat=('%Y-%m-%d'),
                openinterest=-1,
            )

            cerebro.adddata(data)
            cerebro.broker.setcash(10000.0)
            cerebro.broker.setcommission(commission=0.001)  # 0.1% commission

            yield cerebro
        finally:
            # Clean up temp file
            if os.path.exists(temp_file):
                os.unlink(temp_file)

    def test_trade_recording(self, cerebro_with_data):
        """Test that trades are recorded correctly"""
        cerebro = cerebro_with_data
        cerebro.addstrategy(SimpleTestStrategy)
        cerebro.addobserver(TradeRecorder)

        # Run backtest
        results = cerebro.run()

        # Get strategy and observer
        strategy = results[0]

        # Find the TradeRecorder observer
        observer = self._find_trade_recorder(strategy)

        assert observer is not None, "TradeRecorder observer should be attached"

        # Verify trades were recorded
        assert len(observer.trades) > 0, "Trades should be recorded"

        # Verify trade has required fields
        trade = observer.trades[0]
        required_fields = [
            'entry_time',
            'exit_time',
            'side',
            'entry_price',
            'exit_price',
            'size',
            'commission',
            'pnl',
        ]

        for field in required_fields:
            assert field in trade, f"Trade should have {field} field"

    def test_data_format(self, cerebro_with_data):
        """Test that data is formatted correctly"""
        cerebro = cerebro_with_data
        cerebro.addstrategy(SimpleTestStrategy)
        cerebro.addobserver(TradeRecorder)

        results = cerebro.run()
        strategy = results[0]
        observer = self._find_trade_recorder(strategy)

        assert observer is not None, "TradeRecorder observer should be attached"

        if len(observer.trades) > 0:
            trade = observer.trades[0]

            # Verify types
            assert isinstance(trade['entry_time'], str), "entry_time should be string"
            assert isinstance(trade['exit_time'], str), "exit_time should be string"
            assert isinstance(trade['side'], str), "side should be string"
            assert isinstance(trade['entry_price'], float), "entry_price should be float"
            assert isinstance(trade['exit_price'], float), "exit_price should be float"
            assert isinstance(trade['size'], (int, float)), "size should be numeric"
            assert isinstance(trade['commission'], float), "commission should be float"
            assert isinstance(trade['pnl'], float), "pnl should be float"

            # Verify side is BUY or SELL
            assert trade['side'] in ['BUY', 'SELL'], "side should be BUY or SELL"

    def test_multiple_trades(self, cerebro_with_data):
        """Test that multiple trades are recorded correctly"""
        cerebro = cerebro_with_data
        cerebro.addstrategy(MultipleTradesStrategy)
        cerebro.addobserver(TradeRecorder)

        results = cerebro.run()
        strategy = results[0]
        observer = self._find_trade_recorder(strategy)

        assert observer is not None, "TradeRecorder observer should be attached"

        # Should have 3 trades
        assert len(observer.trades) == 3, f"Should have 3 trades, got {len(observer.trades)}"

        # Verify trades are in chronological order (by entry_time)
        for i in range(len(observer.trades) - 1):
            assert observer.trades[i]['entry_time'] <= observer.trades[i + 1]['entry_time'], \
                "Trades should be in chronological order"

    def test_no_trades(self, cerebro_with_data):
        """Test observer with strategy that doesn't trade"""
        cerebro = cerebro_with_data
        cerebro.addstrategy(NoTradeStrategy)
        cerebro.addobserver(TradeRecorder)

        results = cerebro.run()
        strategy = results[0]
        observer = self._find_trade_recorder(strategy)

        assert observer is not None, "TradeRecorder observer should be attached"

        # Should have no trades
        assert len(observer.trades) == 0, "Should have no trades"

    def test_only_buy_trades(self, cerebro_with_data):
        """Test observer with strategy that only buys"""
        cerebro = cerebro_with_data
        cerebro.addstrategy(BuyOnlyStrategy)
        cerebro.addobserver(TradeRecorder)

        results = cerebro.run()
        strategy = results[0]
        observer = self._find_trade_recorder(strategy)

        assert observer is not None, "TradeRecorder observer should be attached"

        # Should have no completed trades (position never closed)
        assert len(observer.trades) == 0, "Should have no completed trades"

    def test_trade_has_profit_info(self, cerebro_with_data):
        """Test that trade contains profit information"""
        cerebro = cerebro_with_data
        cerebro.addstrategy(SimpleTestStrategy)
        cerebro.addobserver(TradeRecorder)

        results = cerebro.run()
        strategy = results[0]
        observer = self._find_trade_recorder(strategy)

        assert observer is not None, "TradeRecorder observer should be attached"

        if len(observer.trades) > 0:
            trade = observer.trades[0]

            # PnL should be a number
            assert isinstance(trade['pnl'], (int, float)), "pnl should be numeric"

            # Commission should be positive
            assert trade['commission'] >= 0, "commission should be non-negative"
