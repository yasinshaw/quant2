"""
Custom On Balance Volume (OBV) indicator for Backtrader.

Backtrader does not include a built-in OBV indicator, so we implement it here.

OBV Formula:
  if close > prev_close: obv += volume
  if close < prev_close: obv -= volume
  if close == prev_close: obv unchanged

Usage:
  obv = OBV(self.data)
  obv_ma = bt.indicators.SMA(obv, period=20)
"""
import backtrader as bt


class OBV(bt.Indicator):
    """
    On Balance Volume (OBV)

    Measures buying/selling pressure by accumulating volume:
    - Volume added when price closes up (accumulation)
    - Volume subtracted when price closes down (distribution)
    - Unchanged when price closes flat

    Lines:
      obv: cumulative volume line
    """
    lines = ('obv',)
    params = ()
    plotinfo = dict(subplot=True)
    plotlines = dict(obv=dict(name='OBV', color='blue'))

    def __init__(self):
        super().__init__()

    def nextstart(self):
        """First bar: OBV starts at 0"""
        self.lines.obv[0] = 0

    def next(self):
        """Calculate OBV for each bar"""
        close = self.data.close[0]
        prev_close = self.data.close[-1]
        volume = self.data.volume[0]

        if close > prev_close:
            self.lines.obv[0] = self.lines.obv[-1] + volume
        elif close < prev_close:
            self.lines.obv[0] = self.lines.obv[-1] - volume
        else:
            self.lines.obv[0] = self.lines.obv[-1]

    def oncestart(self, start, end):
        """First bar initialization for batch mode"""
        self.lines.obv[start] = 0

    def once(self, start, end):
        """Batch calculation for performance"""
        oline = self.lines.obv
        cline = self.data.close
        vline = self.data.volume

        oline[start] = 0

        for i in range(start + 1, end):
            if cline[i] > cline[i - 1]:
                oline[i] = oline[i - 1] + vline[i]
            elif cline[i] < cline[i - 1]:
                oline[i] = oline[i - 1] - vline[i]
            else:
                oline[i] = oline[i - 1]
