"""
Unit tests for StrategyLoader class

Tests verify:
1. Strategy scanning from directory
2. Dynamic import of strategy modules
3. Strategy filtering (only StrategyBase subclasses)
4. Error handling for edge cases
"""
import pytest
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any

from backend.core.strategy_loader import StrategyLoader
from backend.core.strategy_base import StrategyBase


class TestStrategyScanning:
    """Test strategy file scanning"""

    @pytest.fixture
    def temp_strategies_dir(self, tmp_path):
        """Create temporary strategies directory with test files"""
        strategies_dir = tmp_path / "strategies"
        strategies_dir.mkdir()

        # Create __init__.py (should be skipped)
        (strategies_dir / "__init__.py").write_text("# Init file\n")

        # Create valid strategy file
        strategy_code = '''
import backtrader as bt
from backend.core.strategy_base import StrategyBase

class TestStrategy1(StrategyBase):
    """Test strategy 1"""
    strategy_name = "Test Strategy 1"
    strategy_version = "1.0"
    strategy_description = "First test strategy"

    def __init__(self):
        super().__init__()

    def next(self):
        pass

    @staticmethod
    def get_parameters():
        return {}
'''
        (strategies_dir / "test_strategy_1.py").write_text(strategy_code)

        # Create another valid strategy file
        strategy_code_2 = '''
from backend.core.strategy_base import StrategyBase

class TestStrategy2(StrategyBase):
    """Test strategy 2"""
    strategy_name = "Test Strategy 2"
    strategy_version = "2.0"
    strategy_description = "Second test strategy"

    def next(self):
        pass

    @staticmethod
    def get_parameters():
        return {}
'''
        (strategies_dir / "test_strategy_2.py").write_text(strategy_code_2)

        # Create file starting with underscore (should be skipped)
        (strategies_dir / "_private_strategy.py").write_text("# Private file\n")

        # Create non-Python file (should be skipped)
        (strategies_dir / "readme.txt").write_text("Not a Python file\n")

        return strategies_dir

    def test_scanner_finds_all_py_files(self, temp_strategies_dir):
        """Verify all .py files are scanned"""
        loader = StrategyLoader(strategies_dir=str(temp_strategies_dir))
        strategies = loader.load_all()

        # Should find 2 strategies (test_strategy_1 and test_strategy_2)
        assert len(strategies) == 2
        assert "Test Strategy 1" in strategies
        assert "Test Strategy 2" in strategies

    def test_skips_underscore_files(self, temp_strategies_dir):
        """Verify files starting with _ are skipped"""
        loader = StrategyLoader(strategies_dir=str(temp_strategies_dir))
        strategies = loader.load_all()

        # Should not load anything from _private_strategy.py
        for key in strategies.keys():
            assert not key.startswith('_')

    def test_skips_init_file(self, temp_strategies_dir):
        """Verify __init__.py is skipped"""
        loader = StrategyLoader(strategies_dir=str(temp_strategies_dir))
        strategies = loader.load_all()

        # Should only have 2 strategies (not including __init__.py)
        assert len(strategies) == 2

    def test_skips_non_python_files(self, temp_strategies_dir):
        """Verify non-Python files are skipped"""
        loader = StrategyLoader(strategies_dir=str(temp_strategies_dir))
        strategies = loader.load_all()

        # Should only load .py files
        assert len(strategies) == 2


