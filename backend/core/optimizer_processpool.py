"""
ProcessPool-based Optimizer

Uses multiprocessing.Pool for true parallel execution.
"""

import asyncio
import time
import logging
from concurrent.futures import ProcessPoolExecutor
from typing import Dict, List, Any, Type
import multiprocessing

logger = logging.getLogger(__name__)


def run_backtest_process(
    strategy_module: str,
    strategy_class_name: str,
    params: Dict[str, Any],
    candles_list: list,
) -> Dict[str, Any]:
    """
    Run backtest in a separate process.

    Args:
        strategy_module: Full module path to strategy
        strategy_class_name: Name of strategy class
        params: Strategy parameters
        candles_list: List of candle dicts

    Returns:
        Backtest result dict
    """
    # Import strategy dynamically
    import importlib
    module = importlib.import_module(strategy_module)
    strategy_class = getattr(module, strategy_class_name)

    # Run backtest
    import backtrader as bt

    # Create data feed
    data = _create_data_feed(candles_list)

    # Configure Cerebro
    cerebro = bt.Cerebro(oldsync=True)
    cerebro.adddata(data)
    clean_params = {k: v for k, v in params.items() if not k.startswith('_')}
    cerebro.addstrategy(strategy_class, **clean_params)
    cerebro.broker.setcash(100000.0)
    cerebro.broker.setcommission(commission=0.001)

    # Add observer
    from backend.observers.trade_recorder import TradeRecorder
    cerebro.addobserver(TradeRecorder)

    # Run backtest
    initial_value = cerebro.broker.getvalue()
    results = cerebro.run(runonce=False)
    final_value = cerebro.broker.getvalue()

    # Get trades
    strategy = results[0]
    trades = []
    for obs in strategy.observers:
        if isinstance(obs, TradeRecorder):
            trades = obs.trades
            break

    # Calculate metrics
    pnl = final_value - initial_value
    pnl_pct = (pnl / initial_value) * 100

    return {
        'pnl': pnl,
        'pnl_pct': pnl_pct,
        'total_trades': len(trades),
        'win_rate': sum(1 for t in trades if t['pnl'] > 0) / len(trades) * 100 if trades else 0.0,
        'trades': trades
    }


