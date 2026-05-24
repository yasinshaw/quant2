"""
Walk-Forward Validation for Pair Trading Strategies

Rolling-origin backtest: for each window, optimize parameters on the train
period (grid search), then evaluate on the following test period. This avoids
in-sample overfitting and gives a realistic estimate of out-of-sample
performance.

Usage:
    >>> validator = PairWalkForwardValidator(engine)
    >>> result = validator.run(
    ...     strategy_class=BtcEthPair,
    ...     dataset_a_id=24, dataset_b_id=16,
    ...     train_bars=2000, test_bars=500, step_bars=250,
    ...     param_grid={...},
    ... )
"""
from __future__ import annotations

import itertools
import logging
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Dict, List, Type

import numpy as np

from backend.core.pair_backtest_engine import PairBacktestEngine
from backend.core.strategy_base import StrategyBase
from backend.database import Database

logger = logging.getLogger(__name__)


@dataclass
class WindowResult:
    train_start: datetime
    train_end: datetime
    test_start: datetime
    test_end: datetime
    best_params: Dict[str, Any]
    train_score: float  # Sharpe or composite
    test_return_pct: float
    test_sharpe: float
    test_dd_pct: float
    test_trades: int
    test_win_rate: float
    test_profit_factor: float


class PairWalkForwardValidator:
    """Walk-forward validator for pair trading strategies."""

    def __init__(self, engine: PairBacktestEngine):
        self.engine = engine
        self.db: Database = engine.db

    def run(
        self,
        strategy_class: Type[StrategyBase],
        dataset_a_id: int,
        dataset_b_id: int,
        train_bars: int,
        test_bars: int,
        step_bars: int,
        param_grid: Dict[str, List[Any]],
        score_key: str = 'sharpe_ratio',  # 'sharpe_ratio' or 'profit_factor'
        commission: float = 0.0005,
        initial_cash: float = 100000.0,
        verbose: bool = False,
    ) -> Dict[str, Any]:
        """Run walk-forward validation.

        Args:
            strategy_class: Strategy class (BtcEthPair or compatible)
            dataset_a_id: BTC dataset ID
            dataset_b_id: ETH dataset ID
            train_bars: Number of bars in each train window
            test_bars: Number of bars in each test window
            step_bars: Bars to slide between windows (<= test_bars)
            param_grid: Dict of param_name -> list of values to search
            score_key: Metric to optimize ('sharpe_ratio' or 'profit_factor')
            commission: Per-leg commission rate
            initial_cash: Initial cash

        Returns:
            Dict with window_results[] and aggregated metrics.
        """
        # Load full aligned candle timestamps
        timestamps = self._load_aligned_timestamps(dataset_a_id, dataset_b_id)
        n = len(timestamps)
        if n < train_bars + test_bars:
            raise ValueError(
                f"Insufficient data: {n} bars, need {train_bars + test_bars}"
            )

        windows = []
        w_idx = 0
        while True:
            train_end_idx = train_bars + w_idx * step_bars
            test_end_idx = train_end_idx + test_bars
            if test_end_idx > n:
                break
            windows.append((w_idx * step_bars, train_end_idx, test_end_idx))
            w_idx += 1

        if not windows:
            raise ValueError("No valid windows generated")

        logger.info(f"Walk-forward: {len(windows)} windows, train={train_bars}, "
                    f"test={test_bars}, step={step_bars}")

        results: List[WindowResult] = []
        for i, (train_start_idx, train_end_idx, test_end_idx) in enumerate(windows):
            if verbose:
                logger.info(f"Window {i+1}/{len(windows)}: train bars "
                            f"[{train_start_idx}, {train_end_idx}), test bars "
                            f"[{train_end_idx}, {test_end_idx})")

            train_start = timestamps[train_start_idx]
            train_end = timestamps[train_end_idx - 1]
            test_start = timestamps[train_end_idx]
            test_end = timestamps[test_end_idx - 1]

            best_params, best_score = self._grid_search(
                strategy_class, dataset_a_id, dataset_b_id,
                train_start, train_end,
                param_grid, score_key, commission, initial_cash,
            )

            test_res = self.engine.run(
                strategy_class=strategy_class,
                dataset_a_id=dataset_a_id,
                dataset_b_id=dataset_b_id,
                start_time=test_start,
                end_time=test_end,
                parameters=best_params,
                initial_cash=initial_cash,
                commission=commission,
                feed_a_name='BTC',
                feed_b_name='ETH',
            )

            results.append(WindowResult(
                train_start=train_start, train_end=train_end,
                test_start=test_start, test_end=test_end,
                best_params=best_params, train_score=best_score,
                test_return_pct=test_res['pnl_pct'],
                test_sharpe=test_res['sharpe_ratio'],
                test_dd_pct=test_res['max_drawdown'],
                test_trades=test_res['total_trades'],
                test_win_rate=test_res['win_rate'],
                test_profit_factor=test_res['profit_factor'],
            ))
            if verbose:
                logger.info(
                    f"  best params: {best_params}, train {score_key}={best_score:.2f}, "
                    f"test ret={test_res['pnl_pct']:+.1f}% sharpe={test_res['sharpe_ratio']:.2f}"
                )

        return self._aggregate(results, train_bars, test_bars, step_bars)

    def _load_aligned_timestamps(
        self, dataset_a_id: int, dataset_b_id: int
    ) -> List[datetime]:
        """Return sorted list of common timestamps between the two datasets."""
        ds_a = self.db.get_dataset(dataset_a_id)
        ds_b = self.db.get_dataset(dataset_b_id)
        s = max(ds_a.start_time, ds_b.start_time)
        e = min(ds_a.end_time, ds_b.end_time)
        candles_a = self.db.get_candles_by_dataset(dataset_a_id, s, e)
        candles_b = self.db.get_candles_by_dataset(dataset_b_id, s, e)
        ts_a = {c.open_time for c in candles_a}
        ts_b = {c.open_time for c in candles_b}
        return sorted(ts_a & ts_b)

    def _grid_search(
        self,
        strategy_class: Type[StrategyBase],
        dataset_a_id: int,
        dataset_b_id: int,
        start_time: datetime,
        end_time: datetime,
        param_grid: Dict[str, List[Any]],
        score_key: str,
        commission: float,
        initial_cash: float,
    ) -> tuple[Dict[str, Any], float]:
        """Exhaustive grid search over param grid. Returns (best_params, best_score)."""
        keys = list(param_grid.keys())
        values = list(param_grid.values())
        best_score = -np.inf
        best_params = None

        for combo in itertools.product(*values):
            params = dict(zip(keys, combo))
            try:
                res = self.engine.run(
                    strategy_class=strategy_class,
                    dataset_a_id=dataset_a_id,
                    dataset_b_id=dataset_b_id,
                    start_time=start_time,
                    end_time=end_time,
                    parameters=params,
                    initial_cash=initial_cash,
                    commission=commission,
                    feed_a_name='BTC',
                    feed_b_name='ETH',
                )
                score = res.get(score_key, -np.inf)
                if score is None or np.isnan(score):
                    score = -np.inf
                if score > best_score:
                    best_score = score
                    best_params = params
            except Exception as e:
                logger.warning(f"Grid search failed for {params}: {e}")
                continue

        if best_params is None:
            raise RuntimeError("Grid search produced no valid results")
        return best_params, best_score

    def _aggregate(
        self,
        results: List[WindowResult],
        train_bars: int,
        test_bars: int,
        step_bars: int,
    ) -> Dict[str, Any]:
        """Aggregate window results into summary statistics."""
        if not results:
            return {}

        returns = [r.test_return_pct for r in results]
        sharpes = [r.test_sharpe for r in results]
        dds = [r.test_dd_pct for r in results]
        wrs = [r.test_win_rate for r in results]
        pfs = [r.test_profit_factor for r in results]
        trades = [r.test_trades for r in results]

        # Find worst/best windows
        best_idx = int(np.argmax(returns))
        worst_idx = int(np.argmin(returns))

        # Parameter stability: count unique param sets
        param_sets = [frozenset(r.best_params.items()) for r in results]
        unique_params = len(set(param_sets))

        return {
            'n_windows': len(results),
            'train_bars': train_bars,
            'test_bars': test_bars,
            'step_bars': step_bars,
            'windows': [
                {
                    'train_start': r.train_start.isoformat(),
                    'train_end': r.train_end.isoformat(),
                    'test_start': r.test_start.isoformat(),
                    'test_end': r.test_end.isoformat(),
                    'best_params': r.best_params,
                    'train_score': r.train_score,
                    'test_return_pct': r.test_return_pct,
                    'test_sharpe': r.test_sharpe,
                    'test_dd_pct': r.test_dd_pct,
                    'test_trades': r.test_trades,
                    'test_win_rate': r.test_win_rate,
                    'test_profit_factor': r.test_profit_factor,
                }
                for r in results
            ],
            'aggregated': {
                'total_return_pct': sum(returns),
                'mean_return_pct': np.mean(returns),
                'std_return_pct': np.std(returns, ddof=1),
                'median_return_pct': np.median(returns),
                'win_rate_pct': sum(1 for r in returns if r > 0) / len(returns) * 100,
                'mean_sharpe': np.mean(sharpes),
                'median_sharpe': np.median(sharpes),
                'mean_max_dd_pct': np.mean(dds),
                'median_max_dd_pct': np.median(dds),
                'mean_win_rate_pct': np.mean(wrs),
                'mean_profit_factor': np.mean(pfs),
                'total_trades': sum(trades),
                'mean_trades_per_window': np.mean(trades),
                'param_stability': unique_params / len(results),  # higher = more stable
            },
            'best_window': {
                'test_return_pct': results[best_idx].test_return_pct,
                'test_sharpe': results[best_idx].test_sharpe,
                'test_dd_pct': results[best_idx].test_dd_pct,
                'params': results[best_idx].best_params,
                'test_start': results[best_idx].test_start.isoformat(),
                'test_end': results[best_idx].test_end.isoformat(),
            },
            'worst_window': {
                'test_return_pct': results[worst_idx].test_return_pct,
                'test_sharpe': results[worst_idx].test_sharpe,
                'test_dd_pct': results[worst_idx].test_dd_pct,
                'params': results[worst_idx].best_params,
                'test_start': results[worst_idx].test_start.isoformat(),
                'test_end': results[worst_idx].test_end.isoformat(),
            },
        }
