"""
Tests for dataset management operations in Database class
"""
import pytest
import tempfile
import os
from datetime import datetime
from backend.database import Database
from backend.models.candle import Candle
from backend.models.symbol import Symbol
from backend.models.dataset import Dataset
from backend.models.backtest_job import BacktestJob


@pytest.fixture
def temp_db():
    """Create a temporary database for testing"""
    fd, db_path = tempfile.mkstemp(suffix='.db')
    database_url = f"sqlite:///{db_path}"
    db = Database(database_url)
    db.create_tables()

    # Create a default dataset with ID=1 to satisfy foreign key constraints
    # (the migration adds dataset_id with DEFAULT 0, but FK requires valid dataset)
    with db.get_session() as session:
        default_dataset = Dataset(
            name="Default Dataset",
            symbol="DEFAULT",
            interval="1h",
            start_time=datetime(2024, 1, 1),
            end_time=datetime(2024, 12, 31),
            candle_count=0,
            created_at=datetime.utcnow()
        )
        session.add(default_dataset)
        session.commit()

    yield db
    os.close(fd)
    os.unlink(db_path)


@pytest.fixture
def populated_db(temp_db):
    """Create a database with test data"""
    # Get the default dataset ID created in temp_db
    with temp_db.get_session() as session:
        default_dataset = session.query(Dataset).filter(Dataset.name == "Default Dataset").first()
        default_dataset_id = default_dataset.id

    # Create symbol
    symbol = Symbol(name="BTCUSDT", base_currency="BTC", quote_currency="USDT")
    with temp_db.get_session() as session:
        session.add(symbol)
        session.flush()

        # Add candles for different intervals
        for interval in ['1h', '4h']:
            for i in range(10):
                candle = Candle(
                    symbol_id=symbol.id,
                    interval=interval,
                    open_time=datetime(2024, 1, 1, i),
                    close_time=datetime(2024, 1, 1, i+1),
                    open_price=100.0 + i,
                    high_price=110.0 + i,
                    low_price=90.0 + i,
                    close_price=105.0 + i,
                    volume=1000.0,
                    dataset_id=default_dataset_id  # Use valid dataset ID
                )
                session.add(candle)
        session.commit()

    yield temp_db


class TestGetAllSymbolIntervalCombinations:
    """Test get_all_symbol_interval_combinations method"""

    def test_empty_database(self, temp_db):
        """Test with empty database"""
        combinations = temp_db.get_all_symbol_interval_combinations()
        assert combinations == []

    def test_single_symbol_multiple_intervals(self, populated_db):
        """Test with single symbol and multiple intervals"""
        combinations = populated_db.get_all_symbol_interval_combinations()

        assert len(combinations) == 2
        assert ('BTCUSDT', '1h') in combinations
        assert ('BTCUSDT', '4h') in combinations

    def test_multiple_symbols(self, temp_db):
        """Test with multiple symbols"""
        # Get default dataset ID
        with temp_db.get_session() as session:
            default_dataset = session.query(Dataset).filter(Dataset.name == "Default Dataset").first()
            default_dataset_id = default_dataset.id

        # Create multiple symbols with candles
        with temp_db.get_session() as session:
            for symbol_name in ['BTCUSDT', 'ETHUSDT']:
                symbol = Symbol(name=symbol_name, base_currency=symbol_name.replace('USDT', ''), quote_currency='USDT')
                session.add(symbol)
                session.flush()

                candle = Candle(
                    symbol_id=symbol.id,
                    interval='1h',
                    open_time=datetime(2024, 1, 1),
                    close_time=datetime(2024, 1, 2),
                    open_price=100.0,
                    high_price=110.0,
                    low_price=90.0,
                    close_price=105.0,
                    volume=1000.0,
                    dataset_id=default_dataset_id
                )
                session.add(candle)
            session.commit()

        combinations = temp_db.get_all_symbol_interval_combinations()

        assert len(combinations) == 2
        assert ('BTCUSDT', '1h') in combinations
        assert ('ETHUSDT', '1h') in combinations


