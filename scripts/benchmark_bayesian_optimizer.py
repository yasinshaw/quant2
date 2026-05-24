#!/usr/bin/env python3
"""
Performance Benchmark Script for Bayesian Optimizer

Measures and reports performance metrics for the Bayesian optimizer.
Run this before and after optimizations to validate improvements.

Usage:
    python scripts/benchmark_bayesian_optimizer.py [--quick]

Options:
    --quick    Run quick benchmark (10 trials instead of 100)
"""

import asyncio
import sys
import time
import tracemalloc
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.core.bayesian_optimizer import BayesianOptimizer
from backend.core.backtest_engine import BacktestEngine
from backend.database import Database
from backend.strategies.double_ma_strategy import DoubleMAStrategy


class PerformanceMetrics:
    """Container for performance metrics"""

    def __init__(self):
        self.start_time = None
        self.end_time = None
        self.total_duration = None
        self.peak_memory_mb = None
        self.trials_per_second = None
        self.avg_trial_time = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'total_duration_seconds': self.total_duration,
            'peak_memory_mb': self.peak_memory_mb,
            'trials_per_second': self.trials_per_second,
            'avg_trial_time_seconds': self.avg_trial_time
        }


class BenchmarkConfig:
    """Configuration for benchmark scenarios"""

    def __init__(self, name: str, n_trials: int, parameter_ranges: Dict[str, Any]):
        self.name = name
        self.n_trials = n_trials
        self.parameter_ranges = parameter_ranges


