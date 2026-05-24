"""
BTC-ETH Pair Walk-Forward Validation Runner

Rolling-origin validation: optimizes parameters on each train window,
evaluates on the following test window. This gives a realistic estimate
of out-of-sample performance and detects parameter stability.

Usage:
    python scripts/run_walk_forward_pair.py \
        --btc-dataset 24 --eth-dataset 16 \
        --train-bars 2000 --test-bars 500 --step-bars 250
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from backend.config import settings
from backend.core.pair_backtest_engine import PairBacktestEngine
from backend.core.pair_walk_forward import PairWalkForwardValidator
from backend.database import Database
from backend.strategies.btc_eth_pair_strategy import BtcEthPair

logging.basicConfig(
    level=logging.WARNING,
    format='%(asctime)s %(levelname)s %(name)s: %(message)s',
)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument('--btc-dataset', type=int, default=24)
    p.add_argument('--eth-dataset', type=int, default=16)
    p.add_argument('--initial-cash', type=float, default=100000.0)
    p.add_argument('--commission', type=float, default=0.0005)

    # Window sizes
    p.add_argument('--train-bars', type=int, default=2000,
                   help='Bars in each train window (2000 ≈ 11 months on 4h)')
    p.add_argument('--test-bars', type=int, default=500,
                   help='Bars in each test window (500 ≈ 2.7 months on 4h)')
    p.add_argument('--step-bars', type=int, default=250,
                   help='Bars to slide between windows (250 ≈ 1.4 months)')

    # Parameter grid for optimization
    p.add_argument('--windows', type=int, nargs='+',
                   default=[120, 180, 240],
                   help='zscore_window candidates')
    p.add_argument('--entry-zs', type=float, nargs='+',
                   default=[1.5, 2.0, 2.5],
                   help='entry_z candidates')
    p.add_argument('--stop-zs', type=float, nargs='+',
                   default=[2.5, 3.0, 3.5, 4.0],
                   help='stop_z candidates')
    p.add_argument('--slope-pcts', type=float, nargs='+',
                   default=[0.01, 0.015, 0.02, 0.025],
                   help='max_abs_slope_pct candidates')
    p.add_argument('--exit-zs', type=float, nargs='+', default=[0.0])

    p.add_argument('--score-key', type=str, default='sharpe_ratio',
                   choices=['sharpe_ratio', 'profit_factor'])
    p.add_argument('--verbose', action='store_true')
    p.add_argument('--save-json', type=str, default='reports/walk_forward_pair.json')
    return p.parse_args()


def fmt_row(label: str, ret: float, sharpe: float, dd: float, trades: int) -> str:
    return (
        f"| {label:<20} "
        f"| {ret:+7.2f}% "
        f"| {sharpe:>6.2f} "
        f"| {dd:>6.2f}% "
        f"| {trades:>4} |"
    )


def main() -> None:
    args = parse_args()
    if args.verbose:
        logging.getLogger('backend').setLevel(logging.INFO)

    db = Database(settings.database_url)
    engine = PairBacktestEngine(db)
    validator = PairWalkForwardValidator(engine)

    param_grid = {
        'zscore_window': args.windows,
        'entry_z': args.entry_zs,
        'exit_z': args.exit_zs,
        'stop_z': args.stop_zs,
        'max_abs_slope_pct': args.slope_pcts,
        'use_detrend': [True],
        'leg_notional_pct': [25.0],
        'leverage': [2.0],
        'max_hold_bars': [240],
    }

    total_combos = 1
    for v in param_grid.values():
        total_combos *= len(v)
    n_windows = (9343 - args.train_bars - args.test_bars) // args.step_bars
    estimated_backtests = n_windows * total_combos

    print('=' * 80)
    print('BTC-ETH Pair Walk-Forward Validation')
    print('=' * 80)
    print(f"Strategy     : {BtcEthPair.strategy_name}")
    print(f"Datasets     : BTC={args.btc_dataset}, ETH={args.eth_dataset}")
    print(f"Window sizes : train={args.train_bars}, test={args.test_bars}, step={args.step_bars}")
    print(f"Param grid   : {total_combos} combos × ~{n_windows} windows ≈ {estimated_backtests:,} backtests")
    print(f"Score metric : {args.score_key}")
    print()

    result = validator.run(
        strategy_class=BtcEthPair,
        dataset_a_id=args.btc_dataset,
        dataset_b_id=args.eth_dataset,
        train_bars=args.train_bars,
        test_bars=args.test_bars,
        step_bars=args.step_bars,
        param_grid=param_grid,
        score_key=args.score_key,
        commission=args.commission,
        initial_cash=args.initial_cash,
        verbose=args.verbose,
    )

    agg = result['aggregated']
    print()
    print('=' * 80)
    print('Walk-Forward Results Summary')
    print('=' * 80)
    print(f"Windows          : {result['n_windows']}")
    print(f"Total return     : {agg['total_return_pct']:+.2f}%")
    print(f"Mean return      : {agg['mean_return_pct']:+.2f}% (σ={agg['std_return_pct']:.2f}%)")
    print(f"Median return    : {agg['median_return_pct']:+.2f}%")
    print(f"Win rate (windows): {agg['win_rate_pct']:.1f}%")
    print(f"Mean Sharpe      : {agg['mean_sharpe']:.2f} (median={agg['median_sharpe']:.2f})")
    print(f"Mean Max DD      : {agg['mean_max_dd_pct']:.2f}% (median={agg['median_max_dd_pct']:.2f}%)")
    print(f"Mean Win Rate    : {agg['mean_win_rate_pct']:.1f}%")
    print(f"Mean Profit Factor: {agg['mean_profit_factor']:.2f}")
    print(f"Total trades     : {agg['total_trades']}")
    print(f"Param stability  : {agg['param_stability']:.2%} "
          f"(unique sets / total windows)")
    print()

    header = "| Window                | Return   | Sharpe | MaxDD  | Trd  |"
    print(header)
    print("|" + "-" * 76 + "|")

    for i, w in enumerate(result['windows']):
        label = f"{i+1:2d}. {w['test_start'][:10]}"
        print(fmt_row(
            label,
            w['test_return_pct'],
            w['test_sharpe'],
            w['test_dd_pct'],
            w['test_trades'],
        ))

    print("|" + "-" * 76 + "|")
    print(fmt_row(
        "MEAN",
        agg['mean_return_pct'],
        agg['mean_sharpe'],
        agg['mean_max_dd_pct'],
        int(agg['mean_trades_per_window']),
    ))
    print()

    # Best / worst
    print("--- Best Window ---")
    bw = result['best_window']
    print(f"  Period     : {bw['test_start'][:10]} → {bw['test_end'][:10]}")
    print(f"  Return     : {bw['test_return_pct']:+.2f}%")
    print(f"  Sharpe     : {bw['test_sharpe']:.2f}")
    print(f"  Max DD     : {bw['test_dd_pct']:.2f}%")
    print(f"  Params     : {bw['params']}")

    print("\n--- Worst Window ---")
    ww = result['worst_window']
    print(f"  Period     : {ww['test_start'][:10]} → {ww['test_end'][:10]}")
    print(f"  Return     : {ww['test_return_pct']:+.2f}%")
    print(f"  Sharpe     : {ww['test_sharpe']:.2f}")
    print(f"  Max DD     : {ww['test_dd_pct']:.2f}%")
    print(f"  Params     : {ww['params']}")

    # Parameter analysis
    param_counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for w in result['windows']:
        for k, v in w['best_params'].items():
            param_counts[k][str(v)] += 1

    print("\n--- Parameter Selection Frequency ---")
    for param_name in sorted(param_counts.keys()):
        counts = sorted(param_counts[param_name].items(), key=lambda x: -x[1])
        total = sum(c for _, c in counts)
        print(f"  {param_name}:")
        for val, cnt in counts[:5]:  # top 5
            print(f"    {val}: {cnt}/{total} ({cnt/total*100:.1f}%)")

    # Save
    Path(args.save_json).parent.mkdir(parents=True, exist_ok=True)
    with open(args.save_json, 'w') as f:
        json.dump(result, f, indent=2, default=str)
    print(f"\nResults saved to {args.save_json}")


if __name__ == '__main__':
    main()
