"""
Tests for Strategies Management API

Tests verify:
1. List all available strategies
2. Refresh strategy list from folder
3. Get specific strategy details
4. Error handling (404, etc.)
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from typing import Dict, Type

from backend.core.strategy_base import StrategyBase


class MockStrategy1(StrategyBase):
    """Mock strategy 1 for testing"""

    strategy_name = "Mock Strategy 1"
    strategy_version = "1.0.0"
    strategy_description = "First mock strategy for testing"

    def next(self):
        pass

    @staticmethod
    def get_parameters():
        return {
            'period': {
                'type': 'int',
                'default': 10,
                'min': 5,
                'max': 50,
                'description': 'Strategy period'
            }
        }


class MockStrategy2(StrategyBase):
    """Mock strategy 2 for testing"""

    strategy_name = "Mock Strategy 2"
    strategy_version = "2.0.0"
    strategy_description = "Second mock strategy for testing"

    def next(self):
        pass

    @staticmethod
    def get_parameters():
        return {
            'threshold': {
                'type': 'float',
                'default': 0.5,
                'min': 0.0,
                'max': 1.0,
                'description': 'Buy threshold'
            }
        }


class TestListStrategies:
    """Test GET /api/v1/strategies endpoint"""

    @pytest.fixture
    def client(self):
        """Create test client"""
        from backend.main import app
        return TestClient(app)

    def test_list_strategies_returns_200(self, client):
        """GET /api/v1/strategies returns 200 status"""
        with patch('backend.api.strategies._loader') as mock_loader:
            mock_loader.load_all.return_value = {
                "Mock Strategy 1": MockStrategy1,
                "Mock Strategy 2": MockStrategy2
            }

            response = client.get("/api/v1/strategies")
            assert response.status_code == 200

    def test_list_strategies_returns_correct_format(self, client):
        """Response has correct format with strategies list"""
        with patch('backend.api.strategies._loader') as mock_loader:
            mock_loader.load_all.return_value = {
                "Mock Strategy 1": MockStrategy1,
                "Mock Strategy 2": MockStrategy2
            }

            response = client.get("/api/v1/strategies")
            data = response.json()

            assert "strategies" in data
            assert isinstance(data["strategies"], list)

    def test_list_strategies_includes_metadata(self, client):
        """Each strategy includes name, version, and description"""
        with patch('backend.api.strategies._loader') as mock_loader:
            mock_loader.load_all.return_value = {
                "Mock Strategy 1": MockStrategy1
            }

            response = client.get("/api/v1/strategies")
            data = response.json()

            assert len(data["strategies"]) == 1
            strategy = data["strategies"][0]

            assert "name" in strategy
            assert "version" in strategy
            assert "description" in strategy

            assert strategy["name"] == "Mock Strategy 1"
            assert strategy["version"] == "1.0.0"
            assert strategy["description"] == "First mock strategy for testing"

    def test_list_multiple_strategies(self, client):
        """List all available strategies"""
        with patch('backend.api.strategies._loader') as mock_loader:
            mock_loader.load_all.return_value = {
                "Mock Strategy 1": MockStrategy1,
                "Mock Strategy 2": MockStrategy2
            }

            response = client.get("/api/v1/strategies")
            data = response.json()

            assert len(data["strategies"]) == 2
            names = [s["name"] for s in data["strategies"]]
            assert "Mock Strategy 1" in names
            assert "Mock Strategy 2" in names

    def test_list_strategies_empty(self, client):
        """Return empty list when no strategies available"""
        with patch('backend.api.strategies._loader') as mock_loader:
            mock_loader.load_all.return_value = {}

            response = client.get("/api/v1/strategies")
            data = response.json()

            assert response.status_code == 200
            assert data["strategies"] == []


class TestRefreshStrategies:
    """Test POST /api/v1/strategies/refresh endpoint"""

    @pytest.fixture
    def client(self):
        """Create test client"""
        from backend.main import app
        return TestClient(app)

    def test_refresh_strategies_returns_200(self, client):
        """POST /api/v1/strategies/refresh returns 200 status"""
        with patch('backend.api.strategies._loader') as mock_loader:
            mock_loader.load_all.return_value = {
                "Mock Strategy 1": MockStrategy1
            }

            response = client.post("/api/v1/strategies/refresh")
            assert response.status_code == 200

    def test_refresh_strategies_returns_message(self, client):
        """Response includes success message"""
        with patch('backend.api.strategies._loader') as mock_loader:
            mock_loader.load_all.return_value = {
                "Mock Strategy 1": MockStrategy1
            }

            response = client.post("/api/v1/strategies/refresh")
            data = response.json()

            assert "message" in data
            assert data["message"] == "Strategies refreshed"

    def test_refresh_strategies_returns_count(self, client):
        """Response includes count of loaded strategies"""
        with patch('backend.api.strategies._loader') as mock_loader:
            mock_loader.load_all.return_value = {
                "Mock Strategy 1": MockStrategy1,
                "Mock Strategy 2": MockStrategy2
            }

            response = client.post("/api/v1/strategies/refresh")
            data = response.json()

            assert "count" in data
            assert data["count"] == 2

    def test_refresh_strategies_calls_loader(self, client):
        """Verify load_all is called to reload strategies"""
        with patch('backend.api.strategies._loader') as mock_loader:
            mock_loader.load_all.return_value = {}

            client.post("/api/v1/strategies/refresh")

            mock_loader.load_all.assert_called_once()


class TestGetStrategy:
    """Test GET /api/v1/strategies/{name} endpoint"""

    @pytest.fixture
    def client(self):
        """Create test client"""
        from backend.main import app
        return TestClient(app)

    def test_get_strategy_returns_200(self, client):
        """GET /api/v1/strategies/{name} returns 200 for existing strategy"""
        with patch('backend.api.strategies._loader') as mock_loader:
            mock_loader.load_all.return_value = {
                "Mock Strategy 1": MockStrategy1
            }

            response = client.get("/api/v1/strategies/Mock Strategy 1")
            assert response.status_code == 200

    def test_get_strategy_returns_correct_data(self, client):
        """Response includes all strategy metadata"""
        with patch('backend.api.strategies._loader') as mock_loader:
            mock_loader.load_all.return_value = {
                "Mock Strategy 1": MockStrategy1
            }

            response = client.get("/api/v1/strategies/Mock Strategy 1")
            data = response.json()

            assert data["name"] == "Mock Strategy 1"
            assert data["version"] == "1.0.0"
            assert data["description"] == "First mock strategy for testing"

    def test_get_strategy_includes_parameters(self, client):
        """Response includes strategy parameter definitions"""
        with patch('backend.api.strategies._loader') as mock_loader:
            mock_loader.load_all.return_value = {
                "Mock Strategy 1": MockStrategy1
            }

            response = client.get("/api/v1/strategies/Mock Strategy 1")
            data = response.json()

            assert "parameters" in data
            assert "period" in data["parameters"]
            assert data["parameters"]["period"]["type"] == "int"
            assert data["parameters"]["period"]["default"] == 10
            assert data["parameters"]["period"]["min"] == 5
            assert data["parameters"]["period"]["max"] == 50

    def test_get_strategy_not_found_returns_404(self, client):
        """GET /api/v1/strategies/{name} returns 404 for non-existent strategy"""
        with patch('backend.api.strategies._loader') as mock_loader:
            mock_loader.load_all.return_value = {}

            response = client.get("/api/v1/strategies/Nonexistent Strategy")

            assert response.status_code == 404

    def test_get_strategy_not_found_error_message(self, client):
        """404 response includes descriptive error message"""
        with patch('backend.api.strategies._loader') as mock_loader:
            mock_loader.load_all.return_value = {}

            response = client.get("/api/v1/strategies/Nonexistent Strategy")
            data = response.json()

            assert "detail" in data
            assert "Nonexistent Strategy" in data["detail"]

    def test_get_strategy_with_special_characters(self, client):
        """Test strategy name with special characters"""
        class SpecialStrategy(StrategyBase):
            strategy_name = "Strategy with-Special_Characters.123"
            strategy_version = "1.0"
            strategy_description = "Test"

            def next(self):
                pass

            @staticmethod
            def get_parameters():
                return {}

        with patch('backend.api.strategies._loader') as mock_loader:
            mock_loader.load_all.return_value = {
                "Strategy with-Special_Characters.123": SpecialStrategy
            }

            response = client.get(
                "/api/v1/strategies/Strategy with-Special_Characters.123"
            )
            assert response.status_code == 200
            data = response.json()
            assert data["name"] == "Strategy with-Special_Characters.123"


class TestErrorHandling:
    """Test error handling"""

    @pytest.fixture
    def client(self):
        """Create test client"""
        from backend.main import app
        return TestClient(app)

    def test_strategy_with_missing_metadata(self, client):
        """Test strategy with incomplete metadata"""
        class IncompleteStrategy(StrategyBase):
            # Missing strategy_name, uses default
            strategy_version = "1.0"
            strategy_description = "Incomplete"

            def next(self):
                pass

            @staticmethod
            def get_parameters():
                return {}

        with patch('backend.api.strategies._loader') as mock_loader:
            mock_loader.load_all.return_value = {
                "Base Strategy": IncompleteStrategy
            }

            response = client.get("/api/v1/strategies/Base Strategy")
            assert response.status_code == 200
            data = response.json()
            assert "name" in data

    def test_strategy_with_empty_parameters(self, client):
        """Test strategy with no parameters"""
        class NoParamStrategy(StrategyBase):
            strategy_name = "No Parameters"
            strategy_version = "1.0"
            strategy_description = "No parameters"

            def next(self):
                pass

            @staticmethod
            def get_parameters():
                return {}

        with patch('backend.api.strategies._loader') as mock_loader:
            mock_loader.load_all.return_value = {
                "No Parameters": NoParamStrategy
            }

            response = client.get("/api/v1/strategies/No Parameters")
            data = response.json()

            assert response.status_code == 200
            assert data["parameters"] == {}
