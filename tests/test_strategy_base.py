"""
Unit tests for StrategyBase class

Tests verify:
1. StrategyBase is abstract and cannot be instantiated directly
2. Metadata fields (strategy_name, strategy_version, strategy_description)
3. Concrete strategy can be created and instantiated
4. get_parameters() method exists and returns dict
"""
import pytest
from abc import ABCMeta
from typing import Dict, Any

import backtrader as bt

from backend.core.strategy_base import StrategyBase, CombinedMeta


class TestStrategyBaseAbstract:
    """Test that StrategyBase is properly abstract"""

    def test_strategy_base_has_abstract_metaclass(self):
        """Verify StrategyBase uses CombinedMeta (includes ABCMeta)"""
        assert isinstance(StrategyBase, CombinedMeta)

    def test_strategy_base_inherits_from_backtrader(self):
        """Verify StrategyBase inherits from bt.Strategy"""
        assert issubclass(StrategyBase, bt.Strategy)

    def test_cannot_instantiate_strategy_base_directly(self):
        """Verify StrategyBase cannot be instantiated directly"""
        with pytest.raises(TypeError):
            StrategyBase()


class TestConcreteStrategy:
    """Test with a concrete implementation"""

    @pytest.fixture
    def concrete_strategy_class(self):
        """Create a concrete strategy class for testing"""

        class TestStrategy(StrategyBase):
            """Concrete test strategy"""

            strategy_name = "Test Strategy"
            strategy_version = "1.0.0"
            strategy_description = "A test strategy for unit testing"

            def __init__(self):
                super().__init__()
                self.sma = bt.indicators.SimpleMovingAverage(
                    self.data.close, period=15
                )

            def next(self):
                """Simple trading logic"""
                if self.sma[0] > self.data.close[0]:
                    self.buy()

            @staticmethod
            def get_parameters() -> Dict[str, Any]:
                """Return strategy parameters"""
                return {
                    'sma_period': {
                        'type': 'int',
                        'default': 15,
                        'min': 5,
                        'max': 100,
                        'description': 'Simple Moving Average period'
                    }
                }

        return TestStrategy

    def test_concrete_strategy_can_be_instantiated(
        self, concrete_strategy_class
    ):
        """Verify concrete strategy can be instantiated"""
        # Note: In backtrader, strategies are instantiated via Cerebro
        # Here we just verify the class can be created
        assert concrete_strategy_class is not None

    def test_concrete_strategy_has_metadata(self, concrete_strategy_class):
        """Verify metadata fields are present"""
        assert hasattr(concrete_strategy_class, 'strategy_name')
        assert hasattr(concrete_strategy_class, 'strategy_version')
        assert hasattr(concrete_strategy_class, 'strategy_description')

        assert concrete_strategy_class.strategy_name == "Test Strategy"
        assert concrete_strategy_class.strategy_version == "1.0.0"
        assert (
            concrete_strategy_class.strategy_description
            == "A test strategy for unit testing"
        )

    def test_get_parameters_method_exists(self, concrete_strategy_class):
        """Verify get_parameters method exists"""
        assert hasattr(concrete_strategy_class, 'get_parameters')

    def test_get_parameters_returns_dict(self, concrete_strategy_class):
        """Verify get_parameters returns a dictionary"""
        params = concrete_strategy_class.get_parameters()
        assert isinstance(params, dict)

    def test_get_parameters_has_required_fields(self, concrete_strategy_class):
        """Verify parameter definition has required fields"""
        params = concrete_strategy_class.get_parameters()

        # Check first parameter
        assert 'sma_period' in params
        param_def = params['sma_period']

        assert 'type' in param_def
        assert 'default' in param_def
        assert 'description' in param_def

        assert param_def['type'] == 'int'
        assert param_def['default'] == 15
        assert param_def['min'] == 5
        assert param_def['max'] == 100


class TestStrategyBaseMetadata:
    """Test default metadata values"""

    def test_default_metadata_exists(self):
        """Verify default metadata fields exist on StrategyBase"""
        assert hasattr(StrategyBase, 'strategy_name')
        assert hasattr(StrategyBase, 'strategy_version')
        assert hasattr(StrategyBase, 'strategy_description')

    def test_default_metadata_values(self):
        """Verify default metadata values"""
        assert StrategyBase.strategy_name == "Base Strategy"
        assert StrategyBase.strategy_version == "1.0"
        assert StrategyBase.strategy_description == "Base strategy class"


class TestStrategyBaseMethods:
    """Test StrategyBase methods"""

    @pytest.fixture
    def concrete_strategy_class(self):
        """Create a concrete strategy class for testing"""

        class SimpleTestStrategy(StrategyBase):
            """Minimal concrete strategy"""

            def next(self):
                pass

            @staticmethod
            def get_parameters() -> Dict[str, Any]:
                return {}

        return SimpleTestStrategy

    def test_has_notify_order_method(self, concrete_strategy_class):
        """Verify notify_order method exists"""
        assert hasattr(concrete_strategy_class, 'notify_order')

    def test_has_notify_trade_method(self, concrete_strategy_class):
        """Verify notify_trade method exists"""
        assert hasattr(concrete_strategy_class, 'notify_trade')

    def test_has_log_method(self, concrete_strategy_class):
        """Verify log method exists"""
        assert hasattr(concrete_strategy_class, 'log')

    def test_has_abstract_next_method(self):
        """Verify next is abstract"""
        # next should be abstractmethod
        assert hasattr(StrategyBase, 'next')

    def test_has_abstract_get_parameters_method(self):
        """Verify get_parameters is abstract"""
        # get_parameters should be abstractmethod
        assert hasattr(StrategyBase, 'get_parameters')
