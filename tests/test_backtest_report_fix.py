"""
Test for backtest report generation fix

This test verifies that the backtest API correctly converts trade dictionaries
to Trade objects before passing them to the report generator.

Related issue: 'dict' object has no attribute 'timestamp'
"""
import pytest
from datetime import datetime
from backend.models.trade import Trade
from backend.core.report_generator import ReportGenerator


def test_report_generation_with_trade_dicts():
    """Test that report generator works with Trade objects converted from dicts"""
    generator = ReportGenerator()

    # Create sample trade data (as returned by BacktestEngine)
    trade_dicts = [
        {
            'entry_time': '2024-01-15T10:00:00',
            'exit_time': '2024-01-15T14:00:00',
            'side': 'BUY',
            'entry_price': 42000.0,
            'exit_price': 42500.0,
            'size': 1.0,
            'commission': 10.0,
            'pnl': 490.0
        },
        {
            'entry_time': '2024-01-16T09:00:00',
            'exit_time': '2024-01-16T15:00:00',
            'side': 'SELL',
            'entry_price': 43000.0,
            'exit_price': 42500.0,
            'size': 1.0,
            'commission': 10.0,
            'pnl': -510.0
        }
    ]

    # Convert to Trade objects (as done in backtest.py)
    trade_objects = []
    for trade_data in trade_dicts:
        trade_obj = Trade(
            backtest_job_id=0,
            order_id=None,
            symbol='BTCUSDT',
            side=trade_data['side'],
            price=trade_data['exit_price'],
            size=trade_data['size'],
            commission=trade_data['commission'],
            timestamp=datetime.fromisoformat(trade_data['exit_time'])
        )
        # Add pnl as an attribute (not a database field)
        trade_obj.pnl = trade_data['pnl']
        trade_objects.append(trade_obj)

    # Create BacktestResult
    from backend.models.backtest_result import BacktestResult
    backtest_result = BacktestResult(
        backtest_job_id=0,
        total_return=0.5,
        annual_return=None,
        sharpe_ratio=None,
        max_drawdown=0.0,
        win_rate=50.0,
        profit_factor=1.0,
        total_trades=2,
        initial_cash=100000.0,
        final_value=100000.5
    )

    # Generate report - this should not raise AttributeError
    report = generator.generate_report(backtest_result, trade_objects)

    # Verify report structure
    assert 'summary' in report
    assert 'monthly_returns' in report
    assert 'trade_analysis' in report
    assert 'equity_curve' in report

    # Verify monthly returns calculation
    assert isinstance(report['monthly_returns'], dict)

    # Verify trade analysis
    assert report['trade_analysis']['long_trades'] == 1
    assert report['trade_analysis']['short_trades'] == 1


def test_report_generator_handles_empty_trades():
    """Test that report generator handles empty trade list"""
    generator = ReportGenerator()

    from backend.models.backtest_result import BacktestResult
    backtest_result = BacktestResult(
        backtest_job_id=0,
        total_return=0.0,
        annual_return=None,
        sharpe_ratio=None,
        max_drawdown=0.0,
        win_rate=0.0,
        profit_factor=0.0,
        total_trades=0,
        initial_cash=100000.0,
        final_value=100000.0
    )

    # Generate report with empty trades list
    report = generator.generate_report(backtest_result, [])

    # Verify report structure
    assert 'summary' in report
    assert 'monthly_returns' in report
    assert report['monthly_returns'] == {}
    assert 'trade_analysis' in report
    assert 'equity_curve' in report