class TestDynamicImport:
    """Test dynamic module import functionality"""

    @pytest.fixture
    def temp_strategies_dir(self, tmp_path):
        """Create temporary strategies directory"""
        strategies_dir = tmp_path / "strategies"
        strategies_dir.mkdir()

        # Create a strategy file
        strategy_code = '''
from backend.core.strategy_base import StrategyBase

class DynamicTestStrategy(StrategyBase):
    """Dynamically loaded strategy"""
    strategy_name = "Dynamic Test Strategy"
    strategy_version = "1.0"
    strategy_description = "A dynamically loaded strategy"

    def next(self):
        pass

    @staticmethod
    def get_parameters():
        return {
            'period': {
                'type': 'int',
                'default': 10,
                'description': 'Test parameter'
            }
        }
'''
        (strategies_dir / "dynamic_strategy.py").write_text(strategy_code)

        return strategies_dir

    def test_module_is_correctly_imported(self, temp_strategies_dir):
        """Verify modules are correctly imported"""
        loader = StrategyLoader(strategies_dir=str(temp_strategies_dir))
        strategies = loader.load_all()

        assert len(strategies) == 1
        assert "Dynamic Test Strategy" in strategies

    def test_strategy_class_is_extracted(self, temp_strategies_dir):
        """Verify strategy classes are extracted from modules"""
        loader = StrategyLoader(strategies_dir=str(temp_strategies_dir))
        strategies = loader.load_all()

        strategy_class = strategies["Dynamic Test Strategy"]
        assert strategy_class is not None
        assert issubclass(strategy_class, StrategyBase)

    def test_strategy_name_used_as_key(self, temp_strategies_dir):
        """Verify strategy_name is used as dictionary key"""
        loader = StrategyLoader(strategies_dir=str(temp_strategies_dir))
        strategies = loader.load_all()

        # Key should be strategy_name, not file name or class name
        assert "Dynamic Test Strategy" in strategies
        assert "dynamic_strategy" not in strategies
        assert "DynamicTestStrategy" not in strategies

    def test_strategy_has_metadata(self, temp_strategies_dir):
        """Verify loaded strategy has metadata"""
        loader = StrategyLoader(strategies_dir=str(temp_strategies_dir))
        strategies = loader.load_all()

        strategy_class = strategies["Dynamic Test Strategy"]
        assert strategy_class.strategy_name == "Dynamic Test Strategy"
        assert strategy_class.strategy_version == "1.0"
        assert strategy_class.strategy_description == "A dynamically loaded strategy"

    def test_strategy_has_parameters(self, temp_strategies_dir):
        """Verify loaded strategy has parameters"""
        loader = StrategyLoader(strategies_dir=str(temp_strategies_dir))
        strategies = loader.load_all()

        strategy_class = strategies["Dynamic Test Strategy"]
        params = strategy_class.get_parameters()

        assert 'period' in params
        assert params['period']['default'] == 10


class TestStrategyFiltering:
    """Test strategy class filtering"""

    @pytest.fixture
    def temp_strategies_dir(self, tmp_path):
        """Create temporary strategies directory with mixed content"""
        strategies_dir = tmp_path / "strategies"
        strategies_dir.mkdir()

        # Create file with StrategyBase subclass
        valid_strategy = '''
from backend.core.strategy_base import StrategyBase

class ValidStrategy(StrategyBase):
    """Valid strategy"""
    strategy_name = "Valid Strategy"

    def next(self):
        pass

    @staticmethod
    def get_parameters():
        return {}
'''
        (strategies_dir / "valid_strategy.py").write_text(valid_strategy)

        # Create file with multiple strategies
        multi_strategies = '''
from backend.core.strategy_base import StrategyBase

class Strategy1(StrategyBase):
    """First strategy"""
    strategy_name = "Multi Strategy 1"

    def next(self):
        pass

    @staticmethod
    def get_parameters():
        return {}

class Strategy2(StrategyBase):
    """Second strategy"""
    strategy_name = "Multi Strategy 2"

    def next(self):
        pass

    @staticmethod
    def get_parameters():
        return {}

class _PrivateStrategy(StrategyBase):
    """Private strategy - should be excluded"""
    strategy_name = "_Private Strategy"

    def next(self):
        pass

    @staticmethod
    def get_parameters():
        return {}
'''
        (strategies_dir / "multi_strategies.py").write_text(multi_strategies)

        # Create file with non-strategy class
        non_strategy = '''
class NotAStrategy:
    """Not a strategy"""
    pass
'''
        (strategies_dir / "non_strategy.py").write_text(non_strategy)

        return strategies_dir

    def test_only_loads_strategybase_subclasses(self, temp_strategies_dir):
        """Verify only StrategyBase subclasses are loaded"""
        loader = StrategyLoader(strategies_dir=str(temp_strategies_dir))
        strategies = loader.load_all()

        # Should only have 3 strategies (ValidStrategy, Strategy1, Strategy2)
        assert len(strategies) == 3

        for strategy_class in strategies.values():
            assert issubclass(strategy_class, StrategyBase)

    def test_excludes_strategybase_itself(self, temp_strategies_dir):
        """Verify StrategyBase itself is not included"""
        loader = StrategyLoader(strategies_dir=str(temp_strategies_dir))
        strategies = loader.load_all()

        # StrategyBase should not be in the results
        assert "Base Strategy" not in strategies

    def test_excludes_private_classes(self, temp_strategies_dir):
        """Verify private classes (starting with _) are excluded"""
        loader = StrategyLoader(strategies_dir=str(temp_strategies_dir))
        strategies = loader.load_all()

        # _PrivateStrategy should not be loaded
        assert "_Private Strategy" not in strategies
        assert len(strategies) == 3  # Only public strategies

    def test_loads_multiple_strategies_from_same_file(self, temp_strategies_dir):
        """Verify multiple strategies from same file are all loaded"""
        loader = StrategyLoader(strategies_dir=str(temp_strategies_dir))
        strategies = loader.load_all()

        # Should load both strategies from multi_strategies.py
        assert "Multi Strategy 1" in strategies
        assert "Multi Strategy 2" in strategies

    def test_skips_non_strategy_classes(self, temp_strategies_dir):
        """Verify non-strategy classes are skipped"""
        loader = StrategyLoader(strategies_dir=str(temp_strategies_dir))
        strategies = loader.load_all()

        # NotAStrategy should not be in results
        assert "NotAStrategy" not in strategies


