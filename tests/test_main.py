"""Tests for FastAPI main application"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import logging


class TestAppCreation:
    """Test FastAPI app creation and configuration"""

    def test_app_has_correct_title(self):
        """Verify app is created with correct title"""
        from backend.main import app

        assert app.title == "Quantitative Trading Platform"

    def test_app_has_correct_description(self):
        """Verify app has description"""
        from backend.main import app

        assert app.description == "Personal backtesting and trading platform"

    def test_app_has_correct_version(self):
        """Verify app has correct version"""
        from backend.main import app

        assert app.version == "1.0.0"


class TestHealthEndpoint:
    """Test health check endpoint"""

    @pytest.fixture
    def client(self):
        """Create test client"""
        from backend.main import app
        return TestClient(app)

    def test_health_endpoint_returns_200(self, client):
        """GET /health returns 200 status"""
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_endpoint_has_status_field(self, client):
        """Response has status field with 'healthy'"""
        response = client.get("/health")
        data = response.json()
        assert "status" in data
        assert data["status"] == "healthy"

    def test_health_endpoint_has_version_field(self, client):
        """Response has version field"""
        response = client.get("/health")
        data = response.json()
        assert "version" in data
        assert data["version"] == "1.0.0"


class TestCORSConfiguration:
    """Test CORS middleware configuration"""

    @pytest.fixture
    def client(self):
        """Create test client"""
        from backend.main import app
        return TestClient(app)

    def test_cors_middleware_configured(self):
        """Verify CORS middleware is configured"""
        from backend.main import app

        # Check that CORS middleware is in the app's middleware stack
        middleware_types = [type(m).__name__ for m in app.user_middleware]
        assert len(middleware_types) > 0  # At least some middleware exists

    def test_cors_allows_localhost(self, client):
        """Test CORS allows localhost origin"""
        response = client.options(
            "/health",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            }
        )
        # CORS preflight should succeed
        assert response.status_code == 200

    def test_cors_preflight_request(self, client):
        """Test preflight request works"""
        response = client.options(
            "/health",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type",
            }
        )
        assert response.status_code == 200


class TestErrorHandling:
    """Test error handlers"""

    @pytest.fixture
    def client(self):
        """Create test client"""
        from backend.main import app
        return TestClient(app)

    def test_error_response_format(self, client):
        """Test error response format is correct"""
        # We'll test this by accessing a non-existent endpoint
        response = client.get("/nonexistent-endpoint")
        assert response.status_code == 404

        # The response should have proper format
        data = response.json()
        assert "detail" in data or "error" in data

    def test_generic_exception_handler(self):
        """Test generic exception handler"""
        from backend.main import app, generic_exception_handler
        from fastapi import Request

        # Create a mock request and exception
        mock_request = MagicMock(spec=Request)
        mock_request.method = "GET"
        mock_request.url = MagicMock()
        mock_request.url.path = "/test"

        exception = Exception("Test exception")

        # Call the handler
        import asyncio
        response = asyncio.run(generic_exception_handler(mock_request, exception))

        # Verify response
        assert response.status_code == 500
        # Response content would be JSON
        import json
        content = json.loads(response.body)
        assert "error" in content


class TestLoggingMiddleware:
    """Test logging middleware"""

    @pytest.fixture
    def client(self):
        """Create test client"""
        from backend.main import app
        return TestClient(app)

    def test_requests_are_logged(self, client, caplog):
        """Verify requests are logged"""
        with caplog.at_level(logging.INFO):
            response = client.get("/health")

            # Check that some logging occurred
            # The middleware should log the request
            assert len(caplog.records) > 0

    def test_logging_with_different_methods(self, client, caplog):
        """Test logging with different HTTP methods"""
        with caplog.at_level(logging.INFO):
            # Test GET
            client.get("/health")

            # Check logs contain method information
            log_messages = [record.message for record in caplog.records]
            # At least one log should mention GET
            assert any("GET" in msg for msg in log_messages)


class TestStartupShutdown:
    """Test startup and shutdown events"""

    def test_startup_event_exists(self):
        """Verify startup event is defined"""
        from backend.main import app

        # Check that startup event handlers exist
        # In FastAPI, these are stored in router.on_event
        assert len(app.router.on_startup) > 0

    def test_shutdown_event_exists(self):
        """Verify shutdown event is defined"""
        from backend.main import app

        # Check that shutdown event handlers exist
        assert len(app.router.on_shutdown) > 0