class TestGetTimeRange:
    """Test get_time_range method"""

    def test_existing_data(self, populated_db):
        """Test getting time range for existing data"""
        time_range = populated_db.get_time_range('BTCUSDT', '1h')

        assert time_range.start == datetime(2024, 1, 1, 0)
        assert time_range.end == datetime(2024, 1, 1, 9)

    def test_nonexistent_symbol(self, populated_db):
        """Test with non-existent symbol"""
        with pytest.raises(ValueError, match="No data found for NONEXISTUSDT 1h"):
            populated_db.get_time_range('NONEXISTUSDT', '1h')

    def test_nonexistent_interval(self, populated_db):
        """Test with non-existent interval"""
        with pytest.raises(ValueError, match="No data found for BTCUSDT 1d"):
            populated_db.get_time_range('BTCUSDT', '1d')


class TestCreateDataset:
    """Test create_dataset method"""

    def test_create_dataset_basic(self, temp_db):
        """Test basic dataset creation"""
        dataset_id = temp_db.create_dataset(
            name="Test Dataset",
            symbol="BTCUSDT",
            interval="1h",
            start_time=datetime(2024, 1, 1),
            end_time=datetime(2024, 12, 31),
            candle_count=1000
        )

        assert dataset_id > 0

        # Verify dataset was created
        with temp_db.get_session() as session:
            dataset = session.query(Dataset).filter(Dataset.id == dataset_id).first()
            assert dataset is not None
            assert dataset.name == "Test Dataset"
            assert dataset.symbol == "BTCUSDT"
            assert dataset.interval == "1h"
            assert dataset.candle_count == 1000


class TestGetDatasets:
    """Test get_datasets method"""

    def test_empty_list(self, temp_db):
        """Test with only default dataset"""
        datasets = temp_db.get_datasets()
        # Should have only the default dataset created by temp_db fixture
        assert len(datasets) == 1
        assert datasets[0].name == "Default Dataset"

    def test_multiple_datasets(self, temp_db):
        """Test retrieving multiple datasets"""
        # Create datasets
        with temp_db.get_session() as session:
            for i in range(3):
                dataset = Dataset(
                    name=f"Dataset {i}",
                    symbol="BTCUSDT",
                    interval="1h",
                    start_time=datetime(2024, 1, 1),
                    end_time=datetime(2024, 12, 31),
                    candle_count=1000,
                    created_at=datetime(2024, 1, i+1)
                )
                session.add(dataset)
            session.commit()

        datasets = temp_db.get_datasets()

        # Should have 3 new datasets + 1 default dataset = 4 total
        assert len(datasets) == 4
        # Should be ordered by created_at desc
        # Default dataset will be first since it's created before the loop
        assert datasets[1].name == "Dataset 2"
        assert datasets[2].name == "Dataset 1"
        assert datasets[3].name == "Dataset 0"


class TestGetDataset:
    """Test get_dataset method"""

    def test_get_existing_dataset(self, temp_db):
        """Test getting existing dataset"""
        with temp_db.get_session() as session:
            dataset = Dataset(
                name="Test Dataset",
                symbol="BTCUSDT",
                interval="1h",
                start_time=datetime(2024, 1, 1),
                end_time=datetime(2024, 12, 31),
                candle_count=1000,
                created_at=datetime.utcnow()
            )
            session.add(dataset)
            session.commit()
            dataset_id = dataset.id

        retrieved = temp_db.get_dataset(dataset_id)

        assert retrieved.name == "Test Dataset"
        assert retrieved.symbol == "BTCUSDT"

    def test_get_nonexistent_dataset(self, temp_db):
        """Test getting non-existent dataset"""
        with pytest.raises(ValueError, match="Dataset 999 not found"):
            temp_db.get_dataset(999)