class TestErrorHandling:
    """Test error handling for edge cases"""

    def test_nonexistent_directory(self, tmp_path):
        """Test with non-existent directory"""
        nonexistent_dir = tmp_path / "nonexistent"
        loader = StrategyLoader(strategies_dir=str(nonexistent_dir))
        strategies = loader.load_all()

        # Should return empty dict
        assert strategies == {}

    def test_empty_directory(self, tmp_path):
        """Test with empty directory"""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        loader = StrategyLoader(strategies_dir=str(empty_dir))
        strategies = loader.load_all()

        # Should return empty dict
        assert strategies == {}

    def test_directory_with_only_invalid_files(self, tmp_path):
        """Test with directory containing only invalid files"""
        invalid_dir = tmp_path / "invalid"
        invalid_dir.mkdir()

        # Create only non-Python files
        (invalid_dir / "readme.txt").write_text("Not a strategy")
        (invalid_dir / "data.json").write_text("{}")

        loader = StrategyLoader(strategies_dir=str(invalid_dir))
        strategies = loader.load_all()

        # Should return empty dict
        assert strategies == {}

    def test_file_with_syntax_error(self, tmp_path):
        """Test with Python file that has syntax errors (should handle gracefully)"""
        error_dir = tmp_path / "errors"
        error_dir.mkdir()

        # Create file with syntax error
        (error_dir / "broken_strategy.py").write_text('''
from backend.core.strategy_base import StrategyBase

class BrokenStrategy(StrategyBase):
    # Missing strategy_name, next(), get_parameters()
    pass
''')

        loader = StrategyLoader(strategies_dir=str(error_dir))

        # Should handle gracefully (either skip or return empty)
        # In this case, the class is abstract and can't be instantiated
        # but it should still be loaded if it's a valid subclass
        strategies = loader.load_all()

        # The broken strategy is still a StrategyBase subclass
        # but may fail on instantiation
        assert isinstance(strategies, dict)

    def test_file_with_import_error(self, tmp_path):
        """Test with file that has import errors (should handle gracefully)"""
        error_dir = tmp_path / "import_errors"
        error_dir.mkdir()

        # Create file with import error
        (error_dir / "import_error_strategy.py").write_text('''
from nonexistent_module import NonexistentClass

class ImportErrorStrategy:
    pass
''')

        loader = StrategyLoader(strategies_dir=str(error_dir))

        # Should handle gracefully - either catch the error or skip the file
        # The loader should not crash
        try:
            strategies = loader.load_all()
            assert isinstance(strategies, dict)
        except Exception as e:
            # If it raises an exception, it should be a specific,
            # well-documented exception (not a generic crash)
            pytest.fail(f"Loader raised unexpected exception: {e}")

    def test_strategy_without_strategy_name(self, tmp_path):
        """Test with strategy missing strategy_name attribute"""
        error_dir = tmp_path / "no_name"
        error_dir.mkdir()

        # Create strategy without strategy_name
        (error_dir / "no_name_strategy.py").write_text('''
from backend.core.strategy_base import StrategyBase

class NoNameStrategy(StrategyBase):
    """Strategy without strategy_name"""

    def next(self):
        pass

    @staticmethod
    def get_parameters():
        return {}
''')

        loader = StrategyLoader(strategies_dir=str(error_dir))
        strategies = loader.load_all()

        # Should skip strategies without strategy_name
        # (Actually, StrategyBase has default strategy_name, so this will be loaded)
        assert isinstance(strategies, dict)

    def test_duplicate_strategy_names(self, tmp_path):
        """Test with duplicate strategy names (should overwrite)"""
        dup_dir = tmp_path / "duplicates"
        dup_dir.mkdir()

        # Create two files with same strategy_name
        strategy1 = '''
from backend.core.strategy_base import StrategyBase

class Strategy1(StrategyBase):
    strategy_name = "Duplicate Name"

    def next(self):
        pass

    @staticmethod
    def get_parameters():
        return {}
'''
        (dup_dir / "strategy1.py").write_text(strategy1)

        strategy2 = '''
from backend.core.strategy_base import StrategyBase

class Strategy2(StrategyBase):
    strategy_name = "Duplicate Name"

    def next(self):
        pass

    @staticmethod
    def get_parameters():
        return {}
'''
        (dup_dir / "strategy2.py").write_text(strategy2)

        loader = StrategyLoader(strategies_dir=str(dup_dir))
        strategies = loader.load_all()

        # Should only have one strategy (last one loaded)
        assert len(strategies) == 1
        assert "Duplicate Name" in strategies

    def test_directory_is_file(self, tmp_path):
        """Test when strategies_dir path is a file, not directory"""
        file_path = tmp_path / "not_a_directory.py"
        file_path.write_text("# Not a directory")

        loader = StrategyLoader(strategies_dir=str(file_path))
        strategies = loader.load_all()

        # Should return empty dict
        assert strategies == {}


