"""
Comprehensive tests for the database layer
"""
import pytest
import tempfile
import os
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from backend.database import Database, CandleData
from backend.models.symbol import Symbol
from backend.models.candle import Candle
from backend.models.trade import Trade
from backend.models.backtest_job import BacktestJob
from backend.models.backtest_result import BacktestResult
from backend.models.optimization_job import OptimizationJob
from backend.models.optimization_result import OptimizationResult


@pytest.fixture
def temp_db():
    """Create a temporary database for testing"""
    fd, db_path = tempfile.mkstemp(suffix='.db')
    database_url = f"sqlite:///{db_path}"
    db = Database(database_url)
    db.create_tables()
    yield db
    os.close(fd)
    os.unlink(db_path)


class TestDatabaseInitialization:
    """Test database initialization and connection"""

    def test_database_creation(self, temp_db):
        """Test database is created successfully"""
        assert temp_db.engine is not None
        assert temp_db.SessionLocal is not None

    def test_create_tables(self, temp_db):
        """Test table creation"""
        # Tables should be created without errors
        temp_db.create_tables()

        # Verify tables exist by querying
        with temp_db.get_session() as session:
            # Should not raise any errors
            session.query(Symbol).all()
            session.query(Candle).all()
            session.query(Trade).all()
            session.query(BacktestJob).all()


class TestSessionManagement:
    """Test session context manager"""

    def test_successful_session(self, temp_db):
        """Test successful session commit"""
        with temp_db.get_session() as session:
            symbol = Symbol(
                name='TESTUSDT',
                base_currency='TEST',
                quote_currency='USDT'
            )
            session.add(symbol)

        # Verify data is committed
        with temp_db.get_session() as session:
            result = session.query(Symbol).filter(Symbol.name == 'TESTUSDT').first()
            assert result is not None
            assert result.base_currency == 'TEST'

    def test_failed_session_rollback(self, temp_db):
        """Test session rollback on error"""
        try:
            with temp_db.get_session() as session:
                symbol = Symbol(
                    name='TESTUSDT',
                    base_currency='TEST',
                    quote_currency='USDT'
                )
                session.add(symbol)
                # Force an error
                raise ValueError("Test error")
        except ValueError:
            pass

        # Verify data is rolled back
        with temp_db.get_session() as session:
            result = session.query(Symbol).filter(Symbol.name == 'TESTUSDT').first()
            assert result is None


class TestSymbolOperations:
    """Test symbol-related operations"""

    def test_get_or_create_symbol_new(self, temp_db):
        """Test creating a new symbol"""
        symbol = temp_db.get_or_create_symbol('BTCUSDT', 'BTC', 'USDT')

        assert symbol is not None
        assert symbol.name == 'BTCUSDT'
        assert symbol.base_currency == 'BTC'
        assert symbol.quote_currency == 'USDT'

    def test_get_or_create_symbol_existing(self, temp_db):
        """Test retrieving an existing symbol"""
        # Create symbol first time
        symbol1 = temp_db.get_or_create_symbol('ETHUSDT', 'ETH', 'USDT')

        # Get the same symbol again
        symbol2 = temp_db.get_or_create_symbol('ETHUSDT')

        assert symbol1.id == symbol2.id
        assert symbol1.name == symbol2.name

    def test_get_or_create_symbol_auto_extract(self, temp_db):
        """Test auto-extraction of base currency"""
        symbol = temp_db.get_or_create_symbol('BNBUSDT')

        assert symbol.base_currency == 'BNB'
        assert symbol.quote_currency == 'USDT'


