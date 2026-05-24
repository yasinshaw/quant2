"""
Strategy Loader

Dynamically loads user-created strategy files from the strategies directory.
Enables users to add new strategies by simply creating Python files
without modifying core code.
"""
import sys
import importlib.util
import inspect
import logging
from pathlib import Path
from typing import Dict, Type

from backend.core.strategy_base import StrategyBase


logger = logging.getLogger(__name__)


class StrategyLoader:
    """
    Strategy Loader - Dynamically loads strategy classes

    Scans the strategies directory and loads all StrategyBase subclasses.
    Users can add strategies by creating .py files in the strategies directory.
    """

    def __init__(self, strategies_dir: str = None):
        """
        Initialize StrategyLoader

        Args:
            strategies_dir: Path to strategies directory (default: "backend/strategies" or "strategies")
        """
        if strategies_dir is None:
            # Try to find strategies directory automatically
            # Check relative to project root (when running from backend/ directory)
            project_root = Path(__file__).parent.parent.parent
            possible_paths = [
                project_root / "backend" / "strategies",  # backend/strategies from project root
                Path("strategies"),  # strategies from backend/ directory
                Path(__file__).parent.parent / "strategies",  # Relative to this file
            ]

            for path in possible_paths:
                if path.exists() and path.is_dir():
                    strategies_dir = str(path)
                    logger.info(f"Auto-detected strategies directory: {strategies_dir}")
                    break

            # Fallback to default
            if strategies_dir is None:
                strategies_dir = "strategies"
                logger.warning(f"Could not auto-detect strategies directory, using default: {strategies_dir}")

        self.strategies_dir = Path(strategies_dir)

    def load_all(self) -> Dict[str, Type[StrategyBase]]:
        """
        Scan strategies directory and load all strategy classes

        Returns:
            Dict[str, Type[StrategyBase]]: Dictionary mapping strategy_name to strategy_class

        Example:
            >>> loader = StrategyLoader()
            >>> strategies = loader.load_all()
            >>> for name, strategy_class in strategies.items():
            ...     print(f"{name}: {strategy_class.strategy_version}")
        """
        strategies = {}

        # Check if directory exists
        if not self.strategies_dir.exists():
            logger.warning(
                f"Strategies directory does not exist: {self.strategies_dir}"
            )
            return strategies

        # Check if directory is a directory
        if not self.strategies_dir.is_dir():
            logger.error(
                f"Strategies path is not a directory: {self.strategies_dir}"
            )
            return strategies

        # Scan all .py files
        for file_path in self.strategies_dir.glob("*.py"):
            # Skip files starting with underscore (including __init__.py)
            if file_path.name.startswith("_"):
                logger.debug(f"Skipping file: {file_path.name}")
                continue

            try:
                # Dynamically import module
                module_name = file_path.stem
                logger.debug(f"Loading module: {module_name} from {file_path}")

                spec = importlib.util.spec_from_file_location(module_name, file_path)
                if spec is None or spec.loader is None:
                    logger.warning(f"Failed to create spec for: {file_path}")
                    continue

                module = importlib.util.module_from_spec(spec)
                # Register module in sys.modules so Backtrader can find it
                sys.modules[module_name] = module
                spec.loader.exec_module(module)

                # Find all StrategyBase subclasses
                for name, obj in inspect.getmembers(module, inspect.isclass):
                    # Skip StrategyBase itself
                    if obj is StrategyBase:
                        continue

                    # Only include StrategyBase subclasses
                    if not issubclass(obj, StrategyBase):
                        continue

                    # Skip private classes (starting with _)
                    if obj.__name__.startswith('_'):
                        logger.debug(f"Skipping private class: {obj.__name__}")
                        continue

                    # Verify strategy has strategy_name attribute
                    if not hasattr(obj, 'strategy_name'):
                        logger.warning(
                            f"Strategy {obj.__name__} missing strategy_name attribute"
                        )
                        continue

                    # Add to strategies dict using strategy_name as key
                    strategy_name = obj.strategy_name
                    if strategy_name in strategies:
                        logger.warning(
                            f"Duplicate strategy name '{strategy_name}', "
                            f"overwriting previous strategy"
                        )

                    strategies[strategy_name] = obj
                    logger.info(
                        f"Loaded strategy: {strategy_name} "
                        f"(version {obj.strategy_version})"
                    )

            except SyntaxError as e:
                logger.error(
                    f"Syntax error in {file_path}: {e}"
                )
                continue
            except ImportError as e:
                logger.error(
                    f"Import error in {file_path}: {e}"
                )
                continue
            except Exception as e:
                logger.error(
                    f"Unexpected error loading {file_path}: {e}",
                    exc_info=True
                )
                continue

        logger.info(f"Loaded {len(strategies)} strategies total")
        return strategies
