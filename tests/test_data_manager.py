import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from backend.core.data_manager import DataManager
from backend.core.data_source import CandleData


@pytest.fixture
def mock_data_source():
    """Create mock DataSource"""
    source = AsyncMock()
    return source


@pytest.fixture
def mock_database():
    """Create mock Database"""
    db = MagicMock()
    return db


@pytest.fixture
def sample_candles():
    """Create sample valid candle data"""
    now = datetime(2024, 1, 1, 0, 0, 0)
    return [
        CandleData(
            symbol='BTCUSDT',
            interval='1m',
            open_time=now,
            close_time=now + timedelta(minutes=1),
            open_price=50000.0,
            high_price=50100.0,
            low_price=49900.0,
            close_price=50050.0,
            volume=100.0
        ),
        CandleData(
            symbol='BTCUSDT',
            interval='1m',
            open_time=now + timedelta(minutes=1),
            close_time=now + timedelta(minutes=2),
            open_price=50050.0,
            high_price=50200.0,
            low_price=50000.0,
            close_price=50150.0,
            volume=150.0
        ),
    ]


@pytest.fixture
def invalid_candles():
    """Create candle data with various validation issues"""
    now = datetime(2024, 1, 1, 0, 0, 0)
    return [
        # Invalid: high < low
        CandleData(
            symbol='BTCUSDT',
            interval='1m',
            open_time=now,
            close_time=now + timedelta(minutes=1),
            open_price=50000.0,
            high_price=49900.0,  # high < low
            low_price=50000.0,
            close_price=50000.0,
            volume=100.0
        ),
        # Invalid: open price out of range
        CandleData(
            symbol='BTCUSDT',
            interval='1m',
            open_time=now + timedelta(minutes=1),
            close_time=now + timedelta(minutes=2),
            open_price=50200.0,  # > high
            high_price=50100.0,
            low_price=49900.0,
            close_price=50000.0,
            volume=100.0
        ),
        # Invalid: non-positive price
        CandleData(
            symbol='BTCUSDT',
            interval='1m',
            open_time=now + timedelta(minutes=2),
            close_time=now + timedelta(minutes=3),
            open_price=0.0,  # non-positive
            high_price=50100.0,
            low_price=49900.0,
            close_price=50000.0,
            volume=100.0
        ),
        # Valid candle
        CandleData(
            symbol='BTCUSDT',
            interval='1m',
            open_time=now + timedelta(minutes=3),
            close_time=now + timedelta(minutes=4),
            open_price=50000.0,
            high_price=50100.0,
            low_price=49900.0,
            close_price=50050.0,
            volume=100.0
        ),
    ]