class TestCandleOperations:
    """Test candle-related operations"""

    @pytest.fixture
    def sample_candles(self):
        """Create sample candle data"""
        base_time = datetime(2024, 1, 1, 0, 0, 0)
        candles = []

        for i in range(5):
            candle = CandleData(
                symbol='BTCUSDT',
                interval='1h',
                open_time=base_time + timedelta(hours=i),
                close_time=base_time + timedelta(hours=i, minutes=59, seconds=59),
                open_price=50000.0 + i * 100,
                high_price=50100.0 + i * 100,
                low_price=49900.0 + i * 100,
                close_price=50050.0 + i * 100,
                volume=1000.0 + i * 10
            )
            candles.append(candle)

        return candles

    def test_save_candles(self, temp_db, sample_candles):
        """Test saving candles"""
        saved_count = temp_db.save_candles(sample_candles)
        assert saved_count == 5

    def test_save_candles_skip_duplicates(self, temp_db, sample_candles):
        """Test that duplicate candles are skipped"""
        # Save first time
        saved_count1 = temp_db.save_candles(sample_candles)
        assert saved_count1 == 5

        # Try to save same candles again
        saved_count2 = temp_db.save_candles(sample_candles)
        assert saved_count2 == 0

    def test_get_candles(self, temp_db, sample_candles):
        """Test retrieving candles"""
        # Save candles first
        temp_db.save_candles(sample_candles)

        # Retrieve candles
        start_time = datetime(2024, 1, 1, 0, 0, 0).isoformat()
        end_time = datetime(2024, 1, 1, 4, 0, 0).isoformat()

        candles = temp_db.get_candles('BTCUSDT', '1h', start_time, end_time)

        assert len(candles) == 5
        assert candles[0].open_price == 50000.0
        assert candles[-1].open_price == 50400.0

    def test_get_candles_symbol_not_found(self, temp_db):
        """Test retrieving candles for non-existent symbol"""
        candles = temp_db.get_candles(
            'NONEXISTENT',
            '1h',
            '2024-01-01T00:00:00',
            '2024-01-01T04:00:00'
        )
        assert candles == []

    def test_get_candles_count(self, temp_db, sample_candles):
        """Test counting candles"""
        temp_db.save_candles(sample_candles)

        start_time = datetime(2024, 1, 1, 0, 0, 0)
        end_time = datetime(2024, 1, 1, 4, 0, 0)

        count = temp_db.get_candles_count('BTCUSDT', '1h', start_time, end_time)
        assert count == 5


class TestBacktestOperations:
    """Test backtest-related operations"""

    def test_create_backtest_job(self, temp_db):
        """Test creating a backtest job"""
        job = BacktestJob(
            strategy_name='SMA_Cross',
            symbol='BTCUSDT',
            interval='1h',
            start_time=datetime(2024, 1, 1),
            end_time=datetime(2024, 1, 31),
            parameters={'fast_period': 10, 'slow_period': 20},
            status='pending'
        )

        job_id = temp_db.create_backtest_job(job)

        assert job_id is not None

        # Verify by querying
        with temp_db.get_session() as session:
            created = session.query(BacktestJob).filter(BacktestJob.id == job_id).first()
            assert created.strategy_name == 'SMA_Cross'
            assert created.status == 'pending'

    def test_update_backtest_job_status(self, temp_db):
        """Test updating backtest job status"""
        # Create job first
        job = BacktestJob(
            strategy_name='SMA_Cross',
            symbol='BTCUSDT',
            interval='1h',
            start_time=datetime(2024, 1, 1),
            end_time=datetime(2024, 1, 31),
            parameters={'fast_period': 10, 'slow_period': 20},
            status='pending'
        )
        job_id = temp_db.create_backtest_job(job)

        # Update status
        completed_at = datetime.utcnow()
        temp_db.update_backtest_job_status(job_id, 'completed', completed_at)

        # Verify update
        with temp_db.get_session() as session:
            updated_job = session.query(BacktestJob).filter(
                BacktestJob.id == job_id
            ).first()

            assert updated_job.status == 'completed'
            assert updated_job.completed_at is not None

    def test_save_backtest_result(self, temp_db):
        """Test saving backtest result and trades"""
        # Create job first
        job = BacktestJob(
            strategy_name='SMA_Cross',
            symbol='BTCUSDT',
            interval='1h',
            start_time=datetime(2024, 1, 1),
            end_time=datetime(2024, 1, 31),
            parameters={'fast_period': 10, 'slow_period': 20},
            status='completed'
        )
        job_id = temp_db.create_backtest_job(job)

        # Create result
        result = BacktestResult(
            backtest_job_id=job_id,
            total_return=0.25,
            annual_return=0.30,
            sharpe_ratio=1.5,
            max_drawdown=-0.10,
            win_rate=0.60,
            profit_factor=1.8,
            total_trades=100,
            initial_cash=100000.0,
            final_value=125000.0
        )

        # Create trades
        trades = [
            Trade(
                backtest_job_id=job_id,
                order_id='1',
                symbol='BTCUSDT',
                side='BUY',
                price=50000.0,
                size=0.1,
                commission=5.0,
                timestamp=datetime(2024, 1, 5, 10, 0, 0)
            ),
            Trade(
                backtest_job_id=job_id,
                order_id='2',
                symbol='BTCUSDT',
                side='SELL',
                price=52000.0,
                size=0.1,
                commission=5.2,
                timestamp=datetime(2024, 1, 10, 14, 0, 0)
            )
        ]

        temp_db.save_backtest_result(result, trades)

        # Verify result saved
        saved_result = temp_db.get_backtest_result(job_id)
        assert saved_result is not None
        assert saved_result.total_return == 0.25
        assert saved_result.sharpe_ratio == 1.5

        # Verify trades saved
        saved_trades = temp_db.get_trades(job_id)
        assert len(saved_trades) == 2
        assert saved_trades[0].side == 'BUY'
        assert saved_trades[1].side == 'SELL'

    def test_get_backtest_jobs_by_status(self, temp_db):
        """Test filtering jobs by status"""
        # Create multiple jobs with different statuses
        for i, status in enumerate(['pending', 'running', 'completed']):
            job = BacktestJob(
                strategy_name=f'Strategy_{i}',
                symbol='BTCUSDT',
                interval='1h',
                start_time=datetime(2024, 1, 1),
                end_time=datetime(2024, 1, 31),
                parameters={'param': i},
                status=status
            )
            temp_db.create_backtest_job(job)

        # Get pending jobs
        pending_jobs = temp_db.get_backtest_jobs_by_status('pending')
        assert len(pending_jobs) == 1
        assert pending_jobs[0].status == 'pending'

        # Get completed jobs
        completed_jobs = temp_db.get_backtest_jobs_by_status('completed')
        assert len(completed_jobs) == 1