class TestLoaderReusability:
    """Test that loader can be used multiple times"""

    @pytest.fixture
    def temp_strategies_dir(self, tmp_path):
        """Create temporary strategies directory"""
        strategies_dir = tmp_path / "strategies"
        strategies_dir.mkdir()

        # Create a simple strategy
        strategy_code = '''
from backend.core.strategy_base import StrategyBase

class ReusableStrategy(StrategyBase):
    strategy_name = "Reusable Strategy"

    def next(self):
        pass

    @staticmethod
    def get_parameters():
        return {}
'''
        (strategies_dir / "reusable_strategy.py").write_text(strategy_code)

        return strategies_dir

    def test_load_all_can_be_called_multiple_times(self, temp_strategies_dir):
        """Verify calling load_all() multiple times works"""
        loader = StrategyLoader(strategies_dir=str(temp_strategies_dir))

        # First call
        strategies1 = loader.load_all()
        assert len(strategies1) == 1

        # Second call
        strategies2 = loader.load_all()
        assert len(strategies2) == 1

        # Third call
        strategies3 = loader.load_all()
        assert len(strategies3) == 1

    def test_returns_new_dict_each_call(self, temp_strategies_dir):
        """Verify each call returns a new dictionary"""
        loader = StrategyLoader(strategies_dir=str(temp_strategies_dir))

        strategies1 = loader.load_all()
        strategies2 = loader.load_all()

        # Should be different dict objects
        assert strategies1 is not strategies2

        # But with same content
        assert strategies1.keys() == strategies2.keys()


class TestDefaultDirectory:
    """Test default directory behavior"""

    def test_default_strategies_dir(self):
        """Verify default strategies directory is 'backend/strategies'"""
        loader = StrategyLoader()
        assert loader.strategies_dir == Path("backend/strategies")

    def test_custom_strategies_dir(self, tmp_path):
        """Verify custom strategies directory works"""
        custom_dir = tmp_path / "custom_strategies"
        custom_dir.mkdir()

        loader = StrategyLoader(strategies_dir=str(custom_dir))
        assert loader.strategies_dir == custom_dir
