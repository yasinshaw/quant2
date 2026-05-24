"""
Example SMA Crossover Strategy

A simple moving average crossover strategy for demonstration purposes.
This strategy demonstrates how to create a user-defined strategy that
can be dynamically loaded by the StrategyLoader.
"""
import backtrader as bt
from backend.core.strategy_base import StrategyBase


class SMAStrategy(StrategyBase):
    """
    Simple Moving Average Crossover Strategy

    Buy when price crosses above SMA, sell when crosses below.
    """

    strategy_name = "SMA Crossover"
    strategy_version = "1.0.0"
    strategy_description = "Simple Moving Average crossover strategy"

    # Strategy parameters
    params = (
        ('sma_period', 20),  # SMA period
    )

    def __init__(self):
        """Initialize strategy indicators"""
        super().__init__()
        self.sma = bt.indicators.SimpleMovingAverage(
            self.data.close, period=self.params.sma_period
        )
        self.crossover = bt.indicators.CrossOver(self.data.close, self.sma)

    def next(self):
        """Trading logic - called for each bar"""
        if not self.position:
            if self.crossover > 0:
                self.buy()
        else:
            if self.crossover < 0:
                self.sell()

    @staticmethod
    def get_parameters():
        """Return strategy tunable parameters"""
        return {
            'sma_period': {
                'type': 'int',
                'default': 20,
                'min': 5,
                'max': 100,
                'description': 'Simple Moving Average period'
            }
        }
