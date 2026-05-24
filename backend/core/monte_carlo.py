"""Monte Carlo simulation for strategy robustness analysis."""
import numpy as np
from dataclasses import dataclass
from typing import List


@dataclass
class MonteCarloResult:
    """Result of Monte Carlo simulation."""
    num_simulations: int
    equity_curves: List[List[float]]
    final_returns: List[float]
    max_drawdowns: List[float]
    median_return: float
    p5_return: float
    p95_return: float
    median_max_drawdown: float
    p95_max_drawdown: float
    ruin_probability: float
    original_return: float
    original_max_drawdown: float


class MonteCarloSimulator:
    """Runs Monte Carlo simulation by shuffling trade order."""

    RUIN_THRESHOLD = 0.5

    @staticmethod
    def simulate(
        trades_pnl: List[float],
        initial_cash: float,
        original_return: float,
        original_max_drawdown: float,
        num_simulations: int = 1000,
    ) -> MonteCarloResult:
        if len(trades_pnl) < 2:
            raise ValueError("Monte Carlo simulation requires at least 2 trades")

        pnl_array = np.array(trades_pnl, dtype=np.float64)
        n_trades = len(pnl_array)

        all_curves = np.zeros((num_simulations, n_trades + 1))
        all_curves[:, 0] = initial_cash

        for i in range(num_simulations):
            shuffled = pnl_array.copy()
            np.random.shuffle(shuffled)
            cumulative_pnl = np.cumsum(shuffled)
            all_curves[i, 1:] = initial_cash + cumulative_pnl

        final_values = all_curves[:, -1]
        final_returns = (final_values - initial_cash) / initial_cash

        max_drawdowns = np.zeros(num_simulations)
        for i in range(num_simulations):
            curve = all_curves[i]
            peak = np.maximum.accumulate(curve)
            drawdowns = (peak - curve) / peak
            max_drawdowns[i] = np.max(drawdowns)

        min_equity = np.min(all_curves, axis=1)
        ruin_mask = min_equity < (initial_cash * MonteCarloSimulator.RUIN_THRESHOLD)
        ruin_probability = float(np.mean(ruin_mask))

        sample_count = min(n_trades, 100)
        sample_indices = np.linspace(0, n_trades, sample_count, dtype=int)
        if sample_indices[0] != 0:
            sample_indices[0] = 0

        equity_curves = []
        for i in range(num_simulations):
            equity_curves.append(all_curves[i, sample_indices].tolist())

        return MonteCarloResult(
            num_simulations=num_simulations,
            equity_curves=equity_curves,
            final_returns=final_returns.tolist(),
            max_drawdowns=max_drawdowns.tolist(),
            median_return=float(np.median(final_returns)),
            p5_return=float(np.percentile(final_returns, 5)),
            p95_return=float(np.percentile(final_returns, 95)),
            median_max_drawdown=float(np.median(max_drawdowns)),
            p95_max_drawdown=float(np.percentile(max_drawdowns, 95)),
            ruin_probability=ruin_probability,
            original_return=original_return,
            original_max_drawdown=original_max_drawdown,
        )