class BenchmarkRunner:
    """Runs performance benchmarks for Bayesian optimizer"""

    def __init__(self, db_path: str = None):
        """Initialize benchmark runner

        Args:
            db_path: Path to SQLite database for testing (default: use config)
        """
        if db_path is None:
            # Use default database from config
            from backend.config import settings
            db_path = settings.database_url

        self.db = Database(db_path)
        self.backtest_engine = BacktestEngine(self.db)
        self.optimizer = BayesianOptimizer(self.backtest_engine)

        # Test data configuration (using available data in database)
        self.symbol = "ETHUSDT"
        self.interval = "1h"
        # Use limited date range for faster benchmarking
        self.start_time = "2025-01-01T00:00:00"
        self.end_time = "2025-01-31T23:59:59"  # 1 month of data

    def _setup_test_data(self) -> bool:
        """Ensure test data exists in database

        Returns:
            True if data is available, False otherwise
        """
        candles = self.db.get_candles(
            self.symbol,
            self.interval,
            self.start_time,
            self.end_time
        )

        if candles:
            print(f"✓ Found {len(candles)} candles in database")
            return True

        print(f"✗ No test data found. Please download data first:")
        print(f"  curl -X POST http://localhost:8000/api/v1/data/download \\")
        print(f"    -H 'Content-Type: application/json' \\")
        print(f"    -d '{{\"symbol\":\"BTCUSDT\",\"interval\":\"1h\",")
        print(f"         \"start_time\":\"{self.start_time}\",")
        print(f"         \"end_time\":\"{self.end_time}\"}}'")
        return False

    def _run_benchmark(self, config: BenchmarkConfig) -> PerformanceMetrics:
        """Run a single benchmark

        Args:
            config: Benchmark configuration

        Returns:
            PerformanceMetrics object with results
        """
        print(f"\n{'='*60}")
        print(f"Benchmark: {config.name}")
        print(f"{'='*60}")
        print(f"  Trials: {config.n_trials}")
        print(f"  Parameters: {config.parameter_ranges}")

        # Create optimization job
        from backend.models.optimization_job import OptimizationJob

        job = OptimizationJob(
            strategy_name=DoubleMAStrategy.strategy_name,
            symbol=self.symbol,
            interval=self.interval,
            start_time=datetime.fromisoformat(self.start_time),
            end_time=datetime.fromisoformat(self.end_time),
            parameter_ranges=config.parameter_ranges,
            optimization_method='bayesian',
            status='running'
        )
        job_id = self.db.create_optimization_job(job)

        # Start memory tracking
        tracemalloc.start()
        metrics = PerformanceMetrics()
        metrics.start_time = time.time()

        try:
            # Run optimization
            result = asyncio.run(self.optimizer.optimize(
                strategy_class=DoubleMAStrategy,
                symbol=self.symbol,
                interval=self.interval,
                start_time=self.start_time,
                end_time=self.end_time,
                parameter_ranges=config.parameter_ranges,
                optimization_job_id=job_id,
                n_trials=config.n_trials
            ))

            metrics.end_time = time.time()
            metrics.total_duration = metrics.end_time - metrics.start_time

            # Calculate performance metrics
            current, peak = tracemalloc.get_traced_memory()
            metrics.peak_memory_mb = peak / 1024 / 1024
            metrics.trials_per_second = config.n_trials / metrics.total_duration
            metrics.avg_trial_time = metrics.total_duration / config.n_trials

            # Print results
            print(f"\n✓ Benchmark completed")
            print(f"  Total time: {metrics.total_duration:.2f}s")
            print(f"  Average time per trial: {metrics.avg_trial_time:.3f}s")
            print(f"  Trials per second: {metrics.trials_per_second:.2f}")
            print(f"  Peak memory: {metrics.peak_memory_mb:.2f} MB")
            print(f"  Best score: {result['best_score']:.4f}")
            print(f"  Best params: {result['best_params']}")

        except Exception as e:
            print(f"\n✗ Benchmark failed: {e}")
            import traceback
            traceback.print_exc()
            raise
        finally:
            tracemalloc.stop()

        return metrics

    def run_all_benchmarks(self, quick_mode: bool = False) -> Dict[str, PerformanceMetrics]:
        """Run all benchmark scenarios

        Args:
            quick_mode: If True, run quick benchmarks with fewer trials

        Returns:
            Dict mapping benchmark names to PerformanceMetrics
        """
        print(f"\n{'='*60}")
        print(f"Bayesian Optimizer Performance Benchmark")
        print(f"{'='*60}")
        print(f"Strategy: {DoubleMAStrategy.strategy_name}")
        print(f"Data: {self.symbol} {self.interval}")
        print(f"Period: {self.start_time} to {self.end_time}")
        print(f"Quick Mode: {quick_mode}")

        # Setup test data
        if not self._setup_test_data():
            return {}

        # Define benchmark scenarios
        scenarios = [
            BenchmarkConfig(
                name="Small (2 params, 10 trials)",
                n_trials=10,
                parameter_ranges={
                    'fast_period': {'type': 'int', 'min': 5, 'max': 15},
                    'slow_period': {'type': 'int', 'min': 20, 'max': 30}
                }
            ),
            BenchmarkConfig(
                name="Medium (2 params, 50 trials)",
                n_trials=20 if quick_mode else 50,
                parameter_ranges={
                    'fast_period': {'type': 'int', 'min': 5, 'max': 50},
                    'slow_period': {'type': 'int', 'min': 20, 'max': 100}
                }
            ),
            BenchmarkConfig(
                name="Large (2 params, 100 trials)",
                n_trials=30 if quick_mode else 100,
                parameter_ranges={
                    'fast_period': {'type': 'int', 'min': 5, 'max': 100},
                    'slow_period': {'type': 'int', 'min': 20, 'max': 200}
                }
            ),
            # Add extra large scenario to test multi-process scaling
            BenchmarkConfig(
                name="XLarge (2 params, 200 trials)" if not quick_mode else "Medium-Plus (2 params, 60 trials)",
                n_trials=200 if not quick_mode else 60,
                parameter_ranges={
                    'fast_period': {'type': 'int', 'min': 5, 'max': 100},
                    'slow_period': {'type': 'int', 'min': 20, 'max': 200}
                }
            ),
        ]

        # Run benchmarks
        results = {}
        for scenario in scenarios:
            try:
                metrics = self._run_benchmark(scenario)
                results[scenario.name] = metrics
            except Exception as e:
                print(f"\n✗ Failed to run {scenario.name}: {e}")
                continue

        return results

    def print_summary(self, results: Dict[str, PerformanceMetrics]):
        """Print benchmark summary

        Args:
            results: Dict of benchmark results
        """
        print(f"\n{'='*60}")
        print(f"Benchmark Summary")
        print(f"{'='*60}\n")

        if not results:
            print("No results to display")
            return

        # Print table header
        print(f"{'Scenario':<30} {'Time':>10} {'Trials/s':>10} {'Memory':>10}")
        print("-" * 62)

        # Print each scenario
        for name, metrics in results.items():
            print(
                f"{name:<30} "
                f"{metrics.total_duration:>10.2f} "
                f"{metrics.trials_per_second:>10.2f} "
                f"{metrics.peak_memory_mb:>10.2f}"
            )

        # Calculate overall statistics
        all_times = [m.total_duration for m in results.values()]
        all_trial_rates = [m.trials_per_second for m in results.values()]
        all_memory = [m.peak_memory_mb for m in results.values()]

        print("-" * 62)
        print(
            f"{'Average':<30} "
            f"{sum(all_times)/len(all_times):>10.2f} "
            f"{sum(all_trial_rates)/len(all_trial_rates):>10.2f} "
            f"{sum(all_memory)/len(all_memory):>10.2f}"
        )

    def save_results(self, results: Dict[str, PerformanceMetrics], filepath: str = "benchmark_results.json"):
        """Save benchmark results to JSON file

        Args:
            results: Dict of benchmark results
            filepath: Path to save results
        """
        import json

        # Convert results to JSON-serializable format
        serializable_results = {
            'timestamp': datetime.now().isoformat(),
            'strategy': DoubleMAStrategy.strategy_name,
            'data': {
                'symbol': self.symbol,
                'interval': self.interval,
                'start': self.start_time,
                'end': self.end_time
            },
            'benchmarks': {
                name: metrics.to_dict()
                for name, metrics in results.items()
            }
        }

        with open(filepath, 'w') as f:
            json.dump(serializable_results, f, indent=2)

        print(f"\n✓ Results saved to {filepath}")


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Benchmark Bayesian Optimizer performance"
    )
    parser.add_argument(
        '--quick',
        action='store_true',
        help='Run quick benchmark with fewer trials'
    )
    parser.add_argument(
        '--output',
        default='benchmark_results.json',
        help='Output file for results (default: benchmark_results.json)'
    )

    args = parser.parse_args()

    # Run benchmarks
    runner = BenchmarkRunner()
    results = runner.run_all_benchmarks(quick_mode=args.quick)

    # Print summary
    runner.print_summary(results)

    # Save results
    if results:
        runner.save_results(results, args.output)


if __name__ == '__main__':
    main()
