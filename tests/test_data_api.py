"""
Tests for Data Management API

Tests verify:
1. List all available trading symbols
2. Get candle data with filters
3. Download historical data from Binance
4. Check data availability status
5. Error handling (validation, database errors, etc.)
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime
from typing import List

from backend.database import Database, CandleData
from backend.models.symbol import Symbol
from backend.models.candle import Candle


class TestListSymbols:
    """Test GET /api/v1/data/symbols endpoint"""

    @pytest.fixture
    def client(self):
        """Create test client"""
        from backend.main import app
        return TestClient(app)

    def test_list_symbols_returns_200(self, client):
        """GET /api/v1/data/symbols returns 200 status"""
        with patch('backend.api.data._db') as mock_db:
            mock_db.get_all_symbols.return_value = ["BTCUSDT", "ETHUSDT"]

            response = client.get("/api/v1/data/symbols")
            assert response.status_code == 200

    def test_list_symbols_returns_correct_format(self, client):
        """Response has correct format with symbols list"""
        with patch('backend.api.data._db') as mock_db:
            mock_db.get_all_symbols.return_value = ["BTCUSDT", "ETHUSDT"]

            response = client.get("/api/v1/data/symbols")
            data = response.json()

            assert "symbols" in data
            assert isinstance(data["symbols"], list)

    def test_list_multiple_symbols(self, client):
        """List all available symbols"""
        with patch('backend.api.data._db') as mock_db:
            mock_db.get_all_symbols.return_value = [
                "BTCUSDT", "ETHUSDT", "BNBUSDT"
            ]

            response = client.get("/api/v1/data/symbols")
            data = response.json()

            assert len(data["symbols"]) == 3
            assert "BTCUSDT" in data["symbols"]
            assert "ETHUSDT" in data["symbols"]
            assert "BNBUSDT" in data["symbols"]

    def test_list_symbols_empty(self, client):
        """Return empty list when no symbols available"""
        with patch('backend.api.data._db') as mock_db:
            mock_db.get_all_symbols.return_value = []

            response = client.get("/api/v1/data/symbols")
            data = response.json()

            assert response.status_code == 200
            assert data["symbols"] == []


class TestGetCandles:
    """Test GET /api/v1/data/candles endpoint"""

    @pytest.fixture
    def client(self):
        """Create test client"""
        from backend.main import app
        return TestClient(app)

    @pytest.fixture
    def mock_candles(self):
        """Create mock candle objects"""
        candle1 = MagicMock(spec=Candle)
        candle1.open_time = datetime(2024, 1, 1, 0, 0, 0)
        candle1.close_time = datetime(2024, 1, 1, 1, 0, 0)
        candle1.open_price = 42000.0
        candle1.high_price = 42500.0
        candle1.low_price = 41800.0
        candle1.close_price = 42300.0
        candle1.volume = 100.5

        candle2 = MagicMock(spec=Candle)
        candle2.open_time = datetime(2024, 1, 1, 1, 0, 0)
        candle2.close_time = datetime(2024, 1, 1, 2, 0, 0)
        candle2.open_price = 42300.0
        candle2.high_price = 42800.0
        candle2.low_price = 42200.0
        candle2.close_price = 42600.0
        candle2.volume = 120.3

        return [candle1, candle2]

    def test_get_candles_returns_200(self, client, mock_candles):
        """GET /api/v1/data/candles returns 200 with valid parameters"""
        with patch('backend.api.data._db') as mock_db:
            mock_db.get_candles.return_value = mock_candles

            response = client.get(
                "/api/v1/data/candles",
                params={
                    "symbol": "BTCUSDT",
                    "interval": "1h",
                    "start_time": "2024-01-01T00:00:00",
                    "end_time": "2024-01-01T02:00:00"
                }
            )
            assert response.status_code == 200

    def test_get_candles_returns_correct_format(self, client, mock_candles):
        """Response has correct candle data format"""
        with patch('backend.api.data._db') as mock_db:
            mock_db.get_candles.return_value = mock_candles

            response = client.get(
                "/api/v1/data/candles",
                params={
                    "symbol": "BTCUSDT",
                    "interval": "1h",
                    "start_time": "2024-01-01T00:00:00",
                    "end_time": "2024-01-01T02:00:00"
                }
            )
            data = response.json()

            assert "candles" in data
            assert isinstance(data["candles"], list)
            assert len(data["candles"]) == 2

            # Check first candle structure
            candle = data["candles"][0]
            assert "open_time" in candle
            assert "close_time" in candle
            assert "open" in candle
            assert "high" in candle
            assert "low" in candle
            assert "close" in candle
            assert "volume" in candle

    def test_get_candles_with_valid_parameters(self, client, mock_candles):
        """Get candles with valid query parameters"""
        with patch('backend.api.data._db') as mock_db:
            mock_db.get_candles.return_value = mock_candles

            response = client.get(
                "/api/v1/data/candles",
                params={
                    "symbol": "BTCUSDT",
                    "interval": "1h",
                    "start_time": "2024-01-01T00:00:00",
                    "end_time": "2024-01-01T02:00:00"
                }
            )
            data = response.json()

            assert response.status_code == 200
            assert len(data["candles"]) == 2

            # Verify database was called with correct parameters
            mock_db.get_candles.assert_called_once()

    def test_get_candles_invalid_date_format(self, client):
        """Return 400 for invalid datetime format"""
        with patch('backend.api.data._db') as mock_db:
            response = client.get(
                "/api/v1/data/candles",
                params={
                    "symbol": "BTCUSDT",
                    "interval": "1h",
                    "start_time": "invalid-date",
                    "end_time": "2024-01-01T02:00:00"
                }
            )

            assert response.status_code == 400

    def test_get_candles_start_after_end(self, client):
        """Return 400 when start_time >= end_time"""
        with patch('backend.api.data._db') as mock_db:
            response = client.get(
                "/api/v1/data/candles",
                params={
                    "symbol": "BTCUSDT",
                    "interval": "1h",
                    "start_time": "2024-01-02T00:00:00",
                    "end_time": "2024-01-01T00:00:00"
                }
            )

            assert response.status_code == 400
            data = response.json()
            assert "start_time must be before end_time" in data["detail"]

    def test_get_candles_missing_parameters(self, client):
        """Return 400 for missing required parameters"""
        # Missing symbol
        response = client.get(
            "/api/v1/data/candles",
            params={
                "interval": "1h",
                "start_time": "2024-01-01T00:00:00",
                "end_time": "2024-01-01T02:00:00"
            }
        )
        assert response.status_code == 400

        # Missing interval
        response = client.get(
            "/api/v1/data/candles",
            params={
                "symbol": "BTCUSDT",
                "start_time": "2024-01-01T00:00:00",
                "end_time": "2024-01-01T02:00:00"
            }
        )
        assert response.status_code == 400

    def test_get_candles_empty_result(self, client):
        """Return empty candles list when no data found"""
        with patch('backend.api.data._db') as mock_db:
            mock_db.get_candles.return_value = []

            response = client.get(
                "/api/v1/data/candles",
                params={
                    "symbol": "BTCUSDT",
                    "interval": "1h",
                    "start_time": "2024-01-01T00:00:00",
                    "end_time": "2024-01-01T02:00:00"
                }
            )
            data = response.json()

            assert response.status_code == 200
            assert data["candles"] == []


class TestDownloadData:
    """Test POST /api/v1/data/download endpoint"""

    @pytest.fixture
    def client(self):
        """Create test client"""
        from backend.main import app
        return TestClient(app)

    def test_download_data_returns_200(self, client):
        """POST /api/v1/data/download returns 200 with valid data"""
        with patch('backend.api.data._data_manager') as mock_manager:
            mock_manager.download_and_save = AsyncMock(return_value={
                "symbol": "BTCUSDT",
                "interval": "1h",
                "count": 1000,
                "status": "downloaded",
                "start_time": "2024-01-01T00:00:00",
                "end_time": "2024-01-31T23:59:59"
            })

            response = client.post(
                "/api/v1/data/download",
                json={
                    "symbol": "BTCUSDT",
                    "interval": "1h",
                    "start_time": "2024-01-01T00:00:00",
                    "end_time": "2024-01-31T23:59:59"
                }
            )

            assert response.status_code == 200

    def test_download_data_returns_correct_format(self, client):
        """Response includes success message and count"""
        with patch('backend.api.data._data_manager') as mock_manager:
            mock_manager.download_and_save = AsyncMock(return_value={
                "symbol": "BTCUSDT",
                "interval": "1h",
                "count": 1000,
                "status": "downloaded",
                "start_time": "2024-01-01T00:00:00",
                "end_time": "2024-01-31T23:59:59"
            })

            response = client.post(
                "/api/v1/data/download",
                json={
                    "symbol": "BTCUSDT",
                    "interval": "1h",
                    "start_time": "2024-01-01T00:00:00",
                    "end_time": "2024-01-31T23:59:59"
                }
            )
            data = response.json()

            assert "message" in data
            assert "count" in data
            assert "status" in data
            assert data["status"] == "downloaded"
            assert data["count"] == 1000

    def test_download_data_already_exists(self, client):
        """Handle already_exists status"""
        with patch('backend.api.data._data_manager') as mock_manager:
            mock_manager.download_and_save = AsyncMock(return_value={
                "symbol": "BTCUSDT",
                "interval": "1h",
                "count": 500,
                "status": "already_exists"
            })

            response = client.post(
                "/api/v1/data/download",
                json={
                    "symbol": "BTCUSDT",
                    "interval": "1h",
                    "start_time": "2024-01-01T00:00:00",
                    "end_time": "2024-01-31T23:59:59"
                }
            )
            data = response.json()

            assert response.status_code == 200
            assert data["status"] == "already_exists"
            assert data["count"] == 500

    def test_download_data_missing_required_fields(self, client):
        """Return 400 for missing required fields"""
        # Missing symbol
        response = client.post(
            "/api/v1/data/download",
            json={
                "interval": "1h",
                "start_time": "2024-01-01T00:00:00",
                "end_time": "2024-01-31T23:59:59"
            }
        )
        assert response.status_code == 400

        # Missing interval
        response = client.post(
            "/api/v1/data/download",
            json={
                "symbol": "BTCUSDT",
                "start_time": "2024-01-01T00:00:00",
                "end_time": "2024-01-31T23:59:59"
            }
        )
        assert response.status_code == 400

    def test_download_data_invalid_datetime_format(self, client):
        """Return 400 for invalid datetime format"""
        response = client.post(
            "/api/v1/data/download",
            json={
                "symbol": "BTCUSDT",
                "interval": "1h",
                "start_time": "invalid-datetime",
                "end_time": "2024-01-31T23:59:59"
            }
        )

        assert response.status_code == 400
        data = response.json()
        assert "Invalid datetime format" in data["detail"]

    def test_download_data_error_status(self, client):
        """Handle error status from DataManager"""
        with patch('backend.api.data._data_manager') as mock_manager:
            mock_manager.download_and_save = AsyncMock(return_value={
                "symbol": "BTCUSDT",
                "interval": "1h",
                "count": 0,
                "status": "error",
                "error": "Network error"
            })

            response = client.post(
                "/api/v1/data/download",
                json={
                    "symbol": "BTCUSDT",
                    "interval": "1h",
                    "start_time": "2024-01-01T00:00:00",
                    "end_time": "2024-01-31T23:59:59"
                }
            )
            data = response.json()

            assert response.status_code == 200
            assert data["status"] == "error"
            assert "error" in data


class TestGetDataStatus:
    """Test GET /api/v1/data/status/{symbol}/{interval} endpoint"""

    @pytest.fixture
    def client(self):
        """Create test client"""
        from backend.main import app
        return TestClient(app)

    def test_get_status_returns_200(self, client):
        """GET /api/v1/data/status/{symbol}/{interval} returns 200"""
        with patch('backend.api.data._db') as mock_db:
            mock_db.get_candles_count.return_value = 8760

            response = client.get("/api/v1/data/status/BTCUSDT/1h")
            assert response.status_code == 200

    def test_get_status_with_available_data(self, client):
        """Return correct status when data is available"""
        with patch('backend.api.data._db') as mock_db:
            mock_db.get_candles_count.return_value = 8760

            response = client.get("/api/v1/data/status/BTCUSDT/1h")
            data = response.json()

            assert data["symbol"] == "BTCUSDT"
            assert data["interval"] == "1h"
            assert data["available"] is True
            assert data["count"] == 8760

    def test_get_status_with_no_data(self, client):
        """Return correct status when no data available"""
        with patch('backend.api.data._db') as mock_db:
            mock_db.get_candles_count.return_value = 0

            response = client.get("/api/v1/data/status/ETHUSDT/1h")
            data = response.json()

            assert data["symbol"] == "ETHUSDT"
            assert data["interval"] == "1h"
            assert data["available"] is False
            assert data["count"] == 0

    def test_get_status_correct_count(self, client):
        """Verify count is accurate"""
        with patch('backend.api.data._db') as mock_db:
            mock_db.get_candles_count.return_value = 1234

            response = client.get("/api/v1/data/status/BNBUSDT/5m")
            data = response.json()

            assert data["count"] == 1234
            assert data["available"] is True


class TestGetDownloadedData:
    """Test GET /api/v1/data/downloaded endpoint"""

    @pytest.fixture
    def client(self):
        """Create test client"""
        from backend.main import app
        return TestClient(app)

    def test_get_downloaded_data_empty(self, client):
        """测试空数据库返回空列表"""
        with patch('backend.api.data._db') as mock_db:
            mock_db.get_downloaded_data_summary.return_value = []

            response = client.get("/api/v1/data/downloaded")
            assert response.status_code == 200
            data = response.json()
            assert "data" in data
            assert data["data"] == []

    def test_get_downloaded_data_single_symbol(self, client):
        """测试单个 symbol 的数据"""
        with patch('backend.api.data._db') as mock_db:
            # Mock download endpoint
            mock_db.get_candles_count.return_value = 10
            mock_db.get_earliest_candle.return_value = MagicMock(
                open_time=datetime(2024, 1, 1, 0, 0, 0)
            )
            mock_db.get_latest_candle.return_value = MagicMock(
                open_time=datetime(2024, 1, 1, 9, 0, 0)
            )

            # Mock downloaded data summary
            mock_db.get_downloaded_data_summary.return_value = [
                {
                    "symbol": "BTCUSDT",
                    "intervals": [
                        {
                            "interval": "1h",
                            "count": 10,
                            "start_time": datetime(2024, 1, 1, 0, 0, 0),
                            "end_time": datetime(2024, 1, 1, 9, 0, 0)
                        }
                    ]
                }
            ]

            response = client.get("/api/v1/data/downloaded")
            assert response.status_code == 200
            data = response.json()

            assert len(data["data"]) == 1
            assert data["data"][0]["symbol"] == "BTCUSDT"
            assert len(data["data"][0]["intervals"]) == 1

            interval = data["data"][0]["intervals"][0]
            assert interval["interval"] == "1h"
            assert interval["count"] == 10
            assert "start_time" in interval
            assert "end_time" in interval
            assert "T" in interval["start_time"]  # ISO format check

    def test_get_downloaded_data_multiple_symbols(self, client):
        """测试多个 symbol 的数据"""
        with patch('backend.api.data._db') as mock_db:
            # Mock downloaded data summary
            mock_db.get_downloaded_data_summary.return_value = [
                {
                    "symbol": "BTCUSDT",
                    "intervals": [
                        {
                            "interval": "1h",
                            "count": 6,
                            "start_time": datetime(2024, 1, 1, 0, 0, 0),
                            "end_time": datetime(2024, 1, 1, 5, 0, 0)
                        }
                    ]
                },
                {
                    "symbol": "ETHUSDT",
                    "intervals": [
                        {
                            "interval": "1d",
                            "count": 3,
                            "start_time": datetime(2024, 1, 1, 0, 0, 0),
                            "end_time": datetime(2024, 1, 3, 0, 0, 0)
                        }
                    ]
                }
            ]

            response = client.get("/api/v1/data/downloaded")
            assert response.status_code == 200
            data = response.json()

            assert len(data["data"]) == 2

            # 验证按字母顺序排序
            symbols = [item["symbol"] for item in data["data"]]
            assert symbols == ["BTCUSDT", "ETHUSDT"]

    def test_get_downloaded_data_response_format(self, client):
        """验证响应格式正确"""
        with patch('backend.api.data._db') as mock_db:
            # Mock downloaded data summary
            mock_db.get_downloaded_data_summary.return_value = [
                {
                    "symbol": "BTCUSDT",
                    "intervals": [
                        {
                            "interval": "1h",
                            "count": 3,
                            "start_time": datetime(2024, 1, 1, 0, 0, 0),
                            "end_time": datetime(2024, 1, 1, 2, 0, 0)
                        }
                    ]
                }
            ]

            response = client.get("/api/v1/data/downloaded")

            # 验证响应结构
            assert response.status_code == 200
            data = response.json()

            # 检查顶层结构
            assert isinstance(data, dict)
            assert "data" in data
            assert isinstance(data["data"], list)

            # 检查 symbol 结构
            symbol_data = data["data"][0]
            assert "symbol" in symbol_data
            assert "intervals" in symbol_data
            assert isinstance(symbol_data["intervals"], list)

            # 检查 interval 结构
            interval_data = symbol_data["intervals"][0]
            assert "interval" in interval_data
            assert "count" in interval_data
            assert "start_time" in interval_data
            assert "end_time" in interval_data

            # 验证类型
            assert isinstance(interval_data["interval"], str)
            assert isinstance(interval_data["count"], int)
            assert isinstance(interval_data["start_time"], str)
            assert isinstance(interval_data["end_time"], str)

    def test_get_downloaded_data_database_error(self, client):
        """测试数据库错误处理"""
        with patch('backend.api.data._db') as mock_db:
            mock_db.get_downloaded_data_summary.side_effect = Exception("Database error")

            response = client.get("/api/v1/data/downloaded")

            assert response.status_code == 500


class TestErrorHandling:
    """Test error handling"""

    @pytest.fixture
    def client(self):
        """Create test client"""
        from backend.main import app
        return TestClient(app)

    def test_database_error_on_get_symbols(self, client):
        """Handle database errors gracefully"""
        with patch('backend.api.data._db') as mock_db:
            mock_db.get_all_symbols.side_effect = Exception("Database error")

            response = client.get("/api/v1/data/symbols")

            assert response.status_code == 500

    def test_database_error_on_get_candles(self, client):
        """Handle database errors gracefully in get_candles"""
        with patch('backend.api.data._db') as mock_db:
            mock_db.get_candles.side_effect = Exception("Database error")

            response = client.get(
                "/api/v1/data/candles",
                params={
                    "symbol": "BTCUSDT",
                    "interval": "1h",
                    "start_time": "2024-01-01T00:00:00",
                    "end_time": "2024-01-01T02:00:00"
                }
            )

            assert response.status_code == 500
