"""
BTC-ETH Pair Trading Backtest Runner

Runs `BtcEthPair` strategy against aligned BTC (dataset_a_id) + ETH
(dataset_b_id) datasets, produces a yearly performance breakdown, and
prints a comparison table.

Usage:
    python scripts/run_btc_eth_pair_backtest.py \
        --btc-dataset 24 --eth-dataset 16
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from backend.config import settings  # noqa: E402
from backend.core.pair_backtest_engine import PairBacktestEngine  # noqa: E402
from backend.database import Database  # noqa: E402
from backend.strategies.btc_eth_pair_strategy import BtcEthPair  # noqa: E402

logging.basicConfig(
    level=logging.WARNING,
    format='%(asctime)s %(levelname)s %(name)s: %(message)s',
)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument('--btc-dataset', type=int, default=24)
    p.add_argument('--eth-dataset', type=int, default=16)
    p.add_argument('--initial-cash', type=float, default=100000.0)
    p.add_argument('--commission', type=float, default=0.0005,
                   help='Per-leg commission (0.0005 = 5bps taker perp)')
    p.add_argument('--start', type=str, default='2022-01-01')
    p.add_argument('--end', type=str, default='2026-04-10')

    # Strategy params (override defaults)
    p.add_argument('--zscore-window', type=int, default=120)
    p.add_argument('--entry-z', type=float, default=2.0)
    p.add_argument('--exit-z', type=float, default=0.3)
    p.add_argument('--stop-z', type=float, default=4.0)
    p.add_argument('--leg-notional-pct', type=float, default=25.0)
    p.add_argument('--leverage', type=float, default=2.0)
    p.add_argument('--max-hold-bars', type=int, default=240)
    p.add_argument('--use-detrend', action='store_true', default=True)
    p.add_argument('--no-detrend', dest='use_detrend', action='store_false')
    p.add_argument('--max-abs-slope-pct', type=float, default=0.0,
                   help='Counter-trend filter threshold (% per bar, 0 = off)')
    p.add_argument('--stop-z-leverage-scaling', action='store_true', default=True)
    p.add_argument('--no-stop-z-scaling', dest='stop_z_leverage_scaling', action='store_false')
    p.add_argument('--stop-z-leverage-factor', type=float, default=0.8)
    p.add_argument('--auto-reduce-notional', action='store_true', default=True)
    p.add_argument('--no-auto-reduce', dest='auto_reduce_notional', action='store_false')
    p.add_argument('--partial-exit-pct', type=float, default=0.5)

    p.add_argument('--save-json', type=str, default=None)
    p.add_argument('--verbose', action='store_true')
    return p.parse_args()


def run_one(
    engine: PairBacktestEngine,
    btc_id: int,
    eth_id: int,
    start: datetime,
    end: datetime,
    params: dict,
    initial_cash: float,
    commission: float,
) -> dict:
    return engine.run(
        strategy_class=BtcEthPair,
        dataset_a_id=btc_id,
        dataset_b_id=eth_id,
        start_time=start,
        end_time=end,
        parameters=params,
        initial_cash=initial_cash,
        commission=commission,
        feed_a_name='BTC',
        feed_b_name='ETH',
    )


def fmt_row(label: str, r: dict) -> str:
    return (
        f"| {label:<14} "
        f"| {r['pnl_pct']:+7.2f}% "
        f"| {r['sharpe_ratio']:>6.2f} "
        f"| {r['max_drawdown']:>6.2f}% "
        f"| {r['total_trades']:>6} "
        f"| {r['win_rate']:>5.1f}% "
        f"| {r['profit_factor']:>5.2f} "
        f"|"
    )


def main() -> None:
    args = parse_args()
    if args.verbose:
        logging.getLogger('backend').setLevel(logging.INFO)

    db = Database(settings.database_url)
    engine = PairBacktestEngine(db)

    params = {
        'zscore_window': args.zscore_window,
        'entry_z': args.entry_z,
        'exit_z': args.exit_z,
        'stop_z': args.stop_z,
        'leg_notional_pct': args.leg_notional_pct,
        'leverage': args.leverage,
        'max_hold_bars': args.max_hold_bars,
        'use_detrend': args.use_detrend,
        'max_abs_slope_pct': args.max_abs_slope_pct,
        'stop_z_leverage_scaling': args.stop_z_leverage_scaling,
        'stop_z_leverage_factor': args.stop_z_leverage_factor,
        'auto_reduce_notional': args.auto_reduce_notional,
        'partial_exit_pct': args.partial_exit_pct,
    }

    full_start = datetime.fromisoformat(args.start)
    full_end = datetime.fromisoformat(args.end)

    print('=' * 88)
    print('BTC-ETH Pair Trading Backtest')
    print('=' * 88)
    print(f"Strategy  : {BtcEthPair.strategy_name} v{BtcEthPair.strategy_version}")
    print(f"Params    : {params}")
    print(f"Datasets  : BTC={args.btc_dataset}, ETH={args.eth_dataset}")
    print(f"Period    : {full_start.date()} → {full_end.date()}")
    print(f"Cash      : ${args.initial_cash:,.0f}  Commission/leg: {args.commission*100:.3f}%")
    print()

    header = (
        "| Period         | Return   | Sharpe | MaxDD  | Trades | WinR  | PF    |\n"
        "|----------------|----------|--------|--------|--------|-------|-------|"
    )
    print(header)

    # Yearly runs
    yearly: dict[str, dict] = {}
    year_start = full_start.year
    year_end = full_end.year
    for y in range(year_start, year_end + 1):
        ys = max(datetime(y, 1, 1), full_start)
        ye = min(datetime(y + 1, 1, 1), full_end)
        if ys >= ye:
            continue
        try:
            r = run_one(
                engine, args.btc_dataset, args.eth_dataset, ys, ye,
                params, args.initial_cash, args.commission,
            )
            yearly[str(y)] = r
            print(fmt_row(str(y), r))
        except Exception as e:
            print(f"| {y:<14} | ERROR: {e}")

    # Full period
    print("|" + "-" * 86 + "|")
    full = run_one(
        engine, args.btc_dataset, args.eth_dataset, full_start, full_end,
        params, args.initial_cash, args.commission,
    )
    print(fmt_row('FULL', full))
    print()

    # Trade anatomy
    trades = full['trades']
    if trades:
        pnls = [t['pnl'] for t in trades]
        winners = [p for p in pnls if p > 0]
        losers = [p for p in pnls if p < 0]
        print('--- Full-period trade anatomy ---')
        print(f"  Trades        : {len(trades)} (BTC+ETH legs combined)")
        print(f"  Avg win       : ${sum(winners)/len(winners):.2f}" if winners else "  No winners")
        print(f"  Avg loss      : ${sum(losers)/len(losers):.2f}" if losers else "  No losers")
        print(f"  Biggest win   : ${max(pnls):.2f}")
        print(f"  Biggest loss  : ${min(pnls):.2f}")
        print(f"  Total fees    : ${sum(t['commission'] for t in trades):.2f}")

    if args.save_json:
        Path(args.save_json).parent.mkdir(parents=True, exist_ok=True)
        with open(args.save_json, 'w') as f:
            # Strip per-trade detail from yearly to keep file small; keep for full
            slim_yearly = {
                k: {kk: vv for kk, vv in v.items() if kk != 'trades'}
                for k, v in yearly.items()
            }
            json.dump(
                {
                    'params': params,
                    'full_period': full,
                    'yearly': slim_yearly,
                },
                f, indent=2, default=str,
            )
        print(f'\nResults saved to {args.save_json}')


if __name__ == '__main__':
    main()
