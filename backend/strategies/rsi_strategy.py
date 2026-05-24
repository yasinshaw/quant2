"""
RSI Mean Reversion Strategy

A mean reversion strategy based on the Relative Strength Index (RSI).
The RSI measures the speed and magnitude of price movements.
"""
import backtrader as bt
from backend.core.strategy_base import StrategyBase
from typing import Dict, Any


class RSIStrategy(StrategyBase):
    """
    RSI Mean Reversion Strategy

    A mean reversion strategy based on the Relative Strength Index (RSI).
    The RSI measures the speed and magnitude of price movements.

    Trading Logic:
    - Buy when RSI falls below oversold threshold (indicating oversold condition)
    - Sell when RSI rises above overbought threshold (indicating overbought condition)

    Example:
        RSI period: 14, Oversold: 30, Overbought: 70
        If RSI < 30: Generate BUY signal (expecting price to revert up)
        If RSI > 70: Generate SELL signal (expecting price to revert down)
    """

    # Strategy metadata
    strategy_name = "RSI Mean Reversion"
    strategy_version = "1.0.0"
    strategy_description = "Mean reversion strategy using RSI indicator"

    # Strategy parameters
    params = (
        ('rsi_period', 14),  # RSI calculation period
        ('oversold_threshold', 30),  # RSI level to buy
        ('overbought_threshold', 70),  # RSI level to sell
    )

    def __init__(self):
        """Initialize the strategy with RSI indicator."""
        super().__init__()

        # Create RSI indicator
        self.rsi = bt.indicators.RSI(
            self.data.close,
            period=self.params.rsi_period
        )

    def next(self):
        """
        Execute trading logic on each bar.

        Called by Backtrader for each data point.
        """
        # Check if we have enough data for RSI
        if len(self.data) < self.params.rsi_period:
            return

        # Check if we have an open position
        if not self.position:
            # No position - check for buy signal
            if self.rsi[0] < self.params.oversold_threshold:
                self.buy()
                self.log(f'BUY SIGNAL: RSI({self.params.rsi_period}) = {self.rsi[0]:.2f} < {self.params.oversold_threshold}')

        else:
            # Have position - check for sell signal
            if self.rsi[0] > self.params.overbought_threshold:
                self.sell()
                self.log(f'SELL SIGNAL: RSI({self.params.rsi_period}) = {self.rsi[0]:.2f} > {self.params.overbought_threshold}')

    @staticmethod
    def get_parameters() -> Dict[str, Any]:
        """
        Return strategy parameter definitions.

        Returns:
            Dictionary of parameter specifications
        """
        return {
            'rsi_period': {
                'type': 'int',
                'default': 14,
                'min': 1,
                'max': 100,
                'description': 'Period for RSI calculation'
            },
            'oversold_threshold': {
                'type': 'int',
                'default': 30,
                'min': 0,
                'max': 50,
                'description': 'RSI level to generate buy signal (oversold)'
            },
            'overbought_threshold': {
                'type': 'int',
                'default': 70,
                'min': 50,
                'max': 100,
                'description': 'RSI level to generate sell signal (overbought)'
            }
        }
