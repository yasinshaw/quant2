"""
Unit tests for ReportGenerator class

Tests verify:
1. Complete report generation with all sections
2. Monthly returns calculation (single month, multiple months, year boundary)
3. Trade analysis (statistics, long/short, best/worst trades)
4. Equity curve generation (cumulative PnL over time)
5. Edge cases (no trades, single trade, all winning, all losing)
"""
import pytest
from datetime import datetime, timedelta
from typing import Dict, Any, List

from backend.core.report_generator import ReportGenerator
from backend.models.backtest_result import BacktestResult
from backend.models.trade import Trade


# ========================================
# Test Fixtures
# ========================================

@pytest.fixture
def report_generator():
    """Create a ReportGenerator instance"""
    return ReportGenerator()


@pytest.fixture
def sample_backtest_result():
    """Create a sample BacktestResult"""
    return BacktestResult(
        backtest_job_id=1,
        total_return=15.5,
        annual_return=78.2,
        sharpe_ratio=1.85,
        max_drawdown=-8.3,
        win_rate=62.5,
        profit_factor=2.1,
        total_trades=24,
        initial_cash=100000.0,
        final_value=115500.0
    )


@pytest.fixture
def sample_trades():
    """Create sample trades for testing (January to March 2024)"""
    base_time = datetime(2024, 1, 1, 10, 0, 0)
    trades = []

    # January: 3 winning trades
    for i in range(3):
        entry_time = base_time + timedelta(days=i*3)
        exit_time = entry_time + timedelta(hours=6)
        trades.append(Trade(
            backtest_job_id=1,
            order_id=f'order_{i}',
            symbol='BTCUSDT',
            side='BUY',
            price=100.0 + i,
            size=1.0,
            commission=0.1,
            timestamp=exit_time
        ))
        # Manually set PnL for testing (would normally be calculated)
        trades[-1].pnl = 50.0 + i * 10

    # February: 2 losing trades
    for i in range(2):
        entry_time = base_time + timedelta(days=31 + i*4)
        exit_time = entry_time + timedelta(hours=8)
        trades.append(Trade(
            backtest_job_id=1,
            order_id=f'order_{i+3}',
            symbol='BTCUSDT',
            side='SELL',
            price=110.0 + i,
            size=0.5,
            commission=0.05,
            timestamp=exit_time
        ))
        trades[-1].pnl = -30.0 - i * 5

    # March: 2 winning trades
    for i in range(2):
        entry_time = base_time + timedelta(days=60 + i*5)
        exit_time = entry_time + timedelta(hours=4)
        trades.append(Trade(
            backtest_job_id=1,
            order_id=f'order_{i+5}',
            symbol='BTCUSDT',
            side='BUY',
            price=115.0 + i,
            size=0.8,
            commission=0.08,
            timestamp=exit_time
        ))
        trades[-1].pnl = 40.0 + i * 15

    return trades


@pytest.fixture
def empty_trades():
    """Empty trades list for edge case testing"""
    return []


@pytest.fixture
def all_winning_trades():
    """All winning trades"""
    base_time = datetime(2024, 1, 1, 10, 0, 0)
    trades = []
    for i in range(5):
        entry_time = base_time + timedelta(days=i)
        exit_time = entry_time + timedelta(hours=2)
        trades.append(Trade(
            backtest_job_id=1,
            order_id=f'order_{i}',
            symbol='BTCUSDT',
            side='BUY',
            price=100.0,
            size=1.0,
            commission=0.1,
            timestamp=exit_time
        ))
        trades[-1].pnl = 50.0 + i * 10
    return trades


@pytest.fixture
def all_losing_trades():
    """All losing trades"""
    base_time = datetime(2024, 1, 1, 10, 0, 0)
    trades = []
    for i in range(5):
        entry_time = base_time + timedelta(days=i)
        exit_time = entry_time + timedelta(hours=2)
        trades.append(Trade(
            backtest_job_id=1,
            order_id=f'order_{i}',
            symbol='BTCUSDT',
            side='SELL',
            price=100.0,
            size=1.0,
            commission=0.1,
            timestamp=exit_time
        ))
        trades[-1].pnl = -40.0 - i * 10
    return trades


@pytest.fixture
def single_trade():
    """Single trade for edge case testing"""
    return [Trade(
        backtest_job_id=1,
        order_id='order_0',
        symbol='BTCUSDT',
        side='BUY',
        price=100.0,
        size=1.0,
        commission=0.1,
        timestamp=datetime(2024, 1, 1, 12, 0, 0)
    )]


# ========================================
# Test Report Generation
# ========================================

