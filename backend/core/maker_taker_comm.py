"""
Custom Backtrader commission scheme with separate maker/taker rates.

OKX perpetual swap fee schedule (normal user):
  - Maker (limit orders):  0.02% = 0.0002
  - Taker (market orders): 0.05% = 0.0005

Grid strategies:
  - Entries are placed at predefined price levels → limit orders → maker rate
  - SL / TP / time-exit are market orders → taker rate

Thread safety:
  Uses threading.local() so parallel optimizer runs don't interfere.

Usage in strategy:
    from backend.core.maker_taker_comm import MakerTakerCommInfo
    MakerTakerCommInfo.set_order_type(is_maker=True)   # before entry orders
    self.buy(size=size)
    MakerTakerCommInfo.set_order_type(is_maker=False)  # before exit orders
    self.sell(size=size)
"""
import threading

import backtrader as bt


class MakerTakerCommInfo(bt.CommInfoBase):
    """Commission scheme with separate maker and taker rates.

    Thread-safe: each thread gets its own order-type flag via threading.local().
    Strategies toggle the flag before placing orders.
    """

    params = (
        ('maker_rate', 0.0002),   # 0.02% — OKX maker
        ('taker_rate', 0.0005),   # 0.05% — OKX taker
        # CommInfoBase compatibility
        ('commission', 0.0002),
        ('commtype', bt.CommInfoBase.COMM_PERC),
        ('percabs', True),
        ('stocklike', False),
    )

    _local = threading.local()

    @classmethod
    def set_order_type(cls, is_maker: bool):
        """Set whether the next order batch is maker (limit) or taker (market)."""
        cls._local.use_maker = is_maker

    @classmethod
    def is_maker_order(cls) -> bool:
        """Check if the current order should use maker rate."""
        return getattr(cls._local, 'use_maker', True)

    def _getcommission(self, size, price, pseudoexec):
        """Return commission using maker or taker rate depending on flag."""
        rate = self.p.maker_rate if self.is_maker_order() else self.p.taker_rate
        return abs(size) * rate * price