class TestRenameDataset:
    """Test rename_dataset method"""

    def test_rename_success(self, temp_db):
        """Test successful rename"""
        with temp_db.get_session() as session:
            dataset = Dataset(
                name="Old Name",
                symbol="BTCUSDT",
                interval="1h",
                start_time=datetime(2024, 1, 1),
                end_time=datetime(2024, 12, 31),
                candle_count=1000,
                created_at=datetime.utcnow()
            )
            session.add(dataset)
            session.commit()
            dataset_id = dataset.id

        result = temp_db.rename_dataset(dataset_id, "New Name")

        assert result is True

        # Verify rename
        with temp_db.get_session() as session:
            dataset = session.query(Dataset).filter(Dataset.id == dataset_id).first()
            assert dataset.name == "New Name"

    def test_rename_duplicate_name(self, temp_db):
        """Test rename to existing name"""
        with temp_db.get_session() as session:
            dataset1 = Dataset(
                name="Dataset 1",
                symbol="BTCUSDT",
                interval="1h",
                start_time=datetime(2024, 1, 1),
                end_time=datetime(2024, 12, 31),
                candle_count=1000,
                created_at=datetime.utcnow()
            )
            dataset2 = Dataset(
                name="Dataset 2",
                symbol="BTCUSDT",
                interval="1h",
                start_time=datetime(2024, 1, 1),
                end_time=datetime(2024, 12, 31),
                candle_count=1000,
                created_at=datetime.utcnow()
            )
            session.add_all([dataset1, dataset2])
            session.commit()
            dataset1_id = dataset1.id
            dataset2_id = dataset2.id

        result = temp_db.rename_dataset(dataset1_id, "Dataset 2")

        assert result is False

    def test_rename_nonexistent_dataset(self, temp_db):
        """Test renaming non-existent dataset"""
        result = temp_db.rename_dataset(999, "New Name")
        # Should return False instead of raising exception
        assert result is False


class TestDeleteDataset:
    """Test delete_dataset method"""

    def test_delete_with_candles(self, temp_db):
        """Test deleting dataset with candles"""
        # Create dataset and candles
        with temp_db.get_session() as session:
            dataset = Dataset(
                name="Test Dataset",
                symbol="BTCUSDT",
                interval="1h",
                start_time=datetime(2024, 1, 1),
                end_time=datetime(2024, 12, 31),
                candle_count=1000,
                created_at=datetime.utcnow()
            )
            session.add(dataset)
            session.flush()

            # Add candles with dataset_id
            symbol = Symbol(name="BTCUSDT", base_currency="BTC", quote_currency="USDT")
            session.add(symbol)
            session.flush()

            for i in range(5):
                candle = Candle(
                    symbol_id=symbol.id,
                    interval="1h",
                    open_time=datetime(2024, 1, 1, i),
                    close_time=datetime(2024, 1, 1, i+1),
                    open_price=100.0 + i,
                    high_price=110.0 + i,
                    low_price=90.0 + i,
                    close_price=105.0 + i,
                    volume=1000.0,
                    dataset_id=dataset.id
                )
                session.add(candle)

            session.commit()
            dataset_id = dataset.id

        candle_count = temp_db.delete_dataset(dataset_id)

        assert candle_count == 5

        # Verify dataset and candles are deleted
        with temp_db.get_session() as session:
            dataset = session.query(Dataset).filter(Dataset.id == dataset_id).first()
            assert dataset is None

            candles = session.query(Candle).filter(Candle.dataset_id == dataset_id).all()
            assert len(candles) == 0

    def test_delete_nonexistent_dataset(self, temp_db):
        """Test deleting non-existent dataset"""
        with pytest.raises(ValueError, match="Dataset 999 not found"):
            temp_db.delete_dataset(999)


class TestCheckDatasetUsage:
    """Test check_dataset_usage method"""

    def test_unused_dataset(self, temp_db):
        """Test checking unused dataset"""
        with temp_db.get_session() as session:
            dataset = Dataset(
                name="Test Dataset",
                symbol="BTCUSDT",
                interval="1h",
                start_time=datetime(2024, 1, 1),
                end_time=datetime(2024, 12, 31),
                candle_count=1000,
                created_at=datetime.utcnow()
            )
            session.add(dataset)
            session.commit()
            dataset_id = dataset.id

        usage_count = temp_db.check_dataset_usage(dataset_id)

        assert usage_count == 0

    def test_used_dataset(self, temp_db):
        """Test checking dataset used in backtest"""
        with temp_db.get_session() as session:
            dataset = Dataset(
                name="Test Dataset",
                symbol="BTCUSDT",
                interval="1h",
                start_time=datetime(2024, 1, 1),
                end_time=datetime(2024, 12, 31),
                candle_count=1000,
                created_at=datetime.utcnow()
            )
            session.add(dataset)
            session.flush()

            # Create backtest job using dataset
            job = BacktestJob(
                strategy_name="TestStrategy",
                symbol="BTCUSDT",
                interval="1h",
                start_time=datetime(2024, 1, 1),
                end_time=datetime(2024, 12, 31),
                parameters={},
                status="pending",
                dataset_id=dataset.id
            )
            session.add(job)
            session.commit()
            dataset_id = dataset.id

        usage_count = temp_db.check_dataset_usage(dataset_id)

        assert usage_count == 1