class TestReportGeneration:
    """Test complete report generation"""

    def test_generate_full_report(self, report_generator, sample_backtest_result, sample_trades):
        """Test generating a complete report"""
        report = report_generator.generate_report(sample_backtest_result, sample_trades)

        # Verify all sections are present
        assert 'summary' in report
        assert 'monthly_returns' in report
        assert 'trade_analysis' in report
        assert 'equity_curve' in report

        # Verify summary structure
        summary = report['summary']
        assert 'total_return' in summary
        assert 'final_value' in summary
        assert 'total_trades' in summary
        assert 'win_rate' in summary
        assert 'profit_factor' in summary
        assert 'max_drawdown' in summary
        assert 'sharpe_ratio' in summary
        assert 'avg_trade' in summary
        assert 'avg_winning_trade' in summary
        assert 'avg_losing_trade' in summary

        # Verify monthly_returns is a dict
        assert isinstance(report['monthly_returns'], dict)

        # Verify trade_analysis structure (flat structure)
        trade_analysis = report['trade_analysis']
        assert 'trades' in trade_analysis
        assert 'long_trades' in trade_analysis
        assert 'short_trades' in trade_analysis
        assert 'avg_hold_time' in trade_analysis
        assert 'best_trade' in trade_analysis
        assert 'worst_trade' in trade_analysis

        # Verify equity_curve is a list
        assert isinstance(report['equity_curve'], list)

    def test_report_with_no_trades(self, report_generator, sample_backtest_result, empty_trades):
        """Test report generation with no trades"""
        report = report_generator.generate_report(sample_backtest_result, empty_trades)

        # Should still have all sections
        assert 'summary' in report
        assert 'monthly_returns' in report
        assert 'trade_analysis' in report
        assert 'equity_curve' in report

        # Monthly returns should be empty dict
        assert report['monthly_returns'] == {}

        # Trade list should be empty
        assert report['trade_analysis']['trades'] == []

        # Equity curve should be empty or have just initial value
        assert len(report['equity_curve']) == 0


# ========================================
# Test Monthly Returns Calculation
# ========================================

class TestMonthlyReturns:
    """Test monthly returns calculation"""

    def test_single_month(self, report_generator):
        """Test trades in a single month"""
        # Create trades only in January
        base_time = datetime(2024, 1, 15, 10, 0, 0)
        trades = [
            Trade(
                backtest_job_id=1,
                order_id='order_1',
                symbol='BTCUSDT',
                side='BUY',
                price=100.0,
                size=1.0,
                commission=0.1,
                timestamp=base_time
            ),
            Trade(
                backtest_job_id=1,
                order_id='order_2',
                symbol='BTCUSDT',
                side='BUY',
                price=101.0,
                size=1.0,
                commission=0.1,
                timestamp=base_time + timedelta(days=5)
            )
        ]
        trades[0].pnl = 100.0
        trades[1].pnl = 150.0

        monthly = report_generator._calculate_monthly_returns(trades)

        # Should have only January
        assert '2024-01' in monthly
        assert monthly['2024-01'] == 250.0  # Sum of both trades
        assert len(monthly) == 1

    def test_multiple_months(self, report_generator, sample_trades):
        """Test trades across multiple months"""
        monthly = report_generator._calculate_monthly_returns(sample_trades)

        # Should have 3 months
        assert len(monthly) == 3

        # Verify each month exists
        assert '2024-01' in monthly
        assert '2024-02' in monthly
        assert '2024-03' in monthly

        # Verify returns are calculated correctly
        # January: 50 + 60 + 70 = 180
        assert monthly['2024-01'] == 180.0

        # February: -30 + -35 = -65
        assert monthly['2024-02'] == -65.0

        # March: 40 + 55 = 95
        assert monthly['2024-03'] == 95.0

    def test_year_boundary(self, report_generator):
        """Test trades crossing year boundary (Dec 2023 to Jan 2024)"""
        trades = [
            Trade(
                backtest_job_id=1,
                order_id='order_1',
                symbol='BTCUSDT',
                side='BUY',
                price=100.0,
                size=1.0,
                commission=0.1,
                timestamp=datetime(2023, 12, 28, 10, 0, 0)
            ),
            Trade(
                backtest_job_id=1,
                order_id='order_2',
                symbol='BTCUSDT',
                side='BUY',
                price=101.0,
                size=1.0,
                commission=0.1,
                timestamp=datetime(2024, 1, 3, 10, 0, 0)
            )
        ]
        trades[0].pnl = 100.0
        trades[1].pnl = 150.0

        monthly = report_generator._calculate_monthly_returns(trades)

        # Should have 2 different months
        assert len(monthly) == 2
        assert '2023-12' in monthly
        assert '2024-01' in monthly
        assert monthly['2023-12'] == 100.0
        assert monthly['2024-01'] == 150.0

    def test_empty_trades(self, report_generator, empty_trades):
        """Test monthly returns with no trades"""
        monthly = report_generator._calculate_monthly_returns(empty_trades)
        assert monthly == {}