class TestDataManager:
    """Test suite for DataManager"""

    def test_init(self, mock_data_source, mock_database):
        """Test DataManager initialization"""
        manager = DataManager(mock_data_source, mock_database)

        assert manager.data_source is mock_data_source
        assert manager.db is mock_database

    @pytest.mark.asyncio
    async def test_download_and_save_success(
        self, mock_data_source, mock_database, sample_candles
    ):
        """Test successful download and save"""
        mock_database.get_candles_count.return_value = 0
        mock_data_source.fetch_candles.return_value = sample_candles
        mock_database.save_candles.return_value = 2

        manager = DataManager(mock_data_source, mock_database)
        start_time = datetime(2024, 1, 1)
        end_time = datetime(2024, 1, 2)

        result = await manager.download_and_save(
            symbol='BTCUSDT',
            interval='1m',
            start_time=start_time,
            end_time=end_time
        )

        assert result['symbol'] == 'BTCUSDT'
        assert result['interval'] == '1m'
        assert result['count'] == 2
        assert result['status'] == 'downloaded'
        assert result['start_time'] == start_time.isoformat()
        assert result['end_time'] == end_time.isoformat()

        mock_data_source.fetch_candles.assert_called_once_with(
            'BTCUSDT', '1m', start_time, end_time
        )
        mock_database.save_candles.assert_called_once()

    @pytest.mark.asyncio
    async def test_download_and_save_already_exists(
        self, mock_data_source, mock_database
    ):
        """Test when data already exists"""
        mock_database.get_candles_count.return_value = 100

        manager = DataManager(mock_data_source, mock_database)
        start_time = datetime(2024, 1, 1)
        end_time = datetime(2024, 1, 2)

        result = await manager.download_and_save(
            symbol='BTCUSDT',
            interval='1m',
            start_time=start_time,
            end_time=end_time
        )

        assert result['symbol'] == 'BTCUSDT'
        assert result['interval'] == '1m'
        assert result['count'] == 100
        assert result['status'] == 'already_exists'

        # Should not call fetch or save
        mock_data_source.fetch_candles.assert_not_called()
        mock_database.save_candles.assert_not_called()

    @pytest.mark.asyncio
    async def test_download_and_save_invalid_time_range(
        self, mock_data_source, mock_database
    ):
        """Test error when start_time >= end_time"""
        manager = DataManager(mock_data_source, mock_database)
        start_time = datetime(2024, 1, 2)
        end_time = datetime(2024, 1, 1)  # End before start

        result = await manager.download_and_save(
            symbol='BTCUSDT',
            interval='1m',
            start_time=start_time,
            end_time=end_time
        )

        assert result['status'] == 'error'
        assert 'start_time must be before end_time' in result['error']

    @pytest.mark.asyncio
    async def test_download_and_save_no_data_from_source(
        self, mock_data_source, mock_database
    ):
        """Test error when data source returns empty"""
        mock_database.get_candles_count.return_value = 0
        mock_data_source.fetch_candles.return_value = []

        manager = DataManager(mock_data_source, mock_database)
        start_time = datetime(2024, 1, 1)
        end_time = datetime(2024, 1, 2)

        result = await manager.download_and_save(
            symbol='BTCUSDT',
            interval='1m',
            start_time=start_time,
            end_time=end_time
        )

        assert result['status'] == 'error'
        assert 'No data received' in result['error']

    @pytest.mark.asyncio
    async def test_download_and_save_source_exception(
        self, mock_data_source, mock_database
    ):
        """Test handling of exception from data source"""
        mock_database.get_candles_count.return_value = 0
        mock_data_source.fetch_candles.side_effect = Exception("Network error")

        manager = DataManager(mock_data_source, mock_database)
        start_time = datetime(2024, 1, 1)
        end_time = datetime(2024, 1, 2)

        result = await manager.download_and_save(
            symbol='BTCUSDT',
            interval='1m',
            start_time=start_time,
            end_time=end_time
        )

        assert result['status'] == 'error'
        assert 'Network error' in result['error']

    def test_validate_candles_valid(self, mock_data_source, mock_database, sample_candles):
        """Test validation of valid candles"""
        manager = DataManager(mock_data_source, mock_database)

        validated = manager._validate_candles(sample_candles, '1m')

        assert len(validated) == 2
        assert validated == sample_candles

    def test_validate_candles_filters_invalid(
        self, mock_data_source, mock_database, invalid_candles
    ):
        """Test validation filters out invalid candles"""
        manager = DataManager(mock_data_source, mock_database)

        validated = manager._validate_candles(invalid_candles, '1m')

        # Only the last candle should pass validation
        assert len(validated) == 1
        assert validated[0].open_price == 50000.0

    def test_validate_candles_high_less_than_low(
        self, mock_data_source, mock_database
    ):
        """Test validation rejects candle where high < low"""
        manager = DataManager(mock_data_source, mock_database)
        now = datetime(2024, 1, 1)

        candles = [
            CandleData(
                symbol='BTCUSDT',
                interval='1m',
                open_time=now,
                close_time=now + timedelta(minutes=1),
                open_price=50000.0,
                high_price=49900.0,  # high < low
                low_price=50000.0,
                close_price=50000.0,
                volume=100.0
            )
        ]

        validated = manager._validate_candles(candles, '1m')

        assert len(validated) == 0

    def test_validate_candles_open_out_of_range(
        self, mock_data_source, mock_database
    ):
        """Test validation rejects candle where open is out of range"""
        manager = DataManager(mock_data_source, mock_database)
        now = datetime(2024, 1, 1)

        candles = [
            CandleData(
                symbol='BTCUSDT',
                interval='1m',
                open_time=now,
                close_time=now + timedelta(minutes=1),
                open_price=50200.0,  # > high
                high_price=50100.0,
                low_price=49900.0,
                close_price=50000.0,
                volume=100.0
            )
        ]

        validated = manager._validate_candles(candles, '1m')

        assert len(validated) == 0

    def test_validate_candles_close_out_of_range(
        self, mock_data_source, mock_database
    ):
        """Test validation rejects candle where close is out of range"""
        manager = DataManager(mock_data_source, mock_database)
        now = datetime(2024, 1, 1)

        candles = [
            CandleData(
                symbol='BTCUSDT',
                interval='1m',
                open_time=now,
                close_time=now + timedelta(minutes=1),
                open_price=50000.0,
                high_price=50100.0,
                low_price=49900.0,
                close_price=49800.0,  # < low
                volume=100.0
            )
        ]

        validated = manager._validate_candles(candles, '1m')

        assert len(validated) == 0

    def test_validate_candles_non_positive_price(
        self, mock_data_source, mock_database
    ):
        """Test validation rejects candle with non-positive price"""
        manager = DataManager(mock_data_source, mock_database)
        now = datetime(2024, 1, 1)

        candles = [
            CandleData(
                symbol='BTCUSDT',
                interval='1m',
                open_time=now,
                close_time=now + timedelta(minutes=1),
                open_price=0.0,  # non-positive
                high_price=50100.0,
                low_price=49900.0,
                close_price=50000.0,
                volume=100.0
            )
        ]

        validated = manager._validate_candles(candles, '1m')

        assert len(validated) == 0

    def test_validate_candles_empty_list(
        self, mock_data_source, mock_database
    ):
        """Test validation of empty candle list"""
        manager = DataManager(mock_data_source, mock_database)

        validated = manager._validate_candles([], '1m')

        assert len(validated) == 0