class TestOptimizationOperations:
    """Test optimization-related operations"""

    def test_create_optimization_job(self, temp_db):
        """Test creating an optimization job"""
        job = OptimizationJob(
            strategy_name='SMA_Cross',
            symbol='BTCUSDT',
            interval='1h',
            start_time=datetime(2024, 1, 1),
            end_time=datetime(2024, 1, 31),
            parameter_ranges={
                'fast_period': [5, 10, 15],
                'slow_period': [20, 30, 40]
            },
            optimization_method='grid',
            status='pending'
        )

        job_id = temp_db.create_optimization_job(job)

        assert job_id is not None

        # Verify by querying
        with temp_db.get_session() as session:
            created = session.query(OptimizationJob).filter(OptimizationJob.id == job_id).first()
            assert created.strategy_name == 'SMA_Cross'
            assert created.optimization_method == 'grid'

    def test_update_optimization_job_status(self, temp_db):
        """Test updating optimization job status"""
        # Create job
        job = OptimizationJob(
            strategy_name='SMA_Cross',
            symbol='BTCUSDT',
            interval='1h',
            start_time=datetime(2024, 1, 1),
            end_time=datetime(2024, 1, 31),
            parameter_ranges={'fast_period': [5, 10]},
            optimization_method='grid',
            status='pending'
        )
        job_id = temp_db.create_optimization_job(job)

        # Update status
        completed_at = datetime.utcnow()
        temp_db.update_optimization_job_status(job_id, 'completed', completed_at)

        # Verify
        with temp_db.get_session() as session:
            updated_job = session.query(OptimizationJob).filter(
                OptimizationJob.id == job_id
            ).first()

            assert updated_job.status == 'completed'
            assert updated_job.completed_at is not None

    def test_save_optimization_result(self, temp_db):
        """Test saving optimization result"""
        # Create optimization job
        opt_job = OptimizationJob(
            strategy_name='SMA_Cross',
            symbol='BTCUSDT',
            interval='1h',
            start_time=datetime(2024, 1, 1),
            end_time=datetime(2024, 1, 31),
            parameter_ranges={'fast_period': [5, 10, 15]},
            optimization_method='grid',
            status='completed'
        )
        opt_job_id = temp_db.create_optimization_job(opt_job)

        # Create backtest job for result
        bt_job = BacktestJob(
            strategy_name='SMA_Cross',
            symbol='BTCUSDT',
            interval='1h',
            start_time=datetime(2024, 1, 1),
            end_time=datetime(2024, 1, 31),
            parameters={'fast_period': 10},
            status='completed'
        )
        bt_job_id = temp_db.create_backtest_job(bt_job)

        # Create backtest result
        bt_result = BacktestResult(
            backtest_job_id=bt_job_id,
            total_return=0.25,
            max_drawdown=-0.10,
            initial_cash=100000.0,
            final_value=125000.0
        )
        bt_result_id = temp_db.save_backtest_result(bt_result, [])

        # Save optimization result
        opt_result = OptimizationResult(
            optimization_job_id=opt_job_id,
            parameters={'fast_period': 10},
            score=1.5,
            backtest_result_id=bt_result_id
        )
        temp_db.save_optimization_result(opt_result)

        # Verify
        results = temp_db.get_optimization_results(opt_job_id)
        assert len(results) == 1
        assert results[0].score == 1.5
        assert results[0].parameters == {'fast_period': 10}

    def test_get_best_optimization_result(self, temp_db):
        """Test getting best optimization result"""
        # Create optimization job
        opt_job = OptimizationJob(
            strategy_name='SMA_Cross',
            symbol='BTCUSDT',
            interval='1h',
            start_time=datetime(2024, 1, 1),
            end_time=datetime(2024, 1, 31),
            parameter_ranges={'fast_period': [5, 10, 15]},
            optimization_method='grid',
            status='completed'
        )
        opt_job_id = temp_db.create_optimization_job(opt_job)

        # Save multiple results with different scores
        for i, score in enumerate([1.2, 1.5, 1.3]):
            result = OptimizationResult(
                optimization_job_id=opt_job_id,
                parameters={'fast_period': 5 + i * 5},
                score=score
            )
            temp_db.save_optimization_result(result)

        # Get best result
        best = temp_db.get_best_optimization_result(opt_job_id)

        assert best is not None
        assert best.score == 1.5
        assert best.parameters == {'fast_period': 10}


