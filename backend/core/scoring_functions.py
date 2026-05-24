"""
Composite Scoring Functions for Parameter Optimization

Provides multi-metric scoring functions that balance returns with risk,
replacing single-metric optimization (e.g., PnL-only).

Anti-overfitting protections:
1. Minimum trade count threshold - penalizes "do nothing" strategies
2. Calmar ratio - rewards return relative to drawdown
3. Trade frequency bonus - rewards strategies with enough samples
"""

from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

# Default weights prioritize Sharpe ratio while considering returns and risk
DEFAULT_WEIGHTS = {
    'sharpe_ratio': 0.3,
    'calmar_ratio': 0.2,     # Return / Max Drawdown (replaces raw return)
    'max_drawdown': -0.15,   # Negative: smaller drawdown is better
    'win_rate': 0.1,
    'trade_frequency': 0.1,  # Bonus for sufficient trade count
    'profit_factor': 0.15,   # Gross profit / Gross loss
}

# Minimum trades needed for statistical significance
# Below this, the score is heavily penalized
MIN_TRADES_ABSOLUTE = 5   # Below this: score = 0
MIN_TRADES_ADEQUATE = 20  # At this point: no penalty


def calculate_composite_score(
    backtest_result: Dict[str, Any],
    weights: Optional[Dict[str, float]] = None
) -> float:
    """
    Calculate composite score from backtest metrics.

    Anti-overfitting protections:
    1. Minimum trade count: < 5 trades → score = 0
    2. Trade count penalty: < 20 trades → reduced score
    3. Calmar ratio: return relative to drawdown (not just raw return)
    4. Profit factor: gross profit / gross loss (rewards consistency)

    Args:
        backtest_result: Dict containing metrics like 'sharpe_ratio',
            'pnl_pct', 'max_drawdown', 'win_rate', 'total_trades'
        weights: Optional custom weights dict. Uses DEFAULT_WEIGHTS if None.

    Returns:
        Composite score between 0 and 1 (higher is better)
    """
    if weights is None:
        weights = DEFAULT_WEIGHTS

    total_trades = backtest_result.get('total_trades', 0)

    # Protection 1: Absolute minimum trade count
    if total_trades < MIN_TRADES_ABSOLUTE:
        logger.debug(
            f"Score=0: only {total_trades} trades "
            f"(minimum {MIN_TRADES_ABSOLUTE})"
        )
        return 0.0

    score = 0.0

    # --- Sharpe Ratio ---
    sharpe = backtest_result.get('sharpe_ratio')
    if sharpe is not None:
        sharpe_normalized = max(0, min(sharpe / 3.0, 1.0))
        score += sharpe_normalized * weights.get('sharpe_ratio', 0)

    # --- Calmar Ratio (Return / Max Drawdown) ---
    # Replaces raw total_return to penalize "low drawdown but also low return"
    pnl_pct = backtest_result.get('pnl_pct', 0)
    max_drawdown = backtest_result.get('max_drawdown', 0)
    calmar_weight = weights.get('calmar_ratio', 0)

    if calmar_weight > 0:
        drawdown_abs = abs(max_drawdown)
        if drawdown_abs > 0 and pnl_pct > 0:
            calmar = pnl_pct / drawdown_abs
            # Calmar > 3.0 is excellent, normalize to 0-1
            calmar_normalized = min(calmar / 3.0, 1.0)
            score += calmar_normalized * calmar_weight
        elif pnl_pct <= 0:
            # Negative return → 0 calmar score
            pass
        elif drawdown_abs == 0 and pnl_pct > 0:
            # Zero drawdown with positive return → cap at 0.8
            # (zero drawdown is suspicious, likely too few trades)
            score += 0.8 * calmar_weight

    # --- Max Drawdown ---
    dd_weight = weights.get('max_drawdown', 0)
    if dd_weight != 0 and max_drawdown is not None:
        drawdown_abs = abs(max_drawdown) / 100
        drawdown_score = max(0, 1 - drawdown_abs / 0.5)
        score += drawdown_score * abs(dd_weight)

    # --- Win Rate ---
    win_rate = backtest_result.get('win_rate')
    wr_weight = weights.get('win_rate', 0)
    if wr_weight > 0 and win_rate is not None:
        win_rate_normalized = max(0, min(win_rate / 100, 1.0))
        score += win_rate_normalized * wr_weight

    # --- Trade Frequency Bonus ---
    # Rewards strategies with enough trades for statistical significance
    tf_weight = weights.get('trade_frequency', 0)
    if tf_weight > 0:
        # Sigmoid-like: full bonus at MIN_TRADES_ADEQUATE, half at ~12
        if total_trades >= MIN_TRADES_ADEQUATE:
            freq_normalized = 1.0
        else:
            freq_normalized = total_trades / MIN_TRADES_ADEQUATE
        score += freq_normalized * tf_weight

    # --- Profit Factor (Gross Profit / Gross Loss) ---
    pf_weight = weights.get('profit_factor', 0)
    if pf_weight > 0 and total_trades > 0:
        pf = _calculate_profit_factor(backtest_result)
        if pf is not None:
            # Profit factor > 2.0 is good, > 3.0 is excellent
            pf_normalized = min(pf / 3.0, 1.0)
            score += pf_normalized * pf_weight

    # Protection 2: Penalty for too few trades
    if total_trades < MIN_TRADES_ADEQUATE:
        # Linear penalty from MIN_TRADES_ABSOLUTE to MIN_TRADES_ADEQUATE
        # At MIN_TRADES_ABSOLUTE: penalty = 0.5
        # At MIN_TRADES_ADEQUATE: penalty = 0
        penalty_ratio = 1 - (total_trades - MIN_TRADES_ABSOLUTE) / (MIN_TRADES_ADEQUATE - MIN_TRADES_ABSOLUTE)
        penalty = penalty_ratio * 0.5
        score *= (1 - penalty)

    # Protection 3: Indicator participation penalty
    # If an enabled indicator (RSI, BB) never produces a directional signal,
    # it means the optimizer effectively "disabled" it with extreme parameters
    signal_stats = backtest_result.get('signal_stats')
    if signal_stats and signal_stats.get('confirmation_checks', 0) > 0:
        checks = signal_stats['confirmation_checks']
        indicator_penalties = 0.0

        for indicator_name, confirmed_key in [
            ('macd', 'macd_confirmed'),
            ('rsi', 'rsi_confirmed'),
            ('bollinger', 'bollinger_confirmed'),
        ]:
            confirmed = signal_stats.get(confirmed_key, 0)
            participation_rate = confirmed / checks if checks > 0 else 0

            # If an indicator participates in < 5% of confirmations, it's effectively disabled
            # This catches cases like RSI(26, oversold=22) which never triggers
            if participation_rate < 0.05:
                indicator_penalties += 0.15  # 15% penalty per disabled indicator

        if indicator_penalties > 0:
            score *= max(0.1, 1 - min(indicator_penalties, 0.5))
            logger.debug(
                f"Indicator participation penalty: {indicator_penalties:.2f}, "
                f"stats: macd={signal_stats.get('macd_confirmed',0)}/{checks}, "
                f"rsi={signal_stats.get('rsi_confirmed',0)}/{checks}, "
                f"bb={signal_stats.get('bollinger_confirmed',0)}/{checks}"
            )

    return max(0, min(score, 1))


