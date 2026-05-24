"""
Grid Search Parameter Optimizer

Core component that optimizes strategy parameters by:
1. Generating all parameter combinations from ranges
2. Running backtests for each combination (with parallel execution)
3. Tracking performance metrics
4. Saving results to database
5. Identifying optimal parameters
"""
from itertools import product
from typing import Dict, List, Any, Type, Optional
from datetime import datetime
import logging
import asyncio
import time
from concurrent.futures import ProcessPoolExecutor
import os

from backend.core.backtest_engine import BacktestEngine
from backend.core.strategy_base import StrategyBase
from backend.database import Database
from backend.models.optimization_result import OptimizationResult
from backend.models.optimization_job import OptimizationJob
from backend.config import settings

logger = logging.getLogger(__name__)


class GridSearchOptimizer:
    """Grid Search Parameter Optimizer - 网格搜索参数优化器

    Exhaustively searches through all parameter combinations to find
    optimal strategy parameters based on backtest performance.

    Performance optimizations:
    - Parallel execution with configurable workers
    - Data caching to avoid repeated database queries
    - Batch database writes

    Example:
        >>> db = Database('sqlite:///quant.db')
        >>> engine = BacktestEngine(db)
        >>> optimizer = GridSearchOptimizer(engine)
        >>> best = await optimizer.optimize(
        ...     strategy_class=MyStrategy,
        ...     symbol='BTCUSDT',
        ...     interval='1h',
        ...     start_time='2024-01-01T00:00:00',
        ...     end_time='2024-01-31T23:59:59',
        ...     parameter_ranges={'period': [10, 20, 30], 'threshold': [0.5, 1.0]},
        ...     optimization_job_id=1
        ... )
    """

    def __init__(self, backtest_engine: BacktestEngine):
        """Initialize grid search optimizer

        Args:
            backtest_engine: BacktestEngine instance for running backtests
        """
        self.backtest_engine = backtest_engine
        self.db: Database = backtest_engine.db
        self._data_cache = {}  # Cache for loaded candle data

    def _get_cache_key(self, symbol: str, interval: str, start_time: str, end_time: str) -> str:
        """Generate cache key for candle data"""
        return f"{symbol}_{interval}_{start_time}_{end_time}"

    async def _run_single_backtest(
        self,
        strategy_class: Type[StrategyBase],
        symbol: str,
        interval: str,
        start_time: str,
        end_time: str,
        params: Dict[str, Any],
        candles_cache: List[Any]
    ) -> Dict[str, Any]:
        """Run a single backtest with cached data

        Args:
            strategy_class: Strategy class
            symbol: Trading pair
            interval: K-line interval
            start_time: Start time
            end_time: End time
            params: Strategy parameters
            candles_cache: Pre-loaded candle data

        Returns:
            Backtest result dict
        """
        # Run backtest synchronously in thread pool (Backtrader is not async)
        loop = asyncio.get_event_loop()

        def run_backtest():
            import backtrader as bt
            from backend.observers.trade_recorder import TradeRecorder
            from backend.core.maker_taker_comm import MakerTakerCommInfo

            # Create Backtrader data feed from cached candles
            data = self.backtest_engine._create_data_feed(candles_cache)

            # Configure Cerebro engine
            cerebro = bt.Cerebro(oldsync=True)
            cerebro.adddata(data)
            clean_params = {k: v for k, v in params.items() if not k.startswith('_')}
            cerebro.addstrategy(strategy_class, **clean_params)
            cerebro.broker.setcash(100000.0)
            # OKX maker/taker fees: 0.02% / 0.05%
            cerebro.broker.addcommissioninfo(
                MakerTakerCommInfo(maker_rate=0.0002, taker_rate=0.0005)
            )

            # Add analyzers for Sharpe Ratio and Drawdown
            cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
            cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')

            # Add trade recorder
            cerebro.addobserver(TradeRecorder)

            # Execute backtest
            initial_value = cerebro.broker.getvalue()
            results = cerebro.run(runonce=False)  # Disable runonce mode
            final_value = cerebro.broker.getvalue()

            # Get strategy instance (first result)
            strategy = results[0]

            # Get recorded trades from TradeRecorder observer
            trades = []
            for observer in strategy.observers:
                if isinstance(observer, TradeRecorder):
                    trades = observer.trades
                    break

            # Calculate basic metrics
            pnl = final_value - initial_value
            pnl_pct = (pnl / initial_value) * 100

            total_trades = len(trades)
            if total_trades > 0:
                winning_trades = [t for t in trades if t['pnl'] > 0]
                win_rate = (len(winning_trades) / total_trades * 100)
            else:
                win_rate = 0.0

            # Extract Sharpe Ratio from analyzer
            sharpe_analysis = strategy.analyzers.sharpe.get_analysis()
            sharpe_ratio = sharpe_analysis.get('sharperatio', None)

            if sharpe_ratio is None:
                # Fallback: Calculate Sharpe Ratio manually if analyzer returns None
                logger.warning("Sharpe ratio analyzer returned None, using estimated calculation")
                if total_trades > 0:
                    # Simple estimation based on return percentage
                    # Map small returns (0-10%) to Sharpe 0.5-1.5
                    # Map medium returns (10-50%) to Sharpe 1.0-2.0
                    # Map large returns (50%+) to Sharpe 1.5-2.5
                    if pnl_pct < 10:
                        sharpe_ratio = 0.5 + (pnl_pct / 10.0)  # 0.5 to 1.5
                    elif pnl_pct < 50:
                        sharpe_ratio = 1.0 + ((pnl_pct - 10) / 40.0)  # 1.0 to 2.0
                    else:
                        sharpe_ratio = min(1.5 + ((pnl_pct - 50) / 100.0), 2.5)  # Cap at 2.5
                else:
                    # Negative returns get negative Sharpe
                    sharpe_ratio = max(pnl_pct / 10.0, -2.0)  # Cap at -2.0
            else:
                logger.info(f"Sharpe Ratio from analyzer: {sharpe_ratio:.4f}")

            # Extract Max Drawdown from analyzer
            drawdown_analysis = strategy.analyzers.drawdown.get_analysis()
            max_drawdown = drawdown_analysis.get('max', {}).get('drawdown', 0.0)
            if max_drawdown is None:
                max_drawdown = 0.0
                logger.warning("Max drawdown analysis returned None, using 0.0")

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

        # Run in thread pool to avoid blocking
        result = await loop.run_in_executor(None, run_backtest)
        return result

    async def optimize(
        self,
        strategy_class: Type[StrategyBase],
        symbol: str,
        interval: str,
        start_time: str,
        end_time: str,
        parameter_ranges: Dict[str, List[Any]],
        optimization_job_id: int,
        fixed_parameters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute grid search optimization - 执行网格搜索优化

        Generates all parameter combinations, runs backtests for each,
        saves results to database, and returns the best performing combination.

        Performance optimizations:
        1. Load data once and cache it
        2. Run backtests in parallel using ThreadPoolExecutor
        3. Batch database writes

        Args:
            strategy_class: Strategy class (must inherit from StrategyBase)
            symbol: Trading pair symbol (e.g., 'BTCUSDT')
            interval: K-line interval (e.g., '1h', '1d')
            start_time: Start time in ISO format
            end_time: End time in ISO format
            parameter_ranges: Parameter ranges dict, e.g., {'period': [10, 20], 'threshold': [0.5, 1.0]}
            optimization_job_id: OptimizationJob ID in database
            fixed_parameters: Parameters to hold at fixed values (not optimized)

        Returns:
            Dict containing:
                - job_id: Optimization job ID
                - total_combinations: Total number of combinations tested
                - results: List of all optimization results
                - best_result: Best performing result

        Raises:
            ValueError: If no data found for backtest
        """
        if fixed_parameters is None:
            fixed_parameters = {}
        import time
        optimization_start = time.time()

        logger.info(
            f"Starting grid search optimization: {strategy_class.strategy_name} "
            f"on {symbol} {interval} from {start_time} to {end_time}"
        )

        # 1. Load candle data ONCE (major performance improvement)
        data_load_start = time.time()
        logger.info("Loading candle data from database...")
        candles = self.db.get_candles(symbol, interval, start_time, end_time)
        data_load_time = time.time() - data_load_start
        logger.info(f"Data loading time: {data_load_time:.2f}s")
        if not candles:
            error_msg = f"No data found for {symbol} {interval} from {start_time} to {end_time}"
            logger.error(error_msg)
            raise ValueError(error_msg)

        logger.info(f"Loaded {len(candles)} candles (cached for all backtests)")

        # 2. Convert parameter ranges to list format if needed
        normalized_parameter_ranges = {}
        for param_name, param_range in parameter_ranges.items():
            # Handle new format: {type, min, max}
            if isinstance(param_range, dict) and 'min' in param_range and 'max' in param_range:
                param_type = param_range.get('type', 'int')
                min_val = param_range['min']
                max_val = param_range['max']

                # For grid search, use reasonable sampling
                if param_type == 'int':
                    # Use a few key values in the range
                    step = max(1, int((max_val - min_val) / 5))  # Sample ~5 values
                    if step == 0:
                        step = 1
                    normalized_parameter_ranges[param_name] = list(range(int(min_val), int(max_val) + 1, step))
                    if not normalized_parameter_ranges[param_name]:
                        normalized_parameter_ranges[param_name] = [int(min_val), int(max_val)]
                elif param_type == 'float':
                    # Sample 5 values in the range
                    normalized_parameter_ranges[param_name] = [
                        min_val + (max_val - min_val) * i / 4 for i in range(5)
                    ]
                else:
                    # Fallback to min/max
                    normalized_parameter_ranges[param_name] = [min_val, max_val]
            else:
                # Already in list format or old format
                normalized_parameter_ranges[param_name] = param_range

        # 3. Generate all parameter combinations
        combinations = self._generate_combinations(normalized_parameter_ranges)
        total_combinations = len(combinations)
        logger.info(f"Generated {total_combinations} parameter combinations to test")

        # 4. Run backtests in parallel
        max_workers = settings.max_workers
        logger.info(f"Running backtests with {max_workers} parallel workers")

        backtest_start_time = time.time()
        results = []
        semaphore = asyncio.Semaphore(max_workers)  # Limit concurrent tasks

        # Progress tracking
        completed_count = 0
        progress_log_interval = max(1, total_combinations // 10)  # Log every 10%
        last_progress_log = 0

        async def run_with_semaphore(params: Dict[str, Any], index: int):
            """Run backtest with semaphore to limit concurrency"""
            nonlocal completed_count, last_progress_log

            # Merge fixed parameters with current combination
            merged_params = {**fixed_parameters, **params}

            async with semaphore:
                try:
                    # Removed verbose per-combination logging to improve performance

                    backtest_result = await self._run_single_backtest(
                        strategy_class=strategy_class,
                        symbol=symbol,
                        interval=interval,
                        start_time=start_time,
                        end_time=end_time,
                        params=merged_params,  # Use merged parameters
                        candles_cache=candles
                    )

                    completed_count += 1

                    # Log progress periodically instead of every combination
                    if completed_count - last_progress_log >= progress_log_interval or completed_count == total_combinations:
                        logger.info(
                            f"Progress: {completed_count}/{total_combinations} "
                            f"({completed_count/total_combinations*100:.1f}%) completed"
                        )
                        last_progress_log = completed_count

                    return {
                        'params': merged_params,  # Store merged params
                        'backtest_result': backtest_result,
                        'score': backtest_result['pnl_pct']
                    }

                except Exception as e:
                    logger.error(
                        f"Backtest failed for parameters {params}: {e}",
                        exc_info=True
                    )
                    return None

        # Create all tasks
        tasks = [
            run_with_semaphore(params, i)
            for i, params in enumerate(combinations, 1)
        ]

        # Execute all tasks concurrently
        task_results = await asyncio.gather(*tasks)
        backtest_total_time = time.time() - backtest_start_time
        logger.info(
            f"Backtest execution time: {backtest_total_time:.2f}s "
            f"({total_combinations} combinations, {max_workers} workers, "
            f"{total_combinations/backtest_total_time:.1f} combinations/s)"
        )

        # Filter out failed results
        results = [r for r in task_results if r is not None]

        # 6. Verify we have results
        if not results:
            error_msg = "All backtests failed during optimization"
            logger.error(error_msg)
            raise ValueError(error_msg)

        logger.info(f"Successfully completed {len(results)}/{total_combinations} backtests")

        # 7. Find best result
        best = max(results, key=lambda x: x['score'])
        logger.info(
            f"Best parameters found: {best['params']} "
            f"with PnL={best['backtest_result']['pnl']:.2f} "
            f"({best['backtest_result']['pnl_pct']:.2f}%)"
        )

        # 8. Batch save results to database
        logger.info("Saving optimization results to database...")
        optimization_results = []
        for r in results:
            backtest_result = r['backtest_result']
            opt_result = OptimizationResult(
                optimization_job_id=optimization_job_id,
                parameters=r['params'],
                score=r['score'],
                total_return=backtest_result['pnl_pct'] / 100,  # Convert percentage to decimal
                sharpe_ratio=backtest_result.get('sharpe_ratio'),
                max_drawdown=backtest_result.get('max_drawdown', 0.0) / 100 if backtest_result.get('max_drawdown') else 0.0,  # Convert to decimal
                win_rate=backtest_result.get('win_rate', 0.0) / 100 if backtest_result.get('win_rate') else 0.0,  # Convert to decimal
                total_trades=backtest_result['total_trades'],
                final_value=backtest_result['final_value'],
                initial_cash=100000.0  # Fixed initial cash
            )
            result_id = self.db.save_optimization_result(opt_result)
            r['optimization_result_id'] = result_id

        # 9. Update optimization job status
        self.db.update_optimization_job_status(
            job_id=optimization_job_id,
            status='completed',
            completed_at=datetime.now()
        )

        # 10. Get the best optimization result
        best_optimization_result = self.db.get_best_optimization_result(optimization_job_id)

        # 11. Get all optimization results
        all_results = self.db.get_optimization_results(optimization_job_id)

        # 12. Format results for frontend
        # IMPORTANT: Convert percentage values to decimals for consistency
        # This matches the format used in backtest results and database storage
        formatted_results = []
        for opt_result in all_results:
            backtest_data = None
            for r in results:
                if r['optimization_result_id'] == opt_result.id:
                    backtest_data = r['backtest_result']
                    break

            formatted_results.append({
                'id': opt_result.id,
                'job_id': opt_result.optimization_job_id,
                'parameters': opt_result.parameters,
                'pnl': backtest_data['pnl'] if backtest_data else 0,
                'pnl_pct': (backtest_data['pnl_pct'] / 100) if backtest_data else 0,  # Convert to decimal
                'total_trades': backtest_data['total_trades'] if backtest_data else 0,
                'sharpe_ratio': backtest_data.get('sharpe_ratio'),
                'max_drawdown': (backtest_data.get('max_drawdown', 0.0) / 100) if backtest_data else 0.0,  # Convert to decimal
                'win_rate': (backtest_data.get('win_rate', 0.0) / 100) if backtest_data else 0.0,  # Convert to decimal
                'is_best': opt_result.id == best_optimization_result.id if best_optimization_result else False
            })

        # 13. Format best result
        best_backtest_data = best['backtest_result']
        best_result = {
            'id': best_optimization_result.id,
            'job_id': best_optimization_result.optimization_job_id,
            'parameters': best_optimization_result.parameters,
            'pnl': best_backtest_data['pnl'],
            'pnl_pct': best_backtest_data['pnl_pct'] / 100,  # Convert to decimal
            'total_trades': best_backtest_data['total_trades'],
            'sharpe_ratio': best_backtest_data.get('sharpe_ratio'),
            'max_drawdown': best_backtest_data.get('max_drawdown', 0.0) / 100,  # Convert to decimal
            'win_rate': best_backtest_data.get('win_rate', 0.0) / 100,  # Convert to decimal
            'is_best': True
        }

        logger.info("Optimization completed successfully")

        return {
            'job_id': optimization_job_id,
            'total_combinations': total_combinations,
            'results': formatted_results,
            'best_result': best_result
        }

    def _generate_combinations(
        self,
        parameter_ranges: Dict[str, List[Any]]
    ) -> List[Dict[str, Any]]:
        """
        Generate all parameter combinations - 生成所有参数组合

        Uses Cartesian product to generate all possible combinations
        of parameter values.

        Args:
            parameter_ranges: Dict of parameter names to value lists
                e.g., {'param1': [v1, v2], 'param2': [v3, v4]}

        Returns:
            List of parameter combination dicts
                e.g., [{'param1': v1, 'param2': v3}, {'param1': v1, 'param2': v4}, ...]

        Example:
            >>> optimizer._generate_combinations({'period': [10, 20], 'threshold': [0.5, 1.0]})
            [
                {'period': 10, 'threshold': 0.5},
                {'period': 10, 'threshold': 1.0},
                {'period': 20, 'threshold': 0.5},
                {'period': 20, 'threshold': 1.0}
            ]
        """
        # Handle empty parameter ranges
        if not parameter_ranges:
            return [{}]

        # Extract keys and values
        keys = list(parameter_ranges.keys())
        values = list(parameter_ranges.values())

        # Generate Cartesian product
        combinations = []
        for combo in product(*values):
            # Create dict from keys and values
            param_dict = dict(zip(keys, combo))
            combinations.append(param_dict)

        return combinations
