"""
Strategy Base Class

All user strategies must inherit from this class.
Provides common functionality and enforces interface compliance.
"""
import backtrader as bt
from abc import ABCMeta, abstractmethod
from typing import Dict, Any


# Create a combined metaclass to resolve conflict between bt.Strategy and ABC
class CombinedMeta(bt.Strategy.__class__, ABCMeta):
    """Combined metaclass for StrategyBase"""
    pass


class StrategyBase(bt.Strategy, metaclass=CombinedMeta):
    """
    Strategy Base Class - All user strategies must inherit from this class

    Users must implement:
    1. __init__(): Initialize indicators
    2. next(): Called for each bar, implement trading logic
    3. get_parameters(): Return strategy tunable parameters definition
    """

    # Strategy metadata (subclasses should override)
    strategy_name: str = "Base Strategy"
    strategy_version: str = "1.0"
    strategy_description: str = "Base strategy class"

    def __init__(self):
        """Initialize strategy"""
        self.order = None
        self.buy_price = None
        self.buy_comm = None

    @abstractmethod
    def next(self):
        """
        Trading logic - called for each bar

        Subclasses must implement this method
        """
        pass

    @staticmethod
    @abstractmethod
    def get_parameters() -> Dict[str, Any]:
        """
        Return strategy tunable parameters definition

        Return format:
        {
            'param_name': {
                'type': 'int' | 'float' | 'str' | 'bool',
                'default': default_value,
                'min': min_value,  # Only for numeric types
                'max': max_value,  # Only for numeric types
                'description': 'Parameter description'
            },
            ...
        }

        Subclasses must implement this method

        Returns:
            Dict containing parameter definitions
        """
        pass

    def notify_order(self, order):
        """
        Order status notification

        Args:
            order: Backtrader order object
        """
        if order.status in [order.Submitted, order.Accepted]:
            # Order submitted/accepted - no action needed
            return

        # Check if order is completed
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(
                    f'BUY EXECUTED, Price: {order.executed.price:.2f}, '
                    f'Cost: {order.executed.value:.2f}, '
                    f'Comm: {order.executed.comm:.2f}'
                )
                self.buy_price = order.executed.price
                self.buy_comm = order.executed.comm
            else:
                self.log(
                    f'SELL EXECUTED, Price: {order.executed.price:.2f}, '
                    f'Cost: {order.executed.value:.2f}, '
                    f'Comm: {order.executed.comm:.2f}'
                )

            # Record bar when order was executed
            self.bar_executed = len(self)

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            # Order failed
            self.log('Order Canceled/Margin/Rejected')

        # Clear order reference
        self.order = None

    def notify_trade(self, trade):
        """
        Trade notification

        Args:
            trade: Backtrader trade object
        """
        # Only notify closed trades
        if not trade.isclosed:
            return

        self.log(
            f'TRADE PROFIT, GROSS: {trade.pnl:.2f}, NET: {trade.pnlcomm:.2f}'
        )

    def log(self, txt: str, dt=None):
        """
        Log output

        Args:
            txt: Log message
            dt: Datetime (defaults to current bar date)
        """
        dt = dt or self.datas[0].datetime.date(0)
        print(f'{dt.isoformat()}, {txt}')
