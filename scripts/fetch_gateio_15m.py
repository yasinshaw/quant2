"""
从 Gate.io 拉 ETH/USDT 15m K线 → CSV
覆盖 2024-01-01 至今，每次 2000 条
"""
import requests
import pandas as pd
import time
import os

def fetch_gateio_15m(start_date='2024-01-01'):
    proxy = os.environ.get('HTTPS_PROXY', os.environ.get('HTTP_PROXY', ''))
    proxies = {'https': proxy, 'http': proxy} if proxy else None
    if proxy:
        print(f"Using proxy: {proxy}")

    base_url = "https://api.gateio.ws/api/v4/spot/candlesticks"
    pair = "ETH_USDT"
    interval = "15m"
    
    # Gate.io 用 Unix 秒时间戳
    start_ts = int(pd.Timestamp(start_date).timestamp())
    end_ts = int(pd.Timestamp.now().timestamp())
    
    all_data = []
    current_start = start_ts
    
    while current_start < end_ts:
        params = {
            'currency_pair': pair,
            'interval': interval,
            'from': current_start,
            'limit': 2000,  # gate.io max
        }
        try:
            resp = requests.get(base_url, params=params, proxies=proxies, timeout=30)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            print(f"  Error: {e}, retrying in 5s...")
            time.sleep(5)
            continue
        
        if not data:
            break
        
        all_data.extend(data)
        # Gate.io 返回 [timestamp, volume, ...格式]
        last_ts = int(data[-1][0])
        current_start = last_ts + 1
        print(f"  Fetched {len(all_data)} candles, latest: {pd.Timestamp(last_ts, unit='s')}")
        
        if len(data) < 2000:
            break
        time.sleep(0.3)
    
    # Parse: [t, vol, open, high, low, close, ...]
    records = []
    for d in all_data:
        records.append({
            'timestamp': int(d[0]),
            'open': float(d[2]),
            'high': float(d[3]),
            'low': float(d[4]),
            'close': float(d[5]),
            'volume': float(d[1]),
        })
    
    df = pd.DataFrame(records)
    df['datetime'] = pd.to_datetime(df['timestamp'], unit='s')
    df = df.drop_duplicates(subset='timestamp').sort_values('timestamp').reset_index(drop=True)
    df = df.set_index('datetime')
    
    outfile = 'data/ethusdt_15m_gateio.csv'
    df.to_csv(outfile)
    print(f"\nSaved {len(df)} candles to {outfile}")
    print(f"Range: {df.index[0]} → {df.index[-1]}")
    return df


if __name__ == '__main__':
    fetch_gateio_15m()
