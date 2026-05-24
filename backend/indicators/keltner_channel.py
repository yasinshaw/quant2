"""
Keltner Channel Indicator for Backtrader.

ATR-based envelope around an EMA midpoint.
Preferred over Bollinger Bands for trend following because
ATR expands more smoothly than standard deviation.

Lines:
  mid:   EMA of close price
  upper: mid + mult * ATR
  lower: mid - mult * ATR
"""
import backtrader as bt


class KeltnerChannel(bt.Indicator):
    """
    Keltner Channel

    Params:
      period:     EMA period (midline)
      mult:       ATR multiplier (channel width)
      atr_period: ATR calculation period
    """
    lines = ('mid', 'upper', 'lower')
    params = (
        ('period', 20),
        ('mult', 2.0),
        ('atr_period', 10),
    )
    plotinfo = dict(subplot=False)
    plotlines = dict(
        mid=dict(name='KC Mid', color='blue'),
        upper=dict(name='KC Upper', color='red'),
        lower=dict(name='KC Lower', color='green'),
    )

    def __init__(self):
        self.lines.mid = bt.indicators.EMA(
            self.data.close, period=self.params.period
        )
        atr = bt.indicators.ATR(self.data, period=self.params.atr_period)
        self.lines.upper = self.lines.mid + self.params.mult * atr
        self.lines.lower = self.lines.mid - self.params.mult * atr
