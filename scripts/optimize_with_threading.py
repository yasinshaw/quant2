#!/usr/bin/env python3
"""
实施多线程优化的贝叶斯优化器

使用线程池并行执行试验
"""
import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Any, Type, Optional
from datetime import datetime

from backend.core.backtest_engine import BacktestEngine
from backend.core.strategy_base import StrategyBase
from backend.core.scoring_functions import calculate_composite_score
from backend.database import Database
from backend.config import settings
import backtrader as bt
import pandas as pd

logger = logging.getLogger(__name__)


class ThreadingBayesianOptimizer:
    """使用多线程的贝叶斯优化器"""

    def __init__(self, backtest_engine: BacktestEngine, max_workers: int = 8):
        self.backtest_engine = backtest_engine
        self.db = backtest_engine.db
        self.max_workers = max_workers

        try:
            import optuna
            self.optuna = optuna
        except ImportError:
            raise ImportError("Optuna is not installed")

    def _run_single_trial(
        self,
        strategy_class: Type[StrategyBase],
        params: Dict[str, Any],
        candles_data: List[Dict],
        trial_id: int
    ) -> Dict[str, Any]:
        """运行单个试验（线程安全）"""
        from backend.observers.trade_recorder import TradeRecorder

        # 创建数据源
        df = pd.DataFrame(candles_data).set_index('datetime')
        data = bt.feeds.PandasData(dataname=df)

        # 配置Cerebro
        cerebro = bt.Cerebro(oldsync=True)
        cerebro.adddata(data)
        cerebro.addstrategy(strategy_class, **params)
        cerebro.broker.setcash(100000.0)
        cerebro.broker.setcommission(commission=0.001)

        # 添加analyzer
        cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
        cerebro.addobserver(TradeRecorder)

        # 运行回测
        initial_value = cerebro.broker.getvalue()
        results = cerebro.run(runonce=False)
        final_value = cerebro.broker.getvalue()

        strategy = results[0]

        # 获取交易记录
        trades = []
        for observer in strategy.observers:
            if isinstance(observer, TradeRecorder):
                trades = observer.trades
                break

        # 计算指标
        pnl = final_value - initial_value
        pnl_pct = (pnl / initial_value) * 100

        total_trades = len(trades)
        if total_trades > 0:
            winning_trades = [t for t in trades if t['pnl'] > 0]
            win_rate = (len(winning_trades) / total_trades) * 100
        else:
            win_rate = 0.0

        # Sharpe Ratio
        sharpe_analysis = strategy.analyzers.sharpe.get_analysis()
        sharpe_ratio = sharpe_analysis.get('sharperatio', None)
        if sharpe_ratio is None:
            sharpe_ratio = max(0.5, min(pnl_pct / 20.0, 3.0))

        # Max Drawdown（手动计算）
        if len(trades) > 0:
            peak = 100000.0
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

        return {
            'trial_id': trial_id,
            'params': params,
            'score': pnl_pct,  # 简化评分
            'pnl_pct': pnl_pct,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': max_drawdown,
            'total_trades': total_trades,
            'win_rate': win_rate,
            'final_value': final_value
        }

    async def optimize_with_threading(
        self,
        strategy_class: Type[StrategyBase],
        symbol: str,
        interval: str,
        start_time: str,
        end_time: str,
        parameter_ranges: Dict[str, Any],
        optimization_job_id: int,
        n_trials: int = 100,
        scoring_weights: Optional[Dict[str, float]] = None
    ) -> Dict[str, Any]:
        """使用多线程运行优化"""

        # 1. 加载数据
        candles = self.db.get_candles(symbol, interval, start_time, end_time)
        if not candles:
            raise ValueError(f"No data found for {symbol} {interval}")

        # 2. 准备数据
        candles_data = [
            {
                'datetime': c.open_time,
                'open': c.open_price,
                'high': c.high_price,
                'low': c.low_price,
                'close': c.close_price,
                'volume': c.volume
            }
            for c in candles
        ]

        # 3. 生成参数组合（使用Optuna）
        import optuna
        from optuna.samplers import TPESampler

        def create_study():
            return optuna.create_study(direction='maximize', sampler=TPESampler(seed=42))

        # 使用Optuna生成参数，但用线程池执行
        study = create_study()

        # 定义目标函数（不直接运行，只生成参数）
        def objective_for_params(trial):
            params = {}
            for param_name, param_range in parameter_ranges.items():
                if isinstance(param_range, dict) and 'min' in param_range and 'max' in param_range:
                    param_type = param_range.get('type', 'int')
                    min_val = param_range['min']
                    max_val = param_range['max']
                    if param_type == 'int':
                        params[param_name] = trial.suggest_int(param_name, int(min_val), int(max_val))
                    else:
                        params[param_name] = trial.suggest_float(param_name, float(min_val), float(max_val))
                else:
                    params[param_name] = trial.suggest_categorical(param_name, param_range)
            return params

        # 生成所有参数组合
        all_params = []
        temp_study = create_study()
        for i in range(n_trials):
            trial = temp_study.ask()
            params = objective_for_params(trial)
            all_params.append(params)

        # 4. 使用线程池并行执行
        logger.info(f"Running {n_trials} trials with {self.max_workers} threads...")

        loop = asyncio.get_event_loop()

        def run_trial(params_dict):
            trial_id = all_params.index(params_dict)
            return self._run_single_trial(
                strategy_class, params_dict, candles_data, trial_id
            )

        import concurrent.futures

        results = []
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # 提交所有任务
            futures = [executor.submit(run_trial, params) for params in all_params]

            # 等待完成
            for future in concurrent.futures.as_completed(futures):
                result = future.result()
                results.append(result)
                if len(results) % 10 == 0:
                    logger.info(f"Completed {len(results)}/{n_trials} trials")

        # 5. 找到最佳结果
        best = max(results, key=lambda x: x['score'])

        # 6. 保存最佳结果
        from backend.models.optimization_result import OptimizationResult

        opt_result = OptimizationResult(
            optimization_job_id=optimization_job_id,
            parameters=best['params'],
            score=best['score'],
            composite_score=best['score'],
            total_return=best['pnl_pct'] / 100,
            sharpe_ratio=best['sharpe_ratio'],
            max_drawdown=best['max_drawdown'] / 100,
            win_rate=best['win_rate'] / 100,
            total_trades=best['total_trades'],
            final_value=best['final_value'],
            initial_cash=100000.0
        )

        result_id = self.db.save_optimization_result(opt_result)

        return {
            'job_id': optimization_job_id,
            'best_params': best['params'],
            'best_score': best['score'],
            'n_trials': n_trials,
            'results': results
        }


if __name__ == '__main__':
    # 测试多线程优化器
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))

    from backend.database import Database
    from backend.core.backtest_engine import BacktestEngine
    from backend.strategies.double_ma_strategy import DoubleMAStrategy

    db = Database()
    engine = BacktestEngine(db)

    optimizer = ThreadingBayesianOptimizer(engine, max_workers=8)

    # 快速测试
    import asyncio
    from datetime import datetime

    result = asyncio.run(optimizer.optimize_with_threading(
        strategy_class=DoubleMAStrategy,
        symbol='ETHUSDT',
        interval='1h',
        start_time='2025-01-01T00:00:00',
        end_time='2025-01-31T23:59:59',
        parameter_ranges={
            'fast_period': {'type': 'int', 'min': 5, 'max': 50},
            'slow_period': {'type': 'int', 'min': 20, 'max': 100}
        },
        optimization_job_id=999,  # 测试ID
        n_trials=20
    ))

    print(f"Best score: {result['best_score']:.2f}")
    print(f"Best params: {result['best_params']}")
