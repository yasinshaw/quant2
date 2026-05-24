"""
Data Management API

REST API endpoints for managing historical market data:
- List all available trading symbols
- Get candle data with filters
- Download historical data from Binance
- Check data availability status
"""
from fastapi import APIRouter, HTTPException, status, Query
from typing import Dict, Any
from datetime import datetime
import logging

from backend.database import Database
from backend.core.data_manager import DataManager
from backend.utils.binance_client import BinanceDataSource
from backend.config import settings

logger = logging.getLogger(__name__)


def parse_iso_datetime(datetime_str: str) -> datetime:
    """
    Parse ISO 8601 datetime string, handling both Python and JavaScript formats.

    Handles:
    - Python format: "2024-01-01T00:00:00"
    - JavaScript format: "2024-01-01T00:00:00.000Z"
    - With timezone: "2024-01-01T00:00:00+00:00"

    Args:
        datetime_str: ISO 8601 formatted datetime string

    Returns:
        datetime object (timezone-naive)

    Raises:
        ValueError: If string cannot be parsed
    """
    # Replace 'Z' (UTC timezone marker) with '+00:00' for Python compatibility
    if datetime_str.endswith('Z'):
        datetime_str = datetime_str[:-1] + '+00:00'

    dt = datetime.fromisoformat(datetime_str)

    # Return timezone-naive datetime to avoid comparison issues
    # If datetime has timezone info, remove it
    if dt.tzinfo is not None:
        dt = dt.replace(tzinfo=None)

    return dt

# Create router
router = APIRouter(prefix="/data", tags=["Data"])

# Global instances
_db = Database(settings.database_url)
_data_source = BinanceDataSource(
    base_url=settings.binance_base_url,
    timeout=settings.binance_timeout,
    http_proxy=settings.http_proxy,
    https_proxy=settings.https_proxy
)
_data_manager = DataManager(_data_source, _db)


@router.get("/symbols")
async def list_symbols() -> Dict[str, Any]:
    """
    List all available trading symbols.

    Returns all trading symbols that have data in the database.

    Returns:
        Dict containing list of symbol names:
        {
            "symbols": ["BTCUSDT", "ETHUSDT", "BNBUSDT", ...]
        }
    """
    try:
        symbols = _db.get_all_symbols()
        return {"symbols": symbols}
    except Exception as e:
        logger.error(f"Failed to list symbols: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve symbols"
        )


@router.get("/candles")
async def get_candles(
    symbol: str = Query(..., description="Trading pair (e.g., BTCUSDT)"),
    interval: str = Query(..., description="K-line interval (e.g., 1h)"),
    start_time: str = Query(..., description="Start time (ISO format)"),
    end_time: str = Query(..., description="End time (ISO format)")
) -> Dict[str, Any]:
    """
    Get candle data for specified parameters.

    Retrieves historical candle data from the database for the specified
    symbol, interval, and time range.

    Args:
        symbol: Trading pair symbol (e.g., BTCUSDT)
        interval: K-line interval (e.g., 1m, 5m, 1h, 1d)
        start_time: Start time in ISO format (e.g., 2024-01-01T00:00:00)
        end_time: End time in ISO format (e.g., 2024-01-31T23:59:59)

    Returns:
        Dict containing list of candles:
        {
            "candles": [
                {
                    "open_time": "2024-01-01T00:00:00",
                    "close_time": "2024-01-01T01:00:00",
                    "open": 42000.0,
                    "high": 42500.0,
                    "low": 41800.0,
                    "close": 42300.0,
                    "volume": 100.5
                },
                ...
            ]
        }

    Raises:
        HTTPException: 400 if parameters are invalid
        HTTPException: 500 if database error occurs
    """
    try:
        # Parse datetime strings
        try:
            start_dt = parse_iso_datetime(start_time)
            end_dt = parse_iso_datetime(end_time)
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid datetime format: {e}"
            )

        # Validate time range
        if start_dt >= end_dt:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="start_time must be before end_time"
            )

        # Query database
        candles = _db.get_candles(symbol, interval, start_time, end_time)

        # Convert to dict format
        return {
            "candles": [
                {
                    "open_time": c.open_time.isoformat(),
                    "close_time": c.close_time.isoformat(),
                    "open": c.open_price,
                    "high": c.high_price,
                    "low": c.low_price,
                    "close": c.close_price,
                    "volume": c.volume
                }
                for c in candles
            ]
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get candles: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve candles"
        )


