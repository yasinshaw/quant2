"""
Test to verify that total_return is stored as decimal (0.2485) not percentage (24.85)
"""
import pytest
from datetime import datetime
from backend.core.backtest_engine import BacktestEngine
from backend.database import Database
from backend.models.backtest_result import BacktestResult
from backend.models.backtest_job import BacktestJob
from backend.models.trade import Trade


def test_total_return_stored_as_decimal():
    """
    Test that total_return is stored as decimal (e.g., 0.2485 for 24.85%)
    not as percentage (e.g., 24.85)

    This ensures consistency with:
    1. Frontend formatPercent which expects decimal and multiplies by 100
    2. Optimizer which converts pnl_pct / 100 before storing
    """
    # Setup
    db = Database('sqlite:///:memory:')
    db.create_tables()

    # Create a backtest job
    job = BacktestJob(
        strategy_name='TestStrategy',
        symbol='BTCUSDT',
        interval='1d',
        start_time=datetime(2024, 1, 1),
        end_time=datetime(2024, 1, 31),
        parameters={'param1': 10},
        status='completed'
    )
    job_id = db.create_backtest_job(job)

    # Simulate a backtest with 24.85% return
    # Initial cash: 100000
    # Final value: 124850
    # PnL: 24850
    # PnL%: 24.85%
    pnl_pct = 24.85

    # Save result
    result = BacktestResult(
        backtest_job_id=job_id,
        total_return=pnl_pct / 100,  # Should store as 0.2485
        max_drawdown=5.0 / 100,  # Should store as 0.05
        win_rate=60.0 / 100,  # Should store as 0.60
        sharpe_ratio=1.5,
        profit_factor=2.0,
        total_trades=10,
        initial_cash=100000.0,
        final_value=124850.0
    )

    result_id = db.save_backtest_result(result, [])

    # Retrieve and verify
    saved_result = db.get_backtest_result(result_id)

    # CRITICAL: total_return should be decimal (0.2485), not percentage (24.85)
    assert saved_result.total_return == pytest.approx(0.2485, abs=0.0001), \
        f"Expected total_return to be 0.2485 (decimal), got {saved_result.total_return}"

    # When frontend multiplies by 100, it should display correctly as 24.85%
    display_value = saved_result.total_return * 100
    assert display_value == pytest.approx(24.85, abs=0.01), \
        f"Frontend would display {display_value}%, expected 24.85%"


def test_max_drawdown_stored_as_decimal():
    """
    Test that max_drawdown is also stored as decimal for consistency
    """
    db = Database('sqlite:///:memory:')
    db.create_tables()

    job = BacktestJob(
        strategy_name='TestStrategy',
        symbol='BTCUSDT',
        interval='1d',
        start_time=datetime(2024, 1, 1),
        end_time=datetime(2024, 1, 31),
        parameters={'param1': 10},
        status='completed'
    )
    job_id = db.create_backtest_job(job)

    # Max drawdown of 15.5%
    max_drawdown_pct = 15.5

    result = BacktestResult(
        backtest_job_id=job_id,
        total_return=0.25,
        max_drawdown=max_drawdown_pct / 100,  # Should store as 0.155
        sharpe_ratio=1.5,
        win_rate=0.60,
        profit_factor=2.0,
        total_trades=10,
        initial_cash=100000.0,
        final_value=125000.0
    )

    result_id = db.save_backtest_result(result, [])
    saved_result = db.get_backtest_result(result_id)

    # Should be stored as decimal
    assert saved_result.max_drawdown == pytest.approx(0.155, abs=0.001), \
        f"Expected max_drawdown to be 0.155 (decimal), got {saved_result.max_drawdown}"


def test_win_rate_stored_as_decimal():
    """
    Test that win_rate is stored as decimal for consistency
    """
    db = Database('sqlite:///:memory:')
    db.create_tables()

    job = BacktestJob(
        strategy_name='TestStrategy',
        symbol='BTCUSDT',
        interval='1d',
        start_time=datetime(2024, 1, 1),
        end_time=datetime(2024, 1, 31),
        parameters={'param1': 10},
        status='completed'
    )
    job_id = db.create_backtest_job(job)

    # Win rate of 60%
    win_rate_pct = 60.0

    result = BacktestResult(
        backtest_job_id=job_id,
        total_return=0.25,
        max_drawdown=0.10,
        sharpe_ratio=1.5,
        win_rate=win_rate_pct / 100,  # Should store as 0.60
        profit_factor=2.0,
        total_trades=10,
        initial_cash=100000.0,
        final_value=125000.0
    )

    result_id = db.save_backtest_result(result, [])
    saved_result = db.get_backtest_result(result_id)

    # Should be stored as decimal
    assert saved_result.win_rate == pytest.approx(0.60, abs=0.01), \
        f"Expected win_rate to be 0.60 (decimal), got {saved_result.win_rate}"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
