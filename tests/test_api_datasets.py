"""
Tests for Dataset Management API endpoints

Tests verify:
1. Create dataset when downloading data
2. List all datasets
3. Rename dataset
4. Delete dataset with validation
5. Error handling
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime

from backend.database import Database
from backend.models.dataset import Dataset


class TestCreateDatasetOnDownload:
    """Test dataset creation via download endpoint"""

    @pytest.fixture
    def client(self):
        """Create test client"""
        from backend.main import app
        return TestClient(app)

    def test_download_creates_dataset_with_custom_name(self, client):
        """Download creates dataset with custom name"""
        with patch('backend.api.data._data_manager') as mock_manager, \
             patch('backend.api.data._db') as mock_db:

            # Mock download result
            mock_manager.download_and_save = AsyncMock(return_value={
                "symbol": "BTCUSDT",
                "interval": "1h",
                "count": 1000,
                "status": "downloaded",
                "start_time": "2024-01-01T00:00:00",
                "end_time": "2024-01-31T23:59:59"
            })

            # Mock database operations
            mock_db.create_dataset.return_value = 123
            mock_db.update_candles_dataset_id.return_value = 1000

            response = client.post(
                "/api/v1/data/download",
                json={
                    "symbol": "BTCUSDT",
                    "interval": "1h",
                    "start_time": "2024-01-01T00:00:00",
                    "end_time": "2024-01-31T23:59:59",
                    "dataset_name": "My Custom Dataset"
                }
            )

            assert response.status_code == 200
            data = response.json()

            assert data["dataset_id"] == 123
            assert data["dataset_name"] == "My Custom Dataset"
            assert data["status"] == "downloaded"
            assert data["message"] == "Data downloaded successfully"

            # Verify dataset was created
            mock_db.create_dataset.assert_called_once()
            call_args = mock_db.create_dataset.call_args
            assert call_args[1]["name"] == "My Custom Dataset"
            assert call_args[1]["symbol"] == "BTCUSDT"

            # Verify candles were associated
            mock_db.update_candles_dataset_id.assert_called_once_with(
                symbol="BTCUSDT",
                interval="1h",
                dataset_id=123
            )

    def test_download_creates_dataset_with_auto_name(self, client):
        """Download creates dataset with auto-generated name"""
        with patch('backend.api.data._data_manager') as mock_manager, \
             patch('backend.api.data._db') as mock_db:

            # Mock download result
            mock_manager.download_and_save = AsyncMock(return_value={
                "symbol": "BTCUSDT",
                "interval": "1h",
                "count": 1000,
                "status": "downloaded",
                "start_time": "2024-01-01T00:00:00",
                "end_time": "2024-01-31T23:59:59"
            })

            # Mock database operations
            mock_db.create_dataset.return_value = 456
            mock_db.update_candles_dataset_id.return_value = 1000

            response = client.post(
                "/api/v1/data/download",
                json={
                    "symbol": "BTCUSDT",
                    "interval": "1h",
                    "start_time": "2024-01-01T00:00:00",
                    "end_time": "2024-01-31T23:59:59"
                    # No dataset_name provided
                }
            )

            assert response.status_code == 200
            data = response.json()

            assert data["dataset_id"] == 456
            assert data["dataset_name"] is not None
            assert "BTCUSDT" in data["dataset_name"]
            assert "1h" in data["dataset_name"]
            assert "2024-01-01" in data["dataset_name"]
            assert "2024-01-31" in data["dataset_name"]

            # Verify dataset was created with auto-generated name
            mock_db.create_dataset.assert_called_once()
            call_args = mock_db.create_dataset.call_args
            assert call_args[1]["name"] == data["dataset_name"]

    def test_download_dataset_creation_error(self, client):
        """Handle dataset creation error gracefully"""
        with patch('backend.api.data._data_manager') as mock_manager, \
             patch('backend.api.data._db') as mock_db:

            # Mock download result
            mock_manager.download_and_save = AsyncMock(return_value={
                "symbol": "BTCUSDT",
                "interval": "1h",
                "count": 1000,
                "status": "downloaded"
            })

            # Mock database error
            mock_db.create_dataset.side_effect = Exception("Database error")

            response = client.post(
                "/api/v1/data/download",
                json={
                    "symbol": "BTCUSDT",
                    "interval": "1h",
                    "start_time": "2024-01-01T00:00:00",
                    "end_time": "2024-01-31T23:59:59",
                    "dataset_name": "Test Dataset"
                }
            )

            assert response.status_code == 200
            data = response.json()

            assert data["status"] == "error"
            assert "error" in data
            assert "Database error" in data["error"]


class TestListDatasets:
    """Test GET /api/v1/data/datasets endpoint"""

    @pytest.fixture
    def client(self):
        """Create test client"""
        from backend.main import app
        return TestClient(app)

    def test_list_datasets_empty(self, client):
        """List datasets when empty"""
        with patch('backend.api.data._db') as mock_db:
            mock_db.get_datasets.return_value = []

            response = client.get("/api/v1/data/datasets")

            assert response.status_code == 200
            data = response.json()

            assert "datasets" in data
            assert data["datasets"] == []

    def test_list_datasets_multiple(self, client):
        """List multiple datasets"""
        with patch('backend.api.data._db') as mock_db:
            # Create mock datasets
            dataset1 = MagicMock(spec=Dataset)
            dataset1.id = 1
            dataset1.name = "BTC Q1 2024"
            dataset1.symbol = "BTCUSDT"
            dataset1.interval = "1h"
            dataset1.start_time = datetime(2024, 1, 1)
            dataset1.end_time = datetime(2024, 3, 31)
            dataset1.candle_count = 2184
            dataset1.created_at = datetime(2024, 1, 1, 10, 0, 0)

            dataset2 = MagicMock(spec=Dataset)
            dataset2.id = 2
            dataset2.name = "ETH Q1 2024"
            dataset2.symbol = "ETHUSDT"
            dataset2.interval = "1h"
            dataset2.start_time = datetime(2024, 1, 1)
            dataset2.end_time = datetime(2024, 3, 31)
            dataset2.candle_count = 2184
            dataset2.created_at = datetime(2024, 1, 1, 11, 0, 0)

            mock_db.get_datasets.return_value = [dataset1, dataset2]

            response = client.get("/api/v1/data/datasets")

            assert response.status_code == 200
            data = response.json()

            assert len(data["datasets"]) == 2

            # Verify first dataset
            ds1 = data["datasets"][0]
            assert ds1["id"] == 1
            assert ds1["name"] == "BTC Q1 2024"
            assert ds1["symbol"] == "BTCUSDT"
            assert ds1["interval"] == "1h"
            assert ds1["candle_count"] == 2184
            assert "start_time" in ds1
            assert "end_time" in ds1
            assert "created_at" in ds1

            # Verify second dataset
            ds2 = data["datasets"][1]
            assert ds2["id"] == 2
            assert ds2["name"] == "ETH Q1 2024"

    def test_list_datasets_response_format(self, client):
        """Verify response format has ISO datetime strings"""
        with patch('backend.api.data._db') as mock_db:
            dataset = MagicMock(spec=Dataset)
            dataset.id = 1
            dataset.name = "Test Dataset"
            dataset.symbol = "BTCUSDT"
            dataset.interval = "1h"
            dataset.start_time = datetime(2024, 1, 1, 10, 30, 0)
            dataset.end_time = datetime(2024, 12, 31, 23, 59, 59)
            dataset.candle_count = 8760
            dataset.created_at = datetime(2024, 3, 27, 10, 30, 0)

            mock_db.get_datasets.return_value = [dataset]

            response = client.get("/api/v1/data/datasets")

            assert response.status_code == 200
            data = response.json()

            ds = data["datasets"][0]

            # Verify ISO format (contains 'T')
            assert "T" in ds["start_time"]
            assert "T" in ds["end_time"]
            assert "T" in ds["created_at"]

    def test_list_datasets_database_error(self, client):
        """Handle database errors"""
        with patch('backend.api.data._db') as mock_db:
            mock_db.get_datasets.side_effect = Exception("Database error")

            response = client.get("/api/v1/data/datasets")

            assert response.status_code == 500


class TestRenameDataset:
    """Test PUT /api/v1/data/datasets/{id}/rename endpoint"""

    @pytest.fixture
    def client(self):
        """Create test client"""
        from backend.main import app
        return TestClient(app)

    def test_rename_dataset_success(self, client):
        """Rename dataset successfully"""
        with patch('backend.api.data._db') as mock_db:
            mock_db.rename_dataset.return_value = True

            response = client.put(
                "/api/v1/data/datasets/1/rename",
                json={"name": "New Dataset Name"}
            )

            assert response.status_code == 200
            data = response.json()

            assert data["id"] == 1
            assert data["name"] == "New Dataset Name"

            # Verify database was called
            mock_db.rename_dataset.assert_called_once_with(1, "New Dataset Name")

    def test_rename_dataset_missing_name(self, client):
        """Return 400 when name is missing"""
        response = client.put(
            "/api/v1/data/datasets/1/rename",
            json={}
        )

        assert response.status_code == 400

    def test_rename_dataset_duplicate_name(self, client):
        """Return 400 when name already exists"""
        with patch('backend.api.data._db') as mock_db:
            mock_db.rename_dataset.return_value = False

            response = client.put(
                "/api/v1/data/datasets/1/rename",
                json={"name": "Existing Name"}
            )

            assert response.status_code == 400
            data = response.json()

            assert "already exists" in data["detail"]

    def test_rename_dataset_not_found(self, client):
        """Return 404 when dataset not found"""
        with patch('backend.api.data._db') as mock_db:
            mock_db.rename_dataset.side_effect = ValueError("Dataset 999 not found")

            response = client.put(
                "/api/v1/data/datasets/999/rename",
                json={"name": "New Name"}
            )

            assert response.status_code == 404
            data = response.json()

            assert "999" in data["detail"]


class TestDeleteDataset:
    """Test DELETE /api/v1/data/datasets/{id} endpoint"""

    @pytest.fixture
    def client(self):
        """Create test client"""
        from backend.main import app
        return TestClient(app)

    def test_delete_dataset_success(self, client):
        """Delete dataset successfully"""
        with patch('backend.api.data._db') as mock_db:
            mock_db.delete_dataset.return_value = 1000

            response = client.delete("/api/v1/data/datasets/1")

            assert response.status_code == 200
            data = response.json()

            assert data["dataset_id"] == 1
            assert data["deleted_count"] == 1000
            assert data["message"] == "Dataset deleted successfully"

            # Verify database calls
            mock_db.delete_dataset.assert_called_once_with(1)

    def test_delete_dataset_not_found(self, client):
        """Return 404 when dataset not found"""
        with patch('backend.api.data._db') as mock_db:
            mock_db.delete_dataset.side_effect = ValueError("Dataset 999 not found")

            response = client.delete("/api/v1/data/datasets/999")

            assert response.status_code == 404

    def test_delete_dataset_even_when_used_in_backtests(self, client):
        """Allow deletion even when dataset is used in backtests"""
        with patch('backend.api.data._db') as mock_db:
            mock_db.delete_dataset.return_value = 5

            response = client.delete("/api/v1/data/datasets/1")

            assert response.status_code == 200
            data = response.json()
            assert data["deleted_count"] == 5
            assert data["message"] == "Dataset deleted successfully"

    def test_delete_dataset_database_error(self, client):
        """Handle database errors"""
        with patch('backend.api.data._db') as mock_db:
            mock_db.delete_dataset.side_effect = Exception("Database error")

            response = client.delete("/api/v1/data/datasets/1")

            assert response.status_code == 500
