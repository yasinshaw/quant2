"""
Tests for Backtest API

Tests verify:
1. Run single backtest successfully
2. Run parameter optimization
3. List backtest jobs
4. Get job status and results
5. Get detailed backtest report
6. Error handling (invalid strategy, missing parameters, etc.)
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime
from typing import Dict, Any

from backend.core.strategy_base import StrategyBase
from backend.models.backtest_job import BacktestJob
from backend.models.backtest_result import BacktestResult
from backend.models.optimization_job import OptimizationJob
from backend.models.optimization_result import OptimizationResult


class MockStrategy(StrategyBase):
    """Mock strategy for testing"""

    strategy_name = "Mock Strategy"
    strategy_version = "1.0.0"
    strategy_description = "Mock strategy for testing"

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


class TestRunBacktest:
    """Test POST /api/v1/backtest/run endpoint"""

    @pytest.fixture
    def client(self):
        """Create test client"""
        from backend.main import app
        return TestClient(app)

    def test_run_backtest_returns_200(self, client):
        """POST /api/v1/backtest/run returns 200 for valid request"""
        with patch('backend.api.backtest._strategy_loader') as mock_loader, \
             patch('backend.api.backtest._engine') as mock_engine, \
             patch('backend.api.backtest._db') as mock_db:
            mock_loader.load_all.return_value = {"Mock Strategy": MockStrategy}
            mock_engine.run = AsyncMock(return_value={
                'final_value': 105000.0,
                'pnl': 5000.0,
                'pnl_pct': 5.0,
                'trades': []
            })
            # Mock database methods
            mock_db.create_backtest_job.return_value = 1
            mock_db.update_backtest_job_status.return_value = None

            response = client.post("/api/v1/backtest/run", json={
                "strategy_name": "Mock Strategy",
                "symbol": "BTCUSDT",
                "interval": "1h",
                "start_time": "2024-01-01T00:00:00",
                "end_time": "2024-01-31T23:59:59",
                "parameters": {"period": 20},
                "initial_cash": 100000.0
            })

            assert response.status_code == 200

    def test_run_backtest_returns_correct_data(self, client):
        """Response includes backtest results"""
        with patch('backend.api.backtest._strategy_loader') as mock_loader, \
             patch('backend.api.backtest._engine') as mock_engine:
            mock_loader.load_all.return_value = {"Mock Strategy": MockStrategy}
            mock_engine.run = AsyncMock(return_value={
                'final_value': 105000.0,
                'pnl': 5000.0,
                'pnl_pct': 5.0,
                'trades': []
            })

            response = client.post("/api/v1/backtest/run", json={
                "strategy_name": "Mock Strategy",
                "symbol": "BTCUSDT",
                "interval": "1h",
                "start_time": "2024-01-01T00:00:00",
                "end_time": "2024-01-31T23:59:59",
                "parameters": {"period": 20},
                "initial_cash": 100000.0
            })

            data = response.json()
            assert data['final_value'] == 105000.0
            assert data['pnl'] == 5000.0
            assert data['pnl_pct'] == 5.0
            assert 'trades' in data

    def test_run_backtest_invalid_strategy_returns_404(self, client):
        """POST /api/v1/backtest/run returns 404 for non-existent strategy"""
        with patch('backend.api.backtest._strategy_loader') as mock_loader:
            mock_loader.load_all.return_value = {}

            response = client.post("/api/v1/backtest/run", json={
                "strategy_name": "Nonexistent Strategy",
                "symbol": "BTCUSDT",
                "interval": "1h",
                "start_time": "2024-01-01T00:00:00",
                "end_time": "2024-01-31T23:59:59"
            })

            assert response.status_code == 404
            assert "not found" in response.json()['detail'].lower()

    def test_run_backtest_missing_required_field_returns_400(self, client):
        """POST /api/v1/backtest/run returns 400 for missing required fields"""
        response = client.post("/api/v1/backtest/run", json={
            "strategy_name": "Mock Strategy"
            # Missing symbol, interval, start_time, end_time
        })

        assert response.status_code == 400

    def test_run_backtest_invalid_datetime_format_returns_400(self, client):
        """POST /api/v1/backtest/run returns 400 for invalid datetime"""
        with patch('backend.api.backtest._strategy_loader') as mock_loader:
            mock_loader.load_all.return_value = {"Mock Strategy": MockStrategy}

            response = client.post("/api/v1/backtest/run", json={
                "strategy_name": "Mock Strategy",
                "symbol": "BTCUSDT",
                "interval": "1h",
                "start_time": "invalid-datetime",
                "end_time": "2024-01-31T23:59:59"
            })

            assert response.status_code == 400
            assert "datetime" in response.json()['detail'].lower()

    def test_run_backtest_engine_error_returns_500(self, client):
        """POST /api/v1/backtest/run returns 500 when engine fails"""
        with patch('backend.api.backtest._strategy_loader') as mock_loader, \
             patch('backend.api.backtest._engine') as mock_engine:
            mock_loader.load_all.return_value = {"Mock Strategy": MockStrategy}
            mock_engine.run = AsyncMock(side_effect=ValueError("No data found"))

            response = client.post("/api/v1/backtest/run", json={
                "strategy_name": "Mock Strategy",
                "symbol": "BTCUSDT",
                "interval": "1h",
                "start_time": "2024-01-01T00:00:00",
                "end_time": "2024-01-31T23:59:59"
            })

            assert response.status_code == 500


class TestOptimizeParameters:
    """Test POST /api/v1/backtest/optimize endpoint"""

    @pytest.fixture
    def client(self):
        """Create test client"""
        from backend.main import app
        return TestClient(app)

    def test_optimize_returns_200(self, client):
        """POST /api/v1/backtest/optimize returns 200"""
        with patch('backend.api.backtest._strategy_loader') as mock_loader, \
             patch('backend.api.backtest._optimizer') as mock_optimizer:
            mock_loader.load_all.return_value = {"Mock Strategy": MockStrategy}
            mock_optimizer.optimize = AsyncMock(return_value={
                'parameters': {'period': 20},
                'backtest_result': {
                    'final_value': 110000.0,
                    'pnl': 10000.0,
                    'pnl_pct': 10.0,
                    'trades': []
                },
                'optimization_result': MagicMock(parameters={'period': 20}, score=10.0)
            })

            response = client.post("/api/v1/backtest/optimize", json={
                "strategy_name": "Mock Strategy",
                "symbol": "BTCUSDT",
                "interval": "1h",
                "start_time": "2024-01-01T00:00:00",
                "end_time": "2024-01-31T23:59:59",
                "parameter_ranges": {"period": [10, 20, 30]}
            })

            assert response.status_code == 200

    def test_optimize_returns_best_parameters(self, client):
        """Response includes best parameters and results"""
        with patch('backend.api.backtest._strategy_loader') as mock_loader, \
             patch('backend.api.backtest._optimizer') as mock_optimizer:
            mock_loader.load_all.return_value = {"Mock Strategy": MockStrategy}
            mock_optimizer.optimize = AsyncMock(return_value={
                'parameters': {'period': 20},
                'backtest_result': {
                    'final_value': 110000.0,
                    'pnl': 10000.0,
                    'pnl_pct': 10.0,
                    'trades': []
                },
                'optimization_result': MagicMock(parameters={'period': 20}, score=10.0)
            })

            response = client.post("/api/v1/backtest/optimize", json={
                "strategy_name": "Mock Strategy",
                "symbol": "BTCUSDT",
                "interval": "1h",
                "start_time": "2024-01-01T00:00:00",
                "end_time": "2024-01-31T23:59:59",
                "parameter_ranges": {"period": [10, 20, 30]}
            })

            data = response.json()
            assert 'parameters' in data
            assert data['parameters'] == {'period': 20}
            assert 'backtest_result' in data

    def test_optimize_invalid_strategy_returns_404(self, client):
        """POST /api/v1/backtest/optimize returns 404 for non-existent strategy"""
        with patch('backend.api.backtest._strategy_loader') as mock_loader:
            mock_loader.load_all.return_value = {}

            response = client.post("/api/v1/backtest/optimize", json={
                "strategy_name": "Nonexistent Strategy",
                "symbol": "BTCUSDT",
                "interval": "1h",
                "start_time": "2024-01-01T00:00:00",
                "end_time": "2024-01-31T23:59:59",
                "parameter_ranges": {"period": [10, 20]}
            })

            assert response.status_code == 404

    def test_optimize_endpoint_accepts_fixed_parameters(self, client):
        """Test that /api/v1/backtest/optimize accepts fixed_parameters field"""
        with patch('backend.api.backtest._strategy_loader') as mock_loader, \
             patch('backend.api.backtest._optimizer') as mock_optimizer:
            mock_loader.load_all.return_value = {"Mock Strategy": MockStrategy}
            mock_optimizer.optimize = AsyncMock(return_value={
                'job_id': 1,
                'total_combinations': 2,
                'results': [],
                'best_result': {
                    'id': 1,
                    'job_id': 1,
                    'parameters': {'period': 10},
                    'pnl': 1000,
                    'pnl_pct': 0.01,
                    'total_trades': 5,
                    'sharpe_ratio': 1.5,
                    'max_drawdown': 0.02,
                    'win_rate': 0.6,
                    'is_best': True
                }
            })

            response = client.post("/api/v1/backtest/optimize", json={
                "strategy_name": "Mock Strategy",
                "symbol": "BTCUSDT",
                "interval": "1h",
                "start_time": "2024-01-01T00:00:00",
                "end_time": "2024-01-31T23:59:59",
                "parameter_ranges": {
                    "period": [10, 20]
                },
                "fixed_parameters": {
                    "threshold": 0.5
                }
            })

            assert response.status_code == 200

            # Verify optimizer was called with fixed_parameters
            mock_optimizer.optimize.assert_called_once()
            call_kwargs = mock_optimizer.optimize.call_args[1]
            assert 'fixed_parameters' in call_kwargs
            assert call_kwargs['fixed_parameters']['threshold'] == 0.5

    def test_optimize_endpoint_backward_compatible(self, client):
        """Test that API calls without fixed_parameters still work"""
        with patch('backend.api.backtest._strategy_loader') as mock_loader, \
             patch('backend.api.backtest._optimizer') as mock_optimizer:
            mock_loader.load_all.return_value = {"Mock Strategy": MockStrategy}
            mock_optimizer.optimize = AsyncMock(return_value={
                'job_id': 1,
                'total_combinations': 1,
                'results': [],
                'best_result': {
                    'id': 1,
                    'job_id': 1,
                    'parameters': {'period': 10},
                    'pnl': 1000,
                    'pnl_pct': 0.01,
                    'total_trades': 5,
                    'sharpe_ratio': 1.5,
                    'max_drawdown': 0.02,
                    'win_rate': 0.6,
                    'is_best': True
                }
            })

            # Request WITHOUT fixed_parameters (old format)
            response = client.post("/api/v1/backtest/optimize", json={
                "strategy_name": "Mock Strategy",
                "symbol": "BTCUSDT",
                "interval": "1h",
                "start_time": "2024-01-01T00:00:00",
                "end_time": "2024-01-31T23:59:59",
                "parameter_ranges": {"period": [10, 20]}
            })

            assert response.status_code == 200
            mock_optimizer.optimize.assert_called_once()
            call_kwargs = mock_optimizer.optimize.call_args[1]
            assert call_kwargs['fixed_parameters'] == {}  # Should default to empty dict


class TestListJobs:
    """Test GET /api/v1/backtest/jobs endpoint"""

    @pytest.fixture
    def client(self):
        """Create test client"""
        from backend.main import app
        return TestClient(app)

    def test_list_jobs_returns_200(self, client):
        """GET /api/v1/backtest/jobs returns 200"""
        with patch('backend.api.backtest._db') as mock_db:
            mock_db.get_backtest_jobs_by_status.return_value = []

            response = client.get("/api/v1/backtest/jobs")

            assert response.status_code == 200

    def test_list_jobs_returns_jobs_list(self, client):
        """Response includes jobs list"""
        with patch('backend.api.backtest._db') as mock_db:
            mock_job = MagicMock()
            mock_job.id = 1
            mock_job.strategy_name = "Mock Strategy"
            mock_job.symbol = "BTCUSDT"
            mock_job.status = "completed"
            mock_job.created_at = datetime(2024, 1, 1, 12, 0, 0)
            mock_db.get_backtest_jobs_by_status.return_value = [mock_job]

            response = client.get("/api/v1/backtest/jobs")
            data = response.json()

            assert 'jobs' in data
            assert len(data['jobs']) == 1
            assert data['jobs'][0]['id'] == 1

    def test_list_jobs_filter_by_status(self, client):
        """Filter jobs by status query parameter"""
        with patch('backend.api.backtest._db') as mock_db:
            mock_db.get_backtest_jobs_by_status.return_value = []

            response = client.get("/api/v1/backtest/jobs?status=completed")

            mock_db.get_backtest_jobs_by_status.assert_called_once_with(status='completed')
            assert response.status_code == 200

    def test_list_jobs_empty_list(self, client):
        """Return empty list when no jobs exist"""
        with patch('backend.api.backtest._db') as mock_db:
            mock_db.get_backtest_jobs_by_status.return_value = []

            response = client.get("/api/v1/backtest/jobs")
            data = response.json()

            assert data['jobs'] == []


class TestGetJob:
    """Test GET /api/v1/backtest/jobs/{job_id} endpoint"""

    @pytest.fixture
    def client(self):
        """Create test client"""
        from backend.main import app
        return TestClient(app)

    def test_get_job_returns_200(self, client):
        """GET /api/v1/backtest/jobs/{job_id} returns 200 for existing job"""
        with patch('backend.api.backtest._db') as mock_db:
            mock_job = MagicMock()
            mock_job.id = 1
            mock_job.strategy_name = "Mock Strategy"
            mock_job.symbol = "BTCUSDT"
            mock_job.status = "completed"
            mock_job.created_at = datetime(2024, 1, 1, 12, 0, 0)
            mock_db.get_backtest_job.return_value = mock_job

            response = client.get("/api/v1/backtest/jobs/1")

            assert response.status_code == 200

    def test_get_job_returns_correct_data(self, client):
        """Response includes job details"""
        with patch('backend.api.backtest._db') as mock_db:
            mock_job = MagicMock()
            mock_job.id = 1
            mock_job.strategy_name = "Mock Strategy"
            mock_job.symbol = "BTCUSDT"
            mock_job.status = "completed"
            mock_job.created_at = datetime(2024, 1, 1, 12, 0, 0)
            mock_db.get_backtest_job.return_value = mock_job

            response = client.get("/api/v1/backtest/jobs/1")
            data = response.json()

            assert 'job' in data
            assert data['job']['id'] == 1
            assert data['job']['strategy_name'] == "Mock Strategy"

    def test_get_job_not_found_returns_404(self, client):
        """GET /api/v1/backtest/jobs/{job_id} returns 404 for non-existent job"""
        with patch('backend.api.backtest._db') as mock_db:
            mock_db.get_backtest_job.return_value = None

            response = client.get("/api/v1/backtest/jobs/999")

            assert response.status_code == 404
            assert "not found" in response.json()['detail'].lower()

    def test_get_job_includes_result_when_completed(self, client):
        """Response includes result when job is completed"""
        with patch('backend.api.backtest._db') as mock_db:
            mock_job = MagicMock()
            mock_job.id = 1
            mock_job.strategy_name = "Mock Strategy"
            mock_job.symbol = "BTCUSDT"
            mock_job.status = "completed"
            mock_job.created_at = datetime(2024, 1, 1, 12, 0, 0)

            mock_result = MagicMock()
            mock_result.total_return = 5.0
            mock_result.final_value = 105000.0

            mock_db.get_backtest_job.return_value = mock_job
            mock_db.get_backtest_result_by_job_id.return_value = mock_result

            response = client.get("/api/v1/backtest/jobs/1")
            data = response.json()

            assert 'result' in data
            assert data['result']['total_return'] == 5.0


class TestGetReport:
    """Test GET /api/v1/backtest/results/{result_id}/report endpoint"""

    @pytest.fixture
    def client(self):
        """Create test client"""
        from backend.main import app
        return TestClient(app)

    def test_get_report_returns_200(self, client):
        """GET /api/v1/backtest/results/{result_id}/report returns 200"""
        with patch('backend.api.backtest._db') as mock_db, \
             patch('backend.api.backtest._report_generator') as mock_report_gen:
            mock_result = MagicMock()
            mock_result.id = 1
            mock_result.initial_cash = 100000.0
            mock_db.get_backtest_result.return_value = mock_result
            mock_db.get_trades.return_value = []
            mock_report_gen.generate_report.return_value = {
                'summary': {},
                'monthly_returns': {},
                'trade_analysis': {},
                'equity_curve': []
            }

            response = client.get("/api/v1/backtest/results/1/report")

            assert response.status_code == 200

    def test_get_report_returns_full_report(self, client):
        """Response includes summary, monthly returns, trade analysis, and equity curve"""
        with patch('backend.api.backtest._db') as mock_db, \
             patch('backend.api.backtest._report_generator') as mock_report_gen:
            mock_result = MagicMock()
            mock_result.id = 1
            mock_result.initial_cash = 100000.0
            mock_db.get_backtest_result.return_value = mock_result
            mock_db.get_trades.return_value = []

            mock_report = {
                'summary': {
                    'total_return': 5.0,
                    'sharpe_ratio': 1.5,
                    'max_drawdown': -2.0
                },
                'monthly_returns': {'2024-01': 5.0},
                'trade_analysis': {'trades': [], 'statistics': {}},
                'equity_curve': []
            }
            mock_report_gen.generate_report.return_value = mock_report

            response = client.get("/api/v1/backtest/results/1/report")
            data = response.json()

            assert 'summary' in data
            assert 'monthly_returns' in data
            assert 'trade_analysis' in data
            assert 'equity_curve' in data

    def test_get_report_result_not_found_returns_404(self, client):
        """GET /api/v1/backtest/results/{result_id}/report returns 404 for non-existent result"""
        with patch('backend.api.backtest._db') as mock_db:
            mock_db.get_backtest_result.return_value = None

            response = client.get("/api/v1/backtest/results/999/report")

            assert response.status_code == 404
            assert "not found" in response.json()['detail'].lower()


class TestErrorHandling:
    """Test error handling"""

    @pytest.fixture
    def client(self):
        """Create test client"""
        from backend.main import app
        return TestClient(app)

    def test_database_error_returns_500(self, client):
        """Database errors return 500 status"""
        with patch('backend.api.backtest._db') as mock_db:
            mock_db.get_backtest_job.side_effect = Exception("Database error")

            response = client.get("/api/v1/backtest/jobs/1")

            assert response.status_code == 500

    def test_invalid_json_returns_400(self, client):
        """Invalid JSON returns 400 status"""
        response = client.post(
            "/api/v1/backtest/run",
            content="invalid json",
            headers={"Content-Type": "application/json"}
        )

        assert response.status_code == 400

    def test_missing_content_type_returns_422(self, client):
        """Missing content type returns 422 status"""
        response = client.post(
            "/api/v1/backtest/run",
            content='{"strategy_name": "test"}'
        )

        assert response.status_code == 422


class TestGetBacktestHistory:
    """Test GET /api/v1/backtest/history endpoint"""

    @pytest.fixture
    def client(self):
        """Create test client"""
        from backend.main import app
        return TestClient(app)

    def test_get_backtest_history_returns_200(self, client):
        """GET /api/v1/backtest/history returns 200"""
        with patch('backend.api.backtest._db') as mock_db:
            mock_db.get_backtest_history.return_value = {
                'total': 0,
                'page': 1,
                'page_size': 20,
                'total_pages': 0,
                'items': []
            }

            response = client.get("/api/v1/backtest/history")

            assert response.status_code == 200

    def test_get_backtest_history_returns_correct_format(self, client):
        """Response includes pagination metadata and items list"""
        with patch('backend.api.backtest._db') as mock_db:
            mock_db.get_backtest_history.return_value = {
                'total': 1,
                'page': 1,
                'page_size': 20,
                'total_pages': 1,
                'items': [
                    {
                        'id': 1,
                        'strategy_name': 'Test Strategy',
                        'symbol': 'BTCUSDT',
                        'interval': '1h',
                        'start_time': datetime(2024, 1, 1, 0, 0, 0),
                        'end_time': datetime(2024, 1, 31, 23, 59, 59),
                        'status': 'completed',
                        'total_return': 5.0,
                        'sharpe_ratio': 1.5,
                        'max_drawdown': -2.0,
                        'total_trades': 10,
                        'created_at': datetime(2024, 1, 1, 12, 0, 0),
                        'completed_at': datetime(2024, 1, 1, 12, 5, 0)
                    }
                ]
            }

            response = client.get("/api/v1/backtest/history")
            data = response.json()

            assert 'total' in data
            assert 'page' in data
            assert 'page_size' in data
            assert 'total_pages' in data
            assert 'items' in data
            assert data['total'] == 1
            assert data['page'] == 1
            assert len(data['items']) == 1

    def test_get_backtest_history_filter_by_strategy(self, client):
        """Filter by strategy_name query parameter"""
        with patch('backend.api.backtest._db') as mock_db:
            mock_db.get_backtest_history.return_value = {
                'total': 0,
                'page': 1,
                'page_size': 20,
                'total_pages': 0,
                'items': []
            }

            response = client.get("/api/v1/backtest/history?strategy_name=Test Strategy")

            mock_db.get_backtest_history.assert_called_once()
            call_kwargs = mock_db.get_backtest_history.call_args[1]
            assert call_kwargs['strategy_name'] == 'Test Strategy'
            assert response.status_code == 200

    def test_get_backtest_history_filter_by_symbol(self, client):
        """Filter by symbol query parameter"""
        with patch('backend.api.backtest._db') as mock_db:
            mock_db.get_backtest_history.return_value = {
                'total': 0,
                'page': 1,
                'page_size': 20,
                'total_pages': 0,
                'items': []
            }

            response = client.get("/api/v1/backtest/history?symbol=BTCUSDT")

            mock_db.get_backtest_history.assert_called_once()
            call_kwargs = mock_db.get_backtest_history.call_args[1]
            assert call_kwargs['symbol'] == 'BTCUSDT'
            assert response.status_code == 200

    def test_get_backtest_history_filter_by_status(self, client):
        """Filter by status query parameter"""
        with patch('backend.api.backtest._db') as mock_db:
            mock_db.get_backtest_history.return_value = {
                'total': 0,
                'page': 1,
                'page_size': 20,
                'total_pages': 0,
                'items': []
            }

            response = client.get("/api/v1/backtest/history?status=completed")

            mock_db.get_backtest_history.assert_called_once()
            call_kwargs = mock_db.get_backtest_history.call_args[1]
            assert call_kwargs['status'] == 'completed'
            assert response.status_code == 200

    def test_get_backtest_history_pagination(self, client):
        """Pagination parameters work correctly"""
        with patch('backend.api.backtest._db') as mock_db:
            mock_db.get_backtest_history.return_value = {
                'total': 50,
                'page': 2,
                'page_size': 10,
                'total_pages': 5,
                'items': []
            }

            response = client.get("/api/v1/backtest/history?page=2&page_size=10")

            mock_db.get_backtest_history.assert_called_once()
            call_kwargs = mock_db.get_backtest_history.call_args[1]
            assert call_kwargs['page'] == 2
            assert call_kwargs['page_size'] == 10
            assert response.status_code == 200

    def test_get_backtest_history_sorting(self, client):
        """Sorting parameters work correctly"""
        with patch('backend.api.backtest._db') as mock_db:
            mock_db.get_backtest_history.return_value = {
                'total': 0,
                'page': 1,
                'page_size': 20,
                'total_pages': 0,
                'items': []
            }

            response = client.get("/api/v1/backtest/history?sort_by=total_return&sort_order=asc")

            mock_db.get_backtest_history.assert_called_once()
            call_kwargs = mock_db.get_backtest_history.call_args[1]
            assert call_kwargs['sort_by'] == 'total_return'
            assert call_kwargs['sort_order'] == 'asc'
            assert response.status_code == 200

    def test_get_backtest_history_invalid_page_returns_400(self, client):
        """Invalid page number returns 400"""
        response = client.get("/api/v1/backtest/history?page=0")

        assert response.status_code == 400

    def test_get_backtest_history_invalid_page_size_returns_400(self, client):
        """Invalid page_size returns 400"""
        response = client.get("/api/v1/backtest/history?page_size=0")

        assert response.status_code == 400

        response = client.get("/api/v1/backtest/history?page_size=101")

        assert response.status_code == 400

    def test_get_backtest_history_database_error_returns_500(self, client):
        """Database errors return 500 status"""
        with patch('backend.api.backtest._db') as mock_db:
            mock_db.get_backtest_history.side_effect = Exception("Database error")

            response = client.get("/api/v1/backtest/history")

            assert response.status_code == 500


class TestDeleteBacktestJob:
    """Test DELETE /api/v1/backtest/jobs/{job_id} endpoint"""

    @pytest.fixture
    def client(self):
        """Create test client"""
        from backend.main import app
        return TestClient(app)

    def test_delete_backtest_job_returns_200(self, client):
        """DELETE /api/v1/backtest/jobs/{job_id} returns 200 on success"""
        with patch('backend.api.backtest._db') as mock_db:
            mock_db.delete_backtest_job.return_value = True

            response = client.delete("/api/v1/backtest/jobs/1")

            assert response.status_code == 200
            data = response.json()
            assert data['success'] is True
            assert 'deleted successfully' in data['message']

    def test_delete_running_job_returns_400(self, client):
        """DELETE returns 400 when trying to delete running job"""
        with patch('backend.api.backtest._db') as mock_db:
            mock_db.delete_backtest_job.side_effect = ValueError("Cannot delete running backtest job 1")

            response = client.delete("/api/v1/backtest/jobs/1")

            assert response.status_code == 400
            assert "running" in response.json()['detail'].lower()

    def test_delete_nonexistent_job_returns_404(self, client):
        """DELETE returns 404 when job not found"""
        with patch('backend.api.backtest._db') as mock_db:
            mock_db.delete_backtest_job.side_effect = ValueError("Backtest job 999 not found")

            response = client.delete("/api/v1/backtest/jobs/999")

            assert response.status_code == 404
            assert "not found" in response.json()['detail'].lower()

    def test_delete_backtest_job_database_error_returns_500(self, client):
        """Database errors return 500 status"""
        with patch('backend.api.backtest._db') as mock_db:
            mock_db.delete_backtest_job.side_effect = Exception("Database error")

            response = client.delete("/api/v1/backtest/jobs/1")

            assert response.status_code == 500


class TestGetOptimizationHistory:
    """Test GET /api/v1/backtest/optimization/history endpoint"""

    @pytest.fixture
    def client(self):
        """Create test client"""
        from backend.main import app
        return TestClient(app)

    def test_get_optimization_history_returns_200(self, client):
        """GET /api/v1/backtest/optimization/history returns 200"""
        with patch('backend.api.backtest._db') as mock_db:
            mock_db.get_optimization_history.return_value = {
                'total': 0,
                'page': 1,
                'page_size': 20,
                'total_pages': 0,
                'items': []
            }

            response = client.get("/api/v1/backtest/optimization/history")

            assert response.status_code == 200

    def test_get_optimization_history_returns_correct_format(self, client):
        """Response includes pagination metadata and items list"""
        with patch('backend.api.backtest._db') as mock_db:
            mock_db.get_optimization_history.return_value = {
                'total': 1,
                'page': 1,
                'page_size': 20,
                'total_pages': 1,
                'items': [
                    {
                        'id': 1,
                        'strategy_name': 'Test Strategy',
                        'symbol': 'BTCUSDT',
                        'interval': '1h',
                        'start_time': datetime(2024, 1, 1, 0, 0, 0),
                        'end_time': datetime(2024, 1, 31, 23, 59, 59),
                        'status': 'completed',
                        'best_score': 2.5,
                        'best_parameters': {'period': 20},
                        'total_combinations': 10,
                        'created_at': datetime(2024, 1, 1, 12, 0, 0),
                        'completed_at': datetime(2024, 1, 1, 12, 10, 0)
                    }
                ]
            }

            response = client.get("/api/v1/backtest/optimization/history")
            data = response.json()

            assert 'total' in data
            assert 'page' in data
            assert 'page_size' in data
            assert 'total_pages' in data
            assert 'items' in data
            assert data['total'] == 1
            assert data['page'] == 1
            assert len(data['items']) == 1
            assert data['items'][0]['best_score'] == 2.5

    def test_get_optimization_history_filter_by_strategy(self, client):
        """Filter by strategy_name query parameter"""
        with patch('backend.api.backtest._db') as mock_db:
            mock_db.get_optimization_history.return_value = {
                'total': 0,
                'page': 1,
                'page_size': 20,
                'total_pages': 0,
                'items': []
            }

            response = client.get("/api/v1/backtest/optimization/history?strategy_name=Test Strategy")

            mock_db.get_optimization_history.assert_called_once()
            call_kwargs = mock_db.get_optimization_history.call_args[1]
            assert call_kwargs['strategy_name'] == 'Test Strategy'
            assert response.status_code == 200

    def test_get_optimization_history_filter_by_symbol(self, client):
        """Filter by symbol query parameter"""
        with patch('backend.api.backtest._db') as mock_db:
            mock_db.get_optimization_history.return_value = {
                'total': 0,
                'page': 1,
                'page_size': 20,
                'total_pages': 0,
                'items': []
            }

            response = client.get("/api/v1/backtest/optimization/history?symbol=BTCUSDT")

            mock_db.get_optimization_history.assert_called_once()
            call_kwargs = mock_db.get_optimization_history.call_args[1]
            assert call_kwargs['symbol'] == 'BTCUSDT'
            assert response.status_code == 200

    def test_get_optimization_history_filter_by_status(self, client):
        """Filter by status query parameter"""
        with patch('backend.api.backtest._db') as mock_db:
            mock_db.get_optimization_history.return_value = {
                'total': 0,
                'page': 1,
                'page_size': 20,
                'total_pages': 0,
                'items': []
            }

            response = client.get("/api/v1/backtest/optimization/history?status=completed")

            mock_db.get_optimization_history.assert_called_once()
            call_kwargs = mock_db.get_optimization_history.call_args[1]
            assert call_kwargs['status'] == 'completed'
            assert response.status_code == 200

    def test_get_optimization_history_pagination(self, client):
        """Pagination parameters work correctly"""
        with patch('backend.api.backtest._db') as mock_db:
            mock_db.get_optimization_history.return_value = {
                'total': 50,
                'page': 2,
                'page_size': 10,
                'total_pages': 5,
                'items': []
            }

            response = client.get("/api/v1/backtest/optimization/history?page=2&page_size=10")

            mock_db.get_optimization_history.assert_called_once()
            call_kwargs = mock_db.get_optimization_history.call_args[1]
            assert call_kwargs['page'] == 2
            assert call_kwargs['page_size'] == 10
            assert response.status_code == 200

    def test_get_optimization_history_sorting(self, client):
        """Sorting parameters work correctly"""
        with patch('backend.api.backtest._db') as mock_db:
            mock_db.get_optimization_history.return_value = {
                'total': 0,
                'page': 1,
                'page_size': 20,
                'total_pages': 0,
                'items': []
            }

            response = client.get("/api/v1/backtest/optimization/history?sort_by=best_score&sort_order=asc")

            mock_db.get_optimization_history.assert_called_once()
            call_kwargs = mock_db.get_optimization_history.call_args[1]
            assert call_kwargs['sort_by'] == 'best_score'
            assert call_kwargs['sort_order'] == 'asc'
            assert response.status_code == 200

    def test_get_optimization_history_invalid_page_returns_400(self, client):
        """Invalid page number returns 400"""
        response = client.get("/api/v1/backtest/optimization/history?page=0")

        assert response.status_code == 400

    def test_get_optimization_history_invalid_page_size_returns_400(self, client):
        """Invalid page_size returns 400"""
        response = client.get("/api/v1/backtest/optimization/history?page_size=0")

        assert response.status_code == 400

        response = client.get("/api/v1/backtest/optimization/history?page_size=101")

        assert response.status_code == 400

    def test_get_optimization_history_database_error_returns_500(self, client):
        """Database errors return 500 status"""
        with patch('backend.api.backtest._db') as mock_db:
            mock_db.get_optimization_history.side_effect = Exception("Database error")

            response = client.get("/api/v1/backtest/optimization/history")

            assert response.status_code == 500


class TestDeleteOptimizationJob:
    """Test DELETE /api/v1/backtest/optimization/jobs/{job_id} endpoint"""

    @pytest.fixture
    def client(self):
        """Create test client"""
        from backend.main import app
        return TestClient(app)

    def test_delete_optimization_job_returns_200(self, client):
        """DELETE /api/v1/backtest/optimization/jobs/{job_id} returns 200 on success"""
        with patch('backend.api.backtest._db') as mock_db:
            mock_db.delete_optimization_job.return_value = True

            response = client.delete("/api/v1/backtest/optimization/jobs/1")

            assert response.status_code == 200
            data = response.json()
            assert data['success'] is True
            assert 'deleted successfully' in data['message']

    def test_delete_running_optimization_job_returns_400(self, client):
        """DELETE returns 400 when trying to delete running job"""
        with patch('backend.api.backtest._db') as mock_db:
            mock_db.delete_optimization_job.side_effect = ValueError("Cannot delete running optimization job 1")

            response = client.delete("/api/v1/backtest/optimization/jobs/1")

            assert response.status_code == 400
            assert "running" in response.json()['detail'].lower()

    def test_delete_nonexistent_optimization_job_returns_404(self, client):
        """DELETE returns 404 when job not found"""
        with patch('backend.api.backtest._db') as mock_db:
            mock_db.delete_optimization_job.side_effect = ValueError("Optimization job 999 not found")

            response = client.delete("/api/v1/backtest/optimization/jobs/999")

            assert response.status_code == 404
            assert "not found" in response.json()['detail'].lower()

    def test_delete_optimization_job_database_error_returns_500(self, client):
        """Database errors return 500 status"""
        with patch('backend.api.backtest._db') as mock_db:
            mock_db.delete_optimization_job.side_effect = Exception("Database error")

            response = client.delete("/api/v1/backtest/optimization/jobs/1")

            assert response.status_code == 500
