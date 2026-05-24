from abc import ABC, abstractmethod
from typing import List
from datetime import datetime
from dataclasses import dataclass


@dataclass
class CandleData:
    """K-line data transfer object"""
    symbol: str
    interval: str
    open_time: datetime
    close_time: datetime
    open_price: float
    high_price: float
    low_price: float
    close_price: float
    volume: float


class DataSource(ABC):
    """Abstract base class for data sources (Binance, OKX, etc.)"""

    @abstractmethod
    async def fetch_candles(
        self,
        symbol: str,
        interval: str,
        start_time: datetime,
        end_time: datetime
    ) -> List[CandleData]:
        """
        Fetch K-line candle data

        Args:
            symbol: Trading pair symbol (e.g., 'BTCUSDT')
            interval: K-line interval (e.g., '1m', '5m', '1h', '1d')
            start_time: Start datetime
            end_time: End datetime

        Returns:
            List of CandleData objects
        """
        pass

    @abstractmethod
    async def get_supported_symbols(self) -> List[str]:
        """
        Get list of supported trading pairs

        Returns:
            List of symbol strings (e.g., ['BTCUSDT', 'ETHUSDT'])
        """
        pass

    @abstractmethod
    async def get_supported_intervals(self) -> List[str]:
        """
        Get list of supported K-line intervals

        Returns:
            List of interval strings (e.g., ['1m', '5m', '1h', '1d'])
        """
        pass
