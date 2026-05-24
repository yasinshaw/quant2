#!/usr/bin/env python3
"""
Backtest script for Multi-Indicator V3 Strategy on ETH 4h

Tests 2025 H1 data (Jan 1 - Jun 30, 2025)
"""
import sys
import os
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import backtrader as bt
from backend.config import settings
from backend.database import Database
from backend.strategies.multi_indicator_v3_strategy import MultiIndicatorStrategyV3
from backend.observers.trade_recorder import TradeRecorder


def run_backtest():
    """Run backtest for V3 strategy on ETH 4h 2025 H1"""

    # Initialize database
    db = Database(settings.database_url)

    # Load ETH 4h data for 2025 H1
    symbol = 'ETHUSDT'
    interval = '4h'
    start_date = '2025-01-01'
    end_date = '2025-06-30'

    print(f"\n{'='*80}")
    print(f"Multi-Indicator V3 Strategy Backtest")
    print(f"{'='*80}")
    print(f"Symbol: {symbol}")
    print(f"Interval: {interval}")
    print(f"Period: {start_date} to {end_date}")
    print(f"{'='*80}\n")

    # Fetch candles from database
    print("Loading data from database...")
    candles = db.get_candles(
        symbol=symbol,
        interval=interval,
        start_time=start_date,
        end_time=end_date
    )

    if not candles:
        print(f"❌ No data found for {symbol} {interval} from {start_date} to {end_date}")
        print(f"\nPlease download data first:")
        print(f"  python scripts/download_data.py --symbol {symbol} --interval {interval} --start {start_date} --end {end_date}")
        return

    print(f"✓ Loaded {len(candles)} candles")

    # Convert to pandas DataFrame
    import pandas as pd
    df = pd.DataFrame([
        {
            'datetime': c.open_time,
            'open': c.open_price,
            'high': c.high_price,
            'low': c.low_price,
            'close': c.close_price,
            'volume': c.volume
        }
        for c in candles
    ])
    df['datetime'] = pd.to_datetime(df['datetime'])
    df.set_index('datetime', inplace=True)
    df.sort_index(inplace=True)

    print(f"  Date range: {df.index[0]} to {df.index[-1]}")
    print(f"  Price range: ${df['close'].min():.2f} to ${df['close'].max():.2f}")

    # Create backtrader cerebro
    cerebro = bt.Cerebro()

    # Add strategy with default parameters
    cerebro.addstrategy(MultiIndicatorStrategyV3)

    # Create data feed
    data = bt.feeds.PandasData(
        dataname=df,
        name=f'{symbol}_{interval}'
    )
    cerebro.adddata(data)

    # Set initial capital
    initial_cash = 10000.0
    cerebro.broker.setcash(initial_cash)

    # Add analyzers
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')
    cerebro.addanalyzer(bt.analyzers.SQN, _name='sqn')  # System Quality Number
    cerebro.addanalyzer(bt.analyzers.VWR, _name='vwr')  # Variability-Weighted Return

    # Add observers for detailed tracking
    cerebro.addobserver(TradeRecorder)

    # Set commission (Binance: 0.1%)
    cerebro.broker.setcommission(commission=0.001)

    print(f"\n{'='*80}")
    print("Running backtest...")
    print(f"{'='*80}\n")

    # Run backtest
    results = cerebro.run()
    strat = results[0]

    # Get final portfolio value
    final_value = cerebro.broker.getvalue()
    pnl = final_value - initial_cash
    pnl_pct = (pnl / initial_cash) * 100

    # Get analyzer results
    sharpe = strat.analyzers.sharpe.get_analysis()
    drawdown = strat.analyzers.drawdown.get_analysis()
    trades = strat.analyzers.trades.get_analysis()
    sqn = strat.analyzers.sqn.get_analysis()
    vwr = strat.analyzers.vwr.get_analysis()

    # Print results
    print(f"\n{'='*80}")
    print("BACKTEST RESULTS")
    print(f"{'='*80}\n")

    print("📊 Performance Metrics:")
    print(f"  Initial Capital:      ${initial_cash:,.2f}")
    print(f"  Final Portfolio:      ${final_value:,.2f}")
    print(f"  Total P&L:            ${pnl:,.2f}")
    print(f"  Return:               {pnl_pct:+.2f}%")

    if sharpe:
        sharpe_ratio = sharpe.get('sharperatio')
        if sharpe_ratio:
            print(f"  Sharpe Ratio:         {sharpe_ratio:.3f}")
        else:
            print(f"  Sharpe Ratio:         N/A")

    if drawdown:
        max_dd = drawdown.get('max', {}).get('drawdown', 0)
        max_dd_len = drawdown.get('max', {}).get('len', 0)
        print(f"  Max Drawdown:         {max_dd:.2f}%")
        print(f"  Max DD Duration:      {max_dd_len} bars")

    if vwr:
        vwr_value = vwr.get('vwr')
        if vwr_value:
            print(f"  VWR:                  {vwr_value:.3f}")

    if sqn:
        sqn_value = sqn.get('sqn')
        if sqn_value:
            print(f"  SQN:                  {sqn_value:.2f}")

    print(f"\n📈 Trade Statistics:")
    if trades:
        total_trades = trades.get('total', {}).get('total', 0)
        won = trades.get('won', {}).get('total', 0)
        lost = trades.get('lost', {}).get('total', 0)

        print(f"  Total Trades:         {total_trades}")
        print(f"  Won:                  {won}")
        print(f"  Lost:                 {lost}")

        if total_trades > 0:
            win_rate = (won / total_trades) * 100
            print(f"  Win Rate:             {win_rate:.1f}%")

        if won > 0:
            avg_won = trades.get('won', {}).get('pnl', {}).get('average', 0)
            print(f"  Avg Win:              ${avg_won:,.2f}")

        if lost > 0:
            avg_lost = trades.get('lost', {}).get('pnl', {}).get('average', 0)
            print(f"  Avg Loss:             ${avg_lost:,.2f}")

        if won > 0 and lost > 0:
            profit_factor = trades.get('won', {}).get('pnl', {}).get('total', 0) / abs(
                trades.get('lost', {}).get('pnl', {}).get('total', 1)
            )
            print(f"  Profit Factor:        {profit_factor:.2f}")

    # Get trades from recorder
    if hasattr(strat, 'trade_recorder') and strat.trade_recorder.trades:
        print(f"\n📝 Recent Trades (last 10):")
        recent_trades = strat.trade_recorder.trades[-10:]
        for i, trade in enumerate(recent_trades, 1):
            print(f"  {i}. {trade['direction']:5s} | Entry: ${trade['entry_price']:.2f} | "
                  f"Exit: ${trade['exit_price']:.2f} | PnL: ${trade['pnl']:.2f}")

    print(f"\n{'='*80}")
    print("Strategy Parameters:")
    print(f"{'='*80}")
    params = strat.get_parameters()
    for key, value in sorted(params.items()):
        if key in ['trend_fast', 'trend_slow', 'atr_period', 'confirmation_threshold',
                   'enable_dynamic_leverage', 'enable_trailing_stop', 'enable_adx_filter',
                   'enable_volatility_filter', 'max_consecutive_losses', 'max_drawdown_threshold']:
            default = value.get('default')
            print(f"  {key:30s} = {default}")

    print(f"\n{'='*80}\n")

    return {
        'final_value': final_value,
        'pnl': pnl,
        'pnl_pct': pnl_pct,
        'sharpe': sharpe.get('sharperatio') if sharpe else None,
        'max_drawdown': drawdown.get('max', {}).get('drawdown', 0) if drawdown else 0,
        'total_trades': trades.get('total', {}).get('total', 0) if trades else 0,
        'win_rate': (trades.get('won', {}).get('total', 0) / trades.get('total', {}).get('total', 1)) * 100 if trades and trades.get('total', {}).get('total', 0) > 0 else 0,
    }


if __name__ == '__main__':
    try:
        results = run_backtest()
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Backtest failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
