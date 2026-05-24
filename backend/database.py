from sqlalchemy import create_engine, event, func, text
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime
from dataclasses import dataclass
import logging

from backend.models.base import Base
from backend.models.symbol import Symbol
from backend.models.candle import Candle
from backend.models.dataset import Dataset
from backend.models.trade import Trade
from backend.models.backtest_job import BacktestJob
from backend.models.backtest_result import BacktestResult
from backend.models.optimization_job import OptimizationJob
from backend.models.optimization_result import OptimizationResult
from backend.models.hidden_strategy import HiddenStrategy

logger = logging.getLogger(__name__)


@dataclass
class CandleData:
    """Data transfer object for candle data"""
    symbol: str
    interval: str
    open_time: datetime
    close_time: datetime
    open_price: float
    high_price: float
    low_price: float
    close_price: float
    volume: float


class Database:
    """Database manager - encapsulates all database operations"""

    def __init__(self, database_url: str):
        """Initialize database connection

        Args:
            database_url: Database connection URL (e.g., sqlite:///data/quant.db)
        """
        self.engine = create_engine(database_url, echo=False)
        self.SessionLocal = sessionmaker(bind=self.engine)

        # Enable foreign key constraints for SQLite
        @event.listens_for(self.engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

        # Ensure new columns exist for backward compatibility
        self.ensure_optimization_columns()
        self.ensure_dataset_columns()

        # Ensure performance indexes exist
        self.ensure_backtest_indexes()
        self.ensure_backtest_columns()

        logger.info(f"Database initialized: {database_url}")

    def create_tables(self):
        """Create all database tables"""
        Base.metadata.create_all(self.engine)
        logger.info("Database tables created")

    def ensure_optimization_columns(self):
        """
        Ensure new optimization columns exist in database.

        Adds new columns if they don't exist (for backward compatibility).
        Skips if tables don't exist yet (will be created by create_tables).
        """
        # Check optimization_jobs columns
        # PRAGMA table_info returns empty list if table doesn't exist
        # Column 1 is 'name' in PRAGMA table_info result
        jobs_columns = [c[1] for c in self.engine.connect().execute(
            text("PRAGMA table_info(optimization_jobs)")
        ).fetchall()]

        # Skip if table doesn't exist (empty columns list)
        if not jobs_columns:
            logger.debug("optimization_jobs table does not exist yet, skipping column migration")
            return

        new_jobs_columns = [
            ('scoring_weights', 'JSON'),
            ('test_start_time', 'DateTime'),
            ('test_end_time', 'DateTime'),
            ('enable_out_of_sample', 'BOOLEAN DEFAULT 0'),
            ('enable_stability_analysis', 'BOOLEAN DEFAULT 1'),
            ('stability_score', 'Float'),
            ('stability_variance', 'Float'),
            ('is_stable', 'BOOLEAN')
        ]

        for col_name, col_type in new_jobs_columns:
            if col_name not in jobs_columns:
                logger.info(f"Adding column {col_name} to optimization_jobs")
                with self.engine.connect() as conn:
                    conn.execute(
                        text(f"ALTER TABLE optimization_jobs ADD COLUMN {col_name} {col_type}")
                    )
                    conn.commit()

        # Check optimization_results columns
        # Column 1 is 'name' in PRAGMA table_info result
        results_columns = [c[1] for c in self.engine.connect().execute(
            text("PRAGMA table_info(optimization_results)")
        ).fetchall()]

        # Skip if table doesn't exist
        if not results_columns:
            logger.debug("optimization_results table does not exist yet, skipping column migration")
            return

        new_results_columns = [
            ('composite_score', 'Float'),
            ('is_out_of_sample', 'BOOLEAN DEFAULT 0'),
            ('stability_neighbors', 'JSON')
        ]

        for col_name, col_type in new_results_columns:
            if col_name not in results_columns:
                logger.info(f"Adding column {col_name} to optimization_results")
                with self.engine.connect() as conn:
                    conn.execute(
                        text(f"ALTER TABLE optimization_results ADD COLUMN {col_name} {col_type}")
                    )
                    conn.commit()

        logger.info("Database migration complete")

    def ensure_dataset_columns(self):
        """
        Ensure new dataset columns exist in database.

        Adds new columns if they don't exist (for backward compatibility).
        Skips if tables don't exist yet (will be created by create_tables).
        """
        # Check candles columns
        candles_columns = [c[1] for c in self.engine.connect().execute(
            text("PRAGMA table_info(candles)")
        ).fetchall()]

        # Skip if table doesn't exist
        if not candles_columns:
            logger.debug("candles table does not exist yet, skipping column migration")
            return

        # Add dataset_id to candles if it doesn't exist
        if 'dataset_id' not in candles_columns:
            logger.info("Adding column dataset_id to candles")
            with self.engine.connect() as conn:
                conn.execute(
                    text("ALTER TABLE candles ADD COLUMN dataset_id INTEGER NOT NULL DEFAULT 0")
                )
                conn.commit()
                # Create index on dataset_id and open_time
                conn.execute(
                    text("CREATE INDEX IF NOT EXISTS idx_candles_dataset_time ON candles(dataset_id, open_time)")
                )
                conn.commit()

        # Check backtest_jobs columns
        jobs_columns = [c[1] for c in self.engine.connect().execute(
            text("PRAGMA table_info(backtest_jobs)")
        ).fetchall()]

        # Skip if table doesn't exist
        if not jobs_columns:
            logger.debug("backtest_jobs table does not exist yet, skipping column migration")
            return

        # Add dataset_id to backtest_jobs if it doesn't exist
        if 'dataset_id' not in jobs_columns:
            logger.info("Adding column dataset_id to backtest_jobs")
            with self.engine.connect() as conn:
                conn.execute(
                    text("ALTER TABLE backtest_jobs ADD COLUMN dataset_id INTEGER DEFAULT NULL")
                )
                conn.commit()

        logger.info("Dataset columns migration complete")

    def ensure_trade_columns(self):
        """
        Ensure new trade columns exist in database.

        Adds entry_time and exit_time columns if they don't exist (for backward compatibility).
        Skips if tables don't exist yet (will be created by create_tables).
        """
        # Check trades columns
        trades_columns = [c[1] for c in self.engine.connect().execute(
            text("PRAGMA table_info(trades)")
        ).fetchall()]

        # Skip if table doesn't exist
        if not trades_columns:
            logger.debug("trades table does not exist yet, skipping column migration")
            return

        # Add entry_time column if it doesn't exist
        if 'entry_time' not in trades_columns:
            logger.info("Adding column entry_time to trades")
            with self.engine.connect() as conn:
                conn.execute(
                    text("ALTER TABLE trades ADD COLUMN entry_time DateTime")
                )
                conn.commit()
                logger.info("Added entry_time column to trades table")

        # Add exit_time column if it doesn't exist
        if 'exit_time' not in trades_columns:
            logger.info("Adding column exit_time to trades")
            with self.engine.connect() as conn:
                conn.execute(
                    text("ALTER TABLE trades ADD COLUMN exit_time DateTime")
                )
                conn.commit()
                logger.info("Added exit_time column to trades table")

        # If we added new columns, migrate existing data from timestamp to exit_time
        if 'exit_time' not in trades_columns or 'entry_time' not in trades_columns:
            logger.info("Migrating existing trade data...")
            with self.engine.connect() as conn:
                # Update exit_time from timestamp for existing records
                conn.execute(
                    text("UPDATE trades SET exit_time = timestamp WHERE exit_time IS NULL")
                )
                conn.commit()
                # For entry_time, we can't recover it from old data, so set it to exit_time
                # This will result in hold_duration = 0 for old trades, but better than NULL
                conn.execute(
                    text("UPDATE trades SET entry_time = timestamp WHERE entry_time IS NULL")
                )
                conn.commit()
                logger.info("Trade data migration complete")

        logger.info("Trade columns migration complete")

    def ensure_backtest_indexes(self):
        """
        Ensure backtest performance indexes exist in database.

        Creates indexes for common query patterns to improve performance.
        """
        # Check if backtest_jobs table exists
        jobs_columns = [c[1] for c in self.engine.connect().execute(
            text("PRAGMA table_info(backtest_jobs)")
        ).fetchall()]

        # Skip if table doesn't exist
        if not jobs_columns:
            logger.debug("backtest_jobs table does not exist yet, skipping index migration")
            return

        # Get existing indexes
        existing_indexes = [c[1] for c in self.engine.connect().execute(
            text("PRAGMA index_list(backtest_jobs)")
        ).fetchall()]

        # Define indexes to create
        indexes_to_create = [
            ('idx_backtest_strategy_name', 'CREATE INDEX IF NOT EXISTS idx_backtest_strategy_name ON backtest_jobs(strategy_name)'),
            ('idx_backtest_symbol', 'CREATE INDEX IF NOT EXISTS idx_backtest_symbol ON backtest_jobs(symbol)'),
            ('idx_backtest_created_at', 'CREATE INDEX IF NOT EXISTS idx_backtest_created_at ON backtest_jobs(created_at)'),
            ('idx_backtest_strategy_created', 'CREATE INDEX IF NOT EXISTS idx_backtest_strategy_created ON backtest_jobs(strategy_name, created_at)'),
        ]

        # Create missing indexes
        with self.engine.connect() as conn:
            for index_name, create_sql in indexes_to_create:
                if index_name not in existing_indexes:
                    logger.info(f"Creating index {index_name}")
                    conn.execute(text(create_sql))
                    conn.commit()
                else:
                    logger.debug(f"Index {index_name} already exists")

        logger.info("Backtest indexes migration complete")

    def ensure_backtest_columns(self):
        """Add is_favorite column to backtest_jobs if missing."""
        jobs_columns = [c[1] for c in self.engine.connect().execute(
            text("PRAGMA table_info(backtest_jobs)")
        ).fetchall()]

        if not jobs_columns:
            return

        if 'is_favorite' not in jobs_columns:
            logger.info("Adding column is_favorite to backtest_jobs")
            with self.engine.connect() as conn:
                conn.execute(text("ALTER TABLE backtest_jobs ADD COLUMN is_favorite BOOLEAN DEFAULT 0"))
                conn.commit()
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_backtest_is_favorite ON backtest_jobs(is_favorite)"))
                conn.commit()

    @staticmethod
    def _parse_iso_datetime(datetime_str: str) -> datetime:
        """Parse ISO 8601 datetime string, handling both Python and JavaScript formats

        Handles:
        - Python format: "2024-01-01T00:00:00"
        - JavaScript format: "2024-01-01T00:00:00.000Z"
        - With timezone: "2024-01-01T00:00:00+00:00"

        Args:
            datetime_str: ISO 8601 formatted datetime string

        Returns:
            datetime object (timezone-naive)

        Raises:
            ValueError: If string cannot be parsed
        """
        # Replace 'Z' (UTC timezone marker) with '+00:00' for Python compatibility
        if datetime_str.endswith('Z'):
            datetime_str = datetime_str[:-1] + '+00:00'

        dt = datetime.fromisoformat(datetime_str)

        # Return timezone-naive datetime to avoid comparison issues
        # If datetime has timezone info, remove it
        if dt.tzinfo is not None:
            dt = dt.replace(tzinfo=None)

        return dt

    @contextmanager
    def get_session(self) -> Session:
        """Get database session (context manager)

        Yields:
            Session: SQLAlchemy session object

        Raises:
            Exception: Re-raises any database exception after rollback
        """
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            session.close()

    # ========================================
    # Symbol operations
    # ========================================

    def get_all_symbols(self) -> List[str]:
        """Get all symbol names

        Returns:
            List[str]: List of symbol names (e.g., ['BTCUSDT', 'ETHUSDT'])
        """
        with self.get_session() as session:
            symbols = session.query(Symbol).filter(
                Symbol.enabled == True
            ).order_by(Symbol.name).all()

            symbol_names = [s.name for s in symbols]
            logger.debug(f"Retrieved {len(symbol_names)} symbols")
            return symbol_names

    def get_or_create_symbol(self, symbol: str, base_currency: str = None, quote_currency: str = 'USDT') -> Symbol:
        """Get or create a symbol record

        Args:
            symbol: Symbol name (e.g., 'BTCUSDT')
            base_currency: Base currency (e.g., 'BTC'), auto-extracted if not provided
            quote_currency: Quote currency (default: 'USDT')

        Returns:
            Symbol: Symbol object (detached)
        """
        with self.get_session() as session:
            symbol_obj = session.query(Symbol).filter(
                Symbol.name == symbol
            ).first()

            if not symbol_obj:
                if base_currency is None:
                    base_currency = symbol.replace('USDT', '')

                symbol_obj = Symbol(
                    name=symbol,
                    base_currency=base_currency,
                    quote_currency=quote_currency
                )
                session.add(symbol_obj)
                session.flush()
                logger.info(f"Created new symbol: {symbol}")
                # Refresh to get a clean instance
                session.refresh(symbol_obj)

            # Make a copy to avoid detachment issues
            session.expunge(symbol_obj)
            return symbol_obj

    # ========================================
    # Candle operations
    # ========================================

    def get_candles(
        self,
        symbol: str,
        interval: str,
        start_time: str,
        end_time: str
    ) -> List[Candle]:
        """Get candle data

        Args:
            symbol: Symbol name (e.g., 'BTCUSDT')
            interval: Time interval (e.g., '1m', '5m', '1h', '1d')
            start_time: Start time in ISO format
            end_time: End time in ISO format

        Returns:
            List[Candle]: List of candle objects (detached)
        """
        # Parse ISO datetime strings (handles Python and JS formats)
        start_dt = self._parse_iso_datetime(start_time)
        end_dt = self._parse_iso_datetime(end_time)

        # Convert to string format compatible with SQLite (space instead of T)
        start_dt_str = start_dt.strftime('%Y-%m-%d %H:%M:%S')
        end_dt_str = end_dt.strftime('%Y-%m-%d %H:%M:%S')

        with self.get_session() as session:
            symbol_obj = session.query(Symbol).filter(
                Symbol.name == symbol
            ).first()

            if not symbol_obj:
                logger.warning(f"Symbol not found: {symbol}")
                return []

            # Build query - use string comparison for SQLite compatibility
            candles = session.query(Candle).filter(
                Candle.symbol_id == symbol_obj.id,
                Candle.interval == interval,
                Candle.open_time >= start_dt_str,
                Candle.open_time <= end_dt_str
            ).order_by(Candle.open_time).all()

            # Expunge all to avoid detachment issues
            for candle in candles:
                session.expunge(candle)

            logger.debug(f"Retrieved {len(candles)} candles for {symbol} {interval}")
            return candles

    def save_candles(self, candles: List[CandleData], dataset_id: int = None) -> int:
        """Save candles to database

        Args:
            candles: List of CandleData objects to save
            dataset_id: Optional dataset ID to associate candles with

        Returns:
            int: Number of candles saved (excluding duplicates)
        """
        if not candles:
            return 0

        with self.get_session() as session:
            saved_count = 0

            for candle in candles:
                # Get or create symbol
                symbol_obj = session.query(Symbol).filter(
                    Symbol.name == candle.symbol
                ).first()

                if not symbol_obj:
                    symbol_obj = Symbol(
                        name=candle.symbol,
                        base_currency=candle.symbol.replace('USDT', ''),
                        quote_currency='USDT'
                    )
                    session.add(symbol_obj)
                    session.flush()

                # Check if already exists
                existing = session.query(Candle).filter(
                    Candle.symbol_id == symbol_obj.id,
                    Candle.interval == candle.interval,
                    Candle.open_time == candle.open_time
                ).first()

                if not existing:
                    candle_dict = {
                        'symbol_id': symbol_obj.id,
                        'interval': candle.interval,
                        'open_time': candle.open_time,
                        'close_time': candle.close_time,
                        'open_price': candle.open_price,
                        'high_price': candle.high_price,
                        'low_price': candle.low_price,
                        'close_price': candle.close_price,
                        'volume': candle.volume
                    }

                    # Only set dataset_id if provided and not None
                    if dataset_id is not None:
                        candle_dict['dataset_id'] = dataset_id

                    candle_model = Candle(**candle_dict)
                    session.add(candle_model)
                    saved_count += 1
                elif dataset_id is not None and existing.dataset_id == 0:
                    # Update existing candle's dataset_id if it was previously unassigned
                    existing.dataset_id = dataset_id

            logger.info(f"Saved {saved_count} candles ({len(candles) - saved_count} duplicates skipped)")
            return saved_count

    def get_candles_count(
        self,
        symbol: str,
        interval: str,
        start_time: datetime,
        end_time: datetime
    ) -> int:
        """Get candle count

        Args:
            symbol: Symbol name
            interval: Time interval
            start_time: Start datetime
            end_time: End datetime

        Returns:
            int: Number of candles in the specified range
        """
        with self.get_session() as session:
            symbol_obj = session.query(Symbol).filter(
                Symbol.name == symbol
            ).first()

            if not symbol_obj:
                return 0

            count = session.query(Candle).filter(
                Candle.symbol_id == symbol_obj.id,
                Candle.interval == interval,
                Candle.open_time >= start_time,
                Candle.open_time <= end_time
            ).count()

            return count

    def get_downloaded_data_summary(self) -> List[Dict[str, Any]]:
        """
        获取所有已下载数据的摘要信息

        使用 GROUP BY 聚合查询，按 symbol 和 interval 分组，
        计算每个组的统计数据：
        - K线数量 (COUNT)
        - 最早时间 (MIN open_time)
        - 最晚时间 (MAX open_time)

        Returns:
            List[Dict]: 按 symbol 分组的数据摘要列表
        """
        with self.get_session() as session:
            # 查询所有启用的 symbol
            symbols = session.query(Symbol).filter(
                Symbol.enabled == True
            ).order_by(Symbol.name).all()

            result = []
            for symbol in symbols:
                # 聚合查询该 symbol 的所有 interval 数据
                intervals_data = session.query(
                    Candle.interval,
                    func.count(Candle.id).label('count'),
                    func.min(Candle.open_time).label('start_time'),
                    func.max(Candle.open_time).label('end_time')
                ).filter(
                    Candle.symbol_id == symbol.id
                ).group_by(Candle.interval).all()

                # 只包含有数据的 symbol
                if intervals_data:
                    result.append({
                        "symbol": symbol.name,
                        "intervals": [
                            {
                                "interval": interval,
                                "count": count,
                                "start_time": start_time,
                                "end_time": end_time
                            }
                            for interval, count, start_time, end_time in intervals_data
                        ]
                    })

            return result

    def delete_candles_by_symbol_interval(self, symbol: str, interval: str) -> int:
        """
        Delete all candles for a specific symbol and interval.

        Args:
            symbol: Trading pair symbol (e.g., BTCUSDT)
            interval: K-line interval (e.g., 1h)

        Returns:
            Number of deleted records

        Raises:
            Exception: Database error
        """
        with self.get_session() as session:
            # Find symbol first
            symbol_obj = session.query(Symbol).filter(
                Symbol.name == symbol
            ).first()

            if not symbol_obj:
                logger.warning(f"Symbol not found: {symbol}")
                return 0

            count = session.query(Candle)\
                .filter(Candle.symbol_id == symbol_obj.id)\
                .filter(Candle.interval == interval)\
                .delete()

            logger.info(f"Deleted {count} candles for {symbol} {interval}")
            return count

    # ========================================
    # Backtest operations
    # ========================================

    def create_backtest_job(self, job: BacktestJob) -> int:
        """Create backtest job

        Args:
            job: BacktestJob object to create

        Returns:
            int: Created job ID
        """
        with self.get_session() as session:
            session.add(job)
            session.flush()
            job_id = job.id
            logger.info(f"Created backtest job {job_id}: {job.strategy_name} on {job.symbol}")
            return job_id

    def update_backtest_job_status(self, job_id: int, status: str, completed_at: datetime = None):
        """Update backtest job status

        Args:
            job_id: Job ID to update
            status: New status ('pending', 'running', 'completed', 'failed')
            completed_at: Completion timestamp (optional)
        """
        with self.get_session() as session:
            job = session.query(BacktestJob).filter(BacktestJob.id == job_id).first()
            if job:
                job.status = status
                if completed_at:
                    job.completed_at = completed_at
                logger.info(f"Updated backtest job {job_id} status to {status}")
            else:
                logger.warning(f"Backtest job {job_id} not found")

    def save_backtest_result(self, result: BacktestResult, trades: List[Trade]) -> int:
        """Save backtest result and trades

        Args:
            result: BacktestResult object
            trades: List of Trade objects

        Returns:
            int: Result ID
        """
        with self.get_session() as session:
            session.add(result)
            session.flush()
            result_id = result.id

            for trade in trades:
                trade.backtest_job_id = result.backtest_job_id
                session.add(trade)

            logger.info(f"Saved backtest result for job {result.backtest_job_id} with {len(trades)} trades")
            return result_id

    def get_backtest_result(self, job_id: int) -> Optional[BacktestResult]:
        """Get backtest result by job ID

        DEPRECATED: Use get_backtest_result_by_job_id() for clarity.
        This method is kept for backward compatibility but queries by backtest_job_id.

        Args:
            job_id: Backtest job ID

        Returns:
            BacktestResult or None if not found (detached)
        """
        return self.get_backtest_result_by_job_id(job_id)

    def get_backtest_result_by_id(self, result_id: int) -> Optional[BacktestResult]:
        """Get backtest result by result ID (primary key)

        Args:
            result_id: BacktestResult ID (primary key)

        Returns:
            BacktestResult or None if not found (detached)
        """
        with self.get_session() as session:
            result = session.query(BacktestResult).filter(
                BacktestResult.id == result_id
            ).first()
            if result:
                session.expunge(result)
                logger.debug(f"Retrieved backtest result {result_id}")
            return result

    def get_trades(self, backtest_job_id: int) -> List[Trade]:
        """Get trades for backtest

        Args:
            backtest_job_id: Backtest job ID

        Returns:
            List[Trade]: List of trades (detached)
        """
        with self.get_session() as session:
            trades = session.query(Trade).filter(
                Trade.backtest_job_id == backtest_job_id
            ).all()
            for trade in trades:
                session.expunge(trade)
            logger.debug(f"Retrieved {len(trades)} trades for job {backtest_job_id}")
            return trades

    def get_backtest_jobs_by_status(self, status: str) -> List[BacktestJob]:
        """Get backtest jobs by status

        Args:
            status: Job status to filter by

        Returns:
            List[BacktestJob]: List of matching jobs (detached)
        """
        with self.get_session() as session:
            jobs = session.query(BacktestJob).filter(
                BacktestJob.status == status
            ).all()
            for job in jobs:
                session.expunge(job)
            return jobs

    def get_backtest_job(self, job_id: int) -> Optional[BacktestJob]:
        """Get single backtest job by ID

        Args:
            job_id: Job ID to retrieve

        Returns:
            BacktestJob or None if not found (detached)
        """
        with self.get_session() as session:
            job = session.query(BacktestJob).filter(
                BacktestJob.id == job_id
            ).first()
            if job:
                session.expunge(job)
                logger.debug(f"Retrieved backtest job {job_id}")
            return job

    def toggle_backtest_favorite(self, job_id: int) -> bool:
        """Toggle favorite status for a backtest job.

        Returns:
            bool: New is_favorite value after toggle
        """
        with self.get_session() as session:
            job = session.query(BacktestJob).filter(BacktestJob.id == job_id).first()
            if not job:
                raise ValueError(f"Backtest job {job_id} not found")
            job.is_favorite = not job.is_favorite
            logger.info(f"Toggled favorite for job {job_id}: {job.is_favorite}")
            return job.is_favorite

    def get_backtest_result_by_job_id(self, job_id: int) -> Optional[BacktestResult]:
        """Get backtest result by job ID

        Args:
            job_id: Backtest job ID

        Returns:
            BacktestResult or None if not found (detached)
        """
        with self.get_session() as session:
            result = session.query(BacktestResult).filter(
                BacktestResult.backtest_job_id == job_id
            ).first()
            if result:
                session.expunge(result)
                logger.debug(f"Retrieved backtest result for job {job_id}")
            return result

    # ========================================
    # Optimization operations
    # ========================================

    def create_optimization_job(self, job: OptimizationJob) -> int:
        """Create optimization job

        Args:
            job: OptimizationJob object to create

        Returns:
            int: Created job ID
        """
        with self.get_session() as session:
            session.add(job)
            session.flush()
            job_id = job.id
            logger.info(f"Created optimization job {job_id}: {job.strategy_name} on {job.symbol}")
            return job_id

    def update_optimization_job_status(self, job_id: int, status: str, completed_at: datetime = None):
        """Update optimization job status

        Args:
            job_id: Job ID to update
            status: New status
            completed_at: Completion timestamp (optional)
        """
        with self.get_session() as session:
            job = session.query(OptimizationJob).filter(OptimizationJob.id == job_id).first()
            if job:
                job.status = status
                if completed_at:
                    job.completed_at = completed_at
                logger.info(f"Updated optimization job {job_id} status to {status}")
            else:
                logger.warning(f"Optimization job {job_id} not found")

    def save_optimization_result(self, result: OptimizationResult) -> int:
        """Save optimization result

        Args:
            result: OptimizationResult object to save

        Returns:
            int: Result ID
        """
        with self.get_session() as session:
            session.add(result)
            session.flush()
            result_id = result.id
            logger.info(f"Saved optimization result for job {result.optimization_job_id}")
            return result_id

    def get_optimization_job(self, job_id: int) -> Optional[OptimizationJob]:
        """Get single optimization job by ID

        Args:
            job_id: Job ID to retrieve

        Returns:
            OptimizationJob or None if not found (detached)
        """
        with self.get_session() as session:
            job = session.query(OptimizationJob).filter(
                OptimizationJob.id == job_id
            ).first()
            if job:
                session.expunge(job)
                logger.debug(f"Retrieved optimization job {job_id}")
            return job

    def get_optimization_results(self, job_id: int) -> List[OptimizationResult]:
        """Get optimization results for a job

        Args:
            job_id: Optimization job ID

        Returns:
            List[OptimizationResult]: List of results (detached)
        """
        with self.get_session() as session:
            results = session.query(OptimizationResult).filter(
                OptimizationResult.optimization_job_id == job_id
            ).all()
            for result in results:
                session.expunge(result)
            return results

    def get_best_optimization_result(self, job_id: int) -> Optional[OptimizationResult]:
        """Get best optimization result (highest score)

        Args:
            job_id: Optimization job ID

        Returns:
            OptimizationResult: Best result or None (detached)
        """
        with self.get_session() as session:
            result = session.query(OptimizationResult).filter(
                OptimizationResult.optimization_job_id == job_id
            ).order_by(OptimizationResult.score.desc()).first()
            if result:
                session.expunge(result)
            return result

    def update_optimization_job_stability(
        self,
        job_id: int,
        stability_score: float,
        variance: float,
        is_stable: bool
    ):
        """Update stability metrics for optimization job

        Args:
            job_id: Optimization job ID
            stability_score: Stability score (0-1)
            variance: Performance variance
            is_stable: Whether parameters are stable
        """
        with self.get_session() as session:
            job = session.query(OptimizationJob).filter(
                OptimizationJob.id == job_id
            ).first()
            if job:
                job.stability_score = stability_score
                job.stability_variance = variance
                job.is_stable = is_stable
                session.commit()

    def update_optimization_result_stability_neighbors(
        self,
        result_id: int,
        neighbors: List[Dict[str, Any]]
    ):
        """Update stability neighbors for optimization result

        Args:
            result_id: Optimization result ID
            neighbors: List of neighbor test results
        """
        with self.get_session() as session:
            result = session.query(OptimizationResult).filter(
                OptimizationResult.id == result_id
            ).first()
            if result:
                result.stability_neighbors = neighbors
                session.commit()

    # ========================================
    # History query operations
    # ========================================

    def get_backtest_history(
        self,
        strategy_name: Optional[str] = None,
        symbol: Optional[str] = None,
        status: Optional[str] = None,
        is_favorite: Optional[bool] = None,
        sort_by: str = 'created_at',
        sort_order: str = 'desc',
        page: int = 1,
        page_size: int = 20
    ) -> Dict[str, Any]:
        """Get backtest history with filtering, sorting and pagination

        Args:
            strategy_name: Filter by strategy name (optional)
            symbol: Filter by trading pair (optional)
            status: Filter by status (optional)
            is_favorite: Filter by favorite status (optional)
            sort_by: Sort field ('created_at', 'total_return', 'sharpe_ratio')
            sort_order: Sort order ('asc' or 'desc')
            page: Page number (1-based)
            page_size: Number of items per page

        Returns:
            Dict with keys: total, page, page_size, total_pages, items
        """
        with self.get_session() as session:
            # Build base query with join
            query = session.query(BacktestJob).outerjoin(
                BacktestResult,
                BacktestJob.id == BacktestResult.backtest_job_id
            )

            # Apply filters
            if strategy_name:
                query = query.filter(BacktestJob.strategy_name == strategy_name)
            if symbol:
                query = query.filter(BacktestJob.symbol == symbol)
            if status:
                query = query.filter(BacktestJob.status == status)
            if is_favorite is not None:
                query = query.filter(BacktestJob.is_favorite == is_favorite)

            # Get total count
            total = query.count()

            # Apply sorting
            sort_column = BacktestJob.created_at
            if sort_by == 'total_return':
                sort_column = BacktestResult.total_return
            elif sort_by == 'sharpe_ratio':
                sort_column = BacktestResult.sharpe_ratio
            elif sort_by == 'created_at':
                sort_column = BacktestJob.created_at

            if sort_order == 'desc':
                query = query.order_by(sort_column.desc())
            else:
                query = query.order_by(sort_column.asc())

            # Apply pagination
            offset = (page - 1) * page_size
            query = query.offset(offset).limit(page_size)

            # Execute query
            jobs = query.all()

            # Build result items
            items = []
            for job in jobs:
                item = {
                    'job_id': job.id,
                    'strategy_name': job.strategy_name,
                    'symbol': job.symbol,
                    'interval': job.interval,
                    'start_time': job.start_time,
                    'end_time': job.end_time,
                    'status': job.status,
                    'is_favorite': job.is_favorite,
                    'initial_cash': job.result.initial_cash if job.result else None,
                    'final_value': job.result.final_value if job.result else None,
                    'total_return': job.result.total_return if job.result else None,
                    'sharpe_ratio': job.result.sharpe_ratio if job.result else None,
                    'max_drawdown': job.result.max_drawdown if job.result else None,
                    'win_rate': job.result.win_rate if job.result else None,
                    'profit_factor': job.result.profit_factor if job.result else None,
                    'total_trades': job.result.total_trades if job.result else None,
                    'created_at': job.created_at,
                    'completed_at': job.completed_at
                }
                # Include result_id if job is completed and has a result
                if job.result:
                    item['result_id'] = job.result.id
                items.append(item)

            # Calculate total pages
            total_pages = (total + page_size - 1) // page_size if total > 0 else 0

            return {
                'total': total,
                'page': page,
                'page_size': page_size,
                'total_pages': total_pages,
                'items': items
            }

    def get_optimization_history(
        self,
        strategy_name: Optional[str] = None,
        symbol: Optional[str] = None,
        status: Optional[str] = None,
        sort_by: str = 'created_at',
        sort_order: str = 'desc',
        page: int = 1,
        page_size: int = 20
    ) -> Dict[str, Any]:
        """Get optimization history with filtering, sorting and pagination

        Args:
            strategy_name: Filter by strategy name (optional)
            symbol: Filter by trading pair (optional)
            status: Filter by status (optional)
            sort_by: Sort field ('created_at', 'best_score')
            sort_order: Sort order ('asc' or 'desc')
            page: Page number (1-based)
            page_size: Number of items per page

        Returns:
            Dict with keys: total, page, page_size, total_pages, items
        """
        with self.get_session() as session:
            # Build base query - need to get best result for each job
            # Subquery to get best score per job
            best_result_subquery = session.query(
                OptimizationResult.optimization_job_id,
                func.max(OptimizationResult.score).label('best_score')
            ).group_by(OptimizationResult.optimization_job_id).subquery()

            # Main query
            query = session.query(
                OptimizationJob,
                best_result_subquery.c.best_score
            ).outerjoin(
                best_result_subquery,
                OptimizationJob.id == best_result_subquery.c.optimization_job_id
            )

            # Apply filters
            if strategy_name:
                query = query.filter(OptimizationJob.strategy_name == strategy_name)
            if symbol:
                query = query.filter(OptimizationJob.symbol == symbol)
            if status:
                query = query.filter(OptimizationJob.status == status)

            # Get total count
            total = query.count()

            # Apply sorting
            if sort_by == 'best_score':
                if sort_order == 'desc':
                    query = query.order_by(best_result_subquery.c.best_score.desc())
                else:
                    query = query.order_by(best_result_subquery.c.best_score.asc())
            else:  # default: created_at
                if sort_order == 'desc':
                    query = query.order_by(OptimizationJob.created_at.desc())
                else:
                    query = query.order_by(OptimizationJob.created_at.asc())

            # Apply pagination
            offset = (page - 1) * page_size
            query = query.offset(offset).limit(page_size)

            # Execute query
            results = query.all()

            # Build result items
            items = []
            for job, best_score in results:
                # Get best result to extract best_parameters
                best_result = session.query(OptimizationResult).filter(
                    OptimizationResult.optimization_job_id == job.id
                ).order_by(OptimizationResult.score.desc()).first()

                # Count total combinations
                total_combinations = session.query(OptimizationResult).filter(
                    OptimizationResult.optimization_job_id == job.id
                ).count()

                item = {
                    'job_id': job.id,
                    'strategy_name': job.strategy_name,
                    'symbol': job.symbol,
                    'interval': job.interval,
                    'start_time': job.start_time,
                    'end_time': job.end_time,
                    'status': job.status,
                    'best_score': best_score,
                    'best_parameters': best_result.parameters if best_result else None,
                    'total_combinations': total_combinations,
                    'optimization_method': job.optimization_method,
                    'created_at': job.created_at,
                    'completed_at': job.completed_at
                }
                items.append(item)

            # Calculate total pages
            total_pages = (total + page_size - 1) // page_size if total > 0 else 0

            return {
                'total': total,
                'page': page,
                'page_size': page_size,
                'total_pages': total_pages,
                'items': items
            }

    def delete_backtest_job(self, job_id: int) -> bool:
        """Delete a backtest job

        Args:
            job_id: Job ID to delete

        Returns:
            bool: True if deleted successfully

        Raises:
            ValueError: If job is running or not found
        """
        with self.get_session() as session:
            job = session.query(BacktestJob).filter(BacktestJob.id == job_id).first()

            if not job:
                raise ValueError(f"Backtest job {job_id} not found")

            if job.status == 'running':
                raise ValueError(f"Cannot delete running backtest job {job_id}")

            session.delete(job)
            logger.info(f"Deleted backtest job {job_id}")
            return True

    def delete_optimization_job(self, job_id: int) -> bool:
        """Delete an optimization job

        Args:
            job_id: Job ID to delete

        Returns:
            bool: True if deleted successfully

        Raises:
            ValueError: If job is running or not found
        """
        with self.get_session() as session:
            job = session.query(OptimizationJob).filter(OptimizationJob.id == job_id).first()

            if not job:
                raise ValueError(f"Optimization job {job_id} not found")

            if job.status == 'running':
                raise ValueError(f"Cannot delete running optimization job {job_id}")

            session.delete(job)
            logger.info(f"Deleted optimization job {job_id}")
            return True

    # ========================================
    # Dataset management operations
    # ========================================

    def get_all_symbol_interval_combinations(self) -> List[Tuple[str, str]]:
        """Get all distinct symbol + interval combinations for migration.

        Returns:
            List of (symbol, interval) tuples
        """
        with self.SessionLocal() as session:
            results = session.query(
                Symbol.name,
                Candle.interval
            ).join(
                Candle, Symbol.id == Candle.symbol_id
            ).distinct().all()
            return [(r.name, r.interval) for r in results]

    def get_time_range(self, symbol: str, interval: str) -> 'TimeRange':
        """Get min/max timestamp for symbol/interval combination.

        Args:
            symbol: Trading pair symbol
            interval: K-line interval

        Returns:
            TimeRange named tuple with start and end datetime
        """
        from collections import namedtuple
        TimeRange = namedtuple('TimeRange', ['start', 'end'])

        with self.SessionLocal() as session:
            result = session.query(
                func.min(Candle.open_time),
                func.max(Candle.open_time)
            ).join(
                Symbol, Symbol.id == Candle.symbol_id
            ).filter(
                Symbol.name == symbol,
                Candle.interval == interval
            ).first()

            if not result or not result[0]:
                raise ValueError(f"No data found for {symbol} {interval}")

            return TimeRange(start=result[0], end=result[1])

    def create_dataset(
        self,
        name: str,
        symbol: str,
        interval: str,
        start_time: datetime,
        end_time: datetime,
        candle_count: int
    ) -> int:
        """Create dataset record and return dataset_id.

        Args:
            name: Dataset name
            symbol: Trading pair symbol
            interval: K-line interval
            start_time: Start datetime
            end_time: End datetime
            candle_count: Number of candles

        Returns:
            dataset_id (int)
        """
        with self.SessionLocal() as session:
            dataset = Dataset(
                name=name,
                symbol=symbol,
                interval=interval,
                start_time=start_time,
                end_time=end_time,
                candle_count=candle_count,
                created_at=datetime.now()
            )
            session.add(dataset)
            session.commit()
            session.refresh(dataset)
            return dataset.id

    def get_datasets(self) -> List[Dataset]:
        """Get all datasets.

        Returns:
            List of Dataset objects
        """
        with self.SessionLocal() as session:
            return session.query(Dataset).order_by(Dataset.created_at.desc()).all()

    def get_dataset(self, dataset_id: int) -> Dataset:
        """Get single dataset by ID.

        Args:
            dataset_id: Dataset ID

        Returns:
            Dataset object

        Raises:
            ValueError: If dataset not found
        """
        with self.SessionLocal() as session:
            dataset = session.query(Dataset).filter(Dataset.id == dataset_id).first()
            if not dataset:
                raise ValueError(f"Dataset {dataset_id} not found")
            return dataset

    def rename_dataset(self, dataset_id: int, new_name: str) -> bool:
        """Rename dataset.

        Args:
            dataset_id: Dataset ID
            new_name: New name

        Returns:
            True if successful, False if name already exists
        """
        try:
            with self.SessionLocal() as session:
                # Check if name already exists
                existing = session.query(Dataset).filter(Dataset.name == new_name).first()
                if existing:
                    return False

                dataset = session.query(Dataset).filter(Dataset.id == dataset_id).first()
                if not dataset:
                    raise ValueError(f"Dataset {dataset_id} not found")

                dataset.name = new_name
                session.commit()
                return True
        except Exception as e:
            logger.error(f"Failed to rename dataset: {e}")
            return False

    def update_dataset_metadata(
        self,
        dataset_id: int,
        candle_count: int = None,
        start_time: datetime = None,
        end_time: datetime = None
    ) -> bool:
        """Update dataset metadata.

        Args:
            dataset_id: Dataset ID
            candle_count: Optional new candle count
            start_time: Optional new start time
            end_time: Optional new end time

        Returns:
            True if updated successfully

        Raises:
            ValueError: If dataset not found
        """
        with self.get_session() as session:
            dataset = session.query(Dataset).filter(Dataset.id == dataset_id).first()
            if not dataset:
                raise ValueError(f"Dataset {dataset_id} not found")

            # Update fields if provided
            if candle_count is not None:
                dataset.candle_count = candle_count

            if start_time is not None:
                dataset.start_time = start_time

            if end_time is not None:
                dataset.end_time = end_time

            dataset.updated_at = datetime.now()
            session.commit()

            logger.info(f"Updated dataset {dataset_id} metadata")
            return True

    def verify_and_fix_dataset_metadata(self, dataset_id: int) -> Dict[str, Any]:
        """Verify dataset metadata matches actual candles data.

        Checks and corrects:
        - candle_count
        - start_time
        - end_time

        Args:
            dataset_id: Dataset ID to verify

        Returns:
            Dict with verification results:
            {
                'dataset_id': int,
                'was_valid': bool,
                'corrections': Dict[str, Any],
                'actual': Dict[str, Any]
            }
        """
        with self.get_session() as session:
            dataset = session.query(Dataset).filter(Dataset.id == dataset_id).first()
            if not dataset:
                raise ValueError(f"Dataset {dataset_id} not found")

            # Query actual candle statistics
            stats = session.query(
                func.count(Candle.id).label('count'),
                func.min(Candle.open_time).label('min_time'),
                func.max(Candle.open_time).label('max_time')
            ).filter(Candle.dataset_id == dataset_id).first()

            actual_count = stats.count or 0
            actual_start = stats.min_time
            actual_end = stats.max_time

            # Check for discrepancies
            corrections = {}
            was_valid = True

            if dataset.candle_count != actual_count:
                corrections['candle_count'] = {
                    'expected': dataset.candle_count,
                    'actual': actual_count
                }
                dataset.candle_count = actual_count
                was_valid = False

            if actual_start and dataset.start_time != actual_start:
                corrections['start_time'] = {
                    'expected': dataset.start_time.isoformat() if dataset.start_time else None,
                    'actual': actual_start.isoformat()
                }
                dataset.start_time = actual_start
                was_valid = False

            if actual_end and dataset.end_time != actual_end:
                corrections['end_time'] = {
                    'expected': dataset.end_time.isoformat() if dataset.end_time else None,
                    'actual': actual_end.isoformat()
                }
                dataset.end_time = actual_end
                was_valid = False

            # Commit corrections if any
            if corrections:
                dataset.updated_at = datetime.now()
                session.commit()
                logger.info(f"Fixed dataset {dataset_id} metadata: {corrections}")

            return {
                'dataset_id': dataset_id,
                'was_valid': was_valid,
                'corrections': corrections,
                'actual': {
                    'candle_count': actual_count,
                    'start_time': actual_start.isoformat() if actual_start else None,
                    'end_time': actual_end.isoformat() if actual_end else None
                }
            }

    def delete_dataset(self, dataset_id: int) -> int:
        """Delete dataset and associated candles (cascade).

        Args:
            dataset_id: Dataset ID

        Returns:
            Number of candles deleted

        Raises:
            ValueError: If dataset not found
        """
        with self.SessionLocal() as session:
            dataset = session.query(Dataset).filter(Dataset.id == dataset_id).first()
            if not dataset:
                raise ValueError(f"Dataset {dataset_id} not found")

            # Count candles before deletion
            candle_count = session.query(Candle).filter(Candle.dataset_id == dataset_id).count()

            # Delete dataset (cascade will delete candles)
            session.delete(dataset)
            session.commit()

            return candle_count

    def check_dataset_usage(self, dataset_id: int) -> int:
        """Check how many backtest results reference this dataset.

        Args:
            dataset_id: Dataset ID

        Returns:
            Number of backtest results using this dataset
        """
        with self.SessionLocal() as session:
            return session.query(BacktestJob).filter(
                BacktestJob.dataset_id == dataset_id
            ).count()

    def update_candles_dataset_id(
        self,
        symbol: str,
        interval: str,
        dataset_id: int,
        start_time: datetime = None,
        end_time: datetime = None
    ) -> int:
        """Update candles for symbol/interval within time range to have dataset_id.

        Args:
            symbol: Trading pair symbol
            interval: K-line interval
            dataset_id: Dataset ID to assign
            start_time: Optional start datetime (if None, no lower bound)
            end_time: Optional end datetime (if None, no upper bound)

        Returns:
            Number of candles updated
        """
        with self.engine.begin() as conn:
            # Build query with optional time range filters
            sql = """
                UPDATE candles
                SET dataset_id = :dataset_id
                WHERE symbol_id = (
                    SELECT id FROM symbols WHERE name = :symbol
                )
                AND interval = :interval
            """
            params = {
                "dataset_id": dataset_id,
                "symbol": symbol,
                "interval": interval
            }

            # Add time range filters if provided
            if start_time:
                sql += " AND open_time >= :start_time"
                params["start_time"] = start_time

            if end_time:
                sql += " AND open_time <= :end_time"
                params["end_time"] = end_time

            result = conn.execute(text(sql), params)
            return result.rowcount

    def get_candles_by_dataset(
        self,
        dataset_id: int,
        start_time: datetime,
        end_time: datetime
    ) -> List[Candle]:
        """Get candles for dataset within time range.

        Args:
            dataset_id: Dataset ID
            start_time: Start datetime
            end_time: End datetime

        Returns:
            List of Candle objects
        """
        with self.SessionLocal() as session:
            return session.query(Candle).filter(
                Candle.dataset_id == dataset_id,
                Candle.open_time >= start_time,
                Candle.open_time <= end_time
            ).order_by(Candle.open_time).all()

    # ========================================
    # Clear history operations
    # ========================================

    def clear_all_backtest_history(self) -> Dict[str, int]:
        """Clear all backtest history (jobs, results, and trades)

        Returns:
            Dict with counts of deleted records by table:
            {
                "backtest_jobs": int,
                "backtest_results": int,
                "trades": int
            }
        """
        with self.get_session() as session:
            # Count records before deletion
            jobs_count = session.query(BacktestJob).count()
            results_count = session.query(BacktestResult).count()
            trades_count = session.query(Trade).count()

            # Delete all records (trades will be cascade deleted via backtest_results)
            session.query(BacktestResult).delete()
            session.query(BacktestJob).delete()

            logger.info(f"Cleared {jobs_count} backtest jobs, {results_count} results, {trades_count} trades")

            return {
                "backtest_jobs": jobs_count,
                "backtest_results": results_count,
                "trades": trades_count
            }

    def clear_all_optimization_history(self) -> Dict[str, int]:
        """Clear all optimization history (jobs and results)

        Returns:
            Dict with counts of deleted records by table:
            {
                "optimization_jobs": int,
                "optimization_results": int
            }
        """
        with self.get_session() as session:
            # Count records before deletion
            jobs_count = session.query(OptimizationJob).count()
            results_count = session.query(OptimizationResult).count()

            # Delete all records (results will be cascade deleted via jobs)
            session.query(OptimizationJob).delete()

            logger.info(f"Cleared {jobs_count} optimization jobs, {results_count} results")

            return {
                "optimization_jobs": jobs_count,
                "optimization_results": results_count
            }

    # ========================================
    # Hidden strategy operations
    # ========================================

    def get_hidden_strategy_names(self) -> List[str]:
        """Get names of all hidden strategies.

        Returns:
            List[str]: Strategy names that are hidden
        """
        with self.get_session() as session:
            hidden = session.query(HiddenStrategy).filter(
                HiddenStrategy.is_hidden == True
            ).all()
            return [h.strategy_name for h in hidden]

    def hide_strategy(self, strategy_name: str) -> bool:
        """Hide a strategy from the UI.

        Args:
            strategy_name: Name of the strategy to hide

        Returns:
            True if successful
        """
        with self.get_session() as session:
            existing = session.query(HiddenStrategy).filter(
                HiddenStrategy.strategy_name == strategy_name
            ).first()

            if existing:
                existing.is_hidden = True
            else:
                session.add(HiddenStrategy(strategy_name=strategy_name, is_hidden=True))

            logger.info(f"Hidden strategy: {strategy_name}")
            return True

    def show_strategy(self, strategy_name: str) -> bool:
        """Show a previously hidden strategy.

        Args:
            strategy_name: Name of the strategy to show

        Returns:
            True if successful
        """
        with self.get_session() as session:
            existing = session.query(HiddenStrategy).filter(
                HiddenStrategy.strategy_name == strategy_name
            ).first()

            if existing:
                existing.is_hidden = False
                logger.info(f"Showing strategy: {strategy_name}")
            return True

    def clear_all_history(self) -> Dict[str, Any]:
        """Clear all backtest and optimization history

        Returns:
            Dict with counts of deleted records by table:
            {
                "backtest_jobs": int,
                "backtest_results": int,
                "trades": int,
                "optimization_jobs": int,
                "optimization_results": int
            }
        """
        backtest_stats = self.clear_all_backtest_history()
        optimization_stats = self.clear_all_optimization_history()

        return {
            **backtest_stats,
            **optimization_stats
        }