@router.post("/download")
async def download_data(request: dict) -> Dict[str, Any]:
    """
    Download historical data from Binance.

    Downloads historical candle data from Binance and saves it to the database.
    Creates a dataset record for the downloaded data.

    Args:
        request: Dict containing:
            - symbol: Trading pair (e.g., BTCUSDT)
            - interval: K-line interval (e.g., 1h)
            - start_time: Start time in ISO format
            - end_time: End time in ISO format
            - dataset_name: Optional dataset name

    Returns:
        Dict containing:
            - dataset_id: int
            - dataset_name: str
            - symbol: str
            - interval: str
            - count: int (number of candles downloaded)
            - status: 'downloaded' | 'error'
            - message: str (only on success or error)
    """
    # Validate required fields
    required = ["symbol", "interval", "start_time", "end_time"]
    for field in required:
        if field not in request:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Missing required field: {field}"
            )

    # Parse datetime
    try:
        start_dt = parse_iso_datetime(request["start_time"])
        end_dt = parse_iso_datetime(request["end_time"])
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid datetime format: {e}"
        )

    # Get dataset name (optional) or generate auto name
    import time
    dataset_name = request.get("dataset_name")
    if not dataset_name:
        timestamp_suffix = int(time.time())
        dataset_name = f"{request['symbol']} {request['interval']} ({request['start_time'][:10]} ~ {request['end_time'][:10]})_{timestamp_suffix}"

    # Step 1: Create dataset record first
    try:
        dataset_id = _db.create_dataset(
            name=dataset_name,
            symbol=request["symbol"],
            interval=request["interval"],
            start_time=start_dt,
            end_time=end_dt,
            candle_count=0  # Will update after download
        )
    except Exception as e:
        logger.error(f"Failed to create dataset: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create dataset: {e}"
        )

    # Step 2: Download and save candles with dataset_id
    download_result = await _data_manager.download_and_save(
        symbol=request["symbol"],
        interval=request["interval"],
        start_time=start_dt,
        end_time=end_dt,
        dataset_id=dataset_id  # Pass dataset_id to save directly
    )

    # Step 3: Handle different statuses
    if download_result["status"] == "error":
        # Rollback: delete dataset if download failed
        try:
            _db.delete_dataset(dataset_id)
        except Exception as delete_error:
            logger.error(f"Failed to rollback dataset creation: {delete_error}")

        return download_result

    # Step 4: Update dataset metadata and associate candles
    try:
        # Update dataset with actual statistics
        _db.update_dataset_metadata(
            dataset_id=dataset_id,
            candle_count=download_result["count"]
        )

        # Associate candles to dataset (only within time range)
        # This handles both new downloads and already existing data
        _db.update_candles_dataset_id(
            symbol=request["symbol"],
            interval=request["interval"],
            dataset_id=dataset_id,
            start_time=start_dt,
            end_time=end_dt
        )
    except Exception as e:
        logger.warning(f"Failed to update dataset metadata: {e}")
        # Non-critical error, continue

    download_result["dataset_id"] = dataset_id
    download_result["dataset_name"] = dataset_name

    # Add message based on status
    if download_result["status"] == "downloaded":
        download_result["message"] = "Data downloaded successfully"
    elif download_result["status"] == "already_exists":
        download_result["message"] = "Data already exists, dataset created"

    return download_result