class TestDownloadedDataSummary:
    """Test get_downloaded_data_summary method"""

    def test_get_downloaded_data_summary_empty(self, temp_db):
        """测试空数据库返回空列表"""
        result = temp_db.get_downloaded_data_summary()
        assert result == []

    def test_get_downloaded_data_summary_single_symbol(self, temp_db):
        """测试单个 symbol 的数据摘要"""
        # 创建测试数据
        from backend.database import CandleData

        symbol = temp_db.get_or_create_symbol("BTCUSDT")

        # 插入测试 K 线数据
        candles = [
            CandleData(
                symbol="BTCUSDT",
                interval="1h",
                open_time=datetime(2024, 1, 1, i),
                close_time=datetime(2024, 1, 1, i, 59, 59),
                open_price=42000.0,
                high_price=42500.0,
                low_price=41800.0,
                close_price=42300.0,
                volume=100.0
            )
            for i in range(10)
        ]
        temp_db.save_candles(candles)

        # 查询摘要
        result = temp_db.get_downloaded_data_summary()

        # 验证
        assert len(result) == 1
        assert result[0]["symbol"] == "BTCUSDT"
        assert len(result[0]["intervals"]) == 1
        assert result[0]["intervals"][0]["interval"] == "1h"
        assert result[0]["intervals"][0]["count"] == 10
        assert result[0]["intervals"][0]["start_time"] == datetime(2024, 1, 1, 0)
        assert result[0]["intervals"][0]["end_time"] == datetime(2024, 1, 1, 9)

    def test_get_downloaded_data_summary_multiple_intervals(self, temp_db):
        """测试多个 interval 的数据摘要"""
        from backend.database import CandleData

        symbol = temp_db.get_or_create_symbol("ETHUSDT")

        # 插入 1h 数据
        candles_1h = [
            CandleData(
                symbol="ETHUSDT",
                interval="1h",
                open_time=datetime(2024, 1, 1, i),
                close_time=datetime(2024, 1, 1, i, 59, 59),
                open_price=2200.0,
                high_price=2250.0,
                low_price=2180.0,
                close_price=2230.0,
                volume=50.0
            )
            for i in range(5)
        ]

        # 插入 1d 数据
        candles_1d = [
            CandleData(
                symbol="ETHUSDT",
                interval="1d",
                open_time=datetime(2024, 1, i),
                close_time=datetime(2024, 1, i, 23, 59, 59),
                open_price=2200.0,
                high_price=2300.0,
                low_price=2100.0,
                close_price=2250.0,
                volume=500.0
            )
            for i in range(1, 4)
        ]

        temp_db.save_candles(candles_1h + candles_1d)

        # 查询摘要
        result = temp_db.get_downloaded_data_summary()

        # 验证
        assert len(result) == 1
        assert result[0]["symbol"] == "ETHUSDT"
        assert len(result[0]["intervals"]) == 2

        # 验证 interval 数据
        intervals = {item["interval"]: item for item in result[0]["intervals"]}
        assert "1h" in intervals
        assert "1d" in intervals
        assert intervals["1h"]["count"] == 5
        assert intervals["1d"]["count"] == 3

    def test_get_downloaded_data_summary_disabled_symbol_filtered(self, temp_db):
        """测试禁用的 symbol 不会出现在结果中"""
        from backend.database import CandleData, Symbol

        # 创建启用的 symbol
        enabled_symbol = temp_db.get_or_create_symbol("BTCUSDT")

        # 创建禁用的 symbol
        disabled_symbol = temp_db.get_or_create_symbol("ETHUSDT")
        with temp_db.get_session() as session:
            session.query(Symbol).filter(Symbol.name == "ETHUSDT").update({"enabled": False})

        # 给两个 symbol 都添加数据
        candles = [
            CandleData(
                symbol="BTCUSDT",
                interval="1h",
                open_time=datetime(2024, 1, 1, i),
                close_time=datetime(2024, 1, 1, i, 59, 59),
                open_price=42000.0, high_price=42500.0,
                low_price=41800.0, close_price=42300.0,
                volume=100.0
            )
            for i in range(5)
        ] + [
            CandleData(
                symbol="ETHUSDT",  # disabled symbol
                interval="1h",
                open_time=datetime(2024, 1, 1, i),
                close_time=datetime(2024, 1, 1, i, 59, 59),
                open_price=2200.0, high_price=2250.0,
                low_price=2180.0, close_price=2230.0,
                volume=50.0
            )
            for i in range(3)
        ]
        temp_db.save_candles(candles)

        # 查询摘要
        result = temp_db.get_downloaded_data_summary()

        # 验证只返回启用的 symbol
        assert len(result) == 1
        assert result[0]["symbol"] == "BTCUSDT"
        assert result[0]["intervals"][0]["count"] == 5


