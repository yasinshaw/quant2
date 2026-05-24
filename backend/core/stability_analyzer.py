"""
Parameter stability analysis to detect overfitting.

Analyzes performance variance around optimal parameters to distinguish
between robust parameter plateaus vs isolated overfitted peaks.
"""

from typing import Dict, Any, List, Tuple
import copy
from backend.core.backtest_runner import BacktestRunner
from backend.core.scoring_functions import calculate_composite_score


class StabilityAnalyzer:
    """Analyzes parameter stability to detect overfitting

    Overfitted parameters often show isolated performance peaks with high
    variance in neighboring regions. Stable parameters show consistent
    performance across similar parameter combinations.
    """

    def __init__(self, backtest_engine):
        """Initialize stability analyzer

        Args:
            backtest_engine: BacktestEngine instance for running backtests
        """
        self.backtest_engine = backtest_engine

    async def analyze_stability(
        self,
        strategy_class,
        optimal_params: Dict[str, Any],
        parameter_ranges: Dict[str, Dict[str, Any]],
        symbol: str,
        interval: str,
        start_time,
        end_time,
        optimization_job_id: int,
        variation_pct: float = 0.10,
        samples_per_param: int = 3
    ) -> Dict[str, Any]:
        """Analyze stability of optimal parameters

        Tests performance variance around optimal parameters by running
        backtests with small parameter variations.

        Args:
            strategy_class: Strategy class to test
            optimal_params: Best parameters found by optimization
            parameter_ranges: Parameter range definitions
            symbol: Trading symbol
            interval: Candle interval
            start_time: Backtest start time
            end_time: Backtest end time
            optimization_job_id: Database job ID
            variation_pct: Percentage to vary each parameter (default 10%)
            samples_per_param: Number of variations to test per parameter

        Returns:
            Dict with stability metrics:
                - stability_score: 0-1 score (higher = more stable)
                - variance: Performance variance across neighbors
                - neighbors: List of neighbor test results
                - is_stable: Boolean assessment
        """
        # Load candles for backtesting
        from backend.database import Database
        db = Database()

        candles = db.get_candles(
            symbol=symbol,
            interval=interval,
            start_time=start_time,
            end_time=end_time
        )

        if not candles:
            raise ValueError(f"No candles found for {symbol} {interval} "
                           f"from {start_time} to {end_time}")

        # Get optimal score
        optimal_backtest = await self._run_backtest_with_params(
            strategy_class, optimal_params, candles
        )
        optimal_score = calculate_composite_score(optimal_backtest)

        # Generate and test neighbor parameter sets
        neighbor_results = []

        for param_name, param_config in parameter_ranges.items():
            if param_name.startswith('_') or not isinstance(param_config, dict):
                continue
            if param_name not in optimal_params:
                continue

            optimal_value = optimal_params[param_name]
            param_type = param_config.get('type', 'int')

            # Generate variations for this parameter
            variations = self._generate_variations(
                optimal_value,
                param_type,
                param_config,
                variation_pct,
                samples_per_param
            )

            for varied_value in variations:
                # Create neighbor parameter set
                neighbor_params = copy.deepcopy(optimal_params)
                neighbor_params[param_name] = varied_value

                # Run backtest with varied parameters
                try:
                    neighbor_result = await self._run_backtest_with_params(
                        strategy_class, neighbor_params, candles
                    )
                    neighbor_score = calculate_composite_score(neighbor_result)

                    neighbor_results.append({
                        'parameters': neighbor_params.copy(),
                        'score': neighbor_score,
                        'pnl_pct': neighbor_result['pnl_pct'],
                        'sharpe_ratio': neighbor_result['sharpe_ratio'],
                        'max_drawdown': neighbor_result['max_drawdown']
                    })
                except Exception as e:
                    # Log but continue - failed backtests don't invalidate stability
                    print(f"Stability test failed for params {neighbor_params}: {e}")

        # Calculate stability metrics
        stability_metrics = self._calculate_stability_metrics(
            optimal_score, neighbor_results
        )

        # Store stability data in database
        self._store_stability_results(
            optimization_job_id,
            stability_metrics,
            neighbor_results
        )

        return stability_metrics

    def _generate_variations(
        self,
        optimal_value: Any,
        param_type: str,
        param_config: Dict[str, Any],
        variation_pct: float,
        samples: int
    ) -> List[Any]:
        """Generate parameter variations for stability testing

        Args:
            optimal_value: Optimal parameter value
            param_type: Parameter type (int, float, choice)
            param_config: Parameter configuration
            variation_pct: Percentage to vary
            samples: Number of variations to generate

        Returns:
            List of varied parameter values
        """
        variations = []

        if param_type == 'choice':
            # For discrete choices, test all options except optimal
            options = param_config.get('options', [])
            variations = [v for v in options if v != optimal_value]
        else:
            # For numeric parameters, generate variations around optimal
            min_val = param_config.get('min', optimal_value * 0.5)
            max_val = param_config.get('max', optimal_value * 1.5)

            if param_type == 'int':
                step = max(1, int((max_val - min_val) * variation_pct / samples))
                for i in range(1, samples + 1):
                    # Vary in both directions
                    lower = max(min_val, optimal_value - i * step)
                    upper = min(max_val, optimal_value + i * step)
                    if lower != optimal_value:
                        variations.append(lower)
                    if upper != optimal_value and upper not in variations:
                        variations.append(upper)
            else:  # float
                step = (max_val - min_val) * variation_pct / samples
                for i in range(1, samples + 1):
                    lower = max(min_val, optimal_value - i * step)
                    upper = min(max_val, optimal_value + i * step)
                    if lower != optimal_value:
                        variations.append(round(lower, 6))
                    if upper != optimal_value and round(upper, 6) not in variations:
                        variations.append(round(upper, 6))

        return variations[:samples]

    async def _run_backtest_with_params(
        self,
        strategy_class,
        params: Dict[str, Any],
        candles: List[Any]
    ) -> Dict[str, Any]:
        """Run backtest with given parameters

        Args:
            strategy_class: Strategy class
            params: Strategy parameters
            candles: Candle data

        Returns:
            Backtest result dict
        """
        from pandas import DataFrame

        # Create data feed
        df = DataFrame(candles)
        df['timestamp'] = df['timestamp'].astype('datetime64[s]')
        df.set_index('timestamp', inplace=True)

        data_feed = self.backtest_engine._create_data_feed(df)

        # Run backtest using shared BacktestRunner
        result = await BacktestRunner.run_backtest(
            strategy_class=strategy_class,
            params=params,
            candles=candles,
            create_data_feed_fn=lambda c: data_feed
        )

        return result

    def _calculate_stability_metrics(
        self,
        optimal_score: float,
        neighbor_results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Calculate stability metrics from neighbor results

        Args:
            optimal_score: Optimal parameter set score
            neighbor_results: List of neighbor test results

        Returns:
            Dict with stability metrics
        """
        if not neighbor_results:
            return {
                'stability_score': 0.0,
                'variance': 0.0,
                'neighbors': [],
                'is_stable': False
            }

        # Extract scores
        scores = [r['score'] for r in neighbor_results]

        # Calculate variance (standard deviation of scores)
        import statistics
        variance = statistics.stdev(scores) if len(scores) > 1 else 0.0

        # Calculate stability score
        # High stability: neighbors score close to optimal (low variance)
        # Low stability: neighbors score much worse than optimal (high variance)
        score_drop = optimal_score - max(scores) if scores else 0

        # Stability score: 1.0 if variance < 0.05 and score_drop < 0.1
        # Decreases as variance and score_drop increase
        variance_penalty = min(variance * 2, 1.0)
        drop_penalty = min(score_drop * 5, 1.0)

        stability_score = max(0, 1.0 - (variance_penalty + drop_penalty) / 2)

        # Consider stable if score > 0.7
        is_stable = stability_score >= 0.7

        return {
            'stability_score': stability_score,
            'variance': variance,
            'neighbors': neighbor_results,
            'is_stable': is_stable,
            'optimal_score': optimal_score,
            'mean_neighbor_score': statistics.mean(scores) if scores else 0.0
        }

    def _store_stability_results(
        self,
        optimization_job_id: int,
        stability_metrics: Dict[str, Any],
        neighbor_results: List[Dict[str, Any]]
    ):
        """Store stability analysis results in database

        Args:
            optimization_job_id: Job ID to update
            stability_metrics: Calculated stability metrics
            neighbor_results: Neighbor test results
        """
        from backend.database import Database

        db = Database()

        # Update optimization job with stability metrics
        db.update_optimization_job_stability(
            job_id=optimization_job_id,
            stability_score=stability_metrics['stability_score'],
            variance=stability_metrics['variance'],
            is_stable=stability_metrics['is_stable']
        )

        # Store neighbor data in best result
        # (We update the optimization_result with neighbor data)
        best_result = db.get_best_optimization_result(optimization_job_id)
        if best_result:
            db.update_optimization_result_stability_neighbors(
                result_id=best_result['id'],
                neighbors=neighbor_results
            )