@router.get("/status/{symbol}/{interval}")
async def get_data_status(symbol: str, interval: str) -> Dict[str, Any]:
    """
    Check data availability status for a symbol/interval.

    Returns information about how much data is available for the specified
    symbol and interval in the database.

    Args:
        symbol: Trading pair symbol (e.g., BTCUSDT)
        interval: K-line interval (e.g., 1h)

    Returns:
        Dict containing:
        {
            "symbol": "BTCUSDT",
            "interval": "1h",
            "available": true,
            "count": 8760
        }
    """
    # Get total candle count (using a very wide time range)
    start_time = datetime(2000, 1, 1)
    end_time = datetime(2100, 1, 1)

    count = _db.get_candles_count(symbol, interval, start_time, end_time)

    return {
        "symbol": symbol,
        "interval": interval,
        "available": count > 0,
        "count": count
    }


@router.get("/downloaded")
async def get_downloaded_data() -> Dict[str, Any]:
    """
    获取所有已下载数据的摘要列表

    返回所有已下载的历史数据，按 symbol 分组，包含每个 interval 的
    时间范围和 K 线数量信息。

    Returns:
        Dict with "data" key containing list of symbol summaries
        {
            "data": [
                {
                    "symbol": "BTCUSDT",
                    "intervals": [
                        {
                            "interval": "1h",
                            "count": 8760,
                            "start_time": "2024-01-01T00:00:00",
                            "end_time": "2024-12-31T23:00:00"
                        }
                    ]
                }
            ]
        }

    Raises:
        HTTPException: 500 if database error occurs
    """
    try:
        summary = _db.get_downloaded_data_summary()

        # Create new structure with ISO-formatted strings (immutable approach)
        formatted_summary = [
            {
                "symbol": symbol_data["symbol"],
                "intervals": [
                    {
                        "interval": interval_data["interval"],
                        "count": interval_data["count"],
                        "start_time": interval_data["start_time"].isoformat(),
                        "end_time": interval_data["end_time"].isoformat()
                    }
                    for interval_data in symbol_data["intervals"]
                ]
            }
            for symbol_data in summary
        ]

        return {"data": formatted_summary}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get downloaded data summary: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve downloaded data"
        )


@router.get("/datasets")
async def list_datasets() -> Dict[str, Any]:
    """
    List all datasets.

    Returns:
        Dict with "datasets" key containing list of dataset objects
        {
            "datasets": [
                {
                    "id": 123,
                    "name": "BTC 2024 Q1",
                    "symbol": "BTCUSDT",
                    "interval": "1h",
                    "start_time": "2024-01-01T00:00:00",
                    "end_time": "2024-12-31T23:59:59",
                    "candle_count": 8760,
                    "created_at": "2024-03-27T10:30:00"
                }
            ]
        }
    """
    try:
        datasets = _db.get_datasets()

        # Convert to dict format
        formatted_datasets = []
        for dataset in datasets:
            formatted_datasets.append({
                "id": dataset.id,
                "name": dataset.name,
                "symbol": dataset.symbol,
                "interval": dataset.interval,
                "start_time": dataset.start_time.isoformat(),
                "end_time": dataset.end_time.isoformat(),
                "candle_count": dataset.candle_count,
                "created_at": dataset.created_at.isoformat()
            })

        return {"datasets": formatted_datasets}
    except Exception as e:
        logger.error(f"Failed to list datasets: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve datasets"
        )


@router.put("/datasets/{dataset_id}/rename")
async def rename_dataset(dataset_id: int, request: dict) -> Dict[str, Any]:
    """
    Rename a dataset.

    Args:
        dataset_id: Dataset ID
        request: Dict with "name" key

    Returns:
        Dict with "id" and "name" of renamed dataset

    Raises:
        HTTPException: 404 if not found, 400 if name exists
    """
    if "name" not in request:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing required field: name"
        )

    new_name = request["name"]

    try:
        success = _db.rename_dataset(dataset_id, new_name)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Dataset name already exists. Please choose a different name."
            )

        return {"id": dataset_id, "name": new_name}

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to rename dataset: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to rename dataset"
        )