class TestHistoryQueries:
    """Test history query operations"""

    @pytest.fixture
    def setup_backtest_data(self, temp_db):
        """Create sample backtest jobs with different strategies, symbols and statuses"""
        jobs_data = []
        strategies = ['SMA_Cross', 'RSI_Strategy', 'MACD_Strategy']
        symbols = ['BTCUSDT', 'ETHUSDT']
        statuses = ['completed', 'failed', 'running', 'pending']

        # Create 12 jobs: 3 strategies * 2 symbols * 2 completed statuses
        job_index = 0
        for strategy in strategies:
            for symbol in symbols:
                for status in ['completed', 'failed']:
                    job = BacktestJob(
                        strategy_name=strategy,
                        symbol=symbol,
                        interval='1h',
                        start_time=datetime(2024, 1, 1),
                        end_time=datetime(2024, 1, 31),
                        parameters={'param': job_index},
                        status=status
                    )
                    job_id = temp_db.create_backtest_job(job)

                    # Create result for completed jobs
                    if status == 'completed':
                        result = BacktestResult(
                            backtest_job_id=job_id,
                            total_return=0.1 * (job_index + 1),
                            annual_return=0.12 * (job_index + 1),
                            sharpe_ratio=1.0 + job_index * 0.2,
                            max_drawdown=-0.05 * (job_index + 1),
                            win_rate=0.5 + job_index * 0.05,
                            profit_factor=1.5 + job_index * 0.1,
                            total_trades=10 * (job_index + 1),
                            initial_cash=100000.0,
                            final_value=100000.0 * (1 + 0.1 * (job_index + 1))
                        )
                        temp_db.save_backtest_result(result, [])

                    jobs_data.append({
                        'id': job_id,
                        'strategy': strategy,
                        'symbol': symbol,
                        'status': status
                    })
                    job_index += 1

        return jobs_data

    def test_get_backtest_history_no_filters(self, temp_db, setup_backtest_data):
        """Test getting all backtest history without filters"""
        result = temp_db.get_backtest_history()

        assert result['total'] == 12  # 3 strategies * 2 symbols * 2 statuses
        assert result['page'] == 1
        assert result['page_size'] == 20
        assert len(result['items']) == 12
        assert result['total_pages'] == 1

    def test_get_backtest_history_filter_by_strategy(self, temp_db, setup_backtest_data):
        """Test filtering by strategy name"""
        result = temp_db.get_backtest_history(strategy_name='SMA_Cross')

        assert result['total'] == 4
        for item in result['items']:
            assert item['strategy_name'] == 'SMA_Cross'

    def test_get_backtest_history_filter_by_symbol(self, temp_db, setup_backtest_data):
        """Test filtering by symbol"""
        result = temp_db.get_backtest_history(symbol='ETHUSDT')

        assert result['total'] == 6
        for item in result['items']:
            assert item['symbol'] == 'ETHUSDT'

    def test_get_backtest_history_filter_by_status(self, temp_db, setup_backtest_data):
        """Test filtering by status"""
        result = temp_db.get_backtest_history(status='completed')

        # 3 strategies * 2 symbols = 6 completed jobs
        assert result['total'] == 6
        for item in result['items']:
            assert item['status'] == 'completed'

    def test_get_backtest_history_pagination(self, temp_db, setup_backtest_data):
        """Test pagination"""
        # Page 1
        result = temp_db.get_backtest_history(page=1, page_size=5)
        assert result['total'] == 12
        assert result['page'] == 1
        assert result['page_size'] == 5
        assert len(result['items']) == 5
        assert result['total_pages'] == 3

        # Page 2
        result = temp_db.get_backtest_history(page=2, page_size=5)
        assert result['page'] == 2
        assert len(result['items']) == 5

        # Page 3
        result = temp_db.get_backtest_history(page=3, page_size=5)
        assert result['page'] == 3
        assert len(result['items']) == 2

    def test_get_backtest_history_sort_by_created_at(self, temp_db, setup_backtest_data):
        """Test sorting by created_at"""
        # Descending (default)
        result_desc = temp_db.get_backtest_history(sort_by='created_at', sort_order='desc')
        timestamps_desc = [item['created_at'] for item in result_desc['items']]

        # Ascending
        result_asc = temp_db.get_backtest_history(sort_by='created_at', sort_order='asc')
        timestamps_asc = [item['created_at'] for item in result_asc['items']]

        assert timestamps_desc == sorted(timestamps_desc, reverse=True)
        assert timestamps_asc == sorted(timestamps_asc)

    def test_get_backtest_history_sort_by_total_return(self, temp_db, setup_backtest_data):
        """Test sorting by total_return"""
        result = temp_db.get_backtest_history(
            status='completed',
            sort_by='total_return',
            sort_order='desc'
        )

        # Should only return completed jobs with results
        returns = [item['total_return'] for item in result['items'] if item['total_return'] is not None]
        assert returns == sorted(returns, reverse=True)

    def test_get_backtest_history_sort_by_sharpe_ratio(self, temp_db, setup_backtest_data):
        """Test sorting by sharpe_ratio"""
        result = temp_db.get_backtest_history(
            status='completed',
            sort_by='sharpe_ratio',
            sort_order='asc'
        )

        sharpe_values = [item['sharpe_ratio'] for item in result['items'] if item['sharpe_ratio'] is not None]
        assert sharpe_values == sorted(sharpe_values)

    def test_get_backtest_history_result_fields(self, temp_db, setup_backtest_data):
        """Test that result contains all required fields"""
        result = temp_db.get_backtest_history(page=1, page_size=1)
        item = result['items'][0]

        required_fields = [
            'id', 'strategy_name', 'symbol', 'interval',
            'start_time', 'end_time', 'status',
            'total_return', 'sharpe_ratio', 'max_drawdown', 'total_trades',
            'created_at', 'completed_at'
        ]

        for field in required_fields:
            assert field in item

    def test_get_backtest_history_empty(self, temp_db):
        """Test getting history when no jobs exist"""
        result = temp_db.get_backtest_history()

        assert result['total'] == 0
        assert result['items'] == []
        assert result['total_pages'] == 0


