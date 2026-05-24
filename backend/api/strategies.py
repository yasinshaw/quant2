"""
Strategies Management API

REST API endpoints for managing trading strategies:
- List all available strategies
- Refresh strategy list from folder
- Get specific strategy details
- Hide/show strategies
"""
from fastapi import APIRouter, HTTPException, Query, status
from typing import Dict, Any, List

from backend.core.strategy_loader import StrategyLoader
from backend.core.strategy_base import StrategyBase
from backend.database import Database
from backend.config import settings


# Create router
router = APIRouter(prefix="/strategies", tags=["Strategies"])

# Global instances
_loader = StrategyLoader()
_db = Database(settings.database_url)


@router.get("/")
async def list_strategies(
    show_hidden: bool = Query(False, description="Include hidden strategies")
) -> Dict[str, Any]:
    """
    List all available strategies.

    Args:
        show_hidden: If true, include hidden strategies (marked with is_hidden)

    Returns:
        Dict containing list of strategy metadata with hidden status
    """
    strategies = _loader.load_all()
    hidden_names = set(_db.get_hidden_strategy_names())

    result = []
    for cls in strategies.values():
        is_hidden = cls.strategy_name in hidden_names
        if not show_hidden and is_hidden:
            continue
        result.append({
            "name": cls.strategy_name,
            "version": cls.strategy_version,
            "description": cls.strategy_description,
            "is_hidden": is_hidden
        })

    return {"strategies": result}


@router.post("/refresh")
async def refresh_strategies() -> Dict[str, Any]:
    """
    Refresh strategy list from folder.

    Re-scans the strategies directory and reloads all strategy classes.

    Returns:
        Dict containing message and count
    """
    strategies = _loader.load_all()

    return {
        "message": "Strategies refreshed",
        "count": len(strategies)
    }


@router.get("/{strategy_name}")
async def get_strategy(strategy_name: str) -> Dict[str, Any]:
    """
    Get specific strategy details.

    Args:
        strategy_name: Name of the strategy to retrieve

    Returns:
        Dict containing strategy metadata and parameters

    Raises:
        HTTPException: 404 if strategy not found
    """
    strategies = _loader.load_all()

    if strategy_name not in strategies:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Strategy '{strategy_name}' not found"
        )

    strategy_class = strategies[strategy_name]

    params = strategy_class.get_parameters()
    params = {
        k: v for k, v in params.items()
        if not k.startswith('_')
    }

    hidden_names = set(_db.get_hidden_strategy_names())

    return {
        "name": strategy_class.strategy_name,
        "version": strategy_class.strategy_version,
        "description": strategy_class.strategy_description,
        "is_hidden": strategy_name in hidden_names,
        "parameters": params
    }


@router.post("/{strategy_name}/hide")
async def hide_strategy(strategy_name: str) -> Dict[str, Any]:
    """Hide a strategy from the strategy list."""
    strategies = _loader.load_all()
    if strategy_name not in strategies:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Strategy '{strategy_name}' not found"
        )

    _db.hide_strategy(strategy_name)
    return {"message": f"Strategy '{strategy_name}' hidden"}


@router.post("/{strategy_name}/show")
async def show_strategy(strategy_name: str) -> Dict[str, Any]:
    """Show a previously hidden strategy."""
    _db.show_strategy(strategy_name)
    return {"message": f"Strategy '{strategy_name}' is now visible"}
