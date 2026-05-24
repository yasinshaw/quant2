"""
Trade Recorder Observer

Records all completed trade details during backtesting for later analysis
and reporting.

Uses order-level tracking (notify_order) instead of Backtrader's Trade objects,
which correctly handles multi-position strategies (e.g. grid trading) where
multiple buys/sells occur before the position reaches zero.

For single-position strategies, the output is identical to the old trade-level
approach. For multi-position strategies, each buy-sell pair produces its own
trade record instead of being merged into a single mega-trade.
"""
import backtrader as bt
from typing import Dict, List
import logging

logger = logging.getLogger(__name__)


class TradeRecorder(bt.Observer):
    """
    Backtrader Observer that records all completed trade details.

    Uses order-level FIFO matching: each completed buy() creates an open lot,
    each completed sell() closes the oldest matching lot(s). This produces
    accurate per-lot trade records for grid and other multi-position strategies.

    The recorded trades can be accessed via the `trades` attribute after
    backtesting completes.

    Trade record format (same as before):
        {
            'entry_time': str (ISO format),
            'exit_time': str (ISO format),
            'side': 'BUY' or 'SELL',
            'entry_price': float,
            'exit_price': float,
            'size': float,
            'commission': float,
            'pnl': float,            # Gross PnL (before commission)
        }

    Example:
        >>> cerebro = bt.Cerebro()
        >>> cerebro.addstrategy(MyStrategy)
        >>> cerebro.addobserver(TradeRecorder)
        >>> results = cerebro.run()
        >>> strategy = results[0]
        >>> observer = strategy.observers[0]  # TradeRecorder
        >>> trades = observer.trades
    """

    lines = ('dummy',)
    params = ()
    plotinfo = dict(plot=False)

    def __init__(self):
        """Initialize the trade recorder with order-level tracking."""
        self.trades: List[Dict] = []
        self._open_lots: List[Dict] = []  # FIFO queue of unmatched buy orders
        self._open_shorts: List[Dict] = []  # FIFO queue of unmatched sell (short) orders

        # Hook into the strategy's notify_order method
        strategy = self._owner
        self._original_notify_order = None
        if hasattr(strategy, 'notify_order'):
            self._original_notify_order = strategy.notify_order

        def notify_order_wrapper(order):
            self._on_order(order)
            if self._original_notify_order:
                self._original_notify_order(order)

        strategy.notify_order = notify_order_wrapper

    def next(self):
        """Called for each bar — required by Backtrader."""
        self.lines.dummy[0] = 0

    def _on_order(self, order):
        """
        Process a completed order — record entry or match with existing entry.

        Args:
            order: Backtrader Order object
        """
        if order.status != bt.Order.Completed:
            return

        data = order.data
        dt = data.num2date(order.executed.dt)
        exec_price = float(order.executed.price)
        exec_size = float(order.executed.size)
        exec_comm = float(order.executed.comm)

        if order.isbuy():
            self._open_lots.append({
                'entry_time': dt,
                'entry_price': exec_price,
                'size': exec_size,
                'commission': exec_comm,
            })
            logger.debug(
                f"BUY order recorded: {exec_size:.6f} @ {exec_price:.2f}, "
                f"comm={exec_comm:.4f}"
            )

        elif order.issell():
            # Match against open buy lots (FIFO)
            # Note: Backtrader reports sell executed.size as NEGATIVE
            close_size_total = abs(exec_size)
            total_comm_ratio = exec_comm / close_size_total if close_size_total > 0 else 0
            remaining = close_size_total

            while remaining > 1e-10 and self._open_lots:
                lot = self._open_lots[0]
                close_size = min(remaining, lot['size'])

                # Pro-rate commissions based on closed size
                lot_comm_part = lot['commission'] * (close_size / lot['size']) if lot['size'] > 0 else 0
                sell_comm_part = total_comm_ratio * close_size
                total_comm = lot_comm_part + sell_comm_part

                # Gross PnL for long: size * (exit - entry)
                pnl = close_size * (exec_price - lot['entry_price'])

                trade_record = {
                    'entry_time': lot['entry_time'].isoformat(),
                    'exit_time': dt.isoformat(),
                    'side': 'BUY',
                    'entry_price': lot['entry_price'],
                    'exit_price': exec_price,
                    'size': close_size,
                    'commission': total_comm,
                    'pnl': pnl,
                }
                self.trades.append(trade_record)

                logger.debug(
                    f"Trade closed: BUY {close_size:.6f} @ "
                    f"{lot['entry_price']:.2f} -> {exec_price:.2f}, "
                    f"PnL=${pnl:.2f}"
                )

                if close_size >= lot['size'] - 1e-10:
                    # Lot fully closed
                    self._open_lots.pop(0)
                else:
                    # Partial close — reduce lot
                    lot['size'] -= close_size
                    lot['commission'] -= lot_comm_part

                remaining -= close_size

            if remaining > 1e-10:
                # No matching buy lot — this is a short entry
                self._open_shorts.append({
                    'entry_time': dt,
                    'entry_price': exec_price,
                    'size': remaining,
                    'commission': exec_comm * (remaining / close_size_total) if close_size_total > 0 else 0,
                })

    # ── Properties for post-backtest access ──────────────────────────

    @property
    def open_lots_remaining(self) -> int:
        """Number of unmatched buy lots remaining (debug helper)."""
        return len(self._open_lots)