class TestOptimizationHistory:
    """Test optimization history query operations"""

    @pytest.fixture
    def setup_optimization_data(self, temp_db):
        """Create sample optimization jobs"""
        jobs_data = []
        strategies = ['SMA_Cross', 'RSI_Strategy']
        symbols = ['BTCUSDT', 'ETHUSDT']
        statuses = ['completed', 'failed', 'running']

        for i, (strategy, symbol, status) in enumerate(zip(strategies * 2, symbols * 2, statuses * 2)):
            job = OptimizationJob(
                strategy_name=strategy,
                symbol=symbol,
                interval='1h',
                start_time=datetime(2024, 1, 1),
                end_time=datetime(2024, 1, 31),
                parameter_ranges={'param': [1, 2, 3]},
                optimization_method='grid',
                status=status
            )
            job_id = temp_db.create_optimization_job(job)

            # Create results for completed jobs
            if status == 'completed':
                for j in range(3):  # 3 parameter combinations
                    result = OptimizationResult(
                        optimization_job_id=job_id,
                        parameters={'param': j + 1},
                        score=1.0 + j * 0.3
                    )
                    temp_db.save_optimization_result(result)

            jobs_data.append({
                'id': job_id,
                'strategy': strategy,
                'symbol': symbol,
                'status': status
            })

        return jobs_data

    def test_get_optimization_history_no_filters(self, temp_db, setup_optimization_data):
        """Test getting all optimization history without filters"""
        result = temp_db.get_optimization_history()

        assert result['total'] == 4  # 2 strategies * 2 symbols
        assert result['page'] == 1
        assert result['page_size'] == 20
        assert len(result['items']) == 4

    def test_get_optimization_history_filter_by_strategy(self, temp_db, setup_optimization_data):
        """Test filtering by strategy name"""
        result = temp_db.get_optimization_history(strategy_name='SMA_Cross')

        assert result['total'] == 2
        for item in result['items']:
            assert item['strategy_name'] == 'SMA_Cross'

    def test_get_optimization_history_filter_by_symbol(self, temp_db, setup_optimization_data):
        """Test filtering by symbol"""
        result = temp_db.get_optimization_history(symbol='ETHUSDT')

        assert result['total'] == 2
        for item in result['items']:
            assert item['symbol'] == 'ETHUSDT'

    def test_get_optimization_history_filter_by_status(self, temp_db, setup_optimization_data):
        """Test filtering by status"""
        result = temp_db.get_optimization_history(status='completed')

        assert result['total'] == 2
        for item in result['items']:
            assert item['status'] == 'completed'

    def test_get_optimization_history_pagination(self, temp_db, setup_optimization_data):
        """Test pagination"""
        result = temp_db.get_optimization_history(page=1, page_size=2)

        assert result['total'] == 4
        assert result['page'] == 1
        assert result['page_size'] == 2
        assert len(result['items']) == 2
        assert result['total_pages'] == 2

    def test_get_optimization_history_sort_by_best_score(self, temp_db, setup_optimization_data):
        """Test sorting by best_score"""
        result = temp_db.get_optimization_history(
            status='completed',
            sort_by='best_score',
            sort_order='desc'
        )

        scores = [item['best_score'] for item in result['items'] if item['best_score'] is not None]
        assert scores == sorted(scores, reverse=True)

    def test_get_optimization_history_result_fields(self, temp_db, setup_optimization_data):
        """Test that result contains all required fields"""
        result = temp_db.get_optimization_history(page=1, page_size=1)
        item = result['items'][0]

        required_fields = [
            'id', 'strategy_name', 'symbol', 'interval',
            'start_time', 'end_time', 'status',
            'best_score', 'best_parameters', 'total_combinations',
            'created_at', 'completed_at'
        ]

        for field in required_fields:
            assert field in item

    def test_get_optimization_history_best_parameters(self, temp_db, setup_optimization_data):
        """Test that best_parameters is populated for completed jobs"""
        result = temp_db.get_optimization_history(status='completed')

        for item in result['items']:
            if item['status'] == 'completed':
                assert item['best_parameters'] is not None
                assert item['best_score'] is not None
                assert item['total_combinations'] == 3


