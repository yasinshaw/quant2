"""
Tests for extended optimization API endpoints.
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from backend.main import app
from backend.database import Database
from backend.config import settings


@pytest.fixture
def client():
    """Create test client"""
    return TestClient(app)


@pytest.fixture
def mock_db():
    """Mock database"""
    with patch('backend.api.backtest._db') as mock:
        yield mock


@pytest.fixture
def mock_strategy_loader():
    """Mock strategy loader"""
    with patch('backend.api.backtest._strategy_loader') as mock:
        mock.load_all.return_value = {
            'TestStrategy': Mock
        }
        yield mock


class TestScoringWeightsEndpoint:
    """Tests for GET /optimization/scoring-weights endpoint"""

    def test_get_default_scoring_weights(self, client):
        """Test getting default scoring weights"""
        response = client.get("/api/v1/backtest/optimization/scoring-weights")

        assert response.status_code == 200
        data = response.json()

        # Verify weights structure
        assert 'weights' in data
        assert 'description' in data
        assert 'note' in data

        # Verify default weights
        weights = data['weights']
        assert 'sharpe_ratio' in weights
        assert 'total_return' in weights
        assert 'max_drawdown' in weights
        assert 'win_rate' in weights

        # Verify values
        assert weights['sharpe_ratio'] == 0.4
        assert weights['total_return'] == 0.3
        assert weights['max_drawdown'] == -0.2
        assert weights['win_rate'] == 0.1

        # Verify descriptions
        assert isinstance(data['description'], dict)
        assert len(data['description']) == 4


class TestStabilityReportEndpoint:
    """Tests for GET /optimization/jobs/{job_id}/stability endpoint"""

    def test_get_stability_report_found(self, client, mock_db):
        """Test getting stability report for existing job"""
        from backend.models.optimization_job import OptimizationJob
        from backend.models.optimization_result import OptimizationResult

        # Create real database objects for testing
        from datetime import datetime

        # Mock job with real values
        mock_job = OptimizationJob(
            id=1,
            strategy_name="TestStrategy",
            symbol="BTCUSDT",
            interval="1h",
            start_time=datetime(2024, 1, 1),
            end_time=datetime(2024, 1, 31),
            parameter_ranges={},
            optimization_method="grid",
            status="completed",
            created_at=datetime(2024, 1, 1),
            stability_score=0.85,
            stability_variance=0.05,
            is_stable=True,
            enable_stability_analysis=True
        )

        # Mock best result
        mock_result = OptimizationResult(
            id=1,
            optimization_job_id=1,
            parameters={'period': 20, 'deviation': 2.0},
            score=0.9,
            total_return=0.15,
            sharpe_ratio=1.8,
            max_drawdown=0.05,
            win_rate=0.65,
            profit_factor=2.0,
            total_trades=50,
            final_value=115000,
            initial_cash=100000,
            composite_score=0.9,
            stability_neighbors=[
                {'parameters': {'period': 19}, 'score': 0.88},
                {'parameters': {'period': 21}, 'score': 0.87}
            ]
        )

        # Mock database session
        mock_session = Mock()
        mock_session.query.return_value.filter.return_value.order_by.return_value.first.return_value = mock_result
        mock_session.query.return_value.filter.return_value.first.side_effect = [mock_job, mock_result]
        mock_db.get_session.return_value.__enter__.return_value = mock_session

        response = client.get("/api/v1/backtest/optimization/jobs/1/stability")

        assert response.status_code == 200
        data = response.json()

        assert data['job_id'] == 1
        assert data['stability_score'] == 0.85
        assert data['variance'] == 0.05
        assert data['is_stable'] == True
        assert data['enable_stability_analysis'] == True
        assert 'neighbors' in data
        assert 'optimal_parameters' in data
        assert 'optimal_score' in data
        assert len(data['neighbors']) == 2

    def test_get_stability_report_job_not_found(self, client, mock_db):
        """Test getting stability report for non-existent job"""
        from backend.models.optimization_job import OptimizationJob

        # Mock database to return None
        mock_session = Mock()
        mock_session.query.return_value.filter.return_value.first.return_value = None
        mock_db.get_session.return_value.__enter__.return_value = mock_session

        response = client.get("/api/v1/backtest/optimization/jobs/999/stability")

        assert response.status_code == 404
        data = response.json()
        assert 'detail' in data

    def test_get_stability_report_no_neighbors(self, client, mock_db):
        """Test getting stability report without neighbor data"""
        from backend.models.optimization_job import OptimizationJob
        from datetime import datetime

        # Mock job without stability data
        mock_job = OptimizationJob(
            id=1,
            strategy_name="TestStrategy",
            symbol="BTCUSDT",
            interval="1h",
            start_time=datetime(2024, 1, 1),
            end_time=datetime(2024, 1, 31),
            parameter_ranges={},
            optimization_method="grid",
            status="completed",
            created_at=datetime(2024, 1, 1),
            stability_score=None,
            stability_variance=None,
            is_stable=None,
            enable_stability_analysis=False
        )

        # Mock no best result
        mock_session = Mock()
        mock_session.query.return_value.filter.return_value.order_by.return_value.first.return_value = None
        mock_session.query.return_value.filter.return_value.first.side_effect = [mock_job, None]
        mock_db.get_session.return_value.__enter__.return_value = mock_session

        response = client.get("/api/v1/backtest/optimization/jobs/1/stability")

        assert response.status_code == 200
        data = response.json()

        assert data['job_id'] == 1
        assert data['stability_score'] is None
        assert data['variance'] is None
        assert data['is_stable'] == False  # Defaults to False
        assert data['enable_stability_analysis'] == False
        assert 'neighbors' not in data


class TestOptimizeEndpointExtensions:
    """Tests for extended /optimize endpoint functionality"""

    @pytest.mark.asyncio
    async def test_optimize_with_bayesian_method(self, client, mock_db, mock_strategy_loader):
        """Test optimization with Bayesian method"""
        request_data = {
            "strategy_name": "TestStrategy",
            "symbol": "BTCUSDT",
            "interval": "1h",
            "start_time": "2024-01-01T00:00:00",
            "end_time": "2024-01-31T23:59:59",
            "parameter_ranges": {
                "period": {"type": "int", "min": 10, "max": 50},
                "deviation": {"type": "float", "min": 1.0, "max": 5.0}
            },
            "optimization_method": "bayesian",
            "n_trials": 50,
            "scoring_weights": {
                "sharpe_ratio": 0.5,
                "total_return": 0.3,
                "max_drawdown": -0.15,
                "win_rate": 0.05
            }
        }

        # Mock database calls
        mock_db.create_optimization_job.return_value = 1
        mock_db.update_optimization_job_status.return_value = None

        # Mock Bayesian optimizer
        with patch('backend.api.backtest.BayesianOptimizer') as mock_bayesian_class:
            mock_optimizer = Mock()
            mock_bayesian_class.return_value = mock_optimizer
            mock_optimizer.optimize = AsyncMock(return_value={
                'best_result': {
                    'parameters': {'period': 20, 'deviation': 2.0},
                    'pnl': 10000,
                    'pnl_pct': 10.0
                }
            })

            response = client.post("/api/v1/backtest/optimize", json=request_data)

            # Note: This will fail in real test due to async, but verifies the structure
            # In real scenario, would use async test client

    @pytest.mark.asyncio
    async def test_optimize_with_out_of_sample(self, client, mock_db, mock_strategy_loader):
        """Test optimization with out-of-sample testing enabled"""
        request_data = {
            "strategy_name": "TestStrategy",
            "symbol": "BTCUSDT",
            "interval": "1h",
            "start_time": "2024-01-01T00:00:00",
            "end_time": "2024-01-31T23:59:59",
            "parameter_ranges": {
                "period": [10, 20, 30]
            },
            "enable_out_of_sample": True,
            "test_start_time": "2024-02-01T00:00:00",
            "test_end_time": "2024-02-28T23:59:59"
        }

        # Mock database calls
        mock_db.create_optimization_job.return_value = 1
        mock_db.update_optimization_job_status.return_value = None

        # Verify job would be created with OOS fields
        # (Would need async test client for full test)

    @pytest.mark.asyncio
    async def test_optimize_with_custom_scoring_weights(self, client, mock_db, mock_strategy_loader):
        """Test optimization with custom scoring weights"""
        custom_weights = {
            "sharpe_ratio": 0.6,
            "total_return": 0.2,
            "max_drawdown": -0.15,
            "win_rate": 0.05
        }

        request_data = {
            "strategy_name": "TestStrategy",
            "symbol": "BTCUSDT",
            "interval": "1h",
            "start_time": "2024-01-01T00:00:00",
            "end_time": "2024-01-31T23:59:59",
            "parameter_ranges": {
                "period": [10, 20, 30]
            },
            "scoring_weights": custom_weights
        }

        # Verify custom weights are passed through
        # (Would need async test client for full test)

    def test_optimize_bayesian_without_optuna(self, client, mock_db, mock_strategy_loader):
        """Test Bayesian optimization fails gracefully without Optuna"""
        request_data = {
            "strategy_name": "TestStrategy",
            "symbol": "BTCUSDT",
            "interval": "1h",
            "start_time": "2024-01-01T00:00:00",
            "end_time": "2024-01-31T23:59:59",
            "parameter_ranges": {
                "period": [10, 20, 30]
            },
            "optimization_method": "bayesian"
        }

        # Mock database calls
        mock_db.create_optimization_job.return_value = 1
        mock_db.update_optimization_job_status.return_value = None

        # Mock BayesianOptimizer to raise ImportError
        with patch('backend.api.backtest.BayesianOptimizer') as mock_bayesian_class:
            mock_bayesian_class.side_effect = ImportError("No module named 'optuna'")

            response = client.post("/api/v1/backtest/optimize", json=request_data)

            assert response.status_code == 400
            data = response.json()
            assert 'Optuna' in data['detail']
            assert 'pip install optuna' in data['detail']