class TestUpdateCandlesDatasetId:
    """Test update_candles_dataset_id method"""

    def test_update_candles(self, temp_db):
        """Test updating candles dataset_id"""
        # Get default dataset
        with temp_db.get_session() as session:
            default_dataset = session.query(Dataset).filter(Dataset.name == "Default Dataset").first()
            default_dataset_id = default_dataset.id

        # Create symbol and candles with default dataset
        with temp_db.get_session() as session:
            symbol = Symbol(name="BTCUSDT", base_currency="BTC", quote_currency="USDT")
            session.add(symbol)
            session.flush()

            # Create candles with default dataset_id
            for i in range(5):
                candle = Candle(
                    symbol_id=symbol.id,
                    interval="1h",
                    open_time=datetime(2024, 1, 1, i),
                    close_time=datetime(2024, 1, 1, i+1),
                    open_price=100.0 + i,
                    high_price=110.0 + i,
                    low_price=90.0 + i,
                    close_price=105.0 + i,
                    volume=1000.0,
                    dataset_id=default_dataset_id
                )
                session.add(candle)
            session.commit()
            symbol_id = symbol.id

        # Create new dataset
        new_dataset_id = temp_db.create_dataset(
            name="Test Dataset",
            symbol="BTCUSDT",
            interval="1h",
            start_time=datetime(2024, 1, 1),
            end_time=datetime(2024, 12, 31),
            candle_count=5
        )

        # Update candles from default to new dataset
        updated_count = temp_db.update_candles_dataset_id("BTCUSDT", "1h", new_dataset_id)

        assert updated_count == 5

        # Verify update
        with temp_db.get_session() as session:
            candles = session.query(Candle).filter(
                Candle.symbol_id == symbol_id,
                Candle.interval == "1h"
            ).all()

            for candle in candles:
                assert candle.dataset_id == new_dataset_id


class TestGetCandlesByDataset:
    """Test get_candles_by_dataset method"""

    def test_get_candles_in_range(self, temp_db):
        """Test getting candles within time range"""
        # Create dataset and candles
        with temp_db.get_session() as session:
            dataset = Dataset(
                name="Test Dataset",
                symbol="BTCUSDT",
                interval="1h",
                start_time=datetime(2024, 1, 1),
                end_time=datetime(2024, 12, 31),
                candle_count=10,
                created_at=datetime.utcnow()
            )
            session.add(dataset)
            session.flush()

            symbol = Symbol(name="BTCUSDT", base_currency="BTC", quote_currency="USDT")
            session.add(symbol)
            session.flush()

            # Add candles across multiple days
            for day in range(1, 11):
                candle = Candle(
                    symbol_id=symbol.id,
                    interval="1h",
                    open_time=datetime(2024, 1, day),
                    close_time=datetime(2024, 1, day, 1),
                    open_price=100.0 + day,
                    high_price=110.0 + day,
                    low_price=90.0 + day,
                    close_price=105.0 + day,
                    volume=1000.0,
                    dataset_id=dataset.id
                )
                session.add(candle)

            session.commit()
            dataset_id = dataset.id

        # Get candles for date range
        candles = temp_db.get_candles_by_dataset(
            dataset_id,
            datetime(2024, 1, 3),
            datetime(2024, 1, 7)
        )

        # Should get candles for days 3, 4, 5, 6, 7 (5 candles)
        assert len(candles) == 5
        assert all(c.dataset_id == dataset_id for c in candles)

    def test_get_candles_empty_range(self, temp_db):
        """Test getting candles with empty range"""
        # Create dataset
        with temp_db.get_session() as session:
            dataset = Dataset(
                name="Test Dataset",
                symbol="BTCUSDT",
                interval="1h",
                start_time=datetime(2024, 1, 1),
                end_time=datetime(2024, 12, 31),
                candle_count=10,
                created_at=datetime.utcnow()
            )
            session.add(dataset)
            session.commit()
            dataset_id = dataset.id

        # Get candles for future date range
        candles = temp_db.get_candles_by_dataset(
            dataset_id,
            datetime(2025, 1, 1),
            datetime(2025, 12, 31)
        )

        assert len(candles) == 0
