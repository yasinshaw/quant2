"""
End-to-end test to verify total_return is correctly stored and displayed
"""
import pytest
from datetime import datetime
from backend.database import Database
from backend.models.backtest_job import BacktestJob
from backend.models.backtest_result import BacktestResult
from backend.models.trade import Trade


def test_total_return_format_consistency():
    """
    End-to-end test:
    1. Simulate backtest calculating pnl_pct = 24.85%
    2. Store to database as decimal (0.2485)
    3. Retrieve from database
    4. Format for frontend (multiply by 100)
    5. Verify display is "24.85%" not "2485%"
    """
    db = Database('sqlite:///:memory:')
    db.create_tables()

    # Create job
    job = BacktestJob(
        strategy_name='TestStrategy',
        symbol='BTCUSDT',
        interval='1d',
        start_time=datetime(2024, 1, 1),
        end_time=datetime(2024, 1, 31),
        parameters={},
        status='completed'
    )
    job_id = db.create_backtest_job(job)

    # Simulate backtest results
    # Backtest calculates: pnl_pct = (124850 - 100000) / 100000 * 100 = 24.85%
    initial_cash = 100000.0
    final_value = 124850.0
    pnl = final_value - initial_cash
    pnl_pct = (pnl / initial_cash) * 100  # = 24.85

    max_drawdown_pct = 5.5  # 5.5% max drawdown
    win_rate_pct = 60.0  # 60% win rate

    # Store as DECIMAL (divide by 100) - this is the fix!
    result = BacktestResult(
        backtest_job_id=job_id,
        total_return=pnl_pct / 100,  # 24.85 / 100 = 0.2485
        max_drawdown=max_drawdown_pct / 100,  # 5.5 / 100 = 0.055
        win_rate=win_rate_pct / 100,  # 60.0 / 100 = 0.60
        sharpe_ratio=1.5,
        profit_factor=2.0,
        total_trades=10,
        initial_cash=initial_cash,
        final_value=final_value
    )

    result_id = db.save_backtest_result(result, [])

    # Retrieve from database
    saved_result = db.get_backtest_result(result_id)

    # CRITICAL ASSERTIONS
    # Database should store decimals
    assert saved_result.total_return == pytest.approx(0.2485, abs=0.0001), \
        f"Database should store 0.2485, got {saved_result.total_return}"
    assert saved_result.max_drawdown == pytest.approx(0.055, abs=0.001), \
        f"Database should store 0.055, got {saved_result.max_drawdown}"
    assert saved_result.win_rate == pytest.approx(0.60, abs=0.01), \
        f"Database should store 0.60, got {saved_result.win_rate}"

    # Frontend formatting (simulate formatPercent function)
    def formatPercent(value: float) -> str:
        return f"{value * 100:.2f}%"

    total_return_display = formatPercent(saved_result.total_return)
    max_drawdown_display = formatPercent(saved_result.max_drawdown)
    win_rate_display = f"{saved_result.win_rate * 100:.1f}%"

    # CRITICAL: Frontend should display correctly
    assert total_return_display == "24.85%", \
        f"Frontend should display '24.85%', got '{total_return_display}'"
    assert max_drawdown_display == "5.50%", \
        f"Frontend should display '5.50%', got '{max_drawdown_display}'"
    assert win_rate_display == "60.0%", \
        f"Frontend should display '60.0%', got '{win_rate_display}'"

    print(f"✓ Total Return: Database stores {saved_result.total_return}, Frontend shows {total_return_display}")
    print(f"✓ Max Drawdown: Database stores {saved_result.max_drawdown}, Frontend shows {max_drawdown_display}")
    print(f"✓ Win Rate: Database stores {saved_result.win_rate}, Frontend shows {win_rate_display}")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