class TestDeleteJobs:
    """Test job deletion operations"""

    def test_delete_backtest_job_completed(self, temp_db):
        """Test deleting a completed backtest job"""
        # Create a completed job
        job = BacktestJob(
            strategy_name='SMA_Cross',
            symbol='BTCUSDT',
            interval='1h',
            start_time=datetime(2024, 1, 1),
            end_time=datetime(2024, 1, 31),
            parameters={'param': 1},
            status='completed'
        )
        job_id = temp_db.create_backtest_job(job)

        # Delete it
        result = temp_db.delete_backtest_job(job_id)
        assert result is True

        # Verify it's deleted
        deleted_job = temp_db.get_backtest_job(job_id)
        assert deleted_job is None

    def test_delete_backtest_job_running_raises_error(self, temp_db):
        """Test that deleting a running job raises ValueError"""
        # Create a running job
        job = BacktestJob(
            strategy_name='SMA_Cross',
            symbol='BTCUSDT',
            interval='1h',
            start_time=datetime(2024, 1, 1),
            end_time=datetime(2024, 1, 31),
            parameters={'param': 1},
            status='running'
        )
        job_id = temp_db.create_backtest_job(job)

        # Try to delete - should raise ValueError
        with pytest.raises(ValueError, match="Cannot delete running backtest job"):
            temp_db.delete_backtest_job(job_id)

    def test_delete_backtest_job_not_found_raises_error(self, temp_db):
        """Test that deleting non-existent job raises ValueError"""
        with pytest.raises(ValueError, match="Backtest job 999 not found"):
            temp_db.delete_backtest_job(999)

    def test_delete_backtest_job_cascades_to_result_and_trades(self, temp_db):
        """Test that deleting a job cascades to result and trades"""
        # Create job with result and trades
        job = BacktestJob(
            strategy_name='SMA_Cross',
            symbol='BTCUSDT',
            interval='1h',
            start_time=datetime(2024, 1, 1),
            end_time=datetime(2024, 1, 31),
            parameters={'param': 1},
            status='completed'
        )
        job_id = temp_db.create_backtest_job(job)

        # Add result
        result = BacktestResult(
            backtest_job_id=job_id,
            total_return=0.1,
            max_drawdown=-0.05,
            initial_cash=100000.0,
            final_value=110000.0
        )
        temp_db.save_backtest_result(result, [])

        # Add trade
        trade = Trade(
            backtest_job_id=job_id,
            order_id='1',
            symbol='BTCUSDT',
            side='BUY',
            price=50000.0,
            size=0.1,
            commission=5.0,
            timestamp=datetime.utcnow()
        )
        with temp_db.get_session() as session:
            session.add(trade)

        # Delete job
        temp_db.delete_backtest_job(job_id)

        # Verify cascades
        with temp_db.get_session() as session:
            assert session.query(BacktestJob).filter_by(id=job_id).first() is None
            assert session.query(BacktestResult).filter_by(backtest_job_id=job_id).first() is None
            assert session.query(Trade).filter_by(backtest_job_id=job_id).first() is None

    def test_delete_optimization_job_completed(self, temp_db):
        """Test deleting a completed optimization job"""
        # Create a completed job
        job = OptimizationJob(
            strategy_name='SMA_Cross',
            symbol='BTCUSDT',
            interval='1h',
            start_time=datetime(2024, 1, 1),
            end_time=datetime(2024, 1, 31),
            parameter_ranges={'param': [1, 2]},
            optimization_method='grid',
            status='completed'
        )
        job_id = temp_db.create_optimization_job(job)

        # Add some results
        result = OptimizationResult(
            optimization_job_id=job_id,
            parameters={'param': 1},
            score=1.5
        )
        temp_db.save_optimization_result(result)

        # Delete it
        deleted = temp_db.delete_optimization_job(job_id)
        assert deleted is True

        # Verify it's deleted
        with temp_db.get_session() as session:
            assert session.query(OptimizationJob).filter_by(id=job_id).first() is None
            assert session.query(OptimizationResult).filter_by(optimization_job_id=job_id).count() == 0

    def test_delete_optimization_job_running_raises_error(self, temp_db):
        """Test that deleting a running optimization job raises ValueError"""
        # Create a running job
        job = OptimizationJob(
            strategy_name='SMA_Cross',
            symbol='BTCUSDT',
            interval='1h',
            start_time=datetime(2024, 1, 1),
            end_time=datetime(2024, 1, 31),
            parameter_ranges={'param': [1, 2]},
            optimization_method='grid',
            status='running'
        )
        job_id = temp_db.create_optimization_job(job)

        # Try to delete - should raise ValueError
        with pytest.raises(ValueError, match="Cannot delete running optimization job"):
            temp_db.delete_optimization_job(job_id)

    def test_delete_optimization_job_not_found_raises_error(self, temp_db):
        """Test that deleting non-existent optimization job raises ValueError"""
        with pytest.raises(ValueError, match="Optimization job 999 not found"):
            temp_db.delete_optimization_job(999)


