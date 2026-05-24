"""
Tests for DELETE /api/v1/data/{symbol}/{interval} endpoint

Tests verify:
1. Successful deletion returns 200 with confirmation
2. No data found returns 404
3. Database errors return 500
4. Correct response format
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch


class TestDeleteDataBySymbolInterval:
    """Test DELETE /api/v1/data/{symbol}/{interval} endpoint"""

    @pytest.fixture
    def client(self):
        """Create test client"""
        from backend.main import app
        return TestClient(app)

    def test_delete_returns_200_when_data_exists(self, client):
        """DELETE returns 200 with deletion confirmation when data exists"""
        with patch('backend.api.data._db') as mock_db:
            mock_db.delete_candles_by_symbol_interval.return_value = 100

            response = client.delete("/api/v1/data/BTCUSDT/1h")

            assert response.status_code == 200
            data = response.json()
            assert "symbol" in data
            assert "interval" in data
            assert "deleted_count" in data
            assert "message" in data
            assert data["symbol"] == "BTCUSDT"
            assert data["interval"] == "1h"
            assert data["deleted_count"] == 100

    def test_delete_returns_404_when_no_data_found(self, client):
        """DELETE returns 404 when no data exists for symbol/interval"""
        with patch('backend.api.data._db') as mock_db:
            mock_db.delete_candles_by_symbol_interval.return_value = 00

            response = client.delete("/api/v1/data/BTCUSDT/1h")

            assert response.status_code == 404
            data = response.json()
            assert "detail" in data
            assert "No data found" in data["detail"]

    def test_delete_returns_500_on_database_error(self, client):
        """DELETE returns 500 when database error occurs"""
        with patch('backend.api.data._db') as mock_db:
            mock_db.delete_candles_by_symbol_interval.side_effect = Exception("Database connection failed")

            response = client.delete("/api/v1/data/BTCUSDT/1h")

            assert response.status_code == 500
            data = response.json()
            assert "detail" in data

    def test_delete_calls_database_with_correct_parameters(self, client):
        """Verify database method is called with correct parameters"""
        with patch('backend.api.data._db') as mock_db:
            mock_db.delete_candles_by_symbol_interval.return_value = 10

            response = client.delete("/api/v1/data/ETHUSDT/5m")

            assert response.status_code == 200
            mock_db.delete_candles_by_symbol_interval.assert_called_once_with(
                "ETHUSDT",
                "5m"
            )

    def test_delete_with_different_intervals(self, client):
        """Test deletion with different interval values"""
        with patch('backend.api.data._db') as mock_db:
            # Test 1h interval
            mock_db.delete_candles_by_symbol_interval.return_value = 20
            response = client.delete("/api/v1/data/BTCUSDT/1h")
            assert response.status_code == 200
            assert response.json()["deleted_count"] == 20

            # Test 1d interval
            mock_db.delete_candles_by_symbol_interval.return_value = 30
            response = client.delete("/api/v1/data/BTCUSDT/1d")
            assert response.status_code == 200
            assert response.json()["deleted_count"] == 30

    def test_delete_response_includes_success_message(self, client):
        """Response includes user-friendly success message"""
        with patch('backend.api.data._db') as mock_db:
            mock_db.delete_candles_by_symbol_interval.return_value = 100

            response = client.delete("/api/v1/data/BTCUSDT/1h")
            data = response.json()

            assert "message" in data
            assert len(data["message"]) > 0
            assert isinstance(data["message"], str)