# ========================================
# Test Trade Analysis
# ========================================

class TestTradeAnalysis:
    """Test trade analysis functionality"""

    def test_trade_statistics(self, report_generator, sample_trades):
        """Test trade statistics calculation"""
        analysis = report_generator._analyze_trades(sample_trades)

        # Verify analysis structure (flat structure, not nested)
        assert 'trades' in analysis
        assert 'long_trades' in analysis
        assert 'short_trades' in analysis
        assert 'avg_hold_time' in analysis
        assert 'best_trade' in analysis
        assert 'worst_trade' in analysis

        # Verify values (5 BUY, 2 SELL in fixture)
        assert len(analysis['trades']) == 7
        assert analysis['long_trades'] == 5
        assert analysis['short_trades'] == 2

    def test_all_winning_trades(self, report_generator, all_winning_trades):
        """Test analysis when all trades are winning"""
        analysis = report_generator._analyze_trades(all_winning_trades)

        assert len(analysis['trades']) == 5
        assert analysis['long_trades'] == 5  # All are BUY in fixture
        assert analysis['short_trades'] == 0
        assert analysis['best_trade'] > 0
        assert analysis['worst_trade'] > 0  # All winning, so worst is also positive

    def test_all_losing_trades(self, report_generator, all_losing_trades):
        """Test analysis when all trades are losing"""
        analysis = report_generator._analyze_trades(all_losing_trades)

        assert len(analysis['trades']) == 5
        assert analysis['long_trades'] == 0  # All are SELL in fixture
        assert analysis['short_trades'] == 5
        assert analysis['best_trade'] < 0  # Best of losing trades
        assert analysis['worst_trade'] < 0

    def test_single_trade(self, report_generator, single_trade):
        """Test analysis with single trade"""
        single_trade[0].pnl = 50.0
        analysis = report_generator._analyze_trades(single_trade)

        assert len(analysis['trades']) == 1
        assert analysis['long_trades'] == 1  # BUY in fixture
        assert analysis['short_trades'] == 0
        assert analysis['best_trade'] == 50.0
        assert analysis['worst_trade'] == 50.0

    def test_trade_details_list(self, report_generator, sample_trades):
        """Test that trade details list is included"""
        analysis = report_generator._analyze_trades(sample_trades)

        # Verify trades list
        assert 'trades' in analysis
        trades_list = analysis['trades']
        assert len(trades_list) == 7

        # Verify each trade has required fields
        for trade in trades_list:
            assert 'entry_time' in trade
            assert 'exit_time' in trade
            assert 'side' in trade
            assert 'entry_price' in trade
            assert 'exit_price' in trade
            assert 'size' in trade
            assert 'pnl' in trade
            assert 'commission' in trade
            assert 'hold_duration' in trade


# ========================================
# Test Equity Curve Generation
# ========================================

class TestEquityCurve:
    """Test equity curve generation"""

    def test_equity_curve_values(self, report_generator, sample_trades):
        """Test equity curve has correct cumulative values"""
        initial_cash = 100000.0
        curve = report_generator._generate_equity_curve(sample_trades, initial_cash)

        # Should have one point per trade
        assert len(curve) == 7

        # Verify cumulative nature
        cumulative_pnl = 0.0
        for i, point in enumerate(curve):
            assert 'time' in point
            assert 'value' in point

            # Portfolio value should be initial_cash + cumulative PnL
            expected_value = initial_cash + cumulative_pnl
            assert point['value'] == pytest.approx(expected_value, rel=0.01)

            # Add this trade's PnL for next iteration
            cumulative_pnl += sample_trades[i].pnl

    def test_equity_curve_chronological_order(self, report_generator, sample_trades):
        """Test equity curve points are in chronological order"""
        curve = report_generator._generate_equity_curve(sample_trades, 100000.0)

        # Verify timestamps are in order
        timestamps = [point['time'] for point in curve]
        assert timestamps == sorted(timestamps)

    def test_equity_curve_empty_trades(self, report_generator, empty_trades):
        """Test equity curve with no trades"""
        curve = report_generator._generate_equity_curve(empty_trades, 100000.0)
        assert len(curve) == 0

    def test_equity_curve_single_trade(self, report_generator, single_trade):
        """Test equity curve with single trade"""
        single_trade[0].pnl = 50.0
        start_time = datetime(2024, 1, 1, 0, 0, 0)
        curve = report_generator._generate_equity_curve(single_trade, 100000.0, start_time)

        # Should have 2 points: initial cash + after trade
        assert len(curve) == 2
        # First point should be initial cash
        assert curve[0]['value'] == 100000.0
        # Second point should be after trade
        assert curve[1]['value'] == 100050.0

    def test_equity_curve_starts_with_initial_cash(self, report_generator, sample_trades):
        """Test that equity curve starts with initial cash value"""
        initial_cash = 100000.0
        start_time = datetime(2024, 1, 1, 0, 0, 0)
        curve = report_generator._generate_equity_curve(sample_trades, initial_cash, start_time)

        # Should have one more point than trades (initial point + trades)
        assert len(curve) == 8  # 7 trades + 1 initial point

        # First point should be initial cash
        assert curve[0]['value'] == initial_cash
        assert curve[0]['time'] == start_time.isoformat()

        # Second point should be after first trade
        assert curve[1]['value'] == initial_cash + sample_trades[0].pnl


