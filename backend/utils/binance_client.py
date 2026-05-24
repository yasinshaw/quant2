import httpx
from datetime import datetime
from typing import List
import logging
import asyncio

from backend.core.data_source import DataSource, CandleData

logger = logging.getLogger(__name__)


class BinanceDataSource(DataSource):
    """Binance data source - public API, no API key needed"""

    def __init__(
        self,
        base_url: str = "https://api.binance.com",
        timeout: float = 30.0,
        http_proxy: str = "",
        https_proxy: str = ""
    ):
        self.base_url = base_url

        # Configure proxy if provided
        proxy = None
        if https_proxy:
            proxy = https_proxy
            logger.info(f"Using proxy: {proxy}")
        elif http_proxy:
            proxy = http_proxy
            logger.info(f"Using proxy: {proxy}")

        self.client = httpx.AsyncClient(timeout=timeout, proxy=proxy)
        logger.info(f"Binance data source initialized: {base_url}")

    async def fetch_candles(
        self,
        symbol: str,
        interval: str,
        start_time: datetime,
        end_time: datetime
    ) -> List[CandleData]:
        """Fetch K-line data from Binance"""
        candles = []
        current_start = start_time

        retry_count = 0
        max_retries = 3

        while current_start < end_time:
            params = {
                'symbol': symbol,
                'interval': interval,
                'startTime': int(current_start.timestamp() * 1000),
                'endTime': int(end_time.timestamp() * 1000),
                'limit': 1000
            }

            try:
                response = await self.client.get(
                    f"{self.base_url}/api/v3/klines",
                    params=params
                )
                response.raise_for_status()
                data = response.json()

                if not data:
                    break

                for item in data:
                    candle = CandleData(
                        symbol=symbol,
                        interval=interval,
                        open_time=datetime.fromtimestamp(item[0] / 1000),
                        close_time=datetime.fromtimestamp(item[6] / 1000),
                        open_price=float(item[1]),
                        high_price=float(item[2]),
                        low_price=float(item[3]),
                        close_price=float(item[4]),
                        volume=float(item[5])
                    )
                    candles.append(candle)

                current_start = datetime.fromtimestamp(data[-1][6] / 1000)
                retry_count = 0

            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:  # Rate limit
                    retry_count += 1
                    if retry_count < max_retries:
                        wait_time = 2 ** retry_count
                        logger.warning(f"Rate limit hit, waiting {wait_time}s")
                        await asyncio.sleep(wait_time)
                        continue
                    else:
                        logger.error(f"Max retries exceeded for {symbol}")
                        raise
                else:
                    logger.error(f"HTTP error fetching candles: {e}")
                    raise

            except Exception as e:
                logger.error(f"Failed to fetch candles: {e}")
                raise

        logger.info(f"Fetched {len(candles)} candles for {symbol} {interval}")
        return candles

    async def get_supported_symbols(self) -> List[str]:
        """Get list of USDT trading pairs"""
        try:
            response = await self.client.get(f"{self.base_url}/api/v3/exchangeInfo")
            response.raise_for_status()
            data = response.json()

            symbols = [
                s['symbol'] for s in data['symbols']
                if s['quoteAsset'] == 'USDT' and s['status'] == 'TRADING'
            ]
            logger.info(f"Supported symbols: {len(symbols)}")
            return sorted(symbols)

        except Exception as e:
            logger.error(f"Failed to get symbols: {e}")
            raise

    async def get_supported_intervals(self) -> List[str]:
        """Return supported K-line intervals"""
        return ['1m', '5m', '15m', '1h', '4h', '1d']
