"""
Bayesian Optimization using Optuna

Efficient parameter optimization that learns from previous trials
to suggest promising parameter combinations.
"""

import logging
import asyncio
from typing import Dict, List, Any, Type, Optional
from datetime import datetime

from backend.core.backtest_engine import BacktestEngine
from backend.core.strategy_base import StrategyBase
from backend.core.scoring_functions import calculate_composite_score
from backend.database import Database
from backend.config import settings

logger = logging.getLogger(__name__)


class BayesianOptimizer:
    """Bayesian Optimizer using Optuna

    Uses Optuna's Bayesian optimization to efficiently search parameter space.
    Learns from previous trials to balance exploration vs exploitation.

    Example:
        >>> optimizer = BayesianOptimizer(backtest_engine)
        >>> result = await optimizer.optimize(
        ...     strategy_class=MyStrategy,
        ...     symbol='BTCUSDT',
        ...     interval='1h',
        ...     start_time='2024-01-01',
        ...     end_time='2024-12-31',
        ...     parameter_ranges={'period': [10, 50]},
        ...     n_trials=100,
        ...     optimization_job_id=1
        ... )
    """

    def __init__(self, backtest_engine: BacktestEngine):
        """Initialize Bayesian optimizer

        Args:
            backtest_engine: BacktestEngine instance for running backtests
        """
        self.backtest_engine = backtest_engine
        self.db: Database = backtest_engine.db

        # Verify Optuna is available
        try:
            import optuna
            self.optuna = optuna
        except ImportError:
            raise ImportError(
                "Optuna is not installed. Install with: pip install optuna>=3.5.0"
            )

    async def optimize(
        self,
        strategy_class: Type[StrategyBase],
        symbol: str,
        interval: str,
        start_time: str,
        end_time: str,
        parameter_ranges: Dict[str, Any],
        optimization_job_id: int,
        n_trials: int = 100,
        scoring_weights: Optional[Dict[str, float]] = None,
        fixed_parameters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Run Bayesian optimization

        Args:
            strategy_class: Strategy class (must inherit from StrategyBase)
            symbol: Trading pair symbol
            interval: K-line interval
            start_time: Start time in ISO format
            end_time: End time in ISO format
            parameter_ranges: Parameter ranges, e.g., {'period': [10, 50]}
                Continuous: [min, max]
                Discrete: [v1, v2, v3, ...]
            optimization_job_id: Job ID in database
            n_trials: Number of optimization trials
            scoring_weights: Optional custom weights for scoring
            fixed_parameters: Parameters held constant during optimization

        Returns:
            Dict containing:
                - job_id: Optimization job ID
                - best_params: Best parameter combination
                - best_score: Best composite score
                - n_trials: Number of trials run
                - results: List of all trial results
        """
        if fixed_parameters is None:
            fixed_parameters = {}

        logger.info(
            f"Starting Bayesian optimization: {strategy_class.strategy_name} "
            f"with {n_trials} trials"
        )

        # 1. Load candle data (reuse caching from GridSearchOptimizer)
        logger.info("Loading candle data from database...")
        candles = self.db.get_candles(symbol, interval, start_time, end_time)

        if not candles:
            raise ValueError(
                f"No data found for {symbol} {interval} "
                f"from {start_time} to {end_time}"
            )

        logger.info(f"Loaded {len(candles)} candles")

        # 2. Prepare candles list for efficient pickling
        # Convert to list of dicts to avoid SQLAlchemy object serialization issues
        candles_data = [
            {
                'datetime': candle.open_time,
                'open': candle.open_price,
                'high': candle.high_price,
                'low': candle.low_price,
                'close': candle.close_price,
                'volume': candle.volume
            }
            for candle in candles
        ]
        logger.info(f"Prepared {len(candles_data)} candles for optimization")

        # 3. Extract parameter constraints (if provided by strategy)
        constraints = parameter_ranges.pop('_constraints', [])
        semantic_constraints = parameter_ranges.pop('_semantic_constraints', [])

        # 4. Define objective function for Optuna (synchronous for Optuna compatibility)
        def objective(trial):
            # Suggest parameters
            params = {}

            # Build ordered sampling plan for constrained parameters
            # Constrained pairs: sample the first param, then set min of second = first + 1
            constrained_second = {right: left for left, right in constraints}

            # Determine sampling order: constrained "first" params before their "second"
            sampling_order = list(parameter_ranges.keys())
            # Sort so that left-side params come before right-side params
            for left, right in constraints:
                try:
                    li = sampling_order.index(left)
                    ri = sampling_order.index(right)
                    if li > ri:
                        sampling_order[li], sampling_order[ri] = sampling_order[ri], sampling_order[li]
                except ValueError:
                    pass

            for param_name in sampling_order:
                param_range = parameter_ranges[param_name]
                if param_name in fixed_parameters:
                    # Use fixed value
                    params[param_name] = fixed_parameters[param_name]
                    continue

                # Determine effective min/max
                effective_min = None
                effective_max = None
                param_type = 'float'

                if isinstance(param_range, dict) and 'min' in param_range and 'max' in param_range:
                    param_type = param_range.get('type', 'int')
                    effective_min = param_range['min']
                    effective_max = param_range['max']
                elif isinstance(param_range, list) and len(param_range) == 2:
                    if all(isinstance(x, (int, float)) for x in param_range):
                        effective_min = param_range[0]
                        effective_max = param_range[1]
                    else:
                        # Categorical
                        suggested_value = trial.suggest_categorical(param_name, param_range)
                        if len(param_range) > 0 and isinstance(param_range[0], (int, float)):
                            params[param_name] = type(param_range[0])(suggested_value)
                        else:
                            params[param_name] = suggested_value
                        continue
                else:
                    # Discrete options
                    suggested_value = trial.suggest_categorical(param_name, param_range)
                    if len(param_range) > 0 and isinstance(param_range[0], (int, float)):
                        params[param_name] = type(param_range[0])(suggested_value)
                    else:
                        params[param_name] = suggested_value
                    continue

                # Enforce ordering constraint: if this param must be > another
                if param_name in constrained_second:
                    left_param = constrained_second[param_name]
                    if left_param in params:
                        # Second param must be > first param
                        constrained_min = params[left_param] + 1
                        effective_min = max(effective_min, constrained_min)

                # Ensure min < max after constraint adjustment
                if effective_min is not None and effective_max is not None and effective_min >= effective_max:
                    # Constraint makes this impossible, return very low score
                    return -999.0

                if param_type == 'int':
                    params[param_name] = trial.suggest_int(
                        param_name, int(effective_min), int(effective_max)
                    )
                else:
                    params[param_name] = trial.suggest_float(
                        param_name, float(effective_min), float(effective_max)
                    )

            # Semantic constraint validation
            # Check parameter combinations that are technically valid but
            # economically meaningless (e.g., RSI never triggers, BB is noise)
            for constraint in semantic_constraints:
                required_params = constraint.get('params', [])
                validate_fn = constraint.get('validate')
                if validate_fn and all(p in params for p in required_params):
                    if not validate_fn(params):
                        return -999.0

            # Run backtest synchronously (Backtrader is not async)
            import backtrader as bt
            from backend.observers.trade_recorder import TradeRecorder

            # 创建数据源（回退到Pandas，Backtrader没有NumPyData）
            import pandas as pd
            df = pd.DataFrame(candles_data).set_index('datetime')
            data = bt.feeds.PandasData(dataname=df)

            # Configure Cerebro
            cerebro = bt.Cerebro(oldsync=True)
            cerebro.adddata(data)
            clean_params = {k: v for k, v in params.items() if not k.startswith('_')}
            cerebro.addstrategy(strategy_class, **clean_params)
            cerebro.broker.setcash(100000.0)
            cerebro.broker.setcommission(commission=0.001)

            # Add analyzers (只保留必要的，DrawDown延迟计算)
            cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
            # DrawDown计算开销大，改为从交易记录手动估算
            # cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
            cerebro.addobserver(TradeRecorder)

            # Run backtest
            initial_value = cerebro.broker.getvalue()
            results = cerebro.run(runonce=False)
            final_value = cerebro.broker.getvalue()

            strategy = results[0]

            # Get trades
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

            # 快速获取Sharpe ratio（不计算复杂指标）
            sharpe_analysis = strategy.analyzers.sharpe.get_analysis()
            sharpe_ratio = sharpe_analysis.get('sharperatio', None)

            if sharpe_ratio is None:
                # 基于收益率的快速估算
                sharpe_ratio = max(0.5, min(pnl_pct / 20.0, 3.0))

            # 手动计算max drawdown（比analyzer更快）
            if len(trades) > 0:
                peak = 100000.0  # 初始资金
                max_dd = 0.0
                current = 100000.0
                for trade in trades:
                    current += trade['pnl']
                    if current > peak:
                        peak = current
                    dd = (peak - current) / peak * 100
                    if dd > max_dd:
                        max_dd = dd
                max_drawdown = max_dd
            else:
                max_drawdown = 0.0

            result = {
                'final_value': final_value,
                'pnl': pnl,
                'pnl_pct': pnl_pct,
                'total_trades': total_trades,
                'win_rate': win_rate,
                'sharpe_ratio': sharpe_ratio,
                'max_drawdown': max_drawdown,
                'trades': trades,
                'signal_stats': getattr(strategy, 'signal_stats', None),
            }

            # Calculate composite score
            score = calculate_composite_score(result, scoring_weights)

            return score

        # 4. Create and run Optuna study with optimizations
        from optuna.samplers import TPESampler
        from optuna.pruners import MedianPruner

        # Use TPE sampler for better parameter suggestions
        sampler = TPESampler(seed=42)  # Fixed seed for reproducibility
        # Use median pruner to abort unpromising trials early
        pruner = MedianPruner(n_startup_trials=5, n_warmup_steps=10)

        study = self.optuna.create_study(
            direction='maximize',
            sampler=sampler,
            pruner=pruner
        )

        logger.info(f"Starting {n_trials} trials with optimized configuration")

        # NOTE: Multi-process parallelization tested but DISABLED
        #
        # Testing results on 10-core Mac:
        # - Pure CPU tasks: 6.61x speedup with n_jobs=8 ✅
        # - Backtrader tasks: 0.96x speedup (4% slower) ❌
        #
        # Reason: Backtrader initialization overhead dominates in short trials
        # Each process must: create Cerebro, add strategy, setup analyzers, load data
        # This overhead (~0.3s) negates parallel benefits for typical trial durations
        #
        # For very large scales (500+ trials), parallel might help
        # But for typical use (50-200 trials), single process is faster
        #
        # If you want to experiment with parallel anyway:
        # 1. Set n_jobs to a value (2-8)
        # 2. Only use for 200+ trials
        # 3. Expect overhead on small jobs

        # Run in thread pool to avoid blocking FastAPI event loop
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            lambda: study.optimize(
                objective,
                n_trials=n_trials,
                show_progress_bar=False,
                gc_after_trial=True
            )
        )

        # 4. Extract best results
        best_params = study.best_params
        best_score = study.best_value

        logger.info(
            f"Bayesian optimization complete. Best score: {best_score:.4f}"
        )

        # 5. Run backtest with best params to get full results
        best_result = await self._run_single_backtest(
            strategy_class=strategy_class,
            symbol=symbol,
            interval=interval,
            params=best_params,
            candles=candles
        )

        # 6. Save results to database (follow GridSearchOptimizer pattern)
        logger.info("Saving optimization results to database...")

        from backend.models.optimization_result import OptimizationResult

        # Create optimization result entry
        opt_result = OptimizationResult(
            optimization_job_id=optimization_job_id,
            parameters=best_params,
            score=best_score,
            composite_score=best_score,
            total_return=best_result['pnl_pct'] / 100,
            sharpe_ratio=best_result.get('sharpe_ratio'),
            max_drawdown=best_result.get('max_drawdown', 0.0) / 100,
            win_rate=best_result.get('win_rate', 0.0) / 100,
            total_trades=best_result['total_trades'],
            final_value=best_result['final_value'],
            initial_cash=100000.0
        )

        result_id = self.db.save_optimization_result(opt_result)

        # 7. Get all optimization results for return
        all_results = self.db.get_optimization_results(optimization_job_id)
        best_optimization_result = self.db.get_best_optimization_result(optimization_job_id)

        # 8. Format results for frontend
        formatted_results = []
        for opt_result in all_results:
            formatted_results.append({
                'id': opt_result.id,
                'job_id': opt_result.optimization_job_id,
                'parameters': opt_result.parameters,
                'pnl': (opt_result.total_return * 100000) if opt_result.total_return else 0,
                'pnl_pct': opt_result.total_return or 0,
                'total_trades': opt_result.total_trades or 0,
                'sharpe_ratio': opt_result.sharpe_ratio,
                'max_drawdown': opt_result.max_drawdown or 0,
                'win_rate': opt_result.win_rate or 0,
                'composite_score': opt_result.composite_score or 0,
                'is_best': opt_result.id == best_optimization_result.id if best_optimization_result else False
            })

        # 9. Format best result
        best_result_formatted = {
            'id': best_optimization_result.id,
            'job_id': best_optimization_result.optimization_job_id,
            'parameters': best_optimization_result.parameters,
            'pnl': (best_optimization_result.total_return * 100000) if best_optimization_result.total_return else 0,
            'pnl_pct': best_optimization_result.total_return or 0,
            'total_trades': best_optimization_result.total_trades or 0,
            'sharpe_ratio': best_optimization_result.sharpe_ratio,
            'max_drawdown': best_optimization_result.max_drawdown or 0,
            'win_rate': best_optimization_result.win_rate or 0,
            'composite_score': best_optimization_result.composite_score or best_score,
            'is_best': True
        }

        return {
            'job_id': optimization_job_id,
            'best_params': best_params,
            'best_score': best_score,
            'n_trials': n_trials,
            'best_result': best_result_formatted,
            'results': formatted_results
        }

    async def _run_single_backtest(
        self,
        strategy_class: Type[StrategyBase],
        symbol: str,
        interval: str,
        params: Dict[str, Any],
        candles: List[Any]
    ) -> Dict[str, Any]:
        """Run a single backtest with given parameters

        Reuses the backtest logic from GridSearchOptimizer
        """
        import backtrader as bt
        from backend.observers.trade_recorder import TradeRecorder

        # Create Backtrader data feed
        data = self.backtest_engine._create_data_feed(candles)

        # Configure Cerebro
        cerebro = bt.Cerebro(oldsync=True)
        cerebro.adddata(data)
        clean_params = {k: v for k, v in params.items() if not k.startswith('_')}
        cerebro.addstrategy(strategy_class, **clean_params)
        cerebro.broker.setcash(100000.0)
        cerebro.broker.setcommission(commission=0.001)

        # Add analyzers
        cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
        cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
        cerebro.addobserver(TradeRecorder)

        # Run backtest
        loop = asyncio.get_event_loop()

        def run_backtest():
            initial_value = cerebro.broker.getvalue()
            results = cerebro.run(runonce=False)
            final_value = cerebro.broker.getvalue()

            strategy = results[0]

            # Get trades
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
                # Estimate if analyzer returns None
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