class TestForeignKeyConstraints:
    """Test foreign key constraints are enforced"""

    def test_cascade_delete_symbol(self, temp_db):
        """Test that deleting a symbol cascades to candles"""
        # Create symbol and candle
        symbol = temp_db.get_or_create_symbol('BTCUSDT')

        candle = CandleData(
            symbol='BTCUSDT',
            interval='1h',
            open_time=datetime(2024, 1, 1),
            close_time=datetime(2024, 1, 1, 0, 59, 59),
            open_price=50000.0,
            high_price=50100.0,
            low_price=49900.0,
            close_price=50050.0,
            volume=1000.0
        )
        temp_db.save_candles([candle])

        # Delete symbol
        with temp_db.get_session() as session:
            symbol_to_delete = session.query(Symbol).filter(
                Symbol.name == 'BTCUSDT'
            ).first()
            session.delete(symbol_to_delete)

        # Verify candle is also deleted
        with temp_db.get_session() as session:
            remaining_candles = session.query(Candle).all()
            assert len(remaining_candles) == 0

    def test_cascade_delete_backtest_job(self, temp_db):
        """Test that deleting a backtest job cascades to trades"""
        # Create backtest job
        job = BacktestJob(
            strategy_name='SMA_Cross',
            symbol='BTCUSDT',
            interval='1h',
            start_time=datetime(2024, 1, 1),
            end_time=datetime(2024, 1, 31),
            parameters={'fast_period': 10},
            status='completed'
        )
        job_id = temp_db.create_backtest_job(job)

        # Create trades
        trades = [
            Trade(
                backtest_job_id=job_id,
                order_id='1',
                symbol='BTCUSDT',
                side='BUY',
                price=50000.0,
                size=0.1,
                commission=5.0,
                timestamp=datetime.utcnow()
            )
        ]
        temp_db.save_backtest_result(
            BacktestResult(
                backtest_job_id=job_id,
                total_return=0.1,
                max_drawdown=-0.05,
                initial_cash=100000.0,
                final_value=110000.0
            ),
            trades
        )

        # Delete job
        with temp_db.get_session() as session:
            job_to_delete = session.query(BacktestJob).filter(
                BacktestJob.id == job_id
            ).first()
            session.delete(job_to_delete)

        # Verify trades are deleted
        with temp_db.get_session() as session:
            remaining_trades = session.query(Trade).all()
            assert len(remaining_trades) == 0
