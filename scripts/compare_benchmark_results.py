#!/usr/bin/env python3
"""
Compare Benchmark Results

Compares performance before and after optimizations to validate improvements.

Usage:
    # First run benchmark before optimization
    python scripts/benchmark_bayesian_optimizer.py --output before.json

    # Apply optimizations

    # Run benchmark after optimization
    python scripts/benchmark_bayesian_optimizer.py --output after.json

    # Compare results
    python scripts/compare_benchmark_results.py before.json after.json
"""

import sys
import json
from pathlib import Path
from typing import Dict, Any


def load_results(filepath: str) -> Dict[str, Any]:
    """Load benchmark results from JSON file

    Args:
        filepath: Path to JSON file

    Returns:
        Dict containing benchmark results
    """
    with open(filepath, 'r') as f:
        return json.load(f)


def calculate_improvement(before: float, after: float) -> Dict[str, float]:
    """Calculate improvement metrics

    Args:
        before: Value before optimization
        after: Value after optimization

    Returns:
        Dict with improvement metrics
    """
    if before == 0:
        return {
            'absolute': after,
            'relative': 0.0,
            'improvement_pct': 0.0
        }

    absolute = before - after
    relative = absolute / before
    improvement_pct = relative * 100

    return {
        'absolute': absolute,
        'relative': relative,
        'improvement_pct': improvement_pct
    }


def format_improvement(value: float, higher_is_better: bool = True) -> str:
    """Format improvement value for display

    Args:
        value: Improvement value
        higher_is_better: If True, positive values are good

    Returns:
        Formatted string with color coding
    """
    is_improvement = (value > 0) if higher_is_better else (value < 0)

    if is_improvement:
        return f"\\033[92m+{value:+.1f}%\\033[0m"  # Green
    elif value < 0:
        return f"\\033[91m{value:+.1f}%\\033[0m"  # Red
    else:
        return f"{value:+.1f}%"


def compare_results(before_path: str, after_path: str):
    """Compare two benchmark results

    Args:
        before_path: Path to before optimization results
        after_path: Path to after optimization results
    """
    print("\n" + "="*70)
    print("Performance Comparison Report")
    print("="*70 + "\n")

    # Load results
    before_data = load_results(before_path)
    after_data = load_results(after_path)

    # Print metadata
    print(f"Before: {before_data['timestamp']}")
    print(f"After:  {after_data['timestamp']}")
    print(f"Strategy: {before_data['strategy']}")
    print()

    # Compare each benchmark
    benchmarks_before = before_data['benchmarks']
    benchmarks_after = after_data['benchmarks']

    # Get common benchmarks
    common_names = set(benchmarks_before.keys()) & set(benchmarks_after.keys())

    if not common_names:
        print("⚠ No common benchmarks found")
        return

    # Print comparison table
    print(f"{'Scenario':<30} {'Before':>12} {'After':>12} {'Change':>12}")
    print("-" * 70)

    for name in sorted(common_names):
        before = benchmarks_before[name]
        after = benchmarks_after[name]

        # Compare total duration (lower is better)
        duration_imp = calculate_improvement(
            before['total_duration_seconds'],
            after['total_duration_seconds']
        )

        # Compare trials per second (higher is better)
        tps_imp = calculate_improvement(
            before['trials_per_second'],
            after['trials_per_second']
        )

        # Compare memory usage (lower is better)
        memory_imp = calculate_improvement(
            before['peak_memory_mb'],
            after['peak_memory_mb']
        )

        print(f"\n{name}")
        print(f"  {'Time (s)':<28} {before['total_duration_seconds']:>12.2f} {after['total_duration_seconds']:>12.2f} {format_improvement(duration_imp['improvement_pct'], higher_is_better=False):>12}")
        print(f"  {'Trials/s':<28} {before['trials_per_second']:>12.2f} {after['trials_per_second']:>12.2f} {format_improvement(tps_imp['improvement_pct'], higher_is_better=True):>12}")
        print(f"  {'Memory (MB)':<28} {before['peak_memory_mb']:>12.2f} {after['peak_memory_mb']:>12.2f} {format_improvement(memory_imp['improvement_pct'], higher_is_better=False):>12}")

    # Calculate overall improvement
    print("\n" + "="*70)
    print("Overall Improvement")
    print("="*70 + "\n")

    avg_duration_before = sum(b['total_duration_seconds'] for b in benchmarks_before.values()) / len(benchmarks_before)
    avg_duration_after = sum(b['total_duration_seconds'] for b in benchmarks_after.values()) / len(benchmarks_after)
    duration_imp = calculate_improvement(avg_duration_before, avg_duration_after)

    avg_tps_before = sum(b['trials_per_second'] for b in benchmarks_before.values()) / len(benchmarks_before)
    avg_tps_after = sum(b['trials_per_second'] for b in benchmarks_after.values()) / len(benchmarks_after)
    tps_imp = calculate_improvement(avg_tps_before, avg_tps_after)

    avg_memory_before = sum(b['peak_memory_mb'] for b in benchmarks_before.values()) / len(benchmarks_before)
    avg_memory_after = sum(b['peak_memory_mb'] for b in benchmarks_after.values()) / len(benchmarks_after)
    memory_imp = calculate_improvement(avg_memory_before, avg_memory_after)

    print(f"Average Time:        {format_improvement(duration_imp['improvement_pct'], higher_is_better=False)}")
    print(f"Average Throughput:  {format_improvement(tps_imp['improvement_pct'], higher_is_better=True)}")
    print(f"Average Memory:      {format_improvement(memory_imp['improvement_pct'], higher_is_better=False)}")

    # Calculate speedup factor
    speedup = avg_duration_before / avg_duration_after
    print(f"\n🚀 Overall Speedup: {speedup:.2f}x")

    # Determine if optimization was successful
    if speedup >= 1.1:
        print("✅ Optimization successful!")
    elif speedup >= 1.0:
        print("⚠️  Minor improvement")
    else:
        print("❌ Performance degraded")

    print()


def main():
    """Main entry point"""
    if len(sys.argv) != 3:
        print("Usage: python compare_benchmark_results.py <before.json> <after.json>")
        print("\nExample:")
        print("  python scripts/benchmark_bayesian_optimizer.py --output before.json")
        print("  # Apply optimizations...")
        print("  python scripts/benchmark_bayesian_optimizer.py --output after.json")
        print("  python scripts/compare_benchmark_results.py before.json after.json")
        sys.exit(1)

    before_path = sys.argv[1]
    after_path = sys.argv[2]

    # Verify files exist
    if not Path(before_path).exists():
        print(f"❌ File not found: {before_path}")
        sys.exit(1)

    if not Path(after_path).exists():
        print(f"❌ File not found: {after_path}")
        sys.exit(1)

    # Compare results
    compare_results(before_path, after_path)


if __name__ == '__main__':
    main()
