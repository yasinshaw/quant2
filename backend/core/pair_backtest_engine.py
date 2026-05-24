"""
Pair Backtest Engine

Minimal dual-feed backtest engine for pair trading strategies
(e.g., BTC-ETH statistical arbitrage).

Keeps single-feed `BacktestEngine` untouched. Loads two datasets from DB,
inner-joins on timestamp, feeds both into Backtrader's Cerebro.

Conventions:
- `datas[0]` = feed_a (the "quote leg", e.g. BTC)
- `datas[1]` = feed_b (the "base leg", e.g. ETH)
- Strategies receive parameters via `cerebro.addstrategy(cls, **params)`
"""
import backtrader as bt
import pandas as pd
from datetime import datetime
from typing import Any, Dict, List, Optional, Type
import logging

from backend.core.strategy_base import StrategyBase
from backend.database import Database
from backend.observers.trade_recorder import TradeRecorder

logger = logging.getLogger(__name__)


class PairBacktestEngine:
    """Two-feed backtest engine for pair / statistical arbitrage strategies."""

    def __init__(self, db: Database):
        self.db = db

    def run(
        self,
        strategy_class: Type[StrategyBase],
        dataset_a_id: int,
        dataset_b_id: int,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        parameters: Optional[Dict[str, Any]] = None,
        initial_cash: float = 100000.0,
        commission: float = 0.001,
        feed_a_name: str = 'A',
        feed_b_name: str = 'B',
    ) -> Dict[str, Any]:
        parameters = parameters or {}

        ds_a = self.db.get_dataset(dataset_a_id)
        ds_b = self.db.get_dataset(dataset_b_id)

        # Resolve time bounds (intersection)
        eff_start = max(
            start_time or ds_a.start_time,
            ds_a.start_time,
            ds_b.start_time,
        )
        eff_end = min(
            end_time or ds_a.end_time,
            ds_a.end_time,
            ds_b.end_time,
        )
        if eff_start >= eff_end:
            raise ValueError(
                f"Empty intersection: {eff_start} >= {eff_end}"
            )

        candles_a = self.db.get_candles_by_dataset(
            dataset_id=dataset_a_id,
            start_time=eff_start,
            end_time=eff_end,
        )
        candles_b = self.db.get_candles_by_dataset(
            dataset_id=dataset_b_id,
            start_time=eff_start,
            end_time=eff_end,
        )
        if not candles_a or not candles_b:
            raise ValueError(
                f"Missing candles (a={len(candles_a)}, b={len(candles_b)})"
            )

        df_a, df_b = self._align_and_frame(candles_a, candles_b)
        if len(df_a) == 0:
            raise ValueError("No overlapping candles between the two datasets")

        logger.info(
            f"Pair backtest: {ds_a.symbol}/{ds_b.symbol} "
            f"aligned bars={len(df_a)} "
            f"({df_a.index[0]} → {df_a.index[-1]})"
        )

        cerebro = bt.Cerebro(oldsync=True, tradehistory=True)
        feed_a = bt.feeds.PandasData(dataname=df_a, openinterest=-1)
        feed_b = bt.feeds.PandasData(dataname=df_b, openinterest=-1)
        cerebro.adddata(feed_a, name=feed_a_name)
        cerebro.adddata(feed_b, name=feed_b_name)

        clean_params = {
            k: v for k, v in parameters.items() if not k.startswith('_')
        }
        cerebro.addstrategy(strategy_class, **clean_params)

        cerebro.broker.setcash(initial_cash)
        cerebro.broker.setcommission(commission=commission)

        cerebro.addobserver(TradeRecorder)
        cerebro.addanalyzer(
            bt.analyzers.SharpeRatio,
            _name='sharpe',
            timeframe=bt.TimeFrame.Days,
            annualize=True,
            riskfreerate=0.0,
        )
        cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')

        initial_value = cerebro.broker.getvalue()
        results = cerebro.run(runonce=False)
        final_value = cerebro.broker.getvalue()
        strategy = results[0]

        trades: List[Dict[str, Any]] = []
        for obs in strategy.observers:
            if isinstance(obs, TradeRecorder):
                trades = obs.trades
                break

        sharpe = strategy.analyzers.sharpe.get_analysis().get('sharperatio', 0.0)
        sharpe = 0.0 if sharpe is None else sharpe
        dd = strategy.analyzers.drawdown.get_analysis().get('max', {}).get('drawdown', 0.0)
        dd = 0.0 if dd is None else dd

        pnl = final_value - initial_value
        total_trades = len(trades)
        wins = [t for t in trades if t['pnl'] > 0]
        win_rate = (len(wins) / total_trades * 100) if total_trades else 0.0
        gross_profit = sum(t['pnl'] for t in trades if t['pnl'] > 0)
        gross_loss = abs(sum(t['pnl'] for t in trades if t['pnl'] < 0))
        profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else 0.0

        return {
            'initial_cash': initial_value,
            'final_value': final_value,
            'pnl': pnl,
            'pnl_pct': pnl / initial_value * 100,
            'sharpe_ratio': sharpe,
            'max_drawdown': dd,
            'total_trades': total_trades,
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'trades': trades,
            'bars': len(df_a),
            'start_time': df_a.index[0].isoformat(),
            'end_time': df_a.index[-1].isoformat(),
            'dataset_a': {
                'id': ds_a.id, 'symbol': ds_a.symbol, 'interval': ds_a.interval,
            },
            'dataset_b': {
                'id': ds_b.id, 'symbol': ds_b.symbol, 'interval': ds_b.interval,
            },
        }

    def _align_and_frame(
        self, candles_a: List, candles_b: List
    ) -> tuple[pd.DataFrame, pd.DataFrame]:
        """Inner-join two candle lists on open_time. Returns two DataFrames
        sharing identical indices (so Backtrader stays in sync bar-by-bar)."""
        df_a = self._to_frame(candles_a)
        df_b = self._to_frame(candles_b)
        common = df_a.index.intersection(df_b.index)
        return df_a.loc[common].sort_index(), df_b.loc[common].sort_index()

    @staticmethod
    def _to_frame(candles: List) -> pd.DataFrame:
        df = pd.DataFrame([
            {
                'datetime': c.open_time,
                'open': c.open_price,
                'high': c.high_price,
                'low': c.low_price,
                'close': c.close_price,
                'volume': c.volume,
            }
            for c in candles
        ])
        df.set_index('datetime', inplace=True)
        return df
