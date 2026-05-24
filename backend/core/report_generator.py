"""
Report Generator for Backtest Results

Generates comprehensive backtest reports including:
- Core performance metrics summary
- Monthly returns breakdown
- Per-trade analysis with detailed statistics
- Equity curve data
"""
from typing import Dict, List, Any
from datetime import datetime, timedelta
from collections import defaultdict
import logging

from backend.models.backtest_result import BacktestResult
from backend.models.trade import Trade

logger = logging.getLogger(__name__)


class ReportGenerator:
    """报告生成器 - 生成详细的回测报告"""

    def generate_report(
        self,
        backtest_result: BacktestResult,
        trades: List[Trade],
        start_time: datetime = None
    ) -> Dict[str, Any]:
        """
        生成完整的回测报告

        Args:
            backtest_result: 回测结果对象
            trades: 交易记录列表
            start_time: 回测开始时间（可选，用于权益曲线初始点）

        Returns:
            {
                'summary': {...},
                'monthly_returns': {...},
                'trade_analysis': {...},
                'equity_curve': [...]
            }
        """
        logger.info(f"Generating report for {len(trades)} trades")

        return {
            'summary': self._generate_summary(backtest_result, trades),
            'monthly_returns': self._calculate_monthly_returns(trades),
            'trade_analysis': self._analyze_trades(trades),
            'equity_curve': self._generate_equity_curve(trades, backtest_result.initial_cash, start_time)
        }

    def _generate_summary(
        self,
        backtest_result: BacktestResult,
        trades: List[Trade]
    ) -> Dict[str, Any]:
        """
        生成核心指标摘要

        Args:
            backtest_result: 回测结果
            trades: 交易列表

        Returns:
            Summary dict with key metrics
        """
        # Calculate trade-based statistics
        total_trades = len(trades)
        winning_trades = [t for t in trades if hasattr(t, 'pnl') and t.pnl and t.pnl > 0]
        losing_trades = [t for t in trades if hasattr(t, 'pnl') and t.pnl and t.pnl < 0]

        num_winning = len(winning_trades)
        num_losing = len(losing_trades)

        # Win rate (stored as decimal, e.g., 0.4677 for 46.77%)
        win_rate = (num_winning / total_trades) if total_trades > 0 else 0.0

        # Average trades
        if total_trades > 0:
            all_pnls = [t.pnl for t in trades if hasattr(t, 'pnl') and t.pnl is not None]
            average_trade = sum(all_pnls) / len(all_pnls) if all_pnls else 0.0
        else:
            average_trade = 0.0

        average_winning_trade = (
            sum([t.pnl for t in winning_trades]) / num_winning
            if num_winning > 0 else 0.0
        )

        average_losing_trade = (
            sum([t.pnl for t in losing_trades]) / num_losing
            if num_losing > 0 else 0.0
        )

        # Profit factor
        gross_profit = sum([t.pnl for t in winning_trades]) if winning_trades else 0.0
        gross_loss = abs(sum([t.pnl for t in losing_trades])) if losing_trades else 0.0

        if gross_loss > 0:
            profit_factor = gross_profit / gross_loss
        elif gross_profit > 0:
            profit_factor = float('inf')  # No losses
        else:
            profit_factor = 0.0  # No profits

        return {
            # From BacktestResult
            'total_return': backtest_result.total_return,
            'annual_return': backtest_result.annual_return,
            'final_value': backtest_result.final_value,
            'initial_cash': backtest_result.initial_cash,
            'max_drawdown': backtest_result.max_drawdown,
            'sharpe_ratio': backtest_result.sharpe_ratio,

            # From trades
            'total_trades': total_trades,
            'winning_trades': num_winning,
            'losing_trades': num_losing,
            'win_rate': win_rate,

            # Calculated from trades
            'avg_trade': average_trade,
            'avg_winning_trade': average_winning_trade,
            'avg_losing_trade': average_losing_trade,
            'gross_profit': gross_profit,
            'gross_loss': gross_loss,
            'profit_factor': profit_factor
        }

    def _calculate_monthly_returns(
        self,
        trades: List[Trade]
    ) -> Dict[str, float]:
        """
        计算月度收益率

        Args:
            trades: 交易列表

        Returns:
            Dict mapping 'YYYY-MM' to monthly return percentage
        """
        if not trades:
            return {}

        # Group trades by month
        monthly_pnl = defaultdict(float)

        for trade in trades:
            pnl = trade.pnl if hasattr(trade, 'pnl') and trade.pnl is not None else 0.0

            # Extract year-month from timestamp
            month_key = trade.timestamp.strftime('%Y-%m')
            monthly_pnl[month_key] += pnl

        # Convert to regular dict and sort by date
        monthly_returns = dict(sorted(monthly_pnl.items()))

        logger.debug(f"Calculated monthly returns for {len(monthly_returns)} months")
        return monthly_returns

    def _analyze_trades(
        self,
        trades: List[Trade]
    ) -> Dict[str, Any]:
        """
        分析交易统计

        Args:
            trades: 交易列表

        Returns:
            {
                'trades': [...],  # List of trade details
                'long_trades': int,
                'short_trades': int,
                'avg_hold_time': float,
                'best_trade': float,
                'worst_trade': float
            }
        """
        if not trades:
            return {
                'trades': [],
                'long_trades': 0,
                'short_trades': 0,
                'avg_hold_time': 0.0,
                'best_trade': 0.0,
                'worst_trade': 0.0
            }

        # Prepare trade details list
        trades_list = []
        for idx, trade in enumerate(trades, 1):
            pnl = trade.pnl if hasattr(trade, 'pnl') and trade.pnl is not None else 0.0
            entry_price = trade.entry_price if hasattr(trade, 'entry_price') and trade.entry_price is not None else trade.price
            exit_price = trade.exit_price if hasattr(trade, 'exit_price') and trade.exit_price is not None else trade.price

            # Get entry and exit times
            # Try new fields first (entry_time, exit_time), fallback to timestamp
            if hasattr(trade, 'entry_time') and trade.entry_time is not None:
                entry_dt = trade.entry_time
            else:
                entry_dt = trade.timestamp

            if hasattr(trade, 'exit_time') and trade.exit_time is not None:
                exit_dt = trade.exit_time
            else:
                exit_dt = trade.timestamp

            # Calculate hold duration in seconds
            hold_duration = (exit_dt - entry_dt).total_seconds() if entry_dt and exit_dt else 0.0

            trade_detail = {
                'trade_no': idx,
                'entry_time': entry_dt.isoformat(),
                'exit_time': exit_dt.isoformat(),
                'side': trade.side,
                'entry_price': entry_price,
                'exit_price': exit_price,
                'size': trade.size,
                'pnl': pnl,
                'commission': trade.commission,
                'hold_duration': hold_duration
            }
            trades_list.append(trade_detail)

        # Calculate statistics
        pnls = [t.pnl for t in trades if hasattr(t, 'pnl') and t.pnl is not None]

        # Long vs short
        long_trades = sum(1 for t in trades if t.side == 'BUY')
        short_trades = sum(1 for t in trades if t.side == 'SELL')

        # Average hold time (simplified - would need proper entry/exit tracking)
        hold_times = [t['hold_duration'] for t in trades_list]
        avg_hold_time = (sum(hold_times) / len(hold_times) / 3600.0) if hold_times else 0  # Convert to hours

        # Best and worst trades
        best_trade = max(pnls) if pnls else 0.0
        worst_trade = min(pnls) if pnls else 0.0

        logger.debug(f"Analyzed {len(trades)} trades: {long_trades} long, {short_trades} short")

        return {
            'trades': trades_list,
            'long_trades': long_trades,
            'short_trades': short_trades,
            'avg_hold_time': avg_hold_time,
            'best_trade': best_trade,
            'worst_trade': worst_trade
        }

    def _generate_equity_curve(
        self,
        trades: List[Trade],
        initial_cash: float,
        start_time: datetime = None
    ) -> List[Dict[str, Any]]:
        """
        生成资金曲线

        Args:
            trades: 交易列表
            initial_cash: 初始资金
            start_time: 回测开始时间（可选，用于添加初始资金点）

        Returns:
            List of {'time': str, 'value': float}
        """
        if not trades:
            return []

        equity_curve = []
        cumulative_pnl = 0.0

        # Sort trades by timestamp to ensure chronological order
        sorted_trades = sorted(trades, key=lambda t: t.timestamp)

        # Add initial point if start_time is provided
        if start_time is not None:
            equity_curve.append({
                'time': start_time.isoformat(),
                'value': initial_cash
            })

        for trade in sorted_trades:
            pnl = trade.pnl if hasattr(trade, 'pnl') and trade.pnl is not None else 0.0
            cumulative_pnl += pnl

            portfolio_value = initial_cash + cumulative_pnl

            equity_curve.append({
                'time': trade.timestamp.isoformat(),
                'value': portfolio_value
            })

        logger.debug(f"Generated equity curve with {len(equity_curve)} points")
        return equity_curve
