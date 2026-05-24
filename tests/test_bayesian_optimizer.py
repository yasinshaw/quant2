"""
Unit tests for Bayesian optimizer
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from backend.core.bayesian_optimizer import BayesianOptimizer
from backend.core.backtest_engine import BacktestEngine
from backend.database import Database

# Check if Optuna is available
try:
    import optuna
    OPTUNA_AVAILABLE = True
except ImportError:
    OPTUNA_AVAILABLE = False


@pytest.fixture
def mock_backtest_engine():
    """Create mock backtest engine"""
    engine = Mock(spec=BacktestEngine)
    engine.db = Mock(spec=Database)
    return engine


@pytest.fixture
def mock_strategy_class():
    """Create mock strategy class"""
    strategy = Mock()
    strategy.strategy_name = "TestStrategy"
    strategy.__name__ = "TestStrategy"
    return strategy


@pytest.mark.skipif(not OPTUNA_AVAILABLE, reason="Optuna not installed")
@pytest.mark.asyncio
async def test_bayesian_optimizer_initialization(mock_backtest_engine):
    """Test optimizer initializes correctly"""
    optimizer = BayesianOptimizer(mock_backtest_engine)

    assert optimizer.backtest_engine == mock_backtest_engine
    assert optimizer.db == mock_backtest_engine.db


@pytest.mark.skipif(not OPTUNA_AVAILABLE, reason="Optuna not installed")
@pytest.mark.asyncio
async def test_bayesian_optimizer_verifies_optuna_available():
    """Test that optimizer checks for Optuna availability"""
    engine = Mock(spec=BacktestEngine)
    engine.db = Mock(spec=Database)

    # Should not raise ImportError if Optuna is available
    optimizer = BayesianOptimizer(engine)
    assert optimizer is not None
    assert hasattr(optimizer, 'optuna')


def test_bayesian_optimizer_import_error_without_optuna():
    """Test that optimizer raises ImportError when Optuna is not installed"""
    if OPTUNA_AVAILABLE:
        pytest.skip("Optuna is installed, cannot test import error")

    engine = Mock(spec=BacktestEngine)
    engine.db = Mock(spec=Database)

    # Should raise ImportError with helpful message
    with pytest.raises(ImportError) as exc_info:
        BayesianOptimizer(engine)

    assert "Optuna is not installed" in str(exc_info.value)
    assert "pip install optuna" in str(exc_info.value)



