import asyncio
import backtrader as bt
from typing import Dict, Any, Type, List
from backend.core.strategy_base import StrategyBase
from backend.core.maker_taker_comm import MakerTakerCommInfo
from backend.observers.trade_recorder import TradeRecorder


class BacktestRunner:
    """Shared backtest execution logic

    Used by GridSearchOptimizer, BayesianOptimizer, and StabilityAnalyzer
    to avoid code duplication.
    """

    @staticmethod
    async def run_backtest(
        strategy_class: Type[StrategyBase],
        params: Dict[str, Any],
        candles: List[Any],
        create_data_feed_fn,
        initial_cash: float = 100000.0,
        commission: float = None,
        maker_rate: float = 0.0002,
        taker_rate: float = 0.0005
    ) -> Dict[str, Any]:
        """
        Run backtest with given parameters and candles.

        Args:
            strategy_class: Strategy class to instantiate
            params: Strategy parameters
            candles: Candle data list
            create_data_feed_fn: Function to create Backtrader data feed from candles
            initial_cash: Starting portfolio value
            commission: Legacy single commission rate (deprecated)
            maker_rate: Maker (limit order) commission rate
            taker_rate: Taker (market order) commission rate

        Returns:
            Dict with backtest metrics
        """
        # Create data feed using provided function
        data = create_data_feed_fn(candles)

        # Configure Cerebro
        cerebro = bt.Cerebro(oldsync=True)
        cerebro.adddata(data)
        clean_params = {k: v for k, v in params.items() if not k.startswith('_')}
        cerebro.addstrategy(strategy_class, **clean_params)
        cerebro.broker.setcash(initial_cash)
        # Use MakerTakerCommInfo for separate maker/taker rates
        if commission is not None:
            comminfo = MakerTakerCommInfo(maker_rate=commission, taker_rate=commission)
        else:
            comminfo = MakerTakerCommInfo(maker_rate=maker_rate, taker_rate=taker_rate)
        cerebro.broker.addcommissioninfo(comminfo)

        # Add analyzers
        cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
        cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
        cerebro.addobserver(TradeRecorder)

        # Run backtest in thread pool (Backtrader is not async)
        loop = asyncio.get_event_loop()

        def run_backtest():
            initial_value = cerebro.broker.getvalue()
            results = cerebro.run(runonce=False)
            final_value = cerebro.broker.getvalue()

            strategy = results[0]

            # Get trades from observer
            trades = []
            for observer in strategy.observers:
                if isinstance(observer, TradeRecorder):
                    trades = observer.trades
                    break

            # Calculate metrics
            pnl = final_value - initial_value
            pnl_pct = (pnl / initial_value) * 100

            total_trades = len(trades)
            if total_trades > 0:
                winning_trades = [t for t in trades if t['pnl'] > 0]
                win_rate = (len(winning_trades) / total_trades) * 100
            else:
                win_rate = 0.0

            # Extract Sharpe ratio
            sharpe_analysis = strategy.analyzers.sharpe.get_analysis()
            sharpe_ratio = sharpe_analysis.get('sharperatio', None)

            if sharpe_ratio is None:
                # Fallback estimation
                if pnl_pct < 10:
                    sharpe_ratio = 0.5 + (pnl_pct / 10.0)
                elif pnl_pct < 50:
                    sharpe_ratio = 1.0 + ((pnl_pct - 10) / 40.0)
                else:
                    sharpe_ratio = min(1.5 + ((pnl_pct - 50) / 100.0), 2.5)

            # Extract max drawdown
            drawdown_analysis = strategy.analyzers.drawdown.get_analysis()
            max_drawdown = drawdown_analysis.get('max', {}).get('drawdown', 0.0)

            return {
                'final_value': final_value,
                'pnl': pnl,
                'pnl_pct': pnl_pct,
                'total_trades': total_trades,
                'win_rate': win_rate,
                'sharpe_ratio': sharpe_ratio,
                'max_drawdown': max_drawdown,
                'trades': trades
            }

        result = await loop.run_in_executor(None, run_backtest)
        return result
