import pytest
import numpy as np
from backend.core.monte_carlo import MonteCarloSimulator, MonteCarloResult


class TestMonteCarloSimulator:
    def test_simulate_returns_result_with_correct_fields(self):
        pnl = [100, -50, 200, -30, 80, -20, 150, -60, 90, -10]
        result = MonteCarloSimulator.simulate(
            trades_pnl=pnl,
            initial_cash=100000,
            original_return=0.45,
            original_max_drawdown=0.05,
            num_simulations=100,
        )
        assert isinstance(result, MonteCarloResult)
        assert result.num_simulations == 100
        assert len(result.final_returns) == 100
        assert len(result.max_drawdowns) == 100
        assert len(result.equity_curves) == 100
        assert result.original_return == 0.45
        assert result.original_max_drawdown == 0.05

    def test_simulate_preserves_total_pnl(self):
        """Each simulation should have the same total PnL as original."""
        pnl = [100, -50, 200, -30, 80]
        total_pnl = sum(pnl)
        initial_cash = 100000
        result = MonteCarloSimulator.simulate(
            trades_pnl=pnl,
            initial_cash=initial_cash,
            original_return=0.3,
            original_max_drawdown=0.05,
            num_simulations=50,
        )
        expected_return = total_pnl / initial_cash
        for ret in result.final_returns:
            assert abs(ret - expected_return) < 1e-10

    def test_simulate_max_drawdowns_are_positive(self):
        pnl = [100, -200, 300, -50, 80, -30, 200, -100, 50, -20]
        result = MonteCarloSimulator.simulate(
            trades_pnl=pnl,
            initial_cash=100000,
            original_return=0.33,
            original_max_drawdown=0.2,
            num_simulations=100,
        )
        for dd in result.max_drawdowns:
            assert dd >= 0

    def test_simulate_statistics_in_range(self):
        pnl = [100, -50, 200, -30, 80, -20, 150, -60, 90, -10]
        result = MonteCarloSimulator.simulate(
            trades_pnl=pnl,
            initial_cash=100000,
            original_return=0.45,
            original_max_drawdown=0.05,
            num_simulations=1000,
        )
        assert 0 <= result.ruin_probability <= 1
        assert result.p5_return <= result.median_return <= result.p95_return
        assert result.median_max_drawdown <= result.p95_max_drawdown

    def test_simulate_equity_curves_sampled_length(self):
        pnl = [100, -50, 200, -30, 80, -20, 150, -60, 90, -10]
        result = MonteCarloSimulator.simulate(
            trades_pnl=pnl,
            initial_cash=100000,
            original_return=0.45,
            original_max_drawdown=0.05,
            num_simulations=10,
        )
        expected_len = min(len(pnl), 100)
        for curve in result.equity_curves:
            assert len(curve) == expected_len

    def test_simulate_ruin_probability_with_large_losses(self):
        """When a single loss can wipe 50%+, some shuffles should cause ruin."""
        pnl = [-60000, 100, 100, 100, 100]
        result = MonteCarloSimulator.simulate(
            trades_pnl=pnl,
            initial_cash=100000,
            original_return=-0.596,
            original_max_drawdown=0.6,
            num_simulations=1000,
        )
        assert result.ruin_probability > 0

    def test_simulate_requires_minimum_trades(self):
        with pytest.raises(ValueError, match="at least 2 trades"):
            MonteCarloSimulator.simulate(
                trades_pnl=[100],
                initial_cash=100000,
                original_return=0.001,
                original_max_drawdown=0.0,
                num_simulations=100,
            )