# ========================================
# Test Summary Generation
# ========================================

class TestSummaryGeneration:
    """Test summary generation"""

    def test_summary_values(self, report_generator, sample_backtest_result, sample_trades):
        """Test summary values are calculated correctly"""
        summary = report_generator._generate_summary(sample_backtest_result, sample_trades)

        # Verify values from BacktestResult
        assert summary['total_return'] == 15.5
        assert summary['final_value'] == 115500.0
        assert summary['max_drawdown'] == -8.3
        assert summary['sharpe_ratio'] == 1.85
        assert summary['initial_cash'] == 100000.0

        # Verify values from trades
        assert summary['total_trades'] == 7
        assert summary['winning_trades'] == 5
        assert summary['losing_trades'] == 2
        assert summary['win_rate'] == pytest.approx(0.7143, rel=0.01)  # Changed to decimal format

        # Verify calculated values
        assert 'avg_trade' in summary
        assert 'avg_winning_trade' in summary
        assert 'avg_losing_trade' in summary
        assert 'profit_factor' in summary

    def test_summary_with_no_trades(self, report_generator, sample_backtest_result, empty_trades):
        """Test summary with no trades"""
        summary = report_generator._generate_summary(sample_backtest_result, empty_trades)

        # Should handle gracefully
        assert summary['total_trades'] == 0
        assert summary['winning_trades'] == 0
        assert summary['losing_trades'] == 0
        assert summary['win_rate'] == 0.0
        assert summary['avg_trade'] == 0.0


# ========================================
# Test Edge Cases
# ========================================

class TestEdgeCases:
    """Test edge cases"""

    def test_report_with_none_values(self, report_generator):
        """Test report when BacktestResult has None values"""
        backtest_result = BacktestResult(
            backtest_job_id=1,
            total_return=10.0,
            annual_return=None,
            sharpe_ratio=None,
            max_drawdown=-5.0,
            win_rate=None,
            profit_factor=None,
            total_trades=5,
            initial_cash=100000.0,
            final_value=110000.0
        )

        trades = [Trade(
            backtest_job_id=1,
            order_id='order_1',
            symbol='BTCUSDT',
            side='BUY',
            price=100.0,
            size=1.0,
            commission=0.1,
            timestamp=datetime(2024, 1, 1, 12, 0, 0)
        )]
        trades[0].pnl = 50.0

        # Should not crash
        report = report_generator.generate_report(backtest_result, trades)
        assert report is not None

        # None values should be handled
        assert report['summary']['sharpe_ratio'] is None
        assert report['summary']['annual_return'] is None

    def test_trades_without_pnl(self, report_generator):
        """Test trades that don't have PnL set"""
        trades = [Trade(
            backtest_job_id=1,
            order_id='order_1',
            symbol='BTCUSDT',
            side='BUY',
            price=100.0,
            size=1.0,
            commission=0.1,
            timestamp=datetime(2024, 1, 1, 12, 0, 0)
        )]
        # Don't set pnl - should default to 0 or None

        backtest_result = BacktestResult(
            backtest_job_id=1,
            total_return=0.0,
            annual_return=0.0,
            sharpe_ratio=0.0,
            max_drawdown=0.0,
            win_rate=0.0,
            profit_factor=0.0,
            total_trades=1,
            initial_cash=100000.0,
            final_value=100000.0
        )

        # Should handle gracefully
        report = report_generator.generate_report(backtest_result, trades)
        assert report is not None
