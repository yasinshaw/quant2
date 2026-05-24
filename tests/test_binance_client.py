import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch, MagicMock
import httpx

from backend.utils.binance_client import BinanceDataSource
from backend.core.data_source import CandleData


@pytest.fixture
def binance_client():
    """Create BinanceDataSource instance"""
    return BinanceDataSource()


@pytest.fixture
def mock_klines_response():
    """Mock Binance klines API response"""
    return [
        [
            1609459200000,  # Open time (2021-01-01 00:00:00)
            "28923.63",     # Open
            "28927.38",     # High
            "28900.00",     # Low
            "28910.01",     # Close
            "12.345",       # Volume
            1609459259999,  # Close time
            "356789.12",    # Quote asset volume
            450,            # Number of trades
            "6.78",         # Taker buy base volume
            "195678.90",    # Taker buy quote volume
            "0"             # Ignore
        ],
        [
            1609459260000,  # Open time (2021-01-01 00:01:00)
            "28910.01",     # Open
            "28935.50",     # High
            "28905.00",     # Low
            "28925.00",     # Close
            "15.678",       # Volume
            1609459319999,  # Close time
            "452123.45",    # Quote asset volume
            520,            # Number of trades
            "8.90",         # Taker buy base volume
            "257123.45",    # Taker buy quote volume
            "0"             # Ignore
        ]
    ]


@pytest.fixture
def mock_exchange_info_response():
    """Mock Binance exchange info API response"""
    return {
        "symbols": [
            {
                "symbol": "BTCUSDT",
                "status": "TRADING",
                "quoteAsset": "USDT"
            },
            {
                "symbol": "ETHUSDT",
                "status": "TRADING",
                "quoteAsset": "USDT"
            },
            {
                "symbol": "BTCBUSD",
                "status": "TRADING",
                "quoteAsset": "BUSD"  # Should be filtered out
            },
            {
                "symbol": "XRPUSDT",
                "status": "BREAK",  # Should be filtered out
                "quoteAsset": "USDT"
            }
        ]
    }


class TestBinanceDataSource:
    """Test suite for BinanceDataSource"""

    @pytest.mark.asyncio
    async def test_fetch_candles_success(self, binance_client, mock_klines_response):
        """Test successful candle fetching"""
        with patch.object(binance_client.client, 'get', new_callable=AsyncMock) as mock_get:
            mock_response = MagicMock()
            mock_response.json.return_value = mock_klines_response
            mock_response.raise_for_status = MagicMock()
            mock_get.return_value = mock_response

            start_time = datetime(2021, 1, 1, 0, 0, 0)
            end_time = datetime(2021, 1, 1, 0, 2, 0)

            candles = await binance_client.fetch_candles(
                symbol="BTCUSDT",
                interval="1m",
                start_time=start_time,
                end_time=end_time
            )

            assert len(candles) == 2
            assert all(isinstance(c, CandleData) for c in candles)
            assert candles[0].symbol == "BTCUSDT"
            assert candles[0].interval == "1m"
            assert candles[0].open_price == 28923.63
            assert candles[0].high_price == 28927.38
            assert candles[0].low_price == 28900.00
            assert candles[0].close_price == 28910.01
            assert candles[0].volume == 12.345

    @pytest.mark.asyncio
    async def test_fetch_candles_rate_limit_retry(self, binance_client, mock_klines_response):
        """Test rate limit retry with exponential backoff"""
        with patch.object(binance_client.client, 'get', new_callable=AsyncMock) as mock_get:
            # First call: rate limit error
            error_response = MagicMock()
            error_response.status_code = 429
            http_error = httpx.HTTPStatusError(
                "Rate limit",
                request=MagicMock(),
                response=error_response
            )

            # Second call: success
            success_response = MagicMock()
            success_response.json.return_value = mock_klines_response
            success_response.raise_for_status = MagicMock()

            mock_get.side_effect = [http_error, success_response]

            start_time = datetime(2021, 1, 1, 0, 0, 0)
            end_time = datetime(2021, 1, 1, 0, 2, 0)

            candles = await binance_client.fetch_candles(
                symbol="BTCUSDT",
                interval="1m",
                start_time=start_time,
                end_time=end_time
            )

            assert len(candles) == 2
            assert mock_get.call_count == 2

    @pytest.mark.asyncio
    async def test_fetch_candles_max_retries_exceeded(self, binance_client):
        """Test max retries exceeded raises error"""
        with patch.object(binance_client.client, 'get', new_callable=AsyncMock) as mock_get:
            error_response = MagicMock()
            error_response.status_code = 429
            http_error = httpx.HTTPStatusError(
                "Rate limit",
                request=MagicMock(),
                response=error_response
            )
            mock_get.side_effect = http_error

            start_time = datetime(2021, 1, 1, 0, 0, 0)
            end_time = datetime(2021, 1, 1, 0, 2, 0)

            with pytest.raises(httpx.HTTPStatusError):
                await binance_client.fetch_candles(
                    symbol="BTCUSDT",
                    interval="1m",
                    start_time=start_time,
                    end_time=end_time
                )

            assert mock_get.call_count == 3  # Initial + 2 retries before max_retries

    @pytest.mark.asyncio
    async def test_fetch_candles_empty_response(self, binance_client):
        """Test handling of empty response"""
        with patch.object(binance_client.client, 'get', new_callable=AsyncMock) as mock_get:
            mock_response = MagicMock()
            mock_response.json.return_value = []
            mock_response.raise_for_status = MagicMock()
            mock_get.return_value = mock_response

            start_time = datetime(2021, 1, 1, 0, 0, 0)
            end_time = datetime(2021, 1, 1, 0, 2, 0)

            candles = await binance_client.fetch_candles(
                symbol="BTCUSDT",
                interval="1m",
                start_time=start_time,
                end_time=end_time
            )

            assert len(candles) == 0

    @pytest.mark.asyncio
    async def test_get_supported_symbols(self, binance_client, mock_exchange_info_response):
        """Test getting supported USDT trading pairs"""
        with patch.object(binance_client.client, 'get', new_callable=AsyncMock) as mock_get:
            mock_response = MagicMock()
            mock_response.json.return_value = mock_exchange_info_response
            mock_response.raise_for_status = MagicMock()
            mock_get.return_value = mock_response

            symbols = await binance_client.get_supported_symbols()

            assert len(symbols) == 2
            assert "BTCUSDT" in symbols
            assert "ETHUSDT" in symbols
            assert "BTCBUSD" not in symbols
            assert "XRPUSDT" not in symbols
            assert symbols == sorted(symbols)  # Should be sorted

    @pytest.mark.asyncio
    async def test_get_supported_symbols_error(self, binance_client):
        """Test error handling when getting symbols"""
        with patch.object(binance_client.client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = httpx.HTTPError("Network error")

            with pytest.raises(httpx.HTTPError):
                await binance_client.get_supported_symbols()

    @pytest.mark.asyncio
    async def test_get_supported_intervals(self, binance_client):
        """Test getting supported intervals"""
        intervals = await binance_client.get_supported_intervals()

        assert isinstance(intervals, list)
        assert '1m' in intervals
        assert '5m' in intervals
        assert '15m' in intervals
        assert '1h' in intervals
        assert '4h' in intervals
        assert '1d' in intervals

    def test_init_with_custom_url(self):
        """Test initialization with custom base URL"""
        custom_url = "https://testnet.binance.vision"
        client = BinanceDataSource(base_url=custom_url)

        assert client.base_url == custom_url
        assert isinstance(client.client, httpx.AsyncClient)