@router.post("/datasets/{dataset_id}/verify")
async def verify_dataset(dataset_id: int) -> Dict[str, Any]:
    """
    Verify and fix dataset metadata.

    Checks that dataset metadata (candle_count, start_time, end_time)
    matches the actual candles data and corrects any discrepancies.

    Args:
        dataset_id: Dataset ID

    Returns:
        Dict with verification results:
        {
            "dataset_id": int,
            "was_valid": bool,
            "corrections": {...},
            "actual": {...}
        }

    Raises:
        HTTPException: 404 if dataset not found
    """
    try:
        result = _db.verify_and_fix_dataset_metadata(dataset_id)
        return result

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to verify dataset: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to verify dataset"
        )


@router.post("/datasets/verify-all")
async def verify_all_datasets() -> Dict[str, Any]:
    """
    Verify and fix metadata for all datasets.

    Returns:
        Dict with verification summary:
        {
            "total_datasets": int,
            "valid_datasets": int,
            "fixed_datasets": int,
            "results": [...]
        }
    """
    try:
        datasets = _db.get_datasets()
        results = []
        fixed_count = 0

        for dataset in datasets:
            try:
                result = _db.verify_and_fix_dataset_metadata(dataset.id)
                results.append(result)
                if not result['was_valid']:
                    fixed_count += 1
            except Exception as e:
                logger.error(f"Failed to verify dataset {dataset.id}: {e}")
                results.append({
                    'dataset_id': dataset.id,
                    'error': str(e)
                })

        return {
            "total_datasets": len(datasets),
            "valid_datasets": len(datasets) - fixed_count,
            "fixed_datasets": fixed_count,
            "results": results
        }

    except Exception as e:
        logger.error(f"Failed to verify all datasets: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to verify datasets"
        )


@router.delete("/datasets/{dataset_id}")
async def delete_dataset_endpoint(dataset_id: int) -> Dict[str, Any]:
    """
    Delete a dataset and all associated candles.

    Args:
        dataset_id: Dataset ID

    Returns:
        Dict with deletion confirmation

    Raises:
        HTTPException: 404 if not found
    """
    try:
        # Delete dataset
        deleted_count = _db.delete_dataset(dataset_id)

        return {
            "dataset_id": dataset_id,
            "deleted_count": deleted_count,
            "message": "Dataset deleted successfully"
        }

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete dataset: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete dataset"
        )


@router.delete("/history/all")
async def clear_all_history() -> Dict[str, Any]:
    """
    Clear all backtest and optimization history.

    Deletes all records from:
    - backtest_jobs
    - backtest_results
    - trades
    - optimization_jobs
    - optimization_results

    Returns:
        Dict containing deletion statistics:
        {
            "backtest_jobs": int,
            "backtest_results": int,
            "trades": int,
            "optimization_jobs": int,
            "optimization_results": int,
            "message": str
        }

    Raises:
        HTTPException: 500 if deletion fails
    """
    try:
        stats = _db.clear_all_history()

        total_deleted = (
            stats["backtest_jobs"] +
            stats["backtest_results"] +
            stats["trades"] +
            stats["optimization_jobs"] +
            stats["optimization_results"]
        )

        logger.info(f"Cleared all history: {stats}")

        return {
            **stats,
            "total_deleted": total_deleted,
            "message": f"Successfully cleared {total_deleted} records"
        }
    except Exception as e:
        logger.error(f"Failed to clear history: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to clear history"
        )


@router.delete("/{symbol}/{interval}")
async def delete_data(symbol: str, interval: str) -> Dict[str, Any]:
    """
    Delete all candles for a specific symbol and interval.

    Args:
        symbol: Trading pair symbol (e.g., BTCUSDT)
        interval: K-line interval (e.g., 1h)

    Returns:
        Dict containing deletion confirmation

    Raises:
        HTTPException: 404 if no data found, 500 if deletion fails
    """
    try:
        deleted_count = _db.delete_candles_by_symbol_interval(symbol, interval)

        if deleted_count == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No data found for {symbol} {interval}"
            )

        logger.info(f"Deleted {deleted_count} candles for {symbol} {interval}")

        return {
            "symbol": symbol,
            "interval": interval,
            "deleted_count": deleted_count,
            "message": "Successfully deleted data"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete data: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete data"
        )


