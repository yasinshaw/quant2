"""Data Manager - coordinates data download, validation, and storage"""

from typing import Dict, List
from datetime import datetime
import logging

from backend.core.data_source import DataSource, CandleData
from backend.database import Database

logger = logging.getLogger(__name__)


class DataManager:
    """Manages data download, validation, and storage"""

    def __init__(self, data_source: DataSource, db: Database):
        """Initialize DataManager

        Args:
            data_source: Data source instance (e.g., BinanceDataSource)
            db: Database instance
        """
        self.data_source = data_source
        self.db = db

    async def download_and_save(
        self,
        symbol: str,
        interval: str,
        start_time: datetime,
        end_time: datetime,
        dataset_id: int = None,
        force_download: bool = False
    ) -> Dict:
        """
        Download and save historical data

        Args:
            symbol: Trading pair symbol (e.g., 'BTCUSDT')
            interval: K-line interval (e.g., '1m', '5m', '1h', '1d')
            start_time: Start datetime
            end_time: End datetime
            dataset_id: Optional dataset ID to associate candles with
            force_download: If True, always download even if data exists

        Returns:
            Dict with keys:
                - symbol: str
                - interval: str
                - count: int
                - start_time: str (ISO format, only on success)
                - end_time: str (ISO format, only on success)
                - status: 'downloaded' | 'already_exists' | 'error'
                - error: str (only on error)
        """
        try:
            # Validate parameters
            if start_time >= end_time:
                raise ValueError("start_time must be before end_time")

            # Check if data already exists (unless force_download)
            if not force_download:
                existing_count = self.db.get_candles_count(symbol, interval, start_time, end_time)
                if existing_count > 0:
                    logger.info(f"Data already exists: {existing_count} candles")
                    return {
                        'symbol': symbol,
                        'interval': interval,
                        'count': existing_count,
                        'start_time': start_time.isoformat(),
                        'end_time': end_time.isoformat(),
                        'status': 'already_exists'
                    }

            # Download from data source
            logger.info(f"Downloading data: {symbol} {interval}")
            candles = await self.data_source.fetch_candles(
                symbol, interval, start_time, end_time
            )

            if not candles:
                raise ValueError("No data received from data source")

            # Validate data
            validated_candles = self._validate_candles(candles, interval)

            # Save to database with dataset_id if provided
            saved_count = self.db.save_candles(validated_candles, dataset_id=dataset_id)

            logger.info(f"Downloaded and saved {saved_count} candles")

            return {
                'symbol': symbol,
                'interval': interval,
                'count': saved_count,
                'start_time': start_time.isoformat(),
                'end_time': end_time.isoformat(),
                'status': 'downloaded'
            }

        except Exception as e:
            logger.error(f"Failed to download data: {e}", exc_info=True)
            return {
                'symbol': symbol,
                'interval': interval,
                'count': 0,
                'status': 'error',
                'error': str(e)
            }

    def _validate_candles(
        self,
        candles: List[CandleData],
        interval: str
    ) -> List[CandleData]:
        """
        Validate candle data quality

        Checks:
        1. Price reasonability (high >= low, open/close within range)
        2. Prices are positive

        Args:
            candles: List of CandleData objects to validate
            interval: K-line interval (for logging)

        Returns:
            List of validated CandleData objects
        """
        validated = []

        for candle in candles:
            # Check price reasonability
            if candle.high_price < candle.low_price:
                logger.warning(
                    f"Invalid candle: high < low at {candle.open_time}"
                )
                continue

            if not (candle.low_price <= candle.open_price <= candle.high_price):
                logger.warning(
                    f"Invalid candle: open price out of range at {candle.open_time}"
                )
                continue

            if not (candle.low_price <= candle.close_price <= candle.high_price):
                logger.warning(
                    f"Invalid candle: close price out of range at {candle.open_time}"
                )
                continue

            # Check positive prices
            if candle.open_price <= 0 or candle.close_price <= 0:
                logger.warning(
                    f"Invalid candle: non-positive price at {candle.open_time}"
                )
                continue

            validated.append(candle)

        if len(validated) < len(candles):
            logger.warning(
                f"Validated {len(validated)}/{len(candles)} candles for {interval}"
            )

        return validated
