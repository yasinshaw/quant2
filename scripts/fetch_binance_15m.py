"""
拉取 Binance ETHUSDT 15m 历史 K线 → CSV
覆盖 2024-01-01 至今（约 2 年）
"""
import ccxt
import pandas as pd
import time
import sys
import os

def fetch_binance_15m(symbol='ETH/USDT', start_date='2024-01-01', timeframe='15m'):
    # 代理设置
    proxy = os.environ.get('HTTPS_PROXY', os.environ.get('HTTP_PROXY', ''))
    
    exchange = ccxt.binance({
        'enableRateLimit': True,
        'options': {'defaultType': 'spot'},
    })
    if proxy:
        exchange.proxies = {'https': proxy, 'http': proxy}
        print(f"Using proxy: {proxy}")

    since = exchange.parse8601(f'{start_date}T00:00:00Z')
    all_ohlcv = []
    
    print(f"Fetching {symbol} {timeframe} from {start_date}...")
    
    while True:
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe, since=since, limit=1000)
        if not ohlcv:
            break
        all_ohlcv.extend(ohlcv)
        last_ts = ohlcv[-1][0]
        since = last_ts + 1
        print(f"  Fetched {len(all_ohlcv)} candles, latest: {pd.Timestamp(last_ts, unit='ms')}")
        if len(ohlcv) < 1000:
            break
        time.sleep(0.2)

    df = pd.DataFrame(all_ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
    df = df.drop_duplicates(subset='timestamp').sort_values('timestamp').reset_index(drop=True)
    df = df.set_index('datetime')
    
    outfile = 'data/ethusdt_15m_binance.csv'
    df.to_csv(outfile)
    print(f"\nSaved {len(df)} candles to {outfile}")
    print(f"Range: {df.index[0]} → {df.index[-1]}")
    return df


if __name__ == '__main__':
    fetch_binance_15m()