def _calculate_profit_factor(backtest_result: Dict[str, Any]) -> Optional[float]:
    """
    Calculate profit factor from trades or estimate from win rate + avg win/loss.

    Profit Factor = Gross Profit / Gross Loss
    > 1.5 is good, > 2.0 is excellent

    Args:
        backtest_result: Dict with trades or win_rate/pnl info

    Returns:
        Profit factor or None if cannot calculate
    """
    trades = backtest_result.get('trades', [])
    if trades:
        gross_profit = sum(t.get('pnl', 0) for t in trades if t.get('pnl', 0) > 0)
        gross_loss = abs(sum(t.get('pnl', 0) for t in trades if t.get('pnl', 0) < 0))
        if gross_loss > 0:
            return gross_profit / gross_loss
        elif gross_profit > 0:
            return 10.0  # All wins, cap at 10
        return None

    # Estimate from win_rate and total return if no trade details
    win_rate = backtest_result.get('win_rate', 0) / 100
    total_trades = backtest_result.get('total_trades', 0)
    pnl_pct = backtest_result.get('pnl_pct', 0)

    if total_trades < 2 or win_rate <= 0 or win_rate >= 1:
        return None

    # Estimate: pnl = wins * avg_win - losses * avg_loss
    # profit_factor = (wins * avg_win) / (losses * avg_loss)
    # Simplified estimate from win_rate and net pnl
    return max(0.1, (win_rate * pnl_pct) / max(abs((1 - win_rate) * pnl_pct), 1))
